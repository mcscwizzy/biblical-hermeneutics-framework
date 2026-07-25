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


class EzekielRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.ezekiel = cls.library.retrieve_by_id("ezekiel").object

    def test_ezekiel_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Ezekiel son of Buzi",
                "YHWH, whose speech Ezekiel reports",
                "the hand and Spirit of YHWH",
                "living creatures, cherubim, and wheels",
                "elders and exiles beside the Kebar canal",
                "Jerusalem's inhabitants, priests, rulers, and false prophets",
                "Oholah and Oholibah as personified Samaria and Jerusalem",
                "the shepherds, watchmen, prince, Gog, and temple guide",
                "the house of Israel, nations, and communal speakers",
                "prose narrators and reported interlocutors",
            }.issubset(self.ezekiel.key_people)
        )
        self.assertTrue(
            {
                "Ezekiel 1-3: dated throne vision, prophetic call, scroll eating, watchman commission, and constrained speech",
                "Ezekiel 4-24: enacted signs, allegories, lawsuits, temple-departure visions, responsibility teaching, and judgment on Jerusalem",
                "Ezekiel 25-32: oracles and laments concerning neighboring nations, Tyre, and Egypt",
                "Ezekiel 33-39: renewed watchman commission, fall report, shepherd critique, restoration, dry bones, reunification, and Gog",
                "Ezekiel 40-48: dated temple vision, guided tour, returning glory, cultic and land instructions, river, tribal allotments, and YHWH-shammah",
            }.issubset(self.ezekiel.structure)
        )

    def test_ezekiel_removes_inherited_major_prophets_placeholder(self) -> None:
        inherited_values = {
            "Isaiah",
            "Jeremiah",
            "Call and judgment",
            "Temple visions",
            "Restoration and new temple",
            "8th-6th centuries BCE with later shaping in some books",
            "Final forms often reflect exilic or post-exilic editing",
        }
        record_values = {
            *self.ezekiel.authorship_positions,
            *self.ezekiel.date_ranges,
            *self.ezekiel.key_people,
            *self.ezekiel.structure,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "throne vision and call report",
                "symbolic-action report",
                "allegory and riddle",
                "covenant lawsuit",
                "lament over a ruler or city",
                "proverb and disputation",
                "watchman commission",
                "oracle concerning a nation",
                "symbolic resurrection vision",
                "apocalyptic battle oracle",
                "temple vision and guided tour",
                "land-allotment instruction",
            }.issubset(self.ezekiel.genre)
        )
        self.assertIn(
            "Masoretic Ezekiel and Old Greek Iezekiel",
            self.ezekiel.primary_sources,
        )
        self.assertIn(
            "Papyrus 967, Qumran Ezekiel fragments, and the Masada Ezekiel scroll",
            self.ezekiel.primary_sources,
        )

    def test_ezekiel_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.ezekiel.content_status, "draft")
        self.assertEqual(self.ezekiel.review_status, "in_review")
        self.assertTrue(self.ezekiel.human_review_required)
        self.assertIsNone(self.ezekiel.last_reviewed)
        self.assertEqual(self.ezekiel.section_status["human_review"], "missing")
        self.assertEqual(
            self.ezekiel.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.ezekiel.sources}
        self.assertGreaterEqual(len(self.ezekiel.claims), 18)
        self.assertGreaterEqual(len(self.ezekiel.interpretive_notes), 28)
        for claim in self.ezekiel.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.ezekiel.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_ezekiel_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.ezekiel.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 14)
        self.assertTrue(self.ezekiel.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.ezekiel.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.ezekiel.retrieval_metadata["common_questions"])
        self.assertTrue(self.ezekiel.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "babylonian-exile",
                "temple-theme",
                "spirit-theme",
                "restoration-theme",
                "exile-theme",
                "davidic-covenant",
                "resurrection",
                "revelation",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.ezekiel.related_objects
                }
            )
        )

    def test_retrieval_answers_ezekiel_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Ezekiel son of Buzi and when was he called?",
            "What is the Kebar canal in Ezekiel?",
            "Why did Ezekiel eat a scroll and lie on his side?",
            "Was Ezekiel literally mute?",
            "What does son of man mean in Ezekiel?",
            "When does God's glory leave and return to the temple?",
            "Does Ezekiel 18 deny intergenerational consequences?",
            "Who are Oholah and Oholibah in Ezekiel 23?",
            "Is the king of Tyre in Ezekiel 28 Satan?",
            "What does the death of Ezekiel's wife mean?",
            "Who are the shepherds and Davidic shepherd in Ezekiel 34?",
            "What are the new heart and new spirit in Ezekiel 36?",
            "Do Ezekiel's dry bones teach bodily resurrection?",
            "Who are Gog and Magog in Ezekiel 38 and 39?",
            "Is Ezekiel's temple in chapters 40 through 48 literal?",
            "What is Papyrus 967 and why is Ezekiel ordered differently?",
            "How does Revelation reuse Ezekiel?",
            "Does Ezekiel justify modern land seizure or temple rebuilding?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "ezekiel")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        dry_bones = [
            note
            for note in self.ezekiel.interpretive_notes
            if "dry-bones vision explicitly interprets the bones as the whole house of Israel"
            in note.note
        ]
        self.assertTrue(dry_bones)
        self.assertEqual(
            dry_bones[0].dispute_status,
            "major_scholarly_disagreement",
        )

        gog = [
            note
            for note in self.ezekiel.interpretive_notes
            if "Gog cannot responsibly be identified with certainty as a modern nation"
            in note.note
        ]
        self.assertTrue(gog)
        self.assertEqual(gog[0].note_type, "interpretive-caution")

        temple = [
            note
            for note in self.ezekiel.interpretive_notes
            if "temple vision does not by itself authorize a modern construction project"
            in note.note
        ]
        self.assertTrue(temple)
        self.assertEqual(
            temple[0].dispute_status,
            "denominational_disagreement",
        )

        antisupersessionism = [
            note
            for note in self.ezekiel.interpretive_notes
            if "must not erase Jewish readers or transfer Israel's identity through supersessionism"
            in note.note
        ]
        self.assertTrue(antisupersessionism)
        self.assertEqual(
            antisupersessionism[0].note_type,
            "interpretive-caution",
        )

        gendered_violence = [
            note
            for note in self.ezekiel.interpretive_notes
            if "sexualized violence in Ezekiel 16 and 23 must be named as disturbing rhetoric"
            in note.note
        ]
        self.assertTrue(gendered_violence)
        self.assertEqual(
            gendered_violence[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_ezekiel_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-ezekiel.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("ezekiel").object
            self.assertEqual(sqlite_record.to_dict(), self.ezekiel.to_dict())


if __name__ == "__main__":
    unittest.main()
