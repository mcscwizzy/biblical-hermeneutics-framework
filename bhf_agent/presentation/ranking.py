"""Deterministic salience ranking before any presentation model is called."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from .models import EvidenceBundle, EvidenceItem


_WORD_RE = re.compile(r"[a-z0-9]+")
_CONFIDENCE = {"high": 0.09, "medium": 0.055, "low": 0.01}
_RELATIONSHIP = {
    "direct": 0.24,
    "primary": 0.23,
    "contextual": 0.14,
    "supporting": 0.11,
    "background": 0.06,
    "comparative": 0.03,
    "disputed": 0.02,
}
_SPECIFICITY = {"verse": 0.12, "chapter": 0.075, "book": 0.01, "unknown": -0.05}
_SIGNIFICANCE = {
    "culture": 0.055,
    "geography": 0.07,
    "history": 0.055,
    "archaeology": 0.07,
    "language": 0.055,
    "politics": 0.055,
    "economics": 0.06,
    "social": 0.06,
    "chronology": 0.05,
}


@dataclass(frozen=True)
class RankedEvidence:
    item: EvidenceItem
    score: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        value = self.item.to_dict()
        value["salience"] = {"score": self.score, "reasons": list(self.reasons)}
        return value


def rank_evidence(
    bundle: EvidenceBundle,
    *,
    limit: int = 8,
    minimum_score: float = 0.36,
) -> list[RankedEvidence]:
    """Return a narrow, de-duplicated pool suitable for presentation."""

    if limit <= 0:
        return []
    term_frequency = Counter(
        term
        for item in bundle.evidence_items
        for term in set(_terms(item.claim))
    )
    total = max(len(bundle.evidence_items), 1)
    entity_ids = set(bundle.entities_by_id)
    scored: list[RankedEvidence] = []

    for item in bundle.evidence_items:
        metadata = item.relevance_metadata
        reasons: list[str] = []
        relationship = str(metadata.get("passage_relationship") or "contextual")
        specificity = str(metadata.get("anchor_specificity") or "unknown")
        score = _RELATIONSHIP.get(relationship, 0.04)
        reasons.append(f"{relationship} passage relationship")
        score += _SPECIFICITY.get(specificity, -0.05)
        reasons.append(f"{specificity} Scripture anchor")
        score += _CONFIDENCE.get(item.confidence, 0.0)
        reasons.append(f"{item.confidence} confidence")
        score += _SIGNIFICANCE.get(item.category, 0.04)

        distance = metadata.get("verse_distance")
        if isinstance(distance, (int, float)):
            if distance == 0:
                score += 0.06
                reasons.append("exact passage overlap")
            elif distance <= 5:
                score += 0.035
                reasons.append("nearby verse")
            elif distance > 100:
                score -= min(0.20, 0.05 + float(distance) / 4000)
                reasons.append("distant passage association")

        related = [entity_id for entity_id in item.related_entity_ids if entity_id in entity_ids]
        if related:
            score += min(0.07, 0.035 + 0.01 * len(related))
            reasons.append("linked passage entity")
        elif item.related_entity_ids:
            score -= 0.16
            reasons.append("weakly connected entity")

        exploration = _number(metadata.get("exploration_potential"), 0.0)
        score += min(0.06, exploration * 0.06)
        if exploration >= 0.5:
            reasons.append("supports an exploration path")
        if metadata.get("presentation_role") == "significance":
            score += 0.04
            reasons.append("explicit passage significance")

        importance = min(max(_number(metadata.get("object_importance"), 0.0), 0.0), 100.0)
        score += importance / 2000.0
        retrieval_score = min(max(_number(metadata.get("retrieval_score"), 0.0), 0.0), 1.0)
        score += retrieval_score * 0.05
        if item.source_ids:
            score += 0.04
            reasons.append("source provenance available")

        terms = set(_terms(item.claim))
        rare_terms = [term for term in terms if term_frequency[term] <= max(1, total // 5)]
        if rare_terms:
            score += min(0.05, 0.02 + len(rare_terms) * 0.004)
            reasons.append("distinctive evidence")

        if bool(metadata.get("broad_tag_only")):
            score -= 0.55
            reasons.append("broad-tag-only penalty")
        if specificity in {"book", "unknown"} and relationship not in {"direct", "primary"}:
            score -= 0.16
            reasons.append("generic background penalty")
        if item.confidence == "low" and relationship not in {"direct", "primary"}:
            score -= 0.10
            reasons.append("weak evidence penalty")
        if len(terms) < 5:
            score -= 0.07
            reasons.append("low-information penalty")

        score = round(max(0.0, min(score, 1.0)), 4)
        if score >= minimum_score:
            scored.append(RankedEvidence(item=item, score=score, reasons=tuple(reasons)))

    scored.sort(key=lambda value: (-value.score, value.item.id))
    selected: list[RankedEvidence] = []
    for candidate in scored:
        if any(_near_duplicate(candidate.item.claim, existing.item.claim) for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def _near_duplicate(left: str, right: str) -> bool:
    normalized_left = " ".join(_terms(left))
    normalized_right = " ".join(_terms(right))
    if not normalized_left or not normalized_right:
        return False
    if normalized_left in normalized_right or normalized_right in normalized_left:
        shorter = min(len(normalized_left), len(normalized_right))
        longer = max(len(normalized_left), len(normalized_right))
        if shorter / longer >= 0.72:
            return True
    return SequenceMatcher(None, normalized_left, normalized_right).ratio() >= 0.86


def _terms(value: str) -> Iterable[str]:
    return _WORD_RE.findall(str(value or "").casefold())


def _number(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
