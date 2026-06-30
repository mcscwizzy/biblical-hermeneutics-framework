"""Repositories for saved map studies and map note persistence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from ..common import DEFAULT_DB_PATH, StudyDataError, reference_filter, timestamp
from ..connection import connect


EnsureSchema = Callable[[Any], None]
MapStudyValidator = Callable[[dict[str, Any]], dict[str, Any]]
MapNoteValidator = Callable[[dict[str, Any]], dict[str, Any]]


def list_saved_map_studies(
    book: str | None = None,
    chapter: int | str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> list[dict[str, Any]]:
    with connect(path) as connection:
        ensure_schema(connection)
        if book is None and chapter is None:
            rows = connection.execute(
                "SELECT * FROM saved_map_studies ORDER BY created_at DESC"
            ).fetchall()
        else:
            canonical, chapter_number = reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM saved_map_studies
                WHERE book = ? AND chapter = ?
                ORDER BY created_at DESC
                """,
                (canonical, chapter_number),
            ).fetchall()
    studies = [saved_map_study_from_row(row) for row in rows]
    for study in studies:
        study["map_notes"] = map_notes_for_ids(
            place_id=study["selected_place_id"],
            route_id=study["selected_route_id"],
            layer_id=study["selected_layer_id"],
            archaeology_id=study["selected_archaeology_id"],
            manuscript_id=study["selected_manuscript_id"],
            path=path,
            ensure_schema=ensure_schema,
        )
    return studies


def get_saved_map_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM saved_map_studies WHERE id = ?",
            (study_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("saved map study not found")
    study = saved_map_study_from_row(row)
    study["map_notes"] = map_notes_for_ids(
        place_id=study["selected_place_id"],
        route_id=study["selected_route_id"],
        layer_id=study["selected_layer_id"],
        archaeology_id=study["selected_archaeology_id"],
        manuscript_id=study["selected_manuscript_id"],
        path=path,
        ensure_schema=ensure_schema,
    )
    return study


def create_saved_map_study(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    validate_saved_map_study: MapStudyValidator,
) -> dict[str, Any]:
    study = validate_saved_map_study(data)
    now = timestamp()
    study_id = uuid.uuid4().hex
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO saved_map_studies (
                id, book, chapter, verse_start, verse_end, passage_reference,
                selected_place_id, selected_route_id, selected_layer_id,
                archaeology_id, manuscript_id,
                selected_layers, map_view_state, generated_summary, user_notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                study_id,
                study["book"],
                study["chapter"],
                study["start_verse"],
                study["end_verse"],
                study["passage_reference"],
                study["selected_place_id"],
                study["selected_route_id"],
                study["selected_layer_id"],
                study["selected_archaeology_id"],
                study["selected_manuscript_id"],
                json.dumps(study["selected_layers"]),
                json.dumps(study["map_view_state"]),
                study["generated_summary"],
                study["user_notes"],
                now,
                now,
            ),
        )
    return {
        **study,
        "id": study_id,
        "created_at": now,
        "updated_at": now,
    }


def delete_saved_map_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> bool:
    with connect(path) as connection:
        ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM saved_map_studies WHERE id = ?",
            (study_id,),
        )
        if cursor.rowcount == 0:
            raise StudyDataError("saved map study not found")
    return True


def create_map_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
    validate_map_note: MapNoteValidator,
) -> dict[str, Any]:
    note = validate_map_note(data)
    now = timestamp()
    note_id = uuid.uuid4().hex
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


def saved_map_study_from_row(row: Any) -> dict[str, Any]:
    selected_layers = _json_list(row["selected_layers"])
    map_view_state = _json_dict(row["map_view_state"])
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "passage_reference": row["passage_reference"],
        "selected_place_id": row["selected_place_id"],
        "selected_route_id": row["selected_route_id"],
        "selected_layer_id": row["selected_layer_id"],
        "selected_archaeology_id": row["archaeology_id"],
        "selected_manuscript_id": row["manuscript_id"],
        "selected_layers": [str(value) for value in selected_layers if str(value).strip()],
        "map_view_state": map_view_state,
        "generated_summary": row["generated_summary"],
        "user_notes": row["user_notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


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


def _json_dict(value: Any) -> dict[str, Any]:
    try:
        decoded = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _json_list(value: Any) -> list[Any]:
    try:
        decoded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []
