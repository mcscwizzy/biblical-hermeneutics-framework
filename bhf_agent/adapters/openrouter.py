"""OpenRouter adapter using its OpenAI-compatible chat API."""

from __future__ import annotations

from typing import Optional

from .openai_compatible import OpenAICompatibleAdapter
from bhf_agent.providers.openrouter_config import OPENROUTER_BASE_URL



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
