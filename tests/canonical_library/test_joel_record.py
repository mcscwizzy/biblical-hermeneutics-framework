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


class JoelRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.joel = cls.library.retrieve_by_id("joel").object

    def test_joel_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Joel son of Pethuel",
                "YHWH in reported speech and direct address",
                "the prophetic first-person voice",
                "elders, priests, ministers, farmers, vine dressers, and drunkards",
                "inhabitants, children, bridegroom, bride, and communal lamenters",
                "nations, warriors, captives, and enslaved people",
                "sons, daughters, elders, youths, male slaves, and female slaves as recipients of the spirit",
            }.issubset(self.joel.key_people)
        )
        self.assertTrue(
            {
                "Joel 1:1-20: superscription, locust and drought lament, testimony across generations, and summons to priests and land workers",
                "Joel 2:1-17: alarm, day-of-YHWH army imagery, call to return, fast, assembly, and priestly plea",
                "Joel 2:18-27: YHWH's response, removal of the northern threat, agricultural restoration, and renewed presence",
                "Joel 3:1-5 MT / 2:28-32 common English: spirit, prophecy, dreams, visions, cosmic signs, and deliverance",
                "Joel 4:1-21 MT / 3:1-21 common English: nations judgment, valley imagery, refuge in Zion, and final restoration",
            }.issubset(self.joel.structure)
        )

    def test_joel_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Hosea",
            "Amos",
            "Jonah",
            "Nineveh",
        }
        record_values = {
            *self.joel.authorship_positions,
            *self.joel.date_ranges,
            self.joel.historical_setting,
            *self.joel.key_people,
            *self.joel.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "prophetic superscription",
                "communal lament",
                "summons and alarm",
                "fast liturgy",
                "priestly prayer",
                "day-of-YHWH oracle",
                "theophanic army imagery",
                "divine-response speech",
                "salvation oracle",
                "spirit oracle",
                "nations-judgment oracle",
                "restoration imagery",
            }.issubset(self.joel.genre)
        )
        self.assertIn(
            "Masoretic Joel within the Book of the Twelve",
            self.joel.primary_sources,
        )
        self.assertIn(
            "Old Greek Ioel and other ancient versions",
            self.joel.primary_sources,
        )
        self.assertIn(
            "Qumran manuscripts of the Twelve preserving portions of Joel",
            self.joel.primary_sources,
        )

    def test_joel_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.joel.content_status, "draft")
        self.assertEqual(self.joel.review_status, "in_review")
        self.assertTrue(self.joel.human_review_required)
        self.assertIsNone(self.joel.last_reviewed)
        self.assertEqual(self.joel.section_status["human_review"], "missing")
        self.assertEqual(
            self.joel.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.joel.sources}
        self.assertGreaterEqual(len(self.joel.claims), 18)
        self.assertGreaterEqual(len(self.joel.interpretive_notes), 28)
        for claim in self.joel.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.joel.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_joel_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.joel.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 14)
        self.assertTrue(self.joel.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.joel.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.joel.retrieval_metadata["common_questions"])
        self.assertTrue(self.joel.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "day-of-the-lord-prophecy",
                "repentance",
                "restoration-theme",
                "spirit-theme",
                "judgment",
                "zion",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.joel.related_objects
                }
            )
        )

    def test_retrieval_answers_joel_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Joel son of Pethuel?",
            "When was the book of Joel written?",
            "Was Joel written in the Persian period or before the exile?",
            "What caused the locust plague and drought in Joel 1?",
            "Are Joel's four locust names species, life stages, or poetic synonyms?",
            "Is the army in Joel 2 literal, metaphorical, locusts, or human invaders?",
            "What does blow the trumpet in Zion mean in Joel?",
            "Does Joel say disasters prove that victims committed particular sins?",
            "What does rend your hearts and not your garments mean?",
            "Does Joel 2 require coercive public fasting?",
            "Why do priests weep between the vestibule and altar?",
            "What does gracious and merciful slow to anger mean in Joel 2:13?",
            "What is the day of YHWH in Joel?",
            "What are the cosmic signs of sun, moon, blood, fire, and smoke?",
            "What does Joel mean by pouring out the spirit on all flesh?",
            "Are women, elders, youths, and enslaved people included in Joel's spirit promise?",
            "How does Peter use Joel 3 MT and Old Greek Ioel at Pentecost?",
            "How does Romans 10 use everyone who calls on the Lord?",
            "How does Revelation reuse Joel's harvest and winepress imagery?",
            "Why do Hebrew Bibles have Joel 3 and 4 where English Bibles have Joel 2 and 3?",
            "What is the valley of Jehoshaphat or valley of decision?",
            "Does Joel authorize vengeance, nationalism, genocide, or violence against nations?",
            "What are Old Greek Ioel and the Qumran Joel manuscripts?",
            "Does Christian interpretation of Joel erase Jewish readings or replace Israel?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "joel")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        army = [
            note
            for note in self.joel.interpretive_notes
            if "Whether Joel 2's advancing force continues the locust imagery, depicts a human army, or fuses both within day-of-YHWH theophany remains disputed"
            in note.note
        ]
        self.assertTrue(army)
        self.assertEqual(
            army[0].dispute_status,
            "major_scholarly_disagreement",
        )

        disaster = [
            note
            for note in self.joel.interpretive_notes
            if "Joel must not be used to claim that a disaster identifies particular victims as uniquely guilty"
            in note.note
        ]
        self.assertTrue(disaster)
        self.assertEqual(disaster[0].note_type, "interpretive-caution")

        spirit = [
            note
            for note in self.joel.interpretive_notes
            if "The phrase 'all flesh' is specified through socially expansive groups"
            in note.note
        ]
        self.assertTrue(spirit)
        self.assertEqual(
            spirit[0].dispute_status,
            "minor_scholarly_disagreement",
        )

        violence = [
            note
            for note in self.joel.interpretive_notes
            if "Joel's nations-judgment and martial imagery does not authorize readers to enact vengeance"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

        antisupersessionism = [
            note
            for note in self.joel.interpretive_notes
            if "Christian reuse of Joel must not erase Israel, Jewish readers, or continuing Jewish interpretation"
            in note.note
        ]
        self.assertTrue(antisupersessionism)
        self.assertEqual(
            antisupersessionism[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_joel_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-joel.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("joel").object
            self.assertEqual(sqlite_record.to_dict(), self.joel.to_dict())


if __name__ == "__main__":
    unittest.main()
