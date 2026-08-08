"""Reusable BHF agent runner."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

from .adapters import ChatAdapter, OllamaAdapter, OpenAICompatibleAdapter
from .adapters import OpenRouterAdapter
from .adapters.openrouter import OPENROUTER_BASE_URL
from .bible import BibleError, build_interpretation_context
from .ckl import (
    CULTURAL_CONTEXT_MAX_OUTPUT_TOKENS,
    CULTURAL_CONTEXT_MAX_TOKENS,
    build_canonical_context,
    build_canonical_query,
    canonical_context_has_strong_match,
    format_canonical_context_for_prompt,
    load_canonical_library,
)
from .config import AgentConfig, ConfigError
from .coverage import (
    AnswerCoverageAssessment,
    BROAD_KNOWLEDGE_EXPANSION,
    CKL_PRIMARY,
    evaluate_answer_coverage,
    format_coverage_prompt,
)
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
    FinalAnswer,
    PipelineContext,
    RepairAttempt,
    RetrievedEvidence,
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
from .prompts import PROMPT_VERSION, build_prompt_result
from .research import (
    NullResearchProvider,
    ResearchProvider,
    ResearchResult,
    format_research_result_for_prompt,
    normalize_research_result,
)
from .question_types import classify_question_type
from .repair import build_repair_prompt, decide_repair
from .references import detect_reference
from .runner_state import PIPELINE_STEPS, STEP_INDEX, STEP_MESSAGES, STAGE_TO_STEP, TOTAL_STEPS
from .study_actions import format_fact_packet_for_prompt
from .token_estimation import estimate_tokens
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
from framework.lexical import LexicalLookupService
from framework.lexical.service import format_lexical_unavailable_context
from framework.commentary.evidence import (
    TyndaleEvidenceProvider,
    format_tyndale_result_for_prompt,
)


StatusCallback = Callable[[dict[str, Any]], None]
OBSERVABILITY_LOGGER = logging.getLogger("bhf_agent.observability")
STRONGS_QUERY_RE = re.compile(r"\b[HG]\s*0*\d{1,5}[A-Za-z]?\b", re.IGNORECASE)
NON_ANSWER_RE = re.compile(
    r"(?i)^\s*(?:the answer is not valid|still not valid|unable to answer)\.?\s*$"
)


def _failed_stage_for_category(category: str | None) -> str:
    return {
        "provider_timeout": "waiting_for_model_response",
        "provider_connection": "connecting_to_model_backend",
        "provider_failure": "waiting_for_model_response",
        "response_extraction": "extracting_model_response",
        "response_normalization": "normalizing_model_response",
        "response_validation": "validating_model_response",
        "response_repair": "repairing_model_response",
        "unexpected_internal_error": "building_final_answer",
    }.get(str(category or "").strip().lower(), "waiting_for_model_response")


def _infer_error_category(errors: list[str]) -> str:
    text = " ".join(str(error) for error in errors).lower()
    if "timed out" in text or "timeout" in text:
        return "provider_timeout"
    if "could not connect" in text or "connection refused" in text:
        return "provider_connection"
    if "http " in text or "endpoint request failed" in text:
        return "provider_failure"
    return "provider_failure"


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
        lexical_engine: Optional[LexicalLookupService] = None,
        research_provider: Optional[ResearchProvider] = None,
        tyndale_provider: Optional[TyndaleEvidenceProvider] = None,
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
        self.lexical_engine = lexical_engine or LexicalLookupService(
            self.config.lexicon.runtime_database_path
        )
        self.research_provider = research_provider or NullResearchProvider()
        self.tyndale_provider = tyndale_provider or TyndaleEvidenceProvider(
            self.config.commentary.database_path,
            max_entries=self.config.commentary.max_entries,
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
        canonical_fact_packet: dict[str, Any] | None = None,
        transient_translation_lookup: bool = False,
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
            ctx.debug_metadata["transient_translation_lookup"] = bool(
                transient_translation_lookup
            )
            if canonical_fact_packet:
                ctx.debug_metadata["deterministic_fact_packet"] = canonical_fact_packet
            ctx = self._detect_reference(ctx)
            ctx = self._retrieve_scripture_context(ctx)
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
                if self._should_fail_synthesis_after_model_call(ctx, response_contract):
                    ctx = self._mark_synthesis_failure(
                        ctx,
                        reason="model backend was unavailable or returned no usable text",
                    )
                else:
                    ctx = self._clean_output(ctx)
                    if response_contract == ANSWER_CONTRACT:
                        ctx = self._validate_response(ctx)
                        ctx = self._repair_response(ctx)
                        if self._should_fail_synthesis_after_validation(ctx):
                            ctx = self._mark_synthesis_failure(
                                ctx,
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
            if result.fatal_errors:
                failed_stage = result.failed_stage or "waiting_for_model_response"
                self._emit_status(
                    "error",
                    "BHF request failed",
                    status="error",
                    details={
                        "failed_stage": failed_stage,
                        "error_category": result.error_category,
                        "errors": list(result.fatal_errors),
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
            answer_mode="unified",
            debug_metadata={
                "stages_completed": [],
                "adapter_type": self.config.adapter,
                "model": self.config.model,
                "profile": self.config.profile,
                "runtime_profile_mode": "unified",
                "legacy_runtime_profile_mode": self.config.runtime_profile_mode,
                "full_profile_injected": False,
                "answer_mode": "unified",
                "legacy_answer_mode": self.config.answer_mode,
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
                "scripture_context_required": False,
                "scripture_context_retrieval_status": "not_started",
                "scripture_context_translation": None,
                "scripture_context_chapter": None,
                "scripture_context_focal_reference": None,
                "scripture_context_scope": None,
                "scripture_context_chapter_verse_count": 0,
                "scripture_context_prompt_tokens": 0,
                "local_knowledge_keys": [],
                "lexical_engine_enabled": self.config.lexicon.enabled,
                "lexical_engine_lookup_attempted": False,
                "lexical_engine_entry_count": 0,
                "lexical_engine_prompt_tokens": 0,
                "lexical_engine_error": None,
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
                "knowledge_expansion_enabled": self.config.knowledge_expansion.enabled,
                "knowledge_expansion_sufficient_threshold": self.config.knowledge_expansion.sufficient_coverage_threshold,
                "knowledge_expansion_major_gap_threshold": self.config.knowledge_expansion.major_gap_threshold,
                "knowledge_expansion_research_override_enabled": self.config.knowledge_expansion.research_override_enabled,
                "knowledge_expansion_allow_model_knowledge": self.config.knowledge_expansion.allow_model_knowledge_expansion,
                "knowledge_expansion_allow_external_retrieval": self.config.knowledge_expansion.allow_external_retrieval,
                "knowledge_expansion_max_gap_items": self.config.knowledge_expansion.max_gap_items,
                "answer_coverage_score": None,
                "answer_coverage_mode": None,
                "answer_coverage_sufficient": None,
                "answer_coverage_evaluator": None,
                "answer_coverage_rationale": None,
                "answer_coverage_covered_dimensions": [],
                "answer_coverage_missing_dimensions": [],
                "research_override_detected": False,
                "knowledge_expansion_requested": False,
                "knowledge_expansion_performed": False,
                "knowledge_expansion_source": "none",
                "knowledge_expansion_blocked": False,
                "knowledge_expansion_blocked_reason": None,
                "external_research_enabled": self.config.knowledge_expansion.allow_external_retrieval,
                "external_research_available": False,
                "external_research_attempted": False,
                "external_research_succeeded": False,
                "external_research_result_count": 0,
                "external_research_error": None,
                "external_research_provider": self._research_provider_identity(),
                "tyndale_enabled": self.config.commentary.enabled,
                "tyndale_database_path": self.config.commentary.database_path,
                "tyndale_available": False,
                "tyndale_eligible": False,
                "tyndale_retrieval_attempted": False,
                "tyndale_retrieval_succeeded": False,
                "tyndale_retrieval_reason": None,
                "tyndale_result_count": 0,
                "tyndale_source_id": None,
                "tyndale_source_sha256": None,
                "tyndale_error": None,
                "tyndale_prompt_tokens": 0,
                "answer_coverage_before_tyndale": None,
                "answer_coverage_after_tyndale": None,
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
                "public_answer_cache_answer_mode": "unified",
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
                "prompt_token_estimates": {},
                "prompt_character_counts": {},
                "prompt_token_estimator": "approximate: round(character_count / 4)",
            },
        )
        return self._mark_stage(ctx, "initialize_context")

    def _detect_reference(self, ctx: PipelineContext) -> PipelineContext:
        ctx.reference_context = detect_reference(ctx.original_question)
        return self._mark_stage(ctx, "detect_reference")

    def _retrieve_scripture_context(self, ctx: PipelineContext) -> PipelineContext:
        """Retrieve mandatory chapter-first context before any interpretation."""

        reference = ctx.reference_context
        if reference is None:
            raise RuntimeError("reference_context must be set before Scripture retrieval")
        ctx.debug_metadata["scripture_context_required"] = bool(
            reference.is_reference_based
        )
        if not reference.is_reference_based:
            ctx.scripture_context = None
            ctx.debug_metadata["scripture_context_retrieval_status"] = "not_required"
            return self._mark_stage(ctx, "retrieve_scripture_context")
        if not reference.book or reference.chapter is None:
            raise BibleError("A biblical book and chapter are required for Scripture retrieval")
        try:
            context = build_interpretation_context(
                reference.book,
                reference.chapter,
                reference.verse,
                reference.verse_end,
            )
        except BibleError:
            ctx.debug_metadata["scripture_context_retrieval_status"] = "failed"
            raise
        ctx.scripture_context = context
        ctx.debug_metadata.update(
            {
                "scripture_context_retrieval_status": "complete",
                "scripture_context_translation": context["translation"].get("id"),
                "scripture_context_chapter": context["chapter_reference"],
                "scripture_context_focal_reference": context["focal_reference"],
                "scripture_context_scope": context["context_scope"],
                "scripture_context_chapter_verse_count": context["chapter_verse_count"],
                "scripture_context_prompt_tokens": estimate_tokens(
                    str(context["chapter_text"])
                ),
            }
        )
        return self._mark_stage(ctx, "retrieve_scripture_context")

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
        # Prompt profiles were retired with the mode system. Preserve the
        # configured value only as diagnostic compatibility metadata.
        ctx.profile_name = "unified"
        ctx.profile_content = ""
        ctx.debug_metadata["profile"] = "unified"
        ctx.debug_metadata["legacy_profile"] = self.config.profile
        ctx.debug_metadata["prompt_strategy"] = "UnifiedFinalAnswerPrompt"
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
        self._lookup_lexical_engine(ctx)
        if ctx.debug_metadata.get("deterministic_fact_packet"):
            self._apply_deterministic_fact_packet(ctx)
            self._evaluate_answer_coverage(ctx)
            self._package_retrieved_evidence(ctx)
            return self._mark_stage(ctx, "lookup_local_knowledge")
        if ctx.debug_metadata.get("transient_translation_lookup"):
            # A translation comparison is intentionally model-looked-up and
            # transient. Do not involve CKL caches or persist retrieved text.
            ctx.canonical_library_context = None
            ctx.canonical_library_prompt = None
            ctx.knowledge_expansion_context_prompt = None
            ctx.debug_metadata["canonical_library_retrieval_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_context_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
            ctx.debug_metadata["transient_translation_lookup_cache_policy"] = "bypass"
            return self._mark_stage(ctx, "lookup_local_knowledge")
        self._lookup_canonical_library(ctx)
        self._evaluate_answer_coverage(ctx)
        self._package_retrieved_evidence(ctx)
        return self._mark_stage(ctx, "lookup_local_knowledge")

    def _package_retrieved_evidence(self, ctx: PipelineContext) -> None:
        """Keep selected research separate from final answer prose.

        This package is intentionally internal. Prompt construction can use its
        constituent evidence, while result rendering receives only FinalAnswer.
        """

        scripture = ctx.scripture_context or {}
        canonical_context = ctx.canonical_library_context or {}
        metadata = (
            canonical_context.get("metadata")
            if isinstance(canonical_context, dict)
            else {}
        )
        metadata = metadata if isinstance(metadata, dict) else {}
        topics = (
            list(canonical_context.get("retrieved_topics") or [])
            if isinstance(canonical_context, dict)
            else []
        )
        direct_textual_evidence = metadata.get("direct_textual_evidence")
        direct_facts = list(
            direct_textual_evidence.get("facts") or []
            if isinstance(direct_textual_evidence, Mapping)
            else []
        )
        references: list[str] = []

        def add_reference(value: Any) -> None:
            text = str(value or "").strip()
            if text and text not in references:
                references.append(text)

        add_reference(scripture.get("focal_reference"))
        for fact in direct_facts:
            if isinstance(fact, Mapping):
                add_reference(fact.get("reference"))
        for topic in topics:
            if not isinstance(topic, Mapping):
                continue
            for reference in topic.get("scripture_references") or []:
                if isinstance(reference, Mapping):
                    add_reference(reference.get("reference"))
                else:
                    add_reference(reference)

        lexical_entries: list[dict[str, Any]] = []
        if isinstance(ctx.local_knowledge, LocalKnowledgeBundle):
            lexical_entries = [
                {
                    "key": entry.key,
                    "language": entry.language,
                    "original": entry.original,
                    "transliteration": entry.transliteration,
                    "glosses": list(entry.glosses),
                    "semantic_range": list(entry.semantic_range),
                }
                for entry in ctx.local_knowledge.lexical_entries
            ]
        ctx.retrieved_evidence = RetrievedEvidence(
            passage_text=str(scripture.get("focal_text") or ""),
            immediate_context="\n\n".join(
                value
                for value in (
                    str(scripture.get("preceding_passage") or "").strip(),
                    str(scripture.get("following_passage") or "").strip(),
                )
                if value
            ),
            ckl_entries=[
                dict(topic) for topic in topics if isinstance(topic, Mapping)
            ],
            lexical_entries=lexical_entries,
            historical_context=[
                dict(topic)
                for topic in topics
                if isinstance(topic, Mapping) and topic.get("historical_context")
            ],
            direct_facts=[
                dict(fact) for fact in direct_facts if isinstance(fact, Mapping)
            ],
            tyndale_entries=[
                dict(item)
                for item in (ctx.debug_metadata.get("tyndale_items") or [])
                if isinstance(item, Mapping)
            ],
            selected_references=references,
        )
        ctx.debug_metadata["evidence_packaged"] = True
        ctx.debug_metadata["evidence_selected_reference_count"] = len(references)

    def _lookup_lexical_engine(self, ctx: PipelineContext) -> None:
        """Retrieve only explicit original-language targets before CKL lookup."""

        ctx.lexical_context_prompt = None
        ctx.debug_metadata["lexical_engine_enabled"] = bool(self.config.lexicon.enabled)
        ctx.debug_metadata["lexical_engine_lookup_attempted"] = False
        ctx.debug_metadata["lexical_engine_entry_count"] = 0
        ctx.debug_metadata["lexical_engine_prompt_tokens"] = 0
        if not self.config.lexicon.enabled or ctx.question_context is None:
            return
        if (
            ctx.question_context.question_type != "word_study"
            and not STRONGS_QUERY_RE.search(ctx.original_question)
        ):
            return
        ctx.debug_metadata["lexical_engine_lookup_attempted"] = True
        try:
            entries, prompt_context = self.lexical_engine.lookup_question(
                language=ctx.question_context.target_language,
                terms=ctx.question_context.target_terms,
                question=ctx.original_question,
                max_results=3,
                max_prompt_tokens=350,
            )
        except (FileNotFoundError, OSError, sqlite3.Error, ValueError) as exc:
            ctx.debug_metadata["lexical_engine_error"] = str(exc)
            ctx.lexical_context_prompt = format_lexical_unavailable_context(
                self.lexical_engine.database_path
            )
            return
        ctx.lexical_context_prompt = prompt_context or None
        ctx.debug_metadata["lexical_engine_entry_count"] = len(entries)
        ctx.debug_metadata["lexical_engine_prompt_tokens"] = estimate_tokens(prompt_context)

    def _apply_deterministic_fact_packet(self, ctx: PipelineContext) -> None:
        packet = ctx.debug_metadata.get("deterministic_fact_packet")
        if not isinstance(packet, dict):
            return
        prompt = format_fact_packet_for_prompt(packet)
        metadata = packet.get("metadata") if isinstance(packet.get("metadata"), dict) else {}
        object_ids = _normalize_object_id_list(metadata.get("object_ids") or [])
        ctx.canonical_library_context = {
            "query": ctx.original_question,
            "retrieved_topics": [],
            "metadata": {
                "retrieval_method": "deterministic_fact_packet",
                "retrieved_object_ids": object_ids,
                "topic_count": len(packet.get("sections") or []),
            },
            "fact_packet": packet,
        }
        ctx.canonical_library_query = str(packet.get("title") or ctx.original_question)
        ctx.canonical_library_prompt = prompt
        ctx.debug_metadata["canonical_library_loaded"] = self.canonical_library is not None
        ctx.debug_metadata["canonical_library_object_ids"] = object_ids
        ctx.debug_metadata["canonical_library_retrieval_method"] = "deterministic_fact_packet"
        ctx.debug_metadata["canonical_library_topic_count"] = len(packet.get("sections") or [])
        ctx.debug_metadata["canonical_library_prompt_tokens"] = estimate_tokens(prompt)
        ctx.debug_metadata["canonical_library_query"] = ctx.canonical_library_query
        ctx.debug_metadata["canonical_library_prompt_mode"] = "deterministic_fact_packet"
        ctx.debug_metadata["canonical_library_context_cache_status"] = "disabled"
        ctx.debug_metadata["canonical_library_retrieval_cache_status"] = "disabled"
        ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
        ctx.debug_metadata["ckl_attempted"] = False
        ctx.debug_metadata["ckl_result_count"] = len(object_ids)
        ctx.debug_metadata["ckl_context_injected"] = True
        ctx.debug_metadata["ckl_retrieval_usable"] = True
        ctx.debug_metadata["fallback_to_model"] = False
        ctx.debug_metadata["fallback_reason"] = None

    def _evaluate_answer_coverage(self, ctx: PipelineContext) -> None:
        """Assess local answer coverage and prepare optional expansion evidence."""

        if ctx.reference_context is None or ctx.question_context is None:
            raise RuntimeError("pipeline context is incomplete before coverage evaluation")

        expansion_config = self.config.knowledge_expansion
        assessment = evaluate_answer_coverage(
            question=ctx.original_question,
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
            question_context=ctx.question_context,
            canonical_context=ctx.canonical_library_context,
            canonical_strong_match=bool(
                ctx.debug_metadata.get("canonical_library_strong_match", False)
            ),
            ckl_coverage_gap=ctx.debug_metadata.get("ckl_coverage_gap"),
            local_knowledge=ctx.local_knowledge,
            lexical_context_prompt=ctx.lexical_context_prompt,
            map_context=ctx.debug_metadata.get("map_tool_context"),
            sufficient_threshold=expansion_config.sufficient_coverage_threshold,
            major_gap_threshold=expansion_config.major_gap_threshold,
            max_gap_items=expansion_config.max_gap_items,
            research_override_enabled=expansion_config.research_override_enabled,
        )
        self._lookup_tyndale_evidence(ctx, assessment)
        if ctx.tyndale_context_prompt:
            metadata_before_tyndale = assessment.to_dict()
            assessment = evaluate_answer_coverage(
                question=ctx.original_question,
                reference_context=ctx.reference_context,
                genre_context=ctx.genre_context,
                question_context=ctx.question_context,
                canonical_context=ctx.canonical_library_context,
                canonical_strong_match=bool(
                    ctx.debug_metadata.get("canonical_library_strong_match", False)
                ),
                ckl_coverage_gap=ctx.debug_metadata.get("ckl_coverage_gap"),
                local_knowledge=ctx.local_knowledge,
                lexical_context_prompt=ctx.lexical_context_prompt,
                map_context=ctx.debug_metadata.get("map_tool_context"),
                additional_evidence=ctx.tyndale_context_prompt,
                sufficient_threshold=expansion_config.sufficient_coverage_threshold,
                major_gap_threshold=expansion_config.major_gap_threshold,
                max_gap_items=expansion_config.max_gap_items,
                research_override_enabled=expansion_config.research_override_enabled,
            )
            ctx.debug_metadata["answer_coverage_before_tyndale"] = metadata_before_tyndale
            ctx.debug_metadata["answer_coverage_after_tyndale"] = assessment.to_dict()
        ctx.answer_coverage_assessment = assessment
        metadata = ctx.debug_metadata
        metadata.update(
            {
                "answer_coverage_score": assessment.score,
                "answer_coverage_mode": assessment.mode,
                "answer_coverage_sufficient": assessment.sufficient,
                "answer_coverage_evaluator": assessment.evaluator,
                "answer_coverage_rationale": assessment.rationale,
                "answer_coverage_covered_dimensions": list(assessment.covered_dimensions),
                "answer_coverage_missing_dimensions": list(assessment.missing_dimensions),
                "research_override_detected": assessment.research_override,
                "knowledge_expansion_requested": False,
                "knowledge_expansion_performed": False,
                "knowledge_expansion_source": "none",
                "knowledge_expansion_blocked": False,
                "knowledge_expansion_blocked_reason": None,
                "external_research_enabled": bool(expansion_config.allow_external_retrieval),
                "external_research_available": False,
                "external_research_attempted": False,
                "external_research_succeeded": False,
                "external_research_result_count": 0,
                "external_research_error": None,
                "external_research_provider": self._research_provider_identity(),
            }
        )
        if ctx.canonical_library_context is not None and ctx.canonical_library_query:
            # CKL context itself is reusable, but the key exposed to the
            # context/response cache must reflect the coverage route that will
            # shape the final prompt.
            metadata["canonical_library_context_cache_key"] = build_context_cache_key(
                canonical_query=ctx.canonical_library_query,
                retrieved_topics=list(
                    ctx.canonical_library_context.get("retrieved_topics") or []
                ),
                answer_mode=ctx.answer_mode,
                max_context_tokens=self.config.canonical_library.max_context_tokens,
                prompt_mode=str(metadata.get("canonical_library_prompt_mode") or "summary"),
                prompt_version=PROMPT_VERSION,
                coverage_mode=assessment.mode,
                missing_dimension_fingerprint="|".join(assessment.missing_dimensions),
            )
        ctx.knowledge_expansion_context_prompt = None

        requested = bool(
            expansion_config.enabled
            and (assessment.mode != CKL_PRIMARY or assessment.research_override)
        )
        metadata["knowledge_expansion_requested"] = requested
        if not requested:
            if not expansion_config.enabled:
                metadata["knowledge_expansion_blocked"] = True
                metadata["knowledge_expansion_blocked_reason"] = "disabled"
            ctx.knowledge_expansion_context_prompt = (
                format_coverage_prompt(
                    assessment,
                    strict_mode=not expansion_config.enabled,
                    model_knowledge_allowed=expansion_config.enabled,
                )
                if expansion_config.enabled or assessment.mode != CKL_PRIMARY
                else None
            )
            return

        strict_mode = bool(self.config.canonical_library.strict_mode)
        model_allowed = bool(
            expansion_config.allow_model_knowledge_expansion
            and self.config.canonical_library.fallback_to_model
            and not strict_mode
        )
        external_prompt = ""
        external_allowed = bool(
            expansion_config.allow_external_retrieval and not strict_mode
        )
        if strict_mode:
            metadata["knowledge_expansion_blocked"] = True
            metadata["knowledge_expansion_blocked_reason"] = "strict_mode"
        elif not self.config.canonical_library.fallback_to_model and not external_allowed:
            metadata["knowledge_expansion_blocked"] = True
            metadata["knowledge_expansion_blocked_reason"] = "fallback_to_model_disabled"

        if external_allowed:
            try:
                available = bool(self.research_provider.is_available())
            except Exception as exc:  # provider availability must never block an answer
                available = False
                metadata["external_research_error"] = str(exc)
            metadata["external_research_available"] = available
            if available:
                metadata["external_research_attempted"] = True
                try:
                    raw_result = self.research_provider.retrieve(
                        question=ctx.original_question,
                        missing_dimensions=assessment.missing_dimensions,
                        reference_context=ctx.reference_context,
                        max_results=expansion_config.max_gap_items,
                    )
                    result = normalize_research_result(
                        raw_result,
                        provider=self._research_provider_identity(),
                    )
                    metadata["external_research_result_count"] = len(result.items)
                    metadata["external_research_succeeded"] = bool(result.items)
                    metadata["external_research_error"] = result.error
                    external_prompt = format_research_result_for_prompt(result)
                except Exception as exc:  # provider failure degrades to model/local path
                    metadata["external_research_error"] = str(exc)
                    ctx.warnings.append(f"External research provider failed: {exc}")

        sources: list[str] = []
        if model_allowed:
            sources.append("model_knowledge")
        if metadata["external_research_succeeded"]:
            sources.append("external_provider")
        if sources:
            metadata["knowledge_expansion_performed"] = True
            metadata["knowledge_expansion_source"] = (
                "model_and_external" if len(sources) > 1 else sources[0]
            )
        elif strict_mode:
            metadata["knowledge_expansion_source"] = "strict_local_only"
        elif metadata["knowledge_expansion_blocked"]:
            metadata["knowledge_expansion_blocked"] = True

        ctx.knowledge_expansion_context_prompt = format_coverage_prompt(
            assessment,
            strict_mode=strict_mode,
            model_knowledge_allowed=model_allowed,
            external_retrieval_enabled=bool(metadata["external_research_succeeded"]),
            external_research_prompt=external_prompt,
        )

    def _lookup_tyndale_evidence(
        self,
        ctx: PipelineContext,
        assessment: AnswerCoverageAssessment,
    ) -> None:
        """Retrieve Tyndale only for an explicit request or a narrow gap."""

        metadata = ctx.debug_metadata
        config = self.config.commentary
        if not config.enabled:
            metadata["tyndale_retrieval_reason"] = "disabled"
            return
        try:
            available = bool(self.tyndale_provider.is_available())
        except Exception as exc:  # local optional resource must never block answers
            metadata["tyndale_error"] = str(exc)
            metadata["tyndale_retrieval_reason"] = "availability_check_failed"
            return
        metadata["tyndale_available"] = available
        if not available:
            metadata["tyndale_retrieval_reason"] = "commentary_not_installed"
            return
        eligible, reason = self.tyndale_provider.should_retrieve(
            question=ctx.original_question,
            missing_dimensions=assessment.missing_dimensions,
            allow_explicit_source_requests=config.allow_explicit_source_requests,
            allow_targeted_gap_requests=config.allow_targeted_gap_requests,
            coverage_mode=assessment.mode,
        )
        metadata["tyndale_eligible"] = eligible
        metadata["tyndale_retrieval_reason"] = reason
        if not eligible:
            return
        metadata["tyndale_retrieval_attempted"] = True
        try:
            result = self.tyndale_provider.retrieve(
                question=ctx.original_question,
                missing_dimensions=assessment.missing_dimensions,
                reference_context=ctx.reference_context,
                max_results=config.max_entries,
            )
            metadata["tyndale_result_count"] = len(result.items)
            metadata["tyndale_retrieval_succeeded"] = bool(result.items)
            metadata["tyndale_error"] = result.error
            if result.items:
                ctx.tyndale_context_prompt = format_tyndale_result_for_prompt(result)
                metadata["tyndale_prompt_tokens"] = estimate_tokens(ctx.tyndale_context_prompt)
                metadata["tyndale_items"] = [
                    {
                        "title": item.title,
                        "text": item.text,
                        "source": item.source,
                        "url": item.url,
                        "provenance": dict(item.provenance),
                    }
                    for item in result.items
                ]
                first_provenance = result.items[0].provenance
                metadata["tyndale_source_id"] = first_provenance.get("source_id")
                metadata["tyndale_source_sha256"] = first_provenance.get("source_sha256")
        except Exception as exc:  # optional evidence must degrade gracefully
            metadata["tyndale_error"] = str(exc)
            ctx.warnings.append(f"Tyndale evidence lookup failed: {exc}")

    def _research_provider_identity(self) -> str:
        identity = getattr(self.research_provider, "identity", None)
        if callable(identity):
            try:
                return str(identity() or "external_provider")
            except Exception:
                return "external_provider"
        return str(getattr(self.research_provider, "name", "external_provider") or "external_provider")

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
                    study_action=ctx.question_context.question_type,
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
        # Developer-only trace for question-driven retrieval.  This remains in
        # model metadata/debug views and is never rendered in the user answer.
        ctx.debug_metadata["canonical_library_retrieval_intent"] = metadata.get("retrieval_intent")
        ctx.debug_metadata["canonical_library_direct_textual_evidence"] = metadata.get("direct_textual_evidence")
        ctx.debug_metadata["canonical_library_rejected_results"] = metadata.get("rejected_results") or []
        ctx.debug_metadata["canonical_library_ranking"] = [
            {
                "id": topic.get("id"),
                "category": topic.get("type"),
                "score": topic.get("score"),
                "entity_match_score": topic.get("entity_match_score"),
                "passage_proximity_score": topic.get("passage_proximity_score"),
                "combined_score": topic.get("combined_score"),
            }
            for topic in canonical_context.get("retrieved_topics") or []
            if isinstance(topic, Mapping)
        ]

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
            coverage_mode=ctx.debug_metadata.get("answer_coverage_mode"),
            missing_dimension_fingerprint="|".join(
                ctx.debug_metadata.get("answer_coverage_missing_dimensions") or []
            ),
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
                    max_context_tokens=(
                        min(self.config.canonical_library.max_context_tokens, CULTURAL_CONTEXT_MAX_TOKENS)
                        if ctx.question_context.question_type == "cultural_context"
                        else self.config.canonical_library.max_context_tokens
                    ),
                    answer_mode=ctx.answer_mode,
                    study_action=ctx.question_context.question_type,
                )
                ctx.canonical_library_prompt = canonical_prompt
            elif strict_ckl_only:
                ctx.canonical_library_prompt = STRICT_CKL_NO_MATCH_PROMPT
            ctx.debug_metadata["canonical_library_prompt_tokens"] = estimate_tokens(
                ctx.canonical_library_prompt
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
        if ctx.debug_metadata.get("transient_translation_lookup"):
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "disabled"
            ctx.debug_metadata["public_answer_cache_error"] = (
                "transient translation lookup"
            )
            return ctx
        if ctx.debug_metadata.get("tyndale_eligible"):
            # A public answer may have been generated without this explicitly
            # requested secondary source.
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "disabled"
            ctx.debug_metadata["public_answer_cache_error"] = (
                "selective Tyndale evidence"
            )
            return ctx
        if ctx.debug_metadata.get("deterministic_fact_packet"):
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "disabled"
            ctx.debug_metadata["public_answer_cache_error"] = "deterministic fact packet supplied"
            return ctx
        if ctx.debug_metadata.get("knowledge_expansion_requested"):
            # Public CKL answers predate the coverage/expansion decision and
            # must not satisfy a request that needs broader or targeted work.
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "bypassed_expansion"
            ctx.debug_metadata["public_answer_cache_error"] = (
                "knowledge expansion requested"
            )
            return ctx
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

        cached_answer = entry.answer.strip()
        cached_validation = normalize_model_response(
            cached_answer,
            response_contract=ANSWER_CONTRACT,
            diagnostics={"cache_layer": "public_answer_cache"},
        )
        if not cached_validation.passed:
            ctx.debug_metadata["public_answer_cache_hit"] = False
            ctx.debug_metadata["public_answer_cache_lookup_status"] = "rejected_unsafe_answer"
            ctx.debug_metadata["public_answer_cache_error"] = "; ".join(
                cached_validation.errors
            )
            ctx.warnings.append(
                "A cached answer was rejected because it was not safe final prose."
            )
            return ctx

        usage_count = entry.usage_count
        try:
            self.public_answer_cache.increment_usage(normalized_question, ctx.answer_mode)
            usage_count = entry.usage_count + 1
        except Exception as exc:  # noqa: BLE001 - cache should not block answers
            ctx.warnings.append(f"Public answer cache usage tracking failed: {exc}")
            ctx.debug_metadata["public_answer_cache_error"] = str(exc)

        cached_answer = cached_validation.sanitized_text
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
        if ctx.debug_metadata.get("transient_translation_lookup"):
            ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_response_cache_key"] = None
            return ctx
        if ctx.debug_metadata.get("deterministic_fact_packet"):
            ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
            ctx.debug_metadata["canonical_library_response_cache_key"] = None
            return ctx
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
            prompt_mode=(
                f"{ctx.debug_metadata.get('canonical_library_prompt_mode') or ''}"
                "|answer_format=unified"
            ),
            knowledge_expansion_fingerprint=self._knowledge_expansion_cache_fingerprint(ctx),
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
        cached_validation = normalize_model_response(
            answer_text,
            response_contract=self._response_contract(ctx.original_question),
            diagnostics={"cache_layer": "runtime_response_cache"},
        )
        if not cached_validation.passed:
            ctx.debug_metadata["canonical_library_response_cache_hit"] = False
            ctx.debug_metadata["canonical_library_response_cache_status"] = "rejected_unsafe_answer"
            ctx.debug_metadata["canonical_library_response_cache_error"] = "; ".join(
                cached_validation.errors
            )
            ctx.warnings.append(
                "A cached response was rejected because it was not safe final prose."
            )
            return ctx
        answer_text = cached_validation.sanitized_text
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

    def _knowledge_expansion_cache_fingerprint(self, ctx: PipelineContext) -> str:
        """Make coverage and provider state part of prompt/response identity."""

        payload = {
            "mode": ctx.debug_metadata.get("answer_coverage_mode"),
            "score": ctx.debug_metadata.get("answer_coverage_score"),
            "research_override": ctx.debug_metadata.get("research_override_detected"),
            "model_allowed": self.config.knowledge_expansion.allow_model_knowledge_expansion,
            "external_enabled": self.config.knowledge_expansion.allow_external_retrieval,
            "external_provider": ctx.debug_metadata.get("external_research_provider"),
            "external_result_count": ctx.debug_metadata.get("external_research_result_count"),
            "tyndale_enabled": self.config.commentary.enabled,
            "tyndale_provider": self.tyndale_provider.identity(),
            "tyndale_available": ctx.debug_metadata.get("tyndale_available"),
            "tyndale_eligible": ctx.debug_metadata.get("tyndale_eligible"),
            "tyndale_result_count": ctx.debug_metadata.get("tyndale_result_count"),
            "tyndale_source_id": ctx.debug_metadata.get("tyndale_source_id"),
            "tyndale_source_sha256": ctx.debug_metadata.get("tyndale_source_sha256"),
            "missing_dimensions": ctx.debug_metadata.get("answer_coverage_missing_dimensions", []),
            "blocked": ctx.debug_metadata.get("knowledge_expansion_blocked"),
            "blocked_reason": ctx.debug_metadata.get("knowledge_expansion_blocked_reason"),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _store_response_cache(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.debug_metadata.get("transient_translation_lookup"):
            ctx.debug_metadata["canonical_library_response_cache_status"] = "disabled"
            return ctx
        if ctx.debug_metadata.get("deterministic_fact_packet"):
            return ctx
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
        if (
            ctx.debug_metadata.get("external_research_attempted")
            and not ctx.debug_metadata.get("external_research_succeeded")
        ):
            # Do not turn a transient provider outage into a successful
            # response-cache entry that masks a later available result.
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
        if ctx.debug_metadata.get("transient_translation_lookup"):
            ctx.session_memory = None
            ctx.debug_metadata["memory_turns_loaded"] = 0
            ctx.debug_metadata["memory_bypass_reason"] = "transient translation lookup"
            return self._mark_stage(ctx, "load_session_memory")
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
        response_format = self._response_format_for_contract(ctx)
        response_contract_prompt = self._response_contract_prompt(
            ctx,
            response_format=response_format,
        )
        prompt_result = build_prompt_result(
            profile_name=ctx.profile_name,
            profile_content=ctx.profile_content,
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
            question_context_or_question=ctx.question_context,
            question=ctx.original_question,
            show_method_notes=self.config.show_method_notes,
            local_knowledge=ctx.local_knowledge,
            map_context=map_context,
            session_memory=ctx.session_memory,
            answer_mode=ctx.answer_mode,
            canonical_context_prompt=ctx.canonical_library_prompt,
            lexical_context_prompt=ctx.lexical_context_prompt,
            knowledge_coverage_prompt=ctx.knowledge_expansion_context_prompt,
            tyndale_context_prompt=ctx.tyndale_context_prompt,
            runtime_profile_mode=self.config.runtime_profile_mode,
            response_contract_prompt=response_contract_prompt,
            scripture_context=ctx.scripture_context,
        )
        ctx.system_prompt = prompt_result.system_prompt
        ctx.user_prompt = prompt_result.user_prompt
        ctx.debug_metadata.update(prompt_result.metadata)
        return self._mark_stage(ctx, "build_prompts")

    def _response_contract_prompt(
        self,
        ctx: PipelineContext,
        *,
        response_format: dict[str, Any] | None,
    ) -> str:
        if self._response_contract(ctx.original_question) != ANSWER_CONTRACT:
            return ""
        if response_format is not None:
            return (
                "# STRUCTURED RESPONSE CONTRACT\n\n"
                'Return JSON with exactly one top-level key, "answer". '
                "The answer value must contain the full user-facing answer as markdown prose. "
                "Do not include analysis, reasoning, debug metadata, retrieval details, or tool calls."
            )
        return (
            "# RESPONSE CONTRACT\n\n"
            "Return the full user-facing answer as Markdown/prose. "
            "Do not wrap the answer in JSON. Do not include analysis, reasoning, debug metadata, retrieval details, or tool calls."
        )

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
            # Local Ollama models and OpenRouter's model catalog do not share a
            # reliable structured-output capability. In automatic mode, let
            # those providers use the prose contract and keep JSON parsing as
            # a compatibility recovery path. Explicit JSON policies still
            # request JSON below.
            if (
                isinstance(self.adapter, OllamaAdapter)
                or self.config.adapter in {"ollama", "openrouter"}
            ):
                return None
            return structured_response_format()
        if contract == SEARCH_RESULTS_CONTRACT and policy != "json_schema":
            return structured_response_format()
        if contract == SEARCH_RESULTS_CONTRACT and supports_schema:
            return structured_response_format()
        return None

    def _should_fail_synthesis_after_model_call(
        self,
        ctx: PipelineContext,
        response_contract: str,
    ) -> bool:
        if response_contract != ANSWER_CONTRACT:
            return False
        if ctx.errors:
            return True
        return not bool((ctx.raw_answer_text or "").strip())

    def _should_fail_synthesis_after_validation(
        self,
        ctx: PipelineContext,
    ) -> bool:
        # Method-quality validation is intentionally soft. If normalization
        # left safe, nonempty prose, the answer is usable even when it does
        # not satisfy every preferred structure check.
        answer_text = (ctx.cleaned_answer_text or "").strip()
        return (
            not answer_text
            or bool(ctx.debug_metadata.get("response_validation_errors"))
            or bool(ctx.debug_metadata.get("repair_rejected") and NON_ANSWER_RE.match(answer_text))
        )

    def _mark_synthesis_failure(
        self,
        ctx: PipelineContext,
        *,
        reason: str,
    ) -> PipelineContext:
        """Fail safely when final prose cannot be produced.

        Retrieval data is evidence, not an alternative answer format.  In
        particular, a timeout, parser failure, or rejected repair must never
        turn CKL entry serialization into the user's response.
        """

        if not ctx.errors:
            ctx.errors.append(
                "The model returned a response, but BHF could not recover usable answer text from it."
            )
        ctx.cleaned_answer_text = ""
        ctx.final_answer = ""
        ctx.final_response = FinalAnswer(text="", warnings=[reason])
        ctx.validation_result = ValidationResult(
            passed=False,
            score=0,
            warnings=[reason],
            suggestions=["Try the request again when the model backend is available."],
        )
        ctx.debug_metadata["synthesis_failed"] = True
        ctx.debug_metadata["synthesis_failure_reason"] = reason
        ctx.debug_metadata.setdefault("error_category", "response_validation")
        ctx.debug_metadata.setdefault("failed_stage", "validating_model_response")
        ctx.debug_metadata["fallback_used"] = False
        return ctx

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

        # The search-results contract is the only intentionally deterministic
        # retrieval response. Normal ask responses always require synthesis.
        raise RuntimeError("Deterministic answer fallback is not available for prose answers")

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
        ctx.debug_metadata["response_validation_error_category"] = (
            validation_result.error_category
        )
        ctx.debug_metadata["response_validation_failed_stage"] = (
            validation_result.failed_stage
        )
        ctx.debug_metadata["response_validation_json_without_answer"] = any(
            "no extractable answer text" in str(error).lower()
            for error in validation_result.errors
        )
        if validation_result.errors:
            ctx.debug_metadata.setdefault(
                "error_category",
                validation_result.error_category or "response_normalization",
            )
            ctx.debug_metadata.setdefault(
                "failed_stage",
                validation_result.failed_stage or "normalizing_model_response",
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
            max_tokens=(
                min(self.config.max_tokens, CULTURAL_CONTEXT_MAX_OUTPUT_TOKENS)
                if ctx.question_context.question_type == "cultural_context"
                else self.config.max_tokens
            ),
            context_window=self.config.context_window,
            response_format=response_format,
            metadata={
                "profile": ctx.profile_name,
                "runtime_profile_mode": "unified",
                "legacy_runtime_profile_mode": self.config.runtime_profile_mode,
                "full_profile_injected": bool(
                    ctx.debug_metadata.get("full_profile_injected")
                ),
                "answer_mode": "unified",
                "legacy_answer_mode": self.config.answer_mode,
                "response_contract": self._response_contract(ctx.original_question),
                "prompt_token_estimates": ctx.debug_metadata.get(
                    "prompt_token_estimates", {}
                ),
                "reference_context": ctx.reference_context.to_dict(),
                "genre_context": ctx.genre_context.to_dict(),
                "question_context": ctx.question_context.to_dict(),
                "local_knowledge_keys": ctx.debug_metadata.get(
                    "local_knowledge_keys", []
                ),
                "lexical_engine_enabled": ctx.debug_metadata.get(
                    "lexical_engine_enabled", False
                ),
                "lexical_engine_entry_count": ctx.debug_metadata.get(
                    "lexical_engine_entry_count", 0
                ),
                "lexical_engine_prompt_tokens": ctx.debug_metadata.get(
                    "lexical_engine_prompt_tokens", 0
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
        if chat_response.errors:
            category = chat_response.error_category or _infer_error_category(
                chat_response.errors
            )
            ctx.debug_metadata["error_category"] = category
            ctx.debug_metadata["failed_stage"] = _failed_stage_for_category(
                category
            )
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
        for warning in ctx.validation_result.warnings:
            if warning not in ctx.warnings:
                ctx.warnings.append(warning)
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
            max_tokens=(
                min(self.config.max_tokens, CULTURAL_CONTEXT_MAX_OUTPUT_TOKENS)
                if ctx.question_context.question_type == "cultural_context"
                else self.config.max_tokens
            ),
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
        if chat_response.errors:
            category = chat_response.error_category or _infer_error_category(
                chat_response.errors
            )
            ctx.debug_metadata["error_category"] = category
            ctx.debug_metadata["failed_stage"] = _failed_stage_for_category(category)

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
            # The original answer remains the candidate result when a repair
            # call returns nothing. Do not let the failed repair overwrite the
            # original response's normalization state.
            ctx.debug_metadata["response_validation_errors"] = []
            ctx.debug_metadata["response_validation_passed"] = bool(
                (ctx.cleaned_answer_text or "").strip()
            )
            ctx.debug_metadata["response_validation_warnings"] = list(
                ctx.debug_metadata.get("response_validation_warnings") or []
            )
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
        for warning in repaired_validation.warnings:
            if warning not in ctx.warnings:
                ctx.warnings.append(warning)
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
            if ctx.debug_metadata.get("error_category") in {
                "response_extraction",
                "response_normalization",
                "response_validation",
                "response_repair",
            }:
                ctx.debug_metadata.pop("error_category", None)
                ctx.debug_metadata.pop("failed_stage", None)
        else:
            ctx.warnings.append(f"Repair was attempted but rejected: {reason}.")
            ctx.debug_metadata["repair_rejected"] = True
            diagnostic = f"Response quality warning: {reason}."
            if diagnostic not in ctx.errors:
                # Retain the diagnostic for debug/API consumers, but the
                # answer remains successful because ``fatal_errors`` is empty.
                ctx.errors.append(diagnostic)

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
        # Only validated synthesis prose can cross the result boundary. Evidence
        # remains in ``ctx.retrieved_evidence`` and debug-only metadata.
        if ctx.debug_metadata.get("synthesis_failed"):
            ctx.final_answer = ""
        else:
            ctx.final_answer = ctx.cleaned_answer_text or ""
        validation_errors = list(ctx.debug_metadata.get("response_validation_errors") or [])
        if validation_errors and not ctx.debug_metadata.get("fallback_used"):
            for error in validation_errors:
                controlled_error = f"Invalid model output: {error}"
                if controlled_error not in ctx.errors:
                    ctx.errors.append(controlled_error)
            ctx.debug_metadata.setdefault("error_category", "response_validation")
            ctx.debug_metadata.setdefault("failed_stage", "validating_model_response")
        if not ctx.final_answer.strip():
            if not validation_errors and not ctx.errors:
                ctx.errors.append(
                    "The model returned a response, but BHF could not recover usable answer text from it."
                )
                ctx.debug_metadata.setdefault("error_category", "response_validation")
                ctx.debug_metadata.setdefault("failed_stage", "building_final_answer")
        evidence = ctx.retrieved_evidence
        ctx.final_response = FinalAnswer(
            text=ctx.final_answer,
            citations=list(evidence.selected_references) if evidence else [],
            warnings=list(ctx.warnings),
        )
        message = (
            "Finalizing fallback answer"
            if ctx.debug_metadata.get("fallback_used")
            else None
        )
        return self._mark_stage(ctx, "finalize_result", message=message)

    def _save_session_turn(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.debug_metadata.get("transient_translation_lookup"):
            ctx.debug_metadata["memory_saved"] = False
            ctx.debug_metadata["memory_bypass_reason"] = "transient translation lookup"
            return self._mark_stage(ctx, "save_session_turn")
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
            "runtime_profile_mode": ctx.debug_metadata.get("runtime_profile_mode"),
            "full_profile_injected": ctx.debug_metadata.get(
                "full_profile_injected", False
            ),
            "prompt_token_estimates": ctx.debug_metadata.get(
                "prompt_token_estimates", {}
            ),
            "prompt_character_counts": ctx.debug_metadata.get(
                "prompt_character_counts", {}
            ),
            "prompt_token_estimator": ctx.debug_metadata.get("prompt_token_estimator"),
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
            "failed_stage": ctx.debug_metadata.get("failed_stage"),
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
            "scripture_context": {
                "required": ctx.debug_metadata.get("scripture_context_required", False),
                "retrieval_status": ctx.debug_metadata.get(
                    "scripture_context_retrieval_status"
                ),
                "translation": ctx.debug_metadata.get("scripture_context_translation"),
                "chapter": ctx.debug_metadata.get("scripture_context_chapter"),
                "focal_reference": ctx.debug_metadata.get(
                    "scripture_context_focal_reference"
                ),
                "scope": ctx.debug_metadata.get("scripture_context_scope"),
            },
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

        fatal_categories = {
            "provider_timeout",
            "provider_connection",
            "provider_failure",
            "response_extraction",
            "response_normalization",
            "response_validation",
            "response_repair",
            "unexpected_internal_error",
        }
        error_category = (
            ctx.debug_metadata.get("error_category")
            or chat_response.error_category
        )
        fatal_errors = list(ctx.errors) if (
            ctx.debug_metadata.get("synthesis_failed")
            or not (ctx.final_answer or "").strip()
            or error_category in fatal_categories
        ) else []

        return AgentResult(
            answer_text=(ctx.final_response.text if ctx.final_response else ctx.final_answer or ""),
            reference_context=ctx.reference_context,
            genre_context=ctx.genre_context,
            question_context=ctx.question_context,
            profile_used=ctx.profile_name,
            validation_result=ctx.validation_result,
            model_metadata=model_metadata,
            warnings=ctx.warnings,
            errors=ctx.errors,
            fatal_errors=fatal_errors,
            error_category=error_category,
            failed_stage=ctx.debug_metadata.get("failed_stage"),
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
                (raw_response.provider if raw_response is not None else None)
                or ctx.debug_metadata.get("provider")
                or self.config.adapter
            )
            model_name = (
                (raw_response.model if raw_response is not None else None)
                or ctx.debug_metadata.get("model")
                or self.config.model
            )
            model_latency_ms = raw_response.latency_ms if raw_response is not None else None
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
            request_failed = error is not None or bool(
                result.fatal_errors if result is not None else []
            )

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
                "runtime_profile_mode": ctx.debug_metadata.get("runtime_profile_mode"),
                "full_profile_injected": bool(
                    ctx.debug_metadata.get("full_profile_injected", False)
                ),
                "prompt_token_estimates": dict(
                    ctx.debug_metadata.get("prompt_token_estimates") or {}
                ),
                "prompt_token_estimator": ctx.debug_metadata.get(
                    "prompt_token_estimator"
                ),
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
                record["runtime_profile_mode"] = ctx.debug_metadata.get(
                    "runtime_profile_mode"
                )
                record["full_profile_injected"] = bool(
                    ctx.debug_metadata.get("full_profile_injected", False)
                )
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
                        "runtime_profile_mode": ctx.debug_metadata.get(
                            "runtime_profile_mode"
                        ),
                        "full_profile_injected": bool(
                            ctx.debug_metadata.get("full_profile_injected", False)
                        ),
                        "prompt_token_estimates": dict(
                            ctx.debug_metadata.get("prompt_token_estimates") or {}
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
        if config.adapter == "openrouter":
            return OpenRouterAdapter(
                base_url=config.base_url or OPENROUTER_BASE_URL,
                api_key=config.api_key,
                timeout_seconds=config.timeout_seconds,
            )
        raise ConfigError(f"unsupported adapter: {config.adapter}")
