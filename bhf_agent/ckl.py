"""Runtime helpers for integrating the Canonical Knowledge Library."""

from __future__ import annotations

import re
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from framework.canonical_library import (
    CanonicalContextBuilder,
    CanonicalLibrary,
    CKLRepositoryConfig,
    JsonCanonicalRepository,
    SQLiteCanonicalLibrary,
    SQLiteCanonicalRepository,
    build_canonical_prompt_context,
    load_canonical_repository,
)
from framework.canonical_library.normalization import normalize_text, tokenize_query
from framework.canonical_library.query_analysis import analyze_query as analyze_structured_query

from .bible import resolve_chapter
from .models import QuestionContext, ReferenceContext
from .token_estimation import estimate_tokens


def _estimate_tokens(text: str) -> int:
    return estimate_tokens(text)


CKL_STRONG_MATCH_THRESHOLD = 0.85
CULTURAL_CONTEXT_MAX_RESULTS = 3
CULTURAL_CONTEXT_MAX_TOKENS = 1100
CULTURAL_CONTEXT_MAX_OUTPUT_TOKENS = 700
CULTURAL_CONTEXT_OBJECT_TYPES = frozenset(
    {"archaeology", "institution", "place", "person", "word_study", "theme", "faq"}
)


QUESTION_STARTERS = {
    "how",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "can",
    "could",
    "did",
    "do",
    "does",
    "explain",
    "is",
    "may",
    "please",
    "should",
    "tell",
    "was",
    "were",
    "will",
    "would",
}

THEME_QUERY_TOKENS = {
    "adoption",
    "blessing",
    "covenant",
    "creation",
    "exile",
    "exodus",
    "faithfulness",
    "fall",
    "fire",
    "glory",
    "hope",
    "holy",
    "justice",
    "kingdom",
    "land",
    "light",
    "messiah",
    "mercy",
    "new",
    "peace",
    "presence",
    "prayer",
    "priesthood",
    "promise",
    "righteousness",
    "resurrection",
    "restoration",
    "sabbath",
    "sacrifice",
    "sanctuary",
    "shepherd",
    "spirit",
    "temple",
    "word",
    "worship",
    "water",
}

CAPITALIZED_TERM_RE = re.compile(r"\b[A-Z][A-Za-z0-9'-]+\b")

# These terms are deliberately small and transparent.  They help locate the
# immediate textual evidence for common question forms without pretending to
# be a general purpose NLP model.
_QUESTION_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cause", re.compile(r"\b(?:why|cause|reason)\b", re.IGNORECASE)),
    ("identity", re.compile(r"\bwho (?:is|was|were)\b", re.IGNORECASE)),
    ("book_overview", re.compile(r"\b(?:overall message|main (?:point|message)|overview|what is .+ about)\b", re.IGNORECASE)),
    ("definition", re.compile(r"\b(?:what (?:is|does)|mean|represent)\b", re.IGNORECASE)),
    ("purpose", re.compile(r"\b(?:why did|purpose|for what)\b", re.IGNORECASE)),
)
_ROLE_WORDS = frozenset({"the", "a", "an", "prophet", "moabite", "king", "queen", "apostle", "priest", "judge"})
_PASSAGE_HINTS: dict[str, tuple[str, ...]] = {
    "conceive": ("womb", "barren", "barrenness", "conceived", "child"),
    "infertility": ("womb", "barren", "barrenness", "conceived"),
    "feet": ("feet", "lie", "lay", "uncover", "uncovered"),
    "stars": ("stars", "angels", "churches"),
    "star": ("stars", "angels", "churches"),
}
_RETRIEVAL_NOISE_TERMS = frozenset({"a", "an", "and", "did", "do", "does", "down", "for", "how", "in", "is", "it", "of", "the", "to", "unable", "was", "what", "who", "why"})
_PASSAGE_ANCHOR_TERMS = frozenset({"womb", "barren", "barrenness", "conceived", "uncover", "uncovered", "feet", "stars", "angels", "churches"})

# Legacy answer-mode values are intentionally normalized to one retrieval
# policy so request compatibility cannot change the user-facing answer.
ANSWER_MODE_DETAIL_LEVELS: dict[str, int] = {"unified": 1}
CONTEXT_TOPIC_BUDGET_RATIOS: dict[str, float] = {"unified": 0.65}

TOPIC_FIELDS_BY_DETAIL_LEVEL: dict[int, tuple[str, ...]] = {
    0: (
        "aliases",
        "summary",
        "scripture_references",
        "common_questions",
        "related_objects",
        "sources",
    ),
    1: (
        "aliases",
        "summary",
        "original_audience",
        "historical_setting",
        "genre",
        "major_themes",
        "canonical_placement",
        "key_people",
        "key_places",
        "key_events",
        "primary_sources",
        "historical_context",
        "literary_context",
        "covenantal_significance",
        "hebraic_worldview",
        "canonical_context",
        "intertextuality",
        "scripture_references",
        "common_questions",
        "interpretive_notes",
        "related_objects",
        "sources",
    ),
    2: (
        "aliases",
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
        "hebraic_worldview",
        "second_temple_context",
        "literary_context",
        "covenantal_significance",
        "canonical_context",
        "later_christian_reception",
        "intertextuality",
        "cross_references",
        "scripture_references",
        "common_questions",
        "interpretive_notes",
        "hebrew_words",
        "greek_words",
        "timeline",
        "archaeology",
        "new_testament_connections",
        "related_objects",
        "sources",
    ),
}

SHARED_SECTION_FIELDS_BY_DETAIL_LEVEL: dict[int, tuple[tuple[str, str], ...]] = {
    0: (
        ("Historical Context", "historical_context"),
        ("Literary Context", "literary_context"),
        ("Intertextual Connections", "intertextuality"),
        ("Related Topics", "related_topics"),
    ),
    1: (
        ("Historical Context", "historical_context"),
        ("Ancient Near Eastern Context", "ancient_near_east_context"),
        ("Hebraic Worldview", "hebraic_worldview"),
        ("Literary Context", "literary_context"),
        ("Covenantal Significance", "covenantal_significance"),
        ("Canonical Context", "canonical_context"),
        ("Intertextual Connections", "intertextuality"),
        ("New Testament Connections", "new_testament_connections"),
    ),
    2: (
        ("Historical Context", "historical_context"),
        ("Ancient Near Eastern Context", "ancient_near_east_context"),
        ("Hebraic Worldview", "hebraic_worldview"),
        ("Second Temple Context", "second_temple_context"),
        ("Literary Context", "literary_context"),
        ("Covenantal Significance", "covenantal_significance"),
        ("Canonical Context", "canonical_context"),
        ("Intertextual Connections", "intertextuality"),
        ("Cross References", "cross_references"),
        ("Word Studies", "word_studies"),
        ("Timeline", "timeline"),
        ("Archaeology", "archaeology"),
        ("New Testament Connections", "new_testament_connections"),
        ("Later Christian Reception", "later_christian_reception"),
    ),
}

SOURCE_LIMITS_BY_DETAIL_LEVEL: dict[int, int] = {
    0: 2,
    1: 3,
    2: 5,
}


@lru_cache(maxsize=1)
def _load_default_canonical_library() -> CanonicalLibrary:
    backend = os.environ.get("BHF_CKL_BACKEND", "").strip()
    database_path = os.environ.get("BHF_CKL_DATABASE_PATH", "").strip()
    stale_policy = os.environ.get("BHF_CKL_STALE_DATABASE_POLICY", "").strip()
    if backend or database_path or stale_policy:
        return _library_from_repository_config(
            CKLRepositoryConfig(
                backend=backend or "sqlite",
                database_path=database_path or ".bhf/ckl.sqlite",
                json_root=os.environ.get("BHF_CKL_ROOT", "").strip() or None,
                stale_database_policy=stale_policy or "fallback_to_json",
            )
        )
    root = os.environ.get("BHF_CKL_ROOT", "").strip()
    if root:
        return CanonicalLibrary(root=Path(root)).load()
    return CanonicalLibrary.load_default()


def _library_from_repository_config(config: Any) -> CanonicalLibrary:
    repository_config = CKLRepositoryConfig(
        backend=str(getattr(config, "backend", "sqlite") or "sqlite"),
        database_path=str(getattr(config, "database_path", ".bhf/ckl.sqlite") or ".bhf/ckl.sqlite"),
        json_root=getattr(config, "json_root", None),
        stale_database_policy=str(getattr(config, "stale_database_policy", "fallback_to_json") or "fallback_to_json"),
        read_only=bool(getattr(config, "read_only", True)),
        cache_size=int(getattr(config, "repository_cache_size", 256) or 256),
    )
    repository = load_canonical_repository(repository_config)
    if isinstance(repository, JsonCanonicalRepository):
        return repository.library
    if isinstance(repository, SQLiteCanonicalRepository):
        return SQLiteCanonicalLibrary(
            repository,
            root=repository_config.json_root or Path(__file__).resolve().parents[1] / "framework" / "canonical_library",
        )
    raise TypeError(f"unsupported canonical repository: {type(repository).__name__}")


def load_canonical_library(root: str | Path | None = None, config: Any | None = None) -> CanonicalLibrary:
    """Return a loaded CKL instance, caching the default inventory in memory."""

    if config is not None:
        return _library_from_repository_config(config)
    if root is None:
        return _load_default_canonical_library()
    return CanonicalLibrary(root=Path(root)).load()


def build_canonical_query(
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
) -> str:
    parts: list[str] = []

    def add_part(value: str | None) -> None:
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)

    add_part(question)
    if reference_context is not None:
        add_part(reference_context.book)
        if reference_context.book and reference_context.chapter is not None:
            add_part(f"{reference_context.book} {reference_context.chapter}")
            if reference_context.verse is not None:
                verse_reference = (
                    f"{reference_context.book} "
                    f"{reference_context.chapter}:{reference_context.verse}"
                )
                if reference_context.verse_end is not None:
                    verse_reference += f"-{reference_context.verse_end}"
                add_part(verse_reference)
        add_part(reference_context.topic)
    if question_context is not None:
        add_part(question_context.target_language)
        for term in question_context.target_terms:
            add_part(term)

    return " ".join(parts).strip()


def _candidate_exact_queries(
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
) -> list[str]:
    candidates: list[str] = []

    def add(value: str | None) -> None:
        text = str(value or "").strip()
        if text and text not in candidates:
            candidates.append(text)

    if reference_context is not None:
        add(reference_context.book)
        add(reference_context.topic)
    if question_context is not None:
        for term in question_context.target_terms:
            add(term)

    for match in CAPITALIZED_TERM_RE.finditer(question):
        candidate = match.group(0).strip()
        if candidate.lower() in QUESTION_STARTERS:
            continue
        add(candidate)

    if question_context is None or question_context.question_type != "word_study":
        for token in tokenize_query(question):
            if token in THEME_QUERY_TOKENS:
                add(f"{token} theme")

    add(question)
    return candidates


def _normalize_answer_mode(answer_mode: str | None) -> str:
    return "unified"


def _context_detail_level(answer_mode: str | None) -> int:
    return ANSWER_MODE_DETAIL_LEVELS[_normalize_answer_mode(answer_mode)]


def _topic_token_budget(max_context_tokens: int | None, answer_mode: str | None) -> int | None:
    if max_context_tokens is None:
        return None
    return max(0, int(max_context_tokens * CONTEXT_TOPIC_BUDGET_RATIOS[_normalize_answer_mode(answer_mode)]))


def _fact_key(value: str) -> str:
    return normalize_text(value)


def _record_fact(seen_facts: set[str] | None, value: str) -> bool:
    key = _fact_key(value)
    if not key:
        return False
    if seen_facts is not None:
        if key in seen_facts:
            return False
        seen_facts.add(key)
    return True


def _render_fact_list(
    values: Any,
    *,
    limit: int | None = None,
    seen_facts: set[str] | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        text = str(values or "").strip()
        if text and _record_fact(seen_facts, text):
            return text
        return ""

    rendered: list[str] = []
    local_seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if limit is not None and len(rendered) >= limit:
            break
    return ", ".join(rendered)


def _render_scripture_references(
    values: Any,
    *,
    limit: int | None = None,
    seen_facts: set[str] | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    local_seen: set[str] = set()
    for value in values:
        text = ""
        if isinstance(value, Mapping):
            reference = str(value.get("reference") or "").strip()
            relationship = str(value.get("relationship") or "").strip()
            if reference and relationship:
                text = f"{reference} ({relationship})"
            elif reference:
                text = reference
        else:
            text = str(value).strip()
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if limit is not None and len(rendered) >= limit:
            break
    return ", ".join(rendered)


def _render_related_objects(
    values: Any,
    *,
    limit: int | None = None,
    seen_facts: set[str] | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        return ""
    rendered: list[str] = []
    local_seen: set[str] = set()
    for value in values:
        if isinstance(value, Mapping):
            object_id = str(value.get("id") or "").strip()
            relationship = str(value.get("relationship") or "").strip()
            weight = value.get("weight")
            notes = str(value.get("notes") or "").strip()
            parts = [part for part in [object_id, relationship] if part]
            if weight is not None:
                parts.append(f"weight {weight}")
            if notes:
                parts.append(notes)
            text = " / ".join(parts)
        else:
            text = str(value).strip()
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if limit is not None and len(rendered) >= limit:
            break
    return ", ".join(rendered)


def _render_source_entry(value: Any, *, detail_level: int) -> str:
    if isinstance(value, Mapping):
        title = str(value.get("title") or "").strip()
        locator = str(value.get("locator") or "").strip()
        author = str(value.get("author") or "").strip()
        publisher = str(value.get("publisher") or "").strip()
        source_type = str(value.get("source_type") or "").strip()
        notes = str(value.get("notes") or "").strip()
        year = value.get("year")

        parts: list[str] = []
        if title:
            parts.append(title)
        elif author:
            parts.append(author)
        elif source_type:
            parts.append(source_type)

        if detail_level <= 1:
            if locator:
                parts.append(f"[{locator}]")
            return " ".join(part for part in parts if part)

        if author and author not in parts:
            parts.append(author)
        if publisher:
            parts.append(publisher)
        if year is not None:
            parts.append(str(year))
        if source_type:
            parts.append(source_type)
        if locator:
            parts.append(locator)
        if notes:
            parts.append(notes)
        return " / ".join(part for part in parts if part)

    return str(value or "").strip()


def _render_sources(
    values: Any,
    *,
    detail_level: int,
    seen_facts: set[str] | None = None,
    limit: int | None = None,
) -> str:
    if not isinstance(values, (list, tuple)):
        text = _render_source_entry(values, detail_level=detail_level)
        if text and _record_fact(seen_facts, text):
            return text
        return ""

    rendered: list[str] = []
    local_seen: set[str] = set()
    effective_limit = limit if limit is not None else SOURCE_LIMITS_BY_DETAIL_LEVEL[detail_level]
    for value in values:
        text = _render_source_entry(value, detail_level=detail_level)
        if not text:
            continue
        key = _fact_key(text)
        if not key or key in local_seen:
            continue
        if seen_facts is not None and key in seen_facts:
            continue
        local_seen.add(key)
        if seen_facts is not None:
            seen_facts.add(key)
        rendered.append(text)
        if effective_limit is not None and len(rendered) >= effective_limit:
            break
    return ", ".join(rendered)


def _topic_fields_for_detail_level(detail_level: int, compact: bool) -> tuple[str, ...]:
    adjusted_level = max(0, detail_level - 1) if compact else detail_level
    if adjusted_level >= 2:
        return TOPIC_FIELDS_BY_DETAIL_LEVEL[2]
    if adjusted_level == 1:
        return TOPIC_FIELDS_BY_DETAIL_LEVEL[1]
    return TOPIC_FIELDS_BY_DETAIL_LEVEL[0]


def _shared_sections_for_detail_level(detail_level: int) -> tuple[tuple[str, str], ...]:
    return SHARED_SECTION_FIELDS_BY_DETAIL_LEVEL.get(
        detail_level,
        SHARED_SECTION_FIELDS_BY_DETAIL_LEVEL[1],
    )


def _render_topic_field(
    label: str,
    value: Any,
    *,
    detail_level: int,
    seen_facts: set[str] | None,
    compact: bool,
) -> str:
    if value is None:
        return ""

    limit = None
    if compact:
        limit_map = {
            "Aliases": 2,
            "Authorship positions": 2,
            "Date ranges": 2,
            "Original audience": 1,
            "Historical setting": 1,
            "Genre": 2,
            "Structure": 3,
            "Major themes": 3,
            "Canonical placement": 1,
            "Key people": 3,
            "Key places": 3,
            "Key events": 3,
            "Interpretive disputes": 2,
            "Primary sources": 3,
            "Scripture references": 2,
            "Common questions": 1,
            "Interpretive notes": 1,
            "Related objects": 2,
            "Sources": max(1, SOURCE_LIMITS_BY_DETAIL_LEVEL[detail_level] - 1),
        }
        limit = limit_map.get(label)
    elif label in {
        "Aliases",
        "Authorship positions",
        "Date ranges",
        "Genre",
        "Structure",
        "Major themes",
        "Key people",
        "Key places",
        "Key events",
        "Interpretive disputes",
        "Primary sources",
        "Scripture references",
        "Related objects",
    }:
        limit = 3
    elif label in {"Common questions", "Interpretive notes"}:
        limit = 2

    if label == "Scripture references":
        rendered = _render_scripture_references(value, limit=limit, seen_facts=seen_facts)
    elif label == "Related objects":
        rendered = _render_related_objects(value, limit=limit, seen_facts=seen_facts)
    elif label == "Sources":
        rendered = _render_sources(value, detail_level=detail_level, seen_facts=seen_facts, limit=limit)
    else:
        rendered = _render_fact_list(value, limit=limit, seen_facts=seen_facts)

    if not rendered:
        return ""
    return f"  - {label}: {rendered}"


def _question_type(question: str) -> str:
    for name, pattern in _QUESTION_TYPE_PATTERNS:
        if pattern.search(question):
            return name
    return "general"


def _is_book_overview_question(question: str, reference: ReferenceContext | None) -> bool:
    if _question_type(question) == "book_overview":
        return True
    normalized = normalize_text(question)
    return bool(reference and reference.book and re.search(r"\b(?:message|overview|book)\b", normalized))


def _entity_tokens(title: str) -> set[str]:
    return {
        token for token in tokenize_query(title)
        if len(token) >= 3 and token not in _ROLE_WORDS
    }


def _extract_primary_entities(library: CanonicalLibrary, question: str) -> list[dict[str, str]]:
    """Resolve named CKL entities directly from the user's wording.

    This supplements CKL's broad lexical retrieval.  It intentionally matches
    only entity- or concept-bearing categories and requires a meaningful title
    token, so a book title cannot displace a named person, covenant, or cultural
    institution merely because the passage is in that book.
    """
    question_tokens = set(tokenize_query(question))
    question_tokens.update(token[:-1] for token in tuple(question_tokens) if token.endswith("s") and len(token) > 4)
    found: list[dict[str, str]] = []
    header_loader = getattr(library, "object_headers", None)
    entity_categories = {
        "person",
        "place",
        "event",
        "institution",
        "theme",
        "covenant",
        "biblical_theology",
        "cultural_background",
        "symbol",
        "literary_device",
        "doctrine",
    }
    if callable(header_loader):
        candidates = header_loader(tuple(sorted(entity_categories)))
    else:
        candidates = [
            {"id": object_id, "type": getattr(obj, "type", ""), "title": getattr(obj, "title", object_id)}
            for object_id, obj in (getattr(library, "objects_by_id", {}) or {}).items()
        ]
    for header in candidates:
        object_id = str(header.get("id") or "")
        category = str(header.get("type") or "").strip().lower()
        if category not in entity_categories:
            continue
        title = str(header.get("title") or object_id)
        tokens = _entity_tokens(title)
        if not tokens or not tokens.intersection(question_tokens):
            continue
        # Single-name persons (Hannah, Ruth, Boaz, Samuel) are high-signal;
        # multiword titles require all distinctive tokens to avoid weak hits.
        if len(tokens) > 1 and not tokens.issubset(question_tokens):
            continue
        found.append({"id": object_id, "name": title, "type": category})
    return sorted(found, key=lambda item: (item["type"] != "person", item["name"].lower(), item["id"]))


def _question_terms_with_hints(question: str) -> set[str]:
    terms = set(tokenize_query(question))
    for term in tuple(terms):
        terms.update(_PASSAGE_HINTS.get(term, ()))
    return {term for term in terms if len(term) >= 3 and term not in _RETRIEVAL_NOISE_TERMS}


def _extract_primary_symbols(question: str) -> list[str]:
    normalized = normalize_text(question)
    symbols: list[str] = []
    for phrase in ("seven stars", "seven churches", "lampstands", "beast", "dragon"):
        if phrase in normalized:
            symbols.append(phrase)
    return symbols


def _infer_passage_from_entities(
    question: str,
    entities: Sequence[Mapping[str, str]],
) -> ReferenceContext | None:
    """Infer one immediate chapter from locally installed Scripture.

    This is a fallback for questions such as “Why was Hannah unable to
    conceive?” that name a narrative subject but omit a reference.  It uses
    entity co-occurrence and question terms, not a model-generated guess.
    """
    names = [normalize_text(str(entity.get("name") or "")) for entity in entities]
    entity_terms = {token for name in names for token in tokenize_query(name) if len(token) >= 3 and token not in _ROLE_WORDS}
    if not entity_terms:
        return None
    try:
        from .bible import build_bible_search_index
        from .references import BOOKS

        best: tuple[int, str, int] | None = None
        question_terms = _question_terms_with_hints(question)
        for verse in build_bible_search_index():
            text = normalize_text(str(verse.get("text") or ""))
            words = set(tokenize_query(text))
            entity_hits = len(entity_terms.intersection(words))
            if not entity_hits:
                continue
            term_hits = question_terms.intersection(words)
            score = entity_hits * 80 + len(term_hits) * 70
            for hit in term_hits.intersection(_PASSAGE_ANCHOR_TERMS):
                # For causal barrenness questions, the text's stated condition
                # (closed womb) is more diagnostic than the later conception.
                score += 420 if hit in {"womb", "barren", "barrenness"} else 150
            # Prefer the first occurrence only after textual relevance ties;
            # this preserves narrative order without turning book metadata into
            # a retrieval feature.
            candidate = (score, str(verse["book"]), int(verse["chapter"]))
            if best is None or candidate[0] > best[0]:
                best = candidate
        if best is None:
            return None
        return ReferenceContext(
            book=best[1], chapter=best[2], testament=BOOKS[best[1]][0],
            is_reference_based=False, topic=None, confidence=0.62,
        )
    except Exception:  # Scripture evidence is helpful, never a retrieval blocker.
        return None


def _reference_overlap(topic: Mapping[str, Any], reference: ReferenceContext | None) -> int:
    if reference is None or not reference.book or reference.chapter is None:
        return 0
    prefix = normalize_text(f"{reference.book} {reference.chapter}")
    for item in topic.get("scripture_references") or []:
        value = item.get("reference") if isinstance(item, Mapping) else item
        if normalize_text(str(value or "")).startswith(prefix):
            return 1
    return 0


def _direct_textual_evidence(reference: ReferenceContext | None, question: str, entities: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    if reference is None or not reference.book or reference.chapter is None:
        return {"reference": None, "facts": [], "chronology": []}
    try:
        chapter = resolve_chapter(reference.book, reference.chapter)
    except Exception:
        return {"reference": f"{reference.book} {reference.chapter}", "facts": [], "chronology": []}
    entity_terms = {token for item in entities for token in tokenize_query(str(item.get("name") or "")) if len(token) >= 3 and token not in _ROLE_WORDS}
    question_terms = _question_terms_with_hints(question)
    question_terms.difference_update(tokenize_query(reference.book))
    selected: list[dict[str, str]] = []
    for verse in chapter.get("verses") or []:
        text = str(verse.get("text") or "").strip()
        words = set(tokenize_query(text))
        entity_hit = entity_terms.intersection(words)
        question_hit = question_terms.intersection(words)
        if (entity_hit and (question_hit or len(selected) < 1)) or (not entity_terms and question_hit) or (selected and question_hit):
            selected.append({"reference": f"{reference.book} {reference.chapter}:{verse['verse']}", "claim": text})
    if not selected:
        for verse in chapter.get("verses") or []:
            text = str(verse.get("text") or "").strip()
            if entity_terms.intersection(set(tokenize_query(text))):
                selected.append({"reference": f"{reference.book} {reference.chapter}:{verse['verse']}", "claim": text})
                break
    # Keep the most question-bearing verses, then restore narrative order. This
    # surfaces an explicit interpretation such as Revelation 1:20 instead of
    # merely the first occurrence of a repeated symbol.
    selected.sort(
        key=lambda item: (
            -(
                len(question_terms.intersection(set(tokenize_query(item["claim"]))))
                + len(question_terms.intersection(set(tokenize_query(item["claim"]))).intersection(_PASSAGE_ANCHOR_TERMS)) * 4
            ),
            int(item["reference"].rsplit(":", 1)[-1]),
        )
    )
    selected = sorted(
        selected[:4], key=lambda item: int(item["reference"].rsplit(":", 1)[-1])
    )
    # The same ordered facts provide a lightweight chronology guard against
    # treating a later prayer or vow as an earlier cause.
    return {
        "reference": f"{reference.book} {reference.chapter}",
        "facts": selected,
        "chronology": [item["reference"] for item in selected],
        "chronology_guard": (
            "Do not treat a later action in this sequence as the cause of an earlier condition unless the text explicitly makes that connection."
            if _question_type(question) == "cause" else ""
        ),
    }


def _rank_retrieval_topics(
    topics: Sequence[dict[str, Any]],
    *,
    entity_ids: set[str],
    reference: ReferenceContext | None,
    broad_question: bool,
) -> list[dict[str, Any]]:
    """Apply the deterministic question-driven tier order to CKL candidates."""
    ranked: list[dict[str, Any]] = []
    for topic in topics:
        category = str(topic.get("type") or "").lower()
        score = float(topic.get("score") or 0.0)
        entity_match = str(topic.get("id") or "") in entity_ids
        passage_overlap = _reference_overlap(topic, reference)
        combined = score * 100
        if entity_match:
            combined += 120
        if str(topic.get("match_type") or "") == "exact_entity" and not broad_question:
            combined += 150
        if passage_overlap:
            combined += 85
        if category == "book" and not broad_question:
            combined -= 75
            if passage_overlap:
                combined += 160
        if category == "book" and broad_question:
            combined += 125
        if category in {"faq", "theology", "archaeology"} and not entity_match:
            combined -= 80
        if reference and reference.book and reference.chapter and not passage_overlap and category != "book":
            references = topic.get("scripture_references") or []
            if references:
                combined -= 55
        topic["entity_match_score"] = 1.0 if entity_match else 0.0
        topic["passage_proximity_score"] = 1.0 if passage_overlap else 0.0
        topic["combined_score"] = round(combined, 3)
        ranked.append(topic)
    return sorted(ranked, key=lambda item: (-float(item["combined_score"]), str(item.get("id") or "")))


def build_canonical_context(
    library: CanonicalLibrary,
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
    *,
    max_results: int = 5,
    include_placeholders: bool = True,
    allowed_statuses: Sequence[str] | None = None,
    answer_mode: str = "study",
    max_context_tokens: int | None = None,
    study_action: str | None = None,
) -> dict[str, Any] | None:
    """Retrieve a compact CKL context package for one question."""

    normalized_answer_mode = _normalize_answer_mode(answer_mode)
    normalized_study_action = str(study_action or "").strip().lower()
    cultural_scope = normalized_study_action == "cultural_context" or (
        question_context is not None and question_context.question_type == "cultural_context"
    )
    if cultural_scope:
        max_results = min(max_results, CULTURAL_CONTEXT_MAX_RESULTS)
        if max_context_tokens is None:
            max_context_tokens = CULTURAL_CONTEXT_MAX_TOKENS
        else:
            max_context_tokens = min(max_context_tokens, CULTURAL_CONTEXT_MAX_TOKENS)
    query = build_canonical_query(question, reference_context, question_context)
    search_limit = max(max_results * 4, max_results, 12)
    topic_budget = _topic_token_budget(max_context_tokens, normalized_answer_mode)
    builder = CanonicalContextBuilder(
        library,
        max_topics=search_limit,
        max_relationship_depth=1,
        max_expanded_topics=max_results,
        min_relationship_weight=6,
    )
    context = builder.build(
        query,
        limit=search_limit,
        include_placeholders=include_placeholders,
        allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
    )

    broad_topics = list(context.get("retrieved_topics") or [])
    selected_topics: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    exact_queries = _candidate_exact_queries(question, reference_context, question_context)
    retrieval_entities = _extract_primary_entities(library, question)
    evidence_reference = reference_context
    if evidence_reference is None:
        alias_loader = getattr(library, "book_alias_lookup", None)
        alias_lookup = alias_loader() if callable(alias_loader) else getattr(library, "_book_alias_lookup", {})
        structured_query = analyze_structured_query(question, book_alias_lookup=alias_lookup)
        if structured_query.scripture_references:
            span = structured_query.scripture_references[0]
            evidence_reference = ReferenceContext(
                book=span.book,
                chapter=span.start_chapter,
                verse=span.start_verse,
                verse_end=span.end_verse,
                is_reference_based=span.start_chapter is not None,
                confidence=1.0,
            )
    broad_question = _is_book_overview_question(question, evidence_reference)
    if not broad_question and not (evidence_reference and evidence_reference.book and evidence_reference.chapter):
        evidence_reference = _infer_passage_from_entities(question, retrieval_entities)
    direct_evidence = _direct_textual_evidence(evidence_reference, question, retrieval_entities)
    exact_count = 0
    scripture_count = 0
    topic_tokens_used = 0

    def _is_cultural_topic(topic: Mapping[str, Any]) -> bool:
        if not cultural_scope:
            return True
        object_type = str(topic.get("type") or "").strip().lower()
        if object_type not in CULTURAL_CONTEXT_OBJECT_TYPES:
            return False
        if reference_context is None or reference_context.testament != "New Testament":
            return True
        # Do not inject an Ancient Near Eastern-only entry into an NT study unless
        # the query explicitly asks for that background.
        ancient = str(topic.get("ancient_near_east_context") or "").strip()
        other_cultural = any(
            str(topic.get(field) or "").strip()
            for field in ("hebraic_worldview", "second_temple_context")
        ) or bool(topic.get("archaeology"))
        return not ancient or other_cultural or "ancient near eastern" in query.lower()

    def _track_topic_tokens(topic: Mapping[str, Any]) -> None:
        nonlocal topic_tokens_used
        topic_tokens_used += int(topic.get("estimated_tokens") or 0)

    def _within_topic_budget(topic: Mapping[str, Any]) -> bool:
        if topic_budget is None:
            return True
        if not selected_topics:
            return True
        estimated = int(topic.get("estimated_tokens") or 0)
        return topic_tokens_used + estimated <= topic_budget

    # A genuinely broad question is the one exception to the usual rule: the
    # matching book overview is its direct subject, not background material.
    if broad_question:
        normalized_question = normalize_text(question)
        header_loader = getattr(library, "object_headers", None)
        if callable(header_loader):
            book_headers = header_loader(("book",))
        else:
            book_headers = [
                {"id": object_id, "title": getattr(obj, "title", ""), "type": getattr(obj, "type", "")}
                for object_id, obj in (getattr(library, "objects_by_id", {}) or {}).items()
                if str(getattr(obj, "type", "") or "").lower() == "book"
            ]
        for header in book_headers:
            object_id = str(header.get("id") or "")
            title = normalize_text(str(header.get("title") or ""))
            if not title or title not in normalized_question:
                continue
            result = library.retrieve_by_id(
                object_id,
                include_placeholders=include_placeholders,
                allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
            )
            if result is None:
                continue
            builder._append_topic(
                selected_topics, result.object, inclusion_type="primary", seen_ids=seen_ids,
                score=result.score, match_type="exact_book_subject", matched_alias=result.matched_alias,
                matched_terms=[str(getattr(result.object, "title", ""))], matched_fields=["title"],
            )
            _track_topic_tokens(selected_topics[-1])
            exact_count += 1
            break

    # Tier 2: exact named CKL entities and events precede book-level passage
    # matches.  The former code performed this in reverse order, so a broad
    # book record could consume the result budget before Hannah, Ruth, or Boaz
    # was even considered.
    for entity in retrieval_entities:
        result = library.retrieve_by_id(
            entity["id"],
            include_placeholders=include_placeholders,
            allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
        )
        if result is None or result.object.id in seen_ids:
            continue
        builder._append_topic(
            selected_topics, result.object, inclusion_type="primary", seen_ids=seen_ids,
            score=result.score, match_type="exact_entity", matched_alias=result.matched_alias,
            matched_terms=[entity["name"]], matched_fields=["title"],
        )
        _track_topic_tokens(selected_topics[-1])
        exact_count += 1
        if len(selected_topics) >= max_results:
            break

    # Tier 1 CKL passage matches follow the named subject; direct Bible text is
    # separately packed ahead of both tiers below.
    if evidence_reference is not None and evidence_reference.book:
        scripture_results = library.retrieve_by_scripture_reference(
            evidence_reference,
            limit=search_limit,
            include_placeholders=include_placeholders,
            allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
        )
        for result in scripture_results:
            if len(selected_topics) >= max_results:
                break
            if result.object.id in seen_ids:
                continue
            candidate = []
            builder._append_topic(
                candidate,
                result.object,
                inclusion_type="primary",
                seen_ids=set(),
                score=result.score,
                match_type=result.match_type,
                matched_alias=result.matched_alias,
                matched_terms=result.matched_terms,
                matched_fields=result.matched_fields,
            )
            if not candidate or not _is_cultural_topic(candidate[0]):
                continue
            builder._append_topic(
                selected_topics,
                result.object,
                inclusion_type="primary",
                seen_ids=seen_ids,
                score=result.score,
                match_type=result.match_type,
                matched_alias=result.matched_alias,
                matched_terms=result.matched_terms,
                matched_fields=result.matched_fields,
            )
            _track_topic_tokens(selected_topics[-1])
            scripture_count += 1

    if len(selected_topics) < max_results:
        for search_text in exact_queries:
            if len(selected_topics) >= max_results:
                break
            result = library.retrieve_exact(
                search_text,
                include_placeholders=include_placeholders,
                allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
            )
            if result is None or result.object.id in seen_ids:
                continue
            candidate = []
            builder._append_topic(
                candidate,
                result.object,
                inclusion_type="primary",
                seen_ids=set(),
                score=result.score,
                match_type=result.match_type,
                matched_alias=result.matched_alias,
                matched_terms=result.matched_terms,
                matched_fields=result.matched_fields,
            )
            if not candidate or not _is_cultural_topic(candidate[0]):
                continue
            builder._append_topic(
                selected_topics,
                result.object,
                inclusion_type="primary",
                seen_ids=seen_ids,
                score=result.score,
                match_type=result.match_type,
                matched_alias=result.matched_alias,
                matched_terms=result.matched_terms,
                matched_fields=result.matched_fields,
            )
            _track_topic_tokens(selected_topics[-1])
            exact_count += 1

    expanded_count = 0

    if len(selected_topics) < max_results:
        for topic in broad_topics:
            object_id = str(topic.get("id") or "").strip()
            if not object_id or object_id in seen_ids:
                continue
            if topic_budget is not None and not _within_topic_budget(topic):
                continue
            if not _is_cultural_topic(topic):
                continue
            selected_topics.append(topic)
            seen_ids.add(object_id)
            _track_topic_tokens(topic)
            if len(selected_topics) >= max_results:
                break

    # Retain one book record as lower-tier literary context whenever a passage
    # is known. It is re-ranked after direct people/events and can replace only
    # the last weak candidate when the result budget is already full.
    if evidence_reference and evidence_reference.book and not any(
        str(topic.get("type") or "").lower() == "book" for topic in selected_topics
    ):
        target = normalize_text(evidence_reference.book)
        for object_id, obj in (getattr(library, "objects_by_id", {}) or {}).items():
            if str(getattr(obj, "type", "") or "").lower() != "book" or normalize_text(str(getattr(obj, "title", ""))) != target:
                continue
            result = library.retrieve_by_id(
                object_id,
                include_placeholders=include_placeholders,
                allowed_statuses=tuple(allowed_statuses) if allowed_statuses is not None else None,
            )
            if result is not None:
                if len(selected_topics) >= max_results:
                    removed = selected_topics.pop()
                    seen_ids.discard(str(removed.get("id") or ""))
                builder._append_topic(
                    selected_topics, result.object, inclusion_type="background", seen_ids=seen_ids,
                    score=result.score, match_type="book_context", matched_alias=result.matched_alias,
                    matched_terms=[evidence_reference.book], matched_fields=["title"],
                )
            break

    retrieved_topics = _rank_retrieval_topics(
        selected_topics,
        entity_ids={entity["id"] for entity in retrieval_entities},
        reference=evidence_reference,
        broad_question=broad_question,
    )
    if not retrieved_topics:
        return None

    metadata = dict(context.get("metadata") or {})
    retrieved_object_ids = [str(topic.get("id") or "").strip() for topic in retrieved_topics]
    retrieved_object_ids = [object_id for object_id in retrieved_object_ids if object_id]
    retrieval_steps: list[str] = []
    if exact_count:
        retrieval_steps.append("exact")
    if scripture_count:
        retrieval_steps.append("scripture")
    if expanded_count:
        retrieval_steps.append("relationship")
    if len(retrieved_topics) > exact_count + scripture_count + expanded_count:
        retrieval_steps.append("keyword")
    retrieval_method = "+".join(dict.fromkeys(retrieval_steps))
    if not retrieval_method:
        retrieval_method = str(metadata.get("retrieval_method") or "keyword").strip() or "keyword"
    metadata.update(
        {
            "query": query,
            "retrieved_object_ids": retrieved_object_ids,
            "retrieval_method": retrieval_method,
            "answer_mode": normalized_answer_mode,
            "topic_count": len(retrieved_topics),
            "primary_topic_count": exact_count,
            "scripture_topic_count": scripture_count,
            "expanded_topic_count": expanded_count,
            "relationship_topic_count": expanded_count,
            "max_results": max_results,
            "max_context_tokens": max_context_tokens,
            "study_action": "cultural_context" if cultural_scope else normalized_study_action,
            "retrieval_scope": "cultural" if cultural_scope else "general",
            "topic_token_budget": topic_budget,
            "estimated_topic_tokens": sum(int(topic.get("estimated_tokens") or 0) for topic in retrieved_topics),
            "include_placeholders": include_placeholders,
            "allowed_statuses": list(allowed_statuses) if allowed_statuses is not None else None,
            "retrieval_intent": {
                "question": question,
                "passage": direct_evidence.get("reference"),
                "primary_entities": retrieval_entities,
                "primary_events": [entity for entity in retrieval_entities if entity["type"] == "event"],
                "primary_symbols": _extract_primary_symbols(question),
                "themes": sorted(_question_terms_with_hints(question)),
                "question_type": _question_type(question),
                "broad_question": broad_question,
            },
            "direct_textual_evidence": direct_evidence,
            "rejected_results": [],
        }
    )
    context["metadata"] = metadata
    context["question"] = question
    context["query"] = query
    context["retrieved_topics"] = retrieved_topics
    context["retrieved_object_ids"] = retrieved_object_ids
    return context


def format_canonical_context_for_prompt(
    context: Mapping[str, Any] | None,
    *,
    max_context_tokens: int = 1200,
    answer_mode: str = "study",
    study_action: str | None = None,
) -> str:
    if not context:
        return ""

    retrieved_topics = list(context.get("retrieved_topics") or [])
    if not retrieved_topics:
        return ""

    metadata = dict(context.get("metadata") or {})
    normalized_answer_mode = _normalize_answer_mode(answer_mode or metadata.get("answer_mode") or "study")
    cultural_scope = (
        str(study_action or metadata.get("study_action") or "").strip().lower()
        == "cultural_context"
        or str(metadata.get("retrieval_scope") or "").strip().lower() == "cultural"
    )
    if cultural_scope:
        max_context_tokens = min(max_context_tokens, CULTURAL_CONTEXT_MAX_TOKENS)
    max_entries, max_facts_per_entry, max_scripture_references_per_entry, max_caution_notes_per_entry = _canonical_prompt_limits(
        normalized_answer_mode
    )
    prompt_context = build_canonical_prompt_context(
        context,
        max_context_tokens=max_context_tokens,
        max_entries=max_entries,
        max_facts_per_entry=max_facts_per_entry,
        max_scripture_references_per_entry=max_scripture_references_per_entry,
        max_caution_notes_per_entry=max_caution_notes_per_entry,
        answer_mode=normalized_answer_mode,
        scope="cultural_context" if cultural_scope else "general",
    )

    prompt = _render_canonical_prompt_context(prompt_context, answer_mode=normalized_answer_mode)
    if not prompt:
        return ""
    direct_evidence = metadata.get("direct_textual_evidence")
    if isinstance(direct_evidence, Mapping) and direct_evidence.get("facts"):
        lines = ["# DIRECT TEXTUAL EVIDENCE", f"Requested passage: {direct_evidence.get('reference')}"]
        for fact in direct_evidence.get("facts") or []:
            if isinstance(fact, Mapping):
                reference = str(fact.get("reference") or "").strip()
                claim = str(fact.get("claim") or "").strip()
                if reference and claim:
                    lines.append(f"- {reference}: {claim}")
        chronology_guard = str(direct_evidence.get("chronology_guard") or "").strip()
        if chronology_guard:
            lines.append(f"- Chronology guard: {chronology_guard}")
        lines.append("")
        # Direct Scripture always precedes CKL summaries in the final packed
        # context, even when a broad book record is retained as background.
        prompt = "\n".join(lines) + prompt
    if _estimate_tokens(prompt) > max_context_tokens:
        prompt = _shrink_prompt(prompt, max_context_tokens)
    return prompt


def canonical_context_has_strong_match(
    context: Mapping[str, Any] | None,
    *,
    minimum_score: float = CKL_STRONG_MATCH_THRESHOLD,
) -> bool:
    if not context:
        return False

    metadata = dict(context.get("metadata") or {})
    if int(metadata.get("primary_topic_count") or 0) > 0:
        return True

    # A high numeric score is not sufficient on its own. Generic phrase or
    # keyword overlap can score highly (for example, a question containing a
    # chapter number and "mean") while pointing to an unrelated book. Strong
    # context must come from a direct/entity/scripture match or an explicitly
    # counted primary topic.
    strong_match_types = {
        "id",
        "alias",
        "exact",
        "exact_entity",
        "exact_book_subject",
        "scripture",
        "scripture_match",
    }
    for topic in context.get("retrieved_topics") or []:
        if not isinstance(topic, Mapping):
            continue
        match_type = str(topic.get("match_type") or "").strip().lower()
        if match_type in strong_match_types:
            if match_type in {"id", "alias", "exact", "exact_entity", "exact_book_subject"}:
                return True
            try:
                score = float(topic.get("score") or 0)
            except (TypeError, ValueError):
                score = 0.0
            if score >= float(minimum_score):
                return True
    return False


def build_canonical_fallback_answer(
    context: Mapping[str, Any] | None,
    *,
    max_context_tokens: int = 1200,
    answer_mode: str = "study",
    retrieval_failed: bool = False,
) -> dict[str, Any]:
    """Return a safe limitation message for legacy fallback callers.

    CKL records are research evidence. They must never be serialized as a
    substitute for a synthesized user-facing answer, even if model generation
    is unavailable. The normal ask pipeline now treats this condition as a
    controlled synthesis failure instead of calling this compatibility helper.
    """

    if retrieval_failed:
        message = "The Canonical Knowledge Library could not be retrieved for this question."
        return {
            "text": message,
            "kind": "retrieval_failed",
            "message": message,
            "strong_match": False,
            "selected_entry_ids": [],
            "entry_count": 0,
            "estimated_tokens": 0,
            "truncated": False,
        }

    if not context:
        message = "The Canonical Knowledge Library does not currently have a strong match for this question."
        return {
            "text": message,
            "kind": "no_strong_match",
            "message": message,
            "strong_match": False,
            "selected_entry_ids": [],
            "entry_count": 0,
            "estimated_tokens": 0,
            "truncated": False,
        }

    normalized_answer_mode = _normalize_answer_mode(answer_mode)
    max_entries, max_facts_per_entry, max_scripture_references_per_entry, max_caution_notes_per_entry = _canonical_prompt_limits(
        normalized_answer_mode
    )
    prompt_context = build_canonical_prompt_context(
        context,
        max_context_tokens=max_context_tokens,
        max_entries=min(3, max_entries),
        max_facts_per_entry=min(3, max_facts_per_entry),
        max_scripture_references_per_entry=min(3, max_scripture_references_per_entry),
        max_caution_notes_per_entry=min(2, max_caution_notes_per_entry),
        answer_mode=normalized_answer_mode,
    )
    metadata = dict(prompt_context.get("metadata") or {})
    selected_entry_ids = [
        str(entry_id).strip()
        for entry_id in metadata.get("selected_entry_ids") or []
        if str(entry_id).strip()
    ]

    if not canonical_context_has_strong_match(context):
        message = "The Canonical Knowledge Library does not currently have a strong match for this question."
        return {
            "text": message,
            "kind": "no_strong_match",
            "message": message,
            "strong_match": False,
            "selected_entry_ids": selected_entry_ids,
            "entry_count": int(metadata.get("entry_count") or 0),
            "estimated_tokens": int(metadata.get("estimated_tokens") or 0),
            "truncated": bool(metadata.get("truncated", False)),
        }

    del normalized_answer_mode
    message = (
        "BHF found relevant study evidence but could not generate a validated "
        "final answer. Please try the question again when the model backend is available."
    )
    return {
        "text": message,
        "kind": "synthesis_unavailable",
        "message": message,
        "strong_match": True,
        "selected_entry_ids": selected_entry_ids,
        "entry_count": int(metadata.get("entry_count") or 0),
        "estimated_tokens": int(metadata.get("estimated_tokens") or 0),
        "truncated": bool(metadata.get("truncated", False)),
    }


def format_canonical_context_for_fallback(
    context: Mapping[str, Any] | None,
    *,
    max_context_tokens: int = 1200,
    answer_mode: str = "study",
    retrieval_failed: bool = False,
) -> str:
    return str(
        build_canonical_fallback_answer(
            context,
            max_context_tokens=max_context_tokens,
            answer_mode=answer_mode,
            retrieval_failed=retrieval_failed,
        ).get("text", "")
    )



def _render_topic_block(
    topic: Mapping[str, Any],
    *,
    answer_mode: str,
    compact: bool,
    seen_facts: set[str] | None = None,
) -> str:
    object_id = str(topic.get("id") or "").strip() or "unknown"
    title = str(topic.get("title") or object_id).strip()
    type_name = str(topic.get("type") or "unknown").strip()
    match_type = str(topic.get("match_type") or "unknown").strip()
    inclusion_type = str(topic.get("inclusion_type") or "primary").strip()
    score = topic.get("score")
    content_status = str(topic.get("content_status") or "placeholder").strip()
    review_status = str(topic.get("review_status") or "unreviewed").strip()
    detail_level = _context_detail_level(answer_mode)

    lines = [
        f"- {title} (`{object_id}`) [{type_name}]",
        f"  - Match: {match_type} ({inclusion_type})",
        f"  - Status: {content_status} / {review_status}",
    ]
    if score is not None:
        lines.append(f"  - Score: {float(score):.4f}")

    estimated_tokens = topic.get("estimated_tokens")
    if estimated_tokens is not None:
        lines.append(f"  - Estimated tokens: {int(estimated_tokens)}")

    fields = _topic_fields_for_detail_level(detail_level, compact)
    label_map = {
        "aliases": "Aliases",
        "summary": "Summary",
        "authorship_positions": "Authorship positions",
        "date_ranges": "Date ranges",
        "original_audience": "Original audience",
        "historical_setting": "Historical setting",
        "genre": "Genre",
        "structure": "Structure",
        "major_themes": "Major themes",
        "canonical_placement": "Canonical placement",
        "key_people": "Key people",
        "key_places": "Key places",
        "key_events": "Key events",
        "interpretive_disputes": "Interpretive disputes",
        "primary_sources": "Primary sources",
        "historical_context": "Historical context",
        "ancient_near_east_context": "Ancient Near East context",
        "hebraic_worldview": "Hebraic worldview",
        "second_temple_context": "Second Temple context",
        "literary_context": "Literary context",
        "covenantal_significance": "Covenantal significance",
        "canonical_context": "Canonical context",
        "later_christian_reception": "Later Christian reception",
        "intertextuality": "Intertextual connections",
        "cross_references": "Cross references",
        "scripture_references": "Scripture references",
        "common_questions": "Common questions",
        "interpretive_notes": "Interpretive notes",
        "hebrew_words": "Hebrew words",
        "greek_words": "Greek words",
        "timeline": "Timeline",
        "archaeology": "Archaeology",
        "new_testament_connections": "New Testament connections",
        "related_objects": "Related objects",
        "sources": "Sources",
    }
    for field_name in fields:
        rendered = _render_topic_field(
            label_map[field_name],
            topic.get(field_name),
            detail_level=detail_level,
            seen_facts=seen_facts,
            compact=compact,
        )
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)

def _shrink_prompt(prompt: str, max_context_tokens: int) -> str:
    if _estimate_tokens(prompt) <= max_context_tokens:
        return prompt
    max_chars = max_context_tokens * 4
    trimmed = prompt[:max_chars].rstrip()
    if trimmed and not trimmed.endswith("..."):
        trimmed = trimmed.rstrip() + "\n..."
    return trimmed


def _canonical_prompt_limits(answer_mode: str) -> tuple[int, int, int, int]:
    detail_level = _context_detail_level(answer_mode)
    if detail_level <= 0:
        return 4, 2, 3, 1
    if detail_level == 1:
        return 6, 3, 5, 2
    return 8, 5, 6, 3


def _render_canonical_prompt_entry_lines(
    entry: Mapping[str, Any],
    *,
    answer_mode: str,
    include_internal_details: bool = True,
    include_source_ids: bool = True,
) -> list[str]:
    title = str(entry.get("title") or entry.get("id") or "unknown").strip()
    category = str(entry.get("category") or "Unknown").strip()
    detail_level = _context_detail_level(answer_mode)
    lines: list[str] = ["", f"## Entry: {title}", f"Category: {category}"]

    sections = list(entry.get("sections") or [])
    if sections:
        rendered_sources_section = False
        for section in sections:
            heading = str(section.get("heading") or "").strip()
            raw_items = list(section.get("items") or [])
            items: list[str] = []
            for raw_item in raw_items:
                if heading == "Sources":
                    text = _render_source_entry(raw_item, detail_level=detail_level)
                else:
                    text = str(raw_item).strip()
                if text:
                    items.append(text)
            if not heading or not items:
                continue
            if heading == "Summary":
                lines.append("Summary:")
                lines.append(items[0])
                continue
            lines.append(f"{heading}:")
            if heading == "Sources":
                rendered_sources_section = True
                if include_source_ids:
                    source_ids = [
                        str(item).strip()
                        for item in entry.get("source_ids") or []
                        if str(item).strip()
                    ]
                    if source_ids:
                        if len(source_ids) == 1:
                            lines.append(f"Source ID: {source_ids[0]}")
                        else:
                            lines.append("Source IDs: " + ", ".join(source_ids))
            lines.extend(f"- {item}" for item in items)
        if not rendered_sources_section and entry.get("sources"):
            source_items = [
                _render_source_entry(item, detail_level=detail_level)
                for item in entry.get("sources") or []
            ]
            source_items = [item for item in source_items if item]
            if source_items:
                lines.append("Sources:")
                if include_source_ids:
                    source_ids = [
                        str(item).strip()
                        for item in entry.get("source_ids") or []
                        if str(item).strip()
                    ]
                    if source_ids:
                        if len(source_ids) == 1:
                            lines.append(f"Source ID: {source_ids[0]}")
                        else:
                            lines.append("Source IDs: " + ", ".join(source_ids))
                lines.extend(f"- {item}" for item in source_items)
        return [line for line in lines if line is not None]

    summary = str(entry.get("summary") or "").strip()
    facts = [str(item).strip() for item in entry.get("facts") or [] if str(item).strip()]
    scripture_references = [
        str(item).strip()
        for item in entry.get("scripture_references") or []
        if str(item).strip()
    ]
    caution_notes = [
        str(item).strip()
        for item in entry.get("caution_notes") or []
        if str(item).strip()
    ]
    source_ids = [
        str(item).strip()
        for item in entry.get("source_ids") or []
        if str(item).strip()
    ]

    if include_internal_details:
        if summary:
            lines.append("Summary:")
            lines.append(summary)
        if facts:
            lines.append("Relevant facts:")
            lines.extend(f"- {fact}" for fact in facts)
        if scripture_references:
            lines.append("Primary Scripture References:")
            lines.extend(f"- {reference}" for reference in scripture_references)
        if caution_notes:
            lines.append("Interpretive Disputes and Cautions:")
            lines.extend(f"- {note}" for note in caution_notes)
        if source_ids and include_source_ids:
            if len(source_ids) == 1:
                lines.append(f"Source ID: {source_ids[0]}")
            else:
                lines.append("Source IDs: " + ", ".join(source_ids))
    else:
        if summary:
            lines.append(summary)
        if facts:
            lines.append("Relevant facts:")
            lines.extend(f"- {fact}" for fact in facts)
        if scripture_references:
            lines.append("Primary Scripture References:")
            lines.extend(f"- {reference}" for reference in scripture_references)
        if caution_notes:
            lines.append("Interpretive Disputes and Cautions:")
            lines.extend(f"- {note}" for note in caution_notes)

    return [line for line in lines if line is not None]


def _render_canonical_prompt_context(
    context: Mapping[str, Any] | None,
    *,
    answer_mode: str = "study",
    include_internal_details: bool = True,
    include_source_ids: bool = True,
) -> str:
    if not context:
        return ""

    entries = list(context.get("entries") or [])
    if not entries:
        return ""

    lines: list[str] = []
    for entry in entries:
        lines.extend(
            _render_canonical_prompt_entry_lines(
                entry,
                answer_mode=answer_mode,
                include_internal_details=include_internal_details,
                include_source_ids=include_source_ids,
            )
        )

    return "\n".join(line for line in lines if line is not None).strip()
