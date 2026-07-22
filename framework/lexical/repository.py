"""Read-only SQLite repository for lexical runtime lookups."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from .models import LexicalEntry, WordOccurrence


class LexicalRepository:
    """Query the generated lexical database without loading source XML."""

    def __init__(self, database_path: str | Path, *, read_only: bool = True) -> None:
        self.path = Path(database_path)
        self.read_only = read_only
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._table_cache: dict[str, bool] = {}

    def close(self) -> None:
        with self._lock:
            connections = list(self._connections)
            self._connections.clear()
        for connection in connections:
            connection.close()

    def lookup_by_strongs(self, language: str, strongs: str) -> list[LexicalEntry]:
        normalized = _normalize_strongs(strongs, language)
        if not normalized:
            return []
        rows = self._connection.execute(
            """
            SELECT e.*, s.attribution
            FROM lexical_entries AS e
            LEFT JOIN lexical_sources AS s ON s.source = e.source
            WHERE e.language = ? AND e.strongs_number = ?
            ORDER BY e.source, e.id
            """,
            (language.strip().lower(), normalized),
        ).fetchall()
        return [_entry_from_row(row) for row in rows]

    def lookup_by_lemma(self, language: str, lemma: str) -> list[LexicalEntry]:
        normalized = _normalize_form(lemma)
        if not normalized:
            return []
        rows = self._connection.execute(
            """
            SELECT e.*, s.attribution
            FROM lexical_entries AS e
            LEFT JOIN lexical_sources AS s ON s.source = e.source
            WHERE e.language = ? AND e.normalized_lemma = ?
            ORDER BY e.source, e.id
            """,
            (language.strip().lower(), normalized),
        ).fetchall()
        return [_entry_from_row(row) for row in rows]

    def lookup_by_transliteration(self, language: str, transliteration: str) -> list[LexicalEntry]:
        normalized = _normalize_transliteration(transliteration)
        if not normalized:
            return []
        rows = self._connection.execute(
            """
            SELECT e.*, s.attribution
            FROM lexical_entries AS e
            LEFT JOIN lexical_sources AS s ON s.source = e.source
            WHERE e.language = ? AND e.normalized_transliteration = ?
            ORDER BY e.source, e.id
            """,
            (language.strip().lower(), normalized),
        ).fetchall()
        return [_entry_from_row(row) for row in rows]

    def count(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM lexical_entries").fetchone()[0])

    def counts_by_language(self) -> dict[str, int]:
        rows = self._connection.execute(
            """
            SELECT language, COUNT(*) AS entry_count
            FROM lexical_entries
            GROUP BY language
            ORDER BY language
            """
        ).fetchall()
        return {str(row["language"]): int(row["entry_count"]) for row in rows}

    def sources(self) -> list[dict[str, str]]:
        rows = self._connection.execute(
            """
            SELECT source, license, attribution, source_url, revision,
                   imported_at, source_file
            FROM lexical_sources
            ORDER BY source, revision
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def lookup_verse_words(self, book: str, chapter: int, verse: int) -> list[WordOccurrence]:
        if not self._has_table("verse_words"):
            return []
        rows = self._connection.execute(
            """
            SELECT *
            FROM verse_words
            WHERE book = ? AND chapter = ? AND verse = ?
            ORDER BY word_position, language, source_word_id
            """,
            (str(book).strip(), int(chapter), int(verse)),
        ).fetchall()
        return [_occurrence_from_row(row) for row in rows]

    def lookup_word_at_position(
        self,
        book: str,
        chapter: int,
        verse: int,
        position: int,
    ) -> WordOccurrence | None:
        if not self._has_table("verse_words"):
            return None
        row = self._connection.execute(
            """
            SELECT *
            FROM verse_words
            WHERE book = ? AND chapter = ? AND verse = ? AND word_position = ?
            ORDER BY language, source_word_id
            LIMIT 1
            """,
            (str(book).strip(), int(chapter), int(verse), int(position)),
        ).fetchone()
        return _occurrence_from_row(row) if row else None

    def find_occurrences(
        self,
        language: str,
        lemma: str,
        limit: int = 5,
    ) -> list[WordOccurrence]:
        if limit <= 0 or not self._has_table("verse_words"):
            return []
        rows = self._connection.execute(
            """
            SELECT *
            FROM verse_words
            WHERE language = ? AND normalized_lemma = ?
            ORDER BY book, chapter, verse, word_position
            LIMIT ?
            """,
            (str(language).strip().lower(), _normalize_form(lemma), int(limit)),
        ).fetchall()
        return [_occurrence_from_row(row) for row in rows]

    @property
    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            if self.read_only:
                connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
                connection.execute("PRAGMA query_only = ON")
            else:
                connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            self._local.connection = connection
            with self._lock:
                self._connections.append(connection)
        return connection

    def _has_table(self, name: str) -> bool:
        if name not in self._table_cache:
            row = self._connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (name,),
            ).fetchone()
            self._table_cache[name] = row is not None
        return self._table_cache[name]


def _entry_from_row(row: sqlite3.Row) -> LexicalEntry:
    return LexicalEntry(
        id=int(row["id"]),
        language=str(row["language"]),
        strongs_number=_optional(row["strongs_number"]),
        lemma=str(row["lemma"]),
        transliteration=_optional(row["transliteration"]),
        pronunciation=_optional(row["pronunciation"]),
        definition=str(row["definition"]),
        short_definition=_optional(row["short_definition"]),
        root=_optional(row["root"]),
        part_of_speech=_optional(row["part_of_speech"]),
        morphology=_optional(row["morphology"]),
        semantic_domain=_optional(row["semantic_domain"]),
        usage_notes=_optional(row["usage_notes"]),
        source=str(row["source"]),
        license=str(row["license"]),
        created_at=str(row["created_at"]),
        attribution=_optional(row["attribution"]),
    )


def _occurrence_from_row(row: sqlite3.Row) -> WordOccurrence:
    return WordOccurrence(
        book=str(row["book"]),
        chapter=int(row["chapter"]),
        verse=int(row["verse"]),
        position=int(row["word_position"]),
        language=str(row["language"]),
        surface_form=str(row["surface_form"]),
        lemma=str(row["lemma"]),
        strongs_number=_optional(row["strongs_number"]),
        morphology=_json_object(row["morphology_json"]),
        transliteration=_optional(row["transliteration"]),
        morphology_code=_optional(row["morphology_code"]),
        source=_optional(row["source"]),
        source_word_id=_optional(row["source_word_id"]),
    )


def _optional(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_object(value: object) -> dict[str, object]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
    text = text.translate(str.maketrans({"ḥ": "h", "ḫ": "h", "š": "s", "ś": "s", "ṭ": "t", "ṣ": "s", "ẓ": "z"}))
    return "".join(char for char in text if char.isalnum() or char.isspace()).strip()


def _normalize_strongs(value: str, language: str) -> str | None:
    import re

    raw = str(value or "").strip().upper()
    match = re.fullmatch(r"([HG])?\s*0*([0-9]+)[A-Z]?", raw)
    if not match:
        return None
    prefix, digits = match.groups()
    expected = "H" if language.strip().lower() == "hebrew" else "G"
    if prefix and prefix != expected:
        return None
    return f"{expected}{int(digits)}"
