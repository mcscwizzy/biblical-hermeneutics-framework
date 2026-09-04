"""Read-only presentation projection for the released BHF commentary corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhf_agent.chapter_commentary.models import ChapterCommentary
from bhf_agent.presentation.models import EvidenceBundle
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


def project_commentary_evidence(
    commentary: ChapterCommentary,
    bundle: EvidenceBundle,
) -> dict[str, Any]:
    """Project only the evidence IDs cited by a frozen commentary artifact.

    The browser must never receive a substitute search result when a stored
    citation is unavailable. Unknown citations are reported explicitly so the
    evidence explorer remains honest without exposing the whole CKL bundle.
    """
    cited_ids = _unique(
        [evidence_id for section in commentary.sections for block in section.blocks for evidence_id in block.evidence_ids]
    )
    sources = {
        str(source.get("id") or ""): source
        for source in bundle.provenance.get("sources", [])
        if isinstance(source, dict) and str(source.get("id") or "")
    }
    entities = bundle.entities_by_id
    items: list[dict[str, Any]] = []
    unavailable_ids: list[str] = []
    for evidence_id in cited_ids:
        item = bundle.evidence_by_id.get(evidence_id)
        if item is None:
            unavailable_ids.append(evidence_id)
            continue
        metadata = item.relevance_metadata or {}
        items.append(
            {
                "id": item.id,
                "claim": item.claim,
                "category": item.category,
                "confidence": item.confidence,
                "scripture_anchors": list(item.passage_anchors),
                "dispute_status": str(metadata.get("dispute_status") or "") or None,
                "assertion_type": str(metadata.get("assertion_type") or "") or None,
                "interpretation_levels": list(metadata.get("allowed_interpretation_levels") or []),
                "source_ids": list(item.source_ids),
                "sources": [
                    {
                        "id": source_id,
                        "title": str(sources.get(source_id, {}).get("title") or source_id),
                        "source_type": str(sources.get(source_id, {}).get("source_type") or ""),
                    }
                    for source_id in item.source_ids
                ],
                "related_entities": [
                    {
                        "id": entity_id,
                        "title": entities[entity_id].title,
                        "type": entities[entity_id].type,
                    }
                    for entity_id in item.related_entity_ids
                    if entity_id in entities
                ],
            }
        )
    return {
        "release": COMMENTARY_RELEASE,
        "book": commentary.book,
        "chapter": commentary.chapter,
        "availability": commentary.evidence_availability,
        "evidence_items": items,
        "unavailable_ids": unavailable_ids,
        "evidence_count": len(cited_ids),
    }
