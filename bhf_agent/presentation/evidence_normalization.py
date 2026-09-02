"""Low-level normalization helpers for EvidenceBundle construction."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from .models import mapping


ENTITY_BUCKET_BY_TYPE = {
    "person": "people",
    "place": "places",
    "people_group": "groups",
    "people-group": "groups",
    "group": "groups",
    "institution": "groups",
    "event": "events",
    "timeline": "events",
    "artifact": "artifacts",
    "archaeology": "artifacts",
}

LEGACY_FIELDS = {
    "historical_context": "history",
    "historical_setting": "history",
    "ancient_near_east_context": "culture",
    "hebraic_worldview": "culture",
    "second_temple_context": "culture",
    "original_audience": "social",
    "date_ranges": "chronology",
    "timeline": "chronology",
    "key_places": "geography",
    "archaeology": "archaeology",
}

_EVIDENCE_CATEGORY = {
    "artifact": "archaeology",
    "archaeological-site": "archaeology",
    "inscription": "archaeology",
    "manuscript": "language",
    "material-culture": "archaeology",
    "geography-environment": "geography",
    "historical-event": "history",
    "historical-period": "chronology",
    "cultural-practice": "culture",
    "people-group": "social",
    "institution": "social",
    "worldview-concept": "culture",
    "literary-convention": "culture",
    "ancient-text": "history",
    "primary-source": "history",
    "secondary-source": "history",
    "biblical_text": "history",
    "historical_cultural": "culture",
    "lexical": "language",
    "archaeology": "archaeology",
    "literary": "culture",
    "biblical_theology": "culture",
}


def normalize_geography(data: Mapping[str, Any]) -> dict[str, Any]:
    places = [_geography_record(value) for value in sequence(data.get("places"))]
    routes = [_geography_record(value) for value in sequence(data.get("routes"))]
    return {
        "places": [value for value in places if value.get("id")],
        "routes": [value for value in routes if value.get("id")],
        "regions": [_geography_record(value) for value in sequence(data.get("regions"))],
        "political_territories": [
            _geography_record(value) for value in sequence(data.get("political_territories"))
        ],
        "map_location_refs": unique(text(value.get("id")) for value in places),
        "map_route_refs": unique(text(value.get("id")) for value in routes),
    }


def evidence_category(value: Any, claim: str = "") -> str:
    normalized = text(value).casefold().replace("-", "_")
    claim_terms = set(re.findall(r"[a-z]+", claim.casefold()))
    if claim_terms.intersection(
        {"economic", "economics", "economy", "market", "markets", "wage", "wages", "wealth", "provision", "provisions", "provisioning"}
    ):
        return "economics"
    if claim_terms.intersection(
        {"geography", "terrain", "route", "routes", "shore", "lake", "river", "mountain", "eastern", "western"}
    ):
        return "geography"
    if claim_terms.intersection(
        {"political", "politics", "empire", "imperial", "governor", "kingship"}
    ):
        return "politics"
    direct = {
        "culture", "geography", "history", "archaeology", "language",
        "politics", "economics", "social", "chronology",
    }
    if normalized in direct:
        return normalized
    return _EVIDENCE_CATEGORY.get(
        normalized,
        _EVIDENCE_CATEGORY.get(normalized.replace("_", "-"), "culture"),
    )


def certainty_confidence(certainty: Any, fallback: str) -> str:
    normalized = text(certainty).casefold()
    if normalized in {"textually_explicit", "strong_consensus"}:
        return "high"
    if normalized in {"probable", "plausible"}:
        return "medium"
    if normalized in {"disputed", "speculative", "insufficient_evidence"}:
        return "low"
    return fallback


def confidence(value: Any) -> str:
    normalized = text(value).casefold()
    if normalized in {"high", "strong", "certain"}:
        return "high"
    if normalized in {"medium", "likely", "probable"}:
        return "medium"
    return "low"


def sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def strings(value: Any) -> list[str]:
    return unique(text(item) for item in sequence(value))


def unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = text(value)
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return text(value.get("claim") or value.get("note") or value.get("summary") or value.get("title"))
    return " ".join(str(value).split())


def number(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _geography_record(value: Any) -> dict[str, Any]:
    data = mapping(value)
    if not data and value:
        data = {"id": text(value), "title": text(value)}
    return {
        key: item
        for key, item in data.items()
        if item not in (None, "") and key not in {"geojson", "media"}
    }
