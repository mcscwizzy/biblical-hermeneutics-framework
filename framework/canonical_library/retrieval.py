"""Retrieval interfaces and deterministic ranking helpers for CKL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping, Protocol

from .normalization import STOP_WORDS, normalize_alias, normalize_id, normalize_text, tokenize_query

FIELD_WEIGHTS: dict[str, int] = {
    "id": 12,
    "title": 12,
    "aliases": 10,
    "common_questions": 8,
    "summary": 7,
    "hebrew_words": 7,
    "greek_words": 7,
    "related_objects": 6,
    "related_people": 6,
    "related_places": 6,
    "related_events": 6,
    "scripture_references": 5,
    "covenantal_significance": 5,
    "intertextuality": 5,
    "historical_context": 3,
    "ancient_near_east_context": 3,
    "literary_context": 3,
    "interpretive_notes": 2,
}

MAX_FIELD_WEIGHT = max(FIELD_WEIGHTS.values())

if TYPE_CHECKING:
    from .loader import CanonicalLibrary
    from .schema import CanonicalObject


@dataclass(frozen=True)
class RetrievalResult:
    object: "CanonicalObject"
    score: float
    match_type: str
    matched_terms: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    matched_alias: str | None = None


class CanonicalRetriever(Protocol):
    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        ...


class ExactCanonicalRetriever:
    """Adapter that exposes exact retrieval through the retriever protocol."""

    def __init__(self, library: "CanonicalLibrary") -> None:
        self._library = library

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:
        result = self._library.retrieve_exact(query)
        if result is None:
            return []
        return [result][:limit]


class FutureSemanticRetriever:
    """Placeholder for a future embedding-backed retriever."""

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:  # noqa: ARG002
        raise NotImplementedError("semantic retrieval is not implemented yet")


class FutureHybridRetriever:
    """Placeholder for a future exact-plus-semantic retriever."""

    def retrieve(self, query: str, limit: int = 10) -> list[RetrievalResult]:  # noqa: ARG002
        raise NotImplementedError("hybrid retrieval is not implemented yet")


def canonical_search_terms(*values: str) -> set[str]:
    """Return stop-word-filtered search tokens for one object."""

    terms: set[str] = set()
    for value in values:
        for token in tokenize_query(value):
            if token and token not in STOP_WORDS:
                terms.add(token)
    return terms


def _mapping_values(value: Any, keys: tuple[str, ...]) -> list[str]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        return []
    values: list[str] = []
    for key in keys:
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            values.append(item)
    return values


def field_search_terms(field_name: str, value: Any) -> set[str]:
    if value is None:
        return set()
    if field_name in {
        "id",
        "title",
        "summary",
        "historical_context",
        "ancient_near_east_context",
        "literary_context",
        "covenantal_significance",
    }:
        if isinstance(value, str):
            return canonical_search_terms(value)
        return set()
    if field_name in {
        "aliases",
        "common_questions",
        "intertextuality",
        "hebrew_words",
        "greek_words",
        "interpretive_notes",
        "related_people",
        "related_places",
        "related_events",
    }:
        terms: set[str] = set()
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    terms.update(canonical_search_terms(item))
        return terms
    if field_name == "related_objects":
        terms: set[str] = set()
        if isinstance(value, list):
            for item in value:
                terms.update(canonical_search_terms(*_mapping_values(item, ("id", "relationship", "notes"))))
        return terms
    if field_name == "scripture_references":
        terms: set[str] = set()
        if isinstance(value, list):
            for item in value:
                terms.update(canonical_search_terms(*_mapping_values(item, ("reference", "relationship", "notes"))))
        return terms
    return set()


def collect_field_search_terms(obj: Any) -> dict[str, set[str]]:
    field_terms: dict[str, set[str]] = {}
    for field_name in FIELD_WEIGHTS:
        terms = field_search_terms(field_name, getattr(obj, field_name, None))
        if terms:
            field_terms[field_name] = terms
    return field_terms


def score_keyword_result(
    *,
    query_terms: list[str],
    field_terms: Mapping[str, set[str]],
    importance: int,
) -> tuple[float, list[str], list[str]]:
    """Score a deterministic keyword hit.

    The score is based on exact token overlap and a small importance bonus.
    It is a ranking value, not a semantic confidence measure.
    """

    matched_terms: list[str] = []
    matched_fields: list[str] = []
    score_total = 0.0

    for term in query_terms:
        term_fields = [field_name for field_name in FIELD_WEIGHTS if term in field_terms.get(field_name, set())]
        if not term_fields:
            continue
        matched_terms.append(term)
        for field_name in term_fields:
            if field_name not in matched_fields:
                matched_fields.append(field_name)
        score_total += max(FIELD_WEIGHTS[field_name] for field_name in term_fields)

    if not matched_terms:
        return 0.0, [], []

    query_coverage = score_total / max(MAX_FIELD_WEIGHT * len(query_terms), 1)
    importance_bonus = min(max(importance, 0), 100) / 1000.0
    score = query_coverage + importance_bonus
    return round(min(score, 1.0), 4), matched_terms, matched_fields


def sort_retrieval_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    """Sort results deterministically by score, title, and id."""

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            normalize_text(result.object.title),
            normalize_id(result.object.id),
        ),
    )
