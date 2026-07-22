"""Validate lexical database integrity, provenance, and token coverage."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from framework.canonical_library.lexicon_morphology import decode_morphology


REQUIRED_ENTRY_COLUMNS = {
    "id", "language", "strongs_number", "lemma", "transliteration", "pronunciation",
    "definition", "short_definition", "root", "part_of_speech", "morphology",
    "semantic_domain", "usage_notes", "source", "license", "created_at",
}


def validate_database(path: str | Path, *, strict: bool = False) -> dict[str, Any]:
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
        token_report = _validate_token_integrity(connection)
        if strict:
            problems = _strict_token_problems(token_report)
            if problems:
                raise ValueError("lexical token validation failed: " + "; ".join(problems))
        return {
            "path": str(database_path),
            "entries": count,
            "sources": int(connection.execute("SELECT COUNT(*) FROM lexical_sources").fetchone()[0]),
            "integrity": integrity,
            "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            **token_report,
        }
    finally:
        connection.close()


validate_lexicon = validate_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if imported verse tokens/forms have unresolved Strong's numbers, missing lemmas, malformed morphology JSON, or invalid positions.",
    )
    args = parser.parse_args(argv)
    result = validate_database(args.database, strict=args.strict)
    print(f"Lexical database valid: {result['entries']} entries, {result['sources']} sources")
    print(
        "Token coverage: "
        f"{result['verse_words']} verse words, {result['word_forms']} word forms, "
        f"{result['unresolved_token_strongs']} unresolved Strong's, "
        f"{result['unresolved_token_lemmas']} unresolved lemmas"
    )
    return 0


def _validate_token_integrity(connection: sqlite3.Connection) -> dict[str, Any]:
    table_counts = {
        "verse_words": _table_count(connection, "verse_words"),
        "word_forms": _table_count(connection, "word_forms"),
    }
    unresolved_strongs = {
        table: _unresolved_strongs(connection, table)
        for table in ("verse_words", "word_forms")
    }
    unresolved_lemmas = {
        table: _unresolved_lemmas(connection, table)
        for table in ("verse_words", "word_forms")
    }
    invalid_positions = _invalid_verse_word_positions(connection)
    morphology_report = _morphology_report(connection)
    return {
        **table_counts,
        "unresolved_strongs_by_table": unresolved_strongs,
        "unresolved_lemmas_by_table": unresolved_lemmas,
        "unresolved_token_strongs": sum(unresolved_strongs.values()),
        "unresolved_token_lemmas": sum(unresolved_lemmas.values()),
        "invalid_verse_word_positions": invalid_positions,
        **morphology_report,
    }


def _strict_token_problems(report: dict[str, Any]) -> list[str]:
    checks = (
        ("unresolved_token_strongs", "token Strong's numbers do not resolve"),
        ("unresolved_token_lemmas", "token lemmas do not resolve"),
        ("invalid_verse_word_positions", "verse words have invalid reference positions"),
        ("invalid_morphology_json", "token morphology JSON is malformed"),
    )
    problems = []
    for key, label in checks:
        value = int(report.get(key) or 0)
        if value:
            problems.append(f"{value} {label}")
    return problems


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _unresolved_strongs(connection: sqlite3.Connection, table: str) -> int:
    return int(
        connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {table} AS token
            LEFT JOIN lexical_entries AS entry
              ON entry.language = token.language
             AND entry.strongs_number = token.strongs_number
            WHERE TRIM(COALESCE(token.strongs_number, '')) <> ''
              AND entry.id IS NULL
            """
        ).fetchone()[0]
    )


def _unresolved_lemmas(connection: sqlite3.Connection, table: str) -> int:
    return int(
        connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {table} AS token
            LEFT JOIN lexical_entries AS entry
              ON entry.language = token.language
             AND entry.normalized_lemma = token.normalized_lemma
            WHERE TRIM(COALESCE(token.normalized_lemma, '')) <> ''
              AND entry.id IS NULL
            """
        ).fetchone()[0]
    )


def _invalid_verse_word_positions(connection: sqlite3.Connection) -> int:
    return int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM verse_words
            WHERE TRIM(COALESCE(book, '')) = ''
               OR chapter <= 0
               OR verse <= 0
               OR word_position <= 0
            """
        ).fetchone()[0]
    )


def _morphology_report(connection: sqlite3.Connection) -> dict[str, int]:
    invalid_json = 0
    unknown_codes = 0
    parsed_codes = 0
    for table in ("verse_words", "word_forms"):
        rows = connection.execute(
            f"""
            SELECT language, morphology_code, morphology_json
            FROM {table}
            WHERE TRIM(COALESCE(morphology_code, '')) <> ''
               OR TRIM(COALESCE(morphology_json, '')) <> ''
            """
        ).fetchall()
        for row in rows:
            morphology_json = str(row["morphology_json"] or "").strip()
            if morphology_json:
                try:
                    parsed = json.loads(morphology_json)
                except (TypeError, ValueError):
                    invalid_json += 1
                    parsed = None
                if parsed is not None and not isinstance(parsed, dict):
                    invalid_json += 1
            code = str(row["morphology_code"] or "").strip()
            if code:
                decoded = decode_morphology(str(row["language"]), code)
                if decoded.get("unknown_code"):
                    unknown_codes += 1
                elif decoded:
                    parsed_codes += 1
    return {
        "parsed_morphology_codes": parsed_codes,
        "unknown_morphology_codes": unknown_codes,
        "invalid_morphology_json": invalid_json,
    }


if __name__ == "__main__":
    raise SystemExit(main())
