import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bhf_agent.config import AgentConfig
from bhf_agent.eval import (
    answer_from_agent,
    load_fixture,
    result_to_json,
    score_answer,
)
from tools.eval_local import main


FIXTURE_PATH = Path("tests/prompts/proverbs-context-basic.json")


class EvalLocalTests(unittest.TestCase):
    def test_fixture_loads(self):
        fixture = load_fixture(FIXTURE_PATH)

        self.assertEqual(fixture.id, "proverbs-context-basic")
        self.assertEqual(fixture.profile, "standard")
        self.assertEqual(fixture.answer_mode, "study")
        self.assertEqual(fixture.pass_threshold, 70)
        self.assertTrue(fixture.expected_behaviors)

    def test_expected_behavior_matching_works(self):
        fixture = load_fixture(FIXTURE_PATH)
        answer = (
            "Proverbs is wisdom literature. A proverb is not a mechanical "
            "promise. Start with genre and context before application."
        )

        result = score_answer(answer, fixture)

        self.assertTrue(result.passed)
        self.assertEqual(result.score, 100)
        self.assertTrue(all(item.matched for item in result.expected))

    def test_forbidden_behavior_lowers_score(self):
        fixture = load_fixture(FIXTURE_PATH)
        answer = (
            "Proverbs is wisdom literature. A proverb is not a mechanical "
            "promise. Start with genre and context before application. "
            "It always guarantees prosperity."
        )

        result = score_answer(answer, fixture)

        self.assertEqual(result.score, 80)
        self.assertTrue(any(item.matched for item in result.forbidden))

    def test_json_output_is_valid(self):
        fixture = load_fixture(FIXTURE_PATH)
        result = score_answer("Proverbs is wisdom literature.", fixture)

        data = json.loads(result_to_json(result))

        self.assertEqual(data["fixture_id"], "proverbs-context-basic")
        self.assertIn("score", data)
        self.assertIn("expected", data)

    def test_answer_mode_from_fixture_is_passed_to_agent_mode(self):
        captured = {}

        class FakeAgent:
            def __init__(self, config: AgentConfig):
                captured["config"] = config

            def ask(self, question: str):
                captured["question"] = question

                class Result:
                    answer_text = "Proverbs is wisdom literature."

                return Result()

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "agent.json"
            config_path.write_text(
                json.dumps(
                    {
                        "config_version": 1,
                        "adapter": "openai_compatible",
                        "base_url": "http://localhost:1234/v1",
                        "model": "local-model",
                        "profile": "minimal-7b",
                        "answer_mode": "concise",
                    }
                ),
                encoding="utf-8",
            )

            with patch("bhf_agent.eval.BHFAgent", FakeAgent):
                answer = answer_from_agent(load_fixture(FIXTURE_PATH), config_path)

        self.assertEqual(answer, "Proverbs is wisdom literature.")
        self.assertEqual(captured["config"].profile, "standard")
        self.assertEqual(captured["config"].answer_mode, "study")
        self.assertIn("Proverbs", captured["question"])

    def test_answer_file_mode_requires_no_external_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            answer_path = Path(tmp) / "answer.txt"
            answer_path.write_text(
                "Proverbs is wisdom literature. A proverb is not a mechanical "
                "promise. Start with genre and context before application.",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("bhf_agent.eval.BHFAgent") as agent_class:
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--fixture",
                            str(FIXTURE_PATH),
                            "--answer-file",
                            str(answer_path),
                            "--json",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        agent_class.assert_not_called()
        data = json.loads(stdout.getvalue())
        self.assertTrue(data["passed"])


if __name__ == "__main__":
    unittest.main()
