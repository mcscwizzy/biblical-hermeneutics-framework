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
NE6V_PLACE_ID = "ne6v_synthetic_place_001"
NE6V_ROUTE_ID = "ne6v_synthetic_route_001"


def _install_ne6v_map_fixture(
    driver,
    *,
    focus_override_id: str | None = None,
    include_related_passages: bool = True,
    detail_failure_count: int = 0,
) -> None:
    """Inject labeled, test-only API responses without writing a data store."""
    driver.execute_script("""
        const placeRecordId = arguments[0];
        const routeRecordId = arguments[1];
        const focusOverrideId = arguments[2];
        const includeRelatedPassages = arguments[3];
        const detailFailureCount = Number(arguments[4] || 0);
        const placeItemId = `maps:${placeRecordId}`;
        const routeItemId = `maps:${routeRecordId}`;
        const place = {
          id: placeRecordId,
          name: 'NE-6V Synthetic Test Place',
          latitude: 12.345678,
          longitude: 45.678901,
          modern_location: 'Synthetic test coordinates only',
          ancient_region: 'Synthetic test fixture',
          description: 'Synthetic browser test data only; not a biblical place or BHF source.',
          confidence: 'Certain',
          periods: ['Test fixture'],
          aliases: [],
          notes: `Synthetic test record ID: ${placeRecordId}. Not authoritative geography.`,
          source_name: 'Synthetic test data only (NE-6V acceptance)',
          source_url: '',
          license: 'Test-only fixture',
          related_references: [{
            book: 'Genesis', chapter: 2, verse_start: 8, verse_end: 8,
            relationship_type: 'synthetic_test_anchor',
          }],
          related_passages: {
            place_id: placeRecordId,
            place_name: 'NE-6V Synthetic Test Place',
            count: 1,
            groups: [{
              group_type: 'directly_mentioned',
              label: 'Directly Mentioned',
              summary: 'Synthetic test relationship only.',
              count: 1,
              passages: [{
                book: 'Genesis', chapter: 2, verse_start: 8, verse_end: 8,
                reference: 'Genesis 2:8', relationship_type: 'synthetic_test_anchor',
                relationship_label: 'Synthetic test anchor', notes: 'Synthetic test data only.',
                source: {kind: 'place', id: placeRecordId, name: 'NE-6V Synthetic Test Place',
                  label: 'Synthetic test fixture', entity_type: 'test fixture', notes: '',
                  confidence: 'Certain', confidence_rank: 100, source_url: '', periods: ['Test fixture']},
              }],
              testament_groups: [],
            }],
          },
        };
        const syntheticRelatedPassages = place.related_passages;
        if (!includeRelatedPassages) delete place.related_passages;
        const route = {
          id: routeRecordId,
          name: 'NE-6V Synthetic Test Route',
          route_type: 'Synthetic test route',
          period: 'Test fixture',
          description: 'Synthetic browser test data only; not a biblical route or BHF source.',
          confidence: 'Certain',
          source_name: 'Synthetic test data only (NE-6V acceptance)',
          source_url: '',
          license: 'Test-only fixture',
          notes: `Synthetic test record ID: ${routeRecordId}. Not authoritative geography.`,
          scripture_links: [{
            book: 'Genesis', chapter: 2, verse_start: 8, verse_end: 8,
            relationship_type: 'synthetic_test_anchor',
          }],
          geojson: {
            type: 'FeatureCollection',
            features: [{
              type: 'Feature',
              geometry: {type: 'LineString', coordinates: [[45.678901, 12.345678], [45.789012, 12.456789]]},
              properties: {},
            }],
          },
        };
        const makeJsonResponse = (value) => new Response(JSON.stringify(value), {
          status: 200,
          headers: {'Content-Type': 'application/json'},
        });
        const fixtureMetadata = {
          test_fixture: true,
          source_name: 'Synthetic test data only (NE-6V acceptance)',
          physical_identification_status: 'established',
        };
        const makeProjectionItem = ({kind, itemId, recordId, title, coordinates, geometry, navigationKind}) => ({
          id: itemId,
          domain: 'maps',
          record_kind: navigationKind,
          object_id: recordId,
          parent_object_id: null,
          claim_id: null,
          evidence_id: null,
          object_type: kind === 'route' ? 'physical_route' : 'physical_place',
          title,
          claim_text: null,
          description: `Synthetic test data only; not authoritative geography. Record ID: ${recordId}.`,
          evidence_category: null,
          claim_type: null,
          assertion_type: null,
          source_ids: [],
          sources: [],
          passage_anchors: [{reference: 'Genesis 2:8', relationship: 'synthetic_test_anchor'}],
          applicable_passage_anchors: [{reference: 'Genesis 2:8', relationship: 'synthetic_test_anchor'}],
          related_passages: ['Genesis 2:8'],
          original_relationship_types: ['synthetic_test_anchor'],
          confidence: 'high',
          certainty: 'certain',
          dispute_status: 'not_disputed',
          interpretation_state: 'known',
          review_status: 'test_fixture_only',
          content_status: 'test_fixture_only',
          human_review_required: false,
          temporal_relation: null,
          temporal_relations: [],
          temporal_scope: null,
          rationale: {basis: 'Synthetic browser integration fixture; not a BHF source record.'},
          source_metadata: {...fixtureMetadata},
          physical_identification_status: 'established',
          geography_kind: kind === 'route' ? 'route' : 'physical_place',
          place_identification_confidence: 'high',
          stored_coordinates: coordinates || null,
          coordinates_displayable: kind === 'place',
          coordinate_display_reason: kind === 'place' ? null : 'route_geometry_not_point',
          stored_geometry: geometry || null,
          geometry_displayable: kind === 'route',
          geometry_display_reason: kind === 'route' ? null : 'not_applicable',
          section_ids: ['biblical_geography'],
          navigation: {
            id: `navigation:${itemId}`,
            kind: navigationKind,
            target_id: recordId,
            href: kind === 'route' ? '/api/maps/routes' : '/api/maps/biblical-places',
            selection_required: true,
          },
        });
        const placeItem = makeProjectionItem({
          kind: 'place', itemId: placeItemId, recordId: placeRecordId,
          title: place.name, coordinates: {latitude: place.latitude, longitude: place.longitude},
          navigationKind: 'map_place',
        });
        const routeItem = makeProjectionItem({
          kind: 'route', itemId: routeItemId, recordId: routeRecordId,
          title: route.name,
          geometry: {type: 'LineString', coordinates: [[45.678901, 12.345678], [45.789012, 12.456789]]},
          navigationKind: 'map_route',
        });
        window.__ne6vNativeFetch = window.fetch.bind(window);
        window.__ne6vFocusRequests = [];
        window.__ne6vDetailRequests = [];
        window.fetch = async (input, init) => {
          const rawUrl = String(typeof input === 'string' ? input : input.url);
          const url = new URL(rawUrl, window.location.href);
          if (url.pathname === '/api/maps/places-for-passage'
              && url.searchParams.get('book') === 'Genesis'
              && url.searchParams.get('chapter') === '2') {
            return makeJsonResponse({markers: [place], count: 1, empty_state: false});
          }
          if (url.pathname === '/api/maps/routes-for-passage'
              && url.searchParams.get('book') === 'Genesis'
              && url.searchParams.get('chapter') === '2') {
            return makeJsonResponse({routes: [route], count: 1, empty_state: false});
          }
          if (url.pathname === '/api/maps/related-passages-for-place'
              && url.searchParams.get('place_id') === placeRecordId) {
            window.__ne6vDetailRequests.push(url.search);
            if (window.__ne6vDetailRequests.length <= detailFailureCount) {
              return new Response(JSON.stringify({error: 'Synthetic one-time detail failure.'}), {
                status: 503,
                headers: {'Content-Type': 'application/json'},
              });
            }
            return makeJsonResponse(syntheticRelatedPassages);
          }
          const response = await window.__ne6vNativeFetch(input, init);
          if (url.pathname !== '/api/narrative-explorer/v1/passages/Genesis/2') return response;
          const projection = await response.clone().json();
          projection.items.push(placeItem, routeItem);
          const geography = projection.sections.find((section) => section.id === 'biblical_geography');
          geography.item_ids = Array.from(new Set([...(geography.item_ids || []), placeItemId, routeItemId]));
          geography.state = 'available';
          geography.source_domains = Array.from(new Set([...(geography.source_domains || []), 'test_only_fixture']));
          const mapCoverage = projection.coverage.find((entry) => entry.domain === 'maps');
          Object.assign(mapCoverage, {
            state: 'available', query_status: 'complete', query_returned_count: 2,
            projected_item_count: 2, reason_code: null, missing_subdomains: [],
            description: 'Controlled synthetic browser fixture; not authoritative map coverage.',
          });
          return makeJsonResponse(projection);
        };
        const originalOpenMapPanel = window.BHFMaps.openMapPanel.bind(window.BHFMaps);
        window.BHFMaps.openMapPanel = async (context) => {
          const requestContext = focusOverrideId && context?.acknowledgeFocus === true && context?.focusKind === 'place'
            ? {...context, focusPlaceId: focusOverrideId, focusTargetId: focusOverrideId}
            : context;
          const acknowledgment = await originalOpenMapPanel(requestContext);
          if (requestContext?.acknowledgeFocus === true) {
            window.__ne6vFocusRequests.push({context: requestContext, acknowledgment});
          }
          return acknowledgment;
        };
        window.__ne6vFixtureRecordIds = {place: placeRecordId, route: routeRecordId};
    """, NE6V_PLACE_ID, NE6V_ROUTE_ID, focus_override_id, include_related_passages, detail_failure_count)


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


def _read_http_body(url: str) -> tuple[bytes, dict[str, object]]:
    started = time.perf_counter()
    with urlopen(url, timeout=180) as response:
        headers_received = time.perf_counter()
        body = response.read()
        completed = time.perf_counter()
        return body, {
            "status": response.status,
            "content_length": response.headers.get("Content-Length"),
            "ttfb_ms": round((headers_received - started) * 1000, 3),
            "body_read_ms": round((completed - headers_received) * 1000, 3),
        }


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
        from bhf_agent.db.connection import connect
        from bhf_web import app as web_app_module

        cls._web_app_module = web_app_module
        cls._database_path = require_current_study_database(STUDY_DB)
        with connect(cls._database_path) as connection:
            if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
                raise AssertionError("BHF_STUDY_DB_READ_ONLY=1 did not guard the configured study database.")
            cls._study_schema_version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
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
                schema_version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                if schema_version != cls._study_schema_version:
                    raise AssertionError("The protected study database migration version changed during verification.")
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

    def test_firefox_disabled_flag_makes_no_explorer_or_map_requests_during_reading(self):
        runtime_config = self._app.state.runtime_config
        configured_value = runtime_config["narrativeExplorerEnabled"]
        runtime_config["narrativeExplorerEnabled"] = False
        try:
            self.open_home(1280, 900, query="ne6v-feature-disabled=1")
            self.assertFalse(self.driver.execute_script("return window.BHFRuntimeConfig.narrativeExplorerEnabled"))
            Select(self.driver.find_element(By.ID, "book-select")).select_by_visible_text("Genesis")
            self.select_value("#chapter-select", "2")
            self.wait.until(lambda browser: "Genesis 2" in browser.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
            self.driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]').click()
            self.wait.until(lambda browser: browser.find_element(
                By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]'
            ).get_attribute("aria-pressed") == "true")
            api_requests = self.driver.execute_script("""
                return performance.getEntriesByType('resource').map(entry => entry.name)
                  .filter(name => name.includes('/api/narrative-explorer/v1/') || name.includes('/api/maps/'));
            """)
            self.assertEqual(api_requests, [])
        finally:
            runtime_config["narrativeExplorerEnabled"] = configured_value

    def test_firefox_positive_map_focus_selects_isolated_synthetic_place(self):
        driver = self.driver
        self.open_home(1440, 1100, query="ne6v-synthetic-fixture=1")
        Select(driver.find_element(By.ID, "book-select")).select_by_visible_text("Genesis")
        self.select_value("#chapter-select", "2")
        self.wait.until(lambda browser: "Genesis 2" in browser.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
        driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]').click()
        self.wait.until(lambda browser: browser.execute_script(
            "const state=window.BHFStudySelection.getState(); return state.book==='Genesis' && state.chapter===2 && state.selectedVerses.includes(8)"
        ))
        self.assertTrue(driver.execute_script("return window.BHFRuntimeConfig.narrativeExplorerEnabled"))
        self.assertFalse(driver.execute_script("return Boolean(window.BHFTestMode)"))
        _install_ne6v_map_fixture(
            driver,
            include_related_passages=False,
            detail_failure_count=1,
        )

        driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        self.assertIn("Genesis 2:8", driver.find_element(By.CSS_SELECTOR, ".narrative-explorer-passage").text)
        geography = driver.find_element(By.CSS_SELECTOR, '[data-section-id="biblical_geography"]')
        geography.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()

        place_item_id = f"maps:{NE6V_PLACE_ID}"
        place_selector = f'[data-section-id="biblical_geography"] [data-narrative-item-id="{place_item_id}"]'
        place_item = self.wait.until(lambda browser: browser.find_element(By.CSS_SELECTOR, place_selector).find_element(By.XPATH, "ancestor::article"))
        place_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance summary").click()
        self.wait.until(lambda browser: "Physical identification status: established" in browser.find_element(
            By.CSS_SELECTOR, place_selector
        ).find_element(By.XPATH, "ancestor::article").text)
        place_item = driver.find_element(By.CSS_SELECTOR, place_selector).find_element(By.XPATH, "ancestor::article")
        self.assertIn("Physical identification status: established", place_item.text)
        self.assertIn("Place identification confidence: high", place_item.text)
        self.assertIn("Synthetic test data only (NE-6V acceptance)", place_item.text)
        self.assertIn("Genesis 2:8", place_item.text)
        self.assertEqual(place_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-action").text, "Open Maps Explorer and try to focus this item")
        place_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-action").click()

        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") == "selected")
        self.wait.until(lambda browser: browser.execute_script("return window.__ne6vFocusRequests.length >= 1"))
        place_ack = driver.execute_script("return window.__ne6vFocusRequests.at(-1)")
        print("NE6V_PLACE_ACK", json.dumps(place_ack))
        self.assertEqual(place_ack["context"]["focusKind"], "place")
        self.assertEqual(place_ack["context"]["focusTargetId"], NE6V_PLACE_ID)
        self.assertEqual(place_ack["acknowledgment"]["status"], "selected")
        self.assertEqual(place_ack["acknowledgment"]["requestedKind"], "place")
        self.assertEqual(place_ack["acknowledgment"]["requestedId"], NE6V_PLACE_ID)
        self.assertEqual(place_ack["acknowledgment"]["selectedKind"], "place")
        self.assertEqual(place_ack["acknowledgment"]["selectedId"], NE6V_PLACE_ID)
        self.assertEqual(driver.find_element(By.ID, "map-panel-status").get_attribute("data-state"), "selected")
        place_details = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#map-details .map-details-card")))
        self.assertIn("NE-6V Synthetic Test Place", place_details.text)
        self.assertIn(f"Synthetic test record ID: {NE6V_PLACE_ID}", place_details.text)
        self.assertIn(f"/api/maps/places/{NE6V_PLACE_ID}.kml", place_details.find_element(By.CSS_SELECTOR, ".map-kml-link").get_attribute("href"))
        retry_details = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-related-passages-retry]")))
        self.assertIn("authored links shown here are incomplete", place_details.text)
        self.assertEqual(driver.execute_script("return window.__ne6vDetailRequests.length"), 1)
        retry_details.click()
        self.wait.until(lambda browser: browser.execute_script(
            "return window.__ne6vDetailRequests.length === 2 "
            "&& document.querySelectorAll('#map-details .map-related-passages-group').length > 0"
        ))
        self.assertIn("Genesis 2:8", driver.find_element(By.CSS_SELECTOR, "#map-details .map-details-card").text)
        self.wait.until(lambda browser: browser.find_elements(
            By.CSS_SELECTOR, '#map-stage .leaflet-marker-icon[title="NE-6V Synthetic Test Place"]'
        ))

        catalog = _read_json(self._base_url + "/api/maps/catalog")
        projection = _read_json(self._base_url + "/api/narrative-explorer/v1/passages/Genesis/2?verse_start=8&verse_end=8")
        fixture_record_ids = {NE6V_PLACE_ID, NE6V_ROUTE_ID}
        self.assertFalse(
            any(str(item.get("id")) in fixture_record_ids for item in [*(catalog.get("places") or []), *(catalog.get("routes") or [])]),
            "real map catalog must not contain synthetic fixture records",
        )
        self.assertFalse(
            any(str(item.get("id")) in {f"maps:{record_id}" for record_id in fixture_record_ids} or str(item.get("object_id")) in fixture_record_ids for item in projection.get("items", [])),
            "real passage projection must not contain synthetic fixture records",
        )
        ckl_manifest = (ROOT / "framework" / "canonical_library" / "manifest.json").read_text(encoding="utf-8")
        self.assertFalse(any(record_id in ckl_manifest for record_id in fixture_record_ids))

        driver.find_element(By.CSS_SELECTOR, "[data-map-panel-close]").click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel").get_attribute("hidden") is not None)
        self.assertEqual(driver.switch_to.active_element.get_attribute("data-testid"), "map-browse-button")

    def test_firefox_john2_compact_maps_selection_mobile_cache_and_offline_retry(self):
        driver = self.driver
        runtime_config = self._app.state.runtime_config
        had_auto_pack_setting = "autoInstallOfflinePacks" in runtime_config
        previous_auto_pack_setting = runtime_config.get("autoInstallOfflinePacks")
        runtime_config["autoInstallOfflinePacks"] = False

        def restore_auto_pack_setting():
            if had_auto_pack_setting:
                runtime_config["autoInstallOfflinePacks"] = previous_auto_pack_setting
            else:
                runtime_config.pop("autoInstallOfflinePacks", None)

        self.addCleanup(restore_auto_pack_setting)
        self.open_home(390, 844, query="ne6r1-john2-compact=1")
        self.wait.until(lambda browser: browser.execute_script(
            "return Boolean(navigator.serviceWorker?.controller)"
        ))
        worker_url = driver.execute_script("return navigator.serviceWorker.controller.scriptURL")
        self.assertTrue(worker_url.endswith("/sw.js"), worker_url)
        driver.execute_async_script("""
            const done = arguments[0];
            (async () => {
              for (let index = localStorage.length - 1; index >= 0; index -= 1) {
                const key = localStorage.key(index);
                if (key?.startsWith('bhf.map-service:')) localStorage.removeItem(key);
              }
              done(true);
            })().catch(error => done({error: String(error)}));
        """)
        driver.execute_script("""
            window.__ne6r1MapApiTimings = [];
            const originalFetch = window.fetch.bind(window);
            window.fetch = async (input, init) => {
              const url = String(typeof input === 'string' ? input : input.url);
              const started = performance.now();
              const response = await originalFetch(input, init);
              if (!new URL(url, location.href).pathname.startsWith('/api/maps/')) return response;
              const headersAt = performance.now();
              const originalJson = response.json.bind(response);
              response.json = async () => {
                const bodyAndParseStarted = performance.now();
                const value = await originalJson();
                const completed = performance.now();
                window.__ne6r1MapApiTimings.push({
                  path: new URL(url, location.href).pathname,
                  includeRecords: new URL(url, location.href).searchParams.get('include_records'),
                  status: response.status,
                  contentLength: response.headers.get('Content-Length'),
                  offline: response.headers.get('X-BHF-Offline') === 'true',
                  headerWaitMs: Number((headersAt - started).toFixed(2)),
                  bodyAndJsonParseMs: Number((completed - bodyAndParseStarted).toFixed(2)),
                  totalMs: Number((completed - started).toFixed(2)),
                });
                return value;
              };
              return response;
            };
        """)
        opened = driver.execute_async_script("""
            const done = arguments[0];
            const started = performance.now();
            window.BHFMaps.openMapPanel({book: 'John', chapter: 2}).then(() => done({
              status: document.querySelector('#map-panel-status')?.dataset.state || '',
              hidden: Boolean(document.querySelector('#map-panel-status')?.hidden),
              width: innerWidth,
              scrollWidth: document.documentElement.scrollWidth,
              initialMapPanelMs: Number((performance.now() - started).toFixed(2)),
            })).catch(error => done({error: String(error)}));
        """)
        self.assertNotIn("error", opened)
        self.wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, "#map-stage .leaflet-marker-icon"))
        initial_catalog_timing = driver.execute_script("""
            return window.__ne6r1MapApiTimings.find(entry => entry.path === '/api/maps/catalog') || null;
        """)
        self.assertIsNotNone(initial_catalog_timing)
        self.assertEqual(initial_catalog_timing["includeRecords"], "false")
        self.assertLess(int(initial_catalog_timing["contentLength"]), 4096)
        compact_request = driver.execute_script("""
            return performance.getEntriesByType('resource')
              .map(entry => entry.name)
              .find(name => name.includes('/api/maps/places-for-passage?')
                && name.includes('book=John') && name.includes('chapter=2')) || '';
        """)
        self.assertIn("include_related_passages=false", compact_request)

        candidate = driver.execute_script("""
            const keys = Array.from({length: localStorage.length}, (_, index) => localStorage.key(index));
            const key = keys.find(value => value?.startsWith('bhf.map-service:')
              && value.includes('/api/maps/places-for-passage?') && value.includes('include_related_passages=false'));
            const cached = key ? JSON.parse(localStorage.getItem(key))?.value : null;
            const marker = cached?.markers?.find(value => value.id === 'openbible-aac6cda');
            const icon = marker && Array.from(document.querySelectorAll('#map-stage .leaflet-marker-icon'))
              .find(value => value.title === marker.name);
            return marker && icon ? {
              id: marker.id, name: marker.name, referenceCount: marker.reference_count,
              markerCount: cached.markers.length, iconCount: document.querySelectorAll('#map-stage .leaflet-marker-icon').length,
            } : null;
        """)
        self.assertIsNotNone(candidate, "the real compact passage result must include the stable source record")
        self.assertEqual(candidate["id"], "openbible-aac6cda")
        driver.execute_script("""
            window.__ne6r1DetailStarted = performance.now();
            const marker = Array.from(document.querySelectorAll('#map-stage .leaflet-marker-icon'))
              .find(value => value.title === arguments[0]);
            if (!marker) throw new Error('The requested rendered marker is missing.');
            marker.click();
        """, candidate["name"])
        self.wait.until(lambda browser: browser.execute_script("""
            const heading = document.querySelector('#map-details .map-details-card h3');
            const column = document.querySelector('#map-details-column');
            return heading?.textContent?.trim() === arguments[0]
              && column?.classList.contains('is-mobile-open');
        """, candidate["name"]))
        self.wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, "#map-details .map-related-passages-total"))
        details = driver.find_element(By.CSS_SELECTOR, "#map-details .map-details-card")
        selected_heading = driver.execute_script(
            "return document.querySelector('#map-details .map-details-card h3')?.textContent?.trim() || '';"
        )
        self.assertEqual(selected_heading, candidate["name"])
        kml_url = details.find_element(By.CSS_SELECTOR, ".map-kml-link").get_attribute("href")
        self.assertTrue(kml_url.endswith(f"/api/maps/places/{candidate['id']}.kml"), kml_url)
        detail_request = driver.execute_script("""
            return performance.getEntriesByType('resource').map(entry => entry.name)
              .find(name => name.includes('/api/maps/related-passages-for-place?')
                && name.includes('place_id=' + encodeURIComponent(arguments[0]))) || '';
        """, candidate["id"])
        self.assertIn(f"place_id={candidate['id']}", detail_request)
        self.assertGreater(len(driver.find_elements(By.CSS_SELECTOR, "#map-details .map-related-passages-group")), 0)
        detail_timing = driver.execute_script("""
            const name = arguments[0];
            const entry = performance.getEntriesByName(name).at(-1);
            return {
              elapsedSinceMarkerSelectionMs: Number((performance.now() - window.__ne6r1DetailStarted).toFixed(2)),
              durationMs: entry ? Number(entry.duration.toFixed(2)) : null,
              transferSize: entry?.transferSize ?? null,
              encodedBodySize: entry?.encodedBodySize ?? null,
              decodedBodySize: entry?.decodedBodySize ?? null,
            };
        """, detail_request)
        compact_timing = driver.execute_script("""
            const name = arguments[0];
            const entry = performance.getEntriesByName(name).at(-1);
            return entry ? {
              durationMs: Number(entry.duration.toFixed(2)),
              transferSize: entry.transferSize,
              encodedBodySize: entry.encodedBodySize,
              decodedBodySize: entry.decodedBodySize,
            } : null;
        """, compact_request)
        self.assertLessEqual(
            driver.execute_script("return document.documentElement.scrollWidth"),
            driver.execute_script("return window.innerWidth"),
        )

        driver.set_script_timeout(240)
        offline_pack_install = driver.execute_async_script("""
            const done = arguments[0];
            const started = performance.now();
            window.BHFPWA.installOfflinePack('maps').then(pack => done({
              packId: pack.pack_id,
              responseCount: pack.responses?.length || 0,
              elapsedMs: Number((performance.now() - started).toFixed(2)),
            })).catch(error => done({error: String(error)}));
        """)
        self.assertNotIn("error", offline_pack_install)
        self.assertEqual(offline_pack_install["packId"], "maps")
        self.assertEqual(offline_pack_install["responseCount"], 7)

        cache_stats = driver.execute_async_script("""
            const done = arguments[0];
            (async () => {
              const cache = await caches.open('bhf-api-v49');
              const requests = (await cache.keys()).filter(request => new URL(request.url).pathname.startsWith('/api/maps/'));
              let cacheBytes = 0;
              const paths = [];
              for (const request of requests) {
                const response = await cache.match(request);
                const bytes = await response.clone().arrayBuffer().then(value => value.byteLength);
                cacheBytes += bytes;
                paths.push({path: new URL(request.url).pathname, bytes});
              }
              const keys = Array.from({length: localStorage.length}, (_, index) => localStorage.key(index))
                .filter(key => key?.startsWith('bhf.map-service:'));
              const localStorageBytes = keys.reduce((sum, key) => sum + localStorage.getItem(key).length * 2, 0);
              const packMetadata = await window.BHFOfflineDB.get('metadata', 'pack:maps');
              const wholePack = await window.BHFOfflineDB.get('apiResponses', '/api/offline/packs/maps');
              const indexedMapEntries = (await window.BHFOfflineDB.list('apiResponses'))
                .filter(entry => String(entry.url || '').startsWith('/api/maps/'))
                .map(entry => ({url: entry.url, bytes: new TextEncoder().encode(JSON.stringify(entry.payload)).byteLength}));
              done({
                cacheCount: requests.length, cacheBytes, paths,
                localStorageCount: keys.length, localStorageBytes,
                offlinePackVersion: packMetadata?.payload?.cache_version || '',
                wholePackStoredInIndexedDb: Boolean(wholePack), indexedMapEntries,
              });
            })().catch(error => done({error: String(error)}));
        """)
        self.assertNotIn("error", cache_stats)
        self.assertLessEqual(cache_stats["cacheCount"], 32)
        self.assertLessEqual(cache_stats["cacheBytes"], 8 * 1024 * 1024)
        self.assertTrue(all(path["bytes"] <= 4 * 1024 * 1024 for path in cache_stats["paths"]))
        self.assertTrue(any(path["path"] == "/api/maps/places-for-passage" and path["bytes"] < 512 * 1024
                            for path in cache_stats["paths"]))
        self.assertIn("/api/maps/catalog", [path["path"] for path in cache_stats["paths"]])
        self.assertIn("/api/maps/biblical-places", [path["path"] for path in cache_stats["paths"]])
        self.assertNotIn("/api/offline/packs/maps", [path["path"] for path in cache_stats["paths"]])
        self.assertLessEqual(cache_stats["localStorageCount"], 16)
        self.assertLessEqual(cache_stats["localStorageBytes"], 2 * 1024 * 1024)
        self.assertEqual(cache_stats["offlinePackVersion"], "v49")
        self.assertFalse(cache_stats["wholePackStoredInIndexedDb"])
        self.assertTrue(all(entry["bytes"] <= 512 * 1024 for entry in cache_stats["indexedMapEntries"]))

        driver.execute_async_script("""
            const done = arguments[0];
            window.BHFMaps.openMapPanel({book: '3 John', chapter: 1}).then(() => done(true))
              .catch(error => done({error: String(error)}));
        """)
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") != "loading")
        self.assertEqual(driver.find_elements(By.CSS_SELECTOR, "#map-stage .leaflet-marker-icon"), [])
        driver.execute_async_script("""
            const done = arguments[0];
            window.BHFMaps.openMapPanel({book: 'John', chapter: 2}).then(() => done(true))
              .catch(error => done({error: String(error)}));
        """)
        self.wait.until(lambda browser: len(browser.find_elements(By.CSS_SELECTOR, "#map-stage .leaflet-marker-icon")) == 69)

        # Stop the server so the active worker must serve cached Maps responses
        # with its offline header. Restart in a finally block for later tests.
        type(self)._server_runner.should_exit = True
        type(self)._thread.join(timeout=15)
        self.assertFalse(type(self)._thread.is_alive(), "test server must stop before the offline request")
        try:
            driver.execute_async_script("""
                const done = arguments[0];
                window.BHFMaps.openMapPanel({book: 'John', chapter: 2}).then(() => done(true))
                  .catch(error => done({error: String(error)}));
            """)
            self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") == "warning")
            offline_status_text = driver.execute_script(
                "return document.querySelector('#map-panel-status')?.textContent?.trim() || '';"
            )
            self.assertIn("cached local map data", offline_status_text)
        finally:
            type(self)._server_runner = Server(Config(
                type(self)._app,
                host="127.0.0.1",
                port=type(self)._port,
                log_level="warning",
                access_log=False,
            ))
            type(self)._thread = threading.Thread(target=type(self)._server_runner.run, daemon=True)
            type(self)._thread.start()
            _wait_for_url(self._base_url + "/api/health")

        retried = driver.execute_async_script("""
            const done = arguments[0];
            window.BHFMaps.openMapPanel({book: 'John', chapter: 2}).then(() => done({
              status: document.querySelector('#map-panel-status')?.dataset.state || '',
              hidden: Boolean(document.querySelector('#map-panel-status')?.hidden),
            })).catch(error => done({error: String(error)}));
        """)
        self.assertNotIn("error", retried)
        self.assertNotEqual(retried["status"], "warning")
        print("NE6R1_JOHN2_COMPACT", json.dumps({
            "browser": driver.capabilities.get("browserVersion"),
            "service_worker": worker_url,
            "viewport": driver.execute_script("return {width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth}"),
            "compact_request": compact_request,
            "initial_map_panel_ms": opened["initialMapPanelMs"],
            "initial_catalog_timing": initial_catalog_timing,
            "map_api_timings": driver.execute_script("return window.__ne6r1MapApiTimings || []"),
            "compact_request_timing": compact_timing,
            "selected_id": candidate["id"],
            "details_request": detail_request,
            "selected_detail_timing": detail_timing,
            "offline_pack_install": offline_pack_install,
            "cache_storage": cache_stats,
            "offline_status_text": offline_status_text,
            "offline_status": "warning with cached data, retry refreshed online",
        }))

    def test_firefox_repeated_john2_legacy_body_consumption_with_and_without_service_worker(self):
        from fastapi.responses import JSONResponse
        import bhf_web.routes.maps as map_routes

        driver = self.driver
        self.open_home(1280, 900, query="ne6r1-large-body-replay=1")
        self.wait.until(lambda browser: browser.execute_script(
            "return Boolean(navigator.serviceWorker?.controller)"
        ))
        legacy_url = self._base_url + "/api/maps/places-for-passage?book=John&chapter=2"
        raw_body, direct_http = _read_http_body(legacy_url)
        payload = json.loads(raw_body.decode("utf-8"))
        body_sha256 = hashlib.sha256(raw_body).hexdigest()
        self.assertEqual(direct_http["status"], 200)
        self.assertEqual(len(raw_body), int(direct_http["content_length"]))
        self.assertEqual(len(payload["markers"]), 69)
        self.assertEqual(body_sha256, "fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f")
        self.assertEqual(hashlib.sha256(JSONResponse(payload).body).hexdigest(), body_sha256)

        async_script = """
          const baseUrl = arguments[0];
          const runCount = arguments[1];
          const expectedIds = arguments[2];
          const done = arguments[3];
          (async () => {
            const runs = [];
            for (let index = 0; index < runCount; index += 1) {
              const url = `${baseUrl}&ne6r1_replay=${index}`;
              const started = performance.now();
              try {
                const response = await fetch(url, {headers: {Accept: 'application/json'}, cache: 'no-store'});
                const headersAt = performance.now();
                const contentLength = Number(response.headers.get('Content-Length') || 0);
                const text = await response.text();
                const bodyCompleted = performance.now();
                const result = JSON.parse(text);
                const completed = performance.now();
                const resource = performance.getEntriesByName(url).at(-1);
                const ids = (result.markers || []).map(marker => marker.id);
                runs.push({
                  ok: response.status === 200 && JSON.stringify(ids) === JSON.stringify(expectedIds),
                  status: response.status,
                  contentLength,
                  bodyBytes: new TextEncoder().encode(text).byteLength,
                  markerCount: ids.length,
                  exactIds: JSON.stringify(ids) === JSON.stringify(expectedIds),
                  totalMs: Number((completed - started).toFixed(2)),
                  headerWaitMs: Number((headersAt - started).toFixed(2)),
                  bodyReadMs: Number((bodyCompleted - headersAt).toFixed(2)),
                  jsonParseMs: Number((completed - bodyCompleted).toFixed(2)),
                  ttfbMs: resource ? Number((resource.responseStart - resource.requestStart).toFixed(2)) : null,
                  bodyMs: resource ? Number((resource.responseEnd - resource.responseStart).toFixed(2)) : null,
                  encodedBodySize: resource?.encodedBodySize ?? null,
                });
              } catch (error) {
                runs.push({ok: false, error: String(error)});
              }
            }
            done(runs);
          })().catch(error => done({fatal: String(error)}));
        """
        expected_ids = [marker["id"] for marker in payload["markers"]]
        driver.set_script_timeout(240)
        with patch.object(map_routes, "resolve_places_for_passage", return_value=payload):
            service_worker_runs = driver.execute_async_script(
                async_script,
                self._base_url + "/api/maps/places-for-passage?book=John&chapter=2",
                5,
                expected_ids,
            )
            self.assertEqual(len(service_worker_runs), 5, service_worker_runs)
            self.assertTrue(all(run.get("ok") for run in service_worker_runs), service_worker_runs)
            no_large_cache_entries = driver.execute_async_script("""
                const done = arguments[0];
                (async () => {
                  const cache = await caches.open('bhf-api-v49');
                  const requests = await cache.keys();
                  done(requests.filter(request => request.url.includes('ne6r1_replay=')).map(request => request.url));
                })().catch(error => done({error: String(error)}));
            """)
            self.assertEqual(no_large_cache_entries, [])

            control_options = FirefoxOptions()
            control_options.add_argument("-headless")
            control_options.set_preference("dom.serviceWorkers.enabled", False)
            control = webdriver.Firefox(
                service=FirefoxService(executable_path=str(GECKODRIVER)),
                options=control_options,
            )
            control.set_page_load_timeout(90)
            control.set_script_timeout(240)
            try:
                control.set_window_size(1280, 900)
                control.get(self._base_url + "/")
                WebDriverWait(control, 90).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="reader-passage"]')))
                self.assertFalse(control.execute_script("return Boolean(navigator.serviceWorker?.controller)"))
                control_runs = control.execute_async_script(
                    async_script,
                    self._base_url + "/api/maps/places-for-passage?book=John&chapter=2",
                    5,
                    expected_ids,
                )
            finally:
                control.quit()

        self.assertEqual(len(control_runs), 5, control_runs)
        self.assertTrue(all(run.get("ok") for run in control_runs), control_runs)
        print("NE6R1_JOHN2_FULL_BODY", json.dumps({
            "browser": driver.capabilities.get("browserVersion"),
            "runs_per_mode": 5,
            "service_worker_cache_state": "fresh v49 map cache; each 21.7 MB body deliberately uncached",
            "direct_http": direct_http,
            "body_bytes": len(raw_body),
            "raw_sha256": body_sha256,
            "marker_count": len(expected_ids),
            "service_worker_successes": sum(bool(run.get("ok")) for run in service_worker_runs),
            "service_worker_failures": sum(not run.get("ok") for run in service_worker_runs),
            "service_worker_runs": service_worker_runs,
            "sw_disabled_successes": sum(bool(run.get("ok")) for run in control_runs),
            "sw_disabled_failures": sum(not run.get("ok") for run in control_runs),
            "sw_disabled_runs": control_runs,
        }))

    def test_firefox_positive_map_focus_selects_isolated_synthetic_route(self):
        driver = self.driver
        self.open_home(1440, 1100, query="ne6v-synthetic-route=1")
        Select(driver.find_element(By.ID, "book-select")).select_by_visible_text("Genesis")
        self.select_value("#chapter-select", "2")
        self.wait.until(lambda browser: "Genesis 2" in browser.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
        driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]').click()
        self.wait.until(lambda browser: browser.execute_script(
            "const state=window.BHFStudySelection.getState(); return state.book==='Genesis' && state.chapter===2 && state.selectedVerses.includes(8)"
        ))
        _install_ne6v_map_fixture(driver)
        driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        driver.find_element(By.CSS_SELECTOR, '[data-section-id="biblical_geography"] .narrative-explorer-inspect').click()

        route_selector = f'[data-section-id="biblical_geography"] [data-narrative-item-id="maps:{NE6V_ROUTE_ID}"]'
        route_item = self.wait.until(lambda browser: browser.find_element(By.CSS_SELECTOR, route_selector).find_element(By.XPATH, "ancestor::article"))
        route_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-provenance summary").click()
        self.wait.until(lambda browser: "Physical identification status: established" in browser.find_element(
            By.CSS_SELECTOR, route_selector
        ).find_element(By.XPATH, "ancestor::article").text)
        route_item = driver.find_element(By.CSS_SELECTOR, route_selector).find_element(By.XPATH, "ancestor::article")
        self.assertIn("Physical identification status: established", route_item.text)
        self.assertIn("Place identification confidence: high", route_item.text)
        self.assertIn("Synthetic test data only (NE-6V acceptance)", route_item.text)
        self.assertEqual(route_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-action").text, "Open Maps Explorer and try to focus this item")
        route_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-action").click()

        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") == "selected")
        self.wait.until(lambda browser: browser.execute_script("return window.__ne6vFocusRequests.length >= 1"))
        route_ack = driver.execute_script("return window.__ne6vFocusRequests.at(-1)")
        print("NE6V_ROUTE_ACK", json.dumps(route_ack))
        self.assertEqual(route_ack["context"]["focusKind"], "route")
        self.assertEqual(route_ack["context"]["focusTargetId"], NE6V_ROUTE_ID)
        self.assertEqual(route_ack["acknowledgment"]["status"], "selected")
        self.assertEqual(route_ack["acknowledgment"]["requestedKind"], "route")
        self.assertEqual(route_ack["acknowledgment"]["requestedId"], NE6V_ROUTE_ID)
        self.assertEqual(route_ack["acknowledgment"]["selectedKind"], "route")
        self.assertEqual(route_ack["acknowledgment"]["selectedId"], NE6V_ROUTE_ID)
        self.assertEqual(driver.find_element(By.ID, "map-panel-status").get_attribute("aria-live"), "polite")
        route_details = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#map-details .map-details-card")))
        self.assertIn("NE-6V Synthetic Test Route", route_details.text)
        self.assertIn(f"/api/maps/routes/{NE6V_ROUTE_ID}.kml", route_details.find_element(By.CSS_SELECTOR, ".map-kml-link").get_attribute("href"))
        self.assertTrue(driver.find_elements(By.CSS_SELECTOR, "#map-stage .leaflet-overlay-pane path.leaflet-interactive"))

    def test_firefox_negative_map_focus_returns_not_found_for_wrong_id(self):
        driver = self.driver
        self.open_home(1280, 900, query="ne6v-synthetic-negative=1")
        Select(driver.find_element(By.ID, "book-select")).select_by_visible_text("Genesis")
        self.select_value("#chapter-select", "2")
        self.wait.until(lambda browser: "Genesis 2" in browser.find_element(By.CSS_SELECTOR, "#chapter-reader h3").text)
        driver.find_element(By.CSS_SELECTOR, '#chapter-reader [data-verse="8"] [data-verse-select]').click()
        self.wait.until(lambda browser: browser.execute_script(
            "const state=window.BHFStudySelection.getState(); return state.book==='Genesis' && state.chapter===2 && state.selectedVerses.includes(8)"
        ))
        _install_ne6v_map_fixture(driver, focus_override_id="ne6v_missing_place_999")
        driver.find_element(By.CSS_SELECTOR, '[data-testid="companion-narrative-explorer"]').click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".narrative-explorer-sections")))
        geography = driver.find_element(By.CSS_SELECTOR, '[data-section-id="biblical_geography"]')
        geography.find_element(By.CSS_SELECTOR, ".narrative-explorer-inspect").click()
        place_item = self.wait.until(lambda browser: browser.find_element(
            By.CSS_SELECTOR, f'[data-section-id="biblical_geography"] [data-narrative-item-id="maps:{NE6V_PLACE_ID}"]'
        ).find_element(By.XPATH, "ancestor::article"))
        place_item.find_element(By.CSS_SELECTOR, ".narrative-explorer-item-action").click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") == "empty")
        self.wait.until(lambda browser: browser.execute_script("return window.__ne6vFocusRequests.length >= 1"))
        focus_attempt = driver.execute_script("return window.__ne6vFocusRequests.at(-1)")
        acknowledgment = focus_attempt["acknowledgment"]
        print("NE6V_MISSING_ID_ACK", json.dumps(focus_attempt))
        self.assertEqual(focus_attempt["context"]["focusTargetId"], "ne6v_missing_place_999")
        self.assertEqual(acknowledgment["status"], "not_found")
        self.assertNotEqual(acknowledgment["status"], "selected")
        status = driver.find_element(By.ID, "map-panel-status")
        self.assertEqual(status.get_attribute("data-state"), "empty")
        self.assertEqual(status.get_attribute("aria-live"), "polite")
        self.assertIn("was not found in the map results", status.text)
        self.assertIn("It has not been selected", status.text)

    def test_firefox_desktop_mobile_trail_maps_fallback_and_offline_retry(self):
        driver = self.driver
        self.open_home(1440, 1100)
        self.wait.until(lambda browser: browser.execute_script("return Boolean(navigator.serviceWorker?.controller)"))
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
        trail_navigation = evidence.find_element(By.CSS_SELECTOR, 'nav[aria-label="Evidence trail"]')
        current_trail_step = trail_navigation.find_element(By.CSS_SELECTOR, '[aria-current="page"]')
        self.assertIn("Garden planting and divine presence", current_trail_step.text)
        self.assertTrue(evidence.find_element(By.CSS_SELECTOR, '[aria-label="Evidence trail navigation"]').is_displayed())
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
        self.wait.until(lambda browser: browser.execute_script(
            "return document.activeElement?.dataset?.narrativePrimary === 'true'"
        ))
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
        self.wait.until(lambda browser: browser.execute_script(
            "return document.querySelector('.narrative-explorer-passage')?.textContent.includes('Genesis 2:8')"
        ))
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
            window.BHFMaps.openMapPanel({book:'3 John', chapter:1,
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
            window.__ne6RetryStatusTransitions = [];
            const retryStatus = document.querySelector('#map-panel-status');
            const replaceRetryStatus = retryStatus.replaceChildren.bind(retryStatus);
            retryStatus.replaceChildren = (...nodes) => {
              const result = replaceRetryStatus(...nodes);
              window.__ne6RetryStatusTransitions.push({
                state: retryStatus.dataset.state || '',
                message: retryStatus.textContent,
              });
              return result;
            };
            if (window.__ne6Fetch) window.fetch = (input, init) => {
              const url = String(typeof input === 'string' ? input : input.url);
              return window.__ne6Fetch(input, init).then(response => {
                const record = {
                  url,
                  status: response.status,
                  contentLength: response.headers.get('content-length'),
                  json: 'pending',
                };
                const responseJson = response.json.bind(response);
                response.json = (...args) => responseJson(...args).then(value => {
                  record.json = 'parsed';
                  return value;
                }).catch(error => {
                  record.json = {name: error.name, message: error.message};
                  throw error;
                });
                window.__ne6RetryFetchLog.push(record);
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
        retry_transitions = driver.execute_script("return window.__ne6RetryStatusTransitions")
        self.assertTrue(retry_log, "online retry should issue fresh map-data requests")
        self.assertIn("It has not been selected", retry_result.text, msg=f"online retry state={retry_result.get_attribute('data-state')} requests={retry_log}")
        self.assertEqual(
            retry_result.get_attribute("data-state"),
            "empty",
            msg=(
                f"online successful retry should classify an absent ID as not_found; "
                f"message={retry_result.text!r} requests={retry_log} "
                f"transitions={retry_transitions}"
            ),
        )
        self.assertIn("not found in the map results", retry_result.text)
        places_retry = next(entry for entry in retry_log if "/api/maps/places-for-passage" in entry["url"])
        self.assertEqual(places_retry["status"], 200, places_retry)
        self.assertEqual(places_retry["json"], "parsed", places_retry)
        self.assertTrue(places_retry["url"].startswith("/api/maps/places-for-passage?book=3+John&chapter=1"))
        print("NE6_MAP_RETRY", json.dumps({
            "state": retry_result.get_attribute("data-state"),
            "message": retry_result.text,
            "requests": retry_log,
            "status_transitions": retry_transitions,
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
        explorer_resource_timings = driver.execute_script("""
            return performance.getEntriesByType('resource')
              .filter(entry => entry.name.includes('/api/narrative-explorer/v1/passages/'))
              .map(entry => ({
                name: new URL(entry.name).pathname + new URL(entry.name).search,
                start_ms: entry.startTime,
                request_start_ms: entry.requestStart,
                response_start_ms: entry.responseStart,
                response_end_ms: entry.responseEnd,
                duration_ms: entry.duration,
                server_wait_ms: entry.responseStart && entry.requestStart
                  ? entry.responseStart - entry.requestStart : null,
                body_transfer_ms: entry.responseEnd && entry.responseStart
                  ? entry.responseEnd - entry.responseStart : null,
                transfer_size_bytes: entry.transferSize,
                encoded_body_bytes: entry.encodedBodySize,
                decoded_body_bytes: entry.decodedBodySize,
              }));
        """)
        print("NE6_BROWSER_METRICS", json.dumps({
            "explorer_response_samples": [{
                "passage": entry.get("passage"),
                "response_ms": entry.get("response_ms"),
                "payload_bytes": entry.get("payload_bytes"),
            } for entry in responses],
            "explorer_network_requests": response.get("network_requests"),
            "explorer_initial_overview_render_ms": render.get("initial_overview_render_ms"),
            "explorer_dom_node_growth": render.get("dom_node_growth"),
            "explorer_resource_timings": explorer_resource_timings,
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
        driver.execute_script("""
            window.__ne6MobileMapRequests = [];
            window.__ne6MobileOriginalFetch = window.fetch.bind(window);
            window.fetch = (input, init) => {
              const rawUrl = String(typeof input === 'string' ? input : input.url);
              const pathname = new URL(rawUrl, window.location.href).pathname;
              return window.__ne6MobileOriginalFetch(input, init).then(response => {
                if (pathname.startsWith('/api/maps/')) {
                  window.__ne6MobileMapRequests.push({pathname, status: response.status, ok: response.ok, finished: true});
                }
                return response;
              }).catch(error => {
                if (pathname.startsWith('/api/maps/')) {
                  window.__ne6MobileMapRequests.push({pathname, error: String(error), finished: true});
                }
                throw error;
              });
            };
        """)
        driver.find_element(By.CSS_SELECTOR, '[data-companion-resource="maps"]').click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        def catalog_terminal(browser):
            outcome = browser.execute_script("""
                const status = document.querySelector('#map-panel-status');
                return {
                  requests: window.__ne6MobileMapRequests || [],
                  state: status?.dataset.state || '',
                  hidden: Boolean(status?.hidden),
                  message: status?.textContent || '',
                };
            """)
            if not any(request.get("pathname") == "/api/maps/catalog" and request.get("finished") for request in outcome["requests"]):
                return False
            if outcome["state"] == "loading":
                return False
            return outcome

        catalog = WebDriverWait(driver, 120).until(catalog_terminal)
        catalog_request = next(request for request in catalog["requests"] if request["pathname"] == "/api/maps/catalog")
        self.assertEqual(catalog_request.get("status"), 200, msg=f"mobile map catalog request={catalog_request}")
        self.assertTrue(catalog["hidden"], msg=f"successful catalog load must clear the loading status: {catalog}")
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

        navigator_trigger.click()
        self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-map-search-query]")))
        search = driver.find_element(By.CSS_SELECTOR, "[data-map-search-query]")
        search.clear()
        search.send_keys("Jerusalem")
        search.send_keys(Keys.ENTER)

        def search_terminal(browser):
            requests = browser.execute_script("return window.__ne6MobileMapRequests || []")
            completed = any(request.get("pathname") == "/api/maps/search" and request.get("finished") for request in requests)
            return completed and browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") != "loading"

        WebDriverWait(driver, 90).until(search_terminal)
        search_log = driver.execute_script("return window.__ne6MobileMapRequests")
        search_request = next(request for request in search_log if request["pathname"] == "/api/maps/search")
        self.assertEqual(search_request.get("status"), 200, msg=f"mobile catalog search request={search_request}")
        self.assertGreater(int(driver.find_element(By.ID, "map-search-results-count").text), 0)
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-map-search-result-button]"))).click()
        self.wait.until(lambda browser: "Jerusalem" in browser.find_element(By.CSS_SELECTOR, "#map-details .map-details-card h3").text)
        self.assertIn("/api/maps/places/jerusalem.kml", driver.find_element(By.CSS_SELECTOR, "#map-details .map-kml-link").get_attribute("href"))
        self.assertLessEqual(
            driver.execute_script("return document.documentElement.scrollWidth"),
            driver.execute_script("return window.innerWidth"),
        )

        touch_targets = driver.execute_script("""
            return [
              '[data-map-navigator-open]', '[data-map-details-open]',
              '[data-map-panel-close]', '[data-map-search-submit]',
              '[data-map-search-result-button]'
            ].map(selector => {
              const element = document.querySelector(selector);
              const rect = element?.getBoundingClientRect();
              return {selector, width: rect?.width || 0, height: rect?.height || 0};
            });
        """)
        self.assertTrue(all(target["width"] >= 44 and target["height"] >= 44 for target in touch_targets), touch_targets)

        driver.save_screenshot("/tmp/ne6-firefox-mobile.png")
        driver.find_element(By.CSS_SELECTOR, "[data-map-navigator-close]").click()
        self.wait.until(lambda browser: "is-mobile-open" not in browser.find_element(
            By.ID, "map-study-navigator"
        ).get_attribute("class"))
        self.assertIn("is-mobile-open", driver.find_element(By.ID, "map-details-column").get_attribute("class"))
        self.assertTrue(driver.find_element(By.CSS_SELECTOR, "#map-details .map-details-card").is_displayed())
        driver.find_element(By.CSS_SELECTOR, "[data-map-panel-close]").click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel").get_attribute("hidden") is not None)
        self.assertEqual(driver.switch_to.active_element.get_attribute("data-testid"), "map-browse-button")
        print("NE6_MOBILE_MAPS", json.dumps({
            "viewport": driver.execute_script("return {width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth}"),
            "catalog_request": catalog_request,
            "loading_status_hidden_after_catalog": catalog["hidden"],
            "search_request": search_request,
            "search_results": int(driver.find_element(By.ID, "map-search-results-count").get_attribute("textContent")),
            "selected_detail_heading": driver.execute_script("return document.querySelector('#map-details .map-details-card h3')?.textContent?.trim() || ''"),
            "touch_targets": touch_targets,
            "close_focus_test_id": driver.switch_to.active_element.get_attribute("data-testid"),
        }))
        driver.find_element(By.CSS_SELECTOR, '[data-testid="map-browse-button"]').click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "map-panel")))
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel-status").get_attribute("data-state") != "loading")
        self.assertLessEqual(
            driver.execute_script("return document.documentElement.scrollWidth"),
            driver.execute_script("return window.innerWidth"),
        )
        driver.find_element(By.CSS_SELECTOR, "[data-map-panel-close]").click()
        self.wait.until(lambda browser: browser.find_element(By.ID, "map-panel").get_attribute("hidden") is not None)
        self.assertEqual(driver.switch_to.active_element.get_attribute("data-testid"), "map-browse-button")
