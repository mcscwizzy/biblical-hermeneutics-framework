"""Strict validation for untrusted PresentationPacket JSON."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .models import (
    ACTION_TYPES,
    CARD_TYPES,
    CONFIDENCE_VALUES,
    INTERPRETATION_LEVELS,
    DigDeeperAction,
    EvidenceBundle,
    GeneratedFrom,
    PresentationCard,
    PresentationPacket,
)


_DATE_RE = re.compile(
    r"(?<!\w)(?:(?:c\.?|ca\.?|circa|approximately|about)\s+)?"
    r"(?:(?:AD|CE|BC|BCE)\s+[1-9]\d{0,3}|[1-9]\d{0,3}\s*(?:AD|CE|BC|BCE))(?!\w)",
    re.IGNORECASE,
)
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class PresentationValidationResult:
    valid: bool
    packet: PresentationPacket | None
    errors: tuple[str, ...]


def validate_presentation_packet(
    value: Any,
    bundle: EvidenceBundle,
    *,
    maximum_cards: int = 3,
    maximum_body_length: int = 420,
    expected_prompt_version: str | None = None,
    expected_model: str | None = None,
) -> PresentationValidationResult:
    """Parse and validate a provider or cache result without repairing it."""

    errors: list[str] = []
    if not isinstance(value, Mapping):
        return PresentationValidationResult(False, None, ("presentation packet must be an object",))
    _unknown(value, {"passage_ref", "cards", "generated_from"}, "packet", errors)
    passage_ref = _required_text(value, "passage_ref", "packet", errors)
    if passage_ref != bundle.passage_ref:
        errors.append("packet passage_ref does not match the EvidenceBundle")
    cards_raw = value.get("cards")
    if not isinstance(cards_raw, list):
        errors.append("packet.cards must be a list")
        cards_raw = []
    if len(cards_raw) > maximum_cards:
        errors.append(f"packet.cards exceeds the configured maximum of {maximum_cards}")

    generated = _parse_generated_from(
        value.get("generated_from"),
        bundle,
        errors,
        expected_prompt_version=expected_prompt_version,
        expected_model=expected_model,
    )
    cards: list[PresentationCard] = []
    card_ids: set[str] = set()
    for index, raw_card in enumerate(cards_raw):
        card = _parse_card(
            raw_card,
            index,
            bundle,
            errors,
            maximum_body_length=maximum_body_length,
        )
        if card is None:
            continue
        if card.id in card_ids:
            errors.append(f'card[{index}] duplicates card id "{card.id}"')
        card_ids.add(card.id)
        cards.append(card)
    if sum(card.type == "walk_the_land" for card in cards) > 1:
        errors.append("packet.cards may contain at most one walk_the_land card")
    if sum(card.type == "why_it_matters" for card in cards) > 1:
        errors.append("packet.cards may contain at most one why_it_matters card")

    if errors or generated is None:
        return PresentationValidationResult(False, None, tuple(errors))
    return PresentationValidationResult(
        True,
        PresentationPacket(passage_ref=passage_ref, cards=cards, generated_from=generated),
        (),
    )


def _parse_generated_from(
    raw: Any,
    bundle: EvidenceBundle,
    errors: list[str],
    *,
    expected_prompt_version: str | None,
    expected_model: str | None,
) -> GeneratedFrom | None:
    if not isinstance(raw, Mapping):
        errors.append("packet.generated_from must be an object")
        return None
    fields = {
        "evidence_hash",
        "evidence_bundle_version",
        "presentation_schema_version",
        "prompt_version",
        "model",
    }
    _unknown(raw, fields, "generated_from", errors)
    values = {field: _required_text(raw, field, "generated_from", errors) for field in fields}
    if values["evidence_hash"] != bundle.evidence_hash:
        errors.append("generated_from.evidence_hash is stale or unsupported")
    if values["evidence_bundle_version"] != bundle.version:
        errors.append("generated_from.evidence_bundle_version does not match")
    if values["presentation_schema_version"] != "1.0":
        errors.append("generated_from.presentation_schema_version is unsupported")
    if expected_prompt_version and values["prompt_version"] != expected_prompt_version:
        errors.append("generated_from.prompt_version does not match")
    if expected_model and values["model"] != expected_model:
        errors.append("generated_from.model does not match")
    if any(not value for value in values.values()):
        return None
    return GeneratedFrom(**values)


def _parse_card(
    raw: Any,
    index: int,
    bundle: EvidenceBundle,
    errors: list[str],
    *,
    maximum_body_length: int,
) -> PresentationCard | None:
    label = f"card[{index}]"
    if not isinstance(raw, Mapping):
        errors.append(f"{label} must be an object")
        return None
    fields = {
        "id", "type", "headline", "body", "evidence_ids", "confidence",
        "interpretation_level", "related_entity_ids", "map_focus", "dig_deeper_actions",
    }
    _unknown(raw, fields, label, errors)
    card_id = _required_text(raw, "id", label, errors)
    card_type = _required_text(raw, "type", label, errors)
    headline = _required_text(raw, "headline", label, errors)
    body = _required_text(raw, "body", label, errors)
    confidence = _required_text(raw, "confidence", label, errors)
    interpretation = _required_text(raw, "interpretation_level", label, errors)
    if card_type not in CARD_TYPES:
        errors.append(f"{label}.type is invalid")
    if confidence not in CONFIDENCE_VALUES:
        errors.append(f"{label}.confidence is invalid")
    if interpretation not in INTERPRETATION_LEVELS:
        errors.append(f"{label}.interpretation_level is invalid")
    if len(headline) > 100:
        errors.append(f"{label}.headline exceeds 100 characters")
    if len(body) > maximum_body_length:
        errors.append(f"{label}.body exceeds {maximum_body_length} characters")

    evidence_ids = _string_list(raw.get("evidence_ids"), f"{label}.evidence_ids", errors)
    related_ids = _string_list(raw.get("related_entity_ids", []), f"{label}.related_entity_ids", errors)
    if not evidence_ids:
        errors.append(f"{label}.evidence_ids must cite at least one supplied item")
    unknown_evidence = [item_id for item_id in evidence_ids if item_id not in bundle.evidence_by_id]
    if unknown_evidence:
        errors.append(f"{label} cites unsupported evidence IDs: {', '.join(unknown_evidence)}")
    unknown_entities = [item_id for item_id in related_ids if item_id not in bundle.entities_by_id]
    if unknown_entities:
        errors.append(f"{label} cites unsupported entity IDs: {', '.join(unknown_entities)}")

    supplied = [bundle.evidence_by_id[item_id] for item_id in evidence_ids if item_id in bundle.evidence_by_id]
    if supplied and confidence in _CONFIDENCE_RANK:
        maximum_supported = min(_CONFIDENCE_RANK.get(item.confidence, 0) for item in supplied)
        if _CONFIDENCE_RANK[confidence] > maximum_supported:
            errors.append(f"{label}.confidence exceeds its cited evidence")
    if interpretation == "fact" and any(_is_disputed(item.relevance_metadata) for item in supplied):
        errors.append(f"{label} turns disputed evidence into fact")
    _validate_new_dates(headline + " " + body, supplied, label, errors)

    actions_raw = raw.get("dig_deeper_actions", [])
    if not isinstance(actions_raw, list):
        errors.append(f"{label}.dig_deeper_actions must be a list")
        actions_raw = []
    actions = [
        action
        for action_index, raw_action in enumerate(actions_raw)
        if (action := _parse_action(raw_action, label, action_index, bundle, supplied, errors)) is not None
    ]

    map_focus_raw = raw.get("map_focus")
    map_focus: dict[str, Any] | None = None
    if map_focus_raw is not None:
        if not isinstance(map_focus_raw, Mapping):
            errors.append(f"{label}.map_focus must be an object or null")
        else:
            _unknown(map_focus_raw, {"kind", "target_id", "place_id"}, f"{label}.map_focus", errors)
            target_id = str(map_focus_raw.get("target_id") or map_focus_raw.get("place_id") or "").strip()
            kind = str(map_focus_raw.get("kind") or "place").strip()
            available = (
                set(bundle.geography.get("map_route_refs") or [])
                if kind == "route"
                else set(bundle.geography.get("map_location_refs") or [])
            )
            if kind not in {"place", "route"}:
                errors.append(f"{label}.map_focus kind is invalid")
            elif not target_id or target_id not in available:
                errors.append(f"{label}.map_focus references an unavailable map resource")
            map_focus = {"kind": kind, "target_id": target_id}
    if card_type == "walk_the_land":
        if map_focus is None:
            errors.append(f"{label}.walk_the_land requires map_focus")
        else:
            expected_action = "show_route" if map_focus["kind"] == "route" else "open_map"
            if not any(
                action.type == expected_action and action.target_id == map_focus["target_id"]
                for action in actions
            ):
                errors.append(f"{label}.walk_the_land requires a matching map action")
    if card_type == "why_it_matters":
        if not any(
            item.relevance_metadata.get("presentation_role") == "significance"
            for item in supplied
        ):
            errors.append(f"{label}.why_it_matters requires explicit significance evidence")
        if interpretation == "fact":
            errors.append(f"{label}.why_it_matters must be labeled inference or disputed")

    return PresentationCard(
        id=card_id,
        type=card_type,
        headline=headline,
        body=body,
        evidence_ids=evidence_ids,
        confidence=confidence,
        interpretation_level=interpretation,
        related_entity_ids=related_ids,
        map_focus=map_focus,
        dig_deeper_actions=actions,
    )


def _parse_action(
    raw: Any,
    card_label: str,
    index: int,
    bundle: EvidenceBundle,
    evidence: list[Any],
    errors: list[str],
) -> DigDeeperAction | None:
    label = f"{card_label}.dig_deeper_actions[{index}]"
    if not isinstance(raw, Mapping):
        errors.append(f"{label} must be an object")
        return None
    fields = {"type", "label", "target_id", "reference", "parameters"}
    _unknown(raw, fields, label, errors)
    action_type = _required_text(raw, "type", label, errors)
    action_label = _required_text(raw, "label", label, errors)
    target_id = str(raw.get("target_id") or "").strip() or None
    reference = str(raw.get("reference") or "").strip() or None
    parameters_raw = raw.get("parameters", {})
    if not isinstance(parameters_raw, Mapping):
        errors.append(f"{label}.parameters must be an object")
        parameters_raw = {}
    if action_type not in ACTION_TYPES:
        errors.append(f"{label}.type is invalid")
    elif not _action_is_fulfillable(action_type, target_id, reference, bundle, evidence):
        errors.append(f"{label} references a resource BHF cannot fulfill")
    return DigDeeperAction(
        type=action_type,
        label=action_label,
        target_id=target_id,
        reference=reference,
        parameters=dict(parameters_raw),
    )


def _action_is_fulfillable(
    action_type: str,
    target_id: str | None,
    reference: str | None,
    bundle: EvidenceBundle,
    evidence: list[Any],
) -> bool:
    entity = bundle.entities_by_id.get(target_id or "")
    geography_ids = set(bundle.geography.get("map_location_refs") or [])
    route_ids = set(bundle.geography.get("map_route_refs") or [])
    if action_type == "show_evidence":
        return target_id is None or target_id in bundle.evidence_by_id
    if action_type == "explore_person":
        return bool(entity and entity.type == "person")
    if action_type == "explore_place":
        return bool(entity and entity.type == "place")
    if action_type == "explore_event":
        return bool(entity and entity.type in {"event", "timeline"})
    if action_type == "open_map":
        return bool(target_id and target_id in geography_ids)
    if action_type == "show_route":
        return bool(target_id and target_id in route_ids)
    if action_type == "archaeology":
        return bool(
            (target_id and entity and entity.type in {"artifact", "archaeology"})
            or any(item.category == "archaeology" for item in evidence)
        )
    if action_type == "related_passages":
        anchors = {anchor for item in evidence for anchor in item.passage_anchors}
        return bool(reference and reference in anchors)
    if action_type == "explore_language":
        return any(item.category == "language" for item in evidence)
    if action_type == "explore_history":
        return any(item.category in {"history", "chronology", "politics"} for item in evidence)
    if action_type == "explore_custom":
        return bool(target_id and (target_id in bundle.entities_by_id or target_id in bundle.evidence_by_id))
    return False


def _validate_new_dates(text: str, evidence: list[Any], label: str, errors: list[str]) -> None:
    supplied_text = " ".join(
        [item.claim for item in evidence]
        + [str(value) for item in evidence for value in item.relevance_metadata.values()]
    )
    supplied_dates = {_date_key(match.group(0)) for match in _DATE_RE.finditer(supplied_text)}
    unsupported = sorted(
        {
            match.group(0)
            for match in _DATE_RE.finditer(text)
            if _date_key(match.group(0)) not in supplied_dates
        }
    )
    if unsupported:
        errors.append(f"{label} introduces unsupported date(s): {', '.join(unsupported)}")


def _date_key(value: str) -> tuple[str, int]:
    era_match = re.search(r"\b(BCE|BC|CE|AD)\b", value, re.IGNORECASE)
    number_match = re.search(r"\b([1-9]\d{0,3})\b", value)
    era = str(era_match.group(1) if era_match else "").upper()
    normalized_era = "BC" if era in {"BC", "BCE"} else "AD"
    return normalized_era, int(number_match.group(1) if number_match else 0)


def _is_disputed(metadata: Mapping[str, Any]) -> bool:
    certainty = str(metadata.get("certainty") or "").casefold()
    dispute = str(metadata.get("dispute_status") or "").casefold()
    assertion = str(metadata.get("assertion_type") or "").casefold()
    return (
        certainty in {"disputed", "speculative", "insufficient_evidence"}
        or (dispute and dispute not in {"not_disputed", "consensus", "broad-consensus"})
        or assertion == "inference"
    )


def _unknown(value: Mapping[str, Any], allowed: set[str], label: str, errors: list[str]) -> None:
    unknown = sorted(str(key) for key in value if key not in allowed)
    if unknown:
        errors.append(f"{label} has unknown field(s): {', '.join(unknown)}")


def _required_text(value: Mapping[str, Any], field: str, label: str, errors: list[str]) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        errors.append(f"{label}.{field} must be a non-empty string")
        return ""
    return " ".join(item.split())


def _string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{label} must be a list of non-empty strings")
        return []
    return list(dict.fromkeys(" ".join(item.split()) for item in value))
