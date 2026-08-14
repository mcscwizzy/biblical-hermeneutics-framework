import unittest
from pathlib import Path

from bhf_agent.ckl import build_canonical_context, format_canonical_context_for_prompt, load_canonical_library
from bhf_agent.genre import classify_genre
from bhf_agent.prompts import build_prompt
from bhf_agent.question_types import classify_question_type
from bhf_agent.references import detect_reference

try:
    from bhf_web.services.web_helpers import build_ask_question, normalize_study_action
except ModuleNotFoundError:
    build_ask_question = None
    normalize_study_action = None


class CulturalContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.question = "Using BHF, explain the focused Cultural Context of ASV Genesis 1:1-2."
        self.reference = detect_reference(self.question)
        self.question_context = classify_question_type(self.question, self.reference)
        self.genre = classify_genre(self.reference)

    def test_cultural_context_action_remains_available_to_study_workflows(self) -> None:
        script = Path("bhf_web/static/htmx-lite.js").read_text(encoding="utf-8")
        self.assertIn('"cultural_context",', script)
        self.assertIn('ancient_context: "cultural_context",', script)

    @unittest.skipUnless(normalize_study_action is not None, "web dependencies are not installed")
    def test_legacy_actions_normalize_to_cultural_context(self) -> None:
        self.assertEqual(normalize_study_action("ancient_context"), "cultural_context")
        self.assertEqual(normalize_study_action("ancient_cultural_context"), "cultural_context")

    def test_cultural_prompt_is_narrow_and_historical_prompt_is_separate(self) -> None:
        cultural_system, cultural_user = build_prompt(
            "standard", "PROFILE", self.reference, self.genre, self.question_context, self.question
        )
        cultural_block = cultural_system.split("# Cultural Context Action", 1)[1]
        self.assertIn("Relevant Cultural Practice or Assumption", cultural_block)
        self.assertNotIn("Historical / Cultural Setting", cultural_block)
        self.assertIn("cultural_context", cultural_user)
        self.assertNotIn("Original Audience / Ancient Context; Observation; Interpretation; Application", cultural_user)

        historical_question = "What is the historical context of Genesis 1?"
        historical_reference = detect_reference(historical_question)
        historical_context = classify_question_type(historical_question, historical_reference)
        historical_system, _ = build_prompt(
            "standard", "PROFILE", historical_reference, classify_genre(historical_reference), historical_context, historical_question
        )
        self.assertNotIn("# Cultural Context Action", historical_system)

    def test_cultural_retrieval_is_scoped_and_budgeted(self) -> None:
        context = build_canonical_context(
            load_canonical_library(),
            self.question,
            self.reference,
            self.question_context,
            max_results=8,
            max_context_tokens=3000,
        )
        self.assertIsNotNone(context)
        metadata = context["metadata"]
        self.assertEqual(metadata["retrieval_scope"], "cultural")
        self.assertLessEqual(metadata["max_results"], 3)
        self.assertLessEqual(metadata["max_context_tokens"], 1100)
        self.assertLessEqual(len(context["retrieved_topics"]), 3)
        self.assertTrue(
            all(topic["type"] not in {"book", "event", "theology", "prophecy"} for topic in context["retrieved_topics"])
        )

        prompt = format_canonical_context_for_prompt(
            context, max_context_tokens=3000, study_action="cultural_context"
        )
        self.assertIn("Relevant Cultural Background:", prompt)
        self.assertNotIn("Historical Context:", prompt)
        self.assertNotIn("Covenant and Canonical Context:", prompt)

    @unittest.skipUnless(build_ask_question is not None, "web dependencies are not installed")
    def test_old_reader_action_is_accepted_by_question_builder(self) -> None:
        form = {
            "reader_book": "Genesis",
            "reader_chapter": "1",
            "reader_start_verse": "1",
            "reader_end_verse": "2",
            "reader_selected_text": "In the beginning God created the heavens and the earth.",
            "ask_mode": "ancient_context",
            "question": "",
        }
        question, _ = build_ask_question(form)
        self.assertIn("Question type: cultural_context", question)


if __name__ == "__main__":
    unittest.main()
