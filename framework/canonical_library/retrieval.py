"""Retrieval interfaces and deterministic ranking helpers for CKL."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping, Protocol

from .normalization import STOP_WORDS, normalize_alias, normalize_id, normalize_text, tokenize_query

FIELD_WEIGHTS: dict[str, int] = {
    "id": 12,
    "title": 12,
    "aliases": 10,
    "common_questions": 8,
    "summary": 7,
    "authorship_positions": 6,
    "date_ranges": 5,
    "original_audience": 7,
    "historical_setting": 7,
    "genre": 6,
    "structure": 5,
    "major_themes": 7,
    "canonical_placement": 6,
    "key_people": 6,
    "key_places": 6,
    "key_events": 6,
    "interpretive_disputes": 5,
    "primary_sources": 6,
    "hebrew_words": 7,
    "greek_words": 7,
    "related_objects": 6,
    "related_people": 6,
    "related_places": 6,
    "related_events": 6,
    "scripture_references": 5,
    "covenantal_significance": 5,
    "intertextuality": 5,
    "cross_references": 4,
    "new_testament_connections": 4,
    "archaeology": 4,
    "historical_context": 3,
    "ancient_near_east_context": 3,
    "literary_context": 3,
    "timeline": 3,
    "maps": 3,
    "interpretive_notes": 2,
}

MAX_FIELD_WEIGHT = max(FIELD_WEIGHTS.values())

MATCH_TYPE_PRIORITY: dict[str, int] = {
    "id": 0,
    "alias": 1,
    "scripture": 1,
    "title": 2,
    "phrase": 3,
    "fuzzy_alias": 4,
    "keyword": 5,
    "relationship": 6,
}

SEARCH_STOP_WORDS = frozenset(
    STOP_WORDS
    | {
        "am",
        "are",
        "be",
        "been",
        "being",
        "can",
        "could",
        "did",
        "do",
        "does",
        "done",
        "explain",
        "find",
        "give",
        "help",
        "how",
        "may",
        "might",
        "must",
        "please",
        "say",
        "show",
        "shall",
        "should",
        "tell",
        "was",
        "were",
        "will",
        "would",
        "whom",
        "whose",
        "you",
        "your",
        "my",
        "our",
        "their",
        "them",
        "us",
        "it",
        "this",
        "that",
        "these",
        "those",
        "as",
        "by",
        "from",
        "in",
        "of",
        "on",
        "to",
        "with",
        "or",
        "and",
    }
)

EXACT_MATCH_BONUS: dict[str, float] = {
    "id": 0.55,
    "title": 0.52,
    "aliases": 0.48,
    "common_questions": 0.42,
    "summary": 0.28,
    "authorship_positions": 0.22,
    "date_ranges": 0.2,
    "original_audience": 0.24,
    "historical_setting": 0.24,
    "genre": 0.22,
    "structure": 0.2,
    "major_themes": 0.26,
    "canonical_placement": 0.22,
    "key_people": 0.22,
    "key_places": 0.22,
    "key_events": 0.22,
    "interpretive_disputes": 0.2,
    "primary_sources": 0.22,
    "historical_context": 0.2,
    "ancient_near_east_context": 0.2,
    "literary_context": 0.2,
    "covenantal_significance": 0.22,
    "scripture_references": 0.32,
    "related_objects": 0.22,
    "related_people": 0.18,
    "related_places": 0.18,
    "related_events": 0.18,
    "cross_references": 0.16,
    "new_testament_connections": 0.16,
    "timeline": 0.14,
    "maps": 0.14,
    "archaeology": 0.18,
    "interpretive_notes": 0.14,
    "hebrew_words": 0.16,
    "greek_words": 0.16,
}

PHRASE_MATCH_BONUS: dict[str, float] = {
    "id": 0.42,
    "title": 0.4,
    "aliases": 0.38,
    "common_questions": 0.34,
    "summary": 0.24,
    "authorship_positions": 0.18,
    "date_ranges": 0.16,
    "original_audience": 0.2,
    "historical_setting": 0.2,
    "genre": 0.18,
    "structure": 0.16,
    "major_themes": 0.2,
    "canonical_placement": 0.18,
    "key_people": 0.18,
    "key_places": 0.18,
    "key_events": 0.18,
    "interpretive_disputes": 0.16,
    "primary_sources": 0.18,
    "historical_context": 0.16,
    "ancient_near_east_context": 0.16,
    "literary_context": 0.16,
    "covenantal_significance": 0.18,
    "scripture_references": 0.22,
    "related_objects": 0.18,
    "related_people": 0.16,
    "related_places": 0.16,
    "related_events": 0.16,
    "cross_references": 0.14,
    "new_testament_connections": 0.14,
    "timeline": 0.12,
    "maps": 0.12,
    "archaeology": 0.16,
    "interpretive_notes": 0.12,
    "hebrew_words": 0.14,
    "greek_words": 0.14,
}

FUZZY_MATCH_MULTIPLIER: dict[str, float] = {
    "title": 0.9,
    "aliases": 0.86,
    "common_questions": 0.82,
    "summary": 0.62,
}

CATEGORY_QUERY_HINTS: dict[str, frozenset[str]] = {
    "person": frozenset(
        {
            "who",
            "whom",
            "whose",
            "man",
            "woman",
            "person",
            "people",
            "king",
            "queen",
            "prophet",
            "apostle",
            "disciple",
            "father",
            "mother",
            "son",
            "daughter",
            "brother",
            "sister",
        }
    ),
    "place": frozenset(
        {
            "where",
            "place",
            "location",
            "site",
            "city",
            "town",
            "land",
            "mount",
            "mountain",
            "valley",
            "river",
            "desert",
            "region",
        }
    ),
    "event": frozenset(
        {
            "when",
            "event",
            "buried",
            "burial",
            "renewal",
            "battle",
            "birth",
            "death",
            "exile",
            "exodus",
            "crucifixion",
            "resurrection",
            "journey",
            "call",
        }
    ),
    "book": frozenset({"book", "chapter", "verse", "passage", "gospel", "epistle", "letter", "psalm"}),
    "word_study": frozenset({"word", "meaning", "hebrew", "greek", "term", "phrase", "language", "lexical"}),
    "archaeology": frozenset(
        {
            "inscription",
            "inscribed",
            "artifact",
            "artifacts",
            "stele",
            "seal",
            "tablet",
            "excavation",
            "excavated",
            "museum",
            "find",
            "finds",
        }
    ),
    "institution": frozenset(
        {"temple", "tabernacle", "priesthood", "synagogue", "sanhedrin", "kingdom", "covenant", "law", "sabbath", "passover"}
    ),
    "prophecy": frozenset({"prophecy", "prophet", "oracle", "vision", "apocalyptic", "eschatology"}),
}

QUESTION_FORM_HINTS: dict[str, tuple[str, ...]] = {
    "theme": ("what", "why", "how"),
    "theology": ("what", "why", "how"),
    "faq": ("what", "why", "how", "where", "who"),
}

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
        for token in query_search_terms(value):
            if token:
                terms.add(token)
    return terms


def query_search_terms(value: str) -> list[str]:
    """Return ordered, stop-word-filtered search terms for a query or field."""

    normalized = normalize_text(value)
    if not normalized:
        return []
    terms: list[str] = []
    seen: set[str] = set()
    for token in normalized.split():
        if token in SEARCH_STOP_WORDS or token in seen:
            continue
        seen.add(token)
        terms.append(token)
    return terms


def infer_query_categories(query: str, query_terms: Sequence[str] | None = None) -> list[str]:
    """Return likely CKL categories for a query string.

    The categories are only used as deterministic ranking hints.
    """

    lowered = normalize_text(query)
    tokens = set(query_search_terms(query) if query_terms is None else query_terms)
    raw_tokens = set(tokenize_query(query))
    combined = tokens | raw_tokens
    preferences: list[str] = []

    def add(category: str) -> None:
        if category not in preferences:
            preferences.append(category)

    for category, hints in CATEGORY_QUERY_HINTS.items():
        if combined.intersection(hints):
            add(category)

    for category, hints in QUESTION_FORM_HINTS.items():
        if any(hint in lowered for hint in hints):
            add(category)

    if re.search(r"\bwhat\s+does\b", lowered) or re.search(r"\bwhat\s+is\b", lowered):
        add("faq")
        add("theme")

    if re.search(r"\bwhy\s+is\b", lowered) or re.search(r"\bwhy\s+did\b", lowered):
        add("faq")
        add("theology")
        add("theme")

    return preferences


def exact_match_bonus(field_name: str, *, scripture_mode: bool = False) -> float:
    bonus = EXACT_MATCH_BONUS.get(field_name, 0.0)
    if scripture_mode and field_name in {"id", "title", "aliases", "common_questions"}:
        return 0.0
    return bonus


def phrase_match_bonus(field_name: str, phrase_length: int, *, scripture_mode: bool = False) -> float:
    bonus = PHRASE_MATCH_BONUS.get(field_name, 0.0) + max(phrase_length - 2, 0) * 0.02
    if scripture_mode and field_name in {"id", "title", "aliases", "common_questions"}:
        return round(bonus * 0.35, 4)
    return round(bonus, 4)


def fuzzy_match_bonus(field_name: str, ratio: float, *, scripture_mode: bool = False) -> float:
    multiplier = FUZZY_MATCH_MULTIPLIER.get(field_name, 0.0)
    if multiplier <= 0:
        return 0.0
    if scripture_mode and field_name in {"title", "aliases", "common_questions"}:
        return 0.0
    return round(min(0.9, ratio * multiplier), 4)


def category_bonus(object_type: str, preferred_categories: Sequence[str]) -> float:
    if object_type in preferred_categories:
        return 0.06
    if object_type == "faq" and any(category in preferred_categories for category in {"theme", "theology"}):
        return 0.03
    if object_type == "theme" and "theology" in preferred_categories:
        return 0.03
    return 0.0


def governance_bonus(review_status: str, confidence: str) -> float:
    review_scores = {
        "approved": 0.06,
        "reviewed": 0.04,
        "in_review": 0.02,
        "unreviewed": 0.0,
        "rejected": -0.08,
    }
    confidence_scores = {
        "high": 0.03,
        "medium": 0.015,
        "low": 0.005,
        "unrated": 0.0,
    }
    return review_scores.get(review_status, 0.0) + confidence_scores.get(confidence, 0.0)


def searchable_text_fields(obj: Any) -> dict[str, list[str]]:
    """Return raw searchable strings grouped by logical field name."""

    fields: dict[str, list[str]] = {}

    def add(field_name: str, value: Any) -> None:
        if value is None:
            return
        if hasattr(value, "to_dict"):
            value = value.to_dict()
        if isinstance(value, str):
            text = value.strip()
            if text:
                fields.setdefault(field_name, []).append(text)
            return
        if isinstance(value, Mapping):
            for key in (
                "id",
                "reference",
                "relationship",
                "notes",
                "title",
                "locator",
                "source_type",
                "author",
                "publisher",
                "url",
            ):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    fields.setdefault(field_name, []).append(item.strip())
            return
        if isinstance(value, list):
            for item in value:
                add(field_name, item)

    for field_name in (
        "id",
        "title",
        "aliases",
        "common_questions",
        "summary",
        "authorship_positions",
        "date_ranges",
        "original_audience",
        "historical_setting",
        "genre",
        "structure",
        "major_themes",
        "canonical_placement",
        "key_people",
        "key_places",
        "key_events",
        "interpretive_disputes",
        "primary_sources",
        "historical_context",
        "ancient_near_east_context",
        "literary_context",
        "covenantal_significance",
        "hebrew_words",
        "greek_words",
        "related_people",
        "related_places",
        "related_events",
        "related_objects",
        "scripture_references",
        "cross_references",
        "new_testament_connections",
        "interpretive_notes",
        "timeline",
        "maps",
        "archaeology",
    ):
        add(field_name, getattr(obj, field_name, None))

    return fields


def _candidate_phrases(query_terms: Sequence[str]) -> list[list[str]]:
    if len(query_terms) < 2:
        return []
    phrases: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    max_length = min(4, len(query_terms))
    for length in range(max_length, 1, -1):
        for start in range(0, len(query_terms) - length + 1):
            phrase = tuple(query_terms[start : start + length])
            if phrase in seen:
                continue
            seen.add(phrase)
            phrases.append(list(phrase))
    return phrases


def _contains_phrase(tokens: Sequence[str], phrase: Sequence[str]) -> bool:
    if not tokens or not phrase or len(phrase) > len(tokens):
        return False
    last_start = len(tokens) - len(phrase)
    for start in range(last_start + 1):
        if list(tokens[start : start + len(phrase)]) == list(phrase):
            return True
    return False


def score_text_match(
    query: str,
    obj: Any,
    *,
    scripture_mode: bool = False,
) -> tuple[float, str, list[str], str | None]:
    """Return a deterministic bonus for exact, phrase, or fuzzy text hits."""

    normalized_query = normalize_alias(query)
    query_terms = query_search_terms(query)
    fields = searchable_text_fields(obj)

    exact_field_order = (
        "id",
        "title",
        "aliases",
        "common_questions",
        "summary",
        "authorship_positions",
        "date_ranges",
        "original_audience",
        "historical_setting",
        "genre",
        "structure",
        "major_themes",
        "canonical_placement",
        "key_people",
        "key_places",
        "key_events",
        "interpretive_disputes",
        "primary_sources",
        "historical_context",
        "ancient_near_east_context",
        "literary_context",
        "covenantal_significance",
        "scripture_references",
        "related_objects",
        "related_people",
        "related_places",
        "related_events",
        "cross_references",
        "new_testament_connections",
        "interpretive_notes",
        "timeline",
        "maps",
        "archaeology",
    )
    if scripture_mode:
        exact_field_order = tuple(
            field_name for field_name in exact_field_order if field_name != "scripture_references"
        )

    for field_name in exact_field_order:
        values = fields.get(field_name, [])
        for value in values:
            if normalize_alias(value) != normalized_query:
                continue
            return (
                exact_match_bonus(field_name, scripture_mode=scripture_mode),
                "id"
                if field_name == "id"
                else "title"
                if field_name == "title"
                else "alias"
                if field_name in {"aliases", "common_questions"}
                else "phrase",
                [field_name],
                value if field_name in {"aliases", "common_questions"} else None,
            )

    phrases = _candidate_phrases(query_terms)
    if phrases:
        for field_name in exact_field_order:
            values = fields.get(field_name, [])
            for value in values:
                tokens = query_search_terms(value)
                if not tokens:
                    continue
                for phrase in phrases:
                    if not _contains_phrase(tokens, phrase):
                        continue
                    return (
                        phrase_match_bonus(field_name, len(phrase), scripture_mode=scripture_mode),
                        "phrase",
                        [field_name],
                        value if field_name in {"aliases", "common_questions", "title"} else None,
                    )

    fuzzy_field_order = ("title", "aliases", "common_questions", "summary")
    question_form = bool(re.search(r"\b(?:what|why|where|who|when|how)\b", normalized_query))
    if len(normalized_query) >= 4 and not question_form and not scripture_mode and len(query_terms) <= 2:
        best_ratio = 0.0
        best_field = ""
        best_value = None
        for field_name in fuzzy_field_order:
            values = fields.get(field_name, [])
            for value in values:
                candidate = normalize_alias(value)
                if not candidate or candidate == normalized_query:
                    continue
                ratio = SequenceMatcher(None, normalized_query, candidate).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_field = field_name
                    best_value = value
        if best_ratio >= 0.82 and best_field:
            return (
                fuzzy_match_bonus(best_field, best_ratio, scripture_mode=scripture_mode),
                "fuzzy_alias",
                [best_field],
                best_value if best_field in {"title", "aliases", "common_questions"} else None,
            )

    return 0.0, "keyword", [], None


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
        "original_audience",
        "historical_setting",
        "canonical_placement",
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
        "authorship_positions",
        "date_ranges",
        "genre",
        "structure",
        "major_themes",
        "key_people",
        "key_places",
        "key_events",
        "interpretive_disputes",
        "primary_sources",
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
    """Sort results deterministically by score, match type, title, and id."""

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            MATCH_TYPE_PRIORITY.get(result.match_type, 99),
            normalize_text(result.object.title),
            normalize_id(result.object.id),
        ),
    )
