"""Map data access helpers for the BHF map panel."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bhf_agent.bible import BibleError, normalize_book_name, resolve_passage, testament_for_book
from bhf_agent.study_db import (
    get_biblical_place,
    list_archaeology_items,
    list_archaeology_sites,
    list_archaeology_scripture_links,
    list_biblical_places,
    list_historical_layers,
    list_map_routes,
    list_manuscript_items,
    list_manuscript_scripture_links,
    list_political_context_layers,
    list_political_context_references,
    list_place_references,
    list_route_references,
)


def get_biblical_place_markers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return places from the local SQLite data store in map-marker shape."""

    places = list_biblical_places(period=period, path=path) if path else list_biblical_places(period=period)
    markers: list[dict[str, Any]] = []
    for place in places:
        markers.append(_place_to_marker(place, period=period, path=path))
    return markers


def get_related_passages_for_place(
    place_id: str,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    place = get_biblical_place(place_id, path=path) if path else get_biblical_place(place_id)
    return _related_passages_for_place(place, period=period, path=path)


def resolve_places_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve curated places from a passage using deterministic matching only."""

    # Passage-to-place resolution should stay stable regardless of any
    # historical-layer period filter currently active in the map UI.
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
            period=period,
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
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve curated routes from a passage using deterministic matching only."""

    routes = list_map_routes(period=period, path=path) if path else list_map_routes(period=period)
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
            period=period,
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


def get_political_context_layers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    layers = (
        list_political_context_layers(period=period, path=path)
        if path
        else list_political_context_layers(period=period)
    )
    return [_political_context_to_item(layer) for layer in layers]


def resolve_political_context_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    layers = (
        list_political_context_layers(period=period, path=path)
        if path
        else list_political_context_layers(period=period)
    )
    if passage_text and passage_text.strip():
        text_source = passage_text
    elif book is not None and chapter is not None:
        passage = resolve_passage(book, chapter, verse_start, verse_end)
        text_source = passage["selected_text"]
    else:
        text_source = ""

    normalized_text = _normalize_for_match(text_source)
    matched_layers: list[dict[str, Any]] = []
    matched_terms: dict[str, list[str]] = {}

    for layer in layers:
        candidate_terms = [
            layer["name"],
            layer.get("summary", ""),
            layer.get("entity_type", ""),
        ]
        matches = [term for term in candidate_terms if _term_in_text(term, normalized_text)]
        if matches:
            matched_layers.append(layer)
            matched_terms[layer["id"]] = _unique_terms(matches)

    if not matched_layers and book is not None and chapter is not None:
        matched_layers, matched_terms = _resolve_political_context_from_reference(
            layers=layers,
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            path=path,
        )

    layer_items = [_political_context_to_item(layer, path=path) for layer in matched_layers]
    return {
        "reference": _format_reference(book, chapter, verse_start, verse_end),
        "passage_text": text_source,
        "layers": layer_items,
        "matched_political_context_ids": [layer["id"] for layer in matched_layers],
        "matched_terms": matched_terms,
        "match_count": len(layer_items),
        "empty_state": len(layer_items) == 0,
    }


def get_archaeology_markers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    sites = list_archaeology_sites(period=period, path=path) if path else list_archaeology_sites(period=period)
    markers: list[dict[str, Any]] = []
    for site in sites:
        markers.extend(_archaeology_site_to_markers(site, path=path))
    return markers


def get_manuscript_markers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    items = list_manuscript_items(period=period, path=path) if path else list_manuscript_items(period=period)
    return [_manuscript_item_to_marker(item, path=path) for item in items]


def resolve_manuscripts_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    items = list_manuscript_items(period=period, path=path) if path else list_manuscript_items(period=period)
    if passage_text and passage_text.strip():
        text_source = passage_text
    elif book is not None and chapter is not None:
        passage = resolve_passage(book, chapter, verse_start, verse_end)
        text_source = passage["selected_text"]
    else:
        text_source = ""

    normalized_text = _normalize_for_match(text_source)
    matched_items: list[dict[str, Any]] = []
    matched_terms: dict[str, list[str]] = {}

    for item in items:
        candidate_terms = [
            item["name"],
            item.get("manuscript_type", ""),
            item.get("language", ""),
            item.get("significance", ""),
            ", ".join(item.get("related_books", [])),
        ]
        matches = [term for term in candidate_terms if _term_in_text(term, normalized_text)]
        if matches:
            matched_items.append(item)
            matched_terms[item["id"]] = _unique_terms(matches)

    if not matched_items and book is not None and chapter is not None:
        matched_items, matched_terms = _resolve_manuscripts_from_reference(
            items=items,
            book=book,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            path=path,
        )

    markers = [_manuscript_item_to_marker(item, path=path) for item in matched_items]
    return {
        "reference": _format_reference(book, chapter, verse_start, verse_end),
        "passage_text": text_source,
        "markers": markers,
        "matched_manuscript_ids": [item["id"] for item in matched_items],
        "matched_terms": matched_terms,
        "match_count": len(markers),
        "empty_state": len(markers) == 0,
    }


def resolve_archaeology_for_passage(
    *,
    book: str | None = None,
    chapter: int | str | None = None,
    verse_start: int | str | None = None,
    verse_end: int | str | None = None,
    passage_text: str | None = None,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    sites = list_archaeology_sites(period=period, path=path) if path else list_archaeology_sites(period=period)
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
            period=period,
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
    period: str | None = None,
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
    period: str | None = None,
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
    period: str | None = None,
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


def _resolve_manuscripts_from_reference(
    *,
    items: list[dict[str, Any]],
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

    references = list_manuscript_scripture_links(path=path)
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

    matched_items = [item for item in items if item["id"] in reference_item_ids]
    matched_terms = {item["id"]: [item["name"]] for item in matched_items}
    return matched_items, matched_terms


def _resolve_political_context_from_reference(
    *,
    layers: list[dict[str, Any]],
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

    references = list_political_context_references(path=path)
    reference_context_ids = {
        reference["context_id"]
        for reference in references
        if reference["book"] == canonical_book
        and reference["chapter"] == chapter_number
        and reference["verse_start"] <= end
        and reference["verse_end"] >= start
    }
    if not reference_context_ids:
        return [], {}

    matched_layers = [layer for layer in layers if layer["id"] in reference_context_ids]
    matched_terms = {layer["id"]: [layer["name"]] for layer in matched_layers}
    return matched_layers, matched_terms


def _manuscript_item_to_marker(item: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    references = (
        list_manuscript_scripture_links(item["id"], path=path)
        if path
        else list_manuscript_scripture_links(item["id"])
    )
    return {
        "id": item["id"],
        "name": item["name"],
        "manuscript_type": item["manuscript_type"],
        "language": item["language"],
        "date": item["date"],
        "material": item["material"],
        "discovery_location": item["discovery_location"],
        "current_location": item["current_location"],
        "location": item["discovery_location"] or item["current_location"] or "Unknown location",
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "related_books": item.get("related_books", []),
        "period": item["period"],
        "periods": item.get("periods", []),
        "significance": item["significance"],
        "confidence": item["confidence"],
        "confidence_rank": item["confidence_rank"],
        "source_id": item.get("source_id", ""),
        "source": item.get("source"),
        "source_name": item["source_name"],
        "source_url": item["source_url"],
        "license": item["license"],
        "notes": item["notes"],
        "bhf_caution": item["bhf_caution"],
        "scripture_links": references,
        "reference_count": len(references),
        "has_coordinates": item["latitude"] is not None and item["longitude"] is not None,
        "marker_kind": "manuscript",
    }


def _place_to_marker(
    place: dict[str, Any],
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    latitude = place.get("latitude")
    longitude = place.get("longitude")
    references = list_place_references(place["id"], path=path) if path else list_place_references(place["id"])
    return {
        "id": place["id"],
        "name": place["name"],
        "marker_kind": "place",
        "region": place["ancient_region"] or "Unknown region",
        "description": place["description"] or "No description available.",
        "periods": place.get("periods", []),
        "latitude": latitude,
        "longitude": longitude,
        "aliases": place["aliases"],
        "modern_location": place["modern_location"],
        "ancient_region": place["ancient_region"],
        "confidence": place["confidence"],
        "confidence_rank": place["confidence_rank"],
        "source_id": place.get("source_id", ""),
        "source": place.get("source"),
        "source_name": place["source_name"],
        "source_url": place["source_url"],
        "license": place["license"],
        "notes": place["notes"],
        "related_references": references,
        "related_passages": _related_passages_for_place(place, period=period, path=path),
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
        "periods": route.get("periods", []),
        "route_type": route["route_type"],
        "geojson": route.get("geojson", {}),
        "confidence": route["confidence"],
        "confidence_rank": route["confidence_rank"],
        "source_id": route.get("source_id", ""),
        "source": route.get("source"),
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
        "periods": layer.get("periods", []),
        "description": layer["description"],
        "layer_type": layer["layer_type"],
        "geojson": layer.get("geojson", {}),
        "confidence": layer["confidence"],
        "confidence_rank": layer["confidence_rank"],
        "source_id": layer.get("source_id", ""),
        "source": layer.get("source"),
        "source_name": layer["source_name"],
        "source_url": layer["source_url"],
        "notes": layer["notes"],
        "geometry_type": geometry.get("type", ""),
    }


def _political_context_to_item(layer: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    scripture_links = (
        list_political_context_references(layer["id"], path=path)
        if path
        else list_political_context_references(layer["id"])
    )
    geometry = layer.get("geojson", {}).get("geometry", {})
    return {
        "id": layer["id"],
        "name": layer["name"],
        "entity_type": layer["entity_type"],
        "period": layer["period"],
        "periods": layer.get("periods", []),
        "summary": layer["summary"],
        "description": layer["description"],
        "layer_type": layer["layer_type"],
        "sort_order": layer["sort_order"],
        "geojson": layer.get("geojson", {}),
                "confidence": layer["confidence"],
                "confidence_rank": layer["confidence_rank"],
                "source_id": layer.get("source_id", ""),
                "source": layer.get("source"),
                "source_name": layer["source_name"],
                "source_url": layer["source_url"],
                "notes": layer["notes"],
        "scripture_links": scripture_links,
        "reference_count": len(scripture_links),
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
                "periods": item.get("periods", site.get("periods", [])),
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
                "source_id": item.get("source_id", "") or site.get("source_id", ""),
                "source": item.get("source") or site.get("source"),
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


def _related_passages_for_place(
    place: dict[str, Any],
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    direct_refs = list_place_references(place["id"], path=path) if path else list_place_references(place["id"])
    direct_entries = [
        _related_passage_entry(
            reference,
            relationship_type=reference["relationship_type"],
            relationship_label=_relationship_label(reference["relationship_type"]),
            source_kind="place",
            source_id=place["id"],
            source_name=place["name"],
            source_label=place.get("ancient_region") or place.get("modern_location") or place["name"],
            source_notes=place.get("notes", ""),
            source_confidence=place.get("confidence", "unknown"),
            source_confidence_rank=place.get("confidence_rank", 0),
            source_url=place.get("source_url", ""),
            source_periods=place.get("periods", []),
            source_entity_type="biblical place",
        )
        for reference in direct_refs
    ]

    groups: list[dict[str, Any]] = []
    groups.append(
        {
            "group_type": "directly_mentioned",
            "label": "Directly Mentioned",
            "summary": "Passages that explicitly name this place.",
            "passages": direct_entries,
            "count": len(direct_entries),
            "testament_groups": _group_passages_by_testament(direct_entries),
        }
    )

    seen_keys = {_passage_key(entry) for entry in direct_entries}

    region_entries: list[dict[str, Any]] = []
    place_region = str(place.get("ancient_region") or "").strip()
    if place_region:
        other_places = list_biblical_places(period=period, path=path) if path else list_biblical_places(period=period)
        for other_place in other_places:
            if other_place["id"] == place["id"] or other_place.get("ancient_region") != place_region:
                continue
            other_refs = list_place_references(other_place["id"], path=path) if path else list_place_references(other_place["id"])
            for reference in other_refs:
                entry = _related_passage_entry(
                    reference,
                    relationship_type="same_region",
                    relationship_label="Same region",
                    source_kind="place",
                    source_id=other_place["id"],
                    source_name=other_place["name"],
                    source_label=other_place.get("ancient_region") or other_place["name"],
                    source_notes=other_place.get("notes", ""),
                    source_confidence=other_place.get("confidence", "unknown"),
                    source_confidence_rank=other_place.get("confidence_rank", 0),
                    source_url=other_place.get("source_url", ""),
                    source_periods=other_place.get("periods", []),
                    source_entity_type="biblical place",
                )
                if _passage_key(entry) in seen_keys:
                    continue
                seen_keys.add(_passage_key(entry))
                region_entries.append(entry)
    if region_entries:
        groups.append(
            {
                "group_type": "same_region",
                "label": f"Same Region: {place_region}" if place_region else "Same Region",
                "summary": "Passages tied to other places in the same ancient region.",
                "passages": _sorted_related_passages(region_entries),
                "count": len(region_entries),
            }
        )

    route_entries: list[dict[str, Any]] = []
    place_coords = (place.get("latitude"), place.get("longitude"))
    if place_coords[0] is not None and place_coords[1] is not None:
        routes = list_map_routes(period=period, path=path) if path else list_map_routes(period=period)
        for route in routes:
            if not _periods_overlap(place.get("periods", []), route.get("periods", [])):
                continue
            if not _route_is_near_place(route, float(place_coords[0]), float(place_coords[1])):
                continue
            route_refs = list_route_references(route["id"], path=path) if path else list_route_references(route["id"])
            for reference in route_refs:
                entry = _related_passage_entry(
                    reference,
                    relationship_type="same_route",
                    relationship_label="Same route",
                    source_kind="route",
                    source_id=route["id"],
                    source_name=route["name"],
                    source_label=route.get("route_type") or route.get("period") or route["name"],
                    source_notes=route.get("notes", ""),
                    source_confidence=route.get("confidence", "unknown"),
                    source_confidence_rank=route.get("confidence_rank", 0),
                    source_url=route.get("source_url", ""),
                    source_periods=route.get("periods", []),
                    source_entity_type="map route",
                )
                if _passage_key(entry) in seen_keys:
                    continue
                seen_keys.add(_passage_key(entry))
                route_entries.append(entry)
    if route_entries:
        groups.append(
            {
                "group_type": "same_route",
                "label": "Same Route",
                "summary": "Passages connected to a curated route that passes near this place.",
                "passages": _sorted_related_passages(route_entries),
                "count": len(route_entries),
            }
        )

    context_entries: list[dict[str, Any]] = []
    layers = list_political_context_layers(period=period, path=path) if path else list_political_context_layers(period=period)
    for layer in layers:
        if not _periods_overlap(place.get("periods", []), layer.get("periods", [])):
            continue
        links = list_political_context_references(layer["id"], path=path) if path else list_political_context_references(layer["id"])
        for reference in links:
            entry = _related_passage_entry(
                reference,
                relationship_type="same_empire_period",
                relationship_label="Same empire / period",
                source_kind="political_context",
                source_id=layer["id"],
                source_name=layer["name"],
                source_label=layer.get("entity_type") or layer.get("period") or layer["name"],
                source_notes=layer.get("notes", ""),
                source_confidence=layer.get("confidence", "unknown"),
                source_confidence_rank=layer.get("confidence_rank", 0),
                source_url=layer.get("source_url", ""),
                source_periods=layer.get("periods", []),
                source_entity_type=layer.get("entity_type", "political context"),
            )
            if _passage_key(entry) in seen_keys:
                continue
            seen_keys.add(_passage_key(entry))
            context_entries.append(entry)
    if context_entries:
        groups.append(
            {
                "group_type": "same_empire_period",
                "label": "Same Empire / Period",
                "summary": "Passages tied to the broader political background of this place.",
                "passages": _sorted_related_passages(context_entries),
                "count": len(context_entries),
            }
        )

    return {
        "place_id": place["id"],
        "place_name": place["name"],
        "ancient_region": place.get("ancient_region", ""),
        "periods": place.get("periods", []),
        "groups": groups,
        "count": sum(group["count"] for group in groups),
    }


def _related_passage_entry(
    reference: dict[str, Any],
    *,
    relationship_type: str,
    relationship_label: str,
    source_kind: str,
    source_id: str,
    source_name: str,
    source_label: str,
    source_notes: str,
    source_confidence: str,
    source_confidence_rank: int,
    source_url: str,
    source_periods: list[str],
    source_entity_type: str,
) -> dict[str, Any]:
    return {
        "book": reference["book"],
        "chapter": reference["chapter"],
        "verse_start": reference["verse_start"],
        "verse_end": reference["verse_end"],
        "reference": _format_reference(reference["book"], reference["chapter"], reference["verse_start"], reference["verse_end"]),
        "testament": testament_for_book(reference["book"]),
        "relationship_type": relationship_type,
        "relationship_label": relationship_label,
        "notes": reference.get("notes", ""),
        "source": {
            "kind": source_kind,
            "id": source_id,
            "name": source_name,
            "label": source_label,
            "entity_type": source_entity_type,
            "notes": source_notes,
            "confidence": source_confidence,
            "confidence_rank": source_confidence_rank,
            "source_url": source_url,
            "periods": source_periods,
        },
    }


def _group_passages_by_testament(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    order = ["Old Testament", "New Testament", "Other"]
    for passage in passages:
        testament = passage.get("testament") or "Other"
        buckets.setdefault(testament, []).append(passage)
    return [
        {
            "testament": testament,
            "label": f"{testament} location links" if testament in {"Old Testament", "New Testament"} else "Other location links",
            "passages": _sorted_related_passages(buckets[testament]),
            "count": len(buckets[testament]),
        }
        for testament in order
        if testament in buckets
    ]


def _sorted_related_passages(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        passages,
        key=lambda passage: (
            passage.get("book", ""),
            int(passage.get("chapter", 0)),
            int(passage.get("verse_start", 0)),
            int(passage.get("verse_end", 0)),
            passage.get("source", {}).get("name", ""),
        ),
    )


def _passage_key(entry: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return (
        entry.get("book"),
        entry.get("chapter"),
        entry.get("verse_start"),
        entry.get("verse_end"),
    )


def _relationship_label(value: str) -> str:
    labels = {
        "directly_named": "Directly mentioned",
        "same_region": "Same region",
        "same_route": "Same route",
        "same_empire_period": "Same empire / period",
        "historical_context": "Historical context",
        "textual_witness": "Textual witness",
    }
    return labels.get(value, value.replace("_", " ").strip().title() or "Related passage")


def _periods_overlap(left: list[str], right: list[str]) -> bool:
    left_normalized = {str(item).strip() for item in left if str(item).strip()}
    right_normalized = {str(item).strip() for item in right if str(item).strip()}
    if not left_normalized or not right_normalized:
        return False
    if "Broad / uncertain period" in left_normalized or "Broad / uncertain period" in right_normalized:
        return True
    return bool(left_normalized.intersection(right_normalized))


def _route_is_near_place(route: dict[str, Any], latitude: float, longitude: float, threshold: float = 0.45) -> bool:
    geojson = route.get("geojson", {})
    geometry = geojson.get("geometry", {}) if isinstance(geojson, dict) else {}
    coordinates = geometry.get("coordinates", [])
    for first, second in _flatten_coordinates(coordinates):
        if (
            abs(float(first) - latitude) <= threshold and abs(float(second) - longitude) <= threshold
        ) or (
            abs(float(first) - longitude) <= threshold and abs(float(second) - latitude) <= threshold
        ):
            return True
    return False


def _flatten_coordinates(value: Any) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    if isinstance(value, list):
        if len(value) >= 2 and all(not isinstance(item, list) for item in value[:2]):
            try:
                coords.append((float(value[0]), float(value[1])))
            except (TypeError, ValueError):
                return coords
            return coords
        for item in value:
            coords.extend(_flatten_coordinates(item))
    return coords
