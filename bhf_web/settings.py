"""Runtime settings for the BHF web UI."""

from __future__ import annotations

import os
from pathlib import Path

from bhf_agent.study_db import DEFAULT_DB_PATH


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


STUDY_DB_PATH = Path(os.environ.get("BHF_STUDY_DB_PATH", str(DEFAULT_DB_PATH)))
JOB_DB_PATH = Path(
    os.environ.get("BHF_JOB_DB_PATH", str(STUDY_DB_PATH.with_name("jobs.sqlite")))
)
COMMENTARY_DB_PATH = Path(os.environ.get("BHF_COMMENTARY_DB_PATH", ".bhf/commentary.sqlite"))
WEB_CONFIG_PATH = Path(os.environ.get("BHF_WEB_CONFIG_PATH", ".bhf/web-config.json"))
TEST_MODE = _env_bool("BHF_TEST_MODE", False)
