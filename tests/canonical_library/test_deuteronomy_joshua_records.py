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


class DeuteronomyJoshuaRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.deuteronomy = cls.library.retrieve_by_id("deuteronomy").object
        cls.joshua = cls.library.retrieve_by_id("joshua").object

    def test_deuteronomy_is_anchored_in_moses_moab_speeches(self) -> None:
        self.assertTrue(
            {"Moses", "Joshua son of Nun", "the generation poised to enter the land"}.issubset(
                self.deuteronomy.key_people
            )
        )
        self.assertTrue(
            {"the plains of Moab", "Mount Horeb", "Mount Nebo"}.issubset(
                self.deuteronomy.key_places
            )
        )
        self.assertTrue(
            {
                "the covenant words and Shema are proclaimed",
                "covenant is renewed in Moab",
                "Joshua is commissioned",
                "Moses views the land and dies",
            }.issubset(self.deuteronomy.key_events)
        )
        normalized = [
            normalize_alias(event) for event in self.deuteronomy.key_events
        ]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_joshua_has_no_later_monarchy_or_exile_template_leakage(self) -> None:
        self.assertTrue(
            {"Joshua son of Nun", "Rahab and her household", "Achan", "Caleb"}.issubset(
                self.joshua.key_people
            )
        )
        self.assertTrue(
            {"the Jordan River", "Jericho", "Shiloh", "Shechem"}.issubset(
                self.joshua.key_places
            )
        )
        self.assertTrue(
            {
                "Israel crosses the Jordan and erects a memorial",
                "Jericho falls",
                "the land and cities are allotted among the tribes and Levites",
                "covenant is renewed at Shechem",
            }.issubset(self.joshua.key_events)
        )
        later_history_terms = {
            "David",
            "Solomon",
            "Jerusalem",
            "Samaria",
            "monarchy",
            "exile",
        }
        self.assertTrue(
            later_history_terms.isdisjoint(
                {
                    *self.joshua.key_people,
                    *self.joshua.key_places,
                    *self.joshua.key_events,
                }
            )
        )

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.deuteronomy, self.joshua):
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
        for record in (self.deuteronomy, self.joshua):
            source_ids = {source.id for source in record.sources}
            self.assertGreaterEqual(len(record.claims), 5)
            self.assertGreaterEqual(len(record.interpretive_notes), 4)
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
        for record in (self.deuteronomy, self.joshua):
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
            "Why does Deuteronomy repeat earlier laws?": "deuteronomy",
            "How does Deuteronomy prepare for Joshua?": "deuteronomy",
            "How complete was the conquest in Joshua?": "joshua",
            "What does Joshua say about remaining land?": "joshua",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_joshua_archaeology_is_labeled_uncertain(self) -> None:
        archaeology_notes = [
            note
            for note in self.joshua.interpretive_notes
            if note.dispute_status == "archaeological_uncertainty"
        ]
        self.assertTrue(archaeology_notes)
        self.assertTrue(
            any(
                "Jericho" in note.note
                and "Ai" in note.note
                and note.certainty == "insufficient_evidence"
                for note in archaeology_notes
            )
        )

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-deuteronomy-joshua.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            for json_record in (self.deuteronomy, self.joshua):
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
