"""Serializable data models for the BHF agent core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Union


@dataclass
class Serializable:
    """Small dataclass serialization helper for future app/API boundaries."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChatMessage(Serializable):
    role: str
    content: str


@dataclass
class ChatRequest(Serializable):
    system_prompt: str
    user_prompt: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 8192
    context_window: int = 12288
    metadata: dict[str, Any] = field(default_factory=dict)
    response_format: Optional[dict[str, Any]] = None

    def messages(self) -> list[ChatMessage]:
        return [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=self.user_prompt),
        ]


@dataclass
class ChatResponse(Serializable):
    text: str
    model: Optional[str] = None
    provider: Optional[str] = None
    latency_ms: Optional[int] = None
    usage: Optional[dict[str, Any]] = None
    raw_provider_response: Optional[Union[dict[str, Any], str]] = None
    error_category: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def answer(self) -> str:
        return self.text

    @answer.setter
    def answer(self, value: str) -> None:
        self.text = value

    @property
    def raw_response(self) -> Optional[Union[dict[str, Any], str]]:
        return self.raw_provider_response

    @raw_response.setter
    def raw_response(self, value: Optional[Union[dict[str, Any], str]]) -> None:
        self.raw_provider_response = value


@dataclass
class ReferenceContext(Serializable):
    book: Optional[str] = None
    chapter: Optional[int] = None
    verse: Optional[int] = None
    testament: Optional[str] = None
    is_reference_based: bool = False
    topic: Optional[str] = None
    confidence: float = 0.0


@dataclass
class GenreContext(Serializable):
    primary_genre: Optional[str] = None
    secondary_genres: list[str] = field(default_factory=list)
    historical_context_hint: Optional[str] = None
    recommended_modules: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class QuestionContext(Serializable):
    question_type: str
    target_language: Optional[str] = None
    target_terms: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ValidationResult(Serializable):
    passed: bool
    score: int
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class RepairDecision(Serializable):
    should_repair: bool
    reason: str
    warnings_used: list[str] = field(default_factory=list)
    original_score: Optional[int] = None


@dataclass
class RepairAttempt(Serializable):
    attempt_number: int
    repair_prompt: Optional[str] = None
    repaired_answer: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    accepted: bool = False
    reason: str = ""


@dataclass
class AgentResult(Serializable):
    answer_text: str
    reference_context: ReferenceContext
    genre_context: GenreContext
    question_context: QuestionContext
    profile_used: str
    validation_result: ValidationResult
    model_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    repair_applied: bool = False
    repair_attempted: bool = False
    repair_reason: Optional[str] = None
    original_validation_result: Optional[ValidationResult] = None
    repaired_validation_result: Optional[ValidationResult] = None

    def public_response(self) -> dict[str, str]:
        """Return the user-facing response payload."""

        return {"answer": self.answer_text}

    def internal_response(self) -> dict[str, Any]:
        """Return a compact internal response payload for diagnostics."""

        metadata = self.model_metadata or {}
        retrieval_ids = list(metadata.get("canonical_library_object_ids") or [])
        retrieval_tokens = metadata.get("canonical_library_prompt_tokens")
        if retrieval_tokens is None:
            pipeline = metadata.get("pipeline")
            if isinstance(pipeline, dict):
                retrieval_tokens = pipeline.get("canonical_library_prompt_tokens")
        try:
            context_tokens = int(retrieval_tokens) if retrieval_tokens is not None else 0
        except (TypeError, ValueError):
            context_tokens = 0

        return {
            "answer": self.answer_text,
            "retrieval": {
                "result_count": len(retrieval_ids),
                "entry_ids": retrieval_ids,
                "context_tokens": context_tokens,
            },
            "model": {
                "provider": metadata.get("adapter_type") or metadata.get("provider"),
                "model": metadata.get("model") or metadata.get("configured_model"),
            },
        }


@dataclass
class PipelineContext(Serializable):
    """Mutable state for one BHF agent run.

    The context is intentionally simple and dataclass-based so future app/API
    boundaries can serialize or inspect it without coupling to a workflow
    framework.
    """

    original_question: str
    normalized_question: Optional[str] = None
    config_profile: Optional[str] = None
    answer_mode: str = "study"
    reference_context: Optional[ReferenceContext] = None
    genre_context: Optional[GenreContext] = None
    question_context: Optional[QuestionContext] = None
    profile_name: Optional[str] = None
    profile_content: Optional[str] = None
    local_knowledge: Optional[Any] = None
    canonical_library_context: Optional[dict[str, Any]] = None
    canonical_library_prompt: Optional[str] = None
    canonical_library_query: Optional[str] = None
    answer_coverage_assessment: Optional[Any] = None
    knowledge_expansion_context_prompt: Optional[str] = None
    lexical_context_prompt: Optional[str] = None
    session_memory: Optional[Any] = None
    memory_path: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    raw_model_response: Optional[ChatResponse] = None
    raw_answer_text: Optional[str] = None
    cleaned_answer_text: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    original_validation_result: Optional[ValidationResult] = None
    repair_decision: Optional[RepairDecision] = None
    repair_attempts: list[RepairAttempt] = field(default_factory=list)
    repaired_answer_text: Optional[str] = None
    repaired_validation_result: Optional[ValidationResult] = None
    repair_applied: bool = False
    final_answer: Optional[str] = None
    debug_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
