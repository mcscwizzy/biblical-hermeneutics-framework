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


class EphesiansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("ephesians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "named Paul",
            "Tychicus",
            "Gentile addressees",
            "Wives and husbands",
            "enslaved people and masters",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Ephesians 1:1-2:10",
            "Ephesians 2:11-3:21",
            "Ephesians 4:1-5:20",
            "Ephesians 5:21-6:9",
            "Ephesians 6:10-24",
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
            "Timothy",
            "Titus",
            "Rome",
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
        self.assertIn("textually uncertain", self.record.original_audience)

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
        self.assertGreaterEqual(len(self.record.interpretive_notes), 44)
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
        self.assertGreaterEqual(len(external), 20)
        self.assertGreaterEqual(len(self.record.hebrew_words), 10)
        self.assertGreaterEqual(len(self.record.greek_words), 20)
        self.assertTrue(
            {
                "paul",
                "grace",
                "faith",
                "union-with-christ",
                "people-of-god-theme",
                "spiritual-gifts",
                "temple",
                "spirit-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Ephesians and when?",
            "Was Ephesians originally sent to Ephesus or was it circular?",
            "Why do P46 Sinaiticus and Vaticanus omit in Ephesus?",
            "How is Ephesians related to Colossians?",
            "What do election and predestination mean in Ephesians?",
            "What does saved by grace through faith mean?",
            "Is faith itself the gift in Ephesians 2:8?",
            "What are good works in Ephesians 2:10?",
            "What is the dividing wall in Ephesians?",
            "Does Ephesians abolish Torah or support supersessionism?",
            "What is one new humanity?",
            "What do household and temple mean?",
            "What is the mystery in Ephesians 3?",
            "Who are rulers and powers in heavenly places?",
            "What unity does Ephesians 4 require?",
            "Who are apostles prophets evangelists pastors and teachers?",
            "What does descent to the lower regions mean?",
            "What do old and new humanity mean?",
            "What does speaking truth in love require?",
            "How should anger and forgiveness be applied safely?",
            "What is the quotation in Ephesians 5:14?",
            "What does being filled with the Spirit mean?",
            "Does Ephesians 5 teach mutual submission or male headship?",
            "Does the marriage analogy justify marital control or abuse?",
            "Does Ephesians authorize child punishment?",
            "Does Ephesians endorse slavery or worker exploitation?",
            "What is the armor of God?",
            "Does spiritual warfare mean demons cause mental illness?",
            "Who was Tychicus?",
            "Does Artemis explain Ephesians?",
            "Does Ephesians authorize militarism nationalism or violence?",
            "How can Ephesians be read without antisemitism or misogyny?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Ephesians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "ephesians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Torah", "antisemitism", "supersessionism"),
            ("submission", "marital rape", "abuse"),
            ("slave", "slavery", "worker"),
            ("Spiritual-warfare", "mental illness", "disability"),
            ("Armor", "militarism", "religious violence"),
            ("Children", "corporal harm", "absolute parental control"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-ephesians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("ephesians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
