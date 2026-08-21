"""Read-only repository for the commentary SQLite database."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .database_schema import DEFAULT_COMMENTARY_DATABASE_PATH, SCHEMA_VERSION
from .models import CommentaryEntry, CommentarySource, ScriptureAnchor


class CommentaryRepository:
    def __init__(self, database_path: str | Path = DEFAULT_COMMENTARY_DATABASE_PATH):
        self.database_path = Path(database_path)

    @property
    def available(self) -> bool:
        return self.database_path.is_file()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if not self.available:
            raise FileNotFoundError(str(self.database_path))
        connection = sqlite3.connect(f"file:{self.database_path.resolve()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def list_sources(self) -> list[CommentarySource]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM commentary_sources ORDER BY id").fetchall()
        return [_source_from_row(row) for row in rows]

    def get_source(self, source_id: str | None = None) -> CommentarySource | None:
        query = "SELECT * FROM commentary_sources"
        params: tuple[Any, ...] = ()
        if source_id:
            query += " WHERE id = ?"
            params = (source_id,)
        query += " ORDER BY id LIMIT 1"
        with self.connection() as connection:
            row = connection.execute(query, params).fetchone()
        return _source_from_row(row) if row else None

    def get_metadata(self, key: str) -> str | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT value FROM commentary_metadata WHERE key = ?",
                (key,),
            ).fetchone()
        return str(row[0]) if row else None

    def validate(self) -> dict[str, Any]:
        """Return a read-only health report for an installed commentary database."""

        if not self.available:
            return {"valid": False, "reason": "commentary_not_installed"}

        required_tables = {
            "commentary_metadata",
            "commentary_sources",
            "commentary_entries",
            "commentary_anchors",
        }
        try:
            with self.connection() as connection:
                integrity_check = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
                schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                counts = {
                    "sources": int(connection.execute("SELECT COUNT(*) FROM commentary_sources").fetchone()[0]),
                    "entries": int(connection.execute("SELECT COUNT(*) FROM commentary_entries").fetchone()[0]),
                    "anchors": int(connection.execute("SELECT COUNT(*) FROM commentary_anchors").fetchone()[0]),
                    "orphaned_anchors": int(connection.execute(
                        """SELECT COUNT(*)
                           FROM commentary_anchors a
                           LEFT JOIN commentary_entries e ON e.id = a.entry_id
                           WHERE e.id IS NULL"""
                    ).fetchone()[0]),
                }
        except (OSError, sqlite3.DatabaseError, TypeError, ValueError) as exc:
            return {"valid": False, "reason": "commentary_database_error", "detail": str(exc)}

        missing_tables = sorted(required_tables - tables)
        problems: list[str] = []
        if integrity_check.lower() != "ok":
            problems.append(f"integrity_check: {integrity_check}")
        if schema_version != SCHEMA_VERSION:
            problems.append(
                f"unsupported schema version {schema_version}; expected {SCHEMA_VERSION}"
            )
        if missing_tables:
            problems.append("missing tables: " + ", ".join(missing_tables))
        if counts["sources"] == 0:
            problems.append("no commentary sources installed")
        if counts["entries"] == 0:
            problems.append("no commentary entries installed")
        if counts["orphaned_anchors"]:
            problems.append(f"orphaned anchors: {counts['orphaned_anchors']}")
        return {
            "valid": not problems,
            "schema_version": schema_version,
            "integrity_check": integrity_check,
            "required_tables_present": not missing_tables,
            "missing_tables": missing_tables,
            "counts": counts,
            "problems": problems,
        }

    def lookup_chapter(self, book: str, chapter: int) -> list[CommentaryEntry]:
        sql = """
            SELECT e.*, s.id AS source_meta_id, s.name AS source_meta_name,
                   s.copyright AS source_meta_copyright, s.license AS source_meta_license,
                   s.license_url AS source_meta_license_url, s.attribution AS source_meta_attribution,
                   s.source_url AS source_meta_source_url, s.source_sha256 AS source_meta_source_sha256,
                   s.imported_at AS source_meta_imported_at, s.importer_version AS source_meta_importer_version,
                   a.book, a.start_chapter, a.start_verse, a.end_chapter,
                   a.end_verse, a.relationship
            FROM commentary_entries e
            JOIN commentary_sources s ON s.id = e.source_id
            LEFT JOIN commentary_anchors a ON a.entry_id = e.id
            WHERE (a.book = ? AND (
                (COALESCE(a.start_chapter, ?) <= ? AND COALESCE(a.end_chapter, a.start_chapter, ?) >= ?)
            ))
               OR (a.entry_id IS NULL AND e.kind IN ('book_introduction', 'profile'))
            ORDER BY CASE WHEN a.start_chapter IS NULL THEN 3
                          WHEN a.start_verse IS NULL THEN 2 ELSE 1 END,
                     COALESCE(a.start_chapter, 0), COALESCE(a.start_verse, 0),
                     e.sort_order, e.id
        """
        with self.connection() as connection:
            rows = connection.execute(sql, (book, chapter, chapter, chapter, chapter)).fetchall()
        return [_entry_from_row(row, match_type="chapter") for row in rows]

    def count_chapter(self, book: str, chapter: int) -> int:
        """Count matching chapter entries without loading commentary bodies."""

        sql = """
            SELECT COUNT(*)
            FROM commentary_entries e
            LEFT JOIN commentary_anchors a ON a.entry_id = e.id
            WHERE (a.book = ? AND (
                COALESCE(a.start_chapter, ?) <= ?
                AND COALESCE(a.end_chapter, a.start_chapter, ?) >= ?
            ))
               OR (a.entry_id IS NULL AND e.kind IN ('book_introduction', 'profile'))
        """
        with self.connection() as connection:
            return int(
                connection.execute(
                    sql,
                    (book, chapter, chapter, chapter, chapter),
                ).fetchone()[0]
            )

    def lookup_passage(self, book: str, chapter: int, start_verse: int, end_verse: int) -> list[CommentaryEntry]:
        sql = """
            SELECT e.*, s.id AS source_meta_id, s.name AS source_meta_name,
                   s.copyright AS source_meta_copyright, s.license AS source_meta_license,
                   s.license_url AS source_meta_license_url, s.attribution AS source_meta_attribution,
                   s.source_url AS source_meta_source_url, s.source_sha256 AS source_meta_source_sha256,
                   s.imported_at AS source_meta_imported_at, s.importer_version AS source_meta_importer_version,
                   a.book, a.start_chapter, a.start_verse, a.end_chapter,
                   a.end_verse, a.relationship
            FROM commentary_entries e
            JOIN commentary_sources s ON s.id = e.source_id
            JOIN commentary_anchors a ON a.entry_id = e.id
            WHERE a.book = ?
              AND COALESCE(a.start_chapter, ?) <= ?
              AND COALESCE(a.end_chapter, a.start_chapter, ?) >= ?
              AND (
                a.start_chapter != ? OR a.end_chapter != ? OR
                COALESCE(a.start_verse, 0) <= ? AND COALESCE(a.end_verse, a.start_verse, 2147483647) >= ?
              )
            ORDER BY CASE
                       WHEN a.start_chapter = ? AND a.end_chapter = ?
                        AND a.start_verse = ? AND a.end_verse = ? THEN 0
                       WHEN a.start_verse IS NULL THEN 2 ELSE 1 END,
                     COALESCE(a.start_chapter, 0), COALESCE(a.start_verse, 0),
                     e.sort_order, e.id
        """
        params = (
            book, chapter, chapter, chapter, chapter,
            chapter, chapter, start_verse, end_verse,
            chapter, chapter, start_verse, end_verse,
        )
        with self.connection() as connection:
            rows = connection.execute(sql, params).fetchall()
        entries = [_entry_from_row(row, match_type="overlap") for row in rows]
        return entries

    def count_passage(self, book: str, chapter: int, start_verse: int, end_verse: int) -> int:
        """Count overlapping passage entries without loading commentary bodies."""

        sql = """
            SELECT COUNT(*)
            FROM commentary_entries e
            JOIN commentary_anchors a ON a.entry_id = e.id
            WHERE a.book = ?
              AND COALESCE(a.start_chapter, ?) <= ?
              AND COALESCE(a.end_chapter, a.start_chapter, ?) >= ?
              AND (
                a.start_chapter != ? OR a.end_chapter != ? OR
                COALESCE(a.start_verse, 0) <= ?
                AND COALESCE(a.end_verse, a.start_verse, 2147483647) >= ?
              )
        """
        params = (
            book,
            chapter,
            chapter,
            chapter,
            chapter,
            chapter,
            chapter,
            start_verse,
            end_verse,
        )
        with self.connection() as connection:
            return int(connection.execute(sql, params).fetchone()[0])


def _source_from_row(row: sqlite3.Row) -> CommentarySource:
    return CommentarySource(**{key: row[key] for key in CommentarySource.__dataclass_fields__})


def _entry_from_row(row: sqlite3.Row, *, match_type: str) -> CommentaryEntry:
    source = CommentarySource(
        id=row["source_meta_id"],
        name=row["source_meta_name"],
        copyright=row["source_meta_copyright"],
        license=row["source_meta_license"],
        license_url=row["source_meta_license_url"],
        attribution=row["source_meta_attribution"],
        source_url=row["source_meta_source_url"],
        source_sha256=row["source_meta_source_sha256"],
        imported_at=row["source_meta_imported_at"],
        importer_version=row["source_meta_importer_version"],
    )
    payload = json.loads(row["payload_json"]) if row["payload_json"] else None
    anchor = None
    if row["book"]:
        anchor = ScriptureAnchor(
            book=row["book"], start_chapter=row["start_chapter"], start_verse=row["start_verse"],
            end_chapter=row["end_chapter"], end_verse=row["end_verse"], relationship=row["relationship"],
        )
    return CommentaryEntry(
        id=row["id"], source=source, source_id=row["source_id"], external_id=row["external_id"],
        kind=row["kind"], title=row["title"], body=row["body"], sort_order=row["sort_order"],
        source_locator=row["source_locator"], anchor=anchor, payload=payload, match_type=match_type,
    )
