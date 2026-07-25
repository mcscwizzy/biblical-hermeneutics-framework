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


class ChroniclesRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.first_chronicles = cls.library.retrieve_by_id(
            "1-chronicles"
        ).object
        cls.second_chronicles = cls.library.retrieve_by_id(
            "2-chronicles"
        ).object

    def test_first_chronicles_tracks_genealogies_david_and_temple_preparation(
        self,
    ) -> None:
        self.assertTrue(
            {
                "Adam",
                "Judah",
                "Levi and Aaron",
                "Saul and Jonathan",
                "David",
                "Asaph, Heman, and Jeduthun",
                "Ornan the Jebusite",
                "Solomon",
            }.issubset(self.first_chronicles.key_people)
        )
        self.assertTrue(
            {
                "Jerusalem",
                "Hebron",
                "Gibeon",
                "Kiriath-jearim",
                "Ornan's threshing floor on Mount Moriah",
            }.issubset(self.first_chronicles.key_places)
        )
        self.assertTrue(
            {
                "genealogies connect Adam, the nations, Israel's tribes, David's line, and the restored Jerusalem community",
                "all Israel gathers to make David king at Hebron",
                "David identifies the altar site as the location for the LORD's house",
                "David gives Solomon the temple plan and charges him to be strong and faithful",
            }.issubset(self.first_chronicles.key_events)
        )
        inherited_terms = {"Joshua", "Canaan", "conquest", "monarchy"}
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.first_chronicles.key_people,
                    *self.first_chronicles.key_places,
                    *self.first_chronicles.key_events,
                }
            )
        )

    def test_second_chronicles_tracks_judah_reform_exile_and_cyrus(
        self,
    ) -> None:
        self.assertTrue(
            {
                "Solomon",
                "Rehoboam",
                "Asa",
                "Jehoshaphat",
                "Athaliah and Jehoshabeath",
                "Hezekiah and Isaiah",
                "Manasseh and Amon",
                "Josiah, Hilkiah, Shaphan, and Huldah",
                "Nebuchadnezzar",
                "Cyrus of Persia",
            }.issubset(self.second_chronicles.key_people)
        )
        self.assertTrue(
            {
                "Gibeon",
                "Jerusalem",
                "Mount Moriah and Ornan's threshing floor",
                "the Jerusalem temple, courts, chambers, gates, and altar",
                "Megiddo",
                "Babylon",
                "Persia",
            }.issubset(self.second_chronicles.key_places)
        )
        self.assertTrue(
            {
                "Solomon builds the temple on Mount Moriah and installs its furnishings",
                "Hezekiah cleanses the temple, restores worship, and invites Israel and Judah to celebrate Passover",
                "Manasseh is taken captive, humbles himself, returns to Jerusalem, and removes foreign gods",
                "Babylon destroys Jerusalem and the temple and carries survivors into exile",
                "the land observes its Sabbaths, Jeremiah's word is fulfilled, and Cyrus authorizes rebuilding and ascent",
            }.issubset(self.second_chronicles.key_events)
        )
        self.assertNotIn("Joshua", self.second_chronicles.key_people)
        self.assertNotIn("Canaan", self.second_chronicles.key_places)

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.first_chronicles, self.second_chronicles):
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
        for record in (self.first_chronicles, self.second_chronicles):
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

    def test_wave_records_have_external_sources_and_reviewer_metadata(
        self,
    ) -> None:
        for record in (self.first_chronicles, self.second_chronicles):
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
            "Why are there genealogies in 1 Chronicles?": "1-chronicles",
            "How did David prepare for the temple in 1 Chronicles?": "1-chronicles",
            "Why does 2 Chronicles focus on Judah?": "2-chronicles",
            "What does 2 Chronicles say about healing the land?": "2-chronicles",
            "How does 2 Chronicles end?": "2-chronicles",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        genealogy_notes = [
            note
            for note in self.first_chronicles.interpretive_notes
            if "selective literary maps" in note.note
        ]
        self.assertTrue(genealogy_notes)
        self.assertEqual(genealogy_notes[0].certainty, "strong_consensus")
        self.assertEqual(
            genealogy_notes[0].dispute_status,
            "minor_scholarly_disagreement",
        )

        census_notes = [
            note
            for note in self.first_chronicles.interpretive_notes
            if "census incitement" in note.note
        ]
        self.assertTrue(census_notes)
        self.assertEqual(
            census_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        levitical_notes = [
            note
            for note in self.first_chronicles.interpretive_notes
            if "Levitical, musical, and administrative orders" in note.note
        ]
        self.assertTrue(levitical_notes)
        self.assertEqual(
            levitical_notes[0].dispute_status,
            "historical_uncertainty",
        )

        healing_notes = [
            note
            for note in self.second_chronicles.interpretive_notes
            if "2 Chronicles 7:14" in note.note
        ]
        self.assertTrue(healing_notes)
        self.assertEqual(healing_notes[0].note_type, "interpretive-caution")

        retribution_notes = [
            note
            for note in self.second_chronicles.interpretive_notes
            if "every sufferer" in note.note
        ]
        self.assertTrue(retribution_notes)
        self.assertEqual(
            retribution_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        manasseh_notes = [
            note
            for note in self.second_chronicles.interpretive_notes
            if "Manasseh's captivity" in note.note
        ]
        self.assertTrue(manasseh_notes)
        self.assertEqual(manasseh_notes[0].note_type, "canonical-connection")

        cyrus_notes = [
            note
            for note in self.second_chronicles.interpretive_notes
            if "Cyrus proclamation" in note.note
        ]
        self.assertTrue(cyrus_notes)
        self.assertEqual(
            cyrus_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-chronicles.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            for json_record in (
                self.first_chronicles,
                self.second_chronicles,
            ):
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
