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


class FirstCorinthiansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("1-corinthians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        self.assertTrue(
            {
                "Paul and Sosthenes as named senders; Chloe's people as reporters; and the Corinthian assemblies as addressees",
                "Apollos, Cephas, Stephanas's household, Crispus, Gaius, Fortunatus, Achaicus, Timothy, Aquila, Prisca, and other coworkers",
                "Women and men who pray and prophesy; married, unmarried, widowed, enslaved, free, hungry, ill, weak, strong, and questioning participants",
                "Adam, Israel in the wilderness, Moses, and scriptural voices; apostles, rhetorical interlocutors, factions, patrons, workers, litigants, meal participants, and later interpreters",
            }.issubset(self.record.key_people)
        )
        self.assertTrue(
            {
                "1 Corinthians 1:1-4:21: prescript, thanksgiving, Chloe's report, factions, cross and wisdom, apostles, temple, irony, and apostolic example",
                "1 Corinthians 5:1-6:20: incest case, discipline, lawsuits, vice list, freedom slogan, sex, bodies, and belonging to Christ",
                "1 Corinthians 7:1-40: reported question or slogan, marriage, celibacy, divorce, mixed marriages, calling, slavery, singleness, and present distress",
                "1 Corinthians 8:1-11:1: idol food, knowledge, love, conscience, apostolic rights, renunciation, Israel exempla, idolatry, table fellowship, and imitation",
                "1 Corinthians 11:2-14:40: head coverings and hair, Lord's supper, class inequality, body and gifts, love, tongues, prophecy, discernment, women speaking, and order",
                "1 Corinthians 15:1-58: received gospel tradition, witnesses, denial, Adam and Messiah, resurrection body, baptism for the dead, victory, and steadfast work",
                "1 Corinthians 16:1-24: collection, travel plans, Timothy, Apollos, Stephanas's household, coworkers, greetings, anathema, love, and grace",
            }.issubset(self.record.structure)
        )

    def test_record_removes_placeholder_and_qualifies_composition(self) -> None:
        record_values = {
            *self.record.authorship_positions,
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        self.assertNotIn("Titus", record_values)
        self.assertNotIn("Rome", record_values)
        self.assertNotIn("church formation", record_values)
        self.assertNotIn("pastoral instruction", record_values)
        self.assertEqual(
            len(self.record.key_events),
            len({event.casefold() for event in self.record.key_events}),
        )
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "Paul" in position
                and "Sosthenes" in position
                and "co-sender" in position
                for position in self.record.authorship_positions
            )
        )
        self.assertTrue(
            {
                "Pauline letter with prescript, thanksgiving, report response, answers to a received letter, travel report, greetings, anathema, and benediction",
                "diatribe, rhetorical question, possible Corinthian slogan, irony, parody, apostolic self-presentation, vice list, analogy, case judgment, and deliberative counsel",
                "scriptural quotation and exemplum, household instruction, apocalyptic warning, tradition report, gift list, encomium or hymn-like praise, and resurrection argument",
            }.issubset(self.record.genre)
        )

    def test_record_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.record.content_status, "draft")
        self.assertEqual(self.record.review_status, "in_review")
        self.assertTrue(self.record.human_review_required)
        self.assertIsNone(self.record.last_reviewed)
        self.assertEqual(self.record.section_status["human_review"], "missing")
        self.assertEqual(self.record.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.record.sources}
        self.assertGreaterEqual(len(self.record.claims), 42)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 70)
        for claim in self.record.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.record.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_record_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.record.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 28)
        self.assertTrue(self.record.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.record.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.record.retrieval_metadata["common_questions"])
        self.assertTrue(self.record.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "paul",
                "apollos",
                "adam",
                "corinth",
                "spiritual-gifts",
                "lords-supper",
                "resurrection-theme",
                "baptism",
                "spirit-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote 1 Corinthians and what role did Sosthenes have?",
            "When and where was First Corinthians written?",
            "Who were Chloe's people in 1 Corinthians?",
            "What does 1 Corinthians 7:1 say about the letter sent to Paul?",
            "What were the Corinthian factions and slogans?",
            "Was 1 Corinthians assembled from multiple letters?",
            "What are P15 P46 and P123 in 1 Corinthians?",
            "What do Sinaiticus Vaticanus Ephraemi and Claromontanus show in 1 Corinthians?",
            "What does the word of the cross mean in 1 Corinthians?",
            "What are wisdom foolishness and power in 1 Corinthians?",
            "Who is the spiritual person in 1 Corinthians 2?",
            "What does God's temple mean in 1 Corinthians 3?",
            "What does Paul mean by judging nothing before the time?",
            "What happened in the incest case in 1 Corinthians 5?",
            "What does deliver to Satan mean in 1 Corinthians?",
            "Should Christians judge outsiders in 1 Corinthians?",
            "What do lawsuits teach in 1 Corinthians 6?",
            "What do malakoi and arsenokoitai mean in 1 Corinthians 6?",
            "Does 1 Corinthians address modern sexual orientation?",
            "What does the body as temple mean in 1 Corinthians 6?",
            "What does all things are lawful mean in 1 Corinthians?",
            "What does 1 Corinthians teach about marriage and celibacy?",
            "What does 1 Corinthians teach about divorce and mixed marriages?",
            "What does remain in your calling mean in 1 Corinthians 7?",
            "Does 1 Corinthians justify slavery?",
            "Who are the virgins or betrothed in 1 Corinthians 7?",
            "What does idol food mean in 1 Corinthians 8?",
            "Who are weaker members and what is conscience?",
            "Why does Paul renounce apostolic rights in 1 Corinthians 9?",
            "What does becoming all things to all people mean in 1 Corinthians?",
            "How does 1 Corinthians 10 interpret Israel in the wilderness?",
            "Are idols nothing or demonic in 1 Corinthians?",
            "What does one table mean in 1 Corinthians 10?",
            "Must women cover their heads in 1 Corinthians 11?",
            "What does kephale mean in 1 Corinthians 11?",
            "Who are the angels and what does nature teach about hair?",
            "What was wrong with the Lord's supper in 1 Corinthians?",
            "Does unworthy manner mean personal unworthiness in 1 Corinthians?",
            "What do weakness illness and death mean at the Corinthian meal?",
            "What does one body and many members mean?",
            "How should spiritual gifts be ranked in 1 Corinthians?",
            "What does the love chapter mean in the literary context of 1 Corinthians?",
            "Are tongues human languages or ecstatic speech in 1 Corinthians?",
            "How should prophecy and discernment work in 1 Corinthians 14?",
            "Is 1 Corinthians 13 an interpolation?",
            "Did Paul silence all women in 1 Corinthians 14?",
            "Why do 1 Corinthians 14:34-35 move in some manuscripts?",
            "What gospel tradition did Paul receive in 1 Corinthians 15?",
            "Who were the resurrection witnesses in 1 Corinthians 15?",
            "What does baptism for the dead mean in 1 Corinthians?",
            "What is a spiritual body in 1 Corinthians 15?",
            "How do Adam and Christ relate in 1 Corinthians 15?",
            "What does death where is your victory mean in 1 Corinthians?",
            "Why was Paul collecting money for Jerusalem in 1 Corinthians?",
            "Who were Stephanas Fortunatus and Achaicus in 1 Corinthians?",
            "What does maranatha mean in 1 Corinthians 16?",
            "Does 1 Corinthians justify public shaming or authoritarian discipline?",
            "Does 1 Corinthians justify anti LGBTQ coercion or violence?",
            "Does 1 Corinthians justify misogyny or gender essentialism?",
            "Does 1 Corinthians justify forced marriage celibacy or divorce coercion?",
            "Does 1 Corinthians justify slavery or worker exploitation?",
            "Does 1 Corinthians justify class humiliation or eucharistic exclusion?",
            "Does 1 Corinthians justify coercive tongues prophecy or dangerous exorcism?",
            "Does 1 Corinthians justify antisemitism or supersessionism?",
            "Does 1 Corinthians support prosperity extraction or poverty romanticization?",
            "Does 1 Corinthians authorize nationalism conspiracy theories or partisan capture?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "1-corinthians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        self.assertTrue(
            any(
                "malakoi" in note
                and "arsenokoitai" in note
                and "modern sexual orientation" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "head coverings" in note
                and "kephale" in note
                and "silencing women" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "14:34-35" in note
                and "textual displacement" in note
                and "women pray and prophesy" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Lord's supper" in note
                and "class humiliation" in note
                and "eucharistic exclusion" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "slavery" in note
                and "cannot justify" in note
                and "enslavement" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "resurrection body" in note
                and "physicality" in note
                and "body shame" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-1-corinthians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("1-corinthians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())
