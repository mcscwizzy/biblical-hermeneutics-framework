from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from framework.canonical_library import CanonicalLibrary

from .helpers import make_object, write_library


@contextmanager
def loaded_library(objects: list[dict[str, object]]):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        write_library(root, objects)
        yield CanonicalLibrary(root=root).load()


def user_facing_retrieval_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "abraham",
            "person",
            "Abraham",
            ["Abram"],
            summary="Abram, later Abraham, was called into covenant faithfulness.",
            common_questions=["Who was Abram?"],
            importance=8,
        ),
        make_object(
            "genesis",
            "book",
            "Genesis",
            ["beginnings"],
            summary="The first book of the Bible and the book of beginnings.",
            common_questions=["book of Genesis"],
            importance=7,
        ),
        make_object(
            "tel-dan-stele",
            "archaeology",
            "Tel Dan Stele",
            ["Aramaic stele"],
            summary="An archaeological inscription mentioning the house of David.",
            common_questions=["house of David inscription"],
            importance=6,
        ),
        make_object(
            "shechem-covenant-renewal",
            "event",
            "Shechem and Covenant Renewal",
            ["covenant renewal at shechem"],
            summary="The covenant renewal at Shechem after Joshua's covenant ceremony.",
            common_questions=["covenant at Shechem"],
            related_objects=[
                {
                    "id": "shechem",
                    "relationship": "associated-place",
                    "weight": 6,
                    "notes": "covenant renewal site",
                }
            ],
            importance=9,
        ),
        make_object(
            "joseph",
            "person",
            "Joseph",
            ["jacob's son joseph"],
            summary="Joseph was buried at Shechem.",
            common_questions=["Where was Joseph buried?"],
            related_objects=[
                {
                    "id": "shechem",
                    "relationship": "associated-place",
                    "weight": 6,
                    "notes": "burial site",
                }
            ],
            importance=9,
        ),
        make_object(
            "shechem",
            "place",
            "Shechem",
            ["ancient shechem"],
            summary="Shechem is the burial site associated with Joseph.",
            common_questions=["Where was Joseph buried?"],
            related_objects=[
                {
                    "id": "joseph",
                    "relationship": "associated-person",
                    "weight": 6,
                    "notes": "burial connection",
                }
            ],
            importance=8,
        ),
    ]


def phrase_matching_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "shechem",
            "place",
            "Shechem",
            ["where is shechem"],
            summary="Shechem is a covenant location.",
            importance=8,
        ),
        make_object(
            "shechem-covenant-renewal",
            "event",
            "Shechem and Covenant Renewal",
            ["covenant renewal site"],
            summary="The covenant renewal at Shechem after Joshua's ceremony.",
            common_questions=["How does the covenant renewal at Shechem work?"],
            importance=9,
        ),
    ]


def governance_filter_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "shechem-and-covenant-renewal",
            "event",
            "Shechem and Covenant Renewal",
            ["covenant renewal"],
            summary="The covenant renewal at Shechem.",
            common_questions=["covenant at Shechem"],
            content_status="complete",
            review_status="approved",
            reviewed_by=["alice"],
            last_reviewed="2024-07-13",
            confidence="high",
            scripture_references=[
                {
                    "reference": "Joshua 24:1-28",
                    "relationship": "primary",
                    "notes": "",
                }
            ],
            sources=[
                {
                    "title": "Joshua",
                    "author": "",
                    "publisher": "",
                    "year": None,
                    "locator": "24:1-28",
                    "url": "",
                    "source_type": "biblical-text",
                    "notes": "",
                }
            ],
            importance=8,
        ),
        make_object(
            "covenant-shechem-note",
            "theme",
            "Covenant Shechem Note",
            ["shechem note"],
            summary="A note about the covenant at Shechem.",
            common_questions=["covenant at Shechem"],
            importance=90,
        ),
        make_object(
            "old-shechem-note",
            "faq",
            "Old Shechem Note",
            ["archived shechem note"],
            summary="An old note about Shechem.",
            content_status="deprecated",
        ),
        make_object(
            "rejected-david-note",
            "faq",
            "Rejected David Note",
            ["david note"],
            summary="A rejected note about the house of David.",
            review_status="rejected",
            reviewed_by=["zoe"],
            last_reviewed="2024-07-13",
        ),
    ]


class CanonicalRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        write_library(
            self.root,
            [
                make_object(
                    "abraham",
                    "person",
                    "Abraham",
                    ["who is abraham", "tell me about abraham"],
                ),
                make_object(
                    "covenant-theme",
                    "theme",
                    "Covenant Theme",
                    ["covenant motif", "covenant pattern"],
                ),
                make_object(
                    "shechem",
                    "place",
                    "Shechem",
                    ["where is shechem", "why is shechem important"],
                ),
            ],
        )
        self.library = CanonicalLibrary(root=self.root).load()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_exact_id_lookup_is_case_insensitive(self) -> None:
        result = self.library.retrieve_exact("SHECHEM")

        self.assertIsNotNone(result)
        self.assertEqual(result.object.id, "shechem")
        self.assertEqual(result.match_type, "id")
        self.assertEqual(result.matched_fields, ["id"])

    def test_alias_lookup(self) -> None:
        result = self.library.retrieve_exact("why is shechem important")

        self.assertIsNotNone(result)
        self.assertEqual(result.object.id, "shechem")
        self.assertEqual(result.match_type, "alias")
        self.assertEqual(result.matched_alias, "why is shechem important")
        self.assertEqual(result.matched_fields, ["aliases"])

    def test_title_lookup(self) -> None:
        result = self.library.retrieve_exact("Shechem")

        self.assertIsNotNone(result)
        self.assertEqual(result.object.id, "shechem")
        self.assertEqual(result.match_type, "id")
        self.assertEqual(result.matched_fields, ["id"])

    def test_keyword_lookup_returns_stable_ranked_results(self) -> None:
        first = self.library.retrieve_by_keywords("covenant abraham", limit=2)
        second = self.library.retrieve_by_keywords("covenant abraham", limit=2)

        self.assertEqual([result.object.id for result in first], [result.object.id for result in second])
        self.assertEqual(len(first), 2)
        self.assertTrue({result.object.id for result in first}.issuperset({"abraham", "covenant-theme"}))
        self.assertGreaterEqual(first[0].score, first[1].score)

    def test_keyword_limit_is_respected(self) -> None:
        results = self.library.retrieve_by_keywords("covenant abraham shechem", limit=1)

        self.assertEqual(len(results), 1)

    def test_retrieval_can_exclude_placeholder_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "aardvark-placeholder",
                        "place",
                        "Shechem Reference",
                        ["shechem placeholder"],
                        content_status="placeholder",
                        review_status="unreviewed",
                    ),
                    make_object(
                        "zebra-approved",
                        "place",
                        "Shechem Reference",
                        ["shechem approved"],
                        content_status="complete",
                        review_status="approved",
                        summary="A reviewed Shechem reference record.",
                        reviewed_by=["alice"],
                        last_reviewed="2024-07-13",
                        confidence="high",
                        scripture_references=[
                            {
                                "reference": "Joshua 24:1-28",
                                "relationship": "primary",
                                "notes": "",
                            }
                        ],
                        sources=[
                            {
                                "title": "Joshua",
                                "author": "",
                                "publisher": "",
                                "year": None,
                                "locator": "24:1-28",
                                "url": "",
                                "source_type": "biblical-text",
                                "notes": "",
                            }
                        ],
                    ),
                ],
            )

            library = CanonicalLibrary(root=root).load()

        placeholder_result = library.retrieve_exact("Shechem Reference")
        strict_result = library.retrieve_exact(
            "Shechem Reference",
            include_placeholders=False,
            allowed_statuses=("approved",),
        )

        self.assertIsNotNone(placeholder_result)
        self.assertEqual(placeholder_result.object.id, "aardvark-placeholder")
        self.assertIsNotNone(strict_result)
        self.assertEqual(strict_result.object.id, "zebra-approved")

    def test_unknown_query_returns_empty_results(self) -> None:
        self.assertEqual(self.library.retrieve_by_keywords("the and of", limit=5), [])
        self.assertIsNone(self.library.retrieve_exact(""))

    def test_semantic_retrieval_is_explicitly_unsupported(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.library.retrieve_semantic("covenant")

    def test_hybrid_retrieval_prioritizes_scripture_and_fuzzy_aliases(self) -> None:
        default_library = CanonicalLibrary.load_default()
        scripture_results = default_library.retrieve_hybrid("Joshua 24", limit=5)
        self.assertEqual([result.object.id for result in scripture_results[:3]], ["shechem", "joshua-son-of-nun", "joshua"])
        self.assertEqual(scripture_results[0].match_type, "scripture")

        fuzzy_result = default_library.retrieve_exact("Abram")
        self.assertIsNotNone(fuzzy_result)
        self.assertEqual(fuzzy_result.object.id, "abraham")
        self.assertEqual(fuzzy_result.match_type, "fuzzy_alias")
        self.assertEqual(fuzzy_result.matched_alias, "Abraham")

    def test_phrase_matching_can_prefer_a_more_specific_object(self) -> None:
        with loaded_library(phrase_matching_objects()) as library:
            results = library.retrieve_by_keywords("covenant renewal at Shechem", limit=3)

            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0].object.id, "shechem-covenant-renewal")
            self.assertEqual(results[0].match_type, "phrase")
            self.assertIn("summary", results[0].matched_fields)

    def test_field_aware_keyword_lookup_supports_user_facing_queries(self) -> None:
        with loaded_library(user_facing_retrieval_objects()) as library:
            cases = [
                ("Who was Abram?", "abraham", "common_questions"),
                ("book of Genesis", "genesis", "title"),
                ("house of David inscription", "tel-dan-stele", "summary"),
                ("covenant at Shechem", "shechem-covenant-renewal", "title"),
            ]

            for query, expected_id, expected_field in cases:
                with self.subTest(query=query):
                    results = library.retrieve_by_keywords(query, limit=3)
                    self.assertGreaterEqual(len(results), 1)
                    self.assertEqual(results[0].object.id, expected_id)
                    self.assertTrue(results[0].matched_terms)
                    self.assertIn(expected_field, results[0].matched_fields)

            burial_results = library.retrieve_by_keywords("where was Joseph buried?", limit=2)
            self.assertEqual([result.object.id for result in burial_results[:2]], ["joseph", "shechem"])
            self.assertTrue(burial_results[0].matched_terms)
            self.assertTrue(burial_results[1].matched_terms)
            self.assertIn("common_questions", burial_results[0].matched_fields)
            self.assertIn("common_questions", burial_results[1].matched_fields)

    def test_retrieval_flags_skip_deprecated_and_rejected_content(self) -> None:
        with loaded_library(governance_filter_objects()) as library:
            self.assertEqual(library.retrieve_by_keywords("archived old", limit=5), [])
            deprecated_results = library.retrieve_by_keywords(
                "archived old",
                limit=5,
                exclude_deprecated=False,
            )
            self.assertEqual([result.object.id for result in deprecated_results], ["old-shechem-note"])

            self.assertIsNone(library.retrieve_exact("Rejected David Note"))
            rejected_result = library.retrieve_exact("Rejected David Note", exclude_rejected=False)
            self.assertIsNotNone(rejected_result)
            self.assertEqual(rejected_result.object.id, "rejected-david-note")

    def test_approved_only_restricts_results_to_approved_content(self) -> None:
        with loaded_library(governance_filter_objects()) as library:
            approved_results = library.retrieve_by_keywords(
                "covenant at Shechem",
                limit=5,
                approved_only=True,
            )

            self.assertEqual([result.object.id for result in approved_results], ["shechem-and-covenant-renewal"])
            self.assertEqual(approved_results[0].object.review_status, "approved")
            self.assertIn("title", approved_results[0].matched_fields)

            self.assertIsNone(library.retrieve_exact("Covenant Shechem Note", approved_only=True))


if __name__ == "__main__":
    unittest.main()
