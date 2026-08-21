"""Typed, auditable evidence records embedded in canonical CKL objects.

JSON remains the authoring source of truth.  These small value objects keep
evidence, chronology, passage relevance, and external-domain links explicit
without requiring a graph database or an LLM at retrieval time.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Mapping, Sequence

from .normalization import normalize_id
from .scripture import build_book_alias_lookup, parse_scripture_reference


EVIDENCE_TYPE_VALUES: tuple[str, ...] = (
    "artifact",
    "archaeological-site",
    "inscription",
    "ancient-text",
    "manuscript",
    "historical-event",
    "person",
    "people-group",
    "institution",
    "cultural-practice",
    "geography-environment",
    "historical-period",
    "literary-convention",
    "worldview-concept",
    "primary-source",
    "secondary-source",
    "material-culture",
    "other",
)

EVIDENCE_ASSERTION_TYPE_VALUES: tuple[str, ...] = (
    "primary-evidence",
    "secondary-evidence",
    "scholarly-reconstruction",
    "inference",
)

EVIDENCE_CONFIDENCE_VALUES: tuple[str, ...] = (
    "unrated",
    "low",
    "medium",
    "high",
)

EVIDENCE_CERTAINTY_VALUES: tuple[str, ...] = (
    "textually_explicit",
    "strong_consensus",
    "probable",
    "plausible",
    "disputed",
    "speculative",
    "insufficient_evidence",
)

EVIDENCE_DISPUTE_STATUS_VALUES: tuple[str, ...] = (
    "not_disputed",
    "minor_scholarly_disagreement",
    "major_scholarly_disagreement",
    "textual_variant",
    "lexical_uncertainty",
    "historical_uncertainty",
    "chronological_uncertainty",
    "archaeological_uncertainty",
    "identification_uncertainty",
    "interpretive_uncertainty",
)

EVIDENCE_PASSAGE_RELATIONSHIP_VALUES: tuple[str, ...] = (
    "direct",
    "contextual",
    "comparative",
    "contrast",
    "disputed",
)

TEMPORAL_RELATION_VALUES: tuple[str, ...] = (
    "contemporary",
    "near-contemporary",
    "earlier-comparative",
    "later-comparative",
    "diachronic",
    "unknown",
)

EXTERNAL_EVIDENCE_DOMAIN_VALUES: tuple[str, ...] = (
    "archaeology-item",
    "archaeology-site",
    "map-place",
    "external-dataset",
)

EVIDENCE_METADATA_FIELDS: tuple[str, ...] = (
    "artifact_name",
    "site_name",
    "discovery_location",
    "present_location",
    "archaeological_period",
    "associated_culture",
    "associated_biblical_geography",
    "image_source_url",
    "image_license",
    "image_attribution",
)

_KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BOOK_ALIAS_LOOKUP = build_book_alias_lookup(())


class EvidenceValidationError(ValueError):
    """Raised when one evidence record is structurally unsafe or ambiguous."""


@dataclass(frozen=True)
class CanonicalTemporalScope:
    """Signed years use negative integers for BCE and positive for CE."""

    start_year: int | None = None
    end_year: int | None = None
    approximate: bool = False
    periods: list[str] = field(default_factory=list)
    narrative_setting: str = ""
    source_composition_start_year: int | None = None
    source_composition_end_year: int | None = None
    source_composition_approximate: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | "CanonicalTemporalScope") -> "CanonicalTemporalScope":
        if isinstance(value, cls):
            return value
        return validate_temporal_scope(value)


@dataclass(frozen=True)
class CanonicalEvidencePassageLink:
    reference: str
    relationship: str
    temporal_relation: str
    relevance_rationale: str
    weight: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CanonicalEvidenceRelationship:
    id: str
    relationship: str
    weight: int = 1
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CanonicalExternalEvidenceReference:
    domain: str
    id: str
    relationship: str = "same-evidence"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CanonicalEvidenceItem:
    id: str
    title: str
    evidence_type: str
    description: str
    assertion_type: str
    confidence: str
    confidence_rationale: str
    passage_relevance: str
    certainty: str = "plausible"
    dispute_status: str = "not_disputed"
    primary_observation: str = ""
    scholarly_interpretation: str = ""
    temporal_scope: CanonicalTemporalScope = field(default_factory=CanonicalTemporalScope)
    geography_ids: list[str] = field(default_factory=list)
    related_objects: list[CanonicalEvidenceRelationship] = field(default_factory=list)
    related_evidence: list[CanonicalEvidenceRelationship] = field(default_factory=list)
    scripture_references: list[CanonicalEvidencePassageLink] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    external_references: list[CanonicalExternalEvidenceReference] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | "CanonicalEvidenceItem") -> "CanonicalEvidenceItem":
        if isinstance(value, cls):
            return value
        return validate_evidence_item(value)


def validate_temporal_scope(value: Mapping[str, Any] | CanonicalTemporalScope | None) -> CanonicalTemporalScope:
    if value is None:
        return CanonicalTemporalScope()
    if isinstance(value, CanonicalTemporalScope):
        return value
    if not isinstance(value, Mapping):
        raise EvidenceValidationError("temporal_scope must be an object")

    allowed = {
        "start_year",
        "end_year",
        "approximate",
        "periods",
        "narrative_setting",
        "source_composition_start_year",
        "source_composition_end_year",
        "source_composition_approximate",
        "notes",
    }
    _reject_unknown_fields(value, allowed, label="temporal_scope")
    start_year = _optional_year(value.get("start_year"), "temporal_scope.start_year")
    end_year = _optional_year(value.get("end_year"), "temporal_scope.end_year")
    composition_start = _optional_year(
        value.get("source_composition_start_year"),
        "temporal_scope.source_composition_start_year",
    )
    composition_end = _optional_year(
        value.get("source_composition_end_year"),
        "temporal_scope.source_composition_end_year",
    )
    _validate_year_range(start_year, end_year, "temporal_scope")
    _validate_year_range(composition_start, composition_end, "temporal_scope source composition")
    return CanonicalTemporalScope(
        start_year=start_year,
        end_year=end_year,
        approximate=_boolean(value.get("approximate", False), "temporal_scope.approximate"),
        periods=_string_list(value.get("periods", []), "temporal_scope.periods"),
        narrative_setting=_string(value.get("narrative_setting", ""), "temporal_scope.narrative_setting"),
        source_composition_start_year=composition_start,
        source_composition_end_year=composition_end,
        source_composition_approximate=_boolean(
            value.get("source_composition_approximate", False),
            "temporal_scope.source_composition_approximate",
        ),
        notes=_string(value.get("notes", ""), "temporal_scope.notes"),
    )


def validate_evidence_items(value: Any) -> list[CanonicalEvidenceItem]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvidenceValidationError("evidence_items must be a list")
    items = [validate_evidence_item(item) for item in value]
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
        raise EvidenceValidationError("duplicate evidence item id(s): " + ", ".join(duplicates))
    known = set(ids)
    for item in items:
        for relationship in item.related_evidence:
            if relationship.id not in known:
                raise EvidenceValidationError(
                    f'evidence item "{item.id}" references missing evidence item "{relationship.id}"'
                )
    return items


def validate_evidence_item(value: Mapping[str, Any] | CanonicalEvidenceItem) -> CanonicalEvidenceItem:
    if isinstance(value, CanonicalEvidenceItem):
        return value
    if not isinstance(value, Mapping):
        raise EvidenceValidationError("each evidence item must be an object")

    allowed = {
        "id",
        "title",
        "evidence_type",
        "description",
        "assertion_type",
        "confidence",
        "confidence_rationale",
        "passage_relevance",
        "certainty",
        "dispute_status",
        "primary_observation",
        "scholarly_interpretation",
        "temporal_scope",
        "geography_ids",
        "related_objects",
        "related_evidence",
        "scripture_references",
        "source_ids",
        "claim_ids",
        "external_references",
        "metadata",
        "notes",
    }
    _reject_unknown_fields(value, allowed, label="evidence item")
    item_id = normalize_id(_required_string(value, "id"))
    if not item_id or not _KEBAB_CASE_RE.fullmatch(item_id):
        raise EvidenceValidationError("evidence item id must be canonical kebab-case")

    evidence_type = _enum(value.get("evidence_type"), EVIDENCE_TYPE_VALUES, "evidence_type")
    assertion_type = _enum(
        value.get("assertion_type"),
        EVIDENCE_ASSERTION_TYPE_VALUES,
        "assertion_type",
    )
    confidence = _enum(value.get("confidence"), EVIDENCE_CONFIDENCE_VALUES, "confidence")
    certainty = _enum(
        value.get("certainty", "plausible"),
        EVIDENCE_CERTAINTY_VALUES,
        "certainty",
    )
    dispute_status = _enum(
        value.get("dispute_status", "not_disputed"),
        EVIDENCE_DISPUTE_STATUS_VALUES,
        "dispute_status",
    )
    source_ids = _id_list(value.get("source_ids", []), "source_ids")
    scripture_references = _passage_links(value.get("scripture_references", []))
    if not source_ids:
        raise EvidenceValidationError(f'evidence item "{item_id}" must cite at least one source_id')
    if not scripture_references:
        raise EvidenceValidationError(
            f'evidence item "{item_id}" must explain relevance to at least one Scripture reference'
        )

    metadata_value = value.get("metadata", {})
    if not isinstance(metadata_value, Mapping):
        raise EvidenceValidationError("evidence item metadata must be an object")
    _reject_unknown_fields(metadata_value, set(EVIDENCE_METADATA_FIELDS), label="evidence metadata")
    metadata = {
        str(key): _string(item, f"metadata.{key}")
        for key, item in metadata_value.items()
        if _string(item, f"metadata.{key}")
    }
    if metadata.get("image_source_url") and not metadata.get("image_license"):
        raise EvidenceValidationError("evidence metadata image_source_url requires image_license")
    if metadata.get("image_source_url") and not metadata.get("image_attribution"):
        raise EvidenceValidationError("evidence metadata image_source_url requires image_attribution")

    return CanonicalEvidenceItem(
        id=item_id,
        title=_required_string(value, "title"),
        evidence_type=evidence_type,
        description=_required_string(value, "description"),
        assertion_type=assertion_type,
        confidence=confidence,
        confidence_rationale=_required_string(value, "confidence_rationale"),
        passage_relevance=_required_string(value, "passage_relevance"),
        certainty=certainty,
        dispute_status=dispute_status,
        primary_observation=_string(value.get("primary_observation", ""), "primary_observation"),
        scholarly_interpretation=_string(
            value.get("scholarly_interpretation", ""),
            "scholarly_interpretation",
        ),
        temporal_scope=validate_temporal_scope(value.get("temporal_scope")),
        geography_ids=_id_list(value.get("geography_ids", []), "geography_ids"),
        related_objects=_relationships(value.get("related_objects", []), "related_objects"),
        related_evidence=_relationships(value.get("related_evidence", []), "related_evidence"),
        scripture_references=scripture_references,
        source_ids=source_ids,
        claim_ids=_id_list(value.get("claim_ids", []), "claim_ids"),
        external_references=_external_references(value.get("external_references", [])),
        metadata=metadata,
        notes=_string(value.get("notes", ""), "notes"),
    )


def validate_evidence_references(
    items: Sequence[CanonicalEvidenceItem],
    *,
    object_ids: Sequence[str],
    claim_ids: Sequence[str],
    source_ids: Sequence[str],
) -> None:
    known_objects = set(object_ids)
    known_claims = set(claim_ids)
    known_sources = set(source_ids)
    for item in items:
        missing_objects = sorted(
            {
                *{relationship.id for relationship in item.related_objects},
                *set(item.geography_ids),
            }
            - known_objects
        )
        missing_claims = sorted(set(item.claim_ids) - known_claims)
        missing_sources = sorted(set(item.source_ids) - known_sources)
        if missing_objects:
            raise EvidenceValidationError(
                f'evidence item "{item.id}" references missing CKL object(s): {", ".join(missing_objects)}'
            )
        if missing_claims:
            raise EvidenceValidationError(
                f'evidence item "{item.id}" references missing claim(s): {", ".join(missing_claims)}'
            )
        if missing_sources:
            raise EvidenceValidationError(
                f'evidence item "{item.id}" references missing source(s): {", ".join(missing_sources)}'
            )


def _passage_links(value: Any) -> list[CanonicalEvidencePassageLink]:
    if not isinstance(value, list):
        raise EvidenceValidationError("scripture_references must be a list")
    links: list[CanonicalEvidencePassageLink] = []
    seen: set[tuple[str, str]] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise EvidenceValidationError("each evidence Scripture reference must be an object")
        _reject_unknown_fields(
            raw,
            {"reference", "relationship", "temporal_relation", "relevance_rationale", "weight"},
            label="evidence Scripture reference",
        )
        weight = _integer(raw.get("weight", 1), "scripture reference weight")
        if not 1 <= weight <= 10:
            raise EvidenceValidationError("evidence Scripture reference weight must be between 1 and 10")
        reference = _required_string(raw, "reference")
        if parse_scripture_reference(reference, book_alias_lookup=_BOOK_ALIAS_LOOKUP) is None:
            raise EvidenceValidationError(
                f'evidence Scripture reference is not parseable: "{reference}"'
            )
        relationship = _enum(
            raw.get("relationship"),
            EVIDENCE_PASSAGE_RELATIONSHIP_VALUES,
            "scripture reference relationship",
        )
        key = (reference.casefold(), relationship)
        if key in seen:
            raise EvidenceValidationError(
                f"duplicate evidence Scripture relationship: {reference} {relationship}"
            )
        seen.add(key)
        links.append(
            CanonicalEvidencePassageLink(
                reference=reference,
                relationship=relationship,
                temporal_relation=_enum(
                    raw.get("temporal_relation"),
                    TEMPORAL_RELATION_VALUES,
                    "scripture reference temporal_relation",
                ),
                relevance_rationale=_required_string(raw, "relevance_rationale"),
                weight=weight,
            )
        )
    return links


def _relationships(value: Any, label: str) -> list[CanonicalEvidenceRelationship]:
    if not isinstance(value, list):
        raise EvidenceValidationError(f"{label} must be a list")
    relationships: list[CanonicalEvidenceRelationship] = []
    seen: set[tuple[str, str]] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise EvidenceValidationError(f"each {label} entry must be an object")
        _reject_unknown_fields(raw, {"id", "relationship", "weight", "notes"}, label=label)
        target_id = normalize_id(_required_string(raw, "id"))
        relationship = _required_string(raw, "relationship")
        if not _KEBAB_CASE_RE.fullmatch(relationship):
            raise EvidenceValidationError(f"{label} relationship must be kebab-case")
        weight = _integer(raw.get("weight", 1), f"{label} weight")
        if not 1 <= weight <= 10:
            raise EvidenceValidationError(f"{label} weight must be between 1 and 10")
        key = (target_id, relationship)
        if key in seen:
            raise EvidenceValidationError(f"duplicate {label} relationship: {target_id} {relationship}")
        seen.add(key)
        relationships.append(
            CanonicalEvidenceRelationship(
                id=target_id,
                relationship=relationship,
                weight=weight,
                notes=_string(raw.get("notes", ""), f"{label} notes"),
            )
        )
    return relationships


def _external_references(value: Any) -> list[CanonicalExternalEvidenceReference]:
    if not isinstance(value, list):
        raise EvidenceValidationError("external_references must be a list")
    references: list[CanonicalExternalEvidenceReference] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise EvidenceValidationError("each external reference must be an object")
        _reject_unknown_fields(raw, {"domain", "id", "relationship", "notes"}, label="external reference")
        relationship = _string(raw.get("relationship", "same-evidence"), "external reference relationship")
        if not relationship or not _KEBAB_CASE_RE.fullmatch(relationship):
            raise EvidenceValidationError("external reference relationship must be kebab-case")
        domain = _enum(raw.get("domain"), EXTERNAL_EVIDENCE_DOMAIN_VALUES, "external reference domain")
        external_id = _required_string(raw, "id")
        key = (domain, external_id, relationship)
        if key in seen:
            raise EvidenceValidationError(
                f"duplicate external evidence reference: {domain} {external_id} {relationship}"
            )
        seen.add(key)
        references.append(
            CanonicalExternalEvidenceReference(
                domain=domain,
                id=external_id,
                relationship=relationship,
                notes=_string(raw.get("notes", ""), "external reference notes"),
            )
        )
    return references


def _reject_unknown_fields(value: Mapping[str, Any], allowed: set[str], *, label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise EvidenceValidationError(f"{label} contains unknown field(s): {', '.join(unknown)}")


def _required_string(value: Mapping[str, Any], field_name: str) -> str:
    result = _string(value.get(field_name), field_name).strip()
    if not result:
        raise EvidenceValidationError(f"{field_name} must be a non-empty string")
    return result


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{label} must be a string")
    return value.strip()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvidenceValidationError(f"{label} must be a list of strings")
    normalized = [item.strip() for item in value if item.strip()]
    return list(dict.fromkeys(normalized))


def _id_list(value: Any, label: str) -> list[str]:
    normalized = [normalize_id(item) for item in _string_list(value, label)]
    if any(not item or not _KEBAB_CASE_RE.fullmatch(item) for item in normalized):
        raise EvidenceValidationError(f"{label} must contain canonical kebab-case ids")
    return list(dict.fromkeys(normalized))


def _enum(value: Any, allowed: Sequence[str], label: str) -> str:
    normalized = _string(value, label)
    if normalized not in allowed:
        raise EvidenceValidationError(f"{label} must be one of: {', '.join(allowed)}")
    return normalized


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise EvidenceValidationError(f"{label} must be a boolean")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceValidationError(f"{label} must be an integer")
    return value


def _optional_year(value: Any, label: str) -> int | None:
    if value is None:
        return None
    year = _integer(value, label)
    if year == 0 or not -10000 <= year <= 3000:
        raise EvidenceValidationError(f"{label} must be a signed year from -10000 to 3000, excluding zero")
    return year


def _validate_year_range(start: int | None, end: int | None, label: str) -> None:
    if start is not None and end is not None and end < start:
        raise EvidenceValidationError(f"{label} end_year must not be earlier than start_year")
