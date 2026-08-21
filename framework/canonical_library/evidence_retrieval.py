"""Deterministic ranking and packaging for structured CKL evidence items."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping, Sequence

from .evidence_models import CanonicalEvidenceItem
from .normalization import STOP_WORDS, normalize_text, tokenize_query


_CONFIDENCE_SCORE = {"high": 0.10, "medium": 0.07, "low": 0.03, "unrated": 0.0}
_ASSERTION_SCORE = {
    "primary-evidence": 0.10,
    "secondary-evidence": 0.07,
    "scholarly-reconstruction": 0.04,
    "inference": 0.01,
}
_SOURCE_QUALITY_SCORE = {
    "scripture": 0.06,
    "ancient-primary-source": 0.06,
    "excavation-report": 0.06,
    "museum-collection": 0.055,
    "journal-article": 0.055,
    "academic-book": 0.05,
    "lexicon": 0.05,
    "grammar": 0.05,
    "reference-work": 0.035,
    "confessional-source": 0.02,
    "other": 0.0,
}
_TEMPORAL_SCORE = {
    "contemporary": 0.15,
    "near-contemporary": 0.12,
    "earlier-comparative": 0.05,
    "later-comparative": 0.05,
    "diachronic": 0.04,
    "unknown": -0.10,
}
_DIMENSION_TYPES: dict[str, frozenset[str]] = {
    "historical setting": frozenset({"historical-event", "historical-period", "institution", "people-group"}),
    "cultural practice": frozenset({"cultural-practice", "institution", "material-culture"}),
    "ancient near eastern background": frozenset({"ancient-text", "inscription", "cultural-practice", "worldview-concept"}),
    "second temple context": frozenset({"ancient-text", "manuscript", "institution", "people-group"}),
    "greco roman context": frozenset({"ancient-text", "inscription", "institution", "cultural-practice"}),
    "manuscript textual evidence": frozenset({"manuscript", "ancient-text"}),
    "literary structure": frozenset({"literary-convention"}),
    "archaeology": frozenset({"artifact", "archaeological-site", "inscription", "material-culture"}),
    "evidence supporting an interpretation": frozenset(
        {
            "artifact",
            "archaeological-site",
            "inscription",
            "ancient-text",
            "manuscript",
            "historical-event",
            "cultural-practice",
            "literary-convention",
        }
    ),
}


@dataclass(frozen=True)
class RetrievedEvidenceItem:
    parent_object_id: str
    parent_title: str
    evidence_id: str
    title: str
    evidence_type: str
    description: str
    assertion_type: str
    confidence: str
    confidence_rationale: str
    passage_relevance: str
    certainty: str
    dispute_status: str
    primary_observation: str
    scholarly_interpretation: str
    temporal_scope: dict[str, Any]
    passage_relationship: str
    chronological_relation: str
    scripture_references: tuple[dict[str, Any], ...]
    sources: tuple[dict[str, Any], ...]
    claims: tuple[dict[str, Any], ...]
    related_objects: tuple[dict[str, Any], ...]
    related_evidence: tuple[dict[str, Any], ...]
    external_references: tuple[dict[str, Any], ...]
    metadata: dict[str, str]
    retrieval_score: float
    retrieval_reason: tuple[str, ...]
    matched_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for field_name in (
            "scripture_references",
            "sources",
            "claims",
            "related_objects",
            "related_evidence",
            "external_references",
            "retrieval_reason",
            "matched_terms",
        ):
            data[field_name] = list(data[field_name])
        return data


def rank_evidence_items(
    question: str,
    parent: Any,
    *,
    parent_relevance: float = 0.0,
    requested_dimensions: Sequence[str] = (),
    scripture_references: Sequence[str] = (),
    limit: int = 4,
) -> list[RetrievedEvidenceItem]:
    """Rank evidence within already relevant subjects, rejecting passage leakage."""

    if limit <= 0:
        return []
    parent_data = _mapping(parent)
    evidence_items = list(parent_data.get("evidence_items") or [])
    sources = {
        str(source.get("id") or ""): source
        for source in (_mapping(item) for item in (parent_data.get("sources") or []))
        if str(source.get("id") or "")
    }
    claims = {
        str(claim.get("id") or claim.get("claim_id") or ""): claim
        for claim in (_mapping(item) for item in (parent_data.get("claims") or []))
        if str(claim.get("id") or claim.get("claim_id") or "")
    }
    query_terms = _meaningful_terms(question)
    query_refs = tuple(str(value).strip() for value in scripture_references if str(value).strip())
    requested = {normalize_text(value) for value in requested_dimensions if str(value).strip()}
    ranked: list[RetrievedEvidenceItem] = []

    for raw_item in evidence_items:
        item = raw_item if isinstance(raw_item, CanonicalEvidenceItem) else CanonicalEvidenceItem.from_mapping(_mapping(raw_item))
        links = [link.to_dict() for link in item.scripture_references]
        matching_links = [
            link
            for link in links
            if any(_reference_overlap(reference, str(link["reference"])) for reference in query_refs)
        ]
        # A passage-scoped request may only use evidence explicitly connected
        # to that passage/book.  Cross-period evidence remains eligible only
        # when its authored passage link says so and explains why.
        if query_refs and not matching_links:
            continue

        searchable = normalize_text(
            " ".join(
                (
                    item.title,
                    item.description,
                    item.primary_observation,
                    item.scholarly_interpretation,
                    item.passage_relevance,
                    item.confidence_rationale,
                    item.evidence_type,
                )
            )
        )
        item_terms = set(_meaningful_terms(searchable))
        matched_terms = tuple(sorted(set(query_terms) & item_terms))
        reasons: list[str] = []
        score = 0.0
        if matched_terms:
            coverage = len(matched_terms) / max(len(set(query_terms)), 1)
            score += min(0.48, 0.16 + (0.42 * coverage))
            reasons.append("query overlap: " + ", ".join(matched_terms))
        if matching_links:
            strongest_weight = max(int(link.get("weight") or 1) for link in matching_links)
            score += min(0.32, 0.18 + (strongest_weight * 0.014))
            reasons.append("explicit passage relationship")

        dimension_matches = sorted(
            dimension
            for dimension in requested
            if item.evidence_type in _DIMENSION_TYPES.get(dimension, frozenset())
        )
        if dimension_matches:
            score += min(0.16, 0.08 + 0.025 * len(dimension_matches))
            reasons.append("requested evidence dimension: " + ", ".join(dimension_matches))
        score += _CONFIDENCE_SCORE.get(item.confidence, 0.0)
        score += _ASSERTION_SCORE.get(item.assertion_type, 0.0)
        selected_sources = [sources[source_id] for source_id in item.source_ids if source_id in sources]
        if selected_sources:
            source_quality = max(
                _SOURCE_QUALITY_SCORE.get(str(source.get("source_type") or "other"), 0.0)
                for source in selected_sources
            )
            score += source_quality
            reasons.append(
                "source provenance: "
                + ", ".join(
                    sorted({str(source.get("source_type") or "other") for source in selected_sources})
                )
            )
        if item.confidence_rationale:
            score += 0.03
            reasons.append("confidence is explained")
        if parent_relevance > 0:
            score += min(0.10, max(0.0, float(parent_relevance)) * 0.10)

        applicable_links = matching_links or links
        chronological_relation = _strongest_temporal_relation(applicable_links)
        passage_relationship = _strongest_passage_relationship(applicable_links)
        score += _TEMPORAL_SCORE.get(chronological_relation, -0.10)
        reasons.append("chronology: " + chronological_relation)
        if not query_refs and not matched_terms and not dimension_matches:
            continue
        if score <= 0:
            continue

        ranked.append(
            RetrievedEvidenceItem(
                parent_object_id=str(parent_data.get("id") or ""),
                parent_title=str(parent_data.get("title") or ""),
                evidence_id=item.id,
                title=item.title,
                evidence_type=item.evidence_type,
                description=item.description,
                assertion_type=item.assertion_type,
                confidence=item.confidence,
                confidence_rationale=item.confidence_rationale,
                passage_relevance=item.passage_relevance,
                certainty=item.certainty,
                dispute_status=item.dispute_status,
                primary_observation=item.primary_observation,
                scholarly_interpretation=item.scholarly_interpretation,
                temporal_scope=item.temporal_scope.to_dict(),
                passage_relationship=passage_relationship,
                chronological_relation=chronological_relation,
                scripture_references=tuple(matching_links or links),
                sources=tuple(dict(source) for source in selected_sources),
                claims=tuple(dict(claims[claim_id]) for claim_id in item.claim_ids if claim_id in claims),
                related_objects=tuple(relationship.to_dict() for relationship in item.related_objects),
                related_evidence=tuple(relationship.to_dict() for relationship in item.related_evidence),
                external_references=tuple(reference.to_dict() for reference in item.external_references),
                metadata=dict(item.metadata),
                retrieval_score=round(min(score, 1.0), 4),
                retrieval_reason=tuple(reasons),
                matched_terms=matched_terms,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.retrieval_score,
            _passage_relationship_sort_rank(item.passage_relationship),
            _temporal_sort_rank(item.chronological_relation),
            item.evidence_id,
        )
    )
    return ranked[:limit]


def _mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _meaningful_terms(value: str) -> list[str]:
    return [term for term in tokenize_query(value) if term not in STOP_WORDS and len(term) > 1]


def _reference_overlap(left: str, right: str) -> bool:
    left_book, left_chapter = _reference_book_chapter(left)
    right_book, right_chapter = _reference_book_chapter(right)
    if not left_book or not right_book or left_book != right_book:
        return False
    if left_chapter is None or right_chapter is None:
        return True
    return left_chapter == right_chapter


def _reference_book_chapter(value: str) -> tuple[str, int | None]:
    text = str(value or "").strip()
    match = re.match(r"^(.+?)\s+(\d+)(?::|\s|$)", text)
    if match is None:
        return normalize_text(text), None
    return normalize_text(match.group(1)), int(match.group(2))


def _strongest_temporal_relation(links: Sequence[Mapping[str, Any]]) -> str:
    priority = (
        "contemporary",
        "near-contemporary",
        "earlier-comparative",
        "later-comparative",
        "diachronic",
        "unknown",
    )
    values = {str(link.get("temporal_relation") or "unknown") for link in links}
    return next((value for value in priority if value in values), "unknown")


def _strongest_passage_relationship(links: Sequence[Mapping[str, Any]]) -> str:
    values = {str(link.get("relationship") or "disputed") for link in links}
    return min(values, key=_passage_relationship_sort_rank) if values else "disputed"


def _passage_relationship_sort_rank(value: str) -> int:
    order = {
        "direct": 0,
        "contextual": 1,
        "contrast": 2,
        "comparative": 3,
        "disputed": 4,
    }
    return order.get(value, 5)


def _temporal_sort_rank(value: str) -> int:
    order = {
        "contemporary": 0,
        "near-contemporary": 1,
        "earlier-comparative": 2,
        "later-comparative": 3,
        "diachronic": 4,
        "unknown": 5,
    }
    return order.get(value, 6)
