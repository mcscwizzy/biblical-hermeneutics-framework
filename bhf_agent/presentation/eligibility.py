"""Shared passage eligibility rules for canonical presentation material."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .models import mapping
from .references import _BOOK_ALIASES, anchor_specificity, references_overlap
from framework.canonical_library.scripture import format_scripture_reference, parse_scripture_references


def scripture_anchors(value: Any) -> list[str]:
    """Return normalized Scripture anchors declared by a canonical record."""

    data = mapping(value)
    raw_values = data.get("scripture_references") or []
    if not isinstance(raw_values, (list, tuple, set)):
        raw_values = [raw_values]
    anchors: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        if isinstance(raw, Mapping):
            raw = raw.get("reference")
        for parsed in parse_scripture_references(
            str(raw or ""),
            book_alias_lookup=_BOOK_ALIASES,
        ):
            anchor = format_scripture_reference(parsed)
            if anchor not in seen:
                anchors.append(anchor)
                seen.add(anchor)
    return anchors


def canonical_object_anchors(value: Any) -> list[str]:
    """Return normalized Scripture anchors declared by a canonical object."""

    return scripture_anchors(value)


def passage_matching_scripture_anchors(passage_ref: str, value: Any) -> list[str]:
    """Return record anchors that overlap the requested passage."""

    normalized_reference = " ".join(str(passage_ref or "").split())
    return [
        anchor
        for anchor in scripture_anchors(value)
        if references_overlap(normalized_reference, anchor)
    ]


def is_canonical_object_passage_eligible(passage_ref: str, value: Any) -> bool:
    """Require explicit overlap and reject book-only leakage into narrower scopes."""

    normalized_reference = " ".join(str(passage_ref or "").split())
    matching = passage_matching_scripture_anchors(normalized_reference, value)
    if not matching:
        return False
    if anchor_specificity(normalized_reference) == "book":
        return True
    return any(anchor_specificity(anchor) != "book" for anchor in matching)


def canonical_narration_material(
    passage_ref: str,
    results: Sequence[Any],
) -> list[Any]:
    """Select CKL material safe for passage-scoped legacy narration.

    Passage-eligible parents retain their complete retrieval result. A broad
    parent can still contribute explicitly overlapping claims or notes, but it
    is projected down to those nested records so unrelated parent summaries,
    context fields, entities, and cross-references cannot leak into narration.
    EvidenceBundle remains the canonical path for structured evidence items.
    """

    selected: list[Any] = []
    for result in results:
        raw_object = getattr(result, "object", result)
        data = mapping(raw_object)
        if not data:
            continue
        if is_canonical_object_passage_eligible(passage_ref, data):
            selected.append(result)
            continue

        claims = [
            mapping(item)
            for item in _sequence(data.get("claims"))
            if passage_matching_scripture_anchors(passage_ref, item)
        ]
        notes = [
            mapping(item)
            for item in _sequence(data.get("interpretive_notes"))
            if passage_matching_scripture_anchors(passage_ref, item)
        ]
        if not claims and not notes:
            continue

        projection = {
            key: data[key]
            for key in (
                "id",
                "type",
                "title",
                "sources",
                "content_status",
                "review_status",
                "human_review_required",
            )
            if key in data
        }
        projection["claims"] = claims
        projection["interpretive_notes"] = notes
        projection["score"] = getattr(result, "score", 0.0)
        selected.append(projection)
    return selected


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]
