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


class ObadiahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.obadiah = cls.library.retrieve_by_id("obadiah").object

    def test_obadiah_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Obadiah, named in the superscription without patronymic or royal date",
                "YHWH in reported speech and direct address",
                "the prophetic voice reporting a message and addressing Edom",
                "Edom or Esau and its proud inhabitants, allies, sages, and warriors",
                "Jacob or Israel, Judah, Jerusalem, fugitives, and survivors",
                "the nations summoned against Edom and judged on the day of YHWH",
                "the houses of Jacob, Joseph, and Esau",
                "Benjamin, inhabitants of the Negeb and Shephelah, and exiles in Sepharad",
            }.issubset(self.obadiah.key_people)
        )
        self.assertTrue(
            {
                "Obadiah 1: superscription, vision report, divine report, and messenger among the nations",
                "Obadiah 2-9: Edom's humiliation, deceptive security, plunder, failed alliances, wisdom, and warriors",
                "Obadiah 10-14: accusation for violence against Jacob and participation in Jerusalem's calamity",
                "Obadiah 15-16: day of YHWH for all nations and reciprocal judgment",
                "Obadiah 17-21: survivors on Mount Zion, holiness, territorial restoration, Edom consumed, and YHWH's kingdom",
            }.issubset(self.obadiah.structure)
        )

    def test_obadiah_removes_inherited_minor_prophets_placeholder(self) -> None:
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
            *self.obadiah.authorship_positions,
            *self.obadiah.date_ranges,
            self.obadiah.historical_setting,
            *self.obadiah.key_people,
            *self.obadiah.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "prophetic superscription",
                "vision report",
                "divine messenger report",
                "nations oracle",
                "taunt and reversal saying",
                "accusation and judgment oracle",
                "prohibition or ironic retrospective command",
                "day-of-YHWH oracle",
                "salvation oracle",
                "territorial catalogue",
                "kingship conclusion",
            }.issubset(self.obadiah.genre)
        )
        self.assertIn(
            "Masoretic Obadiah within the Book of the Twelve",
            self.obadiah.primary_sources,
        )
        self.assertIn(
            "Old Greek Abdias and other ancient versions",
            self.obadiah.primary_sources,
        )
        self.assertIn(
            "4Q82 and other Judean Desert witnesses to the Twelve",
            self.obadiah.primary_sources,
        )

    def test_obadiah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.obadiah.content_status, "draft")
        self.assertEqual(self.obadiah.review_status, "in_review")
        self.assertTrue(self.obadiah.human_review_required)
        self.assertIsNone(self.obadiah.last_reviewed)
        self.assertEqual(self.obadiah.section_status["human_review"], "missing")
        self.assertEqual(
            self.obadiah.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.obadiah.sources}
        self.assertGreaterEqual(len(self.obadiah.claims), 20)
        self.assertGreaterEqual(len(self.obadiah.interpretive_notes), 32)
        for claim in self.obadiah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.obadiah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_obadiah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.obadiah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 14)
        self.assertTrue(self.obadiah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.obadiah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.obadiah.retrieval_metadata["common_questions"])
        self.assertTrue(self.obadiah.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "edom",
                "judgment",
                "day-of-the-lord-prophecy",
                "justice-theme",
                "restoration-theme",
                "zion",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.obadiah.related_objects
                }
            )
        )

    def test_retrieval_answers_obadiah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was the prophet Obadiah and does the book give his patronymic?",
            "When was Obadiah written?",
            "Does Obadiah describe Babylon's destruction of Jerusalem in 587 or 586 BCE?",
            "What is the relationship between Obadiah and Jeremiah 49?",
            "Who is the messenger sent among the nations in Obadiah 1?",
            "Why does Obadiah condemn Edom's pride and mountain security?",
            "What did Edom do when Jerusalem fell?",
            "Are Obadiah 12 to 14 prohibitions, accusations, or ironic retrospective commands?",
            "What does as you have done it shall be done to you mean?",
            "What is the day of YHWH upon all nations in Obadiah?",
            "What does drinking on my holy mountain mean?",
            "Who are the survivors on Mount Zion in Obadiah 17?",
            "What do the houses of Jacob Joseph and Esau mean?",
            "Where are the Negeb Shephelah Gilead and Sepharad in Obadiah 19 to 20?",
            "Does saviors in Obadiah 21 mean deliverers, judges, or conquerors?",
            "What does the kingdom shall be YHWH's mean in Obadiah?",
            "What are Old Greek Abdias and 4Q82?",
            "How is Obadiah placed within the Book of the Twelve?",
            "Does Obadiah appear as a direct quotation in the New Testament?",
            "Does Obadiah authorize hatred of Edomites, Arabs, or any modern ethnic group?",
            "Can Edom be treated as a code for Rome or a modern nation in Obadiah?",
            "Does Obadiah authorize nationalism, land seizure, genocide, or revenge?",
            "How should trauma survivors read Obadiah's judgment rhetoric?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "obadiah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        date = [
            note
            for note in self.obadiah.interpretive_notes
            if "The Jerusalem catastrophe behind verses 10-14 is often identified with the Babylonian destruction of 587/586 BCE, but seventh-century and later proposals remain"
            in note.note
        ]
        self.assertTrue(date)
        self.assertEqual(
            date[0].dispute_status,
            "major_scholarly_disagreement",
        )

        commands = [
            note
            for note in self.obadiah.interpretive_notes
            if "The force and temporal viewpoint of the repeated forms in verses 12-14 remain disputed"
            in note.note
        ]
        self.assertTrue(commands)
        self.assertEqual(
            commands[0].dispute_status,
            "lexical_uncertainty",
        )

        ethnicity = [
            note
            for note in self.obadiah.interpretive_notes
            if "Obadiah's oracle against ancient Edom must not be racialized or mapped onto Arabs, Jews, Palestinians, Jordanians, or any modern people"
            in note.note
        ]
        self.assertTrue(ethnicity)
        self.assertEqual(ethnicity[0].note_type, "interpretive-caution")

        violence = [
            note
            for note in self.obadiah.interpretive_notes
            if "The book's reciprocal judgment, fire, dispossession, and conquest imagery does not delegate revenge"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

        antisupersessionism = [
            note
            for note in self.obadiah.interpretive_notes
            if "Christian or ecclesial readings of Zion, survivors, land, and kingdom must not erase Jewish readers or replace Israel"
            in note.note
        ]
        self.assertTrue(antisupersessionism)
        self.assertEqual(
            antisupersessionism[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_obadiah_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-obadiah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("obadiah").object
            self.assertEqual(sqlite_record.to_dict(), self.obadiah.to_dict())


if __name__ == "__main__":
    unittest.main()
