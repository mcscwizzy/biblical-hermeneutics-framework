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


class GenesisExodusRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.genesis = cls.library.retrieve_by_id("genesis").object
        cls.exodus = cls.library.retrieve_by_id("exodus").object

    def test_genesis_has_book_specific_people_places_and_events(self) -> None:
        self.assertTrue(
            {"Adam", "Eve", "Noah", "Abraham", "Jacob", "Joseph"}.issubset(
                self.genesis.key_people
            )
        )
        self.assertTrue(
            {"Eden", "Canaan", "Egypt"}.issubset(self.genesis.key_places)
        )
        self.assertTrue(
            {
                "creation and the seventh day",
                "the flood and covenant with Noah",
                "the descent of Jacob's household to Egypt",
            }.issubset(self.genesis.key_events)
        )
        inherited_exodus_terms = {
            "Moses",
            "Aaron",
            "Sinai",
            "Moab",
            "the exodus from Egypt",
            "the Sinai covenant",
            "the wilderness journey",
        }
        self.assertTrue(
            inherited_exodus_terms.isdisjoint(
                {
                    *self.genesis.key_people,
                    *self.genesis.key_places,
                    *self.genesis.key_events,
                }
            )
        )

    def test_exodus_has_book_specific_people_places_and_unique_events(self) -> None:
        self.assertTrue(
            {"Moses", "Aaron", "Miriam", "Zipporah", "Jethro"}.issubset(
                self.exodus.key_people
            )
        )
        self.assertTrue(
            {"Egypt", "Midian", "Mount Sinai"}.issubset(self.exodus.key_places)
        )
        self.assertNotIn("Moab", self.exodus.key_places)
        self.assertTrue(
            {
                "the sea crossing and song",
                "the golden calf and Moses's intercession",
                "construction of the tabernacle",
                "the glory filling the tabernacle",
            }.issubset(self.exodus.key_events)
        )
        normalized_events = [normalize_alias(event) for event in self.exodus.key_events]
        self.assertEqual(len(normalized_events), len(set(normalized_events)))

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.genesis, self.exodus):
            with self.subTest(record=record.id):
                self.assertEqual(record.content_status, "draft")
                self.assertEqual(record.review_status, "in_review")
                self.assertTrue(record.human_review_required)
                self.assertEqual(record.section_status["human_review"], "missing")
                self.assertNotIn(
                    "complete",
                    {
                        record.section_status[section]
                        for section in record.section_status
                        if section != "human_review"
                    },
                )
                self.assertEqual(
                    record.knowledge_layers["primary"],
                    "biblical_text",
                )

    def test_claims_and_interpretive_notes_use_current_evidence_taxonomy(self) -> None:
        for record in (self.genesis, self.exodus):
            source_ids = {source.id for source in record.sources}
            self.assertGreaterEqual(len(record.claims), 4)
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

    def test_wave_records_have_reviewer_facing_sources_and_retrieval_metadata(self) -> None:
        for record in (self.genesis, self.exodus):
            with self.subTest(record=record.id):
                self.assertGreaterEqual(len(record.sources), 4)
                self.assertTrue(any(source.url for source in record.sources))
                self.assertTrue(record.hermeneutical_lens["book_context"])
                self.assertTrue(
                    record.hermeneutical_lens["common_misinterpretations"]
                )
                self.assertTrue(record.retrieval_metadata["common_questions"])
                self.assertTrue(record.retrieval_metadata["semantic_keywords"])

    def test_retrieval_answers_wave_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = {
            "Why does Genesis end in Egypt?": "genesis",
            "Why does Exodus include so much tabernacle material?": "exodus",
            "What historical evidence relates to Exodus?": "exodus",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_draft_books_do_not_displace_more_specific_golden_topics(self) -> None:
        service = CKLRetrievalService(library=self.library)
        cases = {
            "What is the significance of Joseph's bones?": (
                "genesis",
                "joseph-interprets-pharaohs-dreams",
            ),
            "Why did Joshua say Israel could not serve the Lord?": (
                "exodus",
                "joshua-son-of-nun",
            ),
            "What is covenant renewal?": (
                "exodus",
                "new-covenant-prophecy",
            ),
        }
        for query, pair in cases.items():
            broad_draft_id, focused_id = pair
            with self.subTest(query=query):
                ids = [
                    result.id
                    for result in service.search(query, limit=8).results
                ]
                self.assertIn(focused_id, ids)
                if broad_draft_id in ids:
                    self.assertLess(
                        ids.index(focused_id),
                        ids.index(broad_draft_id),
                    )

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )

            for json_record in (self.genesis, self.exodus):
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
