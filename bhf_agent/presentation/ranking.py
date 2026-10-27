"""Deterministic salience ranking before any presentation model is called."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from framework.canonical_library.scripture import parse_scripture_references

from bhf_agent.references import BOOKS

from .models import EvidenceBundle, EvidenceItem
from .references import _BOOK_ALIASES


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
_SEMANTIC_RELATIONSHIP_PENALTY = {
    "BOOK_CONTEXT": 0.08,
    "GENERIC_BACKGROUND": 0.14,
    "COMPARATIVE_CONTEXT": 0.08,
    "INTERTEXTUAL_REUSE": 0.10,
    "LATER_RECEPTION": 0.12,
    "WEAKLY_RELATED": 0.48,
    "SEMANTICALLY_MISANCHORED": 0.55,
}
_APPLICABILITY_SCOPE_PENALTY = {
    "section": 0.04,
    "book": 0.10,
    "testament": 0.16,
    "global": 0.18,
    "entity": 0.05,
}
_COMPARATIVE_TEXT_RE = re.compile(
    r"\b(?:compar(?:e|ative|ison)|parallel(?:s)?|analogue|shared motifs?|"
    r"shared language|earlier [a-z ]{0,25} evidence|ancient near eastern"
    r".{0,55}(?:environment|traditions|texts))\b",
    re.IGNORECASE,
)
_RECEPTION_TEXT_RE = re.compile(
    r"\b(?:re[- ]?read(?:s|ing)?|reinterprets?|reception|appropriat(?:es|ion)|"
    r"cites|quotes|echoes)\b",
    re.IGNORECASE,
)
_SECOND_TEMPLE_RECEPTION_RE = re.compile(
    r"\b(?:second temple|1 enoch|book of jubilees|jubilees)\b.{0,100}"
    r"\b(?:reading|interpretation|reception|develops?|reworks?)\b",
    re.IGNORECASE,
)
_SCRIPTURE_BOOK_PATTERNS = tuple(
    (canonical, re.compile(rf"(?<![A-Za-z]){re.escape(canonical)}\s+(\d{{1,3}})\b", re.IGNORECASE))
    for canonical in sorted(BOOKS, key=len, reverse=True)
)


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
    candidates = [
        item
        for item in bundle.evidence_items
        if not (
            item.relevance_metadata.get("presentation_role") == "significance"
            and item.relevance_metadata.get("supports_evidence_ids")
        )
        and not (
            item.relevance_metadata.get("source_kind") == "ckl_interpretive_note"
            and re.match(
                r"\s*(?:do not|avoid|must not|never|don't)\b", item.claim, re.I
            )
        )
    ]
    term_frequency = Counter(
        term
        for item in candidates
        for term in set(_terms(item.claim))
    )
    total = max(len(candidates), 1)
    entity_ids = set(bundle.entities_by_id)
    scored: list[RankedEvidence] = []

    for item in candidates:
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

        is_passage_map = str(metadata.get("source_kind") or "").startswith(
            "passage_map_"
        )
        semantic_relationship = presentation_relationship(bundle, item)
        scope = str(metadata.get("applicability_scope") or "").casefold()
        broad_anchor_penalty = _broad_anchor_penalty(item.passage_anchors)
        authored_direct_scope = (
            relationship in {"direct", "primary"}
            and specificity == "verse"
            and scope in {"passage", "section"}
            and broad_anchor_penalty == 0
        )
        semantic_penalty = _SEMANTIC_RELATIONSHIP_PENALTY.get(
            semantic_relationship, 0.0
        )
        weak_classification_with_direct_anchor = (
            semantic_relationship == "WEAKLY_RELATED" and authored_direct_scope
        )
        if (
            semantic_penalty
            and not is_passage_map
            and not weak_classification_with_direct_anchor
        ):
            score -= semantic_penalty
            reasons.append(f"{semantic_relationship.casefold().replace('_', ' ')} penalty")

        scope_penalty = _APPLICABILITY_SCOPE_PENALTY.get(scope, 0.0)
        if scope_penalty:
            score -= scope_penalty
            reasons.append(f"{scope} applicability penalty")

        if broad_anchor_penalty:
            score -= broad_anchor_penalty
            reasons.append("multi-chapter anchor penalty")

        cross_chapter_penalty = _cross_chapter_claim_penalty(bundle, item)
        if cross_chapter_penalty:
            score -= cross_chapter_penalty
            reasons.append("cross-chapter claim penalty")

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
        elif metadata.get("presentation_role") == "dig_deeper":
            score -= 0.04
            reasons.append("deeper comparative context penalty")
        if metadata.get("source_kind") == "ckl_interpretive_note":
            score -= 0.12
            reasons.append("interpretive-note penalty")

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


def presentation_relationship(bundle: EvidenceBundle, item: EvidenceItem) -> str:
    """Refine direct labels when the cited claim itself names comparative texts."""

    metadata = item.relevance_metadata
    relationship = str(metadata.get("semantic_relationship") or "").upper()
    if relationship not in {"DIRECT_CONTEXT", "BOOK_CONTEXT"}:
        return relationship
    claim = item.claim
    if _COMPARATIVE_TEXT_RE.search(claim):
        return "COMPARATIVE_CONTEXT"
    if _SECOND_TEMPLE_RECEPTION_RE.search(claim):
        return "LATER_RECEPTION"

    target_spans = parse_scripture_references(
        bundle.passage_ref, book_alias_lookup=_BOOK_ALIASES
    )
    target_book = next((span.book for span in target_spans), "")
    if not target_book:
        return relationship
    external_books = _scripture_books_in_text(claim) - {target_book}
    source_titles = {
        str(source.get("id") or ""): str(source.get("title") or "")
        for source in bundle.provenance.get("sources", [])
        if isinstance(source, dict)
    }
    for source_id in item.source_ids:
        title = source_titles.get(source_id, source_id)
        external_books.update(_scripture_books_in_text(title) - {target_book})
    if not external_books:
        return relationship

    if _RECEPTION_TEXT_RE.search(claim):
        target_testament = BOOKS.get(target_book, ("",))[0]
        source_testaments = {BOOKS.get(book, ("",))[0] for book in external_books}
        if target_testament == "Old Testament" and "New Testament" in source_testaments:
            return "LATER_RECEPTION"
    return "COMPARATIVE_CONTEXT"


def _scripture_books_in_text(value: str) -> set[str]:
    return {
        canonical
        for canonical, pattern in _SCRIPTURE_BOOK_PATTERNS
        if pattern.search(value)
    }


def _cross_chapter_claim_penalty(bundle: EvidenceBundle, item: EvidenceItem) -> float:
    target_spans = parse_scripture_references(
        bundle.passage_ref, book_alias_lookup=_BOOK_ALIASES
    )
    target = next(
        ((span.book, span.start_chapter) for span in target_spans if span.start_chapter),
        None,
    )
    if target is None:
        return 0.0
    for canonical, pattern in _SCRIPTURE_BOOK_PATTERNS:
        if canonical != target[0]:
            continue
        for match in pattern.finditer(item.claim):
            if int(match.group(1)) != target[1]:
                return 0.08
    return 0.0


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


def _broad_anchor_penalty(anchors: list[str]) -> float:
    """Penalize multi-chapter sources even when one verse overlaps the target."""

    penalty = 0.0
    for anchor in anchors:
        try:
            spans = parse_scripture_references(
                anchor, book_alias_lookup=_BOOK_ALIASES
            )
        except (TypeError, ValueError):
            continue
        for span in spans:
            start = span.start_chapter
            end = span.end_chapter if span.end_chapter is not None else start
            if start is None or end is None or end <= start:
                continue
            penalty = max(penalty, min(0.20, 0.06 + (end - start) * 0.01))
    return penalty


def _terms(value: str) -> Iterable[str]:
    return _WORD_RE.findall(str(value or "").casefold())


def _number(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
