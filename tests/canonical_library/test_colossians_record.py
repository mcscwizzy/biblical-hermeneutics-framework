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


class ColossiansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("colossians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul and Timothy",
            "Epaphras",
            "Tychicus and Onesimus",
            "Nympha",
            "Archippus",
            "enslaved people and masters",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Colossians 1:1-23",
            "Colossians 1:24-2:23",
            "Colossians 3:1-4:6",
            "Colossians 4:7-18",
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
            "Corinth",
            "mission",
            "church formation",
            "pastoral instruction",
        ):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "Pauline authorship" in position
                and "disputed" in position
                for position in self.record.authorship_positions
            )
        )
        self.assertIn("cannot be reconstructed as one system", self.record.historical_setting)

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
        self.assertGreaterEqual(len(self.record.interpretive_notes), 46)
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
        self.assertGreaterEqual(len(external), 22)
        self.assertGreaterEqual(len(self.record.hebrew_words), 10)
        self.assertGreaterEqual(len(self.record.greek_words), 20)
        self.assertTrue(
            {
                "paul",
                "christology",
                "union-with-christ",
                "grace",
                "faith",
                "new-creation-theme",
                "people-of-god-theme",
                "wisdom-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Colossians and when?",
            "Was Colossians written by Paul or a Pauline-school author?",
            "Was Colossians written from Rome Ephesus or Caesarea?",
            "How is Colossians related to Ephesians and Philemon?",
            "Who were Epaphras Tychicus and Onesimus?",
            "What does image of the invisible God mean?",
            "What does firstborn of all creation mean?",
            "Is Colossians 1:15-20 an early hymn?",
            "What does all fullness mean in Colossians?",
            "What is lacking in Christ's afflictions?",
            "What is the mystery hidden for ages?",
            "Who were the Colossian opponents?",
            "What does philosophy and empty deceit mean?",
            "What are the elemental powers in Colossians?",
            "How are circumcision and baptism connected?",
            "What is the erased handwritten record in Colossians 2?",
            "What does disarmed rulers and powers mean?",
            "Does Colossians attack Torah Sabbath or Jewish festivals?",
            "What is angel worship in Colossians?",
            "What were the Colossian visions?",
            "Does Colossians teach asceticism or body shame?",
            "What does seek the things above mean?",
            "What is the old and new humanity?",
            "What does neither Greek nor Jew Scythian slave free mean?",
            "Does the Colossians household code endorse patriarchy or child abuse?",
            "Does Colossians endorse slavery or worker exploitation?",
            "Who was Nympha and what is the textual variant?",
            "Who was Archippus?",
            "What was the letter from Laodicea?",
            "Why does Paul mention his autograph and chains?",
            "Does Colossians support dangerous spiritual warfare or exorcism?",
            "How can Colossians be read without antisemitism misogyny or slavery apologetics?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Colossians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "colossians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("festival", "Sabbath", "antisemitism", "supersessionism"),
            ("household code", "patriarchal", "abuse"),
            ("Enslaved", "slavery", "worker exploitation"),
            ("angel", "mental illness", "dangerous exorcism"),
            ("Ascetic", "body shame", "medical neglect"),
            ("Scythian", "ethnic contempt", "racism"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-colossians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("colossians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
