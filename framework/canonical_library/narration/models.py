"""Typed, serializable models for deterministic CKL narration.

These models deliberately describe presentation output.  They are not CKL
records and should never be written back to the canonical library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NarrationLimits:
    """Small budgets that keep human-facing context compact."""

    max_lead_sentences: int = 1
    max_primary_facts: int = 3
    max_supporting_facts: int = 2
    max_cautions: int = 2
    max_visible_qualifications_per_section: int = 1
    max_archaeology_items: int = 2
    max_entities: int = 4
    max_cross_references: int = 4


@dataclass(frozen=True)
class NarratedSentence:
    """One realized sentence and the evidence that produced it."""

    text: str
    role: str
    claim_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    source_details: list[dict[str, Any]] = field(default_factory=list)
    scripture_references: list[str] = field(default_factory=list)
    parent_object_id: str | None = None
    parent_title: str | None = None
    parent_records: list[dict[str, str | None]] = field(default_factory=list)
    certainty: str | None = None
    dispute_status: str | None = None
    certainties: list[str] = field(default_factory=list)
    dispute_statuses: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    content_status: str | None = None
    review_status: str | None = None
    human_review_required: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "role": self.role,
            "claim_ids": list(self.claim_ids),
            "source_ids": list(self.source_ids),
            "source_details": [dict(source) for source in self.source_details],
            "scripture_references": list(self.scripture_references),
            "parent_object_id": self.parent_object_id,
            "parent_title": self.parent_title,
            "parent_records": [dict(record) for record in self.parent_records],
            "certainty": self.certainty,
            "dispute_status": self.dispute_status,
            "certainties": list(self.certainties),
            "dispute_statuses": list(self.dispute_statuses),
            "evidence_ids": list(self.evidence_ids),
            "content_status": self.content_status,
            "review_status": self.review_status,
            "human_review_required": self.human_review_required,
        }


@dataclass(frozen=True)
class NarratedSection:
    """A compact section of related narrated evidence."""

    section_type: str
    heading: str
    sentences: list[NarratedSentence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.section_type,
            "heading": self.heading,
            "sentences": [sentence.to_dict() for sentence in self.sentences],
        }


@dataclass(frozen=True)
class NarrationResult:
    """Structured narration returned to the Study Companion or another UI."""

    reference: str = ""
    title: str = ""
    lead: NarratedSentence | None = None
    sections: list[NarratedSection] = field(default_factory=list)
    additional_evidence_count: int = 0
    evidence_count: int = 0
    source_count: int = 0
    entities: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    content_statuses: list[str] = field(default_factory=list)
    review_statuses: list[str] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(self.lead or self.sections)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "title": self.title,
            "lead": self.lead.to_dict() if self.lead else None,
            "sections": [section.to_dict() for section in self.sections],
            "additional_evidence_count": self.additional_evidence_count,
            "evidence_count": self.evidence_count,
            "source_count": self.source_count,
            "entities": list(self.entities),
            "cross_references": list(self.cross_references),
            "content_statuses": list(self.content_statuses),
            "review_statuses": list(self.review_statuses),
            "has_content": self.has_content,
        }
