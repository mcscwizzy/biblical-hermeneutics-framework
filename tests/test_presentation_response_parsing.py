from __future__ import annotations

import json

import pytest

from bhf_agent.models import ChatResponse
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    MemoryPresentationCache,
    PresentationEngine,
    PresentationProvider,
    PresentationResponseParseError,
    build_evidence_bundle,
    parse_presentation_json_response,
)


def test_parse_presentation_json_response_accepts_direct_object():
    assert parse_presentation_json_response(
        '  {"passage_ref":"John 4:23","cards":[]}\n'
    ) == {"passage_ref": "John 4:23", "cards": []}


@pytest.mark.parametrize(
    "opening",
    ["```json", "```"],
)
def test_parse_presentation_json_response_accepts_outer_markdown_fence(opening):
    response = f'{opening}\n{{"passage_ref":"John 4:23","cards":[]}}\n```'

    assert parse_presentation_json_response(response)["passage_ref"] == "John 4:23"


def test_parse_presentation_json_response_accepts_preamble_and_trailing_prose():
    response = (
        "Here is the requested JSON:\n"
        '{"passage_ref":"John 4:23","cards":[]}\n'
        "I hope this helps."
    )

    assert parse_presentation_json_response(response)["cards"] == []


def test_balanced_extraction_ignores_braces_inside_json_strings():
    response = (
        "Here is the requested JSON:\n"
        + json.dumps(
            {
                "passage_ref": "John 4:23",
                "body": "The inscription contains {braces} in the quotation.",
            }
        )
    )

    assert parse_presentation_json_response(response)["body"].endswith("quotation.")


def test_balanced_extraction_handles_escaped_quotes_inside_json_strings():
    response = "JSON follows:\n" + json.dumps(
        {
            "passage_ref": "John 4:23",
            "body": 'The witness said "worship" before {this phrase}.',
        }
    )

    assert 'said "worship"' in parse_presentation_json_response(response)["body"]


@pytest.mark.parametrize(
    "response",
    [
        '{"a":1} {"b":2}',
        '[{"a":1}]',
        '{"a":1 "b":2}',
        '{"a":1',
        "",
        "   \n\t",
    ],
    ids=["multiple-objects", "array", "missing-comma", "missing-brace", "empty", "whitespace"],
)
def test_parse_presentation_json_response_rejects_non_object_or_malformed_json(response):
    with pytest.raises(PresentationResponseParseError):
        parse_presentation_json_response(response)


class _ResponseAdapter:
    def __init__(self, response_factory):
        self.response_factory = response_factory
        self.requests = []

    def supports_json_schema_response_format(self):
        return False

    def chat(self, request):
        self.requests.append(request)
        supplied = json.loads(request.user_prompt)
        return ChatResponse(text=self.response_factory(supplied))


def _bundle():
    return build_evidence_bundle(
        "John 4:23",
        geography={
            "places": [
                {
                    "id": "samaria",
                    "title": "Samaria",
                    "summary": "Samaria is the passage setting.",
                    "confidence": "high",
                }
            ],
            "routes": [],
        },
    )


def _valid_packet(supplied):
    return {
        "passage_ref": supplied["passage_ref"],
        "cards": [],
        "generated_from": supplied["generated_from_must_equal"],
    }


def test_fenced_provider_packet_is_validated_generated_and_cached():
    adapter = _ResponseAdapter(
        lambda supplied: f"```json\n{json.dumps(_valid_packet(supplied))}\n```"
    )
    provider = AdapterPresentationProvider(adapter, model="fixture-model")
    cache = MemoryPresentationCache()
    engine = PresentationEngine(provider=provider, cache=cache)

    result = engine.present(_bundle())

    assert result.mode == "generated"
    assert result.diagnostics == ()
    assert len(cache._values) == 1
    assert len(adapter.requests) == 1
    assert engine.diagnostics()["provider"] == {
        "attempts": 1,
        "failures": 0,
        "parse_failures": 0,
        "rejections": 0,
        "saturated": 0,
    }


def test_fenced_packet_with_unsupported_evidence_still_falls_back(caplog):
    def invalid_packet(supplied):
        packet = _valid_packet(supplied)
        packet["cards"] = [
            {
                "id": "unsupported",
                "type": "did_you_know",
                "headline": "Unsupported",
                "body": "An unsupported claim.",
                "dig_in_summary": None,
                "evidence_ids": ["invented-evidence"],
                "confidence": "high",
                "interpretation_level": "fact",
                "related_entity_ids": [],
                "map_focus": None,
                "dig_deeper_actions": [],
            }
        ]
        return f"```json\n{json.dumps(packet)}\n```"

    adapter = _ResponseAdapter(invalid_packet)
    engine = PresentationEngine(
        provider=AdapterPresentationProvider(adapter, model="fixture-model")
    )

    with caplog.at_level("WARNING", logger="bhf_agent.presentation.engine"):
        result = engine.present(_bundle())

    assert result.mode == "deterministic_fallback"
    assert any(
        diagnostic.startswith("validation rejection: card[0] cites unsupported evidence IDs")
        for diagnostic in result.diagnostics
    )
    assert "validation rejection: card[0] cites unsupported evidence IDs" in caplog.text
    assert engine.diagnostics()["provider"]["parse_failures"] == 0
    assert engine.diagnostics()["provider"]["rejections"] == 1


def test_parse_failure_is_safely_classified_and_logged(caplog):
    raw_response = "secret model output from internal.example: {not valid JSON}"
    adapter = _ResponseAdapter(lambda supplied: raw_response)
    engine = PresentationEngine(
        provider=AdapterPresentationProvider(adapter, model="fixture-model")
    )

    with caplog.at_level("WARNING", logger="bhf_agent.presentation.engine"):
        result = engine.present(_bundle())

    assert result.mode == "deterministic_fallback"
    assert result.diagnostics == (
        "provider response parse failure: PresentationResponseParseError",
    )
    assert "provider response parse failure: PresentationResponseParseError" in caplog.text
    assert raw_response not in caplog.text
    assert "internal.example" not in caplog.text
    assert engine.diagnostics()["provider"]["parse_failures"] == 1
    assert engine.diagnostics()["provider"]["failures"] == 0


def test_provider_runtime_failure_logs_only_exception_type(caplog):
    class _SecretFailingProvider(PresentationProvider):
        model = "fixture-model"

        def generate(self, bundle, ranked, generated_from):
            raise RuntimeError("secret-token internal.example")

    with caplog.at_level("WARNING", logger="bhf_agent.presentation.engine"):
        result = PresentationEngine(provider=_SecretFailingProvider()).present(_bundle())

    assert result.diagnostics == ("provider failure: RuntimeError",)
    assert "provider failure: RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text
    assert "internal.example" not in caplog.text


def test_multiple_validation_diagnostics_are_compact_and_visible(caplog):
    class _InvalidProvider(PresentationProvider):
        model = "fixture-model"

        def generate(self, bundle, ranked, generated_from):
            packet = _valid_packet(
                {
                    "passage_ref": "wrong passage",
                    "generated_from_must_equal": generated_from.to_dict(),
                }
            )
            packet["generated_from"]["model"] = "wrong-model"
            return packet

    with caplog.at_level("WARNING", logger="bhf_agent.presentation.engine"):
        result = PresentationEngine(provider=_InvalidProvider()).present(_bundle())

    assert result.mode == "deterministic_fallback"
    assert "presentation generation rejected; falling back (2):" in caplog.text
    assert "validation rejection: packet passage_ref does not match" in caplog.text
    assert "validation rejection: generated_from.model does not match" in caplog.text
