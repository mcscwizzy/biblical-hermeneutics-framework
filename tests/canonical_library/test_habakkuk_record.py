from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import (
    CURRENT_CERTAINTY_VALUES,
    CURRENT_DISPUTE_STATUS_VALUES,
    CanonicalLibrary,
    SQLiteCanonicalLibrary,
)
from framework.canonical_library.database_builder import build_database
from framework.canonical_library.retrieval import CKLRetrievalService


class HabakkukRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.habakkuk = cls.library.retrieve_by_id("habakkuk").object

    def test_habakkuk_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Habakkuk, the framing voice, and the first-person complainant, watcher, petitioner, and singer",
                "YHWH in direct answers, reported action, and divine-warrior manifestation",
                "Judah's wicked and righteous, Torah, justice, and the oppressed",
                "the Chaldeans or Babylonians, their ruler, army, cavalry, captives, and conquered peoples",
                "the arrogant one, plundered nations, debtors, taunting witnesses, and survivors",
                "personified wealth, death, and Sheol; idol makers, worshipers, and mute images",
                "Cushan, Midian, mountains, rivers, sea, sun, moon, horses, and the anointed one",
                "musicians, fig tree, vine, olive, fields, flock, herd, and later interpreters",
            }.issubset(self.habakkuk.key_people)
        )
        self.assertTrue(
            {
                "Habakkuk 1:1: superscription naming the oracle or burden that Habakkuk the prophet saw",
                "Habakkuk 1:2-4: first complaint over violence, paralyzed Torah, and distorted justice",
                "Habakkuk 1:5-11: divine response announcing the fearsome Chaldeans and qualifying their guilty self-deification",
                "Habakkuk 1:12-17: second complaint over divine use of a more wicked conqueror, fish, hook, net, and sacrifice imagery",
                "Habakkuk 2:1: watchpost declaration awaiting an answer and correction",
                "Habakkuk 2:2-5: vision-tablet instruction, appointed time, waiting, and the righteous living by faithfulness or faith",
                "Habakkuk 2:6-20: taunt and five-woe sequence against plunder, unjust gain, blood-built cities, intoxication, and idolatry",
                "Habakkuk 3:1-2: prayer superscription, shigionoth, petition for renewed work, and mercy within wrath",
                "Habakkuk 3:3-15: performance-marked divine-warrior theophany using exodus, creation, storm, and victory imagery",
                "Habakkuk 3:16-19: trembling, waiting, agricultural collapse, joy, strength, and musical subscription",
            }.issubset(self.habakkuk.structure)
        )

    def test_habakkuk_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Hosea",
            "Amos",
            "Jonah",
            "Nineveh",
        }
        record_values = {
            *self.habakkuk.authorship_positions,
            *self.habakkuk.date_ranges,
            self.habakkuk.historical_setting,
            *self.habakkuk.key_people,
            *self.habakkuk.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "superscription and oracle or burden",
                "prophetic complaint, lament, and disputation",
                "divine response and historical oracle",
                "watchman report and vision instruction",
                "wisdom contrast and appointed-time saying",
                "taunt song and five woe oracles",
                "ridicule and idol polemic",
                "temple acclamation",
                "prayer superscription, petition, and hymn",
                "divine-warrior theophany and victory song",
                "confession of fear, waiting, trust, and joy",
                "musical directions and subscription",
            }.issubset(self.habakkuk.genre)
        )
        self.assertIn(
            "Masoretic Habakkuk within the Book of the Twelve",
            self.habakkuk.primary_sources,
        )
        self.assertIn(
            "Old Greek Ambakoum and other ancient versions",
            self.habakkuk.primary_sources,
        )
        self.assertIn(
            "Judean Desert manuscripts of Habakkuk and Pesher Habakkuk",
            self.habakkuk.primary_sources,
        )

    def test_habakkuk_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.habakkuk.content_status, "draft")
        self.assertEqual(self.habakkuk.review_status, "in_review")
        self.assertTrue(self.habakkuk.human_review_required)
        self.assertIsNone(self.habakkuk.last_reviewed)
        self.assertEqual(
            self.habakkuk.section_status["human_review"],
            "missing",
        )
        self.assertEqual(
            self.habakkuk.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.habakkuk.sources}
        self.assertGreaterEqual(len(self.habakkuk.claims), 24)
        self.assertGreaterEqual(len(self.habakkuk.interpretive_notes), 40)
        for claim in self.habakkuk.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.habakkuk.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_habakkuk_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.habakkuk.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 18)
        self.assertTrue(self.habakkuk.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.habakkuk.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.habakkuk.retrieval_metadata["common_questions"])
        self.assertTrue(self.habakkuk.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "babylon-1",
                "divine-justice",
                "faith",
                "judgment",
                "hope-theme",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.habakkuk.related_objects
                }
            )
        )

    def test_retrieval_answers_habakkuk_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Habakkuk and when was his prophecy written?",
            "What does the oracle or burden title in Habakkuk 1:1 mean?",
            "Why does Habakkuk ask how long because Torah is numb and justice is distorted?",
            "Who are the Chaldeans in Habakkuk 1 and how did Babylon rise?",
            "Does God cause Babylonian violence or hold the Chaldeans morally responsible?",
            "Why does Habakkuk compare conquered people to fish caught by hook dragnet and net?",
            "What is Habakkuk's watchpost and what answer does he await?",
            "Was Habakkuk's vision literally written on clay tablets for a runner?",
            "What is the appointed time and why should the reader wait?",
            "Does Habakkuk 2:4 mean faith faithfulness fidelity or the righteous one?",
            "How do the Masoretic Text Septuagint Paul and Hebrews differ on Habakkuk 2:4?",
            "What are the five woes in Habakkuk 2?",
            "What do debtors and pledge wordplay mean in Habakkuk 2:6-8?",
            "What is unjust gain and the crying stone and timber in Habakkuk 2?",
            "Why are cities built with blood and forced labor in Habakkuk?",
            "What does the earth filled with God's glory mean in Habakkuk 2:14?",
            "How should intoxication nakedness foreskin cup and sexual humiliation in Habakkuk 2 be read?",
            "What do Lebanon animals and ecological violence mean in Habakkuk 2:17?",
            "Why does Habakkuk ridicule idols and tell the earth to be silent before the temple?",
            "What are shigionoth and selah in Habakkuk 3?",
            "Where are Teman Paran Cushan and Midian in Habakkuk's prayer?",
            "Does Habakkuk 3 retell the exodus with rivers sea sun moon and divine horses?",
            "Who is God's anointed one in Habakkuk 3:13?",
            "What is the crushed head of the wicked house in Habakkuk 3?",
            "Why does Habakkuk tremble yet wait quietly?",
            "How can Habakkuk rejoice when fig vine olive fields flock and herd fail?",
            "What does the musical subscription for the choirmaster and stringed instruments mean?",
            "What is 1QpHab Pesher Habakkuk and how did Qumran interpret the Chaldeans?",
            "What do the Babylonian Chronicles say about Nineveh Harran Carchemish and Jerusalem?",
            "How do Acts Romans Galatians and Hebrews receive Habakkuk?",
            "Does the righteous shall live by faith oppose Judaism Torah or works?",
            "Does Habakkuk authorize quietism fatalism prosperity teaching or blaming survivors?",
            "Can Chaldeans or Babylonians be mapped onto modern Iraqis Muslims cities religions or political parties?",
            "Does Habakkuk authorize conquest siege plunder genocide ethnic cleansing collective punishment or revenge?",
            "How should Habakkuk's divine violence trauma disability and ecological imagery be read?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "habakkuk")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        faithfulness = [
            note
            for note in self.habakkuk.interpretive_notes
            if "Habakkuk 2:4 contrasts an inflated or crooked person with a righteous person who lives by faithfulness or faith; Hebrew, Greek, Qumran, Pauline, and Hebrews forms must be distinguished rather than collapsed"
            in note.note
        ]
        self.assertTrue(faithfulness)
        self.assertEqual(
            faithfulness[0].dispute_status,
            "textual_variant",
        )

        agency = [
            note
            for note in self.habakkuk.interpretive_notes
            if "The announcement that YHWH is raising the Chaldeans does not erase their agency or moral culpability"
            in note.note
        ]
        self.assertTrue(agency)
        self.assertEqual(agency[0].note_type, "interpretive-caution")

        gender = [
            note
            for note in self.habakkuk.interpretive_notes
            if "Habakkuk 2:15-16 uses intoxication, nakedness, and sexualized humiliation rhetoric that must not normalize assault, victim blame, or stigma toward survivors"
            in note.note
        ]
        self.assertTrue(gender)
        self.assertEqual(gender[0].note_type, "interpretive-caution")

        ethnicity = [
            note
            for note in self.habakkuk.interpretive_notes
            if "Ancient Chaldeans and Babylonians must not be treated as ethnic or religious proxies for modern Iraqis, Middle Eastern peoples, Muslims, or any contemporary population"
            in note.note
        ]
        self.assertTrue(ethnicity)
        self.assertEqual(ethnicity[0].note_type, "interpretive-caution")

        violence = [
            note
            for note in self.habakkuk.interpretive_notes
            if "Habakkuk's protest and judgment poetry does not authorize conquest, siege, plunder, forced labor, revenge, genocide, ethnic cleansing, displacement, or collective punishment"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_habakkuk_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-habakkuk.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("habakkuk").object
            self.assertEqual(sqlite_record.to_dict(), self.habakkuk.to_dict())


if __name__ == "__main__":
    unittest.main()
