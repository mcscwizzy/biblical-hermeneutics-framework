from __future__ import annotations

import unittest
from types import SimpleNamespace

from framework.canonical_library.retrieval import (
    analyze_query,
    detect_scripture_references,
    extract_phrases,
    extract_terms,
)
from framework.canonical_library.scripture import build_book_alias_lookup


class QueryAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.book_alias_lookup = build_book_alias_lookup([])
        cls.entries_by_id = {
            "joshua-son-of-nun": SimpleNamespace(
                id="joshua-son-of-nun",
                title="Joshua",
                category="person",
            ),
            "shechem": SimpleNamespace(
                id="shechem",
                title="Shechem",
                category="place",
            ),
            "covenant-theme": SimpleNamespace(
                id="covenant-theme",
                title="Covenant Theme",
                category="theme",
            ),
            "new-covenant": SimpleNamespace(
                id="new-covenant",
                title="New Covenant",
                category="theology",
            ),
            "ruach": SimpleNamespace(
                id="ruach",
                title="ruach",
                category="word_study",
            ),
            "pilate-stone": SimpleNamespace(
                id="pilate-stone",
                title="Pilate Stone",
                category="archaeology",
            ),
            "genesis": SimpleNamespace(
                id="genesis",
                title="Genesis",
                category="book",
            ),
        }
        cls.title_index = {
            "joshua": {"joshua-son-of-nun"},
            "shechem": {"shechem"},
            "covenant theme": {"covenant-theme"},
            "new covenant": {"new-covenant"},
            "ruach": {"ruach"},
            "pilate stone": {"pilate-stone"},
            "genesis": {"genesis"},
        }
        cls.alias_index = {
            "sichem": {"shechem"},
            "covenant renewal": {"covenant-theme"},
            "book of genesis": {"genesis"},
            "what is genesis about": {"genesis"},
            "meaning of ruach": {"ruach"},
        }

    def test_extract_terms_normalizes_stop_words_and_plurals(self) -> None:
        terms = extract_terms("Why did the children and women visit the cities?")

        self.assertEqual(terms, ["child", "woman", "visit", "city"])

    def test_extract_phrases_preserves_theological_phrases(self) -> None:
        phrases = extract_phrases("What is the Holy Spirit and the Kingdom of God?")

        self.assertEqual(phrases, ["kingdom of god", "holy spirit"])

    def test_detect_scripture_references_supports_standard_abbreviations(self) -> None:
        spans = detect_scripture_references(
            "See Gen 1:1 and 1 Cor. 13:4-7",
            book_alias_lookup=self.book_alias_lookup,
        )

        self.assertEqual(len(spans), 2)
        self.assertEqual(
            [
                (span.book, span.start_chapter, span.start_verse, span.end_chapter, span.end_verse)
                for span in spans
            ],
            [
                ("Genesis", 1, 1, None, None),
                ("1 Corinthians", 13, 4, None, 7),
            ],
        )

    def test_analyze_query_detects_people_places_themes_and_events(self) -> None:
        analysis = analyze_query(
            "Why did Joshua renew the covenant at Shechem?",
            book_alias_lookup=self.book_alias_lookup,
            title_index=self.title_index,
            alias_index=self.alias_index,
            entries_by_id=self.entries_by_id,
        )

        self.assertEqual(analysis.intent, "explanation")
        self.assertIn("people", analysis.categories)
        self.assertIn("places", analysis.categories)
        self.assertIn("themes", analysis.categories)
        self.assertIn("events", analysis.categories)
        self.assertIn("theological concepts", analysis.categories)
        self.assertEqual(analysis.matched_terms_by_category["people"], ["Joshua"])
        self.assertEqual(analysis.matched_terms_by_category["places"], ["Shechem"])
        self.assertIn("covenant", analysis.matched_terms_by_category["themes"])
        self.assertIn("renew", analysis.matched_terms_by_category["events"])
        self.assertIn("person", analysis.object_categories)
        self.assertIn("place", analysis.object_categories)
        self.assertIn("theme", analysis.object_categories)
        self.assertIn("event", analysis.object_categories)
        self.assertIn("theology", analysis.object_categories)

    def test_analyze_query_detects_original_language_terms_and_archaeology(self) -> None:
        analysis = analyze_query(
            "What does ruach mean and what is the Pilate Stone?",
            book_alias_lookup=self.book_alias_lookup,
            title_index=self.title_index,
            alias_index=self.alias_index,
            entries_by_id=self.entries_by_id,
        )

        self.assertIn("original-language terms", analysis.categories)
        self.assertIn("archaeological topics", analysis.categories)
        self.assertIn("ruach", analysis.matched_terms_by_category["original-language terms"])
        self.assertIn("Pilate Stone", analysis.matched_terms_by_category["archaeological topics"])
        self.assertIn("word_study", analysis.object_categories)
        self.assertIn("archaeology", analysis.object_categories)

    def test_analyze_query_detects_books_from_explicit_book_aliases(self) -> None:
        analysis = analyze_query(
            "What is Genesis about?",
            book_alias_lookup=self.book_alias_lookup,
            title_index=self.title_index,
            alias_index=self.alias_index,
            entries_by_id=self.entries_by_id,
        )

        self.assertIn("books", analysis.categories)
        self.assertIn("book", analysis.object_categories)
        self.assertEqual(analysis.matched_terms_by_category["books"], ["Genesis"])


if __name__ == "__main__":
    unittest.main()
