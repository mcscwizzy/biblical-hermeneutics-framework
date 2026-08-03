"""Shared OpenRouter endpoints and recommended model catalog."""

from __future__ import annotations

from typing import Any


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_AUTH_URL = "https://openrouter.ai/auth"
OPENROUTER_KEY_EXCHANGE_URL = f"{OPENROUTER_BASE_URL}/auth/keys"
DEFAULT_OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_OPENROUTER_MODEL_LABEL = "Gemma 4 26B A4B"

OPENROUTER_MODELS: tuple[dict[str, Any], ...] = (
    {
        "id": DEFAULT_OPENROUTER_MODEL,
        "label": DEFAULT_OPENROUTER_MODEL_LABEL,
        "description": "Recommended for careful, in-depth Bible study.",
        "recommended": True,
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "label": "Gemma 4 31B",
        "description": "A larger Gemma model when available.",
        "recommended": False,
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "label": "Nemotron 3 Ultra",
        "description": "Experimental.",
        "recommended": False,
        "experimental": True,
    },
    {
        "id": "openai/gpt-oss-120b:free",
        "label": "GPT-OSS 120B",
        "description": "Experimental.",
        "recommended": False,
        "experimental": True,
    },
)
