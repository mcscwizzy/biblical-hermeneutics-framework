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


class SecondPeterRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("2-peter").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Symeon or Simon Peter, the named sender",
            "false teachers and scoffers as rhetorical figures",
            "Noah, Lot, Balaam, the donkey, and Paul",
            "angels, scriptural prophets, eyewitnesses, and addressees",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in ("2 Peter 1:1-21", "2 Peter 2:1-22", "2 Peter 3:1-18"):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("James", "John", "Asia Minor", "persecution"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not name", self.record.historical_setting)
        self.assertTrue(
            any("pseudepigraph" in position for position in self.record.authorship_positions)
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
                "paul",
                "noah",
                "balaam",
                "the-flood",
                "second-coming",
                "new-creation-theme",
                "final-judgment",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 2 Peter and when?",
            "Did the apostle Peter write 2 Peter?",
            "Is 2 Peter pseudepigraphal?",
            "Does 2 Peter depend on Jude?",
            "What does Symeon Peter mean?",
            "What is faith of equal honor?",
            "What does participate in the divine nature mean?",
            "What is the virtue chain in 2 Peter 1?",
            "How do you confirm election and calling?",
            "What does Peter's tent and exodus mean?",
            "Does 2 Peter describe the transfiguration?",
            "What is the morning star in 2 Peter 1?",
            "What does no private interpretation mean?",
            "How were prophets carried by the Holy Spirit?",
            "Who are the false teachers in 2 Peter?",
            "What does 2 Peter say about angels in Tartarus?",
            "How does Noah and the flood function in 2 Peter?",
            "Why does 2 Peter mention Sodom and Lot?",
            "What does 2 Peter say about Balaam and the donkey?",
            "What is the textual problem in 2 Peter 2:11?",
            "Does 2 Peter dehumanize opponents?",
            "Who are the scoffers in 2 Peter 3?",
            "What does one day is a thousand years mean?",
            "Does God want everyone to repent in 2 Peter 3:9?",
            "What are the elements that melt with fire?",
            "Does 2 Peter predict destruction of the earth?",
            "What are the new heavens and new earth?",
            "Why has the second coming been delayed?",
            "Does 2 Peter call Paul's letters scripture?",
            "Did 2 Peter know a collection of Paul's letters?",
            "Is 2 Peter anti-intellectual?",
            "Does 2 Peter authorize date setting?",
            "What does grow in grace and knowledge mean?",
            "How should prophecy be interpreted in 2 Peter?",
            "What is the majestic glory at the transfiguration?",
            "What does all things for life and godliness mean?",
            "What are the precious and very great promises?",
            "What is the proverb about the dog and sow?",
            "How does 2 Peter use Jewish apocalyptic traditions?",
            "How should 2 Peter's cosmic judgment shape ecology?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"2 Peter {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "2-peter")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Opponents", "dehumanization", "polemical"),
            ("Sexual", "purity shaming", "anti-LGBTQ"),
            ("Prophecy", "manipulation", "anti-intellectualism"),
            ("Parousia", "date setting", "conspiracy"),
            ("Cosmic fire", "ecological neglect", "new creation"),
            ("Application", "forced conversion", "religious violence"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-2-peter.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("2-peter").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
