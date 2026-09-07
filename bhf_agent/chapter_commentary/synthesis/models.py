"""Serializable contracts for deterministic compiled chapter synthesis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SYNTHESIS_SCHEMA_VERSION = "1.1"
SYNTHESIS_COMPILER_VERSION = "1.1"
SYNTHESIS_PASSAGE_SCOPES = frozenset({"CURRENT_CHAPTER", "SURROUNDING_PASSAGE"})

SYNTHESIS_UNIT_KINDS = frozenset(
    {
        "chapter_overview",
        "historical_context",
        "cultural_context",
        "people_places",
        "archaeology_geography",
        "language_literary",
        "chronology",
        "surrounding_passages",
        "interpretive_questions",
        "things_easy_to_miss",
        "why_it_matters",
    }
)


@dataclass(frozen=True)
class SynthesisUnit:
    """A traceable group of compatible supplied evidence facts."""

    id: str
    kind: str
    facts: list[str]
    verse_refs: list[str]
    evidence_ids: list[str]
    entity_ids: list[str]
    related_unit_ids: list[str] = field(default_factory=list)
    confidence: str = "medium"
    interpretation_level: str = "fact"
    passage_scope: str = "CURRENT_CHAPTER"
    source_anchors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SynthesisGap:
    """A deterministic description of evidence the compiler cannot supply."""

    category: str
    reason: str
    severity: str = "informational"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SynthesisCoverage:
    """Auditable accounting for evidence consumed by the compiler."""

    evidence_item_count: int
    used_evidence_ids: list[str]
    unused_evidence_ids: list[str]
    evidence_categories: dict[str, int]
    category_diversity: int
    specific_evidence_count: int
    entity_counts: dict[str, int]
    unit_kind_counts: dict[str, int]
    relationship_unit_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompiledChapterSynthesis:
    """Deterministic understanding packet compiled from one EvidenceBundle."""

    reference: str
    book: str
    chapter: int
    evidence_hash: str
    evidence_bundle_version: str
    synthesis_schema_version: str
    synthesis_compiler_version: str
    synthesis_hash: str
    evidence_availability: str
    synthesis_units: list[SynthesisUnit]
    evidence_gaps: list[SynthesisGap]
    coverage: SynthesisCoverage

    @property
    def units_by_id(self) -> dict[str, SynthesisUnit]:
        return {unit.id: unit for unit in self.synthesis_units}

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "book": self.book,
            "chapter": self.chapter,
            "evidence_hash": self.evidence_hash,
            "evidence_bundle_version": self.evidence_bundle_version,
            "synthesis_schema_version": self.synthesis_schema_version,
            "synthesis_compiler_version": self.synthesis_compiler_version,
            "synthesis_hash": self.synthesis_hash,
            "evidence_availability": self.evidence_availability,
            "synthesis_units": [unit.to_dict() for unit in self.synthesis_units],
            "evidence_gaps": [gap.to_dict() for gap in self.evidence_gaps],
            "coverage": self.coverage.to_dict(),
        }
