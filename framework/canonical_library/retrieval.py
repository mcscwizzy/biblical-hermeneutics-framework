"""Retrieval interfaces and deterministic ranking helpers for CKL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from .normalization import STOP_WORDS, normalize_alias, normalize_id, normalize_text, tokenize_query

if TYPE_CHECKING:
    from .loader import CanonicalLibrary
    from .schema import CanonicalObject


@dataclass(frozen=True)
class RetrievalResult:
    object: "CanonicalObject"
    score: float
    match_type: str
    matched_terms: list[str] = field(default_factory=list)
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


def score_keyword_result(
    *,
    query_terms: list[str],
    object_terms: set[str],
    importance: int,
) -> tuple[float, list[str]]:
    """Score a deterministic keyword hit.

    The score is based on exact token overlap and a small importance bonus.
    It is a ranking value, not a semantic confidence measure.
    """

    matched_terms = [term for term in query_terms if term in object_terms]
    if not matched_terms:
        return 0.0, []

    query_coverage = len(matched_terms) / max(len(query_terms), 1)
    object_coverage = len(matched_terms) / max(len(object_terms), 1)
    importance_bonus = min(max(importance, 0), 100) / 1000.0
    score = (0.75 * query_coverage) + (0.2 * object_coverage) + importance_bonus
    return round(min(score, 1.0), 4), matched_terms


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

