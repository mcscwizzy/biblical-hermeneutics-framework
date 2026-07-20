import json
import unittest

from bhf_agent.model_response_validation import (
    ANSWER_CONTRACT,
    SEARCH_RESULTS_CONTRACT,
    normalize_model_response,
    structured_response_format,
)


class ModelResponseValidationTests(unittest.TestCase):
    def test_structured_response_format_can_use_json_schema(self):
        payload = structured_response_format(prefer_json_schema=True)

        self.assertEqual(payload["type"], "json_schema")
        self.assertEqual(payload["json_schema"]["name"], "bhf_answer")
        self.assertTrue(payload["json_schema"]["strict"])
        self.assertEqual(
            payload["json_schema"]["schema"]["properties"]["answer"]["minLength"],
            1,
        )

    def test_answer_contract_extracts_structured_answer_field(self):
        result = normalize_model_response(
            '```json\n{"answer":"## 1. Short Answer\\nShechem matters."}\n```',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
        self.assertTrue(result.raw_text_was_json)
        self.assertEqual(result.sanitized_text, "## 1. Short Answer\nShechem matters.")

    def test_answer_contract_accepts_markdown_prose(self):
        result = normalize_model_response(
            "## Short Answer\nShechem anchors covenant renewal.",
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "## Short Answer\nShechem anchors covenant renewal.")

    def test_empty_structured_answer_is_invalid_model_content(self):
        for payload in ("{}", "[]", '{"answer":""}', '{"answer":"   "}'):
            with self.subTest(payload=payload):
                result = normalize_model_response(payload, response_contract=ANSWER_CONTRACT)

                self.assertFalse(result.passed)
                self.assertEqual(result.sanitized_text, "")
                self.assertIn("no extractable answer text", result.errors[0].lower())

    def test_answer_contract_extracts_structured_answer_text_alias(self):
        result = normalize_model_response(
            '{"answer_text":"## 1. Short Answer\\nShechem matters."}',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
        self.assertTrue(result.raw_text_was_json)
        self.assertEqual(result.sanitized_text, "## 1. Short Answer\nShechem matters.")

    def test_answer_contract_extracts_capitalized_answer_key(self):
        result = normalize_model_response(
            '{"Answer":"## 1. Short Answer\\nShechem matters."}',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.structured_output)
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

    def test_answer_contract_extracts_generated_text_recovery(self):
        result = normalize_model_response(
            '{"generated_text":"Valid answer"}',
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "Valid answer")
        self.assertIn("Recovered answer text", " ".join(result.warnings))

    def test_answer_contract_extracts_gemini_candidate_parts(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "role": "model",
                                "parts": [
                                    {"text": "## 1. Short Answer\nShechem matters."}
                                ],
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"totalTokenCount": 25},
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "## 1. Short Answer\nShechem matters.")

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

    def test_answer_contract_extracts_nested_answer_sections(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "answer": {
                        "summary": "Yes.",
                        "explanation": "The passage indicates covenant renewal.",
                        "details": "It does so in a public covenant setting.",
                    }
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(
            result.sanitized_text,
            "## Summary\nYes.\n\n"
            "## Explanation\nThe passage indicates covenant renewal.\n\n"
            "## Details\nIt does so in a public covenant setting.",
        )

    def test_answer_contract_extracts_generic_result_envelope(self):
        result = normalize_model_response(
            json.dumps({"result": {"answer": "Valid answer"}}),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "Valid answer")

    def test_answer_contract_extracts_ollama_message_content(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "content": "Valid answer",
                    }
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "Valid answer")

    def test_answer_contract_extracts_responses_api_content_blocks(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": "First paragraph."},
                                {"type": "output_text", "text": "Second paragraph."},
                            ],
                        }
                    ]
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "First paragraph.\nSecond paragraph.")

    def test_answer_contract_extracts_multiple_text_blocks_in_order(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "First paragraph."},
                            {"type": "text", "text": "Second paragraph."},
                        ],
                    }
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "First paragraph.\nSecond paragraph.")

    def test_answer_contract_extracts_section_body_arrays(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "sections": [
                        {"heading": "Short Answer", "body": "Shechem matters."},
                        {
                            "heading": "Context",
                            "body": "Joshua 24 uses covenant renewal language.",
                        },
                    ]
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(
            result.sanitized_text,
            "Shechem matters.\nJoshua 24 uses covenant renewal language.",
        )

    def test_answer_contract_ignores_reasoning_and_keeps_answer(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "analysis": "private reasoning",
                    "answer": "Valid answer",
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.sanitized_text, "Valid answer")
        self.assertNotIn("analysis", result.sanitized_text.lower())

    def test_answer_contract_rejects_reasoning_only_response(self):
        result = normalize_model_response(
            json.dumps({"analysis": "private reasoning"}),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("no extractable answer text", result.errors[0].lower())

    def test_answer_contract_rejects_tool_call_only_response(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "tool_calls": [
                        {
                            "name": "something",
                            "arguments": {},
                        }
                    ]
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("no extractable answer text", result.errors[0].lower())

    def test_answer_contract_rejects_empty_nested_answer(self):
        result = normalize_model_response(
            json.dumps({"answer": {"summary": "", "details": ""}}),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("no extractable answer text", result.errors[0].lower())

    def test_answer_contract_rejects_ambiguous_unknown_strings(self):
        result = normalize_model_response(
            json.dumps(
                {
                    "prompt": "internal prompt",
                    "analysis": "private reasoning",
                    "generated_text": "Valid answer",
                    "completion": "Also valid",
                }
            ),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("no extractable answer text", result.errors[0].lower())

    def test_answer_contract_rejects_excessive_recursion_depth(self):
        payload: dict[str, object] = {"answer": "Valid answer"}
        for _ in range(8):
            payload = {"data": payload}

        result = normalize_model_response(
            json.dumps(payload),
            response_contract=ANSWER_CONTRACT,
        )

        self.assertFalse(result.passed)
        self.assertIn("no extractable answer text", result.errors[0].lower())

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
        with self.assertLogs("bhf_agent.model_response_validation", level="WARNING") as logs:
            result = normalize_model_response(
                '{"analysis":"internal notes only"}',
                response_contract=ANSWER_CONTRACT,
            )

        self.assertFalse(result.passed)
        self.assertIn("no extractable answer text", result.errors[0].lower())
        self.assertTrue(logs.output)
        self.assertIn("top_level_keys", logs.output[0])

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
