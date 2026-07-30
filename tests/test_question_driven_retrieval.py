"""Regression tests for question-driven CKL retrieval priority."""

from __future__ import annotations

import unittest

from bhf_agent.ckl import build_canonical_context, load_canonical_library
from bhf_agent.models import QuestionContext, ReferenceContext


class QuestionDrivenRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = load_canonical_library()
        cls.question_context = QuestionContext(question_type="general")

    def _context(self, question: str, reference: ReferenceContext | None = None) -> dict:
        context = build_canonical_context(
            self.library, question, reference, self.question_context,
            max_results=5, max_context_tokens=3000,
        )
        self.assertIsNotNone(context)
        return context or {}

    def test_hannah_prefers_entity_and_direct_evidence_to_book_overview(self) -> None:
        context = self._context("Why was Hannah unable to conceive?")
        ids = [topic["id"] for topic in context["retrieved_topics"]]
        facts = context["metadata"]["direct_textual_evidence"]["facts"]

        self.assertEqual(context["metadata"]["retrieval_intent"]["passage"], "1 Samuel 1")
        self.assertEqual(context["metadata"]["retrieval_intent"]["primary_entities"][0]["id"], "hannah")
        self.assertLess(ids.index("hannah"), ids.index("1-samuel"))
        self.assertIn("1 Samuel 1:5", [fact["reference"] for fact in facts])
        self.assertIn("1 Samuel 1:6", [fact["reference"] for fact in facts])
        self.assertNotIn("saul", ids)

    def test_ruth_and_boaz_resolve_to_ruth_three(self) -> None:
        context = self._context("Why did Ruth uncover Boaz's feet and lie down?")
        ids = [topic["id"] for topic in context["retrieved_topics"]]
        facts = context["metadata"]["direct_textual_evidence"]["facts"]

        self.assertEqual(context["metadata"]["retrieval_intent"]["passage"], "Ruth 3")
        self.assertIn("ruth-the-moabite", ids)
        self.assertIn("boaz", ids)
        self.assertLess(ids.index("boaz"), ids.index("ruth"))
        self.assertIn("Ruth 3:7", [fact["reference"] for fact in facts])

    def test_explicit_symbol_interpretation_is_direct_evidence(self) -> None:
        context = self._context(
            "What do the seven stars represent in Revelation 1?",
            ReferenceContext(book="Revelation", chapter=1),
        )
        facts = context["metadata"]["direct_textual_evidence"]["facts"]
        intent = context["metadata"]["retrieval_intent"]

        self.assertIn("seven stars", intent["primary_symbols"])
        self.assertIn("Revelation 1:20", [fact["reference"] for fact in facts])

    def test_identity_question_prefers_person_to_book(self) -> None:
        context = self._context("Who was Samuel?")
        ids = [topic["id"] for topic in context["retrieved_topics"]]

        self.assertEqual(ids[0], "samuel-the-prophet")
        self.assertLess(ids.index("samuel-the-prophet"), ids.index("1-samuel"))

    def test_book_overview_keeps_book_as_the_subject(self) -> None:
        context = self._context("What is the overall message of 1 Samuel?")
        self.assertEqual(context["retrieved_topics"][0]["id"], "1-samuel")


if __name__ == "__main__":
    unittest.main()
