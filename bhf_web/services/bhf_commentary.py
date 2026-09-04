"""Read-only presentation projection for the released BHF commentary corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhf_agent.chapter_commentary.models import ChapterCommentary
from bhf_agent.presentation.models import EvidenceBundle
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.storage import list_commentaries
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle


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


def search_commentary(
    storage_dir: str | Path,
    *,
    query: str = "",
    availability: str | None = None,
    book: str | None = None,
    chapter: int | None = None,
    verse: str | None = None,
    category: str | None = None,
    entity: str | None = None,
    period: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search the immutable commentary projections without a second index."""
    normalized_query = " ".join(str(query or "").casefold().split())
    normalized_book = " ".join(str(book or "").casefold().split())
    normalized_availability = str(availability or "").strip().upper()
    if normalized_availability and normalized_availability not in {"AVAILABLE", "THIN", "DATA_GAP"}:
        raise ValueError("availability must be AVAILABLE, THIN, or DATA_GAP")
    normalized_verse = " ".join(str(verse or "").casefold().split())
    normalized_category = " ".join(str(category or "").casefold().split())
    normalized_entity = " ".join(str(entity or "").casefold().split())
    normalized_period = " ".join(str(period or "").casefold().split())
    results: list[dict[str, Any]] = []
    for candidate_book, candidate_chapter in sorted(list_commentaries(storage_dir), key=lambda item: (item[0].casefold(), item[1])):
        if normalized_book and candidate_book.casefold() != normalized_book:
            continue
        if chapter is not None and candidate_chapter != chapter:
            continue
        commentary = load_commentary(storage_dir, candidate_book, candidate_chapter)
        if commentary is None:
            continue
        projection = project_commentary(commentary)
        if normalized_availability and projection.get("availability") != normalized_availability:
            continue
        verse_references = [str(value) for value in projection["verse_references"]]
        section_text = " ".join(
            f"{section.kind} {section.title}" for section in commentary.sections
        )
        searchable = " ".join(
            [projection["book"], str(projection["chapter"]), projection["commentary"], *verse_references, section_text]
        ).casefold()
        if normalized_query and normalized_query not in searchable:
            continue
        if normalized_verse and not any(normalized_verse in reference.casefold() for reference in verse_references):
            continue
        cited_ids = {evidence_id for section in commentary.sections for block in section.blocks for evidence_id in block.evidence_ids}
        evidence_categories: list[str] = []
        entity_terms: list[str] = []
        period_terms: list[str] = []
        if normalized_category or normalized_entity or normalized_period:
            bundle = get_chapter_evidence_bundle(candidate_book, candidate_chapter)
            if bundle is None:
                continue
            cited_items = [bundle.evidence_by_id[evidence_id] for evidence_id in cited_ids if evidence_id in bundle.evidence_by_id]
            evidence_categories = sorted({str(item.category).casefold() for item in cited_items if item.category})
            for item in cited_items:
                for entity_id in item.related_entity_ids:
                    entity_ref = bundle.entities_by_id.get(entity_id)
                    if entity_ref is not None:
                        entity_terms.append(f"{entity_ref.title} {entity_ref.id}")
                period_terms.extend(
                    str(value) for key, value in item.relevance_metadata.items()
                    if "time" in str(key).casefold() or "date" in str(key).casefold() or "period" in str(key).casefold()
                )
            if normalized_category and normalized_category not in evidence_categories:
                continue
            if normalized_entity and normalized_entity not in " ".join(entity_terms).casefold():
                continue
            if normalized_period and normalized_period not in " ".join(period_terms).casefold():
                continue
        result = dict(projection)
        result["commentary"] = projection["commentary"][:240]
        result["section_kinds"] = _unique([section.kind for section in commentary.sections])
        result["evidence_categories"] = evidence_categories
        results.append(result)
        if len(results) >= max(1, min(int(limit), 100)):
            break
    return {"release": COMMENTARY_RELEASE, "count": len(results), "results": results}


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
