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


class RomansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.romans = cls.library.retrieve_by_id("romans").object

    def test_romans_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "Paul as epistolary sender, Tertius as scribe, Phoebe as commended minister and patron, and the implied Roman audiences",
                "Jewish and gentile rhetorical interlocutors, the weak and strong, governing authorities, enslaved people, workers, petitioners, and later interpreters",
                "Adam, Abraham, Sarah, Isaac, Rebekah, Jacob, Esau, Moses, Pharaoh, Elijah, Israel, the nations, and scriptural voices",
                "Prisca, Aquila, Epaenetus, Mary, Andronicus, Junia, Ampliatus, Urbanus, Stachys, Apelles, Aristobulus's household, Herodion, Narcissus's household, Tryphaena, Tryphosa, Persis, Rufus, and his mother",
                "Asyncritus, Phlegon, Hermes, Patrobas, Hermas, Philologus, Julia, Nereus and his sister, Olympas, Timothy, Lucius, Jason, Sosipater, Gaius, Erastus, and Quartus",
            }.issubset(self.romans.key_people)
        )
        self.assertTrue(
            {
                "Romans 1:1-17: prescript, apostolic self-presentation, gospel, thanksgiving, travel wish, thesis, righteousness, and faith",
                "Romans 1:18-3:20: wrath, idolatry, desire, judgment, diatribe, conscience, Torah, circumcision, Jewish interlocutor, objections, and scriptural catena",
                "Romans 3:21-4:25: God's righteousness, faith or faithfulness, justification, boasting, Torah, Abraham, David, circumcision, promise, and resurrection",
                "Romans 5:1-8:39: peace, reconciliation, Adam and Christ, baptism, sin, grace, slavery metaphors, Torah, flesh, Spirit, adoption, suffering, creation, prayer, and hope",
                "Romans 9:1-11:36: lament for Israel, election, mercy, scriptural argument, hardening, remnant, Messiah and Torah, olive tree, all Israel, irrevocable gifts, and doxology",
                "Romans 12:1-15:13: embodied worship, gifts, mutuality, enemies, governing authorities, love, day and armor, conscience, food and days, weak and strong, welcome, and hope",
                "Romans 15:14-33: apostolic ministry, travel report, Jerusalem collection, Rome, Spain, danger, prayer, and peace",
                "Romans 16:1-27: Phoebe's recommendation, greetings, coworkers and house assemblies, warnings, Tertius's notice, final greetings, benediction, and mobile doxology",
            }.issubset(self.romans.structure)
        )

    def test_romans_removes_placeholder_and_qualifies_composition(self) -> None:
        record_values = {
            *self.romans.authorship_positions,
            *self.romans.key_people,
            *self.romans.key_places,
            *self.romans.key_events,
        }
        self.assertNotIn("Titus", record_values)
        self.assertNotIn("Ephesus", record_values)
        self.assertNotIn("church formation", record_values)
        self.assertNotIn("pastoral instruction", record_values)
        self.assertEqual(
            len(self.romans.key_events),
            len({event.casefold() for event in self.romans.key_events}),
        )
        self.assertFalse(self.romans.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "Paul" in position
                and "Tertius" in position
                and "scribe" in position
                for position in self.romans.authorship_positions
            )
        )
        self.assertTrue(
            {
                "Pauline letter with prescript, thanksgiving, body, travel report, recommendation, greetings, benediction, and doxology",
                "diatribe, rhetorical interlocutor, accusation, objection, response, question, analogy, personification, and scriptural catena",
                "Abraham exemplum, Adam-Christ comparison, typology, lament, paraenesis, gift list, household greeting, and warning",
            }.issubset(self.romans.genre)
        )

    def test_romans_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.romans.content_status, "draft")
        self.assertEqual(self.romans.review_status, "in_review")
        self.assertTrue(self.romans.human_review_required)
        self.assertIsNone(self.romans.last_reviewed)
        self.assertEqual(self.romans.section_status["human_review"], "missing")
        self.assertEqual(self.romans.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.romans.sources}
        self.assertGreaterEqual(len(self.romans.claims), 40)
        self.assertGreaterEqual(len(self.romans.interpretive_notes), 65)
        for claim in self.romans.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    claim.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.romans.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(
                    note.dispute_status,
                    CURRENT_DISPUTE_STATUS_VALUES,
                )
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_romans_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.romans.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 26)
        self.assertTrue(self.romans.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.romans.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.romans.retrieval_metadata["common_questions"])
        self.assertTrue(self.romans.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "paul",
                "abraham",
                "adam",
                "phoebe-of-cenchreae",
                "priscilla",
                "justification",
                "faith",
                "law-and-gospel",
                "spirit-theme",
                "resurrection",
            }.issubset(
                {relationship.id for relationship in self.romans.related_objects}
            )
        )

    def test_retrieval_answers_romans_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Romans and what role did Tertius hold?",
            "When and where was Romans written?",
            "Did Phoebe carry Romans and what does patron mean?",
            "Who were the Roman audiences and house churches?",
            "How did Claudius's expulsion affect Romans?",
            "Why did Paul write Romans and was Spain his goal?",
            "Was Romans assembled from multiple letters?",
            "Was Romans 16 originally sent somewhere else?",
            "Why does the doxology move in manuscripts of Romans?",
            "What are P10 P26 P27 P31 P40 P46 P61 in Romans?",
            "What do Sinaiticus Vaticanus Alexandrinus and Claromontanus show in Romans?",
            "What does the gospel reveal in Romans 1:16-17?",
            "What is the righteousness or justice of God in Romans?",
            "Does pistis Christou mean faith in Christ or Christ's faithfulness?",
            "What does the wrath of God mean in Romans 1?",
            "Does Romans 1 address modern sexual orientation?",
            "Does Romans 1 justify anti LGBTQ coercion or violence?",
            "Does creation make everyone naturally know God in Romans?",
            "What does Romans 2 teach about judgment and conscience?",
            "What are works of Torah or works of the law in Romans?",
            "What does universal sin mean in Romans 3?",
            "Does hilasterion in Romans 3:25 mean sacrifice or mercy seat?",
            "What does justification by faith mean in Romans?",
            "How does Paul interpret Abraham in Romans 4?",
            "Is Romans 5:1's peace verb indicative or exhortative?",
            "What does through one man sin entered mean in Romans 5?",
            "Does Romans teach inherited guilt or original sin?",
            "What does baptism into Christ's death mean in Romans 6?",
            "Do slavery metaphors in Romans justify slavery?",
            "Who is the I in Romans 7 and when is the speaker speaking?",
            "Is Torah sinful in Romans 7?",
            "What do flesh and Spirit mean in Romans 8?",
            "What does creation groaning mean in Romans 8?",
            "What does all things work together for good mean?",
            "Does Romans 8 predestination teach fatalism?",
            "Why does Paul lament for Israel in Romans 9?",
            "Do Jacob Esau Pharaoh and vessels teach individual predestination?",
            "Does Christ as telos of Torah mean termination or goal?",
            "What does the olive tree warning mean in Romans 11?",
            "What does all Israel will be saved mean?",
            "Are God's gifts and calling to Israel irrevocable?",
            "Does Romans 9-11 support supersessionism?",
            "What does living sacrifice mean in Romans 12?",
            "What are the gifts in Romans 12?",
            "What does feeding enemies and heaping coals mean?",
            "Must Christians obey every government because of Romans 13?",
            "Does Romans 13 authorize authoritarianism or nationalism?",
            "What does owing only love mean in Romans 13?",
            "What are the day and armor in Romans 13?",
            "Who are the weak and strong in Romans 14-15?",
            "Does Romans require vegetarianism or observing holy days?",
            "What does welcome one another mean in Romans?",
            "Why did Paul collect money for Jerusalem?",
            "Who was Phoebe and was she a deacon?",
            "Was Junia a woman and an apostle?",
            "What leadership role did Prisca hold in Romans?",
            "How many house assemblies appear in Romans 16?",
            "Who are the people greeted in Romans 16?",
            "Do Romans 16 warnings contradict the letter's welcome?",
            "Does Romans justify antisemitism or collective Jewish guilt?",
            "Does Romans portray Torah or Judaism as uniquely legalistic?",
            "Does Romans justify misogyny or erasing women leaders?",
            "Does Romans justify slavery or worker exploitation?",
            "Does Romans authorize forced conversion colonial mission or religious violence?",
            "Does Romans justify body shame disability stigma or mental health neglect?",
            "Does Romans glorify suffering victim blame or silence lament?",
            "Does Romans support prosperity extraction or poverty romanticization?",
            "Does Romans authorize partisan capture conspiracy theories or territorial claims?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "romans")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.romans.interpretive_notes]
        self.assertTrue(
            any(
                "pistis Christou" in note
                and "faith in Christ" in note
                and "Christ's faithfulness" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Romans 1:18-32" in note
                and "modern sexual orientation" in note
                and "cannot authorize" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Romans 9-11" in note
                and "supersessionism" in note
                and "irrevocable" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Romans 13" in note
                and "cannot authorize" in note
                and "authoritarian" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Phoebe" in note
                and "Junia" in note
                and "women" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "slavery metaphors" in note
                and "cannot justify" in note
                and "enslavement" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "suffering" in note
                and "victim blaming" in note
                and "mental-health" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_romans_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-romans.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("romans").object
            self.assertEqual(sqlite_record.to_dict(), self.romans.to_dict())
