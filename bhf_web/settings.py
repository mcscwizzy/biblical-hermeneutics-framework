"""Runtime settings for the BHF web UI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class RuntimeDataPaths:
    data_dir: Path
    study_db_path: Path
    job_db_path: Path
    commentary_db_path: Path


def resolve_runtime_data_paths(
    environ: Mapping[str, str] | None = None,
) -> RuntimeDataPaths:
    """Resolve writable database paths, preserving explicit path overrides."""

    values = os.environ if environ is None else environ
    data_dir = Path(values.get("BHF_DATA_DIR") or ".bhf-data")
    return RuntimeDataPaths(
        data_dir=data_dir,
        study_db_path=Path(
            values.get("BHF_STUDY_DB_PATH") or data_dir / "study.sqlite"
        ),
        job_db_path=Path(values.get("BHF_JOB_DB_PATH") or data_dir / "jobs.sqlite"),
        commentary_db_path=Path(
            values.get("BHF_COMMENTARY_DB_PATH") or data_dir / "commentary.sqlite"
        ),
    )


RUNTIME_DATA_PATHS = resolve_runtime_data_paths()
DATA_DIR = RUNTIME_DATA_PATHS.data_dir
STUDY_DB_PATH = RUNTIME_DATA_PATHS.study_db_path
JOB_DB_PATH = RUNTIME_DATA_PATHS.job_db_path
COMMENTARY_DB_PATH = RUNTIME_DATA_PATHS.commentary_db_path
WEB_CONFIG_PATH = Path(os.environ.get("BHF_WEB_CONFIG_PATH", ".bhf/web-config.json"))
TEST_MODE = _env_bool("BHF_TEST_MODE", False)
