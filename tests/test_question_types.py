import unittest

from bhf_agent.question_types import classify_question_type
from bhf_agent.references import detect_reference


class QuestionTypeTests(unittest.TestCase):
    def test_hebrew_word_question_is_word_study(self):
        context = classify_question_type(
            "What is the hebrew word for the word spirit or wind?"
        )

        self.assertEqual(context.question_type, "word_study")
        self.assertEqual(context.target_language, "Hebrew")
        self.assertIn("spirit", context.target_terms)
        self.assertIn("wind", context.target_terms)

    def test_greek_word_question_is_word_study(self):
        context = classify_question_type("What is the Greek word for love?")

        self.assertEqual(context.question_type, "word_study")
        self.assertEqual(context.target_language, "Greek")
        self.assertIn("love", context.target_terms)

    def test_ruach_question_is_hebrew_word_study(self):
        context = classify_question_type("What does rûaḥ mean?")

        self.assertEqual(context.question_type, "word_study")
        self.assertEqual(context.target_language, "Hebrew")
        self.assertIn("ruach", context.target_terms)

    def test_genesis_context_question_is_historical_context(self):
        reference = detect_reference("What is the context of Genesis 1?")
        context = classify_question_type(
            "What is the context of Genesis 1?",
            reference,
        )

        self.assertEqual(context.question_type, "historical_context")

    def test_john_explain_question_is_passage_study(self):
        reference = detect_reference("Explain John 3:16")
        context = classify_question_type("Explain John 3:16", reference)

        self.assertEqual(context.question_type, "passage_study")

    def test_paul_women_leadership_question_is_topic_study(self):
        reference = detect_reference(
            "What does Paul say about women in church leadership?"
        )
        context = classify_question_type(
            "What does Paul say about women in church leadership?",
            reference,
        )

        self.assertEqual(context.question_type, "topic_study")


if __name__ == "__main__":
    unittest.main()
