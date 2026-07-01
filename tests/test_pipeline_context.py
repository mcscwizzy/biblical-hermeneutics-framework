import unittest

from bhf_agent.models import PipelineContext


class PipelineContextTests(unittest.TestCase):
    def test_can_initialize_with_only_original_question(self):
        ctx = PipelineContext(original_question="What does John 3:16 mean?")

        self.assertEqual(ctx.original_question, "What does John 3:16 mean?")
        self.assertIsNone(ctx.normalized_question)
        self.assertIsNone(ctx.reference_context)
        self.assertIsNone(ctx.genre_context)
        self.assertIsNone(ctx.question_context)
        self.assertIsNone(ctx.local_knowledge)
        self.assertIsNone(ctx.raw_model_response)
        self.assertIsNone(ctx.final_answer)

    def test_defaults_are_safe_mutable_values(self):
        first = PipelineContext(original_question="First?")
        second = PipelineContext(original_question="Second?")

        first.debug_metadata["stages_completed"] = ["initialize_context"]
        first.warnings.append("warning")
        first.errors.append("error")

        self.assertEqual(second.debug_metadata, {})
        self.assertEqual(second.warnings, [])
        self.assertEqual(second.errors, [])


if __name__ == "__main__":
    unittest.main()
