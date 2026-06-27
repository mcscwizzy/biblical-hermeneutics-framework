import unittest

from bhf_agent.output_cleaner import clean_model_output


class OutputCleanerTests(unittest.TestCase):
    def test_removes_leading_runtime_instruction_block(self):
        result = clean_model_output(
            "# BHF Agent Runtime Instructions\n\n"
            "Use the BHF profile as method guidance.\n\n"
            "# Minimal Runtime Strategy\n\n"
            "Keep answers short.\n\n"
            "## 1. Short Answer\n"
            "The Hebrew word is ruach."
        )

        self.assertTrue(result.applied)
        self.assertIn("BHF Agent Runtime Instructions", result.removed_headings)
        self.assertEqual(
            result.text,
            "## 1. Short Answer\nThe Hebrew word is ruach.",
        )

    def test_does_not_remove_normal_answer_content(self):
        answer = (
            "## 1. Short Answer\n"
            "The Hebrew word is ruach.\n\n"
            "## 5. Cautions\n"
            "Method matters, but this is user-facing content."
        )

        result = clean_model_output(answer)

        self.assertFalse(result.applied)
        self.assertEqual(result.text, answer)

    def test_detects_cleanup_status_when_no_answer_heading_exists(self):
        answer = "# BHF Agent Runtime Instructions\nUse the profile."

        result = clean_model_output(answer)

        self.assertFalse(result.applied)
        self.assertEqual(result.text, answer)


if __name__ == "__main__":
    unittest.main()
