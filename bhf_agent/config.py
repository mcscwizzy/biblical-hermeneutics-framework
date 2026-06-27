"""Configuration loading and validation for the BHF agent."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any, Optional, Union


class ConfigError(ValueError):
    """Raised when agent configuration is missing or invalid."""


ALLOWED_ANSWER_MODES = ("concise", "study", "teaching", "scholar")


@dataclass(frozen=True)
class AgentConfig:
    config_version: int = 1
    adapter: str = "openai_compatible"
    profile: str = "standard"
    answer_mode: str = "study"
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2048
    show_method_notes: bool = True
    timeout_seconds: Optional[float] = 360
    debug: bool = False
    auto_repair: bool = False
    max_repair_attempts: int = 1
    repair_threshold: int = 80

    @classmethod
    def from_json_file(cls, path: Union[str, Path]) -> "AgentConfig":
        config_path = Path(path)
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(f"config file not found: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"config file is not valid JSON: {config_path}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise ConfigError("config JSON must be an object")
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AgentConfig":
        known = {field.name for field in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ConfigError(f"unknown config field(s): {', '.join(unknown)}")
        try:
            config = cls(**data)
        except TypeError as exc:
            raise ConfigError(str(exc)) from exc
        config.validate()
        return config

    def with_overrides(self, **overrides: Any) -> "AgentConfig":
        clean = {key: value for key, value in overrides.items() if value is not None}
        known = {field.name for field in fields(self)}
        unknown = sorted(set(clean) - known)
        if unknown:
            raise ConfigError(f"unknown override field(s): {', '.join(unknown)}")
        config = replace(self, **clean)
        config.validate()
        return config

    def validate(self) -> None:
        if self.config_version != 1:
            raise ConfigError("only config_version 1 is supported")
        if not self.adapter:
            raise ConfigError("adapter is required")
        if self.adapter == "openai_compatible" and not self.base_url:
            raise ConfigError("base_url is required for openai_compatible adapter")
        if not self.model:
            raise ConfigError("model is required")
        if not self.profile:
            raise ConfigError("profile is required")
        if self.answer_mode not in ALLOWED_ANSWER_MODES:
            raise ConfigError(
                "answer_mode must be one of: " + ", ".join(ALLOWED_ANSWER_MODES)
            )
        if not 0 <= float(self.temperature) <= 2:
            raise ConfigError("temperature must be between 0 and 2")
        if int(self.max_tokens) <= 0:
            raise ConfigError("max_tokens must be greater than 0")
        if self.timeout_seconds is not None and float(self.timeout_seconds) <= 0:
            raise ConfigError("timeout_seconds must be greater than 0")
        if int(self.max_repair_attempts) < 0:
            raise ConfigError("max_repair_attempts must be greater than or equal to 0")
        if not 0 <= int(self.repair_threshold) <= 100:
            raise ConfigError("repair_threshold must be between 0 and 100")

    def to_dict(self, redact_secrets: bool = True) -> dict[str, Any]:
        data = asdict(self)
        if redact_secrets and data.get("api_key"):
            data["api_key"] = "<redacted>"
        return data
