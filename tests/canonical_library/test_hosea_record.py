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


class HoseaRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.hosea = cls.library.retrieve_by_id("hosea").object

    def test_hosea_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Hosea son of Beeri",
                "Gomer daughter of Diblaim",
                "Jezreel, Lo-ruhamah, and Lo-ammi",
                "YHWH in reported speech and direct address",
                "personified Israel or Ephraim and Judah",
                "priests, kings, prophets, rulers, nations, and ancestors",
                "third-person family narrator, Hosea's first-person report, and communal voices",
            }.issubset(self.hosea.key_people)
        )
        self.assertTrue(
            {
                "Hosea 1-3: superscription, family narratives, symbolic names, disputed relationship imagery, judgment, and restoration",
                "Hosea 4-11: accusations, lawsuits, political and cultic critique, historical memory, judgment, and divine compassion",
                "Hosea 12-14: Jacob traditions, prophetic retrospect, death and empire imagery, call to return, healing, and wisdom conclusion",
                "Hosea 14:2-9: communal return speech, divine healing and flourishing, and an editorial wisdom epilogue",
            }.issubset(self.hosea.structure)
        )

    def test_hosea_removes_inherited_minor_prophets_placeholder(self) -> None:
        inherited_values = {
            "8th-5th centuries BCE, depending on the prophet",
            "Final forms often reflect later collection and editing",
            "Assyrian, Babylonian, and post-exilic settings across the prophetic corpus",
            "Amos",
            "Jonah",
            "Nineveh",
            "day of the LORD",
        }
        record_values = {
            *self.hosea.authorship_positions,
            *self.hosea.date_ranges,
            self.hosea.historical_setting,
            *self.hosea.key_people,
            *self.hosea.key_places,
            *self.hosea.major_themes,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "prophetic superscription",
                "family narrative",
                "symbolic naming and sign report",
                "covenant lawsuit and accusation",
                "judgment oracle",
                "salvation oracle",
                "metaphor cluster",
                "historical retrospect",
                "call-to-return liturgy",
                "wisdom conclusion",
            }.issubset(self.hosea.genre)
        )
        self.assertIn(
            "Masoretic Hosea and the book within the Twelve",
            self.hosea.primary_sources,
        )
        self.assertIn(
            "Old Greek Osee and other ancient versions",
            self.hosea.primary_sources,
        )
        self.assertIn(
            "Qumran manuscripts of the Twelve preserving portions of Hosea",
            self.hosea.primary_sources,
        )

    def test_hosea_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.hosea.content_status, "draft")
        self.assertEqual(self.hosea.review_status, "in_review")
        self.assertTrue(self.hosea.human_review_required)
        self.assertIsNone(self.hosea.last_reviewed)
        self.assertEqual(self.hosea.section_status["human_review"], "missing")
        self.assertEqual(
            self.hosea.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.hosea.sources}
        self.assertGreaterEqual(len(self.hosea.claims), 18)
        self.assertGreaterEqual(len(self.hosea.interpretive_notes), 28)
        for claim in self.hosea.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.hosea.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_hosea_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.hosea.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 14)
        self.assertTrue(self.hosea.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.hosea.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.hosea.retrieval_metadata["common_questions"])
        self.assertTrue(self.hosea.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "covenant-theme",
                "mercy-theme",
                "repentance",
                "assyria",
                "exile-theme",
                "hesed",
                "fall-of-samaria",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.hosea.related_objects
                }
            )
        )

    def test_retrieval_answers_hosea_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who were Hosea son of Beeri and Gomer daughter of Diblaim?",
            "What does wife of whoredom mean in Hosea 1?",
            "Were Hosea and Gomer's children historical or symbolic?",
            "What do Jezreel Lo-ruhamah and Lo-ammi mean?",
            "Is the woman in Hosea 3 Gomer?",
            "Does Hosea command people to marry an unfaithful spouse?",
            "Does Hosea justify sexual shaming or intimate partner violence?",
            "What is the covenant lawsuit in Hosea 4?",
            "What does Hosea mean by knowledge of God and steadfast love?",
            "What does I desire mercy not sacrifice mean in Hosea 6:6?",
            "Why does Hosea condemn Israel's kings and foreign alliances?",
            "How does Hosea portray Baal fertility worship?",
            "What historical crisis and Assyrian empire stand behind Hosea?",
            "What happened at Jezreel in Hosea 1?",
            "Why does Hosea retell the exodus and Jacob traditions?",
            "How can God say out of Egypt I called my son in Hosea 11:1 and Matthew 2?",
            "What does Hosea 11 teach about divine compassion?",
            "Does death where are your plagues in Hosea 13:14 promise resurrection?",
            "How does Paul use Hosea in Romans 9?",
            "How does 1 Peter reuse Hosea's not my people and no mercy?",
            "What is the textual problem in Hosea 14?",
            "How does Hosea end with healing and a wisdom saying?",
            "What are the Old Greek Osee and Qumran Hosea manuscripts?",
            "Does Christian use of Hosea replace Israel or erase Jewish readings?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "hosea")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        marriage = [
            note
            for note in self.hosea.interpretive_notes
            if "The historicity and precise social scenario of Hosea's marriage cannot be established with certainty"
            in note.note
        ]
        self.assertTrue(marriage)
        self.assertEqual(
            marriage[0].dispute_status,
            "major_scholarly_disagreement",
        )

        violence = [
            note
            for note in self.hosea.interpretive_notes
            if "Hosea's marriage and stripping imagery must not be used to authorize intimate-partner violence"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

        matthew = [
            note
            for note in self.hosea.interpretive_notes
            if "Matthew's use of Hosea 11:1 is a later figural rereading of Israel's exodus"
            in note.note
        ]
        self.assertTrue(matthew)
        self.assertEqual(
            matthew[0].dispute_status,
            "minor_scholarly_disagreement",
        )

        resurrection = [
            note
            for note in self.hosea.interpretive_notes
            if "Hosea 13:14 is textually and rhetorically disputed and cannot by itself bear a certain doctrine of individual resurrection"
            in note.note
        ]
        self.assertTrue(resurrection)
        self.assertEqual(
            resurrection[0].dispute_status,
            "textual_variant",
        )

        antisupersessionism = [
            note
            for note in self.hosea.interpretive_notes
            if "Christian reuse of Hosea must not erase Israel, Jewish readers, or continuing Jewish interpretation"
            in note.note
        ]
        self.assertTrue(antisupersessionism)
        self.assertEqual(
            antisupersessionism[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_hosea_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-hosea.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("hosea").object
            self.assertEqual(sqlite_record.to_dict(), self.hosea.to_dict())


if __name__ == "__main__":
    unittest.main()
