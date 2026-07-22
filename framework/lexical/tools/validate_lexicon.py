"""Validate lexical database integrity and provenance."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any


REQUIRED_ENTRY_COLUMNS = {
    "id", "language", "strongs_number", "lemma", "transliteration", "pronunciation",
    "definition", "short_definition", "root", "part_of_speech", "morphology",
    "semantic_domain", "usage_notes", "source", "license", "created_at",
}


def validate_database(path: str | Path) -> dict[str, Any]:
    database_path = Path(path)
    if not database_path.is_file():
        raise FileNotFoundError(f"lexical SQLite database not found: {database_path}")
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SQLite integrity check failed: {integrity}")
        tables = {
            str(row["name"])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required_tables = {"lexical_entries", "lexical_sources", "word_forms", "verse_words"}
        missing_tables = required_tables - tables
        if missing_tables:
            raise ValueError("missing lexical tables: " + ", ".join(sorted(missing_tables)))
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(lexical_entries)")
        }
        missing_columns = REQUIRED_ENTRY_COLUMNS - columns
        if missing_columns:
            raise ValueError("missing lexical columns: " + ", ".join(sorted(missing_columns)))
        count = int(connection.execute("SELECT COUNT(*) FROM lexical_entries").fetchone()[0])
        missing_provenance = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM lexical_entries
                WHERE TRIM(COALESCE(source, '')) = ''
                   OR TRIM(COALESCE(license, '')) = ''
                   OR TRIM(COALESCE(created_at, '')) = ''
                """
            ).fetchone()[0]
        )
        if missing_provenance:
            raise ValueError(f"{missing_provenance} lexical entries have incomplete provenance")
        orphaned_sources = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM lexical_entries AS e
                LEFT JOIN lexical_sources AS s ON s.source = e.source
                WHERE s.source IS NULL
                """
            ).fetchone()[0]
        )
        if orphaned_sources:
            raise ValueError(f"{orphaned_sources} lexical entries have no source metadata")
        return {
            "path": str(database_path),
            "entries": count,
            "sources": int(connection.execute("SELECT COUNT(*) FROM lexical_sources").fetchone()[0]),
            "integrity": integrity,
            "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
        }
    finally:
        connection.close()


validate_lexicon = validate_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    args = parser.parse_args(argv)
    result = validate_database(args.database)
    print(f"Lexical database valid: {result['entries']} entries, {result['sources']} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
