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
from .retrieval.indexer import inventory_content_signature
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
    source_inventory_signature = inventory_content_signature(root_path)

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
            source_inventory_signature=source_inventory_signature,
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
        claim_count = int(conn.execute("SELECT COUNT(*) FROM canonical_claims").fetchone()[0])
        source_count = int(conn.execute("SELECT COUNT(*) FROM canonical_sources").fetchone()[0])
        if claim_count != int(metadata.get("claim_count", "-1")):
            raise RuntimeError("claim count does not match CKL SQLite metadata")
        if source_count != int(metadata.get("source_count", "-1")):
            raise RuntimeError("source count does not match CKL SQLite metadata")
        fts_count = int(conn.execute("SELECT COUNT(*) FROM canonical_fts").fetchone()[0])
        if fts_count != object_count:
            raise RuntimeError(f"FTS document count mismatch: objects={object_count} fts={fts_count}")

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
            "claim_count": claim_count,
            "source_count": source_count,
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
        claim_count = int(conn.execute("SELECT COUNT(*) FROM canonical_claims").fetchone()[0])
        source_count = int(conn.execute("SELECT COUNT(*) FROM canonical_sources").fetchone()[0])
        return {
            "database_path": str(db_path),
            "database_schema_version": metadata.get("database_schema_version"),
            "framework_version": metadata.get("framework_version"),
            "schema_version": metadata.get("schema_version"),
            "object_count": object_count,
            "claim_count": claim_count,
            "source_count": source_count,
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
    source_inventory_signature: str,
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
                _insert_claims_and_sources(conn, obj, book_alias_lookup=book_alias_lookup)
                _insert_fts_document(conn, obj)
            _insert_metadata(
                conn,
                library=library,
                inventory_fingerprint=inventory_fingerprint,
                manifest_fingerprint=manifest_fingerprint,
                source_inventory_signature=source_inventory_signature,
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


def _insert_claims_and_sources(
    sql: sqlite3.Connection,
    obj: CanonicalObject,
    *,
    book_alias_lookup: Mapping[str, str],
) -> None:
    """Normalize authored claim/source evidence while JSON remains authoritative."""

    claims_by_id = {claim.id: claim for claim in obj.claims}
    sources_by_id = {source.id: source for source in obj.sources}
    for claim in obj.claims:
        sql.execute(
            """
            INSERT INTO canonical_claims (
                object_id, claim_id, claim_text, claim_type, certainty,
                dispute_status, rationale, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.id,
                claim.id,
                claim.claim,
                claim.claim_type,
                claim.certainty,
                claim.dispute_status,
                claim.rationale,
                claim.notes,
            ),
        )
        for reference_text in claim.scripture_references:
            parsed = parse_scripture_reference(reference_text, book_alias_lookup=book_alias_lookup)
            sql.execute(
                """
                INSERT INTO canonical_claim_scripture_references (
                    object_id, claim_id, reference_text, book, start_chapter,
                    start_verse, end_chapter, end_verse
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obj.id,
                    claim.id,
                    reference_text,
                    parsed.book if parsed else None,
                    parsed.start_chapter if parsed else None,
                    parsed.start_verse if parsed else None,
                    parsed.end_chapter if parsed else None,
                    parsed.end_verse if parsed else None,
                ),
            )

    for source in obj.sources:
        sql.execute(
            """
            INSERT INTO canonical_sources (
                object_id, source_id, title, author, publisher, year, locator,
                url, source_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.id,
                source.id,
                source.title,
                source.author,
                source.publisher,
                source.year,
                source.locator,
                source.url,
                source.source_type,
                source.notes,
            ),
        )
        for supported_item in source.supports:
            sql.execute(
                """
                INSERT INTO canonical_source_supports (object_id, source_id, supported_item)
                VALUES (?, ?, ?)
                """,
                (obj.id, source.id, supported_item),
            )

    for claim in obj.claims:
        for source_order, source_id in enumerate(claim.source_ids):
            if source_id not in sources_by_id:
                continue
            sql.execute(
                """
                INSERT OR IGNORE INTO canonical_claim_sources (
                    object_id, claim_id, source_id, relationship, source_order
                ) VALUES (?, ?, ?, 'source_id', ?)
                """,
                (obj.id, claim.id, source_id, source_order),
            )
    for source_order, source in enumerate(obj.sources):
        for supported_item in source.supports:
            if supported_item not in claims_by_id:
                continue
            sql.execute(
                """
                INSERT OR IGNORE INTO canonical_claim_sources (
                    object_id, claim_id, source_id, relationship, source_order
                ) VALUES (?, ?, ?, 'supports', ?)
                """,
                (obj.id, supported_item, source.id, source_order),
            )


def _insert_fts_document(sql: sqlite3.Connection, obj: CanonicalObject) -> None:
    retrieval_metadata = obj.retrieval_metadata if isinstance(obj.retrieval_metadata, Mapping) else {}
    contexts = [
        obj.historical_context,
        obj.ancient_near_east_context,
        obj.hebraic_worldview,
        obj.second_temple_context,
        obj.canonical_context,
        obj.literary_context,
        obj.covenantal_significance,
        *obj.interpretive_disputes,
        *(note.note for note in obj.interpretive_notes),
    ]
    sql.execute(
        """
        INSERT INTO canonical_fts (
            object_id, title, aliases, summary, common_questions, keywords,
            claims, contexts, retrieval_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            obj.id,
            obj.title,
            " ".join(obj.aliases),
            obj.summary,
            " ".join(obj.common_questions),
            " ".join([*obj.keywords, *obj.major_themes, *obj.hebrew_words, *obj.greek_words]),
            " ".join(
                part
                for claim in obj.claims
                for part in (claim.claim, claim.rationale, claim.notes)
                if part
            ),
            " ".join(part for part in contexts if part),
            " ".join(
                str(item)
                for key in (
                    "aliases",
                    "search_terms",
                    "common_questions",
                    "related_topics",
                    "semantic_keywords",
                )
                for item in (retrieval_metadata.get(key) or [])
            ),
        ),
    )


def _insert_metadata(
    sql: sqlite3.Connection,
    *,
    library: CanonicalLibrary,
    inventory_fingerprint: str,
    manifest_fingerprint: str,
    source_inventory_signature: str,
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
        "claim_count": str(sum(len(obj.claims) for obj in library.objects_by_id.values())),
        "source_count": str(sum(len(obj.sources) for obj in library.objects_by_id.values())),
        "source_manifest_fingerprint": manifest_fingerprint,
        "source_inventory_signature": source_inventory_signature,
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
