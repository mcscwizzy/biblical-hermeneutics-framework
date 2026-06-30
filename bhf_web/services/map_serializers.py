"""Serialization helpers for map service responses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhf_agent.bible import testament_for_book
from bhf_agent.study_db import (
    list_archaeology_items,
    list_biblical_places,
    list_map_routes,
    list_political_context_layers,
    list_political_context_references,
    list_place_references,
    list_route_references,
)

from .map_matching import format_reference as _format_reference, periods_overlap, route_is_near_place


def manuscript_item_to_marker(
    item: dict[str, Any],
    list_manuscript_scripture_links: Any,
    path: str | Path | None = None,
) -> dict[str, Any]:
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


def place_to_marker(
    place: dict[str, Any],
    list_place_references: Any,
    related_passages_for_place: Any,
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
        "related_passages": related_passages_for_place(place, period=period, path=path),
        "reference_count": len(references),
        "has_coordinates": latitude is not None and longitude is not None,
    }


def route_to_item(
    route: dict[str, Any],
    list_route_references: Any,
    path: str | Path | None = None,
) -> dict[str, Any]:
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


def historical_layer_to_item(layer: dict[str, Any]) -> dict[str, Any]:
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


def political_context_to_item(
    layer: dict[str, Any],
    list_political_context_references: Any,
    path: str | Path | None = None,
) -> dict[str, Any]:
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


def archaeology_site_to_markers(
    site: dict[str, Any],
    list_archaeology_items: Any,
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


def related_passages_for_place(
    place: dict[str, Any],
    list_biblical_places_fn: Any = list_biblical_places,
    list_map_routes_fn: Any = list_map_routes,
    list_political_context_layers_fn: Any = list_political_context_layers,
    list_place_references_fn: Any = list_place_references,
    list_route_references_fn: Any = list_route_references,
    list_political_context_references_fn: Any = list_political_context_references,
    period: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    direct_refs = (
        list_place_references_fn(place["id"], path=path)
        if path
        else list_place_references_fn(place["id"])
    )
    direct_entries = [
        related_passage_entry(
            reference,
            relationship_type=reference["relationship_type"],
            relationship_label=relationship_label(reference["relationship_type"]),
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

    groups: list[dict[str, Any]] = [
        {
            "group_type": "directly_mentioned",
            "label": "Directly Mentioned",
            "summary": "Passages that explicitly name this place.",
            "passages": direct_entries,
            "count": len(direct_entries),
            "testament_groups": group_passages_by_testament(direct_entries),
        }
    ]

    seen_keys = {passage_key(entry) for entry in direct_entries}

    region_entries: list[dict[str, Any]] = []
    place_region = str(place.get("ancient_region") or "").strip()
    if place_region:
        other_places = (
            list_biblical_places_fn(period=period, path=path)
            if path
            else list_biblical_places_fn(period=period)
        )
        for other_place in other_places:
            if other_place["id"] == place["id"] or other_place.get("ancient_region") != place_region:
                continue
            other_refs = (
                list_place_references_fn(other_place["id"], path=path)
                if path
                else list_place_references_fn(other_place["id"])
            )
            for reference in other_refs:
                entry = related_passage_entry(
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
                if passage_key(entry) in seen_keys:
                    continue
                seen_keys.add(passage_key(entry))
                region_entries.append(entry)
    if region_entries:
        groups.append(
            {
                "group_type": "same_region",
                "label": f"Same Region: {place_region}" if place_region else "Same Region",
                "summary": "Passages tied to other places in the same ancient region.",
                "passages": sorted_related_passages(region_entries),
                "count": len(region_entries),
            }
        )

    route_entries: list[dict[str, Any]] = []
    place_coords = (place.get("latitude"), place.get("longitude"))
    if place_coords[0] is not None and place_coords[1] is not None:
        routes = (
            list_map_routes_fn(period=period, path=path)
            if path
            else list_map_routes_fn(period=period)
        )
        for route in routes:
            if not periods_overlap(place.get("periods", []), route.get("periods", [])):
                continue
            if not route_is_near_place(route, float(place_coords[0]), float(place_coords[1])):
                continue
            route_refs = (
                list_route_references_fn(route["id"], path=path)
                if path
                else list_route_references_fn(route["id"])
            )
            for reference in route_refs:
                entry = related_passage_entry(
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
                if passage_key(entry) in seen_keys:
                    continue
                seen_keys.add(passage_key(entry))
                route_entries.append(entry)
    if route_entries:
        groups.append(
            {
                "group_type": "same_route",
                "label": "Same Route",
                "summary": "Passages connected to a curated route that passes near this place.",
                "passages": sorted_related_passages(route_entries),
                "count": len(route_entries),
            }
        )

    context_entries: list[dict[str, Any]] = []
    layers = (
        list_political_context_layers_fn(period=period, path=path)
        if path
        else list_political_context_layers_fn(period=period)
    )
    for layer in layers:
        if not periods_overlap(place.get("periods", []), layer.get("periods", [])):
            continue
        links = (
            list_political_context_references_fn(layer["id"], path=path)
            if path
            else list_political_context_references_fn(layer["id"])
        )
        for reference in links:
            entry = related_passage_entry(
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
            if passage_key(entry) in seen_keys:
                continue
            seen_keys.add(passage_key(entry))
            context_entries.append(entry)
    if context_entries:
        groups.append(
            {
                "group_type": "same_empire_period",
                "label": "Same Empire / Period",
                "summary": "Passages tied to the broader political background of this place.",
                "passages": sorted_related_passages(context_entries),
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


def related_passage_entry(
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


def group_passages_by_testament(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    order = ["Old Testament", "New Testament", "Other"]
    for passage in passages:
        testament = passage.get("testament") or "Other"
        buckets.setdefault(testament, []).append(passage)
    return [
        {
            "testament": testament,
            "label": f"{testament} location links" if testament in {"Old Testament", "New Testament"} else "Other location links",
            "passages": sorted_related_passages(buckets[testament]),
            "count": len(buckets[testament]),
        }
        for testament in order
        if testament in buckets
    ]


def sorted_related_passages(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def passage_key(entry: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    return (
        entry.get("book"),
        entry.get("chapter"),
        entry.get("verse_start"),
        entry.get("verse_end"),
    )


def relationship_label(value: str) -> str:
    labels = {
        "directly_named": "Directly mentioned",
        "same_region": "Same region",
        "same_route": "Same route",
        "same_empire_period": "Same empire / period",
        "historical_context": "Historical context",
        "textual_witness": "Textual witness",
    }
    return labels.get(value, value.replace("_", " ").strip().title() or "Related passage")
