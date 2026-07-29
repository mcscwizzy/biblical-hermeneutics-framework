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


class PhilemonRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("philemon").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul and Timothy",
            "Philemon, Apphia, and Archippus",
            "Onesimus",
            "Epaphras, Mark, Aristarchus, Demas, and Luke",
            "house assembly",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in ("Philemon 1-7", "Philemon 8-22", "Philemon 23-25"):
            self.assertIn(anchor, structure)

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
            "Titus",
            "Rome",
            "Corinth",
            "Ephesus",
            "mission",
            "church formation",
            "pastoral instruction",
        ):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not identify", self.record.historical_setting)
        self.assertTrue(
            any("Pauline" in position for position in self.record.authorship_positions)
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
                self.assertIn(
                    claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES
                )
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
                "philemon-of-colossae",
                "onesimus",
                "timothy",
                "colossians",
                "grace",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Philemon and when?",
            "Is Pauline authorship of Philemon disputed?",
            "Where was Paul imprisoned when he wrote Philemon?",
            "Was Philemon written from Rome or Ephesus?",
            "Was Philemon sent to Colossae?",
            "How is Philemon related to Colossians?",
            "Who were Philemon Apphia and Archippus?",
            "Was Apphia Philemon's wife?",
            "Why is a house assembly addressed?",
            "Who was Onesimus?",
            "Was Onesimus a fugitive slave?",
            "Did Onesimus steal from Philemon?",
            "Did Onesimus convert through Paul?",
            "What does Onesimus useful wordplay mean?",
            "What does Paul my child mean?",
            "What does splanchna mean in Philemon?",
            "Why did Paul send Onesimus back?",
            "Does Philemon require returning people to abusers?",
            "Why does Paul appeal instead of command?",
            "Is Paul's appeal coercive?",
            "What does without your consent mean?",
            "What does perhaps he was separated mean?",
            "What does no longer as a slave mean?",
            "Does Philemon command manumission?",
            "Does Philemon endorse slavery?",
            "What does beloved brother mean?",
            "What debt did Onesimus owe?",
            "Did Onesimus steal money?",
            "What does charge it to me mean?",
            "What does Philemon owe Paul?",
            "What does receive him as me mean?",
            "What does even more than I say mean?",
            "What does obedience mean in Philemon?",
            "Why does Paul request a guest room?",
            "Who were Epaphras Mark Aristarchus Demas and Luke?",
            "Does Philemon reveal what happened afterward?",
            "Is Onesimus in Philemon the later bishop?",
            "What does Papyrus 87 preserve?",
            "Does Codex Sinaiticus contain Philemon?",
            "How can Philemon be read without slavery apologetics or coercive reconciliation?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Philemon {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "philemon")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Slavery", "enslaved", "slavery apologetics"),
            ("Return", "abusers", "trafficking"),
            ("Consent", "coercion", "clerical"),
            ("Debt", "theft", "debt bondage"),
            ("Manumission", "not explicitly", "outcome"),
            ("Application", "forced conversion", "ecological neglect"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-philemon.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("philemon").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
