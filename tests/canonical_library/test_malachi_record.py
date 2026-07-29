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


class MalachiRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.malachi = cls.library.retrieve_by_id("malachi").object

    def test_malachi_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the superscription and disputation voice, with malakhi possibly a personal name or the title 'my messenger'",
                "YHWH in direct speech, accusation, promise, judgment, compassion, and remembered covenant",
                "priests, Levi and Levites, worshipers, blemished animals, a governor, husbands, wives of youth, and altar weepers",
                "Jacob, Esau, Edom, Judah, Jerusalem, descendants of Jacob, tithers, nations, arrogant people, and evildoers",
                "the coming messenger, the Lord sought, the messenger of the covenant, a refiner, and a launderer",
                "sorcerers, adulterers, false swearers, exploited workers, widows, orphans, and resident aliens",
                "those who fear YHWH, a remembrance book, a treasured possession, Moses, Elijah, parents, children, land, sun, calves, and later interpreters",
            }.issubset(self.malachi.key_people)
        )
        self.assertTrue(
            {
                "Malachi 1:1: superscription identifying the book as a massa of YHWH's word to Israel through malakhi",
                "Malachi 1:2-5: disputed love, Jacob and Esau, Edom's ruin, and YHWH's greatness beyond Israel's border",
                "Malachi 1:6-2:9: priestly dishonor, blemished offerings, YHWH's name among nations, covenant with Levi, Torah instruction, and partiality",
                "Malachi 2:10-16: one-father and covenant appeal, communal faithlessness, foreign-god marriage accusation, altar tears, wife of youth, divorce, and violence",
                "Malachi 2:17-3:5: complaint about divine justice, messenger announcement, sudden coming, Levitical refining, acceptable offerings, and judgment protecting vulnerable neighbors",
                "Malachi 3:6-12: YHWH's constancy, Jacob's preservation, return summons, tithes and offerings, storehouse challenge, agricultural blessing, and nations' recognition",
                "Malachi 3:13-18: harsh speech, arrogant and evildoing people, God-fearers' remembrance book, treasured possession, compassion, and renewed distinction",
                "Malachi 4:1-6 in common Christian numbering, corresponding to 3:19-24 in Hebrew numbering: burning Day, healing sun, remembered Torah of Moses, Elijah's return, intergenerational turning, and threatened herem",
            }.issubset(self.malachi.structure)
        )

    def test_malachi_removes_inherited_minor_prophets_placeholder(self) -> None:
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
            *self.malachi.authorship_positions,
            *self.malachi.date_ranges,
            self.malachi.historical_setting,
            *self.malachi.key_people,
            *self.malachi.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "massa superscription and prophetic word formula",
                "disputation, question-and-answer rhetoric, accusation, answer, and command",
                "election and love oracle, nation contrast, and judgment saying",
                "priestly accusation, cultic critique, curse, covenant lawsuit, and Torah instruction",
                "lament, marriage and kinship accusation, covenant appeal, and difficult legal-poetic speech",
                "messenger oracle, purification scene, judgment catalogue, and vulnerable-neighbor indictment",
                "return call, tithing challenge, blessing promise, agricultural imagery, and nation recognition",
                "remembrance notice, treasured-possession promise, eschatological contrast, Day-of-YHWH oracle, and Torah-prophetic epilogue",
            }.issubset(self.malachi.genre)
        )
        self.assertIn(
            "Masoretic Malachi within the Book of the Twelve",
            self.malachi.primary_sources,
        )
        self.assertIn(
            "Old Greek Malachias and other ancient versions",
            self.malachi.primary_sources,
        )
        self.assertIn(
            "Judean Desert witnesses to Malachi and the Twelve",
            self.malachi.primary_sources,
        )

    def test_malachi_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.malachi.content_status, "draft")
        self.assertEqual(self.malachi.review_status, "in_review")
        self.assertTrue(self.malachi.human_review_required)
        self.assertIsNone(self.malachi.last_reviewed)
        self.assertEqual(
            self.malachi.section_status["human_review"],
            "missing",
        )
        self.assertEqual(
            self.malachi.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.malachi.sources}
        self.assertGreaterEqual(len(self.malachi.claims), 30)
        self.assertGreaterEqual(len(self.malachi.interpretive_notes), 55)
        for claim in self.malachi.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.malachi.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_malachi_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.malachi.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 20)
        self.assertTrue(self.malachi.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.malachi.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(
            self.malachi.retrieval_metadata["common_questions"]
        )
        self.assertTrue(
            self.malachi.retrieval_metadata["semantic_keywords"]
        )
        self.assertTrue(
            {
                "temple-theme",
                "priesthood",
                "covenant-theme",
                "day-of-the-lord-prophecy",
                "messiah-theme",
                "zechariah",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.malachi.related_objects
                }
            )
        )

    def test_retrieval_answers_malachi_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Is Malachi a prophet's name or the Hebrew title my messenger?",
            "When was Malachi written in Persian-period Yehud?",
            "How do Malachi's disputations and question answers work?",
            "Why does YHWH say I have loved you in Malachi?",
            "What do Jacob Esau and Edom mean in Malachi 1?",
            "Does Malachi map Edom onto a modern people or state?",
            "Why are priests accused of despising YHWH's name?",
            "What are polluted food and YHWH's table in Malachi?",
            "Why are blind lame and sick animals rejected as offerings?",
            "What does offering them to your governor imply?",
            "What do rising sun incense and pure offering among nations mean?",
            "What is the covenant with Levi in Malachi 2?",
            "Why should a priest's lips guard Torah knowledge?",
            "How did priests show partiality in Torah?",
            "What do one father and one God mean in Malachi 2:10?",
            "Who is the daughter of a foreign god in Malachi 2:11?",
            "Why do tears cover the altar in Malachi 2?",
            "Who is the wife of your youth and covenant partner?",
            "Does Malachi say God hates divorce?",
            "What do violence and covering a garment mean in Malachi 2:16?",
            "Does Malachi require someone to remain in an abusive marriage?",
            "Who is my messenger preparing the way in Malachi 3:1?",
            "Who are the Lord and messenger of the covenant?",
            "What does sudden coming to the temple mean?",
            "What do refiner's fire and launderer's soap mean?",
            "Why are the sons of Levi purified?",
            "Which sorcerers adulterers false swearers and oppressors are judged?",
            "How does Malachi protect workers widows orphans and resident aliens?",
            "What does I YHWH do not change mean?",
            "How should return to me and I will return to you be read?",
            "Does robbing God refer to tithes and offerings?",
            "What is the whole tithe and temple storehouse?",
            "Why does Malachi tell people to test God?",
            "What are the windows of heaven and the devourer?",
            "Does Malachi promise wealth to everyone who gives money?",
            "What is the remembrance book before YHWH?",
            "Who are YHWH's treasured possession in Malachi 3?",
            "What is the sun of righteousness with healing in its wings?",
            "Why do the righteous leap like calves and tread ashes?",
            "How do Hebrew Malachi 3:19-24 and Christian Malachi 4:1-6 correspond?",
            "Why remember the Torah of Moses at Horeb?",
            "Why does Elijah return before the great and terrible Day?",
            "What does turning parents' and children's hearts mean?",
            "What is the threatened herem or curse at Malachi's end?",
            "What are Masoretic Malachi Old Greek Malachias and Judean Desert witnesses?",
            "How do Ezra Nehemiah Haggai and Zechariah relate to Malachi?",
            "How do Matthew Mark Luke and Romans receive Malachi?",
            "Does Malachi justify antisemitism or treating Jewish priests as uniquely corrupt?",
            "Does Malachi justify coercive tithing fundraising or prosperity teaching?",
            "Does Malachi blame poverty drought crop loss illness or disaster on insufficient giving?",
            "May Malachi's purity language stigmatize disabled people?",
            "Does Malachi authorize forced reconciliation with abusive parents?",
            "Does Malachi predict modern dates wars nations or political parties?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "malachi")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        identity = [
            note
            for note in self.malachi.interpretive_notes
            if "The Hebrew malakhi in 1:1 may function as the prophet's personal name, an abbreviated name, or the title 'my messenger'; the text does not settle the biography"
            in note.note
        ]
        self.assertTrue(identity)
        self.assertEqual(
            identity[0].dispute_status,
            "major_scholarly_disagreement",
        )

        divorce = [
            note
            for note in self.malachi.interpretive_notes
            if "Malachi 2:15-16 is textually and syntactically difficult, so translations differ over subject, agency, hatred, divorce, violence, and the garment"
            in note.note
        ]
        self.assertTrue(divorce)
        self.assertEqual(
            divorce[0].dispute_status,
            "major_scholarly_disagreement",
        )

        messenger = [
            note
            for note in self.malachi.interpretive_notes
            if "The identities and relationship of 'my messenger,' the Lord sought, and the messenger of the covenant in 3:1 remain disputed within the book's historical horizon and later reception"
            in note.note
        ]
        self.assertTrue(messenger)
        self.assertEqual(messenger[0].note_type, "interpretive-caution")

        abuse = [
            note
            for note in self.malachi.interpretive_notes
            if "Malachi's covenant-faithfulness appeal cannot require a spouse or child to remain with, return to, reconcile with, or conceal an abuser"
            in note.note
        ]
        self.assertTrue(abuse)
        self.assertEqual(abuse[0].note_type, "interpretive-caution")

        prosperity = [
            note
            for note in self.malachi.interpretive_notes
            if "Malachi 3:8-12 addresses a particular covenant community, temple storehouse, and agrarian crisis; it cannot guarantee private wealth, license coercive fundraising, or blame suffering on insufficient giving"
            in note.note
        ]
        self.assertTrue(prosperity)
        self.assertEqual(prosperity[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_malachi_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-malachi.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id(
                "malachi"
            ).object
            self.assertEqual(
                sqlite_record.to_dict(),
                self.malachi.to_dict(),
            )
