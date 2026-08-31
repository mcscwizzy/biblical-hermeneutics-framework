"""Shared passage eligibility rules for canonical entities and events."""

from __future__ import annotations

from typing import Any, Mapping

from .models import mapping
from .references import anchor_specificity, references_overlap


def canonical_object_anchors(value: Any) -> list[str]:
    """Return normalized Scripture anchors declared by a canonical object."""

    data = mapping(value)
    raw_values = data.get("scripture_references") or []
    if not isinstance(raw_values, (list, tuple, set)):
        raw_values = [raw_values]
    anchors: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        if isinstance(raw, Mapping):
            raw = raw.get("reference")
        anchor = " ".join(str(raw or "").split())
        if anchor and anchor not in seen:
            anchors.append(anchor)
            seen.add(anchor)
    return anchors


def is_canonical_object_passage_eligible(passage_ref: str, value: Any) -> bool:
    """Require explicit overlap and reject book-only leakage into narrower scopes."""

    normalized_reference = " ".join(str(passage_ref or "").split())
    matching = [
        anchor
        for anchor in canonical_object_anchors(value)
        if references_overlap(normalized_reference, anchor)
    ]
    if not matching:
        return False
    if anchor_specificity(normalized_reference) == "book":
        return True
    return any(anchor_specificity(anchor) != "book" for anchor in matching)
