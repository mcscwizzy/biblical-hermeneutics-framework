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
from framework.canonical_library.normalization import normalize_alias
from framework.canonical_library.retrieval import CKLRetrievalService


class SamuelRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.first_samuel = cls.library.retrieve_by_id("1-samuel").object
        cls.second_samuel = cls.library.retrieve_by_id("2-samuel").object

    def test_first_samuel_tracks_its_own_people_places_and_events(self) -> None:
        self.assertTrue(
            {
                "Hannah",
                "Samuel",
                "Saul",
                "Jonathan",
                "David",
                "Abigail and Nabal",
            }.issubset(self.first_samuel.key_people)
        )
        self.assertTrue(
            {
                "Shiloh",
                "Mizpah",
                "Gibeah",
                "the Valley of Elah",
                "Endor",
                "Mount Gilboa",
            }.issubset(self.first_samuel.key_places)
        )
        self.assertTrue(
            {
                "Israel requests a king and receives warnings about royal power",
                "Saul fails to carry out the Amalek command and is rejected as king",
                "David spares Saul in the cave and again in Saul's camp",
            }.issubset(self.first_samuel.key_events)
        )
        inherited_terms = {
            "Joshua",
            "Solomon",
            "Canaan",
            "Jerusalem",
            "Samaria",
            "conquest",
            "exile",
        }
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.first_samuel.key_people,
                    *self.first_samuel.key_places,
                    *self.first_samuel.key_events,
                }
            )
        )

    def test_second_samuel_tracks_davids_court_household_and_crises(self) -> None:
        self.assertTrue(
            {
                "David",
                "Ish-bosheth",
                "Abner",
                "Joab, Abishai, and Asahel",
                "Nathan the prophet",
                "Bathsheba",
                "Uriah the Hittite",
                "Amnon",
                "Tamar",
                "Absalom",
                "Solomon",
            }.issubset(self.second_samuel.key_people)
        )
        self.assertTrue(
            {
                "Hebron",
                "Jerusalem or the City of David",
                "Rabbah of the Ammonites",
                "the forest of Ephraim",
                "Araunah's threshing floor",
            }.issubset(self.second_samuel.key_places)
        )
        self.assertTrue(
            {
                "the LORD promises David an enduring house while assigning temple building to his offspring",
                "David takes Bathsheba and arranges Uriah's death",
                "Amnon violates Tamar and Absalom kills Amnon",
                "David orders a census, plague follows, and he builds an altar at Araunah's threshing floor",
            }.issubset(self.second_samuel.key_events)
        )
        inherited_terms = {
            "Joshua",
            "Samaria",
            "conquest",
            "exile",
        }
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.second_samuel.key_people,
                    *self.second_samuel.key_places,
                    *self.second_samuel.key_events,
                }
            )
        )
        normalized = [
            normalize_alias(event) for event in self.second_samuel.key_events
        ]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.first_samuel, self.second_samuel):
            with self.subTest(record=record.id):
                self.assertEqual(record.content_status, "draft")
                self.assertEqual(record.review_status, "in_review")
                self.assertTrue(record.human_review_required)
                self.assertIsNone(record.last_reviewed)
                self.assertEqual(record.section_status["human_review"], "missing")
                self.assertEqual(
                    record.knowledge_layers["primary"],
                    "biblical_text",
                )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        for record in (self.first_samuel, self.second_samuel):
            source_ids = {source.id for source in record.sources}
            self.assertGreaterEqual(len(record.claims), 6)
            self.assertGreaterEqual(len(record.interpretive_notes), 5)
            for claim in record.claims:
                with self.subTest(record=record.id, claim=claim.id):
                    self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                    self.assertIn(
                        claim.dispute_status,
                        CURRENT_DISPUTE_STATUS_VALUES,
                    )
                    self.assertTrue(claim.rationale.strip())
                    self.assertTrue(claim.source_ids)
                    self.assertTrue(set(claim.source_ids).issubset(source_ids))
            for index, note in enumerate(record.interpretive_notes):
                with self.subTest(record=record.id, note=index):
                    self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                    self.assertIn(
                        note.dispute_status,
                        CURRENT_DISPUTE_STATUS_VALUES,
                    )
                    self.assertTrue(note.rationale.strip())
                    self.assertTrue(note.sources)
                    self.assertTrue(set(note.sources).issubset(source_ids))

    def test_wave_records_have_external_sources_and_reviewer_metadata(self) -> None:
        for record in (self.first_samuel, self.second_samuel):
            with self.subTest(record=record.id):
                external = [
                    source
                    for source in record.sources
                    if source.source_type != "scripture" and source.url
                ]
                self.assertGreaterEqual(len(external), 3)
                self.assertTrue(record.hermeneutical_lens["book_context"])
                self.assertTrue(
                    record.hermeneutical_lens["common_misinterpretations"]
                )
                self.assertTrue(record.retrieval_metadata["common_questions"])
                self.assertTrue(record.retrieval_metadata["semantic_keywords"])

    def test_retrieval_answers_wave_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = {
            "Why did Israel ask for a king in 1 Samuel?": "1-samuel",
            "Why was Saul rejected in 1 Samuel?": "1-samuel",
            "What does the Davidic covenant promise in 2 Samuel?": "2-samuel",
            "How does 2 Samuel portray David and Bathsheba?": "2-samuel",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        goliath_notes = [
            note
            for note in self.first_samuel.interpretive_notes
            if "shorter ancient Greek form" in note.note
        ]
        self.assertTrue(goliath_notes)
        self.assertEqual(goliath_notes[0].dispute_status, "textual_variant")

        endor_notes = [
            note
            for note in self.first_samuel.interpretive_notes
            if "At Endor" in note.note
        ]
        self.assertTrue(endor_notes)
        self.assertEqual(endor_notes[0].certainty, "disputed")

        bathsheba_notes = [
            note
            for note in self.second_samuel.interpretive_notes
            if "harmless mutual romance" in note.note
        ]
        self.assertTrue(bathsheba_notes)
        self.assertEqual(bathsheba_notes[0].note_type, "interpretive-caution")

        census_notes = [
            note
            for note in self.second_samuel.interpretive_notes
            if "First Chronicles attributes it" in note.note
        ]
        self.assertTrue(census_notes)
        self.assertEqual(
            census_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        archaeology_notes = [
            note
            for note in self.second_samuel.interpretive_notes
            if "later Davidic dynasty" in note.note
        ]
        self.assertTrue(archaeology_notes)
        self.assertEqual(
            archaeology_notes[0].dispute_status,
            "archaeological_uncertainty",
        )

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-samuel.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            for json_record in (self.first_samuel, self.second_samuel):
                with self.subTest(record=json_record.id):
                    sqlite_record = sqlite_library.retrieve_by_id(
                        json_record.id
                    ).object
                    self.assertEqual(
                        sqlite_record.to_dict(),
                        json_record.to_dict(),
                    )


if __name__ == "__main__":
    unittest.main()
