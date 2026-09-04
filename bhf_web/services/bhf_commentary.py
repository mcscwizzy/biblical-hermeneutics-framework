"""Read-only presentation projection for the released BHF commentary corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhf_agent.chapter_commentary.models import ChapterCommentary
from bhf_agent.chapter_commentary.storage import load_commentary


COMMENTARY_RELEASE = "commentary-v1.0"


def _unique(values: list[str]) -> list[str]:
    """Return non-empty values in first-seen order."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def project_commentary(commentary: ChapterCommentary) -> dict[str, Any]:
    """Project stored commentary into the stable, UI-facing read model.

    Storage and generation metadata intentionally remain private to the
    application. The UI receives only the prose and navigation metadata it
    needs to render the context card.
    """
    blocks = [block for section in commentary.sections for block in section.blocks]
    text = "\n\n".join(
        block.text.strip()
        for block in blocks
        if isinstance(block.text, str) and block.text.strip()
    )
    verse_references = _unique(
        [verse_ref for block in blocks for verse_ref in block.verse_refs]
    )
    evidence_ids = _unique(
        [evidence_id for block in blocks for evidence_id in block.evidence_ids]
    )
    return {
        "release": COMMENTARY_RELEASE,
        "book": commentary.book,
        "chapter": commentary.chapter,
        # Preserve null for legacy artifacts whose availability was not
        # recorded. The presentation layer must never infer it.
        "availability": commentary.evidence_availability,
        "commentary": text,
        "verse_references": verse_references,
        "evidence_count": len(evidence_ids),
    }


def load_commentary_projection(
    storage_dir: str | Path,
    book: str,
    chapter: int,
) -> dict[str, Any] | None:
    """Load one immutable corpus artifact and return its UI projection."""
    commentary = load_commentary(storage_dir, book, chapter)
    return project_commentary(commentary) if commentary is not None else None
