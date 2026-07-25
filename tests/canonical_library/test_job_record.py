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


class JobRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.job = cls.library.retrieve_by_id("job").object

    def test_job_tracks_frame_dialogues_oath_and_divine_speeches(self) -> None:
        self.assertTrue(
            {
                "Job",
                "Job's wife",
                "Eliphaz the Temanite",
                "Bildad the Shuhite",
                "Zophar the Naamathite",
                "Elihu son of Barachel the Buzite",
                "the satan or accuser",
                "YHWH",
            }.issubset(self.job.key_people)
        )
        self.assertTrue(
            {
                "the land of Uz",
                "the heavenly council",
                "the ash heap",
                "the city gate",
                "Teman",
                "Buz",
            }.issubset(self.job.key_places)
        )
        self.assertTrue(
            {
                "Job loses his livestock, servants, and ten children in cascading disasters",
                "Job's three friends sit with him in silence for seven days and nights",
                "Job curses the day of his birth and begins the poetic dispute",
                "Job swears an extended oath of innocence",
                "YHWH answers Job from the whirlwind with creation speeches",
                "Job prays for the three friends and his fortunes are restored",
            }.issubset(self.job.key_events)
        )

    def test_job_removes_inherited_wisdom_books_template(self) -> None:
        inherited_terms = {
            "David",
            "Solomon",
            "Israel",
            "court",
            "temple",
            "monarchic wisdom traditions",
        }
        record_terms = {
            *self.job.key_people,
            *self.job.key_places,
            *self.job.key_events,
            *self.job.date_ranges,
        }
        self.assertTrue(inherited_terms.isdisjoint(record_terms))
        self.assertIn("wisdom dialogue", self.job.genre)
        self.assertIn("prose tale framing poetic disputation", self.job.genre)
        self.assertIn("Old Greek Job", self.job.primary_sources)

    def test_job_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.job.content_status, "draft")
        self.assertEqual(self.job.review_status, "in_review")
        self.assertTrue(self.job.human_review_required)
        self.assertIsNone(self.job.last_reviewed)
        self.assertEqual(self.job.section_status["human_review"], "missing")
        self.assertEqual(
            self.job.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.job.sources}
        self.assertGreaterEqual(len(self.job.claims), 8)
        self.assertGreaterEqual(len(self.job.interpretive_notes), 10)
        for claim in self.job.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.job.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_job_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.job.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 7)
        self.assertTrue(self.job.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.job.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.job.retrieval_metadata["common_questions"])
        self.assertTrue(self.job.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "job-the-sufferer",
                "wisdom-theme",
                "theology-of-suffering",
                "divine-justice",
                "creation-theme",
                "psalms",
                "ecclesiastes",
                "james",
            }.issubset(
                {relationship.id for relationship in self.job.related_objects}
            )
        )

    def test_retrieval_answers_job_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Why does Job suffer if he is innocent?",
            "Who is the satan in Job's heavenly council?",
            "Are Job's friends condemned for their advice?",
            "What is the poem about wisdom in Job 28?",
            "Why does Elihu speak before God answers Job?",
            "Are Behemoth and Leviathan dinosaurs in Job?",
            "Does Job repent in dust and ashes?",
            "Does Job teach that suffering always leads to greater wealth?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "job")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        historicity_notes = [
            note
            for note in self.job.interpretive_notes
            if "does not settle the genre or historical referentiality" in note.note
        ]
        self.assertTrue(historicity_notes)
        self.assertEqual(
            historicity_notes[0].dispute_status,
            "historical_uncertainty",
        )

        satan_notes = [
            note
            for note in self.job.interpretive_notes
            if "not yet an unambiguous proper name for the later devil" in note.note
        ]
        self.assertTrue(satan_notes)
        self.assertEqual(satan_notes[0].note_type, "textual-observation")

        repentance_notes = [
            note
            for note in self.job.interpretive_notes
            if "Job 42:6 is textually and lexically difficult" in note.note
        ]
        self.assertTrue(repentance_notes)
        self.assertEqual(
            repentance_notes[0].dispute_status,
            "lexical_uncertainty",
        )

        monster_notes = [
            note
            for note in self.job.interpretive_notes
            if "cannot be identified confidently as dinosaurs" in note.note
        ]
        self.assertTrue(monster_notes)
        self.assertEqual(
            monster_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        pastoral_notes = [
            note
            for note in self.job.interpretive_notes
            if "prosperity guarantee or a formula" in note.note
        ]
        self.assertTrue(pastoral_notes)
        self.assertEqual(
            pastoral_notes[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_job_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-job.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("job").object
            self.assertEqual(sqlite_record.to_dict(), self.job.to_dict())


if __name__ == "__main__":
    unittest.main()
