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


class MicahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.micah = cls.library.retrieve_by_id("micah").object

    def test_micah_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Micah of Moresheth",
                "YHWH in direct speech, reported action, and third-person proclamation",
                "the prophetic first-person voice and the book's framing voice",
                "Samaria, Jerusalem, Jacob, Israel, Judah, daughter Zion, and the remnant",
                "land-grabbers, dispossessed families, false prophets, rulers, chiefs, priests, judges, seers, and diviners",
                "the Bethlehem ruler, the woman in labor, shepherds, and leaders",
                "the mountains, hills, and foundations of the earth as witnesses",
                "Assyria, Babylon, nations, peoples, enemies, and later interpreters",
            }.issubset(self.micah.key_people)
        )
        self.assertTrue(
            {
                "Micah 1:1-16: superscription, divine theophany, judgment on Samaria and Jerusalem, lament, and the Shephelah place-name dirge",
                "Micah 2:1-13: woe against land seizure, disputed prophetic speech, dispossession, remnant gathering, and the breaker",
                "Micah 3:1-12: indictment of rulers, prophets, seers, priests, judges, blood-built Zion, and threatened temple ruin",
                "Micah 4:1-5: nations stream to Zion, instruction, swords become plowshares, and secure life under vine and fig tree",
                "Micah 4:6-5:15 common English / 4:6-5:14 MT: daughter Zion, remnant, labor, Babylon, Bethlehem ruler, Assyria, and purification",
                "Micah 6:1-16: covenant disputation with creation as witness, salvation history, sacrifice questions, Micah 6:8, and Omri's statutes",
                "Micah 7:1-20: lament, social fracture, watchful hope, enemy taunt, shepherd prayer, nations, forgiveness, and promises to Jacob and Abraham",
            }.issubset(self.micah.structure)
        )

    def test_micah_removes_inherited_minor_prophets_placeholder(self) -> None:
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
            *self.micah.authorship_positions,
            *self.micah.date_ranges,
            self.micah.historical_setting,
            *self.micah.key_people,
            *self.micah.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "superscription",
                "theophany",
                "judgment oracle and lament",
                "place-name dirge and wordplay",
                "woe oracle and accusation",
                "disputed prophetic speech and prohibition",
                "remnant and salvation oracle",
                "Zion and nations-pilgrimage oracle",
                "birth, ruler, shepherd, and war oracle",
                "covenant disputation or lawsuit",
                "instruction and wisdom saying",
                "communal lament, confession, enemy taunt, prayer, hymn, and doxology",
            }.issubset(self.micah.genre)
        )
        self.assertIn(
            "Masoretic Micah within the Book of the Twelve",
            self.micah.primary_sources,
        )
        self.assertIn(
            "Old Greek Michaias and other ancient versions",
            self.micah.primary_sources,
        )
        self.assertIn(
            "Judean Desert manuscripts of the Twelve preserving portions of Micah",
            self.micah.primary_sources,
        )

    def test_micah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.micah.content_status, "draft")
        self.assertEqual(self.micah.review_status, "in_review")
        self.assertTrue(self.micah.human_review_required)
        self.assertIsNone(self.micah.last_reviewed)
        self.assertEqual(self.micah.section_status["human_review"], "missing")
        self.assertEqual(
            self.micah.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.micah.sources}
        self.assertGreaterEqual(len(self.micah.claims), 24)
        self.assertGreaterEqual(len(self.micah.interpretive_notes), 40)
        for claim in self.micah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.micah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_micah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.micah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 18)
        self.assertTrue(self.micah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.micah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.micah.retrieval_metadata["common_questions"])
        self.assertTrue(self.micah.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "justice-theme",
                "mercy-theme",
                "messiah-theme",
                "bethlehem-1",
                "assyria",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.micah.related_objects
                }
            )
        )

    def test_retrieval_answers_micah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Micah of Moresheth under Jotham Ahaz and Hezekiah?",
            "When was Micah written and was the whole book composed by the eighth-century prophet?",
            "Where were Moresheth, Gath, Lachish, and the Shephelah towns in Micah 1?",
            "What happened to Samaria in 722 or 721 BCE and Jerusalem in Sennacherib's 701 BCE campaign?",
            "What do Sennacherib's Prism and the Lachish reliefs contribute to reading Micah?",
            "How do the place-name puns work in Micah 1?",
            "Who are the land-grabbers seizing fields, houses, women, children, and inheritance in Micah 2?",
            "Who is speaking in Micah 2:6-11 and who are the breaker and remnant in 2:12-13?",
            "Why does Micah condemn rulers, chiefs, priests, judges, seers, and paid prophets in chapter 3?",
            "How does Jeremiah 26:18 quote Micah 3:12 about Zion becoming a plowed field?",
            "Did Micah 4:1-5 borrow from Isaiah 2:2-4 or did Isaiah borrow from Micah?",
            "What do swords into plowshares and vine and fig tree mean in Micah 4?",
            "Why does Micah 4:10 mention Babylon?",
            "Why do Hebrew and English Bibles number Micah 4:14 and 5:1 differently?",
            "Who is the ruler from Bethlehem Ephrathah whose origins are from ancient days in Micah 5?",
            "Who is the woman in labor in Micah 5 and what are the seven shepherds and eight leaders?",
            "What does Assyria mean in Micah 5 and is the passage messianic?",
            "What military, magical, and cult objects are removed in Micah 5:10-15?",
            "Is Micah 6 a covenant lawsuit or a prophetic disputation?",
            "What do Shittim and Gilgal recall in Micah 6:5?",
            "Does Micah 6:6-8 reject ritual and sacrifice or Judaism?",
            "What do mishpat, hesed, and walking humbly mean in Micah 6:8?",
            "Does the firstborn question in Micah 6:7 endorse child sacrifice?",
            "What are the statutes of Omri and works of Ahab in Micah 6:16?",
            "Who speaks in Micah 7 and how do lament, enemy taunt, confession, and hope fit together?",
            "What does Micah 7:18 mean by who is a God like you and casting sins into the sea?",
            "How do Matthew 2:5-6, Matthew 10:35-36, Luke 12:53, and John 7:42 use Micah?",
            "What are Old Greek Michaias and the Judean Desert manuscripts of Micah?",
            "Can Micah's justice language be captured by a modern political party?",
            "Can Micah 6:8 or forgiveness be weaponized against abuse survivors?",
            "Does Micah authorize antisemitism, supersessionism, nationalism, colonialism, land seizure, or genocide?",
            "How should Micah be read with displaced people, disability language, childbirth imagery, ecology, war, and trauma?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "micah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        composition = [
            note
            for note in self.micah.interpretive_notes
            if "The superscription locates Micah in the reigns of Jotham, Ahaz, and Hezekiah, but the relation between that eighth-century prophet and every unit of the extant book remains disputed"
            in note.note
        ]
        self.assertTrue(composition)
        self.assertEqual(
            composition[0].dispute_status,
            "major_scholarly_disagreement",
        )

        parallel = [
            note
            for note in self.micah.interpretive_notes
            if "Micah 4:1-3 and Isaiah 2:2-4 are closely parallel, but literary direction, dependence, and a possible shared tradition remain disputed"
            in note.note
        ]
        self.assertTrue(parallel)
        self.assertEqual(
            parallel[0].note_type,
            "canonical-connection",
        )

        anti_ritual = [
            note
            for note in self.micah.interpretive_notes
            if "Micah 6:6-8 must not be used to caricature Judaism as legalistic or to oppose ethical obedience to all ritual practice"
            in note.note
        ]
        self.assertTrue(anti_ritual)
        self.assertEqual(
            anti_ritual[0].note_type,
            "interpretive-caution",
        )

        humility = [
            note
            for note in self.micah.interpretive_notes
            if "Walking humbly and extending forgiveness must not be weaponized to silence abuse survivors, bypass accountability, or coerce reconciliation"
            in note.note
        ]
        self.assertTrue(humility)
        self.assertEqual(
            humility[0].note_type,
            "interpretive-caution",
        )

        politics = [
            note
            for note in self.micah.interpretive_notes
            if "Micah's language of justice, land, Zion, nations, peace, and judgment does not map automatically onto any modern party, nation, Zionist, or anti-Zionist program"
            in note.note
        ]
        self.assertTrue(politics)
        self.assertEqual(
            politics[0].note_type,
            "interpretive-caution",
        )

    def test_sqlite_preserves_micah_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-micah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("micah").object
            self.assertEqual(sqlite_record.to_dict(), self.micah.to_dict())


if __name__ == "__main__":
    unittest.main()
