from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from framework.canonical_library.benchmarking import (
    load_retrieval_corpus,
    percentile,
    run_retrieval_benchmark,
)


CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "framework"
    / "canonical_library"
    / "benchmarks"
    / "retrieval_latency.json"
)


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_checked_in_corpus_is_valid_and_broad(self) -> None:
        corpus = load_retrieval_corpus(CORPUS_PATH)
        self.assertEqual(corpus["version"], 1)
        self.assertGreaterEqual(len(corpus["queries"]), 10)
        self.assertTrue(all(len(case["query"].split()) >= 7 for case in corpus["queries"]))

    def test_benchmark_reports_latency_fingerprint_and_anchor_failures(self) -> None:
        ticks = iter([0.0, 0.010, 1.0, 1.030])
        corpus = {
            "version": 1,
            "queries": [
                {
                    "id": "case",
                    "query": "broad query",
                    "limit": 2,
                    "expected_anchors": ["alpha", "missing"],
                }
            ],
        }

        report = run_retrieval_benchmark(
            lambda _query, _limit: [{"id": "alpha"}, {"id": "beta"}],
            corpus,
            iterations=2,
            warmups=0,
            clock=lambda: next(ticks),
        )

        self.assertEqual(report["median_ms"], 20.0)
        self.assertEqual(report["p95_ms"], 30.0)
        self.assertEqual(len(report["result_fingerprint"]), 64)
        self.assertEqual(report["anchor_failures"][0]["missing_anchors"], ["missing"])

    def test_duplicate_case_ids_fail_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corpus.json"
            path.write_text(
                json.dumps(
                    {
                        "queries": [
                            {"id": "same", "query": "one"},
                            {"id": "same", "query": "two"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_retrieval_corpus(path)

    def test_nearest_rank_percentile(self) -> None:
        self.assertEqual(percentile([10.0, 20.0, 30.0, 40.0], 0.95), 40.0)


if __name__ == "__main__":
    unittest.main()
