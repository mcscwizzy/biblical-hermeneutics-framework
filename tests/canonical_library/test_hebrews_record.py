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


class HebrewsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("hebrews").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "anonymous speaker",
            "Jesus",
            "Moses, Aaron, Melchizedek, Abraham, and Sarah",
            "Timothy and people from Italy",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Hebrews 1:1-4:13",
            "Hebrews 4:14-10:39",
            "Hebrews 11:1-12:29",
            "Hebrews 13:1-25",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("James", "Peter", "John", "Asia Minor", "false teaching"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not name", self.record.historical_setting)
        self.assertTrue(
            any("anonymous" in position for position in self.record.authorship_positions)
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
                "jesus",
                "moses",
                "priesthood",
                "temple",
                "sacrifice-theme",
                "faith",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Hebrews and when?",
            "Why is Hebrews anonymous?",
            "Did Paul write Hebrews?",
            "Was Hebrews written before the temple was destroyed?",
            "Was Hebrews sent to Rome or Jerusalem?",
            "Is Hebrews a sermon or a letter?",
            "Who were the original audience of Hebrews?",
            "What does Hebrews say about angels?",
            "What is the rest in Hebrews 4?",
            "What does the word of God mean in Hebrews 4?",
            "How is Jesus a high priest in Hebrews?",
            "Who is Melchizedek in Hebrews?",
            "What does Hebrews 6 impossible to restore mean?",
            "What is the better covenant in Hebrews?",
            "Does Hebrews replace Israel or Judaism?",
            "What does diatheke mean in Hebrews?",
            "What is the heavenly sanctuary in Hebrews?",
            "What does once for all sacrifice mean?",
            "Why does Hebrews talk about blood?",
            "Does Hebrews denigrate Jewish sacrifice?",
            "What does perfection mean in Hebrews?",
            "Does Hebrews say the law is abolished?",
            "What is faith in Hebrews 11?",
            "Who are the women in Hebrews 11?",
            "What is the cloud of witnesses?",
            "Does Hebrews justify abusive discipline?",
            "Why are Sinai and Zion contrasted?",
            "What is the unshakable kingdom?",
            "What does Hebrews say about hospitality and prisoners?",
            "What does Hebrews say about marriage and money?",
            "Should leaders be obeyed without question in Hebrews 13?",
            "What is the altar in Hebrews 13?",
            "What does outside the camp mean?",
            "Who is Timothy in Hebrews 13?",
            "Who are those from Italy?",
            "What does Hebrews say about apostasy?",
            "Can someone repent after Hebrews 10?",
            "Does Hebrews promote supersessionism?",
            "What manuscripts preserve Hebrews?",
            "How can Hebrews be read without antisemitism or spiritual abuse?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Hebrews {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "hebrews")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Supersessionism", "Judaism", "Torah"),
            ("Warning", "terror", "spiritual abuse"),
            ("Discipline", "abuse", "victim"),
            ("Leadership", "authoritarian", "accountability"),
            ("Blood", "violence", "trauma"),
            ("Application", "forced conversion", "ecological neglect"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-hebrews.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("hebrews").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
