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


class GalatiansRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.record = cls.library.retrieve_by_id("galatians").object

    def test_record_maps_major_voices_and_literary_units(self) -> None:
        self.assertTrue(
            {
                "Paul as named sender, autobiographical narrator, rebuking apostle, scriptural interpreter, and exhorter",
                "The assemblies of Galatia, addressed as siblings and as children; women and men, Jews and gentiles, enslaved and free people",
                "Barnabas, Titus, Cephas, James, John, the Jerusalem poor, and unnamed agitators or teachers",
                "Abraham, Sarah, Hagar, Isaac, the scriptural voice, the Messiah, the Spirit, and later interpreters",
            }.issubset(self.record.key_people)
        )
        self.assertTrue(
            {
                "Galatians 1:1-2:21: prescript, curse, divine call, autobiography, Jerusalem contacts, Antioch confrontation, and justification",
                "Galatians 3:1-4:31: Spirit, Abraham, promise, Torah, curse, seed, mediator, pedagogue, baptism, adoption, elemental powers, illness, and Hagar-Sarah allegory",
                "Galatians 5:1-6:10: freedom, circumcision, love, flesh and Spirit, fruit, restoration, burdens, teaching support, and sowing",
                "Galatians 6:11-18: large-letter autograph, circumcision polemic, cross, new creation, Israel of God, marks, and grace",
            }.issubset(self.record.structure)
        )

    def test_record_removes_placeholder_and_qualifies_context(self) -> None:
        record_values = {
            *self.record.authorship_positions,
            *self.record.key_people,
            *self.record.key_places,
            *self.record.key_events,
        }
        for placeholder in (
            "Timothy",
            "Rome",
            "Corinth",
            "Ephesus",
            "church formation",
            "pastoral instruction",
        ):
            self.assertNotIn(placeholder, record_values)
        self.assertFalse(self.record.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "Pauline authorship" in position
                and "scribal assistance" in position
                for position in self.record.authorship_positions
            )
        )
        self.assertTrue(
            {
                "Pauline letter with prescript, astonished rebuke, curse, autobiography, scriptural argument, exhortation, autograph, and benediction",
                "forensic and deliberative rhetoric, diatribe, exemplum, allegory, contrast, vice and virtue catalog, warning, and communal instruction",
                "scriptural quotation, lexical argument, irony, polemic, household and inheritance language, baptismal confession, and apocalyptic disclosure",
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
        self.assertGreaterEqual(len(self.record.claims), 34)
        self.assertGreaterEqual(len(self.record.interpretive_notes), 55)
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
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.record.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.record.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.record.retrieval_metadata["common_questions"])
        self.assertTrue(self.record.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "paul",
                "justification",
                "law-and-gospel",
                "faith",
                "spirit-theme",
                "abraham",
                "torah",
                "new-creation-theme",
            }.issubset(
                {relationship.id for relationship in self.record.related_objects}
            )
        )

    def test_retrieval_answers_book_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote Galatians and did Paul use a scribe?",
            "When and where was Galatians written?",
            "Was Galatians addressed to north or south Galatia?",
            "Who were the agitators or opponents in Galatians?",
            "According to the Epistle to the Galatians how does Paul's own autobiographical Jerusalem chronology compare with the Acts narrative?",
            "What Jerusalem visits does Paul describe in Galatians?",
            "Why was Titus not circumcised?",
            "What happened between Paul and Cephas at Antioch?",
            "What is justification in Galatians?",
            "Does pistis Christou mean faith in Christ or Christ's faithfulness?",
            "What are works of Torah in Galatians?",
            "How does Galatians use Abraham and promise?",
            "What does curse of the law mean in Galatians?",
            "What does seed mean in Galatians 3?",
            "Why was Torah added according to Galatians?",
            "What do angels and mediator mean in Galatians 3?",
            "What is the pedagogue in Galatians?",
            "What does neither Jew nor Greek mean in Galatians 3:28?",
            "Does Galatians 3:28 erase gender or ethnicity?",
            "According to Galatians 4 what do heir guardian redemption adoption Abba and Spirit mean?",
            "What are the elemental powers in Galatians?",
            "What illness and eye problem did Paul have in Galatians?",
            "What is the Hagar and Sarah allegory?",
            "Does Galatians support antisemitism or supersessionism?",
            "Does Galatians teach that Torah or Judaism is evil?",
            "What freedom does Galatians 5 describe?",
            "What does circumcision mean in Galatians?",
            "What are flesh and Spirit in Galatians?",
            "What is the fruit of the Spirit?",
            "How should Galatians 6 restoration avoid public shaming?",
            "What does bear one another's burdens mean?",
            "What does support the teacher mean in Galatians 6?",
            "What does sowing and reaping mean in Galatians?",
            "What is new creation in Galatians 6:15?",
            "Who is the Israel of God?",
            "What are Paul's marks in Galatians 6:17?",
            "Does Galatians justify slavery or worker exploitation?",
            "Does Galatians justify misogyny or anti LGBTQ coercion?",
            "Does Galatians authorize spiritual abuse or authoritarian leadership?",
            "Does Galatians glorify trauma disability or medical neglect?",
            "Does Galatians authorize nationalism conspiracy theories or partisan capture?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(f"Galatians {query}", limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "galatians")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.record.interpretive_notes]
        self.assertTrue(
            any(
                "Torah" in note
                and "antisemitism" in note
                and "supersessionism" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Galatians 3:28" in note
                and "gender erasure" in note
                and "anti-LGBTQ" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "restoration" in note
                and "public shaming" in note
                and "authoritarian" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "Paul's marks" in note
                and "medical neglect" in note
                and "trauma" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "freedom" in note
                and "slavery apologetics" in note
                and "worker exploitation" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-galatians.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("galatians").object
            self.assertEqual(sqlite_record.to_dict(), self.record.to_dict())


if __name__ == "__main__":
    unittest.main()
