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


class EcclesiastesRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.ecclesiastes = cls.library.retrieve_by_id("ecclesiastes").object

    def test_ecclesiastes_distinguishes_frame_qohelet_and_epilogue(self) -> None:
        self.assertTrue(
            {
                "the frame narrator",
                "Qohelet",
                "Qohelet's royal persona",
                "the epilogue narrator",
                "God",
                "the oppressed",
                "rulers",
                "workers",
                "the aged person of Ecclesiastes 12",
            }.issubset(self.ecclesiastes.key_people)
        )
        self.assertTrue(
            {
                "Ecclesiastes 1:1-11: superscription, hebel refrain, and opening poem on recurring cycles",
                "Ecclesiastes 1:12-2:26: Qohelet's royal investigation of wisdom, pleasure, achievement, toil, and enjoyment",
                "Ecclesiastes 3:1-6:12: time poem, divine gift and limits, injustice, oppression, worship, wealth, and mortality",
                "Ecclesiastes 7:1-10:20: comparative sayings and investigations of wisdom, power, uncertainty, and death",
                "Ecclesiastes 11:1-12:7: risk, generosity, joy, accountability, aging, and return to the Creator",
                "Ecclesiastes 12:8: closing hebel refrain",
                "Ecclesiastes 12:9-14: epilogue evaluating Qohelet and concluding with fear of God and judgment",
            }.issubset(self.ecclesiastes.structure)
        )

    def test_ecclesiastes_removes_inherited_generic_wisdom_placeholder(self) -> None:
        inherited_values = {
            "Traditional attribution to Solomon or wise circles",
            "Many scholars see collected wisdom and later shaping",
            "Monarchic wisdom traditions",
            "Israel's covenant community learning wise living under God",
            "Royal, instructional, and reflective wisdom settings within Israel",
            "Job",
            "David",
            "court",
            "temple",
            "suffering",
            "wisdom instruction",
            "praise and lament",
        }
        record_values = {
            *self.ecclesiastes.authorship_positions,
            *self.ecclesiastes.date_ranges,
            self.ecclesiastes.original_audience,
            self.ecclesiastes.historical_setting,
            *self.ecclesiastes.key_people,
            *self.ecclesiastes.key_places,
            *self.ecclesiastes.key_events,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertIn("wisdom reflection", self.ecclesiastes.genre)
        self.assertIn("royal autobiography or persona", self.ecclesiastes.genre)
        self.assertIn("time poem", self.ecclesiastes.genre)
        self.assertIn("frame narrative", self.ecclesiastes.genre)
        self.assertIn(
            "4QQoha (4Q109) and 4QQohb (4Q110)",
            self.ecclesiastes.primary_sources,
        )

    def test_ecclesiastes_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.ecclesiastes.content_status, "draft")
        self.assertEqual(self.ecclesiastes.review_status, "in_review")
        self.assertTrue(self.ecclesiastes.human_review_required)
        self.assertIsNone(self.ecclesiastes.last_reviewed)
        self.assertEqual(
            self.ecclesiastes.section_status["human_review"],
            "missing",
        )
        self.assertEqual(
            self.ecclesiastes.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.ecclesiastes.sources}
        self.assertGreaterEqual(len(self.ecclesiastes.claims), 11)
        self.assertGreaterEqual(len(self.ecclesiastes.interpretive_notes), 16)
        for claim in self.ecclesiastes.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.ecclesiastes.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_ecclesiastes_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.ecclesiastes.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 10)
        self.assertTrue(self.ecclesiastes.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.ecclesiastes.hermeneutical_lens[
                "common_misinterpretations"
            ]
        )
        self.assertTrue(
            self.ecclesiastes.retrieval_metadata["common_questions"]
        )
        self.assertTrue(
            self.ecclesiastes.retrieval_metadata["semantic_keywords"]
        )
        self.assertTrue(
            {
                "wisdom-theme",
                "solomon",
                "proverbs",
                "job",
                "psalms",
                "justice-theme",
                "creation-theme",
                "worship-theme",
                "dead-sea-scrolls",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.ecclesiastes.related_objects
                }
            )
        )

    def test_retrieval_answers_ecclesiastes_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Did Solomon write Ecclesiastes?",
            "What does hebel mean in Ecclesiastes?",
            "What does gain yitron mean under the sun?",
            "Is Ecclesiastes nihilistic or does it commend enjoyment?",
            "Who is Qohelet and who speaks in the epilogue?",
            "Does a time to kill authorize violence or murder?",
            "What does Ecclesiastes say about oppression and injustice?",
            "Does Ecclesiastes blame depressed or grieving people?",
            "What does Ecclesiastes 12 say about aging and disability?",
            "What are 4Q109 and 4Q110 Qohelet scrolls?",
            "Why is Greek Ecclesiastes called Ecclesiast?",
            "How do Proverbs Job and Ecclesiastes differ?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "ecclesiastes")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        hebel_notes = [
            note
            for note in self.ecclesiastes.interpretive_notes
            if "Hebel literally evokes vapor or breath" in note.note
        ]
        self.assertTrue(hebel_notes)
        self.assertEqual(
            hebel_notes[0].dispute_status,
            "lexical_uncertainty",
        )

        enjoyment_notes = [
            note
            for note in self.ecclesiastes.interpretive_notes
            if "does not teach hedonism or prosperity" in note.note
        ]
        self.assertTrue(enjoyment_notes)
        self.assertEqual(
            enjoyment_notes[0].note_type,
            "interpretive-caution",
        )

        violence_notes = [
            note
            for note in self.ecclesiastes.interpretive_notes
            if "does not command killing or authorize violence" in note.note
        ]
        self.assertTrue(violence_notes)
        self.assertEqual(
            violence_notes[0].note_type,
            "interpretive-caution",
        )

        aging_notes = [
            note
            for note in self.ecclesiastes.interpretive_notes
            if "must not be used to mock aging or disability" in note.note
        ]
        self.assertTrue(aging_notes)
        self.assertEqual(
            aging_notes[0].note_type,
            "interpretive-caution",
        )

        mental_health_notes = [
            note
            for note in self.ecclesiastes.interpretive_notes
            if "is not a diagnosis of clinical depression" in note.note
        ]
        self.assertTrue(mental_health_notes)
        self.assertEqual(
            mental_health_notes[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_ecclesiastes_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-ecclesiastes.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id(
                "ecclesiastes"
            ).object
            self.assertEqual(
                sqlite_record.to_dict(),
                self.ecclesiastes.to_dict(),
            )


if __name__ == "__main__":
    unittest.main()
