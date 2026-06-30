"""Shared constants and data-shaping helpers for study-db repositories."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..bible import BibleError, normalize_book_name


DEFAULT_DB_PATH = Path(".bhf") / "study.sqlite"
HIGHLIGHT_COLORS = {"yellow", "green", "blue", "pink"}
DEFAULT_HIGHLIGHT_COLOR = "yellow"


class StudyDataError(ValueError):
    """Raised when study data input or storage cannot be resolved."""


def positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StudyDataError(f"{label} must be a positive integer") from exc
    if number <= 0:
        raise StudyDataError(f"{label} must be a positive integer")
    return number


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_saved_study_title(
    book: str,
    chapter: int,
    start_verse: int,
    end_verse: int,
    study_type: str,
) -> str:
    reference = f"{book} {chapter}"
    if start_verse:
        suffix = str(start_verse) if start_verse == end_verse else f"{start_verse}-{end_verse}"
        reference = f"{reference}:{suffix}"
    label = study_type.replace("_", " ").strip().title()
    return f"{reference} - {label}"


def validated_reference(data: dict[str, Any]) -> dict[str, Any]:
    try:
        book = normalize_book_name(str(data.get("book", "")))
    except BibleError as exc:
        raise StudyDataError(str(exc)) from exc
    chapter = positive_int(data.get("chapter"), "chapter")
    start_verse = positive_int(
        data.get("start_verse") or data.get("verse_start"),
        "start_verse",
    )
    end_verse = positive_int(
        data.get("end_verse") or data.get("verse_end") or start_verse,
        "end_verse",
    )
    if end_verse < start_verse:
        raise StudyDataError("end_verse must be greater than or equal to start_verse")
    return {
        "book": book,
        "chapter": chapter,
        "start_verse": start_verse,
        "end_verse": end_verse,
        "selected_text": str(data.get("selected_text") or "").strip(),
    }


def validated_note(data: dict[str, Any]) -> dict[str, Any]:
    reference = validated_reference(data)
    body = str(data.get("body") or data.get("note_body") or "").strip()
    if not body:
        raise StudyDataError("note body is required")
    return {
        **reference,
        "body": body,
    }


def validated_highlight(data: dict[str, Any]) -> dict[str, Any]:
    reference = validated_reference(data)
    color = str(data.get("color") or DEFAULT_HIGHLIGHT_COLOR).strip().lower()
    if color not in HIGHLIGHT_COLORS:
        raise StudyDataError(
            "highlight color must be one of: " + ", ".join(sorted(HIGHLIGHT_COLORS))
        )
    return {
        **reference,
        "color": color,
    }


def validated_saved_study(data: dict[str, Any]) -> dict[str, Any]:
    reference = validated_reference(data)
    study_type = str(
        data.get("study_type") or data.get("ask_mode") or data.get("type") or ""
    ).strip()
    if not study_type:
        raise StudyDataError("study_type is required")
    question = str(data.get("question") or "").strip()
    if not question:
        raise StudyDataError("question is required")
    answer = str(data.get("answer") or data.get("answer_html") or "").strip()
    if not answer:
        raise StudyDataError("answer is required")
    title = str(data.get("title") or "").strip()
    if not title:
        title = default_saved_study_title(
            reference["book"],
            reference["chapter"],
            reference["start_verse"],
            reference["end_verse"],
            study_type,
        )
    return {
        **reference,
        "study_type": study_type,
        "question": question,
        "answer": answer,
        "title": title,
    }


def reference_filter(
    book: str | None,
    chapter: int | str | None,
) -> tuple[str, int]:
    if book is None or chapter is None:
        raise StudyDataError("book and chapter are both required when filtering study data")
    try:
        canonical = normalize_book_name(str(book))
    except BibleError as exc:
        raise StudyDataError(str(exc)) from exc
    return canonical, positive_int(chapter, "chapter")


def note_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "selected_text": row["selected_text"],
        "body": row["note_body"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def highlight_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "selected_text": row["selected_text"],
        "color": row["color"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def saved_study_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "book": row["book"],
        "chapter": int(row["chapter"]),
        "start_verse": int(row["verse_start"]),
        "end_verse": int(row["verse_end"]),
        "selected_text": row["selected_text"],
        "study_type": row["study_type"],
        "question": row["question"],
        "answer": row["answer"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

