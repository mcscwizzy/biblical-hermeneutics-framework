import unittest

from bhf_agent.genre import classify_genre
from bhf_agent.models import ReferenceContext


class GenreClassificationTests(unittest.TestCase):
    def test_classifies_proverbs_as_wisdom(self):
        genre = classify_genre(ReferenceContext(book="Proverbs"))

        self.assertEqual(genre.primary_genre, "wisdom literature")
        self.assertIn("genre.wisdom", genre.recommended_modules)

    def test_classifies_john_as_gospel(self):
        genre = classify_genre(ReferenceContext(book="John"))

        self.assertEqual(genre.primary_genre, "Gospel")
        self.assertIn("Second Temple Jewish context", genre.historical_context_hint)

    def test_classifies_revelation_as_apocalyptic(self):
        genre = classify_genre(ReferenceContext(book="Revelation"))

        self.assertEqual(genre.primary_genre, "apocalyptic")
        self.assertIn("letter", genre.secondary_genres)

    def test_topic_only_returns_low_confidence_guidance(self):
        genre = classify_genre(ReferenceContext(topic="leadership"))

        self.assertIsNone(genre.primary_genre)
        self.assertLess(genre.confidence, 0.5)


if __name__ == "__main__":
    unittest.main()
