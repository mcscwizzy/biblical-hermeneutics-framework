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


class JudeRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("jude").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Jude, the named sender",
            "James",
            "Michael",
            "Enoch",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Jude 1:1-4",
            "Jude 1:5-16",
            "Jude 1:17-23",
            "Jude 1:24-25",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("Peter", "John", "Asia Minor", "persecution"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not name", self.record.historical_setting)
        self.assertTrue(
            any("brother of James" in position for position in self.record.authorship_positions)
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
        self.assertGreaterEqual(len(self.record.claims), 28)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 36)
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
        self.assertGreaterEqual(len(self.record.greek_words), 30)
        self.assertTrue(
            {
                "final-judgment",
                "perseverance",
                "apostleship",
                "messiah-theme",
                "people-of-god-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Jude and when?",
            "Is Jude the apostle Judas?",
            "Why does Jude call himself brother of James?",
            "Who are the called beloved and kept in Jude?",
            "What is the faith once delivered in Jude?",
            "Who are the intruders in Jude?",
            "Does Jude say Jesus saved Israel from Egypt?",
            "What angels sinned and are kept in chains in Jude?",
            "How does Jude use Sodom and Gomorrah?",
            "What are dreamers flesh lordship and glories in Jude?",
            "Why do Michael and the devil dispute over Moses's body?",
            "Where does Jude's Moses tradition come from?",
            "What do Cain Balaam and Korah mean in Jude?",
            "What are love feasts in Jude?",
            "What are hidden reefs shepherds clouds trees waves and stars?",
            "Why does Jude quote Enoch?",
            "Does Jude treat 1 Enoch as scripture?",
            "How is Jude related to 2 Peter?",
            "Who are the apostles and scoffers in Jude?",
            "What does devoid of the Spirit mean in Jude?",
            "What does build yourselves up in your most holy faith mean?",
            "What does praying in the Holy Spirit mean in Jude?",
            "What does keep yourselves in God's love mean?",
            "What does waiting for Jesus's mercy mean?",
            "Why do Jude 22 and 23 differ across manuscripts?",
            "Who should receive mercy in Jude?",
            "What does save others by snatching them from fire mean?",
            "What is the garment stained by flesh in Jude?",
            "What does able to keep you from stumbling mean?",
            "What is the doxology of Jude?",
            "What does before all time now and forever mean in Jude?",
            "What is Jude's genre?",
            "Where was Jude written?",
            "Who were Jude's opponents?",
            "Does Jude authorize heresy hunting?",
            "Does Jude support sexual shaming?",
            "How should Jude be taught without dehumanizing opponents?",
            "How should Jude be applied without coercive discipline?",
            "Does Jude justify violence or forced conversion?",
            "How should Jude's judgment imagery shape care for creation?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Jude {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "jude")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Intruders", "dehumanization", "heresy-hunting"),
            ("Sexual", "shaming", "anti-LGBTQ"),
            ("Discipline", "surveillance", "spiritual abuse"),
            ("Leadership", "authoritarian", "anti-intellectualism"),
            ("Application", "forced conversion", "religious violence"),
            ("Judgment", "ecological neglect", "creation"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-jude.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("jude").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
