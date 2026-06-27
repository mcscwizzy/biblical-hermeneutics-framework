"""Reusable BHF agent runner."""

from __future__ import annotations

from typing import Any, Optional

from .adapters import ChatAdapter, OpenAICompatibleAdapter
from .config import AgentConfig, ConfigError
from .genre import classify_genre
from .knowledge import LocalKnowledgeBundle, lookup_local_knowledge
from .memory import (
    SessionMemory,
    append_session_turn,
    load_session_memory,
    save_session_memory,
)
from .models import (
    AgentResult,
    ChatRequest,
    PipelineContext,
    RepairAttempt,
    ValidationResult,
)
from .output_cleaner import clean_model_output
from .profiles import ProfileLoader
from .prompts import build_prompt, strategy_for_profile
from .question_types import classify_question_type
from .repair import build_repair_prompt, decide_repair
from .references import detect_reference
from .validation import validate_response


class BHFAgent:
    def __init__(
        self,
        config: AgentConfig,
        adapter: Optional[ChatAdapter] = None,
        profile_loader: Optional[ProfileLoader] = None,
    ) -> None:
        config.validate()
        self.config = config
        self.profile_loader = profile_loader or ProfileLoader()
        self.adapter = adapter or self._build_adapter(config)

    def ask(self, question: str) -> AgentResult:
        ctx = self._initialize_context(question)
        ctx = self._detect_reference(ctx)
        ctx = self._classify_genre(ctx)
        ctx = self._classify_question_type(ctx)
        ctx = self._load_profile(ctx)
        ctx = self._lookup_local_knowledge(ctx)
        ctx = self._load_session_memory(ctx)
        ctx = self._build_prompts(ctx)
        ctx = self._call_model(ctx)
        ctx = self._clean_output(ctx)
        ctx = self._validate_response(ctx)
        ctx = self._repair_response(ctx)
        ctx = self._finalize_result(ctx)
        ctx = self._save_session_turn(ctx)
        return self._to_agent_result(ctx)

    def _initialize_context(self, question: str) -> PipelineContext:
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
                "local_knowledge_keys": [],
                "output_cleanup_applied": False,
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
        return self._mark_stage(ctx, "lookup_local_knowledge")

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
        ctx.system_prompt, ctx.user_prompt = build_prompt(
            ctx.profile_name,
            ctx.profile_content,
            ctx.reference_context,
            ctx.genre_context,
            ctx.question_context,
            ctx.original_question,
            show_method_notes=self.config.show_method_notes,
            local_knowledge=ctx.local_knowledge,
            session_memory=ctx.session_memory,
            answer_mode=ctx.answer_mode,
        )
        return self._mark_stage(ctx, "build_prompts")

    def _call_model(self, ctx: PipelineContext) -> PipelineContext:
        if (
            ctx.system_prompt is None
            or ctx.user_prompt is None
            or ctx.reference_context is None
            or ctx.genre_context is None
            or ctx.question_context is None
        ):
            raise RuntimeError("pipeline context is incomplete before model call")
        chat_request = ChatRequest(
            system_prompt=ctx.system_prompt,
            user_prompt=ctx.user_prompt,
            model=self.config.model or "",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            metadata={
                "profile": ctx.profile_name,
                "answer_mode": ctx.answer_mode,
                "reference_context": ctx.reference_context.to_dict(),
                "genre_context": ctx.genre_context.to_dict(),
                "question_context": ctx.question_context.to_dict(),
                "local_knowledge_keys": ctx.debug_metadata.get(
                    "local_knowledge_keys", []
                ),
                "memory_enabled": self.config.memory_enabled,
                "session_id": ctx.debug_metadata.get("session_id"),
                "memory_turns_loaded": ctx.debug_metadata.get("memory_turns_loaded", 0),
            },
        )
        chat_response = self.adapter.chat(chat_request)
        ctx.raw_model_response = chat_response
        ctx.raw_answer_text = chat_response.text
        ctx.warnings.extend(chat_response.warnings)
        ctx.errors.extend(chat_response.errors)
        if chat_response.model:
            ctx.debug_metadata["model"] = chat_response.model
        return self._mark_stage(ctx, "call_model")

    def _clean_output(self, ctx: PipelineContext) -> PipelineContext:
        cleanup_result = clean_model_output(ctx.raw_answer_text or "")
        ctx.cleaned_answer_text = cleanup_result.text
        ctx.debug_metadata["output_cleanup_applied"] = cleanup_result.applied
        ctx.debug_metadata["cleanup_removed_headings"] = cleanup_result.removed_headings
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
        )
        chat_request = ChatRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=self.config.model or "",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
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

        cleanup_result = clean_model_output(chat_response.text)
        repaired_answer = cleanup_result.text.strip()
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
        return self._mark_stage(ctx, "finalize_result")

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
            "answer_mode": ctx.answer_mode,
            "memory_enabled": self.config.memory_enabled,
            "session_id": ctx.debug_metadata.get("session_id"),
            "memory_path": ctx.debug_metadata.get("memory_path"),
            "memory_turns_loaded": ctx.debug_metadata.get("memory_turns_loaded", 0),
            "memory_turns_saved": ctx.debug_metadata.get("memory_turns_saved", 0),
            "model": chat_response.model,
            "usage": chat_response.usage,
            "cleanup_applied": ctx.debug_metadata.get("output_cleanup_applied", False),
            "cleanup_removed_headings": ctx.debug_metadata.get(
                "cleanup_removed_headings", []
            ),
            "local_knowledge_keys": ctx.debug_metadata.get("local_knowledge_keys", []),
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

    def _mark_stage(self, ctx: PipelineContext, stage: str) -> PipelineContext:
        stages = ctx.debug_metadata.setdefault("stages_completed", [])
        if isinstance(stages, list):
            stages.append(stage)
        return ctx

    def _build_adapter(self, config: AgentConfig) -> ChatAdapter:
        if config.adapter == "openai_compatible":
            if not config.base_url:
                raise ConfigError("base_url is required for openai_compatible adapter")
            return OpenAICompatibleAdapter(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout_seconds=config.timeout_seconds,
            )
        raise ConfigError(f"unsupported adapter: {config.adapter}")
