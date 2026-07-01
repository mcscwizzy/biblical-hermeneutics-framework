"""Deterministic map and archaeology retrieval tools for the BHF agent."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bhf_agent.bible import BibleError, normalize_book_name, resolve_passage
from bhf_agent.models import QuestionContext, ReferenceContext
from bhf_agent.references import BOOK_ALIASES
from bhf_agent.study_db import DEFAULT_DB_PATH, get_biblical_place
from bhf_web.map_service import (
    get_related_passages_for_place,
    get_map_routes_for_passage,
    get_historical_layers,
    get_political_context_layers,
    resolve_archaeology_for_passage,
    resolve_places_for_passage,
)


MAP_KEYWORDS = (
    "map",
    "location",
    "where",
    "place",
    "city",
    "region",
    "route",
    "travel",
    "journey",
    "archaeolog",
    "artifact",
    "inscription",
    "excavation",
    "manuscript",
    "historical context",
    "political context",
    "kingdom",
    "empire",
)

BOOK_PATTERN = "|".join(re.escape(name) for name in sorted(BOOK_ALIASES, key=len, reverse=True))
REFERENCE_PATTERN = re.compile(
    rf"\b(?P<book>{BOOK_PATTERN})\.?\s+"
    r"(?P<chapter>\d{1,3})"
    r"(?:\s*:\s*(?P<verse_start>\d{1,3})(?:\s*-\s*(?P<verse_end>\d{1,3}))?)?\b",
    re.IGNORECASE,
)


def getPlacesForPassage(reference: str, period: str | None = None, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return curated biblical places for a passage reference."""

    parsed = _parse_reference(reference)
    if parsed is None:
        raise ValueError(f"Could not parse passage reference: {reference}")
    return resolve_places_for_passage(period=period, path=path, **parsed)


def getPlaceDetails(placeId: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return a curated biblical place and its related passages."""

    place = get_biblical_place(placeId, path=path)
    related_passages = get_related_passages_for_place(placeId, path=path)
    return {
        **place,
        "related_passages": related_passages,
    }


def getArchaeologyForPassage(reference: str, period: str | None = None, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return curated archaeology markers for a passage reference."""

    parsed = _parse_reference(reference)
    if parsed is None:
        raise ValueError(f"Could not parse passage reference: {reference}")
    return resolve_archaeology_for_passage(period=period, path=path, **parsed)


def getArchaeologyForPlace(placeId: str, period: str | None = None, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return archaeology tied to the curated passages for a place."""

    place_details = getPlaceDetails(placeId, path=path)
    combined_markers: list[dict[str, Any]] = []
    combined_terms: dict[str, list[str]] = {}
    seen_ids: set[str] = set()

    for group in place_details.get("related_passages", {}).get("groups", []):
        for passage in group.get("passages", []):
            reference = str(passage.get("reference") or "").strip()
            if not reference:
                continue
            result = getArchaeologyForPassage(reference, period=period, path=path)
            for marker in result.get("markers", []):
                marker_id = str(marker.get("id") or "")
                if not marker_id or marker_id in seen_ids:
                    continue
                seen_ids.add(marker_id)
                combined_markers.append(marker)
                combined_terms[marker_id] = list(result.get("matched_terms", {}).get(marker_id, [marker.get("name", "")]))

    return {
        "place_id": placeId,
        "place": place_details,
        "markers": combined_markers,
        "matched_archaeology_ids": [marker["id"] for marker in combined_markers],
        "matched_terms": combined_terms,
        "match_count": len(combined_markers),
        "empty_state": len(combined_markers) == 0,
    }


def getRoutesForPassage(reference: str, period: str | None = None, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return curated routes for a passage reference."""

    parsed = _parse_reference(reference)
    if parsed is None:
        raise ValueError(f"Could not parse passage reference: {reference}")
    return get_map_routes_for_passage(period=period, path=path, **parsed)


def getHistoricalContextForPeriod(period: str, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return curated historical and political context for a period."""

    normalized_period = _normalize_period(period)
    return {
        "period": normalized_period,
        "historical_layers": get_historical_layers(period=normalized_period, path=path),
        "political_context_layers": get_political_context_layers(period=normalized_period, path=path),
    }


def getRelatedPassagesByPlace(placeId: str, period: str | None = None, path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    """Return grouped related passages for a biblical place."""

    place = get_biblical_place(placeId, path=path)
    return get_related_passages_for_place(place["id"], period=period, path=path)


def should_retrieve_map_context(
    question: str,
    question_context: QuestionContext | None = None,
    reference_context: ReferenceContext | None = None,
) -> bool:
    normalized = " ".join(question.strip().split()).lower()
    if any(keyword in normalized for keyword in MAP_KEYWORDS):
        return True
    if question_context and question_context.question_type == "historical_context":
        return True
    if reference_context and reference_context.is_reference_based and any(
        token in normalized for token in ("where", "location", "place", "route", "archaeolog", "historical context")
    ):
        return True
    return False


def build_map_tool_context(
    question: str,
    reference_context: ReferenceContext | None = None,
    question_context: QuestionContext | None = None,
    period: str = "all",
    path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    if not should_retrieve_map_context(question, question_context=question_context, reference_context=reference_context):
        return None

    normalized_period = _normalize_period(period)
    resolved_reference = _reference_from_context(question, reference_context)
    context: dict[str, Any] = {
        "period": normalized_period,
        "requested_tools": [],
    }

    if resolved_reference:
        context["reference"] = resolved_reference
        try:
            places = getPlacesForPassage(resolved_reference, period=normalized_period, path=path)
        except (BibleError, ValueError):
            places = None
        else:
            context["requested_tools"].append("getPlacesForPassage")
            context["places"] = places

            markers = places.get("markers", []) if isinstance(places, dict) else []
            place_ids = [str(marker.get("id") or "") for marker in markers if str(marker.get("id") or "").strip()]
            if place_ids:
                context["requested_tools"].append("getPlaceDetails")
                context["place_details"] = [getPlaceDetails(place_id, path=path) for place_id in place_ids[:3]]
                context["requested_tools"].append("getRelatedPassagesByPlace")
                context["related_passages_by_place"] = [
                    getRelatedPassagesByPlace(place_id, period=normalized_period, path=path)
                    for place_id in place_ids[:3]
                ]

        if _question_mentions_archaeology(question):
            context["requested_tools"].append("getArchaeologyForPassage")
            context["archaeology"] = getArchaeologyForPassage(
                resolved_reference,
                period=normalized_period,
                path=path,
            )

        if _question_mentions_routes(question):
            context["requested_tools"].append("getRoutesForPassage")
            context["routes"] = getRoutesForPassage(
                resolved_reference,
                period=normalized_period,
                path=path,
            )

    if (question_context and question_context.question_type == "historical_context") or _question_mentions_history(question):
        context["requested_tools"].append("getHistoricalContextForPeriod")
        context["historical_context"] = getHistoricalContextForPeriod(normalized_period, path=path)

    if _question_mentions_archaeology(question) and "archaeology" not in context:
        place_id = _first_place_id(context)
        if place_id:
            context["requested_tools"].append("getArchaeologyForPlace")
            context["archaeology"] = getArchaeologyForPlace(place_id, period=normalized_period, path=path)

    if not context.get("requested_tools"):
        return None
    return context


def format_map_tool_context_for_prompt(context: dict[str, Any]) -> str:
    lines = [
        "# Retrieved Map / Archaeology Context",
        "Use this curated local data before answering. Do not invent missing geography, archaeology, or manuscript claims.",
    ]
    reference = str(context.get("reference") or "").strip()
    if reference:
        lines.append(f"- Reference: {reference}")
    period = str(context.get("period") or "").strip()
    if period:
        lines.append(f"- Period filter: {period}")
    requested_tools = context.get("requested_tools") or []
    if requested_tools:
        lines.append(f"- Retrieved tools: {', '.join(requested_tools)}")
    places = context.get("places") or {}
    if isinstance(places, dict):
        lines.extend(_format_markers_section("Places", places.get("markers", []), fields=("name", "ancient_region", "modern_location", "confidence")))
    place_details = context.get("place_details") or []
    if isinstance(place_details, list) and place_details:
        lines.append("- Place details:")
        for place in place_details[:3]:
            if not isinstance(place, dict):
                continue
            lines.append(
                f"  - {place.get('name', 'Unnamed place')} | region: {place.get('ancient_region') or 'unknown'} | source: {place.get('source_name') or 'curated local data'}"
            )
            related = place.get("related_passages", {})
            if isinstance(related, dict):
                lines.append(f"    - related passage groups: {len(related.get('groups', []))}")
    archaeology = context.get("archaeology") or {}
    if isinstance(archaeology, dict) and archaeology:
        lines.extend(_format_markers_section("Archaeology", archaeology.get("markers", []), fields=("name", "site_name", "item_type", "relationship", "confidence")))
    routes = context.get("routes") or {}
    if isinstance(routes, dict) and routes:
        lines.extend(_format_markers_section("Routes", routes.get("routes", []), fields=("name", "route_type", "confidence")))
    historical_context = context.get("historical_context") or {}
    if isinstance(historical_context, dict) and historical_context:
        historical_layers = historical_context.get("historical_layers", [])
        political_layers = historical_context.get("political_context_layers", [])
        lines.append(
            f"- Historical context: {len(historical_layers)} historical layer(s), {len(political_layers)} political context layer(s)."
        )
        if historical_layers:
            lines.append("  - Historical layers: " + ", ".join(_marker_summary(layer, ("name", "period", "confidence")) for layer in historical_layers[:5]))
        if political_layers:
            lines.append("  - Political context: " + ", ".join(_marker_summary(layer, ("name", "entity_type", "confidence")) for layer in political_layers[:5]))
    related_passages_by_place = context.get("related_passages_by_place") or []
    if isinstance(related_passages_by_place, list) and related_passages_by_place:
        lines.append("- Related passages by place:")
        for item in related_passages_by_place[:3]:
            if not isinstance(item, dict):
                continue
            place = item.get("place") or {}
            if isinstance(place, dict):
                lines.append(f"  - {place.get('name', 'Unnamed place')}: {len(item.get('groups', []))} group(s)")
    return "\n".join(lines)


def _first_place_id(context: dict[str, Any]) -> str | None:
    places = context.get("places") or {}
    if not isinstance(places, dict):
        return None
    for marker in places.get("markers", []):
        if isinstance(marker, dict) and str(marker.get("id") or "").strip():
            return str(marker["id"])
    return None


def _format_markers_section(title: str, items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[str]:
    if not items:
        return []
    lines = [f"- {title}: {len(items)} item(s)"]
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        lines.append("  - " + _marker_summary(item, fields))
    return lines


def _marker_summary(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    parts: list[str] = []
    for field in fields:
        value = item.get(field)
        if value:
            parts.append(f"{field.replace('_', ' ')}: {value}")
    return " | ".join(parts) if parts else item.get("id", "unknown")


def _parse_reference(reference: str) -> dict[str, Any] | None:
    normalized = " ".join(str(reference or "").split())
    if not normalized:
        return None
    match = REFERENCE_PATTERN.search(normalized)
    if not match:
        return None
    try:
        book = normalize_book_name(match.group("book"))
        chapter = int(match.group("chapter"))
    except (BibleError, TypeError, ValueError):
        return None
    verse_start = match.group("verse_start")
    verse_end = match.group("verse_end")
    parsed: dict[str, Any] = {"book": book, "chapter": chapter}
    if verse_start:
        parsed["verse_start"] = int(verse_start)
        parsed["verse_end"] = int(verse_end) if verse_end else int(verse_start)
    return parsed


def _reference_from_context(question: str, reference_context: ReferenceContext | None) -> str | None:
    if reference_context and reference_context.book and reference_context.chapter:
        return _reference_from_reference_context(reference_context)
    parsed = _parse_reference(question)
    if not parsed:
        return None
    try:
        passage = resolve_passage(
            parsed["book"],
            parsed["chapter"],
            parsed.get("verse_start"),
            parsed.get("verse_end"),
        )
    except BibleError:
        return None
    return passage["reference"]


def _reference_from_reference_context(reference_context: ReferenceContext) -> str | None:
    if not reference_context.book or reference_context.chapter is None:
        return None
    try:
        passage = resolve_passage(
            reference_context.book,
            reference_context.chapter,
            reference_context.verse,
            reference_context.verse,
        )
    except BibleError:
        try:
            passage = resolve_passage(reference_context.book, reference_context.chapter)
        except BibleError:
            return None
    return passage["reference"]


def _normalize_period(period: str | None) -> str | None:
    cleaned = str(period or "").strip()
    if not cleaned or cleaned.lower() == "all":
        return None
    return cleaned


def _question_mentions_archaeology(question: str) -> bool:
    lowered = " ".join(question.lower().split())
    return any(keyword in lowered for keyword in ("archaeolog", "artifact", "inscription", "excavat", "site"))


def _question_mentions_routes(question: str) -> bool:
    lowered = " ".join(question.lower().split())
    return any(keyword in lowered for keyword in ("route", "journey", "travel", "went to", "path"))


def _question_mentions_history(question: str) -> bool:
    lowered = " ".join(question.lower().split())
    return any(keyword in lowered for keyword in ("historical context", "political context", "kingdom", "empire", "background"))
