import unittest

from bhf_agent.validation import validate_response


class ResponseValidationTests(unittest.TestCase):
    def test_valid_method_response_passes(self):
        result = validate_response(
            "Original audience: first-century readers. Genre: epistle. "
            "Observation: the text says this. Interpretation: it likely means "
            "this in context. Application: modern readers may consider this. "
            "Some scholars debate details, so confidence is moderate."
        )

        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score, 70)

    def test_missing_method_markers_warns_without_theology_policing(self):
        result = validate_response("This verse tells you what to do today.")

        self.assertFalse(result.passed)
        self.assertIn("Genre is not clearly identified.", result.warnings)

    def test_flags_doctrinal_overreach(self):
        result = validate_response(
            "Original audience and genre are considered. Observation, "
            "interpretation, and application are present. The only faithful view "
            "is this one."
        )

        self.assertFalse(result.passed)
        self.assertIn("Possible doctrinal overreach detected.", result.warnings)

    def test_flags_unqualified_language_claim(self):
        result = validate_response(
            "Original audience matters. Genre: Gospel. Observation, interpretation, "
            "and application are distinct. The Hebrew literally means this."
        )

        self.assertIn(
            "Possible unsupported original-language claim detected.",
            result.warnings,
        )


if __name__ == "__main__":
    unittest.main()
