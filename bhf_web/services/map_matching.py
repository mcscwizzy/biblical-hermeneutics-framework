"""Matching and fallback helpers for map passage resolution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bhf_agent.bible import BibleError, normalize_book_name


def format_reference(
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


def normalize_for_match(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def term_in_text(term: str, normalized_text: str) -> bool:
    normalized_term = normalize_for_match(term)
    if not normalized_term:
        return False
    pattern = rf"(?:^| )" + re.escape(normalized_term).replace(r"\ ", r"\s+") + r"(?: |$)"
    return bool(re.search(pattern, normalized_text))


def unique_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        normalized = term.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def resolve_places_from_reference(
    *,
    places: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    list_place_references: Any,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    canonical_book, chapter_number, start, end = _reference_window(
        book,
        chapter,
        verse_start,
        verse_end,
    )
    if canonical_book is None:
        return [], {}

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


def resolve_routes_from_reference(
    *,
    routes: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    list_route_references: Any,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    canonical_book, chapter_number, start, end = _reference_window(
        book,
        chapter,
        verse_start,
        verse_end,
    )
    if canonical_book is None:
        return [], {}

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


def resolve_archaeology_from_reference(
    *,
    sites: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    site_markers_fn: Any,
    list_archaeology_scripture_links: Any,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    canonical_book, chapter_number, start, end = _reference_window(
        book,
        chapter,
        verse_start,
        verse_end,
    )
    if canonical_book is None:
        return [], {}

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
        for marker in site_markers_fn(site, path=path):
            if marker["id"] in reference_item_ids:
                matched_markers.append(marker)
                matched_terms[marker["id"]] = [marker["name"]]
    return matched_markers, matched_terms


def resolve_manuscripts_from_reference(
    *,
    items: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    list_manuscript_scripture_links: Any,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    canonical_book, chapter_number, start, end = _reference_window(
        book,
        chapter,
        verse_start,
        verse_end,
    )
    if canonical_book is None:
        return [], {}

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


def resolve_political_context_from_reference(
    *,
    layers: list[dict[str, Any]],
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
    list_political_context_references: Any,
    path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    canonical_book, chapter_number, start, end = _reference_window(
        book,
        chapter,
        verse_start,
        verse_end,
    )
    if canonical_book is None:
        return [], {}

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


def periods_overlap(left: list[str], right: list[str]) -> bool:
    left_normalized = {str(item).strip() for item in left if str(item).strip()}
    right_normalized = {str(item).strip() for item in right if str(item).strip()}
    if not left_normalized or not right_normalized:
        return False
    if "Broad / uncertain period" in left_normalized or "Broad / uncertain period" in right_normalized:
        return True
    return bool(left_normalized.intersection(right_normalized))


def route_is_near_place(route: dict[str, Any], latitude: float, longitude: float, threshold: float = 0.45) -> bool:
    geojson = route.get("geojson", {})
    geometry = geojson.get("geometry", {}) if isinstance(geojson, dict) else {}
    coordinates = geometry.get("coordinates", [])
    for first, second in flatten_coordinates(coordinates):
        if (
            abs(float(first) - latitude) <= threshold and abs(float(second) - longitude) <= threshold
        ) or (
            abs(float(first) - longitude) <= threshold and abs(float(second) - latitude) <= threshold
        ):
            return True
    return False


def flatten_coordinates(value: Any) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    if isinstance(value, list):
        if len(value) >= 2 and all(not isinstance(item, list) for item in value[:2]):
            try:
                coords.append((float(value[0]), float(value[1])))
            except (TypeError, ValueError):
                return coords
            return coords
        for item in value:
            coords.extend(flatten_coordinates(item))
    return coords


def _reference_window(
    book: str,
    chapter: int | str,
    verse_start: int | str | None,
    verse_end: int | str | None,
) -> tuple[str | None, int | None, int, int]:
    try:
        canonical_book = normalize_book_name(book)
        chapter_number = int(chapter)
    except (TypeError, ValueError, BibleError):
        return None, None, 1, 1

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

    return canonical_book, chapter_number, start, end
