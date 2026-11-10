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

EXPECTED_A3 = {
    "psalm-7-cush-superscription-and-setting-limits": ("Psalm 7:1-17", "literary-convention", "berger-psalm7-benjaminite-conflict-2014"),
    "psalm-11-refuge-and-spatial-argument": ("Psalm 11:1-7", "literary-convention", "prinsloo-psalm11-spatial-reading-2015"),
    "psalm-14-psalm53-revision-debate": ("Psalm 14:1-7", "literary-convention", "botha-psalm53-canonical-2013"),
    "psalm-17-textual-proposals-verses-11-and-14": ("Psalm 17:1-15", "manuscript", "bazylinski-psalm17-text-2021"),
    "psalm-21-request-language-diplomatic-proposal": ("Psalm 21:2", "literary-convention", "sheveka-royal-psalms-diplomatic-2005"),
    "psalm-26-walking-integrity-and-wisdom-structure": ("Psalm 26:1-12", "literary-convention", "potgieter-psalm26-wisdom-2013"),
    "psalm-33-sea-and-deep-imagery": ("Psalm 33:6-9", "literary-convention", "stoltz-psalm33-contextual-2018"),
    "psalm-43-refrain-and-stanza-structure": ("Psalm 43:1-5", "literary-convention", "simango-psalm42-43-structure-2025"),
    "psalm-49-wisdom-poem-and-chiastic-focus": ("Psalm 49:1-20", "literary-convention", "pleins-psalm49-structure-1996"),
    "psalm-83-coalition-imagery-and-setting-limits": ("Psalm 83:1-18", "literary-convention", "mitchell-psalter-psalm83-1995"),
}


EXPECTED_A4 = {
    "psalm-46-chaos-waters-and-stream-imagery": ("Psalm 46:2-5", "schader-psalms46-48-spatiality-2010"),
    "psalm-56-superscription-and-editorial-frame": ("Psalm 56:1-13", "potgieter-psalm56-editorial-context-2015"),
    "psalm-77-lament-memory-and-exodus-reframing": ("Psalm 77:1-20", "kamuwanga-psalm77-exile-suffering-2007"),
    "psalm-91-wisdom-language-and-protection-instruction": ("Psalm 91:1-16", "botha-psalm91-wisdom-2012"),
    "psalm-92-creation-order-and-sabbath-song": ("Psalm 92:1-15", "tucker-psalm92-ordered-world-2019"),
    "psalm-105-history-recounted-as-liturgy": ("Psalm 105:1-45", "gillingham-psalms105-106-liturgy-2015"),
    "psalm-111-acrostic-praise-and-scribal-learning": ("Psalm 111:1-10", "prinsloo-psalm111-112-acrostics-2019"),
    "psalm-139-imprecation-and-ambiguity-in-prayer": ("Psalm 139:19-24", "firth-psalm139-ambiguity-2019"),
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

    def test_a3_additions_have_exact_scope_and_resolved_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A3).issubset(self.evidence))
        for evidence_id, (reference, evidence_type, source_id) in EXPECTED_A3.items():
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
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertIn(item["certainty"], {"textually_explicit", "strong_consensus", "probable", "plausible", "disputed", "speculative", "insufficient_evidence"})
                self.assertTrue(item["dispute_status"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                self.assertIn(evidence_id, self.sources[source_id]["supports"])
                self.assertTrue(self.sources[source_id]["locator"])
                self.assertTrue(self.sources[source_id]["url"])


    def test_a4_additions_have_exact_scope_and_verified_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A4).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A4.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                self.assertEqual("literary-convention", item["evidence_type"])
                self.assertEqual("scholarly-reconstruction", item["assertion_type"])
                self.assertEqual([reference], [x["reference"] for x in item["scripture_references"]])
                self.assertEqual("unknown", item["scripture_references"][0]["temporal_relation"])
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
                self.assertIn(evidence_id, self.sources[source_id]["supports"])
                self.assertTrue(self.sources[source_id]["locator"])
                self.assertTrue(self.sources[source_id]["url"])
                self.assertEqual("draft", self.book["content_status"])
                self.assertEqual("in_review", self.book["review_status"])
                self.assertTrue(self.book["human_review_required"])
        self.assertEqual("low", self.evidence["psalm-105-history-recounted-as-liturgy"]["confidence"])
        self.assertEqual("speculative", self.evidence["psalm-105-history-recounted-as-liturgy"]["certainty"])
        self.assertIn("full article was not accessible", self.evidence["psalm-105-history-recounted-as-liturgy"]["scholarly_interpretation"])
        self.assertEqual("major_scholarly_disagreement", self.evidence["psalm-139-imprecation-and-ambiguity-in-prayer"]["dispute_status"])
        self.assertIn("repository record and the PDF's printed page numbers", self.sources["schader-psalms46-48-spatiality-2010"]["notes"])


if __name__ == "__main__":
    unittest.main()
