"""Deployment-aware paths for BHF runtime state and packaged data."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_COMMENTARY_RELEASE = "commentary-v1.1"
LEGACY_COMMENTARY_RELEASE = "commentary-v1.0"
_COMMENTARY_RELEASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PACKAGED_COMMENTARY_DIRS = {
    DEFAULT_COMMENTARY_RELEASE: ".bhf-data/bhf-commentary-v1.1",
    LEGACY_COMMENTARY_RELEASE: ".bhf-data/bhf-commentary",
    "commentary-v1.2": ".bhf-data/bhf-commentary-v1.2",
}


@dataclass(frozen=True)
class RuntimeDataPaths:
    """Resolved runtime paths shared by the agent and web runtime."""

    data_dir: Path
    study_db_path: Path
    job_db_path: Path
    commentary_db_path: Path
    bhf_commentary_storage_path: Path | None
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


def configured_commentary_release(environ: Mapping[str, str] | None = None) -> str:
    """Return the validated immutable commentary release identifier."""

    values = os.environ if environ is None else environ
    release = str(values.get("BHF_COMMENTARY_RELEASE") or DEFAULT_COMMENTARY_RELEASE).strip()
    if not _COMMENTARY_RELEASE_RE.fullmatch(release):
        return DEFAULT_COMMENTARY_RELEASE
    return release if release in _PACKAGED_COMMENTARY_DIRS else DEFAULT_COMMENTARY_RELEASE


def packaged_commentary_storage_path(release: str = DEFAULT_COMMENTARY_RELEASE) -> Path:
    """Return the conventional local path for an immutable authoring release."""

    project_root = Path(__file__).resolve().parents[1]
    packaged_dir = _PACKAGED_COMMENTARY_DIRS.get(release, _PACKAGED_COMMENTARY_DIRS[DEFAULT_COMMENTARY_RELEASE])
    source_checkout_path = project_root / packaged_dir
    if source_checkout_path.is_dir():
        return source_checkout_path
    # The generated releases are not part of the reader package. Keep the
    # conventional fallback for local authoring tools run outside a checkout.
    package_data_path = Path(__file__).resolve().parent / "data" / release
    return package_data_path if package_data_path.is_dir() else source_checkout_path


def default_commentary_storage_path(environ: Mapping[str, str]) -> Path:
    """Resolve the generated release path for authoring and audit tools.

    The browser app no longer uses this selector. Local tooling uses the
    immutable source checkout path or an explicit override; candidate paths
    remain blocked on Vercel.
    """

    release = configured_commentary_release(environ)
    explicit_path = environ.get("BHF_COMMENTARY_STORAGE_PATH")
    if explicit_path:
        explicit = Path(explicit_path)
        if environ.get("VERCEL") and "bhf-commentary-candidates" in explicit.parts:
            return packaged_commentary_storage_path(release)
        return explicit
    if environ.get("VERCEL"):
        return packaged_commentary_storage_path(release)
    return Path(_PACKAGED_COMMENTARY_DIRS[release])


def resolve_runtime_data_paths(
    environ: Mapping[str, str] | None = None,
    *,
    include_bhf_commentary: bool = True,
) -> RuntimeDataPaths:
    """Resolve runtime paths, optionally including the authoring release path."""

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
        bhf_commentary_storage_path=(
            default_commentary_storage_path(values) if include_bhf_commentary else None
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


# The running app uses Bible, Tyndale, user-state, and cache paths. Keep the
# generated BHF release selector lazy and opt in only for authoring/reporting
# tools that explicitly request it with resolve_runtime_data_paths().
RUNTIME_DATA_PATHS = resolve_runtime_data_paths(include_bhf_commentary=False)


__all__ = [
    "RUNTIME_DATA_PATHS",
    "RuntimeDataPaths",
    "DEFAULT_COMMENTARY_RELEASE",
    "LEGACY_COMMENTARY_RELEASE",
    "configured_commentary_release",
    "default_commentary_storage_path",
    "default_runtime_data_dir",
    "packaged_commentary_storage_path",
    "resolve_runtime_data_paths",
]
