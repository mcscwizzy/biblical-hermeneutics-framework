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


class JeremiahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.jeremiah = cls.library.retrieve_by_id("jeremiah").object

    def test_jeremiah_maps_major_voices_and_practical_mt_units(self) -> None:
        self.assertTrue(
            {
                "Jeremiah son of Hilkiah",
                "YHWH, whose speech Jeremiah reports",
                "Baruch son of Neriah",
                "King Josiah",
                "King Jehoiakim",
                "King Zedekiah",
                "Hananiah son of Azzur",
                "Ebed-melech the Cushite",
                "Daughter Zion or Daughter Judah personified",
                "exiles, survivors, and communal speakers",
            }.issubset(self.jeremiah.key_people)
        )
        self.assertTrue(
            {
                "Jeremiah 1: superscription, prophetic call, commission, and inaugural visions",
                "Jeremiah 2-25: poetic and prose indictments, warnings, symbolic actions, temple proclamation, confessions, and the Babylonian judgment horizon",
                "Jeremiah 26-29: conflict narratives, temple-sermon trial, competing prophets, yokes, and the letter to Babylonian exiles",
                "Jeremiah 30-33: restoration collection, Rachel's lament, field purchase, Davidic hope, and the new-covenant promise",
                "Jeremiah 34-45: siege and fall narratives, the 605 BCE scroll account, release and re-enslavement, remnant crisis, and flight to Egypt",
                "Jeremiah 46-51: Masoretic collection of oracles concerning nations, culminating in Babylon",
                "Jeremiah 52: historical appendix recounting Jerusalem's fall, deportations, and Jehoiachin's release",
            }.issubset(self.jeremiah.structure)
        )

    def test_jeremiah_removes_inherited_major_prophets_placeholder(self) -> None:
        inherited_values = {
            "Isaiah",
            "Ezekiel",
            "Call and warnings",
            "Siege and exile",
            "Hope and new covenant",
            "8th-6th centuries BCE with later shaping in some books",
            "Final forms often reflect exilic or post-exilic editing",
        }
        record_values = {
            *self.jeremiah.authorship_positions,
            *self.jeremiah.date_ranges,
            *self.jeremiah.key_people,
            *self.jeremiah.structure,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "call and commission narrative",
                "covenant lawsuit",
                "temple sermon",
                "prophetic confession or lament",
                "symbolic-action report",
                "letter",
                "salvation oracle",
                "oracle concerning a nation",
                "historical appendix",
            }.issubset(self.jeremiah.genre)
        )
        self.assertIn(
            "Masoretic Jeremiah and the shorter, differently ordered Old Greek Ieremias",
            self.jeremiah.primary_sources,
        )
        self.assertIn(
            "4QJer-a through 4QJer-e from Qumran",
            self.jeremiah.primary_sources,
        )

    def test_jeremiah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.jeremiah.content_status, "draft")
        self.assertEqual(self.jeremiah.review_status, "in_review")
        self.assertTrue(self.jeremiah.human_review_required)
        self.assertIsNone(self.jeremiah.last_reviewed)
        self.assertEqual(self.jeremiah.section_status["human_review"], "missing")
        self.assertEqual(
            self.jeremiah.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.jeremiah.sources}
        self.assertGreaterEqual(len(self.jeremiah.claims), 16)
        self.assertGreaterEqual(len(self.jeremiah.interpretive_notes), 24)
        for claim in self.jeremiah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.jeremiah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_jeremiah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.jeremiah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 12)
        self.assertTrue(self.jeremiah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.jeremiah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.jeremiah.retrieval_metadata["common_questions"])
        self.assertTrue(self.jeremiah.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "babylonian-exile",
                "new-covenant",
                "restoration-theme",
                "covenant-theme",
                "exile-theme",
                "davidic-covenant",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.jeremiah.related_objects
                }
            )
        )

    def test_retrieval_answers_jeremiah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Jeremiah and what role did Baruch play?",
            "Why is Jeremiah arranged differently in the Septuagint?",
            "Is Old Greek Jeremiah shorter than Masoretic Jeremiah?",
            "What are 4QJer-a through 4QJer-e?",
            "What are Jeremiah's confessions or laments?",
            "What was Jeremiah's temple sermon?",
            "Who was the false prophet Hananiah in Jeremiah 28?",
            "Does Jeremiah 29:11 promise individual prosperity?",
            "What does seventy years mean in Jeremiah?",
            "What is the new covenant in Jeremiah 31?",
            "Does the new covenant replace Jews with the church?",
            "What does the potter and clay mean in Jeremiah 18?",
            "Does Jeremiah's yoke command submission to abuse?",
            "How does Hebrews quote Jeremiah 31?",
            "What happened to Jeremiah after Jerusalem fell?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "jeremiah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        confessions = [
            note
            for note in self.jeremiah.interpretive_notes
            if "Jeremiah's confessions" in note.note
        ]
        self.assertTrue(confessions)
        self.assertEqual(
            confessions[0].dispute_status,
            "major_scholarly_disagreement",
        )

        editions = [
            note
            for note in self.jeremiah.interpretive_notes
            if "shorter and differently ordered Old Greek" in note.note
        ]
        self.assertTrue(editions)
        self.assertEqual(editions[0].dispute_status, "textual_variant")

        supersessionism = [
            note
            for note in self.jeremiah.interpretive_notes
            if "must not be converted into a claim that God rejected Jews"
            in note.note
        ]
        self.assertTrue(supersessionism)
        self.assertEqual(
            supersessionism[0].note_type,
            "interpretive-caution",
        )

        prosperity = [
            note
            for note in self.jeremiah.interpretive_notes
            if "individual prosperity guarantee" in note.note
        ]
        self.assertTrue(prosperity)
        self.assertEqual(prosperity[0].note_type, "interpretive-caution")

        yoke = [
            note
            for note in self.jeremiah.interpretive_notes
            if "must not authorize coercive submission to an abuser"
            in note.note
        ]
        self.assertTrue(yoke)
        self.assertEqual(yoke[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_jeremiah_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-jeremiah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("jeremiah").object
            self.assertEqual(sqlite_record.to_dict(), self.jeremiah.to_dict())


if __name__ == "__main__":
    unittest.main()
