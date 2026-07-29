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


class IsaiahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.isaiah = cls.library.retrieve_by_id("isaiah").object

    def test_isaiah_maps_major_voices_and_practical_reading_units(
        self,
    ) -> None:
        self.assertTrue(
            {
                "Isaiah son of Amoz",
                "the Holy One of Israel",
                "Shear-jashub",
                "Maher-shalal-hash-baz",
                "Ahaz king of Judah",
                "Hezekiah king of Judah",
                "Sennacherib king of Assyria",
                "Cyrus king of Persia",
                "the servant or servants",
                "Zion or Jerusalem personified",
            }.issubset(self.isaiah.key_people)
        )
        self.assertTrue(
            {
                "Isaiah 1-12: Judah and Jerusalem confronted, Isaiah commissioned, and Assyrian-era judgment and Davidic hope",
                "Isaiah 13-27: oracles concerning nations, imperial downfall, songs, and a world-encompassing judgment-and-restoration horizon",
                "Isaiah 28-35: woes, failed political trust, Zion under threat, and promised restoration",
                "Isaiah 36-39: Hezekiah narratives concerning Sennacherib, deliverance, illness, and the Babylonian embassy",
                "Isaiah 40-55: comfort, new exodus, the incomparable creator, Cyrus, servant texts, and return from Babylon",
                "Isaiah 56-66: contested postexilic community, justice and worship, Zion's restoration, inclusion, judgment, and new creation",
            }.issubset(self.isaiah.structure)
        )

    def test_isaiah_removes_inherited_major_prophets_placeholder(self) -> None:
        inherited_values = {
            "Jeremiah",
            "Ezekiel",
            "Judgment and call",
            "Comfort and restoration",
            "Servant and new creation visions",
            "8th-6th centuries BCE with later shaping in some books",
            "Final forms often reflect exilic or post-exilic editing",
        }
        record_values = {
            *self.isaiah.authorship_positions,
            *self.isaiah.date_ranges,
            *self.isaiah.key_people,
            *self.isaiah.structure,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "prophetic vision report",
                "sign report",
                "woe speech",
                "salvation oracle",
                "historical narrative",
                "trial speech",
                "servant poem",
                "new-creation poetry",
            }.issubset(self.isaiah.genre)
        )
        self.assertIn(
            "Great Isaiah Scroll (1QIsa-a), 1QIsa-b, and other Judean Desert Isaiah manuscripts",
            self.isaiah.primary_sources,
        )

    def test_isaiah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.isaiah.content_status, "draft")
        self.assertEqual(self.isaiah.review_status, "in_review")
        self.assertTrue(self.isaiah.human_review_required)
        self.assertIsNone(self.isaiah.last_reviewed)
        self.assertEqual(self.isaiah.section_status["human_review"], "missing")
        self.assertEqual(self.isaiah.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.isaiah.sources}
        self.assertGreaterEqual(len(self.isaiah.claims), 15)
        self.assertGreaterEqual(len(self.isaiah.interpretive_notes), 22)
        for claim in self.isaiah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.isaiah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_isaiah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.isaiah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 12)
        self.assertTrue(self.isaiah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.isaiah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.isaiah.retrieval_metadata["common_questions"])
        self.assertTrue(self.isaiah.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "exile-theme",
                "messiah-theme",
                "covenant-theme",
                "new-jerusalem",
                "resurrection-theme",
                "creation-theme",
                "kingdom-theme",
                "dead-sea-scrolls",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.isaiah.related_objects
                }
            )
        )

    def test_retrieval_answers_isaiah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Isaiah and are there multiple authors?",
            "What are First Second and Third Isaiah?",
            "Who is Immanuel in Isaiah 7?",
            "Who is the child called Wonderful Counselor in Isaiah 9?",
            "Is the morning star in Isaiah 14 Satan or a Babylonian king?",
            "Who is the suffering servant in Isaiah 52 and 53?",
            "Why does Isaiah call Cyrus God's anointed?",
            "Does Isaiah 6 hardening justify antisemitism?",
            "Does by his wounds we are healed excuse abuse or victim blaming?",
            "What does Isaiah teach about fasting and justice?",
            "What are 1QIsa-a and 1QIsa-b?",
            "How does the Greek book Esaias differ from Masoretic Isaiah?",
            "Does Isaiah predict Jesus or use typology and quotation?",
            "What are the new heavens and new earth in Isaiah 65 and 66?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "isaiah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        immanuel = [
            note
            for note in self.isaiah.interpretive_notes
            if "Immanuel's immediate historical identity is disputed" in note.note
        ]
        self.assertTrue(immanuel)
        self.assertEqual(
            immanuel[0].dispute_status,
            "major_scholarly_disagreement",
        )

        morning_star = [
            note
            for note in self.isaiah.interpretive_notes
            if "morning star, son of dawn" in note.note
        ]
        self.assertTrue(morning_star)
        self.assertEqual(
            morning_star[0].dispute_status,
            "denominational_disagreement",
        )

        hardening = [
            note
            for note in self.isaiah.interpretive_notes
            if "must never authorize antisemitism" in note.note
        ]
        self.assertTrue(hardening)
        self.assertEqual(hardening[0].note_type, "interpretive-caution")

        servant_abuse = [
            note
            for note in self.isaiah.interpretive_notes
            if "must not be used to command victims to remain in abuse"
            in note.note
        ]
        self.assertTrue(servant_abuse)
        self.assertEqual(
            servant_abuse[0].note_type,
            "interpretive-caution",
        )

        disability = [
            note
            for note in self.isaiah.interpretive_notes
            if "must not be mapped onto disabled people" in note.note
        ]
        self.assertTrue(disability)
        self.assertEqual(disability[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_isaiah_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-isaiah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("isaiah").object
            self.assertEqual(sqlite_record.to_dict(), self.isaiah.to_dict())


if __name__ == "__main__":
    unittest.main()
