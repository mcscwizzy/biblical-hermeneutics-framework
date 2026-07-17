from __future__ import annotations

import unittest

from framework.canonical_library import CanonicalContextBuilder, CanonicalLibrary
from framework.canonical_library.query_analysis import analyze_query


class PrecisionFirstRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = CanonicalLibrary.load_default()

    def build(self, query: str, *, limit: int = 5) -> dict[str, object]:
        return CanonicalContextBuilder(self.library).build(query, limit=limit)

    def result_ids(self, context: dict[str, object]) -> list[str]:
        return [item["id"] for item in context["retrieved_topics"]]  # type: ignore[index]

    def test_analyzer_extracts_book_of_john_as_single_book_entity(self) -> None:
        analysis = analyze_query(
            "What is the context of the book of John?",
            book_alias_lookup=self.library._book_alias_lookup,
        )

        self.assertEqual(analysis.intent, "book_context")
        self.assertEqual(analysis.scope, "single_entity")
        self.assertEqual(analysis.entity_candidates, ("John", "Gospel of John"))
        self.assertEqual(analysis.preferred_categories, ("book",))
        self.assertEqual(analysis.category_confidence, 1.0)
        self.assertFalse(analysis.include_related)
        self.assertFalse(analysis.comparative)

    def test_book_of_john_returns_only_john(self) -> None:
        context = self.build("What is the context of the book of John?")

        self.assertEqual(self.result_ids(context), ["john"])
        self.assertEqual(context["metadata"]["primary_topic_count"], 1)  # type: ignore[index]
        self.assertEqual(context["metadata"]["expanded_topic_count"], 0)  # type: ignore[index]
        self.assertNotIn("luke", self.result_ids(context))
        self.assertNotIn("revelation", self.result_ids(context))
        self.assertNotIn("matthew", self.result_ids(context))
        self.assertNotIn("mark", self.result_ids(context))

    def test_gospel_of_john_returns_only_john(self) -> None:
        context = self.build("Tell me about the Gospel of John.")

        self.assertEqual(self.result_ids(context), ["john"])
        self.assertEqual(context["metadata"]["expanded_topic_count"], 0)  # type: ignore[index]

    def test_romans_about_returns_only_romans(self) -> None:
        context = self.build("What is Romans about?")

        self.assertEqual(self.result_ids(context), ["romans"])
        self.assertEqual(context["metadata"]["expanded_topic_count"], 0)  # type: ignore[index]

    def test_person_name_with_qualifier_resolves_to_person(self) -> None:
        context = self.build("Who was John the Baptist?")

        self.assertEqual(self.result_ids(context), ["john-the-baptist"])
        self.assertEqual(context["retrieved_topics"][0]["type"], "person")  # type: ignore[index]

    def test_unqualified_person_name_returns_ambiguity_not_book(self) -> None:
        context = self.build("Who was John?")

        self.assertEqual(self.result_ids(context), [])
        ambiguity = context["metadata"]["ambiguity"]  # type: ignore[index]
        self.assertIsNotNone(ambiguity)
        self.assertEqual(ambiguity["status"], "ambiguous")  # type: ignore[index]
        candidate_ids = [candidate["id"] for candidate in ambiguity["candidates"]]  # type: ignore[index]
        self.assertIn("john-the-baptist", candidate_ids)
        self.assertIn("john-son-of-zebedee", candidate_ids)
        self.assertNotIn("john", candidate_ids)

    def test_multi_entity_comparison_returns_requested_books_only(self) -> None:
        context = self.build("Compare John and Luke.")

        self.assertEqual(self.result_ids(context), ["john", "luke"])
        self.assertNotIn("revelation", self.result_ids(context))
        self.assertEqual(context["metadata"]["expanded_topic_count"], 0)  # type: ignore[index]

    def test_explicit_relationship_query_returns_named_books(self) -> None:
        context = self.build("How is John related to Revelation?")

        self.assertEqual(self.result_ids(context), ["john", "revelation"])
        analysis = context["metadata"]["query_analysis"]  # type: ignore[index]
        self.assertTrue(analysis["include_related"])  # type: ignore[index]

    def test_conceptual_query_uses_thresholded_ranked_retrieval(self) -> None:
        context = self.build("What does Scripture teach about new birth?")

        self.assertGreaterEqual(len(self.result_ids(context)), 1)
        retrieval = context["metadata"]["retrieval"]  # type: ignore[index]
        self.assertEqual(retrieval["method"], "ranked")  # type: ignore[index]
        self.assertTrue(retrieval["threshold_applied"])  # type: ignore[index]

    def test_scripture_query_resolves_book_context_without_neighboring_books(self) -> None:
        context = self.build("What is the context of John 3?")

        self.assertEqual(self.result_ids(context), ["john"])
        self.assertNotIn("luke", self.result_ids(context))
        self.assertNotIn("revelation", self.result_ids(context))


if __name__ == "__main__":
    unittest.main()
