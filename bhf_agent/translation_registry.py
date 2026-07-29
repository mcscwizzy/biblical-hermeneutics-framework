"""SQLite registry for installed Bible translation resources."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .translation_storage import (
    installed_translation_metadata_path,
    installed_translation_path,
    load_asv_bible,
    load_bible_dataset,
    load_legacy_kjv_bible,
    normalize_translation_id,
    translations_root,
)


SCHEMA_VERSION = 1
DEFAULT_TRANSLATION_ID = "asv"
DEFAULT_KJV_TRANSLATION_ID = "kjv"


class TranslationRegistryError(ValueError):
    """Raised when translation registry state cannot be updated."""


def registry_path() -> Path:
    return translations_root() / "translations.sqlite"


def initialize_registry(path: str | Path | None = None) -> None:
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)


def list_translations(*, installed_only: bool = False, path: str | Path | None = None) -> list[dict[str, Any]]:
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)
        sql = 'SELECT id, name, source, installed, "default", created_date FROM translations'
        if installed_only:
            sql += " WHERE installed = 1"
        sql += ' ORDER BY "default" DESC, id ASC'
        return [_row_to_translation(row) for row in connection.execute(sql)]


def list_installed_registry_translations(path: str | Path | None = None) -> list[dict[str, Any]]:
    return list_translations(installed_only=True, path=path)


def get_translation(translation_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    normalized = normalize_translation_id(translation_id)
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            'SELECT id, name, source, installed, "default", created_date FROM translations WHERE id = ?',
            (normalized,),
        ).fetchone()
    return _row_to_translation(row) if row else None


def upsert_translation(
    translation_id: str,
    *,
    name: str,
    source: str,
    installed: bool = True,
    is_default: bool = False,
    created_date: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    normalized = normalize_translation_id(translation_id)
    display_name = str(name or normalized.upper()).strip() or normalized.upper()
    source_value = str(source or "").strip()
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)
        if is_default:
            connection.execute('UPDATE translations SET "default" = 0')
        connection.execute(
            """
            INSERT INTO translations (id, name, source, installed, "default", created_date)
            VALUES (?, ?, ?, ?, ?, COALESCE(?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                source = excluded.source,
                installed = excluded.installed,
                "default" = CASE
                    WHEN excluded."default" = 1 THEN 1
                    ELSE translations."default"
                END,
                created_date = COALESCE(translations.created_date, excluded.created_date)
            """,
            (
                normalized,
                display_name,
                source_value,
                1 if installed else 0,
                1 if is_default else 0,
                created_date,
            ),
        )
        if not _has_default(connection):
            connection.execute('UPDATE translations SET "default" = 1 WHERE id = ?', (DEFAULT_TRANSLATION_ID,))
        row = connection.execute(
            'SELECT id, name, source, installed, "default", created_date FROM translations WHERE id = ?',
            (normalized,),
        ).fetchone()
    return _row_to_translation(row)


def set_default_translation(translation_id: str, path: str | Path | None = None) -> str:
    normalized = normalize_translation_id(translation_id)
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            "SELECT installed FROM translations WHERE id = ?",
            (normalized,),
        ).fetchone()
        if not row or not bool(row["installed"]):
            raise TranslationRegistryError("Only an installed translation can be set as default")
        connection.execute('UPDATE translations SET "default" = 0')
        connection.execute('UPDATE translations SET "default" = 1 WHERE id = ?', (normalized,))
    return normalized


def default_translation_id(path: str | Path | None = None) -> str:
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            'SELECT id FROM translations WHERE installed = 1 AND "default" = 1 ORDER BY id LIMIT 1'
        ).fetchone()
    return str(row["id"]) if row else DEFAULT_TRANSLATION_ID


def mark_translation_removed(translation_id: str, path: str | Path | None = None) -> None:
    normalized = normalize_translation_id(translation_id)
    if normalized in {DEFAULT_TRANSLATION_ID, DEFAULT_KJV_TRANSLATION_ID}:
        raise TranslationRegistryError(f"{normalized.upper()} cannot be removed")
    with closing(_connect(path)) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            'SELECT "default" FROM translations WHERE id = ?',
            (normalized,),
        ).fetchone()
        connection.execute(
            'UPDATE translations SET installed = 0, "default" = 0 WHERE id = ?',
            (normalized,),
        )
        if row and bool(row["default"]):
            connection.execute('UPDATE translations SET "default" = 1 WHERE id = ?', (DEFAULT_TRANSLATION_ID,))


def _connect(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path is not None else registry_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS translations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            installed INTEGER NOT NULL DEFAULT 0,
            "default" INTEGER NOT NULL DEFAULT 0,
            created_date TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    connection.execute("PRAGMA user_version = 1")
    _seed_asv(connection)
    _seed_kjv(connection)
    _migrate_sidecar_metadata(connection)


def _seed_asv(connection: sqlite3.Connection) -> None:
    data = load_asv_bible()
    translation = dict(data.get("translation", {}))
    connection.execute(
        """
        INSERT INTO translations (id, name, source, installed, "default", created_date)
        VALUES (?, ?, ?, 1, 1, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            source = excluded.source,
            installed = 1
        """,
        (
            DEFAULT_TRANSLATION_ID,
            str(translation.get("name") or "American Standard Version"),
            str(translation.get("source") or "bundled:bhf_agent/data/asv_bible.json"),
        ),
    )


def _seed_kjv(connection: sqlite3.Connection) -> None:
    data = load_legacy_kjv_bible()
    translation = dict(data.get("translation", {}))
    connection.execute(
        """
        INSERT INTO translations (id, name, source, installed, "default", created_date)
        VALUES (?, ?, ?, 1, 0, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            source = excluded.source,
            installed = 1
        """,
        (
            DEFAULT_KJV_TRANSLATION_ID,
            str(translation.get("name") or "King James Version"),
            "bundled:bhf_agent/data/kjv_bible.json",
        ),
    )


def _migrate_sidecar_metadata(connection: sqlite3.Connection) -> None:
    root = translations_root()
    if not root.exists():
        return
    for metadata_path in sorted(root.glob("*.metadata.json")):
        if metadata_path.name == "asv.metadata.json":
            continue
        translation_id = metadata_path.name[: -len(".metadata.json")]
        try:
            normalized = normalize_translation_id(translation_id)
        except Exception:
            continue
        if not installed_translation_path(normalized).exists():
            continue
        metadata: dict[str, Any] = {}
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}
        name = str(metadata.get("name") or "").strip()
        if not name:
            try:
                dataset = load_bible_dataset(installed_translation_path(normalized))
                name = str(dataset.get("translation", {}).get("name") or normalized.upper())
            except Exception:
                name = normalized.upper()
        source = str(
            metadata.get("source_url")
            or metadata.get("source_type")
            or metadata.get("source_repository")
            or installed_translation_metadata_path(normalized)
        )
        created_date = str(metadata.get("installed_at") or "").strip() or None
        connection.execute(
            """
            INSERT INTO translations (id, name, source, installed, "default", created_date)
            VALUES (?, ?, ?, 1, 0, COALESCE(?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                source = excluded.source,
                installed = 1,
                created_date = COALESCE(translations.created_date, excluded.created_date)
            """,
            (normalized, name, source, created_date),
        )


def _has_default(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        'SELECT 1 FROM translations WHERE installed = 1 AND "default" = 1 LIMIT 1'
    ).fetchone()
    return row is not None


def _row_to_translation(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "source": row["source"],
        "installed": bool(row["installed"]),
        "default": bool(row["default"]),
        "created_date": row["created_date"],
    }
