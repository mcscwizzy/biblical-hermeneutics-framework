from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library.retrieval import clear_index_cache, load_index, load_service, refresh_index

from .helpers import make_object, write_library


class CKLIndexLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        write_library(
            self.root,
            [
                make_object(
                    "shechem",
                    "place",
                    "Shechem",
                    ["where is shechem"],
                    summary="Shechem is a covenant location.",
                    importance=8,
                ),
                make_object(
                    "joshua",
                    "book",
                    "Joshua",
                    ["book of joshua"],
                    summary="Joshua records covenant renewal at Shechem.",
                    importance=7,
                ),
            ],
        )
        clear_index_cache(self.root)

    def tearDown(self) -> None:
        clear_index_cache(self.root)
        self.tmpdir.cleanup()

    def test_index_build_logs_stats(self) -> None:
        with self.assertLogs("framework.canonical_library.retrieval.indexer", level="INFO") as captured:
            index = refresh_index(self.root)

        self.assertEqual(index.stats.valid_documents, 2)
        self.assertEqual(index.stats.invalid_documents, 0)
        self.assertEqual(index.stats.indexed_entries, 2)
        self.assertTrue(
            any(
                "Built CKL index:" in message
                and "scanned_files=" in message
                and "valid_documents=" in message
                and "invalid_documents=" in message
                and "build_duration_ms=" in message
                for message in captured.output
            )
        )

    def test_index_is_cached_until_inventory_changes(self) -> None:
        first = load_index(self.root)
        second = load_index(self.root)

        self.assertIs(first, second)

        source_path = self.root / "objects" / "places" / "shechem.json"
        data = source_path.read_text(encoding="utf-8")
        source_path.write_text(data.replace("covenant location", "major covenant location"), encoding="utf-8")

        third = load_index(self.root)

        self.assertIsNot(first, third)

    def test_refresh_forces_rebuild(self) -> None:
        first = load_index(self.root)
        second = refresh_index(self.root)

        self.assertIsNot(first, second)

    def test_load_service_reuses_cached_index(self) -> None:
        first = load_service(self.root)
        second = load_service(self.root)

        self.assertIs(first.index, second.index)


if __name__ == "__main__":
    unittest.main()
