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


class EstherRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.esther = cls.library.retrieve_by_id("esther").object

    def test_esther_tracks_court_crisis_reversal_and_purim(self) -> None:
        self.assertTrue(
            {
                "Ahasuerus",
                "Vashti",
                "Esther or Hadassah",
                "Mordecai son of Jair",
                "Haman son of Hammedatha the Agagite",
                "Zeresh",
                "Hathach",
                "Harbona",
            }.issubset(self.esther.key_people)
        )
        self.assertTrue(
            {
                "Susa citadel",
                "Persia and Media",
                "the empire from India to Cush",
                "the women's quarters",
                "the king's gate",
                "the empire's 127 provinces",
            }.issubset(self.esther.key_places)
        )
        self.assertTrue(
            {
                "Vashti refuses the king's command and is deposed",
                "Haman casts the pur and obtains an edict to destroy all Jews",
                "Esther accepts the risk of appearing before the king uninvited",
                "Esther and Mordecai issue a counter-edict authorizing Jewish defense",
                "Purim is established through letters, feasting, gifts, and aid to the poor",
            }.issubset(self.esther.key_events)
        )

    def test_esther_removes_inherited_historical_books_template(self) -> None:
        inherited_terms = {
            "Joshua",
            "David",
            "Solomon",
            "Canaan",
            "conquest",
            "monarchy",
        }
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.esther.key_people,
                    *self.esther.key_places,
                    *self.esther.key_events,
                }
            )
        )
        self.assertIn("diaspora court narrative", self.esther.genre)
        self.assertIn("festival etiology", self.esther.genre)
        self.assertIn(
            "Greek Additions to Esther",
            self.esther.primary_sources,
        )

    def test_esther_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.esther.content_status, "draft")
        self.assertEqual(self.esther.review_status, "in_review")
        self.assertTrue(self.esther.human_review_required)
        self.assertIsNone(self.esther.last_reviewed)
        self.assertEqual(
            self.esther.section_status["human_review"],
            "missing",
        )
        self.assertEqual(
            self.esther.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.esther.sources}
        self.assertGreaterEqual(len(self.esther.claims), 8)
        self.assertGreaterEqual(len(self.esther.interpretive_notes), 10)
        for claim in self.esther.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.esther.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_esther_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.esther.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 7)
        self.assertTrue(self.esther.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.esther.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.esther.retrieval_metadata["common_questions"])
        self.assertTrue(self.esther.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "esther-the-queen",
                "mordecai",
                "persia",
                "susa",
                "providence",
                "honor-and-shame",
            }.issubset(
                {relationship.id for relationship in self.esther.related_objects}
            )
        )

    def test_retrieval_answers_esther_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Why did Vashti refuse the king?",
            "Why is God not named in Esther?",
            "What does Esther say about why Mordecai refused to bow to Haman?",
            "Why could Haman's Persian decree not be revoked?",
            "Why did Esther ask for another day of fighting in Susa?",
            "Why are Hebrew and Greek Esther different?",
            "How did Purim begin?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "esther")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        xerxes_notes = [
            note
            for note in self.esther.interpretive_notes
            if "does not independently verify every person" in note.note
        ]
        self.assertTrue(xerxes_notes)
        self.assertEqual(
            xerxes_notes[0].dispute_status,
            "historical_uncertainty",
        )

        coercion_notes = [
            note
            for note in self.esther.interpretive_notes
            if "coercive power imbalance" in note.note
        ]
        self.assertTrue(coercion_notes)
        self.assertEqual(
            coercion_notes[0].note_type,
            "interpretive-caution",
        )

        providence_notes = [
            note
            for note in self.esther.interpretive_notes
            if "Hidden providence is a coherent canonical reading" in note.note
        ]
        self.assertTrue(providence_notes)
        self.assertEqual(
            providence_notes[0].dispute_status,
            "denominational_disagreement",
        )

        violence_notes = [
            note
            for note in self.esther.interpretive_notes
            if "license modern retaliation" in note.note
        ]
        self.assertTrue(violence_notes)
        self.assertEqual(
            violence_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        textual_notes = [
            note
            for note in self.esther.interpretive_notes
            if "not merely the Hebrew story" in note.note
        ]
        self.assertTrue(textual_notes)
        self.assertEqual(
            textual_notes[0].dispute_status,
            "textual_variant",
        )

    def test_sqlite_preserves_esther_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-esther.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("esther").object
            self.assertEqual(
                sqlite_record.to_dict(),
                self.esther.to_dict(),
            )


if __name__ == "__main__":
    unittest.main()
