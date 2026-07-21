"""Read-only SQLite repository for lexical runtime lookups."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from .models import LexicalEntry


class LexicalRepository:
    """Query the generated lexical database without loading source XML."""

    def __init__(self, database_path: str | Path, *, read_only: bool = True) -> None:
        self.path = Path(database_path)
        self.read_only = read_only
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._lock = threading.Lock()

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


def _optional(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


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
