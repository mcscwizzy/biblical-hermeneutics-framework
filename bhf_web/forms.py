"""Form parsing and local defaults for the BHF web UI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from bhf_agent.config import ALLOWED_ANSWER_MODES, AgentConfig, ConfigError


WEB_CONFIG_PATH = Path(".bhf") / "web-config.json"

ENV_CONFIG_FIELDS = {
    "BHF_BASE_URL": "base_url",
    "BHF_MODEL": "model",
    "BHF_PROFILE": "profile",
    "BHF_ANSWER_MODE": "answer_mode",
    "BHF_TEMPERATURE": "temperature",
    "BHF_MAX_TOKENS": "max_tokens",
    "BHF_TIMEOUT_SECONDS": "timeout_seconds",
    "BHF_SHOW_METHOD_NOTES": "show_method_notes",
    "BHF_MEMORY_ENABLED": "memory_enabled",
    "BHF_MEMORY_PATH": "memory_path",
    "BHF_SESSION_ID": "session_id",
    "BHF_API_KEY": "api_key",
}

DEFAULT_CONFIG_VALUES: dict[str, Any] = {
    "config_version": 1,
    "adapter": "openai_compatible",
    "profile": "minimal-7b",
    "answer_mode": "study",
    "model": "llama3.1:8b",
    "base_url": "http://localhost:11434/v1",
    "temperature": 0.3,
    "max_tokens": 2048,
    "show_method_notes": True,
    "timeout_seconds": 600,
    "debug": False,
    "auto_repair": False,
    "max_repair_attempts": 1,
    "repair_threshold": 80,
    "memory_enabled": False,
    "session_id": None,
    "memory_path": None,
    "memory_max_turns": 8,
}


@dataclass(frozen=True)
class LoadedDefaults:
    config: AgentConfig
    warning: str | None = None


def load_web_defaults(path: Path | str = WEB_CONFIG_PATH) -> LoadedDefaults:
    """Load optional local web defaults, falling back to safe local values."""

    values = dict(DEFAULT_CONFIG_VALUES)
    warning = None
    config_path = Path(path)

    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warning = f"Could not read {config_path}: {exc}. Using other defaults."
        else:
            if isinstance(data, dict):
                values.update(data)
            else:
                warning = f"{config_path} must contain a JSON object. Using other defaults."

    env_warning = _apply_env_overrides(values, os.environ)
    if env_warning:
        warning = "; ".join(item for item in (warning, env_warning) if item)

    try:
        return LoadedDefaults(AgentConfig.from_mapping(values), warning)
    except ConfigError as exc:
        fallback_values = dict(DEFAULT_CONFIG_VALUES)
        _apply_env_overrides(fallback_values, os.environ)
        fallback = AgentConfig.from_mapping(fallback_values)
        return LoadedDefaults(
            fallback,
            f"{config_path} or environment defaults are invalid: {exc}. Using built-in/environment defaults.",
        )


def config_from_form(
    form: Mapping[str, Any],
    defaults: AgentConfig | None = None,
) -> AgentConfig:
    """Build an AgentConfig from submitted form values."""

    base = defaults or load_web_defaults().config
    overrides = {
        "profile": _required_text(form, "profile"),
        "answer_mode": _required_text(form, "answer_mode"),
        "model": _required_text(form, "model"),
        "base_url": _required_text(form, "base_url"),
        "temperature": _float_value(form, "temperature"),
        "max_tokens": _int_value(form, "max_tokens"),
        "timeout_seconds": _optional_float_value(form, "timeout_seconds"),
        "show_method_notes": _checked(form, "show_method_notes"),
        "memory_enabled": _checked(form, "memory_enabled"),
        "session_id": _optional_text(form, "session_id"),
        "memory_path": _optional_text(form, "memory_path"),
        "memory_max_turns": _int_value(form, "memory_max_turns"),
        "debug": False,
    }
    return base.with_overrides(**overrides)


def form_values_from_config(config: AgentConfig, question: str = "") -> dict[str, Any]:
    """Convert an AgentConfig into template-safe form values."""

    return {
        "question": question,
        "profile": config.profile,
        "answer_mode": config.answer_mode,
        "model": config.model or "",
        "base_url": config.base_url or "",
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds or "",
        "show_method_notes": config.show_method_notes,
        "memory_enabled": config.memory_enabled,
        "session_id": config.session_id or "",
        "memory_path": config.memory_path or "",
        "memory_max_turns": config.memory_max_turns,
    }


def validate_question(form: Mapping[str, Any]) -> str:
    question = str(form.get("question") or "").strip()
    if not question:
        raise ConfigError("question is required")
    return question


def _required_text(form: Mapping[str, Any], name: str) -> str:
    value = str(form.get(name) or "").strip()
    if not value:
        raise ConfigError(f"{name.replace('_', ' ')} is required")
    return value


def _optional_text(form: Mapping[str, Any], name: str) -> str | None:
    value = str(form.get(name) or "").strip()
    return value or None


def _float_value(form: Mapping[str, Any], name: str) -> float:
    value = str(form.get(name) or "").strip()
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name.replace('_', ' ')} must be a number") from exc


def _optional_float_value(form: Mapping[str, Any], name: str) -> float | None:
    value = str(form.get(name) or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name.replace('_', ' ')} must be a number") from exc


def _int_value(form: Mapping[str, Any], name: str) -> int:
    value = str(form.get(name) or "").strip()
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name.replace('_', ' ')} must be an integer") from exc


def _checked(form: Mapping[str, Any], name: str) -> bool:
    return name in form


def _apply_env_overrides(values: dict[str, Any], environ: Mapping[str, str]) -> str | None:
    warnings: list[str] = []
    for env_name, field_name in ENV_CONFIG_FIELDS.items():
        raw_value = environ.get(env_name)
        if raw_value is None or raw_value == "":
            continue
        try:
            values[field_name] = _env_value(field_name, raw_value)
        except ConfigError as exc:
            warnings.append(f"{env_name}: {exc}")
    return "; ".join(warnings) or None


def _env_value(field_name: str, raw_value: str) -> Any:
    if field_name in {"temperature", "timeout_seconds"}:
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ConfigError(f"{field_name} must be a number") from exc
    if field_name in {"max_tokens"}:
        try:
            return int(raw_value)
        except ValueError as exc:
            raise ConfigError(f"{field_name} must be an integer") from exc
    if field_name in {"show_method_notes", "memory_enabled"}:
        return _env_bool(raw_value, field_name)
    return raw_value.strip()


def _env_bool(raw_value: str, field_name: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{field_name} must be true or false")


ANSWER_MODES = ALLOWED_ANSWER_MODES
