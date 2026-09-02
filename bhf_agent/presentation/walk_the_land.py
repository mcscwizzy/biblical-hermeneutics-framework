"""Deterministic geography presentation over stable map references."""

from __future__ import annotations

import re

from .models import DigDeeperAction, EvidenceBundle, PresentationCard
from .ranking import RankedEvidence


def build_walk_the_land_card(
    bundle: EvidenceBundle,
    ranked: list[RankedEvidence],
) -> PresentationCard | None:
    """Return one useful, passage-grounded map card or no card."""

    places = {
        str(item.get("id")): item
        for item in bundle.geography.get("places") or []
        if item.get("id")
    }
    routes = {
        str(item.get("id")): item
        for item in bundle.geography.get("routes") or []
        if item.get("id")
    }
    for candidate in ranked:
        if candidate.item.category != "geography":
            continue
        match = _map_match(candidate, places, routes)
        if match is None:
            continue
        kind, target_id, resource = match
        title = str(resource.get("title") or resource.get("name") or target_id).strip()
        if not title:
            continue
        action_type = "show_route" if kind == "route" else "open_map"
        action_label = f"Trace {title}" if kind == "route" else f"Show {title} on the map"
        related = [target_id] if target_id in bundle.entities_by_id else []
        return PresentationCard(
            id=f"walk-the-land-{_slug(kind)}-{_slug(target_id)}",
            type="walk_the_land",
            headline=f"Walk the Land: {title}",
            body=_truncate(candidate.item.claim, 360),
            evidence_ids=[candidate.item.id],
            confidence=candidate.item.confidence,
            interpretation_level=_interpretation_level(candidate.item.relevance_metadata),
            related_entity_ids=related,
            map_focus={"kind": kind, "target_id": target_id},
            dig_deeper_actions=[
                DigDeeperAction(type=action_type, label=action_label, target_id=target_id),
                DigDeeperAction(
                    type="show_evidence",
                    label="View the evidence",
                    target_id=candidate.item.id,
                ),
            ],
        )
    return None


def _map_match(
    candidate: RankedEvidence,
    places: dict[str, dict[str, object]],
    routes: dict[str, dict[str, object]],
) -> tuple[str, str, dict[str, object]] | None:
    metadata = candidate.item.relevance_metadata
    resource_id = str(metadata.get("map_resource_id") or "").strip()
    resource_kind = str(metadata.get("map_resource_kind") or "").strip()
    if resource_kind == "place" and resource_id in places:
        return "place", resource_id, places[resource_id]
    if resource_kind == "route" and resource_id in routes:
        return "route", resource_id, routes[resource_id]
    for entity_id in candidate.item.related_entity_ids:
        if entity_id in places:
            return "place", entity_id, places[entity_id]
    return None


def _interpretation_level(metadata: dict[str, object]) -> str:
    certainty = str(metadata.get("certainty") or "").casefold()
    dispute = str(metadata.get("dispute_status") or "").casefold()
    assertion = str(metadata.get("assertion_type") or "").casefold()
    if certainty in {"disputed", "speculative", "insufficient_evidence"}:
        return "disputed"
    if dispute and dispute not in {"not_disputed", "consensus", "broad-consensus"}:
        return "disputed"
    if assertion in {"inference", "scholarly-reconstruction"}:
        return "inference"
    return "fact"


def _truncate(value: str, maximum: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= maximum:
        return text
    shortened = text[: maximum - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened + "…"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "map"
