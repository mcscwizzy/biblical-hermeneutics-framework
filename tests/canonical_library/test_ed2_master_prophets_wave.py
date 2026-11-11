from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "ezekiel-22-prophets-princes-textual-reading": (
        "books/ezekiel.json",
        "ancient-text",
        [("Ezekiel 22:25", "direct"), ("Ezekiel 22:28", "contextual")],
        "ndoga-ezekiel22-textual-reading-2014",
    ),
    "ezekiel-31-pharaoh-cedar-and-sheol": (
        "books/ezekiel.json",
        "worldview-concept",
        [("Ezekiel 31:1-18", "direct")],
        "lee-ezekiel31-cedar-sheol-2016",
    ),
    "isaiah10-5-8-assyrian-agency-and-polemical-contrast": (
        "books/isaiah.json",
        "literary-convention",
        [("Isaiah 10:5-8", "direct")],
        "aster-isaiah10-assyrian-ideology-2017",
    ),
}


class Ed2MasterProphetsWaveTests(unittest.TestCase):
    def test_d1_records_have_exact_supported_scopes_and_source_disclosures(self) -> None:
        books = {
            path: json.loads((REPO_ROOT / "framework/canonical_library/objects" / path).read_text())
            for path in {value[0] for value in EXPECTED.values()}
        }
        for evidence_id, (path, evidence_type, expected_refs, scholarly_source) in EXPECTED.items():
            with self.subTest(evidence=evidence_id):
                book = books[path]
                items = {item["id"]: item for item in book["evidence_items"]}
                sources = {source["id"]: source for source in book["sources"]}
                item = items[evidence_id]
                self.assertEqual(evidence_type, item["evidence_type"])
                self.assertEqual(expected_refs, [(ref["reference"], ref["relationship"]) for ref in item["scripture_references"]])
                self.assertIn(book["id"] + "-masoretic", item["source_ids"])
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
                self.assertIn("ed2-master/wave-d-prophets/", item["notes"])

    def test_d1_access_limits_and_review_governance_are_explicit(self) -> None:
        ezekiel = json.loads((REPO_ROOT / "framework/canonical_library/objects/books/ezekiel.json").read_text())
        isaiah = json.loads((REPO_ROOT / "framework/canonical_library/objects/books/isaiah.json").read_text())
        items = {
            item["id"]: item
            for book in (ezekiel, isaiah)
            for item in book["evidence_items"]
        }
        self.assertEqual("textual_variant", items["ezekiel-22-prophets-princes-textual-reading"]["dispute_status"])
        self.assertEqual("interpretive_uncertainty", items["ezekiel-31-pharaoh-cedar-and-sheol"]["dispute_status"])
        self.assertEqual("interpretive_uncertainty", items["isaiah10-5-8-assyrian-agency-and-polemical-contrast"]["dispute_status"])
        for book in (ezekiel, isaiah):
            self.assertEqual("draft", book["content_status"])
            self.assertEqual("in_review", book["review_status"])
            self.assertTrue(book["human_review_required"])

    def test_d2_nahum_one_city_reading_remains_a_low_confidence_proposal(self) -> None:
        book = json.loads((REPO_ROOT / "framework/canonical_library/objects/books/nahum.json").read_text())
        item = next(x for x in book["evidence_items"] if x["id"] == "nahum-3-8-9-one-city-text-critical-proposal")
        sources = {source["id"]: source for source in book["sources"]}
        self.assertEqual("ancient-text", item["evidence_type"])
        self.assertEqual(["Nahum 3:8-9"], [x["reference"] for x in item["scripture_references"]])
        self.assertEqual("low", item["confidence"])
        self.assertEqual("textual_variant", item["dispute_status"])
        self.assertEqual("disputed", item["certainty"])
        self.assertTrue({"nahum-masoretic", "catss-nahum", "nets-twelve", "gruetter-nahum3-one-city-2017"}.issubset(item["source_ids"]))
        self.assertIn(item["id"], sources["gruetter-nahum3-one-city-2017"]["supports"])
        self.assertIn("pp. 160–175", sources["gruetter-nahum3-one-city-2017"]["locator"])
        self.assertIn("complete article was inspected", sources["gruetter-nahum3-one-city-2017"]["notes"])
        self.assertIn("not as archaeological evidence", item["scholarly_interpretation"])
        self.assertTrue(item["primary_observation"])
        self.assertTrue(item["temporal_scope"]["notes"])
        self.assertEqual([], item["related_objects"])
        self.assertEqual([], item["related_evidence"])
        self.assertEqual("draft", book["content_status"])
        self.assertEqual("in_review", book["review_status"])
        self.assertTrue(book["human_review_required"])


if __name__ == "__main__":
    unittest.main()
