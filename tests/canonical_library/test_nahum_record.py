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


class NahumRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.nahum = cls.library.retrieve_by_id("nahum").object

    def test_nahum_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Nahum the Elkoshite and the book's framing voice",
                "YHWH in direct speech, reported action, and third-person proclamation",
                "the implied prophet or poet and the bringer of good news",
                "Judah, Jacob, Nineveh as city and feminized personification, peoples, and nations",
                "the wicked counselor or Belial figure and the Assyrian king",
                "the scatterer, attackers, soldiers, guards, captives, and children",
                "princes, commanders, merchants, scribes, shepherds, nobles, and the king of Assyria",
                "the lion, lioness, cubs, locust swarms, and later interpreters",
            }.issubset(self.nahum.key_people)
        )
        self.assertTrue(
            {
                "Nahum 1:1: superscription naming an oracle concerning Nineveh and a vision-book of Nahum the Elkoshite",
                "Nahum 1:2-8: divine-warrior hymn or theophany, disputed partial acrostic, cosmic storm, judgment, and refuge",
                "Nahum 1:9-15 common English / 1:9-2:1 MT: alternating judgment and salvation speech, broken yoke, and messenger of peace",
                "Nahum 2:1-13 common English / 2:2-14 MT: the scatterer, siege and battle poem, plunder, lion fable, and divine oracle",
                "Nahum 3:1-7: woe over the bloody city, violence, exploitation, city personification, exposure, and taunt",
                "Nahum 3:8-13: rhetorical comparison with Thebes or No-amon, captivity, child killing, and failed defenses",
                "Nahum 3:14-19: siege imperatives, fire and sword, locust similes, failed leaders, irreparable wound, and nations' applause",
            }.issubset(self.nahum.structure)
        )

    def test_nahum_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Hosea",
            "Amos",
            "Jonah",
        }
        record_values = {
            *self.nahum.authorship_positions,
            *self.nahum.date_ranges,
            self.nahum.historical_setting,
            *self.nahum.key_people,
            *self.nahum.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "superscription and vision-book title",
                "burden or oracle",
                "divine-warrior hymn and theophany",
                "proposed partial alphabetic acrostic",
                "judgment and salvation oracle",
                "messenger announcement and good-news proclamation",
                "siege and battle poem",
                "taunt and lion fable",
                "woe oracle and city lament",
                "feminized city personification and humiliation imagery",
                "rhetorical question and historical comparison",
                "funeral lament, dirge, and open international response",
            }.issubset(self.nahum.genre)
        )
        self.assertIn(
            "Masoretic Nahum within the Book of the Twelve",
            self.nahum.primary_sources,
        )
        self.assertIn(
            "Old Greek Naoum and other ancient versions",
            self.nahum.primary_sources,
        )
        self.assertIn(
            "Judean Desert manuscripts of the Twelve and Pesher Nahum",
            self.nahum.primary_sources,
        )

    def test_nahum_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.nahum.content_status, "draft")
        self.assertEqual(self.nahum.review_status, "in_review")
        self.assertTrue(self.nahum.human_review_required)
        self.assertIsNone(self.nahum.last_reviewed)
        self.assertEqual(self.nahum.section_status["human_review"], "missing")
        self.assertEqual(
            self.nahum.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.nahum.sources}
        self.assertGreaterEqual(len(self.nahum.claims), 24)
        self.assertGreaterEqual(len(self.nahum.interpretive_notes), 40)
        for claim in self.nahum.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.nahum.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_nahum_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.nahum.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 18)
        self.assertTrue(self.nahum.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.nahum.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.nahum.retrieval_metadata["common_questions"])
        self.assertTrue(self.nahum.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "nineveh",
                "assyria",
                "judgment",
                "divine-justice",
                "exile-theme",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.nahum.related_objects
                }
            )
        )

    def test_retrieval_answers_nahum_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Nahum the Elkoshite and where was Elkosh?",
            "When was Nahum written between the fall of Thebes and Nineveh?",
            "Is Nahum a unified seventh-century prophecy or a later edited composition?",
            "What does the oracle or burden title in Nahum 1:1 mean?",
            "Is Nahum 1:2-8 an alphabetic acrostic hymn?",
            "How does Exodus 34:6-7 shape Nahum's jealous avenging and slow-to-anger language?",
            "Who is the wicked counselor or Belial in Nahum 1?",
            "Why do Hebrew and English Bibles number Nahum 1:15 and chapter 2 differently?",
            "Who is the bringer of good news in Nahum 1:15 and how does this relate to Isaiah 52:7?",
            "Who is the scatterer in Nahum 2:1?",
            "What do red shields flashing chariots and spears mean in Nahum 2?",
            "Do the river gates and collapsing palace describe a flood at Nineveh?",
            "What does the draining pool image in Nahum 2 mean?",
            "What is the lion den fable in Nahum 2:11-13?",
            "Why is Nineveh called the bloody city in Nahum 3?",
            "What do prostitution sorcery exposure and shame imagery mean in Nahum 3:4-7?",
            "Does Nahum demean women or sex workers through city personification?",
            "What happened to Thebes or No-amon in 663 BCE?",
            "Who were Put and the Libyans among Thebes' allies?",
            "Why does Nahum describe children dashed at street corners?",
            "What do locust merchants scribes guards and commanders symbolize?",
            "Who are Assyria's shepherds nobles and king in Nahum 3:18?",
            "What is Nineveh's irreparable wound and why do nations clap?",
            "What does the Babylonian Chronicle say about Nineveh's fall in 612 BCE?",
            "What do Assyrian inscriptions reliefs and archaeology contribute to Nahum?",
            "What are Old Greek Naoum Judean Desert manuscripts and 4Q169 Pesher Nahum?",
            "How do Jonah and Nahum present different memories of Nineveh?",
            "Does Romans 10:15 quote Nahum 1:15 or Isaiah 52:7?",
            "How does Revelation 17-18 compare with Nahum without predicting modern nations?",
            "Does Nahum authorize antisemitism anti-Iraqi racism revenge war propaganda genocide or collective punishment?",
            "How should Nahum's divine violence sexualized humiliation child killing siege and trauma imagery be read?",
            "Can Nineveh or Assyria be mapped onto a modern city religion ethnicity or political party?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "nahum")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        acrostic = [
            note
            for note in self.nahum.interpretive_notes
            if "Nahum 1:2-8 shows a disputed and incomplete alphabetic pattern; proposed reconstructions differ over its extent, sequence, and whether a damaged acrostic was intended"
            in note.note
        ]
        self.assertTrue(acrostic)
        self.assertEqual(
            acrostic[0].dispute_status,
            "major_scholarly_disagreement",
        )

        flood = [
            note
            for note in self.nahum.interpretive_notes
            if "The river gates, collapsing palace, and pool imagery in Nahum 2 do not by themselves prove that a literal flood breached Nineveh's defenses"
            in note.note
        ]
        self.assertTrue(flood)
        self.assertEqual(flood[0].note_type, "interpretive-caution")

        gender = [
            note
            for note in self.nahum.interpretive_notes
            if "Nineveh's feminized exposure and prostitution imagery must be named as gendered humiliation rhetoric and must not be used to normalize sexual violence, misogyny, or stigma against sex workers"
            in note.note
        ]
        self.assertTrue(gender)
        self.assertEqual(gender[0].note_type, "interpretive-caution")

        ethnicity = [
            note
            for note in self.nahum.interpretive_notes
            if "Ancient Assyria and Nineveh must not be treated as ethnic proxies for modern Assyrians, Iraqis, Middle Eastern peoples, Muslims, or any contemporary population"
            in note.note
        ]
        self.assertTrue(ethnicity)
        self.assertEqual(ethnicity[0].note_type, "interpretive-caution")

        violence = [
            note
            for note in self.nahum.interpretive_notes
            if "Nahum's announcement of imperial collapse does not authorize revenge, vigilantism, torture, siege warfare, genocide, ethnic cleansing, forced displacement, or collective punishment"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_nahum_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-nahum.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("nahum").object
            self.assertEqual(sqlite_record.to_dict(), self.nahum.to_dict())


if __name__ == "__main__":
    unittest.main()
