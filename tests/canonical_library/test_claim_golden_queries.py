from __future__ import annotations

import json
from pathlib import Path
import unittest

from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "ckl_claim_golden_queries.json"
DATABASE_PATH = Path(__file__).resolve().parents[2] / ".bhf" / "ckl.sqlite"
ROOT = Path(__file__).resolve().parents[2] / "framework" / "canonical_library"


class CKLClaimGoldenQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.library = SQLiteCanonicalLibrary.from_path(DATABASE_PATH, root=ROOT)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.library.close()

    def test_claim_ranking_and_hydration_match_golden_cases(self) -> None:
        for case in self.fixture["queries"]:
            with self.subTest(case=case["id"]):
                parent_id = case["parent_object_id"]
                ranked = self.library.repository.retrieve_claim_evidence(
                    case["query"],
                    [parent_id],
                    parent_scores={parent_id: 1.0},
                    limit_per_object=3,
                )[parent_id]
                self.assertTrue(ranked)
                selected = ranked[0]
                self.assertEqual(selected.claim_id, case["expected_claim_id"])
                self.assertGreaterEqual(selected.retrieval_score, case["minimum_score"])
                source_ids = {source["id"] for source in selected.sources}
                self.assertTrue(set(case["expected_source_ids"]).issubset(source_ids))
                self.assertTrue(
                    set(case["expected_scripture_references"]).issubset(
                        set(selected.scripture_references)
                    )
                )


if __name__ == "__main__":
    unittest.main()
