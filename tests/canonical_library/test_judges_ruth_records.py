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


class JudgesRuthRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.judges = cls.library.retrieve_by_id("judges").object
        cls.ruth = cls.library.retrieve_by_id("ruth").object

    def test_judges_tracks_its_own_leaders_decline_and_places(self) -> None:
        self.assertTrue(
            {
                "Deborah",
                "Gideon",
                "Jephthah and his daughter",
                "Samson and his parents",
            }.issubset(self.judges.key_people)
        )
        self.assertNotIn("Ruth", self.judges.key_people)
        self.assertTrue(
            {"Shechem and Mount Gerizim", "Gibeah", "Shiloh"}.issubset(
                self.judges.key_places
            )
        )
        self.assertTrue(
            {
                "the abuse and death of the Levite's concubine lead to war against Benjamin",
                "Israel's attempts to preserve Benjamin compound violence against other communities",
            }.issubset(self.judges.key_events)
        )
        normalized = [normalize_alias(event) for event in self.judges.key_events]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_ruth_has_no_inherited_conquest_monarchy_or_exile_leakage(self) -> None:
        self.assertTrue(
            {
                "Naomi",
                "Ruth the Moabite",
                "Boaz",
                "the unnamed nearer redeemer",
                "Obed",
            }.issubset(self.ruth.key_people)
        )
        self.assertTrue(
            {
                "Bethlehem in Judah",
                "the fields of Moab",
                "Boaz's barley field",
                "Bethlehem's town gate",
            }.issubset(self.ruth.key_places)
        )
        self.assertTrue(
            {
                "Ruth gleans in Boaz's field and receives food and protection",
                "the nearer redeemer declines at Bethlehem's gate",
                "the LORD grants conception and Ruth bears Obed",
            }.issubset(self.ruth.key_events)
        )
        inherited_terms = {
            "Joshua",
            "Solomon",
            "Canaan",
            "Jerusalem",
            "Samaria",
            "conquest",
            "monarchy",
            "exile",
        }
        self.assertTrue(
            inherited_terms.isdisjoint(
                {
                    *self.ruth.key_people,
                    *self.ruth.key_places,
                    *self.ruth.key_events,
                }
            )
        )

    def test_wave_records_are_honest_drafts_awaiting_human_review(self) -> None:
        for record in (self.judges, self.ruth):
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
        for record in (self.judges, self.ruth):
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
        for record in (self.judges, self.ruth):
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
            "Why does Judges end in civil war?": "judges",
            "Does Judges endorse monarchy?": "judges",
            "Was Ruth 4 exactly levirate marriage?": "ruth",
            "What happened at the threshing floor in Ruth?": "ruth",
        }
        for query, expected_id in queries.items():
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, expected_id)

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        jephthah_notes = [
            note
            for note in self.judges.interpretive_notes
            if "Jephthah" in note.note
        ]
        self.assertTrue(jephthah_notes)
        self.assertEqual(jephthah_notes[0].certainty, "disputed")
        self.assertEqual(
            jephthah_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        ruth_legal_notes = [
            note
            for note in self.ruth.interpretive_notes
            if "not identical" in note.note
        ]
        self.assertTrue(ruth_legal_notes)
        self.assertEqual(
            ruth_legal_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )
        self.assertTrue(
            any(
                note.note_type == "later-reception"
                and "type of Christ" in note.note
                for note in self.ruth.interpretive_notes
            )
        )

    def test_sqlite_preserves_wave_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-judges-ruth.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            for json_record in (self.judges, self.ruth):
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
