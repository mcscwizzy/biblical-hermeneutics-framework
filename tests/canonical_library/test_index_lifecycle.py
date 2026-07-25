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

    def test_index_includes_knowledge_graph_and_retrieval_metadata(self) -> None:
        root = Path(self.tmpdir.name) / "metadata-library"
        write_library(
            root,
            [
                make_object(
                    "abrahamic-covenant",
                    "covenant",
                    "Abrahamic Covenant",
                    ["Abrahamic covenant"],
                    canonical_story={
                        "phase": "Patriarchs",
                        "role": "Promise of seed, land, and blessing.",
                    },
                    hermeneutical_lens={
                        "book_context": "Genesis develops promise through Abraham's family.",
                        "covenant_context": "Abrahamic covenant",
                        "biblical_theology_themes": ["Seed", "Promise", "Land"],
                    },
                    retrieval_metadata={
                        "aliases": ["promise to Abraham"],
                        "search_terms": ["seed promise"],
                        "common_questions": ["What is the Abrahamic covenant?"],
                        "semantic_keywords": ["patriarchs", "land", "blessing"],
                    },
                    knowledge_layers={
                        "primary": "biblical_theology",
                        "secondary": ["biblical_text"],
                    },
                    claims=[
                        {
                            "id": "abrahamic-seed-promise",
                            "claim": "The covenant includes a seed promise.",
                            "claim_type": "biblical_theology",
                            "certainty": "textually_explicit",
                            "dispute_status": "not_disputed",
                            "scripture_references": ["Genesis 12:1-3"],
                            "rationale": "Seed and blessing are stated in the promise.",
                        }
                    ],
                    canonical_role="The Abrahamic covenant grounds later canonical promise theology.",
                    related_entries=["seed-theme"],
                    keywords=["promise theology"],
                    importance=9,
                )
            ],
        )
        clear_index_cache(root)

        index = refresh_index(root)
        entry = index.entries_by_id["abrahamic-covenant"]

        self.assertIn("seed", entry.field_terms["retrieval_metadata"])
        self.assertIn("promise", entry.field_terms["keywords"])
        self.assertIn("theology", entry.field_terms["canonical_role"])
        self.assertIn("patriarchs", entry.field_terms["canonical_story"])
        self.assertIn("genesis", entry.field_terms["hermeneutical_lens"])
        self.assertIn("seed", entry.field_terms["claims"])
        self.assertEqual(entry.knowledge_layer, "biblical_theology")
        self.assertIn("abrahamic covenant", entry.search_text)


if __name__ == "__main__":
    unittest.main()
