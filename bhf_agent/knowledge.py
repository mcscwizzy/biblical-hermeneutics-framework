"""Local curated knowledge helpers for BHF word-study prompts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .models import QuestionContext


DATA_DIR = Path(__file__).resolve().parent / "data"
LEXICAL_TERMS_PATH = DATA_DIR / "lexical_terms.json"


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
    book: str
    testament: str
    genre: str
    historical_context_hint: str
    cautions: list[str]


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


def format_lexical_entries_for_prompt(entries: list[LexicalEntry]) -> str:
    if not entries:
        return ""
    lines = [
        "# Local Curated Knowledge",
        "",
        "Use the following local curated notes as preferred grounding.",
        "Do not contradict these notes unless explaining uncertainty.",
        "Do not add unsupported lexical claims beyond these notes.",
    ]
    for entry in entries:
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


def _normalize_term(term: str) -> str:
    return term.strip().lower()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
