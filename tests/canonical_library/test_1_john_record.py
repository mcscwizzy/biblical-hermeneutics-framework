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


class FirstJohnRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("1-john").object

    def test_record_maps_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "anonymous first-person plural voice",
            "opponents or secessionists as reconstructed figures",
            "children, fathers, and young people",
            "Cain, Jesus, God, Spirit, and the Paraclete",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in ("1 John 1:1-2:27", "1 John 2:28-4:6", "1 John 4:7-5:21"):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        values = {
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in ("James", "Peter", "Asia Minor", "persecution"):
            self.assertNotIn(placeholder, values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertIn("does not name", self.record.historical_setting)
        self.assertTrue(
            any("anonymous" in position for position in self.record.authorship_positions)
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
                "john-son-of-zebedee",
                "agape",
                "light-and-darkness-theme",
                "incarnation",
                "witness-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 1 John and when?",
            "Did John the apostle write 1 John?",
            "Is 1 John anonymous?",
            "How is 1 John related to the Gospel of John?",
            "Were there Johannine secessionists?",
            "What is the word of life in 1 John?",
            "What does fellowship mean in 1 John?",
            "What does walking in the light mean?",
            "Does 1 John say Christians never sin?",
            "Why confess sins in 1 John 1:9?",
            "What does the blood of Jesus cleanse?",
            "How is Jesus an advocate in 1 John?",
            "What does hilasmos mean in 1 John 2:2?",
            "What is the old and new commandment?",
            "What does do not love the world mean?",
            "What is the last hour in 1 John?",
            "Who are the antichrists in 1 John?",
            "What is the anointing that teaches?",
            "What does remain or abide mean in 1 John?",
            "Can those born of God still sin?",
            "Why does 1 John mention Cain?",
            "What if our heart condemns us?",
            "How should Christians test the spirits?",
            "What does Jesus Christ came in the flesh mean?",
            "What does God is love mean?",
            "Does perfect love cast out fear?",
            "What faith conquers the world?",
            "What do water and blood mean in 1 John?",
            "Is the Comma Johanneum original?",
            "What is sin leading to death?",
            "Should Christians pray about deadly sin?",
            "Does the evil one touch believers?",
            "Is Jesus called the true God in 1 John 5:20?",
            "Why does 1 John end with keep from idols?",
            "Does 1 John teach perfectionism?",
            "Can 1 John intensify scrupulosity?",
            "Does 1 John authorize schism or public shaming?",
            "How should antichrist language be used today?",
            "How does 1 John use testimony language?",
            "How should love in 1 John shape care for creation?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"1 John {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "1-john")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Opponents", "dehumanization", "schism"),
            ("Sinlessness", "perfectionism", "scrupulosity"),
            ("Confession", "coercive", "public shaming"),
            ("Authority", "spiritual abuse", "anti-intellectualism"),
            ("Application", "forced conversion", "religious violence"),
            ("Love", "ecological neglect", "creation"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-1-john.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("1-john").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
