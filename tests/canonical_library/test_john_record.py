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


class JohnRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path("framework/canonical_library")
        cls.library = CanonicalLibrary(root=cls.root).load()
        cls.john = cls.library.retrieve_by_id("john").object

    def test_john_maps_major_voices_and_practical_units(self) -> None:
        self.assertTrue(
            {
                "the narrator and implied author, Logos and divine voices, Scripture, witnesses, crowds, and later interpreters",
                "John the Baptist, Jesus, Jesus' mother and brothers, Andrew, Simon Peter, Philip, Nathanael, the Twelve, Judas Iscariot, Thomas, and the beloved disciple",
                "Nicodemus, the Samaritan woman and villagers, royal official and household, disabled man at Bethesda, people fed, man born blind and his parents, Mary, Martha, Lazarus, and visiting Greeks",
                "Mary Magdalene, other disciples, petitioners, people described through illness or disability, servants, enslaved people, and laborers",
                "Pharisees, chief priests, temple authorities, synagogue communities, Caiaphas, Annas, Pilate, soldiers, Joseph of Arimathea, and later readers",
            }.issubset(self.john.key_people)
        )
        self.assertTrue(
            {
                "John 1:1-18: Logos prologue, creation, life, light, witness, incarnation, glory, grace, truth, and God-language",
                "John 1:19-2:12: Baptist testimony, first disciples, Nathanael, and Cana sign",
                "John 2:13-4:54: temple action, Nicodemus, Baptist-Jesus relation, Samaritan woman and village, and royal official",
                "John 5:1-10:42: Bethesda, Sabbath and Son discourse, feeding, sea crossing, bread discourse, festivals, contested testimony, man born blind, and shepherd speech",
                "John 11:1-12:50: Lazarus, council, anointing, entry, Greeks, hour, glory, and unbelief",
                "John 13:1-17:26: footwashing, meal, Judas, Peter, farewell discourses, Paraclete, vine, world hostility, and prayer",
                "John 18:1-19:42: arrest, Annas and Caiaphas, Peter, Pilate, kingship, crucifixion, death, witness, and burial",
                "John 20:1-31: empty tomb, Mary Magdalene, disciples, Thomas, commissioning, signs, and purpose statement",
                "John 21:1-25: Sea of Tiberias appearance, catch and meal, Peter, beloved disciple, testimony, and epilogue",
            }.issubset(self.john.structure)
        )

    def test_john_removes_placeholder_and_qualifies_authorship(self) -> None:
        record_values = {
            *self.john.authorship_positions,
            *self.john.date_ranges,
            *self.john.key_people,
        }
        self.assertNotIn("Paul", record_values)
        self.assertNotIn("Traditional evangelist or Lukan authorship", record_values)
        self.assertNotIn(
            "Acts is often read as slightly later than Luke",
            record_values,
        )
        self.assertEqual(
            len(self.john.key_events),
            len({event.casefold() for event in self.john.key_events}),
        )
        self.assertFalse(self.john.context_applicability["ancient_near_east"])
        self.assertTrue(
            any(
                "internally anonymous" in position
                and "later" in position
                and "John" in position
                for position in self.john.authorship_positions
            )
        )
        self.assertTrue(
            {
                "Gospel narrative and ancient biography with poetic or hymnic prologue",
                "witness scene, call, sign, pronouncement, symbolic action, dialogue, misunderstanding, irony, controversy, and legal or festival discourse",
                "healing, feeding, sea scene, shepherd speech, resurrection narrative, anointing, footwashing, farewell discourse, and prayer",
                "passion, hearing, trial, mockery, death, burial, empty-tomb, recognition, appearance, commissioning, purpose statement, and epilogue",
            }.issubset(self.john.genre)
        )

    def test_john_is_an_honest_draft_awaiting_human_review(self) -> None:
        self.assertEqual(self.john.content_status, "draft")
        self.assertEqual(self.john.review_status, "in_review")
        self.assertTrue(self.john.human_review_required)
        self.assertIsNone(self.john.last_reviewed)
        self.assertEqual(self.john.section_status["human_review"], "missing")
        self.assertEqual(self.john.knowledge_layers["primary"], "biblical_text")

    def test_claims_and_notes_use_current_evidence_taxonomy(self) -> None:
        source_ids = {source.id for source in self.john.sources}
        self.assertGreaterEqual(len(self.john.claims), 36)
        self.assertGreaterEqual(len(self.john.interpretive_notes), 60)
        for claim in self.john.claims:
            with self.subTest(claim=claim.id):
                self.assertIn(claim.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(claim.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(claim.rationale.strip())
                self.assertTrue(claim.source_ids)
                self.assertTrue(set(claim.source_ids).issubset(source_ids))
        for index, note in enumerate(self.john.interpretive_notes):
            with self.subTest(note=index):
                self.assertIn(note.certainty, CURRENT_CERTAINTY_VALUES)
                self.assertIn(note.dispute_status, CURRENT_DISPUTE_STATUS_VALUES)
                self.assertTrue(note.rationale.strip())
                self.assertTrue(note.sources)
                self.assertTrue(set(note.sources).issubset(source_ids))

    def test_john_has_external_sources_and_reviewer_metadata(self) -> None:
        external = [
            source
            for source in self.john.sources
            if source.source_type != "scripture" and source.url
        ]
        self.assertGreaterEqual(len(external), 24)
        self.assertTrue(self.john.hermeneutical_lens["book_context"])
        self.assertTrue(
            self.john.hermeneutical_lens["common_misinterpretations"]
        )
        self.assertTrue(self.john.retrieval_metadata["common_questions"])
        self.assertTrue(self.john.retrieval_metadata["semantic_keywords"])
        self.assertTrue(
            {
                "jesus",
                "john-the-baptist",
                "peter",
                "mary-magdalene",
                "nicodemus",
                "thomas",
                "lazarus",
                "spirit-theme",
                "temple-theme",
                "logos",
                "crucifixion",
                "resurrection",
            }.issubset(
                {relationship.id for relationship in self.john.related_objects}
            )
        )

    def test_retrieval_answers_john_specific_questions(self) -> None:
        service = CKLRetrievalService(library=self.library)
        queries = [
            "Who wrote John and does the Gospel name its author?",
            "Is the beloved disciple John son of Zebedee?",
            "When and where was John written?",
            "What is the Johannine community and synagogue expulsion theory?",
            "How is John related to Matthew Mark and Luke?",
            "What does the Logos mean in John 1?",
            "Does John 1:1 call the Word God?",
            "Is John 1:18 only begotten God or only Son?",
            "What does Lamb of God mean in John?",
            "Why does Jesus turn water into wine at Cana?",
            "Why does John place the temple action early?",
            "Does born again in John 3 mean born from above?",
            "What does John 3:16 mean and who is speaking?",
            "What is the relationship between John the Baptist and Jesus in John 3?",
            "What does the Samaritan woman and her five husbands mean?",
            "What does salvation is from the Jews mean in John 4:22?",
            "Is the angel stirring the water in John 5:4 original?",
            "Does John 5 teach Jesus is equal with God?",
            "What does eating flesh and drinking blood mean in John 6?",
            "What are John's I am sayings?",
            "Is the woman caught in adultery in the earliest manuscripts of John?",
            "What does before Abraham was I am mean in John 8?",
            "Was the man born blind because of sin?",
            "Does John justify disability stigma or medical neglect?",
            "What does being put out of the synagogue mean in John?",
            "What does I and the Father are one mean in John 10:30?",
            "Why does Jesus weep and raise Lazarus?",
            "What does Caiaphas prophesy in John 11?",
            "What does drawing all people mean in John 12:32?",
            "Why does Jesus wash the disciples' feet?",
            "What is the new commandment in John?",
            "What are the many rooms in the Father's house?",
            "Does John 14:6 justify coercion or religious violence?",
            "Who or what is the Paraclete in John?",
            "What does the Father is greater than I mean in John 14:28?",
            "What does the vine and branches mean in John 15?",
            "What does Jesus pray for in John 17?",
            "Who is responsible for Jesus' death in John's passion?",
            "Why does John describe Jesus as king before Pilate?",
            "What do blood and water from Jesus' side mean?",
            "Who is the beloved disciple at the cross and tomb?",
            "What happens when Mary Magdalene meets the risen Jesus?",
            "What does Thomas mean by my Lord and my God?",
            "What does forgiving and retaining sins mean in John 20:23?",
            "Was John 21 added later?",
            "What do Peter and the beloved disciple mean in John 21?",
            "What are P52 P66 P75 Sinaiticus Vaticanus and Bezae in John?",
            "Does John's language about the Jews justify antisemitism or collective Jewish guilt?",
            "Does John portray Judaism Torah or festivals as obsolete?",
            "Does John authorize colonial mission or forced conversion?",
            "Does John condemn LGBTQ people?",
            "Does John's light and darkness language justify racial prejudice?",
        ]
        for query in queries:
            with self.subTest(query=query):
                response = service.search(query, limit=5)
                self.assertTrue(response.results)
                self.assertEqual(response.results[0].id, "john")

    def test_difficult_interpretations_remain_explicitly_qualified(self) -> None:
        notes = [note.note for note in self.john.interpretive_notes]
        self.assertTrue(
            any(
                "internally anonymous" in note
                and "beloved disciple" in note
                and "does not identify" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "hoi Ioudaioi" in note
                and "cannot authorize" in note
                and "collective Jewish guilt" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "John 7:53-8:11" in note
                and "earliest" in note
                and "later" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "John 14:6" in note
                and "cannot authorize" in note
                and "coercive conversion" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "P52" in note
                and "fragment" in note
                and "does not prove" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "John 21" in note
                and "epilogue" in note
                and "disputed" in note
                for note in notes
            )
        )
        self.assertTrue(
            any(
                "disability" in note
                and "sin" in note
                and "medical care" in note
                for note in notes
            )
        )

    def test_sqlite_preserves_john_claims_and_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "phase-5-john.sqlite"
            build_database(self.root, database)
            sqlite_library = SQLiteCanonicalLibrary.from_path(
                database,
                root=self.root,
            )
            sqlite_record = sqlite_library.retrieve_by_id("john").object
            self.assertEqual(sqlite_record.to_dict(), self.john.to_dict())
