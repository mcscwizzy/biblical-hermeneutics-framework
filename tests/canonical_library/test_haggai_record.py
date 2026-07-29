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


class HaggaiRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.haggai = cls.library.retrieve_by_id("haggai").object

    def test_haggai_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the dated framing voice and Haggai the prophet as YHWH's messenger",
                "YHWH in direct speech, reported action, presence, spirit, blessing, and political shaking",
                "Zerubbabel son of Shealtiel, governor of Judah, and Joshua son of Jehozadak, the high priest",
                "Darius I, Persian king, as the regnal frame rather than a speaking character",
                "priests answering Haggai's Torah questions about holiness and corpse impurity",
                "the remnant or people, including elders who remembered or knew reports of the former temple",
                "laborers, ancestors, nations, kingdoms, heaven, earth, sea, dry land, crops, animals, and later interpreters",
            }.issubset(self.haggai.key_people)
        )
        self.assertTrue(
            {
                "Haggai 1:1: regnal and calendar superscription addressing Zerubbabel and Joshua in Darius I's second year",
                "Haggai 1:2-11: dispute over the temple's time, paneled houses, failed labor, repeated consideration formula, and drought",
                "Haggai 1:12-15: leaders and remnant obey, fear YHWH, receive the presence assurance, and have their spirits stirred",
                "Haggai 2:1-9: encouragement amid comparison with the former house, covenantal presence, cosmic shaking, nations' treasure, glory, and peace",
                "Haggai 2:10-19: priestly Torah inquiry, holiness and corpse impurity analogy, retrospective scarcity, foundation, and promised blessing",
                "Haggai 2:20-23: second oracle on the day, overthrow of kingdoms, Zerubbabel as servant and chosen signet",
            }.issubset(self.haggai.structure)
        )

    def test_haggai_removes_inherited_minor_prophets_placeholder(self) -> None:
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
            *self.haggai.authorship_positions,
            *self.haggai.date_ranges,
            self.haggai.historical_setting,
            *self.haggai.key_people,
            *self.haggai.key_places,
        }
        self.assertTrue(inherited_values.isdisjoint(record_values))
        self.assertTrue(
            {
                "dated superscription and prose prophetic report",
                "messenger formula, disputation, accusation, and rhetorical question",
                "covenant-curse and de-creation speech",
                "exhortation, obedience report, divine assurance, and spirit-stirring notice",
                "temple comparison and salvation promise",
                "divine-warrior and cosmic-shaking oracle",
                "priestly Torah inquiry and ritual-purity analogy",
                "retrospective oracle and blessing promise",
                "royal oracle, servant saying, election formula, and signet metaphor",
            }.issubset(self.haggai.genre)
        )
        self.assertIn(
            "Masoretic Haggai within the Book of the Twelve",
            self.haggai.primary_sources,
        )
        self.assertIn(
            "Old Greek Aggaios and other ancient versions",
            self.haggai.primary_sources,
        )
        self.assertIn(
            "Judean Desert witnesses to Haggai and the Twelve",
            self.haggai.primary_sources,
        )

    def test_haggai_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.haggai.content_status, "draft")
        self.assertEqual(self.haggai.review_status, "in_review")
        self.assertTrue(self.haggai.human_review_required)
        self.assertIsNone(self.haggai.last_reviewed)
        self.assertEqual(self.haggai.section_status["human_review"], "missing")
        self.assertEqual(
            self.haggai.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.haggai.sources}
        self.assertGreaterEqual(len(self.haggai.claims), 24)
        self.assertGreaterEqual(len(self.haggai.interpretive_notes), 40)
        for claim in self.haggai.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.haggai.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_haggai_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.haggai.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 18)
        self.assertTrue(self.haggai.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.haggai.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.haggai.retrieval_metadata["common_questions"])
        self.assertTrue(self.haggai.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "rebuilding-the-temple",
                "temple-theme",
                "return-from-exile",
                "restoration-theme",
                "zechariah-the-prophet",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.haggai.related_objects
                }
            )
        )

    def test_retrieval_answers_haggai_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who was Haggai and what does his name mean?",
            "When were Haggai's four dated messages delivered in 520 BCE?",
            "Who were Zerubbabel son of Shealtiel and Joshua son of Jehozadak?",
            "Why does Haggai date his prophecy by Darius the Persian king?",
            "What did these people mean by saying the time to rebuild had not come?",
            "Were Haggai's paneled houses luxurious or merely roofed?",
            "What does consider your ways mean in Haggai?",
            "Why did wages fall into a bag with holes?",
            "Does Haggai blame drought poverty or crop failure on personal sin?",
            "How did the people obey fear YHWH and have their spirits stirred?",
            "What does I am with you mean in Haggai?",
            "Who remembered the former temple and why did the new house look like nothing?",
            "Why does Haggai repeat be strong and mention the divine spirit?",
            "What covenant was made when Israel came out of Egypt in Haggai 2?",
            "When will God shake the heavens earth sea dry land nations and kingdoms?",
            "Does Haggai 2:7 mean the desire of all nations or their treasures?",
            "How can the latter glory of the temple be greater and bring peace?",
            "Why did Haggai ask priests questions about holy meat and corpse impurity?",
            "Can holiness transfer by touch in Haggai 2?",
            "Who are this people and was their work or worship defiled?",
            "Which date was the temple foundation laid in Haggai?",
            "What changed from this day I will bless you?",
            "Why is Zerubbabel called servant chosen and a signet ring?",
            "Does Haggai reverse Jeremiah 22's judgment on Coniah's signet?",
            "Did Haggai predict Zerubbabel would become king or Messiah?",
            "What are the Masoretic Text Old Greek Aggaios and Judean Desert witnesses?",
            "How do Ezra Zechariah Jeremiah Leviticus Numbers and Hebrews relate to Haggai?",
            "Does Hebrews 12 quote Haggai's shaking oracle?",
            "Does Haggai authorize rebuilding a modern temple or threatening holy sites?",
            "Does Haggai authorize coercive fundraising exploitative church construction or unpaid labor?",
            "Does Haggai support prosperity teaching or blaming poor displaced people for hardship?",
            "May purity language stigmatize corpses illness menstruation disability caste race or class?",
            "Can Persia Yehud Zerubbabel or temple restoration be mapped onto modern states or parties?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "haggai")

    def test_difficult_interpretations_remain_explicitly_qualified(
        self,
    ) -> None:
        treasure = [
            note
            for note in self.haggai.interpretive_notes
            if "The Hebrew phrase in Haggai 2:7 is grammatically and contextually disputed between the desirable or precious things of the nations and a singular desired figure"
            in note.note
        ]
        self.assertTrue(treasure)
        self.assertEqual(
            treasure[0].dispute_status,
            "major_scholarly_disagreement",
        )

        zerubbabel = [
            note
            for note in self.haggai.interpretive_notes
            if "Zerubbabel's designation as servant, chosen one, and signet conveys royal-Davidic significance without reporting that he became king"
            in note.note
        ]
        self.assertTrue(zerubbabel)
        self.assertEqual(zerubbabel[0].note_type, "interpretive-caution")

        temple = [
            note
            for note in self.haggai.interpretive_notes
            if "Haggai's call to rebuild Jerusalem's Persian-period temple does not authorize projects that threaten contemporary Jewish, Muslim, Palestinian, Christian, or other communities and holy sites"
            in note.note
        ]
        self.assertTrue(temple)
        self.assertEqual(temple[0].note_type, "interpretive-caution")

        purity = [
            note
            for note in self.haggai.interpretive_notes
            if "Haggai's ritual-purity analogy must not stigmatize corpses, mourners, illness, menstruation, disability, caste, race, poverty, or social class"
            in note.note
        ]
        self.assertTrue(purity)
        self.assertEqual(purity[0].note_type, "interpretive-caution")

        labor = [
            note
            for note in self.haggai.interpretive_notes
            if "The rebuilding command cannot justify coercive fundraising, exploitative construction, forced or unpaid labor, displacement, or silencing dissent"
            in note.note
        ]
        self.assertTrue(labor)
        self.assertEqual(labor[0].note_type, "interpretive-caution")

    def test_sqlite_preserves_haggai_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-haggai.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("haggai").object
            self.assertEqual(sqlite_record.to_dict(), self.haggai.to_dict())


if __name__ == "__main__":
    unittest.main()
