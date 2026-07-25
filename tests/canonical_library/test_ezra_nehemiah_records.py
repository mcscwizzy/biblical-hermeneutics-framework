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


class EzraNehemiahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.ezra = cls.library.retrieve_by_id("ezra").object
        cls.nehemiah = cls.library.retrieve_by_id("nehemiah").object

    def test_ezra_tracks_distinct_returns_temple_and_torah_reform(self) -> None:
        self.assertTrue(
            {
                "Cyrus of Persia",
                "Sheshbazzar",
                "Zerubbabel son of Shealtiel",
                "Jeshua son of Jozadak",
                "Haggai",
                "Zechariah son of Iddo",
                "Darius I",
                "Artaxerxes",
                "Ezra son of Seraiah",
            }.issubset(self.ezra.key_people)
        )
        self.assertTrue(
            {
                "Babylon",
                "Yehud",
                "Jerusalem",
                "the Second Temple",
                "the province Beyond the River",
                "Ahava canal",
            }.issubset(self.ezra.key_places)
        )
        self.assertTrue(
            {
                "Cyrus authorizes temple rebuilding and return",
                "Haggai and Zechariah prompt renewed temple work",
                "the Second Temple is completed and dedicated",
                "Ezra is commissioned to study, practice, teach, and administer Torah",
                "an assembly adopts a process to dissolve marriages to foreign women",
            }.issubset(self.ezra.key_events)
        )
        inherited_terms = {"Joshua", "David", "Solomon", "Canaan", "conquest"}
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.ezra.key_people,
                    *self.ezra.key_places,
                    *self.ezra.key_events,
                }
            )
        )

    def test_nehemiah_tracks_wall_justice_torah_and_later_reforms(self) -> None:
        self.assertTrue(
            {
                "Nehemiah son of Hacaliah",
                "Artaxerxes",
                "Sanballat the Horonite",
                "Tobiah the Ammonite official",
                "Geshem the Arab",
                "Ezra the scribe",
                "Noadiah the prophetess",
            }.issubset(self.nehemiah.key_people)
        )
        self.assertTrue(
            {
                "Susa citadel",
                "Jerusalem",
                "Yehud",
                "Jerusalem's gates and wall circuit",
                "the square before the Water Gate",
                "Samaria",
                "Ammon",
                "Ashdod",
            }.issubset(self.nehemiah.key_places)
        )
        self.assertTrue(
            {
                "Nehemiah inspects Jerusalem's ruins by night",
                "Nehemiah confronts debt, interest, land loss, and enslavement",
                "the wall is completed in fifty-two days despite intimidation",
                "Ezra reads Torah and Levites help the assembly understand",
                "two thanksgiving processions dedicate the wall",
                "Nehemiah returns after an interval and reverses several violations",
            }.issubset(self.nehemiah.key_events)
        )
        self.assertNotIn("Joshua", self.nehemiah.key_people)
        self.assertNotIn("Canaan", self.nehemiah.key_places)

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.ezra, self.nehemiah):
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
        for record in (self.ezra, self.nehemiah):
            source_ids = {source.id for source in record.sources}
            self.assertGreaterEqual(len(record.claims), 7)
            self.assertGreaterEqual(len(record.interpretive_notes), 8)
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
        for record in (self.ezra, self.nehemiah):
            with self.subTest(record=record.id):
                external = [
                    source
                    for source in record.sources
                    if source.source_type != "scripture" and source.url
                ]
                self.assertGreaterEqual(len(external), 5)
                self.assertTrue(record.hermeneutical_lens["book_context"])
                self.assertTrue(
                    record.hermeneutical_lens["common_misinterpretations"]
                )
                self.assertTrue(record.retrieval_metadata["common_questions"])
                self.assertTrue(record.retrieval_metadata["semantic_keywords"])

    def test_retrieval_answers_wave_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = {
            "Why does Ezra 4 jump between Persian kings?": "ezra",
            "Why is part of Ezra written in Aramaic?": "ezra",
            "Why did Ezra send away foreign wives and children?": "ezra",
            "What injustice occurs in Nehemiah 5?": "nehemiah",
            "What does Nehemiah 8:8 mean?": "nehemiah",
            "Why did Nehemiah pull out people's hair?": "nehemiah",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        cyrus_notes = [
            note
            for note in self.ezra.interpretive_notes
            if "Cyrus Cylinder is comparative evidence" in note.note
        ]
        self.assertTrue(cyrus_notes)
        self.assertEqual(
            cyrus_notes[0].dispute_status,
            "historical_uncertainty",
        )

        chronology_notes = [
            note
            for note in self.ezra.interpretive_notes
            if "seventh-year Artaxerxes" in note.note
        ]
        self.assertTrue(chronology_notes)
        self.assertEqual(
            chronology_notes[0].dispute_status,
            "chronological_uncertainty",
        )

        marriage_notes = [
            note
            for note in self.ezra.interpretive_notes
            if "send away foreign wives and children" in note.note
        ]
        self.assertTrue(marriage_notes)
        self.assertEqual(marriage_notes[0].note_type, "interpretive-caution")
        self.assertEqual(
            marriage_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        wall_notes = [
            note
            for note in self.nehemiah.interpretive_notes
            if "uncontested route" in note.note
        ]
        self.assertTrue(wall_notes)
        self.assertEqual(
            wall_notes[0].dispute_status,
            "archaeological_uncertainty",
        )

        violence_notes = [
            note
            for note in self.nehemiah.interpretive_notes
            if "hair-pulling" in note.note
        ]
        self.assertTrue(violence_notes)
        self.assertEqual(violence_notes[0].note_type, "interpretive-caution")
        self.assertEqual(
            violence_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        exclusion_notes = [
            note
            for note in self.nehemiah.interpretive_notes
            if "Ammonite and Moabite assembly exclusion" in note.note
        ]
        self.assertTrue(exclusion_notes)
        self.assertEqual(exclusion_notes[0].note_type, "canonical-connection")

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-ezra-nehemiah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            for json_record in (self.ezra, self.nehemiah):
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
