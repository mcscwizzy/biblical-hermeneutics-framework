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


class SongOfSongsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.song = cls.library.retrieve_by_id("song-of-songs").object

    def test_song_distinguishes_voices_without_inventing_a_fixed_cast(
        self,
    ) -> None:
        self.assertTrue(
            {
                "the woman or female beloved",
                "the man or male beloved",
                "the daughters of Jerusalem",
                "the woman's brothers",
                "companions or friends",
                "speakers whose identity is uncertain",
            }.issubset(self.song.key_people)
        )
        self.assertTrue(
            {
                "Song of Songs 1:1: superscription associating the song with Solomon",
                "Song of Songs 1:2-2:7: desire, mutual praise, banquet imagery, and the first refrain",
                "Song of Songs 2:8-3:5: spring invitation, absence and search, and the repeated refrain",
                "Song of Songs 3:6-5:1: royal procession, body praise, garden imagery, invitation, and communal acclamation",
                "Song of Songs 5:2-6:3: nocturnal search, violence by watchmen, praise of the absent man, and reunion formula",
                "Song of Songs 6:4-8:4: renewed praise, garden and dance imagery, longing, and the final awakening refrain",
                "Song of Songs 8:5-14: emergence from the wilderness, love and jealousy, family and vineyard sayings, and closing summons",
            }.issubset(self.song.structure)
        )

    def test_song_removes_inherited_generic_wisdom_placeholder(self) -> None:
        inherited_values = {
            "Traditional attribution to Solomon or wise circles",
            "Many scholars see collected wisdom and later shaping",
            "Monarchic wisdom traditions",
            "Israel's covenant community learning wise living under God",
            "Royal, instructional, and reflective wisdom settings within Israel",
            "Job",
            "David",
            "court",
            "temple",
            "suffering",
            "wisdom instruction",
            "praise and lament",
        }
        record_values = {
            *self.song.authorship_positions,
            *self.song.date_ranges,
            self.song.original_audience,
            self.song.historical_setting,
            *self.song.key_people,
            *self.song.key_places,
            *self.song.key_events,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertIn("Hebrew love lyric", self.song.genre)
        self.assertIn("wasf or body-description poem", self.song.genre)
        self.assertIn("search poem", self.song.genre)
        self.assertIn(
            "4QCanta (4Q106), 4QCantb (4Q107), 4QCantc (4Q108), and 6QCant (6Q6)",
            self.song.primary_sources,
        )

    def test_song_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.song.content_status, "draft")
        self.assertEqual(self.song.review_status, "in_review")
        self.assertTrue(self.song.human_review_required)
        self.assertIsNone(self.song.last_reviewed)
        self.assertEqual(self.song.section_status["human_review"], "missing")
        self.assertEqual(self.song.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.song.sources}
        self.assertGreaterEqual(len(self.song.claims), 11)
        self.assertGreaterEqual(len(self.song.interpretive_notes), 18)
        for claim in self.song.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.song.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_song_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.song.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 10)
        self.assertTrue(self.song.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.song.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.song.retrieval_metadata["common_questions"])
        self.assertTrue(self.song.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "solomon",
                "wedding-theme",
                "wisdom-theme",
                "creation-theme",
                "covenant-theme",
                "jerusalem",
                "psalms",
                "proverbs",
                "dead-sea-scrolls",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.song.related_objects
                }
            )
        )

    def test_retrieval_answers_song_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Did Solomon write Song of Songs?",
            "Who is the Shulammite in Song of Songs?",
            "Who speaks in Song of Songs?",
            "What does shalhebetyah flame of Yah mean?",
            "Is Song of Songs erotic love poetry or allegory?",
            "Does do not awaken love forbid dating before marriage?",
            "Does Song of Songs teach consent or permit coercion?",
            "What happens when the watchmen strike the woman?",
            "Does black and beautiful mean black but beautiful?",
            "Does Song of Songs shame bodies singleness or infertility?",
            "What are 4Q106 4Q107 4Q108 and 6Q6?",
            "Why is Greek Song of Songs called Canticle of Canticles?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "song-of-songs")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        shalhebetyah = [
            note
            for note in self.song.interpretive_notes
            if "shalhebetyah may mean" in note.note
        ]
        self.assertTrue(shalhebetyah)
        self.assertEqual(shalhebetyah[0].dispute_status, "lexical_uncertainty")

        consent = [
            note
            for note in self.song.interpretive_notes
            if "does not authorize coercion" in note.note
        ]
        self.assertTrue(consent)
        self.assertEqual(consent[0].note_type, "interpretive-caution")

        colorism = [
            note
            for note in self.song.interpretive_notes
            if "colorist or racialized hierarchy" in note.note
        ]
        self.assertTrue(colorism)
        self.assertEqual(colorism[0].note_type, "interpretive-caution")

        refrain = [
            note
            for note in self.song.interpretive_notes
            if "must not be converted into a universal timetable" in note.note
        ]
        self.assertTrue(refrain)
        self.assertEqual(refrain[0].note_type, "interpretive-caution")

        watchmen = [
            note
            for note in self.song.interpretive_notes
            if "must not normalize assault, stalking, or domestic abuse"
            in note.note
        ]
        self.assertTrue(watchmen)
        self.assertEqual(watchmen[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_song_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-song-of-songs.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id(
                "song-of-songs"
            ).object
            self.assertEqual(sqlite_record.to_dict(), self.song.to_dict())


if __name__ == "__main__":
    unittest.main()
