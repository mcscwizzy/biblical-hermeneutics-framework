"""Deterministic query normalization and extraction helpers for CKL search."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Mapping, Sequence

from ..normalization import normalize_alias, normalize_text, tokenize_query
from ..scripture import ScriptureReferenceSpan, parse_scripture_reference
from .legacy import infer_query_categories as legacy_infer_query_categories
from .legacy import query_search_terms as legacy_query_search_terms
from .models import QueryAnalysis


PROTECTED_PHRASES: tuple[str, ...] = (
    "new covenant",
    "son of man",
    "kingdom of god",
    "day of the lord",
    "holy spirit",
    "new creation",
)

HIGH_LEVEL_FACET_ORDER: tuple[str, ...] = (
    "people",
    "places",
    "books",
    "themes",
    "events",
    "original-language terms",
    "theological concepts",
    "archaeological topics",
)

QUESTION_INTENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("comparison", re.compile(r"\b(compare|difference|different|contrast)\b", re.IGNORECASE)),
    ("definition", re.compile(r"\b(meaning|definition|what is|what does)\b", re.IGNORECASE)),
    ("explanation", re.compile(r"\b(why|how|explain|because)\b", re.IGNORECASE)),
    ("lookup", re.compile(r"\b(where|who|when|which)\b", re.IGNORECASE)),
)

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "about",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "tell",
        "the",
        "to",
        "what",
        "when",
        "where",
        "why",
        "with",
        "was",
        "were",
        "did",
        "do",
        "does",
        "done",
        "am",
        "are",
        "is",
        "be",
        "been",
        "being",
        "can",
        "could",
        "should",
        "shall",
        "would",
        "may",
        "might",
        "must",
        "who",
        "whom",
        "whose",
        "you",
        "your",
        "yours",
        "my",
        "mine",
        "our",
        "ours",
        "their",
        "theirs",
        "them",
        "us",
        "this",
        "that",
        "these",
        "those",
        "as",
        "by",
        "from",
        "or",
    }
)

IRREGULAR_SINGULARS: dict[str, str] = {
    "children": "child",
    "people": "person",
    "men": "man",
    "women": "woman",
    "wives": "wife",
    "lives": "life",
    "leaves": "leaf",
    "loaves": "loaf",
    "wolves": "wolf",
    "knives": "knife",
    "thieves": "thief",
    "elves": "elf",
    "selves": "self",
    "mice": "mouse",
    "geese": "goose",
    "teeth": "tooth",
    "feet": "foot",
    "oxen": "ox",
}

OBJECT_CATEGORY_TO_FACET: dict[str, str] = {
    "person": "people",
    "place": "places",
    "book": "books",
    "theme": "themes",
    "event": "events",
    "word_study": "original-language terms",
    "theology": "theological concepts",
    "archaeology": "archaeological topics",
    "institution": "theological concepts",
    "prophecy": "theological concepts",
}

FACET_TO_OBJECT_CATEGORY: dict[str, str] = {
    "people": "person",
    "places": "place",
    "books": "book",
    "themes": "theme",
    "events": "event",
    "original-language terms": "word_study",
    "theological concepts": "theology",
    "archaeological topics": "archaeology",
}

PERSON_QUERY_HINTS = frozenset(
    {
        "who",
        "whom",
        "whose",
        "person",
        "people",
        "man",
        "woman",
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
        "priest",
        "judge",
        "teacher",
    }
)

PLACE_QUERY_HINTS = frozenset(
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
        "hill",
        "country",
    }
)

BOOK_QUERY_HINTS = frozenset(
    {
        "book",
        "chapter",
        "verse",
        "passage",
        "gospel",
        "epistle",
        "letter",
        "psalm",
        "scripture",
    }
)

THEME_QUERY_HINTS = frozenset(
    {
        "theme",
        "motif",
        "pattern",
        "covenant",
        "promise",
        "inheritance",
        "renewal",
        "kingdom",
        "creation",
        "exile",
        "faithfulness",
        "holiness",
        "resurrection",
        "spirit",
        "messiah",
        "salvation",
        "grace",
    }
)

EVENT_QUERY_HINTS = frozenset(
    {
        "event",
        "renew",
        "renewed",
        "renewing",
        "renewal",
        "buried",
        "burial",
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
)

WORD_STUDY_QUERY_HINTS = frozenset(
    {
        "hebrew",
        "greek",
        "word",
        "meaning",
        "mean",
        "term",
        "phrase",
        "language",
        "lexical",
        "lemma",
        "root",
        "transliteration",
    }
)

THEOLOGY_QUERY_HINTS = frozenset(
    {
        "theology",
        "theological",
        "doctrine",
        "concept",
        "new covenant",
        "son of man",
        "kingdom of god",
        "day of the lord",
        "holy spirit",
        "new creation",
        "covenant",
        "kingdom",
        "spirit",
        "messiah",
        "salvation",
        "grace",
        "faith",
        "atonement",
        "justification",
        "sanctification",
        "trinity",
        "incarnation",
        "eschatology",
    }
)

ARCHAEOLOGY_QUERY_HINTS = frozenset(
    {
        "archaeology",
        "archaeological",
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
        "ruins",
        "dig",
        "finds",
    }
)

PROTECTED_PHRASE_FACETS: dict[str, tuple[str, ...]] = {
    "new covenant": ("theological concepts", "themes"),
    "son of man": ("theological concepts",),
    "kingdom of god": ("theological concepts", "themes"),
    "day of the lord": ("theological concepts", "events"),
    "holy spirit": ("theological concepts", "themes"),
    "new creation": ("theological concepts", "themes"),
}


def normalize_query(query: str) -> str:
    return " ".join(str(query or "").strip().split())


def extract_terms(query: str) -> list[str]:
    normalized = normalize_text(query)
    if not normalized:
        return []
    tokens = tokenize_query(query)
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in STOP_WORDS:
            continue
        singular = _singularize(token)
        candidate = singular if singular and singular not in STOP_WORDS else token
        candidate = candidate.strip()
        if not candidate or candidate in seen or candidate in STOP_WORDS:
            continue
        seen.add(candidate)
        terms.append(candidate)
    return terms


def extract_phrases(query: str) -> list[str]:
    normalized = normalize_text(query)
    if not normalized:
        return []
    phrases: list[str] = []
    seen: set[str] = set()
    for phrase in PROTECTED_PHRASES:
        if phrase in normalized and phrase not in seen:
            seen.add(phrase)
            phrases.append(phrase)
    return phrases


def detect_scripture_references(
    query: str,
    *,
    book_alias_lookup: Mapping[str, str] | None = None,
) -> list[ScriptureReferenceSpan]:
    if not query or not book_alias_lookup:
        return []
    pattern = _build_book_pattern(book_alias_lookup)
    reference_re = re.compile(
        rf"\b(?P<book>{pattern})"
        r"(?:[\s\.,;:\-\u2013\u2014]+[\d:.,;()\-\u2013\u2014]+(?:\s*[\d:.,;()\-\u2013\u2014]+)*)?",
        re.IGNORECASE,
    )
    spans: list[ScriptureReferenceSpan] = []
    seen: set[tuple[str, int | None, int | None, int | None, int | None]] = set()
    for match in reference_re.finditer(query):
        candidate = match.group(0).strip()
        parsed = parse_scripture_reference(candidate, book_alias_lookup=book_alias_lookup)
        if parsed is None:
            continue
        key = (
            parsed.book,
            parsed.start_chapter,
            parsed.start_verse,
            parsed.end_chapter,
            parsed.end_verse,
        )
        if key in seen:
            continue
        seen.add(key)
        spans.append(parsed)
    return spans


def guess_intent(query: str) -> str:
    normalized = normalize_query(query).lower()
    if not normalized:
        return "lookup"
    for intent, pattern in QUESTION_INTENT_PATTERNS:
        if pattern.search(normalized):
            return intent
    return "lookup"


def analyze_query(
    query: str,
    *,
    book_alias_lookup: Mapping[str, str] | None = None,
    title_index: Mapping[str, Any] | None = None,
    alias_index: Mapping[str, Any] | None = None,
    entries_by_id: Mapping[str, Any] | None = None,
) -> QueryAnalysis:
    normalized = normalize_query(query)
    search_text = normalize_text(query)
    terms = extract_terms(query)
    phrases = extract_phrases(query)
    scripture_references = detect_scripture_references(
        query,
        book_alias_lookup=book_alias_lookup,
    )
    object_categories = _unique_sequence(legacy_infer_query_categories(normalized, terms))
    matched_terms_by_category: dict[str, list[str]] = {facet: [] for facet in HIGH_LEVEL_FACET_ORDER}

    _apply_term_hints(
        search_text,
        terms=terms,
        phrases=phrases,
        matched_terms_by_category=matched_terms_by_category,
        object_categories=object_categories,
    )
    _apply_protected_phrase_facets(
        search_text,
        phrases=phrases,
        matched_terms_by_category=matched_terms_by_category,
        object_categories=object_categories,
    )

    for category in object_categories:
        facet = OBJECT_CATEGORY_TO_FACET.get(category)
        if facet:
            _append_facet_term(matched_terms_by_category, facet, category)

    if title_index is not None and alias_index is not None and entries_by_id is not None:
        _apply_index_matches(
            search_text,
            terms=terms,
            scripture_references=scripture_references,
            title_index=title_index,
            alias_index=alias_index,
            entries_by_id=entries_by_id,
            matched_terms_by_category=matched_terms_by_category,
            object_categories=object_categories,
        )

    if scripture_references:
        _append_object_category(object_categories, "book")
        for reference in scripture_references:
            _append_facet_term(matched_terms_by_category, "books", reference.book)

    categories = [facet for facet in HIGH_LEVEL_FACET_ORDER if matched_terms_by_category.get(facet)]
    intent = guess_intent(query)
    if scripture_references and intent == "lookup":
        intent = "scripture"
    return QueryAnalysis(
        raw_query=query,
        normalized_query=normalized,
        terms=terms,
        phrases=phrases,
        scripture_references=scripture_references,
        categories=categories,
        object_categories=object_categories,
        matched_terms_by_category=matched_terms_by_category,
        intent=intent,
    )


def query_search_terms(value: str) -> list[str]:
    return legacy_query_search_terms(value)


def canonical_search_terms(*values: str) -> set[str]:
    terms: set[str] = set()
    for value in values:
        for term in extract_terms(value):
            terms.add(term)
    return terms


def _apply_term_hints(
    search_text: str,
    *,
    terms: Sequence[str],
    phrases: Sequence[str],
    matched_terms_by_category: dict[str, list[str]],
    object_categories: list[str],
) -> None:
    if _contains_any_term(terms, PERSON_QUERY_HINTS):
        _append_object_category(object_categories, "person")
        _append_facet_term(matched_terms_by_category, "people", _first_term_match(terms, PERSON_QUERY_HINTS))
    if _contains_any_term(terms, PLACE_QUERY_HINTS):
        _append_object_category(object_categories, "place")
        _append_facet_term(matched_terms_by_category, "places", _first_term_match(terms, PLACE_QUERY_HINTS))
    if _contains_any_term(terms, BOOK_QUERY_HINTS):
        _append_object_category(object_categories, "book")
        _append_facet_term(matched_terms_by_category, "books", _first_term_match(terms, BOOK_QUERY_HINTS))
    if _contains_any_term(terms, THEME_QUERY_HINTS):
        _append_object_category(object_categories, "theme")
        _append_facet_term(matched_terms_by_category, "themes", _first_term_match(terms, THEME_QUERY_HINTS))
    if _contains_any_term(terms, EVENT_QUERY_HINTS):
        _append_object_category(object_categories, "event")
        _append_facet_term(matched_terms_by_category, "events", _first_term_match(terms, EVENT_QUERY_HINTS))
    if _contains_any_term(terms, WORD_STUDY_QUERY_HINTS):
        _append_object_category(object_categories, "word_study")
        _append_facet_term(
            matched_terms_by_category,
            "original-language terms",
            _first_term_match(terms, WORD_STUDY_QUERY_HINTS),
        )
    if _contains_any_term(terms, THEOLOGY_QUERY_HINTS) or any(phrase in search_text for phrase in PROTECTED_PHRASE_FACETS):
        _append_object_category(object_categories, "theology")
        _append_facet_term(
            matched_terms_by_category,
            "theological concepts",
            _first_term_match(terms, THEOLOGY_QUERY_HINTS) or _first_phrase_match(search_text, PROTECTED_PHRASE_FACETS),
        )
    if _contains_any_term(terms, ARCHAEOLOGY_QUERY_HINTS):
        _append_object_category(object_categories, "archaeology")
        _append_facet_term(
            matched_terms_by_category,
            "archaeological topics",
            _first_term_match(terms, ARCHAEOLOGY_QUERY_HINTS),
        )


def _apply_protected_phrase_facets(
    search_text: str,
    *,
    phrases: Sequence[str],
    matched_terms_by_category: dict[str, list[str]],
    object_categories: list[str],
) -> None:
    for phrase in phrases:
        for facet in PROTECTED_PHRASE_FACETS.get(phrase, ()):
            _append_facet_term(matched_terms_by_category, facet, phrase)
            object_category = FACET_TO_OBJECT_CATEGORY.get(facet)
            if object_category:
                _append_object_category(object_categories, object_category)


def _apply_index_matches(
    search_text: str,
    *,
    terms: Sequence[str],
    scripture_references: Sequence[ScriptureReferenceSpan],
    title_index: Mapping[str, Any],
    alias_index: Mapping[str, Any],
    entries_by_id: Mapping[str, Any],
    matched_terms_by_category: dict[str, list[str]],
    object_categories: list[str],
) -> None:
    for label, entries in _collect_index_matches(
        search_text,
        title_index=title_index,
        alias_index=alias_index,
        entries_by_id=entries_by_id,
    ):
        matched_categories = {
            _entry_category(entry)
            for entry in entries
            if _entry_category(entry)
        }
        for entry in entries:
            category = _entry_category(entry)
            if not category:
                continue
            if category == "book" and not _should_promote_book(
                label=label,
                search_text=search_text,
                terms=terms,
                matched_categories=matched_categories,
                scripture_references=scripture_references,
            ):
                continue
            _append_object_category(object_categories, category)
            facet = OBJECT_CATEGORY_TO_FACET.get(category)
            if facet:
                display_value = _entry_title(entry) or _entry_display_value(entries, label)
                _append_facet_term(matched_terms_by_category, facet, display_value)


def _should_promote_book(
    *,
    label: str,
    search_text: str,
    terms: Sequence[str],
    matched_categories: set[str],
    scripture_references: Sequence[ScriptureReferenceSpan],
) -> bool:
    if "book" not in matched_categories:
        return False
    if scripture_references:
        return True
    if _contains_any_term(terms, BOOK_QUERY_HINTS):
        return True
    if any(hint in search_text for hint in ("book of ", "what is ", "tell me about ")):
        return True
    if label.startswith("book of ") or label.startswith("what is ") or label.startswith("tell me about "):
        return True
    if search_text == label and matched_categories == {"book"}:
        return True
    return False


def _collect_index_matches(
    search_text: str,
    *,
    title_index: Mapping[str, Any],
    alias_index: Mapping[str, Any],
    entries_by_id: Mapping[str, Any],
) -> list[tuple[str, list[Any]]]:
    matches: list[tuple[str, list[Any]]] = []
    title_keys = tuple(sorted(str(label) for label in title_index.keys()))
    alias_keys = tuple(sorted(str(label) for label in alias_index.keys()))
    for label in _sorted_index_labels(title_keys, alias_keys):
        if not _contains_label(search_text, label):
            continue
        entry_ids = _coerce_ids(title_index.get(label)) | _coerce_ids(alias_index.get(label))
        if not entry_ids:
            continue
        entries = [entries_by_id[entry_id] for entry_id in sorted(entry_ids) if entry_id in entries_by_id]
        if entries:
            matches.append((label, entries))
    return matches


@lru_cache(maxsize=32)
def _sorted_index_labels(
    title_index_keys: tuple[str, ...],
    alias_index_keys: tuple[str, ...],
) -> tuple[str, ...]:
    labels = {label for label in title_index_keys if label} | {label for label in alias_index_keys if label}
    return tuple(sorted(labels, key=lambda label: (-len(label.split()), -len(label), label)))


def _contains_label(search_text: str, label: str) -> bool:
    if not search_text or not label:
        return False
    return bool(re.search(rf"\b{re.escape(label)}\b", search_text))


def _coerce_ids(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, set):
        return {str(item) for item in value if str(item).strip()}
    if isinstance(value, (list, tuple)):
        return {str(item) for item in value if str(item).strip()}
    if isinstance(value, str):
        text = value.strip()
        return {text} if text else set()
    return {str(value).strip()} if str(value).strip() else set()


def _entry_category(entry: Any) -> str:
    return str(getattr(entry, "category", getattr(entry, "type", "")) or "").strip()


def _entry_title(entry: Any) -> str:
    return str(getattr(entry, "title", "") or "").strip()


def _entry_display_value(entries: Sequence[Any], fallback: str) -> str:
    for entry in entries:
        title = _entry_title(entry)
        if title:
            return title
    return fallback


def _append_facet_term(
    matched_terms_by_category: dict[str, list[str]],
    facet: str,
    term: str | None,
) -> None:
    if not term:
        return
    terms = matched_terms_by_category.setdefault(facet, [])
    if term not in terms:
        terms.append(term)


def _append_object_category(object_categories: list[str], category: str | None) -> None:
    if not category:
        return
    if category not in object_categories:
        object_categories.append(category)


def _contains_any_term(terms: Sequence[str], candidates: frozenset[str]) -> bool:
    return any(term in candidates for term in terms)


def _first_term_match(terms: Sequence[str], candidates: frozenset[str]) -> str | None:
    for term in terms:
        if term in candidates:
            return term
    return None


def _first_phrase_match(search_text: str, phrase_facets: Mapping[str, tuple[str, ...]]) -> str | None:
    for phrase in phrase_facets:
        if phrase in search_text:
            return phrase
    return None


def _unique_sequence(values: Sequence[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        _append_object_category(unique, value)
    return unique


@lru_cache(maxsize=32)
def _build_book_pattern_cached(book_alias_lookup_items: tuple[tuple[str, str], ...]) -> str:
    aliases = sorted((alias for alias, _canonical in book_alias_lookup_items), key=len, reverse=True)
    return "|".join(re.escape(alias) for alias in aliases)


def _build_book_pattern(book_alias_lookup: Mapping[str, str]) -> str:
    return _build_book_pattern_cached(tuple(sorted(book_alias_lookup.items())))


def _singularize(token: str) -> str:
    if token in IRREGULAR_SINGULARS:
        return IRREGULAR_SINGULARS[token]
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("sses") or token.endswith("shes") or token.endswith("ches") or token.endswith("xes") or token.endswith("zes"):
        return token[:-2]
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token
