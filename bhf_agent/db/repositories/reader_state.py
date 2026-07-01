"""Repositories for notes, highlights, saved studies, and reader actions."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable

from ..common import (
    DEFAULT_DB_PATH,
    StudyDataError,
    highlight_from_row,
    note_from_row,
    reference_filter,
    saved_study_from_row,
    timestamp,
    validated_highlight,
    validated_note,
    validated_reference,
    validated_saved_study,
)
from ..connection import connect


EnsureSchema = Callable[[Any], None]


def initialize_database(
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> None:
    with connect(path) as connection:
        ensure_schema(connection)


def list_notes(
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
                "SELECT * FROM notes ORDER BY book, chapter, verse_start, created_at"
            ).fetchall()
        else:
            canonical, chapter_number = reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM notes
                WHERE book = ? AND chapter = ?
                ORDER BY verse_start, verse_end, created_at
                """,
                (canonical, chapter_number),
            ).fetchall()
    return [note_from_row(row) for row in rows]


def create_note(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    note = validated_note(data)
    now = timestamp()
    note_id = uuid.uuid4().hex
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO notes (
                id, book, chapter, verse_start, verse_end, selected_text,
                note_body, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                note["book"],
                note["chapter"],
                note["start_verse"],
                note["end_verse"],
                note["selected_text"],
                note["body"],
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


def update_note(
    note_id: str,
    updates: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        current_row = connection.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
        if current_row is None:
            raise StudyDataError("note not found")

        current = note_from_row(current_row)
        merged = {**current, **updates}
        if "note_body" in updates and "body" not in updates:
            merged["body"] = updates["note_body"]
        if "verse_start" in updates and "start_verse" not in updates:
            merged["start_verse"] = updates["verse_start"]
        if "verse_end" in updates and "end_verse" not in updates:
            merged["end_verse"] = updates["verse_end"]
        note = validated_note(merged)
        updated_at = timestamp()
        connection.execute(
            """
            UPDATE notes
            SET book = ?, chapter = ?, verse_start = ?, verse_end = ?,
                selected_text = ?, note_body = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                note["book"],
                note["chapter"],
                note["start_verse"],
                note["end_verse"],
                note["selected_text"],
                note["body"],
                updated_at,
                note_id,
            ),
        )
        row = connection.execute(
            "SELECT * FROM notes WHERE id = ?",
            (note_id,),
        ).fetchone()
    return note_from_row(row)


def delete_note(
    note_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> bool:
    with connect(path) as connection:
        ensure_schema(connection)
        cursor = connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cursor.rowcount == 0:
            raise StudyDataError("note not found")
    return True


def list_highlights(
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
                "SELECT * FROM highlights ORDER BY book, chapter, verse_start, created_at"
            ).fetchall()
        else:
            canonical, chapter_number = reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM highlights
                WHERE book = ? AND chapter = ?
                ORDER BY verse_start, verse_end, created_at
                """,
                (canonical, chapter_number),
            ).fetchall()
    return [highlight_from_row(row) for row in rows]


def create_highlight(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    highlight = validated_highlight(data)
    now = timestamp()
    highlight_id = uuid.uuid4().hex
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO highlights (
                id, book, chapter, verse_start, verse_end, selected_text,
                color, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                highlight_id,
                highlight["book"],
                highlight["chapter"],
                highlight["start_verse"],
                highlight["end_verse"],
                highlight["selected_text"],
                highlight["color"],
                now,
                now,
            ),
        )
    return {
        **highlight,
        "id": highlight_id,
        "created_at": now,
        "updated_at": now,
    }


def delete_highlight(
    highlight_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> bool:
    with connect(path) as connection:
        ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM highlights WHERE id = ?",
            (highlight_id,),
        )
        if cursor.rowcount == 0:
            raise StudyDataError("highlight not found")
    return True


def list_saved_studies(
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
                "SELECT * FROM saved_studies ORDER BY created_at DESC"
            ).fetchall()
        else:
            canonical, chapter_number = reference_filter(book, chapter)
            rows = connection.execute(
                """
                SELECT * FROM saved_studies
                WHERE book = ? AND chapter = ?
                ORDER BY created_at DESC
                """,
                (canonical, chapter_number),
            ).fetchall()
    return [saved_study_from_row(row) for row in rows]


def get_saved_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    with connect(path) as connection:
        ensure_schema(connection)
        row = connection.execute(
            "SELECT * FROM saved_studies WHERE id = ?",
            (study_id,),
        ).fetchone()
    if row is None:
        raise StudyDataError("saved study not found")
    return saved_study_from_row(row)


def create_saved_study(
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    study = validated_saved_study(data)
    now = timestamp()
    study_id = uuid.uuid4().hex
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO saved_studies (
                id, title, book, chapter, verse_start, verse_end, selected_text,
                study_type, question, answer, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                study_id,
                study["title"],
                study["book"],
                study["chapter"],
                study["start_verse"],
                study["end_verse"],
                study["selected_text"],
                study["study_type"],
                study["question"],
                study["answer"],
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


def delete_saved_study(
    study_id: str,
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> bool:
    with connect(path) as connection:
        ensure_schema(connection)
        cursor = connection.execute(
            "DELETE FROM saved_studies WHERE id = ?",
            (study_id,),
        )
        if cursor.rowcount == 0:
            raise StudyDataError("saved study not found")
    return True


def record_study_action(
    action_type: str,
    data: dict[str, Any],
    path: str | Path = DEFAULT_DB_PATH,
    *,
    ensure_schema: EnsureSchema,
) -> dict[str, Any]:
    reference = validated_reference(data)
    now = timestamp()
    action_id = uuid.uuid4().hex
    action = {
        "id": action_id,
        "action_type": str(action_type).strip(),
        **reference,
        "created_at": now,
    }
    if not action["action_type"]:
        raise StudyDataError("action_type is required")
    with connect(path) as connection:
        ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO study_actions (
                id, action_type, book, chapter, verse_start, verse_end,
                selected_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action["id"],
                action["action_type"],
                action["book"],
                action["chapter"],
                action["start_verse"],
                action["end_verse"],
                action["selected_text"],
                action["created_at"],
            ),
        )
    return action
