"""Deterministic word-study orchestration over standalone lexical data."""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from framework.lexical.service import DEFAULT_LEXICAL_DATABASE_PATH

from .models import WORD_STUDY_GUARDRAILS, LexicalEntry, WordOccurrence, WordStudyResult
from .normalization import (
    normalize_script_form,
    normalize_strongs_number,
    normalize_transliteration,
)
from .repository import LexiconRepository

STRONGS_RE = re.compile(r"\b[HG]\s*0*\d{1,5}[A-Za-z]?\b", re.IGNORECASE)


class WordStudyService:
    """Build deterministic word-study results from the generated lexical database."""

    def __init__(
        self,
        repository: LexiconRepository | None = None,
        *,
        database_path: str | Path | None = None,
    ) -> None:
        self._repository = repository
        self.database_path = Path(
            database_path
            or os.environ.get("BHF_LEXICAL_DATABASE_PATH")
            or DEFAULT_LEXICAL_DATABASE_PATH
        )

    @property
    def repository(self) -> LexiconRepository:
        if self._repository is None:
            self._repository = LexiconRepository(self.database_path)
        return self._repository

    def build_word_study(
        self,
        passage: Mapping[str, Any],
        *,
        query: str | None = None,
    ) -> WordStudyResult:
        reference = str(passage.get("reference") or "").strip() or _reference_from_passage(
            passage
        )
        book = str(passage.get("book") or "").strip()
        chapter = _int_or_none(passage.get("chapter"))
        verse = _int_or_none(passage.get("start_verse") or passage.get("verse"))
        if not book or chapter is None or verse is None:
            return _unavailable(reference, "A book, chapter, and verse are required for word study.")

        try:
            occurrence = self._resolve_occurrence(book, chapter, verse, passage, query=query)
            if isinstance(occurrence, list):
                return self._ambiguous_result(reference, occurrence)
            if occurrence is None:
                return _unavailable(
                    reference,
                    "No deterministic original-language token was found for this selection.",
                )
            return self._result_for_occurrence(reference, occurrence)
        except (FileNotFoundError, sqlite3.Error, ValueError) as exc:
            return _unavailable(reference, f"Lexical SQLite data is unavailable: {exc}")

    def _resolve_occurrence(
        self,
        book: str,
        chapter: int,
        verse: int,
        passage: Mapping[str, Any],
        *,
        query: str | None,
    ) -> WordOccurrence | list[WordOccurrence] | None:
        position = _int_or_none(
            _first(
                passage,
                "word_position",
                "position",
                "token_position",
                "selected_word_position",
            )
        )
        if position is not None:
            return self.repository.lookup_word_at_position(book, chapter, verse, position)

        strongs_number = _strongs_from_context(passage, query)
        if strongs_number:
            entries = self.repository.lookup_by_strongs(strongs_number)
            occurrence = self._occurrence_for_entries(book, chapter, verse, entries)
            if occurrence is not None:
                return occurrence

        language = str(_first(passage, "language", "source_language") or "").strip().lower()
        lemma = str(_first(passage, "lemma", "selected_lemma") or "").strip()
        if language and lemma:
            entries = self.repository.lookup_by_lemma(language, lemma)
            occurrence = self._occurrence_for_entries(book, chapter, verse, entries)
            if occurrence is not None:
                return occurrence

        verse_words = self.repository.lookup_verse_words(book, chapter, verse)
        if not verse_words:
            return None

        selected = str(
            _first(passage, "surface_form", "selected_surface_form", "selected_text")
            or query
            or ""
        ).strip()
        if selected:
            exact = self._exact_token_matches(verse_words, selected)
            if len(exact) == 1:
                return exact[0]
            if len(exact) > 1:
                return exact

        if len(verse_words) == 1:
            return verse_words[0]
        return verse_words[:8]

    def _occurrence_for_entries(
        self,
        book: str,
        chapter: int,
        verse: int,
        entries: list[LexicalEntry],
    ) -> WordOccurrence | None:
        if not entries:
            return None
        verse_words = self.repository.lookup_verse_words(book, chapter, verse)
        strongs = {entry.strongs_number for entry in entries if entry.strongs_number}
        lemmas = {(entry.language, _normalize_lemma(entry.language, entry.lemma)) for entry in entries}
        for word in verse_words:
            if word.strongs_number and word.strongs_number in strongs:
                return word
            if (word.language, _normalize_lemma(word.language, word.lemma)) in lemmas:
                return word
        entry = entries[0]
        return WordOccurrence(
            book=book,
            chapter=chapter,
            verse=verse,
            position=0,
            language=entry.language,
            surface_form=entry.lemma,
            lemma=entry.lemma,
            strongs_number=entry.strongs_number,
            morphology={},
            transliteration=entry.transliteration,
            source=entry.source,
        )

    def _exact_token_matches(self, verse_words: list[WordOccurrence], selected: str) -> list[WordOccurrence]:
        selected_transliteration = normalize_transliteration(selected)
        matches: list[WordOccurrence] = []
        for word in verse_words:
            normalized_selected = _normalize_lemma(word.language, selected)
            candidates = {
                _normalize_lemma(word.language, word.surface_form),
                _normalize_lemma(word.language, word.lemma),
            }
            if word.transliteration:
                candidates.add(normalize_transliteration(word.transliteration))
            if selected_transliteration and selected_transliteration in candidates:
                matches.append(word)
                continue
            if normalized_selected and normalized_selected in candidates:
                matches.append(word)
        return matches

    def _result_for_occurrence(self, reference: str, occurrence: WordOccurrence) -> WordStudyResult:
        entries = self._entries_for_occurrence(occurrence)
        if not entries:
            identifier = occurrence.strongs_number or occurrence.lemma or occurrence.surface_form
            return _unavailable(
                reference,
                "Original-language token was found, but no lexicon entry resolved for "
                f"{identifier} at {occurrence.reference}.",
            )
        lexical_range = _unique(
            gloss
            for entry in entries
            for gloss in entry.glosses
        )
        representative = self.repository.find_occurrences(
            occurrence.language,
            occurrence.lemma,
            limit=5,
        )
        repository_sources = self.repository.sources()
        sources = _sources_for_entries(entries, repository_sources)
        sources = _with_occurrence_source(sources, occurrence, repository_sources)
        prompt_context = _prompt_context(
            reference=reference,
            occurrence=occurrence,
            lexical_range=lexical_range,
            sources=sources,
        )
        contextual_information = [
            f"Resolved by deterministic lexical token at {occurrence.reference}"
            + (f", position {occurrence.position}." if occurrence.position else "."),
            "Meaning in this passage should be explained from the retrieved lexical and morphological data plus the immediate context.",
        ]
        return WordStudyResult(
            reference=reference,
            status="complete",
            language=occurrence.language,
            surface_form=occurrence.surface_form,
            lemma=occurrence.lemma,
            strongs_number=occurrence.strongs_number or _first_entry_attr(entries, "strongs_number"),
            transliteration=occurrence.transliteration or _first_entry_attr(entries, "transliteration"),
            morphology=occurrence.morphology,
            morphology_code=occurrence.morphology_code,
            lexical_range=lexical_range,
            lexical_entries=entries,
            representative_occurrences=representative,
            sources=sources,
            contextual_information=contextual_information,
            prompt_context=prompt_context,
            confidence=0.94,
        )

    def _entries_for_occurrence(self, occurrence: WordOccurrence) -> list[LexicalEntry]:
        entries: list[LexicalEntry] = []
        if occurrence.strongs_number:
            entries.extend(self.repository.lookup_by_strongs(occurrence.strongs_number))
        entries.extend(self.repository.lookup_by_lemma(occurrence.language, occurrence.lemma))
        return _dedupe_entries(entries)

    def _ambiguous_result(self, reference: str, occurrences: list[WordOccurrence]) -> WordStudyResult:
        enriched = [self._with_gloss(occurrence) for occurrence in occurrences]
        return WordStudyResult(
            reference=reference,
            status="ambiguous",
            ambiguities=enriched,
            message="Multiple possible original-language words found. Please select a specific original-language token.",
            confidence=0.35,
        )

    def _with_gloss(self, occurrence: WordOccurrence) -> WordOccurrence:
        entries = self._entries_for_occurrence(occurrence)
        gloss = _first_gloss(entries)
        strongs = occurrence.strongs_number or _first_entry_attr(entries, "strongs_number")
        transliteration = occurrence.transliteration or _first_entry_attr(entries, "transliteration")
        if not gloss and not strongs and not transliteration:
            return occurrence
        data = occurrence.to_dict()
        data["gloss"] = gloss
        data["strongs_number"] = strongs
        data["transliteration"] = transliteration
        return WordOccurrence(**{key: value for key, value in data.items() if key != "reference"})


def _unavailable(reference: str, message: str) -> WordStudyResult:
    return WordStudyResult(reference=reference, status="unavailable", message=message, confidence=0.0)


def _reference_from_passage(passage: Mapping[str, Any]) -> str:
    book = str(passage.get("book") or "").strip()
    chapter = passage.get("chapter")
    verse = passage.get("start_verse") or passage.get("verse")
    if book and chapter and verse:
        return f"{book} {chapter}:{verse}"
    if book and chapter:
        return f"{book} {chapter}"
    return "selected passage"


def _strongs_from_context(passage: Mapping[str, Any], query: str | None) -> str | None:
    explicit = _first(passage, "strongs_number", "strongs", "selected_strongs")
    if explicit:
        return normalize_strongs_number(str(explicit))
    haystack = " ".join(str(value or "") for value in (query, passage.get("selected_text")))
    match = STRONGS_RE.search(haystack)
    return normalize_strongs_number(match.group(0)) if match else None


def _prompt_context(
    *,
    reference: str,
    occurrence: WordOccurrence,
    lexical_range: list[str],
    sources: list[dict[str, Any]],
    max_words: int = 350,
) -> str:
    lines = [
        "LEXICAL CONTEXT",
        f"Reference: {reference}",
        f"Word: {occurrence.surface_form}",
        f"Lemma: {occurrence.lemma}",
    ]
    if occurrence.transliteration:
        lines.append(f"Transliteration: {occurrence.transliteration}")
    if occurrence.strongs_number:
        lines.append(f"Strong's: {occurrence.strongs_number}")
    morphology = _plain_morphology(occurrence.morphology)
    if morphology:
        lines.append(f"Morphology: {morphology}")
    if lexical_range:
        lines.append("Lexical Range:")
        lines.extend(lexical_range[:6])
    lines.append("Guardrails:")
    lines.extend(WORD_STUDY_GUARDRAILS[:5])
    if sources:
        lines.append("Sources:")
        lines.extend(str(source.get("name") or source.get("source") or "") for source in sources[:5])
    words = "\n".join(line for line in lines if line).split()
    if len(words) <= max_words:
        return "\n".join(line for line in lines if line)
    return " ".join(words[:max_words]).rstrip() + " ..."


def _plain_morphology(morphology: Mapping[str, Any]) -> str:
    ordered = (
        "part_of_speech",
        "stem",
        "conjugation",
        "tense",
        "voice",
        "mood",
        "person",
        "gender",
        "number",
        "case",
        "state",
    )
    return ", ".join(str(morphology[key]) for key in ordered if morphology.get(key))


def _sources_for_entries(
    entries: list[LexicalEntry],
    repository_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_by_name = {str(source.get("name")): source for source in repository_sources}
    output: list[dict[str, Any]] = []
    for entry in entries:
        source = dict(source_by_name.get(entry.source, {}))
        source.setdefault("name", entry.source)
        if entry.license:
            source.setdefault("license", entry.license)
        if entry.attribution:
            source.setdefault("attribution", entry.attribution)
        output.append(source)
    return _dedupe_source_dicts(output)


def _with_occurrence_source(
    sources: list[dict[str, Any]],
    occurrence: WordOccurrence,
    repository_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not occurrence.source:
        return sources
    source_by_name = {str(source.get("name")): source for source in repository_sources}
    source = dict(source_by_name.get(occurrence.source, {}))
    source.setdefault("name", occurrence.source)
    return _dedupe_source_dicts([*sources, source])


def _dedupe_entries(entries: list[LexicalEntry]) -> list[LexicalEntry]:
    output: list[LexicalEntry] = []
    seen: set[tuple[str, str, str | None]] = set()
    for entry in entries:
        key = (entry.source, entry.lemma, entry.strongs_number)
        if key in seen:
            continue
        seen.add(key)
        output.append(entry)
    return output


def _dedupe_source_dicts(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        name = str(source.get("name") or source.get("source") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        output.append(source)
    return output


def _normalize_lemma(language: str, value: str) -> str:
    return normalize_script_form(value, language=language)


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _first_entry_attr(entries: list[LexicalEntry], attr: str) -> str | None:
    for entry in entries:
        value = getattr(entry, attr, None)
        if value:
            return str(value)
    return None


def _first_gloss(entries: list[LexicalEntry]) -> str | None:
    for entry in entries:
        for gloss in entry.glosses:
            text = str(gloss or "").strip()
            if text:
                return text
        text = str(entry.definition or "").strip()
        if text:
            return text
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _unique(values: Any) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output
