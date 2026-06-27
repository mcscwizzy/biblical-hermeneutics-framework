"""Local curated knowledge helpers for BHF prompts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import GenreContext, QuestionContext, ReferenceContext


DATA_DIR = Path(__file__).resolve().parent / "data"
LEXICAL_TERMS_PATH = DATA_DIR / "lexical_terms.json"
BOOK_CONTEXTS_PATH = DATA_DIR / "book_contexts.json"
GENRE_GUIDES_PATH = DATA_DIR / "genre_guides.json"


@dataclass(frozen=True)
class LexicalEntry:
    key: str
    language: str
    original: str | None
    transliteration: str
    glosses: list[str]
    semantic_range: list[str]
    cautions: list[str]
    safe_examples: list[str]
    notes: str | None = None


@dataclass(frozen=True)
class BookContextEntry:
    key: str
    book: str
    testament: str
    genre: str
    historical_context_hint: str
    method_guidance: list[str]
    cautions: list[str]


@dataclass(frozen=True)
class GenreGuideEntry:
    key: str
    genre: str
    description: str
    method_guidance: list[str]
    cautions: list[str]


@dataclass(frozen=True)
class LocalKnowledgeBundle:
    lexical_entries: list[LexicalEntry]
    book_context: BookContextEntry | None = None
    genre_guide: GenreGuideEntry | None = None

    def keys(self) -> list[str]:
        keys = [entry.key for entry in self.lexical_entries]
        if self.book_context:
            keys.append(self.book_context.key)
        if self.genre_guide:
            keys.append(self.genre_guide.key)
        return keys


def lookup_lexical_entries(question_context: QuestionContext) -> list[LexicalEntry]:
    """Return deterministic local lexical notes for a classified question."""

    if question_context.question_type != "word_study":
        return []

    entries = load_lexical_entries()
    terms = {_normalize_term(term) for term in question_context.target_terms}
    language = (question_context.target_language or "").lower()
    selected_keys: list[str] = []

    if "ruach" in terms:
        selected_keys.append("ruach")
    if "pneuma" in terms or ("spirit" in terms and language == "greek"):
        selected_keys.append("pneuma")
    if "nephesh" in terms:
        selected_keys.append("nephesh")
    if "qol" in terms:
        selected_keys.append("qol")

    if language == "hebrew" and {"spirit", "wind"}.intersection(terms):
        selected_keys.append("ruach")
        if {"spirit", "wind"}.issubset(terms):
            selected_keys.extend(["nephesh", "qol"])

    return [entries[key] for key in _unique(selected_keys) if key in entries]


def lookup_book_context(
    reference_context: ReferenceContext,
) -> BookContextEntry | None:
    """Return local book context when a biblical book is detected."""

    if not reference_context.book:
        return None
    entries = load_book_context_entries()
    return entries.get(_normalize_key(reference_context.book))


def lookup_genre_guide(genre_context: GenreContext) -> GenreGuideEntry | None:
    """Return local genre guidance when a genre is detected."""

    candidates = []
    if genre_context.primary_genre:
        candidates.append(genre_context.primary_genre)
    candidates.extend(genre_context.secondary_genres)

    entries = load_genre_guide_entries()
    for candidate in candidates:
        guide = entries.get(_normalize_key(candidate))
        if guide:
            return guide
    return None


def lookup_local_knowledge(
    reference_context: ReferenceContext,
    genre_context: GenreContext,
    question_context: QuestionContext,
) -> LocalKnowledgeBundle:
    """Return all deterministic local knowledge relevant to one request."""

    return LocalKnowledgeBundle(
        lexical_entries=lookup_lexical_entries(question_context),
        book_context=lookup_book_context(reference_context),
        genre_guide=lookup_genre_guide(genre_context),
    )


@lru_cache(maxsize=1)
def load_lexical_entries() -> dict[str, LexicalEntry]:
    raw = json.loads(LEXICAL_TERMS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("lexical_terms.json must contain a list")
    entries: dict[str, LexicalEntry] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("lexical entry must be an object")
        entry = _lexical_entry_from_mapping(item)
        entries[entry.key] = entry
    return entries


@lru_cache(maxsize=1)
def load_book_context_entries() -> dict[str, BookContextEntry]:
    raw = json.loads(BOOK_CONTEXTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("book_contexts.json must contain a list")
    entries: dict[str, BookContextEntry] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("book context entry must be an object")
        entry = _book_context_from_mapping(item)
        entries[_normalize_key(entry.book)] = entry
    return entries


@lru_cache(maxsize=1)
def load_genre_guide_entries() -> dict[str, GenreGuideEntry]:
    raw = json.loads(GENRE_GUIDES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("genre_guides.json must contain a list")
    entries: dict[str, GenreGuideEntry] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("genre guide entry must be an object")
        entry = _genre_guide_from_mapping(item)
        entries[_normalize_key(entry.genre)] = entry
        entries[_normalize_key(entry.key.removeprefix("genre:"))] = entry
    return entries


def format_lexical_entries_for_prompt(entries: list[LexicalEntry]) -> str:
    return format_local_knowledge_for_prompt(
        LocalKnowledgeBundle(lexical_entries=entries)
    )


def format_local_knowledge_for_prompt(bundle: LocalKnowledgeBundle) -> str:
    if (
        not bundle.lexical_entries
        and bundle.book_context is None
        and bundle.genre_guide is None
    ):
        return ""
    lines = [
        "# Local Curated Knowledge",
        "",
        "Use this local curated knowledge as grounding for context and method.",
        "Do not treat it as a doctrinal conclusion.",
        "Do not add unsupported historical claims beyond this local context unless clearly labeled uncertain.",
    ]
    if bundle.book_context:
        entry = bundle.book_context
        lines.extend(
            [
                "",
                f"- Book context ({entry.key})",
                f"  - Book: {entry.book}",
                f"  - Testament: {entry.testament}",
                f"  - Genre: {entry.genre}",
                f"  - Historical context hint: {entry.historical_context_hint}",
                f"  - Method guidance: {' '.join(entry.method_guidance)}",
                f"  - Cautions: {' '.join(entry.cautions)}",
            ]
        )
    if bundle.genre_guide:
        entry = bundle.genre_guide
        lines.extend(
            [
                "",
                f"- Genre guide ({entry.key})",
                f"  - Genre: {entry.genre}",
                f"  - Description: {entry.description}",
                f"  - Method guidance: {' '.join(entry.method_guidance)}",
                f"  - Cautions: {' '.join(entry.cautions)}",
            ]
        )
    for entry in bundle.lexical_entries:
        label = f"{entry.transliteration}"
        if entry.original:
            label = f"{entry.original} / {label}"
        lines.extend(
            [
                "",
                f"- {label} ({entry.language}; key: {entry.key})",
                f"  - Glosses: {', '.join(entry.glosses)}",
                f"  - Semantic range: {', '.join(entry.semantic_range)}",
                f"  - Cautions: {' '.join(entry.cautions)}",
            ]
        )
        if entry.safe_examples:
            lines.append(f"  - Safe examples: {', '.join(entry.safe_examples)}")
        if entry.notes:
            lines.append(f"  - Notes: {entry.notes}")
    return "\n".join(lines)


def _lexical_entry_from_mapping(data: dict[str, Any]) -> LexicalEntry:
    return LexicalEntry(
        key=str(data["key"]),
        language=str(data["language"]),
        original=data.get("original"),
        transliteration=str(data["transliteration"]),
        glosses=[str(value) for value in data.get("glosses", [])],
        semantic_range=[str(value) for value in data.get("semantic_range", [])],
        cautions=[str(value) for value in data.get("cautions", [])],
        safe_examples=[str(value) for value in data.get("safe_examples", [])],
        notes=data.get("notes"),
    )


def _book_context_from_mapping(data: dict[str, Any]) -> BookContextEntry:
    return BookContextEntry(
        key=str(data.get("key") or f"book:{data['book']}"),
        book=str(data["book"]),
        testament=str(data["testament"]),
        genre=str(data["genre"]),
        historical_context_hint=str(data["historical_context_hint"]),
        method_guidance=[str(value) for value in data.get("method_guidance", [])],
        cautions=[str(value) for value in data.get("cautions", [])],
    )


def _genre_guide_from_mapping(data: dict[str, Any]) -> GenreGuideEntry:
    return GenreGuideEntry(
        key=str(data.get("key") or f"genre:{data['genre']}"),
        genre=str(data["genre"]),
        description=str(data["description"]),
        method_guidance=[str(value) for value in data.get("method_guidance", [])],
        cautions=[str(value) for value in data.get("cautions", [])],
    )


def _normalize_term(term: str) -> str:
    return term.strip().lower()


def _normalize_key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
