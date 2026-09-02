"""Deterministic, offline presentation using the same ranked evidence."""

from __future__ import annotations

import re

from .models import (
    PRESENTATION_SCHEMA_VERSION,
    DigDeeperAction,
    EvidenceBundle,
    GeneratedFrom,
    PresentationCard,
    PresentationPacket,
)
from .ranking import RankedEvidence, rank_evidence
from .walk_the_land import build_walk_the_land_card
from .why_it_matters import build_why_it_matters_card


DETERMINISTIC_PROMPT_VERSION = "deterministic-v4"


def deterministic_presentation(
    bundle: EvidenceBundle,
    ranked: list[RankedEvidence] | None = None,
    *,
    maximum_cards: int = 3,
) -> PresentationPacket:
    candidates = list(ranked if ranked is not None else rank_evidence(bundle))
    ordinary = [
        value
        for value in candidates
        if not _is_map_candidate(bundle, value)
        and value.item.relevance_metadata.get("presentation_role") != "significance"
    ]
    # Reserve the first slot for ordinary context whenever it exists. Map and
    # significance cards must not crowd useful Did You Know evidence out.
    selected = _diverse_candidates(ordinary, 1 if maximum_cards > 0 else 0)
    cards = [_card(bundle, candidate) for candidate in selected]
    used_evidence = {item.item.id for item in selected}

    walk_card = (
        build_walk_the_land_card(bundle, candidates)
        if len(cards) < maximum_cards
        else None
    )
    if walk_card is not None:
        cards.append(walk_card)
        used_evidence.update(walk_card.evidence_ids)
    why_card = (
        build_why_it_matters_card(bundle, candidates)
        if len(cards) < maximum_cards
        else None
    )
    if why_card is not None:
        cards.append(why_card)
        used_evidence.update(why_card.evidence_ids)

    remaining = [value for value in ordinary if value.item.id not in used_evidence]
    cards.extend(
        _card(bundle, candidate)
        for candidate in _diverse_candidates(remaining, maximum_cards - len(cards))
    )
    return PresentationPacket(
        passage_ref=bundle.passage_ref,
        cards=cards,
        generated_from=GeneratedFrom(
            evidence_hash=bundle.evidence_hash,
            evidence_bundle_version=bundle.version,
            presentation_schema_version=PRESENTATION_SCHEMA_VERSION,
            prompt_version=DETERMINISTIC_PROMPT_VERSION,
            model="deterministic",
        ),
    )


def _is_map_candidate(bundle: EvidenceBundle, value: RankedEvidence) -> bool:
    item = value.item
    if item.category != "geography":
        return False
    metadata = item.relevance_metadata
    if str(metadata.get("source_kind") or "").startswith("passage_map_"):
        return True
    resource_id = str(metadata.get("map_resource_id") or "")
    available = {
        *bundle.geography.get("map_location_refs", []),
        *bundle.geography.get("map_route_refs", []),
    }
    return resource_id in available or any(
        entity_id in available for entity_id in item.related_entity_ids
    )


def _diverse_candidates(values: list[RankedEvidence], maximum: int) -> list[RankedEvidence]:
    if maximum <= 0:
        return []
    selected: list[RankedEvidence] = []
    seen_categories: set[str] = set()
    for value in values:
        if value.item.category in seen_categories and len(values) > maximum:
            continue
        selected.append(value)
        seen_categories.add(value.item.category)
        if len(selected) >= maximum:
            return selected
    for value in values:
        if value not in selected:
            selected.append(value)
        if len(selected) >= maximum:
            break
    return selected


def _card(bundle: EvidenceBundle, ranked: RankedEvidence) -> PresentationCard:
    item = ranked.item
    body = _truncate(item.claim, 360)
    related = [entity_id for entity_id in item.related_entity_ids if entity_id in bundle.entities_by_id]
    return PresentationCard(
        id="did-you-know-" + _slug(item.id),
        type="did_you_know",
        headline=_headline(item.claim, item.category),
        body=body,
        evidence_ids=[item.id],
        confidence=item.confidence,
        interpretation_level=_interpretation_level(item.relevance_metadata),
        related_entity_ids=related,
        map_focus=_map_focus(bundle, related),
        dig_deeper_actions=_actions(bundle, item.id, item.category, related),
    )


def _actions(
    bundle: EvidenceBundle,
    evidence_id: str,
    category: str,
    related: list[str],
) -> list[DigDeeperAction]:
    actions = [DigDeeperAction(type="show_evidence", label="View the evidence", target_id=evidence_id)]
    map_ids = set(bundle.geography.get("map_location_refs") or [])
    for entity_id in related:
        entity = bundle.entities_by_id[entity_id]
        if entity.type == "person":
            actions.append(DigDeeperAction(type="explore_person", label=f"Explore {entity.title}", target_id=entity_id))
        elif entity.type == "place":
            actions.append(DigDeeperAction(type="explore_place", label=f"Explore {entity.title}", target_id=entity_id))
            if entity_id in map_ids:
                actions.append(DigDeeperAction(type="open_map", label="Show this location", target_id=entity_id))
        elif entity.type in {"event", "timeline"}:
            actions.append(DigDeeperAction(type="explore_event", label=f"Explore {entity.title}", target_id=entity_id))
        elif entity.type in {"artifact", "archaeology"}:
            actions.append(DigDeeperAction(type="archaeology", label="Explore the archaeology", target_id=entity_id))
    if category == "archaeology" and not any(action.type == "archaeology" for action in actions):
        actions.append(DigDeeperAction(type="archaeology", label="Explore the archaeology"))
    elif category == "language":
        actions.append(DigDeeperAction(type="explore_language", label="Explore the language"))
    elif category in {"history", "chronology", "politics"}:
        actions.append(DigDeeperAction(type="explore_history", label="Explore the historical setting"))
    return actions[:4]


def _map_focus(bundle: EvidenceBundle, related: list[str]) -> dict[str, str] | None:
    map_ids = set(bundle.geography.get("map_location_refs") or [])
    for entity_id in related:
        if entity_id in map_ids:
            return {"kind": "place", "target_id": entity_id}
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


def _headline(claim: str, category: str) -> str:
    first_clause = re.split(r"[.;:]", claim, maxsplit=1)[0].strip()
    words = first_clause.split()
    if 4 <= len(words) <= 11 and len(first_clause) <= 92:
        return first_clause.rstrip(".?!")
    labels = {
        "culture": "A cultural detail worth noticing",
        "geography": "The setting changes how this reads",
        "history": "A historical detail worth noticing",
        "archaeology": "Material evidence to explore",
        "language": "A language detail worth noticing",
        "politics": "Power in the background",
        "economics": "The economics behind the passage",
        "social": "The social world behind the passage",
        "chronology": "A timing detail worth noticing",
    }
    return labels.get(category, "A detail worth noticing")


def _truncate(value: str, maximum: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= maximum:
        return text
    shortened = text[: maximum - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened + "…"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "evidence"
