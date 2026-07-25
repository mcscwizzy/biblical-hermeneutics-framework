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


class AmosRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.amos = cls.library.retrieve_by_id("amos").object

    def test_amos_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Amos of Tekoa",
                "YHWH in reported speech and direct address",
                "the prophetic first-person voice in the visions",
                "the third-person narrator of the Bethel conflict",
                "Amaziah, priest of Bethel",
                "Jeroboam II of Israel and Uzziah of Judah",
                "Israel, Judah, Samaria's elites, and the women addressed as cows of Bashan",
                "merchants, judges, poor people, oppressed people, Nazirites, and prophets",
                "Aram, Philistia, Tyre, Edom, Ammon, and Moab",
            }.issubset(self.amos.key_people)
        )
        self.assertTrue(
            {
                "Amos 1:1-2: superscription and opening theophanic announcement",
                "Amos 1:3-2:16: seven neighboring peoples plus Israel under accusation and judgment",
                "Amos 3:1-6:14: summons, accusations, laments, woes, doxologies, and threatened exile",
                "Amos 7:1-9:10: five visions surrounding the Amos-Amaziah narrative and further judgment speech",
                "Amos 9:11-15: raising David's fallen booth and agricultural, urban, and land restoration",
            }.issubset(self.amos.structure)
        )

    def test_amos_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Hosea",
            "Jonah",
            "Nineveh",
        }
        record_values = {
            *self.amos.authorship_positions,
            *self.amos.date_ranges,
            self.amos.historical_setting,
            *self.amos.key_people,
            *self.amos.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "prophetic superscription",
                "nations oracle",
                "accusation and judgment oracle",
                "summons to hear",
                "rhetorical-question chain",
                "lament",
                "woe oracle",
                "hymn and doxology",
                "vision report",
                "symbolic wordplay",
                "biographical narrative",
                "disputation",
                "salvation oracle",
            }.issubset(self.amos.genre)
        )
        self.assertIn(
            "Masoretic Amos within the Book of the Twelve",
            self.amos.primary_sources,
        )
        self.assertIn(
            "Old Greek Amos and other ancient versions",
            self.amos.primary_sources,
        )
        self.assertIn(
            "Qumran manuscripts of the Twelve preserving portions of Amos",
            self.amos.primary_sources,
        )

    def test_amos_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.amos.content_status, "draft")
        self.assertEqual(self.amos.review_status, "in_review")
        self.assertTrue(self.amos.human_review_required)
        self.assertIsNone(self.amos.last_reviewed)
        self.assertEqual(self.amos.section_status["human_review"], "missing")
        self.assertEqual(
            self.amos.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.amos.sources}
        self.assertGreaterEqual(len(self.amos.claims), 20)
        self.assertGreaterEqual(len(self.amos.interpretive_notes), 30)
        for claim in self.amos.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.amos.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_amos_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.amos.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 14)
        self.assertTrue(self.amos.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.amos.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.amos.retrieval_metadata["common_questions"])
        self.assertTrue(self.amos.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "justice-theme",
                "righteousness-theme",
                "judgment",
                "day-of-the-lord-prophecy",
                "restoration-theme",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.amos.related_objects
                }
            )
        )

    def test_retrieval_answers_amos_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Amos of Tekoa?",
            "Was Amos a shepherd, livestock breeder, or sycamore fig dresser?",
            "When did Amos prophesy under Jeroboam II and Uzziah?",
            "Can Amos's earthquake be dated archaeologically?",
            "Why does Amos begin with seven nations plus Israel?",
            "What does for three transgressions and for four mean in Amos?",
            "Who are the cows of Bashan in Amos 4?",
            "Does cows of Bashan authorize misogynistic insults?",
            "What does let justice roll down like waters mean in Amos 5:24?",
            "Does Amos condemn all worship, sacrifice, music, or Jewish ritual?",
            "What is the day of YHWH in Amos 5?",
            "Who are Sikkuth and Kiyyun in Amos 5:26?",
            "What are Amos's five visions?",
            "Why does Amos intercede after the locust and fire visions?",
            "What happens between Amos and Amaziah at Bethel?",
            "Was Amos a professional prophet or not a prophet?",
            "What is the plumb line or tin in Amos 7?",
            "How does the summer fruit wordplay work in Amos 8?",
            "What is the famine of hearing the words of YHWH?",
            "What is David's fallen booth in Amos 9?",
            "How does Acts 7 quote Amos?",
            "How does James use Amos in Acts 15?",
            "Do Acts 15 and Amos erase Israel or replace Jewish readings?",
            "How should Amos be read about poverty, debt, labor, courts, and dishonest trade?",
            "Does Amos authorize partisan politics, nationalism, vengeance, or violence?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "amos")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        occupation = [
            note
            for note in self.amos.interpretive_notes
            if "Amos's labels as noqed, boqer, and dresser of sycamore figs do not securely establish either poverty or elite wealth"
            in note.note
        ]
        self.assertTrue(occupation)
        self.assertEqual(
            occupation[0].dispute_status,
            "lexical_uncertainty",
        )

        ritual = [
            note
            for note in self.amos.interpretive_notes
            if "Amos's attack on festivals, sacrifices, and songs targets worship joined to exploitation"
            in note.note
        ]
        self.assertTrue(ritual)
        self.assertEqual(ritual[0].note_type, "interpretive-caution")

        cows = [
            note
            for note in self.amos.interpretive_notes
            if "The cows-of-Bashan address must not be reused as a misogynistic insult"
            in note.note
        ]
        self.assertTrue(cows)
        self.assertEqual(cows[0].note_type, "interpretive-caution")

        politics = [
            note
            for note in self.amos.interpretive_notes
            if "Amos's justice language cannot be captured by one modern party"
            in note.note
        ]
        self.assertTrue(politics)
        self.assertEqual(politics[0].note_type, "interpretive-caution")

        antisupersessionism = [
            note
            for note in self.amos.interpretive_notes
            if "Christian reuse of Amos in Acts must not erase Israel, Jewish readers, or continuing Jewish interpretation"
            in note.note
        ]
        self.assertTrue(antisupersessionism)
        self.assertEqual(
            antisupersessionism[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_amos_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-amos.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("amos").object
            self.assertEqual(sqlite_record.to_dict(), self.amos.to_dict())
