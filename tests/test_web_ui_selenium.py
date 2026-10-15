from __future__ import annotations

import asyncio
import os
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
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

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
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
    except PermissionError as exc:
        raise unittest.SkipTest(f"Browser smoke tests require socket access: {exc}") from exc


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
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="reader-passage"]'))
        )

    def open_mobile_workspace(self, section: str = "ask"):
        self.open_home()
        if section == "bible":
            return
        self.driver.find_element(By.CSS_SELECTOR, f'[data-testid="app-dock-{section}"]').click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script("return document.body.dataset.appSection") == section
        )

    def test_mobile_workspace_drawer_opens_at_the_top(self):
        self.open_mobile_workspace("ask")
        panel = self.driver.find_element(By.ID, "study-panel")
        rect = panel.rect

        self.assertLessEqual(rect["y"], 4)
        self.assertGreater(rect["width"], 300)
        self.assertTrue(panel.is_displayed())

    def test_map_browse_search_is_available_without_selection(self):
        self.open_mobile_workspace("explore")
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
        search_input.send_keys("Jerusalem", Keys.ENTER)

        WebDriverWait(self.driver, 20).until(
            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#map-search-results-list .map-search-result")) > 0
        )

        results = self.driver.find_elements(By.CSS_SELECTOR, "#map-search-results-list .map-search-result")
        self.assertGreater(len(results), 0)

    def test_reader_search_selection_navigation_and_next_chapter_are_mobile_usable(self):
        self.open_home()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script("return document.body.dataset.appSection") == "bible"
        )
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
        chapter_select = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='chapter-input']")
        Select(chapter_select).select_by_value("2")
        WebDriverWait(self.driver, 20).until(
            lambda driver: "John 2" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
        )
        self.assertFalse(self.driver.find_element(By.ID, "reader-search-results").is_displayed())


@unittest.skipUnless(
    HAS_SELENIUM and HAS_WEB_DEPS and HAS_UVICORN and shutil.which("firefox"),
    "Firefox, selenium, uvicorn, and the web app dependencies are required for browser smoke tests.",
)
class NarrativeExplorerWebUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "study.sqlite"
        initialize_database(cls._db_path)
        cls._db_patch = patch.object(web_app_module, "STUDY_DB_PATH", cls._db_path)
        cls._db_patch.start()
        cls._environment_patch = patch.dict(os.environ, {
            "BHF_NARRATIVE_EXPLORER_ENABLED": "1",
            "BHF_CKL_ROOT": str(Path(__file__).resolve().parents[1] / "framework" / "canonical_library"),
        })
        cls._environment_patch.start()
        cls._app = web_app_module.create_app()
        import httpx

        async def warm_narrative_explorer():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=cls._app),
                base_url="http://testserver",
            ) as client:
                response = await client.get("/api/narrative-explorer/v1/passages/John/1")
                if response.status_code != 200:
                    raise AssertionError(f"NE-3 John 1 prewarm returned HTTP {response.status_code}")

        asyncio.run(warm_narrative_explorer())
        cls._port = _free_port()
        cls._base_url = f"http://127.0.0.1:{cls._port}"
        cls._server_runner = Server(Config(
            cls._app,
            host="127.0.0.1",
            port=cls._port,
            log_level="warning",
            access_log=False,
        ))
        cls._thread = threading.Thread(target=cls._server_runner.run, daemon=True)
        cls._thread.start()
        _wait_for_url(f"{cls._base_url}/api/health")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_server_runner", None) is not None:
            cls._server_runner.should_exit = True
        if getattr(cls, "_thread", None) is not None:
            cls._thread.join(timeout=10)
        if getattr(cls, "_environment_patch", None) is not None:
            cls._environment_patch.stop()
        if getattr(cls, "_db_patch", None) is not None:
            cls._db_patch.stop()
        if getattr(cls, "_tmpdir", None) is not None:
            cls._tmpdir.cleanup()

    def setUp(self):
        options = FirefoxOptions()
        options.add_argument("-headless")
        try:
            self.driver = webdriver.Firefox(options=options)
        except Exception as exc:  # pragma: no cover - depends on local browser setup
            raise unittest.SkipTest(f"Firefox WebDriver could not start: {exc}") from exc
        self.driver.set_page_load_timeout(90)
        self.driver.set_script_timeout(90)

    def tearDown(self):
        self.driver.quit()

    def test_feature_flagged_explorer_uses_desktop_dock_and_mobile_sheet(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(self.driver, 90)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        entry = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']")))
        self.assertEqual(entry.text, "Explore the Narrative")
        self.driver.execute_script(
            """
            window.__ne4ExplorerMetrics = [];
            document.addEventListener('bhf:narrative-explorer-metrics', event => window.__ne4ExplorerMetrics.push(event.detail));
            """,
        )
        self.driver.save_screenshot("/tmp/ne4-narrative-explorer-desktop.png")
        entry.send_keys(Keys.ENTER)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        cards = self.driver.find_elements(By.CSS_SELECTOR, ".narrative-explorer-section")
        self.assertEqual(len(cards), 6)
        self.assertIn("John 1", self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        self.assertGreater(len(self.driver.find_elements(By.CSS_SELECTOR, ".narrative-explorer-item")), 0)
        self.assertLessEqual(
            self.driver.execute_script("return document.documentElement.scrollWidth"),
            self.driver.execute_script("return window.innerWidth"),
        )
        requests = self.driver.execute_script("return performance.getEntriesByType('resource').filter(e => e.name.includes('/api/narrative-explorer/v1/passages/')).length")
        self.assertEqual(requests, 1)
        response_metric = self.driver.execute_script("return window.__ne4ExplorerMetrics.find(item => item.phase === 'response')")
        render_metric = self.driver.execute_script("return window.__ne4ExplorerMetrics.find(item => item.phase === 'render')")
        self.assertGreater(response_metric["payload_bytes"], 0)
        self.assertEqual(response_metric["network_requests"], 1)
        self.assertGreaterEqual(render_metric["dom_node_growth"], 50)

        self.driver.back()
        wait.until(lambda driver: driver.switch_to.active_element.get_attribute("data-testid") == "companion-narrative-explorer")
        self.driver.forward()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        self.assertEqual(
            self.driver.execute_script("return performance.getEntriesByType('resource').filter(e => e.name.includes('/api/narrative-explorer/v1/passages/')).length"),
            2,
        )
        self.driver.back()
        wait.until(lambda driver: driver.switch_to.active_element.get_attribute("data-testid") == "companion-narrative-explorer")

        self.driver.set_window_size(390, 844)
        wait.until(lambda driver: driver.execute_script("return window.matchMedia('(max-width: 760px)').matches"))
        self.driver.find_element(By.CSS_SELECTOR, "#chapter-reader [data-verse-select]").click()
        wait.until(lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "peek")
        peek = self.driver.find_element(By.CSS_SELECTOR, "[data-companion-state-control='study'].companion-peek")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-companion-state-control='study'].companion-peek")))
        wait.until(lambda driver: driver.execute_script(
            "const p=document.querySelector('.companion-peek').getBoundingClientRect(); const d=document.querySelector('.app-dock').getBoundingClientRect(); return p.bottom <= d.top + 1;"
        ))
        peek.click()
        mobile_entry = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']")))
        size = self.driver.execute_script(
            "const r=arguments[0].getBoundingClientRect(); return {width:r.width,height:r.height};",
            mobile_entry,
        )
        self.assertGreaterEqual(size["height"], 44)
        mobile_entry.click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        panel = self.driver.find_element(By.ID, "study-panel")
        self.assertEqual(panel.get_attribute("data-companion-state"), "full")
        self.assertIn("John 1:1", self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        self.assertLessEqual(
            self.driver.execute_script("return document.documentElement.scrollWidth"),
            self.driver.execute_script("return window.innerWidth"),
        )
        self.driver.save_screenshot("/tmp/ne4-narrative-explorer-mobile.png")
        self.driver.find_element(By.CSS_SELECTOR, "[data-companion-back]").click()
        wait.until(lambda driver: driver.switch_to.active_element.get_attribute("data-testid") == "companion-narrative-explorer")
        self.driver.find_element(By.CSS_SELECTOR, "[data-companion-state-control='closed']").click()
        wait.until(lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "closed")


if __name__ == "__main__":
    unittest.main()
