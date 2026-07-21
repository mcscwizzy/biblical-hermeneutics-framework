"""Application repository boundary for lexical SQLite access."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from framework.canonical_library.lexicon_models import LexiconEntry as CKLLexiconEntry
from framework.canonical_library.lexicon_models import VerseWord as CKLVerseWord
from framework.canonical_library.lexicon_models import WordForm as CKLWordForm
from framework.canonical_library.lexicon_repository import (
    LexiconRepository as CKLLexiconRepository,
)

from .models import LexicalEntry, WordOccurrence


class LexiconRepository:
    """Thin adapter over the CKL SQLite lexical repository.

    SQL remains in ``framework.canonical_library``; this layer provides the
    names and typed objects used by study actions and web routes.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = True,
        backend: CKLLexiconRepository | None = None,
    ) -> None:
        self.path = Path(path)
        self._backend = backend or CKLLexiconRepository(self.path, read_only=read_only)

    def close(self) -> None:
        self._backend.close()

    def lookup_by_strongs(self, strongs_number: str) -> list[LexicalEntry]:
        return [
            _entry_from_ckl(entry)
            for entry in self._backend.lookup_by_strongs(strongs_number)
        ]

    def lookup_by_lemma(self, language: str, lemma: str) -> list[LexicalEntry]:
        return [
            _entry_from_ckl(entry)
            for entry in self._backend.lookup_by_lemma(language, lemma)
        ]

    def lookup_surface_form(self, language: str, form: str) -> list[WordOccurrence]:
        return [
            _occurrence_from_word_form(form_row)
            for form_row in self._backend.lookup_word_form(language, form)
        ]

    def lookup_verse_words(self, book: str, chapter: int, verse: int) -> list[WordOccurrence]:
        return [
            _occurrence_from_verse_word(word)
            for word in self._backend.get_verse_words(book, chapter, verse)
        ]

    def lookup_word_at_position(
        self,
        book: str,
        chapter: int,
        verse: int,
        position: int,
    ) -> WordOccurrence | None:
        word = self._backend.get_word_at_position(book, chapter, verse, position)
        return _occurrence_from_verse_word(word) if word is not None else None

    def find_occurrences(
        self,
        language: str,
        lemma: str,
        limit: int = 5,
    ) -> list[WordOccurrence]:
        return [
            _occurrence_from_verse_word(word)
            for word in self._backend.find_occurrences(language, lemma, limit=limit)
        ]

    def sources(self) -> list[dict[str, Any]]:
        return [source.__dict__.copy() for source in self._backend.sources()]


def _entry_from_ckl(entry: CKLLexiconEntry) -> LexicalEntry:
    glosses = _entry_glosses(entry)
    senses = [
        {
            "gloss": sense.gloss,
            "definition": sense.definition,
            "semantic_domain": sense.semantic_domain,
            "usage_note": sense.usage_note,
            "source": sense.source_name,
            "source_sense_id": sense.source_sense_id,
            "sense_order": sense.sense_order,
        }
        for sense in entry.senses
    ]
    return LexicalEntry(
        language=entry.language,
        lemma=entry.lemma,
        transliteration=entry.transliteration,
        strongs_number=entry.strongs_number,
        glosses=glosses,
        definition=entry.definition,
        part_of_speech=entry.part_of_speech,
        source=entry.source_name,
        source_entry_id=entry.source_entry_id,
        license=entry.license,
        attribution=entry.attribution,
        senses=senses,
    )


def _occurrence_from_verse_word(word: CKLVerseWord) -> WordOccurrence:
    return WordOccurrence(
        book=word.book,
        chapter=word.chapter,
        verse=word.verse,
        position=word.word_position,
        language=word.language,
        surface_form=word.surface_form,
        lemma=word.lemma,
        strongs_number=word.strongs_number,
        morphology=word.morphology,
        transliteration=word.transliteration,
        morphology_code=word.morphology_code,
        source=word.source_name,
        source_word_id=word.source_word_id,
    )


def _occurrence_from_word_form(form: CKLWordForm) -> WordOccurrence:
    return WordOccurrence(
        book="",
        chapter=0,
        verse=0,
        position=0,
        language=form.language,
        surface_form=form.surface_form,
        lemma=form.lemma,
        strongs_number=form.strongs_number,
        morphology=form.morphology,
        transliteration=form.transliteration,
        morphology_code=form.morphology_code,
        source=form.source_name,
        source_word_id=form.source_word_id,
    )


def _entry_glosses(entry: CKLLexiconEntry) -> list[str]:
    values: list[str] = []
    for gloss in str(entry.short_gloss or "").replace(",", ";").split(";"):
        text = gloss.strip()
        if text:
            values.append(text)
    for sense in entry.senses:
        if sense.gloss:
            values.append(sense.gloss)
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output
