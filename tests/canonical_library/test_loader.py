from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalLibrary, CanonicalRelationship, CanonicalSource, CanonicalValidationError

from .helpers import make_object, write_library


class CanonicalLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.default_library = CanonicalLibrary.load_default()

    def test_loads_all_objects(self) -> None:
        library = self.default_library
        expected_categories = {
            "theology": 50,
            "themes": 50,
            "people": 101,
            "places": 75,
            "events": 76,
            "books": 66,
            "word_studies": 50,
            "archaeology": 50,
            "institutions": 34,
            "prophecy": 10,
            "faq": 51,
            "timeline": 1,
            "covenants": 1,
            "biblical_theology": 1,
            "cultural_background": 22,
            "symbols": 1,
            "literary_devices": 1,
            "doctrine": 1,
        }

        self.assertEqual(len(library.objects_by_id), 641)
        self.assertEqual(library.manifest["object_count"], 641)
        self.assertEqual(library.manifest["framework_version"], "1.0")
        self.assertEqual(library.manifest["schema_version"], "1.0")
        self.assertEqual(library.manifest["categories"], expected_categories)

    def test_loaded_complete_objects_preserve_governance_metadata(self) -> None:
        library = self.default_library
        abraham = library.objects_by_id["abraham"]

        self.assertEqual(abraham.content_status, "complete")
        self.assertEqual(abraham.review_status, "in_review")
        self.assertEqual(abraham.generated_by[0].type, "ai")
        self.assertEqual(abraham.generated_by[0].name, "codex")
        self.assertEqual(abraham.generated_by[0].workflow, "ane-hebraic-context-expansion")
        self.assertEqual(abraham.reviewed_by, [])
        self.assertEqual(abraham.last_reviewed, "2026-07-14")
        self.assertEqual(abraham.confidence, "medium")
        self.assertTrue(abraham.human_review_required)

    def test_loads_recursively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object("abraham", "person", "Abraham", ["who is abraham"]),
                    make_object("shechem", "place", "Shechem", ["where is shechem"]),
                ],
                path_overrides={
                    "abraham": "objects/people/nested/abraham.json",
                    "shechem": "objects/places/region/shechem.json",
                },
            )

            library = CanonicalLibrary(root=root).load()

        self.assertIn("abraham", library.objects_by_id)
        self.assertIn("shechem", library.objects_by_id)
        self.assertEqual(library.objects_by_id["abraham"].title, "Abraham")
        self.assertEqual(library.objects_by_id["shechem"].title, "Shechem")

    def test_loads_related_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object("abraham", "person", "Abraham", ["who is abraham"]),
                    make_object(
                        "shechem",
                        "place",
                        "Shechem",
                        ["where is shechem"],
                        related_objects=[
                            {
                                "id": "abraham",
                                "relationship": "associated-person",
                                "weight": 5,
                                "notes": "patriarch",
                            }
                        ],
                    ),
                ],
            )

            library = CanonicalLibrary(root=root).load()

        self.assertIsInstance(library.objects_by_id["shechem"].related_objects[0], CanonicalRelationship)
        self.assertEqual(library.objects_by_id["shechem"].related_objects[0].id, "abraham")
        self.assertEqual(library.objects_by_id["shechem"].related_objects[0].relationship, "associated-person")
        self.assertEqual(library.objects_by_id["shechem"].related_objects[0].weight, 5)
        self.assertEqual(library.objects_by_id["shechem"].related_objects[0].notes, "patriarch")

    def test_loads_legacy_string_sources_as_structured_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "shechem",
                        "place",
                        "Shechem",
                        ["where is shechem"],
                        sources=["Westermann, Genesis"],
                    ),
                ],
            )

            library = CanonicalLibrary(root=root).load()

        self.assertIsInstance(library.objects_by_id["shechem"].sources[0], CanonicalSource)
        self.assertEqual(library.objects_by_id["shechem"].sources[0].title, "Westermann, Genesis")
        self.assertEqual(library.objects_by_id["shechem"].sources[0].source_type, "reference-work")

    def test_builds_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "covenant-theme",
                        "theme",
                        "Covenant Theme",
                        ["covenant motif"],
                    ),
                ],
            )

            library = CanonicalLibrary(root=root).load()

        self.assertIn("covenant motif", library.objects_by_alias)
        self.assertEqual(library.objects_by_alias["covenant motif"], ["covenant-theme"])
        self.assertEqual(library.objects_by_type["theme"], ["covenant-theme"])
        self.assertIn("covenant", library.keyword_index)
        self.assertIn("covenant-theme", library.keyword_index["covenant"])
        self.assertIn("title", library.field_keyword_index["covenant-theme"])
        self.assertIn("aliases", library.field_keyword_index["covenant-theme"])
        self.assertIn("covenant", library.field_keyword_index["covenant-theme"]["title"])
        self.assertIn("covenant", library.field_keyword_index["covenant-theme"]["aliases"])

    def test_retrieves_objects_by_scripture_reference(self) -> None:
        results = self.default_library.retrieve_by_scripture_reference("Joshua 24", limit=5)

        self.assertGreaterEqual(len(results), 3)
        self.assertEqual(results[0].object.id, "shechem")
        self.assertEqual(results[0].match_type, "scripture")
        self.assertIn("scripture_references", results[0].matched_fields)
        self.assertTrue(
            {result.object.id for result in results}.issuperset(
                {"shechem", "joshua-son-of-nun", "joshua"}
            )
        )

    def test_traces_relationship_graph_from_seed_object(self) -> None:
        graph = self.default_library.trace_relationship_graph("Shechem", max_depth=1, limit=4)
        retrieved_ids = [item["id"] for item in graph["retrieved_topics"]]

        self.assertEqual(graph["seed_ids"], ["shechem"])
        self.assertEqual(retrieved_ids[0], "shechem")
        self.assertEqual(len(retrieved_ids), 4)
        self.assertTrue(
            set(retrieved_ids[1:]).issuperset({"abraham", "joshua-son-of-nun", "covenant-theme"})
        )
        self.assertEqual(graph["retrieved_topics"][1]["relationship_depth"], 1)

    def test_audit_bidirectional_relationships_reports_missing_reverse_links(self) -> None:
        issues = self.default_library.audit_bidirectional_relationships(limit=2000)

        self.assertTrue(
            any(
                issue["source_id"] == "1-samuel" and issue["target_id"] == "david"
                for issue in issues
            )
        )
        self.assertTrue(
            any(
                issue["source_id"] == "1-kings" and issue["target_id"] == "solomon"
                for issue in issues
            )
        )

    def test_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object("shechem", "place", "Shechem", ["where is shechem"]),
                    make_object("shechem", "theme", "Shechem Theme", ["shechem theme"]),
                ],
            )

            with self.assertRaisesRegex(CanonicalValidationError, "duplicate canonical id"):
                CanonicalLibrary(root=root).load()

    def test_rejects_missing_related_object_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "shechem",
                        "place",
                        "Shechem",
                        ["where is shechem"],
                        related_objects=[
                            {
                                "id": "abraham",
                                "relationship": "associated-person",
                                "weight": 5,
                                "notes": "",
                            }
                        ],
                    )
                ],
            )

            with self.assertRaisesRegex(CanonicalValidationError, 'references unknown canonical id "abraham"'):
                CanonicalLibrary(root=root).load()

    def test_detects_alias_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object("abraham", "person", "Abraham", ["shared alias"]),
                    make_object("isaac", "person", "Isaac", ["shared alias"]),
                ],
            )

            with self.assertRaisesRegex(CanonicalValidationError, "alias collision"):
                CanonicalLibrary(root=root).load()

    def test_does_not_repeatedly_read_files_after_loading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [make_object("alpha", "person", "Alpha", ["who is alpha"])],
            )
            library = CanonicalLibrary(root=root).load()

            shutil.rmtree(root / "objects")
            result = library.retrieve_exact("Alpha")

        self.assertIsNotNone(result)

    def test_inventory_fingerprint_is_stable_for_unchanged_library(self) -> None:
        library = self.default_library

        self.assertEqual(library.inventory_fingerprint(), library.inventory_fingerprint())

    def test_inventory_fingerprint_changes_when_object_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [make_object("alpha", "person", "Alpha", ["who is alpha"], summary="first")],
            )
            original = CanonicalLibrary(root=root).load().inventory_fingerprint()

            alpha_path = root / "objects" / "people" / "alpha.json"
            alpha_data = json.loads(alpha_path.read_text(encoding="utf-8"))
            alpha_data["summary"] = "changed"
            alpha_path.write_text(
                json.dumps(alpha_data, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            updated = CanonicalLibrary(root=root).load().inventory_fingerprint()

        self.assertNotEqual(original, updated)


if __name__ == "__main__":
    unittest.main()
