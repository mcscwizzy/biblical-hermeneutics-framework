from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from framework.canonical_library.evaluation import (
    compare_rankings,
    evaluate_rankings,
    load_candidate_rankings,
    load_relevance_corpus,
)


CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "framework"
    / "canonical_library"
    / "benchmarks"
    / "semantic_relevance.json"
)


class OptionalRetrievalEvaluationTests(unittest.TestCase):
    def test_checked_in_relevance_corpus_is_valid(self) -> None:
        corpus = load_relevance_corpus(CORPUS_PATH)
        self.assertEqual(corpus["version"], 1)
        self.assertGreaterEqual(len(corpus["queries"]), 7)

    def test_metrics_and_deltas_compare_candidate_to_baseline(self) -> None:
        corpus = {
            "queries": [
                {"id": "one", "query": "q", "limit": 3, "relevant_ids": ["a", "b"]}
            ]
        }
        report = compare_rankings(
            corpus,
            {"one": ["x", "a", "y"]},
            {"one": ["a", "b", "x"]},
        )
        self.assertEqual(report["baseline"]["mean_recall_at_k"], 0.5)
        self.assertEqual(report["candidate"]["mean_recall_at_k"], 1.0)
        self.assertEqual(report["delta"]["mean_recall_at_k"], 0.5)
        self.assertGreater(report["delta"]["mean_reciprocal_rank"], 0)

    def test_missing_candidate_queries_score_zero_without_a_model_dependency(self) -> None:
        corpus = {"queries": [{"id": "one", "query": "q", "relevant_ids": ["a"]}]}
        report = evaluate_rankings(corpus, {}, system="empty-candidate")
        self.assertEqual(report["mean_recall_at_k"], 0.0)
        self.assertEqual(report["queries"][0]["missing_relevant_ids"], ["a"])

    def test_candidate_loader_accepts_mapping_and_result_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mapping_path = Path(tmp) / "mapping.json"
            mapping_path.write_text(json.dumps({"one": ["a", "b"]}), encoding="utf-8")
            self.assertEqual(load_candidate_rankings(mapping_path), {"one": ["a", "b"]})
            list_path = Path(tmp) / "list.json"
            list_path.write_text(
                json.dumps({"results": [{"id": "one", "result_ids": ["b", "a"]}]}),
                encoding="utf-8",
            )
            self.assertEqual(load_candidate_rankings(list_path), {"one": ["b", "a"]})


if __name__ == "__main__":
    unittest.main()
