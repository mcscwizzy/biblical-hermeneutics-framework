"""Data models for BHF chapter commentary generation and storage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


COMMENTARY_SCHEMA_VERSION = "1.2"
COMMENTARY_PROMPT_VERSION = "1.4"
DATA_GAP_FALLBACK_TEXT = (
    "Passage-specific contextual evidence is not currently available for this chapter."
)


class CommentaryStatus(str, Enum):
    """Lifecycle status for generated chapter commentary."""

    PENDING = "pending"
    GENERATING = "generating"
    VALIDATED = "validated"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    STALE = "stale"


class EvidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    THIN = "THIN"
    DATA_GAP = "DATA_GAP"


class CommentarySectionKind(str, Enum):
    """Supported section kinds for chapter commentary."""

    CHAPTER_OVERVIEW = "chapter_overview"
    HISTORICAL_CONTEXT = "historical_context"
    CULTURAL_CONTEXT = "cultural_context"
    PEOPLE_PLACES = "people_places"
    ARCHAEOLOGY_GEOGRAPHY = "archaeology_geography"
    LANGUAGE_LITERARY = "language_literary"
    CHRONOLOGY = "chronology"
    SURROUNDING_PASSAGES = "surrounding_passages"
    INTERPRETIVE_QUESTIONS = "interpretive_questions"
    THINGS_EASY_TO_MISS = "things_easy_to_miss"
    WHY_IT_MATTERS = "why_it_matters"
    DIG_DEEPER = "dig_deeper"


SUPPORTED_SECTION_KINDS = frozenset(kind.value for kind in CommentarySectionKind)
VERSE_OPTIONAL_SECTION_KINDS = frozenset(
    {
        CommentarySectionKind.HISTORICAL_CONTEXT.value,
        CommentarySectionKind.CULTURAL_CONTEXT.value,
        CommentarySectionKind.ARCHAEOLOGY_GEOGRAPHY.value,
        CommentarySectionKind.SURROUNDING_PASSAGES.value,
    }
)


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
    synthesis_ids: list[str] = field(default_factory=list)
    confidence: str = "medium"
    interpretation_level: str = "inference"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if not self.synthesis_ids:
            value.pop("synthesis_ids")
        return value


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
    synthesis_hash: str | None = None
    synthesis_schema_version: str | None = None
    synthesis_compiler_version: str | None = None
    renderer_label: str | None = None
    imported_timestamp: str | None = None
    candidate_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "synthesis_hash",
            "synthesis_schema_version",
            "synthesis_compiler_version",
            "renderer_label",
            "imported_timestamp",
            "candidate_id",
        ):
            if value[key] is None:
                value.pop(key)
        return value


@dataclass(frozen=True)
class ExternalCommentaryResponse:
    """Untrusted renderer return envelope matched against a locked prompt packet."""

    reference: str
    packet_id: str
    prompt_version: str
    evidence_hash: str
    synthesis_hash: str
    renderer_label: str
    response_payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "packet_id": self.packet_id,
            "prompt_version": self.prompt_version,
            "evidence_hash": self.evidence_hash,
            "synthesis_hash": self.synthesis_hash,
            "renderer_label": self.renderer_label,
            "response_payload": dict(self.response_payload),
        }


@dataclass(frozen=True)
class ChapterCommentary:
    """Complete commentary for a canonical Bible chapter."""

    reference: str
    book: str
    chapter: int
    status: str
    evidence_availability: str | None = None
    sections: list[CommentarySection] = field(default_factory=list)
    generated_metadata: GeneratedMetadata | None = None
    failure_reason: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    data_gap_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = {
            "reference": self.reference,
            "book": self.book,
            "chapter": self.chapter,
            "status": self.status,
            "evidence_availability": self.evidence_availability,
            "sections": [section.to_dict() for section in self.sections],
            "generated_metadata": (
                self.generated_metadata.to_dict() if self.generated_metadata else None
            ),
            "failure_reason": self.failure_reason,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
        }
        # Keep this application-owned marker absent from ordinary/v1.1 output.
        if self.data_gap_fallback:
            value["data_gap_fallback"] = True
        return value


def data_gap_fallback_payload(reference: str, book: str, chapter: int) -> dict[str, Any]:
    """Build the only prose representation permitted for a true DATA_GAP."""

    return {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "status": "pending",
        "data_gap_fallback": True,
        "sections": [
            {
                "kind": CommentarySectionKind.CHAPTER_OVERVIEW.value,
                "title": "Context availability",
                "blocks": [
                    {
                        "id": "data_gap_notice",
                        "text": DATA_GAP_FALLBACK_TEXT,
                        "verse_refs": [],
                        "evidence_ids": [],
                        "synthesis_ids": [],
                        "confidence": "high",
                        "interpretation_level": "fact",
                    }
                ],
            }
        ],
        "generated_metadata": None,
    }


@dataclass(frozen=True)
class CommentaryGenerationRequest:
    """Request to generate commentary for a chapter."""

    book: str
    chapter: int
    reference: str
    evidence_hash: str
    synthesis_hash: str | None = None
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

    def __post_init__(self) -> None:
        """Keep the derived counters consistent whenever a progress value is made."""
        accounted = self.validated + self.partial + self.needs_review + self.failed + self.stale
        object.__setattr__(self, "pending", max(0, self.total_chapters - accounted))

    @property
    def completed(self) -> int:
        return self.validated + self.partial + self.needs_review + self.failed + self.stale

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
