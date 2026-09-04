"""JSON file storage for generated BHF chapter commentary."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .models import ChapterCommentary, CommentaryStatus


def get_commentary_dir(base_dir: str | Path) -> Path:
    """Get the directory for storing commentary files."""
    path = Path(base_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_commentary_filename(book: str, chapter: int) -> str:
    """Get the filename for a chapter commentary."""
    return f"{_slugify(book)}_{chapter:03d}.json"


def save_commentary(
    commentary: ChapterCommentary,
    storage_dir: str | Path,
) -> Path:
    """Save commentary to JSON file."""
    storage_path = get_commentary_dir(storage_dir)
    filename = get_commentary_filename(commentary.book, commentary.chapter)
    filepath = storage_path / filename

    payload = json.dumps(commentary.to_dict(), indent=2)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=storage_path,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, filepath)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return filepath


def load_commentary(
    storage_dir: str | Path,
    book: str,
    chapter: int,
) -> ChapterCommentary | None:
    """Load commentary from JSON file."""
    storage_path = get_commentary_dir(storage_dir)
    filename = get_commentary_filename(book, chapter)
    filepath = storage_path / filename

    if not filepath.exists():
        return None

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return _from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def delete_commentary(
    storage_dir: str | Path,
    book: str,
    chapter: int,
) -> bool:
    """Delete a commentary file."""
    storage_path = get_commentary_dir(storage_dir)
    filename = get_commentary_filename(book, chapter)
    filepath = storage_path / filename

    if filepath.exists():
        filepath.unlink()
        return True
    return False


def list_commentaries(storage_dir: str | Path) -> list[tuple[str, int]]:
    """List all stored commentaries as (book, chapter) tuples."""
    storage_path = get_commentary_dir(storage_dir)
    result = []

    for filepath in sorted(storage_path.glob("*.json")):
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            book = data.get("book")
            chapter = data.get("chapter")
            if book and isinstance(chapter, int) and chapter > 0:
                result.append((book, chapter))
        except (json.JSONDecodeError, ValueError):
            pass

    return result


def _slugify(book: str) -> str:
    """Convert book name to slug for filename."""
    return book.lower().replace(" ", "_")


def _from_dict(data: dict[str, Any]) -> ChapterCommentary:
    """Reconstruct ChapterCommentary from dict."""
    from .models import CommentaryBlock, CommentarySection, GeneratedMetadata

    sections = []
    for section_data in data.get("sections", []):
        blocks = []
        for block_data in section_data.get("blocks", []):
            blocks.append(CommentaryBlock(**block_data))
        sections.append(
            CommentarySection(
                kind=section_data["kind"],
                title=section_data["title"],
                blocks=blocks,
            )
        )

    generated_metadata = None
    if data.get("generated_metadata"):
        generated_metadata = GeneratedMetadata(**data["generated_metadata"])

    return ChapterCommentary(
        reference=data["reference"],
        book=data["book"],
        chapter=int(data["chapter"]),
        status=data["status"],
        sections=sections,
        generated_metadata=generated_metadata,
        failure_reason=data.get("failure_reason"),
        validation_errors=data.get("validation_errors", []),
        validation_warnings=data.get("validation_warnings", []),
    )
