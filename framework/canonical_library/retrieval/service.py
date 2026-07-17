"""Framework-owned deterministic CKL retrieval service."""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..normalization import normalize_alias
from .indexer import CKLIndex, IndexedCKLEntry, load_index
from .models import CKLIndexStats, CKLSearchResponse, CKLSearchResult, QueryAnalysis
from .ranker import score_indexed_entry
from .tokenizer import analyze_query, normalize_query


class CKLRetrievalService:
    """Deterministic search service over the Canonical Knowledge Library."""

    def __init__(
        self,
        *,
        index: CKLIndex | None = None,
        library: Any | None = None,
        root: str | Path | None = None,
        relevance_threshold: float = 0.45,
        max_results_per_category: int = 3,
        max_related_results: int = 4,
    ) -> None:
        self.relevance_threshold = float(relevance_threshold)
        self.max_results_per_category = int(max_results_per_category)
        self.max_related_results = int(max_related_results)

        if index is not None:
            self.index = index
        elif library is not None:
            self.index = CKLIndex.from_library(library)
        else:
            self.index = load_index(root)

    @classmethod
    def load_default(cls) -> "CKLRetrievalService":
        return load_service()

    def search(
        self,
        query: str,
        limit: int = 8,
        *,
        min_score: float | None = None,
        debug: bool = False,
    ) -> CKLSearchResponse:
        normalized_query = normalize_query(query)
        analysis = analyze_query(
            query,
            book_alias_lookup=self.index.book_alias_lookup,
            title_index=self.index.title_index,
            alias_index=self.index.alias_index,
            entries_by_id=self.index.entries_by_id,
        )
        threshold = float(self.relevance_threshold if min_score is None else min_score)

        candidate_entries = self._collect_candidates(analysis)
        related_seed_ids: list[str] = []
        direct_scores: dict[str, CKLSearchResult] = {}
        result_sources: dict[str, int] = {}

        for entry in candidate_entries:
            scored = score_indexed_entry(analysis, entry, debug=debug)
            if scored is None or scored.score < threshold:
                continue
            direct_scores[scored.id] = scored
            result_sources[scored.id] = 0
            if scored.score >= 0.7:
                related_seed_ids.append(scored.id)

        related_scores: dict[str, CKLSearchResult] = {}
        if related_seed_ids and self.max_related_results > 0:
            related_candidates = self._collect_related_candidates(related_seed_ids)
            for entry in related_candidates:
                if entry.id in direct_scores:
                    continue
                scored = score_indexed_entry(
                    analysis,
                    entry,
                    related_hit_ids=related_seed_ids,
                    debug=debug,
                )
                if scored is None or scored.score < threshold:
                    continue
                if scored.score < 0.1:
                    continue
                related_scores[scored.id] = scored
                result_sources.setdefault(scored.id, 1)

        merged = list(direct_scores.values()) + list(related_scores.values())
        results = self._rank_and_limit(
            merged,
            limit=limit,
            threshold=threshold,
            query=query,
            result_sources=result_sources,
        )

        response = CKLSearchResponse(
            query=query,
            normalized_query=normalized_query,
            analysis=analysis,
            results=results,
            stats=self.index.stats,
        )
        return response

    def to_dict(
        self,
        query: str,
        limit: int = 8,
        *,
        min_score: float | None = None,
        debug: bool = False,
    ) -> dict[str, Any]:
        return self.search(query, limit=limit, min_score=min_score, debug=debug).to_dict(debug=debug)

    def _collect_candidates(self, analysis: QueryAnalysis) -> list[IndexedCKLEntry]:
        candidate_ids: set[str] = set()

        normalized_query = analysis.normalized_query.lower()
        if normalized_query:
            candidate_ids.update(self.index.title_index.get(normalized_query, set()))
            candidate_ids.update(self.index.alias_index.get(normalized_query, set()))

        for phrase in analysis.phrases:
            phrase_normalized = phrase.lower()
            for entry in self.index.iter_entries():
                high_signal_text = normalize_query(str(getattr(entry, "high_signal_text", "") or "")).lower()
                if phrase_normalized in high_signal_text:
                    candidate_ids.add(entry.id)

        for reference in analysis.scripture_references:
            candidate_ids.update(self.index.scripture_index.get(reference.book, set()))

        for term in analysis.terms:
            candidate_ids.update(self.index.keyword_index.get(term, set()))

        for category in analysis.object_categories:
            candidate_ids.update(self.index.category_index.get(category, set()))

        if not candidate_ids and normalized_query:
            for entry in self.index.iter_entries():
                if normalized_query in entry.search_text:
                    candidate_ids.add(entry.id)

        return [self.index.entries_by_id[entry_id] for entry_id in sorted(candidate_ids) if entry_id in self.index.entries_by_id]

    def _collect_related_candidates(self, seed_ids: Sequence[str]) -> list[IndexedCKLEntry]:
        candidate_ids: set[str] = set()
        for seed_id in seed_ids:
            candidate_ids.update(self.index.related_index.get(seed_id, set()))
            candidate_ids.update(self.index.reverse_related_index.get(seed_id, set()))
        candidate_ids.difference_update(seed_ids)
        return [self.index.entries_by_id[entry_id] for entry_id in sorted(candidate_ids) if entry_id in self.index.entries_by_id]

    def _rank_and_limit(
        self,
        results: Sequence[CKLSearchResult],
        *,
        limit: int,
        threshold: float,
        query: str,
        result_sources: Mapping[str, int] | None = None,
    ) -> list[CKLSearchResult]:
        deduped: dict[str, CKLSearchResult] = {}
        for result in results:
            existing = deduped.get(result.id)
            if existing is None or result.score > existing.score:
                deduped[result.id] = result

        query_alignment = {result.id: _result_alignment_rank(query, result) for result in deduped.values()}
        ordered = sorted(
            deduped.values(),
            key=lambda result: (
                query_alignment.get(result.id, 3),
                (result_sources or {}).get(result.id, 1),
                -result.score,
                -result.importance,
                -len(result.scripture_references),
                -len(result.matched_terms),
                result.category,
                normalize_query(result.title).lower(),
                result.id,
            ),
        )

        limited: list[CKLSearchResult] = []
        category_counts: dict[str, int] = {}
        seen_signatures: set[str] = set()
        for result in ordered:
            if result.score < threshold:
                continue
            category_count = category_counts.get(result.category, 0)
            if category_count >= self.max_results_per_category:
                continue
            signatures = _result_signatures(result)
            if signatures and seen_signatures.intersection(signatures):
                continue
            limited.append(result)
            category_counts[result.category] = category_count + 1
            seen_signatures.update(signatures)
            if len(limited) >= limit:
                break
        return limited


def load_service(
    root: str | Path | None = None,
    *,
    refresh: bool = False,
    relevance_threshold: float = 0.45,
    max_results_per_category: int = 3,
    max_related_results: int = 4,
) -> CKLRetrievalService:
    index = load_index(root, refresh=refresh)
    return CKLRetrievalService(
        index=index,
        relevance_threshold=relevance_threshold,
        max_results_per_category=max_results_per_category,
        max_related_results=max_related_results,
    )


def search(
    query: str,
    limit: int = 8,
    *,
    root: str | Path | None = None,
    refresh: bool = False,
    debug: bool = False,
    min_score: float | None = None,
    relevance_threshold: float = 0.45,
    max_results_per_category: int = 3,
    max_related_results: int = 4,
) -> dict[str, Any]:
    service = load_service(
        root,
        refresh=refresh,
        relevance_threshold=relevance_threshold,
        max_results_per_category=max_results_per_category,
        max_related_results=max_related_results,
    )
    return service.to_dict(query, limit=limit, min_score=min_score, debug=debug)


_SIGNATURE_STRIP_WORDS = {
    "faq",
    "guide",
    "notes",
    "note",
    "overview",
    "question",
    "questions",
    "study",
    "summary",
    "theme",
    "themes",
    "theology",
    "theologies",
    "doctrine",
    "doctrines",
    "topic",
    "topics",
    "entry",
    "entries",
    "article",
    "articles",
    "meaning",
    "significance",
    "importance",
    "concept",
    "concepts",
    "book",
}


def _result_alignment_rank(query: str, result: CKLSearchResult) -> int:
    normalized_query = normalize_query(query).lower()
    if not normalized_query:
        return 3

    normalized_title = normalize_query(result.title).lower()
    normalized_aliases = [normalize_query(alias).lower() for alias in result.aliases if normalize_query(alias)]
    if normalized_query == normalized_title or normalized_query in normalized_aliases:
        return 0

    query_signature = _signature_text(query)
    candidate_signatures = _result_signatures(result)
    if query_signature and query_signature in candidate_signatures:
        return 1

    if query_signature:
        for signature in candidate_signatures:
            if _signature_is_related(query_signature, signature):
                return 2

    return 3


def _result_signatures(result: CKLSearchResult) -> list[str]:
    signatures: list[str] = []
    for value in [result.title, *result.aliases]:
        signature = _signature_text(value)
        if signature and signature not in signatures:
            signatures.append(signature)
    return signatures


def _signature_text(value: str) -> str:
    tokens: list[str] = []
    for token in normalize_alias(value).split():
        if not token or token in _SIGNATURE_STRIP_WORDS:
            continue
        if token not in tokens:
            tokens.append(token)
    return " ".join(tokens)


def _signature_is_related(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    if left in right or right in left:
        return True
    return SequenceMatcher(None, left, right).ratio() >= 0.9
