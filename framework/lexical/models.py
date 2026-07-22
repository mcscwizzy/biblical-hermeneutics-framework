"""Data contracts for the standalone lexical engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LexicalEntry:
    id: int
    language: str
    strongs_number: str | None
    lemma: str
    transliteration: str | None
    pronunciation: str | None
    definition: str
    short_definition: str | None
    root: str | None
    part_of_speech: str | None
    morphology: str | None
    semantic_domain: str | None
    usage_notes: str | None
    source: str
    license: str
    created_at: str
    attribution: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "language": self.language,
            "strongs_number": self.strongs_number,
            "lemma": self.lemma,
            "transliteration": self.transliteration,
            "pronunciation": self.pronunciation,
            "definition": self.definition,
            "short_definition": self.short_definition,
            "root": self.root,
            "part_of_speech": self.part_of_speech,
            "morphology": self.morphology,
            "semantic_domain": self.semantic_domain,
            "usage_notes": self.usage_notes,
            "source": self.source,
            "license": self.license,
            "created_at": self.created_at,
            "attribution": self.attribution,
        }


@dataclass(frozen=True)
class ImportStats:
    language: str
    entries_imported: int
    source: str


@dataclass(frozen=True)
class WordOccurrence:
    book: str
    chapter: int
    verse: int
    position: int
    language: str
    surface_form: str
    lemma: str
    strongs_number: str | None
    morphology: dict[str, Any]
    transliteration: str | None
    morphology_code: str | None
    source: str | None
    source_word_id: str | None

    @property
    def reference(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "book": self.book,
            "chapter": self.chapter,
            "verse": self.verse,
            "position": self.position,
            "language": self.language,
            "surface_form": self.surface_form,
            "lemma": self.lemma,
            "strongs_number": self.strongs_number,
            "morphology": self.morphology,
            "transliteration": self.transliteration,
            "morphology_code": self.morphology_code,
            "source": self.source,
            "source_word_id": self.source_word_id,
            "reference": self.reference,
        }
