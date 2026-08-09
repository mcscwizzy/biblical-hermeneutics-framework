"""Bounded deterministic passage-to-archaeology evidence resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .bible import BibleError, normalize_book_name, resolve_passage
from .study_db import (
    DEFAULT_DB_PATH,
    list_archaeology_items,
    list_archaeology_sites,
)


DEFAULT_MAX_RESULTS = 8

_RELATIONSHIP_RANKS = {
    "direct": 400,
    "direct_context": 350,
    "textual_witness": 340,
    "historical_context": 250,
    "historical_setting": 240,
    "cultural_context": 220,
    "context": 200,
}


def resolve_archaeology_evidence(
    *,
    book: str,
    chapter: int | str,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    path: str | Path = DEFAULT_DB_PATH,
    limit: int = DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """Return a bounded evidence packet without generic keyword retrieval.

    Scripture links are the primary match.  Exact named-item/site mentions in
    supplied passage text are a secondary contextual match.  Generic terms
    such as ``king`` or ``city`` are never used as candidates.
    """

    canonical_book = normalize_book_name(book)
    chapter_number = int(chapter)
    has_verse_start = verse_start is not None and str(verse_start).strip()
    start = int(verse_start) if has_verse_start else 1
    # A chapter action means the whole chapter, not verse 1 only.
    end = int(verse_end) if verse_end is not None and str(verse_end).strip() else (start if has_verse_start else 9999)
    if end < start:
        raise ValueError("verse_end must be greater than or equal to verse_start")

    text = str(passage_text or "").strip()
    if not text:
        try:
            text = str(
                resolve_passage(canonical_book, chapter_number, verse_start, verse_end).get(
                    "selected_text", ""
                )
            )
        except BibleError:
            text = ""
    normalized_text = _normalize(text)

    sites = list_archaeology_sites(path=path)
    sites_by_id = {site["id"]: site for site in sites}
    items = list_archaeology_items(path=path)
    ranked: dict[str, tuple[int, str]] = {}
    links_by_item: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        links = item.get("scripture_links", [])
        links_by_item[item["id"]] = links
        relationship_rank = 0
        for link in links:
            if _overlaps_reference(link, canonical_book, chapter_number, start, end):
                relationship_rank = max(
                    relationship_rank,
                    _RELATIONSHIP_RANKS.get(str(link.get("relationship_type") or ""), 200),
                )
        if relationship_rank:
            ranked[item["id"]] = (relationship_rank, "scripture")

    # Text matching is deliberately limited to canonical item/site names.
    # This supports a user-provided passage excerpt without reintroducing the
    # map service's broad item-type/relationship keyword collisions.
    if normalized_text:
        for item in items:
            site = sites_by_id.get(item.get("site_id"), {})
            terms = [item.get("name", ""), site.get("name", "")]
            if any(_term_in_text(term, normalized_text) for term in terms if term):
                current = ranked.get(item["id"])
                if current is None or current[0] < 150:
                    ranked[item["id"]] = (150, "named_context")

    ordered_items = sorted(
        (item for item in items if item["id"] in ranked),
        key=lambda item: (
            -ranked[item["id"]][0],
            -int(item.get("confidence_rank") or 0),
            item["name"],
            item["id"],
        ),
    )[: max(1, min(int(limit), 25))]
    cards = [
        _evidence_card(
            item,
            sites_by_id.get(item.get("site_id"), {}),
            links_by_item.get(item["id"], []),
        )
        for item in ordered_items
    ]
    return {
        "reference": _format_reference(canonical_book, chapter_number, verse_start, verse_end),
        "archaeological_items": cards,
        "sites": [
            _site_summary(sites_by_id[item.get("site_id")])
            for item in ordered_items
            if item.get("site_id") in sites_by_id
        ],
        "claims": [],
        "cautions": _unique(caution for card in cards for caution in card["cautions"]),
        "citations": [card["source"] for card in cards if card.get("source")],
        "media_metadata": [media for card in cards for media in card.get("media", [])],
        "match_count": len(cards),
        "empty_state": not cards,
    }


def _evidence_card(item: dict[str, Any], site: dict[str, Any], links: list[dict[str, Any]]) -> dict[str, Any]:
    details = item.get("evidence_details") or {}
    if not isinstance(details, dict):
        details = {}
    description = str(details.get("description") or item.get("why_it_matters") or "")
    biblical_relevance = str(details.get("biblical_relevance") or item.get("why_it_matters") or "")
    caution = str(details.get("interpretive_caution") or item.get("bhf_caution") or "")
    scripture_references = [
        _format_reference(link["book"], link["chapter"], link["verse_start"], link["verse_end"])
        for link in links
    ]
    relationship = str(
        (links[0].get("relationship_type") if links else None)
        or item.get("relationship")
        or "historical_context"
    )
    external_references = _external_references(details.get("external_references"))
    return {
        "id": item["id"],
        "title": item["name"],
        "item_type": item.get("item_type", ""),
        "site_id": item.get("site_id", ""),
        "site_name": site.get("name", ""),
        "period": item.get("period", ""),
        "date_display": details.get("date_display") or item.get("period", ""),
        "description": description,
        "discovery_context": details.get("discovery_context", ""),
        "dating_basis": details.get("dating_basis", ""),
        "physical_description": details.get("physical_description", ""),
        "evidence_summary": details.get("evidence_summary", ""),
        "biblical_relevance": biblical_relevance,
        # Keep this legacy UI/API alias, but map it to passage relevance rather
        # than duplicating the evidence description.
        "significance": biblical_relevance,
        "scholarly_context": details.get("scholarly_context", ""),
        "interpretive_caution": caution,
        "discovery_year": details.get("discovery_year", ""),
        "current_location": details.get("current_location", ""),
        "biblical_relationship": relationship,
        "scripture_references": scripture_references,
        "related_places": [site.get("modern_location", ""), site.get("ancient_region", "")],
        "related_events": [],
        "related_ckl_objects": [],
        "coordinates": {
            "latitude": site.get("latitude"),
            "longitude": site.get("longitude"),
        },
        "confidence": item.get("confidence", "unknown"),
        "dispute_status": details.get("dispute_status") or (
            "archaeological_uncertainty" if caution else "not_disputed"
        ),
        "cautions": [caution] if caution else [],
        "evidence_sources": external_references,
        "source": item.get("source") or {
            "id": item.get("source_id", ""),
            "label": item.get("source_name", ""),
            "url": item.get("source_url", ""),
            "license": item.get("license", ""),
        },
        "media": item.get("media", []),
    }


def _external_references(value: Any) -> list[dict[str, str]]:
    """Return only display-safe reviewed evidence reference metadata."""

    if not isinstance(value, list):
        return []
    references: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url") or "").strip()
        if not url.startswith(("https://", "http://")):
            continue
        references.append(
            {
                "label": str(entry.get("label") or "External evidence record").strip(),
                "url": url,
                "license": str(entry.get("license") or "").strip(),
                "record_id": str(entry.get("record_id") or "").strip(),
            }
        )
    return references


def _site_summary(site: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": site.get("id", ""),
        "name": site.get("name", ""),
        "latitude": site.get("latitude"),
        "longitude": site.get("longitude"),
        "modern_location": site.get("modern_location", ""),
    }


def _overlaps_reference(link: dict[str, Any], book: str, chapter: int, start: int, end: int) -> bool:
    try:
        return (
            normalize_book_name(str(link.get("book") or "")) == book
            and int(link.get("chapter")) == chapter
            and int(link.get("verse_start")) <= end
            and int(link.get("verse_end")) >= start
        )
    except (TypeError, ValueError, BibleError):
        return False


def _term_in_text(term: str, normalized_text: str) -> bool:
    normalized_term = _normalize(term)
    return bool(normalized_term and f" {normalized_term} " in f" {normalized_text} ")


def _normalize(value: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in value).split())


def _format_reference(book: str, chapter: int, verse_start: int | str | None, verse_end: int | str | None) -> str:
    reference = f"{book} {chapter}"
    if verse_start is None or str(verse_start).strip() == "":
        return reference
    start = str(verse_start)
    end = str(verse_end if verse_end is not None else verse_start)
    return f"{reference}:{start}" if start == end else f"{reference}:{start}-{end}"


def _unique(values: Any) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
