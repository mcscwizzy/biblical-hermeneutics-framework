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


class MarkRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.mark = cls.library.retrieve_by_id("mark").object

    def test_mark_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the narrator, embedded Scripture, God's heavenly voice, angels, spirits, crowds, and later interpreters",
                "Jesus as Messiah, Son of God, Son of Man, teacher, healer, exorcist, servant, suffering and vindicated figure, and king",
                "John the Baptist, Satan, disciples and the Twelve, Peter, James, John, Andrew, women followers, Jesus' family, children, and petitioners",
                "Jairus and his daughter, the hemorrhaging woman, the Syrophoenician woman and her daughter, the deaf man, blind people, and Bartimaeus",
                "scribes, Pharisees, Herodians, Sadducees, chief priests, elders, Herod Antipas and his household, tax collectors, sinners, wealthy people, laborers, and tenants",
                "Judas, the high priest, Pilate, Barabbas, soldiers, Simon of Cyrene, the centurion, Joseph of Arimathea, Mary Magdalene, Mary mother of James, Salome, and the young man at the tomb",
            }.issubset(self.mark.key_people)
        )
        self.assertTrue(
            {
                "Mark 1:1-3:6: scriptural prologue, John, baptism, temptation, Galilean proclamation, calls, healings, exorcisms, and controversies",
                "Mark 3:7-6:6: crowds, Twelve, family and Beelzebul dispute, parables, sea crossing, Gerasene episode, Jairus and hemorrhaging woman, and Nazareth rejection",
                "Mark 6:7-8:21: mission, John's death, two feedings, sea crossings, purity controversy, Syrophoenician woman, deaf man, and disputed leaven",
                "Mark 8:22-10:52: two-stage sight, Peter's confession, three passion predictions, transfiguration, teaching on discipleship, children, wealth, service, and Bartimaeus",
                "Mark 11:1-13:37: Jerusalem entry, fig tree and temple action, controversies, widow, temple discourse, and watchfulness",
                "Mark 14:1-15:47: anointing, meal, Gethsemane, arrest, hearings, crucifixion, death, women witnesses, and burial",
                "Mark 16:1-8: women at the tomb, the young man's announcement, promised Galilee, fear, and the earliest recoverable ending",
            }.issubset(self.mark.structure)
        )

    def test_mark_removes_inherited_placeholder_and_qualifies_ending(self) -> None:
        forbidden = {
            "Traditional evangelist or Lukan authorship",
            "Acts is often read as slightly later than Luke",
            "Paul",
        }
        record_values = {
            *self.mark.authorship_positions,
            *self.mark.date_ranges,
            *self.mark.key_people,
        }
        self.assertTrue(forbidden.isdisjoint(record_values))
        self.assertEqual(
            len(self.mark.key_events),
            len({event.casefold() for event in self.mark.key_events}),
        )
        self.assertIn("Mark 16:1-8", self.mark.summary)
        self.assertIn("longer ending", self.mark.summary)
        self.assertTrue(
            {
                "ancient biography and Gospel narrative",
                "scriptural incipit, proclamation, baptism, temptation, call story, healing, exorcism, controversy, and pronouncement",
                "aphorism, legal interpretation, parable, allegorical explanation, miracle story, sea story, feeding, recognition, and confession",
                "passion prediction, transfiguration, travel narrative, prophetic sign action, and apocalyptic discourse",
                "anointing, meal, passion narrative, hearing, trial, mockery, lament, death, burial, and empty-tomb narrative",
            }.issubset(self.mark.genre)
        )

    def test_mark_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.mark.content_status, "draft")
        self.assertEqual(self.mark.review_status, "in_review")
        self.assertTrue(self.mark.human_review_required)
        self.assertIsNone(self.mark.last_reviewed)
        self.assertEqual(self.mark.section_status["human_review"], "missing")
        self.assertEqual(self.mark.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.mark.sources}
        self.assertGreaterEqual(len(self.mark.claims), 36)
        self.assertGreaterEqual(len(self.mark.interpretive_notes), 60)
        for claim in self.mark.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.mark.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_mark_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.mark.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.mark.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.mark.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.mark.retrieval_metadata["common_questions"])
        self.assertTrue(self.mark.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "jesus",
                "john-the-baptist",
                "peter",
                "kingdom-theme",
                "messiah-theme",
                "crucifixion",
                "resurrection",
                "theology-of-the-cross",
            }.issubset(
                {relationship.id for relationship in self.mark.related_objects}
            )
        )

    def test_retrieval_answers_mark_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Mark and does the Gospel name its author?",
            "What does Papias say about Mark and Peter?",
            "When was Mark written and was it before or after the temple destruction?",
            "Why do scholars usually think Mark was the earliest Gospel?",
            "Was Mark written in Rome Syria or Galilee?",
            "What does the opening title Son of God variant in Mark 1:1 mean?",
            "Why does Mark combine Isaiah and Malachi in its opening citation?",
            "What is the messianic secret in Mark?",
            "What is the unforgivable eternal sin in Mark 3?",
            "Why does Mark use parables and hardening language?",
            "What does Legion and the pigs mean in Mark 5?",
            "Why does Mark sandwich Jairus's daughter around the hemorrhaging woman?",
            "Why are there two feeding stories in Mark?",
            "Does Mark 7:19 declare all foods clean?",
            "Why does Jesus call the Syrophoenician woman a dog in Mark 7?",
            "What do Talitha koum and Ephphatha mean in Mark?",
            "Why does Jesus heal a blind man in two stages in Mark 8?",
            "What are Mark's three passion predictions?",
            "What does the ransom for many mean in Mark 10:45?",
            "What happens in Mark's triumphal entry fig tree and temple action?",
            "Does the widow's offering in Mark 12 praise sacrificial giving or expose exploitation?",
            "What does this generation mean in Mark 13?",
            "What are the abomination and tribulation in Mark 13?",
            "Who is responsible for Jesus' death in Mark's passion?",
            "What do Jesus' cry of abandonment and the torn curtain mean in Mark 15?",
            "What does the centurion mean by Son of God in Mark 15?",
            "Why do the women flee in fear and silence in Mark 16:8?",
            "Does the earliest recoverable text of Mark end at 16:8?",
            "What are the shorter and longer endings of Mark?",
            "What is the Freer Logion in Codex Washingtonianus?",
            "Does Mark 16 require snake handling or drinking poison?",
            "Does Mark's demon language justify stigmatizing mental illness?",
            "Does Mark justify antisemitism or portray Judaism as legalistic?",
            "Does Mark authorize colonial mission coercion or religious violence?",
            "Does Mark romanticize poverty or support prosperity teaching?",
            "What are Codex Sinaiticus Vaticanus and early Mark manuscripts?",
            "Why is Mark usually placed first when comparing Matthew Mark and Luke?",
            "How does Mark receive Hebrew Bible and Septuagint texts?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "mark")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.mark.interpretive_notes]
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
                "earliest recoverable text ends at 16:8" in note
                and "longer ending" in note
                and "later" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "snake handling" in note
                and "cannot require" in note
                and "medical care" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Jewish leaders" in note
                and "cannot authorize" in note
                and "collective Jewish guilt" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Syrophoenician woman" in note
                and "cannot authorize" in note
                and "racism" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_mark_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-mark.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("mark").object
            self.assertEqual(sqlite_record.to_dict(), self.mark.to_dict())
