import shutil
import tempfile
import unittest
from pathlib import Path

from bhf_agent.adapters import ChatAdapter
from bhf_agent.config import AgentConfig
from bhf_agent.models import ChatRequest, ChatResponse
from bhf_agent.profiles import ProfileLoader
from bhf_agent.runner import BHFAgent


class RecordingAdapter(ChatAdapter):
    def __init__(self) -> None:
        self.request: ChatRequest | None = None

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        return ChatResponse(
            text=(
                "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                "semantic range can include wind, breath, or spirit. Context "
                "Matters: meaning depends on passage context. Cautions: this "
                "may not always refer to the Holy Spirit."
            ),
            model="fake-model",
        )


class SequenceAdapter(ChatAdapter):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        index = len(self.requests) - 1
        text = self.responses[index] if index < len(self.responses) else self.responses[-1]
        return ChatResponse(text=text, model="fake-model")


class LeakyAdapter(ChatAdapter):
    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            text=(
                "# BHF Agent Runtime Instructions\n\n"
                "Use the BHF profile as method guidance.\n\n"
                "# Minimal Runtime Strategy\n\n"
                "Keep answers short.\n\n"
                "## 1. Short Answer\n"
                "The Hebrew word is ruach.\n\n"
                "## 2. Basic Meaning\n"
                "Its semantic range can include wind, breath, or spirit.\n\n"
                "## 3. Context Matters\n"
                "Meaning depends on passage context.\n\n"
                "## 5. Cautions\n"
                "Caution: it may not always refer to the Holy Spirit."
            ),
            model="fake-model",
        )


class PromptStageAssertingAgent(BHFAgent):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.system_prompt_before_model: str | None = None
        self.user_prompt_before_model: str | None = None

    def _call_model(self, ctx):
        self.system_prompt_before_model = ctx.system_prompt
        self.user_prompt_before_model = ctx.user_prompt
        return super()._call_model(ctx)


class RunnerTests(unittest.TestCase):
    def make_agent(self, adapter: ChatAdapter, **config_overrides) -> BHFAgent:
        profiles_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, profiles_dir, ignore_errors=True)
        (profiles_dir / "minimal-7b.md").write_text("PROFILE", encoding="utf-8")
        (profiles_dir / "standard.md").write_text("PROFILE", encoding="utf-8")
        values = {
            "base_url": "http://localhost:1234/v1",
            "model": "fake-model",
            "profile": "minimal-7b",
        }
        values.update(config_overrides)
        return BHFAgent(
            AgentConfig(**values),
            adapter=adapter,
            profile_loader=ProfileLoader(profiles_dir),
        )

    def test_agent_result_includes_question_context_and_prompt_receives_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp)
            (profiles_dir / "minimal-7b.md").write_text("PROFILE", encoding="utf-8")
            adapter = RecordingAdapter()
            agent = BHFAgent(
                AgentConfig(
                    base_url="http://localhost:1234/v1",
                    model="fake-model",
                    profile="minimal-7b",
                ),
                adapter=adapter,
                profile_loader=ProfileLoader(profiles_dir),
            )

            result = agent.ask("What is the hebrew word for the word spirit or wind?")

        self.assertEqual(result.question_context.question_type, "word_study")
        self.assertEqual(result.question_context.target_language, "Hebrew")
        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertEqual(
            adapter.request.metadata["question_context"]["question_type"],
            "word_study",
        )
        self.assertEqual(adapter.request.metadata["answer_mode"], "study")
        self.assertIn("Question type: word_study", adapter.request.system_prompt)
        self.assertIn("Answer using the word-study format exactly", adapter.request.user_prompt)
        self.assertFalse(result.reference_context.is_reference_based)
        self.assertEqual(
            result.reference_context.topic,
            "What is the hebrew word for the word spirit or wind",
        )
        self.assertEqual(result.genre_context.recommended_modules, ["core.genre-awareness"])
        self.assertEqual(result.profile_used, "minimal-7b")
        self.assertTrue(result.validation_result.passed)
        self.assertIn("pipeline", result.model_metadata)
        self.assertIn(
            "detect_reference",
            result.model_metadata["pipeline"]["stages_completed"],
        )
        self.assertIn(
            "classify_question_type",
            result.model_metadata["pipeline"]["stages_completed"],
        )
        self.assertIn(
            "classify_genre",
            result.model_metadata["pipeline"]["stages_completed"],
        )
        self.assertIn(
            "build_prompts",
            result.model_metadata["pipeline"]["stages_completed"],
        )
        self.assertEqual(
            result.model_metadata["pipeline"]["prompt_strategy"],
            "MinimalPromptStrategy",
        )
        self.assertEqual(result.model_metadata["answer_mode"], "study")
        self.assertEqual(result.model_metadata["pipeline"]["answer_mode"], "study")
        self.assertEqual(result.model_metadata["pipeline"]["validation_score"], 100)

    def test_answer_mode_threads_to_prompt_request_and_result_metadata(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(adapter, answer_mode="teaching")

        result = agent.ask("What does Proverbs 3 mean?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertEqual(adapter.request.metadata["answer_mode"], "teaching")
        self.assertIn("Answer Mode: Teaching", adapter.request.system_prompt)
        self.assertEqual(result.model_metadata["answer_mode"], "teaching")
        self.assertEqual(result.model_metadata["pipeline"]["answer_mode"], "teaching")

    def test_progress_callback_receives_pipeline_statuses(self):
        events = []
        profiles_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, profiles_dir, ignore_errors=True)
        (profiles_dir / "minimal-7b.md").write_text("PROFILE", encoding="utf-8")
        agent = BHFAgent(
            AgentConfig(
                base_url="http://localhost:1234/v1",
                model="fake-model",
                profile="minimal-7b",
            ),
            adapter=RecordingAdapter(),
            profile_loader=ProfileLoader(profiles_dir),
            progress_callback=lambda stage, message: events.append((stage, message)),
        )

        agent.ask("What does Proverbs 3 mean?")

        stages = [stage for stage, _message in events]
        self.assertIn("preparing_request", stages)
        self.assertIn("detecting_reference", stages)
        self.assertIn("selecting_profile", stages)
        self.assertIn("applying_framework", stages)
        self.assertIn("contacting_model", stages)
        self.assertIn("waiting_for_model", stages)
        self.assertIn("validating_response", stages)
        self.assertIn("formatting_answer", stages)
        self.assertEqual(stages[-1], "complete")

    def test_debug_metadata_includes_local_book_and_genre_keys(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(adapter, profile="standard")

        result = agent.ask("What does Proverbs 3 mean?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertIn("Book context (book:Proverbs)", adapter.request.system_prompt)
        self.assertIn(
            "Genre guide (genre:wisdom literature)",
            adapter.request.system_prompt,
        )
        self.assertIn("book:Proverbs", result.model_metadata["local_knowledge_keys"])
        self.assertIn(
            "genre:wisdom literature",
            result.model_metadata["pipeline"]["local_knowledge_keys"],
        )

    def test_agent_result_uses_cleaned_answer_and_debug_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp)
            (profiles_dir / "minimal-7b.md").write_text("PROFILE", encoding="utf-8")
            agent = BHFAgent(
                AgentConfig(
                    base_url="http://localhost:1234/v1",
                    model="fake-model",
                    profile="minimal-7b",
                    debug=True,
                ),
                adapter=LeakyAdapter(),
                profile_loader=ProfileLoader(profiles_dir),
            )

            result = agent.ask("What is the hebrew word for the word spirit or wind?")

        self.assertTrue(result.answer_text.startswith("## 1. Short Answer"))
        self.assertNotIn("BHF Agent Runtime Instructions", result.answer_text)
        self.assertTrue(result.model_metadata["cleanup_applied"])
        self.assertIn("raw_model_text", result.model_metadata)
        self.assertIn("ruach", result.model_metadata["local_knowledge_keys"])
        self.assertIn("nephesh", result.model_metadata["local_knowledge_keys"])
        self.assertIn("qol", result.model_metadata["local_knowledge_keys"])
        self.assertEqual(
            result.model_metadata["pipeline"]["local_knowledge_keys"],
            ["ruach", "nephesh", "qol"],
        )
        self.assertTrue(result.model_metadata["pipeline"]["output_cleanup_applied"])
        self.assertIn("call_model", result.model_metadata["pipeline"]["stages_completed"])
        self.assertIn("clean_output", result.model_metadata["pipeline"]["stages_completed"])
        self.assertIn(
            "finalize_result",
            result.model_metadata["pipeline"]["stages_completed"],
        )

    def test_repair_disabled_calls_adapter_once(self):
        adapter = SequenceAdapter(["The Hebrew word is ruach."])
        agent = self.make_agent(adapter, auto_repair=False)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertEqual(len(adapter.requests), 1)
        self.assertFalse(result.repair_attempted)
        self.assertFalse(result.repair_applied)
        self.assertEqual(result.answer_text, "The Hebrew word is ruach.")

    def test_repair_enabled_but_validation_passes_calls_adapter_once(self):
        adapter = SequenceAdapter(
            [
                "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                "semantic range can include wind, breath, or spirit. Context "
                "Matters: meaning depends on passage context. Cautions: this "
                "may not always refer to the Holy Spirit."
            ]
        )
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertEqual(len(adapter.requests), 1)
        self.assertFalse(result.repair_attempted)
        self.assertFalse(result.repair_applied)

    def test_repair_enabled_and_validation_fails_calls_adapter_twice(self):
        adapter = SequenceAdapter(
            [
                "The Hebrew word is ruach.",
                "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                "semantic range can include wind, breath, or spirit. Context "
                "Matters: meaning depends on passage context. Cautions: this "
                "may not always refer to the Holy Spirit.",
            ]
        )
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertEqual(len(adapter.requests), 2)
        self.assertTrue(adapter.requests[1].metadata["repair"])
        self.assertTrue(result.repair_attempted)
        self.assertTrue(result.repair_applied)

    def test_better_repaired_answer_is_accepted_and_validation_is_final(self):
        adapter = SequenceAdapter(
            [
                "The Hebrew word is ruach.",
                "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                "semantic range can include wind, breath, or spirit. Context "
                "Matters: meaning depends on passage context. Cautions: this "
                "may not always refer to the Holy Spirit.",
            ]
        )
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertIn("semantic range", result.answer_text)
        self.assertTrue(result.validation_result.passed)
        self.assertEqual(result.validation_result.score, 100)
        self.assertIsNotNone(result.original_validation_result)
        assert result.original_validation_result is not None
        self.assertLess(result.original_validation_result.score, result.validation_result.score)
        self.assertIsNotNone(result.repaired_validation_result)

    def test_worse_repaired_answer_is_rejected(self):
        adapter = SequenceAdapter(
            [
                "The Hebrew word is ruach. Its semantic range can include wind, "
                "breath, or spirit.",
                "I am uncertain.",
            ]
        )
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertEqual(len(adapter.requests), 2)
        self.assertFalse(result.repair_applied)
        self.assertIn("semantic range", result.answer_text)
        self.assertTrue(
            any("Repair was attempted but rejected" in warning for warning in result.warnings)
        )

    def test_empty_repaired_answer_is_rejected(self):
        adapter = SequenceAdapter(["The Hebrew word is ruach.", "   "])
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertEqual(len(adapter.requests), 2)
        self.assertFalse(result.repair_applied)
        self.assertEqual(result.answer_text, "The Hebrew word is ruach.")
        self.assertIn("Repair was attempted but returned an empty answer.", result.warnings)

    def test_pipeline_stores_prompts_before_model_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            profiles_dir = Path(tmp)
            (profiles_dir / "minimal-7b.md").write_text("PROFILE", encoding="utf-8")
            agent = PromptStageAssertingAgent(
                AgentConfig(
                    base_url="http://localhost:1234/v1",
                    model="fake-model",
                    profile="minimal-7b",
                ),
                adapter=RecordingAdapter(),
                profile_loader=ProfileLoader(profiles_dir),
            )

            result = agent.ask("What is the hebrew word for the word spirit or wind?")

        self.assertIsNotNone(agent.system_prompt_before_model)
        self.assertIsNotNone(agent.user_prompt_before_model)
        assert agent.system_prompt_before_model is not None
        assert agent.user_prompt_before_model is not None
        self.assertIn("PROFILE", agent.system_prompt_before_model)
        self.assertIn("Question type: word_study", agent.system_prompt_before_model)
        self.assertIn("Answer using the word-study format exactly", agent.user_prompt_before_model)
        self.assertIn("call_model", result.model_metadata["pipeline"]["stages_completed"])


if __name__ == "__main__":
    unittest.main()
