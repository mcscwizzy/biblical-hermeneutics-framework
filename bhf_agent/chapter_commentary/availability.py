"""Deterministic, passage-specific classification of contextual coverage."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import parse_scripture_references


class EvidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    THIN = "THIN"
    DATA_GAP = "DATA_GAP"


DEFAULT_THIN_EVIDENCE_THRESHOLD = 1.5
AVAILABILITY_CLASSIFIER_VERSION = "availability-v1.1"


def thin_evidence_threshold() -> float:
    raw = os.getenv(
        "BHF_COMMENTARY_THIN_EVIDENCE_THRESHOLD",
        str(DEFAULT_THIN_EVIDENCE_THRESHOLD),
    )
    try:
        return max(1.0, float(raw))
    except ValueError:
        return float(DEFAULT_THIN_EVIDENCE_THRESHOLD)


@dataclass(frozen=True)
class EvidenceContribution:
    """Explain the deterministic contribution assigned to one evidence item."""

    score: float
    specificity: str
    specific: bool


def evidence_contribution(item: Any, _passage_ref: str) -> EvidenceContribution:
    """Score an item using its authored anchor, confidence, and dispute state.

    Whole-book material remains useful background, but its bounded contribution
    cannot make a chapter AVAILABLE without sufficiently specific companions.
    """

    metadata = getattr(item, "relevance_metadata", {}) or {}
    anchors = list(getattr(item, "passage_anchors", ()) or ())
    specificity, anchor_weight = _anchor_weight(anchors)
    confidence = str(getattr(item, "confidence", "") or "").casefold()
    confidence_weight = {"high": 1.0, "medium": 0.85, "low": 0.6}.get(confidence, 0.5)
    dispute_status = str(metadata.get("dispute_status") or "").casefold()
    dispute_weight = 0.75 if dispute_status not in {"", "not_disputed"} else 1.0
    relationship_weight = 0.85 if metadata.get("passage_relationship") in {
        "background",
        "comparative",
    } else 1.0
    category = str(getattr(item, "category", "") or "").casefold()
    category_weight = 1.0 if not category or category in {
        "culture",
        "geography",
        "history",
        "archaeology",
        "language",
        "politics",
        "economics",
        "social",
        "chronology",
    } else 0.5
    # Test doubles and older callers may not expose anchors. Treat those as
    # legacy chapter-scoped items so the public threshold API remains stable.
    if not anchors:
        specificity, anchor_weight = "chapter", 1.0
    score = anchor_weight * confidence_weight * dispute_weight * relationship_weight * category_weight
    return EvidenceContribution(
        score=round(score, 4),
        specificity=specificity,
        specific=anchor_weight >= 0.55,
    )


def classify_evidence_availability(
    bundle,
    *,
    threshold: float | None = None,
) -> EvidenceAvailability:
    """Classify a bundle conservatively without model or provider judgment."""

    items = list(getattr(bundle, "evidence_items", ()) or ())
    if not items:
        return EvidenceAvailability.DATA_GAP

    passage_ref = str(getattr(bundle, "passage_ref", "") or "")
    contributions = [evidence_contribution(item, passage_ref) for item in items]
    total_score = sum(item.score for item in contributions)
    specific_count = sum(item.specific for item in contributions)
    minimum_score = threshold if threshold is not None else thin_evidence_threshold()

    if total_score >= minimum_score and specific_count >= 2:
        return EvidenceAvailability.AVAILABLE
    return EvidenceAvailability.THIN if total_score > 0 else EvidenceAvailability.DATA_GAP


def _anchor_weight(anchors: list[str]) -> tuple[str, float]:
    best = ("unknown", 0.0)
    for anchor in anchors:
        spans = parse_scripture_references(str(anchor), book_alias_lookup=_BOOK_ALIASES)
        for span in spans:
            if span.start_chapter is None:
                candidate = ("book", 0.25)
            elif span.start_verse is not None:
                candidate = ("verse", 1.0)
            elif span.end_chapter is None:
                candidate = ("chapter", 1.0)
            elif span.start_chapter == 1 and span.end_chapter - span.start_chapter >= 10:
                candidate = ("whole_book", 0.25)
            else:
                candidate = ("multi_chapter", 0.65)
            if candidate[1] > best[1]:
                best = candidate
    return best
