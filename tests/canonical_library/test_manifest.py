from __future__ import annotations

import ast
import json
import unittest
from collections import Counter
from pathlib import Path

from bhf_agent.references import BOOKS
from framework.canonical_library import CATEGORY_FOLDERS, CanonicalLibrary, normalize_id, validate_object


REPO_ROOT = Path(__file__).resolve().parents[2]
CKL_ROOT = REPO_ROOT / "framework" / "canonical_library"
OBJECTS_ROOT = CKL_ROOT / "objects"
MANIFEST_PATH = CKL_ROOT / "manifest.json"
EXPECTED_FOLDERS = set(CATEGORY_FOLDERS.values())
EXPECTED_EMPTY_STRING_FIELDS = (
    "summary",
    "historical_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "later_christian_reception",
    "literary_context",
    "covenantal_significance",
)
EXPECTED_EMPTY_LIST_FIELDS = (
    "intertextuality",
    "timeline",
    "maps",
    "archaeology",
    "hebrew_words",
    "greek_words",
    "related_people",
    "related_places",
    "related_events",
    "cross_references",
    "new_testament_connections",
    "interpretive_notes",
    "common_questions",
    "sources",
    "scripture_references",
    "reviewed_by",
    "related_objects",
)
EXPECTED_GOVERNANCE_VALUES = {
    "content_status": "placeholder",
    "review_status": "unreviewed",
    "last_reviewed": None,
    "confidence": "unrated",
}
EXPECTED_CONTEXT_APPLICABILITY = {
    "historical": True,
    "ancient_near_east": True,
    "hebraic_worldview": True,
    "second_temple": True,
    "canonical": True,
    "later_christian_reception": True,
}
AI_IMPORT_PREFIXES = {
    "anthropic",
    "chromadb",
    "faiss",
    "langchain",
    "llama_index",
    "openai",
    "sentence_transformers",
    "tensorflow",
    "torch",
    "transformers",
}


class CanonicalInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = CanonicalLibrary.load_default()

    def test_all_inventory_json_files_validate_and_receive_governance_defaults(self) -> None:
        seen_ids: set[str] = set()
        counts: Counter[str] = Counter()

        for path in sorted(OBJECTS_ROOT.rglob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            obj = validate_object(data, path=path.relative_to(CKL_ROOT).as_posix())

            self.assertNotIn(obj.id, seen_ids)
            seen_ids.add(obj.id)
            self.assertEqual(path.stem, obj.id)
            self.assertIn(path.parent.name, EXPECTED_FOLDERS)
            self.assertEqual(obj.framework_version, "1.0")
            self.assertEqual(obj.object_version, "1")
            if obj.content_status == "placeholder":
                self.assertEqual(obj.importance, 0)

                for field_name in EXPECTED_EMPTY_STRING_FIELDS:
                    self.assertEqual(getattr(obj, field_name), "")
                for field_name in EXPECTED_EMPTY_LIST_FIELDS:
                    self.assertEqual(getattr(obj, field_name), [])
                for field_name, expected in EXPECTED_GOVERNANCE_VALUES.items():
                    self.assertEqual(getattr(obj, field_name), expected)
                self.assertEqual(obj.context_applicability, EXPECTED_CONTEXT_APPLICABILITY)
            elif obj.content_status == "complete":
                self.assertGreater(obj.importance, 0)
                self.assertNotEqual(obj.summary, "")
                self.assertNotEqual(obj.sources, [])
                self.assertNotEqual(obj.scripture_references, [])
                self.assertNotEqual(obj.review_status, "unreviewed")
                self.assertGreaterEqual(len(obj.reviewed_by), 1)
                self.assertIsNotNone(obj.last_reviewed)
                self.assertNotEqual(obj.confidence, "unrated")
            else:
                self.fail(f"unexpected content status {obj.content_status!r} for {obj.id}")

            counts[obj.type] += 1

        self.assertEqual(len(seen_ids), len(self.library.objects_by_id))
        self.assertEqual(counts["book"], 66)
        self.assertEqual(sum(counts.values()), len(self.library.objects_by_id))

    def test_category_directories_are_valid(self) -> None:
        top_level_folders = {path.name for path in OBJECTS_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(top_level_folders, EXPECTED_FOLDERS)

    def test_all_biblical_books_exist(self) -> None:
        expected_book_ids = {normalize_id(title) for title in BOOKS}
        actual_book_ids = set(self.library.objects_by_type["book"])

        self.assertEqual(len(expected_book_ids), 66)
        self.assertEqual(actual_book_ids, expected_book_ids)

    def test_all_biblical_books_include_wave2_metadata(self) -> None:
        for book_id in self.library.objects_by_type["book"]:
            book = self.library.objects_by_id[book_id]

            self.assertTrue(book.authorship_positions, book_id)
            self.assertTrue(book.date_ranges, book_id)
            self.assertTrue(book.original_audience.strip(), book_id)
            self.assertTrue(book.historical_setting.strip(), book_id)
            self.assertTrue(book.genre, book_id)
            self.assertTrue(book.structure, book_id)
            self.assertTrue(book.major_themes, book_id)
            self.assertTrue(book.canonical_placement.strip(), book_id)
            self.assertTrue(book.key_people, book_id)
            self.assertTrue(book.key_places, book_id)
            self.assertTrue(book.key_events, book_id)
            self.assertTrue(book.interpretive_disputes, book_id)
            self.assertTrue(book.primary_sources, book_id)

    def test_wave3_people_places_events_and_institutions_are_populated(self) -> None:
        for category in ("people", "places", "events", "institutions"):
            for path in sorted((OBJECTS_ROOT / category).glob("*.json")):
                obj = validate_object(
                    json.loads(path.read_text(encoding="utf-8")),
                    path=path.relative_to(CKL_ROOT).as_posix(),
                )

                if category == "events" and obj.title.startswith("Event Placeholder"):
                    self.assertEqual(obj.content_status, "placeholder", obj.id)
                    self.assertEqual(obj.review_status, "unreviewed", obj.id)
                    continue

                self.assertEqual(obj.content_status, "complete", obj.id)
                self.assertNotEqual(obj.summary, "", obj.id)
                self.assertNotEqual(obj.scripture_references, [], obj.id)
                self.assertNotEqual(obj.sources, [], obj.id)
                self.assertNotEqual(obj.review_status, "unreviewed", obj.id)
                self.assertGreaterEqual(len(obj.reviewed_by), 1, obj.id)
                self.assertIsNotNone(obj.last_reviewed, obj.id)
                self.assertGreater(obj.importance, 0, obj.id)

    def test_wave4_theology_themes_prophecy_word_studies_archaeology_and_faq_are_populated(
        self,
    ) -> None:
        for category in ("theology", "themes", "prophecy", "word_studies", "archaeology", "faq"):
            for path in sorted((OBJECTS_ROOT / category).glob("*.json")):
                obj = validate_object(
                    json.loads(path.read_text(encoding="utf-8")),
                    path=path.relative_to(CKL_ROOT).as_posix(),
                )

                self.assertEqual(obj.content_status, "complete", obj.id)
                self.assertNotEqual(obj.summary, "", obj.id)
                self.assertNotEqual(obj.sources, [], obj.id)
                self.assertNotEqual(obj.scripture_references, [], obj.id)
                self.assertNotEqual(obj.common_questions, [], obj.id)
                self.assertNotEqual(obj.interpretive_notes, [], obj.id)
                self.assertNotEqual(obj.review_status, "unreviewed", obj.id)
                self.assertGreaterEqual(len(obj.reviewed_by), 1, obj.id)
                self.assertIsNotNone(obj.last_reviewed, obj.id)
                self.assertGreater(obj.importance, 0, obj.id)

    def test_manifest_counts_match_inventory(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        actual_counts = Counter(obj.type for obj in self.library.objects_by_id.values())
        expected_manifest_counts = {
            manifest_category: actual_counts.get(category, 0)
            for category, manifest_category in CATEGORY_FOLDERS.items()
        }

        self.assertEqual(manifest["framework_version"], "1.0")
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["object_count"], len(self.library.objects_by_id))
        self.assertEqual(manifest["categories"], expected_manifest_counts)

    def test_no_ai_dependencies_are_imported(self) -> None:
        for path in sorted(CKL_ROOT.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module_name: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".", 1)[0]
                        self.assertNotIn(
                            module_name,
                            AI_IMPORT_PREFIXES,
                            msg=f"unexpected AI dependency import in {path}: {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module.split(".", 1)[0]
                    self.assertNotIn(
                        module_name,
                        AI_IMPORT_PREFIXES,
                        msg=f"unexpected AI dependency import in {path}: {node.module}",
                    )


if __name__ == "__main__":
    unittest.main()
