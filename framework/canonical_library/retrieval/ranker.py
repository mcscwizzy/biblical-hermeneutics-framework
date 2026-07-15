"""Deterministic ranking helpers for CKL search."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Mapping, Sequence

from ..normalization import normalize_text
from .legacy import query_search_terms, score_keyword_result
from .models import CKLSearchResult, QueryAnalysis, ScoreSignal
from .tokenizer import normalize_query


TITLE_MATCH_WEIGHT = 100.0
ALIAS_MATCH_WEIGHT = 90.0
SCRIPTURE_MATCH_WEIGHT = 85.0
PHRASE_MATCH_WEIGHT = 70.0
KEYWORD_MATCH_WEIGHT = 100.0
THEME_MATCH_WEIGHT = 30.0
FACT_MATCH_WEIGHT = 20.0
RELATED_MATCH_WEIGHT = 10.0
CATEGORY_MATCH_WEIGHT = 15.0
MAX_RAW_SCORE = 100.0

RANKING_BOILERPLATE_TERMS = {
    "important",
    "importance",
    "meaning",
    "mean",
    "significant",
    "significance",
}

FIELD_QUALITY_WEIGHTS: dict[str, float] = {
    "id": 1.0,
    "title": 1.0,
    "aliases": 0.98,
    "common_questions": 0.96,
    "summary": 0.9,
    "scripture_references": 0.95,
    "themes": 0.9,
    "facts": 0.9,
    "cross_references": 0.85,
    "new_testament_connections": 0.85,
    "archaeology": 0.85,
    "historical_context": 0.8,
    "literary_context": 0.8,
    "ancient_near_east_context": 0.75,
    "covenantal_significance": 0.7,
    "intertextuality": 0.75,
    "timeline": 0.75,
    "maps": 0.75,
    "related_objects": 0.65,
    "related_people": 0.65,
    "related_places": 0.65,
    "related_events": 0.65,
    "interpretive_notes": 0.6,
}


def score_indexed_entry(
    analysis: QueryAnalysis,
    entry: Any,
    *,
    related_hit_ids: Sequence[str] | None = None,
    debug: bool = False,
) -> CKLSearchResult | None:
    """Score one indexed CKL entry against an analyzed query."""

    normalized_query = analysis.normalized_query.lower()
    title = str(getattr(entry, "title", "") or "")
    normalized_title = normalize_query(title).lower()
    aliases = list(getattr(entry, "aliases", []) or [])
    normalized_aliases = [normalize_query(alias).lower() for alias in aliases]
    category = str(getattr(entry, "category", getattr(entry, "type", "")) or "").strip()
    theme_terms = set(getattr(entry, "theme_terms", []) or [])
    fact_terms = set(getattr(entry, "fact_terms", []) or [])
    high_signal_text = normalize_text(str(getattr(entry, "high_signal_text", "") or ""))
    searchable_text = high_signal_text or normalize_text(str(getattr(entry, "search_text", "") or ""))
    scripture_spans = list(getattr(entry, "scripture_spans", []) or [])
    field_terms: Mapping[str, set[str]] = getattr(entry, "field_terms", {}) or {}
    related_entries = set(getattr(entry, "related_entries", []) or [])
    related_edges = list(getattr(entry, "related_edges", []) or [])

    signals: list[ScoreSignal] = []
    matched_terms: list[str] = []
    matched_fields: list[str] = []
    score = 0.0

    def add_signal(name: str, value: float, *, terms: list[str] | None = None, fields: list[str] | None = None, note: str | None = None) -> None:
        nonlocal score
        if value <= 0:
            return
        score = min(MAX_RAW_SCORE, score + value)
        signal = ScoreSignal(
            name=name,
            value=round(value, 4),
            matched_terms=list(dict.fromkeys(terms or [])),
            matched_fields=list(dict.fromkeys(fields or [])),
            note=note,
        )
        signals.append(signal)
        if terms:
            for term in terms:
                if term not in matched_terms:
                    matched_terms.append(term)
        if fields:
            for field_name in fields:
                if field_name not in matched_fields:
                    matched_fields.append(field_name)

    # Exact title and alias matches are the strongest signals.
    if normalized_query and normalized_query == normalized_title:
        add_signal("exact_title", TITLE_MATCH_WEIGHT, terms=[title], fields=["title"])
    elif normalized_query and normalized_query in normalized_title:
        add_signal("title_phrase", PHRASE_MATCH_WEIGHT, terms=[title], fields=["title"])

    if normalized_query and normalized_query in normalized_aliases:
        matched_alias = next(
            (alias for alias, normalized in zip(aliases, normalized_aliases) if normalized == normalized_query),
            None,
        )
        add_signal("alias_match", ALIAS_MATCH_WEIGHT, terms=[matched_alias or title], fields=["aliases"])

    # Scripture references are a high-confidence signal.
    scripture_matches: list[str] = []
    for query_reference in analysis.scripture_references:
        for candidate in scripture_spans:
            if query_reference.book != candidate.book:
                continue
            if not _spans_overlap(query_reference, candidate):
                continue
            scripture_matches.append(_format_reference(candidate))
    if scripture_matches:
        add_signal(
            "scripture_match",
            min(SCRIPTURE_MATCH_WEIGHT, SCRIPTURE_MATCH_WEIGHT * min(len(scripture_matches), 3) / 3),
            terms=scripture_matches,
            fields=["scripture_references"],
        )

    # Exact protected phrases or exact query phrases found in the searchable text.
    phrase_matches: list[str] = []
    for phrase in analysis.phrases:
        if phrase in searchable_text:
            phrase_matches.append(phrase)
    if normalized_query and normalized_query in searchable_text:
        phrase_matches.append(normalized_query)
    if phrase_matches:
        add_signal(
            "exact_phrase",
            min(PHRASE_MATCH_WEIGHT, PHRASE_MATCH_WEIGHT * min(len(phrase_matches), 3) / 3),
            terms=phrase_matches,
            fields=["summary", "title", "aliases"],
        )

    # Keyword overlap uses the deterministic CKL vocabulary and keeps field
    # quality in the loop so low-signal matches do not dominate the results.
    keyword_terms = [term for term in (analysis.terms or query_search_terms(analysis.raw_query)) if term not in RANKING_BOILERPLATE_TERMS]
    if not keyword_terms:
        keyword_terms = analysis.terms or query_search_terms(analysis.raw_query)
    keyword_score, keyword_overlap, keyword_fields = score_keyword_result(
        query_terms=keyword_terms,
        field_terms=field_terms,
        importance=int(getattr(entry, "importance", 0) or 0),
    )
    if keyword_overlap:
        keyword_quality = _field_quality_multiplier(keyword_fields)
        direct_keyword_fields = {"id", "title", "aliases", "scripture_references"}
        direct_keyword_hit = bool(direct_keyword_fields.intersection(keyword_fields))
        value = KEYWORD_MATCH_WEIGHT * keyword_score * keyword_quality
        if not direct_keyword_hit:
            value *= 0.6
        add_signal(
            "keyword_match",
            value,
            terms=keyword_overlap,
            fields=keyword_fields,
        )

    # Theme terms get a separate bump when the result is thematic.
    theme_overlap = [term for term in analysis.terms if term in theme_terms]
    if theme_overlap:
        coverage = len(theme_overlap) / max(len(analysis.terms), 1)
        add_signal("theme_match", THEME_MATCH_WEIGHT * min(1.0, coverage), terms=theme_overlap, fields=["themes"])

    # Fact body overlap is lower confidence but still useful.
    fact_overlap = [term for term in analysis.terms if term in fact_terms]
    if fact_overlap:
        coverage = len(fact_overlap) / max(len(analysis.terms), 1)
        add_signal("fact_match", FACT_MATCH_WEIGHT * min(1.0, coverage), terms=fact_overlap, fields=["summary", "facts"])

    # Related expansion is only applied when a result is already on the board.
    related_overlap = []
    for related_id in related_hit_ids or []:
        if related_id in related_entries:
            related_overlap.append(related_id)
        if any(edge.get("id") == related_id for edge in related_edges):
            related_overlap.append(related_id)
    if related_overlap:
        add_signal("related_entry", RELATED_MATCH_WEIGHT * min(1.0, len(related_overlap) / 2), terms=related_overlap, fields=["related_entries"])

    if category and category in analysis.object_categories and _should_apply_category_bonus(
        signals,
        keyword_fields=keyword_fields,
    ):
        add_signal("category_match", CATEGORY_MATCH_WEIGHT, terms=[category], fields=["category"])

    if score <= 0:
        return None

    normalized_score = round(min(score / MAX_RAW_SCORE, 1.0), 4)
    return CKLSearchResult(
        id=str(getattr(entry, "id")),
        category=category,
        title=title,
        score=normalized_score,
        matched_terms=matched_terms,
        matched_fields=matched_fields,
        summary=str(getattr(entry, "summary", "") or ""),
        source_path=str(getattr(entry, "source_path", "") or "") or None,
        aliases=aliases,
        scripture_references=[_format_reference(candidate) for candidate in scripture_spans],
        themes=list(dict.fromkeys(_coerce_str_list(getattr(entry, "themes", []) or []))),
        related_entries=list(dict.fromkeys(_coerce_str_list(getattr(entry, "related_entries", []) or []))),
        content_status=str(getattr(entry, "content_status", "") or "") or None,
        review_status=str(getattr(entry, "review_status", "") or "") or None,
        confidence=str(getattr(entry, "confidence", "") or "") or None,
        importance=int(getattr(entry, "importance", 0) or 0),
        score_details=signals if debug else [],
    )


def score_indexed_candidates(
    analysis: QueryAnalysis,
    candidates: Sequence[Any],
    *,
    related_hit_ids: Sequence[str] | None = None,
    debug: bool = False,
) -> list[CKLSearchResult]:
    results: list[CKLSearchResult] = []
    for entry in candidates:
        scored = score_indexed_entry(
            analysis,
            entry,
            related_hit_ids=related_hit_ids,
            debug=debug,
        )
        if scored is not None:
            results.append(scored)
    return results


def _field_quality_multiplier(fields: Sequence[str]) -> float:
    quality = 0.0
    for field_name in fields:
        quality = max(quality, FIELD_QUALITY_WEIGHTS.get(field_name, 0.5))
    return quality or 0.5


def _should_apply_category_bonus(
    signals: Sequence[ScoreSignal],
    *,
    keyword_fields: Sequence[str],
) -> bool:
    direct_keyword_fields = {"id", "title", "aliases", "scripture_references"}
    if direct_keyword_fields.intersection(keyword_fields):
        return True
    for signal in signals:
        if signal.name in {"exact_title", "alias_match", "scripture_match", "exact_phrase"}:
            return True
    return False


def _coerce_str_list(values: Sequence[Any]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _format_reference(span: Any) -> str:
    if hasattr(span, "book"):
        book = getattr(span, "book")
        start_chapter = getattr(span, "start_chapter", None)
        start_verse = getattr(span, "start_verse", None)
        end_chapter = getattr(span, "end_chapter", None)
        end_verse = getattr(span, "end_verse", None)
        reference = str(book)
        if start_chapter is not None:
            reference += f" {start_chapter}"
        if start_verse is not None:
            reference += f":{start_verse}"
        if end_chapter is not None or end_verse is not None:
            if end_chapter is not None and end_chapter != start_chapter:
                reference += f"-{end_chapter}"
            if end_verse is not None:
                reference += f":{end_verse}"
        return reference
    return str(span)


def _spans_overlap(first: Any, second: Any) -> bool:
    if getattr(first, "book", None) != getattr(second, "book", None):
        return False
    first_start = _range_start(first)
    first_end = _range_end(first)
    second_start = _range_start(second)
    second_end = _range_end(second)
    return not (second_end < first_start or first_end < second_start)


def _range_start(span: Any) -> tuple[int, int]:
    chapter = getattr(span, "start_chapter", None)
    verse = getattr(span, "start_verse", None)
    if chapter is None:
        return (0, 0)
    if verse is None:
        verse_value = 1
    else:
        verse_value = int(verse or 0)
    return (int(chapter), verse_value)


def _range_end(span: Any) -> tuple[int, int]:
    start_chapter = getattr(span, "start_chapter", None)
    end_chapter = getattr(span, "end_chapter", None)
    start_verse = getattr(span, "start_verse", None)
    end_verse = getattr(span, "end_verse", None)
    if start_chapter is None:
        return (0, 0)
    if end_chapter is None:
        end_chapter = start_chapter
    if end_verse is not None:
        return (int(end_chapter), int(end_verse))
    if start_verse is not None:
        return (int(end_chapter), int(start_verse))
    return (int(end_chapter), 999)
