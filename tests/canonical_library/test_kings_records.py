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


class KingsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.first_kings = cls.library.retrieve_by_id("1-kings").object
        cls.second_kings = cls.library.retrieve_by_id("2-kings").object

    def test_first_kings_tracks_solomon_division_and_elijah(self) -> None:
        self.assertTrue(
            {
                "Solomon",
                "the queen of Sheba",
                "Rehoboam",
                "Jeroboam son of Nebat",
                "Ahab",
                "Jezebel",
                "Elijah",
                "Naboth",
                "Micaiah son of Imlah",
            }.issubset(self.first_kings.key_people)
        )
        self.assertTrue(
            {
                "the temple and royal complex in Jerusalem",
                "Bethel and Dan",
                "Samaria",
                "Mount Carmel",
                "Jezreel",
                "Ramoth-gilead",
            }.issubset(self.first_kings.key_places)
        )
        self.assertTrue(
            {
                "the ark is installed and Solomon dedicates the temple with prayer and sacrifice",
                "Rehoboam rejects the elders' counsel and the kingdom divides",
                "Jezebel arranges Naboth's death, Ahab takes the vineyard, and Elijah announces judgment",
            }.issubset(self.first_kings.key_events)
        )
        inherited_terms = {
            "Joshua",
            "Canaan",
            "conquest",
            "exile",
        }
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.first_kings.key_people,
                    *self.first_kings.key_places,
                    *self.first_kings.key_events,
                }
            )
        )

    def test_second_kings_tracks_prophets_empires_and_both_falls(self) -> None:
        self.assertTrue(
            {
                "Elijah",
                "Elisha",
                "Naaman",
                "Hazael",
                "Jehu",
                "Athaliah",
                "Hezekiah",
                "Isaiah",
                "Sennacherib and the Rabshakeh",
                "Josiah",
                "Huldah",
                "Nebuchadnezzar",
                "Jehoiachin",
            }.issubset(self.second_kings.key_people)
        )
        self.assertTrue(
            {
                "Samaria",
                "Damascus",
                "Jerusalem and the temple",
                "Assyria and its resettlement regions",
                "Lachish",
                "Babylon",
                "Riblah",
            }.issubset(self.second_kings.key_places)
        )
        self.assertTrue(
            {
                "Assyria captures Samaria, deports Israelites, and resettles populations",
                "Josiah responds to the discovered scroll, consults Huldah, renews covenant, reforms worship, and keeps Passover",
                "Nebuchadnezzar's forces breach Jerusalem, destroy temple and city, execute officials, and deport the population",
                "Gedaliah is appointed and assassinated, survivors flee to Egypt, and Jehoiachin is later released and honored in Babylon",
            }.issubset(self.second_kings.key_events)
        )
        inherited_people = {
            "Joshua",
            "David",
            "Solomon",
            "Jeremiah the Prophet",
        }
        self.assertTrue(inherited_people.isdisjoint(self.second_kings.key_people))
        normalized = [
            normalize_alias(event) for event in self.second_kings.key_events
        ]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.first_kings, self.second_kings):
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
        for record in (self.first_kings, self.second_kings):
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
        for record in (self.first_kings, self.second_kings):
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
            "Why did the kingdom divide in 1 Kings?": "1-kings",
            "What happened on Mount Carmel in 1 Kings?": "1-kings",
            "Why did Samaria fall in 2 Kings?": "2-kings",
            "How does 2 Kings end?": "2-kings",
            "What does the Sennacherib Prism say about Hezekiah in 2 Kings?": "2-kings",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        solomon_notes = [
            note
            for note in self.first_kings.interpretive_notes
            if "archaeological profile of Solomon's kingdom" in note.note
        ]
        self.assertTrue(solomon_notes)
        self.assertEqual(
            solomon_notes[0].dispute_status,
            "archaeological_uncertainty",
        )

        horeb_notes = [
            note
            for note in self.first_kings.interpretive_notes
            if "qol demamah daqqah" in note.note
        ]
        self.assertTrue(horeb_notes)
        self.assertEqual(horeb_notes[0].certainty, "disputed")
        self.assertEqual(
            horeb_notes[0].dispute_status,
            "lexical_uncertainty",
        )

        violence_notes = [
            note
            for note in self.first_kings.interpretive_notes
            if "cannot authorize religious violence" in note.note
        ]
        self.assertTrue(violence_notes)
        self.assertEqual(violence_notes[0].note_type, "interpretive-caution")

        bears_notes = [
            note
            for note in self.second_kings.interpretive_notes
            if "bears killing forty-two" in note.note
        ]
        self.assertTrue(bears_notes)
        self.assertEqual(bears_notes[0].note_type, "interpretive-caution")
        self.assertEqual(
            bears_notes[0].dispute_status,
            "lexical_uncertainty",
        )

        moab_notes = [
            note
            for note in self.second_kings.interpretive_notes
            if "great wrath against Israel" in note.note
        ]
        self.assertTrue(moab_notes)
        self.assertEqual(moab_notes[0].certainty, "disputed")

        sennacherib_notes = [
            note
            for note in self.second_kings.interpretive_notes
            if "Sennacherib's prism independently names Hezekiah" in note.note
        ]
        self.assertTrue(sennacherib_notes)
        self.assertEqual(
            sennacherib_notes[0].dispute_status,
            "historical_uncertainty",
        )

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-kings.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            for json_record in (self.first_kings, self.second_kings):
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
