from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalLibrary
from framework.canonical_library.retrieval import CKLRetrievalService

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

    def test_search_supports_standard_scripture_abbreviations(self) -> None:
        response = self.service.search("Gen 1:1")

        self.assertGreater(len(response.results), 0)
        self.assertGreaterEqual(len(response.analysis.scripture_references), 1)
        self.assertEqual(response.analysis.scripture_references[0].book, "Genesis")
        self.assertIn("books", response.analysis.categories)
        self.assertTrue(any(result.id == "genesis" for result in response.results[:3]))

    def test_search_prioritizes_joseph_bones_over_generic_significance_entries(self) -> None:
        response = self.service.search("What is the significance of Joseph's bones?")
        ids = [result.id for result in response.results]

        self.assertIn("shechem", ids[:3])
        self.assertNotIn("what-is-a-parable", ids)

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
