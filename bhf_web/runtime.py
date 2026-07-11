"""Runtime configuration for the BHF web UI and future mobile wrappers."""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_PROVIDER_LABELS: dict[str, str] = {
    "local": "Local",
    "openai": "OpenAI",
    "ollama": "Ollama",
    "apple-native-placeholder": "Apple Native Placeholder",
}

DEFAULT_BREAKPOINTS: dict[str, int] = {
    "phone": 680,
    "tablet": 900,
}


def load_runtime_config() -> dict[str, Any]:
    """Return the runtime config injected into the web shell."""

    mode = _normalize_mode(os.environ.get("BHF_RUNTIME_MODE", "web"))
    api_base_url = os.environ.get("BHF_API_BASE_URL", "").strip()
    provider_labels = _load_provider_labels()

    return {
        "appName": "Biblical Hermeneutics Framework",
        "shortName": "BHF",
        "mode": mode,
        "apiBaseUrl": api_base_url,
        "providerLabels": provider_labels,
        "breakpoints": dict(DEFAULT_BREAKPOINTS),
        "themeColor": "#245b82",
        "backgroundColor": "#f6f7f8",
        "enableServiceWorker": mode != "capacitor",
        "offlinePath": "/offline",
    }


def _normalize_mode(value: str | None) -> str:
    normalized = str(value or "web").strip().lower()
    if normalized not in {"web", "pwa", "capacitor"}:
        return "web"
    return normalized


def _load_provider_labels() -> dict[str, str]:
    raw = os.environ.get("BHF_PROVIDER_LABELS_JSON", "").strip()
    if not raw:
        return dict(DEFAULT_PROVIDER_LABELS)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_PROVIDER_LABELS)

    if not isinstance(data, dict):
        return dict(DEFAULT_PROVIDER_LABELS)

    labels: dict[str, str] = dict(DEFAULT_PROVIDER_LABELS)
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip():
            labels[key.strip()] = value.strip()
    return labels
