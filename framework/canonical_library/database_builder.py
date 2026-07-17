"""Build and verify the generated SQLite CKL runtime database."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .database_schema import (
    CKL_DATABASE_SCHEMA_VERSION,
    CKL_RETRIEVAL_INDEX_VERSION,
    REQUIRED_INDEXES,
    SCHEMA_SQL,
)
from .loader import CanonicalLibrary, _stable_json_fingerprint
from .normalization import normalize_alias, normalize_id
from .retrieval import FIELD_WEIGHTS, collect_field_search_terms
from .scripture import build_book_alias_lookup, parse_scripture_reference
from .schema import CanonicalObject


@dataclass(frozen=True)
class BuildDatabaseResult:
    path: Path
    object_count: int
    inventory_fingerprint: str
    database_schema_version: str = CKL_DATABASE_SCHEMA_VERSION


def build_database(
    root: str | Path | None = None,
    output: str | Path | None = None,
) -> BuildDatabaseResult:
    """Build a deterministic SQLite database from validated CKL JSON files."""

    root_path = Path(root) if root is not None else Path(__file__).resolve().parent
    output_path = Path(output) if output is not None else Path(".bhf/ckl.sqlite")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    library = CanonicalLibrary(root=root_path).load()
    fingerprint = library.inventory_fingerprint()
    manifest_fingerprint = _stable_json_fingerprint(_stable_manifest_payload(library.manifest))

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{output_path.name}.",
        suffix=".tmp",
        dir=str(output_path.parent),
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        _write_database(
            tmp_path,
            library=library,
            inventory_fingerprint=fingerprint,
            manifest_fingerprint=manifest_fingerprint,
        )
        verify_database(
            tmp_path,
            root=root_path,
            compare_fingerprint=True,
            expected_fingerprint=fingerprint,
        )
        os.replace(tmp_path, output_path)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    return BuildDatabaseResult(
        path=output_path,
        object_count=len(library.objects_by_id),
        inventory_fingerprint=fingerprint,
    )


def verify_database(
    path: str | Path,
    *,
    root: str | Path | None = None,
    compare_fingerprint: bool = True,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Verify database metadata, integrity, counts, indexes, and freshness."""

    db_path = Path(path)
    if not db_path.exists():
        raise FileNotFoundError(f"CKL SQLite database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        metadata = {
            str(row["key"]): str(row["value"])
            for row in conn.execute("SELECT key, value FROM ckl_metadata")
        }
        schema_version = metadata.get("database_schema_version")
        if schema_version != CKL_DATABASE_SCHEMA_VERSION:
            raise RuntimeError(
                f"CKL SQLite database schema version {CKL_DATABASE_SCHEMA_VERSION} is required, "
                f"but version {schema_version or '<missing>'} was found. Rebuild the database with: "
                "python -m framework.canonical_library build-db"
            )
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RuntimeError(f"SQLite foreign key check failed: {foreign_key_errors}")

        object_count = int(conn.execute("SELECT COUNT(*) FROM canonical_objects").fetchone()[0])
        metadata_count = int(metadata.get("object_count", "-1"))
        if object_count != metadata_count:
            raise RuntimeError(f"object count mismatch: metadata={metadata_count} actual={object_count}")

        indexes = {
            str(row["name"])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex%'"
            )
        }
        missing_indexes = sorted(REQUIRED_INDEXES - indexes)
        if missing_indexes:
            raise RuntimeError("missing required CKL SQLite indexes: " + ", ".join(missing_indexes))

        if compare_fingerprint:
            source_fingerprint = expected_fingerprint
            if source_fingerprint is None:
                root_path = Path(root) if root is not None else Path(__file__).resolve().parent
                source_fingerprint = CanonicalLibrary(root=root_path).load().inventory_fingerprint()
            if metadata.get("inventory_fingerprint") != source_fingerprint:
                raise RuntimeError("CKL SQLite database fingerprint does not match the JSON inventory")

        return {
            "path": str(db_path),
            "database_schema_version": schema_version,
            "framework_version": metadata.get("framework_version"),
            "schema_version": metadata.get("schema_version"),
            "object_count": object_count,
            "build_timestamp": metadata.get("build_timestamp"),
            "inventory_fingerprint": metadata.get("inventory_fingerprint"),
            "file_size": db_path.stat().st_size,
        }
    finally:
        conn.close()


def database_info(path: str | Path) -> dict[str, Any]:
    db_path = Path(path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        metadata = {
            str(row["key"]): str(row["value"])
            for row in conn.execute("SELECT key, value FROM ckl_metadata")
        }
        object_count = int(conn.execute("SELECT COUNT(*) FROM canonical_objects").fetchone()[0])
        return {
            "database_path": str(db_path),
            "database_schema_version": metadata.get("database_schema_version"),
            "framework_version": metadata.get("framework_version"),
            "schema_version": metadata.get("schema_version"),
            "object_count": object_count,
            "build_timestamp": metadata.get("build_timestamp"),
            "inventory_fingerprint": metadata.get("inventory_fingerprint"),
            "database_file_size": db_path.stat().st_size,
        }
    finally:
        conn.close()


def _write_database(
    path: Path,
    *,
    library: CanonicalLibrary,
    inventory_fingerprint: str,
    manifest_fingerprint: str,
) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.executescript(SCHEMA_SQL)

        objects = [library.objects_by_id[object_id] for object_id in sorted(library.objects_by_id)]
        book_alias_lookup = build_book_alias_lookup(obj for obj in objects if obj.type == "book")

        with conn:
            for obj in objects:
                source_path = library.source_path_for(obj.id)
                source_path_text = None
                if source_path is not None:
                    try:
                        source_path_text = source_path.relative_to(library.root).as_posix()
                    except ValueError:
                        source_path_text = source_path.as_posix()
                _insert_object(conn, obj, source_path=source_path_text)
            for obj in objects:
                _insert_aliases(conn, obj)
                _insert_keywords(conn, obj)
                _insert_relationships(conn, obj)
                _insert_scripture_references(conn, obj, book_alias_lookup=book_alias_lookup)
            _insert_metadata(
                conn,
                library=library,
                inventory_fingerprint=inventory_fingerprint,
                manifest_fingerprint=manifest_fingerprint,
                object_count=len(objects),
            )
    finally:
        conn.close()


def _insert_object(sql: sqlite3.Connection, obj: CanonicalObject, *, source_path: str | None) -> None:
    sql.execute(
        """
        INSERT INTO canonical_objects (
            id, type, title, normalized_title, summary, content_status,
            review_status, confidence, importance, object_version, source_path,
            payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            obj.id,
            obj.type,
            obj.title,
            normalize_alias(obj.title),
            obj.summary,
            obj.content_status,
            obj.review_status,
            obj.confidence,
            obj.importance,
            obj.object_version,
            source_path,
            json.dumps(obj.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        ),
    )


def _insert_aliases(sql: sqlite3.Connection, obj: CanonicalObject) -> None:
    for alias in obj.aliases:
        normalized = normalize_alias(alias)
        if not normalized:
            continue
        sql.execute(
            """
            INSERT INTO canonical_aliases (normalized_alias, object_id, original_alias)
            VALUES (?, ?, ?)
            """,
            (normalized, obj.id, alias),
        )


def _insert_keywords(sql: sqlite3.Connection, obj: CanonicalObject) -> None:
    for field_name, terms in collect_field_search_terms(obj).items():
        weight = FIELD_WEIGHTS.get(field_name, 1)
        for term in sorted(terms):
            normalized = normalize_alias(term)
            if not normalized:
                continue
            sql.execute(
                """
                INSERT OR IGNORE INTO canonical_keywords (term, object_id, field_name, field_weight)
                VALUES (?, ?, ?, ?)
                """,
                (normalized, obj.id, field_name, weight),
            )


def _insert_relationships(sql: sqlite3.Connection, obj: CanonicalObject) -> None:
    relationships: list[dict[str, Any]] = [
        relationship.to_dict() if hasattr(relationship, "to_dict") else dict(relationship)
        for relationship in obj.related_objects
    ]
    for field_name, relationship_type in {
        "related_people": "associated-person",
        "related_places": "associated-place",
        "related_events": "associated-event",
    }.items():
        for related_id in getattr(obj, field_name):
            relationships.append(
                {
                    "id": str(related_id),
                    "relationship": relationship_type,
                    "weight": 1,
                    "notes": "",
                }
            )
    for relationship in relationships:
        sql.execute(
            """
            INSERT OR IGNORE INTO canonical_relationships (
                source_id, target_id, relationship, weight, notes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                obj.id,
                normalize_id(str(relationship["id"])),
                relationship["relationship"],
                int(relationship.get("weight") or 1),
                str(relationship.get("notes") or ""),
            ),
        )


def _insert_scripture_references(
    sql: sqlite3.Connection,
    obj: CanonicalObject,
    *,
    book_alias_lookup: Mapping[str, str],
) -> None:
    for reference in obj.scripture_references:
        parsed = parse_scripture_reference(reference.reference, book_alias_lookup=book_alias_lookup)
        if parsed is None:
            continue
        sql.execute(
            """
            INSERT INTO canonical_scripture_references (
                object_id, reference_text, book, start_chapter, start_verse,
                end_chapter, end_verse, relationship, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.id,
                reference.reference,
                parsed.book,
                parsed.start_chapter,
                parsed.start_verse,
                parsed.end_chapter,
                parsed.end_verse,
                reference.relationship,
                reference.notes,
            ),
        )


def _insert_metadata(
    sql: sqlite3.Connection,
    *,
    library: CanonicalLibrary,
    inventory_fingerprint: str,
    manifest_fingerprint: str,
    object_count: int,
) -> None:
    metadata = {
        "framework_version": str(library.manifest.get("framework_version") or ""),
        "schema_version": str(library.manifest.get("schema_version") or ""),
        "database_schema_version": CKL_DATABASE_SCHEMA_VERSION,
        "retrieval_index_version": CKL_RETRIEVAL_INDEX_VERSION,
        "inventory_fingerprint": inventory_fingerprint,
        "build_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "object_count": str(object_count),
        "source_manifest_fingerprint": manifest_fingerprint,
    }
    sql.executemany(
        "INSERT INTO ckl_metadata (key, value) VALUES (?, ?)",
        sorted(metadata.items()),
    )


def _stable_manifest_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "framework_version": manifest.get("framework_version"),
        "schema_version": manifest.get("schema_version"),
        "object_count": manifest.get("object_count"),
        "categories": manifest.get("categories"),
    }
