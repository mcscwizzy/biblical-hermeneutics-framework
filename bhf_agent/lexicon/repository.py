"""Application repository boundary for the generated lexical SQLite database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from framework.lexical.models import LexicalEntry as StandaloneLexicalEntry
from framework.lexical.models import WordOccurrence as StandaloneWordOccurrence
from framework.lexical.repository import LexicalRepository as StandaloneLexicalRepository

from .models import LexicalEntry, WordOccurrence


class LexiconRepository:
    """Adapt the standalone lexical repository to the word-study contracts.

    The normal runtime backend is ``framework.lexical`` and therefore reads
    ``lexicon.sqlite``.  The small legacy-schema branch only lets older CKL
    fixture databases continue to be read when a caller explicitly supplies
    one; it is never selected by a default path or environment variable.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = True,
        backend: StandaloneLexicalRepository | None = None,
    ) -> None:
        self.path = Path(path)
        self._backend = backend or StandaloneLexicalRepository(self.path, read_only=read_only)
        self._legacy = _has_legacy_word_tables(self.path)
        self._legacy_connection: sqlite3.Connection | None = None

    def close(self) -> None:
        self._backend.close()
        if self._legacy_connection is not None:
            self._legacy_connection.close()
            self._legacy_connection = None

    def lookup_by_strongs(self, strongs_number: str) -> list[LexicalEntry]:
        if self._legacy:
            return [
                _entry_from_legacy_row(row)
                for row in self._legacy_rows_by_strongs(strongs_number)
            ]
        languages = _languages_for_strongs(strongs_number)
        entries: list[LexicalEntry] = []
        for language in languages:
            entries.extend(
                _entry_from_standalone(entry)
                for entry in self._backend.lookup_by_strongs(language, strongs_number)
            )
        return entries

    def lookup_by_lemma(self, language: str, lemma: str) -> list[LexicalEntry]:
        if self._legacy:
            return [
                _entry_from_legacy_row(row)
                for row in self._legacy_rows_by_lemma(language, lemma)
            ]
        return [
            _entry_from_standalone(entry)
            for entry in self._backend.lookup_by_lemma(language, lemma)
        ]

    def lookup_surface_form(self, language: str, form: str) -> list[WordOccurrence]:
        if self._legacy:
            return [
                _occurrence_from_legacy_row(row, table="word_forms")
                for row in self._legacy_rows_by_surface(language, form)
            ]
        return [
            _occurrence_from_entry(entry)
            for entry in self._backend.lookup_by_transliteration(language, form)
        ]

    def lookup_verse_words(self, book: str, chapter: int, verse: int) -> list[WordOccurrence]:
        if not self._legacy:
            return [
                _occurrence_from_standalone(row)
                for row in self._backend.lookup_verse_words(book, chapter, verse)
            ]
        rows = self._legacy_connection_or_raise().execute(
            """
            SELECT * FROM verse_words
            WHERE book = ? AND chapter = ? AND verse = ?
            ORDER BY word_position, language, source_word_id
            """,
            (str(book).strip(), int(chapter), int(verse)),
        ).fetchall()
        return [_occurrence_from_legacy_row(row, table="verse_words") for row in rows]

    def count_entries(self) -> int:
        if not self._legacy:
            return self._backend.count()
        return int(
            self._legacy_connection_or_raise()
            .execute("SELECT COUNT(*) FROM lexicon_entries")
            .fetchone()[0]
        )

    def count_table(self, table: str) -> int:
        allowed_tables = {
            "lexical_entries",
            "lexicon_entries",
            "lexical_sources",
            "lexicon_sources",
            "word_forms",
            "verse_words",
        }
        if table not in allowed_tables:
            raise ValueError(f"unsupported lexical table for diagnostics: {table}")
        if not self._legacy:
            standalone_table = "lexical_entries" if table == "lexicon_entries" else table
            return self._backend.count_table(standalone_table)
        legacy_table = "lexicon_entries" if table == "lexical_entries" else table
        connection = self._legacy_connection_or_raise()
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (legacy_table,),
        ).fetchone()
        if row is None:
            return 0
        return int(
            connection.execute(f"SELECT COUNT(*) FROM {legacy_table}").fetchone()[0]
        )

    def count_verse_words(self, book: str, chapter: int, verse: int) -> int:
        if not self._legacy:
            return self._backend.count_verse_words(book, chapter, verse)
        return int(
            self._legacy_connection_or_raise()
            .execute(
                """
                SELECT COUNT(*)
                FROM verse_words
                WHERE book = ? AND chapter = ? AND verse = ?
                """,
                (str(book).strip(), int(chapter), int(verse)),
            )
            .fetchone()[0]
        )

    def count_passage_words(
        self,
        book: str,
        chapter: int,
        verse_start: int | None = None,
        verse_end: int | None = None,
    ) -> int:
        if not self._legacy:
            return self._backend.count_passage_words(book, chapter, verse_start, verse_end)
        parameters: list[Any] = [str(book).strip(), int(chapter)]
        predicate = "book = ? AND chapter = ?"
        if verse_start is not None:
            predicate += " AND verse >= ? AND verse <= ?"
            parameters.extend([int(verse_start), int(verse_end or verse_start)])
        return int(
            self._legacy_connection_or_raise()
            .execute(
                f"SELECT COUNT(*) FROM verse_words WHERE {predicate}",
                tuple(parameters),
            )
            .fetchone()[0]
        )

    def lookup_word_at_position(
        self,
        book: str,
        chapter: int,
        verse: int,
        position: int,
    ) -> WordOccurrence | None:
        if not self._legacy:
            occurrence = self._backend.lookup_word_at_position(book, chapter, verse, position)
            return _occurrence_from_standalone(occurrence) if occurrence else None
        row = self._legacy_connection_or_raise().execute(
            """
            SELECT * FROM verse_words
            WHERE book = ? AND chapter = ? AND verse = ? AND word_position = ?
            ORDER BY language, source_word_id
            LIMIT 1
            """,
            (str(book).strip(), int(chapter), int(verse), int(position)),
        ).fetchone()
        return _occurrence_from_legacy_row(row, table="verse_words") if row else None

    def find_occurrences(
        self,
        language: str,
        lemma: str,
        limit: int = 5,
    ) -> list[WordOccurrence]:
        if limit <= 0:
            return []
        if not self._legacy:
            return [
                _occurrence_from_standalone(row)
                for row in self._backend.find_occurrences(language, lemma, limit=limit)
            ]
        rows = self._legacy_connection_or_raise().execute(
            """
            SELECT * FROM verse_words
            WHERE language = ? AND normalized_lemma = ?
            ORDER BY book, chapter, verse, word_position
            LIMIT ?
            """,
            (str(language).strip().lower(), _normalize_form(lemma), int(limit)),
        ).fetchall()
        if not rows:
            return []
        return [_occurrence_from_legacy_row(row, table="verse_words") for row in rows]

    def sources(self) -> list[dict[str, Any]]:
        if not self._legacy:
            return list(self._backend.sources())
        rows = self._legacy_connection_or_raise().execute(
            """
            SELECT name, repository_url, revision, license, attribution,
                   redistribution_status, imported_at, content_hash
            FROM lexicon_sources
            ORDER BY name, revision
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _legacy_connection_or_raise(self) -> sqlite3.Connection:
        if self._legacy_connection is None:
            self._legacy_connection = sqlite3.connect(
                f"file:{self.path}?mode=ro", uri=True
            )
            self._legacy_connection.row_factory = sqlite3.Row
            self._legacy_connection.execute("PRAGMA query_only = ON")
        return self._legacy_connection

    def _legacy_rows_by_strongs(self, strongs_number: str) -> list[sqlite3.Row]:
        normalized = _normalize_strongs(strongs_number)
        return self._legacy_connection_or_raise().execute(
            """
            SELECT e.* FROM lexicon_entries AS e
            WHERE e.normalized_strongs_number = ? OR e.strongs_number = ?
            ORDER BY e.source_name, e.source_entry_id
            """,
            (normalized, normalized),
        ).fetchall()

    def _legacy_rows_by_lemma(self, language: str, lemma: str) -> list[sqlite3.Row]:
        return self._legacy_connection_or_raise().execute(
            """
            SELECT e.* FROM lexicon_entries AS e
            WHERE e.language = ? AND e.normalized_lemma = ?
            ORDER BY e.source_name, e.source_entry_id
            """,
            (str(language).strip().lower(), _normalize_form(lemma)),
        ).fetchall()

    def _legacy_rows_by_surface(self, language: str, form: str) -> list[sqlite3.Row]:
        return self._legacy_connection_or_raise().execute(
            """
            SELECT * FROM word_forms
            WHERE language = ? AND (
                normalized_form = ? OR normalized_lemma = ?
                OR normalized_transliteration = ?
            )
            ORDER BY source_name, source_word_id
            """,
            (
                str(language).strip().lower(),
                _normalize_form(form),
                _normalize_form(form),
                _normalize_transliteration(form),
            ),
        ).fetchall()


def _has_legacy_word_tables(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        finally:
            connection.close()
        return {"lexicon_entries", "verse_words", "word_forms"}.issubset(tables)
    except sqlite3.Error:
        return False


def _entry_from_standalone(entry: StandaloneLexicalEntry) -> LexicalEntry:
    glosses = _split_glosses(entry.short_definition or entry.definition)
    return LexicalEntry(
        language=entry.language,
        lemma=entry.lemma,
        transliteration=entry.transliteration,
        strongs_number=entry.strongs_number,
        glosses=glosses,
        definition=entry.definition,
        part_of_speech=entry.part_of_speech,
        source=entry.source,
        source_entry_id=str(entry.id),
        license=entry.license,
        attribution=entry.attribution,
    )


def _entry_from_legacy_row(row: sqlite3.Row) -> LexicalEntry:
    senses = _legacy_senses(row)
    glosses = _split_glosses(row["short_gloss"])
    glosses.extend(str(sense["gloss"]) for sense in senses if sense["gloss"])
    return LexicalEntry(
        language=str(row["language"]),
        lemma=str(row["lemma"]),
        transliteration=row["transliteration"],
        strongs_number=row["strongs_number"],
        glosses=_unique(glosses),
        definition=row["definition"],
        part_of_speech=row["part_of_speech"],
        source=str(row["source_name"]),
        source_entry_id=row["source_entry_id"],
        license=row["license"],
        attribution=row["attribution"],
        senses=senses,
    )


def _legacy_senses(row: sqlite3.Row) -> list[dict[str, Any]]:
    # The caller's connection is not available here, so legacy entries use
    # their compact gloss. Detailed senses are not required for resolution.
    return []


def _occurrence_from_entry(entry: StandaloneLexicalEntry) -> WordOccurrence:
    return WordOccurrence(
        book="",
        chapter=0,
        verse=0,
        position=0,
        language=entry.language,
        surface_form=entry.lemma,
        lemma=entry.lemma,
        strongs_number=entry.strongs_number,
        transliteration=entry.transliteration,
        source=entry.source,
        source_word_id=str(entry.id),
    )


def _occurrence_from_standalone(entry: StandaloneWordOccurrence) -> WordOccurrence:
    return WordOccurrence(
        book=entry.book,
        chapter=entry.chapter,
        verse=entry.verse,
        position=entry.position,
        language=entry.language,
        surface_form=entry.surface_form,
        lemma=entry.lemma,
        strongs_number=entry.strongs_number,
        morphology=dict(entry.morphology),
        transliteration=entry.transliteration,
        morphology_code=entry.morphology_code,
        source=entry.source,
        source_word_id=entry.source_word_id,
    )


def _occurrence_from_legacy_row(row: sqlite3.Row, *, table: str) -> WordOccurrence:
    return WordOccurrence(
        book=str(row["book"]) if table == "verse_words" else "",
        chapter=int(row["chapter"]) if table == "verse_words" else 0,
        verse=int(row["verse"]) if table == "verse_words" else 0,
        position=int(row["word_position"]) if table == "verse_words" else 0,
        language=str(row["language"]),
        surface_form=str(row["surface_form"]),
        lemma=str(row["lemma"]),
        strongs_number=row["strongs_number"],
        morphology=_json_object(row["morphology_json"]),
        transliteration=row["transliteration"],
        morphology_code=row["morphology_code"],
        source=row["source_name"],
        source_word_id=row["source_word_id"],
    )


def _languages_for_strongs(value: str) -> tuple[str, ...]:
    normalized = _normalize_strongs(value)
    if normalized.startswith("H"):
        return ("hebrew",)
    if normalized.startswith("G"):
        return ("greek",)
    return ("hebrew", "greek")


def _normalize_strongs(value: str) -> str:
    import re

    raw = str(value or "").strip().upper()
    match = re.fullmatch(r"([HG])?\s*0*([0-9]+)[A-Z]?", raw)
    if not match:
        return raw
    prefix, digits = match.groups()
    return f"{prefix or ''}{int(digits)}"


def _normalize_form(value: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.replace("ς", "σ").split())


def _normalize_transliteration(value: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    for mark in ("ʾ", "ʿ", "ʼ", "‘", "’"):
        text = text.replace(mark, "")
    return "".join(char for char in text if char.isalnum() or char.isspace()).strip()


def _split_glosses(value: object) -> list[str]:
    return _unique(str(value or "").replace(",", ";").split(";"))


def _unique(values: Any) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            output.append(text)
    return output


def _json_object(value: object) -> dict[str, Any]:
    if not value:
        return {}
    try:
        result = json.loads(str(value))
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}
