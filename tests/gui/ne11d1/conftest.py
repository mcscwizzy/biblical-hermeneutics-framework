from __future__ import annotations

import os
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest
import requests

from bhf_agent.study_db import initialize_database
from bhf_web import settings as web_settings


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str) -> None:
    deadline = time.time() + 45
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/health", timeout=2)
            response.raise_for_status()
            if response.json().get("status") == "ok":
                return
        except Exception as exc:  # pragma: no cover - runtime startup varies
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {base_url}/api/health") from last_error


@pytest.fixture(scope="session")
def base_url():
    original_db_path = web_settings.STUDY_DB_PATH
    original_web_config = web_settings.WEB_CONFIG_PATH
    original_test_mode = web_settings.TEST_MODE
    original_ckl_root = os.environ.get("BHF_CKL_ROOT")
    original_explorer_flag = os.environ.get("BHF_NARRATIVE_EXPLORER_ENABLED")

    temporary = tempfile.TemporaryDirectory(prefix="ne11d1-browser-")
    root = Path(temporary.name)
    study_db_path = root / "study.sqlite"
    web_config_path = root / "web-config.json"
    canonical_root = root / "canonical_library"
    shutil.copytree(
        Path("framework/canonical_library").resolve(),
        canonical_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    os.environ["BHF_CKL_ROOT"] = str(canonical_root)
    os.environ["BHF_NARRATIVE_EXPLORER_ENABLED"] = "1"
    web_settings.STUDY_DB_PATH = study_db_path
    web_settings.WEB_CONFIG_PATH = web_config_path
    web_settings.TEST_MODE = True
    initialize_database(study_db_path)

    import bhf_agent.ckl as ckl_module
    from bhf_web.routes import canonical as canonical_routes

    ckl_module._load_default_canonical_library.cache_clear()
    canonical_routes._canonical_library.cache_clear()

    import bhf_web.app as app_module
    from uvicorn import Config, Server

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    server = Server(Config(
        app_module.create_app(),
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    ))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_health(base)

    yield base

    server.should_exit = True
    thread.join(timeout=10)
    temporary.cleanup()
    if original_ckl_root is None:
        os.environ.pop("BHF_CKL_ROOT", None)
    else:
        os.environ["BHF_CKL_ROOT"] = original_ckl_root
    if original_explorer_flag is None:
        os.environ.pop("BHF_NARRATIVE_EXPLORER_ENABLED", None)
    else:
        os.environ["BHF_NARRATIVE_EXPLORER_ENABLED"] = original_explorer_flag
    web_settings.STUDY_DB_PATH = original_db_path
    web_settings.WEB_CONFIG_PATH = original_web_config
    web_settings.TEST_MODE = original_test_mode
    ckl_module._load_default_canonical_library.cache_clear()
    canonical_routes._canonical_library.cache_clear()
