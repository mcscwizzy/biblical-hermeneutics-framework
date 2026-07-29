"""Configuration loading and validation for the BHF agent."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any, Optional, Union

from framework.canonical_library import DEFAULT_PUBLIC_CACHE_PATH, REVIEW_STATUS_VALUES
from framework.canonical_library.database_schema import DEFAULT_CKL_DATABASE_PATH
from framework.lexical.service import DEFAULT_LEXICAL_DATABASE_PATH

from .observability import ObservabilityConfig


class ConfigError(ValueError):
    """Raised when agent configuration is missing or invalid."""


ALLOWED_ANSWER_MODES = ("concise", "study", "teaching", "scholar")
ALLOWED_ADAPTERS = ("openai_compatible", "ollama", "openrouter")
ALLOWED_RESPONSE_FORMAT_POLICIES = ("auto", "json_schema", "json_object", "off")
ALLOWED_RUNTIME_PROFILE_MODES = ("compact", "full")


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
class KnowledgeExpansionConfig:
    """Controls answer-coverage routing after local context retrieval.

    The coverage score is a deterministic routing estimate, not a claim about
    the mathematically complete coverage of biblical scholarship.
    """

    enabled: bool = True
    sufficient_coverage_threshold: float = 0.85
    major_gap_threshold: float = 0.60
    research_override_enabled: bool = True
    allow_model_knowledge_expansion: bool = True
    allow_external_retrieval: bool = False
    max_gap_items: int = 6

    def validate(self) -> None:
        if not 0.0 <= float(self.sufficient_coverage_threshold) <= 1.0:
            raise ConfigError(
                "knowledge_expansion.sufficient_coverage_threshold must be between 0 and 1"
            )
        if not 0.0 <= float(self.major_gap_threshold) <= 1.0:
            raise ConfigError(
                "knowledge_expansion.major_gap_threshold must be between 0 and 1"
            )
        if float(self.major_gap_threshold) >= float(self.sufficient_coverage_threshold):
            raise ConfigError(
                "knowledge_expansion.major_gap_threshold must be lower than "
                "knowledge_expansion.sufficient_coverage_threshold"
            )
        if int(self.max_gap_items) <= 0:
            raise ConfigError("knowledge_expansion.max_gap_items must be greater than 0")


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
class LexiconConfig:
    enabled: bool = True
    database_path: str = DEFAULT_CKL_DATABASE_PATH
    runtime_database_path: str = DEFAULT_LEXICAL_DATABASE_PATH
    max_occurrences: int = 5
    max_prompt_tokens: int = 350
    include_full_definitions: bool = False
    allow_model_context_explanation: bool = True

    def validate(self) -> None:
        if not str(self.database_path).strip():
            raise ConfigError("lexicon.database_path must not be blank")
        if not str(self.runtime_database_path).strip():
            raise ConfigError("lexicon.runtime_database_path must not be blank")
        if int(self.max_occurrences) <= 0:
            raise ConfigError("lexicon.max_occurrences must be greater than 0")
        if int(self.max_prompt_tokens) <= 0:
            raise ConfigError("lexicon.max_prompt_tokens must be greater than 0")


@dataclass(frozen=True)
class AgentConfig:
    config_version: int = 1
    adapter: str = "openai_compatible"
    profile: str = "standard"
    runtime_profile_mode: str = "compact"
    answer_mode: str = "study"
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 8192
    context_window: int = 12288
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
    knowledge_expansion: KnowledgeExpansionConfig = KnowledgeExpansionConfig()
    lexicon: LexiconConfig = LexiconConfig()
    public_cache: PublicCacheConfig = PublicCacheConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    response_format_policy: str = "auto"

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
        data["knowledge_expansion"] = _knowledge_expansion_config_from_value(
            data.get("knowledge_expansion")
        )
        data["lexicon"] = _lexicon_config_from_value(data.get("lexicon"))
        data["public_cache"] = _public_cache_config_from_value(data.get("public_cache"))
        data["observability"] = _observability_config_from_value(data.get("observability"))
        if "runtime_profile_mode" in data:
            data["runtime_profile_mode"] = _coerce_runtime_profile_mode(
                data["runtime_profile_mode"]
            )
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
        if "knowledge_expansion" in clean:
            clean["knowledge_expansion"] = _knowledge_expansion_config_from_value(
                clean["knowledge_expansion"],
                base=self.knowledge_expansion,
            )
        if "lexicon" in clean:
            clean["lexicon"] = _lexicon_config_from_value(
                clean["lexicon"],
                base=self.lexicon,
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
        if "runtime_profile_mode" in clean:
            clean["runtime_profile_mode"] = _coerce_runtime_profile_mode(
                clean["runtime_profile_mode"]
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
        if self.adapter in {"openai_compatible", "ollama", "openrouter"} and not self.base_url:
            raise ConfigError(f"base_url is required for {self.adapter} adapter")
        if self.adapter == "openrouter" and not self.api_key:
            raise ConfigError("api_key is required for openrouter adapter")
        if not self.model:
            raise ConfigError("model is required")
        if self.response_format_policy not in ALLOWED_RESPONSE_FORMAT_POLICIES:
            raise ConfigError(
                "response_format_policy must be one of: "
                + ", ".join(ALLOWED_RESPONSE_FORMAT_POLICIES)
            )
        if not self.profile:
            raise ConfigError("profile is required")
        if self.runtime_profile_mode not in ALLOWED_RUNTIME_PROFILE_MODES:
            raise ConfigError(
                "runtime_profile_mode must be one of: "
                + ", ".join(ALLOWED_RUNTIME_PROFILE_MODES)
            )
        if self.answer_mode not in ALLOWED_ANSWER_MODES:
            raise ConfigError(
                "answer_mode must be one of: " + ", ".join(ALLOWED_ANSWER_MODES)
            )
        if not 0 <= float(self.temperature) <= 2:
            raise ConfigError("temperature must be between 0 and 2")
        if int(self.max_tokens) <= 0:
            raise ConfigError("max_tokens must be greater than 0")
        if int(self.context_window) <= 0:
            raise ConfigError("context_window must be greater than 0")
        if self.timeout_seconds is not None and float(self.timeout_seconds) <= 0:
            raise ConfigError("timeout_seconds must be greater than 0")
        if int(self.max_repair_attempts) < 0:
            raise ConfigError("max_repair_attempts must be greater than or equal to 0")
        if not 0 <= int(self.repair_threshold) <= 100:
            raise ConfigError("repair_threshold must be between 0 and 100")
        if int(self.memory_max_turns) <= 0:
            raise ConfigError("memory_max_turns must be greater than 0")
        self.canonical_library.validate()
        self.knowledge_expansion.validate()
        self.lexicon.validate()
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


def _knowledge_expansion_config_from_value(
    value: Any,
    *,
    base: KnowledgeExpansionConfig | None = None,
) -> KnowledgeExpansionConfig:
    if isinstance(value, KnowledgeExpansionConfig):
        config = value
    elif value is None:
        config = base or KnowledgeExpansionConfig()
    elif isinstance(value, dict):
        base_config = base or KnowledgeExpansionConfig()
        known = {field.name for field in fields(KnowledgeExpansionConfig)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ConfigError(
                f"unknown knowledge_expansion field(s): {', '.join(unknown)}"
            )
        merged = asdict(base_config)
        merged.update(value)
        config = KnowledgeExpansionConfig(
            enabled=_coerce_bool(
                merged["enabled"], field_name="knowledge_expansion.enabled"
            ),
            sufficient_coverage_threshold=_coerce_float(
                merged["sufficient_coverage_threshold"],
                field_name="knowledge_expansion.sufficient_coverage_threshold",
            ),
            major_gap_threshold=_coerce_float(
                merged["major_gap_threshold"],
                field_name="knowledge_expansion.major_gap_threshold",
            ),
            research_override_enabled=_coerce_bool(
                merged["research_override_enabled"],
                field_name="knowledge_expansion.research_override_enabled",
            ),
            allow_model_knowledge_expansion=_coerce_bool(
                merged["allow_model_knowledge_expansion"],
                field_name="knowledge_expansion.allow_model_knowledge_expansion",
            ),
            allow_external_retrieval=_coerce_bool(
                merged["allow_external_retrieval"],
                field_name="knowledge_expansion.allow_external_retrieval",
            ),
            max_gap_items=_coerce_int(
                merged["max_gap_items"],
                field_name="knowledge_expansion.max_gap_items",
            ),
        )
    else:
        raise ConfigError("knowledge_expansion must be an object")

    config.validate()
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


def _lexicon_config_from_value(
    value: Any,
    *,
    base: LexiconConfig | None = None,
) -> LexiconConfig:
    if isinstance(value, LexiconConfig):
        config = value
    elif value is None:
        base_config = base or LexiconConfig()
        config = LexiconConfig(
            enabled=_coerce_bool(
                os.environ.get("BHF_LEXICON_ENABLED", base_config.enabled),
                field_name="lexicon.enabled",
            ),
            database_path=str(
                os.environ.get("BHF_LEXICON_DATABASE_PATH", base_config.database_path)
            ).strip()
            or DEFAULT_CKL_DATABASE_PATH,
            runtime_database_path=str(
                os.environ.get(
                    "BHF_LEXICAL_DATABASE_PATH", base_config.runtime_database_path
                )
            ).strip()
            or DEFAULT_LEXICAL_DATABASE_PATH,
            max_occurrences=_coerce_int(
                os.environ.get("BHF_LEXICON_MAX_OCCURRENCES", base_config.max_occurrences),
                field_name="lexicon.max_occurrences",
            ),
            max_prompt_tokens=_coerce_int(
                os.environ.get(
                    "BHF_LEXICON_MAX_PROMPT_TOKENS",
                    base_config.max_prompt_tokens,
                ),
                field_name="lexicon.max_prompt_tokens",
            ),
            include_full_definitions=base_config.include_full_definitions,
            allow_model_context_explanation=base_config.allow_model_context_explanation,
        )
    elif isinstance(value, dict):
        base_config = base or LexiconConfig()
        known = {field.name for field in fields(LexiconConfig)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ConfigError(f"unknown lexicon field(s): {', '.join(unknown)}")
        merged = asdict(base_config)
        merged.update(value)
        config = LexiconConfig(
            enabled=_coerce_bool(
                os.environ.get("BHF_LEXICON_ENABLED", merged["enabled"]),
                field_name="lexicon.enabled",
            ),
            database_path=str(
                os.environ.get("BHF_LEXICON_DATABASE_PATH", merged["database_path"])
            ).strip()
            or DEFAULT_CKL_DATABASE_PATH,
            runtime_database_path=str(
                os.environ.get(
                    "BHF_LEXICAL_DATABASE_PATH", merged["runtime_database_path"]
                )
            ).strip()
            or DEFAULT_LEXICAL_DATABASE_PATH,
            max_occurrences=_coerce_int(
                os.environ.get("BHF_LEXICON_MAX_OCCURRENCES", merged["max_occurrences"]),
                field_name="lexicon.max_occurrences",
            ),
            max_prompt_tokens=_coerce_int(
                os.environ.get(
                    "BHF_LEXICON_MAX_PROMPT_TOKENS",
                    merged["max_prompt_tokens"],
                ),
                field_name="lexicon.max_prompt_tokens",
            ),
            include_full_definitions=_coerce_bool(
                merged["include_full_definitions"],
                field_name="lexicon.include_full_definitions",
            ),
            allow_model_context_explanation=_coerce_bool(
                merged["allow_model_context_explanation"],
                field_name="lexicon.allow_model_context_explanation",
            ),
        )
    else:
        raise ConfigError("lexicon must be an object")

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


def _coerce_runtime_profile_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode not in ALLOWED_RUNTIME_PROFILE_MODES:
        raise ConfigError(
            "runtime_profile_mode must be one of: "
            + ", ".join(ALLOWED_RUNTIME_PROFILE_MODES)
        )
    return mode
