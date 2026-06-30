import unittest

from bhf_agent.bible import (
    BibleError,
    compare_translation_passages,
    build_selected_passage_context,
    geography_for_book,
    is_topic_style_search_query,
    list_books,
    load_asv_bible,
    load_kjv_bible,
    normalize_book_name,
    parse_reference_query,
    resolve_chapter,
    resolve_passage,
    search_bible_text,
    timeline_for_book,
    verse_range_reference,
)


class BibleDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_asv_bible()

    def test_load_asv_dataset(self):
        self.assertEqual(self.data["translation"]["id"], "ASV")
        self.assertEqual(len(self.data["books"]), 66)
        verse_count = sum(
            len(chapter["verses"])
            for book in self.data["books"]
            for chapter in book["chapters"]
        )
        self.assertEqual(verse_count, 31103)

    def test_load_kjv_dataset(self):
        kjv = load_kjv_bible()

        self.assertEqual(kjv["translation"]["id"], "KJV")
        self.assertEqual(len(kjv["books"]), 66)
        verse_count = sum(
            len(chapter["verses"])
            for book in kjv["books"]
            for chapter in book["chapters"]
        )
        self.assertEqual(verse_count, 31103)

    def test_list_books_reports_order_and_chapter_count(self):
        books = list_books(self.data)

        self.assertEqual(books[0], {"name": "Genesis", "order": 1, "chapters": 50})
        self.assertEqual(books[-1]["name"], "Revelation")
        self.assertEqual(books[-1]["chapters"], 22)

    def test_resolve_valid_chapter(self):
        chapter = resolve_chapter("John", 1, self.data)

        self.assertEqual(chapter["book"], "John")
        self.assertEqual(chapter["chapter"], 1)
        self.assertEqual(chapter["verses"][0]["text"], "In the beginning was the Word, and the Word was with God, and the Word was God.")

    def test_resolve_invalid_chapter(self):
        with self.assertRaisesRegex(BibleError, "John has no chapter 99"):
            resolve_chapter("John", 99, self.data)

    def test_resolve_verse_range(self):
        passage = resolve_passage("Rom", 12, 1, 2, self.data)

        self.assertEqual(passage["reference"], "Romans 12:1-2")
        self.assertEqual(len(passage["selected_verses"]), 2)
        self.assertIn("living sacrifice", passage["selected_text"])

    def test_resolve_invalid_verse_range(self):
        with self.assertRaisesRegex(BibleError, "Romans 12 has no verses 1-999"):
            resolve_passage("Romans", 12, 1, 999, self.data)

    def test_normalize_common_book_names(self):
        self.assertEqual(normalize_book_name("Gen."), "Genesis")
        self.assertEqual(normalize_book_name("1 cor"), "1 Corinthians")
        self.assertEqual(normalize_book_name("song of solomon"), "Song of Songs")

    def test_verse_range_reference(self):
        self.assertEqual(verse_range_reference("Romans", 12), "Romans 12")
        self.assertEqual(verse_range_reference("Romans", 12, 1, 1), "Romans 12:1")
        self.assertEqual(verse_range_reference("Romans", 12, 1, 2), "Romans 12:1-2")

    def test_build_selected_passage_context(self):
        context = build_selected_passage_context(
            "John",
            1,
            1,
            2,
            selected_text="In the beginning was the Word.",
            data=self.data,
        )

        self.assertEqual(context["reference"], "John 1:1-2")
        self.assertEqual(context["selected_text"], "In the beginning was the Word.")
        self.assertIn("In him was life", context["chapter_context"])

    def test_compare_translation_passages_returns_verse_rows(self):
        comparison = compare_translation_passages("John", 1, 1, 2)

        self.assertEqual(comparison["reference"], "John 1:1-2")
        self.assertEqual(len(comparison["translations"]), 2)
        self.assertEqual(comparison["translations"][0]["id"], "ASV")
        self.assertEqual(comparison["translations"][1]["id"], "KJV")
        self.assertEqual(len(comparison["verse_rows"]), 2)
        self.assertIn("ASV", comparison["verse_rows"][0]["texts"])
        self.assertIn("KJV", comparison["verse_rows"][0]["texts"])
        self.assertIn("In the beginning was the Word", comparison["verse_rows"][0]["texts"]["ASV"])
        self.assertIn("In the beginning was the Word", comparison["verse_rows"][0]["texts"]["KJV"])

    def test_timeline_for_book_uses_broad_periods(self):
        guide = timeline_for_book("Exodus")

        self.assertEqual(guide["period"], "Moses and the exodus / wilderness era")
        self.assertIn("without forcing a specific calendar date", guide["notes"])
        self.assertEqual(timeline_for_book("Romans")["period"], "Pauline letter to the Roman church")

    def test_geography_for_book_uses_broad_regions(self):
        guide = geography_for_book("Acts")

        self.assertEqual(guide["region"], "Jerusalem, Samaria, Syria, Asia Minor, Greece, and Rome")
        self.assertIn("Follow the mission outward", guide["notes"])
        self.assertEqual(geography_for_book("Exodus")["region"], "Egypt, the wilderness, and Sinai")

    def test_search_bible_text_returns_phrase_matches(self):
        result = search_bible_text("living sacrifice")

        self.assertFalse(result["direct_reference"])
        self.assertGreater(result["total_results"], 0)
        self.assertEqual(result["results"][0]["reference"], "Romans 12:1")
        self.assertEqual(result["results"][0]["match_type"], "phrase")

    def test_search_bible_text_resolves_direct_reference(self):
        result = search_bible_text("John 1:1-2")

        self.assertTrue(result["direct_reference"])
        self.assertEqual(result["results"][0]["reference"], "John 1:1-2")
        self.assertFalse(result["ai_fallback_eligible"])

    def test_parse_reference_query_handles_ranges(self):
        parsed = parse_reference_query("Rom 12:1-2")

        self.assertEqual(
            parsed,
            {"book": "Romans", "chapter": 12, "verse_start": 1, "verse_end": 2},
        )

    def test_topic_style_search_query_detection(self):
        self.assertTrue(is_topic_style_search_query("Egypt in Exodus"))
        self.assertTrue(is_topic_style_search_query("forgiveness"))
        self.assertFalse(is_topic_style_search_query("living sacrifice"))
        self.assertFalse(is_topic_style_search_query('"living sacrifice"'))

    def test_search_bible_text_marks_topic_fallback_eligible_on_no_hit(self):
        result = search_bible_text("perichoresis hypostasis theosis")

        self.assertEqual(result["results"], [])
        self.assertTrue(result["ai_fallback_eligible"])

    def test_search_bible_text_does_not_mark_literal_no_hit_as_topic_fallback(self):
        result = search_bible_text("zzzxxyyqq")

        self.assertEqual(result["results"], [])
        self.assertFalse(result["ai_fallback_eligible"])


if __name__ == "__main__":
    unittest.main()
