import unittest

from bhf_agent.references import detect_reference


class ReferenceDetectionTests(unittest.TestCase):
    def test_detects_book_and_chapter(self):
        context = detect_reference("What does Proverbs 3 mean?")

        self.assertTrue(context.is_reference_based)
        self.assertEqual(context.book, "Proverbs")
        self.assertEqual(context.chapter, 3)
        self.assertIsNone(context.verse)
        self.assertEqual(context.testament, "Old Testament")

    def test_detects_book_chapter_and_verse(self):
        context = detect_reference("Explain John 3:16")

        self.assertTrue(context.is_reference_based)
        self.assertEqual(context.book, "John")
        self.assertEqual(context.chapter, 3)
        self.assertEqual(context.verse, 16)
        self.assertEqual(context.testament, "New Testament")

    def test_detects_abbreviations(self):
        context = detect_reference("Explain Gen 1")

        self.assertEqual(context.book, "Genesis")
        self.assertEqual(context.chapter, 1)

    def test_detects_topic_only_question(self):
        context = detect_reference("What does Paul say about women in church leadership?")

        self.assertFalse(context.is_reference_based)
        self.assertEqual(context.topic, "women in church leadership")

    def test_revelation_topic_phrase_is_not_forced_to_reference(self):
        context = detect_reference("What does Revelation mean by 666?")

        self.assertFalse(context.is_reference_based)
        self.assertEqual(context.topic, "666")


if __name__ == "__main__":
    unittest.main()
