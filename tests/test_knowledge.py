import unittest

from bhf_agent.knowledge import lookup_lexical_entries
from bhf_agent.models import QuestionContext


class KnowledgeLookupTests(unittest.TestCase):
    def test_hebrew_spirit_wind_returns_ruach_with_caution_entries(self):
        entries = lookup_lexical_entries(
            QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            )
        )

        keys = [entry.key for entry in entries]
        self.assertIn("ruach", keys)
        self.assertIn("nephesh", keys)
        self.assertIn("qol", keys)

    def test_greek_spirit_returns_pneuma(self):
        entries = lookup_lexical_entries(
            QuestionContext(
                question_type="word_study",
                target_language="Greek",
                target_terms=["spirit"],
                confidence=0.9,
            )
        )

        self.assertEqual([entry.key for entry in entries], ["pneuma"])

    def test_nephesh_lookup_returns_nephesh(self):
        entries = lookup_lexical_entries(
            QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["nephesh"],
                confidence=0.9,
            )
        )

        self.assertEqual([entry.key for entry in entries], ["nephesh"])

    def test_qol_lookup_returns_qol(self):
        entries = lookup_lexical_entries(
            QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["qol"],
                confidence=0.9,
            )
        )

        self.assertEqual([entry.key for entry in entries], ["qol"])


if __name__ == "__main__":
    unittest.main()
