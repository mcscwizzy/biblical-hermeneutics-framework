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


class LamentationsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("lamentations").object

    def test_record_maps_voices_and_all_five_poems(self) -> None:
        people = " ".join(self.record.key_people)
        for voice in (
            "poetic narrator",
            "Daughter Zion",
            "first-person man",
            "communal voice",
        ):
            self.assertIn(voice, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Lamentations 1:1-22",
            "Lamentations 2:1-22",
            "Lamentations 3:1-66",
            "Lamentations 4:1-22",
            "Lamentations 5:1-22",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("Isaiah", "Ezekiel", "restoration"):
            self.assertNotIn(placeholder, values)
        self.assertTrue(
            any("anonymous" in position for position in self.record.authorship_positions)
        )
        self.assertIn("does not name", self.record.original_audience)
        self.assertIn("587/586", self.record.historical_setting)

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
        self.assertGreaterEqual(len(self.record.interpretive_notes), 32)
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
        self.assertGreaterEqual(len(self.record.hebrew_words), 24)
        self.assertGreaterEqual(len(self.record.greek_words), 12)
        self.assertTrue(
            {
                "jerusalem",
                "fall-of-jerusalem",
                "babylonian-exile",
                "exile-theme",
                "hope-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Lamentations and did Jeremiah write it?",
            "When was Lamentations written after Jerusalem fell?",
            "Why is Lamentations called Eikhah?",
            "What is the qinah meter in Lamentations?",
            "How do the alphabetic acrostics work in Lamentations?",
            "Why is the pe ayin order different in Lamentations?",
            "Who speaks in Lamentations?",
            "Who is Daughter Zion in Lamentations?",
            "Who is the man who has seen affliction in Lamentations 3?",
            "Is Lamentations 5 a communal prayer?",
            "What happened to Jerusalem in Lamentations 1?",
            "Why is there no comforter in Lamentations?",
            "Does God act like an enemy in Lamentations 2?",
            "Why are children starving in Lamentations?",
            "What does wormwood mean in Lamentations 3?",
            "What do steadfast love mercies and faithfulness mean?",
            "Does Lamentations 3 resolve the whole book with hope?",
            "What does good and bad from the Most High mean?",
            "Does Lamentations command silent submission to abuse?",
            "Why does Lamentations pray for vengeance?",
            "Who is the anointed one in Lamentations 4:20?",
            "What does Lamentations say about Edom?",
            "Does Lamentations teach inherited guilt?",
            "How should sexual violence in Lamentations 5 be read?",
            "Why does Lamentations end with rejection?",
            "Does Lamentations promise automatic restoration?",
            "What Dead Sea Scrolls preserve Lamentations?",
            "How does Greek Lamentations differ from the Hebrew text?",
            "Is Lamentations like ancient Near Eastern city laments?",
            "How is Lamentations related to Jeremiah?",
            "How is Lamentations used on Tisha B'Av?",
            "How have Christians used Lamentations in Holy Week?",
            "Is Lamentations trauma literature?",
            "Does Lamentations blame victims for catastrophe?",
            "Does divine anger justify genocide in Lamentations?",
            "Does Lamentations normalize divine abuse?",
            "How can Lamentations be taught without spiritual bypassing?",
            "Does Lamentations authorize coercive forgiveness?",
            "How should Lamentations address rape without minimizing survivors?",
            "How does ruined Zion shape ecological responsibility?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Lamentations {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "lamentations")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Jeremiah", "anonymous", "attribution"),
            ("Hope", "3:21-33", "bypass"),
            ("Violence", "genocide", "victim"),
            ("Abuse", "coercive forgiveness", "silence"),
            ("Sexual violence", "rape", "survivors"),
            ("Application", "nationalism", "forced conversion"),
            ("Ruined land", "ecological neglect", "creation"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-lamentations.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("lamentations").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
