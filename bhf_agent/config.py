"""Configuration loading and validation for the BHF agent."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any, Optional, Union

from framework.canonical_library import DEFAULT_PUBLIC_CACHE_PATH, REVIEW_STATUS_VALUES
from framework.canonical_library.database_schema import DEFAULT_CKL_DATABASE_PATH

from .observability import ObservabilityConfig


class ConfigError(ValueError):
    """Raised when agent configuration is missing or invalid."""


ALLOWED_ANSWER_MODES = ("concise", "study", "teaching", "scholar")
ALLOWED_ADAPTERS = ("openai_compatible", "ollama")


@dataclass(frozen=True)
class CanonicalLibraryConfig:
    enabled: bool = True
    shadow_mode: bool = False
    fallback_to_model: bool = True
    strict_mode: bool = False
    minimum_relevance_score: float = 0.85
    cache_enabled: bool = True
    cache_max_entries: int = 512
    max_results: int = 5
    max_context_tokens: int = 1200
    include_placeholders: bool = False
    allowed_statuses: tuple[str, ...] = (
        "in_review",
        "reviewed",
        "approved",
    )
    backend: str = "sqlite"
    database_path: str = DEFAULT_CKL_DATABASE_PATH
    json_root: str | None = None
    stale_database_policy: str = "fallback_to_json"
    read_only: bool = True
    repository_cache_size: int = 256

    def validate(self) -> None:
        if self.backend not in {"sqlite", "json"}:
            raise ConfigError("canonical_library.backend must be one of: sqlite, json")
        if not str(self.database_path).strip():
            raise ConfigError("canonical_library.database_path must not be blank")
        if self.stale_database_policy not in {"error", "rebuild", "fallback_to_json", "ignore"}:
            raise ConfigError(
                "canonical_library.stale_database_policy must be one of: error, rebuild, fallback_to_json, ignore"
            )
        if int(self.repository_cache_size) <= 0:
            raise ConfigError("canonical_library.repository_cache_size must be greater than 0")
        if not 0 <= float(self.minimum_relevance_score) <= 1:
            raise ConfigError(
                "canonical_library.minimum_relevance_score must be between 0 and 1"
            )
        if int(self.cache_max_entries) <= 0:
            raise ConfigError(
                "canonical_library.cache_max_entries must be greater than 0"
            )
        if int(self.max_results) <= 0:
            raise ConfigError("canonical_library.max_results must be greater than 0")
        if int(self.max_context_tokens) <= 0:
            raise ConfigError(
                "canonical_library.max_context_tokens must be greater than 0"
            )
        if not self.allowed_statuses:
            raise ConfigError("canonical_library.allowed_statuses must not be empty")
        invalid = sorted(set(self.allowed_statuses) - set(REVIEW_STATUS_VALUES))
        if invalid:
            raise ConfigError(
                "canonical_library.allowed_statuses must be one of: "
                + ", ".join(REVIEW_STATUS_VALUES)
            )


@dataclass(frozen=True)
class PublicCacheConfig:
    enabled: bool = False
    path: str = str(DEFAULT_PUBLIC_CACHE_PATH)
    minimum_quality_score: float = 80.0
    default_ttl_days: int = 365
    allowed_review_statuses: tuple[str, ...] = (
        "reviewed",
        "approved",
    )

    def validate(self) -> None:
        if not str(self.path).strip():
            raise ConfigError("public_cache.path must not be blank")
        if not 0 <= float(self.minimum_quality_score) <= 100:
            raise ConfigError("public_cache.minimum_quality_score must be between 0 and 100")
        if int(self.default_ttl_days) <= 0:
            raise ConfigError("public_cache.default_ttl_days must be greater than 0")
        if not self.allowed_review_statuses:
            raise ConfigError("public_cache.allowed_review_statuses must not be empty")
        invalid = sorted(set(self.allowed_review_statuses) - set(REVIEW_STATUS_VALUES))
        if invalid:
            raise ConfigError(
                "public_cache.allowed_review_statuses must be one of: "
                + ", ".join(REVIEW_STATUS_VALUES)
            )


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
    timeout_seconds: Optional[float] = 600
    debug: bool = False
    auto_repair: bool = False
    max_repair_attempts: int = 1
    repair_threshold: int = 80
    memory_enabled: bool = False
    session_id: Optional[str] = None
    memory_path: Optional[str] = None
    memory_max_turns: int = 8
    canonical_library: CanonicalLibraryConfig = CanonicalLibraryConfig()
    public_cache: PublicCacheConfig = PublicCacheConfig()
    observability: ObservabilityConfig = ObservabilityConfig()

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
        data = dict(data)
        data["canonical_library"] = _canonical_library_config_from_value(
            data.get("canonical_library")
        )
        data["public_cache"] = _public_cache_config_from_value(data.get("public_cache"))
        data["observability"] = _observability_config_from_value(data.get("observability"))
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
        if "canonical_library" in clean:
            clean["canonical_library"] = _canonical_library_config_from_value(
                clean["canonical_library"],
                base=self.canonical_library,
            )
        if "public_cache" in clean:
            clean["public_cache"] = _public_cache_config_from_value(
                clean["public_cache"],
                base=self.public_cache,
            )
        if "observability" in clean:
            clean["observability"] = _observability_config_from_value(
                clean["observability"],
                base=self.observability,
            )
        config = replace(self, **clean)
        config.validate()
        return config

    def validate(self) -> None:
        if self.config_version != 1:
            raise ConfigError("only config_version 1 is supported")
        if not self.adapter:
            raise ConfigError("adapter is required")
        if self.adapter not in ALLOWED_ADAPTERS:
            raise ConfigError(
                "adapter must be one of: " + ", ".join(ALLOWED_ADAPTERS)
            )
        if self.adapter in {"openai_compatible", "ollama"} and not self.base_url:
            raise ConfigError(f"base_url is required for {self.adapter} adapter")
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
        if int(self.memory_max_turns) <= 0:
            raise ConfigError("memory_max_turns must be greater than 0")
        self.canonical_library.validate()
        self.public_cache.validate()
        try:
            self.observability.validate()
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        if self.public_cache.enabled and not (
            self.canonical_library.enabled or self.canonical_library.shadow_mode
        ):
            raise ConfigError(
                "public_cache requires canonical_library to be enabled or shadow_mode to be enabled"
            )

    def to_dict(self, redact_secrets: bool = True) -> dict[str, Any]:
        data = asdict(self)
        if redact_secrets and data.get("api_key"):
            data["api_key"] = "<redacted>"
        return data


def _canonical_library_config_from_value(
    value: Any,
    *,
    base: CanonicalLibraryConfig | None = None,
) -> CanonicalLibraryConfig:
    if isinstance(value, CanonicalLibraryConfig):
        config = value
    elif value is None:
        config = base or CanonicalLibraryConfig()
    elif isinstance(value, dict):
        base_config = base or CanonicalLibraryConfig()
        known = {field.name for field in fields(CanonicalLibraryConfig)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ConfigError(
                f"unknown canonical_library field(s): {', '.join(unknown)}"
            )
        merged = asdict(base_config)
        merged.update(value)
        config = CanonicalLibraryConfig(
            enabled=_coerce_bool(
                merged["enabled"], field_name="canonical_library.enabled"
            ),
            shadow_mode=_coerce_bool(
                merged["shadow_mode"],
                field_name="canonical_library.shadow_mode",
            ),
            fallback_to_model=_coerce_bool(
                merged["fallback_to_model"],
                field_name="canonical_library.fallback_to_model",
            ),
            strict_mode=_coerce_bool(
                merged["strict_mode"],
                field_name="canonical_library.strict_mode",
            ),
            minimum_relevance_score=_coerce_float(
                merged["minimum_relevance_score"],
                field_name="canonical_library.minimum_relevance_score",
            ),
            cache_enabled=_coerce_bool(
                merged["cache_enabled"],
                field_name="canonical_library.cache_enabled",
            ),
            cache_max_entries=_coerce_int(
                merged["cache_max_entries"],
                field_name="canonical_library.cache_max_entries",
            ),
            max_results=_coerce_int(
                merged["max_results"],
                field_name="canonical_library.max_results",
            ),
            max_context_tokens=_coerce_int(
                merged["max_context_tokens"],
                field_name="canonical_library.max_context_tokens",
            ),
            include_placeholders=_coerce_bool(
                merged["include_placeholders"],
                field_name="canonical_library.include_placeholders",
            ),
            allowed_statuses=_coerce_statuses(
                merged["allowed_statuses"],
                field_name="canonical_library.allowed_statuses",
            ),
            backend=str(
                os.environ.get("BHF_CKL_BACKEND", merged["backend"])
            ).strip().lower(),
            database_path=str(
                os.environ.get("BHF_CKL_DATABASE_PATH", merged["database_path"])
            ).strip()
            or DEFAULT_CKL_DATABASE_PATH,
            json_root=(
                str(os.environ.get("BHF_CKL_ROOT", merged["json_root"] or "")).strip()
                or None
            ),
            stale_database_policy=str(
                os.environ.get(
                    "BHF_CKL_STALE_DATABASE_POLICY",
                    merged["stale_database_policy"],
                )
            ).strip().lower(),
            read_only=_coerce_bool(
                merged["read_only"],
                field_name="canonical_library.read_only",
            ),
            repository_cache_size=_coerce_int(
                merged["repository_cache_size"],
                field_name="canonical_library.repository_cache_size",
            ),
        )
    else:
        raise ConfigError("canonical_library must be an object")

    return config


def _public_cache_config_from_value(
    value: Any,
    *,
    base: PublicCacheConfig | None = None,
) -> PublicCacheConfig:
    if isinstance(value, PublicCacheConfig):
        config = value
    elif value is None:
        config = base or PublicCacheConfig()
    elif isinstance(value, dict):
        base_config = base or PublicCacheConfig()
        known = {field.name for field in fields(PublicCacheConfig)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ConfigError(
                f"unknown public_cache field(s): {', '.join(unknown)}"
            )
        merged = asdict(base_config)
        merged.update(value)
        config = PublicCacheConfig(
            enabled=_coerce_bool(merged["enabled"], field_name="public_cache.enabled"),
            path=str(merged["path"]).strip() or str(DEFAULT_PUBLIC_CACHE_PATH),
            minimum_quality_score=_coerce_float(
                merged["minimum_quality_score"],
                field_name="public_cache.minimum_quality_score",
            ),
            default_ttl_days=_coerce_int(
                merged["default_ttl_days"],
                field_name="public_cache.default_ttl_days",
            ),
            allowed_review_statuses=_coerce_statuses(
                merged["allowed_review_statuses"],
                field_name="public_cache.allowed_review_statuses",
            ),
        )
    else:
        raise ConfigError("public_cache must be an object")

    config.validate()
    return config


def _observability_config_from_value(
    value: Any,
    *,
    base: ObservabilityConfig | None = None,
) -> ObservabilityConfig:
    if isinstance(value, ObservabilityConfig):
        config = value
    elif value is None:
        config = base or ObservabilityConfig()
    elif isinstance(value, dict):
        base_config = base or ObservabilityConfig()
        known = {field.name for field in fields(ObservabilityConfig)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ConfigError(
                f"unknown observability field(s): {', '.join(unknown)}"
            )
        merged = asdict(base_config)
        merged.update(value)
        config = ObservabilityConfig(
            enabled=_coerce_bool(merged["enabled"], field_name="observability.enabled"),
            verbose=_coerce_bool(merged["verbose"], field_name="observability.verbose"),
            redact_sensitive=_coerce_bool(
                merged["redact_sensitive"],
                field_name="observability.redact_sensitive",
            ),
        )
    else:
        raise ConfigError("observability must be an object")

    config.validate()
    return config


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"{field_name} must be true or false")


def _coerce_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc


def _coerce_float(value: Any, *, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a number") from exc


def _coerce_statuses(value: Any, *, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = [str(item).strip().lower() for item in value if str(item).strip()]
    else:
        raise ConfigError(f"{field_name} must be a list of review statuses")
    deduped = tuple(dict.fromkeys(items))
    if not deduped:
        raise ConfigError(f"{field_name} must not be empty")
    invalid = sorted(set(deduped) - set(REVIEW_STATUS_VALUES))
    if invalid:
        raise ConfigError(
            f"{field_name} must be one of: " + ", ".join(REVIEW_STATUS_VALUES)
        )
    return deduped
