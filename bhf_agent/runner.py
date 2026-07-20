"""Reusable BHF agent runner."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .adapters import ChatAdapter, OllamaAdapter, OpenAICompatibleAdapter
from .ckl import (
    build_canonical_context,
    build_canonical_fallback_answer,
    build_canonical_query,
    canonical_context_has_strong_match,
    format_canonical_context_for_prompt,
    load_canonical_library,
)
from .config import AgentConfig, ConfigError
from .genre import classify_genre
from .knowledge import LocalKnowledgeBundle, lookup_local_knowledge
from .map_tools import build_map_tool_context
from .memory import (
    SessionMemory,
    append_session_turn,
    load_session_memory,
    save_session_memory,
)
from .models import (
    AgentResult,
    ChatRequest,
    ChatResponse,
    PipelineContext,
    RepairAttempt,
    ValidationResult,
)
from .model_response_validation import (
    ANSWER_CONTRACT,
    SEARCH_RESULTS_CONTRACT,
    ModelResponseValidationResult,
    normalize_model_response,
    structured_response_format,
)
from .observability import render_log_record, summarize_usage
from .profiles import ProfileLoader
from .prompts import PROMPT_VERSION, build_prompt, strategy_for_profile
from .question_types import classify_question_type
from .repair import build_repair_prompt, decide_repair
from .references import detect_reference
from .runner_state import PIPELINE_STEPS, STEP_INDEX, STEP_MESSAGES, STAGE_TO_STEP, TOTAL_STEPS
from .validation import validate_response
from framework.canonical_library import (
    CanonicalLibrary,
    CKLRuntimeCache,
    CKLRetrievalService,
    JsonPublicAnswerCache,
    NullPublicAnswerCache,
    PublicAnswerCache,
    build_context_cache_key,
    build_model_signature,
    build_prompt_context_hash,
    build_response_cache_key,
    build_retrieval_cache_key,
    load_framework_version,
    load_framework_version_fingerprint,
    normalize_public_question,
    public_cache_key,
)


StatusCallback = Callable[[dict[str, Any]], None]
OBSERVABILITY_LOGGER = logging.getLogger("bhf_agent.observability")


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_object_id_list(values: Any) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        object_id = str(value or "").strip()
        if not object_id or object_id in seen:
            continue
        normalized.append(object_id)
        seen.add(object_id)
    return normalized


def _canonical_library_object_ids(metadata: dict[str, Any], canonical_context: dict[str, Any]) -> tuple[list[str], list[str]]:
    prompt_ids = _normalize_object_id_list(metadata.get("retrieved_object_ids") or [])
    object_ids = list(prompt_ids)
    seen_ids = set(object_ids)

    for topic in canonical_context.get("retrieved_topics") or []:
        if not isinstance(topic, dict):
            continue
        for related in topic.get("related_objects") or []:
            if not isinstance(related, dict):
                continue
            related_id = str(related.get("id") or "").strip()
            if not related_id or related_id in seen_ids:
                continue
            object_ids.append(related_id)
            seen_ids.add(related_id)

    return prompt_ids, object_ids


def _scripture_reference_text(reference: Any) -> str:
    if hasattr(reference, "book"):
        book = str(getattr(reference, "book", "") or "").strip()
        start_chapter = getattr(reference, "start_chapter", None)
        start_verse = getattr(reference, "start_verse", None)
        end_chapter = getattr(reference, "end_chapter", None)
        end_verse = getattr(reference, "end_verse", None)
    elif isinstance(reference, dict):
        book = str(reference.get("book") or "").strip()
        start_chapter = reference.get("start_chapter")
        start_verse = reference.get("start_verse")
        end_chapter = reference.get("end_chapter")
        end_verse = reference.get("end_verse")
    else:
        return str(reference or "").strip()

    if not book:
        return ""
    if start_chapter is None:
        return book

    text = f"{book} {start_chapter}"
    if start_verse is not None:
        text += f":{start_verse}"
        if end_chapter is not None and end_chapter != start_chapter:
            text += f"-{end_chapter}"
        if end_verse is not None:
            text += f":{end_verse}"
    return text


def _canonical_context_result_ids(context: dict[str, Any] | None) -> list[str]:
    if not context:
        return []
    ids: list[str] = []
    for topic in context.get("retrieved_topics") or []:
        if not isinstance(topic, dict):
            continue
        object_id = str(topic.get("id") or "").strip()
        if object_id and object_id not in ids:
            ids.append(object_id)
    return ids


def _search_result_match_type(result: Any) -> str:
    value = getattr(result, "match_type", None)
    if value is None:
        value = getattr(result, "category", None)
    return str(value or "").strip().lower()


def _canonical_miss_reason(
    *,
    library: CanonicalLibrary,
    canonical_query: str,
    question: str,
    canonical_context: dict[str, Any] | None,
    answer_mode: str,
    minimum_relevance_score: float,
    include_placeholders: bool,
    allowed_statuses: tuple[str, ...],
    max_results: int,
) -> dict[str, Any]:
    gap: dict[str, Any] = {
        "normalized_question": " ".join(str(question or "").split()),
        "detected_scripture_references": [],
        "detected_books": [],
        "retrieval_terms": [],
        "top_rejected_results": [],
        "rejection_reasons": [],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "answer_mode": answer_mode,
    }

    try:
        service = CKLRetrievalService(library=library)
        search_response = service.search(
            canonical_query or question,
            limit=max(max_results * 4, max_results, 12),
            min_score=0.0,
            debug=True,
        )
    except Exception as exc:  # noqa: BLE001 - diagnostics must never block answers
        gap["rejection_reasons"] = ["retrieval_failed"]
        gap["retrieval_error"] = str(exc)
        return gap

    analysis = search_response.analysis
    gap["retrieval_terms"] = list(dict.fromkeys(analysis.terms or []))
    gap["detected_scripture_references"] = [
        _scripture_reference_text(reference)
        for reference in analysis.scripture_references
        if _scripture_reference_text(reference)
    ]
    gap["detected_books"] = list(
        dict.fromkeys(
            str(reference.book).strip()
            for reference in analysis.scripture_references
            if str(getattr(reference, "book", "") or "").strip()
        )
    )

    selected_ids = set(_canonical_context_result_ids(canonical_context))
    rejected_results: list[dict[str, Any]] = []
    rejection_reasons: set[str] = set()

    for result in search_response.results:
        obj = library.objects_by_id.get(result.id)
        if obj is None or result.id in selected_ids:
            continue

        reasons: list[str] = []
        retrievable = library._is_retrievable(
            obj,
            approved_only=False,
            exclude_deprecated=True,
            exclude_rejected=True,
            include_placeholders=include_placeholders,
            allowed_statuses=allowed_statuses,
        )
        if not retrievable:
            if not include_placeholders and str(getattr(obj, "content_status", "") or "") == "placeholder":
                reasons.append("placeholder_content")
            if allowed_statuses and str(getattr(obj, "review_status", "") or "") not in allowed_statuses:
                reasons.append("disallowed_review_status")
            if str(getattr(obj, "content_status", "") or "") == "deprecated":
                reasons.append("deprecated_content")
            if str(getattr(obj, "review_status", "") or "") == "rejected":
                reasons.append("rejected_review_status")
            if not reasons:
                reasons.append("governance_filtered")
        elif float(result.score or 0) < float(minimum_relevance_score) and _search_result_match_type(result) not in {"exact", "scripture"}:
            reasons.append("below_relevance_threshold")

        if not reasons:
            continue

        rejection_reasons.update(reasons)
        rejected_results.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "score": result.score,
                    "match_type": _search_result_match_type(result),
                    "matched_fields": list(result.matched_fields),
                    "matched_terms": list(result.matched_terms),
                    "review_status": result.review_status,
                "content_status": result.content_status,
                "confidence": result.confidence,
                "rejection_reasons": reasons,
            }
        )
        if len(rejected_results) >= 5:
            break

    if not search_response.results:
        rejection_reasons.add("no_relevant_ckl_results")
    elif not rejection_reasons:
        rejection_reasons.add("below_relevance_threshold")

    gap["top_rejected_results"] = rejected_results
    gap["rejection_reasons"] = sorted(rejection_reasons)
    return gap


def _fallback_reason_from_rejection_reasons(rejection_reasons: Any) -> str:
    reasons = {str(reason or "").strip() for reason in (rejection_reasons or [])}
    for candidate in (
        "placeholder_content",
        "disallowed_review_status",
        "deprecated_content",
        "rejected_review_status",
        "filtered_out",
        "governance_filtered",
        "below_relevance_threshold",
        "no_relevant_ckl_results",
    ):
        if candidate in reasons:
            return candidate
    return "no_relevant_ckl_results"


STRICT_CKL_NO_MATCH_PROMPT = (
    "The Canonical Knowledge Library did not find a strong match for this question. "
    "Answer generally without inventing CKL facts, and state briefly if the library does not yet cover the topic."
)

class BHFAgent:
    def __init__(
        self,
        config: AgentConfig,
        adapter: Optional[ChatAdapter] = None,
        profile_loader: Optional[ProfileLoader] = None,
        canonical_library: Optional[CanonicalLibrary] = None,
        public_answer_cache: Optional[PublicAnswerCache] = None,
        runtime_cache: Optional[CKLRuntimeCache] = None,
    ) -> None:
        config.validate()
        self.config = config
        self.profile_loader = profile_loader or ProfileLoader()
        self.adapter = adapter or self._build_adapter(config)
        self.framework_version = load_framework_version()
        self.framework_version_fingerprint = load_framework_version_fingerprint(
            self.framework_version
        )
        if canonical_library is not None:
            self.canonical_library = canonical_library
        elif self.config.canonical_library.enabled or self.config.canonical_library.shadow_mode:
            self.canonical_library = load_canonical_library(config=self.config.canonical_library)
        else:
            self.canonical_library = None
        if public_answer_cache is not None:
            self.public_answer_cache = public_answer_cache
        elif self.config.public_cache.enabled:
            self.public_answer_cache = JsonPublicAnswerCache(
                self.config.public_cache.path,
                minimum_quality_score=self.config.public_cache.minimum_quality_score,
                allowed_review_statuses=self.config.public_cache.allowed_review_statuses,
                default_ttl_days=self.config.public_cache.default_ttl_days,
            )
        else:
            self.public_answer_cache = NullPublicAnswerCache()
        if runtime_cache is not None:
            self.runtime_cache = runtime_cache
        else:
            self.runtime_cache = CKLRuntimeCache(
                enabled=self.config.canonical_library.cache_enabled,
                max_entries=self.config.canonical_library.cache_max_entries,
            )
        self._status_callback: Optional[StatusCallback] = None
        self._status_run_started_at: float | None = None
        self._status_stage_started_at: float | None = None
        self._status_current_stage: str | None = None

    def _canonical_library_rollout_mode(self) -> str:
        if self.canonical_library is None:
            return "disabled"
        if self.config.canonical_library.shadow_mode and not self.config.canonical_library.enabled:
            return "shadow"
        return "enabled"

    def ask(
        self,
        question: str,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResult:
        previous_callback = self._status_callback
        previous_run_started_at = self._status_run_started_at
        previous_stage_started_at = self._status_stage_started_at
        previous_current_stage = self._status_current_stage
        self._status_callback = status_callback
        self._status_run_started_at = time.monotonic()
        self._status_stage_started_at = self._status_run_started_at
        self._status_current_stage = None
        ctx: PipelineContext | None = None
        result: AgentResult | None = None
        request_error: Exception | None = None
        try:
            self._emit_status("queued", status="running")
            ctx = self._initialize_context(question)
            ctx = self._detect_reference(ctx)
            ctx = self._classify_genre(ctx)
            ctx = self._classify_question_type(ctx)
            ctx = self._load_profile(ctx)
            ctx = self._lookup_local_knowledge(ctx)
            ctx = self._lookup_public_answer_cache(ctx)
            response_contract = self._response_contract(ctx.original_question)
            if ctx.raw_model_response is None:
                ctx = self._load_session_memory(ctx)
                ctx = self._lookup_response_cache(ctx)
            if ctx.raw_model_response is None:
                ctx = self._build_prompts(ctx)
                ctx = self._call_model(ctx)
                if self._should_use_deterministic_fallback_after_model_call(ctx, response_contract):
                    ctx = self._apply_deterministic_fallback(
                        ctx,
                        response_contract=response_contract,
                        reason="model backend was unavailable or returned no usable text",
                    )
                else:
                    ctx = self._clean_output(ctx)
                    if response_contract == ANSWER_CONTRACT:
                        ctx = self._validate_response(ctx)
                        ctx = self._repair_response(ctx)
                        if self._should_use_deterministic_fallback_after_validation(ctx):
                            ctx = self._apply_deterministic_fallback(
                                ctx,
                                response_contract=response_contract,
                                reason="validated model output was still invalid",
                            )
                    elif response_contract == SEARCH_RESULTS_CONTRACT and not bool(
                        ctx.debug_metadata.get("response_validation_passed", True)
                    ):
                        ctx = self._apply_deterministic_fallback(
                            ctx,
                            response_contract=response_contract,
                            reason="structured search results output was invalid",
                        )
            elif self.config.memory_enabled:
                ctx = self._load_session_memory(ctx)
            ctx = self._finalize_result(ctx)
            ctx = self._store_response_cache(ctx)
            ctx = self._save_session_turn(ctx)
            result = self._to_agent_result(ctx)
            if result.errors:
                self._emit_status(
                    "error",
                    "Model backend error",
                    status="error",
                    details={
                        "failed_stage": "waiting_for_model_response",
                        "errors": list(result.errors),
                    },
                )
                return result
            self._emit_status("complete", "Complete", status="complete")
            return result
        except Exception as exc:
            request_error = exc
            self._emit_status(
                "error",
                "Agent request failed",
                status="error",
                details={
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
            )
            raise
        finally:
            if ctx is not None:
                self._log_request_observability(
                    ctx,
                    result=result,
                    error=request_error,
                )
            self._status_callback = previous_callback
            self._status_run_started_at = previous_run_started_at
            self._status_stage_started_at = previous_stage_started_at
            self._status_current_stage = previous_current_stage

    def _initialize_context(self, question: str) -> PipelineContext:
        response_contract = self._response_contract(question)
        ctx = PipelineContext(
            original_question=question,
            normalized_question=" ".join(question.strip().split()),
            config_profile=self.config.profile,
            answer_mode=self.config.answer_mode,
            debug_metadata={
                "stages_completed": [],
                "adapter_type": self.config.adapter,
                "model": self.config.model,
                "profile": self.config.profile,
                "answer_mode": self.config.answer_mode,
                "framework_version": self.framework_version,
                "framework_version_fingerprint": self.framework_version_fingerprint,
                "request_id": uuid.uuid4().hex,
                "request_started_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "prompt_version": PROMPT_VERSION,
                "response_contract": response_contract,
                "response_format_requested": False,
                "response_format_policy": self.config.response_format_policy,
                "local_knowledge_keys": [],
                "canonical_library_enabled": self.config.canonical_library.enabled,
                "canonical_library_shadow_mode": self.config.canonical_library.shadow_mode,
                "canonical_library_rollout_mode": self._canonical_library_rollout_mode(),
                "canonical_library_loaded": self.canonical_library is not None,
                "canonical_library_object_ids": [],
                "canonical_library_retrieval_method": None,
                "canonical_library_topic_count": 0,
                "canonical_library_prompt_tokens": 0,
                "canonical_library_query": None,
                "canonical_library_include_placeholders": self.config.canonical_library.include_placeholders,
                "canonical_library_allowed_statuses": list(self.config.canonical_library.allowed_statuses),
                "canonical_library_minimum_relevance_score": self.config.canonical_library.minimum_relevance_score,
                "canonical_library_fallback_to_model": self.config.canonical_library.fallback_to_model,
                "canonical_library_strict_mode": self.config.canonical_library.strict_mode,
                "ckl_attempted": False,
                "ckl_result_count": 0,
                "ckl_context_injected": False,
                "ckl_retrieval_usable": False,
                "ckl_relevance_threshold": self.config.canonical_library.minimum_relevance_score,
                "fallback_to_model": False,
                "fallback_reason": None,
                "canonical_library_version_fingerprint": None,
                "canonical_library_strong_match": None,
                "canonical_library_prompt_mode": None,
                "canonical_library_error": None,
                "canonical_library_retrieval_cache_enabled": self.config.canonical_library.cache_enabled,
                "canonical_library_retrieval_cache_hit": False,
                "canonical_library_retrieval_cache_status": "disabled"
                if not self.config.canonical_library.cache_enabled
                else "miss",
                "canonical_library_retrieval_cache_key": None,
                "canonical_library_context_cache_enabled": self.config.canonical_library.cache_enabled,
                "canonical_library_context_cache_hit": False,
                "canonical_library_context_cache_status": "disabled"
                if not self.config.canonical_library.cache_enabled
                else "miss",
                "canonical_library_context_cache_key": None,
                "canonical_library_response_cache_enabled": self.config.canonical_library.cache_enabled,
                "canonical_library_response_cache_hit": False,
                "canonical_library_response_cache_status": "disabled"
                if not self.config.canonical_library.cache_enabled
                else "miss",
                "canonical_library_response_cache_key": None,
                "canonical_library_response_context_hash": None,
                "canonical_library_response_model_signature": None,
                "fallback_used": False,
                "fallback_kind": None,
                "fallback_mode": None,
                "fallback_reason": None,
                "fallback_selected_entry_ids": [],
                "fallback_entry_count": 0,
                "fallback_context_tokens": 0,
                "fallback_truncated": False,
                "fallback_message": None,
                "fallback_original_errors": [],
                "fallback_original_validation_passed": None,
                "fallback_original_validation_errors": [],
                "public_answer_cache_enabled": not isinstance(
                    self.public_answer_cache, NullPublicAnswerCache
                ),
                "public_answer_cache_loaded": not isinstance(
                    self.public_answer_cache, NullPublicAnswerCache
                ),
                "public_answer_cache_hit": False,
                "public_answer_cache_lookup_status": "disabled"
                if isinstance(self.public_answer_cache, NullPublicAnswerCache)
                else "miss",
                "public_answer_cache_key": None,
                "public_answer_cache_question": None,
                "public_answer_cache_answer_mode": self.config.answer_mode,
                "public_answer_cache_quality_score": None,
                "public_answer_cache_usage_count": None,
                "public_answer_cache_review_status": None,
                "public_answer_cache_object_dependency_ids": [],
                "public_answer_cache_framework_version": None,
                "public_answer_cache_framework_version_fingerprint": None,
                "public_answer_cache_ckl_version_fingerprint": None,
                "public_answer_cache_expires_at": None,
                "public_answer_cache_invalidated_at": None,
                "public_answer_cache_invalidated_reason": None,
                "public_answer_cache_error": None,
                "runtime_cache_enabled": self.runtime_cache.enabled,
                "map_tool_keys": [],
                "output_cleanup_applied": False,
                "response_validation_passed": None,
                "response_validation_errors": [],
                "response_validation_warnings": [],
                "response_validation_structured_output": False,
                "response_validation_raw_text_was_json": False,
                "response_validation_removed_headings": [],
                "validation_score": None,
                "auto_repair": self.config.auto_repair,
                "repair_threshold": self.config.repair_threshold,
                "max_repair_attempts": self.config.max_repair_attempts,
                "repair_attempted": False,
                "repair_applied": False,
                "memory_enabled": self.config.memory_enabled,
                "session_id": self.config.session_id or "default",
                "memory_turns_loaded": 0,
                "memory_saved": False,
            },
        )
        return self._mark_stage(ctx, "initialize_context")

    def _detect_reference(self, ctx: PipelineContext) -> PipelineContext:
        ctx.reference_context = detect_reference(ctx.original_question)
        return self._mark_stage(ctx, "detect_reference")

    def _classify_genre(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.reference_context is None:
            raise RuntimeError("reference_context must be set before genre classification")
        ctx.genre_context = classify_genre(ctx.reference_context)
        return self._mark_stage(ctx, "classify_genre")

    def _classify_question_type(self, ctx: PipelineContext) -> PipelineContext:
        ctx.question_context = classify_question_type(
            ctx.original_question,
            ctx.reference_context,
        )
        return self._mark_stage(ctx, "classify_question_type")

    def _load_profile(self, ctx: PipelineContext) -> PipelineContext:
        profile = self.profile_loader.load(self.config.profile)
        ctx.profile_name = profile.name
        ctx.profile_content = profile.content
        ctx.debug_metadata["profile"] = profile.name
        ctx.debug_metadata["prompt_strategy"] = strategy_for_profile(
            profile.name
        ).__class__.__name__
        return self._mark_stage(ctx, "load_profile")

    def _lookup_local_knowledge(self, ctx: PipelineContext) -> PipelineContext:
        if (
            ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
        ):
            raise RuntimeError("pipeline context is incomplete before local knowledge lookup")
        bundle = lookup_local_knowledge(
            ctx.reference_context,
            ctx.genre_context,
            ctx.question_context,
        )
        ctx.local_knowledge = bundle
        ctx.debug_metadata["local_knowledge_keys"] = bundle.keys()
        map_context = build_map_tool_context(
            ctx.original_question,
            reference_context=ctx.reference_context,
            question_context=ctx.question_context,
        )
        if map_context:
            ctx.debug_metadata["map_tool_keys"] = list(map_context.get("requested_tools", []))
            ctx.debug_metadata["map_tool_context"] = map_context
        self._lookup_canonical_library(ctx)
        return self._mark_stage(ctx, "lookup_local_knowledge")

    def _lookup_canonical_library(self, ctx: PipelineContext) -> PipelineContext:
        retrieval_started_at = time.perf_counter()
        rollout_mode = self._canonical_library_rollout_mode()
        strict_ckl_only = bool(
            self.config.canonical_library.strict_mode
            or not self.config.canonical_library.fallback_to_model
        )
        ctx.debug_metadata["canonical_library_rollout_mode"] = rollout_mode
        ctx.debug_metadata["canonical_library_fallback_to_model"] = (
            self.config.canonical_library.fallback_to_model
        )
        ctx.debug_metadata["canonical_library_strict_mode"] = self.config.canonical_library.strict_mode
        ctx.debug_metadata["canonical_library_minimum_relevance_score"] = (
            self.config.canonical_library.minimum_relevance_score
        )
        ctx.debug_metadata["ckl_attempted"] = False
        ctx.debug_metadata["ckl_result_count"] = 0
        ctx.debug_metadata["ckl_context_injected"] = False
        ctx.debug_metadata["ckl_retrieval_usable"] = False
        ctx.debug_metadata["ckl_relevance_threshold"] = self.config.canonical_library.minimum_relevance_score
        ctx.debug_metadata["fallback_to_model"] = False
        ctx.debug_metadata["fallback_reason"] = None
        if self.canonical_library is None:
            ctx.canonical_library_context = None
            ctx.canonical_library_prompt = None
            ctx.canonical_library_query = None
            ctx.debug_metadata["canonical_library_loaded"] = False
            ctx.debug_metadata["canonical_library_object_ids"] = []
            ctx.debug_metadata["canonical_library_retrieval_method"] = None
            ctx.debug_metadata["canonical_library_topic_count"] = 0
            ctx.debug_metadata["canonical_library_prompt_tokens"] = 0
            ctx.debug_metadata["canonical_library_strong_match"] = False
            ctx.debug_metadata["canonical_library_prompt_mode"] = "disabled"
            ctx.debug_metadata["canonical_library_retrieval_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_context_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_retrieval_duration_ms"] = 0
            ctx.debug_metadata["fallback_to_model"] = True
            ctx.debug_metadata["fallback_reason"] = "ckl_disabled"
            return ctx
        if ctx.reference_context is None or ctx.question_context is None:
            raise RuntimeError("pipeline context is incomplete before canonical lookup")

        canonical_query = build_canonical_query(
            ctx.original_question,
            ctx.reference_context,
            ctx.question_context,
        )
        ctx.canonical_library_query = canonical_query
        ctx.debug_metadata["canonical_library_query"] = canonical_query
        ctx.debug_metadata["canonical_library_prompt"] = None
        ctx.debug_metadata["canonical_library_prompt_tokens"] = 0
        ctx.debug_metadata["ckl_attempted"] = True
        ctx.debug_metadata["canonical_library_retrieval_cache_hit"] = False
        ctx.debug_metadata["canonical_library_context_cache_hit"] = False
        ctx.debug_metadata["canonical_library_retrieval_cache_status"] = "miss"
        ctx.debug_metadata["canonical_library_context_cache_status"] = "miss"
        ctx.debug_metadata["canonical_library_context_cache_key"] = None

        inventory_fingerprint: str | None = None
        if self.runtime_cache.enabled and self.config.canonical_library.cache_enabled:
            try:
                inventory_fingerprint = self.canonical_library.inventory_fingerprint()
                ctx.debug_metadata["canonical_library_version_fingerprint"] = inventory_fingerprint
            except Exception as exc:  # noqa: BLE001 - cache should never block answers
                ctx.warnings.append(f"Canonical library retrieval cache skipped: {exc}")
                ctx.debug_metadata["canonical_library_retrieval_cache_status"] = "error"
                ctx.debug_metadata["canonical_library_error"] = str(exc)

        retrieval_cache_key: str | None = None
        if inventory_fingerprint and self.runtime_cache.enabled and self.config.canonical_library.cache_enabled:
            retrieval_cache_key = build_retrieval_cache_key(
                canonical_query=canonical_query,
                inventory_fingerprint=inventory_fingerprint,
                answer_mode=ctx.answer_mode,
                max_results=self.config.canonical_library.max_results,
                include_placeholders=self.config.canonical_library.include_placeholders,
                allowed_statuses=self.config.canonical_library.allowed_statuses,
                max_context_tokens=self.config.canonical_library.max_context_tokens,
            )
            ctx.debug_metadata["canonical_library_retrieval_cache_key"] = retrieval_cache_key
            cached_context = self.runtime_cache.lookup_retrieval(retrieval_cache_key)
            if cached_context is not None:
                canonical_context = cached_context
                ctx.debug_metadata["canonical_library_retrieval_cache_hit"] = True
                ctx.debug_metadata["canonical_library_retrieval_cache_status"] = "hit"
            else:
                canonical_context = None
        else:
            ctx.debug_metadata["canonical_library_retrieval_cache_key"] = retrieval_cache_key
            canonical_context = None

        try:
            if canonical_context is None:
                canonical_context = build_canonical_context(
                    self.canonical_library,
                    ctx.original_question,
                    ctx.reference_context,
                    ctx.question_context,
                    max_results=self.config.canonical_library.max_results,
                    include_placeholders=self.config.canonical_library.include_placeholders,
                    allowed_statuses=self.config.canonical_library.allowed_statuses,
                    answer_mode=ctx.answer_mode,
                    max_context_tokens=self.config.canonical_library.max_context_tokens,
                )
        except Exception as exc:  # noqa: BLE001 - retrieval failure must degrade gracefully
            ctx.canonical_library_context = None
            ctx.canonical_library_prompt = None
            ctx.debug_metadata["canonical_library_loaded"] = True
            ctx.debug_metadata["canonical_library_object_ids"] = []
            ctx.debug_metadata["canonical_library_retrieval_method"] = None
            ctx.debug_metadata["canonical_library_topic_count"] = 0
            ctx.debug_metadata["canonical_library_prompt_tokens"] = 0
            ctx.debug_metadata["canonical_library_strong_match"] = False
            ctx.debug_metadata["canonical_library_prompt_mode"] = (
                "disabled" if rollout_mode == "shadow" else "retrieval_failed"
            )
            if rollout_mode == "shadow":
                ctx.debug_metadata["canonical_library_shadow_prompt_mode"] = "retrieval_failed"
            ctx.debug_metadata["canonical_library_error"] = str(exc)
            ctx.debug_metadata["canonical_library_context_cache_key"] = None
            ctx.debug_metadata["canonical_library_context_cache_hit"] = False
            ctx.debug_metadata["canonical_library_context_cache_status"] = "error"
            ctx.debug_metadata["ckl_result_count"] = 0
            ctx.debug_metadata["ckl_context_injected"] = False
            ctx.debug_metadata["ckl_retrieval_usable"] = False
            ctx.debug_metadata["fallback_to_model"] = True
            ctx.debug_metadata["fallback_reason"] = "retrieval_failed"
            ctx.debug_metadata["ckl_coverage_gap"] = _canonical_miss_reason(
                library=self.canonical_library,
                canonical_query=canonical_query,
                question=ctx.original_question,
                canonical_context=None,
                answer_mode=ctx.answer_mode,
                minimum_relevance_score=self.config.canonical_library.minimum_relevance_score,
                include_placeholders=self.config.canonical_library.include_placeholders,
                allowed_statuses=self.config.canonical_library.allowed_statuses,
                max_results=self.config.canonical_library.max_results,
            )
            ctx.debug_metadata["canonical_library_retrieval_duration_ms"] = int(
                round((time.perf_counter() - retrieval_started_at) * 1000)
            )
            if rollout_mode == "shadow":
                ctx.canonical_library_query = None
            ctx.warnings.append(f"Canonical library retrieval failed: {exc}")
            return ctx

        ctx.canonical_library_context = canonical_context
        if (
            retrieval_cache_key
            and canonical_context is not None
            and not ctx.debug_metadata.get("canonical_library_retrieval_cache_hit")
            and self.runtime_cache.enabled
            and self.config.canonical_library.cache_enabled
        ):
            self.runtime_cache.store_retrieval(retrieval_cache_key, canonical_context)
        ctx.canonical_library_query = (
            str(canonical_context.get("query") or canonical_query).strip()
            if canonical_context is not None
            else canonical_query
        )

        if canonical_context is None:
            ctx.canonical_library_prompt = None
            ctx.debug_metadata["canonical_library_loaded"] = True
            ctx.debug_metadata["canonical_library_object_ids"] = []
            ctx.debug_metadata["canonical_library_retrieval_method"] = None
            ctx.debug_metadata["canonical_library_topic_count"] = 0
            ctx.debug_metadata["canonical_library_prompt_tokens"] = 0
            ctx.debug_metadata["canonical_library_strong_match"] = False
            ctx.debug_metadata["canonical_library_prompt_mode"] = (
                "disabled" if rollout_mode == "shadow" else "fallback_to_model"
            )
            if rollout_mode == "shadow":
                ctx.debug_metadata["canonical_library_shadow_prompt_mode"] = "no_match"
            ctx.debug_metadata["canonical_library_context_cache_key"] = None
            ctx.debug_metadata["canonical_library_context_cache_hit"] = False
            ctx.debug_metadata["canonical_library_context_cache_status"] = "miss"
            ctx.debug_metadata["ckl_result_count"] = 0
            ctx.debug_metadata["ckl_context_injected"] = False
            ctx.debug_metadata["ckl_retrieval_usable"] = False
            ctx.debug_metadata["fallback_to_model"] = True
            coverage_gap = _canonical_miss_reason(
                library=self.canonical_library,
                canonical_query=canonical_query,
                question=ctx.original_question,
                canonical_context=None,
                answer_mode=ctx.answer_mode,
                minimum_relevance_score=self.config.canonical_library.minimum_relevance_score,
                include_placeholders=self.config.canonical_library.include_placeholders,
                allowed_statuses=self.config.canonical_library.allowed_statuses,
                max_results=self.config.canonical_library.max_results,
            )
            ctx.debug_metadata["ckl_coverage_gap"] = coverage_gap
            ctx.debug_metadata["fallback_reason"] = _fallback_reason_from_rejection_reasons(
                coverage_gap.get("rejection_reasons")
            )
            ctx.debug_metadata["canonical_library_response_model_signature"] = build_model_signature(
                adapter=self.config.adapter,
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            ctx.debug_metadata["canonical_library_retrieval_duration_ms"] = int(
                round((time.perf_counter() - retrieval_started_at) * 1000)
            )
            if rollout_mode == "shadow":
                ctx.canonical_library_query = None
            return ctx

        metadata = dict(canonical_context.get("metadata") or {})
        prompt_object_ids, object_ids = _canonical_library_object_ids(metadata, canonical_context)
        strong_match = canonical_context_has_strong_match(
            canonical_context,
            minimum_score=self.config.canonical_library.minimum_relevance_score,
        )
        ctx.debug_metadata["canonical_library_strong_match"] = strong_match
        ctx.debug_metadata["canonical_library_loaded"] = True
        ctx.debug_metadata["canonical_library_prompt_entry_ids"] = prompt_object_ids
        ctx.debug_metadata["canonical_library_retrieved_object_ids"] = object_ids
        ctx.debug_metadata["canonical_library_retrieval_method"] = metadata.get("retrieval_method")
        ctx.debug_metadata["canonical_library_topic_count"] = metadata.get("topic_count", 0)
        ctx.debug_metadata["canonical_library_answer_mode"] = metadata.get("answer_mode")
        ctx.debug_metadata["canonical_library_topic_token_budget"] = metadata.get("topic_token_budget")
        ctx.debug_metadata["canonical_library_query"] = ctx.canonical_library_query

        if rollout_mode == "shadow":
            ctx.debug_metadata["canonical_library_shadow_prompt_mode"] = (
                "summary" if strong_match else "no_strong_match"
            )
            ctx.debug_metadata["canonical_library_prompt_mode"] = "disabled"
            ctx.debug_metadata["canonical_library_context_cache_hit"] = False
            ctx.debug_metadata["canonical_library_context_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_context_cache_key"] = None
            ctx.debug_metadata["canonical_library_prompt_tokens"] = 0
            ctx.canonical_library_prompt = None
            ctx.debug_metadata["canonical_library_object_ids"] = []
            ctx.debug_metadata["ckl_result_count"] = 0
            ctx.debug_metadata["ckl_context_injected"] = False
            ctx.debug_metadata["ckl_retrieval_usable"] = strong_match
            ctx.debug_metadata["fallback_to_model"] = True
            ctx.debug_metadata["fallback_reason"] = "shadow_mode"
            ctx.debug_metadata["canonical_library_response_model_signature"] = build_model_signature(
                adapter=self.config.adapter,
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            ctx.debug_metadata["canonical_library_retrieval_duration_ms"] = int(
                round((time.perf_counter() - retrieval_started_at) * 1000)
            )
            ctx.canonical_library_query = None
            return ctx

        if strong_match:
            prompt_mode = "summary"
        elif strict_ckl_only:
            prompt_mode = "strict_no_match"
        else:
            prompt_mode = "fallback_to_model"

        ctx.debug_metadata["canonical_library_prompt_mode"] = prompt_mode
        ctx.debug_metadata["canonical_library_context_cache_hit"] = False
        ctx.debug_metadata["canonical_library_context_cache_status"] = "miss"
        context_cache_key = build_context_cache_key(
            canonical_query=ctx.canonical_library_query or canonical_query,
            retrieved_topics=list(canonical_context.get("retrieved_topics") or []),
            answer_mode=ctx.answer_mode,
            max_context_tokens=self.config.canonical_library.max_context_tokens,
            prompt_mode=prompt_mode,
            prompt_version=PROMPT_VERSION,
        )
        ctx.debug_metadata["canonical_library_context_cache_key"] = context_cache_key
        if self.runtime_cache.enabled and self.config.canonical_library.cache_enabled:
            cached_prompt = self.runtime_cache.lookup_context(context_cache_key)
            if cached_prompt is not None:
                ctx.canonical_library_prompt = str(cached_prompt.get("prompt") or "")
                ctx.debug_metadata["canonical_library_context_cache_hit"] = True
                ctx.debug_metadata["canonical_library_context_cache_status"] = "hit"
                ctx.debug_metadata["canonical_library_prompt_tokens"] = int(
                    cached_prompt.get("prompt_tokens") or 0
                )
            else:
                ctx.canonical_library_prompt = None
        else:
            ctx.canonical_library_prompt = None

        if ctx.canonical_library_prompt is None:
            if strong_match:
                canonical_prompt = format_canonical_context_for_prompt(
                    canonical_context,
                    max_context_tokens=self.config.canonical_library.max_context_tokens,
                    answer_mode=ctx.answer_mode,
                )
                ctx.canonical_library_prompt = canonical_prompt
            elif strict_ckl_only:
                ctx.canonical_library_prompt = STRICT_CKL_NO_MATCH_PROMPT
            ctx.debug_metadata["canonical_library_prompt_tokens"] = (
                max(1, round(len(ctx.canonical_library_prompt) / 4))
                if ctx.canonical_library_prompt
                else 0
            )
            if context_cache_key and self.runtime_cache.enabled and self.config.canonical_library.cache_enabled:
                self.runtime_cache.store_context(
                    context_cache_key,
                    {
                        "prompt": ctx.canonical_library_prompt,
                        "prompt_tokens": ctx.debug_metadata["canonical_library_prompt_tokens"],
                        "prompt_mode": prompt_mode,
                        "canonical_query": ctx.canonical_library_query,
                        "selected_entry_ids": list(prompt_object_ids),
                        "selected_entry_versions": list(
                            metadata.get("retrieved_object_versions") or []
                        ),
                    },
                )
        if strong_match:
            ctx.debug_metadata["canonical_library_object_ids"] = object_ids
            ctx.debug_metadata["ckl_result_count"] = len(prompt_object_ids)
            ctx.debug_metadata["ckl_context_injected"] = True
            ctx.debug_metadata["ckl_retrieval_usable"] = True
            ctx.debug_metadata["fallback_to_model"] = False
            ctx.debug_metadata["fallback_reason"] = None
        else:
            ctx.debug_metadata["canonical_library_object_ids"] = []
            ctx.debug_metadata["ckl_result_count"] = 0
            ctx.debug_metadata["ckl_context_injected"] = False
            ctx.debug_metadata["ckl_retrieval_usable"] = False
            if strict_ckl_only:
                ctx.debug_metadata["fallback_to_model"] = False
                ctx.debug_metadata["fallback_reason"] = "strict_mode"
                ctx.debug_metadata["ckl_coverage_gap"] = _canonical_miss_reason(
                    library=self.canonical_library,
                    canonical_query=canonical_query,
                    question=ctx.original_question,
                    canonical_context=canonical_context,
                    answer_mode=ctx.answer_mode,
                    minimum_relevance_score=self.config.canonical_library.minimum_relevance_score,
                    include_placeholders=self.config.canonical_library.include_placeholders,
                    allowed_statuses=self.config.canonical_library.allowed_statuses,
                    max_results=self.config.canonical_library.max_results,
                )
            else:
                coverage_gap = _canonical_miss_reason(
                    library=self.canonical_library,
                    canonical_query=canonical_query,
                    question=ctx.original_question,
                    canonical_context=canonical_context,
                    answer_mode=ctx.answer_mode,
                    minimum_relevance_score=self.config.canonical_library.minimum_relevance_score,
                    include_placeholders=self.config.canonical_library.include_placeholders,
                    allowed_statuses=self.config.canonical_library.allowed_statuses,
                    max_results=self.config.canonical_library.max_results,
                )
                ctx.debug_metadata["ckl_coverage_gap"] = coverage_gap
                ctx.debug_metadata["fallback_to_model"] = True
                ctx.debug_metadata["fallback_reason"] = _fallback_reason_from_rejection_reasons(
                    coverage_gap.get("rejection_reasons")
                )
        ctx.debug_metadata["canonical_library_response_model_signature"] = build_model_signature(
            adapter=self.config.adapter,
            base_url=self.config.base_url,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        ctx.debug_metadata["canonical_library_response_cache_status"] = "miss"
        ctx.debug_metadata["canonical_library_retrieval_duration_ms"] = int(
            round((time.perf_counter() - retrieval_started_at) * 1000)
        )
        return ctx

    def _lookup_public_answer_cache(self, ctx: PipelineContext) -> PipelineContext:
        if (
            self.canonical_library is None
            or self.public_answer_cache is None
            or isinstance(self.public_answer_cache, NullPublicAnswerCache)
        ):
            ctx.debug_metadata["public_answer_cache_loaded"] = not isinstance(
                self.public_answer_cache, NullPublicAnswerCache
            )
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "disabled"
            ctx.debug_metadata["public_answer_cache_error"] = (
                "canonical library is unavailable"
                if self.canonical_library is None
                else None
            )
            return ctx

        if ctx.reference_context is None or ctx.question_context is None:
            raise RuntimeError("pipeline context is incomplete before public cache lookup")

        normalized_question = normalize_public_question(ctx.original_question)
        cache_key = public_cache_key(normalized_question, ctx.answer_mode)
        ctx.debug_metadata["public_answer_cache_loaded"] = True
        ctx.debug_metadata["public_answer_cache_key"] = cache_key
        ctx.debug_metadata["public_answer_cache_question"] = normalized_question
        ctx.debug_metadata["public_answer_cache_answer_mode"] = ctx.answer_mode
        ctx.debug_metadata["framework_version"] = self.framework_version
        ctx.debug_metadata["framework_version_fingerprint"] = self.framework_version_fingerprint

        try:
            ckl_version_fingerprint = self.canonical_library.inventory_fingerprint()
        except Exception as exc:  # noqa: BLE001 - public cache should degrade gracefully
            ctx.warnings.append(f"Public answer cache lookup skipped: {exc}")
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "error"
            ctx.debug_metadata["public_answer_cache_error"] = str(exc)
            return ctx

        ctx.debug_metadata["canonical_library_version_fingerprint"] = ckl_version_fingerprint

        try:
            entry = self.public_answer_cache.lookup(
                normalized_question,
                ctx.answer_mode,
                ckl_version_fingerprint=ckl_version_fingerprint,
                framework_version_fingerprint=self.framework_version_fingerprint,
            )
        except Exception as exc:  # noqa: BLE001 - cache must never block answers
            ctx.warnings.append(f"Public answer cache lookup failed: {exc}")
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "error"
            ctx.debug_metadata["public_answer_cache_error"] = str(exc)
            return ctx

        ctx.debug_metadata["public_answer_cache_lookup_status"] = getattr(
            self.public_answer_cache,
            "last_lookup_status",
            "miss" if entry is None else "hit",
        )
        ctx.debug_metadata["public_answer_cache_error"] = getattr(
            self.public_answer_cache,
            "last_lookup_reason",
            None,
        )

        if entry is None:
            ctx.debug_metadata["public_answer_cache_hit"] = False
            return ctx

        usage_count = entry.usage_count
        try:
            self.public_answer_cache.increment_usage(normalized_question, ctx.answer_mode)
            usage_count = entry.usage_count + 1
        except Exception as exc:  # noqa: BLE001 - cache should not block answers
            ctx.warnings.append(f"Public answer cache usage tracking failed: {exc}")
            ctx.debug_metadata["public_answer_cache_error"] = str(exc)

        cached_answer = entry.answer.strip()
        cache_entry_payload = entry.to_dict()
        cache_entry_payload["usage_count"] = usage_count
        ctx.raw_model_response = ChatResponse(
            text=cached_answer,
            model="public-cache",
            provider="public-cache",
            latency_ms=0,
            usage={
                "cached": True,
                "usage_count": usage_count,
            },
            raw_provider_response={
                "cache_key": cache_key,
                "entry": cache_entry_payload,
            },
        )
        ctx.raw_answer_text = cached_answer
        ctx.cleaned_answer_text = cached_answer
        ctx.validation_result = ValidationResult(
            passed=True,
            score=max(0, min(100, int(round(entry.quality_score)))),
            warnings=[],
            suggestions=[],
        )
        ctx.debug_metadata["public_answer_cache_hit"] = True
        ctx.debug_metadata["public_answer_cache_quality_score"] = entry.quality_score
        ctx.debug_metadata["public_answer_cache_usage_count"] = usage_count
        ctx.debug_metadata["public_answer_cache_review_status"] = entry.review_status
        ctx.debug_metadata["public_answer_cache_object_dependency_ids"] = list(
            entry.object_dependency_ids
        )
        ctx.debug_metadata["public_answer_cache_framework_version"] = entry.framework_version
        ctx.debug_metadata["public_answer_cache_framework_version_fingerprint"] = (
            entry.framework_version_fingerprint
        )
        ctx.debug_metadata["public_answer_cache_ckl_version_fingerprint"] = (
            entry.ckl_version_fingerprint
        )
        ctx.debug_metadata["public_answer_cache_expires_at"] = entry.expires_at
        ctx.debug_metadata["public_answer_cache_invalidated_at"] = entry.invalidated_at
        ctx.debug_metadata["public_answer_cache_invalidated_reason"] = (
            entry.invalidated_reason
        )
        ctx.debug_metadata["output_cleanup_applied"] = False
        ctx.debug_metadata["validation_score"] = ctx.validation_result.score
        return ctx

    def _lookup_response_cache(self, ctx: PipelineContext) -> PipelineContext:
        if (
            not self.runtime_cache.enabled
            or not self.config.canonical_library.cache_enabled
            or self.canonical_library is None
        ):
            ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
            return ctx
        if (
            ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
            or ctx.profile_name is None
        ):
            raise RuntimeError("pipeline context is incomplete before response cache lookup")

        prompt_context_hash = build_prompt_context_hash(
            normalized_question=ctx.normalized_question or ctx.original_question,
            canonical_query=ctx.canonical_library_query or ctx.original_question,
            canonical_context_cache_key=str(
                ctx.debug_metadata.get("canonical_library_context_cache_key") or ""
            ),
            reference_context=ctx.reference_context.to_dict(),
            genre_context=ctx.genre_context.to_dict(),
            question_context=ctx.question_context.to_dict(),
            local_knowledge_keys=ctx.debug_metadata.get("local_knowledge_keys", []),
            map_tool_keys=ctx.debug_metadata.get("map_tool_keys", []),
            session_memory=(
                ctx.session_memory.to_dict()
                if isinstance(ctx.session_memory, SessionMemory)
                else None
            ),
            profile_name=ctx.profile_name,
            answer_mode=ctx.answer_mode,
            show_method_notes=self.config.show_method_notes,
            prompt_version=PROMPT_VERSION,
            prompt_mode=str(ctx.debug_metadata.get("canonical_library_prompt_mode") or ""),
        )
        ctx.debug_metadata["canonical_library_response_context_hash"] = prompt_context_hash

        model_signature = dict(
            ctx.debug_metadata.get("canonical_library_response_model_signature")
            or build_model_signature(
                adapter=self.config.adapter,
                base_url=self.config.base_url,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        )
        response_cache_key = build_response_cache_key(
            normalized_question=ctx.normalized_question or ctx.original_question,
            prompt_context_hash=prompt_context_hash,
            model_signature=model_signature,
            response_contract=self._response_contract(ctx.original_question),
            prompt_version=PROMPT_VERSION,
        )
        ctx.debug_metadata["canonical_library_response_cache_key"] = response_cache_key

        cached_response = self.runtime_cache.lookup_response(response_cache_key)
        if cached_response is None:
            ctx.debug_metadata["canonical_library_response_cache_hit"] = False
            ctx.debug_metadata["canonical_library_response_cache_status"] = "miss"
            return ctx

        answer_text = str(cached_response.get("answer_text") or "").strip()
        ctx.raw_model_response = ChatResponse(
            text=answer_text,
            model=self.config.model,
            provider=self.config.adapter,
            latency_ms=0,
            usage={
                "cached": True,
                "cache_layer": "response",
            },
            raw_provider_response={
                "cache_key": response_cache_key,
                "cache_layer": "response",
                "entry": cached_response,
            },
            warnings=list(cached_response.get("warnings") or []),
            errors=[],
        )
        ctx.raw_answer_text = answer_text
        ctx.cleaned_answer_text = answer_text
        ctx.warnings.extend(list(cached_response.get("warnings") or []))
        ctx.validation_result = ValidationResult(
            passed=bool(cached_response.get("validation_passed", True)),
            score=int(cached_response.get("validation_score") or 100),
            warnings=list(cached_response.get("validation_warnings") or []),
            suggestions=list(cached_response.get("validation_suggestions") or []),
        )
        ctx.errors = []
        ctx.debug_metadata["canonical_library_response_cache_hit"] = True
        ctx.debug_metadata["canonical_library_response_cache_status"] = "hit"
        ctx.debug_metadata["output_cleanup_applied"] = bool(
            cached_response.get("cleanup_applied", False)
        )
        ctx.debug_metadata["cleanup_removed_headings"] = list(
            cached_response.get("cleanup_removed_headings") or []
        )
        ctx.debug_metadata["response_validation_passed"] = ctx.validation_result.passed
        ctx.debug_metadata["response_validation_errors"] = []
        ctx.debug_metadata["response_validation_warnings"] = list(
            cached_response.get("validation_warnings") or []
        )
        ctx.debug_metadata["response_validation_structured_output"] = bool(
            cached_response.get("structured_output", False)
        )
        ctx.debug_metadata["response_validation_raw_text_was_json"] = bool(
            cached_response.get("raw_text_was_json", False)
        )
        ctx.debug_metadata["response_validation_removed_headings"] = list(
            cached_response.get("removed_headings") or []
        )
        if cached_response.get("parsed_payload") is not None:
            ctx.debug_metadata["response_validation_parsed_payload"] = cached_response.get(
                "parsed_payload"
            )
        else:
            ctx.debug_metadata.pop("response_validation_parsed_payload", None)
        ctx.debug_metadata["validation_score"] = ctx.validation_result.score
        return ctx

    def _store_response_cache(self, ctx: PipelineContext) -> PipelineContext:
        if (
            not self.runtime_cache.enabled
            or not self.config.canonical_library.cache_enabled
            or self.canonical_library is None
            or ctx.raw_model_response is None
            or ctx.validation_result is None
        ):
            return ctx
        if ctx.debug_metadata.get("fallback_used"):
            return ctx
        if ctx.debug_metadata.get("public_answer_cache_hit"):
            return ctx
        if ctx.debug_metadata.get("canonical_library_response_cache_hit"):
            return ctx
        if ctx.errors:
            return ctx
        response_cache_key = str(
            ctx.debug_metadata.get("canonical_library_response_cache_key") or ""
        ).strip()
        if not response_cache_key:
            return ctx
        payload = {
            "answer_text": ctx.final_answer or ctx.cleaned_answer_text or "",
            "validation_passed": ctx.validation_result.passed,
            "validation_score": ctx.validation_result.score,
            "validation_warnings": list(ctx.validation_result.warnings),
            "validation_suggestions": list(ctx.validation_result.suggestions),
            "warnings": list(ctx.warnings),
            "cleanup_applied": bool(ctx.debug_metadata.get("output_cleanup_applied", False)),
            "cleanup_removed_headings": list(
                ctx.debug_metadata.get("cleanup_removed_headings") or []
            ),
            "structured_output": bool(
                ctx.debug_metadata.get("response_validation_structured_output", False)
            ),
            "raw_text_was_json": bool(
                ctx.debug_metadata.get("response_validation_raw_text_was_json", False)
            ),
            "removed_headings": list(
                ctx.debug_metadata.get("response_validation_removed_headings") or []
            ),
            "parsed_payload": ctx.debug_metadata.get("response_validation_parsed_payload"),
        }
        self.runtime_cache.store_response(response_cache_key, payload)
        ctx.debug_metadata["canonical_library_response_cache_status"] = "stored"
        return ctx

    def _load_session_memory(self, ctx: PipelineContext) -> PipelineContext:
        if not self.config.memory_enabled:
            ctx.session_memory = None
            return self._mark_stage(ctx, "load_session_memory")
        memory, warnings = load_session_memory(
            self.config.memory_path,
            self.config.session_id,
            int(self.config.memory_max_turns),
        )
        ctx.session_memory = memory
        ctx.warnings.extend(warnings)
        ctx.debug_metadata["session_id"] = memory.session_id
        ctx.debug_metadata["memory_turns_loaded"] = len(memory.turns)
        if warnings:
            ctx.debug_metadata["memory_warnings"] = warnings
        return self._mark_stage(ctx, "load_session_memory")

    def _build_prompts(self, ctx: PipelineContext) -> PipelineContext:
        if (
            ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
            or ctx.profile_name is None
            or ctx.profile_content is None
        ):
            raise RuntimeError("pipeline context is incomplete before prompt building")
        map_context = ctx.debug_metadata.get("map_tool_context")
        if not isinstance(map_context, dict) or not map_context:
            map_context = build_map_tool_context(
                ctx.original_question,
                reference_context=ctx.reference_context,
                question_context=ctx.question_context,
            )
        if map_context:
            ctx.debug_metadata["map_tool_keys"] = list(map_context.get("requested_tools", []))
            ctx.debug_metadata["map_tool_context"] = map_context
        ctx.system_prompt, ctx.user_prompt = build_prompt(
            ctx.profile_name,
            ctx.profile_content,
            ctx.reference_context,
            ctx.genre_context,
            ctx.question_context,
            ctx.original_question,
            show_method_notes=self.config.show_method_notes,
            local_knowledge=ctx.local_knowledge,
            map_context=map_context,
            session_memory=ctx.session_memory,
            answer_mode=ctx.answer_mode,
            canonical_context_prompt=ctx.canonical_library_prompt,
        )
        response_format = self._response_format_for_contract(ctx)
        if self._response_contract(ctx.original_question) == ANSWER_CONTRACT:
            ctx.system_prompt = "\n\n".join(
                [
                    ctx.system_prompt,
                    (
                        "# STRUCTURED RESPONSE CONTRACT\n\n"
                        'Return JSON with exactly one top-level key, "answer". '
                        "The answer value must contain the full user-facing answer as markdown prose. "
                        "Do not include analysis, reasoning, debug metadata, retrieval details, or tool calls."
                        if response_format is not None
                        else
                        "# RESPONSE CONTRACT\n\n"
                        "Return the full user-facing answer as Markdown/prose. "
                        "Do not wrap the answer in JSON. Do not include analysis, reasoning, debug metadata, retrieval details, or tool calls."
                    ),
                ]
            )
        return self._mark_stage(ctx, "build_prompts")

    def _response_contract(self, question: str) -> str:
        normalized = " ".join(question.strip().lower().split())
        if "return a json object with a results array" in normalized:
            return SEARCH_RESULTS_CONTRACT
        if "identify likely bible passages" in normalized:
            return SEARCH_RESULTS_CONTRACT
        return ANSWER_CONTRACT

    def _response_format_for_contract(self, ctx: PipelineContext) -> dict[str, Any] | None:
        contract = self._response_contract(ctx.original_question)
        policy = self.config.response_format_policy
        if policy == "off":
            return None
        supports_schema = bool(
            getattr(self.adapter, "supports_json_schema_response_format", lambda: False)()
        )
        if contract == ANSWER_CONTRACT:
            if policy == "json_schema":
                return structured_response_format(prefer_json_schema=True) if supports_schema else None
            if policy == "json_object":
                return structured_response_format()
            if supports_schema:
                return structured_response_format(prefer_json_schema=True)
            if isinstance(self.adapter, OllamaAdapter) or self.config.adapter == "ollama":
                return None
            return structured_response_format()
        if contract == SEARCH_RESULTS_CONTRACT and policy != "json_schema":
            return structured_response_format()
        if contract == SEARCH_RESULTS_CONTRACT and supports_schema:
            return structured_response_format()
        return None

    def _should_use_deterministic_fallback_after_model_call(
        self,
        ctx: PipelineContext,
        response_contract: str,
    ) -> bool:
        del response_contract
        if not bool(ctx.debug_metadata.get("ckl_context_injected")):
            return False
        if ctx.errors:
            return True
        return not bool((ctx.raw_answer_text or "").strip())

    def _should_use_deterministic_fallback_after_validation(
        self,
        ctx: PipelineContext,
    ) -> bool:
        if ctx.validation_result is None:
            return True
        if not bool(ctx.debug_metadata.get("ckl_context_injected")):
            return False
        return not ctx.validation_result.passed

    def _deterministic_fallback_response(
        self,
        ctx: PipelineContext,
        *,
        response_contract: str,
    ) -> dict[str, Any]:
        if response_contract == SEARCH_RESULTS_CONTRACT:
            payload = {
                "results": [],
                "message": (
                    "BHF could not identify likely passage candidates without a working model backend."
                ),
            }
            return {
                "text": json.dumps(payload, ensure_ascii=False),
                "kind": "search_results_empty",
                "message": payload["message"],
                "strong_match": False,
                "selected_entry_ids": [],
                "entry_count": 0,
                "estimated_tokens": 0,
                "truncated": False,
                "parsed_payload": payload,
            }

        fallback = build_canonical_fallback_answer(
            ctx.canonical_library_context,
            max_context_tokens=self.config.canonical_library.max_context_tokens,
            answer_mode=ctx.answer_mode,
            retrieval_failed=bool(ctx.debug_metadata.get("canonical_library_error")),
        )
        fallback["parsed_payload"] = None
        return fallback

    def _apply_deterministic_fallback(
        self,
        ctx: PipelineContext,
        *,
        response_contract: str,
        reason: str,
    ) -> PipelineContext:
        fallback = self._deterministic_fallback_response(
            ctx,
            response_contract=response_contract,
        )
        fallback_text = str(fallback.get("text") or "").strip()
        if not fallback_text:
            fallback_text = (
                "The Canonical Knowledge Library does not currently have enough relevant material "
                "to answer this question."
            )

        original_errors = list(ctx.errors)
        original_validation_errors = list(ctx.debug_metadata.get("response_validation_errors") or [])
        original_validation_warnings = list(
            ctx.debug_metadata.get("response_validation_warnings") or []
        )

        ctx.debug_metadata["fallback_used"] = True
        ctx.debug_metadata["fallback_reason"] = reason
        ctx.debug_metadata["fallback_kind"] = fallback.get("kind")
        if response_contract == SEARCH_RESULTS_CONTRACT:
            ctx.debug_metadata["fallback_mode"] = "search_results_empty"
        elif fallback.get("kind") == "retrieval_failed":
            ctx.debug_metadata["fallback_mode"] = "retrieval_failed"
        elif fallback.get("strong_match"):
            ctx.debug_metadata["fallback_mode"] = "canonical_summary"
        else:
            ctx.debug_metadata["fallback_mode"] = "canonical_limitation"
        ctx.debug_metadata["fallback_message"] = fallback.get("message")
        ctx.debug_metadata["fallback_selected_entry_ids"] = list(
            fallback.get("selected_entry_ids") or []
        )
        ctx.debug_metadata["fallback_entry_count"] = int(fallback.get("entry_count") or 0)
        ctx.debug_metadata["fallback_context_tokens"] = int(
            fallback.get("estimated_tokens") or 0
        )
        ctx.debug_metadata["fallback_truncated"] = bool(fallback.get("truncated", False))
        ctx.debug_metadata["fallback_strong_match"] = bool(fallback.get("strong_match", False))
        ctx.debug_metadata["fallback_original_errors"] = original_errors
        ctx.debug_metadata["fallback_original_validation_passed"] = ctx.debug_metadata.get(
            "response_validation_passed"
        )
        ctx.debug_metadata["fallback_original_validation_errors"] = original_validation_errors
        ctx.debug_metadata["fallback_original_validation_warnings"] = original_validation_warnings
        ctx.debug_metadata["output_cleanup_applied"] = True

        ctx.cleaned_answer_text = fallback_text
        ctx.final_answer = fallback_text
        ctx.errors = []
        ctx.validation_result = ValidationResult(
            passed=True,
            score=100,
            warnings=[],
            suggestions=[],
        )
        ctx.debug_metadata["response_validation_passed"] = True
        ctx.debug_metadata["response_validation_errors"] = []
        ctx.debug_metadata["response_validation_warnings"] = []
        ctx.debug_metadata["response_validation_removed_headings"] = []
        ctx.debug_metadata["validation_score"] = ctx.validation_result.score

        if response_contract == SEARCH_RESULTS_CONTRACT:
            ctx.debug_metadata["response_validation_structured_output"] = True
            ctx.debug_metadata["response_validation_raw_text_was_json"] = True
            ctx.debug_metadata["response_validation_parsed_payload"] = (
                fallback.get("parsed_payload")
                or {
                    "results": [],
                    "message": fallback.get("message"),
                }
            )
        else:
            ctx.debug_metadata["response_validation_structured_output"] = False
            ctx.debug_metadata["response_validation_raw_text_was_json"] = False
            ctx.debug_metadata.pop("response_validation_parsed_payload", None)

        ctx.warnings.append(
            f"Deterministic fallback used after {reason}."
        )
        return ctx

    def _apply_model_response_validation(
        self,
        ctx: PipelineContext,
        *,
        response_text: str,
        raw_provider_response: Any = None,
    ) -> ModelResponseValidationResult:
        response_contract = self._response_contract(ctx.original_question)
        raw_response = ctx.raw_model_response
        diagnostics = {
            "adapter": ctx.debug_metadata.get("adapter_type"),
            "provider": raw_response.provider if raw_response is not None else ctx.debug_metadata.get("provider"),
            "model": raw_response.model if raw_response is not None else ctx.debug_metadata.get("model"),
            "request_id": ctx.debug_metadata.get("request_id"),
            "response_contract": response_contract,
            "structured_output_requested": bool(ctx.debug_metadata.get("response_format_requested")),
            "raw_text_length": len(response_text or ""),
        }
        validation_result = normalize_model_response(
            response_text,
            raw_provider_response=raw_provider_response,
            response_contract=response_contract,
            diagnostics=diagnostics,
        )
        ctx.debug_metadata["output_cleanup_applied"] = bool(
            validation_result.removed_headings
            or validation_result.structured_output
            or validation_result.raw_text_was_json
            or validation_result.sanitized_text.strip() != (response_text or "").strip()
        )
        ctx.debug_metadata["cleanup_removed_headings"] = list(
            validation_result.removed_headings
        )
        ctx.debug_metadata["response_validation_passed"] = validation_result.passed
        ctx.debug_metadata["response_validation_errors"] = list(validation_result.errors)
        ctx.debug_metadata["response_validation_warnings"] = list(validation_result.warnings)
        ctx.debug_metadata["response_validation_structured_output"] = (
            validation_result.structured_output
        )
        ctx.debug_metadata["response_validation_raw_text_was_json"] = (
            validation_result.raw_text_was_json
        )
        ctx.debug_metadata["response_validation_removed_headings"] = list(
            validation_result.removed_headings
        )
        ctx.debug_metadata["response_validation_diagnostics"] = validation_result.diagnostics
        ctx.debug_metadata["response_validation_json_without_answer"] = any(
            "no extractable answer text" in str(error).lower()
            for error in validation_result.errors
        )
        if validation_result.parsed_payload is not None:
            ctx.debug_metadata["response_validation_parsed_payload"] = validation_result.parsed_payload
        else:
            ctx.debug_metadata.pop("response_validation_parsed_payload", None)
        ctx.warnings.extend(validation_result.warnings)
        return validation_result

    def _call_model(self, ctx: PipelineContext) -> PipelineContext:
        self._emit_status(
            "call_model_start",
            "Contacting model backend",
            status="running",
            details={
                "adapter": self.config.adapter,
                "model": self.config.model,
                "timeout_seconds": self.config.timeout_seconds,
            },
        )
        if (
            ctx.system_prompt is None
            or ctx.user_prompt is None
            or ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
        ):
            raise RuntimeError("pipeline context is incomplete before model call")
        model_started_at = time.perf_counter()
        response_format = self._response_format_for_contract(ctx)
        ctx.debug_metadata["response_format_requested"] = response_format is not None
        ctx.debug_metadata["response_format_type"] = (
            response_format.get("type") if response_format is not None else None
        )
        chat_request = ChatRequest(
            system_prompt=ctx.system_prompt,
            user_prompt=ctx.user_prompt,
            model=self.config.model or "",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            context_window=self.config.context_window,
            response_format=response_format,
            metadata={
                "profile": ctx.profile_name,
                "answer_mode": ctx.answer_mode,
                "response_contract": self._response_contract(ctx.original_question),
                "reference_context": ctx.reference_context.to_dict(),
                "genre_context": ctx.genre_context.to_dict(),
                "question_context": ctx.question_context.to_dict(),
                "local_knowledge_keys": ctx.debug_metadata.get(
                    "local_knowledge_keys", []
                ),
                "canonical_library_enabled": ctx.debug_metadata.get("canonical_library_enabled"),
                "canonical_library_loaded": ctx.debug_metadata.get("canonical_library_loaded"),
                "canonical_library_object_ids": ctx.debug_metadata.get(
                    "canonical_library_object_ids", []
                ),
                "canonical_library_retrieval_method": ctx.debug_metadata.get(
                    "canonical_library_retrieval_method"
                ),
                "canonical_library_topic_count": ctx.debug_metadata.get(
                    "canonical_library_topic_count", 0
                ),
                "map_tool_keys": ctx.debug_metadata.get("map_tool_keys", []),
                "memory_enabled": self.config.memory_enabled,
                "session_id": ctx.debug_metadata.get("session_id"),
                "memory_turns_loaded": ctx.debug_metadata.get("memory_turns_loaded", 0),
            },
        )
        self._emit_status(
            "waiting_for_model",
            "Waiting for model response",
            status="running",
        )
        chat_response = self.adapter.chat(chat_request)
        ctx.raw_model_response = chat_response
        ctx.raw_answer_text = chat_response.text
        ctx.warnings.extend(chat_response.warnings)
        ctx.errors.extend(chat_response.errors)
        if chat_response.error_category:
            ctx.debug_metadata["error_category"] = chat_response.error_category
        if chat_response.errors and not bool(ctx.debug_metadata.get("ckl_context_injected")):
            ctx.raw_answer_text = ""
        if chat_response.provider:
            ctx.debug_metadata["provider"] = chat_response.provider
        if chat_response.model:
            ctx.debug_metadata["model"] = chat_response.model
        if chat_response.latency_ms is not None:
            ctx.debug_metadata["model_latency_ms"] = chat_response.latency_ms
        ctx.debug_metadata["model_request_duration_ms"] = int(
            round((time.perf_counter() - model_started_at) * 1000)
        )
        if chat_response.errors:
            return self._mark_stage(
                ctx,
                "call_model",
                event_stage="call_model_complete",
                message="Model backend returned an error",
                details={"errors": list(chat_response.errors)},
            )
        return self._mark_stage(
            ctx,
            "call_model",
            event_stage="call_model_complete",
            message="Model response received",
        )

    def _clean_output(self, ctx: PipelineContext) -> PipelineContext:
        response_validation = self._apply_model_response_validation(
            ctx,
            response_text=ctx.raw_answer_text or "",
            raw_provider_response=(
                ctx.raw_model_response.raw_provider_response
                if ctx.raw_model_response is not None
                else None
            ),
        )
        ctx.cleaned_answer_text = response_validation.sanitized_text
        if self._response_contract(ctx.original_question) == SEARCH_RESULTS_CONTRACT:
            ctx.validation_result = ValidationResult(
                passed=response_validation.passed,
                score=100 if response_validation.passed else 0,
                warnings=list(response_validation.warnings),
                suggestions=[],
            )
        return self._mark_stage(ctx, "clean_output")

    def _validate_response(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.question_context is None:
            raise RuntimeError("question_context must be set before validation")
        ctx.validation_result = validate_response(
            ctx.cleaned_answer_text or "",
            question_context=ctx.question_context,
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
        )
        ctx.debug_metadata["validation_score"] = ctx.validation_result.score
        return self._mark_stage(ctx, "validate_response")

    def _repair_response(self, ctx: PipelineContext) -> PipelineContext:
        if (
            ctx.validation_result is None
            or ctx.question_context is None
            or ctx.reference_context is None
            or ctx.genre_context is None
        ):
            raise RuntimeError("pipeline context is incomplete before repair")

        if (
            bool(ctx.debug_metadata.get("ckl_context_injected"))
            and bool(ctx.debug_metadata.get("response_validation_json_without_answer"))
        ):
            ctx.debug_metadata["repair_skipped_reason"] = (
                "deterministic_fallback_preferred_for_empty_structured_output"
            )
            return self._mark_stage(ctx, "repair_response")

        decision = decide_repair(ctx.validation_result, self.config)
        ctx.repair_decision = decision
        ctx.debug_metadata["repair_decision"] = decision.to_dict()
        ctx.debug_metadata["repair_reason"] = decision.reason
        ctx.debug_metadata["repair_attempted"] = False
        ctx.debug_metadata["repair_applied"] = False

        if not decision.should_repair:
            return self._mark_stage(ctx, "repair_response")

        attempts_allowed = min(int(self.config.max_repair_attempts), 1)
        if attempts_allowed <= 0:
            return self._mark_stage(ctx, "repair_response")

        ctx.original_validation_result = ctx.validation_result
        system_prompt, user_prompt = build_repair_prompt(
            original_question=ctx.original_question,
            question_context=ctx.question_context,
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
            original_answer=ctx.cleaned_answer_text or "",
            validation_result=ctx.validation_result,
            force_json_answer=bool(ctx.debug_metadata.get("response_validation_json_without_answer")),
        )
        chat_request = ChatRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.config.model or "",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            context_window=self.config.context_window,
            metadata={
                "repair": True,
                "profile": ctx.profile_name,
                "answer_mode": ctx.answer_mode,
                "question_context": ctx.question_context.to_dict(),
                "reference_context": ctx.reference_context.to_dict(),
                "genre_context": ctx.genre_context.to_dict(),
                "original_validation_score": ctx.validation_result.score,
                "repair_threshold": self.config.repair_threshold,
            },
        )
        chat_response = self.adapter.chat(chat_request)
        ctx.debug_metadata["repair_attempted"] = True
        ctx.warnings.extend(chat_response.warnings)
        ctx.errors.extend(chat_response.errors)
        if chat_response.error_category:
            ctx.debug_metadata["error_category"] = chat_response.error_category

        response_validation = self._apply_model_response_validation(
            ctx,
            response_text=chat_response.text,
            raw_provider_response=chat_response.raw_provider_response,
        )
        repaired_answer = response_validation.sanitized_text.strip()
        if not repaired_answer:
            attempt = RepairAttempt(
                attempt_number=1,
                repair_prompt=None,
                repaired_answer=repaired_answer,
                validation_result=None,
                accepted=False,
                reason="repair output was empty",
            )
            ctx.repair_attempts.append(attempt)
            ctx.warnings.append("Repair was attempted but returned an empty answer.")
            ctx.debug_metadata["repair_attempts"] = [
                attempt.to_dict() for attempt in ctx.repair_attempts
            ]
            ctx.debug_metadata["repair_response_validation"] = response_validation.to_dict()
            return self._mark_stage(ctx, "repair_response")

        repaired_validation = validate_response(
            repaired_answer,
            question_context=ctx.question_context,
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
        )
        accepted, reason = self._should_accept_repair(
            original=ctx.validation_result,
            repaired=repaired_validation,
        )
        attempt = RepairAttempt(
            attempt_number=1,
            repair_prompt=None,
            repaired_answer=repaired_answer if self.config.debug else None,
            validation_result=repaired_validation,
            accepted=accepted,
            reason=reason,
        )
        ctx.repair_attempts.append(attempt)
        ctx.repaired_answer_text = repaired_answer
        ctx.repaired_validation_result = repaired_validation
        ctx.debug_metadata["repaired_validation_score"] = repaired_validation.score

        if accepted:
            ctx.cleaned_answer_text = repaired_answer
            ctx.validation_result = repaired_validation
            ctx.repair_applied = True
            ctx.debug_metadata["validation_score"] = repaired_validation.score
            ctx.debug_metadata["repair_applied"] = True
        else:
            ctx.warnings.append(f"Repair was attempted but rejected: {reason}.")

        ctx.debug_metadata["repair_attempts"] = [
            attempt.to_dict() for attempt in ctx.repair_attempts
        ]
        ctx.debug_metadata["repair_response_validation"] = response_validation.to_dict()
        return self._mark_stage(ctx, "repair_response")

    def _should_accept_repair(
        self,
        original: ValidationResult,
        repaired: ValidationResult,
    ) -> tuple[bool, str]:
        if repaired.score > original.score:
            return True, "repaired validation score improved"
        if repaired.passed and not original.passed:
            return True, "repaired answer passed validation"
        if (
            repaired.score >= int(self.config.repair_threshold)
            and repaired.score >= original.score
        ):
            return True, "repaired score meets repair threshold"
        return False, "repaired answer did not improve validation"

    def _finalize_result(self, ctx: PipelineContext) -> PipelineContext:
        ctx.final_answer = ctx.cleaned_answer_text or ""
        validation_errors = list(
            ctx.debug_metadata.get("response_validation_errors") or []
        )
        if validation_errors and not ctx.debug_metadata.get("fallback_used"):
            for error in validation_errors:
                controlled_error = f"Invalid model output: {error}"
                if controlled_error not in ctx.errors:
                    ctx.errors.append(controlled_error)
            ctx.debug_metadata["error_category"] = "invalid_model_output"
        if not ctx.final_answer.strip():
            if not validation_errors and not ctx.errors:
                ctx.errors.append("Model response was empty after validation.")
        message = (
            "Finalizing fallback answer"
            if ctx.debug_metadata.get("fallback_used")
            else None
        )
        return self._mark_stage(ctx, "finalize_result", message=message)

    def _save_session_turn(self, ctx: PipelineContext) -> PipelineContext:
        if not self.config.memory_enabled:
            return self._mark_stage(ctx, "save_session_turn")
        if (
            ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
            or ctx.profile_name is None
        ):
            raise RuntimeError("pipeline context is incomplete before saving memory")
        memory = ctx.session_memory
        if not isinstance(memory, SessionMemory):
            memory = SessionMemory(session_id=self.config.session_id or "default")
        append_session_turn(
            memory,
            question=ctx.original_question,
            answer_text=ctx.final_answer or "",
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
            question_context=ctx.question_context,
            profile=ctx.profile_name,
            answer_mode=ctx.answer_mode,
            max_turns=int(self.config.memory_max_turns),
        )
        path = save_session_memory(
            memory,
            self.config.memory_path,
            int(self.config.memory_max_turns),
        )
        ctx.session_memory = memory
        ctx.memory_path = str(path)
        ctx.debug_metadata["memory_saved"] = True
        ctx.debug_metadata["memory_path"] = str(path)
        ctx.debug_metadata["memory_turns_saved"] = len(memory.turns)
        return self._mark_stage(ctx, "save_session_turn")

    def _to_agent_result(self, ctx: PipelineContext) -> AgentResult:
        if (
            ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
            or ctx.profile_name is None
            or ctx.validation_result is None
            or ctx.raw_model_response is None
        ):
            raise RuntimeError("pipeline context is incomplete before result conversion")
        local_knowledge = ctx.local_knowledge
        if not isinstance(local_knowledge, LocalKnowledgeBundle):
            local_knowledge = LocalKnowledgeBundle(lexical_entries=[])
        chat_response = ctx.raw_model_response
        model_metadata: dict[str, Any] = {
            "adapter_type": self.config.adapter,
            "base_url": self.config.base_url,
            "configured_model": self.config.model,
            "provider": chat_response.provider or self.config.adapter,
            "latency_ms": chat_response.latency_ms,
            "framework_version": ctx.debug_metadata.get("framework_version"),
            "framework_version_fingerprint": ctx.debug_metadata.get(
                "framework_version_fingerprint"
            ),
            "answer_mode": ctx.answer_mode,
            "response_contract": ctx.debug_metadata.get("response_contract"),
            "memory_enabled": self.config.memory_enabled,
            "session_id": ctx.debug_metadata.get("session_id"),
            "memory_path": ctx.debug_metadata.get("memory_path"),
            "memory_turns_loaded": ctx.debug_metadata.get("memory_turns_loaded", 0),
            "memory_turns_saved": ctx.debug_metadata.get("memory_turns_saved", 0),
            "model": chat_response.model,
            "usage": chat_response.usage,
            "error_category": ctx.debug_metadata.get("error_category")
            or chat_response.error_category,
            "cleanup_applied": ctx.debug_metadata.get("output_cleanup_applied", False),
            "cleanup_removed_headings": ctx.debug_metadata.get(
                "cleanup_removed_headings", []
            ),
            "response_validation_passed": ctx.debug_metadata.get("response_validation_passed"),
            "response_validation_errors": ctx.debug_metadata.get(
                "response_validation_errors", []
            ),
            "response_validation_warnings": ctx.debug_metadata.get(
                "response_validation_warnings", []
            ),
            "response_validation_structured_output": ctx.debug_metadata.get(
                "response_validation_structured_output", False
            ),
            "response_validation_raw_text_was_json": ctx.debug_metadata.get(
                "response_validation_raw_text_was_json", False
            ),
            "response_validation_removed_headings": ctx.debug_metadata.get(
                "response_validation_removed_headings", []
            ),
            "local_knowledge_keys": ctx.debug_metadata.get("local_knowledge_keys", []),
            "canonical_library_object_ids": ctx.debug_metadata.get(
                "canonical_library_object_ids", []
            ),
            "canonical_library_retrieval_method": ctx.debug_metadata.get(
                "canonical_library_retrieval_method"
            ),
            "canonical_library_topic_count": ctx.debug_metadata.get(
                "canonical_library_topic_count", 0
            ),
            "canonical_library_context": ctx.canonical_library_context,
            "canonical_library_version_fingerprint": ctx.debug_metadata.get(
                "canonical_library_version_fingerprint"
            ),
            "local_knowledge_terms": [
                entry.transliteration for entry in local_knowledge.lexical_entries
            ],
            "repair_applied": ctx.repair_applied,
            "repair_attempted": bool(ctx.repair_attempts),
            "repair_reason": ctx.repair_decision.reason if ctx.repair_decision else None,
            "original_validation_score": (
                ctx.repair_decision.original_score if ctx.repair_decision else None
            ),
            "repaired_validation_score": (
                ctx.repaired_validation_result.score
                if ctx.repaired_validation_result
                else None
            ),
            "public_answer_cache": {
                "enabled": not isinstance(
                    self.public_answer_cache, NullPublicAnswerCache
                ),
                "hit": ctx.debug_metadata.get("public_answer_cache_hit", False),
                "lookup_status": ctx.debug_metadata.get(
                    "public_answer_cache_lookup_status"
                ),
                "key": ctx.debug_metadata.get("public_answer_cache_key"),
                "question": ctx.debug_metadata.get("public_answer_cache_question"),
                "answer_mode": ctx.debug_metadata.get(
                    "public_answer_cache_answer_mode"
                ),
                "quality_score": ctx.debug_metadata.get(
                    "public_answer_cache_quality_score"
                ),
                "usage_count": ctx.debug_metadata.get(
                    "public_answer_cache_usage_count"
                ),
                "review_status": ctx.debug_metadata.get(
                    "public_answer_cache_review_status"
                ),
                "object_dependency_ids": ctx.debug_metadata.get(
                    "public_answer_cache_object_dependency_ids", []
                ),
                "framework_version": ctx.debug_metadata.get(
                    "public_answer_cache_framework_version"
                ),
                "framework_version_fingerprint": ctx.debug_metadata.get(
                    "public_answer_cache_framework_version_fingerprint"
                ),
                "ckl_version_fingerprint": ctx.debug_metadata.get(
                    "public_answer_cache_ckl_version_fingerprint"
                ),
                "expires_at": ctx.debug_metadata.get(
                    "public_answer_cache_expires_at"
                ),
                "invalidated_at": ctx.debug_metadata.get(
                    "public_answer_cache_invalidated_at"
                ),
                "invalidated_reason": ctx.debug_metadata.get(
                    "public_answer_cache_invalidated_reason"
                ),
                "error": ctx.debug_metadata.get("public_answer_cache_error"),
            },
            "pipeline": dict(ctx.debug_metadata),
        }
        if self.config.debug:
            model_metadata["raw_model_text"] = chat_response.text
            model_metadata["raw_provider_response"] = chat_response.raw_provider_response

        return AgentResult(
            answer_text=ctx.final_answer or "",
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
            question_context=ctx.question_context,
            profile_used=ctx.profile_name,
            validation_result=ctx.validation_result,
            model_metadata=model_metadata,
            warnings=ctx.warnings,
            errors=ctx.errors,
            repair_applied=ctx.repair_applied,
            repair_attempted=bool(ctx.repair_attempts),
            repair_reason=ctx.repair_decision.reason if ctx.repair_decision else None,
            original_validation_result=ctx.original_validation_result,
            repaired_validation_result=ctx.repaired_validation_result,
        )

    def _log_request_observability(
        self,
        ctx: PipelineContext,
        *,
        result: AgentResult | None,
        error: Exception | None,
    ) -> None:
        if not self.config.observability.enabled:
            return

        try:
            request_id = str(ctx.debug_metadata.get("request_id") or "").strip() or uuid.uuid4().hex
            request_duration_ms = _safe_int(
                int(round((time.monotonic() - self._status_run_started_at) * 1000))
                if self._status_run_started_at is not None
                else None
            )
            raw_response = ctx.raw_model_response
            usage_summary = summarize_usage(raw_response.usage if raw_response is not None else None)
            if usage_summary["cached"] and usage_summary["input_tokens"] is None:
                usage_summary["input_tokens"] = 0
            if usage_summary["cached"] and usage_summary["output_tokens"] is None:
                usage_summary["output_tokens"] = 0
            if usage_summary["cached"] and usage_summary["total_tokens"] is None:
                usage_summary["total_tokens"] = 0
            if usage_summary["cached"] and usage_summary["estimated_cost"] is None:
                usage_summary["estimated_cost"] = 0.0

            model_provider = (
                raw_response.provider
                or ctx.debug_metadata.get("provider")
                or self.config.adapter
            )
            model_name = raw_response.model or ctx.debug_metadata.get("model") or self.config.model
            model_latency_ms = raw_response.latency_ms
            if model_latency_ms is None:
                model_latency_ms = _safe_int(ctx.debug_metadata.get("model_latency_ms"))
            if model_latency_ms is None:
                model_latency_ms = _safe_int(
                    ctx.debug_metadata.get("model_request_duration_ms")
                )

            cache_summary = {
                "public_answer": {
                    "hit": bool(ctx.debug_metadata.get("public_answer_cache_hit", False)),
                    "status": ctx.debug_metadata.get("public_answer_cache_lookup_status"),
                },
                "retrieval": {
                    "hit": bool(
                        ctx.debug_metadata.get("canonical_library_retrieval_cache_hit", False)
                    ),
                    "status": ctx.debug_metadata.get("canonical_library_retrieval_cache_status"),
                },
                "context": {
                    "hit": bool(
                        ctx.debug_metadata.get("canonical_library_context_cache_hit", False)
                    ),
                    "status": ctx.debug_metadata.get("canonical_library_context_cache_status"),
                },
                "response": {
                    "hit": bool(
                        ctx.debug_metadata.get("canonical_library_response_cache_hit", False)
                    ),
                    "status": ctx.debug_metadata.get("canonical_library_response_cache_status"),
                },
            }
            cache_hit = any(layer["hit"] for layer in cache_summary.values())
            cache_layer = None
            if cache_summary["public_answer"]["hit"]:
                cache_layer = "public_answer"
            elif cache_summary["response"]["hit"]:
                cache_layer = "response"
            request_failed = error is not None or bool(result.errors if result is not None else [])

            record: dict[str, Any] = {
                "request_id": request_id,
                "status": "error" if request_failed else "success",
                "normalized_query": ctx.normalized_question or ctx.original_question,
                "retrieval_duration_ms": _safe_int(
                    ctx.debug_metadata.get("canonical_library_retrieval_duration_ms")
                ),
                "retrieval_result_count": _safe_int(
                    ctx.debug_metadata.get("canonical_library_topic_count")
                )
                or 0,
                "selected_entry_ids": list(
                    ctx.debug_metadata.get("canonical_library_object_ids") or []
                ),
                "rollout_mode": ctx.debug_metadata.get("canonical_library_rollout_mode"),
                "ckl": {
                    "attempted": bool(ctx.debug_metadata.get("ckl_attempted", False)),
                    "result_count": _safe_int(ctx.debug_metadata.get("ckl_result_count")) or 0,
                    "context_injected": bool(
                        ctx.debug_metadata.get("ckl_context_injected", False)
                    ),
                    "fallback_to_model": bool(
                        ctx.debug_metadata.get("fallback_to_model", False)
                    ),
                    "fallback_reason": ctx.debug_metadata.get("fallback_reason"),
                    "relevance_threshold": ctx.debug_metadata.get(
                        "ckl_relevance_threshold"
                    ),
                },
                "context_token_count": _safe_int(
                    ctx.debug_metadata.get("canonical_library_prompt_tokens")
                )
                or 0,
                "model_provider": model_provider,
                "model_name": model_name,
                "model_latency_ms": model_latency_ms,
                "input_tokens": usage_summary["input_tokens"],
                "output_tokens": usage_summary["output_tokens"],
                "estimated_cost": usage_summary["estimated_cost"],
                "cache_hit": cache_hit,
                "cache_layer": cache_layer,
                "cache": cache_summary,
                "fallback_used": bool(ctx.debug_metadata.get("fallback_used", False)),
                "fallback_mode": ctx.debug_metadata.get("fallback_mode"),
                "validation_passed": ctx.validation_result.passed if ctx.validation_result else None,
                "validation_score": ctx.validation_result.score if ctx.validation_result else None,
                "request_duration_ms": request_duration_ms,
            }

            if error is not None:
                record["error_type"] = error.__class__.__name__
            elif request_failed:
                record["error_type"] = "model_backend_error"

            if self.config.observability.redact_sensitive:
                record["redacted"] = True
            else:
                record["redacted"] = False
                record["prompt_version"] = ctx.debug_metadata.get("prompt_version")
                record["adapter_type"] = ctx.debug_metadata.get("adapter_type")
                record["answer_mode"] = ctx.answer_mode
                record["profile"] = ctx.profile_name
                record["response_contract"] = ctx.debug_metadata.get("response_contract")
                record["rollout_mode"] = ctx.debug_metadata.get(
                    "canonical_library_rollout_mode"
                )
                record["prompt_mode"] = ctx.debug_metadata.get(
                    "canonical_library_prompt_mode"
                )
                record["shadow_prompt_mode"] = ctx.debug_metadata.get(
                    "canonical_library_shadow_prompt_mode"
                )
                record["stages_completed"] = list(
                    ctx.debug_metadata.get("stages_completed") or []
                )
                record["validation_warnings_count"] = len(
                    ctx.debug_metadata.get("response_validation_warnings") or []
                )

            OBSERVABILITY_LOGGER.info(render_log_record(record))

            if self.config.debug and self.config.observability.verbose:
                verbose_record = {
                    "request_id": request_id,
                    "status": "error" if request_failed else "success",
                    "cache": cache_summary,
                    "fallback": {
                        "used": bool(ctx.debug_metadata.get("fallback_used", False)),
                        "mode": ctx.debug_metadata.get("fallback_mode"),
                        "kind": ctx.debug_metadata.get("fallback_kind"),
                    },
                    "pipeline": {
                        "stages_completed": list(
                            ctx.debug_metadata.get("stages_completed") or []
                        ),
                        "canonical_library_prompt_mode": ctx.debug_metadata.get(
                            "canonical_library_prompt_mode"
                        ),
                        "canonical_library_shadow_prompt_mode": ctx.debug_metadata.get(
                            "canonical_library_shadow_prompt_mode"
                        ),
                        "canonical_library_rollout_mode": ctx.debug_metadata.get(
                            "canonical_library_rollout_mode"
                        ),
                        "canonical_library_retrieval_cache_key": ctx.debug_metadata.get(
                            "canonical_library_retrieval_cache_key"
                        ),
                        "canonical_library_context_cache_key": ctx.debug_metadata.get(
                            "canonical_library_context_cache_key"
                        ),
                        "canonical_library_response_cache_key": ctx.debug_metadata.get(
                            "canonical_library_response_cache_key"
                        ),
                        "response_validation_passed": ctx.debug_metadata.get(
                            "response_validation_passed"
                        ),
                        "response_validation_removed_headings": list(
                            ctx.debug_metadata.get("response_validation_removed_headings")
                            or []
                        ),
                    },
                }
                if not self.config.observability.redact_sensitive:
                    verbose_record["pipeline"]["canonical_library_query"] = ctx.debug_metadata.get(
                        "canonical_library_query"
                    )
                    verbose_record["pipeline"]["session_id"] = ctx.debug_metadata.get(
                        "session_id"
                    )
                    verbose_record["pipeline"]["map_tool_keys"] = list(
                        ctx.debug_metadata.get("map_tool_keys") or []
                    )
                OBSERVABILITY_LOGGER.debug(render_log_record(verbose_record))
        except Exception as exc:  # noqa: BLE001 - observability must never break the request path
            OBSERVABILITY_LOGGER.exception("Failed to emit request observability: %s", exc)

    def _mark_stage(
        self,
        ctx: PipelineContext,
        stage: str,
        event_stage: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> PipelineContext:
        stages = ctx.debug_metadata.setdefault("stages_completed", [])
        if isinstance(stages, list):
            stages.append(stage)
        self._emit_status(event_stage or stage, message, details=details)
        return ctx

    def _emit_status(
        self,
        stage: str,
        message: str | None = None,
        status: str = "complete",
        details: dict[str, Any] | None = None,
    ) -> None:
        if self._status_callback is None:
            return
        now = time.monotonic()
        canonical_stage = STAGE_TO_STEP.get(stage, stage)
        step_index = STEP_INDEX.get(canonical_stage, TOTAL_STEPS)
        run_started_at = self._status_run_started_at or now
        stage_started_at = self._status_stage_started_at or now
        if canonical_stage != self._status_current_stage:
            if status == "running":
                elapsed_current_stage_seconds = 0.0
            else:
                elapsed_current_stage_seconds = now - stage_started_at
            self._status_current_stage = canonical_stage
            self._status_stage_started_at = now
        else:
            elapsed_current_stage_seconds = now - stage_started_at
        event: dict[str, Any] = {
            "stage": canonical_stage,
            "message": message
            or STEP_MESSAGES.get(canonical_stage, canonical_stage.replace("_", " ")),
            "step_index": step_index,
            "total_steps": TOTAL_STEPS,
            "percent_complete": round((step_index / TOTAL_STEPS) * 100, 1),
            "timestamp": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "elapsed_total_seconds": round(now - run_started_at, 3),
            "elapsed_current_stage_seconds": round(elapsed_current_stage_seconds, 3),
            "status": status,
        }
        if details:
            event["details"] = details
        self._status_callback(event)

    def _build_adapter(self, config: AgentConfig) -> ChatAdapter:
        if config.adapter == "openai_compatible":
            if not config.base_url:
                raise ConfigError("base_url is required for openai_compatible adapter")
            return OpenAICompatibleAdapter(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout_seconds=config.timeout_seconds,
            )
        if config.adapter == "ollama":
            if not config.base_url:
                raise ConfigError("base_url is required for ollama adapter")
            return OllamaAdapter(
                base_url=config.base_url,
                timeout_seconds=config.timeout_seconds,
            )
        raise ConfigError(f"unsupported adapter: {config.adapter}")
