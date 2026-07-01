import asyncio
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import quote_plus, urlencode
from unittest.mock import patch

from bhf_agent.config import AgentConfig, ConfigError
from bhf_agent.models import (
    AgentResult,
    GenreContext,
    QuestionContext,
    ReferenceContext,
    ValidationResult,
)
from bhf_web.forms import config_from_form
from bhf_web.forms import load_web_defaults
from bhf_agent.study_db import get_source, initialize_database, list_sources

try:
    from bhf_web.app import AskJob, app

    HAS_WEB_DEPS = True
except ModuleNotFoundError:
    app = None
    AskJob = None
    HAS_WEB_DEPS = False


def read_stylesheet_bundle(path: Path) -> str:
    seen = set()

    def load(file_path: Path) -> str:
        resolved = file_path.resolve()
        if resolved in seen:
            return ""
        seen.add(resolved)
        text = file_path.read_text(encoding="utf-8")
        chunks = []
        for line in text.splitlines():
            match = re.match(r'@import url\(["\'](.+)["\']\);', line.strip())
            if match:
                chunks.append(load(file_path.parent / match.group(1)))
            else:
                chunks.append(line)
        return "\n".join(chunks)

    return load(path)


class WebFormTests(unittest.TestCase):
    def test_config_creation_from_form_validates(self):
        defaults = AgentConfig(
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
            api_key="local-secret",
        )

        config = config_from_form(
            {
                "profile": "standard",
                "answer_mode": "teaching",
                "model": "local-model",
                "base_url": "http://localhost:1234/v1",
                "temperature": "0.4",
                "max_tokens": "1024",
                "show_method_notes": "on",
                "memory_enabled": "on",
                "session_id": "lesson-1",
                "memory_path": ".bhf/sessions",
                "memory_max_turns": "4",
            },
            defaults,
        )

        self.assertEqual(config.profile, "standard")
        self.assertEqual(config.answer_mode, "teaching")
        self.assertEqual(config.model, "local-model")
        self.assertEqual(config.base_url, "http://localhost:1234/v1")
        self.assertEqual(config.temperature, 0.4)
        self.assertEqual(config.max_tokens, 1024)
        self.assertTrue(config.show_method_notes)
        self.assertTrue(config.memory_enabled)
        self.assertEqual(config.session_id, "lesson-1")
        self.assertEqual(config.memory_max_turns, 4)
        self.assertEqual(config.api_key, "local-secret")

    def test_invalid_form_config_returns_clear_error(self):
        defaults = AgentConfig(
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
        )

        with self.assertRaisesRegex(ConfigError, "temperature must be between 0 and 2"):
            config_from_form(
                {
                    "profile": "standard",
                    "answer_mode": "study",
                    "model": "local-model",
                    "base_url": "http://localhost:1234/v1",
                    "temperature": "3",
                    "max_tokens": "1024",
                    "memory_max_turns": "4",
                },
                defaults,
            )

    def test_web_defaults_read_environment_variables(self):
        env = {
            "BHF_BASE_URL": "http://host.docker.internal:11434/v1",
            "BHF_MODEL": "qwen2.5:7b",
            "BHF_PROFILE": "standard",
            "BHF_ANSWER_MODE": "concise",
            "BHF_TEMPERATURE": "0.2",
            "BHF_MAX_TOKENS": "1024",
            "BHF_TIMEOUT_SECONDS": "45",
            "BHF_SHOW_METHOD_NOTES": "false",
            "BHF_MEMORY_ENABLED": "true",
            "BHF_MEMORY_PATH": "/app/.bhf/sessions",
        }

        with patch.dict(os.environ, env, clear=False):
            loaded = load_web_defaults(path="/tmp/bhf-web-config-does-not-exist.json")

        config = loaded.config
        self.assertEqual(config.base_url, "http://host.docker.internal:11434/v1")
        self.assertEqual(config.model, "qwen2.5:7b")
        self.assertEqual(config.profile, "standard")
        self.assertEqual(config.answer_mode, "concise")
        self.assertEqual(config.temperature, 0.2)
        self.assertEqual(config.max_tokens, 1024)
        self.assertEqual(config.timeout_seconds, 45)
        self.assertFalse(config.show_method_notes)
        self.assertTrue(config.memory_enabled)
        self.assertEqual(config.memory_path, "/app/.bhf/sessions")

    def test_web_defaults_use_360_second_timeout(self):
        loaded = load_web_defaults(path="/tmp/bhf-web-config-does-not-exist.json")

        self.assertEqual(loaded.config.timeout_seconds, 360)

    def test_form_values_override_environment_defaults(self):
        env = {
            "BHF_BASE_URL": "http://host.docker.internal:11434/v1",
            "BHF_MODEL": "qwen2.5:7b",
            "BHF_PROFILE": "standard",
            "BHF_ANSWER_MODE": "study",
        }

        with patch.dict(os.environ, env, clear=False):
            defaults = load_web_defaults(
                path="/tmp/bhf-web-config-does-not-exist.json"
            ).config
            config = config_from_form(
                {
                    "profile": "minimal-7b",
                    "answer_mode": "concise",
                    "model": "form-model",
                    "base_url": "http://localhost:1234/v1",
                    "temperature": "0.1",
                    "max_tokens": "512",
                    "memory_max_turns": "4",
                },
                defaults,
            )

        self.assertEqual(config.base_url, "http://localhost:1234/v1")
        self.assertEqual(config.model, "form-model")
        self.assertEqual(config.profile, "minimal-7b")
        self.assertEqual(config.answer_mode, "concise")
        self.assertEqual(config.timeout_seconds, 360)


class WebAssetTests(unittest.TestCase):
    def test_status_script_collapses_active_panel_after_success(self):
        status_script = Path("bhf_web/static/htmx-status.js").read_text(encoding="utf-8")
        controller_script = Path("bhf_web/static/htmx-lite.js").read_text(encoding="utf-8")

        self.assertIn("function markStatusComplete", status_script)
        self.assertIn('querySelector(".status-active").hidden = true', status_script)
        self.assertIn("stopWaiting();", status_script)
        self.assertIn("setRunning(form, submitButton, false);", controller_script)

    def test_status_script_uses_rotating_waiting_text(self):
        script = Path("bhf_web/static/htmx-status.js").read_text(encoding="utf-8")

        self.assertIn("WAITING_MESSAGES", script)
        self.assertIn("Consulting the scrolls...", script)
        self.assertIn("Calling the Schwartz of Solomon...", script)
        self.assertIn("Waiting on the answer...", script)
        self.assertIn("WAITING_MESSAGE_BASE_DELAY_MS", script)
        self.assertIn("Math.random()", script)
        self.assertNotIn("The agent is running. Status updates will appear above.", script)
        self.assertNotIn("progress-track", script)
        self.assertNotIn("toFixed(3)", script)

    def test_reader_script_has_context_menu_and_highlight_actions(self):
        script = Path("bhf_web/static/htmx-lite.js").read_text(encoding="utf-8")

        self.assertIn("createStudyAction", script)
        self.assertIn("dispatchStudyAction", script)
        self.assertIn("sourceTranslation: \"ASV\"", script)
        self.assertIn("ancient_context", script)
        self.assertIn("literary_context", script)
        self.assertIn("cross_references", script)
        self.assertIn("related_ot_themes", script)
        self.assertIn("fulfillment_nt", script)
        self.assertIn("compare_translations", script)
        self.assertIn("timeline", script)
        self.assertIn("openMapPanel", script)
        self.assertIn("BHF_STUDY_ACTIONS", script)
        self.assertIn("contextmenu", script)
        self.assertIn("handleReaderContextMenu", script)
        self.assertIn("closeContextMenuOnEscape", script)
        self.assertIn("word_study", script)
        self.assertIn("open_map_panel", script)
        self.assertNotIn("studyAction.type === \"maps\"", script)

        study_script = Path("bhf_web/static/htmx-study-panels.js").read_text(encoding="utf-8")
        self.assertIn("/api/highlights", study_script)
        self.assertIn("saveLatestStudy", study_script)
        self.assertIn("loadSavedStudies", study_script)
        self.assertIn("formatReference", study_script)
        self.assertIn("prettyStudyType", study_script)

        search_script = Path("bhf_web/static/htmx-search.js").read_text(encoding="utf-8")
        self.assertIn("submitBibleSearch", search_script)
        self.assertIn("runBibleSearchFallback", search_script)
        self.assertIn("syncBibleSearchConfig", search_script)
        self.assertIn("renderBibleSearchResults", search_script)
        self.assertIn("handleBibleSearchResultAction", search_script)

        map_script = Path("bhf_web/static/maps/MapPanel.js").read_text(encoding="utf-8")
        self.assertIn("renderSelectedMarker", map_script)
        self.assertIn("renderSelectedArchaeology", map_script)
        self.assertIn("buildCautionNote", map_script)
        self.assertIn("buildArchaeologyCautionNote", map_script)
        self.assertIn("renderSelectedRoute", map_script)
        self.assertIn("buildRouteCautionNote", map_script)
        self.assertIn("loadArchaeologyForPassage", map_script)
        self.assertIn("loadManuscriptsForPassage", map_script)
        self.assertIn("loadRoutesForPassage", map_script)
        self.assertIn("renderSelectedHistoricalLayer", map_script)
        self.assertIn("buildHistoricalLayerCautionNote", map_script)
        self.assertIn("loadHistoricalLayers", map_script)
        self.assertIn("saveCurrentMapStudy", map_script)
        self.assertIn("renderSavedMapStudies", map_script)
        self.assertIn("openSavedMapStudy", map_script)
        self.assertIn("buildCurrentMapStudyPayload", Path("bhf_web/static/maps/MapPanelStateHelpers.js").read_text(encoding="utf-8"))
        self.assertIn("getCurrentMapSelection", Path("bhf_web/static/maps/MapPanelStateHelpers.js").read_text(encoding="utf-8"))
        self.assertIn("normalizeHistoricalPeriod", Path("bhf_web/static/maps/MapPanelStateHelpers.js").read_text(encoding="utf-8"))

        map_content_script = Path("bhf_web/static/maps/MapPanelContent.js").read_text(encoding="utf-8")
        self.assertIn("renderRelatedVerses", map_content_script)
        self.assertIn("renderRelatedPassages", map_content_script)
        self.assertIn("renderRelatedPassagesList", map_content_script)
        self.assertIn("addCurrentMapNote", map_script)
        self.assertIn("renderSelectedManuscript", map_script)
        self.assertIn("buildManuscriptCautionNote", map_script)
        self.assertIn("setManuscriptVisibility", map_script)
        self.assertIn("reset_map_view", map_script)
        self.assertIn("data-passage-shortcut", map_script)
        self.assertIn("submitRelatedPassageShortcut", map_script)
        self.assertIn("setReaderPassageContext", map_script)
        self.assertIn("renderSourceAttribution", map_content_script)
        self.assertIn("map-attribution", map_content_script)
        map_text_script = Path("bhf_web/static/maps/MapPanelText.js").read_text(encoding="utf-8")
        self.assertIn("/sources/", map_text_script)
        bible_map_script = Path("bhf_web/static/maps/BibleMap.js").read_text(encoding="utf-8")
        self.assertIn("map-entity-marker", bible_map_script)
        self.assertIn("entityMarkerIcon", bible_map_script)
        index_html = Path("bhf_web/templates/index.html").read_text(encoding="utf-8")
        self.assertNotIn('data-context-action="maps"', index_html)
        self.assertIn('data-context-action="open_map_panel"', index_html)
        self.assertNotIn('data-context-action="show_on_map"', index_html)

    def test_map_styles_cover_entity_icons_and_mobile_panel_layout(self):
        style = read_stylesheet_bundle(Path("bhf_web/static/style.css"))

        self.assertIn(".map-entity-marker", style)
        self.assertIn(".map-entity-marker--place", style)
        self.assertIn(".map-entity-marker--archaeology", style)
        self.assertIn(".map-entity-marker--manuscript", style)
        self.assertIn(".map-shortcut", style)
        self.assertIn(".map-details-card .compact", style)
        self.assertIn("@media (max-width: 680px)", style)
        self.assertIn(".map-panel-body {\n    gap: 10px;", style)
        self.assertIn(".map-details-panel,\n  .saved-map-study {\n    padding: 12px;", style)


class SourceRegistryTests(unittest.TestCase):
    def test_sources_are_seeded_and_resolve_attribution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "study.sqlite"
            initialize_database(db_path)
            sources = list_sources(path=db_path)

            self.assertGreaterEqual(len(sources), 1)
            source = get_source(sources[0]["id"], path=db_path)
            self.assertIn("reference_count", source)
            self.assertIn("references", source)
            self.assertGreaterEqual(source["reference_count"], 0)


@unittest.skipUnless(HAS_WEB_DEPS, "FastAPI test dependencies are not installed")
class WebAppTests(unittest.TestCase):
    def setUp(self):
        assert app is not None
        assert AskJob is not None

    def test_get_index_returns_200(self):
        response = asgi_request("GET", "/")

        self.assertEqual(response["status"], 200)
        self.assertIn("BHF ASV Reader", response["body"])
        self.assertIn("/curation", response["body"])
        self.assertIn("ASV Bible", response["body"])
        self.assertIn("book-select", response["body"])
        self.assertIn("reader-context-menu", response["body"])
        self.assertIn("data-context-action=\"ancient_context\"", response["body"])
        self.assertIn("data-context-action=\"literary_context\"", response["body"])
        self.assertIn("data-context-action=\"cross_references\"", response["body"])
        self.assertIn("data-context-action=\"related_ot_themes\"", response["body"])
        self.assertIn("data-context-action=\"fulfillment_nt\"", response["body"])
        self.assertIn("data-context-action=\"compare_translations\"", response["body"])
        self.assertIn("data-context-action=\"timeline\"", response["body"])
        self.assertIn("data-context-action=\"ask_location\"", response["body"])
        self.assertIn("data-context-action=\"open_map_panel\"", response["body"])
        self.assertIn("data-context-action=\"save_map_study\"", response["body"])
        self.assertIn("data-context-action=\"map_note\"", response["body"])
        self.assertIn("data-context-action=\"compare_archaeology\"", response["body"])
        self.assertIn("data-context-action=\"related_passages\"", response["body"])
        self.assertIn("data-context-action=\"view_historical_layer\"", response["body"])
        self.assertIn("data-context-action=\"save_study\"", response["body"])
        self.assertIn("data-context-action=\"word_study\"", response["body"])
        self.assertIn("map-panel", response["body"])
        self.assertIn("map-stage", response["body"])
        self.assertIn("map-details", response["body"])
        self.assertIn("data-archaeology-toggle", response["body"])
        self.assertIn("data-manuscript-toggle", response["body"])
        self.assertIn("data-route-toggle", response["body"])
        self.assertIn("data-historical-period", response["body"])
        self.assertIn("Broad / uncertain period", response["body"])
        self.assertIn("saved-map-studies", response["body"])
        self.assertIn("map_context", response["body"])
        self.assertIn("leaflet.css", response["body"])
        self.assertIn("highlights-list", response["body"])
        self.assertIn("saved-studies-list", response["body"])
        self.assertIn("name=\"question\"", response["body"])
        self.assertIn("status-summary", response["body"])
        self.assertIn("status-current", response["body"])
        self.assertIn("Save Study", response["body"])
        self.assertNotIn("progress-track", response["body"])
        self.assertNotIn("data-total-elapsed", response["body"])
        self.assertNotIn("status-percent", response["body"])

    def test_get_curation_page_returns_200(self):
        with self._temp_curation_db() as db_path:
            initialize_database(db_path)
            with patch("bhf_web.app.STUDY_DB_PATH", db_path):
                response = asgi_request("GET", "/curation")

        self.assertEqual(response["status"], 200)
        self.assertIn("BHF Curation", response["body"])
        self.assertIn("Places", response["body"])
        self.assertIn("Confidence Labels", response["body"])

    def test_curation_record_crud_and_bundle_import(self):
        with self._temp_curation_db() as db_path:
            initialize_database(db_path)
            with patch("bhf_web.app.STUDY_DB_PATH", db_path):
                create = asgi_request(
                    "POST",
                    "/api/curation/confidence_labels",
                    data={
                        "record_json": json.dumps(
                            {
                                "label": "reviewed",
                                "rank": 6,
                                "description": "Manually reviewed entry",
                                "notes": "local test",
                            }
                        )
                    },
                )
                self.assertEqual(create["status"], 201)
                created = json.loads(create["body"])
                self.assertEqual(created["label"], "reviewed")
                created_id = created["id"]

                listed = json.loads(
                    asgi_request("GET", "/api/curation/confidence_labels")["body"]
                )["records"]
                self.assertTrue(any(record["id"] == created_id for record in listed))

                export = json.loads(asgi_request("GET", "/api/curation/export")["body"])
                self.assertIn("collections", export)
                self.assertIn("confidence_labels", export["collections"])

                delete = asgi_request(
                    "POST",
                    f"/api/curation/confidence_labels/{created_id}/delete",
                )
                self.assertEqual(delete["status"], 200)

                after_delete = json.loads(
                    asgi_request("GET", "/api/curation/confidence_labels")["body"]
                )["records"]
                self.assertFalse(any(record["id"] == created_id for record in after_delete))

                bundle = {
                    "collections": {
                        "confidence_labels": [
                            {
                                "id": "curated-review",
                                "label": "curated-review",
                                "rank": 7,
                                "description": "Imported review label",
                                "notes": "",
                            }
                        ]
                    }
                }
                imported = asgi_request(
                    "POST",
                    "/api/curation/import",
                    data={"record_json": json.dumps(bundle)},
                )
                self.assertEqual(imported["status"], 200)
                imported_payload = json.loads(imported["body"])
                self.assertEqual(imported_payload["imported"]["confidence_labels"], 1)

                imported_records = json.loads(
                    asgi_request("GET", "/api/curation/confidence_labels")["body"]
                )["records"]
                self.assertEqual(len(imported_records), 1)
                self.assertEqual(imported_records[0]["id"], "curated-review")

    def _temp_curation_db(self):
        return tempfile.TemporaryDirectory()

    def test_sample_maps_route_returns_markers(self):
        response = asgi_request("GET", "/api/maps/biblical-places")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreaterEqual(len(data["markers"]), 5)
        jerusalem = next(marker for marker in data["markers"] if marker["id"] == "jerusalem")
        self.assertEqual(jerusalem["name"], "Jerusalem")
        self.assertIn("latitude", jerusalem)
        self.assertIn("longitude", jerusalem)
        self.assertIn("aliases", jerusalem)
        self.assertIn("confidence", jerusalem)
        self.assertIn("periods", jerusalem)
        self.assertIn("related_references", jerusalem)
        self.assertIn("related_passages", jerusalem)
        self.assertIn("groups", jerusalem["related_passages"])
        self.assertGreaterEqual(jerusalem["reference_count"], 1)

    def test_archaeology_route_returns_markers(self):
        response = asgi_request("GET", "/api/maps/archaeology")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreaterEqual(len(data["markers"]), 8)
        pilate = next(marker for marker in data["markers"] if marker["id"] == "pilate-stone")
        self.assertEqual(pilate["item_type"], "dedication inscription")
        self.assertIn("periods", pilate)
        self.assertIn("scripture_links", pilate)
        self.assertTrue(pilate["source_id"])
        self.assertIn("source", pilate)
        self.assertEqual(pilate["marker_kind"], "archaeology")

    def test_manuscripts_route_returns_markers(self):
        response = asgi_request("GET", "/api/maps/manuscripts")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreaterEqual(len(data["markers"]), 4)
        sinaiticus = next(marker for marker in data["markers"] if marker["id"] == "codex-sinaiticus")
        self.assertEqual(sinaiticus["manuscript_type"], "codex")
        self.assertIn("scripture_links", sinaiticus)
        self.assertEqual(sinaiticus["marker_kind"], "manuscript")

    def test_routes_route_returns_seeded_route(self):
        response = asgi_request("GET", "/api/maps/routes")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreaterEqual(len(data["routes"]), 1)
        route = next(route for route in data["routes"] if route["id"] == "pauls-first-missionary-journey")
        self.assertEqual(route["route_type"], "missionary_journey")
        self.assertIn("periods", route)
        self.assertEqual(route["geojson"]["geometry"]["type"], "LineString")
        self.assertIn("scripture_links", route)

    def test_map_catalog_route_returns_browse_friendly_sections(self):
        response = asgi_request("GET", "/api/maps/catalog?period=NT+%2F+Roman+period")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertIn("places", data)
        self.assertIn("routes", data)
        self.assertIn("archaeology", data)
        self.assertIn("manuscripts", data)
        self.assertIn("historical_layers", data)
        self.assertIn("political_context", data)
        self.assertIn("saved_map_studies", data)
        self.assertTrue(any(item["id"] == "capernaum" for item in data["places"]))
        self.assertTrue(any(item["id"] == "pilate-stone" for item in data["archaeology"]))

    def test_map_search_route_filters_by_kind_and_query(self):
        response = asgi_request("GET", "/api/maps/search?q=Jerusalem")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertEqual(data["query"], "Jerusalem")
        self.assertGreater(data["total_results"], 0)
        self.assertTrue(any(item["id"] == "jerusalem" for item in data["results"]))
        self.assertTrue(all("search_score" in item for item in data["results"]))

        archaeology_response = asgi_request("GET", "/api/maps/search?q=Pilate&kind=archaeology")
        self.assertEqual(archaeology_response["status"], 200)
        archaeology_data = json.loads(archaeology_response["body"])
        self.assertEqual(archaeology_data["kind"], "archaeology")
        self.assertTrue(all(item["kind"] == "archaeology" for item in archaeology_data["results"]))
        self.assertTrue(any(item["id"] == "pilate-stone" for item in archaeology_data["results"]))

    def test_period_filter_applies_to_all_map_endpoints(self):
        places_response = asgi_request("GET", "/api/maps/biblical-places?period=NT+%2F+Roman+period")
        self.assertEqual(places_response["status"], 200)
        places_data = json.loads(places_response["body"])
        self.assertIn("capernaum", {marker["id"] for marker in places_data["markers"]})

        archaeology_response = asgi_request("GET", "/api/maps/archaeology?period=NT+%2F+Roman+period")
        self.assertEqual(archaeology_response["status"], 200)
        archaeology_data = json.loads(archaeology_response["body"])
        self.assertIn("pilate-stone", {marker["id"] for marker in archaeology_data["markers"]})

        routes_response = asgi_request("GET", "/api/maps/routes?period=NT+%2F+Roman+period")
        self.assertEqual(routes_response["status"], 200)
        routes_data = json.loads(routes_response["body"])
        self.assertEqual(
            {route["id"] for route in routes_data["routes"]},
            {"pauls-first-missionary-journey"},
        )

        manuscripts_response = asgi_request("GET", "/api/maps/manuscripts?period=NT+%2F+Roman+period")
        self.assertEqual(manuscripts_response["status"], 200)
        manuscripts_data = json.loads(manuscripts_response["body"])
        self.assertIn("codex-sinaiticus", {marker["id"] for marker in manuscripts_data["markers"]})

        layers_response = asgi_request("GET", "/api/maps/historical-layers?period=Broad+%2F+uncertain+period")
        self.assertEqual(layers_response["status"], 200)
        layers_data = json.loads(layers_response["body"])
        self.assertEqual(layers_data["layers"], [])

    def test_places_for_passage_route_filters_and_handles_empty_state(self):
        alias_response = asgi_request(
            "GET",
            "/api/maps/places-for-passage?book=Acts&chapter=10&verse_start=1&verse_end=48&passage_text="
            + quote_plus("Cornelius came from Caesarea and went to Beth-lehem."),
        )
        self.assertEqual(alias_response["status"], 200)
        alias_data = json.loads(alias_response["body"])
        self.assertFalse(alias_data["empty_state"])
        self.assertIn("caesarea-maritima", alias_data["matched_place_ids"])
        self.assertIn("related_references", alias_data["markers"][0])
        self.assertTrue(alias_data["markers"][0]["related_references"])

        empty_response = asgi_request(
            "GET",
            "/api/maps/places-for-passage?passage_text=" + quote_plus("No curated locations here."),
        )
        self.assertEqual(empty_response["status"], 200)
        empty_data = json.loads(empty_response["body"])
        self.assertTrue(empty_data["empty_state"])
        self.assertEqual(empty_data["markers"], [])

    def test_related_passages_for_place_route_groups_location_links(self):
        response = asgi_request("GET", "/api/maps/related-passages-for-place?place_id=jerusalem")
        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertEqual(data["place_id"], "jerusalem")
        self.assertGreaterEqual(data["count"], 4)

        direct = next(group for group in data["groups"] if group["group_type"] == "directly_mentioned")
        self.assertEqual(direct["count"], 2)
        self.assertEqual([group["count"] for group in direct["testament_groups"]], [1, 1])
        self.assertTrue(any(group["group_type"] == "same_route" for group in data["groups"]))
        self.assertTrue(any(group["group_type"] == "same_empire_period" for group in data["groups"]))

    def test_routes_for_passage_route_filters_and_handles_empty_state(self):
        route_response = asgi_request(
            "GET",
            "/api/maps/routes-for-passage?book=Acts&chapter=13&verse_start=1&verse_end=52&passage_text="
            + quote_plus("The church in Antioch sent them out."),
        )
        self.assertEqual(route_response["status"], 200)
        route_data = json.loads(route_response["body"])
        self.assertFalse(route_data["empty_state"])
        self.assertIn("pauls-first-missionary-journey", route_data["matched_route_ids"])
        self.assertGreaterEqual(route_data["routes"][0]["reference_count"], 2)

        empty_route_response = asgi_request(
            "GET",
            "/api/maps/routes-for-passage?passage_text=" + quote_plus("No curated route here."),
        )
        self.assertEqual(empty_route_response["status"], 200)
        empty_route_data = json.loads(empty_route_response["body"])
        self.assertTrue(empty_route_data["empty_state"])
        self.assertEqual(empty_route_data["routes"], [])

    def test_archaeology_for_passage_route_filters_and_handles_empty_state(self):
        archaeology_response = asgi_request(
            "GET",
            "/api/maps/archaeology-for-passage?book=John&chapter=9&verse_start=7&verse_end=11&passage_text="
            + quote_plus("He sent him to the pool of Siloam."),
        )
        self.assertEqual(archaeology_response["status"], 200)
        archaeology_data = json.loads(archaeology_response["body"])
        self.assertFalse(archaeology_data["empty_state"])
        self.assertIn("pool-of-siloam", archaeology_data["matched_archaeology_ids"])

        empty_archaeology_response = asgi_request(
            "GET",
            "/api/maps/archaeology-for-passage?passage_text=" + quote_plus("No archaeology matches here."),
        )
        self.assertEqual(empty_archaeology_response["status"], 200)
        empty_archaeology_data = json.loads(empty_archaeology_response["body"])
        self.assertTrue(empty_archaeology_data["empty_state"])
        self.assertEqual(empty_archaeology_data["markers"], [])

    def test_manuscripts_for_passage_route_filters_and_handles_empty_state(self):
        manuscript_response = asgi_request(
            "GET",
            "/api/maps/manuscripts-for-passage?book=John&chapter=1&verse_start=1&verse_end=18&passage_text="
            + quote_plus("In the beginning was the Word."),
        )
        self.assertEqual(manuscript_response["status"], 200)
        manuscript_data = json.loads(manuscript_response["body"])
        self.assertFalse(manuscript_data["empty_state"])
        self.assertIn("codex-sinaiticus", manuscript_data["matched_manuscript_ids"])

        empty_manuscript_response = asgi_request(
            "GET",
            "/api/maps/manuscripts-for-passage?passage_text=" + quote_plus("No manuscript matches here."),
        )
        self.assertEqual(empty_manuscript_response["status"], 200)
        empty_manuscript_data = json.loads(empty_manuscript_response["body"])
        self.assertTrue(empty_manuscript_data["empty_state"])
        self.assertEqual(empty_manuscript_data["markers"], [])

    def test_historical_layers_route_returns_curated_layers(self):
        response = asgi_request("GET", "/api/maps/historical-layers")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreaterEqual(len(data["layers"]), 4)
        layer = next(layer for layer in data["layers"] if layer["id"] == "assyrian-empire")
        self.assertEqual(layer["layer_type"], "empire")
        self.assertEqual(layer["geojson"]["geometry"]["type"], "Polygon")

        filtered_response = asgi_request("GET", "/api/maps/historical-layers?period=Divided+Kingdom")
        self.assertEqual(filtered_response["status"], 200)
        filtered_data = json.loads(filtered_response["body"])
        self.assertEqual(
            {layer["period"] for layer in filtered_data["layers"]},
            {"Divided Kingdom"},
        )

    def test_political_context_route_returns_curated_layers(self):
        response = asgi_request("GET", "/api/maps/political-context")
        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreaterEqual(len(data["layers"]), 8)
        rome = next(layer for layer in data["layers"] if layer["id"] == "rome")
        self.assertEqual(rome["entity_type"], "empire")
        self.assertEqual(rome["geojson"]["geometry"]["type"], "Polygon")
        self.assertIn("scripture_links", rome)

        filtered_response = asgi_request("GET", "/api/maps/political-context?period=NT+%2F+Roman+period")
        self.assertEqual(filtered_response["status"], 200)
        filtered_data = json.loads(filtered_response["body"])
        self.assertEqual({layer["id"] for layer in filtered_data["layers"]}, {"rome"})

    def test_political_context_for_passage_route_filters_and_handles_empty_state(self):
        response = asgi_request(
            "GET",
            "/api/maps/political-context-for-passage?book=John&chapter=19&verse_start=1&verse_end=16&passage_text="
            + quote_plus("Then they led Jesus to Pilate."),
        )
        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertFalse(data["empty_state"])
        self.assertIn("rome", data["matched_political_context_ids"])

        empty_response = asgi_request(
            "GET",
            "/api/maps/political-context-for-passage?passage_text=" + quote_plus("No political context matches here."),
        )
        self.assertEqual(empty_response["status"], 200)
        empty_data = json.loads(empty_response["body"])
        self.assertTrue(empty_data["empty_state"])
        self.assertEqual(empty_data["layers"], [])

    def test_map_studies_route_creates_lists_and_deletes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "study.sqlite"
            with patch("bhf_web.app.STUDY_DB_PATH", db_path):
                create_response = asgi_request(
                    "POST",
                    "/api/map-studies",
                    json_data={
                        "book": "Romans",
                        "chapter": 12,
                        "start_verse": 1,
                        "end_verse": 2,
                        "passage_reference": "Romans 12:1-2",
                        "selected_place_id": "jerusalem",
                        "selected_layers": ["roman-judea-galilee"],
                        "map_view_state": {"center": [31.78, 35.23], "zoom": 8},
                        "generated_summary": "Jerusalem study overlay.",
                        "user_notes": "Focus on the temple setting.",
                    },
                )
                self.assertEqual(create_response["status"], 201)
                study = json.loads(create_response["body"])
                self.assertEqual(study["selected_place_id"], "jerusalem")

                list_response = asgi_request("GET", "/api/map-studies?book=Romans&chapter=12")
                self.assertEqual(list_response["status"], 200)
                studies = json.loads(list_response["body"])["saved_map_studies"]
                self.assertEqual(len(studies), 1)
                self.assertEqual(studies[0]["map_notes"], [])

                open_response = asgi_request("GET", f"/api/map-studies/{study['id']}")
                self.assertEqual(open_response["status"], 200)
                self.assertIn("Jerusalem study overlay.", open_response["body"])

                note_response = asgi_request(
                    "POST",
                    "/api/map-notes",
                    json_data={
                        "book": "Romans",
                        "chapter": 12,
                        "start_verse": 1,
                        "end_verse": 2,
                        "passage_reference": "Romans 12:1-2",
                        "place_id": "jerusalem",
                        "note_body": "Tie this to the temple backdrop.",
                    },
                )
                self.assertEqual(note_response["status"], 201)
                note = json.loads(note_response["body"])
                self.assertEqual(note["place_id"], "jerusalem")

                updated_list = asgi_request("GET", "/api/map-studies?book=Romans&chapter=12")
                updated_studies = json.loads(updated_list["body"])["saved_map_studies"]
                self.assertEqual(len(updated_studies[0]["map_notes"]), 1)

                delete_response = asgi_request("DELETE", f"/api/map-studies/{study['id']}")
                self.assertEqual(delete_response["status"], 200)

    def test_health_route_returns_ok(self):
        response = asgi_request("GET", "/api/health")

        self.assertEqual(response["status"], 200)
        self.assertIn('"status":"ok"', response["body"])
        self.assertIn('"service":"bhf-web"', response["body"])

    def test_bible_books_route_returns_asv_books(self):
        response = asgi_request("GET", "/api/bible/books")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertEqual(data["books"][0]["name"], "Genesis")
        self.assertEqual(data["books"][-1]["name"], "Revelation")

    def test_bible_chapter_route_returns_verses(self):
        response = asgi_request("GET", "/api/bible/Romans/12")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertEqual(data["book"], "Romans")
        self.assertEqual(data["chapter"], 12)
        self.assertIn("living sacrifice", data["verses"][0]["text"])

    def test_bible_search_route_returns_local_results(self):
        response = asgi_request("GET", "/api/bible/search?q=living+sacrifice")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertGreater(data["total_results"], 0)
        self.assertEqual(data["results"][0]["reference"], "Romans 12:1")
        self.assertFalse(data["direct_reference"])

    def test_bible_search_route_flags_topic_fallback_for_no_hit(self):
        response = asgi_request("GET", "/api/bible/search?q=perichoresis+hypostasis+theosis")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertEqual(data["results"], [])
        self.assertTrue(data["ai_fallback_eligible"])

    def test_bible_search_route_resolves_direct_reference(self):
        response = asgi_request("GET", "/api/bible/search?q=John+1%3A1-2")

        self.assertEqual(response["status"], 200)
        data = json.loads(response["body"])
        self.assertTrue(data["direct_reference"])
        self.assertEqual(data["results"][0]["reference"], "John 1:1-2")

    def test_bible_search_fallback_job_returns_structured_candidates(self):
        data = _valid_form()
        data["query"] = "Egypt in Exodus"

        with patch("bhf_web.app.BHFAgent", SearchFallbackAgent):
            response = asgi_request("POST", "/api/bible/search/fallback/jobs", data=data)

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_search_job(job["job_id"])
        self.assertTrue(status["done"])

        result = asgi_request("GET", f"/api/bible/search/fallback/result/{job['job_id']}")
        self.assertEqual(result["status"], 200)
        payload = json.loads(result["body"])
        self.assertEqual(payload["source"], "ai_fallback")
        self.assertEqual(payload["results"][0]["reference"], "Exodus 1")
        self.assertEqual(payload["results"][1]["reference"], "Exodus 12:37-42")

    def test_post_ask_handles_mocked_agent_result(self):
        with patch("bhf_web.app.BHFAgent", FakeAgent):
            response = asgi_request("POST", "/ask", data=_valid_form())

        self.assertEqual(response["status"], 200)
        self.assertIn("Answer", response["body"])
        self.assertIn("Short Answer", response["body"])
        self.assertIn("Profile used", response["body"])
        self.assertIn("minimal-7b", response["body"])
        self.assertIn("Local knowledge used", response["body"])
        self.assertIn("ruach", response["body"])
        self.assertNotIn("local-secret", response["body"])

    def test_post_ask_invalid_config_returns_friendly_error(self):
        data = _valid_form()
        data["max_tokens"] = "0"

        response = asgi_request("POST", "/ask", data=data)

        self.assertEqual(response["status"], 400)
        self.assertIn("Could not ask BHF", response["body"])
        self.assertIn("max_tokens must be greater than 0", response["body"])

    def test_ask_job_reports_status_and_returns_result(self):
        with patch("bhf_web.app.BHFAgent", SuccessfulJobAgent):
            response = asgi_request("POST", "/ask/jobs", data=_valid_form())

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_job(job["job_id"])

        self.assertTrue(status["done"])
        self.assertIsNone(status["error"])
        self.assertEqual(status["stage"], "complete")
        self.assertIn("Waiting for model response", _history_messages(status))
        self.assertEqual(status["percent_complete"], 100.0)
        self.assertEqual(status["status"], "complete")
        self.assertIn("elapsed_total_seconds", status)
        self.assertTrue(
            all("step_index" in entry for entry in status["history"])
        )
        self.assertTrue(
            all("elapsed_current_stage_seconds" in entry for entry in status["history"])
        )

        result = asgi_request("GET", f"/ask/result/{job['job_id']}")
        self.assertEqual(result["status"], 200)
        self.assertIn("Short Answer", result["body"])
        self.assertIn("Metadata", result["body"])

    def test_reader_ask_job_builds_server_side_question(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "What should I observe before interpreting?",
                "reader_book": "Romans",
                "reader_chapter": "12",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "present your bodies a living sacrifice",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_job(job["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Romans 12:1-2")
        self.assertEqual(len(CapturingAgent.questions), 1)
        question = CapturingAgent.questions[0]
        self.assertIn("Using BHF, explain ASV Romans 12:1-2.", question)
        self.assertIn("Selected text (ASV Romans 12:1-2):", question)
        self.assertIn("Full chapter context (ASV Romans 12):", question)
        self.assertIn("observe the text before interpreting", question)

        result = asgi_request("GET", f"/ask/result/{job['job_id']}")
        self.assertEqual(result["status"], 200)
        self.assertIn("ASV Romans 12:1-2", result["body"])

    def test_ancient_context_reader_job_builds_phase_one_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "Genesis",
                "reader_chapter": "1",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "In the beginning God created the heavens and the earth.",
                "ask_mode": "ancient_context",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Genesis 1:1-2")
        question = CapturingAgent.questions[0]
        self.assertIn("explain the ancient context of ASV Genesis 1:1-2", question)
        self.assertIn("Ancient Near Eastern context", question)
        self.assertIn("original audience", question)
        self.assertIn("covenant setting", question)
        self.assertIn("certain from background that is probable", question)

    def test_literary_context_reader_job_builds_phase_one_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "Romans",
                "reader_chapter": "12",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "present your bodies a living sacrifice",
                "ask_mode": "literary_context",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Romans 12:1-2")
        question = CapturingAgent.questions[0]
        self.assertIn("explain the literary context of ASV Romans 12:1-2", question)
        self.assertIn("immediate paragraph, chapter, book, genre", question)
        self.assertIn("what comes before and after", question)
        self.assertIn("Avoid isolating the verse", question)
        self.assertIn("genre awareness", question)

    def test_cross_references_reader_job_builds_phase_two_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "John",
                "reader_chapter": "1",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "In the beginning was the Word",
                "ask_mode": "cross_references",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "John 1:1-2")
        question = CapturingAgent.questions[0]
        self.assertIn("give cross references for ASV John 1:1-2", question)
        self.assertIn("direct quotations", question)
        self.assertIn("strong references from possible references", question)
        self.assertIn("Do not dump a huge list", question)

    def test_related_ot_themes_reader_job_builds_phase_two_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "Romans",
                "reader_chapter": "12",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "present your bodies a living sacrifice",
                "ask_mode": "related_ot_themes",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Romans 12:1-2")
        question = CapturingAgent.questions[0]
        self.assertIn("identify related Old Testament themes", question)
        self.assertIn("covenant", question)
        self.assertIn("strong versus possible thematic links", question)
        self.assertIn("Avoid speculative connections", question)

    def test_fulfillment_nt_reader_job_builds_phase_three_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "Isaiah",
                "reader_chapter": "53",
                "reader_start_verse": "4",
                "reader_end_verse": "6",
                "reader_selected_text": "he was wounded for our transgressions",
                "ask_mode": "fulfillment_nt",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Isaiah 53:4-6")
        question = CapturingAgent.questions[0]
        self.assertIn("evaluate fulfillment in the NT for ASV Isaiah 53:4-6", question)
        self.assertIn("quoted, echoed, developed, fulfilled", question)
        self.assertIn("direct NT citation", question)
        self.assertIn("Avoid forcing Christological or prophetic readings", question)

    def test_compare_translations_reader_job_builds_phase_four_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "John",
                "reader_chapter": "1",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "In the beginning was the Word",
                "ask_mode": "compare_translations",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "John 1:1-2")
        question = CapturingAgent.questions[0]
        self.assertIn("compare the local public-domain translations for ASV John 1:1-2", question)
        self.assertIn("Available translations: ASV (American Standard Version), KJV (King James Version)", question)
        self.assertIn("Comparison data by verse", question)
        self.assertIn("- ASV:", question)
        self.assertIn("- KJV:", question)
        self.assertIn("Do not overstate the significance of minor wording differences", question)

    def test_timeline_reader_job_builds_phase_five_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "Exodus",
                "reader_chapter": "12",
                "reader_start_verse": "1",
                "reader_end_verse": "2",
                "reader_selected_text": "Speak ye unto all the congregation of Israel",
                "ask_mode": "timeline",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Exodus 12:1-2")
        question = CapturingAgent.questions[0]
        self.assertIn("place ASV Exodus 12:1-2 on the biblical timeline", question)
        self.assertIn("Broad period", question)
        self.assertIn("Prefer broad historical placement over fake precision", question)
        self.assertIn("If exact dating is uncertain, say so plainly", question)

    def test_maps_reader_job_builds_phase_six_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "Acts",
                "reader_chapter": "16",
                "reader_start_verse": "6",
                "reader_end_verse": "10",
                "reader_selected_text": "they were forbidden of the Holy Spirit to speak the word in Asia",
                "ask_mode": "maps",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        status = wait_for_job(json.loads(response["body"])["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "Acts 16:6-10")
        question = CapturingAgent.questions[0]
        self.assertIn("give geography notes for ASV Acts 16:6-10", question)
        self.assertIn("Broad region", question)
        self.assertIn("Do not invent locations if uncertain", question)
        self.assertIn("Keep this as a geography helper until real map data is added", question)

    def test_note_routes_create_update_delete_and_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "study.sqlite"
            with patch("bhf_web.app.STUDY_DB_PATH", db_path):
                create = asgi_request(
                    "POST",
                    "/api/notes",
                    json_data={
                        "book": "Rom",
                        "chapter": 12,
                        "start_verse": 1,
                        "end_verse": 2,
                        "selected_text": "living sacrifice",
                        "body": "Observation first.",
                    },
                )
                self.assertEqual(create["status"], 201)
                note = json.loads(create["body"])
                self.assertEqual(note["book"], "Romans")

                list_response = asgi_request("GET", "/api/notes/Romans/12")
                self.assertEqual(list_response["status"], 200)
                self.assertEqual(len(json.loads(list_response["body"])["notes"]), 1)

                update = asgi_request(
                    "PUT",
                    f"/api/notes/{note['id']}",
                    json_data={"body": "Updated observation."},
                )
                self.assertEqual(update["status"], 200)
                self.assertEqual(json.loads(update["body"])["body"], "Updated observation.")

                delete = asgi_request("DELETE", f"/api/notes/{note['id']}")
                self.assertEqual(delete["status"], 200)
                self.assertIn('"deleted":true', delete["body"])

                empty = asgi_request("GET", "/api/notes/Romans/12")
                self.assertEqual(json.loads(empty["body"])["notes"], [])

    def test_highlight_routes_create_delete_and_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "study.sqlite"
            with patch("bhf_web.app.STUDY_DB_PATH", db_path):
                create = asgi_request(
                    "POST",
                    "/api/highlights",
                    json_data={
                        "book": "Rom",
                        "chapter": 12,
                        "start_verse": 1,
                        "end_verse": 2,
                        "selected_text": "living sacrifice",
                        "color": "yellow",
                    },
                )
                self.assertEqual(create["status"], 201)
                highlight = json.loads(create["body"])
                self.assertEqual(highlight["book"], "Romans")
                self.assertEqual(highlight["color"], "yellow")

                list_response = asgi_request("GET", "/api/highlights/Romans/12")
                self.assertEqual(list_response["status"], 200)
                self.assertEqual(
                    len(json.loads(list_response["body"])["highlights"]),
                    1,
                )

                delete = asgi_request("DELETE", f"/api/highlights/{highlight['id']}")
                self.assertEqual(delete["status"], 200)
                self.assertIn('"deleted":true', delete["body"])

                empty = asgi_request("GET", "/api/highlights/Romans/12")
                self.assertEqual(json.loads(empty["body"])["highlights"], [])

    def test_saved_study_routes_create_list_open_and_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "study.sqlite"
            with patch("bhf_web.app.STUDY_DB_PATH", db_path), patch(
                "bhf_web.app.BHFAgent", SuccessfulJobAgent
            ):
                job_response = asgi_request(
                    "POST",
                    "/ask/jobs",
                    data={**_valid_form(), "ask_mode": "literary_context", "reader_book": "Romans", "reader_chapter": "12", "reader_start_verse": "1", "reader_end_verse": "2", "reader_selected_text": "present your bodies a living sacrifice"},
                )
                self.assertEqual(job_response["status"], 202)
                job_id = json.loads(job_response["body"])["job_id"]
                wait_for_job(job_id)

                save = asgi_request("POST", "/api/saved-studies", json_data={"job_id": job_id})
                self.assertEqual(save["status"], 201)
                study = json.loads(save["body"])
                self.assertEqual(study["book"], "Romans")
                self.assertEqual(study["study_type"], "literary_context")

                list_response = asgi_request("GET", "/api/saved-studies?book=Romans&chapter=12")
                self.assertEqual(list_response["status"], 200)
                studies = json.loads(list_response["body"])["saved_studies"]
                self.assertEqual(len(studies), 1)

                open_response = asgi_request("GET", f"/api/saved-studies/{study['id']}")
                self.assertEqual(open_response["status"], 200)
                self.assertIn("Saved study", open_response["body"])
                self.assertIn("Romans 12:1-2", open_response["body"])

                delete = asgi_request("DELETE", f"/api/saved-studies/{study['id']}")
                self.assertEqual(delete["status"], 200)
                self.assertIn('"deleted":true', delete["body"])

    def test_word_study_reader_job_builds_guarded_prompt(self):
        CapturingAgent.questions = []
        data = _valid_form()
        data.update(
            {
                "question": "",
                "reader_book": "John",
                "reader_chapter": "1",
                "reader_start_verse": "1",
                "reader_end_verse": "1",
                "reader_selected_text": "Word",
                "ask_mode": "word_study",
            }
        )

        with patch("bhf_web.app.BHFAgent", CapturingAgent):
            response = asgi_request("POST", "/ask/jobs", data=data)

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_job(job["job_id"])
        self.assertTrue(status["done"])
        self.assertEqual(status["reader_reference"], "John 1:1")
        question = CapturingAgent.questions[0]
        self.assertIn("selected word or phrase is from the ASV English text", question)
        self.assertIn("Do not claim exact Hebrew/Greek alignment", question)
        self.assertIn("Do not invent Strong's numbers", question)
        self.assertIn("actual lexicon/interlinear", question)
        self.assertIn("possible Greek terms", question)

    def test_ask_job_marks_previous_running_step_complete(self):
        job = AskJob(job_id="job-1")
        job.emit(status_event("queued", "Queued", 1, status="running"))
        job.emit(
            status_event(
                "loading_profile",
                "Loading BHF profile",
                6,
                status="running",
            )
        )

        self.assertEqual(job.history[0].status, "complete")
        self.assertEqual(job.history[1].status, "running")

    def test_ask_job_surfaces_agent_errors_with_failed_stage(self):
        with patch("bhf_web.app.BHFAgent", ErrorAgent):
            response = asgi_request("POST", "/ask/jobs", data=_valid_form())

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_job(job["job_id"])

        self.assertTrue(status["done"])
        self.assertIn("timed out", status["error"])
        self.assertEqual(status["failed_stage"], "waiting_for_model_response")
        self.assertEqual(status["status"], "error")

        result = asgi_request("GET", f"/ask/result/{job['job_id']}")
        self.assertEqual(result["status"], 502)
        self.assertIn("timed out", result["body"])
        self.assertIn("failed during waiting for model response", result["body"])


class FakeAgent:
    def __init__(self, config):
        self.config = config

    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(status_event("loading_profile", "Loading BHF profile", 6))
            status_callback(
                status_event(
                    "contacting_model_backend",
                    "Contacting model backend",
                    10,
                    status="running",
                )
            )
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(status_event("validating_response", "Validating response", 14))
            status_callback(status_event("formatting_answer", "Finalizing answer", 15))
            status_callback(status_event("complete", "Complete", 16, status="complete"))
        return fake_result(self.config, errors=["example adapter error"])


class ErrorAgent(FakeAgent):
    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(
                status_event(
                    "contacting_model_backend",
                    "Contacting model backend",
                    10,
                    status="running",
                )
            )
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(
                {
                    "stage": "error",
                    "message": "Model backend error",
                    "step_index": 11,
                    "total_steps": 16,
                    "percent_complete": 68.8,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "elapsed_total_seconds": 1.0,
                    "elapsed_current_stage_seconds": 0.5,
                    "status": "error",
                    "details": {
                        "failed_stage": "waiting_for_model_response",
                        "errors": ["OpenAI-compatible endpoint timed out: timed out"],
                    },
                }
            )
        return fake_result(
            self.config,
            errors=["OpenAI-compatible endpoint timed out: timed out"],
        )


class SuccessfulJobAgent(FakeAgent):
    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(status_event("loading_profile", "Loading BHF profile", 6))
            status_callback(
                status_event(
                    "contacting_model_backend",
                    "Contacting model backend",
                    10,
                    status="running",
                )
            )
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(status_event("complete", "Complete", 16, status="complete"))
        return fake_result(self.config, errors=[])


class CapturingAgent(SuccessfulJobAgent):
    questions = []

    def ask(self, question, status_callback=None):
        self.__class__.questions.append(question)
        return super().ask(question, status_callback=status_callback)


class SearchFallbackAgent(SuccessfulJobAgent):
    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(status_event("loading_profile", "Loading BHF profile", 6))
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(status_event("complete", "Complete", 16, status="complete"))
        return AgentResult(
            answer_text=json.dumps(
                {
                    "results": [
                        {
                            "book": "Exodus",
                            "chapter": 1,
                            "reason": "Egypt frames Israel's oppression at the start of Exodus.",
                            "confidence": "likely",
                        },
                        {
                            "book": "Exodus",
                            "chapter": 12,
                            "verse_start": 37,
                            "verse_end": 42,
                            "reason": "This passage narrates Israel leaving Egypt.",
                            "confidence": "strong",
                        },
                    ]
                }
            ),
            reference_context=ReferenceContext(
                book="Exodus",
                chapter=1,
                verse=None,
                testament="OT",
                is_reference_based=False,
                confidence=0.6,
            ),
            genre_context=GenreContext(primary_genre="narrative"),
            question_context=QuestionContext(question_type="topic_study", confidence=0.8),
            profile_used=self.config.profile,
            validation_result=ValidationResult(
                passed=True,
                score=90,
                warnings=[],
            ),
            model_metadata={
                "answer_mode": self.config.answer_mode,
            },
            errors=[],
        )


def status_event(stage, message, step_index, status="complete"):
    return {
        "stage": stage,
        "message": message,
        "step_index": step_index,
        "total_steps": 16,
        "percent_complete": round((step_index / 16) * 100, 1),
        "timestamp": "2026-01-01T00:00:00Z",
        "elapsed_total_seconds": float(step_index),
        "elapsed_current_stage_seconds": 0.25,
        "status": status,
    }


def fake_result(config, errors):
    return AgentResult(
        answer_text="## Short Answer\nAnswer with **method**.",
        reference_context=ReferenceContext(
            book="Romans",
            chapter=12,
            verse=1,
            testament="NT",
            is_reference_based=True,
            confidence=0.9,
        ),
        genre_context=GenreContext(primary_genre="epistle"),
        question_context=QuestionContext(question_type="context", confidence=0.8),
        profile_used=config.profile,
        validation_result=ValidationResult(
            passed=True,
            score=90,
            warnings=["example warning"],
        ),
        model_metadata={
            "answer_mode": config.answer_mode,
            "local_knowledge_keys": ["ruach"],
        },
        errors=errors,
    )


def _valid_form():
    return {
        "question": "What does Romans 12:1 mean?",
        "profile": "minimal-7b",
        "answer_mode": "study",
        "model": "local-model",
        "base_url": "http://localhost:1234/v1",
        "temperature": "0.3",
        "max_tokens": "1024",
        "timeout_seconds": "600",
        "show_method_notes": "on",
        "memory_max_turns": "8",
    }


def wait_for_job(job_id):
    for _attempt in range(20):
        response = asgi_request("GET", f"/ask/status/{job_id}")
        status = json.loads(response["body"])
        if status.get("done"):
            return status
        time.sleep(0.01)
    raise AssertionError(f"job did not complete: {job_id}")


def wait_for_search_job(job_id):
    for _attempt in range(20):
        response = asgi_request("GET", f"/api/bible/search/fallback/status/{job_id}")
        status = json.loads(response["body"])
        if status.get("done"):
            return status
        time.sleep(0.01)
    raise AssertionError(f"search job did not complete: {job_id}")


def _history_messages(status):
    return [entry["message"] for entry in status["history"]]


def asgi_request(method, path, data=None, json_data=None):
    assert app is not None
    return asyncio.run(_asgi_request(method, path, data, json_data))


async def _asgi_request(method, path, data=None, json_data=None):
    if "?" in path:
        path, query_string = path.split("?", 1)
    else:
        query_string = ""
    if json_data is not None:
        body = json.dumps(json_data).encode("utf-8")
        content_type = b"application/json"
    else:
        body = urlencode(data or {}).encode("utf-8")
        content_type = b"application/x-www-form-urlencoded"
    headers = [(b"host", b"testserver")]
    if body:
        headers.extend(
            [
                (b"content-type", content_type),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string.encode("ascii"),
        "headers": headers,
        "client": ("127.0.0.1", 123),
        "server": ("testserver", 80),
    }
    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(0)
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    status = next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )
    chunks = [
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    ]
    return {
        "status": status,
        "body": b"".join(chunks).decode("utf-8"),
    }


if __name__ == "__main__":
    unittest.main()
