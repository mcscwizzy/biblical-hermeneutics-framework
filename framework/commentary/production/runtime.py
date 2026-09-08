"""Explicit, secret-safe runtime configuration for Commentary production."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from bhf_agent.adapters.factory import build_chat_adapter
from bhf_agent.chapter_commentary.generator import DEFAULT_COMMENTARY_MAX_TOKENS
from bhf_agent.config import AgentConfig, ConfigError

from .models import PRODUCTION_VERSION, ProductionError, sha256_json


RUNTIME_CONFIG_ARTIFACT_VERSION = "commentary-production-runtime-config-v1"
_CREDENTIAL_ENV = "BHF_API_KEY"
_REQUIRED_MANIFEST_CONTRACTS = {
    "commentary_prompt_version": "1.5",
    "commentary_schema_version": "1.2",
    "synthesis_schema_version": "1.1",
    "synthesis_compiler_version": "1.1",
    "gate_version": "commentary-richness-gate-v2.1",
    "dense_reader_version": "commentary-dense-reader-v0.1",
}

EXTERNAL_HANDOFF_MODE = "external_handoff"
DIRECT_PROVIDER_MODE = "direct_provider"


def handoff_generation_receipt(
    renderer_identity: str,
    *,
    reader_enabled: bool,
    contract_versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the deterministic identity for a renderer outside ProductionRunner.

    This deliberately contains no endpoint, credential, or API model field.
    ``renderer_identity`` is an audit label for the external execution
    environment, not a provider identifier.
    """

    label = str(renderer_identity or "").strip()
    if not label:
        raise _runtime_error(
            "EXTERNAL_RENDERER_IDENTITY_REQUIRED",
            "handoff mode requires a non-empty renderer identity",
        )
    contracts = dict(contract_versions or _REQUIRED_MANIFEST_CONTRACTS)
    values = {
        "generation_mode": EXTERNAL_HANDOFF_MODE,
        "renderer_identity": label,
        "commentary_prompt_version": contracts.get("commentary_prompt_version"),
        "commentary_schema_version": contracts.get("commentary_schema_version"),
        "synthesis_schema_version": contracts.get("synthesis_schema_version"),
        "synthesis_compiler_version": contracts.get("synthesis_compiler_version"),
        "gate_version": contracts.get("gate_version"),
        "reader_enabled": bool(reader_enabled),
        "runner_version": PRODUCTION_VERSION,
    }
    return {
        "artifact_version": "commentary-production-handoff-generation-v1",
        "generation_mode": EXTERNAL_HANDOFF_MODE,
        "renderer_identity": label,
        "parameters": values,
        "generation_identity": sha256_json(values),
    }


def validate_handoff_renderer(renderer_identity: str) -> str:
    label = str(renderer_identity or "").strip()
    if not label:
        raise _runtime_error(
            "EXTERNAL_RENDERER_IDENTITY_REQUIRED",
            "handoff mode requires --renderer LABEL",
        )
    return label


def _runtime_error(code: str, message: str) -> ProductionError:
    return ProductionError(f"{code}: {message}")


def resolve_runtime_config(path: str | Path | None) -> AgentConfig:
    """Load the canonical AgentConfig and resolve only the existing API-key env convention."""

    if path is None or not str(path).strip():
        raise _runtime_error(
            "PRODUCTION_RUNTIME_CONFIG_REQUIRED",
            "run, resume, and preflight require --config PATH",
        )
    try:
        config = AgentConfig.from_json_file(path)
    except ConfigError as exc:
        raise _runtime_error("PRODUCTION_RUNTIME_CONFIG_INVALID", str(exc)) from exc

    # BHF_API_KEY is already the web/runtime convention. It is intentionally
    # read only into memory and is never copied to a production artifact.
    env_key = os.environ.get(_CREDENTIAL_ENV, "").strip()
    if env_key and not config.api_key:
        config = config.with_overrides(api_key=env_key)
    if config.api_key == "<redacted>":
        raise _runtime_error(
            "PRODUCTION_RUNTIME_CONFIG_INVALID",
            "api_key must be supplied by the config file or BHF_API_KEY, not as <redacted>",
        )

    return resolve_runtime_config_from_object(config)


def resolve_runtime_config_from_object(config: AgentConfig) -> AgentConfig:
    """Normalize an already loaded config for runner/test injection."""

    if not config.model or str(config.model).strip().lower() in {
        "unknown",
        "none",
        "configured-at-run",
    }:
        raise _runtime_error(
            "PRODUCTION_RUNTIME_CONFIG_INVALID",
            "model must be an intentional non-placeholder model identity",
        )
    try:
        config = config.with_overrides(
            commentary_max_tokens=_effective_commentary_max_tokens(config)
        )
        config.validate()
    except (ConfigError, ValueError) as exc:
        raise _runtime_error("PRODUCTION_RUNTIME_CONFIG_INVALID", str(exc)) from exc
    _validate_base_url_for_artifacts(config)
    return config


def _effective_commentary_max_tokens(config: AgentConfig) -> int:
    if config.commentary_max_tokens is not None:
        value = int(config.commentary_max_tokens)
    else:
        raw = os.environ.get("BHF_COMMENTARY_MAX_TOKENS", "").strip()
        if raw:
            try:
                value = int(raw)
            except ValueError as exc:
                raise ConfigError("BHF_COMMENTARY_MAX_TOKENS must be an integer") from exc
        else:
            value = DEFAULT_COMMENTARY_MAX_TOKENS
    if value <= 0:
        raise ConfigError("commentary_max_tokens must be greater than 0")
    return value


def _validate_base_url_for_artifacts(config: AgentConfig) -> None:
    if not config.base_url:
        return
    parsed = urlsplit(config.base_url)
    if parsed.username is not None or parsed.password is not None:
        raise _runtime_error(
            "PRODUCTION_RUNTIME_CONFIG_INVALID",
            "base_url must not contain embedded credentials",
        )


def credential_present(config: AgentConfig) -> bool:
    if config.adapter == "claude_cli":
        # Claude CLI stores authentication outside AgentConfig. Construction
        # confirms the executable is present; authentication itself is checked
        # only by a real generation call and is therefore not probed here.
        return True
    return bool(config.api_key)


def runtime_parameters(config: AgentConfig, *, reader_enabled: bool) -> dict[str, Any]:
    """Return the redacted material generation settings."""

    return {
        "adapter": config.adapter,
        "model": str(config.model or ""),
        "base_url": config.base_url,
        "temperature": float(config.temperature),
        "max_tokens": int(config.max_tokens),
        "max_output_tokens": int(config.commentary_max_tokens or DEFAULT_COMMENTARY_MAX_TOKENS),
        "context_window": int(config.context_window),
        "timeout_seconds": config.timeout_seconds,
        "response_format_policy": config.response_format_policy,
        "reader_enabled": bool(reader_enabled),
        "runner_version": PRODUCTION_VERSION,
        "credential_present": credential_present(config),
    }


def runtime_config_identity(config: AgentConfig, *, reader_enabled: bool) -> str:
    """Hash generation-affecting values only; secrets and paths are excluded."""

    values = runtime_parameters(config, reader_enabled=reader_enabled)
    values.pop("credential_present", None)
    # The endpoint is material, but must not include credentials (validated
    # above). Preserve it in the identity so provider routing cannot drift.
    return sha256_json(values)


def runtime_receipt(config: AgentConfig, *, reader_enabled: bool) -> dict[str, Any]:
    parameters = runtime_parameters(config, reader_enabled=reader_enabled)
    return {
        "artifact_version": RUNTIME_CONFIG_ARTIFACT_VERSION,
        "runtime_config_identity": runtime_config_identity(
            config, reader_enabled=reader_enabled
        ),
        "parameters": parameters,
    }


def build_runtime_adapter(config: AgentConfig):
    """Construct the configured adapter. This function must never call chat()."""

    try:
        return build_chat_adapter(config)
    except (ConfigError, ImportError, RuntimeError, ValueError) as exc:
        raise _runtime_error("PRODUCTION_RUNTIME_ADAPTER_INVALID", str(exc)) from exc


def validate_manifest_for_preflight(manifest: dict[str, Any], *, canary_limit: int) -> list[str]:
    errors: list[str] = []
    if manifest.get("status") != "PLANNED_NOT_AUTHORIZED":
        errors.append("manifest status must be PLANNED_NOT_AUTHORIZED")
    chapters = manifest.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        errors.append("manifest must contain chapters")
    elif len(chapters) > canary_limit and not manifest.get("full_corpus_authorized", False):
        errors.append(f"manifest has more than {canary_limit} chapters without full-corpus authorization")
    if manifest.get("full_corpus_authorized", False):
        errors.append("preflight does not authorize a full corpus")
    for key, expected in _REQUIRED_MANIFEST_CONTRACTS.items():
        if manifest.get("contract_versions", {}).get(key) != expected:
            errors.append(f"contract_versions.{key} must be {expected}")
    generation_config = manifest.get("generation_config", {})
    if generation_config.get("provider_adapter") != "configured-at-run":
        errors.append("manifest generation_config.provider_adapter must remain configured-at-run")
    if generation_config.get("model") != "configured-at-run":
        errors.append("manifest generation_config.model must remain configured-at-run")
    return errors


def validate_manifest_for_handoff(
    manifest: dict[str, Any],
    *,
    canary_limit: int,
    allow_full_corpus: bool = False,
) -> list[str]:
    """Validate a planned manifest without imposing API runtime placeholders."""

    errors = validate_manifest_for_preflight(manifest, canary_limit=canary_limit)
    errors = [
        error for error in errors
        if not error.startswith("manifest generation_config.provider_adapter must remain configured-at-run")
        and not error.startswith("manifest generation_config.model must remain configured-at-run")
        and not (allow_full_corpus and error == "preflight does not authorize a full corpus")
    ]
    generation_config = manifest.get("generation_config") or {}
    if generation_config.get("provider_adapter") not in (None, "configured-at-run"):
        errors.append("handoff manifest must not select an API provider adapter")
    if generation_config.get("model") not in (None, "configured-at-run"):
        errors.append("handoff manifest must not select an API model")
    return errors


def redacted_preflight_report(
    manifest: dict[str, Any],
    config: AgentConfig,
    *,
    reader_enabled: bool,
    input_identities_match: bool,
    adapter_constructed: bool,
) -> dict[str, Any]:
    parameters = runtime_parameters(config, reader_enabled=reader_enabled)
    return {
        "status": "READY",
        "manifest_identity": manifest["manifest_identity"],
        "run_id": manifest["run_id"],
        "chapter_count": len(manifest["chapters"]),
        "manifest_status": manifest["status"],
        "input_identities_match": input_identities_match,
        "runtime_config_identity": runtime_config_identity(
            config, reader_enabled=reader_enabled
        ),
        "runtime": parameters,
        "reader_enabled": bool(reader_enabled),
        "adapter_constructed": adapter_constructed,
        "provider_called": False,
    }
