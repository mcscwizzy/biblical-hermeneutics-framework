"""Read-only, passage-scoped Narrative Explorer projection contracts.

This module accepts records already retrieved by existing CKL, map, and
archaeology callers. It performs no I/O and never writes source records.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
import math
from typing import Any, Literal, Mapping, Sequence
from urllib.parse import quote, urlencode

from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_references,
)

from .eligibility import (
    _BOOK_ALIASES,
    is_canonical_object_passage_eligible,
    passage_matching_scripture_anchors,
)
from .models import mapping
from .references import references_overlap
from .relevance import SEMANTICALLY_MISANCHORED, classify_semantic_relationship


SCHEMA_VERSION = "1.0"

Domain = Literal["ckl", "maps", "archaeology"]
QueryStatus = Literal["complete", "partial", "failed", "not_run"]
CoverageState = Literal["available", "partial", "not_represented", "unknown"]

_SOURCE_DOMAIN = {
    "ckl": "canonical_knowledge_library",
    "maps": "passage_maps",
    "archaeology": "archaeology_passage_resolver",
}
_DOMAIN_ORDER: tuple[Domain, ...] = ("ckl", "maps", "archaeology")
_SECTION_DOMAINS: tuple[tuple[str, tuple[Domain, ...]], ...] = (
    ("biblical_narrative", ("ckl",)),
    ("archaeology_ancient_history", ("ckl", "archaeology")),
    ("biblical_geography", ("ckl", "maps")),
    ("divine_council_cosmic_geography", ("ckl",)),
    ("themes_biblical_connections", ("ckl",)),
    ("people_events_relationships", ("ckl",)),
)


@dataclass(frozen=True)
class DomainLookup:
    """Result of one caller-owned lookup; records are never mutated here."""

    domain: Domain
    records: Sequence[Any] = field(default_factory=tuple)
    query_status: Literal["complete", "partial", "failed", "not_run"] = "complete"
    reason_code: str | None = None
    missing_subdomains: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.domain not in _SOURCE_DOMAIN:
            raise ValueError(f"unsupported Narrative Explorer lookup domain: {self.domain}")
        if self.query_status not in {"complete", "partial", "failed", "not_run"}:
            raise ValueError(f"unsupported query status: {self.query_status}")
        records = self.records or ()
        if isinstance(records, (set, frozenset)):
            records = sorted(records, key=_stable_record_sort_key)
        object.__setattr__(self, "records", tuple(records))
        object.__setattr__(
            self,
            "missing_subdomains",
            tuple(str(value) for value in (self.missing_subdomains or ()) if str(value)),
        )
        normalized_reason = str(self.reason_code or "").strip()
        object.__setattr__(self, "reason_code", normalized_reason or None)


@dataclass(frozen=True)
class PassageProjection:
    reference: str
    book: str
    chapter: int
    verse_start: int | None
    verse_end: int | None
    scope: Literal["chapter", "verse", "verse_range"]

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DomainCoverage:
    domain: Domain
    source_domain: str
    state: CoverageState
    query_status: QueryStatus
    query_returned_count: int | None
    projected_item_count: int
    reason_code: str | None = None
    missing_subdomains: tuple[str, ...] = ()
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class ProjectionSection:
    id: str
    state: CoverageState
    item_ids: tuple[str, ...]
    source_domains: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class NavigationDestination:
    id: str
    kind: str
    target_id: str
    href: str

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class ProjectedSource:
    id: str
    details_available: bool
    bibliographic_details: Mapping[str, Any] | None = None
    unavailable_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "details_available": self.details_available,
        }
        if self.bibliographic_details:
            result["bibliographic_details"] = _jsonable(self.bibliographic_details)
        if self.unavailable_reason:
            result["unavailable_reason"] = self.unavailable_reason
        return result


@dataclass(frozen=True)
class ProjectedItem:
    id: str
    domain: str
    record_kind: str
    object_id: str | None
    parent_object_id: str | None
    local_id: str | None
    claim_id: str | None
    evidence_id: str | None
    object_type: str | None
    title: str | None
    claim_text: str | None
    description: str | None
    evidence_category: str | None
    claim_type: str | None
    assertion_type: str | None
    source_ids: tuple[str, ...]
    sources: tuple[ProjectedSource, ...]
    passage_anchors: tuple[Mapping[str, Any], ...]
    applicable_passage_anchors: tuple[Mapping[str, Any], ...]
    related_passages: tuple[str, ...]
    original_relationship_types: tuple[str, ...]
    confidence: Any = None
    certainty: Any = None
    dispute_status: Any = None
    interpretation_state: str = "unknown"
    review_status: Any = None
    content_status: Any = None
    human_review_required: Any = None
    temporal_relation: Any = None
    temporal_relations: tuple[Any, ...] = ()
    temporal_scope: Mapping[str, Any] | None = None
    rationale: Mapping[str, Any] = field(default_factory=dict)
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    geography_kind: str = "unknown"
    place_identification_confidence: Any = "unknown"
    stored_coordinates: Mapping[str, Any] | None = None
    coordinates_displayable: bool | None = None
    coordinate_display_reason: str | None = None
    stored_geometry: Mapping[str, Any] | None = None
    geometry_displayable: bool | None = None
    geometry_display_reason: str | None = None
    section_ids: tuple[str, ...] = ()
    navigation: NavigationDestination | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["sources"] = [source.to_dict() for source in self.sources]
        if self.navigation is not None:
            result["navigation"] = self.navigation.to_dict()
        return _jsonable(result)


@dataclass(frozen=True)
class ProjectionConnection:
    id: str
    source_id: str
    target_id: str
    connection_type: str
    original_relationship_type: str | None
    relationship_mode: str
    direction: str
    reverse_edge_id: str | None
    temporal_layer: str
    basis: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class NarrativeExplorerProjection:
    schema_version: str
    passage: PassageProjection
    coverage: tuple[DomainCoverage, ...]
    sections: tuple[ProjectionSection, ...]
    items: tuple[ProjectedItem, ...] = ()
    connections: tuple[ProjectionConnection, ...] = ()
    navigation: tuple[NavigationDestination, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "passage": self.passage.to_dict(),
            "coverage": [entry.to_dict() for entry in self.coverage],
            "sections": [entry.to_dict() for entry in self.sections],
            "items": [item.to_dict() for item in self.items],
            "connections": [edge.to_dict() for edge in self.connections],
            "navigation": [destination.to_dict() for destination in self.navigation],
        }
        validate_projection(result)
        return result


def project_narrative_explorer(
    passage_ref: str,
    *,
    canonical_lookup: DomainLookup,
    map_lookup: DomainLookup | None = None,
    archaeology_lookup: DomainLookup | None = None,
) -> NarrativeExplorerProjection:
    """Build a deterministic v1.0 envelope from supplied evidence lookups."""

    passage = _normalize_passage(passage_ref)
    lookups = {
        "ckl": _require_lookup(canonical_lookup, "ckl"),
        "maps": _optional_lookup(map_lookup, "maps"),
        "archaeology": _optional_lookup(archaeology_lookup, "archaeology"),
    }

    canonical_items, raw_connections = _project_ckl_lookup(passage, lookups["ckl"])
    map_items, map_connections = _project_external_lookup(passage, lookups["maps"])
    archaeology_items, archaeology_connections = _project_external_lookup(
        passage,
        lookups["archaeology"],
    )
    item_groups: dict[Domain, list[ProjectedItem]] = {
        "ckl": canonical_items,
        "maps": map_items,
        "archaeology": archaeology_items,
    }
    all_items = tuple(sorted(
        (item for domain in _DOMAIN_ORDER for item in item_groups[domain]),
        key=lambda item: item.id,
    ))
    coverage = tuple(
        _domain_coverage(domain, lookups[domain], len(item_groups[domain]))
        for domain in _DOMAIN_ORDER
    )
    coverage_by_domain = {entry.domain: entry for entry in coverage}
    section_items: dict[str, list[str]] = {section_id: [] for section_id, _domains in _SECTION_DOMAINS}
    for item in all_items:
        for section_id in item.section_ids:
            if section_id in section_items:
                section_items[section_id].append(item.id)
    sections = tuple(
        ProjectionSection(
            id=section_id,
            state=_section_state(
                section_items[section_id],
                (coverage_by_domain[domain] for domain in domains),
            ),
            item_ids=tuple(sorted(section_items[section_id])),
            source_domains=tuple(_SOURCE_DOMAIN[domain] for domain in domains),
            description=_section_description(
                section_id,
                _section_state(
                    section_items[section_id],
                    (coverage_by_domain[domain] for domain in domains),
                ),
                domains,
            ),
        )
        for section_id, domains in _SECTION_DOMAINS
    )
    connections = _reciprocal_edges(raw_connections + map_connections + archaeology_connections)
    navigation_by_id = {
        item.navigation.id: item.navigation
        for item in all_items
        if item.navigation is not None
    }
    passage_navigation = _passage_navigation(passage)
    navigation_by_id[passage_navigation.id] = passage_navigation
    return NarrativeExplorerProjection(
        schema_version=SCHEMA_VERSION,
        passage=passage,
        coverage=coverage,
        sections=sections,
        items=all_items,
        connections=connections,
        navigation=tuple(navigation_by_id[key] for key in sorted(navigation_by_id)),
    )


def validate_projection(value: Mapping[str, Any]) -> None:
    """Raise `ValueError` when the serialized envelope breaks its v1 contract."""

    required_keys = {
        "schema_version",
        "passage",
        "coverage",
        "sections",
        "items",
        "connections",
        "navigation",
    }
    if set(value) != required_keys:
        raise ValueError("Narrative Explorer projection has an invalid envelope")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported Narrative Explorer schema version")
    items = value.get("items")
    if not isinstance(items, list):
        raise ValueError("projection items must be a list")
    item_ids = [item.get("id") for item in items if isinstance(item, Mapping)]
    if len(item_ids) != len(items) or len(item_ids) != len(set(item_ids)):
        raise ValueError("projection item IDs must be present and unique")
    item_id_set = set(item_ids)
    for section in value.get("sections", []):
        if section.get("state") not in {"available", "partial", "not_represented", "unknown"}:
            raise ValueError("projection section has an invalid coverage state")
        if any(item_id not in item_id_set for item_id in section.get("item_ids", [])):
            raise ValueError("projection section references an unknown item")
    for entry in value.get("coverage", []):
        if entry.get("state") not in {"available", "partial", "not_represented", "unknown"}:
            raise ValueError("projection coverage has an invalid state")
        if entry.get("query_status") not in {"complete", "partial", "failed", "not_run"}:
            raise ValueError("projection coverage has an invalid query status")
    for item in items:
        if item.get("domain") not in _SOURCE_DOMAIN:
            raise ValueError("projection item has an invalid source domain")
        if item.get("geography_kind") not in _GEOGRAPHY_KINDS:
            raise ValueError("projection item has an invalid geography kind")
        if item.get("coordinates_displayable") is True:
            coordinates = item.get("stored_coordinates")
            if item.get("geography_kind") not in _PHYSICAL_GEOGRAPHY_KINDS or not _coordinates_are_valid(coordinates):
                raise ValueError("projection exposes unsupported physical coordinates")
        if item.get("geometry_displayable") is True:
            geometry = item.get("stored_geometry")
            if item.get("geography_kind") not in _PHYSICAL_GEOGRAPHY_KINDS or not _geometry_coordinates_are_valid(geometry):
                raise ValueError("projection exposes unsupported physical geometry")
    connection_types = {
        "direct_quotation",
        "explicit_textual_reference",
        "shared_literary_motif",
        "narrative_parallel",
        "thematic_relationship",
        "later_canonical_reception",
        "proposed_intertextual_echo",
        "interpretive_association",
        "uncategorized",
    }
    connection_ids: set[str] = set()
    for connection in value.get("connections", []):
        if connection.get("connection_type") not in connection_types:
            raise ValueError("projection connection has an invalid type")
        if connection.get("direction") not in {"one_way", "reciprocal"}:
            raise ValueError("projection connection has an invalid direction")
        if connection.get("direction") == "one_way" and connection.get("reverse_edge_id") is not None:
            raise ValueError("one-way connection cannot reference a reverse edge")
        if not connection.get("id") or connection["id"] in connection_ids:
            raise ValueError("projection connection IDs must be present and unique")
        connection_ids.add(connection["id"])


_CONNECTION_TYPE_BY_LABEL = {
    "direct-quotation": "direct_quotation",
    "direct_quotation": "direct_quotation",
    "quotation": "direct_quotation",
    "quotes": "direct_quotation",
    "explicit-textual-reference": "explicit_textual_reference",
    "explicit_textual_reference": "explicit_textual_reference",
    "textual-reference": "explicit_textual_reference",
    "shared-literary-motif": "shared_literary_motif",
    "shared_literary_motif": "shared_literary_motif",
    "narrative-parallel": "narrative_parallel",
    "narrative_parallel": "narrative_parallel",
    "thematic-relationship": "thematic_relationship",
    "thematic_relationship": "thematic_relationship",
    "later-canonical-reception": "later_canonical_reception",
    "later_canonical_reception": "later_canonical_reception",
    "proposed-intertextual-echo": "proposed_intertextual_echo",
    "proposed_intertextual_echo": "proposed_intertextual_echo",
    "allusion": "proposed_intertextual_echo",
    "interpretive-association": "interpretive_association",
    "interpretive_association": "interpretive_association",
}


def _project_ckl_lookup(
    passage: PassageProjection,
    lookup: DomainLookup,
) -> tuple[list[ProjectedItem], list[ProjectionConnection]]:
    items_by_id: dict[str, ProjectedItem] = {}
    connections_by_id: dict[str, ProjectionConnection] = {}
    parent_items: dict[str, ProjectedItem] = {}
    child_section_ids: dict[str, set[str]] = {}
    eligible_claim_ids: dict[str, set[str]] = {}
    eligible_evidence_ids: dict[str, set[str]] = {}

    for candidate in lookup.records:
        raw_object = getattr(candidate, "object", candidate)
        parent = mapping(raw_object)
        parent_id = _text(parent.get("id"))
        if not parent_id:
            continue
        parent_type = _text(parent.get("type"))
        parent_anchors = _anchor_entries(parent.get("scripture_references"))
        eligible_parent_anchors = _eligible_anchor_entries(
            passage.reference,
            parent,
            parent_anchors,
            source_kind="ckl_legacy_field",
        )
        parent_item: ProjectedItem | None = None
        if eligible_parent_anchors:
            parent_item = _make_ckl_item(
                parent_id=parent_id,
                parent=parent,
                record=parent,
                record_kind="object",
                local_id=None,
                original_anchors=parent_anchors,
                applicable_anchors=eligible_parent_anchors,
                source_index=_source_index(parent),
                section_ids=_object_sections(parent_type),
            )
            _add_unique_item(items_by_id, parent_item)
            parent_items[parent_id] = parent_item
            child_section_ids[parent_id] = set(parent_item.section_ids)
            eligible_claim_ids[parent_id] = set()
            eligible_evidence_ids[parent_id] = set()
            for anchor in eligible_parent_anchors:
                _add_connection(
                    connections_by_id,
                    _passage_connection(
                        source_id=parent_item.id,
                        parent_id=parent_id,
                        local_id=None,
                        anchor=anchor,
                    ),
                )
            # Book records have intentionally broad relationship inventories.
            # Their child claims remain eligible by their own anchors, while
            # unscoped book-level related_objects are not promoted to edges.
            if parent_type.casefold() != "book":
                for relation in _sequence(parent.get("related_objects")):
                    _add_connection(
                        connections_by_id,
                        _related_object_connection(
                            source_id=parent_item.id,
                            parent_id=parent_id,
                            local_id=None,
                            relation=relation,
                            assertion_type=None,
                        ),
                    )

        source_index = _source_index(parent)
        for collection_name, record_kind in (
            ("claims", "claim"),
            ("evidence_items", "evidence"),
            ("interpretive_notes", "interpretive_note"),
        ):
            for raw_child in _sequence(parent.get(collection_name)):
                child = mapping(raw_child)
                child_anchors = _anchor_entries(child.get("scripture_references"))
                applicable_anchors = _eligible_anchor_entries(
                    passage.reference,
                    parent,
                    child_anchors,
                    source_kind={
                        "claim": "ckl_claim",
                        "evidence": "ckl_evidence_item",
                        "interpretive_note": "ckl_interpretive_note",
                    }[record_kind],
                )
                if not applicable_anchors:
                    continue
                local_id = _child_local_id(record_kind, child)
                stable_id = _ckl_stable_id(parent_id, record_kind, local_id)
                sections = _child_sections(record_kind, parent_type, child)
                item = _make_ckl_item(
                    parent_id=parent_id,
                    parent=parent,
                    record=child,
                    record_kind=record_kind,
                    local_id=local_id,
                    original_anchors=child_anchors,
                    applicable_anchors=applicable_anchors,
                    source_index=source_index,
                    section_ids=sections,
                    stable_id=stable_id,
                )
                _add_unique_item(items_by_id, item)
                child_section_ids.setdefault(parent_id, set()).update(sections)
                if record_kind == "claim":
                    eligible_claim_ids.setdefault(parent_id, set()).add(local_id)
                elif record_kind == "evidence":
                    eligible_evidence_ids.setdefault(parent_id, set()).add(local_id)

                for anchor in applicable_anchors:
                    _add_connection(
                        connections_by_id,
                        _passage_connection(
                            source_id=item.id,
                            parent_id=parent_id,
                            local_id=local_id,
                            anchor=anchor,
                        ),
                    )
                for relation in _sequence(child.get("related_objects")):
                    _add_connection(
                        connections_by_id,
                        _related_object_connection(
                            source_id=item.id,
                            parent_id=parent_id,
                            local_id=local_id,
                            relation=relation,
                            assertion_type=child.get("assertion_type"),
                        ),
                    )
                for relation in _sequence(child.get("related_evidence")):
                    _add_connection(
                        connections_by_id,
                        _related_evidence_connection(
                            source_id=item.id,
                            parent_id=parent_id,
                            local_id=local_id,
                            relation=relation,
                            assertion_type=child.get("assertion_type"),
                        ),
                    )

    # Bind claim -> evidence only when both child records independently pass
    # passage eligibility. A typed claim_ids edge is an explicit source path.
    for candidate in lookup.records:
        parent = mapping(getattr(candidate, "object", candidate))
        parent_id = _text(parent.get("id"))
        if not parent_id:
            continue
        for raw_evidence in _sequence(parent.get("evidence_items")):
            evidence = mapping(raw_evidence)
            evidence_id = _child_local_id("evidence", evidence)
            evidence_stable_id = _ckl_stable_id(parent_id, "evidence", evidence_id)
            if evidence_id not in eligible_evidence_ids.get(parent_id, set()):
                continue
            evidence_item = items_by_id.get(evidence_stable_id)
            for claim_id in _string_values(evidence.get("claim_ids")):
                claim_stable_id = _ckl_stable_id(parent_id, "claim", claim_id)
                if claim_id not in eligible_claim_ids.get(parent_id, set()):
                    continue
                claim_item = items_by_id.get(claim_stable_id)
                if claim_item is not None and evidence_item is not None:
                    merged_sections = tuple(
                        sorted(set(claim_item.section_ids) | set(evidence_item.section_ids))
                    )
                    items_by_id[claim_stable_id] = replace(
                        claim_item,
                        section_ids=merged_sections,
                    )
                    child_section_ids.setdefault(parent_id, set()).update(merged_sections)
                _add_connection(
                    connections_by_id,
                    _new_connection(
                        source_id=claim_stable_id,
                        target_id=evidence_stable_id,
                        relationship="supports-evidence",
                        relationship_mode="direct",
                        temporal_layer="unknown",
                        basis={
                            "kind": "ckl_evidence_claim_ids",
                            "parent_object_id": parent_id,
                            "claim_id": claim_id,
                            "evidence_id": evidence_id,
                        },
                    ),
                )

    # A parent subject can appear in each section supported by its eligible
    # children, without changing its original CKL object type.
    for parent_id, parent_item in tuple(parent_items.items()):
        sections = tuple(sorted(child_section_ids.get(parent_id, set())))
        if sections != parent_item.section_ids:
            items_by_id[parent_item.id] = replace(parent_item, section_ids=sections)

    # A local evidence edge is only navigable when its target independently
    # passed the same passage filter; a scoped source item cannot pull an
    # unrelated sibling into this projection.
    connections_by_id = {
        connection_id: connection
        for connection_id, connection in connections_by_id.items()
        if connection.basis.get("kind") != "ckl_related_evidence"
        or _text(connection.basis.get("target_evidence_id"))
        in eligible_evidence_ids.get(_text(connection.basis.get("parent_object_id")), set())
    }

    return (
        [items_by_id[key] for key in sorted(items_by_id)],
        [connections_by_id[key] for key in sorted(connections_by_id)],
    )


def _project_external_lookup(
    passage: PassageProjection,
    lookup: DomainLookup,
) -> tuple[list[ProjectedItem], list[ProjectionConnection]]:
    """Project map or archaeology records that were already retrieved."""

    items: dict[str, ProjectedItem] = {}
    connections: dict[str, ProjectionConnection] = {}
    for candidate in _unwrap_external_records(lookup.domain, lookup.records):
        record = mapping(candidate)
        original_id = _text(record.get("id"))
        if not original_id:
            continue
        anchors = _external_anchor_entries(record, lookup.domain)
        parent = {
            "id": original_id,
            "type": _external_object_type(record, lookup.domain),
            "title": _first_record_text(record, "title", "name"),
        }
        applicable = _eligible_anchor_entries(
            passage.reference,
            parent,
            anchors,
            source_kind=f"{lookup.domain}_record",
        )
        if not applicable:
            continue

        stable_id = f"{lookup.domain}:{original_id}"
        source_ids, source_index = _external_source_index(record)
        source_data = _external_source_metadata(record, lookup.domain)
        geography_kind = _geography_kind(record, lookup.domain)
        stored_coordinates = _stored_coordinates(record)
        stored_geometry = _stored_geometry(record)
        coordinates_displayable, coordinate_reason = _coordinate_displayability(
            record,
            geography_kind,
            stored_coordinates,
        )
        geometry_displayable, geometry_reason = _geometry_displayability(
            record,
            geography_kind,
            stored_geometry,
        )
        source_records = tuple(
            _project_external_source(source_id, source_index)
            for source_id in source_ids
        )
        title = _first_record_text(record, "title", "name")
        description = _first_record_text(record, "description", "summary")
        claim_text = _first_record_text(
            record,
            "claim",
            "biblical_relevance",
            "significance",
            "summary",
            "description",
        )
        temporal_relations = tuple(
            deepcopy(anchor["temporal_relation"])
            for anchor in applicable
            if anchor.get("temporal_relation") not in (None, "")
        )
        temporal_relation = record.get("temporal_relation")
        if temporal_relation in (None, "") and len(temporal_relations) == 1:
            temporal_relation = temporal_relations[0]
        item = ProjectedItem(
            id=stable_id,
            domain=lookup.domain,
            record_kind=_external_record_kind(record, lookup.domain),
            object_id=original_id,
            parent_object_id=_optional_text(
                record.get("parent_object_id") or record.get("site_id") or record.get("layer_id")
            ),
            local_id=None,
            claim_id=None,
            evidence_id=None,
            object_type=_external_object_type(record, lookup.domain),
            title=title,
            claim_text=claim_text,
            description=description,
            evidence_category=_first_record_text(
                record,
                "evidence_category",
                "evidence_type",
                "item_type",
                "marker_kind",
            ),
            claim_type=_optional_text(record.get("claim_type")),
            assertion_type=_optional_text(record.get("assertion_type")),
            source_ids=source_ids,
            sources=source_records,
            passage_anchors=tuple(deepcopy(dict(anchor)) for anchor in anchors),
            applicable_passage_anchors=tuple(
                deepcopy(dict(anchor)) for anchor in applicable
            ),
            related_passages=tuple(_text(anchor.get("reference")) for anchor in applicable),
            original_relationship_types=tuple(
                relationship
                for relationship in (_optional_text(anchor.get("relationship")) for anchor in anchors)
                if relationship
            ),
            confidence=deepcopy(record.get("confidence")),
            certainty=deepcopy(record.get("certainty")),
            dispute_status=deepcopy(record.get("dispute_status")),
            interpretation_state=_interpretation_state(record),
            review_status=deepcopy(record.get("review_status")),
            content_status=deepcopy(record.get("content_status")),
            human_review_required=deepcopy(record.get("human_review_required")),
            temporal_relation=deepcopy(temporal_relation),
            temporal_relations=temporal_relations,
            temporal_scope=deepcopy(record.get("temporal_scope")),
            rationale=_external_rationale(record),
            source_metadata=source_data,
            geography_kind=geography_kind,
            place_identification_confidence=deepcopy(
                record.get("place_identification_confidence", record.get("identification_confidence", "unknown"))
            ),
            stored_coordinates=stored_coordinates,
            coordinates_displayable=coordinates_displayable,
            coordinate_display_reason=coordinate_reason,
            stored_geometry=stored_geometry,
            geometry_displayable=geometry_displayable,
            geometry_display_reason=geometry_reason,
            section_ids=_external_sections(lookup.domain, record, geography_kind),
            navigation=_external_navigation(lookup.domain, record, original_id),
        )
        existing = items.get(item.id)
        if existing is not None and existing != item:
            raise ValueError(f"conflicting {lookup.domain} records share stable ID {item.id}")
        items[item.id] = item

        for anchor in applicable:
            relationship = _optional_text(anchor.get("relationship"))
            _add_connection(
                connections,
                _new_connection(
                    source_id=item.id,
                    target_id=f"passage:{_text(anchor.get('reference'))}",
                    relationship=relationship,
                    relationship_mode="direct",
                    temporal_layer=_temporal_layer(
                        relationship or "",
                        _text(anchor.get("temporal_relation")),
                    ),
                    basis={
                        "kind": f"{lookup.domain}_scripture_anchor",
                        "record_id": original_id,
                        "reference": _text(anchor.get("reference")),
                        "anchor_metadata": deepcopy(dict(anchor)),
                    },
                ),
            )

    return [items[key] for key in sorted(items)], [connections[key] for key in sorted(connections)]


def _unwrap_external_records(domain: Domain, records: Sequence[Any]) -> tuple[Any, ...]:
    """Accept the item arrays used by existing map and archaeology resolvers."""

    collection_keys = {
        "maps": ("markers", "places", "routes", "layers", "items"),
        "archaeology": ("archaeological_items", "markers", "items"),
    }[domain]
    if len(records) == 1:
        wrapper = mapping(records[0])
        if not _text(wrapper.get("id")):
            for key in collection_keys:
                values = wrapper.get(key)
                if isinstance(values, (list, tuple)):
                    return tuple(values)
    return tuple(records)


def _external_anchor_entries(record: Mapping[str, Any], domain: Domain) -> list[Mapping[str, Any]]:
    keys = (
        ("scripture_links", "related_references", "scripture_references", "passage_anchors")
        if domain == "maps"
        else ("scripture_links", "scripture_references", "passage_anchors")
    )
    result: list[Mapping[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for key in keys:
        for raw in _sequence(record.get(key)):
            data = mapping(raw)
            raw_reference = _external_reference_text(data) if data else _text(raw)
            if not raw_reference:
                continue
            parsed = parse_scripture_references(raw_reference, book_alias_lookup=_BOOK_ALIASES)
            if not parsed:
                continue
            for span in parsed:
                reference = format_scripture_reference(span)
                relationship = _optional_text(
                    data.get("relationship")
                    or data.get("relationship_type")
                    or (record.get("biblical_relationship") if domain == "archaeology" else None)
                )
                signature = (reference, relationship or "")
                if signature in seen:
                    continue
                anchor: dict[str, Any] = {
                    "reference": reference,
                    "source_field": key,
                    "source_anchor": deepcopy(dict(data) if data else raw),
                }
                if relationship:
                    anchor["relationship"] = relationship
                if data:
                    temporal = data.get("temporal_relation")
                    if temporal not in (None, ""):
                        anchor["temporal_relation"] = deepcopy(temporal)
                    notes = data.get("notes") or data.get("relationship_notes")
                    if notes not in (None, ""):
                        anchor["notes"] = deepcopy(notes)
                    for metadata_key in ("weight", "relevance_rationale", "confidence"):
                        if data.get(metadata_key) not in (None, ""):
                            anchor[metadata_key] = deepcopy(data[metadata_key])
                seen.add(signature)
                result.append(anchor)
    return result


def _external_reference_text(anchor: Mapping[str, Any]) -> str:
    reference = _text(anchor.get("reference") or anchor.get("scripture_reference"))
    if reference:
        return reference
    book = _text(anchor.get("book"))
    chapter = _text(anchor.get("chapter"))
    if not book or not chapter:
        return ""
    result = f"{book} {chapter}"
    start = anchor.get("verse_start")
    end = anchor.get("verse_end")
    if start not in (None, "") and end not in (None, ""):
        result += f":{start}-{end}" if str(start) != str(end) else f":{start}"
    elif start not in (None, ""):
        result += f":{start}"
    elif end not in (None, ""):
        result += f":{end}"
    return result


def _external_object_type(record: Mapping[str, Any], domain: Domain) -> str:
    if domain == "maps":
        return _text(record.get("object_type") or record.get("marker_kind") or record.get("type") or record.get("layer_type"))
    return _text(record.get("object_type") or record.get("item_type") or record.get("type") or "archaeology")


def _external_record_kind(record: Mapping[str, Any], domain: Domain) -> str:
    if domain == "archaeology":
        return "archaeology_item"
    marker_kind = _text(record.get("marker_kind") or record.get("type")).casefold().replace("-", "_")
    if marker_kind in {"place", "physical_place"}:
        return "map_place"
    if marker_kind in {"route", "map_route"}:
        return "map_route"
    if marker_kind in {"manuscript", "map_manuscript"}:
        return "map_manuscript"
    return "map_record"


_GEOGRAPHY_KINDS = {
    "physical_place",
    "physical_region",
    "political_territory",
    "route",
    "archaeological_site",
    "cosmic_textual",
    "sacred_space",
    "literary_space",
    "symbolic_geography",
    "unknown",
}
_PHYSICAL_GEOGRAPHY_KINDS = {
    "physical_place",
    "physical_region",
    "political_territory",
    "route",
    "archaeological_site",
}


def _geography_kind(record: Mapping[str, Any], domain: Domain) -> str:
    metadata = mapping(record.get("metadata"))
    explicit = _text(record.get("geography_kind") or metadata.get("geography_kind")).casefold().replace("-", "_")
    if explicit in _GEOGRAPHY_KINDS:
        return explicit
    if domain == "maps":
        marker_kind = _text(record.get("marker_kind") or record.get("type")).casefold().replace("-", "_")
        if marker_kind in {"place", "physical_place"}:
            return "physical_place"
        if marker_kind in {"route", "map_route"}:
            return "route"
        if marker_kind in {"archaeology", "archaeological_site", "site"}:
            return "archaeological_site"
        if marker_kind in {"historical_layer", "political_context"}:
            return "political_territory" if marker_kind == "political_context" else "unknown"
    if domain == "archaeology":
        item_type = _text(record.get("item_type") or record.get("evidence_category")).casefold().replace("-", "_")
        if item_type in {"site", "archaeological_site"}:
            return "archaeological_site"
    return "unknown"


def _stored_coordinates(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    coordinates = mapping(record.get("coordinates"))
    raw: dict[str, Any] = {}
    for key in ("latitude", "longitude"):
        value = record.get(key, coordinates.get(key))
        if value is not None:
            raw[key] = deepcopy(value)
    return raw or None


def _stored_geometry(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    geojson = mapping(record.get("geojson"))
    geometry = geojson.get("geometry", record.get("geometry"))
    data = mapping(geometry)
    return deepcopy(data) if data else None


def _coordinate_displayability(
    record: Mapping[str, Any],
    geography_kind: str,
    stored_coordinates: Mapping[str, Any] | None,
) -> tuple[bool | None, str | None]:
    if not stored_coordinates:
        return None, None
    if geography_kind not in _PHYSICAL_GEOGRAPHY_KINDS:
        return False, "conceptual_geography_has_no_physical_marker"
    if set(stored_coordinates) != {"latitude", "longitude"}:
        return False, "incomplete_coordinate_pair"
    if not _coordinates_are_valid(stored_coordinates):
        return False, "invalid_stored_coordinates"
    identification = _text(
        record.get("physical_identification_status")
        or record.get("place_identification_status")
        or record.get("identification_status")
    ).casefold().replace("-", "_")
    dispute = _text(record.get("dispute_status")).casefold().replace("-", "_")
    if dispute and dispute not in {"not_disputed", "none", "unknown"}:
        return False, "place_identification_disputed"
    if identification not in {"established", "verified", "identified"}:
        return False, "physical_identification_not_established"
    confidence = _text(
        record.get("place_identification_confidence")
        or record.get("identification_confidence")
    ).casefold().replace("-", "_")
    if confidence != "high":
        return False, "place_identification_confidence_insufficient"
    return True, None


def _geometry_displayability(
    record: Mapping[str, Any],
    geography_kind: str,
    stored_geometry: Mapping[str, Any] | None,
) -> tuple[bool | None, str | None]:
    if not stored_geometry:
        return None, None
    if geography_kind not in _PHYSICAL_GEOGRAPHY_KINDS:
        return False, "conceptual_geography_has_no_physical_geometry"
    identification = _text(
        record.get("physical_identification_status")
        or record.get("place_identification_status")
        or record.get("identification_status")
        or record.get("route_identification_status")
    ).casefold().replace("-", "_")
    dispute = _text(record.get("dispute_status")).casefold().replace("-", "_")
    if dispute and dispute not in {"not_disputed", "none", "unknown"}:
        return False, "geographic_identification_disputed"
    if identification not in {"established", "verified", "identified"}:
        return False, "geographic_identification_not_established"
    if not _geometry_coordinates_are_valid(stored_geometry):
        return False, "invalid_stored_geometry"
    return True, None


def _coordinates_are_valid(coordinates: Any) -> bool:
    data = mapping(coordinates)
    if set(data) != {"latitude", "longitude"}:
        return False
    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _geometry_coordinates_are_valid(geometry: Any) -> bool:
    data = mapping(geometry)
    geometry_type = _text(data.get("type"))
    if geometry_type not in {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}:
        return False
    coordinates = data.get("coordinates")
    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        return False
    pairs = list(_coordinate_pairs(coordinates))
    return bool(pairs) and all(_coordinate_pair_is_valid(pair) for pair in pairs)


def _coordinate_pairs(value: Any) -> Any:
    if not isinstance(value, (list, tuple)):
        return
    if len(value) >= 2 and not isinstance(value[0], (list, tuple)):
        yield value
        return
    for child in value:
        yield from _coordinate_pairs(child)


def _coordinate_pair_is_valid(value: Sequence[Any]) -> bool:
    if len(value) < 2:
        return False
    try:
        longitude = float(value[0])
        latitude = float(value[1])
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _external_source_index(
    record: Mapping[str, Any],
) -> tuple[tuple[str, ...], dict[str, Mapping[str, Any]]]:
    sources: dict[str, Mapping[str, Any]] = {}
    for raw_source in _sequence(record.get("sources")):
        source = mapping(raw_source)
        source_id = _text(source.get("id"))
        if source_id:
            sources[source_id] = source
    raw_primary_source = record.get("source")
    primary = mapping(raw_primary_source)
    if primary and _text(primary.get("id")):
        sources.setdefault(_text(primary.get("id")), primary)
    source_ids: list[str] = []
    for value in _sequence(record.get("source_ids")):
        source_id = _text(value.get("id")) if isinstance(value, Mapping) else _text(value)
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)
    for value in (record.get("source_id"), primary.get("id")):
        source_id = _text(value)
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)
    top_level_source_id = _text(record.get("source_id"))
    if top_level_source_id:
        fallback = dict(sources.get(top_level_source_id, {}))
        for key, value in primary.items():
            fallback.setdefault(key, deepcopy(value))
        fallback.setdefault("id", top_level_source_id)
        for source_key in ("source_name", "source_url", "license", "notes"):
            if record.get(source_key) not in (None, ""):
                fallback.setdefault(source_key, deepcopy(record[source_key]))
        sources[top_level_source_id] = fallback
    return tuple(source_ids), sources


def _project_external_source(
    source_id: str,
    source_index: Mapping[str, Mapping[str, Any]],
) -> ProjectedSource:
    source = source_index.get(source_id)
    if source is None:
        return ProjectedSource(
            id=source_id,
            details_available=False,
            unavailable_reason="source_details_unavailable_in_supplied_record",
        )
    fields = (
        "title",
        "author",
        "publisher",
        "year",
        "locator",
        "url",
        "source_type",
        "supports",
        "notes",
        "label",
        "license",
        "source_name",
        "source_url",
    )
    details = {
        key: deepcopy(source[key])
        for key in fields
        if key in source and source[key] not in (None, "", [])
    }
    if not details:
        return ProjectedSource(
            id=source_id,
            details_available=False,
            unavailable_reason="source_details_unavailable_in_supplied_record",
        )
    return ProjectedSource(id=source_id, details_available=True, bibliographic_details=details)


def _external_source_metadata(record: Mapping[str, Any], domain: Domain) -> dict[str, Any]:
    keys = (
        "marker_kind",
        "period",
        "periods",
        "route_type",
        "layer_type",
        "entity_type",
        "ancient_region",
        "modern_location",
        "region",
        "site_id",
        "site_name",
        "item_type",
        "date_display",
        "biblical_relationship",
        "relationship",
        "relationship_notes",
        "source_name",
        "source_url",
        "license",
        "source",
        "source_id",
        "source_ids",
        "evidence_sources",
        "external_references",
        "confidence_rank",
        "geography_kind",
        "physical_identification_status",
        "place_identification_status",
        "identification_status",
        "place_identification_confidence",
        "identification_confidence",
    )
    result: dict[str, Any] = {"record_kind": _external_record_kind(record, domain)}
    for key in keys:
        if key in record and record[key] not in (None, "", []):
            result[key] = deepcopy(record[key])
    return result


def _external_rationale(record: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "rationale",
        "notes",
        "caution",
        "bhf_caution",
        "interpretive_caution",
        "biblical_relevance",
        "significance",
        "evidence_summary",
        "discovery_context",
        "dating_basis",
        "physical_description",
        "confidence_rationale",
    )
    return {
        key: deepcopy(record[key])
        for key in keys
        if key in record and record[key] not in (None, "", [])
    }


def _external_sections(domain: Domain, record: Mapping[str, Any], geography_kind: str) -> tuple[str, ...]:
    if domain == "archaeology":
        return ("archaeology_ancient_history",)
    if geography_kind != "unknown":
        return ("biblical_geography",)
    marker_kind = _text(record.get("marker_kind") or record.get("type")).casefold().replace("-", "_")
    if marker_kind in {"manuscript", "historical_layer", "political_context"}:
        return ("archaeology_ancient_history",)
    return ()


def _external_navigation(domain: Domain, record: Mapping[str, Any], item_id: str) -> NavigationDestination:
    quoted_id = quote(item_id, safe="-._~")
    if domain == "archaeology":
        kind, href = "archaeology_item", f"/api/archaeology/items/{quoted_id}"
    else:
        record_kind = _external_record_kind(record, domain)
        if record_kind == "map_route":
            kind, href = "map_route", f"/api/maps/routes/{quoted_id}.kml"
        elif record_kind == "map_place":
            kind, href = "map_place", "/api/maps/biblical-places"
        elif record_kind == "map_manuscript":
            kind, href = "map_manuscript", "/api/maps/manuscripts"
        else:
            kind, href = "map_record", "/api/maps/catalog"
    return NavigationDestination(
        id=f"navigation:{domain}:{item_id}",
        kind=kind,
        target_id=item_id,
        href=href,
    )


def _stable_record_sort_key(value: Any) -> str:
    data = mapping(value)
    if not data:
        return str(value)
    return json.dumps(_jsonable(data), ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _eligible_anchor_entries(
    passage_ref: str,
    parent: Mapping[str, Any],
    anchors: Sequence[Mapping[str, Any]],
    *,
    source_kind: str,
) -> list[Mapping[str, Any]]:
    if not anchors:
        return []
    probe = dict(parent)
    probe["scripture_references"] = [deepcopy(dict(anchor)) for anchor in anchors]
    if not is_canonical_object_passage_eligible(passage_ref, probe):
        return []
    matching = passage_matching_scripture_anchors(passage_ref, probe)
    eligible: list[Mapping[str, Any]] = []
    for anchor in anchors:
        reference = _text(anchor.get("reference"))
        if not reference or not any(references_overlap(passage_ref, value) for value in matching):
            continue
        if not references_overlap(passage_ref, reference):
            continue
        semantic = classify_semantic_relationship(
            passage_ref,
            anchors=[reference],
            metadata={
                "parent_object_id": _text(parent.get("id")),
                "parent_type": _text(parent.get("type")),
                "parent_title": _text(parent.get("title")),
                "source_kind": source_kind,
                "passage_relationship": _text(anchor.get("relationship")) or "contextual",
            },
        )
        if semantic != SEMANTICALLY_MISANCHORED:
            eligible.append(anchor)
    return eligible


def _make_ckl_item(
    *,
    parent_id: str,
    parent: Mapping[str, Any],
    record: Mapping[str, Any],
    record_kind: str,
    local_id: str | None,
    original_anchors: Sequence[Mapping[str, Any]],
    applicable_anchors: Sequence[Mapping[str, Any]],
    source_index: Mapping[str, Mapping[str, Any]],
    section_ids: Sequence[str],
    stable_id: str | None = None,
) -> ProjectedItem:
    parent_type = _text(parent.get("type")) or None
    title = _optional_text(record.get("title"))
    if record_kind == "object":
        title = _optional_text(parent.get("title"))
    claim_text = _first_record_text(record, "claim", "description", "note")
    if record_kind == "object":
        claim_text = None
    description = _optional_text(record.get("description"))
    if record_kind == "evidence" and not claim_text:
        claim_text = description
    source_ids = _source_ids(record)
    if record_kind == "object" and not source_ids:
        source_ids = _source_ids(parent, include_object_sources=True)
    sources = tuple(
        _project_source(source_id, source_index)
        for source_id in source_ids
    )
    matching_refs = tuple(_text(anchor.get("reference")) for anchor in applicable_anchors)
    rel_types = tuple(
        _text(anchor.get("relationship"))
        for anchor in original_anchors
        if _text(anchor.get("relationship"))
    )
    temporal_values = tuple(
        deepcopy(anchor["temporal_relation"])
        for anchor in applicable_anchors
        if anchor.get("temporal_relation") not in (None, "")
    )
    temporal_relation = record.get("temporal_relation")
    if temporal_relation in (None, "") and len(temporal_values) == 1:
        temporal_relation = temporal_values[0]
    rationale = _rationale(record)
    source_metadata = _source_metadata(parent, record, record_kind)
    object_id_value: str | None = parent_id
    child_id = local_id
    item_stable_id = stable_id or _ckl_stable_id(parent_id, record_kind, child_id)
    temporal_scope = record.get("temporal_scope", parent.get("temporal_scope"))
    if temporal_scope is not None:
        temporal_scope = deepcopy(mapping(temporal_scope) or temporal_scope)
    return ProjectedItem(
        id=item_stable_id,
        domain="ckl",
        record_kind=record_kind,
        object_id=object_id_value,
        parent_object_id=parent_id if record_kind != "object" else None,
        local_id=child_id,
        claim_id=child_id if record_kind == "claim" else None,
        evidence_id=child_id if record_kind == "evidence" else None,
        object_type=parent_type,
        title=title,
        claim_text=claim_text,
        description=description,
        evidence_category=_optional_text(record.get("evidence_type")),
        claim_type=_optional_text(record.get("claim_type")),
        assertion_type=_optional_text(record.get("assertion_type")),
        source_ids=source_ids,
        sources=sources,
        passage_anchors=tuple(deepcopy(dict(anchor)) for anchor in original_anchors),
        applicable_passage_anchors=tuple(
            deepcopy(dict(anchor)) for anchor in applicable_anchors
        ),
        related_passages=matching_refs,
        original_relationship_types=rel_types,
        confidence=deepcopy(record.get("confidence")),
        certainty=deepcopy(record.get("certainty")),
        dispute_status=deepcopy(record.get("dispute_status")),
        interpretation_state=_interpretation_state(record),
        review_status=deepcopy(record.get("review_status", parent.get("review_status"))),
        content_status=deepcopy(record.get("content_status", parent.get("content_status"))),
        human_review_required=deepcopy(
            record.get("human_review_required", parent.get("human_review_required"))
        ),
        temporal_relation=deepcopy(temporal_relation),
        temporal_relations=temporal_values,
        temporal_scope=deepcopy(temporal_scope),
        rationale=rationale,
        source_metadata=source_metadata,
        geography_kind=_geography_kind(record, "ckl"),
        place_identification_confidence=deepcopy(
            record.get(
                "place_identification_confidence",
                record.get("identification_confidence", mapping(record.get("metadata")).get("identification_confidence", "unknown")),
            )
        ),
        section_ids=tuple(sorted(set(section_ids))),
        navigation=_ckl_navigation(parent_id),
    )


def _source_index(parent: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for raw_source in _sequence(parent.get("sources")):
        source = mapping(raw_source)
        source_id = _text(source.get("id"))
        if source_id:
            indexed[source_id] = source
    return indexed


def _project_source(
    source_id: str,
    source_index: Mapping[str, Mapping[str, Any]],
) -> ProjectedSource:
    source = source_index.get(source_id)
    if source is None:
        return ProjectedSource(
            id=source_id,
            details_available=False,
            unavailable_reason="source_not_found_in_ckl",
        )
    bibliographic_fields = (
        "title",
        "author",
        "publisher",
        "year",
        "locator",
        "url",
        "source_type",
        "supports",
        "notes",
    )
    details = {
        key: deepcopy(source[key])
        for key in bibliographic_fields
        if key in source and source[key] not in (None, "", [])
    }
    return ProjectedSource(
        id=source_id,
        details_available=True,
        bibliographic_details=details or None,
    )


def _source_ids(record: Mapping[str, Any], *, include_object_sources: bool = False) -> tuple[str, ...]:
    raw_values = record.get("source_ids")
    if raw_values is None and "sources" in record and not include_object_sources:
        raw_values = record.get("sources")
    if include_object_sources:
        raw_values = record.get("sources") or record.get("source_ids")
    values: list[str] = []
    for value in _sequence(raw_values):
        if isinstance(value, Mapping):
            source_id = _text(value.get("id"))
        else:
            source_id = _text(value)
        if source_id and source_id not in values:
            values.append(source_id)
    return tuple(values)


def _source_metadata(
    parent: Mapping[str, Any],
    record: Mapping[str, Any],
    record_kind: str,
) -> dict[str, Any]:
    allowed = (
        "object_version",
        "framework_version",
        "schema_version",
        "context_applicability",
        "knowledge_layers",
    )
    result: dict[str, Any] = {
        "record_kind": record_kind,
        "parent_object_type": _text(parent.get("type")),
    }
    for key in allowed:
        if key in parent and parent[key] not in (None, ""):
            result[key] = deepcopy(parent[key])
    if record_kind != "object" and "record_version" in record:
        result["record_version"] = deepcopy(record["record_version"])
    for key in (
        "metadata",
        "geography_ids",
        "external_references",
        "evidence_targets",
        "traditions",
    ):
        if key in record and record[key] not in (None, "", []):
            result[key] = deepcopy(record[key])
    return result


def _rationale(record: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "rationale",
        "notes",
        "confidence_rationale",
        "passage_relevance",
        "relevance_rationale",
        "scholarly_interpretation",
        "primary_observation",
    )
    return {
        key: deepcopy(record[key])
        for key in fields
        if key in record and record[key] not in (None, "", [])
    }


def _interpretation_state(record: Mapping[str, Any]) -> str:
    explicit = _text(
        record.get("interpretation_state")
        or record.get("interpretation_status")
        or record.get("epistemic_status")
    ).casefold().replace("-", "_")
    if explicit in {"unknown", "not_established", "disputed"}:
        return explicit
    certainty = _text(record.get("certainty")).casefold().replace("-", "_")
    dispute = _text(record.get("dispute_status")).casefold().replace("-", "_")
    disputed_values = {
        "disputed",
        "minor_scholarly_disagreement",
        "major_scholarly_disagreement",
        "denominational_disagreement",
        "textual_variant",
        "lexical_uncertainty",
        "historical_uncertainty",
        "chronological_uncertainty",
        "archaeological_uncertainty",
        "identification_uncertainty",
        "interpretive_uncertainty",
    }
    if certainty == "not_established":
        return "not_established"
    if certainty == "disputed" or dispute in disputed_values:
        return "disputed"
    if certainty not in {"", "unknown"}:
        return certainty
    if dispute not in {"", "unknown"}:
        return dispute
    return "unknown"


def _anchor_entries(value: Any) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for raw in _sequence(value):
        anchor = mapping(raw)
        if anchor:
            reference = _text(anchor.get("reference"))
            if reference:
                result.append(deepcopy(anchor))
        elif isinstance(raw, str) and raw.strip():
            result.append({"reference": raw.strip()})
    return result


def _child_local_id(record_kind: str, record: Mapping[str, Any]) -> str:
    local_id = _text(record.get("id"))
    if local_id:
        return local_id
    if record_kind != "interpretive_note":
        return ""
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256-{digest}"


def _ckl_stable_id(parent_id: str, record_kind: str, local_id: str | None) -> str:
    if record_kind == "object":
        return f"ckl:{parent_id}"
    namespace = {"claim": "claim", "evidence": "evidence", "interpretive_note": "interpretive-note"}[record_kind]
    return f"ckl:{parent_id}#{namespace}:{local_id or ''}"


def _ckl_navigation(parent_id: str) -> NavigationDestination:
    destination_id = f"navigation:ckl:{parent_id}"
    return NavigationDestination(
        id=destination_id,
        kind="canonical_object",
        target_id=parent_id,
        href=f"/api/canonical/objects/{quote(parent_id, safe='-._~')}",
    )


def _passage_navigation(passage: PassageProjection) -> NavigationDestination:
    parameters: dict[str, str | int] = {
        "book": passage.book,
        "chapter": passage.chapter,
    }
    if passage.verse_start is not None:
        parameters["verse_start"] = passage.verse_start
    if passage.verse_end is not None:
        parameters["verse_end"] = passage.verse_end
    return NavigationDestination(
        id=f"navigation:passage:{passage.reference}",
        kind="passage",
        target_id=passage.reference,
        href=f"/api/study/companion-context?{urlencode(parameters)}",
    )


def _object_sections(object_type: str) -> tuple[str, ...]:
    normalized = object_type.casefold().replace("-", "_")
    if normalized in {"theme", "theology", "doctrine"}:
        return ("themes_biblical_connections",)
    if normalized in {"person", "people_group", "group", "institution"}:
        return ("people_events_relationships",)
    if normalized == "place":
        return ("biblical_geography",)
    if normalized in {"event", "timeline"}:
        return ("biblical_narrative", "people_events_relationships")
    if normalized == "archaeology":
        return ("archaeology_ancient_history",)
    if normalized == "book":
        return ("biblical_narrative",)
    return ()


def _child_sections(
    record_kind: str,
    parent_type: str,
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    normalized_parent = parent_type.casefold().replace("-", "_")
    if normalized_parent == "theme":
        return ("themes_biblical_connections",)
    if record_kind == "claim":
        claim_type = _text(record.get("claim_type")).casefold().replace("-", "_")
        sections: set[str] = set()
        if claim_type in {"biblical_text", "textual", "textual_observation"}:
            sections.add("biblical_narrative")
        elif claim_type in {"historical_cultural", "historical", "social", "political"}:
            sections.add("archaeology_ancient_history")
        elif claim_type in {"literary", "composition", "rhetorical"}:
            sections.update(("biblical_narrative", "themes_biblical_connections"))
        elif normalized_parent in {"theme", "theology", "doctrine"}:
            sections.add("themes_biblical_connections")
        return tuple(sorted(sections))
    if record_kind == "evidence":
        evidence_type = _text(record.get("evidence_type")).casefold().replace("_", "-")
        if evidence_type == "worldview-concept":
            return ("divine_council_cosmic_geography",)
        if evidence_type in {
            "ancient-text",
            "manuscript",
            "artifact",
            "archaeological-site",
            "inscription",
            "material-culture",
            "primary-source",
            "secondary-source",
            "historical-period",
        }:
            return ("archaeology_ancient_history",)
        if evidence_type == "geography-environment":
            return ("biblical_geography",)
        if evidence_type in {"historical-event", "person", "people-group", "institution"}:
            return ("people_events_relationships",)
        if evidence_type == "literary-convention":
            return ("biblical_narrative", "themes_biblical_connections")
        return ()
    if record_kind == "interpretive_note":
        note_type = _text(record.get("note_type")).casefold().replace("-", "_")
        if note_type in {"ancient_near_east_context", "second_temple_context", "historical_context"}:
            return ("archaeology_ancient_history",)
        if note_type in {"canonical_connection", "later_reception"}:
            return ("biblical_narrative", "themes_biblical_connections")
        if note_type == "literary_observation":
            return ("biblical_narrative", "themes_biblical_connections")
        if note_type == "textual_observation":
            return ("biblical_narrative",)
        if note_type in {"theological_interpretation", "interpretive_caution"}:
            return ("themes_biblical_connections",)
    return ()


def _passage_connection(
    *,
    source_id: str,
    parent_id: str,
    local_id: str | None,
    anchor: Mapping[str, Any],
) -> ProjectionConnection:
    relationship = _optional_text(anchor.get("relationship"))
    temporal_relation = _text(anchor.get("temporal_relation")).casefold().replace("_", "-")
    if relationship:
        temporal_layer = _temporal_layer(relationship, temporal_relation)
    else:
        temporal_layer = _temporal_layer("", temporal_relation)
    basis = {
        "kind": "ckl_scripture_anchor",
        "parent_object_id": parent_id,
        "local_record_id": local_id,
        "reference": _text(anchor.get("reference")),
        "anchor_metadata": deepcopy(dict(anchor)),
    }
    return _new_connection(
        source_id=source_id,
        target_id=f"passage:{_text(anchor.get('reference'))}",
        relationship=relationship,
        relationship_mode="direct",
        temporal_layer=temporal_layer,
        basis=basis,
    )


def _related_object_connection(
    *,
    source_id: str,
    parent_id: str,
    local_id: str | None,
    relation: Any,
    assertion_type: Any,
) -> ProjectionConnection | None:
    data = mapping(relation)
    target_id = _text(data.get("id"))
    if not target_id:
        return None
    relationship = _optional_text(data.get("relationship"))
    basis = {
        "kind": "ckl_related_object",
        "parent_object_id": parent_id,
        "local_record_id": local_id,
        "notes": deepcopy(data.get("notes")) if data.get("notes") not in (None, "") else None,
        "weight": deepcopy(data.get("weight")) if data.get("weight") is not None else None,
    }
    mode = _relationship_mode(relationship, assertion_type)
    return _new_connection(
        source_id=source_id,
        target_id=f"ckl:{target_id}",
        relationship=relationship,
        relationship_mode=mode,
        temporal_layer="unknown",
        basis=basis,
    )


def _related_evidence_connection(
    *,
    source_id: str,
    parent_id: str,
    local_id: str,
    relation: Any,
    assertion_type: Any,
) -> ProjectionConnection | None:
    data = mapping(relation)
    target_id = _text(data.get("id"))
    if not target_id:
        return None
    relationship = _optional_text(data.get("relationship"))
    return _new_connection(
        source_id=source_id,
        target_id=_ckl_stable_id(parent_id, "evidence", target_id),
        relationship=relationship,
        relationship_mode=_relationship_mode(relationship, assertion_type),
        temporal_layer="unknown",
        basis={
            "kind": "ckl_related_evidence",
            "parent_object_id": parent_id,
            "local_record_id": local_id,
            "target_evidence_id": target_id,
            "notes": deepcopy(data.get("notes")) if data.get("notes") not in (None, "") else None,
            "weight": deepcopy(data.get("weight")) if data.get("weight") is not None else None,
        },
    )


def _relationship_mode(relationship: str | None, assertion_type: Any) -> str:
    if _text(assertion_type).casefold().replace("_", "-") == "inference":
        return "inferred"
    if _text(relationship).casefold().replace("_", "-") in {
        "direct",
        "direct-quotation",
        "quotation",
        "quotes",
        "explicit-textual-reference",
    }:
        return "direct"
    return "not_recorded"


def _new_connection(
    *,
    source_id: str,
    target_id: str,
    relationship: str | None,
    relationship_mode: str,
    temporal_layer: str,
    basis: Mapping[str, Any],
) -> ProjectionConnection:
    label = _text(relationship) or None
    connection_type = _CONNECTION_TYPE_BY_LABEL.get(_normalized_label(label), "uncategorized")
    stable_payload = {
        "source_id": source_id,
        "target_id": target_id,
        "relationship": label,
        "basis": basis,
    }
    serialized = json.dumps(stable_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    connection_id = "connection:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return ProjectionConnection(
        id=connection_id,
        source_id=source_id,
        target_id=target_id,
        connection_type=connection_type,
        original_relationship_type=label,
        relationship_mode=relationship_mode,
        direction="one_way",
        reverse_edge_id=None,
        temporal_layer=temporal_layer,
        basis=deepcopy(dict(basis)),
    )


def _reciprocal_edges(edges: Sequence[ProjectionConnection]) -> tuple[ProjectionConnection, ...]:
    edge_index = {
        (edge.source_id, edge.target_id, edge.original_relationship_type): edge
        for edge in edges
        if edge.basis.get("kind") in {"ckl_related_object", "ckl_related_evidence"}
    }
    result: list[ProjectionConnection] = []
    for edge in sorted(edges, key=lambda item: item.id):
        if edge.basis.get("kind") not in {"ckl_related_object", "ckl_related_evidence"}:
            result.append(edge)
            continue
        reverse = edge_index.get((edge.target_id, edge.source_id, edge.original_relationship_type))
        if reverse is None or reverse.id == edge.id:
            result.append(edge)
        else:
            result.append(replace(edge, direction="reciprocal", reverse_edge_id=reverse.id))
    return tuple(result)


def _temporal_layer(relationship: str, temporal_relation: str) -> str:
    normalized_relationship = _normalized_label(relationship)
    normalized_temporal = temporal_relation.casefold().replace("_", "-")
    if normalized_relationship in {"later-canonical-reception", "allusion"} or normalized_temporal == "later-comparative":
        return "later_reception"
    if normalized_relationship == "comparative" or normalized_temporal == "earlier-comparative":
        return "comparative_background"
    if normalized_relationship in {"direct", "primary", "supporting", "quotation"}:
        return "original_passage_context"
    return "unknown"


def _add_unique_item(items: dict[str, ProjectedItem], item: ProjectedItem) -> None:
    existing = items.get(item.id)
    if existing is not None and existing != item:
        raise ValueError(f"conflicting CKL records share stable ID {item.id}")
    items[item.id] = item


def _add_connection(
    connections: dict[str, ProjectionConnection],
    edge: ProjectionConnection | None,
) -> None:
    if edge is None:
        return
    existing = connections.get(edge.id)
    if existing is not None and existing != edge:
        raise ValueError(f"conflicting connection records share stable ID {edge.id}")
    connections[edge.id] = edge


def _normalized_label(value: str | None) -> str:
    return _text(value).casefold().replace(" ", "-")


def _first_record_text(record: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _optional_text(record.get(key))
        if value:
            return value
    return None


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text if text else None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return _text(value.get("reference") or value.get("id") or value.get("claim") or value.get("note"))
    return " ".join(str(value).split())


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, set):
        return sorted(value, key=lambda item: str(item))
    return [value]


def _string_values(value: Any) -> tuple[str, ...]:
    result: list[str] = []
    for raw in _sequence(value):
        text = _text(raw.get("id")) if isinstance(raw, Mapping) else _text(raw)
        if text and text not in result:
            result.append(text)
    return tuple(result)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=lambda item: str(item))]
    return deepcopy(value)


def _normalize_passage(reference: str) -> PassageProjection:
    normalized_input = " ".join(str(reference or "").split())
    spans = parse_scripture_references(normalized_input, book_alias_lookup=_BOOK_ALIASES)
    if len(spans) != 1:
        raise ValueError("passage_ref must identify one chapter or one verse range")
    span = spans[0]
    if span.start_chapter is None or span.start_chapter < 1:
        raise ValueError("passage_ref must identify a chapter")
    if span.end_chapter is not None and span.end_chapter != span.start_chapter:
        raise ValueError("cross-chapter passage scopes are not supported")
    start = span.start_verse
    end = span.end_verse
    if start is not None and start < 1:
        raise ValueError("verse numbers must be positive")
    if end is not None and end < 1:
        raise ValueError("verse numbers must be positive")
    if start is not None and end is not None and end < start:
        raise ValueError("verse_end must be greater than or equal to verse_start")
    if span.end_chapter is not None and end is None:
        raise ValueError("cross-chapter passage scopes are not supported")
    scope: Literal["chapter", "verse", "verse_range"] = "chapter"
    if start is not None:
        scope = "verse_range" if end is not None and end != start else "verse"
    canonical = format_scripture_reference(span)
    return PassageProjection(
        reference=canonical,
        book=span.book,
        chapter=span.start_chapter,
        verse_start=start,
        verse_end=end,
        scope=scope,
    )


def _require_lookup(value: DomainLookup, expected_domain: Domain) -> DomainLookup:
    if not isinstance(value, DomainLookup):
        raise TypeError(f"{expected_domain} lookup must be a DomainLookup")
    if value.domain != expected_domain:
        raise ValueError(f"expected a {expected_domain} lookup, got {value.domain}")
    return value


def _optional_lookup(value: DomainLookup | None, domain: Domain) -> DomainLookup:
    if value is None:
        return DomainLookup(domain=domain, query_status="not_run", reason_code="lookup_not_supplied")
    return _require_lookup(value, domain)


def _domain_coverage(domain: Domain, lookup: DomainLookup, projected_count: int) -> DomainCoverage:
    incomplete = lookup.query_status != "complete" or bool(lookup.missing_subdomains)
    if incomplete:
        state: CoverageState = "partial" if projected_count else "unknown"
    else:
        state = "available" if projected_count else "not_represented"

    if lookup.query_status in {"failed", "not_run"} and not lookup.records:
        returned_count: int | None = None
    else:
        returned_count = len(_unwrap_external_records(domain, lookup.records)) if domain != "ckl" else len(lookup.records)

    reason = lookup.reason_code
    if not reason and lookup.query_status == "complete" and not projected_count:
        reason = "no_eligible_records"
    elif not reason and lookup.query_status == "failed":
        reason = "retrieval_failed"
    elif not reason and lookup.query_status == "not_run":
        reason = "lookup_not_supplied"
    description = _coverage_description(
        source_domain=_SOURCE_DOMAIN[domain],
        state=state,
        query_status=lookup.query_status,
        count=projected_count,
        missing_subdomains=lookup.missing_subdomains,
    )
    return DomainCoverage(
        domain=domain,
        source_domain=_SOURCE_DOMAIN[domain],
        state=state,
        query_status=lookup.query_status,
        query_returned_count=returned_count,
        projected_item_count=projected_count,
        reason_code=reason,
        missing_subdomains=tuple(lookup.missing_subdomains),
        description=description,
    )


def _coverage_description(
    *,
    source_domain: str,
    state: CoverageState,
    query_status: QueryStatus,
    count: int,
    missing_subdomains: Sequence[str],
) -> str:
    if state == "available":
        return f"The {source_domain} lookup returned {count} passage-eligible item(s)."
    if state == "partial":
        missing = ", ".join(missing_subdomains)
        suffix = f" Missing subdomains: {missing}." if missing else ""
        return f"The {source_domain} lookup returned partial passage data.{suffix}"
    if query_status == "complete":
        return f"The completed {source_domain} lookup found no passage-eligible records."
    return f"Availability in {source_domain} is unknown because its lookup did not complete."


def _section_state(
    item_ids: Sequence[str], coverage: Sequence[DomainCoverage] | Any
) -> CoverageState:
    entries = tuple(coverage)
    if item_ids:
        if all(entry.state == "available" for entry in entries):
            return "available"
        return "partial"
    if entries and all(entry.state == "not_represented" for entry in entries):
        return "not_represented"
    return "unknown"


def _section_description(section_id: str, state: CoverageState, domains: Sequence[Domain]) -> str:
    sources = ", ".join(_SOURCE_DOMAIN[domain] for domain in domains)
    if state == "available":
        return f"Passage-linked items are available from {sources}."
    if state == "partial":
        return f"Passage-linked items are available, with incomplete coverage across {sources}."
    if state == "not_represented":
        return f"No eligible records are represented in the completed {sources} lookups."
    return f"Passage-specific availability could not be established across {sources}."
