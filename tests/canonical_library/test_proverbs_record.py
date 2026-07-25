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


class ProverbsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.proverbs = cls.library.retrieve_by_id("proverbs").object

    def test_proverbs_tracks_distinct_collections_and_voices(self) -> None:
        self.assertTrue(
            {
                "YHWH",
                "Solomon",
                "the wise",
                "Hezekiah's officials",
                "Agur son of Jakeh",
                "King Lemuel",
                "King Lemuel's mother",
                "Woman Wisdom",
                "Woman Folly",
                "the capable woman",
            }.issubset(self.proverbs.key_people)
        )
        self.assertTrue(
            {
                "Proverbs 1:1-9:18: title, purpose, parental instructions, and rival invitations of Wisdom and Folly",
                "Proverbs 10:1-22:16: first Solomonic collection of mostly sentence sayings",
                "Proverbs 22:17-24:22: words of the wise",
                "Proverbs 24:23-34: further sayings of the wise",
                "Proverbs 25:1-29:27: Solomonic proverbs copied by Hezekiah's officials",
                "Proverbs 30:1-33: words of Agur, including numerical sayings and riddling observations",
                "Proverbs 31:1-9: words taught to King Lemuel by his mother",
                "Proverbs 31:10-31: alphabetic poem praising a capable woman",
            }.issubset(self.proverbs.structure)
        )

    def test_proverbs_removes_inherited_generic_wisdom_placeholder(self) -> None:
        inherited_values = {
            "Traditional attribution to Solomon or wise circles",
            "Many scholars see collected wisdom and later shaping",
            "Monarchic wisdom traditions",
            "Israel's covenant community learning wise living under God",
            "Royal, instructional, and reflective wisdom settings within Israel",
            "Job",
            "David",
            "temple",
            "suffering",
            "praise and lament",
        }
        record_values = {
            *self.proverbs.authorship_positions,
            *self.proverbs.date_ranges,
            self.proverbs.original_audience,
            self.proverbs.historical_setting,
            *self.proverbs.key_people,
            *self.proverbs.key_places,
            *self.proverbs.key_events,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertIn("instruction discourse", self.proverbs.genre)
        self.assertIn("sentence saying", self.proverbs.genre)
        self.assertIn("numerical saying", self.proverbs.genre)
        self.assertIn("alphabetic acrostic poem", self.proverbs.genre)
        self.assertIn(
            "Septuagint Proverbs with a different order and additional material",
            self.proverbs.primary_sources,
        )

    def test_proverbs_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.proverbs.content_status, "draft")
        self.assertEqual(self.proverbs.review_status, "in_review")
        self.assertTrue(self.proverbs.human_review_required)
        self.assertIsNone(self.proverbs.last_reviewed)
        self.assertEqual(self.proverbs.section_status["human_review"], "missing")
        self.assertEqual(self.proverbs.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.proverbs.sources}
        self.assertGreaterEqual(len(self.proverbs.claims), 10)
        self.assertGreaterEqual(len(self.proverbs.interpretive_notes), 15)
        for claim in self.proverbs.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.proverbs.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_proverbs_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.proverbs.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 9)
        self.assertTrue(self.proverbs.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.proverbs.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.proverbs.retrieval_metadata["common_questions"])
        self.assertTrue(self.proverbs.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "wisdom-theme",
                "solomon",
                "justice-theme",
                "creation-theme",
                "word-of-god-theme",
                "job",
                "ecclesiastes",
                "james",
                "hezekiahs-reforms",
            }.issubset(
                {relationship.id for relationship in self.proverbs.related_objects}
            )
        )

    def test_retrieval_answers_proverbs_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Did Solomon write every proverb in Proverbs?",
            "Who are Agur and King Lemuel in Proverbs 30 and 31?",
            "What did Hezekiah's officials copy in Proverbs 25?",
            "Are biblical proverbs unconditional promises?",
            "Why do Proverbs 26:4 and 26:5 contradict each other?",
            "How is the Instruction of Amenemope related to Proverbs 22?",
            "Who are Woman Wisdom and Woman Folly in Proverbs?",
            "Does Proverbs 31 give every woman a mandatory checklist?",
            "Does spare the rod authorize hitting children?",
            "Why is Greek Septuagint Proverbs in a different order?",
            "Does Proverbs teach that poor people are always lazy?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "proverbs")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        promise_notes = [
            note
            for note in self.proverbs.interpretive_notes
            if "not unconditional promises" in note.note
        ]
        self.assertTrue(promise_notes)
        self.assertEqual(promise_notes[0].note_type, "interpretive-caution")

        discipline_notes = [
            note
            for note in self.proverbs.interpretive_notes
            if "does not authorize abuse" in note.note
        ]
        self.assertTrue(discipline_notes)
        self.assertEqual(discipline_notes[0].note_type, "interpretive-caution")

        gender_notes = [
            note
            for note in self.proverbs.interpretive_notes
            if "must not become a universal suspicion of women" in note.note
        ]
        self.assertTrue(gender_notes)
        self.assertEqual(gender_notes[0].note_type, "interpretive-caution")

        wisdom_notes = [
            note
            for note in self.proverbs.interpretive_notes
            if "Proverbs 8:22 uses the lexically debated Hebrew verb qanah" in note.note
        ]
        self.assertTrue(wisdom_notes)
        self.assertEqual(
            wisdom_notes[0].dispute_status,
            "lexical_uncertainty",
        )

        amenemope_notes = [
            note
            for note in self.proverbs.interpretive_notes
            if "does not by itself settle the direction or mechanism" in note.note
        ]
        self.assertTrue(amenemope_notes)
        self.assertEqual(
            amenemope_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

    def test_sqlite_preserves_proverbs_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-proverbs.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("proverbs").object
            self.assertEqual(sqlite_record.to_dict(), self.proverbs.to_dict())


if __name__ == "__main__":
    unittest.main()
