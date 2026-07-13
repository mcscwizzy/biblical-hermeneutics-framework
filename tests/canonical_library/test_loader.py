from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalLibrary, CanonicalValidationError

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
            "people": 100,
            "places": 75,
            "events": 75,
            "books": 66,
            "word_studies": 50,
            "archaeology": 50,
            "institutions": 34,
            "prophecy": 10,
            "faq": 50,
        }

        self.assertEqual(len(library.objects_by_id), 610)
        self.assertEqual(library.manifest["object_count"], 610)
        self.assertEqual(library.manifest["framework_version"], "1.0")
        self.assertEqual(library.manifest["schema_version"], "1.0")
        self.assertEqual(library.manifest["categories"], expected_categories)

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
        self.assertEqual(result.object.id, "alpha")


if __name__ == "__main__":
    unittest.main()
