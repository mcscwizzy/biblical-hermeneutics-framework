"""Map data access helpers for the BHF map panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhf_agent.bible import BibleError, resolve_passage
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
    list_saved_map_studies,
)
from .services.map_matching import (
    format_reference as _format_reference,
    normalize_for_match as _normalize_for_match,
    resolve_archaeology_from_reference as _resolve_archaeology_from_reference,
    resolve_manuscripts_from_reference as _resolve_manuscripts_from_reference,
    resolve_places_from_reference as _resolve_from_reference,
    resolve_political_context_from_reference as _resolve_political_context_from_reference,
    resolve_routes_from_reference as _resolve_routes_from_reference,
    term_in_text as _term_in_text,
    unique_terms as _unique_terms,
)
from .services.map_serializers import (
    archaeology_site_to_markers as _archaeology_site_to_markers,
    historical_layer_to_item as _historical_layer_to_item,
    manuscript_item_to_marker as _manuscript_item_to_marker,
    place_to_marker as _place_to_marker,
    political_context_to_item as _political_context_to_item,
    related_passages_for_place as _related_passages_for_place,
    route_to_item as _route_to_item,
)


_MAP_SEARCH_KIND_ALIASES = {
    "all": "all",
    "topic": "all",
    "place": "place",
    "places": "place",
    "location": "place",
    "locations": "place",
    "route": "route",
    "routes": "route",
    "archaeology": "archaeology",
    "archaeological": "archaeology",
    "manuscript": "manuscript",
    "manuscripts": "manuscript",
    "historical layer": "historical_layer",
    "historical_layer": "historical_layer",
    "historical layers": "historical_layer",
    "historical": "historical_layer",
    "political context": "political_context",
    "political_context": "political_context",
    "context": "political_context",
}


def _normalize_map_search_kind(kind: str | None) -> str:
    normalized = _normalize_for_match(str(kind or "all"))
    return _MAP_SEARCH_KIND_ALIASES.get(normalized, "all")


def _search_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return " ".join(_search_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_search_text(item) for item in value.values())
    return str(value)


def _first_text(item: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        value = _search_text(item.get(field, "")).strip()
        if value:
            return value
    return ""


def _score_match(query: str, item: dict[str, Any], fields: list[tuple[str, int]]) -> tuple[int, list[str]]:
    normalized_query = _normalize_for_match(query)
    if not normalized_query:
        return 0, []

    query_terms = [term for term in normalized_query.split(" ") if term]
    score = 0
    matched_fields: list[str] = []

    for field_name, weight in fields:
        value = _search_text(item.get(field_name, ""))
        normalized_value = _normalize_for_match(value)
        if not normalized_value:
            continue
        if normalized_query in normalized_value:
            score += weight * 3
            matched_fields.append(field_name)
            continue
        if any(term in normalized_value for term in query_terms):
            score += weight
            matched_fields.append(field_name)

    return score, matched_fields


def _search_catalog_items(
    query: str,
    items: list[dict[str, Any]],
    *,
    kind: str,
    kind_label: str,
    fields: list[tuple[str, int]],
    subtitle_fields: list[str],
    summary_fields: list[str],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for item in items:
        score, matched_fields = _score_match(query, item, fields)
        if score <= 0:
            continue
        subtitle = _first_text(item, subtitle_fields)
        summary = _first_text(item, summary_fields)
        hits.append(
            {
                "kind": kind,
                "kind_label": kind_label,
                "id": item.get("id", ""),
                "title": item.get("name") or item.get("title") or item.get("reference") or "Unnamed item",
                "subtitle": subtitle,
                "summary": summary,
                "period": item.get("period") or "",
                "confidence": item.get("confidence") or "",
                "reference_count": int(item.get("reference_count") or 0),
                "marker_kind": item.get("marker_kind") or kind,
                "has_coordinates": bool(item.get("has_coordinates")),
                "search_score": score,
                "matched_fields": matched_fields,
                "item": item,
            }
        )
    hits.sort(key=lambda hit: (-int(hit["search_score"]), str(hit["title"]).lower(), str(hit["id"])))
    return hits


def get_map_catalog(
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "places": get_biblical_place_markers(period=period, path=path),
        "routes": get_map_routes(period=period, path=path),
        "archaeology": get_archaeology_markers(period=period, path=path),
        "manuscripts": get_manuscript_markers(period=period, path=path),
        "historical_layers": get_historical_layers(period=period, path=path),
        "political_context": get_political_context_layers(period=period, path=path),
        "saved_map_studies": list_saved_map_studies(path=path),
    }


def search_map_catalog(
    query: str,
    *,
    kind: str | None = None,
    period: str | None = None,
    limit: int = 25,
    path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        return {
            "query": "",
            "kind": _normalize_map_search_kind(kind),
            "period": period or "all",
            "results": [],
            "total_results": 0,
        }

    catalog = get_map_catalog(period=period, path=path)
    search_kind = _normalize_map_search_kind(kind)
    allowed_kinds = {
        "all": {"place", "route", "archaeology", "manuscript", "historical_layer", "political_context"},
        "place": {"place"},
        "route": {"route"},
        "archaeology": {"archaeology"},
        "manuscript": {"manuscript"},
        "historical_layer": {"historical_layer"},
        "political_context": {"political_context"},
    }[search_kind]

    all_hits: list[dict[str, Any]] = []
    if "place" in allowed_kinds:
        all_hits.extend(
            _search_catalog_items(
                normalized_query,
                catalog["places"],
                kind="place",
                kind_label="Location",
                fields=[
                    ("name", 5),
                    ("aliases", 4),
                    ("description", 2),
                    ("ancient_region", 2),
                    ("modern_location", 2),
                    ("periods", 1),
                    ("confidence", 1),
                    ("notes", 1),
                ],
                subtitle_fields=["ancient_region", "modern_location"],
                summary_fields=["description", "notes"],
            )
        )
    if "route" in allowed_kinds:
        all_hits.extend(
            _search_catalog_items(
                normalized_query,
                catalog["routes"],
                kind="route",
                kind_label="Route",
                fields=[
                    ("name", 5),
                    ("description", 2),
                    ("route_type", 3),
                    ("period", 2),
                    ("periods", 1),
                    ("confidence", 1),
                    ("notes", 1),
                ],
                subtitle_fields=["route_type", "period"],
                summary_fields=["summary", "description", "notes"],
            )
        )
    if "archaeology" in allowed_kinds:
        all_hits.extend(
            _search_catalog_items(
                normalized_query,
                catalog["archaeology"],
                kind="archaeology",
                kind_label="Archaeology evidence",
                fields=[
                    ("name", 5),
                    ("site_name", 4),
                    ("site_type", 3),
                    ("item_type", 2),
                    ("relationship", 2),
                    ("why_it_matters", 2),
                    ("location", 1),
                    ("ancient_region", 1),
                    ("description", 1),
                    ("periods", 1),
                    ("confidence", 1),
                    ("notes", 1),
                ],
                subtitle_fields=["site_name", "location", "ancient_region"],
                summary_fields=["relationship", "why_it_matters", "notes"],
            )
        )
    if "manuscript" in allowed_kinds:
        all_hits.extend(
            _search_catalog_items(
                normalized_query,
                catalog["manuscripts"],
                kind="manuscript",
                kind_label="Textual witness",
                fields=[
                    ("name", 5),
                    ("manuscript_type", 3),
                    ("language", 2),
                    ("material", 2),
                    ("discovery_location", 2),
                    ("current_location", 2),
                    ("location", 2),
                    ("significance", 2),
                    ("related_books", 2),
                    ("periods", 1),
                    ("confidence", 1),
                    ("notes", 1),
                ],
                subtitle_fields=["discovery_location", "current_location", "location"],
                summary_fields=["significance", "notes"],
            )
        )
    if "historical_layer" in allowed_kinds:
        all_hits.extend(
            _search_catalog_items(
                normalized_query,
                catalog["historical_layers"],
                kind="historical_layer",
                kind_label="Historical layer",
                fields=[
                    ("name", 5),
                    ("description", 2),
                    ("layer_type", 3),
                    ("period", 2),
                    ("periods", 1),
                    ("confidence", 1),
                    ("notes", 1),
                ],
                subtitle_fields=["period", "layer_type"],
                summary_fields=["description", "notes"],
            )
        )
    if "political_context" in allowed_kinds:
        all_hits.extend(
            _search_catalog_items(
                normalized_query,
                catalog["political_context"],
                kind="political_context",
                kind_label="Political context",
                fields=[
                    ("name", 5),
                    ("summary", 3),
                    ("description", 2),
                    ("entity_type", 3),
                    ("period", 2),
                    ("periods", 1),
                    ("confidence", 1),
                    ("notes", 1),
                ],
                subtitle_fields=["entity_type", "period"],
                summary_fields=["summary", "description", "notes"],
            )
        )

    total_results = len(all_hits)
    return {
        "query": normalized_query,
        "kind": search_kind,
        "period": period or "all",
        "results": all_hits[: max(0, int(limit))],
        "total_results": total_results,
    }


def get_map_routes(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    routes = list_map_routes(period=period, path=path) if path else list_map_routes(period=period)
    return [_route_to_item(route, list_route_references, path=path) for route in routes]


def get_biblical_place_markers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return places from the local SQLite data store in map-marker shape."""

    places = list_biblical_places(period=period, path=path) if path else list_biblical_places(period=period)
    return [
        _place_to_marker(
            place,
            list_place_references,
            _related_passages_for_place,
            period=period,
            path=path,
        )
        for place in places
    ]


def get_related_passages_for_place(
    place_id: str,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    place = get_biblical_place(place_id, path=path) if path else get_biblical_place(place_id)
    return _related_passages_for_place(
        place,
        list_biblical_places,
        list_map_routes,
        list_political_context_layers,
        list_place_references,
        list_route_references,
        list_political_context_references,
        period=period,
        path=path,
    )


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
            list_place_references=list_place_references,
            path=path,
        )

    markers = [
        _place_to_marker(
            place,
            list_place_references,
            _related_passages_for_place,
            path=path,
        )
        for place in matched_places
    ]
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
            list_route_references=list_route_references,
            path=path,
        )

    route_items = [_route_to_item(route, list_route_references, path=path) for route in matched_routes]
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
    return [
        _political_context_to_item(layer, list_political_context_references, path=path)
        for layer in layers
    ]


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
            list_political_context_references=list_political_context_references,
            path=path,
        )

    layer_items = [
        _political_context_to_item(layer, list_political_context_references, path=path)
        for layer in matched_layers
    ]
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
        markers.extend(_archaeology_site_to_markers(site, list_archaeology_items, path=path))
    return markers


def get_manuscript_markers(
    period: str | None = None,
    path: str | Path | None = None,
) -> list[dict[str, Any]]:
    items = list_manuscript_items(period=period, path=path) if path else list_manuscript_items(period=period)
    return [_manuscript_item_to_marker(item, list_manuscript_scripture_links, path=path) for item in items]


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
            list_manuscript_scripture_links=list_manuscript_scripture_links,
            path=path,
        )

    markers = [
        _manuscript_item_to_marker(item, list_manuscript_scripture_links, path=path)
        for item in matched_items
    ]
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
        for marker in _archaeology_site_to_markers(site, list_archaeology_items, path=path):
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
            site_markers_fn=lambda site, path=None: _archaeology_site_to_markers(
                site,
                list_archaeology_items,
                path=path,
            ),
            list_archaeology_scripture_links=list_archaeology_scripture_links,
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
