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


class ThirdJohnRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("3-john").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "the elder, the named sender",
            "Gaius, the named addressee",
            "Diotrephes",
            "Demetrius",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "3 John 1:1-4",
            "3 John 1:5-8",
            "3 John 1:9-12",
            "3 John 1:13-15",
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
        self.assertGreaterEqual(len(self.record.claims), 25)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 34)
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
                "apostleship",
                "witness-theme",
                "people-of-god-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 3 John and when?",
            "Did the apostle John write 3 John?",
            "Who is the elder in 3 John?",
            "Who is Gaius in 3 John?",
            "Is Gaius in 3 John the same as another New Testament Gaius?",
            "Who are the brothers and strangers in 3 John?",
            "Who is Diotrephes in 3 John?",
            "Why does Diotrephes love first place?",
            "What authority did Diotrephes refuse?",
            "Who is Demetrius in 3 John?",
            "Why is Demetrius commended?",
            "How is 3 John related to 1 John?",
            "How is 3 John related to 2 John?",
            "How is 3 John related to the Gospel of John?",
            "What does truth mean in 3 John?",
            "What does walking in truth mean in 3 John?",
            "What does health and soul mean in 3 John?",
            "Does 3 John teach the prosperity gospel?",
            "What does faithful work for strangers mean?",
            "What hospitality does 3 John commend?",
            "What does sending worthily of God mean?",
            "What does going out for the Name mean?",
            "Who are the Gentiles in 3 John?",
            "Why did the travelers accept nothing from Gentiles?",
            "What does coworkers with truth mean?",
            "What did the elder write to the church?",
            "What are Diotrephes's malicious words?",
            "Whom did Diotrephes refuse and expel?",
            "Does 3 John authorize church expulsion?",
            "What does imitate good not evil mean?",
            "What is the testimony of truth about Demetrius?",
            "What do pen and ink mean in 3 John?",
            "What does face to face mean in 3 John?",
            "Who are the friends in 3 John?",
            "What does greet the friends by name mean?",
            "What is the genre of 3 John?",
            "Where was 3 John written?",
            "Does 3 John support authoritarian leadership?",
            "How should 3 John guide hospitality and safety?",
            "How should truth and hospitality in 3 John shape care for creation?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"3 John {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "3-john")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Diotrephes", "dehumanization", "schism"),
            ("Hospitality", "coercive exclusion", "surveillance"),
            ("Leadership", "spiritual abuse", "anti-intellectualism"),
            ("Health", "prosperity", "disability"),
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
            database = Path(tmp) / "phase-5-3-john.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("3-john").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
