"""Runtime configuration for the BHF web UI and future mobile wrappers."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.parse import urlsplit

from .ai_config import browser_ai_config

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

BACKEND_CONFIGURATION_MESSAGE = (
    "BHF_API_BASE_URL is required when BHF_BACKEND_MODE=remote."
)


def load_runtime_config() -> dict[str, Any]:
    """Return the runtime config injected into the web shell."""

    mode = _normalize_mode(os.environ.get("BHF_RUNTIME_MODE", "web"))
    backend_mode = _normalize_backend_mode(
        os.environ.get("BHF_BACKEND_MODE", "same-origin")
    )
    api_base_url = os.environ.get("BHF_API_BASE_URL", "").strip()
    backend_config_error = _backend_configuration_error(
        backend_mode,
        api_base_url,
    )
    async_jobs = not (
        backend_mode == "same-origin" and bool(os.environ.get("VERCEL"))
    )
    provider_labels = _load_provider_labels()

    return {
        "appName": "BHF Bible Reader",
        "shortName": "BHF Bible",
        "mode": mode,
        "backendMode": backend_mode,
        "apiBaseUrl": api_base_url,
        "backendConfigError": backend_config_error,
        # Vercel instances cannot reliably preserve an in-memory/SQLite job
        # between polling requests.  The browser uses the synchronous /ask
        # route there, while durable and self-hosted backends keep progress
        # polling through /ask/jobs.
        "asyncJobs": async_jobs,
        # Presentation enhancement has no synchronous serverless fallback: it
        # remains deterministic-only when durable polling state is unavailable.
        "presentationJobs": async_jobs,
        "providerLabels": provider_labels,
        "breakpoints": dict(DEFAULT_BREAKPOINTS),
        "themeColor": "#245b82",
        "backgroundColor": "#f6f7f8",
        "enableServiceWorker": mode != "capacitor",
        "offlinePath": "/offline",
        "ai": browser_ai_config(),
        # OAuth client IDs and redirect URLs are public configuration. Secrets
        # are never injected into the browser; OneDrive uses PKCE.
        "studyVault": {
            "oneDriveClientId": os.environ.get("BHF_ONEDRIVE_CLIENT_ID", "").strip(),
            "oneDriveRedirectUri": os.environ.get("BHF_ONEDRIVE_REDIRECT_URI", "").strip(),
            "cloudKitContainerIdentifier": os.environ.get("BHF_CLOUDKIT_CONTAINER_IDENTIFIER", "").strip(),
            "cloudKitApiToken": os.environ.get("BHF_CLOUDKIT_API_TOKEN", "").strip(),
            "cloudKitEnvironment": os.environ.get("BHF_CLOUDKIT_ENVIRONMENT", "production").strip().lower(),
        },
    }


def _normalize_mode(value: str | None) -> str:
    normalized = str(value or "web").strip().lower()
    if normalized not in {"web", "pwa", "capacitor"}:
        return "web"
    return normalized


def _normalize_backend_mode(value: str | None) -> str:
    normalized = str(value or "same-origin").strip().lower()
    if normalized in {"same-origin", "remote"}:
        return normalized
    return normalized or "same-origin"


def _backend_configuration_error(backend_mode: str, api_base_url: str) -> str:
    if backend_mode not in {"same-origin", "remote"}:
        return "BHF_BACKEND_MODE must be either same-origin or remote."
    if backend_mode == "same-origin":
        return ""
    if not api_base_url:
        return BACKEND_CONFIGURATION_MESSAGE
    parsed = urlsplit(api_base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return (
            "BHF_API_BASE_URL must be a valid http(s) backend URL when "
            "BHF_BACKEND_MODE=remote."
        )
    return ""


def load_cors_origins(environ: Mapping[str, str] | None = None) -> list[str]:
    """Return the explicit browser-origin allowlist for split-host deployments."""

    values = os.environ if environ is None else environ
    origins: list[str] = []
    for raw_origin in values.get("BHF_CORS_ORIGINS", "").split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "BHF_CORS_ORIGINS must contain comma-separated http(s) origins "
                "without paths or wildcards."
            )
        if origin not in origins:
            origins.append(origin)
    return origins


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
