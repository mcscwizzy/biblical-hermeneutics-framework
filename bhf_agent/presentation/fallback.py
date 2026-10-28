"""Deterministic, offline presentation using the same ranked evidence."""

from __future__ import annotations

import re
from dataclasses import replace

from .models import (
    PRESENTATION_SCHEMA_VERSION,
    DigDeeperAction,
    EvidenceBundle,
    EvidenceItem,
    GeneratedFrom,
    PresentationCard,
    PresentationPacket,
)
from .ranking import RankedEvidence, presentation_relationship, rank_evidence
from .walk_the_land import build_walk_the_land_card


DETERMINISTIC_PROMPT_VERSION = "deterministic-v5"
_WORD_RE = re.compile(r"[a-z0-9]+")
_SUPPORT_STOP_WORDS = frozenset(
    {
        "a", "about", "after", "also", "and", "as", "at", "be", "becomes",
        "by", "for", "from", "in", "into", "is", "it", "later", "of", "on",
        "or", "that", "the", "their", "this", "to", "with",
    }
)

# These pairs have been reviewed as describing the same discovery. A shared
# word, source and passage alone cannot establish a semantic association.
_REVIEWED_SUPPORT_PAIRS = frozenset({
    ("jonah", "jonah-great-fish", "jonah-three-days"),
})


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
        and not (
            value.item.relevance_metadata.get("presentation_role") == "significance"
            and value.item.relevance_metadata.get("supports_evidence_ids")
        )
    ]
    # Reserve the first slot for ordinary context whenever it exists. Derived
    # significance duplicates stay in evidence metadata; independent sourced
    # items such as archaeology remain eligible as ordinary discoveries.
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


def attach_relevant_support_evidence(
    bundle: EvidenceBundle,
    packet: PresentationPacket,
    ranked: list[RankedEvidence],
) -> PresentationPacket:
    """Cite one tightly related dig-deeper record on an existing discovery.

    The supporting item must already be inside the deterministic candidate
    shortlist. It must have the same CKL parent, exact verse anchors, and at
    least one shared subject term and source as a selected direct-context
    discovery, and the record pair must have been reviewed. This adds evidence
    to a card without allocating another card.
    """

    cited_ids = {
        evidence_id
        for card in packet.cards
        for evidence_id in card.evidence_ids
    }
    support_candidates = [
        candidate.item
        for candidate in ranked
        if candidate.item.id not in cited_ids
        and candidate.item.relevance_metadata.get("presentation_role") == "dig_deeper"
        and candidate.item.relevance_metadata.get("source_kind")
        in {"ckl_claim", "ckl_evidence_item"}
    ]
    if not support_candidates:
        return packet

    evidence_by_id = bundle.evidence_by_id
    for card_index, card in enumerate(packet.cards):
        if card.type != "did_you_know":
            continue
        primary_items = [
            evidence_by_id[evidence_id]
            for evidence_id in card.evidence_ids
            if evidence_id in evidence_by_id
        ]
        for primary in primary_items:
            support = next(
                (
                    item
                    for item in support_candidates
                    if item.id not in cited_ids
                    and _is_relevant_support(bundle, primary, item)
                ),
                None,
            )
            if support is None:
                continue
            cards = list(packet.cards)
            cards[card_index] = replace(
                card,
                evidence_ids=[*card.evidence_ids, support.id],
            )
            return replace(packet, cards=cards)
    return packet


def _is_relevant_support(
    bundle: EvidenceBundle,
    primary: EvidenceItem,
    support: EvidenceItem,
) -> bool:
    primary_metadata = primary.relevance_metadata
    support_metadata = support.relevance_metadata
    parent_id = str(primary_metadata.get("parent_object_id") or "")
    if not parent_id or support_metadata.get("parent_object_id") != parent_id:
        return False
    if (parent_id, primary.id, support.id) not in _REVIEWED_SUPPORT_PAIRS:
        return False
    if primary_metadata.get("source_kind") not in {"ckl_claim", "ckl_evidence_item"}:
        return False
    if primary_metadata.get("semantic_relationship") != "DIRECT_CONTEXT":
        return False
    if presentation_relationship(bundle, support) not in {
        "LATER_RECEPTION",
        "COMPARATIVE_CONTEXT",
        "INTERTEXTUAL_REUSE",
    }:
        return False
    if primary_metadata.get("applicability_scope") != "passage":
        return False
    if support_metadata.get("applicability_scope") != "passage":
        return False
    if primary_metadata.get("anchor_specificity") != "verse":
        return False
    if support_metadata.get("anchor_specificity") != "verse":
        return False
    primary_anchors = {
        " ".join(str(anchor).split()).casefold()
        for anchor in primary.passage_anchors
    }
    support_anchors = {
        " ".join(str(anchor).split()).casefold()
        for anchor in support.passage_anchors
    }
    if not primary_anchors or primary_anchors != support_anchors:
        return False
    if not set(primary.source_ids).intersection(support.source_ids):
        return False
    parent_terms = set(
        _WORD_RE.findall(str(primary_metadata.get("parent_title") or "").casefold())
    )
    primary_terms = set(_WORD_RE.findall(primary.claim.casefold()))
    support_terms = set(_WORD_RE.findall(support.claim.casefold()))
    shared_terms = primary_terms.intersection(support_terms) - parent_terms - _SUPPORT_STOP_WORDS
    return bool(shared_terms)


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
    interpretation_level = _interpretation_level(item.relevance_metadata)
    if (
        item.relevance_metadata.get("presentation_role") == "significance"
        and interpretation_level == "fact"
    ):
        interpretation_level = "inference"
    return PresentationCard(
        id="did-you-know-" + _slug(item.id),
        type="did_you_know",
        headline=_headline(
            item.claim,
            {
                **item.relevance_metadata,
                "presentation_relationship": presentation_relationship(bundle, item),
            },
        ),
        body=body,
        evidence_ids=[item.id],
        confidence=item.confidence,
        interpretation_level=interpretation_level,
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


def _headline(
    claim: str,
    metadata: dict[str, object] | None = None,
) -> str:
    first_clause = re.split(r"[.;]", claim, maxsplit=1)[0].strip()
    excerpt = first_clause or " ".join(str(claim or "").split())
    relationship = str(
        (metadata or {}).get("presentation_relationship")
        or (metadata or {}).get("semantic_relationship")
        or ""
    ).upper()
    if excerpt.casefold().startswith(("do not ", "avoid ", "must not ")):
        relationship = ""
    prefix = {
        "COMPARATIVE_CONTEXT": "Comparative evidence",
        "LATER_RECEPTION": (
            "Second Temple reception"
            if re.search(r"\b(?:Second Temple|1 Enoch|Jubilees)\b", claim, re.IGNORECASE)
            else "Later biblical reception"
        ),
        "INTERTEXTUAL_REUSE": "Biblical reuse",
    }.get(relationship)
    if prefix:
        excerpt = _truncate(excerpt, max(24, 96 - len(prefix) - 2))
        return f"{prefix}: {excerpt}".rstrip(".?!")
    return _truncate(excerpt, 96).rstrip(".?!")


def _truncate(value: str, maximum: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= maximum:
        return text
    shortened = text[: maximum - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened + "…"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "evidence"
