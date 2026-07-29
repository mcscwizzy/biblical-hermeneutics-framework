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


class JonahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.jonah = cls.library.retrieve_by_id("jonah").object

    def test_jonah_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the narrator",
                "YHWH in direct speech and as sender of storm, fish, plant, worm, and wind",
                "Jonah son of Amittai",
                "the shipmaster, sailors, lot-casters, rowers, and vow-makers",
                "the appointed great fish",
                "the people of Nineveh, their king, and nobles",
                "humans and animals participating in the fast and sackcloth",
                "the appointed plant, worm, and scorching east wind",
            }.issubset(self.jonah.key_people)
        )
        self.assertTrue(
            {
                "Jonah 1:1-3: first commission and Jonah's flight toward Tarshish from Joppa",
                "Jonah 1:4-16: YHWH's storm, the sailors' actions, lot, confession, casting overboard, calm, sacrifice, and vows",
                "Jonah 1:17 common English / 2:1 MT through 2:10 common English / 2:11 MT: appointed fish, Jonah's prayer, and deliverance",
                "Jonah 3:1-10: renewed commission, judgment announcement, Nineveh's response, royal decree, and divine relenting",
                "Jonah 4:1-11: Jonah's anger, death wishes, plant, worm, wind, disputed pity, and YHWH's unresolved question",
            }.issubset(self.jonah.structure)
        )

    def test_jonah_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Hosea",
            "Amos",
        }
        record_values = {
            *self.jonah.authorship_positions,
            *self.jonah.date_ranges,
            self.jonah.historical_setting,
            *self.jonah.key_people,
            *self.jonah.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "prophetic call narrative",
                "travel and sea narrative",
                "storm and lot-casting scene",
                "confession, sacrifice, and vow",
                "thanksgiving psalm or prayer",
                "rescue tale",
                "city mission and judgment announcement",
                "communal fast and royal decree",
                "repentance and divine-relenting narrative",
                "prophetic disputation",
                "satire, irony, hyperbole, and fable-like episode",
                "open divine question",
            }.issubset(self.jonah.genre)
        )
        self.assertIn(
            "Masoretic Jonah within the Book of the Twelve",
            self.jonah.primary_sources,
        )
        self.assertIn(
            "Old Greek Ionas and other ancient versions",
            self.jonah.primary_sources,
        )
        self.assertIn(
            "Qumran manuscripts of the Twelve preserving portions of Jonah",
            self.jonah.primary_sources,
        )

    def test_jonah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.jonah.content_status, "draft")
        self.assertEqual(self.jonah.review_status, "in_review")
        self.assertTrue(self.jonah.human_review_required)
        self.assertIsNone(self.jonah.last_reviewed)
        self.assertEqual(self.jonah.section_status["human_review"], "missing")
        self.assertEqual(
            self.jonah.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.jonah.sources}
        self.assertGreaterEqual(len(self.jonah.claims), 22)
        self.assertGreaterEqual(len(self.jonah.interpretive_notes), 36)
        for claim in self.jonah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.jonah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_jonah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.jonah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 16)
        self.assertTrue(self.jonah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.jonah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.jonah.retrieval_metadata["common_questions"])
        self.assertTrue(self.jonah.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "nineveh",
                "repentance",
                "divine-mercy",
                "prophets",
                "assyria",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.jonah.related_objects
                }
            )
        )

    def test_retrieval_answers_jonah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who is Jonah son of Amittai in Jonah and 2 Kings 14:25?",
            "When was the book of Jonah written?",
            "Is Jonah history, fiction, satire, parody, or a didactic tale?",
            "Where were Joppa and Tarshish in Jonah?",
            "Why does Jonah flee from YHWH?",
            "Who are the sailors and shipmaster in Jonah 1?",
            "What does the lot reveal in Jonah 1?",
            "Does Jonah want the sailors to kill him?",
            "What species was the great fish in Jonah?",
            "Did Jonah die inside the fish and does Sheol prove it?",
            "Is Jonah 2 an inserted thanksgiving psalm or integrated prayer?",
            "Why do Hebrew and English Bibles number Jonah 1:17 and chapter 2 differently?",
            "What do three days and three nights mean in Jonah?",
            "Was Nineveh really a three-day journey across?",
            "Who was the king of Nineveh in Jonah 3?",
            "Did animals wear sackcloth and fast in Jonah?",
            "Does Nineveh's repentance prove coercive conversion is acceptable?",
            "Why does God relent from disaster in Jonah 3?",
            "Why is Jonah angry and asking to die in Jonah 4?",
            "What was the qiqayon plant in Jonah 4?",
            "What does not knowing right from left mean in Jonah 4:11?",
            "Why does Jonah end with an unanswered divine question?",
            "What are Old Greek Ionas, 4Q76, and 4Q82?",
            "How is Jonah read on Yom Kippur?",
            "What is the sign of Jonah in Matthew 12 and Luke 11?",
            "Does Jonah portray Jews as uniquely xenophobic or inferior to Gentiles?",
            "Does Jonah excuse Assyrian empire or authorize ethnic hatred?",
            "Can Jonah be used to shame suicidal people or blame disaster victims?",
            "How should Jonah be read ecologically with animals, plant, worm, wind, fish, and city?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "jonah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        genre = [
            note
            for note in self.jonah.interpretive_notes
            if "Labels such as historical narrative, novella, didactic tale, satire, parody, and fiction describe overlapping features but remain disputed"
            in note.note
        ]
        self.assertTrue(genre)
        self.assertEqual(
            genre[0].dispute_status,
            "major_scholarly_disagreement",
        )

        fish = [
            note
            for note in self.jonah.interpretive_notes
            if "The text identifies an appointed great fish but neither names a species nor says that Jonah dies inside it"
            in note.note
        ]
        self.assertTrue(fish)
        self.assertEqual(fish[0].note_type, "interpretive-caution")

        mental_health = [
            note
            for note in self.jonah.interpretive_notes
            if "Jonah's repeated requests for death must not be used to shame suicidal people or replace compassionate mental-health care"
            in note.note
        ]
        self.assertTrue(mental_health)
        self.assertEqual(
            mental_health[0].note_type,
            "interpretive-caution",
        )

        antisemitism = [
            note
            for note in self.jonah.interpretive_notes
            if "Jonah must not be turned into an antisemitic caricature of Jews as uniquely disobedient, vengeful, or hostile to outsiders"
            in note.note
        ]
        self.assertTrue(antisemitism)
        self.assertEqual(
            antisemitism[0].note_type,
            "interpretive-caution",
        )

        empire = [
            note
            for note in self.jonah.interpretive_notes
            if "Divine compassion for Nineveh neither excuses Assyrian imperial violence nor licenses hatred of ancient or modern peoples"
            in note.note
        ]
        self.assertTrue(empire)
        self.assertEqual(empire[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_jonah_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-jonah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("jonah").object
            self.assertEqual(sqlite_record.to_dict(), self.jonah.to_dict())


if __name__ == "__main__":
    unittest.main()
