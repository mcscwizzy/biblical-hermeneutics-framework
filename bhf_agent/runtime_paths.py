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
    bhf_commentary_storage_path: Path
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


def packaged_commentary_storage_path() -> Path:
    """Return the immutable commentary corpus bundled with the application."""

    project_root = Path(__file__).resolve().parents[1]
    return project_root / ".bhf-data" / "bhf-commentary"


def default_commentary_storage_path(environ: Mapping[str, str]) -> Path:
    """Resolve commentary separately from writable runtime data.

    Vercel's ``/tmp`` directory is appropriate for mutable runtime state but
    does not contain the released commentary corpus. The corpus is packaged
    with the application and must be read from the resolved project root.
    Local development retains the existing relative path for NAS and source
    checkout compatibility.
    """

    if environ.get("VERCEL"):
        return packaged_commentary_storage_path()
    return Path(".bhf-data") / "bhf-commentary"


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
        bhf_commentary_storage_path=Path(
            values.get("BHF_COMMENTARY_STORAGE_PATH")
            or default_commentary_storage_path(values)
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
    "default_commentary_storage_path",
    "default_runtime_data_dir",
    "packaged_commentary_storage_path",
    "resolve_runtime_data_paths",
]
