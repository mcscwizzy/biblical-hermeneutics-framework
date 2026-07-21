"""SQLite repository for deterministic lexical lookups."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Sequence

from .lexicon_models import LexiconEntry, LexiconSense, LexiconSource, VerseWord, WordForm
from .lexicon_normalization import (
    normalize_language,
    normalize_script_form,
    normalize_strongs_number,
    normalize_transliteration,
    strongs_digits,
)


class LexiconRepository:
    """Read-mostly repository over BHF lexical SQLite tables."""

    def __init__(self, path: str | Path, *, read_only: bool = True) -> None:
        self.path = Path(path)
        self.read_only = read_only
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()

    def close(self) -> None:
        with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()
        for conn in connections:
            try:
                conn.close()
            except sqlite3.ProgrammingError:
                pass

    def sources(self) -> list[LexiconSource]:
        rows = self._conn.execute(
            """
            SELECT name, repository_url, revision, license, attribution,
                   redistribution_status, imported_at, content_hash
            FROM lexicon_sources
            ORDER BY name, revision
            """
        ).fetchall()
        return [_source_from_row(row) for row in rows]

    def database_fingerprint(self) -> str:
        rows = self._conn.execute(
            """
            SELECT name, revision, content_hash
            FROM lexicon_sources
            ORDER BY name, revision, content_hash
            """
        ).fetchall()
        return "|".join(
            f"{row['name']}@{row['revision']}:{row['content_hash']}" for row in rows
        )

    def lookup_by_strongs(self, strongs_number: str) -> list[LexiconEntry]:
        normalized = normalize_strongs_number(strongs_number)
        digits = strongs_digits(strongs_number)
        if not normalized:
            return []
        if normalized[:1] in {"H", "G"}:
            rows = self._conn.execute(
                """
                SELECT *
                FROM lexicon_entries
                WHERE normalized_strongs_number = ?
                ORDER BY language, source_name, source_entry_id
                """,
                (normalized,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT *
                FROM lexicon_entries
                WHERE strongs_digits = ?
                ORDER BY language, source_name, source_entry_id
                """,
                (digits,),
            ).fetchall()
        return [self._entry_from_row(row) for row in rows]

    def lookup_by_lemma(self, language: str, lemma: str) -> list[LexiconEntry]:
        normalized_language = normalize_language(language)
        normalized = normalize_script_form(lemma, language=normalized_language)
        rows = self._conn.execute(
            """
            SELECT *
            FROM lexicon_entries
            WHERE language = ? AND normalized_lemma = ?
            ORDER BY source_name, source_entry_id
            """,
            (normalized_language, normalized),
        ).fetchall()
        return [self._entry_from_row(row) for row in rows]

    def lookup_word_form(self, language: str, form: str) -> list[WordForm]:
        normalized_language = normalize_language(language)
        normalized = normalize_script_form(form, language=normalized_language)
        transliteration = normalize_transliteration(form)
        rows = self._conn.execute(
            """
            SELECT *
            FROM word_forms
            WHERE language = ?
              AND (
                normalized_form = ?
                OR normalized_lemma = ?
                OR normalized_transliteration = ?
              )
            ORDER BY normalized_form = ? DESC, source_name, source_word_id
            """,
            (normalized_language, normalized, normalized, transliteration, normalized),
        ).fetchall()
        return [_word_form_from_row(row) for row in rows]

    def get_verse_words(self, book: str, chapter: int, verse: int) -> list[VerseWord]:
        rows = self._conn.execute(
            """
            SELECT *
            FROM verse_words
            WHERE book = ? AND chapter = ? AND verse = ?
            ORDER BY word_position, language, source_word_id
            """,
            (str(book).strip(), int(chapter), int(verse)),
        ).fetchall()
        return [_verse_word_from_row(row) for row in rows]

    def get_word_at_position(
        self,
        book: str,
        chapter: int,
        verse: int,
        word_position: int,
    ) -> VerseWord | None:
        row = self._conn.execute(
            """
            SELECT *
            FROM verse_words
            WHERE book = ? AND chapter = ? AND verse = ? AND word_position = ?
            ORDER BY language, source_word_id
            LIMIT 1
            """,
            (str(book).strip(), int(chapter), int(verse), int(word_position)),
        ).fetchone()
        return _verse_word_from_row(row) if row is not None else None

    def find_occurrences(
        self,
        language: str,
        lemma: str,
        *,
        book: str | None = None,
        limit: int = 50,
    ) -> list[VerseWord]:
        if limit <= 0:
            return []
        normalized_language = normalize_language(language)
        normalized = normalize_script_form(lemma, language=normalized_language)
        params: list[Any] = [normalized_language, normalized]
        book_filter = ""
        if book:
            book_filter = "AND book = ?"
            params.append(str(book).strip())
        params.append(int(limit))
        rows = self._conn.execute(
            f"""
            SELECT *
            FROM verse_words
            WHERE language = ? AND normalized_lemma = ?
              {book_filter}
            ORDER BY book, chapter, verse, word_position
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [_verse_word_from_row(row) for row in rows]

    def search(self, query: str, *, limit: int = 10) -> list[LexiconEntry]:
        """Search exact identifiers and normalized forms before gloss text."""

        if limit <= 0:
            return []
        raw = str(query or "").strip()
        if not raw:
            return []
        seen: set[int] = set()
        results: list[LexiconEntry] = []
        for entry in self.lookup_by_strongs(raw):
            if entry.id not in seen:
                seen.add(entry.id or -1)
                results.append(entry)
        for language in ("hebrew", "aramaic", "greek"):
            for entry in self.lookup_by_lemma(language, raw):
                if entry.id not in seen:
                    seen.add(entry.id or -1)
                    results.append(entry)
            normalized_transliteration = normalize_transliteration(raw)
            rows = self._conn.execute(
                """
                SELECT *
                FROM lexicon_entries
                WHERE language = ? AND normalized_transliteration = ?
                ORDER BY source_name, source_entry_id
                """,
                (language, normalized_transliteration),
            ).fetchall()
            for row in rows:
                entry = self._entry_from_row(row)
                if entry.id not in seen:
                    seen.add(entry.id or -1)
                    results.append(entry)
            if len(results) >= limit:
                return results[:limit]
        if len(results) < limit:
            rows = self._conn.execute(
                """
                SELECT *
                FROM lexicon_entries
                WHERE short_gloss LIKE ? OR definition LIKE ?
                ORDER BY source_name, source_entry_id
                LIMIT ?
                """,
                (f"%{raw}%", f"%{raw}%", int(limit - len(results))),
            ).fetchall()
            for row in rows:
                entry = self._entry_from_row(row)
                if entry.id not in seen:
                    seen.add(entry.id or -1)
                    results.append(entry)
        return results[:limit]

    def _entry_from_row(self, row: sqlite3.Row) -> LexiconEntry:
        senses = self._senses_for_entry(int(row["id"]))
        return LexiconEntry(
            id=int(row["id"]),
            language=str(row["language"]),
            lemma=str(row["lemma"]),
            normalized_lemma=str(row["normalized_lemma"]),
            transliteration=_optional_text(row["transliteration"]),
            normalized_transliteration=_optional_text(row["normalized_transliteration"]),
            pronunciation=_optional_text(row["pronunciation"]),
            strongs_number=_optional_text(row["strongs_number"]),
            normalized_strongs_number=_optional_text(row["normalized_strongs_number"]),
            strongs_digits=_optional_text(row["strongs_digits"]),
            part_of_speech=_optional_text(row["part_of_speech"]),
            short_gloss=_optional_text(row["short_gloss"]),
            definition=_optional_text(row["definition"]),
            source_name=str(row["source_name"]),
            source_entry_id=str(row["source_entry_id"]),
            source_revision=str(row["source_revision"]),
            license=str(row["license"]),
            attribution=str(row["attribution"]),
            senses=tuple(senses),
        )

    def _senses_for_entry(self, entry_id: int) -> list[LexiconSense]:
        rows = self._conn.execute(
            """
            SELECT *
            FROM lexicon_senses
            WHERE lexicon_entry_id = ?
            ORDER BY sense_order, source_name, source_sense_id
            """,
            (entry_id,),
        ).fetchall()
        return [
            LexiconSense(
                gloss=str(row["gloss"]),
                definition=_optional_text(row["definition"]),
                semantic_domain=_optional_text(row["semantic_domain"]),
                usage_note=_optional_text(row["usage_note"]),
                source_name=str(row["source_name"]),
                source_sense_id=_optional_text(row["source_sense_id"]),
                sense_order=int(row["sense_order"]),
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            conn.execute("PRAGMA query_only = ON")
        else:
            conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = self._connect()
            self._local.connection = conn
            with self._connections_lock:
                self._connections.append(conn)
        return conn


def _word_form_from_row(row: sqlite3.Row) -> WordForm:
    return WordForm(
        id=int(row["id"]),
        language=str(row["language"]),
        surface_form=str(row["surface_form"]),
        normalized_form=str(row["normalized_form"]),
        lemma=str(row["lemma"]),
        normalized_lemma=str(row["normalized_lemma"]),
        transliteration=_optional_text(row["transliteration"]),
        normalized_transliteration=_optional_text(row["normalized_transliteration"]),
        strongs_number=_optional_text(row["strongs_number"]),
        normalized_strongs_number=_optional_text(row["normalized_strongs_number"]),
        strongs_digits=_optional_text(row["strongs_digits"]),
        morphology_code=_optional_text(row["morphology_code"]),
        morphology=_json_object(row["morphology_json"]),
        lexicon_entry_id=_optional_int(row["lexicon_entry_id"]),
        source_name=_optional_text(row["source_name"]),
        source_word_id=_optional_text(row["source_word_id"]),
    )


def _verse_word_from_row(row: sqlite3.Row) -> VerseWord:
    return VerseWord(
        id=int(row["id"]),
        book=str(row["book"]),
        chapter=int(row["chapter"]),
        verse=int(row["verse"]),
        word_position=int(row["word_position"]),
        source_word_id=_optional_text(row["source_word_id"]),
        language=str(row["language"]),
        surface_form=str(row["surface_form"]),
        normalized_form=str(row["normalized_form"]),
        lemma=str(row["lemma"]),
        normalized_lemma=str(row["normalized_lemma"]),
        transliteration=_optional_text(row["transliteration"]),
        normalized_transliteration=_optional_text(row["normalized_transliteration"]),
        strongs_number=_optional_text(row["strongs_number"]),
        normalized_strongs_number=_optional_text(row["normalized_strongs_number"]),
        strongs_digits=_optional_text(row["strongs_digits"]),
        morphology_code=_optional_text(row["morphology_code"]),
        morphology=_json_object(row["morphology_json"]),
        lexicon_entry_id=_optional_int(row["lexicon_entry_id"]),
        source_name=_optional_text(row["source_name"]),
    )


def _source_from_row(row: sqlite3.Row) -> LexiconSource:
    return LexiconSource(
        name=str(row["name"]),
        repository_url=str(row["repository_url"]),
        revision=str(row["revision"]),
        license=str(row["license"]),
        attribution=str(row["attribution"]),
        redistribution_status=str(row["redistribution_status"]),
        imported_at=str(row["imported_at"]),
        content_hash=str(row["content_hash"]),
    )


def _json_object(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    data = json.loads(str(value))
    return data if isinstance(data, dict) else {}


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_int(value: object) -> int | None:
    return int(value) if value is not None else None
