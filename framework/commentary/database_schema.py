"""Versioned SQLite schema for standalone commentary resources."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_COMMENTARY_DATABASE_PATH = Path(".bhf") / "commentary.sqlite"
SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS commentary_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commentary_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    copyright TEXT,
    license TEXT,
    license_url TEXT,
    attribution TEXT,
    source_url TEXT,
    source_sha256 TEXT,
    imported_at TEXT,
    importer_version TEXT
);

CREATE TABLE IF NOT EXISTS commentary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES commentary_sources(id),
    external_id TEXT,
    kind TEXT NOT NULL,
    title TEXT,
    body TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    source_locator TEXT,
    payload_json TEXT
);

CREATE TABLE IF NOT EXISTS commentary_anchors (
    entry_id INTEGER PRIMARY KEY REFERENCES commentary_entries(id) ON DELETE CASCADE,
    book TEXT NOT NULL,
    start_chapter INTEGER,
    start_verse INTEGER,
    end_chapter INTEGER,
    end_verse INTEGER,
    relationship TEXT
);

CREATE INDEX IF NOT EXISTS idx_commentary_anchors_book_chapter
    ON commentary_anchors(book, start_chapter, end_chapter);
CREATE INDEX IF NOT EXISTS idx_commentary_anchors_book_verse
    ON commentary_anchors(book, start_chapter, start_verse, end_chapter, end_verse);
CREATE INDEX IF NOT EXISTS idx_commentary_entries_source_order
    ON commentary_entries(source_id, sort_order, id);
CREATE INDEX IF NOT EXISTS idx_commentary_entries_kind
    ON commentary_entries(kind, sort_order, id);
"""


def initialize_database(path: str | Path = DEFAULT_COMMENTARY_DATABASE_PATH) -> Path:
    """Create or upgrade a commentary database and return its path."""

    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > SCHEMA_VERSION:
            raise ValueError(
                f"commentary database schema {current_version} is newer than supported schema {SCHEMA_VERSION}"
            )
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            "INSERT INTO commentary_metadata(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SCHEMA_VERSION),),
        )
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return database_path
