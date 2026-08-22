"""Shared OpenRouter endpoints and recommended model catalog."""

from __future__ import annotations

from typing import Any


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_AUTH_URL = "https://openrouter.ai/auth"
OPENROUTER_KEY_EXCHANGE_URL = f"{OPENROUTER_BASE_URL}/auth/keys"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"
DEFAULT_OPENROUTER_MODEL_LABEL = "OpenRouter Free Router"

OPENROUTER_MODELS: tuple[dict[str, Any], ...] = (
    {
        "id": DEFAULT_OPENROUTER_MODEL,
        "label": DEFAULT_OPENROUTER_MODEL_LABEL,
        "description": "Automatically routes to an available free model.",
        "recommended": True,
    },
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "label": "Gemma 4 26B A4B (Free)",
        "description": "Pin requests to the Gemma 4 26B A4B free model.",
        "recommended": False,
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "label": "Gemma 4 31B (Free)",
        "description": "A larger Gemma model when available.",
        "recommended": False,
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "label": "Nemotron 3 Ultra (Free)",
        "description": "Experimental.",
        "recommended": False,
        "experimental": True,
    },
    {
        "id": "openai/gpt-oss-120b:free",
        "label": "GPT-OSS 120B (Free)",
        "description": "Experimental.",
        "recommended": False,
        "experimental": True,
    },
)
