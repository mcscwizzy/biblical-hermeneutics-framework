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


class SecondJohnRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("2-john").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "the elder, the named sender",
            "the elect lady and her children",
            "deceivers and antichrist figures",
            "the elect sister's children",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "2 John 1:1-3",
            "2 John 1:4-6",
            "2 John 1:7-11",
            "2 John 1:12-13",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("James", "Peter", "Asia Minor", "persecution"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not name", self.record.historical_setting)
        self.assertTrue(
            any("elder" in position for position in self.record.authorship_positions)
        )

    def test_record_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.record.content_status, "draft")
        self.assertEqual(self.record.review_status, "in_review")
        self.assertTrue(self.record.human_review_required)
        self.assertIsNone(self.record.last_reviewed)
        self.assertEqual(self.record.section_status["human_review"], "missing")
        self.assertEqual(self.record.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.record.sources}
        self.assertGreaterEqual(len(self.record.claims), 24)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 32)
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
        self.assertGreaterEqual(len(self.record.greek_words), 25)
        self.assertTrue(
            {
                "john-son-of-zebedee",
                "agape",
                "incarnation",
                "witness-theme",
                "people-of-god-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 2 John and when?",
            "Did the apostle John write 2 John?",
            "Who is the elder in 2 John?",
            "Who is the elect lady in 2 John?",
            "Is the elect lady a church or a woman?",
            "Who are the elect lady's children?",
            "Who is the elect sister in 2 John?",
            "How is 2 John related to 1 John?",
            "How is 2 John related to 3 John?",
            "How is 2 John related to the Gospel of John?",
            "What does truth mean in 2 John?",
            "What does love mean in 2 John?",
            "What do grace mercy and peace mean in 2 John?",
            "What does walking in truth mean?",
            "What is the old commandment in 2 John?",
            "What does walking in love mean?",
            "Who are the deceivers in 2 John?",
            "What does Jesus Christ coming in flesh mean?",
            "Who is the antichrist in 2 John?",
            "What does going ahead mean in 2 John?",
            "What is the teaching of Christ in 2 John?",
            "What does remaining in the teaching mean?",
            "What does having the Father and Son mean?",
            "Should Christians receive teachers into the house?",
            "Does 2 John ban hospitality?",
            "What does greeting a false teacher mean?",
            "What does sharing in evil works mean?",
            "Does 2 John authorize shunning?",
            "Does 2 John support church surveillance?",
            "Does 2 John justify schism?",
            "What do paper and ink mean in 2 John?",
            "What does face to face mean in 2 John?",
            "What joy does the elder hope to complete?",
            "Was 2 John sent to a house church?",
            "What is the genre of 2 John?",
            "Where was 2 John written?",
            "Were the opponents Docetists or gnostics?",
            "How should antichrist language be used today?",
            "How should 2 John guide hospitality and safety?",
            "How should truth and love in 2 John shape care for creation?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"2 John {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "2-john")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Opponents", "dehumanization", "schism"),
            ("Hospitality", "coercive exclusion", "surveillance"),
            ("Authority", "spiritual abuse", "anti-intellectualism"),
            ("Gender", "misogyny", "anti-LGBTQ"),
            ("Application", "forced conversion", "religious violence"),
            ("Love", "ecological neglect", "creation"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-2-john.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("2-john").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
