"""Map data access helpers for the BHF map panel."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bhf_agent.bible import BibleError, normalize_book_name, resolve_passage
from bhf_agent.study_db import (
    list_archaeology_items,
    list_archaeology_sites,
    list_archaeology_scripture_links,
    list_biblical_places,
    list_historical_layers,
    list_map_routes,
    list_place_references,
    list_route_references,
)


def get_biblical_place_markers(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return places from the local SQLite data store in map-marker shape."""

    places = list_biblical_places(path=path) if path else list_biblical_places()
    markers: list[dict[str, Any]] = []
    for place in places:
        markers.append(_place_to_marker(place, path=path))
    return markers


def resolve_places_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve curated places from a passage using deterministic matching only."""

    places = list_biblical_places(path=path) if path else list_biblical_places()
    if passage_text and passage_text.strip():
        text_source = passage_text
    elif book is not None and chapter is not None:
        passage = resolve_passage(book, chapter, verse_start, verse_end)
        text_source = passage["selected_text"]
    else:
        text_source = ""

    normalized_text = _normalize_for_match(text_source)
    matched_places: list[dict[str, Any]] = []
    matched_terms: dict[str, list[str]] = {}

    for place in places:
        candidate_terms = [place["name"], *place.get("aliases", [])]
        matches = [term for term in candidate_terms if _term_in_text(term, normalized_text)]
        if matches:
            matched_places.append(place)
            matched_terms[place["id"]] = _unique_terms(matches)

    if not matched_places and book is not None and chapter is not None:
        matched_places, matched_terms = _resolve_from_reference(
            places=places,
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            path=path,
        )

    markers = [_place_to_marker(place, path=path) for place in matched_places]
    return {
        "reference": _format_reference(book, chapter, verse_start, verse_end),
        "passage_text": text_source,
        "markers": markers,
        "matched_place_ids": [place["id"] for place in matched_places],
        "matched_terms": matched_terms,
        "match_count": len(markers),
        "empty_state": len(markers) == 0,
    }


def get_map_routes_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve curated routes from a passage using deterministic matching only."""

    routes = list_map_routes(path=path) if path else list_map_routes()
    if passage_text and passage_text.strip():
        text_source = passage_text
    elif book is not None and chapter is not None:
        passage = resolve_passage(book, chapter, verse_start, verse_end)
        text_source = passage["selected_text"]
    else:
        text_source = ""

    normalized_text = _normalize_for_match(text_source)
    matched_routes: list[dict[str, Any]] = []
    matched_terms: dict[str, list[str]] = {}

    for route in routes:
        candidate_terms = [route["name"], route.get("description", ""), route.get("period", "")]
        matches = [term for term in candidate_terms if _term_in_text(term, normalized_text)]
        if matches:
            matched_routes.append(route)
            matched_terms[route["id"]] = _unique_terms(matches)

    if not matched_routes and book is not None and chapter is not None:
        matched_routes, matched_terms = _resolve_routes_from_reference(
            routes=routes,
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            path=path,
        )

    route_items = [_route_to_item(route, path=path) for route in matched_routes]
    return {
        "reference": _format_reference(book, chapter, verse_start, verse_end),
        "passage_text": text_source,
        "routes": route_items,
        "matched_route_ids": [route["id"] for route in matched_routes],
        "matched_terms": matched_terms,
        "match_count": len(route_items),
        "empty_state": len(route_items) == 0,
    }


def get_historical_layers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    layers = list_historical_layers(period=period, path=path) if path else list_historical_layers(period=period)
    return [_historical_layer_to_item(layer) for layer in layers]


def get_archaeology_markers(path: str | Path | None = None) -> list[dict[str, Any]]:
    sites = list_archaeology_sites(path=path) if path else list_archaeology_sites()
    markers: list[dict[str, Any]] = []
    for site in sites:
        markers.extend(_archaeology_site_to_markers(site, path=path))
    return markers


def resolve_archaeology_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    sites = list_archaeology_sites(path=path) if path else list_archaeology_sites()
    if passage_text and passage_text.strip():
        text_source = passage_text
    elif book is not None and chapter is not None:
        try:
            passage = resolve_passage(book, chapter, verse_start, verse_end)
        except BibleError:
            passage = {"selected_text": ""}
        text_source = passage.get("selected_text", "")
    else:
        text_source = ""

    normalized_text = _normalize_for_match(text_source)
    matched_sites: list[dict[str, Any]] = []
    matched_terms: dict[str, list[str]] = {}

    for site in sites:
        for marker in _archaeology_site_to_markers(site, path=path):
            candidate_terms = [
                marker["name"],
                marker.get("site_name", ""),
                marker.get("site_type", ""),
                marker.get("item_type", ""),
                marker.get("relationship", ""),
            ]
            matches = [term for term in candidate_terms if _term_in_text(term, normalized_text)]
            if matches:
                matched_sites.append(marker)
                matched_terms[marker["id"]] = _unique_terms(matches)

    if not matched_sites and book is not None and chapter is not None:
        matched_sites, matched_terms = _resolve_archaeology_from_reference(
            sites=sites,
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            path=path,
        )

    return {
        "reference": _format_reference(book, chapter, verse_start, verse_end),
        "passage_text": text_source,
        "markers": matched_sites,
        "matched_archaeology_ids": [marker["id"] for marker in matched_sites],
        "matched_terms": matched_terms,
        "match_count": len(matched_sites),
        "empty_state": len(matched_sites) == 0,
    }


def _resolve_from_reference(
    *,
    places: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    try:
        canonical_book = normalize_book_name(book)
        chapter_number = int(chapter)
    except (TypeError, ValueError, BibleError):
        return [], {}

    if verse_start is None or str(verse_start).strip() == "":
        start = 1
    else:
        try:
            start = int(verse_start)
        except (TypeError, ValueError):
            start = 1

    if verse_end is None or str(verse_end).strip() == "":
        end = start
    else:
        try:
            end = int(verse_end)
        except (TypeError, ValueError):
            end = start

    references = list_place_references(path=path)
    reference_place_ids = {
        reference["place_id"]
        for reference in references
        if reference["book"] == canonical_book
        and reference["chapter"] == chapter_number
        and reference["verse_start"] <= end
        and reference["verse_end"] >= start
    }
    if not reference_place_ids:
        return [], {}

    matched_places = [place for place in places if place["id"] in reference_place_ids]
    matched_terms = {place["id"]: [place["name"]] for place in matched_places}
    return matched_places, matched_terms


def _resolve_routes_from_reference(
    *,
    routes: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    try:
        canonical_book = normalize_book_name(book)
        chapter_number = int(chapter)
    except (TypeError, ValueError, BibleError):
        return [], {}

    if verse_start is None or str(verse_start).strip() == "":
        start = 1
    else:
        try:
            start = int(verse_start)
        except (TypeError, ValueError):
            start = 1

    if verse_end is None or str(verse_end).strip() == "":
        end = start
    else:
        try:
            end = int(verse_end)
        except (TypeError, ValueError):
            end = start

    references = list_route_references(path=path)
    reference_route_ids = {
        reference["route_id"]
        for reference in references
        if reference["book"] == canonical_book
        and reference["chapter"] == chapter_number
        and reference["verse_start"] <= end
        and reference["verse_end"] >= start
    }
    if not reference_route_ids:
        return [], {}

    matched_routes = [route for route in routes if route["id"] in reference_route_ids]
    matched_terms = {route["id"]: [route["name"]] for route in matched_routes}
    return matched_routes, matched_terms


def _resolve_archaeology_from_reference(
    *,
    sites: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    try:
        canonical_book = normalize_book_name(book)
        chapter_number = int(chapter)
    except (TypeError, ValueError, BibleError):
        return [], {}

    if verse_start is None or str(verse_start).strip() == "":
        start = 1
    else:
        try:
            start = int(verse_start)
        except (TypeError, ValueError):
            start = 1

    if verse_end is None or str(verse_end).strip() == "":
        end = start
    else:
        try:
            end = int(verse_end)
        except (TypeError, ValueError):
            end = start

    references = list_archaeology_scripture_links(path=path)
    reference_item_ids = {
        reference["item_id"]
        for reference in references
        if reference["book"] == canonical_book
        and reference["chapter"] == chapter_number
        and reference["verse_start"] <= end
        and reference["verse_end"] >= start
    }
    if not reference_item_ids:
        return [], {}

    matched_markers: list[dict[str, Any]] = []
    matched_terms: dict[str, list[str]] = {}
    for site in sites:
        for marker in _archaeology_site_to_markers(site, path=path):
            if marker["id"] in reference_item_ids:
                matched_markers.append(marker)
                matched_terms[marker["id"]] = [marker["name"]]
    return matched_markers, matched_terms


def _place_to_marker(place: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    latitude = place.get("latitude")
    longitude = place.get("longitude")
    references = list_place_references(place["id"], path=path) if path else list_place_references(place["id"])
    return {
        "id": place["id"],
        "name": place["name"],
        "region": place["ancient_region"] or "Unknown region",
        "description": place["description"] or "No description available.",
        "latitude": latitude,
        "longitude": longitude,
        "aliases": place["aliases"],
        "modern_location": place["modern_location"],
        "ancient_region": place["ancient_region"],
        "confidence": place["confidence"],
        "confidence_rank": place["confidence_rank"],
        "source_name": place["source_name"],
        "source_url": place["source_url"],
        "license": place["license"],
        "notes": place["notes"],
        "related_references": references,
        "reference_count": len(references),
        "has_coordinates": latitude is not None and longitude is not None,
    }


def _route_to_item(route: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    scripture_links = (
        list_route_references(route["id"], path=path)
        if path
        else list_route_references(route["id"])
    )
    geometry = route.get("geojson", {}).get("geometry", {})
    return {
        "id": route["id"],
        "name": route["name"],
        "description": route["description"],
        "period": route["period"],
        "route_type": route["route_type"],
        "geojson": route.get("geojson", {}),
        "confidence": route["confidence"],
        "confidence_rank": route["confidence_rank"],
        "source_name": route["source_name"],
        "source_url": route["source_url"],
        "notes": route["notes"],
        "scripture_links": scripture_links,
        "reference_count": len(scripture_links),
        "geometry_type": geometry.get("type", ""),
    }


def _historical_layer_to_item(layer: dict[str, Any]) -> dict[str, Any]:
    geometry = layer.get("geojson", {}).get("geometry", {})
    return {
        "id": layer["id"],
        "name": layer["name"],
        "period": layer["period"],
        "description": layer["description"],
        "layer_type": layer["layer_type"],
        "geojson": layer.get("geojson", {}),
        "confidence": layer["confidence"],
        "confidence_rank": layer["confidence_rank"],
        "source_name": layer["source_name"],
        "source_url": layer["source_url"],
        "notes": layer["notes"],
        "geometry_type": geometry.get("type", ""),
    }


def _archaeology_site_to_markers(
    site: dict[str, Any],
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    site_items = list_archaeology_items(site["id"], path=path) if path else list_archaeology_items(site["id"])
    markers: list[dict[str, Any]] = []
    for item in site_items:
        markers.append(
            {
                "id": item["id"],
                "name": item["name"],
                "site_id": site["id"],
                "site_name": site["name"],
                "site_type": site["site_type"],
                "period": item["period"] or site["period"],
                "location": site["modern_location"] or site["ancient_region"],
                "ancient_region": site["ancient_region"],
                "latitude": site["latitude"],
                "longitude": site["longitude"],
                "description": site["description"],
                "item_type": item["item_type"],
                "relationship": item["relationship"],
                "why_it_matters": item["why_it_matters"],
                "bhf_caution": item["bhf_caution"],
                "confidence": item["confidence"],
                "confidence_rank": item["confidence_rank"],
                "source_name": item["source_name"] or site["source_name"],
                "source_url": item["source_url"] or site["source_url"],
                "license": item["license"] or site["license"],
                "notes": item["notes"] or site["notes"],
                "scripture_links": item.get("scripture_links", []),
                "reference_count": item.get("reference_count", 0),
                "has_coordinates": site["latitude"] is not None and site["longitude"] is not None,
                "marker_kind": "archaeology",
            }
        )
    return markers


def _format_reference(
    book: str | None,
    chapter: int | str | None,
    verse_start: int | str | None,
    verse_end: int | str | None,
) -> str:
    if book is None or chapter is None:
        return ""
    reference = f"{book} {chapter}"
    if verse_start is None:
        return reference
    start = str(verse_start)
    end = str(verse_end if verse_end is not None else verse_start)
    suffix = start if start == end else f"{start}-{end}"
    return f"{reference}:{suffix}"


def _normalize_for_match(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _term_in_text(term: str, normalized_text: str) -> bool:
    normalized_term = _normalize_for_match(term)
    if not normalized_term:
        return False
    pattern = rf"(?:^| )" + re.escape(normalized_term).replace(r"\ ", r"\s+") + r"(?: |$)"
    return bool(re.search(pattern, normalized_text))


def _unique_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        normalized = term.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique
