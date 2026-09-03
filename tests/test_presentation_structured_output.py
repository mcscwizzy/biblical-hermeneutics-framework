"""Tests for presentation structured output support."""

from __future__ import annotations

import json

import pytest

from bhf_agent.adapters.openrouter import OpenRouterAdapter
from bhf_agent.adapters.openai_compatible import OpenAICompatibleAdapter
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    GeneratedFrom,
    PresentationResponseParseError,
    build_evidence_bundle,
    rank_evidence,
)


class CaptureAdapter:
    """Adapter that captures requests for inspection."""

    def __init__(self, supports_structured: bool = False):
        self._supports_structured = supports_structured
        self.captured_request = None
        self.captured_payload = None

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


class CaptureHTTPAdapter:
    """Adapter that captures the HTTP payload for inspection."""

    def __init__(self, supports_structured: bool = False, base_adapter_class=None):
        self._supports_structured = supports_structured
        self.captured_request = None
        self.captured_payload = None
        self.base_adapter_class = base_adapter_class or OpenAICompatibleAdapter

    def supports_json_schema_response_format(self) -> bool:
        return self._supports_structured

    def _augment_payload(self, payload, request):
        """Hook to capture payload after augmentation."""
        self.captured_payload = payload.copy()
        return payload

    def chat(self, request):
        self.captured_request = request
        from bhf_agent.models import ChatResponse

        if self.captured_request.response_format is not None:
            payload = {
                "model": request.model,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in request.messages()
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            if request.response_format is not None:
                payload["response_format"] = request.response_format
            self.captured_payload = self._augment_payload(payload, request)

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


def test_openrouter_adds_require_parameters_for_structured_output():
    """OpenRouter should add provider.require_parameters for structured output requests."""
    from unittest.mock import patch

    class OpenRouterCaptureAdapter(OpenRouterAdapter):
        """OpenRouter adapter that captures the outgoing payload."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_payload = None

        def _augment_payload(self, payload, request):
            payload = super()._augment_payload(payload, request)
            self.captured_payload = payload.copy()
            return payload

    def fake_urlopen(request, timeout=None):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.read.return_value = json.dumps({
            "model": "test-model",
            "choices": [{"message": {"content": json.dumps({
                "passage_ref": "Mark 5:1",
                "cards": [],
                "generated_from": {
                    "evidence_hash": "test",
                    "evidence_bundle_version": "1.0",
                    "presentation_schema_version": "1.0",
                    "prompt_version": "test",
                    "model": "test-model",
                },
            })}}],
        }).encode("utf-8")
        response.__enter__ = lambda self: response
        response.__exit__ = lambda self, *args: None
        response.headers = {}
        return response

    adapter = OpenRouterCaptureAdapter(api_key="test")
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

    with patch("urllib.request.urlopen", fake_urlopen):
        provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_payload is not None
    assert "provider" in adapter.captured_payload
    assert "require_parameters" in adapter.captured_payload["provider"]
    assert adapter.captured_payload["provider"]["require_parameters"] is True


def test_openrouter_preserves_existing_provider_options():
    """OpenRouter should preserve other provider options when adding require_parameters."""
    from unittest.mock import patch, MagicMock

    class OpenRouterWithProviderOptions(OpenRouterAdapter):
        """OpenRouter adapter with pre-existing provider options."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_payload = None

        def _augment_payload(self, payload, request):
            if request.response_format is not None and "provider" not in payload:
                payload["provider"] = {"sort": "latency"}
            payload = super()._augment_payload(payload, request)
            self.captured_payload = payload.copy()
            return payload

    def fake_urlopen(request, timeout=None):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "model": "test-model",
            "choices": [{"message": {"content": json.dumps({
                "passage_ref": "Mark 5:1",
                "cards": [],
                "generated_from": {
                    "evidence_hash": "test",
                    "evidence_bundle_version": "1.0",
                    "presentation_schema_version": "1.0",
                    "prompt_version": "test",
                    "model": "test-model",
                },
            })}}],
        }).encode("utf-8")
        response.__enter__ = lambda self: response
        response.__exit__ = lambda self, *args: None
        response.headers = {}
        return response

    adapter = OpenRouterWithProviderOptions(api_key="test")
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

    with patch("urllib.request.urlopen", fake_urlopen):
        provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_payload is not None
    assert "provider" in adapter.captured_payload
    provider_opts = adapter.captured_payload["provider"]
    assert provider_opts.get("require_parameters") is True
    if "sort" in provider_opts:
        assert provider_opts["sort"] == "latency"


def test_openrouter_free_gemma_26b_uses_json_object():
    """Free Gemma 4 26B should use json_object, not strict JSON Schema."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability(
        "google/gemma-4-26b-a4b-it:free"
    )
    assert capability == ResponseFormatCapability.JSON_OBJECT


def test_openrouter_free_gemma_31b_uses_json_object():
    """Free Gemma 4 31B should use json_object, not strict JSON Schema."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability(
        "google/gemma-4-31b-it:free"
    )
    assert capability == ResponseFormatCapability.JSON_OBJECT


def test_openrouter_free_router_uses_json_object():
    """openrouter/free router should use json_object, not strict JSON Schema."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability("openrouter/free")
    assert capability == ResponseFormatCapability.JSON_OBJECT


def test_openrouter_paid_gemma_26b_uses_json_schema():
    """Paid Gemma 4 26B may use strict JSON Schema if OpenRouter supports it."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability(
        "google/gemma-4-26b-a4b-it"
    )
    assert capability == ResponseFormatCapability.JSON_SCHEMA


def test_openrouter_paid_gemma_31b_uses_json_schema():
    """Paid Gemma 4 31B may use strict JSON Schema if OpenRouter supports it."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability(
        "google/gemma-4-31b-it"
    )
    assert capability == ResponseFormatCapability.JSON_SCHEMA


def test_openrouter_gpt_4o_uses_json_schema():
    """GPT-4o should use strict JSON Schema."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability("openai/gpt-4o")
    assert capability == ResponseFormatCapability.JSON_SCHEMA


def test_openrouter_unknown_model_defaults_to_json_object():
    """Unknown OpenRouter models should conservatively use json_object."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability(
        "vendor/unknown-model-xyz"
    )
    assert capability == ResponseFormatCapability.JSON_OBJECT


def test_openrouter_none_model_returns_none():
    """None model should return NONE capability."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    adapter = OpenRouterAdapter(api_key="test")
    capability = adapter.presentation_response_format_capability(None)
    assert capability == ResponseFormatCapability.NONE


def test_presentation_provider_uses_json_object_for_free_gemma():
    """Presentation provider should use json_object for free Gemma models."""
    from unittest.mock import patch

    class OpenRouterCaptureAdapter(OpenRouterAdapter):
        """OpenRouter adapter that captures the outgoing payload."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_payload = None

        def _augment_payload(self, payload, request):
            payload = super()._augment_payload(payload, request)
            self.captured_payload = payload.copy()
            return payload

    def fake_urlopen(request, timeout=None):
        from unittest.mock import MagicMock

        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                "model": "google/gemma-4-26b-a4b-it:free",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "passage_ref": "Mark 5:1",
                                    "cards": [],
                                    "generated_from": {
                                        "evidence_hash": "test",
                                        "evidence_bundle_version": "1.0",
                                        "presentation_schema_version": "1.0",
                                        "prompt_version": "test",
                                        "model": "google/gemma-4-26b-a4b-it:free",
                                    },
                                }
                            )
                        }
                    }
                ],
            }
        ).encode("utf-8")
        response.__enter__ = lambda self: response
        response.__exit__ = lambda self, *args: None
        response.headers = {}
        return response

    adapter = OpenRouterCaptureAdapter(api_key="test")
    provider = AdapterPresentationProvider(
        adapter, model="google/gemma-4-26b-a4b-it:free"
    )

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="google/gemma-4-26b-a4b-it:free",
    )

    with patch("urllib.request.urlopen", fake_urlopen):
        result = provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_payload is not None
    assert adapter.captured_payload.get("response_format") == {"type": "json_object"}
    assert "strict" not in adapter.captured_payload.get("response_format", {})
    assert adapter.captured_payload["provider"]["require_parameters"] is True
    assert "passage_ref" in result


def test_presentation_provider_uses_json_schema_for_gpt_4o():
    """Presentation provider should use json_schema for GPT-4o."""
    from unittest.mock import patch

    class OpenRouterCaptureAdapter(OpenRouterAdapter):
        """OpenRouter adapter that captures the outgoing payload."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_payload = None

        def _augment_payload(self, payload, request):
            payload = super()._augment_payload(payload, request)
            self.captured_payload = payload.copy()
            return payload

    def fake_urlopen(request, timeout=None):
        from unittest.mock import MagicMock

        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                "model": "openai/gpt-4o",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "passage_ref": "Mark 5:1",
                                    "cards": [],
                                    "generated_from": {
                                        "evidence_hash": "test",
                                        "evidence_bundle_version": "1.0",
                                        "presentation_schema_version": "1.0",
                                        "prompt_version": "test",
                                        "model": "openai/gpt-4o",
                                    },
                                }
                            )
                        }
                    }
                ],
            }
        ).encode("utf-8")
        response.__enter__ = lambda self: response
        response.__exit__ = lambda self, *args: None
        response.headers = {}
        return response

    adapter = OpenRouterCaptureAdapter(api_key="test")
    provider = AdapterPresentationProvider(adapter, model="openai/gpt-4o")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="openai/gpt-4o",
    )

    with patch("urllib.request.urlopen", fake_urlopen):
        result = provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_payload is not None
    response_format = adapter.captured_payload.get("response_format")
    assert response_format is not None
    assert response_format.get("type") == "json_schema"
    assert response_format.get("json_schema", {}).get("strict") is True
    assert adapter.captured_payload["provider"]["require_parameters"] is True
    assert "passage_ref" in result


def test_presentation_provider_omits_response_format_for_none_capability():
    """Presentation provider should omit response_format when capability is NONE."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    class TestAdapter:
        def __init__(self):
            self.captured_request = None

        def presentation_response_format_capability(self, model):
            return ResponseFormatCapability.NONE

        def chat(self, request):
            from bhf_agent.models import ChatResponse

            self.captured_request = request
            return ChatResponse(
                text=json.dumps(
                    {
                        "passage_ref": "Mark 5:1",
                        "cards": [],
                        "generated_from": {
                            "evidence_hash": request.metadata.get("evidence_hash", "test"),
                            "evidence_bundle_version": "1.0",
                            "presentation_schema_version": "1.0",
                            "prompt_version": request.metadata.get("prompt_version", "test"),
                            "model": "test-model",
                        },
                    }
                )
            )

    adapter = TestAdapter()
    provider = AdapterPresentationProvider(adapter, model="unknown-model")

    bundle = build_evidence_bundle("Mark 5:1")
    ranked = rank_evidence(bundle)
    generated_from = GeneratedFrom(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version="1.0",
        prompt_version="test",
        model="unknown-model",
    )

    result = provider.generate(bundle, ranked, generated_from)

    assert adapter.captured_request.response_format is None
    assert "passage_ref" in result


def test_json_object_response_validation_not_weakened():
    """Validation should still reject responses missing generated_from with json_object mode."""
    from bhf_agent.adapters.base import ResponseFormatCapability

    class TestAdapter:
        def presentation_response_format_capability(self, model):
            return ResponseFormatCapability.JSON_OBJECT

        def chat(self, request):
            from bhf_agent.models import ChatResponse

            return ChatResponse(
                text=json.dumps(
                    {
                        "passage_ref": "Mark 5:1",
                        "cards": [],
                    }
                )
            )

    adapter = TestAdapter()
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


def test_ordinary_openrouter_request_unchanged():
    """Non-presentation OpenRouter requests should not be affected by capability logic."""
    from unittest.mock import patch

    class OpenRouterCaptureAdapter(OpenRouterAdapter):
        """OpenRouter adapter that captures the outgoing payload."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_payload = None

        def _augment_payload(self, payload, request):
            payload = super()._augment_payload(payload, request)
            self.captured_payload = payload.copy()
            return payload

    def fake_urlopen(request, timeout=None):
        from unittest.mock import MagicMock

        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                "model": "openai/gpt-4o",
                "choices": [{"message": {"content": "answer"}}],
            }
        ).encode("utf-8")
        response.__enter__ = lambda self: response
        response.__exit__ = lambda self, *args: None
        response.headers = {}
        return response

    adapter = OpenRouterCaptureAdapter(api_key="test")

    with patch("urllib.request.urlopen", fake_urlopen):
        response = adapter.chat(
            ChatRequest("system", "user", "openai/gpt-4o", response_format=None)
        )

    assert adapter.captured_payload is not None
    assert adapter.captured_payload.get("response_format") is None
    provider_opts = adapter.captured_payload.get("provider")
    assert provider_opts is None or provider_opts.get("require_parameters") is None
    assert response.text == "answer"
