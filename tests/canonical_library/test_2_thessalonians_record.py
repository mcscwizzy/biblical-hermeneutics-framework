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


class SecondThessaloniansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("2-thessalonians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul, Silvanus, and Timothy",
            "Thessalonian assembly",
            "man of lawlessness",
            "restrainer",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "2 Thessalonians 1:1-12",
            "2 Thessalonians 2:1-17",
            "2 Thessalonians 3:1-18",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        values = {
            *self.record.authorship_positions,
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
            "Titus",
            "Rome",
            "Ephesus",
            "mission",
            "church formation",
            "pastoral instruction",
        ):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(
            any("disputed" in position for position in self.record.authorship_positions)
        )
        self.assertIn("does not identify", self.record.historical_setting)

    def test_record_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.record.content_status, "draft")
        self.assertEqual(self.record.review_status, "in_review")
        self.assertTrue(self.record.human_review_required)
        self.assertIsNone(self.record.last_reviewed)
        self.assertEqual(self.record.section_status["human_review"], "missing")
        self.assertEqual(self.record.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.record.sources}
        self.assertGreaterEqual(len(self.record.claims), 26)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 40)
        for claim in self.record.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_record_has_sources_lexical_data_and_graph_links(self) -> None:
        external = [
            source
            for source in self.record.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 20)
        self.assertGreaterEqual(len(self.record.hebrew_words), 10)
        self.assertGreaterEqual(len(self.record.greek_words), 20)
        self.assertTrue(
            {
                "paul",
                "thessalonica",
                "second-coming",
                "final-judgment",
                "perseverance",
                "faith",
                "grace",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 2 Thessalonians and when?",
            "Why is the authorship of 2 Thessalonians disputed?",
            "Was 2 Thessalonians written before or after 1 Thessalonians?",
            "Who were Paul Silvanus and Timothy?",
            "Who persecuted the Thessalonians?",
            "What does eternal destruction mean?",
            "Does vengeance permit Christians to harm enemies?",
            "What are the coming and gathering?",
            "What is the rebellion or apostasy?",
            "Who is the man of lawlessness?",
            "Is the man of lawlessness the antichrist?",
            "What temple does 2 Thessalonians 2 mean?",
            "Who or what is the restrainer?",
            "What does katechon mean?",
            "What are Satanic signs and wonders?",
            "What is the strong delusion?",
            "What does election mean in chapter 2?",
            "What are the traditions to hold fast?",
            "Was there a forged letter claiming to be from Paul?",
            "How does the autograph claim relate to pseudepigraphy?",
            "What does pray that the word may run mean?",
            "What does if anyone will not work neither eat mean?",
            "Does 2 Thessalonians shame unemployed or disabled people?",
            "Who were the idle or disruptive people?",
            "What does working quietly mean?",
            "Should a disruptive member be shunned?",
            "How should church discipline treat someone as a sibling?",
            "What is the Lord of peace benediction?",
            "Does 2 Thessalonians support date setting?",
            "Can politicians be identified as the man of lawlessness?",
            "How is 2 Thessalonians related to Acts and 1 Thessalonians?",
            "How can 2 Thessalonians be read without fear conspiracy or worker shaming?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"2 Thessalonians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "2-thessalonians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Judgment", "vengeance", "religious violence"),
            ("man of lawlessness", "political", "conspiracy"),
            ("restrainer", "uncertain", "dogmatic"),
            ("Work", "disabled", "unemployed", "exploitation"),
            ("Discipline", "sibling", "public shaming", "spiritual abuse"),
            ("Apocalyptic", "date setting", "rapture panic", "ecological"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-2-thessalonians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id(
                "2-thessalonians"
            ).object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
