from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import threading
import time
import unittest
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import patch

try:
    from uvicorn import Config, Server
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait
except ImportError:  # pragma: no cover - local browser/dependency availability
    Config = Server = webdriver = By = Keys = FirefoxOptions = FirefoxService = None
    EC = Select = StaleElementReferenceException = WebDriverWait = None


ROOT = Path(__file__).resolve().parents[1]
STUDY_DB = Path.home() / "Documents" / "github" / "biblical-hermeneutics-framework" / ".bhf-data" / "study.sqlite"
GECKODRIVER = Path.home() / ".cache/selenium/geckodriver/linux64/0.37.1/geckodriver"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_url(url: str, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2):
                return
        except Exception as exc:  # pragma: no cover - local server timing
            last_error = exc
            time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for {url}") from last_error


def _read_json(url: str) -> dict:
    with urlopen(url, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


@unittest.skipUnless(
    webdriver is not None and shutil.which("firefox") and GECKODRIVER.is_file(),
    "Firefox, geckodriver, selenium, uvicorn, and the web dependencies are required.",
)
class NE6FirefoxIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not STUDY_DB.is_file():
            raise unittest.SkipTest(f"Configured valid study database is missing: {STUDY_DB}")
        cls._environment_patch = patch.dict(os.environ, {
            "BHF_STUDY_DB_PATH": str(STUDY_DB),
            "BHF_STUDY_DB_READ_ONLY": "1",
            "BHF_NARRATIVE_EXPLORER_ENABLED": "1",
            "BHF_CKL_ROOT": str(ROOT / "framework" / "canonical_library"),
        })
        cls._environment_patch.start()
        from bhf_agent.study_db import require_current_study_database
        from bhf_web import app as web_app_module

        cls._web_app_module = web_app_module
        cls._database_path = require_current_study_database(STUDY_DB)
        with sqlite3.connect(cls._database_path.as_uri() + "?mode=ro", uri=True) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise AssertionError("The configured study database did not pass integrity_check.")
        cls._database_sha256 = hashlib.sha256(cls._database_path.read_bytes()).hexdigest()
        cls._app = web_app_module.create_app()
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
        _wait_for_url(cls._base_url + "/api/health")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "_server_runner", None) is not None:
            cls._server_runner.should_exit = True
        if getattr(cls, "_thread", None) is not None:
            cls._thread.join(timeout=15)
        if getattr(cls, "_database_path", None) is not None:
            digest = hashlib.sha256(cls._database_path.read_bytes()).hexdigest()
            if digest != cls._database_sha256:
                raise AssertionError("The protected study database changed during NE-6 read-only verification.")
            with sqlite3.connect(cls._database_path.as_uri() + "?mode=ro", uri=True) as connection:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise AssertionError("Study database integrity changed during verification.")
        if getattr(cls, "_environment_patch", None) is not None:
            cls._environment_patch.stop()

    def setUp(self):
        options = FirefoxOptions()
        options.add_argument("-headless")
        self.driver = webdriver.Firefox(
            service=FirefoxService(executable_path=str(GECKODRIVER)),
            options=options,
        )
        self.driver.set_page_load_timeout(90)
        self.driver.set_script_timeout(90)
        self.wait = WebDriverWait(self.driver, 90)

    def tearDown(self):
        self.driver.quit()

    def open_home(self, width: int, height: int, query: str = ""):
        self.driver.set_window_size(width, height)
        self.driver.get(self._base_url + "/" + (f"?{query}" if query else ""))
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="reader-passage"]')))
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#chapter-reader h3")))

    def select_value(self, selector: str, value: str) -> None:
        def attempt(browser):
            try:
                control = browser.find_element(By.CSS_SELECTOR, selector)
                if control.get_attribute("value") == value:
                    return True
                Select(control).select_by_value(value)
                return True
            except StaleElementReferenceException:
                return False

        self.wait.until(attempt)

    def test_live_database_acts7_and_joshua1_references_remain_uncertain_and_read_only(self):
        acts = _read_json(self._base_url + "/api/narrative-explorer/v1/passages/Acts/7")
        acts_nile = next(item for item in acts["items"] if item["id"] == "maps:openbible-a012705")
        self.assertIn("Acts 7:19", acts_nile["related_passages"])
        self.assertFalse(acts_nile["coordinates_displayable"])
        self.assertEqual(acts_nile["coordinate_display_reason"], "physical_identification_not_established")
        self.assertIsNotNone(acts_nile["stored_coordinates"])

        joshua = _read_json(self._base_url + "/api/narrative-explorer/v1/passages/Joshua/1")
        negeb = next(item for item in joshua["items"] if item["id"] == "maps:openbible-a1cb244")
        self.assertIn("Joshua 1:4", negeb["related_passages"])
        self.assertFalse(negeb["coordinates_displayable"])
        self.assertEqual(negeb["coordinate_display_reason"], "physical_identification_not_established")
        self.assertIsNotNone(negeb["stored_coordinates"])

    def test_firefox_desktop_mobile_trail_maps_fallback_and_offline_retry(self):
        driver = self.driver
        self.open_home(1440, 1100)
        self.assertTrue(driver.execute_script("return window.BHFRuntimeConfig.narrativeExplorerEnabled"))
        self.assertFalse(driver.execute_script("return Boolean(window.BHFTestMode)"), "Map acknowledgments must use the real Leaflet browser controller")
        self.assertTrue(driver.execute_script("return Boolean(window.L)"), "Leaflet must load in the actual Firefox run")
        self.assertTrue(driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').is_displayed())
        driver.execute_script("""
            window.__ne6Metrics = [];
            document.addEventListener('bhf:narrative-explorer-metrics', event => window.__ne6Metrics.push(event.detail));
        """)
        initial_requests = driver.execute_script("""
            return performance.getEntriesByType('resource').map(entry => entry.name)
              .filter(name => name.includes('/api/narrative-explorer/v1/passages/') || name.includes('/api/maps/'));
        """)
        self.assertEqual(initial_requests, [], "inactive Narrative Explorer and Maps must not issue eager API requests")

        Select(driver.find_element(By.ID, "book-select")).select_by_visible_text("Genesis")
        self.wait.until(lambda browser: browser.execute_script(
            "return document.querySelector('#book-select').value === 'Genesis' "
            "&& document.querySelector('#chapter-select option:last-child')?.value === '50'"
        ))
        self.select_value("#chapter-select", "2")
        self.wait.until(lambda browser: "Genesis 2" in browser.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
        verse_eight = driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]')
        verse_eight.click()
        self.wait.until(lambda browser: browser.find_element(
            By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]'
        ).get_attribute("aria-pressed") == "true")
        origin = driver.execute_script("return window.BHFStudySelection.getState()")
        self.assertEqual(origin["selectedVerses"], [8])
        original_translation = origin["translation"]

        driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        self.assertIn("Genesis 2:8", driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        self.assertEqual(
            driver.execute_script("return performance.getEntriesByType('resource').filter(e => e.name.includes('/api/maps/')).length"),
            0,
        )

        cosmic = driver.find_element(By.CSS_SELECTOR, '[data-section-id="divine_council_cosmic_geography"]')
        self.assertIn("Sacred-space interpretation", cosmic.text)
        self.assertIn("not a literal map of heavenly realms", cosmic.text)
        garden_id = "ckl:genesis#evidence:g2-garden-planting-presence"
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'[data-narrative-item-id="{garden_id}"]'))).click()
        evidence = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Evidence detail"]')))
        self.assertIn("Garden planting and divine presence", evidence.text)
        evidence.find_element(By.CSS_SELECTOR, ".narrative-explorer-bibliography summary").click()
        self.wait.until(lambda browser: "Yairah Amit" in browser.find_element(By.CSS_SELECTOR, '[aria-label="Evidence detail"]').text)
        evidence = driver.find_element(By.CSS_SELECTOR, '[aria-label="Evidence detail"]')
        self.assertIn("Original Scripture anchors", evidence.text)
        self.assertIn("one-way", evidence.text)
        self.assertTrue(driver.find_element(By.CSS_SELECTOR, 'nav[aria-label="Evidence trail"]').is_displayed())
        self.assertTrue(driver.find_element(By.CSS_SELECTOR, '[aria-label="Evidence trail navigation"]').is_displayed())

        driver.back()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        self.assertEqual(driver.find_elements(By.CSS_SELECTOR, '[aria-label="Evidence detail"]'), [])
        driver.forward()
        evidence = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Evidence detail"]')))
        connection_button = evidence.find_element(By.XPATH, ".//button[contains(normalize-space(), 'Open connected CKL subject: creation')]" )
        connection_button.click()
        subject = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="Connected CKL subject"]')))
        self.assertIn("Relationship hops: 1 of 3", subject.text)
        self.assertIn("Scripture anchors", subject.text)
        creation_anchor = subject.find_element(By.XPATH, ".//button[contains(normalize-space(), 'Open linked passage: Genesis 1:1-31')]" )
        creation_anchor.click()
        self.wait.until(lambda browser: "Genesis 1:1-31" in browser.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        self.assertIn("2 of 3", driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-trail-depth").text)
        driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-return-origin").click()
        self.wait.until(lambda browser: "Genesis 2:8" in browser.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        self.wait.until(lambda browser: browser.switch_to.active_element.get_attribute("data-narrative-focus-id") == f"item:{garden_id}")
        restored = driver.execute_script("return window.BHFStudySelection.getState()")
        self.assertEqual(restored["book"], "Genesis")
        self.assertEqual(restored["chapter"], 2)
        self.assertEqual(restored["selectedVerses"], [8])
        self.assertEqual(restored["translation"], original_translation)
        self.assertEqual(
            driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]').get_attribute("aria-pressed"),
            "true",
        )

        driver.back()
        self.wait.until(lambda browser: "Genesis 1:1-31" in browser.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        driver.forward()
        self.wait.until(lambda browser: "Genesis 2:8" in browser.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        self.assertLessEqual(
            driver.execute_script("return document.documentElement.scrollWidth"),
            driver.execute_script("return window.innerWidth"),
        )
        driver.save_screenshot("/tmp/ne6-firefox-desktop.png")

        # An unidentified Eden record stays inspectable but offers only the
        # general browser. No stored coordinate reaches the reader surface.
        geo = driver.find_element(By.CSS_SELECTOR, '[data-section-id="biblical_geography"]')
        geo.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()
        eden = self.wait.until(lambda browser: browser.find_element(
            By.CSS_SELECTOR,
            '[data-section-id="biblical_geography"] [data-narrative-item-id="maps:openbible-af3daeb"]',
        ).find_element(By.XPATH, "ancestor::article"))
        eden.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance summary").click()
        eden_selector = '[data-section-id="biblical_geography"] [data-narrative-item-id="maps:openbible-af3daeb"]'
        self.wait.until(lambda browser: "Original map/record ID: openbible-af3daeb" in browser.find_element(
            By.CSS_SELECTOR, eden_selector
        ).find_element(By.XPATH, "ancestor::article").text)
        eden = driver.find_element(By.CSS_SELECTOR, eden_selector).find_element(By.XPATH, "ancestor::article")
        self.assertIn("Place identification confidence: unknown", eden.text)
        self.assertIn("Map point withheld: physical_identification_not_established", eden.text)
        self.assertIn("Recorded map provenance: Source: OpenBible.info Bible Geocoding Data", eden.text)
        self.assertIn("https://www.openbible.info/geo/atlas/eden-1", eden.text)
        self.assertNotIn("32.543333", eden.text)
        self.assertNotIn("44.422222", eden.text)
        eden_action = eden.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-action")
        self.assertEqual(eden_action.text, "Open general Maps Explorer")
        eden_action.click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        self.assertEqual(driver.find_elements(By.CSS_SELECTOR, ".narrative-explorer-item-action"), [])

        not_found = driver.execute_async_script("""
            const done = arguments[0];
            window.BHFMaps.openMapPanel({book:'Genesis', chapter:2,
              focusPlaceId:'ne6-no-such-place', acknowledgeFocus:true,
              focusKind:'place', focusTargetId:'ne6-no-such-place'}).then(done);
        """)
        self.assertEqual(not_found["status"], "not_found")
        status = self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel-status")))
        self.assertIn("was not found in the map results", status.text)
        self.assertIn("It has not been selected", status.text)
        self.assertTrue(status.find_element(By.CSS_SELECTOR, ".map-focus-status-action").is_displayed())

        unsupported = driver.execute_async_script("""
            const done = arguments[0];
            window.BHFMaps.openMapPanel({book:'Genesis', chapter:2,
              acknowledgeFocus:true, focusKind:'historical_layer', focusTargetId:'ne6-layer'}).then(done);
        """)
        self.assertEqual(unsupported["status"], "unsupported")
        self.assertIn("unsupported by the current map layer", driver.find_element(By.ID, "map-panel-status").text)

        failed = driver.execute_async_script("""
            const done = arguments[0];
            window.__ne6Fetch = window.fetch.bind(window);
            window.fetch = (input, init) => {
              const url = String(typeof input === 'string' ? input : input.url);
              if (url.includes('/api/maps/')) return Promise.reject(new TypeError('simulated map request failure'));
              return window.__ne6Fetch(input, init);
            };
            window.BHFMaps.openMapPanel({book:'John', chapter:1,
              focusPlaceId:'ne6-failure-target', acknowledgeFocus:true,
              focusKind:'place', focusTargetId:'ne6-failure-target'}).then(done);
        """)
        self.assertEqual(failed["status"], "failed")
        self.assertIn("could not confirm selection", driver.find_element(By.ID, "map-panel-status").text)

        unavailable = driver.execute_async_script("""
            const done = arguments[0];
            Object.defineProperty(navigator, 'onLine', {configurable:true, value:false});
            window.BHFMaps.openMapPanel({book:'John', chapter:2,
              focusPlaceId:'ne6-offline-target', acknowledgeFocus:true,
              focusKind:'place', focusTargetId:'ne6-offline-target'}).then(done);
        """)
        self.assertEqual(unavailable["status"], "unavailable")
        offline_status = driver.find_element(By.ID, "map-panel-status")
        self.assertIn("while offline", offline_status.text)
        retry = offline_status.find_element(By.XPATH, ".//button[normalize-space()='Retry map lookup']")
        self.assertTrue(retry.is_displayed())
        driver.execute_script("""
            Object.defineProperty(navigator, 'onLine', {configurable:true, value:true});
            window.__ne6RetryFetchLog = [];
            if (window.__ne6Fetch) window.fetch = (input, init) => {
              const url = String(typeof input === 'string' ? input : input.url);
              return window.__ne6Fetch(input, init).then(response => {
                window.__ne6RetryFetchLog.push({url, status: response.status});
                return response;
              }).catch(error => {
                window.__ne6RetryFetchLog.push({url, error: String(error)});
                throw error;
              });
            };
        """)
        retry.click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") in {"empty", "error"})
        retry_result = driver.find_element(By.ID, "map-panel-status")
        retry_log = driver.execute_script("return window.__ne6RetryFetchLog")
        self.assertTrue(retry_log, "online retry should issue fresh map-data requests")
        self.assertIn("It has not been selected", retry_result.text, msg=f"online retry state={retry_result.get_attribute('data-state')} requests={retry_log}")
        if retry_result.get_attribute("data-state") == "empty":
            self.assertIn("not found in the map results", retry_result.text)
        else:
            self.assertIn("could not confirm selection", retry_result.text)
        print("NE6_MAP_RETRY", json.dumps({
            "state": retry_result.get_attribute("data-state"),
            "message": retry_result.text,
            "requests": retry_log,
        }))
        driver.find_element(By.XPATH, "//*[@id='map-panel-status']//button[normalize-space()='Browse maps']").click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "map-search-results")))
        driver.find_element(By.CSS_SELECTOR, "[data-map-panel-close]").click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel").get_attribute("hidden") is not None)
        self.assertEqual(driver.switch_to.active_element.get_attribute("data-testid"), "map-browse-button")

        metrics = driver.execute_script("return window.__ne6Metrics")
        responses = [entry for entry in metrics if entry.get("phase") == "response"]
        response = responses[0]
        render = next(entry for entry in metrics if entry.get("phase") == "render")
        self.assertIsInstance(render.get("initial_overview_render_ms"), (int, float))
        map_request_count = driver.execute_script(
            "return performance.getEntriesByType('resource').filter(e => e.name.includes('/api/maps/')).length"
        )
        print("NE6_BROWSER_METRICS", json.dumps({
            "explorer_response_samples": [{
                "passage": entry.get("passage"),
                "response_ms": entry.get("response_ms"),
                "payload_bytes": entry.get("payload_bytes"),
            } for entry in responses],
            "explorer_network_requests": response.get("network_requests"),
            "explorer_initial_overview_render_ms": render.get("initial_overview_render_ms"),
            "explorer_dom_node_growth": render.get("dom_node_growth"),
            "map_api_requests_during_explicit_map_interactions": map_request_count,
        }))


    def test_firefox_mobile_companion_explorer_and_maps_workspace(self):
        driver = self.driver
        self.open_home(390, 844, query="ne6-mobile=1")
        driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="1"] [data-verse-select]').click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "peek")
        driver.find_element(By.CSS_SELECTOR, ".companion-peek").click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "study")
        driver.find_element(By.CSS_SELECTOR, '[data-companion-state-control="full"]').click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "study-panel").get_attribute("data-companion-state") == "full")
        mobile_entry = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]')))
        mobile_entry.click()

        def explorer_outcome(browser):
            sections = browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-sections")
            failure = browser.find_elements(By.CSS_SELECTOR, ".narrative-explorer-state, .companion-detail-error")
            return ("ready", sections[0]) if sections and sections[0].is_displayed() else (("failure", failure[0]) if failure else False)

        outcome = WebDriverWait(driver, 120).until(explorer_outcome)
        if outcome[0] == "failure":
            snapshot = driver.execute_script("""
                return {
                  viewport: {innerWidth, innerHeight, scrollWidth: document.documentElement.scrollWidth},
                  selected: window.BHFStudySelection?.getState?.(),
                  panel: document.querySelector('#study-panel')?.dataset.companionState,
                  host: document.querySelector('[data-companion-resource-host]')?.innerText,
                  resources: performance.getEntriesByType('resource').map(e => ({name:e.name, duration:e.duration, size:e.transferSize}))
                    .filter(e => e.name.includes('/api/narrative-explorer/') || e.name.includes('/api/maps/')),
                };
            """)
            driver.save_screenshot("/tmp/ne6-firefox-mobile-failure.png")
            self.fail(f"Mobile Explorer rendered a failure state: {outcome[1].text}; browser={json.dumps(snapshot)}")

        self.assertEqual(driver.find_element(By.ID, "study-panel").get_attribute("data-companion-state"), "full")
        self.assertLessEqual(
            driver.execute_script("return document.documentElement.scrollWidth"),
            driver.execute_script("return window.innerWidth"),
        )
        driver.find_element(By.CSS_SELECTOR, '[data-testid="app-dock-explore"]').click()
        self.wait.until(lambda browser: browser.find_element(By.TAG_NAME, "body").get_attribute("data-app-section") == "explore")
        driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="maps"]').click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        navigator_trigger = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-map-navigator-open]")))
        navigator_trigger.click()
        navigator = driver.find_element(By.ID, "map-study-navigator")
        self.assertIn("is-mobile-open", navigator.get_attribute("class"))
        self.assertEqual(navigator_trigger.get_attribute("aria-expanded"), "true")
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-map-search-query]")))
        driver.find_element(By.CSS_SELECTOR, "[data-map-navigator-close]").click()
        details_open = driver.find_element(By.CSS_SELECTOR, "[data-map-details-open]")
        details_open.click()
        self.assertIn("is-mobile-open", driver.find_element(By.ID, "map-details-column").get_attribute("class"))
        self.assertEqual(details_open.get_attribute("aria-expanded"), "true")
        driver.find_element(By.CSS_SELECTOR, "[data-map-details-close]").click()
        self.assertLessEqual(
            driver.execute_script("return document.documentElement.scrollWidth"),
            driver.execute_script("return window.innerWidth"),
        )
        driver.save_screenshot("/tmp/ne6-firefox-mobile.png")
        driver.find_element(By.CSS_SELECTOR, "[data-map-panel-close]").click()
        self.assertEqual(driver.switch_to.active_element.get_attribute("data-testid"), "map-browse-button")
