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


class LeviticusNumbersRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.leviticus = cls.library.retrieve_by_id("leviticus").object
        cls.numbers = cls.library.retrieve_by_id("numbers").object

    def test_leviticus_is_anchored_at_the_sinai_sanctuary(self) -> None:
        self.assertTrue(
            {"Moses", "Aaron", "Nadab", "Abihu", "Eleazar", "Ithamar"}.issubset(
                self.leviticus.key_people
            )
        )
        self.assertTrue(
            {
                "the tent of meeting",
                "the sanctuary",
                "Mount Sinai",
            }.issubset(self.leviticus.key_places)
        )
        self.assertTrue(
            {
                "ordination of Aaron and his sons",
                "the death of Nadab and Abihu",
                "the Day of Atonement ritual",
                "Sabbath-year and Jubilee legislation",
            }.issubset(self.leviticus.key_events)
        )
        inherited_journey_terms = {
            "Egypt",
            "Moab",
            "exodus",
            "Sinai covenant",
            "wilderness journey",
        }
        self.assertTrue(
            inherited_journey_terms.isdisjoint(
                {
                    *self.leviticus.key_people,
                    *self.leviticus.key_places,
                    *self.leviticus.key_events,
                }
            )
        )

    def test_numbers_tracks_two_generations_from_sinai_to_moab(self) -> None:
        self.assertTrue(
            {
                "Moses",
                "Aaron",
                "Miriam",
                "Joshua son of Nun",
                "Caleb",
                "Balaam son of Beor",
            }.issubset(self.numbers.key_people)
        )
        self.assertTrue(
            {
                "Mount Sinai",
                "Kadesh-barnea",
                "the plains of Moab",
            }.issubset(self.numbers.key_places)
        )
        self.assertNotIn("Egypt", self.numbers.key_places)
        self.assertTrue(
            {
                "the first census and ordering of the camp",
                "Israel refuses to enter and the wilderness generation is judged",
                "Balaam blesses Israel despite Balak's intended curse",
                "the second census",
                "Joshua is commissioned",
            }.issubset(self.numbers.key_events)
        )
        for values in (
            self.numbers.key_people,
            self.numbers.key_places,
            self.numbers.key_events,
        ):
            normalized = [normalize_alias(value) for value in values]
            self.assertEqual(len(normalized), len(set(normalized)))

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.leviticus, self.numbers):
            with self.subTest(record=record.id):
                self.assertEqual(record.content_status, "draft")
                self.assertEqual(record.review_status, "in_review")
                self.assertTrue(record.human_review_required)
                self.assertIsNone(record.last_reviewed)
                self.assertEqual(record.section_status["human_review"], "missing")
                self.assertNotIn(
                    "complete",
                    {
                        value
                        for section, value in record.section_status.items()
                        if section != "human_review"
                    },
                )
                self.assertEqual(
                    record.knowledge_layers["primary"],
                    "biblical_text",
                )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        for record in (self.leviticus, self.numbers):
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
        for record in (self.leviticus, self.numbers):
            with self.subTest(record=record.id):
                external_sources = [
                    source
                    for source in record.sources
                    if source.source_type != "scripture" and source.url
                ]
                self.assertGreaterEqual(len(external_sources), 3)
                self.assertTrue(record.hermeneutical_lens["book_context"])
                self.assertTrue(
                    record.hermeneutical_lens["common_misinterpretations"]
                )
                self.assertTrue(record.retrieval_metadata["common_questions"])
                self.assertTrue(record.retrieval_metadata["semantic_keywords"])

    def test_retrieval_answers_wave_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = {
            "What is the difference between holy clean and unclean in Leviticus?": "leviticus",
            "Why does Leviticus begin after the tabernacle is completed?": "leviticus",
            "How do the two censuses frame Numbers?": "numbers",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_focused_balaam_entry_precedes_broad_numbers_draft(self) -> None:
        service = CKLRetrievalService(library=self.library)
        ids = [
            result.id
            for result in service.search(
                "What does the Deir Alla inscription establish about Balaam?",
                limit=5,
            ).results
        ]
        self.assertIn("balaam-inscription", ids)
        self.assertIn("numbers", ids)
        self.assertLess(ids.index("balaam-inscription"), ids.index("numbers"))

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-leviticus-numbers.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )

            for json_record in (self.leviticus, self.numbers):
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
