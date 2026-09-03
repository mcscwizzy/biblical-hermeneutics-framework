"""OpenRouter adapter using its OpenAI-compatible chat API."""

from __future__ import annotations

from typing import Any, Optional

from bhf_agent.models import ChatRequest

from .base import ResponseFormatCapability
from .openai_compatible import OpenAICompatibleAdapter
from bhf_agent.providers.openrouter_config import OPENROUTER_BASE_URL


_OPENROUTER_JSON_OBJECT_MODELS = {
    "openrouter/free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openai/gpt-oss-120b:free",
}

_OPENROUTER_JSON_SCHEMA_MODELS = {
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-turbo",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "google/gemma-4-26b-a4b-it",
    "google/gemma-4-31b-it",
}


class OpenRouterAdapter(OpenAICompatibleAdapter):
    """Adapter for OpenRouter's normalized `/api/v1/chat/completions` API."""

    def __init__(
        self,
        base_url: str = OPENROUTER_BASE_URL,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = 120,
    ) -> None:
        # OpenRouter calls must always be bounded.  ``None`` is useful for some
        # local OpenAI-compatible runtimes, but would let a free-router request
        # wait forever if an upstream model stopped responding.
        effective_timeout = 120 if timeout_seconds is None else timeout_seconds
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=effective_timeout,
            provider_name="openrouter",
            extra_headers={"X-OpenRouter-Metadata": "enabled"},
            max_rate_limit_retries=2,
            rate_limit_retry_seconds=1.0,
            max_rate_limit_retry_seconds=30.0,
        )

    def supports_json_schema_response_format(self) -> bool:
        return True

    def presentation_response_format_capability(
        self, model: Optional[str] = None
    ) -> ResponseFormatCapability:
        """Return model-aware presentation response format capability for OpenRouter.

        Different OpenRouter models have different structured output support:
        - Known schema-capable models (explicit allowlist) use strict JSON Schema.
        - Known JSON-object-capable models (free endpoints, json-only support) use JSON object.
        - Unknown models conservatively use JSON object if available, else None.
        """
        if not model:
            return ResponseFormatCapability.NONE

        normalized_model = str(model).strip()

        if normalized_model in _OPENROUTER_JSON_SCHEMA_MODELS:
            return ResponseFormatCapability.JSON_SCHEMA

        if normalized_model in _OPENROUTER_JSON_OBJECT_MODELS:
            return ResponseFormatCapability.JSON_OBJECT

        return ResponseFormatCapability.JSON_OBJECT

    def _augment_payload(
        self, payload: dict[str, Any], request: ChatRequest
    ) -> dict[str, Any]:
        """Add OpenRouter provider routing for structured output requests."""
        payload = super()._augment_payload(payload, request)

        if request.response_format is not None:
            provider_options = dict(payload.get("provider") or {})
            provider_options["require_parameters"] = True
            payload["provider"] = provider_options

        return payload
