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


class ActsRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.acts = cls.library.retrieve_by_id("acts").object

    def test_acts_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the narrator, implied author and Theophilus, the risen Jesus, the Spirit, angels, Scripture, and later interpreters",
                "the Eleven, Matthias, women disciples, Mary the mother of Jesus, Jesus' brothers, Peter, John, Stephen, Philip, and the Seven",
                "Jewish crowds, priests, Sadducees, Pharisees, synagogue groups, council members, diaspora communities, Samaritans, and the Ethiopian official",
                "Saul or Paul, Barnabas, Ananias, Sapphira, James, Cornelius, Herod Agrippa I, Lydia, Priscilla, Aquila, Apollos, Silas, Timothy, companions, and the we narrator",
                "named women, petitioners, sick and disabled people, people described through spirits, enslaved people, workers, Roman officials, soldiers, sailors, islanders, and households",
            }.issubset(self.acts.key_people)
        )
        self.assertTrue(
            {
                "Acts 1:1-2:47: prologue, restoration question, ascension, Matthias, Pentecost, Peter's speech, baptism, and community summary",
                "Acts 3:1-5:42: temple healing, speeches, property sharing, Ananias and Sapphira, signs, arrests, council, and Gamaliel",
                "Acts 6:1-8:40: the Seven, Stephen's witness and death, persecution, Samaria, Simon, and the Ethiopian official",
                "Acts 9:1-12:25: Saul's encounter and early witness, Peter's healings, Cornelius, Antioch, James's death, Peter's escape, and Herod's death",
                "Acts 13:1-15:35: Antioch commissioning, Cyprus, Pisidian Antioch, Iconium, Lystra, return, Jerusalem council, and decree",
                "Acts 15:36-19:20: divided teams, Macedonia, Lydia, Philippi, Thessalonica, Berea, Athens, Corinth, Apollos, and Ephesus",
                "Acts 19:21-21:16: Ephesian riot, travel, collection journey, Troas, Miletus farewell, Tyre, Caesarea, and Agabus",
                "Acts 21:17-26:32: Jerusalem meeting, temple arrest, defenses, plots, Roman custody, Felix, Festus, Agrippa, and appeal",
                "Acts 27:1-28:31: voyage, storm, shipwreck, Malta, healings, arrival in Rome, Jewish dialogue, and open-ended proclamation",
            }.issubset(self.acts.structure)
        )

    def test_acts_removes_placeholder_and_qualifies_authorship(self) -> None:
        record_values = {
            *self.acts.authorship_positions,
            *self.acts.key_events,
            *self.acts.interpretive_disputes,
        }
        self.assertNotIn("ministry", record_values)
        self.assertNotIn("crucifixion", record_values)
        self.assertNotIn("resurrection", record_values)
        self.assertNotIn("Synoptic relationships and authorship", record_values)
        self.assertEqual(
            len(self.acts.key_events),
            len({event.casefold() for event in self.acts.key_events}),
        )
        self.assertFalse(self.acts.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "internally anonymous" in position
                and "later" in position
                and "Luke" in position
                for position in self.acts.authorship_positions
            )
        )
        self.assertTrue(
            {
                "ancient historiographic narrative with a preface and sequel relationship to Luke",
                "summary, list, call, vision, dream, sign, healing, exorcism, prison escape, household scene, and martyrdom",
                "missionary sermon, defense speech, deliberative speech, council account, judicial hearing, farewell, prophecy, and miracle contest",
                "travel narrative, city episode, riot, sea voyage and shipwreck narrative, hospitality scene, and open ending",
            }.issubset(self.acts.genre)
        )

    def test_acts_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.acts.content_status, "draft")
        self.assertEqual(self.acts.review_status, "in_review")
        self.assertTrue(self.acts.human_review_required)
        self.assertIsNone(self.acts.last_reviewed)
        self.assertEqual(self.acts.section_status["human_review"], "missing")
        self.assertEqual(self.acts.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.acts.sources}
        self.assertGreaterEqual(len(self.acts.claims), 36)
        self.assertGreaterEqual(len(self.acts.interpretive_notes), 60)
        for claim in self.acts.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.acts.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_acts_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.acts.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.acts.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.acts.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.acts.retrieval_metadata["common_questions"])
        self.assertTrue(self.acts.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "jesus",
                "peter",
                "paul",
                "spirit-theme",
                "kingdom-theme",
                "temple-theme",
                "resurrection",
                "ascension",
                "luke",
            }.issubset(
                {relationship.id for relationship in self.acts.related_objects}
            )
        )

    def test_retrieval_answers_acts_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Acts and does Acts name its author?",
            "Was the author of Acts Luke the physician and companion of Paul?",
            "When and where was Acts written?",
            "How are Luke and Acts related and were they published together?",
            "Who was Theophilus in Acts?",
            "What are the we passages in Acts and do they prove eyewitness authorship?",
            "How historically reliable are Acts and its speeches?",
            "Why does Acts end without telling Paul's fate?",
            "What does restoring the kingdom to Israel mean in Acts 1?",
            "What does the ascension cloud mean in Acts 1?",
            "How and why was Matthias chosen?",
            "What happened at Pentecost in Acts 2?",
            "Were Pentecost languages human languages or ecstatic speech?",
            "How does Acts 2 use Joel and the Septuagint?",
            "Does Acts require Christians to hold all property in common?",
            "Why did Ananias and Sapphira die?",
            "Can leaders use Ananias and Sapphira to threaten donors?",
            "Who was Gamaliel and is his speech historical?",
            "Who were the Seven and were they deacons?",
            "Does Stephen's speech blame all Jewish people for Jesus' death?",
            "What happened to Philip in Samaria?",
            "Was the Ethiopian official a eunuch and how should race be discussed?",
            "Was Paul's Damascus experience a conversion or a call?",
            "Why do Paul's three call accounts differ?",
            "How does Acts 9 relate to Paul's Arabia visit in Galatians?",
            "What did Peter's vision and Cornelius mean?",
            "Does Peter's vision declare all foods clean?",
            "How did Herod Agrippa die in Acts and Josephus?",
            "What happened at Antioch and when were disciples called Christians?",
            "What happened to Bar-Jesus or Elymas?",
            "How does the Jerusalem council relate to Galatians 2?",
            "What was the apostolic decree and what are its textual variants?",
            "What leadership roles do Lydia Priscilla and other women have?",
            "Does household baptism in Acts prove infant baptism?",
            "How should spirits exorcism and mental health be discussed in Acts?",
            "What does Paul say at the Areopagus in Athens?",
            "How does Gallio help date Paul's time in Corinth?",
            "What happened in Ephesus with Artemis and the riot?",
            "Was Paul's final Jerusalem journey a collection journey?",
            "Did Agabus predict Paul's arrest incorrectly?",
            "Why did James ask Paul to join a Torah purification rite?",
            "Was Paul really a Roman citizen?",
            "What resurrection hope does Paul defend in his trials?",
            "How should Agrippa and Bernice be described?",
            "How historically plausible is the Acts 27 voyage and shipwreck?",
            "Does the Malta snakebite authorize snake handling?",
            "What happened to Paul after Acts 28?",
            "What are P45 P53 P74 Sinaiticus Vaticanus and Bezae in Acts?",
            "What is the Western text of Acts?",
            "Does Acts justify antisemitism supersessionism or collective Jewish guilt?",
            "Does Acts portray Torah circumcision or the temple as obsolete?",
            "Does Acts authorize colonial mission forced conversion or religious violence?",
            "Does Acts support Christian nationalism or territorial claims?",
            "Does Acts justify authoritarian church unity or clerical control?",
            "Does Acts justify financial coercion prosperity extraction or poverty romanticization?",
            "Does Acts justify slavery or worker exploitation?",
            "Does Acts justify misogyny or anti LGBTQ coercion?",
            "Does Acts justify disability stigma dangerous exorcism or medical neglect?",
            "Does Acts glorify martyrdom trauma prison abuse or victim blaming?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "acts")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.acts.interpretive_notes]
        self.assertTrue(
            any(
                "internally anonymous" in note
                and "we passages" in note
                and "do not by themselves prove" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Jewish" in note
                and "cannot authorize" in note
                and "collective Jewish guilt" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Ananias and Sapphira" in note
                and "cannot authorize" in note
                and "financial coercion" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Ethiopian official" in note
                and "racial" in note
                and "stereotype" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "snakebite" in note
                and "cannot authorize" in note
                and "snake handling" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Jerusalem council" in note
                and "Galatians 2" in note
                and "disputed" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "disability" in note
                and "medical care" in note
                and "exorcism" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_acts_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-acts.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("acts").object
            self.assertEqual(sqlite_record.to_dict(), self.acts.to_dict())
