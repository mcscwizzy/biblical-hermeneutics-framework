from __future__ import annotations

import unittest

from framework.canonical_library.retrieval import CKLRetrievalService


class ED4RetrievalRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = CKLRetrievalService.load_default()

    def result_ids(self, query: str, *, limit: int = 5) -> list[str]:
        return [result.id for result in self.service.search(query, limit=limit).results]

    def test_explicit_1_john_does_not_promote_un_numbered_john(self) -> None:
        ids = self.result_ids("1 John What if our heart condemns us?")

        self.assertEqual(ids[0], "1-john")

    def test_relation_query_ranks_grammatical_focus_before_supporting_passage(self) -> None:
        ids = self.result_ids("How does 1 Thessalonians relate to Acts 17?")

        self.assertEqual(ids[0], "1-thessalonians")
        self.assertIn("acts", ids[:3])

    def test_reversing_relation_subject_reverses_primary_passage(self) -> None:
        ids = self.result_ids("How does Acts 17 relate to 1 Thessalonians?")

        self.assertEqual(ids[0], "acts")
        self.assertIn("1-thessalonians", ids[:3])

    def test_two_passage_comparison_keeps_both_testaments_in_primary_results(self) -> None:
        ids = self.result_ids("Compare Genesis 1 and John 1.", limit=2)

        self.assertEqual(set(ids), {"genesis", "john"})

    def test_separately_named_nested_book_titles_both_remain_retrievable(self) -> None:
        ids = self.result_ids("Compare 1 John 3:19 and John 3:16.", limit=2)

        self.assertEqual(set(ids), {"1-john", "john"})

    def test_numbered_book_titles_do_not_promote_overlapping_un_numbered_title(self) -> None:
        for title, expected in (
            ("1 John", "1-john"),
            ("2 John", "2-john"),
            ("3 John", "3-john"),
            ("1 Samuel", "1-samuel"),
            ("2 Kings", "2-kings"),
            ("1 Chronicles", "1-chronicles"),
            ("2 Thessalonians", "2-thessalonians"),
            ("1 Corinthians", "1-corinthians"),
            ("2 Peter", "2-peter"),
        ):
            with self.subTest(title=title):
                ids = self.result_ids(f"What does {title} say about its audience?")
                self.assertEqual(ids[0], expected)

    def test_representative_evaluation_retrieves_expected_passage_or_evidence(self) -> None:
        cases = (
            ("1 John 3:19-24 What if our heart condemns us?", "1-john"),
            ("What does Hebrew hesed mean in Ruth?", "ruth"),
            ("What manuscript variants occur in Mark 16:9-20?", "mark"),
            (
                "What archaeological evidence relates to Hezekiah's tunnel in 2 Kings 20?",
                "hezekiahs-tunnel-inscription-context",
            ),
            ("Compare Genesis 1 and John 1.", "genesis"),
        )

        for query, expected_id in cases:
            with self.subTest(query=query):
                self.assertIn(expected_id, self.result_ids(query, limit=5))


if __name__ == "__main__":
    unittest.main()
