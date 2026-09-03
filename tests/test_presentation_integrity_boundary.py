from __future__ import annotations

import copy
import json
from pathlib import Path

from bhf_agent.models import ChatResponse
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    GeneratedFrom,
    PresentationEngine,
    PresentationProvider,
    PresentationRejectionCode,
    build_evidence_bundle,
    deterministic_presentation,
    rank_evidence,
    validate_presentation_packet,
)
from bhf_agent.presentation.providers import PRESENTATION_PROMPT_VERSION


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "presentation_passages.json").read_text(
        encoding="utf-8"
    )
)


def _results(objects):
    from types import SimpleNamespace

    return [SimpleNamespace(object=value, score=0.92) for value in objects]


def _bundle(index=2, *, geography=None):
    fixture = FIXTURES[index]
    return build_evidence_bundle(
        fixture["reference"],
        canonical_results=_results(fixture["objects"]),
        geography=geography if geography is not None else fixture.get("geography", {}),
    )


def _card(bundle, evidence_id, *, card_id=None, confidence=None, interpretation="fact"):
    item = bundle.evidence_by_id.get(evidence_id)
    if item is None:
        item = bundle.evidence_items[0]
    return {
        "id": card_id or f"card-{evidence_id}",
        "type": "did_you_know",
        "headline": "A supplied detail",
        "body": item.claim,
        "dig_in_summary": None,
        "evidence_ids": [evidence_id],
        "confidence": confidence or item.confidence,
        "interpretation_level": interpretation,
        "related_entity_ids": [],
        "map_focus": None,
        "dig_deeper_actions": [],
    }


def _packet(bundle, cards, *, passage_ref=None, evidence_hash=None):
    return {
        "passage_ref": passage_ref or bundle.passage_ref,
        "cards": cards,
        "generated_from": {
            "evidence_hash": evidence_hash or bundle.evidence_hash,
            "evidence_bundle_version": bundle.version,
            "presentation_schema_version": "1.0",
            "prompt_version": PRESENTATION_PROMPT_VERSION,
            "model": "fixture-model",
        },
    }


class _PacketProvider(PresentationProvider):
    model = "fixture-model"

    def __init__(self, packet_factory):
        self.packet_factory = packet_factory
        self.calls = 0

    def generate(self, bundle, ranked, generated_from):
        self.calls += 1
        packet = copy.deepcopy(self.packet_factory(bundle, ranked))
        packet["generated_from"] = generated_from.to_dict()
        return packet


def test_valid_cards_are_returned_as_generated_and_card_failures_are_partial():
    bundle = _bundle()
    evidence_ids = [item.id for item in bundle.evidence_items]
    cards = [
        _card(bundle, evidence_ids[1], card_id="one"),
        _card(bundle, "invented", card_id="two"),
        _card(bundle, evidence_ids[1], card_id="three"),
    ]
    provider = _PacketProvider(lambda _bundle, _ranked: _packet(bundle, cards))

    result = PresentationEngine(provider=provider).present(bundle)

    assert result.mode == "generated"
    assert [card.id for card in result.packet.cards] == ["one", "three"]
    assert provider.calls == 1
    validation = validate_presentation_packet(
        _packet(bundle, cards), bundle, expected_model="fixture-model"
    )
    assert validation.packet_valid
    assert not validation.valid
    assert validation.card_results[1].reason_codes == (
        PresentationRejectionCode.UNKNOWN_EVIDENCE_ID.value,
    )


def test_disputed_as_fact_is_rejected_but_disputed_and_inference_survive():
    bundle = _bundle()
    disputed_id = bundle.evidence_items[0].id
    bad = _card(bundle, disputed_id, card_id="bad", interpretation="fact")
    accepted = _card(bundle, disputed_id, card_id="accepted", interpretation="disputed")
    inferred = _card(bundle, disputed_id, card_id="inferred", interpretation="inference")

    result = PresentationEngine(
        provider=_PacketProvider(lambda _bundle, _ranked: _packet(bundle, [bad, accepted, inferred]))
    ).present(bundle)

    assert result.mode == "generated"
    assert [card.id for card in result.packet.cards] == ["accepted", "inferred"]
    validation = validate_presentation_packet(
        _packet(bundle, [bad, accepted, inferred]), bundle, expected_model="fixture-model"
    )
    assert PresentationRejectionCode.DISPUTED_AS_FACT.value in validation.card_results[0].reason_codes


def test_confidence_inflation_is_card_level_and_multiple_evidence_uses_strictest_rule():
    bundle = _bundle()
    low_id, high_id = bundle.evidence_items[0].id, bundle.evidence_items[1].id
    inflated = _card(bundle, low_id, card_id="inflated", confidence="high")
    combined = _card(bundle, high_id, card_id="combined", confidence="high")
    combined["evidence_ids"] = [high_id, low_id]

    result = validate_presentation_packet(
        _packet(bundle, [inflated, combined]), bundle, expected_model="fixture-model"
    )

    assert [card.id for card in result.packet.cards] == []
    assert all(
        PresentationRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value in card.reason_codes
        for card in result.card_results
    )


def test_unsupported_date_invalid_map_and_missing_significance_reject_only_cards():
    bundle = _bundle()
    valid_id = bundle.evidence_items[0].id
    bad_date = _card(bundle, valid_id, card_id="date")
    bad_date["body"] += " This happened in AD 325."
    bad_map = _card(bundle, valid_id, card_id="map")
    bad_map["type"] = "walk_the_land"
    bad_map["map_focus"] = {"kind": "place", "target_id": "missing-map"}
    why = _card(bundle, valid_id, card_id="why")
    why["type"] = "why_it_matters"
    why["interpretation_level"] = "inference"

    result = validate_presentation_packet(
        _packet(bundle, [bad_date, bad_map, why]), bundle, expected_model="fixture-model"
    )

    assert result.packet.cards == []
    assert PresentationRejectionCode.UNSUPPORTED_DATE.value in result.card_results[0].reason_codes
    assert PresentationRejectionCode.INVALID_MAP_REFERENCE.value in result.card_results[1].reason_codes
    assert PresentationRejectionCode.MISSING_SIGNIFICANCE_EVIDENCE.value in result.card_results[2].reason_codes


def test_packet_provenance_failure_rejects_every_card():
    bundle = _bundle()
    packet = _packet(bundle, [_card(bundle, bundle.evidence_items[0].id)], evidence_hash="b" * 64)

    result = validate_presentation_packet(packet, bundle, expected_model="fixture-model")

    assert not result.packet_valid
    assert result.packet is None
    assert result.card_results == ()
    assert any("stale" in error for error in result.packet_errors)


def test_provider_constraints_are_explicit_and_prompt_is_v5():
    bundle = _bundle()
    ranked = rank_evidence(bundle, limit=2)
    requests = []

    class Adapter:
        def supports_json_schema_response_format(self):
            return False

        def chat(self, request):
            requests.append(request)
            supplied = json.loads(request.user_prompt)
            return ChatResponse(text=json.dumps(_packet(bundle, [])))

    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version=PRESENTATION_PROMPT_VERSION,
        model="fixture-model",
    )
    AdapterPresentationProvider(Adapter(), model="fixture-model").generate(
        bundle, ranked, generated_from
    )
    supplied = json.loads(requests[0].user_prompt)

    assert PRESENTATION_PROMPT_VERSION == "presentation-v5"
    assert all(
        set(item["output_constraints"])
        == {"allowed_interpretation_levels", "fact_allowed", "maximum_card_confidence"}
        for item in supplied["evidence"]
    )
    disputed = next(
        item for item in supplied["evidence"]
        if item["output_constraints"]["fact_allowed"] is False
    )
    assert disputed["output_constraints"]["allowed_interpretation_levels"] == [
        "inference",
        "disputed",
    ]
    assert 'interpretation_level MUST be allowed for ALL cited evidence items' in requests[0].system_prompt
