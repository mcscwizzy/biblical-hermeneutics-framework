"""Fail-closed web configuration for optional presentation generation."""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from bhf_agent.adapters import ChatAdapter, build_chat_adapter
from bhf_agent.config import AgentConfig
from bhf_agent.presentation import (
    AdapterPresentationProvider,
    PresentationEngine,
    SQLitePresentationCache,
    default_presentation_cache_path,
    load_presentation_bundle,
)

from .forms import (
    WEB_CONFIG_PATH,
    config_from_form,
    load_web_defaults,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_PRESENTATION_TIMEOUT_SECONDS = 20.0
MAXIMUM_PRESENTATION_TIMEOUT_SECONDS = 30.0
DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS = 2
MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS = 16
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_SERVER_PROVIDER_ENV_FIELDS = {
    "LLM_PROVIDER",
    "BHF_BASE_URL",
    "BHF_MODEL",
    "BHF_API_KEY",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
}
_REQUEST_OPENROUTER_PROFILE_FIELDS = {
    "adapter",
    "model",
    "temperature",
    "max_tokens",
    "context_window",
    "timeout_seconds",
    "response_format_policy",
}


@dataclass(frozen=True)
class PresentationRuntimeSettings:
    enabled: bool = False
    timeout_seconds: float = DEFAULT_PRESENTATION_TIMEOUT_SECONDS
    maximum_concurrent_requests: int = DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS
    warning: str | None = None


@dataclass(frozen=True)
class PresentationRuntime:
    engine: PresentationEngine
    settings: PresentationRuntimeSettings
    configured: bool
    adapter_name: str | None = None
    model: str | None = None
    error: str | None = None
    bundle_path: str | None = None
    bundled_packet_count: int = 0
    bundle_error: str | None = None
    adapter_factory: Callable[[AgentConfig], ChatAdapter] = build_chat_adapter

    def diagnostics(self) -> dict[str, object]:
        result: dict[str, object] = {
            "enabled": self.settings.enabled,
            "legacy_default_enabled": self.settings.enabled,
            "configured": self.configured,
            "timeout_seconds": self.settings.timeout_seconds,
            "maximum_concurrent_requests": self.settings.maximum_concurrent_requests,
        }
        if self.adapter_name:
            result["adapter"] = self.adapter_name
        if self.model:
            result["model"] = self.model
        if self.settings.warning:
            result["warning"] = self.settings.warning
        if self.error:
            result["error"] = self.error
        bundle_diagnostics: dict[str, object] = {
            "configured": self.bundle_path is not None,
            "loaded": self.bundled_packet_count,
        }
        if self.bundle_path:
            bundle_diagnostics["path"] = self.bundle_path
        if self.bundle_error:
            bundle_diagnostics["error"] = self.bundle_error
        result["bundled_packets"] = bundle_diagnostics
        result["activity"] = self.engine.diagnostics()
        return result

    def provider_for_request(
        self,
        ai_profile: Mapping[str, Any] | None,
        transient_api_key: str | None,
    ) -> tuple[AdapterPresentationProvider | None, str | None]:
        """Build a provider that lives only for this HTTP request."""

        if not transient_api_key:
            provider = self.engine.provider
            profile = (
                str(getattr(provider, "generation_profile", "") or "") or None
                if provider is not None
                else None
            )
            return provider, profile

        submitted = dict(ai_profile or {})
        requested_adapter = str(submitted.get("adapter") or "openrouter").strip()
        if requested_adapter != "openrouter":
            raise ValueError(
                "Request-scoped presentation supports OpenRouter browser credentials only."
            )
        values = {
            key: submitted[key]
            for key in _REQUEST_OPENROUTER_PROFILE_FIELDS
            if key in submitted
        }
        # config_from_form pins this adapter to the shared OpenRouter endpoint;
        # connection targets and credentials are deliberately absent above.
        values["adapter"] = "openrouter"
        config = config_from_form(
            values,
            load_web_defaults().config,
            transient_api_key=transient_api_key,
        )
        provider = _provider_from_config(
            config,
            self.settings,
            adapter_factory=self.adapter_factory,
        )
        return provider, provider.generation_profile


def load_presentation_runtime_settings(
    environ: Mapping[str, str] | None = None,
) -> PresentationRuntimeSettings:
    """Read the legacy client default and bounded provider controls."""

    values = os.environ if environ is None else environ
    raw_enabled = str(values.get("BHF_PRESENTATION_ENABLED") or "").strip().lower()
    warning = None
    if not raw_enabled:
        enabled = False
    elif raw_enabled in _TRUE_VALUES:
        enabled = True
    elif raw_enabled in _FALSE_VALUES:
        enabled = False
    else:
        enabled = False
        warning = "BHF_PRESENTATION_ENABLED was invalid; the browser default remains off."

    timeout = DEFAULT_PRESENTATION_TIMEOUT_SECONDS
    raw_timeout = str(values.get("BHF_PRESENTATION_TIMEOUT_SECONDS") or "").strip()
    if raw_timeout:
        try:
            candidate = float(raw_timeout)
            if not math.isfinite(candidate) or candidate <= 0:
                raise ValueError
            timeout = min(candidate, MAXIMUM_PRESENTATION_TIMEOUT_SECONDS)
        except (TypeError, ValueError):
            timeout = DEFAULT_PRESENTATION_TIMEOUT_SECONDS
            timeout_warning = (
                "BHF_PRESENTATION_TIMEOUT_SECONDS was invalid; using the 20-second default."
            )
            warning = "; ".join(item for item in (warning, timeout_warning) if item)

    maximum_concurrent_requests = DEFAULT_MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS
    raw_concurrency = str(
        values.get("BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS") or ""
    ).strip()
    if raw_concurrency:
        try:
            candidate = int(raw_concurrency)
            if candidate < 1:
                raise ValueError
            maximum_concurrent_requests = min(
                candidate,
                MAXIMUM_CONCURRENT_PRESENTATION_REQUESTS,
            )
        except (TypeError, ValueError):
            concurrency_warning = (
                "BHF_PRESENTATION_MAX_CONCURRENT_REQUESTS was invalid; "
                "using the 2-request default."
            )
            warning = "; ".join(
                item for item in (warning, concurrency_warning) if item
            )

    return PresentationRuntimeSettings(
        enabled=enabled,
        timeout_seconds=timeout,
        maximum_concurrent_requests=maximum_concurrent_requests,
        warning=warning,
    )


def configure_presentation_runtime(
    *,
    study_db_path: str | Path,
    environ: Mapping[str, str] | None = None,
    agent_config: AgentConfig | None = None,
    adapter_factory: Callable[[AgentConfig], ChatAdapter] = build_chat_adapter,
) -> PresentationRuntime:
    """Create the engine without contacting a provider or exposing credentials."""

    values = os.environ if environ is None else environ
    settings = load_presentation_runtime_settings(values)
    cache_path = str(values.get("BHF_PRESENTATION_CACHE_PATH") or "").strip()
    cache = SQLitePresentationCache(
        cache_path or default_presentation_cache_path(study_db_path)
    )
    bundle_path = str(values.get("BHF_PRESENTATION_BUNDLE_PATH") or "").strip()
    bundled_packets = {}
    bundle_error = None
    if bundle_path:
        try:
            bundled_packets = load_presentation_bundle(bundle_path)
        except Exception as exc:  # noqa: BLE001 - optional bundles fail closed
            bundle_error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning("presentation bundle was not loaded: %s", bundle_error)
    engine_options = {
        "cache": cache,
        "bundled_packets": bundled_packets,
        "maximum_concurrent_provider_requests": (
            settings.maximum_concurrent_requests
        ),
    }
    runtime_options = {
        "bundle_path": bundle_path or None,
        "bundled_packet_count": len(bundled_packets),
        "bundle_error": bundle_error,
    }
    if not _server_provider_is_explicit(values, agent_config):
        return PresentationRuntime(
            engine=PresentationEngine(**engine_options),
            settings=settings,
            configured=False,
            adapter_factory=adapter_factory,
            **runtime_options,
        )
    try:
        config = agent_config or load_web_defaults().config
        provider = _provider_from_config(
            config,
            settings,
            adapter_factory=adapter_factory,
        )
        model = provider.model
    except Exception as exc:  # noqa: BLE001 - bad optional AI config must not break reading
        error = f"{type(exc).__name__}: {exc}"
        LOGGER.warning("presentation generation is not configured: %s", error)
        return PresentationRuntime(
            engine=PresentationEngine(**engine_options),
            settings=settings,
            configured=False,
            error=error,
            adapter_factory=adapter_factory,
            **runtime_options,
        )

    return PresentationRuntime(
        engine=PresentationEngine(
            provider=provider,
            **engine_options,
        ),
        settings=settings,
        configured=True,
        adapter_name=config.adapter,
        model=model,
        adapter_factory=adapter_factory,
        **runtime_options,
    )


def _server_provider_is_explicit(
    values: Mapping[str, str],
    agent_config: AgentConfig | None,
) -> bool:
    if agent_config is not None:
        return True
    adapter = str(values.get("LLM_PROVIDER") or "").strip().casefold()
    if adapter == "openrouter" and not str(values.get("BHF_API_KEY") or "").strip():
        return False
    if any(
        str(values.get(name) or "").strip()
        for name in _SERVER_PROVIDER_ENV_FIELDS
    ):
        return True
    return WEB_CONFIG_PATH.is_file()


def _provider_from_config(
    config: AgentConfig,
    settings: PresentationRuntimeSettings,
    *,
    adapter_factory: Callable[[AgentConfig], ChatAdapter],
) -> AdapterPresentationProvider:
    model = str(config.model or "").strip()
    if not model:
        raise ValueError("the configured model is blank")
    configured_timeout = config.timeout_seconds
    effective_timeout = settings.timeout_seconds
    if configured_timeout is not None:
        effective_timeout = min(effective_timeout, float(configured_timeout))
    bounded_config = replace(config, timeout_seconds=effective_timeout)
    bounded_config.validate()
    adapter = adapter_factory(bounded_config)
    return AdapterPresentationProvider(
        adapter,
        adapter_name=config.adapter,
        model=model,
        temperature=min(float(config.temperature), 0.2),
        max_tokens=min(int(config.max_tokens), 900),
        context_window=min(int(config.context_window), 4096),
    )
