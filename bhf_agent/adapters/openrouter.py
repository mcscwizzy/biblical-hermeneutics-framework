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
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            provider_name="openrouter",
        )
