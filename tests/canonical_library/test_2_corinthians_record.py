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


class SecondCorinthiansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("2-corinthians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        self.assertTrue(
            {
                "Paul and Timothy as named senders; the Corinthian assembly and all the saints throughout Achaia as addressees",
                "Titus, the unnamed brother or brothers, Macedonian assemblies, and the saints in Jerusalem connected with the collection",
                "The offender, injured party, reconciled majority, rival apostles, rhetorical interlocutors, coworkers, messengers, patrons, laborers, enslaved and free people, women and men, and later interpreters",
                "Moses and scriptural voices; the suffering and risen Messiah; Paul as autobiographical speaker, ironic boaster, visionary, and planned visitor",
            }.issubset(self.record.key_people)
        )
        self.assertTrue(
            {
                "2 Corinthians 1:1-2:13: prescript, blessing, affliction and comfort, conscience, changed travel, painful visit and letter, forgiveness, Troas, and Titus",
                "2 Corinthians 2:14-7:4: triumph and aroma, sufficiency, letter and Spirit, Moses' veil, earthen vessels, resurrection, reconciliation, ambassador appeal, holiness, and renewed appeal",
                "2 Corinthians 7:5-16: Macedonia, Titus's arrival and report, grief, repentance, restored confidence, and unresolved reconstruction",
                "2 Corinthians 8:1-9:15: Macedonian example, Jerusalem collection, grace, equality, delegated brothers, accountability, sowing, generosity, thanksgiving, and solidarity",
                "2 Corinthians 10:1-13:10: authority, boasting, rival apostles, fool's speech, hardships, visions, thorn, signs, weakness, planned visit, warning, and self-examination",
                "2 Corinthians 13:11-14: restoration appeal, peace, greeting, and triadic benediction",
            }.issubset(self.record.structure)
        )

    def test_record_removes_placeholder_and_qualifies_composition(self) -> None:
        record_values = {
            *self.record.authorship_positions,
            *self.record.key_places,
            *self.record.key_events,
        }
        self.assertNotIn("Rome", record_values)
        self.assertNotIn("church formation", record_values)
        self.assertNotIn("pastoral instruction", record_values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "Pauline authorship" in position
                and "Timothy" in position
                and "co-sender" in position
                for position in self.record.authorship_positions
            )
        )
        self.assertTrue(
            {
                "Pauline letter with prescript, blessing, travel explanation, autobiographical report, appeal, warning, greeting, and benediction",
                "scriptural exposition, contrast, metaphor, hardship catalog, ambassadorial appeal, collection exhortation, exemplum, and commendation",
                "irony, invective, parody, boasting, fool's speech, vision report, third-person self-reference, examination, and restoration appeal",
            }.issubset(self.record.genre)
        )

    def test_record_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.record.content_status, "draft")
        self.assertEqual(self.record.review_status, "in_review")
        self.assertTrue(self.record.human_review_required)
        self.assertIsNone(self.record.last_reviewed)
        self.assertEqual(self.record.section_status["human_review"], "missing")
        self.assertEqual(self.record.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.record.sources}
        self.assertGreaterEqual(len(self.record.claims), 38)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 60)
        for claim in self.record.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_record_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.record.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.record.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.record.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.record.retrieval_metadata["common_questions"])
        self.assertTrue(self.record.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "paul",
                "corinth",
                "new-covenant",
                "theology-of-suffering",
                "theology-of-the-cross",
                "moses",
                "resurrection-theme",
                "spirit-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 2 Corinthians and what role did Timothy have?",
            "When and where was Second Corinthians written?",
            "How many letters make up 2 Corinthians?",
            "What were the painful visit and severe letter?",
            "Who were the offender and injured party in 2 Corinthians?",
            "Why did Paul change his travel plans?",
            "What does triumph procession mean in 2 Corinthians?",
            "What does aroma of Christ mean in 2 Corinthians?",
            "What does letter kills but Spirit gives life mean?",
            "Does 2 Corinthians 3 support antisemitism or supersessionism?",
            "What is the veil over Moses in 2 Corinthians 3?",
            "What does beholding or reflecting glory mean in 2 Corinthians?",
            "What is treasure in earthen vessels?",
            "What are the outer and inner person in 2 Corinthians?",
            "What is the heavenly dwelling in 2 Corinthians 5?",
            "What is the judgment seat of Christ?",
            "What does knowing Christ according to flesh mean?",
            "How does 2 Corinthians 5:17 use the phrase new creation?",
            "What does ambassador for Christ mean?",
            "What does be reconciled to God mean?",
            "What does do not be unequally yoked mean?",
            "What does temple of the living God mean in 2 Corinthians?",
            "What is godly grief in 2 Corinthians 7?",
            "Who was Titus and what report did he bring?",
            "Why were the Macedonians poor but generous?",
            "What was the Jerusalem collection in 2 Corinthians?",
            "What does equality mean in 2 Corinthians 8?",
            "How did Paul make the collection accountable?",
            "What does sowing and reaping mean in 2 Corinthians 9?",
            "Does cheerful giving justify financial pressure?",
            "Who were the super apostles in 2 Corinthians?",
            "What is Paul's fool's speech?",
            "Why does Paul list beatings shipwrecks and dangers?",
            "What is the third heaven and paradise?",
            "What was Paul's thorn in the flesh?",
            "What are the signs of an apostle?",
            "What does power made perfect in weakness mean?",
            "What does examine yourselves mean in 2 Corinthians 13?",
            "What does the closing grace love and fellowship benediction mean?",
            "Does 2 Corinthians command coerced forgiveness?",
            "Does 2 Corinthians require reconciliation without safety or repair?",
            "Does 2 Corinthians glorify suffering or stigmatize disability?",
            "Does 2 Corinthians justify collection coercion or prosperity teaching?",
            "Does 2 Corinthians justify slavery or worker exploitation?",
            "Does 2 Corinthians justify misogyny or anti LGBTQ coercion?",
            "Does 2 Corinthians authorize public shaming or authoritarian discipline?",
            "Does 2 Corinthians authorize nationalism conspiracy theories or partisan capture?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"2 Corinthians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "2-corinthians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        self.assertTrue(
            any(
                "Moses' veil" in note
                and "antisemitism" in note
                and "supersessionism" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "reconciliation" in note
                and "safety" in note
                and "repair" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "thorn in the flesh" in note
                and "disability" in note
                and "medical neglect" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "collection" in note
                and "financial coercion" in note
                and "accountability" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "weakness" in note
                and "glorify suffering" in note
                and "victim" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-2-corinthians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("2-corinthians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
