import contextlib
import io
import unittest
from unittest.mock import patch

from bhf_agent.__main__ import build_parser, main
from bhf_agent.models import (
    AgentResult,
    GenreContext,
    QuestionContext,
    ReferenceContext,
    ValidationResult,
)


class FakeAgent:
    def __init__(self, config):
        self.config = config

    def ask(self, question):
        return AgentResult(
            answer_text="## 1. Short Answer\nAnswer.",
            reference_context=ReferenceContext(topic="spirit", confidence=0.5),
            genre_context=GenreContext(primary_genre="not detected"),
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit"],
                confidence=0.8,
            ),
            profile_used="minimal-7b",
            validation_result=ValidationResult(
                passed=True,
                score=90,
                warnings=["example warning"],
            ),
            model_metadata={
                "adapter_type": "openai_compatible",
                "model": "fake-model",
                "local_knowledge_keys": ["ruach"],
                "cleanup_applied": True,
                "pipeline": {
                    "stages_completed": ["initialize_context", "detect_reference"],
                    "prompt_strategy": "MinimalPromptStrategy",
                },
                "raw_provider_response": {"secret": "do-not-print"},
            },
        )


class RepairAppliedAgent(FakeAgent):
    def ask(self, question):
        result = super().ask(question)
        result.repair_applied = True
        result.repair_attempted = True
        result.repair_reason = "validation score is below repair threshold"
        result.original_validation_result = ValidationResult(
            passed=False,
            score=50,
            warnings=["missing caution"],
        )
        result.repaired_validation_result = result.validation_result
        return result


class CLITests(unittest.TestCase):
    def test_repair_flags_parse(self):
        parser = build_parser()

        repair_args = parser.parse_args(
            [
                "--repair",
                "--max-repair-attempts",
                "1",
                "--repair-threshold",
                "80",
                "What does ruach mean?",
            ]
        )
        no_repair_args = parser.parse_args(
            ["--no-repair", "What does ruach mean?"]
        )

        self.assertTrue(repair_args.auto_repair)
        self.assertEqual(repair_args.max_repair_attempts, 1)
        self.assertEqual(repair_args.repair_threshold, 80)
        self.assertFalse(no_repair_args.auto_repair)

    def test_answer_mode_flag_parses(self):
        parser = build_parser()

        args = parser.parse_args(
            ["--answer-mode", "teaching", "What does Proverbs 3 mean?"]
        )

        self.assertEqual(args.answer_mode, "teaching")

    def test_memory_flags_parse(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "--memory",
                "--session-id",
                "lesson-1",
                "--memory-path",
                "/tmp/bhf-sessions",
                "--memory-max-turns",
                "3",
                "What does Proverbs 3 mean?",
            ]
        )
        no_memory_args = parser.parse_args(
            ["--no-memory", "What does Proverbs 3 mean?"]
        )

        self.assertTrue(args.memory_enabled)
        self.assertEqual(args.session_id, "lesson-1")
        self.assertEqual(args.memory_path, "/tmp/bhf-sessions")
        self.assertEqual(args.memory_max_turns, 3)
        self.assertFalse(no_memory_args.memory_enabled)

    def test_default_output_does_not_expose_pipeline_internals(self):
        stdout = io.StringIO()

        with patch("bhf_agent.__main__.BHFAgent", FakeAgent):
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-url",
                        "http://localhost:1234/v1",
                        "--model",
                        "fake-model",
                        "--profile",
                        "minimal-7b",
                        "What does ruach mean?",
                    ]
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("## 1. Short Answer", output)
        self.assertIn("Profile: minimal-7b", output)
        self.assertIn("Answer mode: study", output)
        self.assertIn("Detected question type: word_study [Hebrew]", output)
        self.assertNotIn("Debug:", output)
        self.assertNotIn("PipelineContext", output)
        self.assertNotIn("Pipeline stages completed", output)
        self.assertNotIn("Repair attempted:", output)
        self.assertNotIn("raw_provider_response", output)

    def test_default_output_shows_repair_applied_when_accepted(self):
        stdout = io.StringIO()

        with patch("bhf_agent.__main__.BHFAgent", RepairAppliedAgent):
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-url",
                        "http://localhost:1234/v1",
                        "--model",
                        "fake-model",
                        "--profile",
                        "minimal-7b",
                        "--repair",
                        "What does ruach mean?",
                    ]
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Repair applied: yes", output)
        self.assertNotIn("Repair attempted:", output)

    def test_show_debug_prints_safe_metadata(self):
        stdout = io.StringIO()

        with patch("bhf_agent.__main__.BHFAgent", FakeAgent):
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-url",
                        "http://user:secret@localhost:1234/v1",
                        "--model",
                        "fake-model",
                        "--profile",
                        "minimal-7b",
                        "--show-debug",
                        "What does ruach mean?",
                    ]
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Debug:", output)
        self.assertIn("Base URL: http://localhost:1234/v1", output)
        self.assertIn(
            "Pipeline stages completed: initialize_context, detect_reference",
            output,
        )
        self.assertIn("Prompt strategy: MinimalPromptStrategy", output)
        self.assertIn("Answer mode: study", output)
        self.assertIn("Auto repair: false", output)
        self.assertIn("Repair threshold: 80", output)
        self.assertIn("Max repair attempts: 1", output)
        self.assertIn("Repair attempted: false", output)
        self.assertIn("Repair applied: false", output)
        self.assertIn("Memory enabled: false", output)
        self.assertIn("Memory max turns: 8", output)
        self.assertIn("Local knowledge used: ruach", output)
        self.assertIn("Output cleanup applied: true", output)
        self.assertNotIn("secret", output)
        self.assertNotIn("raw_provider_response", output)

    def test_show_debug_prints_repair_metadata(self):
        stdout = io.StringIO()

        with patch("bhf_agent.__main__.BHFAgent", RepairAppliedAgent):
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--base-url",
                        "http://localhost:1234/v1",
                        "--model",
                        "fake-model",
                        "--profile",
                        "minimal-7b",
                        "--repair",
                        "--show-debug",
                        "What does ruach mean?",
                    ]
                )

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Auto repair: true", output)
        self.assertIn("Repair attempted: true", output)
        self.assertIn("Repair applied: true", output)
        self.assertIn("Original validation score: 50", output)
        self.assertIn("Repaired validation score: 90", output)
        self.assertNotIn("raw_provider_response", output)


if __name__ == "__main__":
    unittest.main()
