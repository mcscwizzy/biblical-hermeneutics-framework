"""Tests for presentation provider error classification and handling."""

from __future__ import annotations

import json
import pytest

from bhf_agent.models import ChatResponse
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    GeneratedFrom,
    build_evidence_bundle,
    rank_evidence,
)
from bhf_agent.presentation.providers import (
    PresentationProviderError,
    PresentationResponseParseError,
)


class MockAdapter:
    """Mock adapter for testing presentation provider error handling."""

    def __init__(self, response: ChatResponse) -> None:
        self.response = response
        self.requests = []

    def supports_json_schema_response_format(self) -> bool:
        return False

    def chat(self, request):
        self.requests.append(request)
        return self.response


def test_provider_rate_limit_error_raises_presentation_provider_error():
    """Provider rate limit errors should raise PresentationProviderError, not parse error."""
    rate_limit_response = ChatResponse(
        text="",
        errors=["OpenRouter rate limited"],
        error_category="provider_rate_limit",
    )
    adapter = MockAdapter(rate_limit_response)
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

    with pytest.raises(PresentationProviderError) as exc_info:
        provider.generate(bundle, ranked, generated_from)

    assert exc_info.value.error_category == "provider_rate_limit"
    assert "rate limited" in str(exc_info.value)


def test_provider_timeout_error_raises_presentation_provider_error():
    """Provider timeout errors should raise PresentationProviderError, not parse error."""
    timeout_response = ChatResponse(
        text="",
        errors=["Request timed out"],
        error_category="provider_timeout",
    )
    adapter = MockAdapter(timeout_response)
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

    with pytest.raises(PresentationProviderError) as exc_info:
        provider.generate(bundle, ranked, generated_from)

    assert exc_info.value.error_category == "provider_timeout"


def test_provider_connection_error_raises_presentation_provider_error():
    """Provider connection errors should raise PresentationProviderError, not parse error."""
    connection_response = ChatResponse(
        text="",
        errors=["Connection refused"],
        error_category="provider_connection",
    )
    adapter = MockAdapter(connection_response)
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

    with pytest.raises(PresentationProviderError) as exc_info:
        provider.generate(bundle, ranked, generated_from)

    assert exc_info.value.error_category == "provider_connection"


def test_response_extraction_error_raises_presentation_provider_error():
    """Response extraction errors should raise PresentationProviderError, not parse error."""
    extraction_response = ChatResponse(
        text="",
        errors=["Could not extract text from response"],
        error_category="response_extraction",
    )
    adapter = MockAdapter(extraction_response)
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

    with pytest.raises(PresentationProviderError) as exc_info:
        provider.generate(bundle, ranked, generated_from)

    assert exc_info.value.error_category == "response_extraction"


def test_malformed_json_still_raises_parse_error():
    """Malformed JSON from provider should still raise PresentationResponseParseError."""
    response = ChatResponse(
        text="This is not valid JSON",
        errors=[],
        error_category=None,
    )
    adapter = MockAdapter(response)
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

    with pytest.raises(PresentationResponseParseError):
        provider.generate(bundle, ranked, generated_from)


def test_valid_response_with_no_errors():
    """Valid response should not raise exceptions."""
    valid_packet = {
        "passage_ref": "Mark 5:1",
        "cards": [],
        "generated_from": {
            "evidence_hash": "abc123",
            "evidence_bundle_version": "1.0",
            "presentation_schema_version": "1.0",
            "prompt_version": "test",
            "model": "test-model",
        },
    }
    response = ChatResponse(
        text=json.dumps(valid_packet),
        errors=[],
        error_category=None,
    )
    adapter = MockAdapter(response)
    provider = AdapterPresentationProvider(adapter, model="test-model")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash="abc123",
        evidence_bundle_version="1.0",
        presentation_schema_version="1.0",
        prompt_version="test",
        model="test-model",
    )

    result = provider.generate(bundle, ranked, generated_from)
    assert result["passage_ref"] == "Mark 5:1"
    assert result["cards"] == []


def test_error_with_empty_message():
    """Error with empty message should still be classified properly."""
    response = ChatResponse(
        text="",
        errors=[],
        error_category="provider_rate_limit",
    )
    adapter = MockAdapter(response)
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

    with pytest.raises(PresentationProviderError) as exc_info:
        provider.generate(bundle, ranked, generated_from)

    assert exc_info.value.error_category == "provider_rate_limit"
