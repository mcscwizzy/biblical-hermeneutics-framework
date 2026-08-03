"""Repository for map note persistence."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Callable

from ..common import DEFAULT_DB_PATH, timestamp
from ..connection import connect


EnsureSchema = Callable[[Any], None]
MapNoteValidator = Callable[[dict[str, Any]], dict[str, Any]]


def create_map_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    validate_map_note: MapNoteValidator,
) -> dict[str, Any]:
    note = validate_map_note(data)
    now = timestamp()
    note_id = _client_record_id(data.get("id"), "map-note") or uuid.uuid4().hex
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO map_notes (
                id, book, chapter, verse_start, verse_end, passage_reference,
                place_id, route_id, layer_id, archaeology_id, manuscript_id,
                note_body, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                note["book"],
                note["chapter"],
                note["start_verse"],
                note["end_verse"],
                note["passage_reference"],
                note["place_id"],
                note["route_id"],
                note["layer_id"],
                note["archaeology_id"],
                note["manuscript_id"],
                note["note_body"],
                now,
                now,
            ),
        )
    return {
        **note,
        "id": note_id,
        "created_at": now,
        "updated_at": now,
    }


def _client_record_id(value: object, prefix: str) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    if re.fullmatch(r"[a-f0-9]{32}", candidate):
        return candidate
    if re.fullmatch(rf"{re.escape(prefix)}-[A-Za-z0-9][A-Za-z0-9_-]{{0,79}}", candidate):
        return candidate
    return None


def list_map_notes(
    place_id: str | None = None,
    route_id: str | None = None,
    layer_id: str | None = None,
    archaeology_id: str | None = None,
    manuscript_id: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        clauses: list[str] = []
        params: list[Any] = []
        if place_id is not None:
            clauses.append("place_id = ?")
            params.append(place_id)
        if route_id is not None:
            clauses.append("route_id = ?")
            params.append(route_id)
        if layer_id is not None:
            clauses.append("layer_id = ?")
            params.append(layer_id)
        if archaeology_id is not None:
            clauses.append("archaeology_id = ?")
            params.append(archaeology_id)
        if manuscript_id is not None:
            clauses.append("manuscript_id = ?")
            params.append(manuscript_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            f"SELECT * FROM map_notes {where} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [map_note_from_row(row) for row in rows]


def map_note_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "passage_reference": row["passage_reference"],
        "place_id": row["place_id"],
        "route_id": row["route_id"],
        "layer_id": row["layer_id"],
        "archaeology_id": row["archaeology_id"],
        "manuscript_id": row["manuscript_id"],
        "note_body": row["note_body"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def map_notes_for_ids(
    *,
    place_id: str = "",
    route_id: str = "",
    layer_id: str = "",
    archaeology_id: str = "",
    manuscript_id: str = "",
    path: str | Path = DEFAULT_DB_PATH,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    if place_id:
        notes.extend(list_map_notes(place_id=place_id, path=path, ensure_schema=ensure_schema))
    if route_id:
        notes.extend(list_map_notes(route_id=route_id, path=path, ensure_schema=ensure_schema))
    if layer_id:
        notes.extend(list_map_notes(layer_id=layer_id, path=path, ensure_schema=ensure_schema))
    if archaeology_id:
        notes.extend(
            list_map_notes(
                archaeology_id=archaeology_id,
                path=path,
                ensure_schema=ensure_schema,
            )
        )
    if manuscript_id:
        notes.extend(
            list_map_notes(
                manuscript_id=manuscript_id,
                path=path,
                ensure_schema=ensure_schema,
            )
        )
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for note in notes:
        note_id = note["id"]
        if note_id in seen:
            continue
        seen.add(note_id)
        unique.append(note)
    return unique
