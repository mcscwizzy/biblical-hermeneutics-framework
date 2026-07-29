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


class LukeRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.luke = cls.library.retrieve_by_id("luke").object

    def test_luke_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the narrator, implied author and Theophilus, embedded Scripture, divine voices, angels, and later interpreters",
                "Zechariah, Elizabeth, Mary, Joseph, shepherds, Simeon, Anna, John the Baptist, Jesus, the Spirit, and Satan",
                "disciples and the Twelve, Peter, James, John, women followers, Mary and Martha, Joanna, Susanna, children, poor and wealthy people, and petitioners",
                "disabled and sick people, people described through spirits, Samaritans, tax collectors and sinners, Pharisees, scribes, lawyers, and synagogue and temple figures",
                "Herod Antipas, Judas, high-priestly leaders, Pilate, soldiers, criminals, the centurion, Joseph of Arimathea, women at the tomb, Cleopas, and the Emmaus companion",
            }.issubset(self.luke.key_people)
        )
        self.assertTrue(
            {
                "Luke 1:1-4: ancient preface, predecessors, eyewitness tradition, investigation, order, Theophilus, and assurance",
                "Luke 1:5-2:52: paired annunciations and births, songs, shepherds, temple scenes, Simeon, Anna, and the child Jesus",
                "Luke 3:1-4:13: John, baptism, genealogy, and temptation",
                "Luke 4:14-9:50: Nazareth program, Galilean proclamation, calls, healings, exorcisms, controversies, meals, parables, mission, feeding, confession, and transfiguration",
                "Luke 9:51-19:27: journey toward Jerusalem, discipleship, prayer, meals, reversals, Samaritans, wealth, and distinctive parables",
                "Luke 19:28-21:38: Jerusalem entry, lament, temple action, controversies, widow, and temple discourse",
                "Luke 22:1-23:56: covenant meal, Gethsemane, arrest, hearings, crucifixion, death, women witnesses, and burial",
                "Luke 24:1-53: empty tomb, Emmaus recognition, Jerusalem appearance, commission, blessing, and textually qualified ascension",
            }.issubset(self.luke.structure)
        )

    def test_luke_removes_placeholder_and_qualifies_authorship(self) -> None:
        record_values = {
            *self.luke.authorship_positions,
            *self.luke.date_ranges,
            *self.luke.key_people,
        }
        self.assertNotIn("Paul", record_values)
        self.assertNotIn("Acts is often read as slightly later than Luke", record_values)
        self.assertEqual(
            len(self.luke.key_events),
            len({event.casefold() for event in self.luke.key_events}),
        )
        self.assertFalse(self.luke.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "internally anonymous" in position
                and "later" in position
                and "Luke" in position
                for position in self.luke.authorship_positions
            )
        )
        self.assertTrue(
            {
                "Gospel narrative and ancient biography with an ancient historiographic preface",
                "annunciation, birth and childhood narrative, hymn, genealogy, proclamation, temptation, synagogue scene, call, healing, exorcism, and controversy",
                "pronouncement, beatitude and woe, prayer, meal, aphorism, legal interpretation, parable, miracle, travel narrative, and prophetic sign",
                "apocalyptic discourse, anointing, covenant meal, passion, hearing, trial, lament, mockery, death, burial, empty-tomb, recognition, appearance, commissioning, and ascension narrative",
            }.issubset(self.luke.genre)
        )

    def test_luke_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.luke.content_status, "draft")
        self.assertEqual(self.luke.review_status, "in_review")
        self.assertTrue(self.luke.human_review_required)
        self.assertIsNone(self.luke.last_reviewed)
        self.assertEqual(self.luke.section_status["human_review"], "missing")
        self.assertEqual(self.luke.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.luke.sources}
        self.assertGreaterEqual(len(self.luke.claims), 36)
        self.assertGreaterEqual(len(self.luke.interpretive_notes), 60)
        for claim in self.luke.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.luke.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_luke_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.luke.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.luke.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.luke.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.luke.retrieval_metadata["common_questions"])
        self.assertTrue(self.luke.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "jesus",
                "mary-mother-of-jesus",
                "john-the-baptist",
                "peter",
                "spirit-theme",
                "kingdom-theme",
                "crucifixion",
                "resurrection",
                "ascension",
                "acts",
            }.issubset(
                {relationship.id for relationship in self.luke.related_objects}
            )
        )

    def test_retrieval_answers_luke_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Luke and does the Gospel name its author?",
            "Was Luke the physician and companion of Paul?",
            "When and where was Luke written?",
            "How are Luke and Acts related and are they one unified work?",
            "What does Luke's prologue say about eyewitnesses predecessors and order?",
            "How does Luke use Mark and other sources?",
            "What is the historical problem with Quirinius and the census in Luke 2?",
            "Was the Magnificat spoken by Mary or Elizabeth?",
            "What does peace among people of goodwill mean in Luke 2:14?",
            "Why does Luke's genealogy differ from Matthew's?",
            "What is the textual variant in Jesus' baptismal voice in Luke 3:22?",
            "What do Isaiah 61 Jubilee and Elijah Elisha mean in Luke 4?",
            "Are Luke's beatitudes about the materially poor?",
            "What does love your enemies mean in Luke?",
            "How should the sinful woman in Luke 7 be read without sexual shaming?",
            "What does the Good Samaritan mean and does it stereotype Samaritans?",
            "What does Mary and Martha mean in Luke 10?",
            "What is Luke's version of the Lord's Prayer?",
            "What is the unforgivable sin in Luke 12?",
            "What does the parable of the rich fool mean?",
            "What do the prodigal son and elder brother mean in Luke 15?",
            "What does the unjust steward mean in Luke 16?",
            "Is the rich man and Lazarus a map of the afterlife?",
            "What do the ten lepers and the Samaritan mean in Luke 17?",
            "What does the widow and unjust judge mean in Luke 18?",
            "What does the Pharisee and tax collector mean in Luke 18?",
            "What does Zacchaeus mean for wealth and restitution?",
            "What do Luke's parable of the minas and benefactor critique mean?",
            "Does Luke's widow story require poor people to give everything?",
            "What does this generation mean in Luke 21?",
            "Why does Jesus tell the disciples to buy swords in Luke 22?",
            "Are Luke 22:19b-20 and the covenant cup original?",
            "Are the angel and bloody sweat in Luke 22:43-44 original?",
            "Who is responsible for Jesus' death in Luke's passion?",
            "Is Father forgive them in Luke 23:34 original?",
            "What does Jesus promise the repentant criminal?",
            "What do the darkness curtain centurion and women mean in Luke 23?",
            "What happens on the Emmaus road in Luke 24?",
            "How physical is Jesus' resurrection appearance in Luke 24?",
            "Does Luke 24 narrate the ascension and what are its textual variants?",
            "What are P45 P75 Sinaiticus Vaticanus and Bezae in Luke?",
            "What is Marcion's Gospel and how is it related to Luke?",
            "Does Luke justify antisemitism or collective Jewish guilt?",
            "Does Luke romanticize poverty or support prosperity teaching?",
            "Does Luke's demon language justify mental health stigma or dangerous exorcism?",
            "Does Luke authorize colonial mission coercion or religious violence?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "luke")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.luke.interpretive_notes]
        self.assertTrue(
            any(
                "internally anonymous" in note
                and "physician" in note
                and "does not prove" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Quirinius" in note
                and "chronological problem" in note
                and "not resolve" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Father, forgive them" in note
                and "textual variant" in note
                and "collective Jewish guilt" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Luke 24:51-52" in note
                and "textual variation" in note
                and "Acts 1" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Marcion" in note
                and "disputed" in note
                and "mutilation" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "buy swords" in note
                and "cannot authorize" in note
                and "religious violence" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_luke_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-luke.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("luke").object
            self.assertEqual(sqlite_record.to_dict(), self.luke.to_dict())
