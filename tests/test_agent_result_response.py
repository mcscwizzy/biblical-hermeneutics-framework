import unittest

from bhf_agent.models import (
    AgentResult,
    GenreContext,
    QuestionContext,
    ReferenceContext,
    ValidationResult,
)


class AgentResultResponseTests(unittest.TestCase):
    def _make_result(self) -> AgentResult:
        return AgentResult(
            answer_text="Shechem matters because of covenant renewal.",
            reference_context=ReferenceContext(),
            genre_context=GenreContext(),
            question_context=QuestionContext(question_type="context"),
            profile_used="minimal-7b",
            validation_result=ValidationResult(passed=True, score=90),
            model_metadata={
                "adapter_type": "openai",
                "configured_model": "gpt-5-mini",
                "canonical_library_object_ids": ["shechem"],
                "canonical_library_prompt_tokens": 321,
            },
        )

    def test_public_response_exposes_only_answer(self):
        result = self._make_result()

        self.assertEqual(
            result.public_response(),
            {"answer": "Shechem matters because of covenant renewal."},
        )

    def test_internal_response_groups_internal_details(self):
        result = self._make_result()

        internal = result.internal_response()

        self.assertEqual(
            internal,
            {
                "answer": "Shechem matters because of covenant renewal.",
                "retrieval": {
                    "result_count": 1,
                    "entry_ids": ["shechem"],
                    "context_tokens": 321,
                },
                "model": {
                    "provider": "openai",
                    "model": "gpt-5-mini",
                },
            },
        )
