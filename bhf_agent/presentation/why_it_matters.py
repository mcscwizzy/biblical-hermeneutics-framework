"""Evidence-authored significance cards without model-created application."""

from __future__ import annotations

import re

from .models import DigDeeperAction, EvidenceBundle, EvidenceItem, PresentationCard
from .ranking import RankedEvidence


def build_why_it_matters_card(
    bundle: EvidenceBundle,
    ranked: list[RankedEvidence],
) -> PresentationCard | None:
    """Return one explicit passage-significance card, never an inferred substitute."""

    for candidate in ranked:
        item = candidate.item
        if item.relevance_metadata.get("presentation_role") != "significance":
            continue
        supporting_ids = [
            str(value)
            for value in item.relevance_metadata.get("supports_evidence_ids") or []
            if str(value) in bundle.evidence_by_id
        ]
        evidence_ids = list(dict.fromkeys([*supporting_ids, item.id]))
        related = [
            entity_id
            for entity_id in item.related_entity_ids
            if entity_id in bundle.entities_by_id
        ]
        return PresentationCard(
            id="why-it-matters-" + _slug(item.id),
            type="why_it_matters",
            headline="Why It Matters Here",
            body=_truncate(item.claim, 360),
            evidence_ids=evidence_ids,
            confidence=item.confidence,
            interpretation_level=_interpretation_level(item.relevance_metadata),
            related_entity_ids=related,
            map_focus=None,
            dig_deeper_actions=_actions(bundle, item, related),
        )
    return None


def _actions(
    bundle: EvidenceBundle,
    item: EvidenceItem,
    related: list[str],
) -> list[DigDeeperAction]:
    evidence_id = item.id
    category = item.category
    actions = [
        DigDeeperAction(type="show_evidence", label="View the evidence", target_id=evidence_id)
    ]
    map_ids = set(bundle.geography.get("map_location_refs") or [])
    for entity_id in related:
        entity = bundle.entities_by_id[entity_id]
        if entity.type == "place" and entity_id in map_ids:
            actions.append(
                DigDeeperAction(
                    type="open_map",
                    label=f"Show {entity.title} on the map",
                    target_id=entity_id,
                )
            )
        elif entity.type == "place":
            actions.append(
                DigDeeperAction(
                    type="explore_place",
                    label=f"Explore {entity.title}",
                    target_id=entity_id,
                )
            )
        elif entity.type == "person":
            actions.append(
                DigDeeperAction(
                    type="explore_person",
                    label=f"Explore {entity.title}",
                    target_id=entity_id,
                )
            )
        elif entity.type in {"artifact", "archaeology"}:
            actions.append(
                DigDeeperAction(
                    type="archaeology",
                    label="Explore the archaeology",
                    target_id=entity_id,
                )
            )
        if len(actions) >= 3:
            return actions
    if category == "language":
        actions.append(DigDeeperAction(type="explore_language", label="Explore the language"))
    elif category in {"history", "chronology", "politics"}:
        actions.append(DigDeeperAction(type="explore_history", label="Explore the historical setting"))
    elif category == "archaeology" and len(actions) == 1:
        actions.append(DigDeeperAction(type="archaeology", label="Explore the archaeology"))
    return actions[:3]


def _interpretation_level(metadata: dict[str, object]) -> str:
    certainty = str(metadata.get("certainty") or "").casefold()
    dispute = str(metadata.get("dispute_status") or "").casefold()
    if certainty in {"disputed", "speculative", "insufficient_evidence"}:
        return "disputed"
    if dispute and dispute not in {"not_disputed", "consensus", "broad-consensus"}:
        return "disputed"
    return "inference"


def _truncate(value: str, maximum: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= maximum:
        return text
    shortened = text[: maximum - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened + "…"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "evidence"
