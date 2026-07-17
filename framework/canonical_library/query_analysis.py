"""Precision-first deterministic query analysis for CKL entity retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Mapping

from .normalization import normalize_alias, normalize_text
from .scripture import ScriptureReferenceSpan, parse_scripture_reference


SINGLE_ENTITY = "single_entity"
MULTIPLE_ENTITIES = "multiple_entities"
CONCEPTUAL = "conceptual"
SCRIPTURE = "scripture"
AMBIGUOUS = "ambiguous"

_BOOK_CONTEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bbook of (?P<entity>.+)$"),
    re.compile(r"\bgospel of (?P<entity>.+)$"),
    re.compile(r"\b(?:letter|epistle) to (?P<entity>.+)$"),
)
_QUESTION_ENTITY_PATTERNS: tuple[tuple[re.Pattern[str], str, tuple[str, ...], float], ...] = (
    (re.compile(r"\bwho (?:was|is) (?P<entity>.+)$"), "person_context", ("person",), 1.0),
    (re.compile(r"\bwhere is (?P<entity>.+)$"), "place_context", ("place",), 1.0),
    (re.compile(r"\bwhat happened at (?P<entity>.+)$"), "event_context", ("event",), 0.85),
    (re.compile(r"\bcontext of (?P<entity>.+)$"), "general", (), 0.0),
    (re.compile(r"\bmeaning of (?P<entity>.+)$"), "theme_question", (), 0.0),
    (re.compile(r"\btell me about (?P<entity>.+)$"), "general", (), 0.0),
    (re.compile(r"\bwhat is (?P<entity>.+) about$"), "general", (), 0.0),
    (re.compile(r"\b(?:connections|cross references|canonical connections) (?:for|of|to) (?P<entity>.+)$"), "relationship", (), 0.0),
)
_COMPARATIVE_RE = re.compile(r"\b(?:compare|contrast|different|differ|versus|vs)\b")
_RELATIONSHIP_RE = re.compile(
    r"\b(?:related|relationship|connect|connected|connections|cross references?|canonical connections?)\b"
)
_THEME_CONNECTION_RE = re.compile(r"\bthemes?\s+connect\b|\bconnect(?:s|ed)?\s+themes?\b")
_ENTITY_SPLIT_RE = re.compile(r"\b(?:and|with|to|from|versus|vs)\b")
_TRAILING_CONTEXT_RE = re.compile(
    r"\b(?:about|context|meaning|related|relationship|compare|compared|different|differ|connect|connected|connections?)\b.*$"
)
_ORDINAL_PREFIXES = {
    "first": "1",
    "i": "1",
    "1st": "1",
    "second": "2",
    "ii": "2",
    "2nd": "2",
    "third": "3",
    "iii": "3",
    "3rd": "3",
}


@dataclass(frozen=True)
class QueryAnalysis:
    original_query: str
    intent: str
    entity_candidates: tuple[str, ...]
    preferred_categories: tuple[str, ...]
    category_confidence: float
    scope: str
    include_related: bool
    comparative: bool
    scripture_references: tuple[ScriptureReferenceSpan, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["entity_candidates"] = list(self.entity_candidates)
        data["preferred_categories"] = list(self.preferred_categories)
        data["scripture_references"] = [asdict(reference) for reference in self.scripture_references]
        return data


@dataclass(frozen=True)
class AmbiguousEntityCandidate:
    id: str
    title: str
    type: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AmbiguousEntityResolution:
    entity: str
    candidates: tuple[AmbiguousEntityCandidate, ...]
    status: str = "ambiguous"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "entity": self.entity,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def analyze_query(
    query: str,
    *,
    book_alias_lookup: Mapping[str, str] | None = None,
) -> QueryAnalysis:
    """Return a deterministic precision-first CKL query analysis."""

    normalized = normalize_text(query)
    comparative = bool(_COMPARATIVE_RE.search(normalized))
    relationship = bool(_RELATIONSHIP_RE.search(normalized) or _THEME_CONNECTION_RE.search(normalized))
    scripture_references = _extract_scripture_references(normalized, book_alias_lookup or {})
    book_titles = _canonical_book_titles(book_alias_lookup or {})

    scripture_subject = _extract_subject_before_scripture(normalized, scripture_references)
    if scripture_subject:
        return QueryAnalysis(
            original_query=query,
            intent="scripture_context",
            entity_candidates=(_display_entity(scripture_subject),),
            preferred_categories=(),
            category_confidence=0.0,
            scope=SINGLE_ENTITY,
            include_related=relationship,
            comparative=comparative,
            scripture_references=scripture_references,
        )

    if scripture_references:
        reference = scripture_references[0]
        return QueryAnalysis(
            original_query=query,
            intent="scripture_context",
            entity_candidates=(reference.book,),
            preferred_categories=("book",),
            category_confidence=1.0,
            scope=SCRIPTURE,
            include_related=relationship,
            comparative=comparative,
            scripture_references=scripture_references,
        )

    extracted = _extract_pattern_entity(normalized, book_titles)
    if extracted is not None:
        candidates, intent, preferred_categories, confidence = extracted
        return QueryAnalysis(
            original_query=query,
            intent=intent,
            entity_candidates=candidates,
            preferred_categories=preferred_categories,
            category_confidence=confidence,
            scope=SINGLE_ENTITY if len(candidates) <= 2 else MULTIPLE_ENTITIES,
            include_related=relationship,
            comparative=comparative,
        )

    named_books = _extract_named_books(normalized, book_titles)
    if len(named_books) >= 2 and (comparative or relationship):
        return QueryAnalysis(
            original_query=query,
            intent="relationship" if relationship else "comparison",
            entity_candidates=tuple(named_books),
            preferred_categories=("book",),
            category_confidence=0.9,
            scope=MULTIPLE_ENTITIES,
            include_related=relationship,
            comparative=comparative,
        )
    if len(named_books) == 1 and _looks_like_book_context(normalized):
        return QueryAnalysis(
            original_query=query,
            intent="book_context",
            entity_candidates=(named_books[0],),
            preferred_categories=("book",),
            category_confidence=0.9,
            scope=SINGLE_ENTITY,
            include_related=relationship,
            comparative=comparative,
        )

    if comparative or relationship:
        candidates = _extract_connector_candidates(normalized)
        scope = MULTIPLE_ENTITIES if len(candidates) > 1 else AMBIGUOUS
        return QueryAnalysis(
            original_query=query,
            intent="relationship" if relationship else "comparison",
            entity_candidates=tuple(candidates),
            preferred_categories=(),
            category_confidence=0.0,
            scope=scope,
            include_related=relationship,
            comparative=comparative,
        )

    return QueryAnalysis(
        original_query=query,
        intent="theme_question" if _looks_conceptual(normalized) else "general",
        entity_candidates=(),
        preferred_categories=(),
        category_confidence=0.0,
        scope=CONCEPTUAL if _looks_conceptual(normalized) else AMBIGUOUS,
        include_related=False,
        comparative=False,
    )


def _extract_pattern_entity(
    normalized: str,
    book_titles: Mapping[str, str],
) -> tuple[tuple[str, ...], str, tuple[str, ...], float] | None:
    for pattern in _BOOK_CONTEXT_PATTERNS:
        match = pattern.search(normalized)
        if match is None:
            continue
        entity = _clean_entity(match.group("entity"))
        if not entity:
            continue
        return _book_candidates(entity), "book_context", ("book",), 1.0

    for pattern, intent, categories, confidence in _QUESTION_ENTITY_PATTERNS:
        match = pattern.search(normalized)
        if match is None:
            continue
        entity = _clean_entity(match.group("entity"))
        if not entity:
            continue
        if entity.startswith("book of "):
            return _book_candidates(entity.removeprefix("book of ")), "book_context", ("book",), 1.0
        if entity.startswith("gospel of "):
            return _book_candidates(entity.removeprefix("gospel of ")), "book_context", ("book",), 1.0
        if intent == "general" and _normalize_numbered_book(entity) in book_titles:
            return (_display_entity(entity),), "book_context", ("book",), 0.9
        if entity.startswith("gospel of "):
            return _book_candidates(entity.removeprefix("gospel of ")), "book_context", ("book",), 1.0
        preferred = categories
        adjusted_intent = intent
        adjusted_confidence = confidence
        if not preferred and _normalize_numbered_book(entity) in book_titles:
            preferred = ("book",)
            adjusted_intent = "book_context"
            adjusted_confidence = 0.9
        return (_display_entity(entity),), adjusted_intent, preferred, adjusted_confidence

    return None


def _extract_scripture_references(
    normalized: str,
    book_alias_lookup: Mapping[str, str],
) -> tuple[ScriptureReferenceSpan, ...]:
    if not normalized or not book_alias_lookup:
        return ()
    references: list[ScriptureReferenceSpan] = []
    seen: set[tuple[str, int | None, int | None]] = set()
    aliases = sorted(book_alias_lookup, key=lambda value: (-len(value), value))
    for alias in aliases:
        if len(alias) < 2:
            continue
        pattern = re.compile(rf"\b{re.escape(alias)}\s+\d+(?:\s+\d+)?(?:\s+\d+)?(?:\s+\d+)?\b")
        for match in pattern.finditer(normalized):
            reference = parse_scripture_reference(match.group(0), book_alias_lookup=book_alias_lookup)
            if reference is None or reference.start_chapter is None:
                continue
            key = (reference.book, reference.start_chapter, reference.start_verse)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return tuple(references)


def _extract_subject_before_scripture(
    normalized: str,
    scripture_references: tuple[ScriptureReferenceSpan, ...],
) -> str:
    if not scripture_references:
        return ""
    first_reference = scripture_references[0]
    reference_book = normalize_alias(first_reference.book)
    reference_start = normalized.find(reference_book)
    if reference_start <= 0:
        return ""
    prefix = normalized[:reference_start].strip()
    match = re.search(r"\bwhy is (?P<entity>.+?) important in$", prefix)
    if match is None:
        match = re.search(r"\b(?P<entity>[a-z0-9 ]+?) in$", prefix)
    if match is None:
        return ""
    return _clean_entity(match.group("entity"))


def _canonical_book_titles(book_alias_lookup: Mapping[str, str]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for title in book_alias_lookup.values():
        normalized = normalize_alias(title)
        if normalized:
            titles[normalized] = title
    return titles


def _extract_named_books(normalized: str, book_titles: Mapping[str, str]) -> list[str]:
    found: list[tuple[int, int, str]] = []
    for normalized_title, title in book_titles.items():
        if not normalized_title:
            continue
        match = re.search(rf"\b{re.escape(normalized_title)}\b", normalized)
        if match is not None:
            found.append((match.start(), -len(normalized_title), title))
    found.sort()

    names: list[str] = []
    occupied: list[tuple[int, int]] = []
    for start, negative_length, title in found:
        end = start - negative_length
        if any(start >= used_start and end <= used_end for used_start, used_end in occupied):
            continue
        if title not in names:
            names.append(title)
        occupied.append((start, end))
    return names


def _extract_connector_candidates(normalized: str) -> list[str]:
    cleaned = re.sub(r"\b(?:compare|contrast|how is|how are|what themes?|themes?|related|relationship|different|differ|connect|connected|connections?)\b", " ", normalized)
    parts = [_clean_entity(part) for part in _ENTITY_SPLIT_RE.split(cleaned)]
    return [_display_entity(part) for part in parts if part]


def _book_candidates(entity: str) -> tuple[str, ...]:
    cleaned = _clean_entity(entity)
    if not cleaned:
        return ()
    displayed = _display_entity(cleaned)
    candidates = [displayed]
    if not normalize_alias(displayed).startswith("gospel of "):
        gospel_candidate = f"Gospel of {displayed}"
        if gospel_candidate not in candidates:
            candidates.append(gospel_candidate)
    return tuple(candidates)


def _clean_entity(value: str) -> str:
    entity = normalize_alias(value)
    entity = re.sub(r"^(?:the|a|an)\s+", "", entity)
    entity = _TRAILING_CONTEXT_RE.sub("", entity).strip()
    entity = re.sub(r"\s+", " ", entity).strip()
    return _normalize_numbered_book(entity)


def _normalize_numbered_book(value: str) -> str:
    tokens = normalize_alias(value).split()
    if not tokens:
        return ""
    prefix = _ORDINAL_PREFIXES.get(tokens[0])
    if prefix and len(tokens) > 1:
        return " ".join([prefix, *tokens[1:]])
    return " ".join(tokens)


def _display_entity(value: str) -> str:
    normalized = _normalize_numbered_book(value)
    if not normalized:
        return ""
    words = []
    for token in normalized.split():
        if token.isdigit():
            words.append(token)
        else:
            words.append(token.capitalize())
    return " ".join(words)


def _looks_like_book_context(normalized: str) -> bool:
    return bool(
        re.search(r"\b(?:book|gospel|epistle|letter|chapter|verse)\b", normalized)
        or re.search(r"\bwhat is .+ about\b", normalized)
    )


def _looks_conceptual(normalized: str) -> bool:
    return bool(
        re.search(r"\b(?:scripture|bible|teach|teaches|theme|themes|meaning|doctrine|theology)\b", normalized)
        or re.search(r"\bwhat does\b", normalized)
    )
