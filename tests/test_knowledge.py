import unittest

from bhf_agent.genre import classify_genre
from bhf_agent.knowledge import (
    lookup_book_context,
    lookup_genre_guide,
    lookup_lexical_entries,
    lookup_local_knowledge,
)
from bhf_agent.models import QuestionContext, ReferenceContext


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

    def test_proverbs_returns_wisdom_literature_book_context(self):
        entry = lookup_book_context(ReferenceContext(book="Proverbs"))

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.genre, "wisdom literature")
        self.assertIn("wisdom", entry.historical_context_hint.lower())

    def test_revelation_returns_apocalyptic_genre_guide(self):
        genre = classify_genre(ReferenceContext(book="Revelation"))
        entry = lookup_genre_guide(genre)

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.key, "genre:apocalyptic")
        self.assertIn("Symbolic visionary literature", entry.description)

    def test_topic_only_question_does_not_crash(self):
        bundle = lookup_local_knowledge(
            ReferenceContext(topic="leadership", confidence=0.5),
            classify_genre(ReferenceContext(topic="leadership", confidence=0.5)),
            QuestionContext(question_type="topic_study", confidence=0.7),
        )

        self.assertEqual(bundle.keys(), [])


if __name__ == "__main__":
    unittest.main()
