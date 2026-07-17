import json
import unittest

from bhf_agent.model_response_validation import (
    ANSWER_CONTRACT,
    SEARCH_RESULTS_CONTRACT,
    normalize_model_response,
)


class ModelResponseValidationTests(unittest.TestCase):
    def test_answer_contract_extracts_structured_answer_field(self):
        result = normalize_model_response(
            '```json\n{"answer":"## 1. Short Answer\\nShechem matters."}\n```',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
        self.assertTrue(result.raw_text_was_json)
        self.assertEqual(result.sanitized_text, "## 1. Short Answer\nShechem matters.")

    def test_answer_contract_extracts_structured_answer_text_alias(self):
        result = normalize_model_response(
            '{"answer_text":"## 1. Short Answer\\nShechem matters."}',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
        self.assertTrue(result.raw_text_was_json)
        self.assertEqual(result.sanitized_text, "## 1. Short Answer\nShechem matters.")

    def test_answer_contract_extracts_common_local_model_response_alias(self):
        result = normalize_model_response(
            '{"response":"## 1. Short Answer\\nFollow Jesus by trusting and obeying him."}',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
        self.assertEqual(
            result.sanitized_text,
            "## 1. Short Answer\nFollow Jesus by trusting and obeying him.",
        )

    def test_answer_contract_extracts_chat_completion_shape(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "## 1. Short Answer\nShechem matters."
                            }
                        }
                    ]
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
        self.assertEqual(result.sanitized_text, "## 1. Short Answer\nShechem matters.")

    def test_answer_contract_extracts_short_answer_sections(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "short_answer": "Shechem anchors covenant renewal.",
                    "explanation": "Joshua 24 uses the place to recall Israel's story.",
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(
            result.sanitized_text,
            "## Short Answer\nShechem anchors covenant renewal.\n\n"
            "## Explanation\nJoshua 24 uses the place to recall Israel's story.",
        )

    def test_answer_contract_removes_internal_sections_after_the_answer(self):
        result = normalize_model_response(
            "# Analysis\n\n"
            "Internal reasoning should not be shown.\n\n"
            "## 1. Short Answer\n"
            "Shechem matters because it anchors covenant renewal.\n\n"
            "Retrieved Context:\n"
            "- places/shechem.json\n"
            "- retrieval score: 0.94\n",
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertIn("Removed leaked runtime instruction headings.", result.warnings)
        self.assertIn("Removed internal analysis sections from model output.", result.warnings)
        self.assertEqual(
            result.sanitized_text,
            "## 1. Short Answer\nShechem matters because it anchors covenant renewal.",
        )
        self.assertNotIn("places/shechem.json", result.sanitized_text)
        self.assertNotIn("0.94", result.sanitized_text)

    def test_answer_contract_rejects_ckl_paths_and_scores(self):
        result = normalize_model_response(
            "## 1. Short Answer\n"
            "Shechem matters because it anchors covenant renewal.\n\n"
            "Source path: framework/canonical_library/objects/places/shechem.json\n"
            "Retrieval score: 0.94\n",
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("CKL file path", result.errors[0])
        self.assertIn("retrieval scoring metadata", " ".join(result.errors).lower())
        self.assertIn("framework/canonical_library/objects/places/shechem.json", result.sanitized_text)
        self.assertIn("0.94", result.sanitized_text)

    def test_answer_contract_rejects_json_without_answer_field(self):
        result = normalize_model_response(
            '{"analysis":"internal notes only"}',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("without an answer field", result.errors[0])

    def test_search_results_contract_preserves_structured_json(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "results": [
                        {
                            "book": "Exodus",
                            "chapter": 1,
                            "reason": "Test candidate.",
                            "confidence": "likely",
                        }
                    ]
                }
            ),
            response_contract=SEARCH_RESULTS_CONTRACT,
        )

        self.assertTrue(result.passed)
        payload = json.loads(result.sanitized_text)
        self.assertEqual(payload["results"][0]["book"], "Exodus")

    def test_provider_error_message_is_reported(self):
        result = normalize_model_response(
            "",
            raw_provider_response="OpenAI-compatible endpoint returned HTTP 500: boom",
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertTrue(result.errors)
        self.assertIn("HTTP 500", result.errors[0])


if __name__ == "__main__":
    unittest.main()
