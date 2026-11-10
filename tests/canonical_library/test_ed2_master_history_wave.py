from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "2chronicles-14-cushites-and-rhetorical-setting": (
        "historical-event",
        [
            ("2 Chronicles 14:9-15", "direct"),
            ("2 Chronicles 16:8", "contextual"),
            ("1 Kings 15:9-24", "comparative"),
        ],
        "jonker-cushites-chronicles-2023",
    ),
    "2chronicles-18-jehoshaphat-and-micaiah": (
        "literary-convention",
        [
            ("2 Chronicles 18:1-34", "direct"),
            ("2 Chronicles 19:1-3", "contextual"),
            ("1 Kings 22:1-40", "comparative"),
        ],
        "dillard-chronicles-jehoshaphat-1986",
    ),
    "2chronicles-25-amaziah-and-kings-parallel": (
        "literary-convention",
        [
            ("2 Chronicles 25:1-28", "direct"),
            ("2 Kings 14:1-20", "comparative"),
        ],
        "hwang-amaziah-kings-chronicles-2025",
    ),
}


class Ed2MasterHistoryWaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.book = json.loads(
            (REPO_ROOT / "framework/canonical_library/objects/books/2-chronicles.json").read_text()
        )

    def test_c1_records_have_exact_supported_scopes_and_source_disclosures(self) -> None:
        items = {x["id"]: x for x in self.book.get("evidence_items", [])}
        sources = {x["id"]: x for x in self.book.get("sources", [])}
        for evidence_id, (evidence_type, expected_refs, scholarly_source) in EXPECTED.items():
            with self.subTest(evidence=evidence_id):
                item = items[evidence_id]
                actual_refs = [
                    (x["reference"], x["relationship"])
                    for x in item["scripture_references"]
                ]
                self.assertEqual(expected_refs, actual_refs)
                self.assertEqual(evidence_type, item["evidence_type"])
                self.assertIn("2-chronicles-1-36", item["source_ids"])
                self.assertIn(scholarly_source, item["source_ids"])
                self.assertIn(evidence_id, sources[scholarly_source]["supports"])
                self.assertTrue(sources[scholarly_source]["locator"])
                self.assertTrue(sources[scholarly_source]["url"])
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                self.assertIn("ed2-master/wave-c-history/", item["notes"])

    def test_c1_source_access_limits_and_review_governance_are_explicit(self) -> None:
        items = {x["id"]: x for x in self.book.get("evidence_items", [])}
        sources = {x["id"]: x for x in self.book.get("sources", [])}
        self.assertIn("pp. 99-100", sources["jonker-cushites-chronicles-2023"]["locator"])
        self.assertIn("p. 20", sources["dillard-chronicles-jehoshaphat-1986"]["locator"])
        self.assertIn("abstract", sources["hwang-amaziah-kings-chronicles-2025"]["locator"].lower())
        self.assertIn("was not consulted", sources["hwang-amaziah-kings-chronicles-2025"]["notes"].lower())
        self.assertEqual("historical_uncertainty", items["2chronicles-14-cushites-and-rhetorical-setting"]["dispute_status"])
        self.assertEqual("low", items["2chronicles-25-amaziah-and-kings-parallel"]["confidence"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertTrue(self.book["human_review_required"])


if __name__ == "__main__":
    unittest.main()
