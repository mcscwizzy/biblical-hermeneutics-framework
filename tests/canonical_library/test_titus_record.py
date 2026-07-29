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


class TitusRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("titus").object

    def test_record_maps_major_groups_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul and Titus",
            "elders and overseers",
            "older men, older women, younger women, and younger men",
            "enslaved people",
            "Artemas or Tychicus",
            "Zenas and Apollos",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in ("Titus 1:1-16", "Titus 2:1-15", "Titus 3:1-15"):
            self.assertIn(anchor, structure)

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        values = {
            *self.record.authorship_positions,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
            "Rome",
            "Corinth",
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
        self.assertIn("does not establish", self.record.historical_setting)

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
                "titus-the-companion",
                "elders",
                "grace",
                "faith",
                "justification",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Titus and when?",
            "Why is Pauline authorship of Titus disputed?",
            "Was Titus written by a secretary or Pauline school?",
            "Where is Crete and what was its Roman context?",
            "How is Titus related to Acts 1 Timothy and 2 Timothy?",
            "Why was Titus left in Crete?",
            "Are elders and overseers the same role in Titus?",
            "What are the household qualifications for elders?",
            "Who were the rebellious people and circumcision group?",
            "Does Titus attack all Jewish people?",
            "Who said Cretans are always liars?",
            "Is the Cretan quotation from Epimenides?",
            "Does Titus authorize ethnic contempt toward Cretans?",
            "What does pure to the pure mean?",
            "What does Titus teach older men and older women?",
            "What does Titus teach younger women and younger men?",
            "Does Titus require women to stay at home?",
            "What does Titus say about enslaved people?",
            "Does Titus defend slavery?",
            "What does the grace of God train people to do?",
            "What is the appearing epiphaneia in Titus 2?",
            "What does Christ gave himself to redeem mean?",
            "What does peculiar people zealous for good works mean?",
            "How should Christians relate to rulers in Titus 3?",
            "Does submission to rulers require obeying injustice?",
            "What does kindness and philanthropy mean in Titus 3?",
            "What is the washing of regeneration?",
            "How does renewal by the Holy Spirit work?",
            "What does justified by grace mean?",
            "How do grace faith and good works relate in Titus?",
            "What controversies genealogies and law disputes are rejected?",
            "What is a divisive person in Titus 3:10?",
            "Does reject after two warnings authorize public shunning?",
            "Who were Artemas and Tychicus?",
            "Where was Nicopolis and did Paul winter there?",
            "Who were Zenas and Apollos?",
            "What does hospitality and meeting urgent needs mean?",
            "Does P32 preserve part of Titus?",
            "Does Codex Vaticanus contain Titus?",
            "How can Titus be read without misogyny slavery apologetics or ethnic stereotyping?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Titus {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "titus")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Cretan quotation", "ethnic stereotype", "anti-Cretan"),
            ("Gender", "misogyny", "modern household"),
            ("Slavery", "enslaved", "slavery apologetics"),
            ("Rulers", "injustice", "nationalism"),
            ("Discipline", "public shaming", "spiritual abuse"),
            ("Application", "forced conversion", "ecological neglect"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-titus.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("titus").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
