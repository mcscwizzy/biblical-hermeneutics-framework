"""Persisted Commentary v1.2 prose-renderer policy and resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bhf_agent.config import AgentConfig


V12_PIPELINE_VERSION = "commentary-v1.2-enrichment"
DEFAULT_V12_PROSE_CONFIG = Path("config/commentary-v1.2-prose.json")
DEFAULT_V12_PROSE_MODEL = "gpt-5.6-terra"
DEFAULT_V12_PROSE_EFFORT = "high"


class V12ProseConfigurationError(RuntimeError):
    """The v1.2 prose configuration cannot be used safely."""


@dataclass(frozen=True)
class V12ProseConfiguration:
    config: AgentConfig
    path: Path
    is_default: bool

    def metadata(self) -> dict[str, Any]:
        return {
            "pipeline": V12_PIPELINE_VERSION,
            "model": self.config.model,
            "prose_model": "Terra" if self.config.model == DEFAULT_V12_PROSE_MODEL else self.config.model,
            "effort": self.config.reasoning_effort,
            "prose_effort": self.config.reasoning_effort,
            "config_path": self.path.as_posix(),
        }


def resolve_v12_prose_config_path(
    repo_root: str | Path,
    explicit_path: str | Path | None = None,
) -> tuple[Path, bool]:
    """Resolve an explicit config or the persisted project default."""

    if explicit_path is not None and str(explicit_path).strip():
        return Path(explicit_path), False
    return Path(repo_root) / DEFAULT_V12_PROSE_CONFIG, True


def load_v12_prose_configuration(
    repo_root: str | Path,
    explicit_path: str | Path | None = None,
) -> V12ProseConfiguration:
    path, is_default = resolve_v12_prose_config_path(repo_root, explicit_path)
    try:
        config = AgentConfig.from_json_file(path)
    except Exception as exc:
        raise V12ProseConfigurationError(
            f"TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: cannot load prose config {path}: {exc}"
        ) from exc
    if is_default and (
        config.model != DEFAULT_V12_PROSE_MODEL
        or config.reasoning_effort != DEFAULT_V12_PROSE_EFFORT
    ):
        raise V12ProseConfigurationError(
            "TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: persisted default must select "
            f"{DEFAULT_V12_PROSE_MODEL} with {DEFAULT_V12_PROSE_EFFORT} effort"
        )
    return V12ProseConfiguration(config=config, path=path, is_default=is_default)


def ensure_v12_prose_renderer_available(
    configuration: V12ProseConfiguration,
    *,
    build_adapter: Any,
    credential_present: Any,
) -> None:
    """Fail closed before generation when Terra High cannot be invoked."""

    config = configuration.config
    if config.model != DEFAULT_V12_PROSE_MODEL:
        return
    if config.reasoning_effort != DEFAULT_V12_PROSE_EFFORT:
        raise V12ProseConfigurationError(
            "TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: Terra requires high reasoning effort"
        )
    if config.adapter not in {"openai_compatible", "openrouter"}:
        raise V12ProseConfigurationError(
            "TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: configured adapter cannot invoke Terra: "
            f"{config.adapter}"
        )
    if not credential_present(config):
        raise V12ProseConfigurationError(
            "TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: provider authentication is missing"
        )
    try:
        adapter = build_adapter(config)
        health = adapter.health_check(config.model)
    except Exception as exc:
        raise V12ProseConfigurationError(
            f"TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: provider preflight failed: {exc}"
        ) from exc
    if not isinstance(health, dict) or not health.get("ok"):
        raise V12ProseConfigurationError(
            "TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: provider health check failed"
        )
    if health.get("model_present") is False:
        raise V12ProseConfigurationError(
            f"TERRA_HIGH_PROSE_RENDERER_UNAVAILABLE: model {config.model} is unavailable"
        )


__all__ = [
    "DEFAULT_V12_PROSE_CONFIG",
    "DEFAULT_V12_PROSE_EFFORT",
    "DEFAULT_V12_PROSE_MODEL",
    "V12_PIPELINE_VERSION",
    "V12ProseConfiguration",
    "V12ProseConfigurationError",
    "ensure_v12_prose_renderer_available",
    "load_v12_prose_configuration",
    "resolve_v12_prose_config_path",
]
