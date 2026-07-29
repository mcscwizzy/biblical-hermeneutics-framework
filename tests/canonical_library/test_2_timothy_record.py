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


class SecondTimothyRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("2-timothy").object

    def test_record_maps_major_voices_people_and_literary_units(self) -> None:
        people = " ".join(self.record.key_people)
        for person in (
            "Paul and Timothy",
            "Lois and Eunice",
            "Onesiphorus",
            "Hymenaeus and Philetus",
            "Demas, Crescens, Titus, Luke, Mark, and Tychicus",
            "Prisca, Aquila",
            "Eubulus, Pudens, Linus, Claudia",
        ):
            self.assertIn(person, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "2 Timothy 1:1-18",
            "2 Timothy 2:1-26",
            "2 Timothy 3:1-17",
            "2 Timothy 4:1-22",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        values = {
            *self.record.authorship_positions,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
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
                "lois",
                "eunice",
                "public-reading-of-scripture",
                "perseverance",
                "faith",
                "grace",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 2 Timothy and when?",
            "Why is Pauline authorship disputed?",
            "Is 2 Timothy a prison letter or literary testament?",
            "Where was Paul imprisoned?",
            "How is 2 Timothy related to Acts 1 Timothy and Titus?",
            "Who were Lois and Eunice?",
            "What gift came through laying on hands?",
            "What is the spirit of fear?",
            "What is the entrusted deposit?",
            "Who was Onesiphorus?",
            "Did everyone in Asia abandon Paul?",
            "What do soldier athlete and farmer metaphors mean?",
            "What does an athlete competing according to the rules mean?",
            "What is the faithful saying in 2 Timothy 2?",
            "What resurrection error did Hymenaeus and Philetus teach?",
            "What does rightly handling the word of truth mean?",
            "What are vessels for honorable and dishonorable use?",
            "Who were Jannes and Jambres?",
            "Does 2 Timothy blame women learners?",
            "What do the last days mean?",
            "What are the sacred writings?",
            "What does all Scripture is God breathed mean?",
            "Does 2 Timothy 3:16 define a closed Bible canon?",
            "What does Scripture being useful and sufficient mean?",
            "What are itching ears?",
            "What does preach the word mean?",
            "What does Paul poured out as a drink offering mean?",
            "What is the crown of righteousness?",
            "What was Paul's first defense?",
            "What does rescued from the lion's mouth mean?",
            "Why did Demas leave?",
            "Why bring Mark because he is useful?",
            "What happened to Trophimus at Miletus?",
            "What were the cloak books and parchments?",
            "Who was Alexander the coppersmith?",
            "Who was Claudia?",
            "Do the greetings prove a complete Pauline itinerary?",
            "Does 2 Timothy glorify martyrdom or trauma?",
            "Do military and athletic metaphors authorize coercion?",
            "How can 2 Timothy be read without misogyny authoritarianism or anti intellectualism?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"2 Timothy {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "2-timothy")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Scripture", "theopneustos", "closed canon"),
            ("Women", "learning women", "misogyny"),
            ("Metaphors", "militarism", "productivity coercion"),
            ("Suffering", "martyrdom", "trauma glorification"),
            ("Leadership", "authoritarian", "leader exceptionalism"),
            ("Application", "nationalism", "ecological neglect"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-2-timothy.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("2-timothy").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
