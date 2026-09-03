"""Strict validation for untrusted PresentationPacket JSON."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
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


class PresentationRejectionCode(str, Enum):
    """Stable codes for safe diagnostics about rejected generated cards."""

    MALFORMED_CARD = "MALFORMED_CARD"
    INVALID_CARD_TYPE = "INVALID_CARD_TYPE"
    INVALID_CONFIDENCE = "INVALID_CONFIDENCE"
    INVALID_INTERPRETATION_LEVEL = "INVALID_INTERPRETATION_LEVEL"
    CARD_LENGTH_EXCEEDED = "CARD_LENGTH_EXCEEDED"
    UNKNOWN_EVIDENCE_ID = "UNKNOWN_EVIDENCE_ID"
    UNKNOWN_ENTITY_ID = "UNKNOWN_ENTITY_ID"
    CONFIDENCE_EXCEEDS_EVIDENCE = "CONFIDENCE_EXCEEDS_EVIDENCE"
    DISPUTED_AS_FACT = "DISPUTED_AS_FACT"
    UNSUPPORTED_DATE = "UNSUPPORTED_DATE"
    INVALID_MAP_REFERENCE = "INVALID_MAP_REFERENCE"
    INVALID_ACTION_REFERENCE = "INVALID_ACTION_REFERENCE"
    MISSING_MAP_INFORMATION = "MISSING_MAP_INFORMATION"
    MISSING_MAP_ACTION = "MISSING_MAP_ACTION"
    MISSING_SIGNIFICANCE_EVIDENCE = "MISSING_SIGNIFICANCE_EVIDENCE"
    WHY_IT_MATTERS_AS_FACT = "WHY_IT_MATTERS_AS_FACT"
    DUPLICATE_CARD_ID = "DUPLICATE_CARD_ID"
    DUPLICATE_CARD_TYPE = "DUPLICATE_CARD_TYPE"


@dataclass(frozen=True)
class GeneratedMetadataValidationResult:
    valid: bool
    generated_from: GeneratedFrom | None
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class PresentationCardValidationResult:
    valid: bool
    card: PresentationCard | None
    errors: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PresentationValidationResult:
    valid: bool
    packet: PresentationPacket | None
    errors: tuple[str, ...]
    card_results: tuple[PresentationCardValidationResult, ...] = ()
    packet_errors: tuple[str, ...] = ()

    @property
    def packet_valid(self) -> bool:
        """Whether packet provenance and structure passed independently of cards."""

        return self.packet is not None

    @property
    def accepted_cards(self) -> tuple[PresentationCard, ...]:
        if self.packet is None:
            return ()
        return tuple(self.packet.cards)


def validate_presentation_packet(
    value: Any,
    bundle: EvidenceBundle,
    *,
    maximum_cards: int = 3,
    maximum_body_length: int = 420,
    maximum_dig_in_summary_length: int = 800,
    expected_prompt_version: str | None = None,
    expected_model: str | None = None,
) -> PresentationValidationResult:
    """Validate packet integrity, then validate each card independently.

    A packet with valid provenance may return a partial ``packet`` even when
    individual cards are rejected. Packet-level failures never return cards.
    """

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

    generated_result = validate_generated_metadata(
        value.get("generated_from"),
        bundle,
        expected_prompt_version=expected_prompt_version,
        expected_model=expected_model,
    )
    errors.extend(generated_result.errors)
    if errors or not generated_result.valid or generated_result.generated_from is None:
        return PresentationValidationResult(
            False,
            None,
            tuple(errors),
            packet_errors=tuple(errors),
        )

    card_results: list[PresentationCardValidationResult] = []
    cards: list[PresentationCard] = []
    card_ids: set[str] = set()
    for index, raw_card in enumerate(cards_raw):
        card_result = validate_presentation_card(
            raw_card,
            index,
            bundle,
            maximum_body_length=maximum_body_length,
            maximum_dig_in_summary_length=maximum_dig_in_summary_length,
        )
        if card_result.card is not None:
            if card_result.card.id in card_ids:
                card_result = _reject_card(
                    card_result,
                    f'card[{index}] duplicates card id "{card_result.card.id}"',
                    PresentationRejectionCode.DUPLICATE_CARD_ID,
                )
            elif card_result.card.type == "walk_the_land" and any(
                card.type == "walk_the_land" for card in cards
            ):
                card_result = _reject_card(
                    card_result,
                    "packet.cards may contain at most one walk_the_land card",
                    PresentationRejectionCode.DUPLICATE_CARD_TYPE,
                )
            elif card_result.card.type == "why_it_matters" and any(
                card.type == "why_it_matters" for card in cards
            ):
                card_result = _reject_card(
                    card_result,
                    "packet.cards may contain at most one why_it_matters card",
                    PresentationRejectionCode.DUPLICATE_CARD_TYPE,
                )
        card_results.append(card_result)
        if card_result.card is not None:
            card_ids.add(card_result.card.id)
            cards.append(card_result.card)

    card_errors = tuple(error for result in card_results for error in result.errors)
    all_errors = tuple(errors) + card_errors
    return PresentationValidationResult(
        not card_errors,
        PresentationPacket(
            passage_ref=passage_ref,
            cards=cards,
            generated_from=generated_result.generated_from,
        ),
        all_errors,
        tuple(card_results),
        (),
    )


def validate_generated_metadata(
    raw: Any,
    bundle: EvidenceBundle,
    *,
    expected_prompt_version: str | None = None,
    expected_model: str | None = None,
) -> GeneratedMetadataValidationResult:
    errors: list[str] = []
    if not isinstance(raw, Mapping):
        errors.append("packet.generated_from must be an object")
        return GeneratedMetadataValidationResult(False, None, tuple(errors))
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
        return GeneratedMetadataValidationResult(False, None, tuple(errors))
    if errors:
        return GeneratedMetadataValidationResult(False, None, tuple(errors))
    return GeneratedMetadataValidationResult(True, GeneratedFrom(**values), ())


def validate_presentation_card(
    raw: Any,
    index: int,
    bundle: EvidenceBundle,
    *,
    maximum_body_length: int = 420,
    maximum_dig_in_summary_length: int = 800,
) -> PresentationCardValidationResult:
    label = f"card[{index}]"
    if not isinstance(raw, Mapping):
        return PresentationCardValidationResult(
            False,
            None,
            (f"{label} must be an object",),
            (PresentationRejectionCode.MALFORMED_CARD.value,),
        )
    errors: list[str] = []
    reason_codes: list[str] = []
    fields = {
        "id", "type", "headline", "body", "evidence_ids", "confidence",
        "interpretation_level", "dig_in_summary", "related_entity_ids", "map_focus", "dig_deeper_actions",
    }
    _unknown(raw, fields, label, errors)
    if any(key not in fields for key in raw):
        reason_codes.append(PresentationRejectionCode.MALFORMED_CARD)
    card_id = _required_text(raw, "id", label, errors)
    card_type = _required_text(raw, "type", label, errors)
    headline = _required_text(raw, "headline", label, errors)
    body = _required_text(raw, "body", label, errors)
    dig_in_summary = str(raw.get("dig_in_summary") or "").strip() or None
    confidence = _required_text(raw, "confidence", label, errors)
    interpretation = _required_text(raw, "interpretation_level", label, errors)
    if card_type not in CARD_TYPES:
        errors.append(f"{label}.type is invalid")
        reason_codes.append(PresentationRejectionCode.INVALID_CARD_TYPE)
    if confidence not in CONFIDENCE_VALUES:
        errors.append(f"{label}.confidence is invalid")
        reason_codes.append(PresentationRejectionCode.INVALID_CONFIDENCE)
    if interpretation not in INTERPRETATION_LEVELS:
        errors.append(f"{label}.interpretation_level is invalid")
        reason_codes.append(PresentationRejectionCode.INVALID_INTERPRETATION_LEVEL)
    if len(headline) > 100:
        errors.append(f"{label}.headline exceeds 100 characters")
        reason_codes.append(PresentationRejectionCode.CARD_LENGTH_EXCEEDED)
    if len(body) > maximum_body_length:
        errors.append(f"{label}.body exceeds {maximum_body_length} characters")
        reason_codes.append(PresentationRejectionCode.CARD_LENGTH_EXCEEDED)
    if dig_in_summary and len(dig_in_summary) > maximum_dig_in_summary_length:
        errors.append(
            f"{label}.dig_in_summary exceeds {maximum_dig_in_summary_length} characters"
        )
        reason_codes.append(PresentationRejectionCode.CARD_LENGTH_EXCEEDED)

    evidence_ids = _string_list(raw.get("evidence_ids"), f"{label}.evidence_ids", errors)
    related_ids = _string_list(raw.get("related_entity_ids", []), f"{label}.related_entity_ids", errors)
    if not evidence_ids:
        errors.append(f"{label}.evidence_ids must cite at least one supplied item")
    unknown_evidence = [item_id for item_id in evidence_ids if item_id not in bundle.evidence_by_id]
    if unknown_evidence:
        errors.append(f"{label} cites unsupported evidence IDs: {', '.join(unknown_evidence)}")
        reason_codes.append(PresentationRejectionCode.UNKNOWN_EVIDENCE_ID)
    unknown_entities = [item_id for item_id in related_ids if item_id not in bundle.entities_by_id]
    if unknown_entities:
        errors.append(f"{label} cites unsupported entity IDs: {', '.join(unknown_entities)}")
        reason_codes.append(PresentationRejectionCode.UNKNOWN_ENTITY_ID)

    supplied = [bundle.evidence_by_id[item_id] for item_id in evidence_ids if item_id in bundle.evidence_by_id]
    if supplied and confidence in _CONFIDENCE_RANK:
        maximum_supported = min(_CONFIDENCE_RANK.get(item.confidence, 0) for item in supplied)
        if _CONFIDENCE_RANK[confidence] > maximum_supported:
            errors.append(f"{label}.confidence exceeds its cited evidence")
            reason_codes.append(PresentationRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE)
    if interpretation == "fact" and any(_is_disputed(item.relevance_metadata) for item in supplied):
        errors.append(f"{label} turns disputed evidence into fact")
        reason_codes.append(PresentationRejectionCode.DISPUTED_AS_FACT)
    _validate_new_dates(
        " ".join(value for value in (headline, body, dig_in_summary) if value),
        supplied,
        label,
        errors,
        reason_codes,
    )

    actions_raw = raw.get("dig_deeper_actions", [])
    if not isinstance(actions_raw, list):
        errors.append(f"{label}.dig_deeper_actions must be a list")
        reason_codes.append(PresentationRejectionCode.MALFORMED_CARD)
        actions_raw = []
    actions = [
        action
        for action_index, raw_action in enumerate(actions_raw)
        if (action := _parse_action(raw_action, label, action_index, bundle, supplied, errors, reason_codes)) is not None
    ]

    map_focus_raw = raw.get("map_focus")
    map_focus: dict[str, Any] | None = None
    if map_focus_raw is not None:
        if not isinstance(map_focus_raw, Mapping):
            errors.append(f"{label}.map_focus must be an object or null")
            reason_codes.append(PresentationRejectionCode.INVALID_MAP_REFERENCE)
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
                reason_codes.append(PresentationRejectionCode.INVALID_MAP_REFERENCE)
            elif not target_id or target_id not in available:
                errors.append(f"{label}.map_focus references an unavailable map resource")
                reason_codes.append(PresentationRejectionCode.INVALID_MAP_REFERENCE)
            map_focus = {"kind": kind, "target_id": target_id}
    if card_type == "walk_the_land":
        if map_focus is None:
            errors.append(f"{label}.walk_the_land requires map_focus")
            reason_codes.append(PresentationRejectionCode.MISSING_MAP_INFORMATION)
        else:
            expected_action = "show_route" if map_focus["kind"] == "route" else "open_map"
            if not any(
                action.type == expected_action and action.target_id == map_focus["target_id"]
                for action in actions
            ):
                errors.append(f"{label}.walk_the_land requires a matching map action")
                reason_codes.append(PresentationRejectionCode.MISSING_MAP_ACTION)
    if card_type == "why_it_matters":
        if not any(
            item.relevance_metadata.get("presentation_role") == "significance"
            for item in supplied
        ):
            errors.append(f"{label}.why_it_matters requires explicit significance evidence")
            reason_codes.append(PresentationRejectionCode.MISSING_SIGNIFICANCE_EVIDENCE)
        if interpretation == "fact":
            errors.append(f"{label}.why_it_matters must be labeled inference or disputed")
            reason_codes.append(PresentationRejectionCode.WHY_IT_MATTERS_AS_FACT)

    card = PresentationCard(
        id=card_id,
        type=card_type,
        headline=headline,
        body=body,
        evidence_ids=evidence_ids,
        confidence=confidence,
        interpretation_level=interpretation,
        dig_in_summary=dig_in_summary,
        related_entity_ids=related_ids,
        map_focus=map_focus,
        dig_deeper_actions=actions,
    )
    if errors and not reason_codes:
        reason_codes.append(PresentationRejectionCode.MALFORMED_CARD)
    if errors:
        return PresentationCardValidationResult(
            False, None, tuple(errors), _normalized_reason_codes(reason_codes)
        )
    return PresentationCardValidationResult(True, card, (), ())


def _parse_action(
    raw: Any,
    card_label: str,
    index: int,
    bundle: EvidenceBundle,
    evidence: list[Any],
    errors: list[str],
    reason_codes: list[str],
) -> DigDeeperAction | None:
    label = f"{card_label}.dig_deeper_actions[{index}]"
    if not isinstance(raw, Mapping):
        errors.append(f"{label} must be an object")
        reason_codes.append(PresentationRejectionCode.MALFORMED_CARD)
        return None
    fields = {"type", "label", "target_id", "reference", "parameters"}
    _unknown(raw, fields, label, errors)
    if any(key not in fields for key in raw):
        reason_codes.append(PresentationRejectionCode.MALFORMED_CARD)
    action_type = _required_text(raw, "type", label, errors)
    action_label = _required_text(raw, "label", label, errors)
    target_id = str(raw.get("target_id") or "").strip() or None
    reference = str(raw.get("reference") or "").strip() or None
    parameters_raw = raw.get("parameters", {})
    if not isinstance(parameters_raw, Mapping):
        errors.append(f"{label}.parameters must be an object")
        reason_codes.append(PresentationRejectionCode.MALFORMED_CARD)
        parameters_raw = {}
    if action_type not in ACTION_TYPES:
        errors.append(f"{label}.type is invalid")
        reason_codes.append(PresentationRejectionCode.INVALID_ACTION_REFERENCE)
    elif not _action_is_fulfillable(action_type, target_id, reference, bundle, evidence):
        errors.append(f"{label} references a resource BHF cannot fulfill")
        reason_codes.append(PresentationRejectionCode.INVALID_ACTION_REFERENCE)
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


def _validate_new_dates(
    text: str,
    evidence: list[Any],
    label: str,
    errors: list[str],
    reason_codes: list[str],
) -> None:
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
        reason_codes.append(PresentationRejectionCode.UNSUPPORTED_DATE)


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


def _reject_card(
    result: PresentationCardValidationResult,
    error: str,
    reason_code: str,
) -> PresentationCardValidationResult:
    return PresentationCardValidationResult(
        False,
        None,
        (*result.errors, error),
        (*result.reason_codes, _code_value(reason_code)),
    )


def _normalized_reason_codes(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_code_value(value) for value in values))


def _code_value(value: str) -> str:
    return value.value if isinstance(value, PresentationRejectionCode) else str(value)


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
