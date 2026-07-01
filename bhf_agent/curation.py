"""Local curation helpers for editable study data."""

from __future__ import annotations

from typing import Any

from .curation_schema import (
    CURATION_COLLECTIONS,
    _timestamp,
    normalized_record,
    row_to_record,
    spec_for,
    value_for_db,
)
from .study_db import (
    DEFAULT_DB_PATH,
    StudyDataError,
    _ensure_schema,
)
from .db.connection import connect


def list_curation_collections(path: str | None = None) -> list[dict[str, Any]]:
    resolved = path or DEFAULT_DB_PATH
    collections: list[dict[str, Any]] = []
    for spec in CURATION_COLLECTIONS.values():
        collections.append(
            {
                "key": spec.key,
                "title": spec.title,
                "count": len(list_curation_records(spec.key, path=resolved)),
            }
        )
    return collections


def list_curation_records(collection: str, path: str | None = None) -> list[dict[str, Any]]:
    spec = spec_for(collection)
    if spec.list_fn is not None:
        return spec.list_fn(None, None, path or DEFAULT_DB_PATH)
    with connect(path or DEFAULT_DB_PATH) as connection:
        _ensure_schema(connection)
        rows = connection.execute(f"SELECT * FROM {spec.table} ORDER BY {spec.order_by}").fetchall()
    return [row_to_record(spec, row) for row in rows]


def get_curation_record(collection: str, record_id: str, path: str | None = None) -> dict[str, Any]:
    spec = spec_for(collection)
    if spec.get_fn is not None:
        return spec.get_fn(record_id, path or DEFAULT_DB_PATH)
    with connect(path or DEFAULT_DB_PATH) as connection:
        _ensure_schema(connection)
        row = connection.execute(f"SELECT * FROM {spec.table} WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        raise StudyDataError(f"{spec.title[:-1].lower()} not found")
    return row_to_record(spec, row)


def save_curation_record(
    collection: str,
    payload: dict[str, Any],
    path: str | None = None,
) -> dict[str, Any]:
    spec = spec_for(collection)
    record = normalized_record(spec, payload)
    resolved = path or DEFAULT_DB_PATH
    now = _timestamp()
    columns = [field.name for field in spec.fields]
    values = [value_for_db(record.get(field.name), field) for field in spec.fields]
    with connect(resolved) as connection:
        _ensure_schema(connection)
        existing = connection.execute(
            f"SELECT id FROM {spec.table} WHERE id = ?",
            (record["id"],),
        ).fetchone()
        if existing is None:
            placeholders = ", ".join(["?"] * len(columns))
            connection.execute(
                f"INSERT INTO {spec.table} ({', '.join(columns)}) VALUES ({placeholders})",
                values,
            )
        else:
            assignments = ", ".join(f"{column} = ?" for column in columns if column != "id")
            update_values = [values[index] for index, field in enumerate(spec.fields) if field.name != "id"]
            update_values.append(record["id"])
            connection.execute(
                f"UPDATE {spec.table} SET {assignments} WHERE id = ?",
                update_values,
            )
    saved = get_curation_record(collection, record["id"], path=resolved)
    saved.setdefault("created_at", now)
    saved.setdefault("updated_at", now)
    return saved


def delete_curation_record(collection: str, record_id: str, path: str | None = None) -> bool:
    spec = spec_for(collection)
    resolved = path or DEFAULT_DB_PATH
    with connect(resolved) as connection:
        _ensure_schema(connection)
        cursor = connection.execute(f"DELETE FROM {spec.table} WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            raise StudyDataError(f"{spec.title[:-1].lower()} not found")
    return True


def export_curation_bundle(path: str | None = None) -> dict[str, Any]:
    resolved = path or DEFAULT_DB_PATH
    return {
        "generated_at": _timestamp(),
        "collections": {
            key: list_curation_records(key, path=resolved) for key in CURATION_COLLECTIONS
        },
    }


def import_curation_bundle(payload: dict[str, Any], path: str | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StudyDataError("import payload must be a JSON object")
    collections = payload.get("collections")
    if not isinstance(collections, dict):
        raise StudyDataError("import payload must include a collections object")
    resolved = path or DEFAULT_DB_PATH
    imported: dict[str, int] = {}
    with connect(resolved) as connection:
        _ensure_schema(connection)
        for collection, records in collections.items():
            spec = spec_for(collection)
            if not isinstance(records, list):
                raise StudyDataError(f"{collection} must be a JSON array")
            connection.execute(f"DELETE FROM {spec.table}")
            imported[collection] = 0
            for record in records:
                if not isinstance(record, dict):
                    raise StudyDataError(f"{collection} records must be JSON objects")
                normalized = normalized_record(spec, record)
                columns = [field.name for field in spec.fields]
                values = [value_for_db(normalized.get(field.name), field) for field in spec.fields]
                placeholders = ", ".join(["?"] * len(columns))
                connection.execute(
                    f"INSERT INTO {spec.table} ({', '.join(columns)}) VALUES ({placeholders})",
                    values,
                )
                imported[collection] += 1
    return {"imported": imported}
