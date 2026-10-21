"""Deployment-aware paths for BHF runtime state and packaged data."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class RuntimeDataPaths:
    """Resolved runtime paths shared by the agent and web runtime."""

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


def packaged_tyndale_database_path() -> Path:
    """Return the immutable Tyndale database bundled into Vercel functions."""

    repository_root = Path(__file__).resolve().parents[1]
    return repository_root / "framework" / "commentary" / "data" / "tyndale.sqlite"


def resolve_runtime_data_paths(
    environ: Mapping[str, str] | None = None,
) -> RuntimeDataPaths:
    """Resolve runtime paths for Bible, Tyndale, and user study data."""

    values = os.environ if environ is None else environ
    data_dir = Path(values.get("BHF_DATA_DIR") or default_runtime_data_dir(values))
    configured_commentary_path = values.get("BHF_COMMENTARY_DB_PATH")
    packaged_commentary_path = packaged_tyndale_database_path()
    if configured_commentary_path:
        commentary_db_path = Path(configured_commentary_path)
    elif values.get("VERCEL") and packaged_commentary_path.is_file():
        commentary_db_path = packaged_commentary_path
    else:
        commentary_db_path = data_dir / "commentary.sqlite"
    return RuntimeDataPaths(
        data_dir=data_dir,
        study_db_path=Path(
            values.get("BHF_STUDY_DB_PATH") or data_dir / "study.sqlite"
        ),
        job_db_path=Path(values.get("BHF_JOB_DB_PATH") or data_dir / "jobs.sqlite"),
        commentary_db_path=commentary_db_path,
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


# The running app uses Bible, Tyndale, user-state, and cache paths.
RUNTIME_DATA_PATHS = resolve_runtime_data_paths()


__all__ = [
    "RUNTIME_DATA_PATHS",
    "RuntimeDataPaths",
    "default_runtime_data_dir",
    "packaged_tyndale_database_path",
    "resolve_runtime_data_paths",
]
