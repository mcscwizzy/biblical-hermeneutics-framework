import unittest

from bhf_agent.models import QuestionContext
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

    def test_word_study_with_ruach_semantic_range_and_context_passes(self):
        result = validate_response(
            "Short Answer: The Hebrew word is ruach. Basic Meaning: its semantic "
            "range can include wind, breath, or spirit. Context Matters: the "
            "meaning depends on the passage context. Cautions: it may not always "
            "refer to the Holy Spirit.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score, 70)

    def test_word_study_cautions_heading_counts_as_uncertainty_label(self):
        result = validate_response(
            "## 1. Short Answer: The Hebrew word is ruach. "
            "## 2. Basic Meaning: its semantic range can include wind, breath, or spirit. "
            "## 3. Context Matters: the meaning depends on the passage context. "
            "## 4. Examples: Genesis 1:2 and Ezekiel 37 are cautious examples. "
            "## 5. Cautions: it should not be flattened into a single doctrine.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertTrue(result.passed)
        self.assertNotIn("Caution or uncertainty is not clearly labeled.", result.warnings)

    def test_word_study_missing_context_dependence_warns(self):
        result = validate_response(
            "The Hebrew word is ruach. Its semantic range can include wind, "
            "breath, or spirit. This may vary.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertIn("Context dependence is not clearly explained.", result.warnings)

    def test_word_study_literally_means_holy_spirit_warns(self):
        result = validate_response(
            "Ruach literally means Holy Spirit.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertIn(
            "Possible overclaim: ruach/pneuma is equated too directly with Holy Spirit.",
            result.warnings,
        )

    def test_word_study_nephesh_or_qol_expansion_warns_for_spirit_wind(self):
        result = validate_response(
            "The Hebrew word is ruach. Its semantic range can include wind, "
            "breath, or spirit. Context Matters: meaning depends on context. "
            "Nephesh and qol are also terms to consider. This may be uncertain.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertIn(
            "The answer may be treating nephesh or qol as primary answers for spirit/wind.",
            result.warnings,
        )

    def test_word_study_cautionary_nephesh_qol_contrast_does_not_warn(self):
        result = validate_response(
            "The Hebrew word is ruach. Its semantic range can include wind, "
            "breath, or spirit. Context Matters: meaning depends on context. "
            "Nephesh is not the normal Hebrew word for wind, and qol is not "
            "the primary answer for spirit or wind. Cautions: this may vary.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertNotIn(
            "The answer may be treating nephesh or qol as primary answers for spirit/wind.",
            result.warnings,
        )

    def test_hebrew_spirit_wind_missing_ruach_warns(self):
        result = validate_response(
            "The Hebrew answer is uncertain. Basic Meaning: spirit can mean "
            "several things. Context Matters: meaning depends on context. "
            "Cautions: this may vary.",
            question_context=QuestionContext(
                question_type="word_study",
                target_language="Hebrew",
                target_terms=["spirit", "wind"],
                confidence=0.9,
            ),
        )

        self.assertIn(
            "The Hebrew spirit/wind answer does not clearly mention ruach.",
            result.warnings,
        )


if __name__ == "__main__":
    unittest.main()
