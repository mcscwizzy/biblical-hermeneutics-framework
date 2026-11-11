from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "luke-5-30-grumbling-and-wilderness-language": (
        "books/luke.json",
        "literary-convention",
        [("Luke 5:30", "direct")],
        "luke-greek",
        "tuohy-luke5-meal-scene-2012",
    ),
    "acts-15-29-eu-prassete-range": (
        "books/acts.json",
        "literary-convention",
        [("Acts 15:29", "direct")],
        "acts-greek",
        "moxon-acts15-eu-prassete-2024",
    ),
    "revelation-13-land-beast-as-asian-elite-network": (
        "books/revelation.json",
        "institution",
        [("Revelation 13:11-18", "direct")],
        "rev-greek",
        "friesen-beast-land-2003",
    ),
    "luke-8-1-3-women-scope": (
        "books/luke.json",
        "literary-convention",
        [("Luke 8:1-3", "direct")],
        "luke-greek",
        "blajer-luke8-women-2026",
    ),
    "luke-13-10-17-sabbath-healing-necessity": (
        "books/luke.json",
        "literary-convention",
        [("Luke 13:10-17", "direct")],
        "luke-greek",
        "kilgallen-luke13-obligation-heal-2001",
    ),
    "mark-7-3-pugme-pukna-variant": (
        "books/mark.json",
        "manuscript",
        [("Mark 7:3", "direct")],
        "mark-greek",
        "burkett-mark7-textual-variant-2019",
    ),
    "john-10-22-dedication-term-and-winter": (
        "books/john.json",
        "cultural-practice",
        [("John 10:22", "direct")],
        "john-greek",
        "foerster-john10-enkainia-2016",
    ),
}


class Ed2MasterNewTestamentWaveTests(unittest.TestCase):
    def test_e1_and_e2_records_have_exact_scopes_and_source_disclosures(self) -> None:
        paths = {value[0] for value in EXPECTED.values()}
        books = {
            path: json.loads((REPO_ROOT / "framework/canonical_library/objects" / path).read_text())
            for path in paths
        }
        for evidence_id, (path, evidence_type, expected_refs, primary_source, scholarly_source) in EXPECTED.items():
            with self.subTest(evidence=evidence_id):
                book = books[path]
                items = {item["id"]: item for item in book["evidence_items"]}
                sources = {source["id"]: source for source in book["sources"]}
                item = items[evidence_id]
                self.assertEqual(evidence_type, item["evidence_type"])
                self.assertEqual(
                    expected_refs,
                    [(ref["reference"], ref["relationship"]) for ref in item["scripture_references"]],
                )
                self.assertIn(primary_source, item["source_ids"])
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
                self.assertIn("ed2-master/wave-e-new-testament/", item["notes"])

    def test_e1_and_e2_items_remain_unreviewed_and_uncertainty_is_explicit(self) -> None:
        books = [
            json.loads((REPO_ROOT / "framework/canonical_library/objects" / path).read_text())
            for path in {value[0] for value in EXPECTED.values()}
        ]
        items = {item["id"]: item for book in books for item in book["evidence_items"]}
        self.assertEqual("interpretive_uncertainty", items["luke-5-30-grumbling-and-wilderness-language"]["dispute_status"])
        self.assertEqual("lexical_uncertainty", items["acts-15-29-eu-prassete-range"]["dispute_status"])
        self.assertEqual("major_scholarly_disagreement", items["revelation-13-land-beast-as-asian-elite-network"]["dispute_status"])
        self.assertEqual("interpretive_uncertainty", items["luke-8-1-3-women-scope"]["dispute_status"])
        self.assertEqual("interpretive_uncertainty", items["luke-13-10-17-sabbath-healing-necessity"]["dispute_status"])
        self.assertEqual("textual_variant", items["mark-7-3-pugme-pukna-variant"]["dispute_status"])
        self.assertEqual("low", items["mark-7-3-pugme-pukna-variant"]["confidence"])
        self.assertEqual("interpretive_uncertainty", items["john-10-22-dedication-term-and-winter"]["dispute_status"])
        self.assertEqual("low", items["john-10-22-dedication-term-and-winter"]["confidence"])
        self.assertIn("publisher’s bibliographic page and abstract", items["john-10-22-dedication-term-and-winter"]["confidence_rationale"])
        self.assertIn("full article was inaccessible", next(book for book in books if book["id"] == "john")["sources"][-1]["notes"])
        for book in books:
            self.assertEqual("draft", book["content_status"])
            self.assertEqual("in_review", book["review_status"])
            self.assertTrue(book["human_review_required"])


if __name__ == "__main__":
    unittest.main()
