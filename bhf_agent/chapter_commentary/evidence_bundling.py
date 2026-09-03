"""Bundle relevant BHF evidence for a canonical chapter."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from bhf_agent import bible
from bhf_agent.presentation.models import EvidenceBundle


def get_chapter_evidence_bundle(
    book: str,
    chapter: int,
) -> EvidenceBundle | None:
    """Retrieve evidence bundle for a canonical chapter.

    Currently returns a minimal structure. Real implementation would
    integrate with CKL/evidence retrieval systems.
    """
    try:
        chapter_data = bible.resolve_chapter(book, chapter)
    except bible.BibleError:
        return None

    reference = bible.verse_range_reference(book, chapter)
    chapter_text = bible.passage_text(chapter_data.get("verses", []))
    evidence_hash = _hash_chapter_evidence(book, chapter, chapter_text)

    bundle = EvidenceBundle(
        passage_ref=reference,
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=[],
        geography={},
        provenance={},
    )

    # Set the hash directly on the frozen dataclass replacement
    return EvidenceBundle(
        passage_ref=bundle.passage_ref,
        entities=bundle.entities,
        evidence_items=bundle.evidence_items,
        geography=bundle.geography,
        provenance=bundle.provenance,
        evidence_hash=evidence_hash,
    )


def _hash_chapter_evidence(book: str, chapter: int, chapter_text: str) -> str:
    """Deterministic hash of chapter evidence state."""
    payload = {
        "book": book,
        "chapter": chapter,
        "text_length": len(chapter_text),
        "schema_version": "1.0",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
