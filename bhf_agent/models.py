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
    max_tokens: int = 2048
    metadata: dict[str, Any] = field(default_factory=dict)

    def messages(self) -> list[ChatMessage]:
        return [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=self.user_prompt),
        ]


@dataclass
class ChatResponse(Serializable):
    text: str
    model: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
    raw_provider_response: Optional[Union[dict[str, Any], str]] = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


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
