"""Data models for BHF chapter commentary generation and storage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


COMMENTARY_SCHEMA_VERSION = "1.0"
COMMENTARY_PROMPT_VERSION = "1.0"


class CommentaryStatus(str, Enum):
    """Lifecycle status for generated chapter commentary."""

    PENDING = "pending"
    GENERATING = "generating"
    VALIDATED = "validated"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    STALE = "stale"


class CommentarySectionKind(str, Enum):
    """Supported section kinds for chapter commentary."""

    CHAPTER_OVERVIEW = "chapter_overview"
    HISTORICAL_CONTEXT = "historical_context"
    PEOPLE_PLACES = "people_places"
    ARCHAEOLOGY_GEOGRAPHY = "archaeology_geography"
    LANGUAGE_LITERARY = "language_literary"
    CHRONOLOGY = "chronology"
    INTERPRETIVE_QUESTIONS = "interpretive_questions"
    THINGS_EASY_TO_MISS = "things_easy_to_miss"
    DIG_DEEPER = "dig_deeper"


SUPPORTED_SECTION_KINDS = frozenset(kind.value for kind in CommentarySectionKind)


class ConfidenceLevel(str, Enum):
    """Confidence in a commentary claim based on evidence."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InterpretationLevel(str, Enum):
    """The nature of the interpretive claim."""

    FACT = "fact"
    INFERENCE = "inference"
    DISPUTED = "disputed"


@dataclass(frozen=True)
class CommentaryBlock:
    """A single prose block within a section with evidence tracking."""

    id: str
    text: str
    verse_refs: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    confidence: str = "medium"
    interpretation_level: str = "inference"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommentarySection:
    """A section within the commentary with multiple blocks."""

    kind: str
    title: str
    blocks: list[CommentaryBlock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True)
class GeneratedMetadata:
    """Metadata about how the commentary was generated."""

    evidence_hash: str
    evidence_bundle_version: str
    commentary_schema_version: str
    commentary_prompt_version: str
    model: str
    generated_timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChapterCommentary:
    """Complete commentary for a canonical Bible chapter."""

    reference: str
    book: str
    chapter: int
    status: str
    sections: list[CommentarySection] = field(default_factory=list)
    generated_metadata: GeneratedMetadata | None = None
    failure_reason: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "book": self.book,
            "chapter": self.chapter,
            "status": self.status,
            "sections": [section.to_dict() for section in self.sections],
            "generated_metadata": (
                self.generated_metadata.to_dict() if self.generated_metadata else None
            ),
            "failure_reason": self.failure_reason,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
        }


@dataclass(frozen=True)
class CommentaryGenerationRequest:
    """Request to generate commentary for a chapter."""

    book: str
    chapter: int
    reference: str
    evidence_hash: str
    force_regenerate: bool = False


@dataclass(frozen=True)
class CommentaryGenerationResult:
    """Result of a generation attempt."""

    reference: str
    status: str
    commentary: ChapterCommentary | None = None
    error: str | None = None


@dataclass(frozen=True)
class CommentaryProgress:
    """Overall progress metrics for full-Bible generation."""

    total_chapters: int
    validated: int = 0
    partial: int = 0
    needs_review: int = 0
    failed: int = 0
    stale: int = 0
    pending: int = 0

    @property
    def completed(self) -> int:
        return self.validated + self.partial + self.needs_review + self.failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_chapters": self.total_chapters,
            "completed": self.completed,
            "validated": self.validated,
            "partial": self.partial,
            "needs_review": self.needs_review,
            "failed": self.failed,
            "stale": self.stale,
            "pending": self.pending,
        }
