from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import unittest

from framework.canonical_library.retrieval import load_service


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "ckl_golden_queries.json"


class CKLGoldenQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.service = load_service()

    def test_golden_queries_match_expected_ranking_and_thresholds(self) -> None:
        for case in self.fixture["queries"]:
            with self.subTest(query=case["query"]):
                limit = int(case.get("limit", 8))
                response = self.service.search(case["query"], limit=limit)
                result_ids = [result.id for result in response.results]
                expected_results = list(case["expected_results"])
                expected_ids = [entry["id"] for entry in expected_results]

                self.assertGreaterEqual(len(result_ids), len(expected_ids))
                self.assertEqual(result_ids[: len(expected_ids)], expected_ids)
                self.assertEqual(len(result_ids), len(set(result_ids)))
                self.assertLessEqual(len(result_ids), limit)

                result_by_id = {result.id: result for result in response.results}
                for expected in expected_results:
                    result = result_by_id[expected["id"]]
                    self.assertGreaterEqual(result.score, float(expected["minimum_score"]))

                category_counts = Counter(result.category for result in response.results)
                self.assertTrue(all(count <= 3 for count in category_counts.values()))


if __name__ == "__main__":
    unittest.main()
