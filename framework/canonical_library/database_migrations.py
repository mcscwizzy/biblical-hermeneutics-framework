"""Backward-compatible migrations for generated CKL SQLite databases."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from .database_schema import (
    CKL_DATABASE_SCHEMA_VERSION,
    CKL_RETRIEVAL_INDEX_VERSION,
    SCHEMA_SQL,
)
from .schema import CanonicalObject


_V4_SCHEMA_OBJECTS = {
    "canonical_temporal_scopes",
    "canonical_evidence_items",
    "canonical_evidence_claims",
    "canonical_evidence_sources",
    "canonical_evidence_scripture_references",
    "canonical_evidence_relationships",
    "canonical_evidence_external_references",
    "idx_temporal_scopes_range",
    "idx_temporal_scopes_periods",
    "idx_evidence_items_type",
    "idx_evidence_items_temporal",
    "idx_evidence_items_confidence",
    "idx_evidence_claims_claim",
    "idx_evidence_sources_source",
    "idx_evidence_scripture_reference",
    "idx_evidence_scripture_temporal",
    "idx_evidence_relationships_target",
    "idx_evidence_external_reference",
}


def migrate_database(
    path: str | Path,
    *,
    backup: bool = True,
) -> dict[str, Any]:
    """Migrate an existing CKL database to the current schema in place.

    Version 3 to 4 is additive: existing objects, claims, sources, lexicon
    tables, and FTS rows remain untouched.  New temporal rows are derived from
    each authoritative payload.  A full rebuild is still recommended after
    authored JSON evidence records have changed.
    """

    database_path = Path(path)
    if not database_path.exists():
        raise FileNotFoundError(f"CKL SQLite database not found: {database_path}")

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        metadata = {
            str(row["key"]): str(row["value"])
            for row in connection.execute("SELECT key, value FROM ckl_metadata")
        }
        source_version = metadata.get("database_schema_version", "")
        if source_version == CKL_DATABASE_SCHEMA_VERSION:
            return {
                "path": str(database_path),
                "from_version": source_version,
                "to_version": source_version,
                "changed": False,
                "backup_path": None,
            }
        if source_version != "3" or CKL_DATABASE_SCHEMA_VERSION != "4":
            raise RuntimeError(
                f"no CKL database migration is available from version {source_version or '<missing>'} "
                f"to {CKL_DATABASE_SCHEMA_VERSION}; rebuild the database instead"
            )

        backup_path: Path | None = None
        if backup:
            backup_path = _available_backup_path(database_path, source_version)
            shutil.copy2(database_path, backup_path)

        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            for statement in _selected_schema_statements(_V4_SCHEMA_OBJECTS):
                connection.execute(statement)
            evidence_count = 0
            for row in connection.execute(
                "SELECT id, payload_json FROM canonical_objects ORDER BY id"
            ):
                payload = json.loads(str(row["payload_json"]))
                obj = CanonicalObject.from_mapping(payload)
                if obj.evidence_items:
                    raise RuntimeError(
                        "version 3 database payload contains structured evidence that cannot be "
                        "safely inferred into the normalized tables; rebuild the CKL database"
                    )
                temporal = obj.temporal_scope
                connection.execute(
                    """
                    INSERT INTO canonical_temporal_scopes (
                        object_id, start_year, end_year, approximate, periods_json,
                        narrative_setting, source_composition_start_year,
                        source_composition_end_year,
                        source_composition_approximate, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        obj.id,
                        temporal.start_year,
                        temporal.end_year,
                        int(temporal.approximate),
                        json.dumps(temporal.periods, sort_keys=True, separators=(",", ":")),
                        temporal.narrative_setting,
                        temporal.source_composition_start_year,
                        temporal.source_composition_end_year,
                        int(temporal.source_composition_approximate),
                        temporal.notes,
                    ),
                )
            connection.execute(
                "UPDATE ckl_metadata SET value = ? WHERE key = 'database_schema_version'",
                (CKL_DATABASE_SCHEMA_VERSION,),
            )
            connection.execute(
                "UPDATE ckl_metadata SET value = ? WHERE key = 'retrieval_index_version'",
                (CKL_RETRIEVAL_INDEX_VERSION,),
            )
            connection.execute(
                "INSERT OR REPLACE INTO ckl_metadata (key, value) VALUES ('evidence_count', ?)",
                (str(evidence_count),),
            )

        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed after CKL migration")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise RuntimeError(f"SQLite foreign key check failed after CKL migration: {foreign_key_errors}")
        return {
            "path": str(database_path),
            "from_version": source_version,
            "to_version": CKL_DATABASE_SCHEMA_VERSION,
            "changed": True,
            "backup_path": str(backup_path) if backup_path is not None else None,
            "evidence_count": evidence_count,
        }
    finally:
        connection.close()


def _selected_schema_statements(names: set[str]) -> list[str]:
    selected: list[str] = []
    for raw_statement in SCHEMA_SQL.split(";"):
        statement = raw_statement.strip()
        if not statement:
            continue
        tokens = statement.replace("\n", " ").split()
        if len(tokens) < 3 or tokens[0].upper() != "CREATE":
            continue
        object_name = ""
        if tokens[1].upper() == "TABLE" and len(tokens) >= 3:
            object_name = tokens[2]
        elif tokens[1].upper() == "INDEX" and len(tokens) >= 3:
            object_name = tokens[2]
        if object_name in names:
            selected.append(statement)
    missing = names - {
        statement.replace("\n", " ").split()[2]
        for statement in selected
    }
    if missing:
        raise RuntimeError("migration schema is missing: " + ", ".join(sorted(missing)))
    return selected


def _available_backup_path(database_path: Path, source_version: str) -> Path:
    base = database_path.with_suffix(database_path.suffix + f".v{source_version}.bak")
    if not base.exists():
        return base
    suffix = 1
    while True:
        candidate = base.with_name(base.name + f".{suffix}")
        if not candidate.exists():
            return candidate
        suffix += 1
