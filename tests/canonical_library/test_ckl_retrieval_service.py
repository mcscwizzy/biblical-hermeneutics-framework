from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.retrieval import CKLRetrievalService
from framework.canonical_library.retrieval.ranker import coherent_evidence_coverage

from .helpers import make_object, write_library


class CKLRetrievalServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = CanonicalLibrary.load_default()
        cls.service = CKLRetrievalService(library=cls.library)

    def test_search_returns_structured_response(self) -> None:
        response = self.service.search("Joshua 24")
        payload = response.to_dict()

        self.assertEqual(payload["query"], "Joshua 24")
        self.assertEqual(payload["normalized_query"], "Joshua 24")
        self.assertIn("analysis", payload)
        self.assertIn("results", payload)
        self.assertIn("stats", payload)
        self.assertGreater(len(payload["results"]), 0)
        self.assertNotIn("score_details", payload["results"][0])

    def test_shechem_ranks_first_for_joshua_24(self) -> None:
        response = self.service.search("Why is Shechem important in Joshua 24?")

        self.assertGreater(len(response.results), 0)
        self.assertEqual(response.results[0].id, "shechem")
        self.assertGreaterEqual(response.results[0].score, 0.9)
        self.assertGreaterEqual(len(response.results[0].matched_terms), 2)
        self.assertGreaterEqual(len(response.results[0].scripture_references), 1)
        self.assertEqual(response.analysis.intent, "explanation")
        self.assertEqual(len(response.analysis.scripture_references), 1)
        self.assertEqual(response.analysis.scripture_references[0].book, "Joshua")
        self.assertEqual(response.analysis.scripture_references[0].start_chapter, 24)

    def test_covenant_renewal_prioritizes_direct_entries(self) -> None:
        response = self.service.search("covenant renewal")
        ids = [result.id for result in response.results]

        self.assertIn("new-covenant", ids[:3])
        self.assertIn("covenant-theme", ids)
        self.assertNotIn("resurrection", ids)
        self.assertTrue(all(result.score >= 0.45 for result in response.results))

    def test_search_uses_deterministic_query_facets(self) -> None:
        response = self.service.search("Why did Joshua renew the covenant at Shechem?")

        self.assertIn("people", response.analysis.categories)
        self.assertIn("places", response.analysis.categories)
        self.assertIn("themes", response.analysis.categories)
        self.assertIn("events", response.analysis.categories)
        self.assertIn("theological concepts", response.analysis.categories)
        self.assertIn("person", response.analysis.object_categories)
        self.assertIn("place", response.analysis.object_categories)
        self.assertIn("theme", response.analysis.object_categories)
        self.assertIn("event", response.analysis.object_categories)

    def test_search_uses_new_context_layer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_library(
                root,
                [
                    make_object(
                        "context-note",
                        "faq",
                        "Context Note",
                        ["context note"],
                        summary="A note about layered context.",
                        hebraic_worldview="Covenant identity and communal memory.",
                        second_temple_context="Second Temple Judaism shaped the background.",
                        canonical_context="This fits the broader covenant storyline.",
                        later_christian_reception="Later Christian interpreters connected it to the church.",
                        context_applicability={
                            "historical": False,
                            "ancient_near_east": False,
                            "hebraic_worldview": True,
                            "second_temple": True,
                            "canonical": True,
                            "later_christian_reception": True,
                        },
                        importance=10,
                    ),
                ],
            )
            service = CKLRetrievalService(library=CanonicalLibrary(root=root))

            hebraic_response = service.search("communal memory")
            second_temple_response = service.search("Second Temple Judaism")
            reception_response = service.search("later Christian interpreters")

        self.assertEqual(hebraic_response.results[0].id, "context-note")
        self.assertEqual(second_temple_response.results[0].id, "context-note")
        self.assertEqual(reception_response.results[0].id, "context-note")

    def test_search_exposes_and_prefers_lower_inference_knowledge_layers_on_ties(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_library(
                root,
                [
                    make_object(
                        "text-observation",
                        "theme",
                        "Text Observation",
                        ["text observation"],
                        summary="Sharedlayerterm evidence.",
                        knowledge_layers={
                            "primary": "biblical_text",
                            "secondary": [],
                        },
                    ),
                    make_object(
                        "systematic-synthesis",
                        "theology",
                        "Systematic Synthesis",
                        ["systematic synthesis"],
                        summary="Sharedlayerterm evidence.",
                        knowledge_layers={
                            "primary": "systematic_theology",
                            "secondary": [],
                        },
                    ),
                ],
            )
            service = CKLRetrievalService(
                library=CanonicalLibrary(root=root),
                relevance_threshold=0.1,
            )
            response = service.search("sharedlayerterm", min_score=0.1)

        self.assertEqual(response.results[0].id, "text-observation")
        self.assertEqual(response.results[0].knowledge_layer, "biblical_text")
        self.assertEqual(
            response.results[0].to_dict()["knowledge_layer"],
            "biblical_text",
        )

    def test_search_supports_standard_scripture_abbreviations(self) -> None:
        response = self.service.search("Gen 1:1")

        self.assertGreater(len(response.results), 0)
        self.assertGreaterEqual(len(response.analysis.scripture_references), 1)
        self.assertEqual(response.analysis.scripture_references[0].book, "Genesis")
        self.assertIn("books", response.analysis.categories)
        self.assertTrue(any(result.id == "genesis" for result in response.results[:3]))

    def test_explicitly_named_book_outranks_a_complete_place_topic(self) -> None:
        response = self.service.search(
            "Galatians Was Galatians addressed to north or south Galatia?"
        )

        self.assertEqual(response.results[0].id, "galatians")

    def test_explicit_book_and_verse_outranks_a_homonymous_place(self) -> None:
        response = self.service.search(
            "Philippians What does politeuesthe mean in Philippians 1:27?"
        )

        self.assertTrue(
            any(
                reference.book == "Philippians"
                and reference.start_chapter == 1
                and reference.start_verse == 27
                for reference in response.analysis.scripture_references
            )
        )
        self.assertEqual(response.results[0].id, "philippians")

    def test_search_prioritizes_joseph_bones_over_generic_significance_entries(self) -> None:
        response = self.service.search("What is the significance of Joseph's bones?")
        ids = [result.id for result in response.results]

        self.assertIn("shechem", ids[:3])
        self.assertNotIn("what-is-a-parable", ids)

    def test_coherent_passage_evidence_outranks_scattered_overlap(self) -> None:
        response = self.service.search(
            "What does one body and many members mean?",
            debug=True,
        )
        ids = [result.id for result in response.results]

        self.assertEqual(
            ids[0],
            "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order",
        )
        self.assertIn("1-corinthians", ids)
        signal = next(
            signal
            for signal in response.results[0].score_details
            if signal.name == "keyword_match"
        )
        self.assertIn("single-unit query-term coverage: 1.00", signal.note or "")
        evidence_signal = next(
            signal
            for signal in response.results[0].score_details
            if signal.name == "coherent_evidence_match"
        )
        self.assertEqual(evidence_signal.matched_terms, ["one", "body", "many", "member"])
        self.assertEqual(evidence_signal.value, 16.0)

    def test_interpretive_caveats_do_not_create_false_coherent_matches(self) -> None:
        query = "What were the Corinthian factions and slogans?"
        analysis = self.service.search(query).analysis
        faction_record = self.service.index.entries_by_id[
            "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
        ]
        ritual_record = self.service.index.entries_by_id[
            "ritual-purity-and-communal-holiness"
        ]

        self.assertEqual(coherent_evidence_coverage(analysis, faction_record), 1.0)
        self.assertLess(coherent_evidence_coverage(analysis, ritual_record), 1.0)

    def test_related_subject_alias_does_not_displace_direct_passage_evidence(self) -> None:
        response = self.service.search(
            "What does Paul mean by judging nothing before the time?",
            debug=True,
        )

        self.assertEqual(response.results[0].id, "1-corinthians")

    def test_scattered_baptism_and_creation_terms_do_not_form_a_coherent_signal(self) -> None:
        response = self.service.search(
            "What does baptism have to do with new creation?",
            debug=True,
        )
        result = next(
            result
            for result in response.results
            if result.id
            == "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead"
        )

        self.assertFalse(
            any(signal.name == "coherent_evidence_match" for signal in result.score_details)
        )

    def test_search_filters_irrelevant_kingdom_noise(self) -> None:
        response = self.service.search("What is the Kingdom of God?")
        ids = [result.id for result in response.results]

        self.assertEqual(ids[0], "what-is-the-kingdom-of-god")
        self.assertNotIn("what-is-a-parable", ids)

    def test_search_deduplicates_near_duplicate_topic_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_library(
                root,
                [
                    make_object(
                        "what-is-the-new-covenant",
                        "faq",
                        "What is the New Covenant?",
                        ["new covenant study"],
                        summary="A concise explanation of the new covenant.",
                        importance=8,
                    ),
                    make_object(
                        "new-covenant",
                        "theology",
                        "New Covenant",
                        ["covenant theology note"],
                        summary="The new covenant in biblical theology.",
                        importance=7,
                    ),
                ],
            )
            service = CKLRetrievalService(library=CanonicalLibrary(root=root))
            response = service.search("What is the New Covenant?")

        self.assertEqual([result.id for result in response.results], ["what-is-the-new-covenant"])

    def test_debug_mode_exposes_internal_score_signals(self) -> None:
        response = self.service.search("Joshua 24", debug=True)

        self.assertTrue(response.results[0].score_details)
        self.assertTrue(
            any(signal.name in {"scripture_match", "keyword_match"} for signal in response.results[0].score_details)
        )


if __name__ == "__main__":
    unittest.main()
