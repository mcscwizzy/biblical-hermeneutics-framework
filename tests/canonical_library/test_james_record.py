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


class JamesRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("james").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "James, the named sender",
            "twelve tribes in the diaspora",
            "Abraham, Rahab, Job, and Elijah",
            "teachers, elders, laborers, merchants, rich and poor hearers",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "James 1:1-27",
            "James 2:1-26",
            "James 3:1-18",
            "James 4:1-5:6",
            "James 5:7-20",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
            "Peter",
            "John",
            "Asia Minor",
            "persecution",
            "false teaching",
        ):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not identify", self.record.historical_setting)
        self.assertTrue(
            any(
                "brother of Jesus" in position
                for position in self.record.authorship_positions
            )
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
        self.assertGreaterEqual(len(self.record.claims), 30)
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
                "james-brother-of-jesus",
                "wisdom-theme",
                "faith",
                "justice-theme",
                "abraham",
                "elijah",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote James and when?",
            "Was James written by the brother of Jesus?",
            "Was James written from Jerusalem?",
            "Who are the twelve tribes in the diaspora?",
            "Was James written only to Jewish Christians?",
            "What genre is James?",
            "How is James related to Jewish wisdom?",
            "Does James preserve sayings of Jesus?",
            "Does James contradict Paul or Romans?",
            "What does testing produce in James 1?",
            "What does perfect mean in James?",
            "What does double-minded mean in James?",
            "Does God tempt people in James 1?",
            "What are firstfruits in James 1?",
            "What is the implanted word?",
            "What is pure religion in James 1?",
            "What is the law of liberty?",
            "What is partiality in James 2?",
            "What is the royal law?",
            "Can faith without works save?",
            "How are Abraham and Rahab justified by works?",
            "Does James teach salvation by works?",
            "Why are teachers judged more strictly?",
            "What does James say about the tongue and fire?",
            "What is wisdom from above?",
            "What causes conflicts in James 4?",
            "What is friendship with the world?",
            "What does the spirit in James 4:5 mean?",
            "What does James say about judging the law?",
            "Why does James say you do not know tomorrow?",
            "What does James condemn about rich oppressors?",
            "What does James say about withheld wages?",
            "What is the coming of the Lord in James 5?",
            "What does James mean by Job's endurance?",
            "Does James prohibit every oath?",
            "What does anointing the sick with oil mean?",
            "Does prayer guarantee physical healing?",
            "What does confess your sins to one another mean?",
            "How is Elijah an example of prayer?",
            "What does covering sins by restoring a wanderer mean?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"James {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "james")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Faith and works", "Paul", "different rhetorical"),
            ("Wealth", "poor", "poverty romanticization"),
            ("Healing", "medical neglect", "illness shame"),
            ("Confession", "coercive", "public shaming"),
            ("Teachers", "authoritarian", "spiritual abuse"),
            ("Application", "forced conversion", "ecological neglect"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-james.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("james").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
