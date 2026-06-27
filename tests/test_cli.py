import contextlib
import io
import unittest
from unittest.mock import patch

from bhf_agent.__main__ import main
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


class CLITests(unittest.TestCase):
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
        self.assertIn("Detected question type: word_study [Hebrew]", output)
        self.assertNotIn("Debug:", output)
        self.assertNotIn("PipelineContext", output)
        self.assertNotIn("Pipeline stages completed", output)
        self.assertNotIn("raw_provider_response", output)

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
        self.assertIn("Local knowledge used: ruach", output)
        self.assertIn("Output cleanup applied: true", output)
        self.assertNotIn("secret", output)
        self.assertNotIn("raw_provider_response", output)


if __name__ == "__main__":
    unittest.main()
