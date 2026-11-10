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

EXPECTED_A5 = {
    "psalm-39-wisdom-reflection-and-delayed-retribution": ("Psalm 39:1-13", "botha-psalm39-retribution-2017"),
    "psalm-48-zion-security-and-remembered-space": ("Psalm 48:8-14", "steiner-psalm48-narrated-space-2012"),
    "psalm-62-community-address-and-wealth-warning": ("Psalm 62:8-12", "botha-psalm62-community-exhortation-2018"),
    "psalm-71-old-age-and-generational-witness": ("Psalm 71:17-21", "liess-psalm71-aging-and-generational-witness-2023"),
}

EXPECTED_A6 = {
    "psalm-12-speech-poor-and-wisdom-polarity": ("Psalm 12:2-7", "botha-psalm12-poor-and-speech-2012"),
    "psalm-28-lament-praise-and-final-petition": ("Psalm 28:1-9", "barus-psalm28-mood-shift-2023"),
    "psalm-35-battlefield-and-courtroom-movement": ("Psalm 35:1-28", "simango-psalm35-structure-and-genre-2022"),
    "psalm-38-embodied-distress-and-prayer-for-wholeness": ("Psalm 38:1-22", "human-psalm38-body-imagery-2022"),
    "psalm-45-sound-and-performance-of-royal-poem": ("Psalm 45:1-2", "wendland-psalm45-sound-and-rhetoric-2013"),
}

EXPECTED_A7 = {
    "psalm-52-wealth-critique-and-wisdom-intertexts": ("Psalm 52:1-9", "botha-psalm52-wisdom-network-2013"),
    "psalm-59-evening-threat-and-morning-confidence": ("Psalm 59:1-17", "janowski-psalm59-time-and-prayer-2013"),
    "psalm-61-royal-voice-proposal": ("Psalm 61:4-7", "lemon-psalms61-63-hezekiah-bulla-2024"),
    "psalm-63-royal-voice-proposal": ("Psalm 63:7-11", "lemon-psalms61-63-hezekiah-bulla-2024"),
    "psalm-64-attack-to-vindication-narrative-movement": ("Psalm 64:1-10", "eder-psalm64-narrative-structure-2019"),
    "psalm-65-zion-to-earth-praise-sequence": ("Psalm 65:1-13", "botha-psalms65-68-cluster-2023"),
}

EXPECTED_A8 = {
    "psalm-86-korah-collection-lament-frame": ("Psalm 86:1-17", "loader-psalm86-korah-contextual-synergy-2010"),
    "psalm-87-zion-status-reading-dispute": ("Psalm 87:1-7", "rautenbach-psalm87-social-values-2008"),
    "psalm-70-concentric-structure-proposal": ("Psalm 70:1-5", "auffret-psalm70-structure-2011"),
    "psalm-101-royal-voice-and-community-justice": ("Psalm 101:1-8", "botha-psalm101-restoration-society-2016"),
    "psalm-108-head-imagery-and-royal-victory-metaphor": ("Psalm 108:1-13", "sutton-human-psalms108-110-head-imagery-2017"),
    "psalm-98-yhwh-kingship-in-book-four-cluster": ("Psalm 98:1-9", "blunda-psalms93-100-kingship-liturgy-2020"),
}

EXPECTED_A9 = {
    "psalm-57-reuse-in-psalm108-reframes-praise": ("Psalm 57:7-11", "botha-psalm108-quest-closure-2010"),
    "psalm-69-restoration-stanza-and-servants": ("Psalm 69:34-36", "lyons-servants-psalms-22-69-102-2021"),
    "psalm-94-weekday-song-and-poetic-sequence": ("Psalm 94:1-23", "jaffe-psalm94-wednesday-song-2026"),
    "psalm-99-zion-and-kingship-sequence": ("Psalm 99:1-9", "hamilton-yhwh-kingship-psalms-2023"),
}

EXPECTED_A10 = {
    "psalm-53-adaptation-and-cluster-context": ("Psalm 53:1-6", "botha-psalm53-canonical-2013"),
    "psalm-102-created-or-set-apart-people": ("Psalm 102:18", "van-wolde-psalm102-qualifications-actions-2019"),
    "psalm-109-speaker-and-reported-speech-debate": ("Psalm 109:1-31", "egwim-psalm109-case-presentation-2004"),
    "psalm-135-exodus-motifs-and-servants": ("Psalm 135", "human-psalms135-136-exodus-motifs-2021"),
}

EXPECTED_A11 = {
    "psalm-58-opening-word-and-versional-readings": (["Psalm 58:1"], ["begg-psalm58-opening-word-1988"]),
    "psalm-76-zion-hymn-and-unspecified-battle": (["Psalm 76:1-12"], ["smith-psalms73-83-editorial-2019"]),
    "psalm-138-praise-in-final-davidic-psalter": (["Psalm 138:1-8"], ["botha-final-davidic-psalter-2021"]),
    "psalm-140-selah-and-petition-structure": (["Psalm 140:3", "Psalm 140:5", "Psalm 140:8"], ["lyon-selah-antiquity-psalms-2018"]),
    "psalm-141-suffixes-and-fabrications": (["Psalm 141:3-5"], ["booij-psalm141-discipline-2005"]),
    "psalm-142-cave-superscription-and-historical-limits": (["Psalm 142:1-7"], ["skinner-davidic-superscriptions-2016"]),
    "psalm-143-in-galatians-argument-debate": (["Psalm 143:2"], ["moore-psalm143-galatians-2022", "bachmann-galatians-logic-2024"]),
    "psalm-144-reworked-royal-victory-song": (["Psalm 144:1-3", "Psalm 144:9-10"], ["zenger-fifth-book-psalms-1998"]),
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

    def test_a5_additions_have_exact_scope_and_verified_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A5).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A5.items():
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
                self.assertEqual("medium", item["confidence"])
                self.assertEqual("plausible", item["certainty"])
                self.assertEqual("interpretive_uncertainty", item["dispute_status"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertIn(evidence_id, source["supports"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
                self.assertIn("Full open-access", source["notes"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertTrue(self.book["human_review_required"])

    def test_a6_additions_have_exact_scope_and_verified_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A6).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A6.items():
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
                self.assertEqual("medium", item["confidence"])
                self.assertEqual("plausible", item["certainty"])
                self.assertEqual("interpretive_uncertainty", item["dispute_status"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertIn(evidence_id, source["supports"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
                self.assertIn("Full open-access article", source["notes"])
        self.assertIn("counts the superscription", self.evidence["psalm-12-speech-poor-and-wisdom-polarity"]["scripture_references"][0]["relevance_rationale"])
        self.assertIn("literary relationship", self.evidence["psalm-12-speech-poor-and-wisdom-polarity"]["scholarly_interpretation"])
        self.assertIn("specific disease or medical cause", self.evidence["psalm-38-embodied-distress-and-prayer-for-wholeness"]["scholarly_interpretation"])
        self.assertIn("public court performance", self.evidence["psalm-45-sound-and-performance-of-royal-poem"]["scholarly_interpretation"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertTrue(self.book["human_review_required"])

    def test_a7_additions_have_exact_scope_and_disclosed_source_access(self) -> None:
        self.assertTrue(set(EXPECTED_A7).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A7.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                self.assertEqual("literary-convention", item["evidence_type"])
                self.assertEqual("scholarly-reconstruction", item["assertion_type"])
                self.assertEqual([reference], [x["reference"] for x in item["scripture_references"]])
                self.assertEqual("unknown", item["scripture_references"][0]["temporal_relation"])
                self.assertEqual({"psalms-masoretic", source_id}, set(item["source_ids"]))
                self.assertTrue(set(item["source_ids"]).issubset(self.sources))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertNotEqual(item["primary_observation"], item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual("plausible", item["certainty"])
                self.assertEqual("interpretive_uncertainty", item["dispute_status"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertIn(evidence_id, source["supports"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
                expected_confidence = "low" if evidence_id in {
                    "psalm-61-royal-voice-proposal",
                    "psalm-63-royal-voice-proposal",
                } else "medium"
                self.assertEqual(expected_confidence, item["confidence"])
        lemon = self.sources["lemon-psalms61-63-hezekiah-bulla-2024"]
        self.assertIn("abstract inspected", lemon["notes"])
        self.assertIn("full article PDF was not accessible", lemon["notes"])
        self.assertIn("Only the 2024 publisher abstract was consulted", self.evidence["psalm-61-royal-voice-proposal"]["temporal_scope"]["notes"])
        self.assertIn("limits", self.sources["eder-psalm64-narrative-structure-2019"]["locator"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertEqual([], self.book["reviewed_by"])
        self.assertIsNone(self.book["last_reviewed"])
        self.assertTrue(self.book["human_review_required"])

    def test_a8_additions_have_exact_scope_and_resolved_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A8).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A8.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                self.assertEqual("literary-convention", item["evidence_type"])
                self.assertEqual("scholarly-reconstruction", item["assertion_type"])
                self.assertEqual([reference], [x["reference"] for x in item["scripture_references"]])
                self.assertEqual("unknown", item["scripture_references"][0]["temporal_relation"])
                self.assertEqual({"psalms-masoretic", source_id}, set(item["source_ids"]))
                self.assertTrue(set(item["source_ids"]).issubset(self.sources))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertNotEqual(item["primary_observation"], item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                expected_certainty = "disputed" if evidence_id == "psalm-87-zion-status-reading-dispute" else "plausible"
                expected_dispute = "major_scholarly_disagreement" if evidence_id == "psalm-87-zion-status-reading-dispute" else "interpretive_uncertainty"
                self.assertEqual(expected_certainty, item["certainty"])
                self.assertEqual(expected_dispute, item["dispute_status"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertIn(evidence_id, source["supports"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
        for evidence_id in {
            "psalm-70-concentric-structure-proposal",
            "psalm-98-yhwh-kingship-in-book-four-cluster",
        }:
            self.assertEqual("low", self.evidence[evidence_id]["confidence"])
            self.assertIn("abstract", self.evidence[evidence_id]["scholarly_interpretation"].lower())
            self.assertIn("abstract", self.evidence[evidence_id]["temporal_scope"]["notes"].lower())
            self.assertIn("abstract", self.sources[EXPECTED_A8[evidence_id][1]]["notes"].lower())
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertEqual([], self.book["reviewed_by"])
        self.assertTrue(self.book["human_review_required"])

    def test_a9_additions_have_exact_scope_and_resolved_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A9).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A9.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                expected_type = "cultural-practice" if evidence_id == "psalm-94-weekday-song-and-poetic-sequence" else "literary-convention"
                self.assertEqual(expected_type, item["evidence_type"])
                self.assertEqual("scholarly-reconstruction", item["assertion_type"])
                self.assertEqual([reference], [x["reference"] for x in item["scripture_references"]])
                self.assertEqual("unknown", item["scripture_references"][0]["temporal_relation"])
                self.assertEqual({"psalms-masoretic", source_id}, set(item["source_ids"]))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertIn(evidence_id, source["supports"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
        self.assertEqual("disputed", self.evidence["psalm-69-restoration-stanza-and-servants"]["certainty"])
        self.assertEqual("major_scholarly_disagreement", self.evidence["psalm-69-restoration-stanza-and-servants"]["dispute_status"])
        self.assertEqual("disputed", self.evidence["psalm-99-zion-and-kingship-sequence"]["certainty"])
        self.assertEqual("major_scholarly_disagreement", self.evidence["psalm-99-zion-and-kingship-sequence"]["dispute_status"])
        self.assertIn("psalm-99-zion-and-kingship-sequence", self.sources["hamilton-yhwh-kingship-psalms-2023"]["supports"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertEqual([], self.book["reviewed_by"])
        self.assertTrue(self.book["human_review_required"])

    def test_a10_additions_have_exact_scope_and_resolved_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A10).issubset(self.evidence))
        for evidence_id, (reference, source_id) in EXPECTED_A10.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                references = [x["reference"] for x in item["scripture_references"]]
                if evidence_id == "psalm-135-exodus-motifs-and-servants":
                    self.assertEqual(["Psalm 135:1", "Psalm 135:8-9"], references)
                else:
                    self.assertEqual([reference], references)
                self.assertEqual("unknown", item["scripture_references"][0]["temporal_relation"])
                self.assertEqual({"psalms-masoretic", source_id}, set(item["source_ids"]))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                source = self.sources[source_id]
                self.assertIn(evidence_id, source["supports"])
                self.assertTrue(source["locator"])
                self.assertTrue(source["url"])
        self.assertEqual("low", self.evidence["psalm-109-speaker-and-reported-speech-debate"]["confidence"])
        self.assertIn("abstract", self.sources["egwim-psalm109-case-presentation-2004"]["notes"].lower())
        self.assertEqual("disputed", self.evidence["psalm-102-created-or-set-apart-people"]["certainty"])
        self.assertEqual("major_scholarly_disagreement", self.evidence["psalm-102-created-or-set-apart-people"]["dispute_status"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertEqual([], self.book["reviewed_by"])
        self.assertTrue(self.book["human_review_required"])

    def test_a11_additions_have_exact_scope_and_resolved_sources(self) -> None:
        self.assertTrue(set(EXPECTED_A11).issubset(self.evidence))
        for evidence_id, (references, scholarly_sources) in EXPECTED_A11.items():
            with self.subTest(evidence=evidence_id):
                item = self.evidence[evidence_id]
                self.assertEqual("literary-convention", item["evidence_type"])
                self.assertEqual("scholarly-reconstruction", item["assertion_type"])
                self.assertEqual(references, [x["reference"] for x in item["scripture_references"]])
                self.assertTrue(all(x["temporal_relation"] == "unknown" for x in item["scripture_references"]))
                self.assertEqual({"psalms-masoretic", *scholarly_sources}, set(item["source_ids"]))
                self.assertTrue(set(item["source_ids"]).issubset(self.sources))
                self.assertTrue(item["primary_observation"])
                self.assertTrue(item["scholarly_interpretation"])
                self.assertNotEqual(item["primary_observation"], item["scholarly_interpretation"])
                self.assertTrue(item["passage_relevance"])
                self.assertTrue(item["confidence_rationale"])
                self.assertTrue(item["temporal_scope"]["notes"])
                self.assertEqual([], item["related_objects"])
                self.assertEqual([], item["related_evidence"])
                self.assertIn("psalms-research-packets-a11.md", item["notes"])
                for source_id in scholarly_sources:
                    source = self.sources[source_id]
                    self.assertIn(evidence_id, source["supports"])
                    self.assertTrue(source["locator"])
                    self.assertTrue(source["url"])
        for evidence_id in {
            "psalm-58-opening-word-and-versional-readings",
            "psalm-141-suffixes-and-fabrications",
        }:
            self.assertEqual("low", self.evidence[evidence_id]["confidence"])
        self.assertIn("only the publisher abstract", self.sources["begg-psalm58-opening-word-1988"]["notes"].lower())
        self.assertIn("numbering includes the superscription", self.sources["booij-psalm141-discipline-2005"]["notes"])
        self.assertIn("publisher marks the full article as access-restricted", self.evidence["psalm-144-reworked-royal-victory-song"]["temporal_scope"]["notes"])
        self.assertIn("related_objects and related_evidence remain empty", self.evidence["psalm-143-in-galatians-argument-debate"]["notes"])
        self.assertEqual("draft", self.book["content_status"])
        self.assertEqual("in_review", self.book["review_status"])
        self.assertEqual([], self.book["reviewed_by"])
        self.assertTrue(self.book["human_review_required"])


if __name__ == "__main__":
    unittest.main()
