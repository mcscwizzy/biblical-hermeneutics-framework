from __future__ import annotations

import os
import socket
import shutil
import tempfile
import threading
import time
from pathlib import Path

import pytest
import requests

from bhf_agent.study_db import initialize_database
from bhf_web import settings as web_settings


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_WAIT_SECONDS = 20


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_health(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/health", timeout=2)
            response.raise_for_status()
            if response.json().get("status") == "ok":
                return
        except Exception as exc:  # pragma: no cover - network timing varies
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {base_url}/api/health") from last_error


@pytest.fixture(scope="session")
def artifacts_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    configured = os.environ.get("BHF_GUI_ARTIFACTS_DIR", "").strip()
    if configured:
        path = Path(configured)
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = tmp_path_factory.mktemp("gui-artifacts")
    return path


@pytest.fixture(scope="session")
def base_url() -> str:
    configured = os.environ.get("BHF_GUI_BASE_URL", "").strip()
    if configured:
        base = configured.rstrip("/")
        _wait_for_health(base)
        return base

    original_db_path = web_settings.STUDY_DB_PATH
    original_web_config = web_settings.WEB_CONFIG_PATH
    original_test_mode = web_settings.TEST_MODE
    original_ckl_root = os.environ.get("BHF_CKL_ROOT")

    temp_dir = tempfile.TemporaryDirectory()
    temp_root = Path(temp_dir.name)
    db_path = temp_root / "study.sqlite"
    config_path = temp_root / "web-config.json"
    port = _free_port()
    local_base_url = f"{DEFAULT_BASE_URL.rsplit(':', 1)[0]}:{port}"

    canonical_root = temp_root / "canonical_library"
    shutil.copytree(
        Path("framework/canonical_library").resolve(),
        canonical_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    os.environ["BHF_CKL_ROOT"] = str(canonical_root)

    web_settings.STUDY_DB_PATH = db_path
    web_settings.WEB_CONFIG_PATH = config_path
    web_settings.TEST_MODE = True
    initialize_database(db_path)

    import bhf_agent.ckl as ckl_module
    from bhf_web.routes import canonical as canonical_routes

    ckl_module._load_default_canonical_library.cache_clear()
    canonical_routes._canonical_library.cache_clear()

    import bhf_web.app as app_module

    app = app_module.create_app()
    from uvicorn import Config, Server

    config = Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_health(local_base_url)

    yield local_base_url

    server.should_exit = True
    thread.join(timeout=10)
    temp_dir.cleanup()
    if original_ckl_root is None:
        os.environ.pop("BHF_CKL_ROOT", None)
    else:
        os.environ["BHF_CKL_ROOT"] = original_ckl_root
    web_settings.STUDY_DB_PATH = original_db_path
    web_settings.WEB_CONFIG_PATH = original_web_config
    web_settings.TEST_MODE = original_test_mode


@pytest.fixture(scope="session")
def browser_remote_url() -> str | None:
    value = os.environ.get("BHF_WEBDRIVER_URL", "").strip()
    return value or None


@pytest.fixture(scope="function")
def driver(request: pytest.FixtureRequest, artifacts_dir: Path, browser_remote_url: str | None):
    pytest.importorskip("selenium")
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService

    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1400")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    browser = None
    if browser_remote_url:
        try:
            browser = webdriver.Remote(command_executor=browser_remote_url, options=options)
        except WebDriverException as exc:  # pragma: no cover - depends on external selenium grid
            pytest.skip(f"Remote Chrome WebDriver is unavailable: {exc}")
    else:
        try:
            browser = webdriver.Chrome(options=options)
        except WebDriverException:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
            except Exception as exc:  # pragma: no cover - optional dependency
                pytest.skip(f"Chrome WebDriver is unavailable: {exc}")
            try:
                service = ChromeService(ChromeDriverManager().install())
                browser = webdriver.Chrome(service=service, options=options)
            except Exception as exc:  # pragma: no cover - webdriver-manager may need network
                pytest.skip(f"Chrome WebDriver is unavailable: {exc}")

    browser.set_page_load_timeout(DEFAULT_WAIT_SECONDS)
    browser.set_script_timeout(DEFAULT_WAIT_SECONDS)

    yield browser

    failed = bool(getattr(request.node, "rep_call", None) and request.node.rep_call.failed)
    if failed:
        stem = request.node.nodeid.replace("/", "_").replace("::", "__")
        screenshot_path = artifacts_dir / f"{stem}.png"
        try:
            browser.save_screenshot(str(screenshot_path))
        except Exception:
            pass
        try:
            browser_logs = browser.get_log("browser")
        except Exception:
            browser_logs = []
        if browser_logs:
            log_path = artifacts_dir / f"{stem}.browser.log"
            log_path.write_text("\n".join(str(entry) for entry in browser_logs), encoding="utf-8")
    browser.quit()


@pytest.fixture(scope="function")
def wait(driver):
    from selenium.webdriver.support.ui import WebDriverWait

    return WebDriverWait(driver, DEFAULT_WAIT_SECONDS)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
