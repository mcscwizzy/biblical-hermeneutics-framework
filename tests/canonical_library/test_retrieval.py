from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalLibrary

from .helpers import make_object, write_library


class CanonicalRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        write_library(
            self.root,
            [
                make_object(
                    "abraham",
                    "person",
                    "Abraham",
                    ["who is abraham", "tell me about abraham"],
                ),
                make_object(
                    "covenant-theme",
                    "theme",
                    "Covenant Theme",
                    ["covenant motif", "covenant pattern"],
                ),
                make_object(
                    "shechem",
                    "place",
                    "Shechem",
                    ["where is shechem", "why is shechem important"],
                ),
            ],
        )
        self.library = CanonicalLibrary(root=self.root).load()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_exact_id_lookup_is_case_insensitive(self) -> None:
        result = self.library.retrieve_exact("SHECHEM")

        self.assertIsNotNone(result)
        self.assertEqual(result.object.id, "shechem")
        self.assertEqual(result.match_type, "id")

    def test_alias_lookup(self) -> None:
        result = self.library.retrieve_exact("why is shechem important")

        self.assertIsNotNone(result)
        self.assertEqual(result.object.id, "shechem")
        self.assertEqual(result.match_type, "alias")
        self.assertEqual(result.matched_alias, "why is shechem important")

    def test_title_lookup(self) -> None:
        result = self.library.retrieve_exact("Shechem")

        self.assertIsNotNone(result)
        self.assertEqual(result.object.id, "shechem")
        self.assertEqual(result.match_type, "id")

    def test_keyword_lookup_returns_stable_ranked_results(self) -> None:
        first = self.library.retrieve_by_keywords("covenant abraham", limit=2)
        second = self.library.retrieve_by_keywords("covenant abraham", limit=2)

        self.assertEqual([result.object.id for result in first], [result.object.id for result in second])
        self.assertEqual(len(first), 2)
        self.assertTrue({result.object.id for result in first}.issuperset({"abraham", "covenant-theme"}))
        self.assertGreaterEqual(first[0].score, first[1].score)

    def test_keyword_limit_is_respected(self) -> None:
        results = self.library.retrieve_by_keywords("covenant abraham shechem", limit=1)

        self.assertEqual(len(results), 1)

    def test_unknown_query_returns_empty_results(self) -> None:
        self.assertEqual(self.library.retrieve_by_keywords("the and of", limit=5), [])
        self.assertIsNone(self.library.retrieve_exact(""))

    def test_semantic_retrieval_is_explicitly_unsupported(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.library.retrieve_semantic("covenant")

        with self.assertRaises(NotImplementedError):
            self.library.retrieve_hybrid("covenant")


if __name__ == "__main__":
    unittest.main()

