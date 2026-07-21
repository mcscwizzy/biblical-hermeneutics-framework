import unittest

from bhf_agent.study_actions import StudyActionRouter, compact_fact_packet, normalize_action


class StudyActionRouterTests(unittest.TestCase):
    def test_context_action_returns_structured_result_without_agent(self):
        result = StudyActionRouter().execute(
            "historical_context",
            passage={
                "book": "John",
                "chapter": 1,
                "start_verse": 1,
                "end_verse": 3,
                "translation": "asv",
            },
        )

        self.assertEqual(result.action, "historical_context")
        self.assertIn(result.status, {"complete", "partial"})
        self.assertIn(result.source, {"scripture", "ckl", "scripture_and_ckl"})
        self.assertGreaterEqual(len(result.sections), 1)
        self.assertEqual(result.metadata["reference"], "John 1:1-3")
        self.assertTrue(result.agent_fallback_allowed)

    def test_reference_actions_are_deterministic_only(self):
        result = StudyActionRouter().execute(
            "people",
            passage={"book": "John", "chapter": 1, "start_verse": 1, "end_verse": 3},
        )

        self.assertEqual(result.action, "people")
        self.assertFalse(result.agent_fallback_allowed)
        self.assertTrue(result.metadata["deterministic_only"])

    def test_related_ot_themes_aliases_to_themes(self):
        self.assertEqual(normalize_action("related_ot_themes"), "themes")

    def test_compact_fact_packet_has_agent_safe_shape(self):
        result = StudyActionRouter().execute(
            "literary_context",
            passage={"book": "John", "chapter": 1, "start_verse": 1, "end_verse": 3},
        )

        packet = compact_fact_packet(result)

        self.assertEqual(packet["action"], "literary_context")
        self.assertIn("sections", packet)
        self.assertIn("metadata", packet)
        self.assertIn("reference", packet["metadata"])


if __name__ == "__main__":
    unittest.main()
