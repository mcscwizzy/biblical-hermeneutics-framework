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


class ZephaniahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.zephaniah = cls.library.retrieve_by_id("zephaniah").object

    def test_zephaniah_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Zephaniah son of Cushi, the framing prophetic voice, and his four-generation genealogy",
                "YHWH in direct speech, reported action, judgment, presence, song, and restoration",
                "Judah, Jerusalem, officials, royal sons, foreign-clothed people, threshold leapers, merchants, and complacent residents",
                "the humble and poor, the remnant, dispersed worshipers, Daughter Zion, Daughter Jerusalem, and returning exiles",
                "Philistines, Cherethites, Moabites, Ammonites, Cushites, Assyrians, Ninevites, peoples, kingdoms, and nations",
                "Jerusalem's officials, rulers, judges, prophets, priests, violent people, shameless people, and faithful remnant",
                "humans, animals, birds, fish, ruins, flocks, wild creatures, creation, and later interpreters",
            }.issubset(self.zephaniah.key_people)
        )
        self.assertTrue(
            {
                "Zephaniah 1:1: superscription dating the word to Josiah and naming Zephaniah's four-generation genealogy",
                "Zephaniah 1:2-6: universal sweep, creation reversal, Judah and Jerusalem, idolatry, astral worship, divided allegiance, and apostasy",
                "Zephaniah 1:7-13: silence, sacrificial summons, elites and merchants, violence and fraud, Jerusalem searched with lamps, and complacency",
                "Zephaniah 1:14-18: the near great Day of YHWH as battle cry, wrath, darkness, distress, blood, and wealth unable to deliver",
                "Zephaniah 2:1-3: imperative gathering and summons to seek YHWH, righteousness, and humility before the day",
                "Zephaniah 2:4-7: oracle against the Philistine coast and promise that the remnant of Judah will possess it",
                "Zephaniah 2:8-11: Moab and Ammon's taunts, reversal, remnant possession, and nations bowing to YHWH",
                "Zephaniah 2:12-15: brief oracle against Cush and taunt over Assyria and desolate Nineveh",
                "Zephaniah 3:1-7: woe over the rebellious city, corrupt leaders, daily justice, nations judged, and refused correction",
                "Zephaniah 3:8-13: courtroom summons, gathering kingdoms, purified speech, dispersed worshipers, humbled remnant, refuge, truth, and security",
                "Zephaniah 3:14-20: Daughter Zion's hymn, YHWH present as king and warrior, disputed quiet-love language, gathering, return, honor, and restoration",
            }.issubset(self.zephaniah.structure)
        )

    def test_zephaniah_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Hosea",
            "Amos",
            "Jonah",
        }
        record_values = {
            *self.zephaniah.authorship_positions,
            *self.zephaniah.date_ranges,
            self.zephaniah.historical_setting,
            *self.zephaniah.key_people,
            *self.zephaniah.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "superscription and prophetic word",
                "prophetic judgment oracle and creation reversal",
                "cultic accusation and sacrifice metaphor",
                "Day-of-YHWH announcement, lament, and battle cry",
                "imperative summons to gather and seek",
                "nation oracle, taunt, and reversal",
                "woe oracle, city address, disputation, and courtroom accusation",
                "remnant promise and salvation oracle",
                "hymn and Daughter-Zion address",
                "divine-warrior, divine-presence, and restoration promise",
            }.issubset(self.zephaniah.genre)
        )
        self.assertIn(
            "Masoretic Zephaniah within the Book of the Twelve",
            self.zephaniah.primary_sources,
        )
        self.assertIn(
            "Old Greek Sophonias and other ancient versions",
            self.zephaniah.primary_sources,
        )
        self.assertIn(
            "Judean Desert manuscripts of Zephaniah and Pesher Zephaniah",
            self.zephaniah.primary_sources,
        )

    def test_zephaniah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.zephaniah.content_status, "draft")
        self.assertEqual(self.zephaniah.review_status, "in_review")
        self.assertTrue(self.zephaniah.human_review_required)
        self.assertIsNone(self.zephaniah.last_reviewed)
        self.assertEqual(
            self.zephaniah.section_status["human_review"],
            "missing",
        )
        self.assertEqual(
            self.zephaniah.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.zephaniah.sources}
        self.assertGreaterEqual(len(self.zephaniah.claims), 24)
        self.assertGreaterEqual(len(self.zephaniah.interpretive_notes), 40)
        for claim in self.zephaniah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.zephaniah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_zephaniah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.zephaniah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 18)
        self.assertTrue(self.zephaniah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.zephaniah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.zephaniah.retrieval_metadata["common_questions"])
        self.assertTrue(self.zephaniah.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "nineveh",
                "divine-justice",
                "judgment",
                "hope-theme",
                "exile-theme",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.zephaniah.related_objects
                }
            )
        )

    def test_retrieval_answers_zephaniah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Zephaniah son of Cushi and was Hezekiah his royal ancestor?",
            "When was Zephaniah written during Josiah's reign before or after the reform?",
            "Does Zephaniah predict a Scythian invasion?",
            "How does Zephaniah 1 reverse creation and Genesis flood language?",
            "Who worshiped Baal the host of heaven and Milcom in Zephaniah?",
            "What do foreign clothing and leaping over the threshold mean in Zephaniah 1?",
            "What are the Fish Gate Second Quarter hills and Maktesh in Jerusalem?",
            "Why does Zephaniah command silence before the Lord's sacrifice and consecrated guests?",
            "What does searching Jerusalem with lamps and thickening on dregs mean?",
            "What is the great Day of YHWH in Zephaniah 1?",
            "Can silver or gold deliver anyone on Zephaniah's day of wrath?",
            "Why does Zephaniah summon the shameless nation to seek humility?",
            "Who are the Cherethites and what are Canaan and the Philistine coast?",
            "Why are Moab and Ammon compared with Sodom and Gomorrah?",
            "Who are the Cushites in Zephaniah 2:12?",
            "Was Nineveh already destroyed when Zephaniah described its desolation?",
            "Which rebellious polluted oppressing city is addressed in Zephaniah 3?",
            "Why are Jerusalem's rulers lions judges wolves prophets reckless and priests profane?",
            "What does wait for me until I gather kingdoms for judgment mean?",
            "What is the purified lip or speech promised to the peoples?",
            "Who are the worshipers from beyond the rivers of Cush?",
            "What defines Zephaniah's humble poor remnant?",
            "Does Zephaniah 3:17 say God is silent in love or renews with love?",
            "How does YHWH rejoice and sing over Daughter Zion?",
            "How should Zephaniah's language about the disabled outcast and shame be read?",
            "What are the Masoretic Text Old Greek Sophonias Judean Desert manuscripts and Pesher Zephaniah?",
            "How do Genesis Deuteronomy Isaiah Jeremiah Amos Micah Nahum Habakkuk Joel and Zechariah relate to Zephaniah?",
            "Does Matthew 13 or Revelation quote or receive Zephaniah?",
            "Does Zephaniah authorize anti-African racism through Cushi or Cush?",
            "Can Philistia Moab Ammon Cush Assyria Nineveh Judah or Jerusalem be mapped onto modern peoples or states?",
            "Does Zephaniah authorize war genocide ethnic cleansing displacement collective punishment or revenge?",
            "How should Zephaniah's divine violence trauma animal harm ecological destruction and disaster imagery be read?",
            "Does seeking humility promise prosperity safety or immunity from suffering?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "zephaniah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        genealogy = [
            note
            for note in self.zephaniah.interpretive_notes
            if "Zephaniah's four-generation genealogy is unusually long, but neither Cushi's name nor the named Hezekiah securely proves African ancestry or royal descent"
            in note.note
        ]
        self.assertTrue(genealogy)
        self.assertEqual(
            genealogy[0].dispute_status,
            "major_scholarly_disagreement",
        )

        city = [
            note
            for note in self.zephaniah.interpretive_notes
            if "The unnamed rebellious, polluted, and oppressing city in Zephaniah 3:1 is most often read as Jerusalem in its literary context, though the absence of a name and the transition from nation oracles require qualification"
            in note.note
        ]
        self.assertTrue(city)
        self.assertEqual(city[0].note_type, "interpretive-caution")

        ethnicity = [
            note
            for note in self.zephaniah.interpretive_notes
            if "Cushi and Cush must not be used to construct anti-Black or anti-African readings, while Philistia, Moab, and Ammon must not be mapped onto Palestinians, Arabs, or modern neighboring peoples"
            in note.note
        ]
        self.assertTrue(ethnicity)
        self.assertEqual(ethnicity[0].note_type, "interpretive-caution")

        disability = [
            note
            for note in self.zephaniah.interpretive_notes
            if "The promise to gather those who limp or are afflicted and collect the outcast must not turn disability into a synonym for sin, defect, helplessness, or lesser worth"
            in note.note
        ]
        self.assertTrue(disability)
        self.assertEqual(disability[0].note_type, "interpretive-caution")

        violence = [
            note
            for note in self.zephaniah.interpretive_notes
            if "Zephaniah's judgment poetry does not authorize war, siege, genocide, ethnic cleansing, displacement, collective punishment, colonial possession, ecological destruction, or revenge"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_zephaniah_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-zephaniah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("zephaniah").object
            self.assertEqual(
                sqlite_record.to_dict(),
                self.zephaniah.to_dict(),
            )


if __name__ == "__main__":
    unittest.main()
