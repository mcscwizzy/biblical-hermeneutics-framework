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


class RevelationRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("revelation").object

    def test_record_maps_named_audiences_and_seven_major_movements(self) -> None:
        people = " ".join(self.record.key_people)
        for figure in ("John", "seven assemblies", "slain Lamb", "Babylon"):
            self.assertIn(figure, people)
        structure = " ".join(self.record.structure)
        for anchor in (
            "Revelation 1:1-3:22",
            "Revelation 4:1-5:14",
            "Revelation 6:1-11:19",
            "Revelation 12:1-14:20",
            "Revelation 15:1-16:21",
            "Revelation 17:1-19:21",
            "Revelation 20:1-22:21",
        ):
            self.assertIn(anchor, structure)

    def test_record_removes_template_and_qualifies_context(self) -> None:
        self.assertTrue(
            any("named seer" in position for position in self.record.authorship_positions)
        )
        self.assertIn("seven named assemblies", self.record.original_audience)
        self.assertIn("Patmos", self.record.historical_setting)
        joined = " ".join(
            [
                self.record.historical_context,
                self.record.historical_setting,
                *self.record.date_ranges,
            ]
        )
        self.assertIn("debated", joined)
        self.assertIn("no emperor", joined)
        self.assertIn("does not establish one continuous empire-wide persecution", joined)

    def test_record_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.record.content_status, "draft")
        self.assertEqual(self.record.review_status, "in_review")
        self.assertTrue(self.record.human_review_required)
        self.assertIsNone(self.record.last_reviewed)
        self.assertEqual(self.record.section_status["human_review"], "missing")
        self.assertEqual(self.record.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.record.sources}
        self.assertGreaterEqual(len(self.record.claims), 28)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 38)
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
        self.assertGreaterEqual(len(external), 22)
        self.assertGreaterEqual(len(self.record.hebrew_words), 18)
        self.assertGreaterEqual(len(self.record.greek_words), 36)
        self.assertTrue(
            {
                "jesus",
                "new-jerusalem",
                "babylon-1",
                "kingdom-theme",
                "temple-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Revelation and is John the apostle?",
            "When was Revelation written under Nero or Domitian?",
            "Why was John on Patmos?",
            "Who were the seven churches of Asia?",
            "Is Revelation a letter prophecy or apocalypse?",
            "Does Revelation predict a linear end-times calendar?",
            "What is recapitulation in Revelation?",
            "Who are the twenty-four elders?",
            "Why is Jesus portrayed as a slain Lamb?",
            "Who are the four horsemen?",
            "Who are the 144000 in Revelation?",
            "Who are the two witnesses?",
            "Who is the woman clothed with the sun?",
            "Who is the dragon in Revelation 12?",
            "What is the beast from the sea?",
            "What is the beast from the land or false prophet?",
            "What does 666 mean in Revelation?",
            "Is Babylon Rome in Revelation?",
            "What is Armageddon?",
            "What do the seven seals trumpets and bowls mean?",
            "Is there one empire-wide persecution behind Revelation?",
            "What is the millennium in Revelation 20?",
            "What is the first resurrection?",
            "What are the lake of fire and second death?",
            "Who are the nations outside New Jerusalem?",
            "What is the tree of life in Revelation 22?",
            "Does Revelation teach eternal conscious torment?",
            "Does Revelation justify religious violence?",
            "How does Revelation reuse Daniel?",
            "How does Revelation reuse Ezekiel?",
            "How does Revelation reuse Exodus plagues?",
            "How does Revelation challenge Roman imperial power?",
            "What do the seven letters say to real assemblies?",
            "Does Revelation attack Jewish people as a synagogue of Satan?",
            "Is the woman Babylon an excuse for misogyny?",
            "Does Revelation identify the Catholic Church as Babylon?",
            "Does Revelation authorize modern nationalism?",
            "Should Christians set dates from Revelation?",
            "Does Revelation's new earth permit ecological neglect?",
            "What textual variant closes Revelation?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Revelation {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "revelation")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        checks = [
            ("Authorship", "John", "apostle"),
            ("Empire", "Rome", "Babylon"),
            ("Numbers", "144,000", "666"),
            ("Violence", "religious violence", "genocide"),
            ("Jewish", "antisemitism", "supersessionism"),
            ("Woman", "misogyny", "sexualized"),
            ("Application", "nationalism", "date-setting"),
            ("Created world", "ecological neglect", "earth"),
        ]
        for words in checks:
            with self.subTest(words=words):
                self.assertTrue(
                    any(all(word in note for word in words) for note in notes)
                )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-revelation.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database, root=self.root
            )
            sqlite_record = sqlite_library.retrieve_by_id("revelation").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
