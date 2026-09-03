"""Presentation-provider interface and adapter-backed online implementation."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional

from bhf_agent.adapters import ChatAdapter
from bhf_agent.adapters.base import ResponseFormatCapability
from bhf_agent.models import ChatRequest, ChatResponse

from .models import EvidenceBundle, GeneratedFrom
from .ranking import RankedEvidence


PRESENTATION_PROMPT_VERSION = "presentation-v5"


class PresentationResponseParseError(ValueError):
    """A provider response was not exactly one valid JSON object."""

    def __init__(self) -> None:
        super().__init__("presentation response was not one valid JSON object")


class PresentationProviderError(RuntimeError):
    """Provider-level error that precedes JSON parsing."""

    def __init__(self, error_category: str, message: str) -> None:
        self.error_category = error_category
        super().__init__(f"presentation provider {error_category}: {message}")


_OUTER_JSON_FENCE_RE = re.compile(
    r"\A```(?:json)?[ \t]*\r?\n(?P<body>.*)\r?\n```\Z",
    re.IGNORECASE | re.DOTALL,
)


def parse_presentation_json_response(text: str) -> Mapping[str, Any]:
    """Parse one JSON object, tolerating only harmless outer presentation text."""

    source = str(text).strip()
    if not source:
        raise PresentationResponseParseError()

    parsed, was_json = _try_parse_json(source)
    if was_json:
        return _require_json_object(parsed)

    fence = _OUTER_JSON_FENCE_RE.fullmatch(source)
    if fence is not None:
        source = fence.group("body").strip()
        parsed, was_json = _try_parse_json(source)
        if was_json:
            return _require_json_object(parsed)

    candidate = _extract_single_balanced_object(source)
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise PresentationResponseParseError() from None
    return _require_json_object(parsed)


def _try_parse_json(source: str) -> tuple[Any, bool]:
    try:
        return json.loads(source), True
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, False


def _require_json_object(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PresentationResponseParseError()
    return value


def _extract_single_balanced_object(source: str) -> str:
    candidates: list[str] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False

    for index, character in enumerate(source):
        if start is None:
            if character == "{":
                start = index
                depth = 1
                in_string = False
                escaped = False
            elif character in "}[]":
                raise PresentationResponseParseError()
            continue

        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                candidates.append(source[start : index + 1])
                start = None

    if start is not None or len(candidates) != 1:
        raise PresentationResponseParseError()
    return candidates[0]

PRESENTATION_SYSTEM_PROMPT = """You curate concise discoveries for the BHF Bible reader.
BHF has supplied all factual material you may use. Return one JSON object matching the
provided schema; never return Markdown or explanatory text outside the JSON object.

You may select, prioritize, combine compatible supplied facts, simplify academic wording,
write concise hooks, and suggest only the supplied exploration capabilities.

You may not invent historical or archaeological claims, dates, entities, relationships,
or evidence IDs; use model memory as a factual source; turn disputed interpretation into
fact; state doctrinal conclusions; sermonize; or write commentary paragraphs. Every card
must cite the exact supplied evidence IDs that support it. Preserve qualifications and
confidence. If the supplied evidence is not sufficient to create a genuinely useful
discovery, return no card. Zero cards is valid. Do not force trivia.

For every card:
1. Inspect every cited evidence item before choosing confidence or interpretation_level.
2. interpretation_level MUST be allowed for ALL cited evidence items.
3. If ANY cited evidence has fact_allowed=false, the card MUST NOT use
   interpretation_level="fact".
4. Card confidence MUST NOT exceed the most restrictive maximum_card_confidence among
   its cited evidence items.
5. Preserve disputed, uncertain, approximate, or qualified wording; never upgrade
   disputed evidence into an unqualified statement.
6. If a useful card cannot satisfy these requirements, OMIT THE CARD.
7. Returning fewer than three cards is always acceptable.
8. Returning zero cards is valid when the supplied evidence cannot support a compliant card.

The output_constraints object on each evidence item is authoritative guidance for those
choices. When a card cites multiple evidence items, apply the strictest constraint from
all of them.

When suitable ranked contextual evidence exists, prefer at least one did_you_know card,
without manufacturing one from map-only or significance-only material. For every card,
write dig_in_summary in the same response as a concise two-to-four-sentence explanation,
or null when the evidence cannot support a useful explanation. It may connect and explain
the card's cited evidence, but every historical, cultural, geographical, archaeological,
chronological, linguistic, or social factual statement must be supported by those same
evidence IDs. Do not add facts, dates, people, places, customs, doctrine, application, or
sermon material from model memory.

Use why_it_matters only when a supplied evidence item has presentation_role=significance.
Keep that card to the authored passage significance: do not add application, doctrine,
ethical instruction, or a model-created conclusion. Label it inference or disputed,
never fact.
"""


class PresentationProvider(ABC):
    """Provider-neutral generation boundary."""

    model: str

    @abstractmethod
    def generate(
        self,
        bundle: EvidenceBundle,
        ranked: list[RankedEvidence],
        generated_from: GeneratedFrom,
    ) -> Any:
        raise NotImplementedError


class AdapterPresentationProvider(PresentationProvider):
    """Generate structured presentation JSON through any BHF ChatAdapter."""

    def __init__(
        self,
        adapter: ChatAdapter,
        *,
        model: str,
        adapter_name: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 900,
        context_window: int = 4096,
    ) -> None:
        self.adapter = adapter
        self.model = model
        self.adapter_name = str(adapter_name) if adapter_name else None
        self.generation_profile = (
            f"{self.adapter_name}:{self.model}" if self.adapter_name else self.model
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.context_window = context_window

    def generate(
        self,
        bundle: EvidenceBundle,
        ranked: list[RankedEvidence],
        generated_from: GeneratedFrom,
    ) -> Any:
        packet = _provider_packet(bundle, ranked, generated_from)
        capability = self.adapter.presentation_response_format_capability(self.model)
        response_format = _build_response_format(capability)
        response = self.adapter.chat(
            ChatRequest(
                system_prompt=PRESENTATION_SYSTEM_PROMPT,
                user_prompt=json.dumps(packet, sort_keys=True, ensure_ascii=False),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                context_window=self.context_window,
                metadata={
                    "response_contract": "presentation_packet_v1",
                    "evidence_hash": bundle.evidence_hash,
                    "prompt_version": generated_from.prompt_version,
                },
                response_format=response_format,
            )
        )
        if response.errors or response.error_category:
            raise PresentationProviderError(
                response.error_category or "unknown",
                "; ".join(response.errors) if response.errors else "no details available",
            )
        return parse_presentation_json_response(response.text)


def _provider_packet(
    bundle: EvidenceBundle,
    ranked: list[RankedEvidence],
    generated_from: GeneratedFrom,
) -> dict[str, Any]:
    entity_ids = {
        entity_id
        for value in ranked
        for entity_id in value.item.related_entity_ids
    }
    entities = [
        {
            "id": entity.id,
            "title": entity.title,
            "type": entity.type,
            **({"aliases": entity.aliases} if entity.aliases else {}),
        }
        for entity_id, entity in bundle.entities_by_id.items()
        if entity_id in entity_ids
    ]
    return {
        "task": (
            "Create zero to three concise exploratory cards grounded only in supplied evidence. "
            "Use did_you_know for contextual discoveries and at most one walk_the_land card when "
            "a supplied geography resource gives the reader a useful place or route to explore. "
            "Every walk_the_land card must use that resource as map_focus and include its matching "
            "open_map or show_route action. Use at most one why_it_matters card, and only from "
            "evidence explicitly marked with presentation_role=significance."
        ),
        "passage_ref": bundle.passage_ref,
        "generated_from_must_equal": generated_from.to_dict(),
        "evidence": [_provider_evidence(value) for value in ranked],
        "entities": entities,
        "geography": _available_geography(bundle, ranked),
        "available_actions": _available_actions(bundle, ranked),
        "limits": {
            "card_count": 3,
            "headline_characters": 100,
            "body_characters": 420,
            "dig_in_summary_characters": 800,
            "card_types": ["did_you_know", "walk_the_land", "why_it_matters"],
        },
        "output_shape": {
            "passage_ref": "string",
            "cards": [
                {
                    "id": "string",
                    "type": "did_you_know|walk_the_land|why_it_matters",
                    "headline": "string",
                    "body": "string",
                    "dig_in_summary": "2-4 sentence string or null",
                    "evidence_ids": ["supplied evidence id"],
                    "confidence": "high|medium|low",
                    "interpretation_level": "fact|inference|disputed",
                    "related_entity_ids": ["supplied entity id"],
                    "map_focus": {"kind": "place|route", "target_id": "supplied map resource id"},
                    "dig_deeper_actions": [
                        {
                            "type": "available action type",
                            "label": "string",
                            "target_id": "supplied resource id or null",
                            "reference": "supplied reference or null",
                            "parameters": {},
                        }
                    ],
                }
            ],
            "generated_from": generated_from.to_dict(),
        },
    }


def _provider_evidence(value: RankedEvidence) -> dict[str, Any]:
    """Expose claims and validation controls, not arbitrary factual metadata."""

    item = value.item
    allowed_metadata = {
        "passage_relationship",
        "anchor_specificity",
        "certainty",
        "dispute_status",
        "assertion_type",
        "presentation_role",
        "supports_evidence_ids",
        "map_resource_kind",
        "map_resource_id",
    }
    return {
        "id": item.id,
        "claim": item.claim,
        "category": item.category,
        "source_ids": item.source_ids,
        "related_entity_ids": item.related_entity_ids,
        "passage_anchors": item.passage_anchors,
        "confidence": item.confidence,
        "relevance_metadata": {
            key: item.relevance_metadata[key]
            for key in allowed_metadata
            if item.relevance_metadata.get(key) not in (None, "", [])
        },
        "output_constraints": _output_constraints(item.confidence, item.relevance_metadata),
        "salience": {"score": value.score, "reasons": list(value.reasons)},
    }


def _output_constraints(
    confidence: str,
    relevance_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Tell the provider the effective card limits for one evidence item."""

    disputed = _is_disputed_metadata(relevance_metadata)
    maximum_confidence = confidence if confidence in {"low", "medium", "high"} else "low"
    if disputed and maximum_confidence == "high":
        maximum_confidence = "medium"
    return {
        "allowed_interpretation_levels": (
            ["inference", "disputed"] if disputed else ["fact", "inference"]
        ),
        "fact_allowed": not disputed,
        "maximum_card_confidence": maximum_confidence,
    }


def _is_disputed_metadata(metadata: Mapping[str, Any]) -> bool:
    certainty = str(metadata.get("certainty") or "").casefold()
    dispute = str(metadata.get("dispute_status") or "").casefold()
    assertion = str(metadata.get("assertion_type") or "").casefold()
    return (
        certainty in {"disputed", "speculative", "insufficient_evidence"}
        or (dispute and dispute not in {"not_disputed", "consensus", "broad-consensus"})
        or assertion == "inference"
    )


def _available_actions(bundle: EvidenceBundle, ranked: list[RankedEvidence]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = [
        {"type": "show_evidence", "target_ids": [value.item.id for value in ranked]}
    ]
    relevant_entity_ids = {
        entity_id
        for value in ranked
        for entity_id in value.item.related_entity_ids
    }
    by_type: dict[str, list[str]] = {}
    for entity_id, entity in bundle.entities_by_id.items():
        if entity_id not in relevant_entity_ids:
            continue
        by_type.setdefault(entity.type, []).append(entity_id)
    if by_type.get("person"):
        actions.append({"type": "explore_person", "target_ids": by_type["person"]})
    if by_type.get("place"):
        actions.append({"type": "explore_place", "target_ids": by_type["place"]})
    event_ids = [*by_type.get("event", []), *by_type.get("timeline", [])]
    if event_ids:
        actions.append({"type": "explore_event", "target_ids": event_ids})
    geography = _available_geography(bundle, ranked)
    map_ids = [str(item["id"]) for item in geography["places"]]
    if map_ids:
        actions.append({"type": "open_map", "target_ids": map_ids})
    route_ids = [str(item["id"]) for item in geography["routes"]]
    if route_ids:
        actions.append({"type": "show_route", "target_ids": route_ids})
    categories = {value.item.category for value in ranked}
    if "archaeology" in categories:
        actions.append({"type": "archaeology"})
    if "language" in categories:
        actions.append({"type": "explore_language"})
    if categories.intersection({"history", "chronology", "politics"}):
        actions.append({"type": "explore_history"})
    return actions


def _available_geography(
    bundle: EvidenceBundle,
    ranked: list[RankedEvidence],
) -> dict[str, list[dict[str, Any]]]:
    resource_ids = {
        str(value.item.relevance_metadata.get("map_resource_id") or "")
        for value in ranked
    }
    resource_ids.update(
        entity_id
        for value in ranked
        for entity_id in value.item.related_entity_ids
    )
    resource_ids.discard("")
    return {
        kind: [
            {
                "id": str(item.get("id") or ""),
                "title": str(item.get("title") or item.get("name") or item.get("id") or ""),
                "kind": kind[:-1] if kind.endswith("s") else kind,
            }
            for item in bundle.geography.get(kind) or []
            if str(item.get("id") or "") in resource_ids
        ]
        for kind in ("places", "routes")
    }


def _build_response_format(capability: ResponseFormatCapability) -> Optional[dict[str, Any]]:
    """Build response_format based on model capability.

    - JSON_SCHEMA: strict JSON Schema with full validation.
    - JSON_OBJECT: JSON object format (no strict schema enforcement).
    - NONE: no response format specified (prompt-only fallback).
    """
    if capability == ResponseFormatCapability.JSON_SCHEMA:
        return _response_format()
    elif capability == ResponseFormatCapability.JSON_OBJECT:
        return {"type": "json_object"}
    else:
        return None


def _response_format() -> dict[str, Any]:
    action = {
        "type": "object",
        "additionalProperties": False,
        "required": ["type", "label", "target_id", "reference", "parameters"],
        "properties": {
            "type": {"type": "string"},
            "label": {"type": "string"},
            "target_id": {"type": ["string", "null"]},
            "reference": {"type": ["string", "null"]},
            "parameters": {"type": "object"},
        },
    }
    card = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "id", "type", "headline", "body", "evidence_ids", "confidence",
            "interpretation_level", "dig_in_summary", "related_entity_ids", "map_focus", "dig_deeper_actions",
        ],
        "properties": {
            "id": {"type": "string"},
            "type": {
                "type": "string",
                "enum": ["did_you_know", "walk_the_land", "why_it_matters"],
            },
            "headline": {"type": "string"},
            "body": {"type": "string"},
            "dig_in_summary": {"type": ["string", "null"], "maxLength": 800},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "interpretation_level": {"type": "string", "enum": ["fact", "inference", "disputed"]},
            "related_entity_ids": {"type": "array", "items": {"type": "string"}},
            "map_focus": {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["kind", "target_id"],
                        "properties": {
                            "kind": {"type": "string", "enum": ["place", "route"]},
                            "target_id": {"type": "string"},
                        },
                    },
                ]
            },
            "dig_deeper_actions": {"type": "array", "items": action},
        },
    }
    generated = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "evidence_hash", "evidence_bundle_version", "presentation_schema_version",
            "prompt_version", "model",
        ],
        "properties": {
            "evidence_hash": {"type": "string"},
            "evidence_bundle_version": {"type": "string"},
            "presentation_schema_version": {"type": "string"},
            "prompt_version": {"type": "string"},
            "model": {"type": "string"},
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "bhf_presentation_packet_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["passage_ref", "cards", "generated_from"],
                "properties": {
                    "passage_ref": {"type": "string"},
                    "cards": {"type": "array", "maxItems": 3, "items": card},
                    "generated_from": generated,
                },
            },
        },
    }
