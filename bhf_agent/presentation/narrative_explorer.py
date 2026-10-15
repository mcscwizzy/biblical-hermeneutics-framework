"""Read-only, passage-scoped Narrative Explorer projection contracts.

This module accepts records already retrieved by existing CKL, map, and
archaeology callers. It performs no I/O and never writes source records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping, Sequence

from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_references,
)

from .eligibility import _BOOK_ALIASES


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
    query_status: Literal["complete", "partial", "failed"] = "complete"
    reason_code: str | None = None
    missing_subdomains: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.domain not in _SOURCE_DOMAIN:
            raise ValueError(f"unsupported Narrative Explorer lookup domain: {self.domain}")
        if self.query_status not in {"complete", "partial", "failed"}:
            raise ValueError(f"unsupported query status: {self.query_status}")
        object.__setattr__(self, "records", tuple(self.records or ()))
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
        return asdict(self)


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
        return asdict(self)


@dataclass(frozen=True)
class ProjectionSection:
    id: str
    state: CoverageState
    item_ids: tuple[str, ...]
    source_domains: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NarrativeExplorerProjection:
    schema_version: str
    passage: PassageProjection
    coverage: tuple[DomainCoverage, ...]
    sections: tuple[ProjectionSection, ...]
    items: tuple[Mapping[str, Any], ...] = ()
    connections: tuple[Mapping[str, Any], ...] = ()
    navigation: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "passage": self.passage.to_dict(),
            "coverage": [entry.to_dict() for entry in self.coverage],
            "sections": [entry.to_dict() for entry in self.sections],
            "items": [dict(item) for item in self.items],
            "connections": [dict(edge) for edge in self.connections],
            "navigation": [dict(destination) for destination in self.navigation],
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

    # Task-specific projectors add eligible items in their domain. Coverage is
    # deliberately computed from projected items rather than raw candidates.
    item_groups: dict[Domain, list[Mapping[str, Any]]] = {domain: [] for domain in _DOMAIN_ORDER}
    coverage = tuple(
        _domain_coverage(domain, lookups[domain], len(item_groups[domain]))
        for domain in _DOMAIN_ORDER
    )
    coverage_by_domain = {entry.domain: entry for entry in coverage}
    sections = tuple(
        ProjectionSection(
            id=section_id,
            state=_section_state((), (coverage_by_domain[domain] for domain in domains)),
            item_ids=(),
            source_domains=tuple(_SOURCE_DOMAIN[domain] for domain in domains),
            description=_section_description(
                section_id,
                _section_state((), (coverage_by_domain[domain] for domain in domains)),
                domains,
            ),
        )
        for section_id, domains in _SECTION_DOMAINS
    )
    return NarrativeExplorerProjection(
        schema_version=SCHEMA_VERSION,
        passage=passage,
        coverage=coverage,
        sections=sections,
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
        return DomainLookup(domain=domain, query_status="failed", reason_code="lookup_not_supplied")
    return _require_lookup(value, domain)


def _domain_coverage(domain: Domain, lookup: DomainLookup, projected_count: int) -> DomainCoverage:
    incomplete = lookup.query_status != "complete" or bool(lookup.missing_subdomains)
    if incomplete:
        state: CoverageState = "partial" if projected_count else "unknown"
    else:
        state = "available" if projected_count else "not_represented"

    if lookup.query_status == "failed" and not lookup.records:
        returned_count: int | None = None
    else:
        returned_count = len(lookup.records)

    reason = lookup.reason_code
    if not reason and lookup.query_status == "complete" and not projected_count:
        reason = "no_eligible_records"
    elif not reason and lookup.query_status == "failed":
        reason = "retrieval_failed"
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
