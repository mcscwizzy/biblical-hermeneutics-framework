import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from bhf_agent.study_db import (
    StudyDataError,
    create_highlight,
    create_note,
    create_map_note,
    create_saved_map_study,
    create_saved_study,
    get_biblical_place,
    get_archaeology_item,
    get_archaeology_site,
    get_manuscript_item,
    get_saved_map_study,
    delete_highlight,
    delete_note,
    delete_saved_map_study,
    delete_saved_study,
    initialize_database,
    get_saved_study,
    list_archaeology_items,
    list_archaeology_scripture_links,
    list_archaeology_sites,
    list_highlights,
    list_biblical_places,
    list_historical_layers,
    list_map_routes,
    list_political_context_layers,
    list_map_notes,
    list_manuscript_items,
    list_manuscript_scripture_links,
    list_place_references,
    list_route_references,
    list_notes,
    list_saved_map_studies,
    list_saved_studies,
    update_note,
)
from bhf_web.map_service import (
    resolve_archaeology_for_passage,
    resolve_places_for_passage,
    resolve_political_context_for_passage,
    resolve_manuscripts_for_passage,
    get_related_passages_for_place,
)


class StudyDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "study.sqlite"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_database_initializes_schema_version(self):
        initialize_database(path=self.path)

        with sqlite3.connect(self.path) as connection:
            versions = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]

        self.assertEqual(versions, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])

        with sqlite3.connect(self.path) as connection:
            saved_studies = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'saved_studies'
                """
            ).fetchone()

        self.assertIsNotNone(saved_studies)

        with sqlite3.connect(self.path) as connection:
            biblical_places = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'biblical_places'
                """
            ).fetchone()

        self.assertIsNotNone(biblical_places)

    def test_v1_database_migrates_to_saved_studies(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (1, '2026-01-01T00:00:00Z')"
            )

        initialize_database(path=self.path)

        with sqlite3.connect(self.path) as connection:
            versions = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]
            saved_studies = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'saved_studies'
                """
            ).fetchone()

        self.assertEqual(versions, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
        self.assertIsNotNone(saved_studies)

    def test_biblical_places_seed_and_references_load_from_database(self):
        initialize_database(path=self.path)

        places = list_biblical_places(path=self.path)
        self.assertGreaterEqual(len(places), 1000)
        jerusalem = next(place for place in places if place["id"] == "jerusalem")
        self.assertIn("Zion", jerusalem["aliases"])
        self.assertEqual(jerusalem["confidence"], "strong")
        self.assertIn("NT / Roman period", jerusalem["periods"])
        self.assertIsNotNone(jerusalem["latitude"])
        self.assertIsNotNone(jerusalem["longitude"])

        roman_places = list_biblical_places(period="NT / Roman period", path=self.path)
        self.assertIn("capernaum", {place["id"] for place in roman_places})
        self.assertIn("jerusalem", {place["id"] for place in roman_places})
        self.assertIn("openbible-af5884f", {place["id"] for place in roman_places})

        nazareth = next(place for place in places if place["id"] == "openbible-af5884f")
        self.assertEqual(nazareth["name"], "Nazareth")
        self.assertEqual(nazareth["source_name"], "OpenBible.info Bible Geocoding Data")
        self.assertEqual(nazareth["license"], "CC-BY-4.0")
        self.assertIsNotNone(nazareth["latitude"])
        self.assertIsNotNone(nazareth["longitude"])

        related = get_related_passages_for_place("jerusalem", path=self.path)
        self.assertEqual(related["place_id"], "jerusalem")
        self.assertGreaterEqual(related["count"], 4)
        direct_group = next(group for group in related["groups"] if group["group_type"] == "directly_mentioned")
        self.assertEqual(direct_group["count"], 2)
        self.assertEqual(
            [group["count"] for group in direct_group["testament_groups"]],
            [1, 1],
        )
        self.assertTrue(
            any(group["group_type"] == "same_route" for group in related["groups"])
        )
        self.assertTrue(
            any(group["group_type"] == "same_empire_period" for group in related["groups"])
        )

        references = list_place_references("jerusalem", path=self.path)
        self.assertGreaterEqual(len(references), 2)
        self.assertEqual(references[0]["place_id"], "jerusalem")
        self.assertEqual(references[0]["relationship_type"], "directly_named")

        fetched = get_biblical_place("jerusalem", path=self.path)
        self.assertEqual(fetched["name"], "Jerusalem")
        self.assertIn("approximate", fetched["notes"].lower())

        routes = list_map_routes(path=self.path)
        self.assertGreaterEqual(len(routes), 1)
        route = next(route for route in routes if route["id"] == "pauls-first-missionary-journey")
        self.assertEqual(route["confidence"], "likely")
        self.assertEqual(route["geojson"]["geometry"]["type"], "LineString")
        self.assertIn("NT / Roman period", route["periods"])

        roman_routes = list_map_routes(period="NT / Roman period", path=self.path)
        self.assertEqual([route["id"] for route in roman_routes], ["pauls-first-missionary-journey"])

        route_refs = list_route_references("pauls-first-missionary-journey", path=self.path)
        self.assertGreaterEqual(len(route_refs), 2)
        self.assertEqual(route_refs[0]["route_id"], "pauls-first-missionary-journey")

        layers = list_historical_layers(path=self.path)
        self.assertGreaterEqual(len(layers), 4)
        divided_kingdom = next(layer for layer in layers if layer["id"] == "divided-kingdom-israel")
        self.assertEqual(divided_kingdom["period"], "Divided Kingdom")
        self.assertIn("Divided Kingdom", divided_kingdom["periods"])
        self.assertEqual(divided_kingdom["geojson"]["geometry"]["type"], "Polygon")
        self.assertIn("schematic", divided_kingdom["notes"].lower())

        roman_layers = list_historical_layers(period="NT / Roman period", path=self.path)
        self.assertEqual([layer["id"] for layer in roman_layers], ["roman-judea-galilee"])

    def test_political_context_seed_and_passage_resolution_load_from_database(self):
        initialize_database(path=self.path)

        layers = list_political_context_layers(path=self.path)
        self.assertGreaterEqual(len(layers), 8)
        assyria = next(layer for layer in layers if layer["id"] == "assyria")
        self.assertEqual(assyria["name"], "Assyria")
        self.assertIn("Assyrian period", assyria["periods"])
        self.assertGreaterEqual(assyria["reference_count"], 1)

        roman_layers = list_political_context_layers(period="NT / Roman period", path=self.path)
        self.assertIn("rome", {layer["id"] for layer in roman_layers})

        resolved = resolve_political_context_for_passage(
            book="John",
            chapter=19,
            verse_start=1,
            verse_end=16,
            passage_text="Then they led Jesus to Pilate.",
            period="NT / Roman period",
            path=self.path,
        )
        self.assertFalse(resolved["empty_state"])
        self.assertIn("rome", resolved["matched_political_context_ids"])
        self.assertIn("scripture_links", resolved["layers"][0])

    def test_archaeology_seed_and_passage_resolution_load_from_database(self):
        initialize_database(path=self.path)

        sites = list_archaeology_sites(path=self.path)
        self.assertGreaterEqual(len(sites), 5)
        for site in sites:
            self.assertTrue(site["source_id"])
            self.assertIsInstance(site["source"], dict)
            self.assertEqual(site["source"]["id"], site["source_id"])
        jerusalem_site = next(site for site in sites if site["id"] == "hezekiahs-tunnel")
        self.assertEqual(jerusalem_site["name"], "Hezekiah's Tunnel")
        self.assertGreaterEqual(jerusalem_site["reference_count"], 1)
        self.assertIn("Assyrian period", jerusalem_site["periods"])

        roman_sites = list_archaeology_sites(period="NT / Roman period", path=self.path)
        self.assertIn("caesarea-maritima", {site["id"] for site in roman_sites})

        items = list_archaeology_items(path=self.path)
        self.assertGreaterEqual(len(items), 8)
        for item in items:
            self.assertTrue(item["source_id"])
            self.assertIsInstance(item["source"], dict)
            self.assertEqual(item["source"]["id"], item["source_id"])
        pilate = next(item for item in items if item["id"] == "pilate-stone")
        self.assertEqual(pilate["item_type"], "dedication inscription")
        self.assertIn("NT / Roman period", pilate["periods"])
        self.assertGreaterEqual(pilate["reference_count"], 1)

        roman_items = list_archaeology_items(period="NT / Roman period", path=self.path)
        self.assertIn("pilate-stone", {item["id"] for item in roman_items})

        links = list_archaeology_scripture_links("pilate-stone", path=self.path)
        self.assertGreaterEqual(len(links), 2)
        self.assertEqual(links[0]["item_id"], "pilate-stone")

        resolved = resolve_archaeology_for_passage(
            book="John",
            chapter=9,
            verse_start=7,
            verse_end=11,
            passage_text="Then he sent him away to the pool of Siloam.",
            period="NT / Roman period",
            path=self.path,
        )
        self.assertFalse(resolved["empty_state"])
        self.assertIn("pool-of-siloam", resolved["matched_archaeology_ids"])
        self.assertIn("scripture_links", resolved["markers"][0])

        routes = list_map_routes(path=self.path)
        self.assertGreaterEqual(len(routes), 1)
        for route in routes:
            self.assertIn(route["geojson"]["geometry"]["type"], {"LineString", "MultiLineString"})
            self.assertTrue(route["source_id"])

    def test_manuscript_seed_and_passage_resolution_load_from_database(self):
        initialize_database(path=self.path)

        items = list_manuscript_items(path=self.path)
        self.assertGreaterEqual(len(items), 4)
        sinaiticus = next(item for item in items if item["id"] == "codex-sinaiticus")
        self.assertEqual(sinaiticus["manuscript_type"], "codex")
        self.assertEqual(sinaiticus["confidence"], "strong")
        self.assertIn("NT / Roman period", sinaiticus["periods"])
        self.assertIn("John", sinaiticus["related_books"])
        self.assertEqual(get_manuscript_item("codex-sinaiticus", path=self.path)["name"], "Codex Sinaiticus")

        roman_items = list_manuscript_items(period="NT / Roman period", path=self.path)
        self.assertIn("codex-sinaiticus", {item["id"] for item in roman_items})

        links = list_manuscript_scripture_links("codex-sinaiticus", path=self.path)
        self.assertGreaterEqual(len(links), 1)
        self.assertEqual(links[0]["item_id"], "codex-sinaiticus")

        resolved = resolve_manuscripts_for_passage(
            book="John",
            chapter=1,
            verse_start=1,
            verse_end=18,
            passage_text="In the beginning was the Word.",
            period="NT / Roman period",
            path=self.path,
        )
        self.assertFalse(resolved["empty_state"])
        self.assertIn("codex-sinaiticus", resolved["matched_manuscript_ids"])
        self.assertIn("scripture_links", resolved["markers"][0])

    def test_biblical_place_with_missing_coordinates_is_returned_cleanly(self):
        initialize_database(path=self.path)

        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO biblical_places (
                    id, name, aliases, latitude, longitude, modern_location,
                    ancient_region, description, confidence, confidence_rank,
                    source_name, source_url, license, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "unknown-site",
                    "Unknown Site",
                    "[]",
                    None,
                    None,
                    "",
                    "Unknown",
                    "A site with uncertain coordinates.",
                    "possible",
                    2,
                    "test",
                    "",
                    "test license",
                    "",
                ),
            )

        place = get_biblical_place("unknown-site", path=self.path)
        self.assertIsNone(place["latitude"])
        self.assertIsNone(place["longitude"])

    def test_resolve_places_for_passage_matches_aliases_and_falls_back_to_references(self):
        initialize_database(path=self.path)

        alias_result = resolve_places_for_passage(
            passage_text="And they went up to Beth-lehem and spoke of Jerusalem.",
            path=self.path,
        )
        self.assertFalse(alias_result["empty_state"])
        self.assertIn("bethlehem", alias_result["matched_place_ids"])
        self.assertIn("jerusalem", alias_result["matched_place_ids"])
        self.assertIn("Beth-lehem", alias_result["matched_terms"]["bethlehem"])

        fallback_result = resolve_places_for_passage(
            book="Acts",
            chapter=10,
            verse_start=1,
            verse_end=48,
            passage_text="Cornelius is described in the passage without naming the city.",
            path=self.path,
        )
        self.assertIn("caesarea-maritima", fallback_result["matched_place_ids"])
        self.assertFalse(fallback_result["empty_state"])

        empty_result = resolve_places_for_passage(
            passage_text="A passage without any curated location names.",
            path=self.path,
        )
        self.assertTrue(empty_result["empty_state"])
        self.assertEqual(empty_result["markers"], [])

    def test_resolve_places_for_passage_ignores_period_filter_for_direct_passage_matching(self):
        initialize_database(path=self.path)

        result = resolve_places_for_passage(
            book="Acts",
            chapter=10,
            verse_start=1,
            verse_end=48,
            passage_text="Cornelius is described in the passage without naming the city.",
            period="Assyrian period",
            path=self.path,
        )

        self.assertFalse(result["empty_state"])
        self.assertIn("caesarea-maritima", result["matched_place_ids"])

    def test_resolve_routes_for_passage_matches_references(self):
        from bhf_web.map_service import get_map_routes_for_passage

        initialize_database(path=self.path)

        route_result = get_map_routes_for_passage(
            book="Acts",
            chapter=13,
            verse_start=1,
            verse_end=52,
            passage_text="The church in Antioch sent them out.",
            path=self.path,
        )
        self.assertFalse(route_result["empty_state"])
        self.assertIn("pauls-first-missionary-journey", route_result["matched_route_ids"])
        self.assertGreaterEqual(route_result["routes"][0]["reference_count"], 2)

        empty_routes = get_map_routes_for_passage(
            passage_text="No curated route here.",
            path=self.path,
        )
        self.assertTrue(empty_routes["empty_state"])
        self.assertEqual(empty_routes["routes"], [])

    def test_create_reload_and_filter_notes(self):
        note = create_note(_note_data(), path=self.path)

        self.assertTrue(note["id"])
        self.assertEqual(note["book"], "Romans")
        self.assertEqual(note["chapter"], 12)
        self.assertEqual(note["created_at"], note["updated_at"])
        self.assertEqual(list_notes("Romans", 12, path=self.path), [note])
        self.assertEqual(list_notes("John", 1, path=self.path), [])

    def test_update_preserves_created_at_and_changes_updated_at(self):
        note = create_note(_note_data(), path=self.path)
        time.sleep(0.001)

        updated = update_note(note["id"], {"body": "Updated note"}, path=self.path)

        self.assertEqual(updated["id"], note["id"])
        self.assertEqual(updated["created_at"], note["created_at"])
        self.assertNotEqual(updated["updated_at"], note["updated_at"])
        self.assertEqual(updated["body"], "Updated note")

    def test_delete_note(self):
        note = create_note(_note_data(), path=self.path)

        self.assertTrue(delete_note(note["id"], path=self.path))
        self.assertEqual(list_notes(path=self.path), [])

    def test_highlights_persist_and_filter(self):
        highlight = create_highlight(_highlight_data(), path=self.path)

        self.assertEqual(highlight["color"], "yellow")
        self.assertEqual(list_highlights("Romans", 12, path=self.path), [highlight])
        self.assertEqual(list_highlights("John", 1, path=self.path), [])

    def test_delete_highlight(self):
        highlight = create_highlight(_highlight_data(), path=self.path)

        self.assertTrue(delete_highlight(highlight["id"], path=self.path))
        self.assertEqual(list_highlights(path=self.path), [])

    def test_invalid_note_input_raises_clear_error(self):
        with self.assertRaisesRegex(StudyDataError, "note body is required"):
            create_note({**_note_data(), "body": " "}, path=self.path)

    def test_invalid_highlight_color_raises_clear_error(self):
        with self.assertRaisesRegex(StudyDataError, "highlight color must be one of"):
            create_highlight({**_highlight_data(), "color": "orange"}, path=self.path)

    def test_json_notes_file_is_not_imported(self):
        json_path = Path(self.tmpdir.name) / "notes.json"
        json_path.write_text(json.dumps([_stored_json_note()]), encoding="utf-8")

        self.assertEqual(list_notes("Romans", 12, path=self.path), [])

    def test_create_reload_and_delete_saved_study(self):
        study = create_saved_study(_saved_study_data(), path=self.path)

        self.assertTrue(study["id"])
        self.assertEqual(study["book"], "Romans")
        self.assertEqual(study["chapter"], 12)
        self.assertEqual(study["study_type"], "literary_context")
        self.assertEqual(list_saved_studies("Romans", 12, path=self.path), [study])

        fetched = get_saved_study(study["id"], path=self.path)
        self.assertEqual(fetched, study)

        self.assertTrue(delete_saved_study(study["id"], path=self.path))
        self.assertEqual(list_saved_studies(path=self.path), [])

    def test_saved_study_defaults_title(self):
        study = create_saved_study(
            {
                **_saved_study_data(),
                "title": " ",
            },
            path=self.path,
        )

        self.assertEqual(study["title"], "Romans 12:1-2 - Literary Context")

    def test_saved_study_requires_answer(self):
        with self.assertRaisesRegex(StudyDataError, "answer is required"):
            create_saved_study(
                {**_saved_study_data(), "answer": " "},
                path=self.path,
            )

    def test_create_reload_and_delete_saved_map_study(self):
        initialize_database(path=self.path)

        study = create_saved_map_study(
                {
                    "book": "Romans",
                    "chapter": 12,
                    "start_verse": 1,
                    "end_verse": 2,
                    "passage_reference": "Romans 12:1-2",
                    "selected_place_id": "jerusalem",
                    "selected_archaeology_id": "pilate-stone",
                    "selected_manuscript_id": "codex-sinaiticus",
                    "selected_layers": ["roman-judea-galilee"],
                    "map_view_state": {"center": [31.78, 35.23], "zoom": 8, "routeVisibility": True},
                    "generated_summary": "Jerusalem study overlay.",
                    "user_notes": "Focus on the temple setting.",
                },
            path=self.path,
        )

        self.assertTrue(study["id"])
        self.assertEqual(study["selected_place_id"], "jerusalem")
        self.assertEqual(study["selected_archaeology_id"], "pilate-stone")
        self.assertEqual(study["selected_manuscript_id"], "codex-sinaiticus")
        self.assertEqual(study["selected_layers"], ["roman-judea-galilee"])

        fetched = get_saved_map_study(study["id"], path=self.path)
        self.assertEqual(fetched["generated_summary"], "Jerusalem study overlay.")
        self.assertEqual(fetched["map_view_state"]["zoom"], 8)

        studies = list_saved_map_studies("Romans", 12, path=self.path)
        self.assertEqual(len(studies), 1)
        self.assertEqual(studies[0]["id"], study["id"])

        self.assertTrue(delete_saved_map_study(study["id"], path=self.path))
        self.assertEqual(list_saved_map_studies(path=self.path), [])

    def test_create_map_note_rejects_missing_target(self):
        initialize_database(path=self.path)

        with self.assertRaisesRegex(StudyDataError, "select a place, route, historical layer, archaeology item, or manuscript"):
            create_map_note(
                {
                    "book": "Romans",
                    "chapter": 12,
                    "start_verse": 1,
                    "end_verse": 2,
                    "note_body": "Interesting geography",
                },
                path=self.path,
            )

    def test_create_map_note_and_list_by_target(self):
        initialize_database(path=self.path)

        note = create_map_note(
            {
                "book": "Romans",
                "chapter": 12,
                "start_verse": 1,
                "end_verse": 2,
                "passage_reference": "Romans 12:1-2",
                "place_id": "jerusalem",
                "archaeology_id": "pilate-stone",
                "note_body": "Tie this to the temple backdrop.",
            },
            path=self.path,
        )

        self.assertTrue(note["id"])
        self.assertEqual(note["place_id"], "jerusalem")
        self.assertEqual(note["archaeology_id"], "pilate-stone")
        self.assertEqual(list_map_notes(place_id="jerusalem", path=self.path)[0]["id"], note["id"])

    def test_create_map_note_accepts_manuscript_target(self):
        initialize_database(path=self.path)

        note = create_map_note(
            {
                "book": "John",
                "chapter": 1,
                "start_verse": 1,
                "end_verse": 18,
                "passage_reference": "John 1:1-18",
                "manuscript_id": "codex-sinaiticus",
                "note_body": "Track the textual witness here.",
            },
            path=self.path,
        )

        self.assertTrue(note["id"])
        self.assertEqual(note["manuscript_id"], "codex-sinaiticus")
        self.assertEqual(list_map_notes(manuscript_id="codex-sinaiticus", path=self.path)[0]["id"], note["id"])


def _note_data():
    return {
        "book": "Rom",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "I beseech you therefore...",
        "body": "Observe the appeal before application.",
    }


def _highlight_data():
    return {
        "book": "Rom",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "living sacrifice",
        "color": "yellow",
    }


def _stored_json_note():
    return {
        "id": "note-1",
        "book": "Romans",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "text",
        "body": "Stored note",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _saved_study_data():
    return {
        "book": "Rom",
        "chapter": 12,
        "start_verse": 1,
        "end_verse": 2,
        "selected_text": "present your bodies a living sacrifice",
        "study_type": "literary_context",
        "question": "Using BHF, explain the literary context of ASV Romans 12:1-2.",
        "answer": "## Short Answer\nObserve the flow before interpretation.",
        "title": "Romans 12:1-2 - Literary Context",
    }


if __name__ == "__main__":
    unittest.main()
