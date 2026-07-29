import unittest

from bhf_agent.config import AgentConfig, ConfigError, KnowledgeExpansionConfig
from bhf_agent.coverage import (
    BROAD_KNOWLEDGE_EXPANSION,
    CKL_PRIMARY,
    TARGETED_GAP_EXPANSION,
    detect_research_intent,
    evaluate_answer_coverage,
)
from bhf_agent.models import GenreContext, QuestionContext, ReferenceContext


class CoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = ReferenceContext(
            book="Ruth", chapter=4, is_reference_based=True, confidence=0.9
        )
        self.genre = GenreContext(primary_genre="narrative", confidence=0.9)
        self.question_context = QuestionContext("passage_study", confidence=0.9)
        self.context = {
            "retrieved_topics": [
                {
                    "id": "ruth",
                    "title": "Ruth",
                    "summary": "Ruth and Boaz marry and the nearer redeemer refuses.",
                    "scripture_references": ["Ruth 4:1-12"],
                    "metadata": {"primary_topic_count": 1},
                }
            ],
            "metadata": {"primary_topic_count": 1},
        }

    def assess(self, question: str, context=None, **kwargs):
        return evaluate_answer_coverage(
            question=question,
            reference_context=self.reference,
            genre_context=self.genre,
            question_context=self.question_context,
            canonical_context=context if context is not None else self.context,
            canonical_strong_match=True,
            ckl_coverage_gap=None,
            local_knowledge={},
            **kwargs,
        )

    def test_direct_question_can_be_ckl_primary(self):
        assessment = self.assess("Who was Boaz?")
        self.assertEqual(assessment.mode, CKL_PRIMARY)
        self.assertGreaterEqual(assessment.score, 0.85)

    def test_relevant_context_can_have_a_targeted_gap(self):
        assessment = self.assess(
            "Why did the nearer redeemer say redeeming Ruth would endanger his inheritance?"
        )
        self.assertEqual(assessment.mode, TARGETED_GAP_EXPANSION)
        self.assertIn("exact financial or inheritance risk", assessment.missing_dimensions)

    def test_missing_context_is_broad(self):
        assessment = evaluate_answer_coverage(
            question="How does this compare with an uncovered treaty pattern?",
            reference_context=self.reference,
            genre_context=self.genre,
            question_context=self.question_context,
            canonical_context=None,
            canonical_strong_match=False,
            ckl_coverage_gap={"rejection_reasons": ["no_relevant_ckl_results"]},
            local_knowledge=None,
        )
        self.assertEqual(assessment.mode, BROAD_KNOWLEDGE_EXPANSION)

    def test_research_intent_is_specific_not_keyword_only(self):
        self.assertTrue(detect_research_intent("What are the major scholarly interpretations?").detected)
        self.assertTrue(detect_research_intent("What does archaeology tell us about this city?").detected)
        self.assertFalse(detect_research_intent("Who was Timothy?").detected)
        self.assertFalse(detect_research_intent("The scholar mentioned a person named Timothy.").detected)

    def test_research_override_applies_to_strong_context(self):
        assessment = self.assess("What are the major scholarly interpretations of this passage?")
        self.assertTrue(assessment.research_override)
        self.assertEqual(assessment.mode, TARGETED_GAP_EXPANSION)

    def test_missing_dimensions_are_bounded(self):
        assessment = self.assess(
            "What are the major scholarly interpretations, manuscript evidence, archaeology, and Second Temple context?",
            max_gap_items=2,
        )
        self.assertLessEqual(len(assessment.missing_dimensions), 2)


class KnowledgeExpansionConfigTests(unittest.TestCase):
    def test_defaults_and_json_mapping(self):
        config = AgentConfig.from_mapping(
            {
                "adapter": "ollama",
                "base_url": "http://localhost:11434",
                "model": "local-model",
                "knowledge_expansion": {"max_gap_items": 4},
            }
        )
        self.assertEqual(config.knowledge_expansion.sufficient_coverage_threshold, 0.85)
        self.assertEqual(config.knowledge_expansion.major_gap_threshold, 0.60)
        self.assertEqual(config.knowledge_expansion.max_gap_items, 4)

    def test_invalid_thresholds_fail(self):
        with self.assertRaises(ConfigError):
            KnowledgeExpansionConfig(sufficient_coverage_threshold=1.1).validate()
        with self.assertRaises(ConfigError):
            KnowledgeExpansionConfig(major_gap_threshold=0.85).validate()
        with self.assertRaises(ConfigError):
            KnowledgeExpansionConfig(max_gap_items=0).validate()
