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


class ZechariahRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.zechariah = cls.library.retrieve_by_id("zechariah").object

    def test_zechariah_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the dated framing voice and Zechariah son of Berechiah son of Iddo",
                "YHWH in direct speech, reported action, judgment, mercy, kingship, and promised presence",
                "the angel who speaks with Zechariah, the angel of YHWH, the horseman, patrols, and heavenly council",
                "the accuser called Satan, Joshua the high priest, Zerubbabel governor of Judah, and the Branch",
                "two anointed ones, the flying scroll, the woman called Wickedness, ephah-bearers, and four chariots",
                "priests, earlier prophets, the Bethel delegation, remnant, shepherds, flocks, mourners, and nations",
                "Daughter Zion, Jerusalem, Judah, a humble king, living waters, creation, and later interpreters",
            }.issubset(self.zechariah.key_people)
        )
        self.assertTrue(
            {
                "Zechariah 1:1-6: dated call to return, ancestral warning, and remembered effectiveness of the earlier prophets",
                "Zechariah 1:7-6:15: interconnected night visions, angelic interpretations, Joshua's cleansing, Zerubbabel oracles, symbolic judgments, chariots, and crowning",
                "Zechariah 7:1-8:23: Bethel's fasting inquiry, justice and mercy indictment, restoration promises, transformed fasts, and nations seeking YHWH",
                "Zechariah 9:1-11:17: nation oracles, humble royal advent, covenant prisoners, restoration warfare, and competing shepherd sign acts",
                "Zechariah 12:1-14:21: Jerusalem conflict, piercing and mourning, purification, struck shepherd, remnant, Day of YHWH, living waters, pilgrimage, and pervasive holiness",
            }.issubset(self.zechariah.structure)
        )

    def test_zechariah_removes_inherited_minor_prophets_placeholder(self) -> None:
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
            *self.zechariah.authorship_positions,
            *self.zechariah.date_ranges,
            self.zechariah.historical_setting,
            *self.zechariah.key_people,
            *self.zechariah.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "dated superscription, return call, and ancestral admonition",
                "night vision, interpreting-angel dialogue, divine-council scene, and oracle",
                "accusation, priestly cleansing, symbolic action, and sign-act report",
                "lampstand vision, rebuilding oracle, flying-scroll vision, ephah vision, and chariot vision",
                "crowning report, fasting inquiry, disputation, ethical exhortation, and salvation promise",
                "nation oracle, royal advent, covenant release, and restoration warfare poetry",
                "shepherd allegory, sign act, rejection report, lament, and judgment oracle",
                "apocalyptic battle oracle, mourning liturgy, purification promise, cosmic transformation, pilgrimage, and holiness conclusion",
            }.issubset(self.zechariah.genre)
        )
        self.assertIn(
            "Masoretic Zechariah within the Book of the Twelve",
            self.zechariah.primary_sources,
        )
        self.assertIn(
            "Old Greek Zacharias and other ancient versions",
            self.zechariah.primary_sources,
        )
        self.assertIn(
            "Judean Desert witnesses to Zechariah and the Twelve",
            self.zechariah.primary_sources,
        )

    def test_zechariah_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.zechariah.content_status, "draft")
        self.assertEqual(self.zechariah.review_status, "in_review")
        self.assertTrue(self.zechariah.human_review_required)
        self.assertIsNone(self.zechariah.last_reviewed)
        self.assertEqual(
            self.zechariah.section_status["human_review"],
            "missing",
        )
        self.assertEqual(
            self.zechariah.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.zechariah.sources}
        self.assertGreaterEqual(len(self.zechariah.claims), 30)
        self.assertGreaterEqual(len(self.zechariah.interpretive_notes), 52)
        for claim in self.zechariah.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.zechariah.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_zechariah_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.zechariah.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 20)
        self.assertTrue(self.zechariah.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.zechariah.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(
            self.zechariah.retrieval_metadata["common_questions"]
        )
        self.assertTrue(
            self.zechariah.retrieval_metadata["semantic_keywords"]
        )
        self.assertTrue(
            {
                "zechariah-the-prophet",
                "rebuilding-the-temple",
                "return-from-exile",
                "messiah-theme",
                "restoration-theme",
                "haggai",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.zechariah.related_objects
                }
            )
        )

    def test_retrieval_answers_zechariah_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Zechariah son of Berechiah son of Iddo?",
            "When were Zechariah's dated messages in Darius years two and four?",
            "How many night visions are in Zechariah and how are they ordered?",
            "Who is the angel who speaks with Zechariah and the angel of YHWH?",
            "What do the colored horses and patrol report in Zechariah 1?",
            "Who are the four horns and craftsmen in Zechariah 1?",
            "Why does a man measure Jerusalem in Zechariah 2?",
            "Who is Satan the accuser in Joshua's heavenly trial?",
            "Why are Joshua the high priest's filthy garments removed?",
            "Who or what is the Branch in Zechariah 3 and 6?",
            "What are the stone and seven eyes before Joshua?",
            "What do the lampstand olive trees and two anointed ones mean?",
            "Why is it not by might nor power but by my Spirit?",
            "How does Zerubbabel finish the temple in Zechariah 4?",
            "What is the flying scroll and its curse in Zechariah 5?",
            "Who is the woman called Wickedness inside the ephah?",
            "Why is the ephah carried to Shinar?",
            "What are the four chariots and winds or spirits of heaven?",
            "Who is crowned in Zechariah 6 and where are the crowns kept?",
            "Did Joshua's crown make him king or enact the Branch?",
            "Why did the Bethel delegation ask about fasting in Zechariah 7?",
            "What happened when ancestors refused justice mercy and compassion?",
            "How do the fasts become cheerful festivals of truth and peace?",
            "Why do nations grasp a Jew's garment in Zechariah 8?",
            "Who is the humble king riding a donkey in Zechariah 9?",
            "What does covenant blood release prisoners from the waterless pit?",
            "Who are the shepherds flocks and two staffs Favor and Union?",
            "What do thirty pieces of silver and potter or treasury mean?",
            "Who is the worthless shepherd in Zechariah 11?",
            "Who is pierced in Zechariah 12 and why do families mourn?",
            "What fountain opens for sin and impurity in Zechariah 13?",
            "Who is the struck shepherd and scattered flock?",
            "What does two-thirds perish and one-third refined mean?",
            "Does the Mount of Olives split literally in Zechariah 14?",
            "What are the living waters flowing from Jerusalem?",
            "Why do nations keep the Feast of Booths in Zechariah 14?",
            "Why are bells and cooking pots holy to YHWH?",
            "Are Zechariah chapters 9 through 14 by the same author and date?",
            "What are Masoretic Zechariah Old Greek Zacharias and Judean Desert witnesses?",
            "How do Haggai Ezra Isaiah Jeremiah Ezekiel Daniel and Psalms relate to Zechariah?",
            "How do the Gospels Hebrews and Revelation receive Zechariah?",
            "Does Zechariah authorize rebuilding a modern temple or threatening holy sites?",
            "Does Zechariah justify calling political opponents satanic or wicked?",
            "Does Zechariah justify nationalism siege conquest or collective punishment?",
            "May Zechariah's purity and disability metaphors stigmatize people?",
            "Does Zechariah predict modern dates states wars or conspiracy theories?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "zechariah")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        branch = [
            note
            for note in self.zechariah.interpretive_notes
            if "The Branch in Zechariah 3:8 and 6:12 carries royal-Davidic associations, but the relationship among the title, Zerubbabel, Joshua, and later messianic reception remains disputed"
            in note.note
        ]
        self.assertTrue(branch)
        self.assertEqual(
            branch[0].dispute_status,
            "major_scholarly_disagreement",
        )

        pierced = [
            note
            for note in self.zechariah.interpretive_notes
            if "The Hebrew of Zechariah 12:10 identifies a pierced figure but leaves contested the speaker, object, agency, identity, and relationship between looking and mourning"
            in note.note
        ]
        self.assertTrue(pierced)
        self.assertEqual(
            pierced[0].dispute_status,
            "major_scholarly_disagreement",
        )

        unity = [
            note
            for note in self.zechariah.interpretive_notes
            if "The final book joins dated material in chapters 1-8 with largely undated oracles in chapters 9-14, whose date, authorship, sources, and redaction remain substantially disputed"
            in note.note
        ]
        self.assertTrue(unity)
        self.assertEqual(unity[0].note_type, "interpretive-caution")

        temple = [
            note
            for note in self.zechariah.interpretive_notes
            if "Zechariah's Persian-period temple restoration does not authorize seizing, damaging, or threatening contemporary Jewish, Muslim, Christian, Palestinian, or other communities and holy sites"
            in note.note
        ]
        self.assertTrue(temple)
        self.assertEqual(temple[0].note_type, "interpretive-caution")

        violence = [
            note
            for note in self.zechariah.interpretive_notes
            if "Zechariah's siege, plague, battle, and remnant imagery cannot legitimate conquest, ethnic cleansing, collective punishment, militarism, or retaliatory violence"
            in note.note
        ]
        self.assertTrue(violence)
        self.assertEqual(violence[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_zechariah_claims_and_governance_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-zechariah.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id(
                "zechariah"
            ).object
            self.assertEqual(
                sqlite_record.to_dict(),
                self.zechariah.to_dict(),
            )
