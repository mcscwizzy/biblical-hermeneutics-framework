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


class FirstThessaloniansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("1-thessalonians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in ("Paul, Silvanus, and Timothy", "Thessalonian assembly", "dead in Messiah"):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "1 Thessalonians 1:1-10",
            "1 Thessalonians 2:1-16",
            "1 Thessalonians 2:17-3:13",
            "1 Thessalonians 4:1-12",
            "1 Thessalonians 4:13-5:11",
            "1 Thessalonians 5:12-28",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        values = {
            *self.record.authorship_positions,
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("Titus", "Rome", "Ephesus", "mission", "church formation", "pastoral instruction"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(any("strong scholarly consensus" in position for position in self.record.authorship_positions))
        self.assertIn("do not identify", self.record.historical_setting)

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
        external = [source for source in self.record.sources if source.source_type != "scripture" and source.url]
        self.assertGreaterEqual(len(external), 20)
        self.assertGreaterEqual(len(self.record.hebrew_words), 10)
        self.assertGreaterEqual(len(self.record.greek_words), 20)
        self.assertTrue(
            {"paul", "thessalonica", "second-coming", "resurrection-theme", "perseverance", "faith", "grace"}.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 1 Thessalonians and when?",
            "Who were Paul Silvanus and Timothy?",
            "Was 1 Thessalonians written from Corinth?",
            "How does 1 Thessalonians relate to Acts 17?",
            "Who were the Thessalonian persecutors?",
            "What does election mean in 1 Thessalonians?",
            "What are the maternal and paternal metaphors?",
            "Why did Paul work night and day?",
            "Is 1 Thessalonians 2:14-16 an interpolation?",
            "Does 1 Thessalonians blame all Jews?",
            "Why was Timothy sent from Athens?",
            "How do sexual holiness vessel and Spirit relate in chapter 4?",
            "Does skeuos mean body or spouse?",
            "What does quiet living mean?",
            "Does 1 Thessalonians shame unemployed or disabled people?",
            "Can Christians grieve for believers who died?",
            "What happens to the dead in Christ?",
            "What is the parousia in 1 Thessalonians?",
            "What do trumpet clouds and archangel mean?",
            "What does apantesis meeting the Lord mean?",
            "Does 1 Thessalonians teach a secret rapture?",
            "Can 1 Thessalonians be used to set a date?",
            "What does peace and security mean?",
            "How do thief light sleep and armor explain the day of the Lord?",
            "What is the armor of faith love and hope?",
            "Who are the leaders in 1 Thessalonians 5?",
            "How should the fainthearted and weak be treated?",
            "Should Christians despise prophecy?",
            "What does test everything mean?",
            "What does entire sanctification mean?",
            "Why must the letter be read to everyone?",
            "How can 1 Thessalonians be read without antisemitism rapture panic or worker shaming?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"1 Thessalonians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "1-thessalonians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("2:14-16", "collective Jewish blame", "antisemitism", "supersessionism"),
            ("Sanctification", "sexual", "coercion", "anti-LGBTQ"),
            ("Work", "disabled", "exploited"),
            ("grief", "emotional suppression", "mental-health"),
            ("Parousia", "date setting", "conspiracy", "ecological"),
            ("prophecy", "consent", "accountability"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(any(all(word in note for word in words) for note in notes))

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-1-thessalonians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(database, root=self.root)
            sqlite_record = sqlite_library.retrieve_by_id("1-thessalonians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
