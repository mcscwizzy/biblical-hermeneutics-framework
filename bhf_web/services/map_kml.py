"""Small, dependency-free KML serializers for local map study exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable
from xml.sax.saxutils import escape


def _coordinate(value: Any, minimum: float, maximum: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if minimum <= number <= maximum else None


def usable_coordinates(item: dict[str, Any]) -> tuple[float, float] | None:
    latitude = _coordinate(item.get("latitude", item.get("lat")), -90, 90)
    longitude = _coordinate(item.get("longitude", item.get("lng")), -180, 180)
    return (longitude, latitude) if latitude is not None and longitude is not None else None


def _text(value: Any) -> str:
    return escape(str(value or ""))


def _description(item: dict[str, Any], references: Iterable[str] = ()) -> str:
    parts = [item.get("description"), item.get("summary"), item.get("modern_location"), item.get("modernLocation")]
    reference_values = [str(reference) for reference in references if reference]
    if reference_values:
        parts.append("Biblical references: " + ", ".join(reference_values))
    return "\n".join(str(part) for part in parts if part)


def _placemark(name: str, description: str = "", coordinates: tuple[float, float] | None = None) -> str:
    if coordinates is None:
        return ""
    longitude, latitude = coordinates
    return (
        "<Placemark>"
        f"<name>{_text(name)}</name>"
        f"<description>{_text(description)}</description>"
        "<Point>"
        f"<coordinates>{longitude:.6f},{latitude:.6f},0</coordinates>"
        "</Point>"
        "</Placemark>"
    )


def _geometry_markup(name: str, description: str, geometry: dict[str, Any]) -> str:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "LineString" and isinstance(coordinates, list):
        values = [f"{point[0]},{point[1]},0" for point in coordinates if isinstance(point, list) and len(point) >= 2]
        if len(values) >= 2:
            return f"<Placemark><name>{_text(name)}</name><description>{_text(description)}</description><LineString><tessellate>1</tessellate><coordinates>{' '.join(values)}</coordinates></LineString></Placemark>"
    if geometry_type == "MultiLineString" and isinstance(coordinates, list):
        lines = []
        for line in coordinates:
            lines.append(_geometry_markup(name, description, {"type": "LineString", "coordinates": line}))
        return "".join(lines)
    if geometry_type == "Polygon" and isinstance(coordinates, list) and coordinates:
        ring = coordinates[0]
        values = [f"{point[0]},{point[1]},0" for point in ring if isinstance(point, list) and len(point) >= 2]
        if len(values) >= 3:
            return f"<Placemark><name>{_text(name)}</name><description>{_text(description)}</description><Polygon><outerBoundaryIs><LinearRing><coordinates>{' '.join(values)}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>"
    return ""


def _document(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2">'
        f"<Document><name>{_text(title)}</name>{body}</Document></kml>"
    )


def place_kml(place: dict[str, Any]) -> str:
    references = [entry.get("reference") for entry in place.get("related_references", [])]
    body = _placemark(place.get("name", "Biblical place"), _description(place, references), usable_coordinates(place))
    return _document(place.get("name", "Biblical place"), body)


def route_kml(route: dict[str, Any]) -> str:
    references = [entry.get("reference") for entry in route.get("scripture_links", [])]
    geometry = route.get("geojson", {}).get("geometry", {})
    body = _geometry_markup(route.get("name", "Map route"), _description(route, references), geometry)
    return _document(route.get("name", "Map route"), body)


def journey_kml(journey: dict[str, Any]) -> str:
    stops = sorted(
        [stop for stop in journey.get("stops", []) if usable_coordinates(stop)],
        key=lambda stop: (stop.get("order", 10**9), str(stop.get("id", ""))),
    )
    body = [f"<Folder><name>{_text(journey.get('title', 'Biblical journey'))}</name>"]
    for index, stop in enumerate(stops, start=1):
        references = stop.get("passages", [])
        body.append(_placemark(f"{index}. {stop.get('name', 'Journey stop')}", _description(stop, references), usable_coordinates(stop)))
    if len(stops) >= 2:
        coordinates = " ".join(f"{usable_coordinates(stop)[0]:.6f},{usable_coordinates(stop)[1]:.6f},0" for stop in stops)
        body.append(
            f"<Placemark><name>{_text(journey.get('title', 'Approximate route'))} — approximate route</name>"
            f"<description>{_text(journey.get('caution') or 'Approximate study route; not an exact historical path.')}</description>"
            f"<LineString><tessellate>1</tessellate><coordinates>{coordinates}</coordinates></LineString></Placemark>"
        )
    body.append("</Folder>")
    return _document(journey.get("title", "Biblical journey"), "".join(body))


def load_journey(path: str | Path, journey_id: str) -> dict[str, Any] | None:
    journey_path = Path(path) / f"{journey_id}.json"
    if not journey_path.is_file():
        return None
    try:
        journey = json.loads(journey_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return journey if isinstance(journey, dict) and journey.get("id") == journey_id else None
