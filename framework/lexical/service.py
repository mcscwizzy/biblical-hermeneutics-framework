"""Small lookup and prompt-formatting API for the lexical engine."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterable

from .models import LexicalEntry
from .repository import LexicalRepository


DEFAULT_LEXICAL_DATABASE_PATH = str(Path(__file__).resolve().parent / "database" / "lexicon.sqlite")
_STRONGS_RE = re.compile(r"\b(?P<value>[HG]\s*0*\d{1,5}[A-Za-z]?)\b", re.IGNORECASE)


class LexicalLookupService:
    """Application-facing lexical retrieval with bounded prompt output."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        repository: LexicalRepository | None = None,
    ) -> None:
        self.database_path = Path(
            database_path
            or os.environ.get("BHF_LEXICAL_DATABASE_PATH")
            or DEFAULT_LEXICAL_DATABASE_PATH
        )
        self._repository = repository

    @property
    def repository(self) -> LexicalRepository:
        if self._repository is None:
            self._repository = LexicalRepository(self.database_path)
        return self._repository

    def close(self) -> None:
        if self._repository is not None:
            self._repository.close()

    def lookup(
        self,
        *,
        language: str,
        strongs: str | None = None,
        lemma: str | None = None,
        transliteration: str | None = None,
    ) -> list[LexicalEntry]:
        language = str(language or "").strip().lower()
        if language not in {"hebrew", "greek", "aramaic"}:
            return []
        if strongs:
            results = self.repository.lookup_by_strongs(language, strongs)
            if results:
                return results
        if lemma:
            results = self.repository.lookup_by_lemma(language, lemma)
            if results:
                return results
        if transliteration:
            return self.repository.lookup_by_transliteration(language, transliteration)
        return []

    def lookup_question(
        self,
        *,
        language: str | None,
        terms: Iterable[str] = (),
        question: str = "",
        max_results: int = 3,
        max_prompt_tokens: int = 350,
    ) -> tuple[list[LexicalEntry], str]:
        """Resolve only explicit original-language targets in a question."""

        normalized_language = str(language or "").strip().lower()
        if normalized_language not in {"hebrew", "greek"}:
            normalized_language = ""
        candidates: list[LexicalEntry] = []
        seen: set[tuple[str, str, str]] = set()
        strongs_numbers = [match.group("value") for match in _STRONGS_RE.finditer(question or "")]
        for strongs_number in strongs_numbers:
            current_language = normalized_language or (
                "hebrew" if strongs_number.upper().startswith("H") else "greek"
            )
            for entry in self.lookup(language=current_language, strongs=strongs_number):
                _append_unique(candidates, seen, entry)
        if normalized_language:
            for term in terms:
                for entry in self.lookup(
                    language=normalized_language,
                    lemma=term,
                    transliteration=term,
                ):
                    _append_unique(candidates, seen, entry)
        candidates = candidates[: max(0, int(max_results))]
        return candidates, format_lexical_context(candidates, max_prompt_tokens=max_prompt_tokens)


def lookup_word(
    *,
    language: str,
    strongs: str | None = None,
    lemma: str | None = None,
    transliteration: str | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Return one compact lexical record for an exact lookup."""

    service = LexicalLookupService(database_path)
    try:
        entries = service.lookup(
            language=language,
            strongs=strongs,
            lemma=lemma,
            transliteration=transliteration,
        )
        if not entries:
            return None
        return entries[0].to_dict()
    finally:
        service.close()


def format_lexical_context(entries: Iterable[LexicalEntry], *, max_prompt_tokens: int = 350) -> str:
    selected = list(entries)
    if not selected:
        return ""
    lines = [
        "# VERIFIED LEXICAL CONTEXT",
        "Use the supplied lexical records as source data. Explain contextually; do not invent or expand lexical definitions from memory.",
    ]
    for entry in selected:
        lines.extend(["", f"Word: {entry.lemma}", f"Language: {entry.language}"])
        if entry.transliteration:
            lines.append(f"Transliteration: {entry.transliteration}")
        if entry.strongs_number:
            lines.append(f"Strong's: {entry.strongs_number}")
        lines.append(f"Source: {entry.source}; License: {entry.license}")
        lines.append(f"Definition: {entry.short_definition or entry.definition}")
        if entry.morphology:
            lines.append(f"Morphology: {entry.morphology}")
        if entry.usage_notes:
            lines.append(f"Usage notes: {entry.usage_notes}")
    words = "\n".join(lines).split()
    if len(words) > max(1, int(max_prompt_tokens)):
        return " ".join(words[: int(max_prompt_tokens)]).rstrip() + " ..."
    return "\n".join(lines)


def _append_unique(
    entries: list[LexicalEntry],
    seen: set[tuple[str, str, str]],
    entry: LexicalEntry,
) -> None:
    key = (entry.language, entry.strongs_number or "", entry.lemma)
    if key not in seen:
        seen.add(key)
        entries.append(entry)
