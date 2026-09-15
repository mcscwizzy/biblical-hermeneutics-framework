"""Atomic storage for versioned compiled chapter synthesis JSON."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from bhf_agent.chapter_commentary.storage import get_commentary_filename

from .models import CompiledChapterSynthesis, SynthesisCoverage, SynthesisGap, SynthesisUnit


def save_synthesis(synthesis: CompiledChapterSynthesis, storage_dir: str | Path) -> Path:
    directory = Path(storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / get_commentary_filename(synthesis.book, synthesis.chapter)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(synthesis.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path


def load_synthesis(
    storage_dir: str | Path, book: str, chapter: int
) -> CompiledChapterSynthesis | None:
    path = Path(storage_dir) / get_commentary_filename(book, chapter)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _from_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _from_dict(data: dict[str, Any]) -> CompiledChapterSynthesis:
    return CompiledChapterSynthesis(
        reference=data["reference"],
        book=data["book"],
        chapter=int(data["chapter"]),
        evidence_hash=data["evidence_hash"],
        evidence_bundle_version=data["evidence_bundle_version"],
        synthesis_schema_version=data["synthesis_schema_version"],
        synthesis_compiler_version=data["synthesis_compiler_version"],
        synthesis_hash=data["synthesis_hash"],
        evidence_availability=data["evidence_availability"],
        synthesis_units=[SynthesisUnit(**unit) for unit in data.get("synthesis_units", [])],
        evidence_gaps=[SynthesisGap(**gap) for gap in data.get("evidence_gaps", [])],
        coverage=SynthesisCoverage(**data["coverage"]),
    )
