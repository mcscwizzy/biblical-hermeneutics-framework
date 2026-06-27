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
class ValidationResult(Serializable):
    passed: bool
    score: int
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class AgentResult(Serializable):
    answer_text: str
    reference_context: ReferenceContext
    genre_context: GenreContext
    profile_used: str
    validation_result: ValidationResult
    model_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
