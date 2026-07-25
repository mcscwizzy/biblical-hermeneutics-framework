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


class PsalmsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.psalms = cls.library.retrieve_by_id("psalms").object

    def test_psalms_tracks_collections_people_places_and_events(self) -> None:
        self.assertTrue(
            {
                "YHWH",
                "David",
                "Asaph",
                "the sons of Korah",
                "Solomon",
                "Moses",
                "Heman the Ezrahite",
                "Ethan the Ezrahite",
            }.issubset(self.psalms.key_people)
        )
        self.assertTrue(
            {
                "Zion",
                "Jerusalem",
                "the sanctuary or temple",
                "Babylon",
                "Sheol and the pit",
            }.issubset(self.psalms.key_places)
        )
        self.assertTrue(
            {
                "Torah meditation and the nations' revolt frame the Psalter",
                "temple destruction, exile, and Babylonian captivity are lamented",
                "pilgrims ascend to worship in the Songs of Ascents",
                "the Psalter closes by summoning all creation to praise YHWH",
            }.issubset(self.psalms.key_events)
        )

    def test_psalms_removes_inherited_wisdom_placeholder(self) -> None:
        inherited_values = {
            "Traditional attribution to Solomon or wise circles",
            "Many scholars see collected wisdom and later shaping",
            "Monarchic wisdom traditions",
            "Israel's covenant community learning wise living under God",
            "Royal, instructional, and reflective wisdom settings within Israel",
            "Job",
            "court",
        }
        record_values = {
            *self.psalms.authorship_positions,
            *self.psalms.date_ranges,
            self.psalms.original_audience,
            self.psalms.historical_setting,
            *self.psalms.key_people,
            *self.psalms.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertIn("individual lament", self.psalms.genre)
        self.assertIn("communal lament", self.psalms.genre)
        self.assertIn("imprecatory prayer", self.psalms.genre)
        self.assertIn("Dead Sea Psalms manuscripts, especially 11QPs-a", self.psalms.primary_sources)

    def test_psalms_has_five_books_and_collection_markers(self) -> None:
        structure = set(self.psalms.structure)
        self.assertTrue(
            {
                "Psalms 1-2: paired wisdom and royal gateway",
                "Book I, Psalms 1-41: predominantly David-linked prayers",
                "Book II, Psalms 42-72: Korahite, David-linked, and Solomonic material",
                "Book III, Psalms 73-89: predominantly Asaphite and Korahite material ending in royal-covenant crisis",
                "Book IV, Psalms 90-106: Moses heading, YHWH-kingship sequence, creation and historical praise",
                "Book V, Psalms 107-150: thanksgiving, Egyptian Hallel, Psalm 119, Songs of Ascents, Davidic group, and Hallelujah conclusion",
                "Doxological seams at Psalms 41:13; 72:18-19; 89:52; 106:48",
            }.issubset(structure)
        )
        claims = {claim.id: claim for claim in self.psalms.claims}
        self.assertIn("psalms-five-book-anthology", claims)
        self.assertIn("psalms-gateway-torah-king", claims)
        self.assertIn("psalms-book-three-crisis", claims)

    def test_psalms_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.psalms.content_status, "draft")
        self.assertEqual(self.psalms.review_status, "in_review")
        self.assertTrue(self.psalms.human_review_required)
        self.assertIsNone(self.psalms.last_reviewed)
        self.assertEqual(self.psalms.section_status["human_review"], "missing")
        self.assertEqual(self.psalms.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.psalms.sources}
        self.assertGreaterEqual(len(self.psalms.claims), 9)
        self.assertGreaterEqual(len(self.psalms.interpretive_notes), 15)
        for claim in self.psalms.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.psalms.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_psalms_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.psalms.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 8)
        self.assertTrue(self.psalms.hermeneutical_lens["book_context"])
        self.assertTrue(self.psalms.hermeneutical_lens["common_misinterpretations"])
        self.assertTrue(self.psalms.retrieval_metadata["common_questions"])
        self.assertTrue(self.psalms.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "david",
                "worship-theme",
                "prayer-theme",
                "wisdom-theme",
                "temple-theme",
                "covenant-theme",
                "messiah-theme",
                "creation-theme",
                "zion",
                "job",
                "lamentations",
            }.issubset({relationship.id for relationship in self.psalms.related_objects})
        )

    def test_retrieval_answers_psalms_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Did David write all 150 Psalms?",
            "Why is the Psalter divided into five books?",
            "What do Asaph and the sons of Korah mean in Psalm headings?",
            "What does Selah mean?",
            "How should Christians pray imprecatory psalms?",
            "Does Psalm 137 authorize violence against children?",
            "Psalter Septuagint Latin numbering Psalms 9 10 114 115 151",
            "What is the Great Psalms Scroll 11Q5?",
            "Do protection psalms guarantee that believers will never suffer?",
            "Psalter New Testament use Psalm 110 royal priestly enthronement",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "psalms")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        superscription_notes = [
            note
            for note in self.psalms.interpretive_notes
            if "do not supply one uniform" in note.note
        ]
        self.assertTrue(superscription_notes)
        self.assertEqual(
            superscription_notes[0].dispute_status,
            "major_scholarly_disagreement",
        )

        qumran_notes = [
            note
            for note in self.psalms.interpretive_notes
            if "different order together with additional compositions" in note.note
        ]
        self.assertTrue(qumran_notes)
        self.assertEqual(qumran_notes[0].note_type, "second-temple-context")

        numbering_notes = [
            note
            for note in self.psalms.interpretive_notes
            if "combines Psalms 9-10 and 114-115" in note.note
        ]
        self.assertTrue(numbering_notes)
        self.assertEqual(numbering_notes[0].dispute_status, "textual_variant")

        violence_notes = [
            note
            for note in self.psalms.interpretive_notes
            if "private, ethnic, or political violence" in note.note
        ]
        self.assertTrue(violence_notes)
        self.assertEqual(violence_notes[0].note_type, "interpretive-caution")

        promise_notes = [
            note
            for note in self.psalms.interpretive_notes
            if "not universal guarantees of safety" in note.note
        ]
        self.assertTrue(promise_notes)
        self.assertEqual(promise_notes[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_psalms_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-psalms.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("psalms").object
            self.assertEqual(sqlite_record.to_dict(), self.psalms.to_dict())


if __name__ == "__main__":
    unittest.main()
