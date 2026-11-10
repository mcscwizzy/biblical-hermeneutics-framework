from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PSALMS_PATH = REPO_ROOT / "framework/canonical_library/objects/books/psalms.json"


EXPECTED = {
    "psalm-55-betrayal-and-historical-setting-limits": ("Psalm 55:9-14", "declaissé-walford-psalter-violence-2023"),
    "psalm-60-communal-defeat-and-book-context": ("Psalm 60:1-12", "verde-psalms-trauma-2022"),
    "psalm-66-collective-and-individual-praise": ("Psalm 66:1-20", "sutton-psalm66-piety-2021"),
    "psalm-75-proposed-wordplay-in-judgment-poem": ("Psalm 75:5-8", "jensen-psalm75-poetic-context-2001"),
    "psalm-80-vine-lament-and-son-ambiguity": ("Psalm 80:8-19", "streett-psalm80-historical-context-2014"),
    "psalm-81-hinge-lines-and-colometry-proposal": ("Psalm 81:5-12", "weber-psalm81-monocola-2024"),
    "psalm-97-kingship-and-book-four-narrative": ("Psalm 97:1-12", "hamilton-yhwh-kingship-psalms-2023"),
    "psalm-100-worship-and-the-psalter-sequence": ("Psalm 100:1-5", "firth-psalm100-worship-war-language-2021"),
}

EXPECTED_A2 = {
    "psalm-5-morning-motif-and-setting-limits": (
        "Psalm 5:1-12",
        "literary-convention",
        "botha-psalm5-polarity-2018",
    ),
    "psalm-20-amherst63-parallel-and-direction-debate": (
        "Psalm 20:1-5",
        "ancient-text",
        "ward-amherst63-psalm20-2023",
    ),
    "psalm-25-individual-prayer-and-collective-epilogue": (
        "Psalm 25:1-22",
        "literary-convention",
        "human-psalm25-tradition-setting-1996",
    ),
}


class Ed2MasterPsalmsWaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.book = json.loads(PSALMS_PATH.read_text(encoding="utf-8"))
        cls.evidence = {x["id"]: x for x in cls.book.get("evidence_items", [])}
        cls.sources = {x["id"]: x for x in cls.book.get("sources", [])}

    def test_additions_have_exact_scope_and_traceable_sources(self) -> None:
        self.assertTrue(set(EXPECTED).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                self.assertEqual("literary-convention", item["evidence_type"])
                self.assertEqual([reference], [x["reference"] for x in item["scripture_references"]])
                self.assertIn("psalms-masoretic", item["source_ids"])
                self.assertIn(source_id, item["source_ids"])
                self.assertTrue(set(item["source_ids"]).issubset(self.sources))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertNotEqual(item["primary_observation"], item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertTrue(source["title"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
                self.assertIn(evidence_id, source["supports"])

    def test_work_remains_unreviewed_and_limited_access_is_disclosed(self) -> None:
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertEqual([], self.book["reviewed_by"])
        self.assertIsNone(self.book["last_reviewed"])
        self.assertTrue(self.book["human_review_required"])
        psalm75 = self.evidence["psalm-75-proposed-wordplay-in-judgment-poem"]
        self.assertEqual("low", psalm75["confidence"])
        self.assertIn("Only abstract-level detail was accessible", psalm75["scholarly_interpretation"])
        self.assertIn(
            "only indexing records and abstract-level description were accessible",
            self.sources["jensen-psalm75-poetic-context-2001"]["notes"],
        )
        self.assertEqual([], self.evidence["psalm-80-vine-lament-and-son-ambiguity"]["related_objects"])

    def test_a2_additions_have_exact_scope_and_resolved_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A2).issubset(self.evidence))
        for evidence_id, (reference, evidence_type, source_id) in EXPECTED_A2.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                self.assertEqual(evidence_type, item["evidence_type"])
                self.assertEqual([reference], [x["reference"] for x in item["scripture_references"]])
                self.assertEqual("scholarly-reconstruction", item["assertion_type"])
                self.assertIn("psalms-masoretic", item["source_ids"])
                self.assertIn(source_id, item["source_ids"])
                self.assertTrue(set(item["source_ids"]).issubset(self.sources))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertNotEqual(item["primary_observation"], item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertIn(item["certainty"], {"established", "probable", "plausible", "uncertain"})
                self.assertTrue(item["dispute_status"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                self.assertIn(evidence_id, self.sources[source_id]["supports"])
                self.assertTrue(self.sources[source_id]["locator"])
                self.assertTrue(self.sources[source_id]["url"])

    def test_a2_source_access_limits_and_textual_uncertainties_are_explicit(self) -> None:
        psalm20 = self.evidence["psalm-20-amherst63-parallel-and-direction-debate"]
        self.assertEqual("medium", psalm20["confidence"])
        self.assertIn("not its direction", psalm20["scholarly_interpretation"])
        self.assertIn("full article was not accessible", psalm20["notes"])
        self.assertIn(
            "publication record and abstract were inspected; full text was not accessible",
            self.sources["kister-psalm20-amherst63-2020"]["notes"],
        )
        psalm25 = self.evidence["psalm-25-individual-prayer-and-collective-epilogue"]
        self.assertIn("not a settled textual or redactional finding", psalm25["temporal_scope"]["notes"])


if __name__ == "__main__":
    unittest.main()
