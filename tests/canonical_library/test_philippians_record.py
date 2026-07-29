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


class PhilippiansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("philippians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul and Timothy",
            "Epaphroditus",
            "Euodia and Syntyche",
            "overseers and deacons",
            "Caesar's household",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Philippians 1:1-30",
            "Philippians 2:1-30",
            "Philippians 3:1-4:1",
            "Philippians 4:2-23",
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
                "strong consensus" in position
                and "Paul" in position
                for position in self.record.authorship_positions
            )
        )
        self.assertIn("not securely identified", self.record.historical_setting)

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
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
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
        self.assertGreaterEqual(len(external), 22)
        self.assertGreaterEqual(len(self.record.hebrew_words), 10)
        self.assertGreaterEqual(len(self.record.greek_words), 20)
        self.assertTrue(
            {
                "paul",
                "philippi",
                "christology",
                "resurrection-theme",
                "perseverance",
                "faith",
                "grace",
                "union-with-christ",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Philippians and what was Timothy's role?",
            "Was Philippians written from Rome Ephesus or Caesarea?",
            "When was Philippians written?",
            "Is Philippians one letter or several letters?",
            "What was Roman colonial Philippi like?",
            "Who were the opponents in Philippians?",
            "Why were rival preachers proclaiming Christ?",
            "What does to live is Christ and to die is gain mean?",
            "Does Philippians glorify suffering or suicide?",
            "What does politeuesthe mean in Philippians 1:27?",
            "Is Philippians 2:6-11 an early hymn?",
            "What does harpagmos mean?",
            "What does Christ emptied himself mean?",
            "How should work out your salvation be understood?",
            "Who were Timothy and Epaphroditus?",
            "Was Epaphroditus's illness a punishment?",
            "Why does Paul say dogs and mutilation?",
            "Does Philippians attack Jews or circumcision?",
            "What does confidence in the flesh mean?",
            "What does knowing Christ mean?",
            "Had Paul already attained resurrection or perfection?",
            "What is heavenly citizenship?",
            "Who were Euodia and Syntyche?",
            "Who is the true companion in Philippians 4:3?",
            "Does Philippians blame women for church conflict?",
            "How should anxiety and prayer in Philippians 4 be applied?",
            "What does I can do all things mean?",
            "What did Paul mean by contentment?",
            "Was the Philippians' gift patronage or friendship?",
            "Who belonged to Caesar's household?",
            "Does Philippians support nationalism or militarism?",
            "How can Philippians be read without antisemitism misogyny or ableism?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Philippians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "philippians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("circumcision", "antisemitism", "supersessionism"),
            ("Euodia", "Syntyche", "misogyny"),
            ("illness", "medical neglect", "disability"),
            ("anxiety", "mental-health", "shame"),
            ("gift", "prosperity", "financial extraction"),
            ("citizenship", "nationalism", "militarism"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-philippians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("philippians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
