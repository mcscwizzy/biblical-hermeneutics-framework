"""Runtime settings for the BHF web UI."""

from __future__ import annotations

import os

from bhf_agent.runtime_paths import (
    RUNTIME_DATA_PATHS,
    RuntimeDataPaths,
    default_runtime_data_dir,
    resolve_runtime_data_paths,
)


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


DATA_DIR = RUNTIME_DATA_PATHS.data_dir
STUDY_DB_PATH = RUNTIME_DATA_PATHS.study_db_path
JOB_DB_PATH = RUNTIME_DATA_PATHS.job_db_path
COMMENTARY_DB_PATH = RUNTIME_DATA_PATHS.commentary_db_path
BHF_COMMENTARY_STORAGE_PATH = RUNTIME_DATA_PATHS.bhf_commentary_storage_path
TRANSLATIONS_PATH = RUNTIME_DATA_PATHS.translations_path
READER_SETTINGS_PATH = RUNTIME_DATA_PATHS.reader_settings_path
WEB_CONFIG_PATH = RUNTIME_DATA_PATHS.web_config_path
MEMORY_PATH = RUNTIME_DATA_PATHS.memory_path
PUBLIC_CACHE_PATH = RUNTIME_DATA_PATHS.public_cache_path
TEST_MODE = _env_bool("BHF_TEST_MODE", False)


_default_data_dir = default_runtime_data_dir
