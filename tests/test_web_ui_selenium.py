from __future__ import annotations

import shutil
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import patch

from bhf_agent.study_db import initialize_database

try:
    from uvicorn import Config, Server

    HAS_UVICORN = True
except ModuleNotFoundError:
    Config = None
    Server = None
    HAS_UVICORN = False

try:
    from bhf_web import app as web_app_module

    HAS_WEB_DEPS = True
except ModuleNotFoundError:
    web_app_module = None
    HAS_WEB_DEPS = False

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    HAS_SELENIUM = True
except ImportError:  # pragma: no cover - optional local dependency
    webdriver = None
    WebDriverException = None
    By = None
    FirefoxOptions = None
    EC = None
    WebDriverWait = None
    HAS_SELENIUM = False


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_url(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2):
                return
        except Exception as exc:  # pragma: no cover - network timing varies
            last_error = exc
            time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for {url}") from last_error


@unittest.skipUnless(
    HAS_SELENIUM and HAS_WEB_DEPS and HAS_UVICORN and shutil.which("firefox"),
    "Firefox, selenium, uvicorn, and the web app dependencies are required for browser smoke tests.",
)
class WebUiSeleniumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "study.sqlite"
        initialize_database(cls._db_path)
        cls._patch = patch.object(web_app_module, "STUDY_DB_PATH", cls._db_path)
        cls._patch.start()
        cls._app = web_app_module.create_app()
        cls._port = _free_port()
        cls._base_url = f"http://127.0.0.1:{cls._port}"
        cls._server = Config(
            cls._app,
            host="127.0.0.1",
            port=cls._port,
            log_level="warning",
            access_log=False,
        )
        cls._server_runner = Server(cls._server)
        cls._thread = threading.Thread(target=cls._server_runner.run, daemon=True)
        cls._thread.start()
        _wait_for_url(f"{cls._base_url}/api/health")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_server_runner", None) is not None:
            cls._server_runner.should_exit = True
        if getattr(cls, "_thread", None) is not None:
            cls._thread.join(timeout=10)
        if getattr(cls, "_patch", None) is not None:
            cls._patch.stop()
        if getattr(cls, "_tmpdir", None) is not None:
            cls._tmpdir.cleanup()

    def setUp(self):
        options = FirefoxOptions()
        options.add_argument("-headless")
        try:
            self.driver = webdriver.Firefox(options=options)
        except Exception as exc:  # pragma: no cover - depends on local browser setup
            raise unittest.SkipTest(f"Firefox WebDriver could not start: {exc}") from exc
        self.driver.set_page_load_timeout(30)
        self.driver.set_window_size(390, 844)

    def tearDown(self):
        self.driver.quit()

    def open_home(self):
        self.driver.get(self._base_url + "/")
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-workspace-drawer-toggle]"))
        )

    def open_mobile_workspace(self):
        self.open_home()
        self.driver.find_element(By.CSS_SELECTOR, "[data-workspace-drawer-toggle]").click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: "is-open" in driver.find_element(By.ID, "study-panel").get_attribute("class")
        )

    def test_mobile_workspace_drawer_opens_at_the_top(self):
        self.open_mobile_workspace()
        panel = self.driver.find_element(By.ID, "study-panel")
        rect = panel.rect

        self.assertLessEqual(rect["y"], 4)
        self.assertGreater(rect["width"], 300)
        self.assertTrue(panel.is_displayed())

    def test_map_browse_search_is_available_without_selection(self):
        self.open_mobile_workspace()
        self.driver.find_element(By.ID, "workspace-tab-maps").click()
        WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-open-map-browser]"))
        )
        self.driver.find_element(By.CSS_SELECTOR, "[data-open-map-browser]").click()
        WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-map-browser]"))
        )

        search_input = self.driver.find_element(By.CSS_SELECTOR, "[data-map-search-query]")
        search_input.clear()
        search_input.send_keys("Jerusalem")
        self.driver.find_element(By.CSS_SELECTOR, "[data-map-search-submit]").click()

        WebDriverWait(self.driver, 20).until(
            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#map-search-results-list .map-search-result")) > 0
        )

        results = self.driver.find_elements(By.CSS_SELECTOR, "#map-search-results-list .map-search-result")
        self.assertGreater(len(results), 0)

    def test_reader_search_selection_navigation_and_next_chapter_are_mobile_usable(self):
        self.open_mobile_workspace()
        query_input = self.driver.find_element(By.CSS_SELECTOR, "[data-bible-search] input[name='query']")
        query_input.clear()
        query_input.send_keys("John 1:1")
        self.driver.find_element(By.CSS_SELECTOR, "[data-bible-search] button[type='submit']").click()

        WebDriverWait(self.driver, 20).until(
            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#reader-search-results-body .search-result-card")) > 0
        )

        self.driver.find_element(By.CSS_SELECTOR, "#reader-search-results-body [data-search-action='open-chapter']").click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: "John 1" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
        )
        search_panel = self.driver.find_element(By.ID, "reader-search-results")
        self.assertFalse(search_panel.is_displayed())

        next_button = self.driver.find_element(By.CSS_SELECTOR, "[data-next-chapter]")
        self.assertFalse(next_button.get_attribute("disabled"))
        next_button.click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: "John 2" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
        )
        self.assertFalse(self.driver.find_element(By.ID, "reader-search-results").is_displayed())


if __name__ == "__main__":
    unittest.main()
