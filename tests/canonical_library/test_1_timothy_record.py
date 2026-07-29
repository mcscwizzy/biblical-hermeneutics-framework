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


class FirstTimothyRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("1-timothy").object

    def test_record_maps_major_voices_groups_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul and Timothy",
            "teachers of different doctrine",
            "women and men",
            "overseers, deacons, and elders",
            "widows",
            "enslaved and free people",
            "wealthy members",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "1 Timothy 1:1-20",
            "1 Timothy 2:1-3:16",
            "1 Timothy 4:1-5:2",
            "1 Timothy 5:3-6:2",
            "1 Timothy 6:3-21",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        values = {
            *self.record.authorship_positions,
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
            "Titus",
            "Rome",
            "Corinth",
            "mission",
            "church formation",
            "pastoral instruction",
        ):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(
            any("disputed" in position for position in self.record.authorship_positions)
        )
        self.assertIn("does not establish", self.record.historical_setting)

    def test_record_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.record.content_status, "draft")
        self.assertEqual(self.record.review_status, "in_review")
        self.assertTrue(self.record.human_review_required)
        self.assertIsNone(self.record.last_reviewed)
        self.assertEqual(self.record.section_status["human_review"], "missing")
        self.assertEqual(self.record.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.record.sources}
        self.assertGreaterEqual(len(self.record.claims), 30)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 40)
        for claim in self.record.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_record_has_sources_lexical_data_and_graph_links(self) -> None:
        external = [
            source
            for source in self.record.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 20)
        self.assertGreaterEqual(len(self.record.hebrew_words), 10)
        self.assertGreaterEqual(len(self.record.greek_words), 20)
        self.assertTrue(
            {
                "paul",
                "timothy",
                "ephesus",
                "elders",
                "diaconate",
                "public-reading-of-scripture",
                "faith",
                "grace",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 1 Timothy and when?",
            "Why is Pauline authorship disputed?",
            "Was a secretary or Pauline school involved?",
            "Was Timothy in Ephesus?",
            "Who taught myths and genealogies?",
            "How does 1 Timothy use the law?",
            "What does arsenokoitai mean in 1 Timothy 1?",
            "Why pray for kings and authorities?",
            "Does God desires all to be saved teach universalism?",
            "What does one mediator mean?",
            "What does modest dress mean?",
            "May women teach in 1 Timothy 2?",
            "What does authentein mean?",
            "Why does the letter appeal to Adam and Eve?",
            "What does saved through childbearing mean?",
            "What are overseer qualifications?",
            "Must an overseer be male and married?",
            "Who are the women in 1 Timothy 3:11?",
            "What are deacon qualifications?",
            "What is the mystery of godliness?",
            "What does 1 Timothy say about asceticism?",
            "Does bodily training have value?",
            "What are public reading exhortation and teaching?",
            "How did Timothy receive his gift?",
            "What does do not let anyone despise your youth mean?",
            "How should older and younger people be treated?",
            "Who qualifies for the widow list?",
            "Did widows have a ministry office?",
            "What does double honor for elders mean?",
            "How should accusations against elders be handled?",
            "Does 1 Timothy protect abusive leaders?",
            "Why does Paul tell Timothy to drink wine?",
            "Does 1 Timothy endorse slavery?",
            "What is godliness with contentment?",
            "Is money the root of all evil?",
            "How should rich Christians use wealth?",
            "What is falsely named knowledge?",
            "How is 1 Timothy related to Acts Titus and 2 Timothy?",
            "How can 1 Timothy be read without misogyny or slavery apologetics?",
            "How should church leadership avoid authoritarian abuse?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"1 Timothy {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "1-timothy")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Gender", "silencing women", "misogyny"),
            ("Authority", "authentein", "authoritarian"),
            ("Leadership", "elder impunity", "victim blaming"),
            ("Slavery", "does not abolish", "slavery apologetics"),
            ("Wealth", "prosperity extraction", "poverty"),
            ("Application", "nationalism", "ecological"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-1-timothy.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("1-timothy").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
