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


class DanielRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.daniel = cls.library.retrieve_by_id("daniel").object

    def test_daniel_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Daniel, also called Belteshazzar",
                "Hananiah, Mishael, and Azariah, also called Shadrach, Meshach, and Abednego",
                "Nebuchadnezzar",
                "Belshazzar",
                "Darius the Mede and Cyrus the Persian",
                "Gabriel, Michael, and other heavenly interpreters or princes",
                "the Ancient of Days, the humanlike figure, beasts, horns, and saints of the Most High",
                "court narrators, royal speakers, communal prayers, and Daniel's visionary first person",
            }.issubset(self.daniel.key_people)
        )
        self.assertTrue(
            {
                "Daniel 1: Judean captives, court education, names, food test, wisdom, and service",
                "Daniel 2-6: multilingual court and diaspora tales of dreams, images, worship coercion, royal pride, judgment, and deliverance",
                "Daniel 7-12: first-person symbolic visions, angelic interpretation, prayer, heavenly conflict, kingdoms, persecution, and resurrection hope",
                "Daniel 2:4b-7:28: the principal Aramaic section spanning court tales and the first apocalypse",
            }.issubset(self.daniel.structure)
        )

    def test_daniel_removes_inherited_major_prophets_placeholder(self) -> None:
        inherited_values = {
            "Isaiah",
            "Jeremiah",
            "Ezekiel",
            "8th-6th centuries BCE with later shaping in some books",
            "Final forms often reflect exilic or post-exilic editing",
            "Judah and Israel in crisis, facing judgment, exile, and restoration hopes",
        }
        record_values = {
            *self.daniel.authorship_positions,
            *self.daniel.date_ranges,
            *self.daniel.key_people,
            *self.daniel.structure,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "court tale",
                "diaspora tale",
                "dream report and interpretation",
                "symbolic vision",
                "apocalypse",
                "communal prayer and confession",
                "angelic interpretation",
                "deliverance story",
                "resurrection oracle",
            }.issubset(self.daniel.genre)
        )
        self.assertIn(
            "Masoretic Daniel, Old Greek Daniel, and Theodotionic Daniel",
            self.daniel.primary_sources,
        )
        self.assertIn(
            "Qumran Daniel manuscripts and the Prayer of Nabonidus",
            self.daniel.primary_sources,
        )
        self.assertIn(
            "Prayer of Azariah and Song of the Three, Susanna, and Bel and the Dragon",
            self.daniel.primary_sources,
        )

    def test_daniel_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.daniel.content_status, "draft")
        self.assertEqual(self.daniel.review_status, "in_review")
        self.assertTrue(self.daniel.human_review_required)
        self.assertIsNone(self.daniel.last_reviewed)
        self.assertEqual(self.daniel.section_status["human_review"], "missing")
        self.assertEqual(
            self.daniel.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.daniel.sources}
        self.assertGreaterEqual(len(self.daniel.claims), 18)
        self.assertGreaterEqual(len(self.daniel.interpretive_notes), 26)
        for claim in self.daniel.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.daniel.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_daniel_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.daniel.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 14)
        self.assertTrue(self.daniel.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.daniel.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.daniel.retrieval_metadata["common_questions"])
        self.assertTrue(self.daniel.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "daniel-the-exile",
                "babylonian-exile",
                "exile-and-return-storyline",
                "kingdom-theme",
                "messiah-theme",
                "resurrection-theme",
                "temple-theme",
                "prayer-theme",
                "revelation",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.daniel.related_objects
                }
            )
        )

    def test_retrieval_answers_daniel_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Why were Daniel and his friends given Babylonian names?",
            "Did Daniel refuse all royal food or only request a test?",
            "What does Nebuchadnezzar's statue in Daniel 2 represent?",
            "Who was the fourth figure in the fiery furnace?",
            "Was Nebuchadnezzar mentally ill in Daniel 4?",
            "Who was Belshazzar and what was the writing on the wall?",
            "Who is Darius the Mede in Daniel 6?",
            "What does the lions' den teach about civil disobedience?",
            "Who are the four beasts and little horn in Daniel 7?",
            "Who is one like a son of man in Daniel 7?",
            "What does the ram and goat vision in Daniel 8 mean?",
            "How should Daniel's seventy weeks be interpreted?",
            "What is the abomination of desolation in Daniel?",
            "Who are Michael and the prince of Persia in Daniel 10?",
            "Does Daniel 12 teach bodily resurrection?",
            "Why is Daniel written in Hebrew and Aramaic?",
            "What are Old Greek and Theodotion Daniel?",
            "Are Susanna and Bel and the Dragon part of Daniel?",
            "Does Daniel predict modern nations or permit end-times date setting?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "daniel")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        son_of_man = [
            note
            for note in self.daniel.interpretive_notes
            if "humanlike figure in Daniel 7 is interpreted within the vision before later messianic and christological reception"
            in note.note
        ]
        self.assertTrue(son_of_man)
        self.assertEqual(
            son_of_man[0].dispute_status,
            "major_scholarly_disagreement",
        )

        seventy_weeks = [
            note
            for note in self.daniel.interpretive_notes
            if "seventy weeks do not license a certain modern date for the end"
            in note.note
        ]
        self.assertTrue(seventy_weeks)
        self.assertEqual(
            seventy_weeks[0].note_type,
            "interpretive-caution",
        )

        beasts = [
            note
            for note in self.daniel.interpretive_notes
            if "beasts and horns cannot responsibly be mapped with certainty onto current rulers, ethnic groups, or states"
            in note.note
        ]
        self.assertTrue(beasts)
        self.assertEqual(beasts[0].note_type, "interpretive-caution")

        mental_health = [
            note
            for note in self.daniel.interpretive_notes
            if "Daniel 4 must not be used to stigmatize mental illness or retrospectively diagnose a living person"
            in note.note
        ]
        self.assertTrue(mental_health)
        self.assertEqual(
            mental_health[0].note_type,
            "interpretive-caution",
        )

        antisupersessionism = [
            note
            for note in self.daniel.interpretive_notes
            if "Christian reception must not erase Daniel's Jewish settings, readers, or continuing Jewish interpretation"
            in note.note
        ]
        self.assertTrue(antisupersessionism)
        self.assertEqual(
            antisupersessionism[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_daniel_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-daniel.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("daniel").object
            self.assertEqual(sqlite_record.to_dict(), self.daniel.to_dict())


if __name__ == "__main__":
    unittest.main()
