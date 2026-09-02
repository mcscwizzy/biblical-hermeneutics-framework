"""Construct chat adapters from the shared agent configuration."""

from __future__ import annotations

from bhf_agent.config import AgentConfig, ConfigError

from .base import ChatAdapter
from .ollama import OllamaAdapter
from .openai_compatible import OpenAICompatibleAdapter
from .openrouter import OPENROUTER_BASE_URL, OpenRouterAdapter


def build_chat_adapter(config: AgentConfig) -> ChatAdapter:
    """Build the configured adapter without making a provider request."""

    if config.adapter == "openai_compatible":
        if not config.base_url:
            raise ConfigError("base_url is required for openai_compatible adapter")
        return OpenAICompatibleAdapter(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        )
    if config.adapter == "ollama":
        if not config.base_url:
            raise ConfigError("base_url is required for ollama adapter")
        return OllamaAdapter(
            base_url=config.base_url,
            timeout_seconds=config.timeout_seconds,
        )
    if config.adapter == "openrouter":
        return OpenRouterAdapter(
            base_url=config.base_url or OPENROUTER_BASE_URL,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        )
    raise ConfigError(f"unsupported adapter: {config.adapter}")
