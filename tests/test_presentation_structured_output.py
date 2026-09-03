"""Tests for presentation structured output support."""

from __future__ import annotations

import json

import pytest

from bhf_agent.adapters.openrouter import OpenRouterAdapter
from bhf_agent.adapters.openai_compatible import OpenAICompatibleAdapter
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    GeneratedFrom,
    build_evidence_bundle,
    rank_evidence,
)


class CaptureAdapter:
    """Adapter that captures requests for inspection."""

    def __init__(self, supports_structured: bool = False):
        self._supports_structured = supports_structured
        self.captured_request = None

    def supports_json_schema_response_format(self) -> bool:
        return self._supports_structured

    def chat(self, request):
        self.captured_request = request
        from bhf_agent.models import ChatResponse

        return ChatResponse(
            text=json.dumps({
                "passage_ref": "Mark 5:1",
                "cards": [],
                "generated_from": {
                    "evidence_hash": request.metadata.get("evidence_hash", "test"),
                    "evidence_bundle_version": "1.0",
                    "presentation_schema_version": "1.0",
                    "prompt_version": request.metadata.get("prompt_version", "test"),
                    "model": "test-model",
                },
            })
        )


def test_openrouter_adapter_supports_json_schema_response_format():
    """OpenRouter adapter should advertise JSON schema support."""
    adapter = OpenRouterAdapter(api_key="test")
    assert adapter.supports_json_schema_response_format() is True


def test_openai_compatible_adapter_does_not_support_json_schema_by_default():
    """Generic OpenAI-compatible adapter should not support JSON schema."""
    adapter = OpenAICompatibleAdapter("http://localhost:8000/v1")
    assert adapter.supports_json_schema_response_format() is False


def test_presentation_provider_sends_response_format_when_supported():
    """Presentation provider should include response_format when adapter supports it."""
    adapter = CaptureAdapter(supports_structured=True)
    provider = AdapterPresentationProvider(adapter, model="test-model")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="test-model",
    )

    provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_request is not None
    assert adapter.captured_request.response_format is not None
    assert adapter.captured_request.response_format["type"] == "json_schema"
    assert "bhf_presentation_packet_v1" in adapter.captured_request.response_format["json_schema"]["name"]


def test_presentation_provider_omits_response_format_when_not_supported():
    """Presentation provider should omit response_format when adapter doesn't support it."""
    adapter = CaptureAdapter(supports_structured=False)
    provider = AdapterPresentationProvider(adapter, model="test-model")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="test-model",
    )

    provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_request is not None
    assert adapter.captured_request.response_format is None


def test_response_format_includes_required_fields():
    """Response format schema should require essential packet fields."""
    adapter = CaptureAdapter(supports_structured=True)
    provider = AdapterPresentationProvider(adapter, model="test-model")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="test-model",
    )

    provider.generate(bundle, ranked, generated_from)

    schema = adapter.captured_request.response_format["json_schema"]["schema"]
    required_fields = schema.get("required", [])

    assert "passage_ref" in required_fields
    assert "cards" in required_fields
    assert "generated_from" in required_fields

    generated_schema = schema["properties"]["generated_from"]
    generated_required = generated_schema.get("required", [])
    assert "evidence_hash" in generated_required
    assert "evidence_bundle_version" in generated_required
    assert "presentation_schema_version" in generated_required
    assert "prompt_version" in generated_required
    assert "model" in generated_required


def test_response_format_is_strict():
    """Response format should have strict mode enabled."""
    adapter = CaptureAdapter(supports_structured=True)
    provider = AdapterPresentationProvider(adapter, model="test-model")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="test-model",
    )

    provider.generate(bundle, ranked, generated_from)

    json_schema = adapter.captured_request.response_format["json_schema"]
    assert json_schema.get("strict") is True
