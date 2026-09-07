"""Compile EvidenceBundle data into deterministic chapter understanding units."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from bhf_agent.chapter_commentary.availability import (
    EvidenceAvailability,
    classify_evidence_availability,
    evidence_contribution,
)
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import (
    ScriptureReferenceSpan,
    format_scripture_reference,
    parse_scripture_references,
)
from bhf_agent import bible

from .hashing import with_synthesis_hash
from .models import (
    SYNTHESIS_COMPILER_VERSION,
    SYNTHESIS_SCHEMA_VERSION,
    CompiledChapterSynthesis,
    SynthesisCoverage,
    SynthesisGap,
    SynthesisUnit,
)


_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
_CATEGORY_KIND = {
    "history": "historical_context",
    "politics": "historical_context",
    "culture": "cultural_context",
    "social": "cultural_context",
    "economics": "cultural_context",
    "geography": "archaeology_geography",
    "archaeology": "archaeology_geography",
    "language": "language_literary",
    "chronology": "chronology",
}
_DISPUTED_VALUES = {
    "disputed",
    "speculative",
    "insufficient_evidence",
    "contested",
    "uncertain",
}
_UNDISPUTED_VALUES = {"", "not_disputed", "undisputed", "supported", "established", "none", "unknown"}
_MAX_FACTS_PER_UNIT = 5


@dataclass(frozen=True)
class _EvidenceGroup:
    kind: str
    items: tuple[EvidenceItem, ...]
    relationship_basis: str
    passage_scope: str = "CURRENT_CHAPTER"


def compile_chapter_synthesis(
    bundle: EvidenceBundle,
    *,
    book: str | None = None,
    chapter: int | None = None,
    schema_version: str = SYNTHESIS_SCHEMA_VERSION,
    compiler_version: str = SYNTHESIS_COMPILER_VERSION,
) -> CompiledChapterSynthesis:
    """Compile a bundle without model calls or outside knowledge."""

    derived_book, derived_chapter = _identity(bundle.passage_ref)
    canonical_book = book or derived_book
    canonical_chapter = chapter or derived_chapter
    if not canonical_book or canonical_chapter < 1:
        raise ValueError(f"cannot derive chapter identity from {bundle.passage_ref!r}")

    availability = classify_evidence_availability(bundle).value
    groups = _project_groups(
        _compatible_groups(bundle.evidence_items),
        book=canonical_book,
        chapter=canonical_chapter,
    )
    units = [
        _unit(group, bundle, book=canonical_book, chapter=canonical_chapter)
        for group in groups
    ]
    relationship_units = _relationship_units(
        groups, units, bundle, book=canonical_book, chapter=canonical_chapter
    )
    all_units = sorted(
        [*units, *relationship_units], key=lambda value: (value.kind, value.id)
    )
    used = sorted({item for unit in all_units for item in unit.evidence_ids})
    item_ids = sorted(item.id for item in bundle.evidence_items)
    category_counts = Counter(item.category for item in bundle.evidence_items)
    unit_counts = Counter(unit.kind for unit in all_units)
    specific_count = sum(
        evidence_contribution(item, bundle.passage_ref).specific
        for item in bundle.evidence_items
    )
    gaps = _evidence_gaps(availability, category_counts, specific_count)
    coverage = SynthesisCoverage(
        evidence_item_count=len(item_ids),
        used_evidence_ids=used,
        unused_evidence_ids=sorted(set(item_ids) - set(used)),
        evidence_categories=dict(sorted(category_counts.items())),
        category_diversity=len(category_counts),
        specific_evidence_count=specific_count,
        entity_counts={
            bucket: len(bundle.entities.get(bucket, []))
            for bucket in ("people", "places", "groups", "events", "artifacts")
        },
        unit_kind_counts=dict(sorted(unit_counts.items())),
        relationship_unit_count=len(relationship_units),
    )
    synthesis = CompiledChapterSynthesis(
        reference=f"{canonical_book} {canonical_chapter}",
        book=canonical_book,
        chapter=canonical_chapter,
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        synthesis_schema_version=schema_version,
        synthesis_compiler_version=compiler_version,
        synthesis_hash="",
        evidence_availability=availability,
        synthesis_units=all_units,
        evidence_gaps=gaps,
        coverage=coverage,
    )
    return with_synthesis_hash(synthesis)


def _compatible_groups(items: Iterable[EvidenceItem]) -> list[_EvidenceGroup]:
    ordered = sorted(items, key=lambda item: item.id)
    buckets: dict[str, list[EvidenceItem]] = {}
    for item in ordered:
        buckets.setdefault(_kind(item), []).append(item)

    groups: list[_EvidenceGroup] = []
    for kind in sorted(buckets):
        remaining = list(buckets[kind])
        while remaining:
            seed = remaining.pop(0)
            component = [seed]
            changed = True
            while changed:
                changed = False
                for candidate in list(remaining):
                    if any(_relationship(item, candidate) for item in component):
                        component.append(candidate)
                        remaining.remove(candidate)
                        changed = True
            component.sort(key=lambda item: item.id)
            for offset in range(0, len(component), _MAX_FACTS_PER_UNIT):
                chunk = tuple(component[offset : offset + _MAX_FACTS_PER_UNIT])
                basis = _group_basis(chunk)
                groups.append(_EvidenceGroup(kind=kind, items=chunk, relationship_basis=basis))
    return groups


def _project_groups(
    groups: Iterable[_EvidenceGroup], *, book: str, chapter: int
) -> list[_EvidenceGroup]:
    """Split mixed anchors so external passage material is explicit context."""

    projected: list[_EvidenceGroup] = []
    for group in groups:
        current: list[EvidenceItem] = []
        surrounding: list[EvidenceItem] = []
        for item in group.items:
            current_refs, external_refs = _project_anchor_refs(
                item.passage_anchors, book=book, chapter=chapter
            )
            # An item whose authored anchor includes any outside chapter must
            # remain whole, but it is exposed only as surrounding context. It
            # must not be silently treated as a direct current-chapter fact.
            if external_refs:
                surrounding.append(item)
            elif current_refs or not item.passage_anchors:
                current.append(item)
            else:
                surrounding.append(item)
        if current:
            projected.append(
                _EvidenceGroup(
                    kind=group.kind,
                    items=tuple(current),
                    relationship_basis=group.relationship_basis,
                    passage_scope="CURRENT_CHAPTER",
                )
            )
        if surrounding:
            projected.append(
                _EvidenceGroup(
                    kind="surrounding_passages",
                    items=tuple(surrounding),
                    relationship_basis=group.relationship_basis,
                    passage_scope="SURROUNDING_PASSAGE",
                )
            )
    return projected


def _project_anchor_refs(
    anchors: Iterable[str], *, book: str, chapter: int
) -> tuple[list[str], list[str]]:
    current: set[str] = set()
    external: set[str] = set()
    canonical_book = bible.normalize_book_name(book)
    for anchor in anchors:
        spans = parse_scripture_references(str(anchor), book_alias_lookup=_BOOK_ALIASES)
        if not spans:
            external.add(" ".join(str(anchor).split()))
            continue
        for span in spans:
            current_refs, external_refs = _split_span(
                span, canonical_book=canonical_book, chapter=chapter
            )
            current.update(current_refs)
            external.update(external_refs)
    return sorted(current), sorted(external)


def _split_span(
    span: ScriptureReferenceSpan, *, canonical_book: str, chapter: int
) -> tuple[list[str], list[str]]:
    if span.book != canonical_book:
        return [], [format_scripture_reference(span)]
    if span.start_chapter is None:
        return [], [format_scripture_reference(span)]
    end_chapter = span.end_chapter or span.start_chapter
    if span.start_chapter == end_chapter == chapter:
        return [format_scripture_reference(span)], []

    current: list[str] = []
    external: list[str] = []
    for value in range(span.start_chapter, end_chapter + 1):
        start_verse = span.start_verse if value == span.start_chapter else 1
        end_verse = span.end_verse if value == end_chapter else None
        try:
            max_verse = max(
                int(item["verse"])
                for item in bible.resolve_chapter(canonical_book, value).get("verses", [])
            )
        except (bible.BibleError, KeyError, TypeError, ValueError):
            max_verse = 999
        if end_verse is None:
            end_verse = max_verse
        if value == chapter:
            current.append(
                bible.verse_range_reference(
                    canonical_book, value, start_verse, end_verse
                )
            )
        else:
            external.append(
                bible.verse_range_reference(
                    canonical_book, value, start_verse, end_verse
                )
            )
    return current, external


def _kind(item: EvidenceItem) -> str:
    metadata = item.relevance_metadata or {}
    if _is_disputed(item):
        return "interpretive_questions"
    role = str(metadata.get("presentation_role") or "").casefold()
    if role == "dig_deeper":
        return "surrounding_passages"
    if role == "historical_context" and item.category in {"culture", "social", "economics"}:
        return "cultural_context"
    if role in {
        "historical_context",
        "archaeology_geography",
        "language_literary",
        "chronology",
        "interpretive_questions",
    }:
        return role
    if str(metadata.get("semantic_relationship") or "").casefold() in {
        "intertextual_reuse",
        "later_reception",
        "comparative_context",
    }:
        return "surrounding_passages"
    if str(metadata.get("passage_relationship") or "").casefold() in {
        "background",
        "comparative",
        "later_reception",
    }:
        return "surrounding_passages"
    return _CATEGORY_KIND.get(item.category, "cultural_context")


def _relationship(left: EvidenceItem, right: EvidenceItem) -> bool:
    left_entities = set(left.related_entity_ids)
    right_entities = set(right.related_entity_ids)
    if left_entities.intersection(right_entities):
        return True
    left_parent = str((left.relevance_metadata or {}).get("parent_object_id") or "")
    right_parent = str((right.relevance_metadata or {}).get("parent_object_id") or "")
    if left_parent and left_parent == right_parent:
        return True
    left_supports = set((left.relevance_metadata or {}).get("supports_evidence_ids") or [])
    right_supports = set((right.relevance_metadata or {}).get("supports_evidence_ids") or [])
    return right.id in left_supports or left.id in right_supports


def _group_basis(items: tuple[EvidenceItem, ...]) -> str:
    if len(items) == 1:
        return "single_evidence_item"
    shared_entities = set(items[0].related_entity_ids)
    for item in items[1:]:
        shared_entities.intersection_update(item.related_entity_ids)
    if shared_entities:
        return "shared_entities"
    parents = {
        str((item.relevance_metadata or {}).get("parent_object_id") or "")
        for item in items
    }
    if len(parents - {""}) == 1:
        return "shared_parent_object"
    return "authored_significance_link"


def _unit(
    group: _EvidenceGroup,
    bundle: EvidenceBundle,
    *,
    book: str,
    chapter: int,
) -> SynthesisUnit:
    evidence_ids = [item.id for item in group.items]
    entity_ids = sorted(
        {
            entity_id
            for item in group.items
            for entity_id in item.related_entity_ids
            if entity_id in bundle.entities_by_id
        }
    )
    metadata = {
        "relationship_basis": group.relationship_basis,
        "source_categories": sorted({item.category for item in group.items}),
        "support_count": len(group.items),
        "passage_scope": group.passage_scope,
        "explicit_significance": any(
            (item.relevance_metadata or {}).get("presentation_role") == "significance"
            for item in group.items
        ),
    }
    source_anchors = sorted(
        {anchor for item in group.items for anchor in item.passage_anchors}
    )
    projected_refs = _project_anchor_refs(
        source_anchors, book=book, chapter=chapter
    )[
        0 if group.passage_scope == "CURRENT_CHAPTER" else 1
    ]
    payload = {
        "kind": group.kind,
        "facts": [item.claim for item in group.items],
        "evidence_ids": evidence_ids,
        "entity_ids": entity_ids,
        "metadata": metadata,
        "passage_scope": group.passage_scope,
        "source_anchors": source_anchors,
        "verse_refs": projected_refs,
    }
    return SynthesisUnit(
        id=_unit_id(group.kind, payload),
        kind=group.kind,
        facts=[item.claim for item in group.items],
        verse_refs=projected_refs,
        evidence_ids=evidence_ids,
        entity_ids=entity_ids,
        confidence=_minimum_confidence(group.items),
        interpretation_level=_interpretation(group.items),
        passage_scope=group.passage_scope,
        source_anchors=source_anchors,
        metadata=metadata,
    )


def _relationship_units(
    groups: list[_EvidenceGroup],
    units: list[SynthesisUnit],
    bundle: EvidenceBundle,
    *,
    book: str,
    chapter: int,
) -> list[SynthesisUnit]:
    results: list[SynthesisUnit] = []
    for group, source_unit in zip(groups, units):
        explicit = any(
            (item.relevance_metadata or {}).get("presentation_role") == "significance"
            for item in group.items
        )
        if len(group.items) < 2 and not explicit:
            continue
        if group.relationship_basis not in {
            "shared_entities",
            "shared_parent_object",
            "authored_significance_link",
        }:
            continue
        metadata = {
            "relationship_basis": group.relationship_basis,
            "support_count": len(group.items),
            "explicit_significance": explicit,
            "safe_for_significance": True,
        }
        relationship_kind = (
            "why_it_matters"
            if group.passage_scope == "CURRENT_CHAPTER"
            else "surrounding_passages"
        )
        payload = {
            "kind": relationship_kind,
            "source_unit": source_unit.id,
            "evidence_ids": source_unit.evidence_ids,
            "metadata": metadata,
            "passage_scope": group.passage_scope,
            "verse_refs": source_unit.verse_refs,
        }
        results.append(
            SynthesisUnit(
                id=_unit_id(relationship_kind, payload),
                kind=relationship_kind,
                facts=list(source_unit.facts),
                verse_refs=list(source_unit.verse_refs),
                evidence_ids=list(source_unit.evidence_ids),
                entity_ids=list(source_unit.entity_ids),
                related_unit_ids=[source_unit.id],
                confidence=source_unit.confidence,
                interpretation_level=(
                    "disputed"
                    if source_unit.interpretation_level == "disputed"
                    else "inference"
                ),
                passage_scope=group.passage_scope,
                source_anchors=list(source_unit.source_anchors),
                metadata=metadata,
            )
        )
    return results


def _interpretation(items: Iterable[EvidenceItem]) -> str:
    values = tuple(items)
    if any(_is_disputed(item) for item in values):
        return "disputed"
    if any(
        str((item.relevance_metadata or {}).get("assertion_type") or "").casefold()
        in {"inference", "interpretation"}
        for item in values
    ):
        return "inference"
    return "fact"


def _is_disputed(item: EvidenceItem) -> bool:
    metadata = item.relevance_metadata or {}
    if metadata.get("disputed") is True:
        return True
    dispute_status = str(metadata.get("dispute_status") or "").casefold()
    certainty = str(metadata.get("certainty") or "").casefold()
    return dispute_status not in _UNDISPUTED_VALUES or certainty in _DISPUTED_VALUES


def _minimum_confidence(items: Iterable[EvidenceItem]) -> str:
    values = tuple(items)
    rank = min((_CONFIDENCE_RANK.get(item.confidence, 0) for item in values), default=0)
    return {value: key for key, value in _CONFIDENCE_RANK.items()}[rank]


def _evidence_gaps(
    availability: str,
    categories: Counter[str],
    specific_count: int,
) -> list[SynthesisGap]:
    gaps: list[SynthesisGap] = []
    if availability == EvidenceAvailability.DATA_GAP.value:
        gaps.append(SynthesisGap("context", "No passage-scoped contextual evidence is available.", "substantial"))
    elif availability == EvidenceAvailability.THIN.value:
        gaps.append(SynthesisGap("context", "Passage-scoped contextual evidence is thin.", "material"))
    if specific_count == 0:
        gaps.append(SynthesisGap("passage_specificity", "No verse- or chapter-specific evidence was compiled.", "material"))
    if not categories.get("geography") and not categories.get("archaeology"):
        gaps.append(SynthesisGap("archaeology_geography", "No archaeology or geography evidence was supplied."))
    if not categories.get("culture") and not categories.get("social"):
        gaps.append(SynthesisGap("culture_social", "No cultural or social evidence was supplied."))
    if not categories.get("language"):
        gaps.append(SynthesisGap("language_literary", "No language evidence was supplied."))
    return gaps


def _unit_id(kind: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    return f"syn_{kind}_{digest}"


def _identity(reference: str) -> tuple[str, int]:
    match = re.match(r"^(.+?)\s+(\d+)(?::.*)?$", " ".join(reference.split()))
    if not match:
        return "", 0
    return match.group(1), int(match.group(2))
