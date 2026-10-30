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

from bhf_agent import translation_registry, translation_settings
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
        commentary_db = Path(__file__).resolve().parents[1] / ".bhf" / "commentary.sqlite"
        cls._commentary_db_patch = None
        if commentary_db.is_file():
            cls._commentary_db_path = Path(cls._tmpdir.name) / "commentary.sqlite"
            shutil.copy2(commentary_db, cls._commentary_db_path)
            cls._commentary_db_patch = patch.object(
                web_app_module,
                "COMMENTARY_DB_PATH",
                cls._commentary_db_path,
            )
            cls._commentary_db_patch.start()
        else:
            cls._commentary_db_path = None
        cls._reader_settings_patch = patch.object(
            translation_settings,
            "SETTINGS_PATH",
            Path(cls._tmpdir.name) / "reader-settings.json",
        )
        cls._reader_settings_patch.start()
        cls._translation_registry_patch = patch(
            "bhf_agent.translation_registry.registry_path",
            return_value=Path(cls._tmpdir.name) / "translations.sqlite",
        )
        cls._translation_registry_patch.start()
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
        if getattr(cls, "_commentary_db_patch", None) is not None:
            cls._commentary_db_patch.stop()
        if getattr(cls, "_translation_registry_patch", None) is not None:
            cls._translation_registry_patch.stop()
        if getattr(cls, "_reader_settings_patch", None) is not None:
            cls._reader_settings_patch.stop()
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

    def open_home(self, *, wait_for_reader: bool = True, wait_for_companion: bool = True):
        self.driver.get(self._base_url + "/")
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="reader-passage"]'))
        )
        if wait_for_reader:
            WebDriverWait(self.driver, 20).until(
                lambda driver: driver.execute_script(
                    "const state = window.BHFStudySelection?.getState?.(); "
                    "return Boolean(state?.book && state?.chapter && "
                    "document.querySelector('#chapter-reader h3')?.textContent?.trim());"
                )
            )
            if wait_for_companion:
                self.wait_for_companion_context()

    def wait_for_companion_context(self):
        WebDriverWait(self.driver, 90).until(
            lambda driver: driver.execute_script("""
              const selection = window.BHFStudySelection?.getState?.() || {};
              if (!selection.book || !selection.chapter) return true;
              const record = window.BHFStudyCompanion?.getContextRecord?.();
              const key = window.BHFCompanionContext?.requestKey?.(selection);
              return Boolean(record && record.key === key &&
                (record.status === 'ready' || record.status === 'error'));
            """)
        )

    def open_mobile_workspace(
        self,
        section: str = "notes",
        *,
        wait_for_reader: bool = True,
        wait_for_companion: bool = True,
    ):
        self.open_home(wait_for_reader=wait_for_reader, wait_for_companion=wait_for_companion)
        if section == "bible":
            return
        self.driver.find_element(By.CSS_SELECTOR, f'[data-testid="app-dock-{section}"]').click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script("return document.body.dataset.appSection") == section
        )

    def test_retired_commentary_and_coverage_are_gone_and_reader_has_no_generated_ui(self):
        self.open_home(wait_for_companion=False)
        browser_state = self.driver.execute_async_script("""
            const done = arguments[0];
            const paths = [
              '/api/bhf-commentary/diagnostics',
              '/api/bhf-commentary/search?q=Abraham',
              '/api/bhf-commentary/Genesis/1',
              '/api/bhf-commentary/Genesis/1/evidence',
              '/api/internal/bhf-commentary/coverage?scope=Genesis',
              '/internal/commentary-coverage',
            ];
            Promise.all(paths.map(async (path) => {
              const response = await fetch(path);
              return {path, status: response.status, body: await response.json()};
            })).then((responses) => done({
              responses,
              hasGeneratedCard: Boolean(document.querySelector('[data-bhf-commentary-card]')),
              hasCoverageUi: Boolean(document.querySelector('[data-commentary-coverage]')),
              bodyHasGeneratedTitle: document.body.innerText.includes('BHF Context'),
              commentaryRelease: window.BHFRuntimeConfig?.commentaryRelease ?? null,
              scriptSources: Array.from(document.scripts).map((script) => script.src),
            }));
        """)

        self.assertEqual(len(browser_state["responses"]), 6)
        for response in browser_state["responses"]:
            self.assertEqual(response["status"], 410, response["path"])
            self.assertEqual(response["body"]["reason"], "feature_retired", response["path"])
        self.assertFalse(browser_state["hasGeneratedCard"])
        self.assertFalse(browser_state["hasCoverageUi"])
        self.assertFalse(browser_state["bodyHasGeneratedTitle"])
        self.assertIsNone(browser_state["commentaryRelease"])
        self.assertFalse(any("bhf-commentary-card.js" in src for src in browser_state["scriptSources"]))
        self.assertFalse(any("commentary-coverage.js" in src for src in browser_state["scriptSources"]))

    def test_cold_reader_initializes_without_eager_optional_offline_packs(self):
        self.open_home()
        WebDriverWait(self.driver, 15).until(
            lambda driver: driver.execute_script("""
              return performance.getEntriesByType('resource').some((entry) =>
                entry.name.includes('/api/offline/manifest')
              );
            """)
        )

        state = self.driver.execute_script("""
            const chapterRequest = performance.getEntriesByType('resource').find((entry) =>
              entry.name.includes('/api/bible/John/1?translation=kjv')
            );
            const selection = window.BHFStudySelection?.getState?.() || {};
            return {
              heading: document.querySelector('#chapter-reader h3')?.textContent?.trim() || '',
              selection: {
                book: selection.book || '',
                chapter: selection.chapter || null,
                translation: selection.translation || '',
              },
              chapterRequestCompleted: Boolean(chapterRequest && chapterRequest.responseEnd > 0),
              autoInstallOfflinePacks: window.BHFRuntimeConfig?.autoInstallOfflinePacks,
              optionalPackRequests: performance.getEntriesByType('resource')
                .filter((entry) => entry.name.includes('/api/offline/packs/'))
                .map((entry) => entry.name),
              explorerRequests: performance.getEntriesByType('resource')
                .filter((entry) => entry.name.includes('/api/narrative-explorer/'))
                .map((entry) => entry.name),
            };
        """)

        self.assertEqual(state["heading"], "John 1")
        self.assertFalse(state["autoInstallOfflinePacks"])
        self.assertEqual(
            state["selection"],
            {"book": "John", "chapter": 1, "translation": "kjv"},
        )
        self.assertTrue(state["chapterRequestCompleted"])
        self.assertEqual(state["optionalPackRequests"], [])
        self.assertEqual(state["explorerRequests"], [])

    def test_reader_translation_range_and_chapter_return(self):
        self.driver.set_window_size(1280, 900)
        self.open_home()
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-book]")).select_by_value("Genesis")
        WebDriverWait(self.driver, 20).until(
            lambda driver: "Genesis 1" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
        )
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value("2")
        WebDriverWait(self.driver, 20).until(
            lambda driver: "Genesis 2" in driver.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text
        )

        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-translation]")).select_by_value("asv")
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script(
                "return window.BHFStudySelection?.getState?.().translation === 'asv' "
                "&& document.querySelector('#chapter-reader h3')?.textContent?.trim() === 'Genesis 2';"
            )
        )
        for verse in (8, 9, 10):
            verse_button = self.driver.find_element(
                By.CSS_SELECTOR, f'#chapter-reader [data-verse="{verse}"] [data-verse-select]'
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                verse_button,
            )
            verse_button.click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script(
                "const state = window.BHFStudySelection?.getState?.(); "
                "return state?.selectedVerses?.join(',') === '8,9,10' && state.translation === 'asv';"
            )
        )
        range_state = self.driver.execute_script("return window.BHFStudySelection.getState()")
        self.assertEqual(range_state["reference"], "Genesis 2:8-10")

        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value("3")
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script(
                "const state = window.BHFStudySelection?.getState?.(); "
                "return document.querySelector('#chapter-reader h3')?.textContent?.trim() === 'Genesis 3' "
                "&& state?.book === 'Genesis' && state.chapter === 3 && state.translation === 'asv';"
            )
        )
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value("2")
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script(
                "const state = window.BHFStudySelection?.getState?.(); "
                "return document.querySelector('#chapter-reader h3')?.textContent?.trim() === 'Genesis 2' "
                "&& state?.book === 'Genesis' && state.chapter === 2 && state.translation === 'asv' "
                "&& /ASV/i.test(document.querySelector('#chapter-reader')?.textContent || '');"
            )
        )

    def test_tyndale_notes_and_translation_comparison_preserve_reading_context(self):
        if self._commentary_db_path is None:
            raise unittest.SkipTest("The local Tyndale Study Notes database is not available.")

        self.open_home()
        notes = WebDriverWait(self.driver, 30).until(
            lambda driver: driver.find_element(By.CSS_SELECTOR, "[data-commentary-body]")
            if driver.find_elements(By.CSS_SELECTOR, "[data-commentary-body] .commentary-entry")
            else False
        )
        self.assertTrue(notes.find_elements(By.CSS_SELECTOR, ".commentary-entry"))
        self.driver.find_element(
            By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] [data-verse-select]'
        ).click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script(
                "const state = window.BHFStudySelection?.getState?.(); "
                "return state?.book === 'John' && state.chapter === 1 "
                "&& state.selectedVerses?.join(',') === '1';"
            )
        )
        self.driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "study"
        )
        self.driver.find_element(
            By.CSS_SELECTOR, '[data-companion-resource="translation_comparison"]'
        ).click()
        comparison = WebDriverWait(self.driver, 30).until(
            lambda driver: driver.find_element(By.CSS_SELECTOR, ".translation-comparison")
            if driver.find_elements(By.CSS_SELECTOR, ".translation-comparison [data-comparison-translation]")
            else False
        )
        self.assertGreaterEqual(
            len(comparison.find_elements(By.CSS_SELECTOR, "[data-comparison-translation]")),
            2,
        )
        original = self.driver.execute_script("return window.BHFStudySelection.getState()")

        self.driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="closed"]').click()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "closed"
        )
        restored = self.driver.execute_script("return window.BHFStudySelection.getState()")
        self.assertEqual(restored, original)
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, '#chapter-reader h3').text.strip(),
            "John 1",
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] [data-verse-select]')
            .get_attribute("aria-pressed"),
            "true",
        )
        self.assertTrue(
            self.driver.find_elements(By.CSS_SELECTOR, "[data-commentary-body] .commentary-entry")
        )

    def test_reader_translation_request_completes_during_study_pack_generation(self):
        self.open_home()
        self.driver.execute_script("""
            window.__studyPackState = {started: true, completed: false, status: null, packId: null};
            window.__studyPackPromise = fetch('/api/offline/packs/study', {
              headers: {Accept: 'application/json', 'X-BHF-Refresh': 'true'}
            }).then(async (response) => {
              const body = await response.json();
              window.__studyPackState = {
                started: true,
                completed: true,
                status: response.status,
                packId: body.pack_id || null,
              };
              return body;
            }, (error) => {
              window.__studyPackState = {
                started: true,
                completed: true,
                status: 0,
                error: String(error),
              };
            });
            window.__bibleDuringPackState = {completed: false, status: null, verseCount: 0};
            window.__bibleDuringPackPromise = fetch('/api/bible/John/1?translation=asv', {
              headers: {Accept: 'application/json'}
            }).then(async (response) => {
              const body = await response.json();
              window.__bibleDuringPackState = {
                completed: true,
                status: response.status,
                verseCount: Array.isArray(body.verses) ? body.verses.length : 0,
              };
              return body;
            }, (error) => {
              window.__bibleDuringPackState = {
                completed: true,
                status: 0,
                verseCount: 0,
                error: String(error),
              };
            });
        """)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                "return window.__bibleDuringPackState?.completed === true"
            )
        )
        state = self.driver.execute_script("""
            return {
              pack: window.__studyPackState,
              bible: window.__bibleDuringPackState,
            };
        """)
        self.assertTrue(state["pack"]["started"])
        self.assertFalse(state["pack"]["completed"])
        self.assertEqual(state["bible"]["status"], 200)
        self.assertEqual(state["bible"]["verseCount"], 51)

        Select(self.driver.find_element(By.CSS_SELECTOR, '[data-reader-translation]')).select_by_value("asv")
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script("""
              const state = window.BHFStudySelection?.getState?.() || {};
              const heading = document.querySelector('#chapter-reader h3')?.textContent?.trim() || '';
              const reader = document.querySelector('#chapter-reader')?.textContent || '';
              return state.translation === 'asv' && heading === 'John 1' && /ASV/i.test(reader);
            """)
        )

        WebDriverWait(self.driver, 90).until(
            lambda driver: driver.execute_script("return window.__studyPackState?.completed === true")
        )
        pack_state = self.driver.execute_script("return window.__studyPackState")
        self.assertEqual(pack_state["status"], 200)
        self.assertEqual(pack_state["packId"], "study")

    def test_mobile_workspace_drawer_opens_at_the_top(self):
        self.open_mobile_workspace("notes")
        panel = self.driver.find_element(By.ID, "study-panel")
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.find_element(By.ID, "study-panel").rect["y"] <= 4
        )
        rect = panel.rect

        self.assertLessEqual(rect["y"], 4)
        self.assertGreater(rect["width"], 300)
        self.assertTrue(panel.is_displayed())

    def test_map_browse_search_is_available_without_selection(self):
        # Maps is opened from the Explore resource list. The workspace tab
        # bar is hidden in that app section.
        self.open_mobile_workspace("explore", wait_for_companion=False)
        maps_entry = WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[data-companion-resource="maps"]'))
        )
        maps_entry.click()
        WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located((By.ID, "map-panel"))
        )
        self.driver.find_element(By.CSS_SELECTOR, "[data-map-navigator-open]").click()
        WebDriverWait(self.driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-map-search-query]"))
        )

        search_input = self.driver.find_element(By.CSS_SELECTOR, "[data-map-search-query]")
        search_input.clear()
        search_input.send_keys("Jerusalem", Keys.ENTER)

        WebDriverWait(self.driver, 20).until(
            lambda driver: len(
                driver.find_elements(By.CSS_SELECTOR, "#map-search-results-list .map-search-result")
            ) > 0
        )

        results = self.driver.find_elements(By.CSS_SELECTOR, "#map-search-results-list .map-search-result")
        self.assertGreater(len(results), 0)
        map_requests = self.driver.execute_script("""
            return performance.getEntriesByType('resource')
              .filter((entry) => entry.name.includes('/api/maps/catalog') || entry.name.includes('/api/maps/search'))
              .map((entry) => ({name: entry.name, completed: entry.responseEnd > 0}));
        """)
        self.assertTrue(any("/api/maps/catalog?include_records=false" in request["name"] for request in map_requests))
        self.assertTrue(any("/api/maps/search?" in request["name"] and request["completed"] for request in map_requests))
        self.assertTrue(all(request["completed"] for request in map_requests))

    def test_reader_search_selection_navigation_and_next_chapter_are_mobile_usable(self):
        self.open_home()
        WebDriverWait(self.driver, 20).until(
            lambda driver: driver.execute_script("return document.body.dataset.appSection") == "bible"
        )
        query_input = self.driver.find_element(By.CSS_SELECTOR, "[data-bible-search] input[name='query']")
        query_input.clear()
        # The browser smoke environment may serve the generated offline text
        # search fallback, which searches verse text rather than parsing a
        # reference string. Search the target verse's wording so the same
        # reader-navigation assertion applies online and offline.
        query_input.send_keys("In the beginning was the Word")
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
        # Warm the expensive source projection directly. The browser journeys below
        # exercise the real HTTP route once Uvicorn is serving the app.
        cls._app.state.narrative_explorer_service.build("John", 1)
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
        from selenium.webdriver.firefox.service import Service

        options = FirefoxOptions()
        options.add_argument("-headless")
        try:
            driver_path = shutil.which("geckodriver")
            service = Service(executable_path=driver_path) if driver_path else None
            self.driver = webdriver.Firefox(service=service, options=options)
        except Exception as exc:  # pragma: no cover - depends on local browser setup
            raise unittest.SkipTest(f"Firefox WebDriver could not start: {exc}") from exc
        self.driver.set_page_load_timeout(90)
        self.driver.set_script_timeout(90)

    def tearDown(self):
        self.driver.quit()

    def test_ne8a_ask_bhf_and_compare_translations_remain_reachable(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(self.driver, 60)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        wait.until(lambda driver: driver.execute_script(
            "const state=window.BHFStudySelection?.getState?.(); "
            "return state?.book === 'John' && state.chapter === 1 "
            "&& document.querySelector('#chapter-reader [data-verse=\"1\"] [data-verse-select]');"
        ))
        self.driver.find_element(
            By.CSS_SELECTOR,
            '#chapter-reader [data-verse="1"] [data-verse-select]',
        ).click()
        wait.until(lambda driver: driver.execute_script(
            "return window.BHFStudySelection?.getState?.().reference === 'John 1:1';"
        ))

        ask = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-ask-bhf]")))
        ask.click()
        dialog = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-ask-bhf-dialog]")))
        self.assertIn("John 1:1", dialog.find_element(By.CSS_SELECTOR, "[data-ask-bhf-reference]").text)
        dialog.find_element(By.CSS_SELECTOR, "[data-ask-bhf-close]").click()
        wait.until(lambda _driver: not dialog.get_attribute("open"))

        self.driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
        wait.until(lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "study")
        self.driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="translation_comparison"]').click()
        comparison = wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, ".translation-comparison")
            if driver.find_elements(By.CSS_SELECTOR, ".translation-comparison [data-comparison-translation]")
            else False)
        self.assertGreaterEqual(len(comparison.find_elements(By.CSS_SELECTOR, "[data-comparison-translation]")), 2)
        self.assertEqual(
            self.driver.execute_script("return window.BHFStudySelection.getState().reference"),
            "John 1:1",
        )

    def test_ne8a_psalm_alias_navigation_preserves_reader_history_and_origin(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select, WebDriverWait

        wait = WebDriverWait(self.driver, 90)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        wait.until(lambda driver: driver.execute_script(
            "return window.BHFStudySelection?.getState?.().book === 'John';"
        ))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-book]")).select_by_value("Psalms")
        wait.until(lambda driver: driver.execute_script(
            "return window.BHFStudySelection?.getState?.().book === 'Psalms';"
        ))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value("82")
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); return s?.book === 'Psalms' && s.chapter === 82;"
        ))
        self.driver.find_element(
            By.CSS_SELECTOR,
            '#chapter-reader [data-verse="1"] [data-verse-select]',
        ).click()
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "return s?.book === 'Psalms' && s.chapter === 82 && s.selectedVerses?.join(',') === '1';"
        ))

        self.driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
        wait.until(lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "study")
        self.driver.find_element(By.CSS_SELECTOR, "[data-companion-resource='translation_comparison']").click()
        comparison = wait.until(lambda driver: driver.find_element(By.CSS_SELECTOR, ".translation-comparison")
            if driver.find_elements(By.CSS_SELECTOR, ".translation-comparison [data-comparison-translation]")
            else False)
        self.assertGreaterEqual(len(comparison.find_elements(By.CSS_SELECTOR, "[data-comparison-translation]")), 2)
        self.assertEqual(
            self.driver.execute_script("return window.BHFStudySelection.getState().book"),
            "Psalms",
        )
        self.assertEqual(
            self.driver.execute_script("return window.BHFStudySelection.getState().selectedVerses.join(',')"),
            "1",
        )
        self.driver.back()
        wait.until(lambda driver: driver.execute_script(
            "return window.BHFStudySelection?.getState?.().selectedVerses?.join(',') === '1';"
        ))
        wait.until(lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") in {"closed", "peek", "study"})
        if self.driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") != "study":
            self.driver.find_element(By.CSS_SELECTOR, '[data-passage-action="explore"]').click()
            wait.until(lambda driver: driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "study")

        self.driver.find_element(By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']").click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        section = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "[data-section-id='divine_council_cosmic_geography']",
        )))
        section.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()
        item_id = "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language"
        item_action = wait.until(lambda driver: next((element for element in driver.find_elements(
            By.CSS_SELECTOR,
            f'[data-narrative-item-id="{item_id}"]',
        ) if element.is_displayed()), False))
        item_action.click()
        detail = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Evidence detail"]')))
        anchor_group = detail.find_element(By.CSS_SELECTOR, ".narrative-explorer-scripture-anchors")
        self.assertTrue(any(
            text.startswith("Psalm 82:1-8") for text in [
                element.text for element in anchor_group.find_elements(By.TAG_NAME, "p")
            ]
        ), "the original CKL reference should retain its singular display spelling")
        self.assertNotIn("Passage navigation unavailable", detail.text)
        link = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//section[contains(@class,'narrative-explorer-scripture-anchors')]//button[normalize-space()='Open Psalms 82:1-8']",
        )))
        history_length = self.driver.execute_script("return window.history.length")
        link.click()
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "return s?.book === 'Psalms' && s.chapter === 82 && s.selectedVerses?.join(',') === '1,2,3,4,5,6,7,8';"
        ))
        self.assertGreater(self.driver.execute_script("return window.history.length"), history_length)
        wait.until(lambda driver: driver.execute_script(
            "const t=window.history.state?.bhfStudyCompanion?.trail; "
            "const n=t?.nodes?.[t.activeIndex]; "
            "return t?.originSelection?.book === 'Psalms' "
            "&& n?.reference === 'Psalms 82:1-8' "
            "&& n?.relationship?.anchor === 'Psalm 82:1-8';"
        ))
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        self.assertIn("Psalms 82", self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)

        self.driver.back()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Evidence detail"]')))
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "const t=window.history.state?.bhfStudyCompanion?.trail; "
            "return s?.book === 'Psalms' && s.chapter === 82 "
            "&& t?.nodes?.[t.activeIndex]?.kind === 'evidence';"
        ))
        self.driver.forward()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "const t=window.history.state?.bhfStudyCompanion?.trail; "
            "return s?.book === 'Psalms' && s.chapter === 82 "
            "&& s.selectedVerses?.join(',') === '1,2,3,4,5,6,7,8' "
            "&& t?.nodes?.[t.activeIndex]?.reference === 'Psalms 82:1-8';"
        ))

        self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-origin").click()
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "return s?.book === 'Psalms' && s.chapter === 82 && s.selectedVerses?.join(',') === '1';"
        ))
        origin_heading = wait.until(lambda driver: next((element for element in driver.find_elements(
            By.CSS_SELECTOR,
            ".narrative-explorer-passage",
        ) if "Psalms 82" in element.text), False))
        self.assertIn("Psalms 82", origin_heading.text)

    def test_ne8a_passage_journeys_show_reader_labels_sources_uncertainty_and_return_path(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select, WebDriverWait

        wait = WebDriverWait(self.driver, 90)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        wait.until(lambda driver: driver.execute_script(
            "return window.BHFStudySelection?.getState?.().book === 'John';"
        ))

        def select_passage(book, chapter, verses=()):
            Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-book]")).select_by_value(book)
            wait.until(lambda driver: driver.execute_script(
                "return window.BHFStudySelection?.getState?.().book === arguments[0];", book,
            ))
            Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value(str(chapter))
            wait.until(lambda driver: driver.execute_script(
                "const state=window.BHFStudySelection?.getState?.(); return state?.book === arguments[0] && state?.chapter === arguments[1];",
                book,
                chapter,
            ))
            for verse in verses:
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    f'#chapter-reader [data-verse="{verse}"] [data-verse-select]',
                ).click()
            if verses:
                expected = ",".join(map(str, verses))
                wait.until(lambda driver: driver.execute_script(
                    "return window.BHFStudySelection?.getState?.().selectedVerses?.join(',') === arguments[0];",
                    expected,
                ))

        def start_new_journey():
            self.driver.get(self._base_url + "/")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
            wait.until(lambda driver: driver.execute_script(
                "const state=window.BHFStudySelection?.getState?.(); "
                "return Boolean(state?.book && state?.chapter && document.querySelector('#chapter-reader h3')?.textContent?.trim());"
            ))

        def open_explorer(reference):
            entry = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                entry,
            )
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']")))
            entry.click()
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
            discovery_heading = self.driver.find_element(
                By.CSS_SELECTOR,
                ".narrative-explorer-connection-discovery h4",
            ).text
            self.assertIn(f"Evidence about {reference}", discovery_heading)
            header_text = self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-header").text
            self.assertIn("Sources and counts show what was returned for this passage", header_text)
            self.assertIn("do not by themselves show borrowing", self.driver.find_element(
                By.CSS_SELECTOR,
                ".narrative-explorer-connection-discovery",
            ).text)
            self.assertNotIn("CKL parent records", header_text)

        def inspect_record(section_id, identity, expected_label, source_id, content_check, caution_check=None):
            section = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                f'[data-section-id="{section_id}"]',
            )))
            section.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()
            item_action = wait.until(lambda driver: next((element for element in driver.find_elements(
                By.CSS_SELECTOR,
                f'[data-narrative-item-id="{identity}"]',
            ) if element.is_displayed()), False))
            item = item_action.find_element(By.XPATH, "ancestor::article")
            self.assertTrue(
                item.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-kind").text.startswith(expected_label),
                f"expected reader-facing layer {expected_label!r}",
            )
            provenance = item.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
            provenance.find_element(By.TAG_NAME, "summary").click()
            self.assertIn("Passage relationship:", provenance.text)
            self.assertIn(source_id, provenance.text)
            item_action.click()
            detail = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Evidence detail"]')))
            rationale_details = detail.find_elements(By.CSS_SELECTOR, ".narrative-explorer-recorded-rationale summary")
            if rationale_details:
                rationale_details[0].click()
            self.assertIn(content_check, detail.text)
            if caution_check:
                cautions = " ".join(element.text for element in detail.find_elements(
                    By.CSS_SELECTOR,
                    ".narrative-explorer-caution",
                ))
                self.assertIn(caution_check, cautions)
            self.assertIn("Original Scripture anchors", detail.text)
            detail.find_element(By.CSS_SELECTOR, ".narrative-explorer-bibliography summary").click()
            self.assertIn(source_id, detail.text)
            detail.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-origin").click()
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))

        # Competing readings, the syntax limits around the Nephilim, and later reception.
        select_passage("Genesis", 6, (1, 2, 3, 4))
        open_explorer("Genesis 6:1-4")
        inspect_record(
            "divine_council_cosmic_geography",
            "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions",
            "Scholarly interpretation · disputed position",
            "g2-doedens-sons-god",
            "remain disputed",
        )
        inspect_record(
            "biblical_narrative",
            "ckl:genesis-flood-postflood-context#evidence:g6-nephilim-and-mighty-men",
            "Scholarly interpretation · literary reading",
            "g2-doedens-sons-god",
            "does not unambiguously state",
        )
        inspect_record(
            "archaeology_ancient_history",
            "ckl:genesis-flood-postflood-context#evidence:g6-second-temple-watchers-reception",
            "Later reception",
            "g2-1-enoch-6",
            "later interpretation rather than adding details",
            "does not establish that reception as the earlier passage's original meaning",
        )

        start_new_journey()

        # Psalm 82 separates the wording of the poem from its Ugaritic comparison.
        select_passage("Psalms", 82)
        open_explorer("Psalms 82")
        inspect_record(
            "divine_council_cosmic_geography",
            "ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language",
            "Original biblical text · worldview language",
            "psalm-82-hebrew-text",
            "identity of the judged figures",
        )
        inspect_record(
            "divine_council_cosmic_geography",
            "ckl:ancient-divine-assembly-imagery#evidence:ugaritic-council-comparison",
            "Ancient comparative literature",
            "smith-ugaritic-baal-cycle-1994",
            "relationship to Psalm 82 involve",
        )

        start_new_journey()

        # Deuteronomy 32 keeps the variant evidence distinct from its implications.
        select_passage("Deuteronomy", 32, (8, 9))
        open_explorer("Deuteronomy 32:8-9")
        inspect_record(
            "archaeology_ancient_history",
            "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
            "Manuscript/textual witness",
            "deuteronomy-32-text",
            "4QDeuteronomy-j",
        )

        start_new_journey()

        # Genesis 2 keeps sacred-space interpretation and physical place limits distinct.
        select_passage("Genesis", 2)
        open_explorer("Genesis 2")
        inspect_record(
            "biblical_geography",
            "ckl:genesis#evidence:g2-garden-planting-presence",
            "Geography and place identification",
            "g1-amit-eden-exposition",
            "sacred-space interpretation is a scholarly reading",
        )
        inspect_record(
            "biblical_geography",
            "ckl:genesis#evidence:g2-rivers-and-eden-geographic-limits",
            "Geography and place identification",
            "g1-amit-eden-exposition",
            "The passage gives no coordinates",
        )
        self.assertLessEqual(
            self.driver.execute_script("return document.documentElement.scrollWidth"),
            self.driver.execute_script("return window.innerWidth"),
        )

    def test_ne8b_connection_preview_desktop_mobile(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select, WebDriverWait

        wait = WebDriverWait(self.driver, 90)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        wait.until(lambda driver: driver.execute_script(
            "const state=window.BHFStudySelection?.getState?.(); "
            "const book=document.querySelector('[data-reader-book]'); "
            "const chapter=document.querySelector('[data-reader-chapter]'); "
            "return state?.book === 'John' && state.chapter === 1 "
            "&& book?.value === 'John' && chapter?.value === '1' "
            "&& document.querySelector('#chapter-reader h3')?.textContent?.trim() === 'John 1';"
        ))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-book]")).select_by_value("Genesis")
        wait.until(lambda driver: driver.execute_script(
            "const state=window.BHFStudySelection?.getState?.(); "
            "return state?.book === 'Genesis' "
            "&& document.querySelector('[data-reader-book]')?.value === 'Genesis';"
        ))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value("6")
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); return s?.book === 'Genesis' && s.chapter === 6;"
        ))
        entry = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']")))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", entry)
        entry.click()
        discovery = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-connection-discovery")))
        wait.until(lambda driver: len(driver.find_elements(
            By.CSS_SELECTOR,
            ".narrative-explorer-connection-discovery [data-narrative-connection-preview='true']",
        )) == 3)
        preview = self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-connection-discovery")
        preview_text = preview.text
        self.assertIn("Evidence about Genesis 6", preview_text)
        self.assertNotIn("Explore related passages and evidence", preview_text)
        self.assertIn("Sons of God: documented interpretive positions", preview_text)
        self.assertIn("Second Temple Watchers reception of Genesis 6", preview_text)
        self.assertIn("Gilgamesh Tablet XI flood comparison", preview_text)
        self.assertIn("Who the “sons of God” are and what the episode means remain disputed", preview_text)
        self.assertIn("Scholars compare the flood motifs; how the traditions are related remains debated", preview_text)
        self.assertIn("This record is later than Genesis, but its time label needs review", preview_text)
        self.assertNotIn("Major scholarly disagreement", preview_text)
        self.assertNotIn("CKL relationship", preview_text)
        self.assertNotIn("metadata", preview_text.lower())
        self.assertNotIn("*bene ha'elohim*", preview_text)
        self.assertIn("A Scripture reference shows where evidence applies", preview_text)
        self.assertIn("doesn't automatically mean two passages are connected", preview_text)
        self.assertIn("Connection context:", preview_text)
        self.assertNotIn("CKL", preview_text)
        self.assertLessEqual(
            self.driver.execute_script("return document.documentElement.scrollWidth"),
            self.driver.execute_script("return window.innerWidth"),
        )
        explore = self.driver.find_element(
            By.CSS_SELECTOR,
            ".narrative-explorer-connection-discovery .narrative-explorer-item-inspect",
        )
        self.assertEqual(explore.text, "Explore this evidence")
        self.assertTrue(explore.is_enabled())
        resource_host = self.driver.find_element(By.CSS_SELECTOR, ".companion-resource-host")
        self.driver.execute_script("arguments[0].scrollTop=0;", resource_host)
        self.driver.save_screenshot("/tmp/ne8b2-genesis6-overview-desktop.png")
        discovery.screenshot("/tmp/ne8b2-genesis6-evidence-desktop.png")

        explore.send_keys(Keys.ENTER)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Evidence detail"]')))
        self.assertTrue(self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-evidence-detail .narrative-explorer-item-action").is_displayed())
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-evidence-detail .narrative-explorer-item-action").text,
            "Open CKL record",
        )
        self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-origin").click()
        discovery = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-connection-discovery")))

        self.driver.set_window_size(390, 1040)
        wait.until(lambda driver: driver.execute_script("return window.matchMedia('(max-width: 760px)').matches"))
        discovery = self.driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-connection-discovery")
        resource_host = self.driver.find_element(By.CSS_SELECTOR, ".companion-resource-host")
        self.driver.execute_script("arguments[0].scrollTop=0;", resource_host)
        self.assertLessEqual(
            self.driver.execute_script("return document.documentElement.scrollWidth"),
            self.driver.execute_script("return window.innerWidth"),
        )
        self.assertGreaterEqual(self.driver.find_element(
            By.CSS_SELECTOR,
            ".narrative-explorer-connection-discovery .narrative-explorer-provenance summary",
        ).rect["height"], 40)
        self.driver.save_screenshot("/tmp/ne8b2-genesis6-overview-mobile.png")
        discovery.screenshot("/tmp/ne8b2-genesis6-evidence-mobile.png")
        scroll_state = self.driver.execute_script("""
          const host = arguments[0];
          const dock = document.querySelector('.app-dock');
          host.scrollTop = host.scrollHeight;
          const actions = host.querySelectorAll('.narrative-explorer-item-inspect');
          const lastAction = actions[actions.length - 1];
          const actionRect = lastAction?.getBoundingClientRect();
          const dockRect = dock?.getBoundingClientRect();
          return {
            scrollTop: host.scrollTop,
            scrollHeight: host.scrollHeight,
            clientHeight: host.clientHeight,
            actionBottom: actionRect?.bottom ?? 0,
            dockTop: dockRect?.top ?? window.innerHeight,
          };
        """, resource_host)
        self.assertGreater(scroll_state["scrollTop"], 0, "the mobile evidence view should scroll through all cards")
        self.assertLessEqual(scroll_state["actionBottom"], scroll_state["dockTop"], "the final card action should remain above the fixed dock")
        provenance = discovery.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance")
        summary = provenance.find_element(By.TAG_NAME, "summary")
        summary.send_keys(Keys.ENTER)
        self.assertTrue(provenance.get_attribute("open"))

    def test_feature_flagged_explorer_uses_desktop_dock_and_mobile_sheet(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(self.driver, 90)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        wait.until(lambda driver: driver.execute_script(
            "const selection = window.BHFStudySelection?.getState?.(); "
            "return selection?.book === 'John' && Number(selection?.chapter) === 1;"
        ))
        entry = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='companion-narrative-explorer']")))
        self.assertEqual(entry.find_element(By.CSS_SELECTOR, "strong").text, "Explore the Narrative")
        self.assertIn("Follow connections", entry.text)
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

    def test_companion_discovery_handoff_highlights_verified_route_and_returns_to_origin(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select, WebDriverWait

        wait = WebDriverWait(self.driver, 90)
        self.driver.set_window_size(1440, 1200)
        self.driver.get(self._base_url + "/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='reader-passage']")))
        wait.until(lambda driver: driver.execute_script("return window.BHFStudySelection?.getState?.().book === 'John';"))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-book]")).select_by_value("Genesis")
        wait.until(lambda driver: driver.execute_script("return window.BHFStudySelection?.getState?.().book === 'Genesis';"))
        Select(self.driver.find_element(By.CSS_SELECTOR, "[data-reader-chapter]")).select_by_value("1")
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); return s?.book === 'Genesis' && s.chapter === 1;",
        ))
        for verse in range(1, 6):
            self.driver.find_element(
                By.CSS_SELECTOR,
                f'#chapter-reader [data-verse="{verse}"] [data-verse-select]',
            ).click()
        wait.until(lambda driver: driver.execute_script(
            "return window.BHFStudySelection?.getState?.().selectedVerses?.join(',') === '1,2,3,4,5';",
        ))

        setup = self.driver.execute_async_script("""
          const done = arguments[0];
          (async () => {
            const selection = window.BHFStudySelection.getState();
            const projection = await window.BHFNarrativeExplorer.load(selection);
            const context = {
              reference: selection.reference,
              presentation_packet: {cards: [{
                id: 'browser-genesis-john-discovery',
                type: 'did_you_know',
                headline: 'John opens with the Word at the beginning',
                body: 'The prologue places the Logos with God in the beginning.',
                confidence: 'high',
                interpretation_level: 'interpretation',
                evidence_ids: ['browser-john-logos'],
                dig_deeper_actions: [{type: 'show_evidence', label: 'View evidence'}],
              }]},
              presentation_evidence: [{
                id: 'browser-john-logos',
                claim: 'John’s prologue presents the Logos with God in the beginning.',
                category: 'theological claim',
                confidence: 'high',
                ckl_record_identity: {object_id: 'john', record_kind: 'claim', record_id: 'john-logos'},
                sources: [{title: 'Canonical Knowledge Library'}],
              }],
            };
            const renderDiscoveries = window.BHFCompanionDiscoveries.render.bind(window.BHFCompanionDiscoveries);
            window.BHFCompanionDiscoveries.render = (panel, _value, options) => renderDiscoveries(
              panel,
              context,
              {...options, visible: true, narrativeExplorerEnabled: true, verifiedProjection: projection},
            );
            window.BHFCompanionDiscoveries.render(
              document.querySelector('[data-study-companion]'),
              context,
              {visible: true, narrativeExplorerEnabled: true, verifiedProjection: projection},
            );
            window.BHFCompanionDiscoveries.render = () => {};
            window.BHFStudyCompanion.setState('study', {focus: false, history: false});
            done({
              reference: selection.reference,
              routeIds: (projection.related_passages?.evidence_backed_bridges || []).map(route => route.id),
              matchIds: window.BHFCompanionDiscoveries.findVerifiedConnections(
                context.presentation_packet.cards[0], context, projection, {narrativeExplorerEnabled: true},
              ).map(route => route.id),
              actionCount: document.querySelectorAll("[data-presentation-action='explore_connection']").length,
              cardText: document.querySelector('.companion-discovery-card')?.textContent || '',
              resourceState: window.BHFStudyCompanion.getState(),
              overviewHidden: document.querySelector('[data-companion-overview]')?.hidden ?? null,
              discoverySectionHidden: document.querySelector('[data-companion-discoveries-section]')?.hidden ?? null,
              panelHidden: document.querySelector('[data-study-companion]')?.hidden ?? null,
            });
          })().catch(error => done({error: String(error)}));
        """)
        self.assertNotIn("error", setup)
        self.assertIn("genesis-1-john-1-creation-word", setup["routeIds"])
        self.assertEqual(setup["matchIds"], ["genesis-1-john-1-creation-word"])
        self.assertEqual(setup["actionCount"], 1)
        self.assertEqual(setup["reference"], "Genesis 1:1-5")
        self.assertIn("John opens with the Word at the beginning", setup["cardText"])
        self.assertFalse(setup["overviewHidden"], repr(setup))
        self.assertFalse(setup["discoverySectionHidden"], repr(setup))
        self.assertFalse(setup["panelHidden"], repr(setup))

        discovery = self.driver.find_element(By.CSS_SELECTOR, ".companion-discovery-card")
        self.driver.execute_script("arguments[0].querySelector('details').open = true;", discovery)
        action = self.driver.find_element(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']")
        self.assertEqual(self.driver.execute_script("return arguments[0].textContent;", action), "Explore this connection")
        self.assertEqual(action.tag_name.lower(), "button")
        self.assertEqual(action.get_attribute("aria-label"), "Explore this connection")
        focus_result = self.driver.execute_script("""
          const button = document.querySelector("[data-presentation-action='explore_connection']");
          if (!button) return {found: false};
          const details = button.closest('details');
          if (details) details.open = true;
          button.scrollIntoView({block: 'center'});
          button.focus();
          return document.activeElement === button;
        """)
        self.assertTrue(focus_result)
        active_action = self.driver.find_element(By.CSS_SELECTOR, "[data-presentation-action='explore_connection']")
        self.assertEqual(self.driver.execute_script("return document.activeElement.dataset.presentationAction;"), "explore_connection")
        active_action.send_keys(Keys.ENTER)
        WebDriverWait(self.driver, 20).until(lambda driver: driver.execute_script(
            "return window.BHFStudyCompanion.getState().resource === 'narrative_explorer';",
        ))

        route_article = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "[data-route-id='genesis-1-john-1-creation-word'][aria-current='true']",
        )))
        active_route = self.driver.execute_script(
            "return document.activeElement?.dataset?.narrativeRouteFocusId || '';",
        )
        self.assertEqual(active_route, "genesis-1-john-1-creation-word")
        route_text = self.driver.execute_script("return arguments[0].textContent.toLowerCase();", route_article)
        self.assertIsNotNone(route_article.find_element(By.CSS_SELECTOR, "[role='status']"))
        self.assertIn("interpretive association", route_text)
        self.assertIn("not proof of direct borrowing", route_text)
        inspection = route_article.find_element(By.CSS_SELECTOR, ".narrative-explorer-related-passage-details")
        self.driver.execute_script("arguments[0].open = true;", inspection)
        self.assertIn("john#claim:john-logos", self.driver.execute_script("return arguments[0].textContent;", inspection))

        follow_button = route_article.find_element(
            By.CSS_SELECTOR,
            "button[data-narrative-focus-id^='related-passage:']",
        )
        self.driver.execute_script("arguments[0].click();", follow_button)
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "const t=window.history.state?.bhfStudyCompanion?.trail; "
            "const active=t?.nodes?.[t.activeIndex]; "
            "return s?.book === 'John' && s?.selectedVerses?.join(',') === '1,2,3,4,5' "
            "&& active?.kind === 'passage' && active.reference === 'John 1:1-5' "
            "&& Number(t.activeIndex) > 0;",
        ))
        return_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-return-origin")))
        self.driver.execute_script("arguments[0].click();", return_button)
        wait.until(lambda driver: driver.execute_script(
            "const s=window.BHFStudySelection?.getState?.(); "
            "return s?.book === 'Genesis' && s?.selectedVerses?.join(',') === '1,2,3,4,5';",
        ))


if __name__ == "__main__":
    unittest.main()
