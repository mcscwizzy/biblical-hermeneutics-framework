"""Provider-independent contracts for contextual evidence and presentation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


EVIDENCE_BUNDLE_VERSION = "1.0"
EVIDENCE_BUNDLE_CANDIDATE_VERSION = "1.1"
PRESENTATION_SCHEMA_VERSION = "1.0"

EVIDENCE_CATEGORIES = frozenset(
    {
        "culture",
        "geography",
        "history",
        "archaeology",
        "language",
        "politics",
        "economics",
        "social",
        "chronology",
    }
)
CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})
CARD_TYPES = frozenset({"did_you_know", "walk_the_land", "why_it_matters"})
INTERPRETATION_LEVELS = frozenset({"fact", "inference", "disputed"})
ACTION_TYPES = frozenset(
    {
        "explore_custom",
        "explore_place",
        "explore_person",
        "open_map",
        "show_route",
        "archaeology",
        "related_passages",
        "show_evidence",
        "explore_event",
        "explore_language",
        "explore_history",
    }
)
ENTITY_BUCKETS = ("people", "places", "groups", "events", "artifacts")


@dataclass(frozen=True)
class EntityRef:
    id: str
    title: str
    type: str
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    claim: str
    category: str
    source_ids: list[str]
    related_entity_ids: list[str]
    passage_anchors: list[str]
    confidence: str
    relevance_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    passage_ref: str
    entities: dict[str, list[EntityRef]]
    evidence_items: list[EvidenceItem]
    geography: dict[str, Any]
    provenance: dict[str, Any]
    version: str = EVIDENCE_BUNDLE_VERSION
    evidence_hash: str = ""

    @property
    def evidence_hash_version(self) -> str:
        """Identity-hash contract used by this bundle generation."""

        return "2" if self.version == EVIDENCE_BUNDLE_CANDIDATE_VERSION else "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passage_ref": self.passage_ref,
            "entities": {
                bucket: [entity.to_dict() for entity in self.entities.get(bucket, [])]
                for bucket in ENTITY_BUCKETS
            },
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "geography": self.geography,
            "provenance": self.provenance,
            "version": self.version,
            "evidence_hash": self.evidence_hash,
            "evidence_hash_version": self.evidence_hash_version,
        }

    @property
    def evidence_by_id(self) -> dict[str, EvidenceItem]:
        return {item.id: item for item in self.evidence_items}

    @property
    def entities_by_id(self) -> dict[str, EntityRef]:
        return {
            entity.id: entity
            for bucket in ENTITY_BUCKETS
            for entity in self.entities.get(bucket, [])
        }


@dataclass(frozen=True)
class DigDeeperAction:
    type: str
    label: str
    target_id: str | None = None
    reference: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PresentationCard:
    id: str
    type: str
    headline: str
    body: str
    evidence_ids: list[str]
    confidence: str
    interpretation_level: str
    dig_in_summary: str | None = None
    related_entity_ids: list[str] = field(default_factory=list)
    map_focus: dict[str, Any] | None = None
    dig_deeper_actions: list[DigDeeperAction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedFrom:
    evidence_hash: str
    evidence_bundle_version: str
    presentation_schema_version: str
    prompt_version: str
    model: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PresentationPacket:
    passage_ref: str
    cards: list[PresentationCard]
    generated_from: GeneratedFrom

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def mapping(value: Any) -> dict[str, Any]:
    """Return a serializable shallow mapping for CKL dataclasses or dictionaries."""

    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        return dict(result) if isinstance(result, Mapping) else {}
    try:
        return asdict(value)
    except (TypeError, ValueError):
        return dict(vars(value)) if hasattr(value, "__dict__") else {}
