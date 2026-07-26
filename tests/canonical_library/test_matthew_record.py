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


class MatthewRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.matthew = cls.library.retrieve_by_id("matthew").object

    def test_matthew_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the narrator and embedded speakers, including angels, Scripture citations, crowds, disciples, opponents, and authorities",
                "Jesus as Messiah, son of David, son of Abraham, Emmanuel, Son of God, Son of Man, teacher, healer, judge, and king",
                "Mary, Joseph, genealogy figures and women, magi, Herod the Great and his household, and children endangered in Bethlehem",
                "John the Baptist, the tempter, disciples and the Twelve, Peter, James, John, Matthew the toll collector, women disciples, children, petitioners, and centurions",
                "scribes, Pharisees, Sadducees, chief priests, elders, Herod Antipas, John's disciples, and the Canaanite woman",
                "Judas, Caiaphas, Pilate and his wife, Barabbas, soldiers, Joseph of Arimathea, Mary Magdalene, the other Mary, guards, angels, and the nations",
                "Israel, Judea, Galilee, Jerusalem, the temple, the ekklesia, Father, Son, Spirit, and later Jewish and Christian interpreters",
            }.issubset(self.matthew.key_people)
        )
        self.assertTrue(
            {
                "Matthew 1:1-4:16: genealogy, conception and birth, magi and Herod, Egypt and Nazareth, John, baptism, temptation, and Galilean dawn",
                "Matthew 4:17-7:29: kingdom proclamation, disciple calls, healings, crowds, and the Sermon on the Mount",
                "Matthew 8:1-11:1: authoritative deeds, healings and exorcisms, contested discipleship, harvest, Twelve, and mission discourse",
                "Matthew 11:2-13:53: responses to Jesus, Sabbath and Beelzebul controversies, family saying, and parables discourse",
                "Matthew 13:54-19:2: rejection, Herod and John, feedings, sea crossings, controversies, Peter's confession, transfiguration, and community discourse",
                "Matthew 19:3-25:46: Judea and Jerusalem journey, temple controversies, woes, lament, and eschatological discourse",
                "Matthew 26:1-28:20: anointing, meal, Gethsemane, arrest, trials, crucifixion, burial, empty tomb, appearance, worship and doubt, and commission",
            }.issubset(self.matthew.structure)
        )

    def test_matthew_removes_inherited_gospels_and_acts_placeholder(self) -> None:
        forbidden = {
            "Traditional evangelist or Lukan authorship",
            "Acts is often read as slightly later than Luke",
            "Paul",
        }
        record_values = {
            *self.matthew.authorship_positions,
            *self.matthew.date_ranges,
            *self.matthew.key_people,
        }
        self.assertTrue(forbidden.isdisjoint(record_values))
        self.assertEqual(
            len(self.matthew.key_events),
            len({event.casefold() for event in self.matthew.key_events}),
        )
        self.assertTrue(
            {
                "ancient biography and Gospel narrative",
                "genealogy, birth narrative, dream report, scriptural citation, and fulfillment formula",
                "kingdom proclamation, call story, healing, exorcism, controversy, pronouncement, and commission",
                "beatitude, aphorism, antithesis, prayer, legal instruction, wisdom saying, and parable",
                "miracle story, confession, transfiguration, community rule, and apocalyptic discourse",
                "passion narrative, meal, trial, lament, mockery, death, burial, empty tomb, appearance, and commissioning scene",
            }.issubset(self.matthew.genre)
        )

    def test_matthew_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.matthew.content_status, "draft")
        self.assertEqual(self.matthew.review_status, "in_review")
        self.assertTrue(self.matthew.human_review_required)
        self.assertIsNone(self.matthew.last_reviewed)
        self.assertEqual(self.matthew.section_status["human_review"], "missing")
        self.assertEqual(
            self.matthew.knowledge_layers["primary"],
            "biblical_text",
        )

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.matthew.sources}
        self.assertGreaterEqual(len(self.matthew.claims), 36)
        self.assertGreaterEqual(len(self.matthew.interpretive_notes), 60)
        for claim in self.matthew.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.matthew.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_matthew_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.matthew.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.matthew.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.matthew.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.matthew.retrieval_metadata["common_questions"])
        self.assertTrue(self.matthew.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "jesus",
                "sermon-on-the-mount",
                "kingdom-theme",
                "messiah-theme",
                "torah",
                "peter",
                "crucifixion",
                "resurrection",
                "trinity",
            }.issubset(
                {
                    relationship.id
                    for relationship in self.matthew.related_objects
                }
            )
        )

    def test_retrieval_answers_matthew_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Matthew and does the Gospel identify its author?",
            "How is Papias related to the traditional authorship of Matthew?",
            "When was Matthew written and was it after the temple destruction?",
            "How does Matthew use Mark and other sources?",
            "Why does Matthew begin with fourteen-generation genealogy blocks?",
            "Why are Tamar Rahab Ruth and the wife of Uriah in Matthew's genealogy?",
            "How should Matthew's virgin conception and Isaiah 7:14 be read?",
            "Who were the magi and what was Matthew's star?",
            "Did Herod massacre Bethlehem's children in Matthew 2?",
            "What does he shall be called a Nazorean mean in Matthew?",
            "How does Jesus fulfill Torah rather than abolish it in Matthew 5?",
            "What are Matthew's antitheses you have heard but I say?",
            "What do Matthew's divorce exception clauses mean?",
            "What is the wording of the Lord's Prayer in Matthew?",
            "What does kingdom of heaven mean in Matthew?",
            "Why does Matthew organize five major discourses?",
            "What is the mission to the lost sheep of Israel in Matthew 10?",
            "Why does Matthew use parables and Isaiah's hardening language?",
            "Why does Jesus call the Canaanite woman a dog in Matthew 15?",
            "What do Peter the rock and the keys mean in Matthew 16?",
            "What do binding and loosing mean in Matthew 16 and 18?",
            "How should church discipline in Matthew 18 be used safely?",
            "What does the parable of the unforgiving servant teach?",
            "Who are eunuchs for the kingdom in Matthew 19?",
            "What does the ransom for many mean in Matthew 20?",
            "What happens in Matthew's triumphal entry and temple action?",
            "What do Matthew's woes against scribes and Pharisees mean?",
            "Does Matthew 23 justify antisemitism or calling Judaism hypocritical?",
            "What does this generation mean in Matthew 24?",
            "What are the abomination and tribulation in Matthew 24?",
            "How should the ten virgins talents and sheep and goats be read?",
            "What does Matthew say about Judas and covenant blood?",
            "Who is responsible for Jesus' death in Matthew's passion?",
            "Does his blood be on us justify deicide or collective Jewish guilt?",
            "What are the darkness earthquake and raised saints in Matthew 27?",
            "Why are women the first witnesses at Matthew's empty tomb?",
            "What is Matthew's guard-at-the-tomb story?",
            "Why do disciples worship and doubt in Matthew 28?",
            "What does the Great Commission mean in Matthew 28?",
            "Is Matthew 28:19's Father Son Spirit formula a textual variant?",
            "Does Matthew authorize coercive conversion colonial mission or forced baptism?",
            "Does Matthew's demon language justify stigmatizing mental illness?",
            "Does Matthew require victims to forgive or reconcile with abusers?",
            "Does Matthew support prosperity teaching or blaming poor people?",
            "Does Matthew predict modern dates wars nations or political parties?",
            "What are Codex Sinaiticus Vaticanus and early Matthew papyri?",
            "How do Matthew Mark and Luke relate in the Synoptic problem?",
            "How does Matthew receive Hebrew Bible and Septuagint texts?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "matthew")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.matthew.interpretive_notes]
        self.assertTrue(
            any(
                "internally anonymous" in note
                and "Papias" in note
                and "does not settle" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Peter's confession, rock, keys, binding, and loosing"
                in note
                and "remain disputed" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "'His blood be on us and on our children'" in note
                and "cannot authorize" in note
                and "collective Jewish guilt" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Great Commission" in note
                and "cannot authorize" in note
                and "coercive conversion" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "church discipline" in note
                and "cannot license" in note
                and "abuse" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_matthew_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-matthew.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("matthew").object
            self.assertEqual(sqlite_record.to_dict(), self.matthew.to_dict())
