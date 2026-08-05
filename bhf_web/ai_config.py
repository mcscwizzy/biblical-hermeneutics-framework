"""Centralized browser-facing AI provider and model configuration."""

from __future__ import annotations

from typing import Any

from bhf_agent.providers.openrouter_config import (
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_OPENROUTER_MODEL_LABEL,
    OPENROUTER_AUTH_URL,
    OPENROUTER_BASE_URL,
    OPENROUTER_KEY_EXCHANGE_URL,
    OPENROUTER_MODELS,
)

WEB_AI_DEFAULTS: dict[str, Any] = {
    "max_tokens": 2048,
    "context_window": 12288,
    "runtime_profile_mode": "compact",
    "memory_enabled": False,
}

OPENROUTER_AI_DEFAULTS: dict[str, int] = {
    "max_tokens": 4096,
    "context_window": 16384,
}


def browser_ai_config() -> dict[str, Any]:
    """Return serializable configuration for the browser UI."""

    return {
        "openrouter": {
            "baseUrl": OPENROUTER_BASE_URL,
            "authUrl": OPENROUTER_AUTH_URL,
            "keyExchangeUrl": OPENROUTER_KEY_EXCHANGE_URL,
            "defaultModel": DEFAULT_OPENROUTER_MODEL,
            "models": [dict(model) for model in OPENROUTER_MODELS],
        },
        "defaults": dict(WEB_AI_DEFAULTS),
        "providerDefaults": {
            "openrouter": dict(OPENROUTER_AI_DEFAULTS),
        },
    }
