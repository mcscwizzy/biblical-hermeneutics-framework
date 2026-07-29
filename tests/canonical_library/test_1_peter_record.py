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


class FirstPeterRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("1-peter").object

    def test_record_maps_people_provinces_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Peter, the named sender",
            "elect sojourners",
            "Silvanus and Mark",
            "elders, younger people, enslaved household members, wives, husbands, rulers, and masters",
        ):
            self.assertIn(person, people)
        places = " ".join(self.record.key_places)
        for province in ("Pontus", "Galatia", "Cappadocia", "Asia", "Bithynia"):
            self.assertIn(province, places)
        structure = " ".join(self.record.structure)
        for anchor in ("1 Peter 1:1-2:10", "1 Peter 2:11-4:11", "1 Peter 4:12-5:14"):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("James", "John", "church communities", "false teaching"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not identify", self.record.historical_setting)
        self.assertTrue(
            any("Babylon" in position and "Rome" in position
                for position in self.record.authorship_positions)
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
        self.assertGreaterEqual(len(self.record.claims), 30)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 40)
        for claim in self.record.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
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
        self.assertGreaterEqual(len(self.record.greek_words), 25)
        self.assertTrue(
            {
                "peter",
                "perseverance",
                "hope-theme",
                "holiness-theme",
                "people-of-god-theme",
                "baptism",
                "noah",
                "silas",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 1 Peter and when?",
            "Did the apostle Peter write 1 Peter?",
            "Did Silvanus write 1 Peter?",
            "Does Babylon mean Rome in 1 Peter?",
            "Who are the elect sojourners in the diaspora?",
            "Was the audience Jewish or gentile?",
            "Was 1 Peter written during Nero's persecution?",
            "What genre is 1 Peter?",
            "What does foreknowledge mean in 1 Peter 1?",
            "What is new birth into a living hope?",
            "What is the imperishable inheritance?",
            "What does testing faith by fire mean?",
            "What does be holy mean in 1 Peter?",
            "What does ransom with Christ's blood mean?",
            "What is imperishable seed in 1 Peter 1?",
            "What are living stones in 1 Peter 2?",
            "What is a royal priesthood in 1 Peter?",
            "Does 1 Peter teach replacement theology?",
            "What does honorable conduct among the nations mean?",
            "Must Christians obey every government?",
            "Does 1 Peter endorse slavery?",
            "What does follow Christ's steps mean for suffering?",
            "Does 1 Peter tell abuse victims to submit?",
            "What does 1 Peter say to husbands?",
            "What does repay evil with blessing mean?",
            "Who are the spirits in prison?",
            "How does Noah relate to baptism?",
            "What does baptism now saves you mean?",
            "Who are the dead preached to in 1 Peter 4?",
            "What does love covers sins mean?",
            "How should gifts and hospitality be used?",
            "What is the fiery trial in 1 Peter?",
            "Why does judgment begin with God's household?",
            "What does sharing Christ's sufferings mean?",
            "What does 1 Peter teach elders?",
            "What does younger people submit to elders mean?",
            "What does cast anxiety on God mean?",
            "Is the devil a literal roaring lion?",
            "Who is Silvanus in 1 Peter 5?",
            "Who are Babylon and Mark in the closing?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"1 Peter {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "1-peter")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("People of God", "supersessionism", "ethnic nationalism"),
            ("Slavery", "trafficking", "worker exploitation"),
            ("Household", "domestic abuse", "coercive submission"),
            ("Suffering", "victim blaming", "trauma"),
            ("Authorities", "authoritarian", "injustice"),
            ("Application", "forced conversion", "ecological neglect"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-1-peter.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("1-peter").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
