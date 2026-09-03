"""Deployment-aware paths for writable BHF runtime state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class RuntimeDataPaths:
    """Resolved writable paths shared by the agent and web runtime."""

    data_dir: Path
    study_db_path: Path
    job_db_path: Path
    commentary_db_path: Path
    translations_path: Path
    reader_settings_path: Path
    web_config_path: Path
    memory_path: Path
    public_cache_path: Path


def default_runtime_data_dir(environ: Mapping[str, str]) -> Path:
    """Return the deployment's writable runtime-data directory."""

    if environ.get("VERCEL"):
        return Path("/tmp/bhf-data")
    return Path(".bhf-data")


def resolve_runtime_data_paths(
    environ: Mapping[str, str] | None = None,
) -> RuntimeDataPaths:
    """Resolve writable runtime paths while preserving explicit overrides."""

    values = os.environ if environ is None else environ
    data_dir = Path(values.get("BHF_DATA_DIR") or default_runtime_data_dir(values))
    return RuntimeDataPaths(
        data_dir=data_dir,
        study_db_path=Path(
            values.get("BHF_STUDY_DB_PATH") or data_dir / "study.sqlite"
        ),
        job_db_path=Path(values.get("BHF_JOB_DB_PATH") or data_dir / "jobs.sqlite"),
        commentary_db_path=Path(
            values.get("BHF_COMMENTARY_DB_PATH") or data_dir / "commentary.sqlite"
        ),
        translations_path=Path(
            values.get("BHF_TRANSLATIONS_PATH") or data_dir / "translations"
        ),
        reader_settings_path=Path(
            values.get("BHF_READER_SETTINGS_PATH")
            or data_dir / "reader-settings.json"
        ),
        web_config_path=Path(
            values.get("BHF_WEB_CONFIG_PATH") or data_dir / "web-config.json"
        ),
        memory_path=Path(values.get("BHF_MEMORY_PATH") or data_dir / "sessions"),
        public_cache_path=Path(
            values.get("BHF_PUBLIC_CACHE_PATH")
            or data_dir / "public-answer-cache.json"
        ),
    )


RUNTIME_DATA_PATHS = resolve_runtime_data_paths()


__all__ = [
    "RUNTIME_DATA_PATHS",
    "RuntimeDataPaths",
    "default_runtime_data_dir",
    "resolve_runtime_data_paths",
]
