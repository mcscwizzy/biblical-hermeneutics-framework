from __future__ import annotations

import unittest
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_B1 = {
    "proverbs-2-conditional-argument-structure": (
        "proverbs",
        ["Proverbs 2:1-22"],
        "loader-proverbs2-syntactic-structure-2013",
    ),
    "proverbs-28-rulers-and-poor-structure": (
        "proverbs",
        ["Proverbs 28:1-28"],
        "gilbert-proverbs28-29-ruling-class-2007",
    ),
    "ecclesiastes-10-1-flies-of-death-translation": (
        "ecclesiastes",
        ["Ecclesiastes 10:1"],
        "whybray-ecclesiastes10-1-lexical-1989",
    ),
}


class Ed2MasterWisdomWaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.objects = {
            name: json.loads(
                (REPO_ROOT / f"framework/canonical_library/objects/books/{name}.json").read_text()
            )
            for name in {value[0] for value in EXPECTED_B1.values()}
        }

    def test_b1_records_have_exact_scope_supported_sources_and_review_status(self) -> None:
        for evidence_id, (book_id, references, source_id) in EXPECTED_B1.items():
            with self.subTest(evidence=evidence_id):
                obj = self.objects[book_id]
                item = next(x for x in obj["evidence_items"] if x["id"] == evidence_id)
                sources = {x["id"]: x for x in obj["sources"]}
                self.assertEqual(references, [x["reference"] for x in item["scripture_references"]])
                self.assertIn("proverbs-masoretic" if book_id == "proverbs" else "ecclesiastes-masoretic", item["source_ids"])
                self.assertIn(source_id, item["source_ids"])
                self.assertIn(source_id, sources)
                self.assertIn(evidence_id, sources[source_id]["supports"])
                self.assertTrue(sources[source_id]["locator"])
                self.assertTrue(sources[source_id]["url"])
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                self.assertIn("ed2-master/wave-b-wisdom/", item["notes"])
                self.assertEqual("draft", obj["content_status"])
                self.assertEqual("in_review", obj["review_status"])
                self.assertTrue(obj["human_review_required"])

    def test_b1_access_limits_and_uncertainty_are_explicit(self) -> None:
        sources = {
            source["id"]: source
            for obj in self.objects.values()
            for source in obj["sources"]
        }
        self.assertIn("Full open-access article inspected", sources["loader-proverbs2-syntactic-structure-2013"]["notes"])
        self.assertIn("abstract", sources["gilbert-proverbs28-29-ruling-class-2007"]["notes"])
        self.assertIn("full scanned commentary", sources["whybray-ecclesiastes10-1-lexical-1989"]["notes"])
        proverbs = {x["id"]: x for x in self.objects["proverbs"]["evidence_items"]}
        ecclesiastes = {x["id"]: x for x in self.objects["ecclesiastes"]["evidence_items"]}
        self.assertEqual("minor_scholarly_disagreement", proverbs["proverbs-2-conditional-argument-structure"]["dispute_status"])
        self.assertEqual("minor_scholarly_disagreement", proverbs["proverbs-28-rulers-and-poor-structure"]["dispute_status"])
        self.assertEqual("lexical_uncertainty", ecclesiastes["ecclesiastes-10-1-flies-of-death-translation"]["dispute_status"])


if __name__ == "__main__":
    unittest.main()
