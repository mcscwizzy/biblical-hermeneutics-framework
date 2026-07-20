import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bhf_agent.adapters import ChatAdapter
from bhf_agent.adapters.ollama import OllamaAdapter
from bhf_agent.config import AgentConfig
from bhf_agent.config import CanonicalLibraryConfig
from bhf_agent.config import ObservabilityConfig
from bhf_agent.models import ChatRequest, ChatResponse
from bhf_agent.profiles import ProfileLoader
from bhf_agent.runner import BHFAgent
from framework.canonical_library import (
    PublicCacheEntry,
    load_framework_version,
    load_framework_version_fingerprint,
    normalize_public_question,
)


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


class StructuredJsonAdapter(ChatAdapter):
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.request: ChatRequest | None = None

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        return ChatResponse(text=self.response_text, model="fake-model")


class JsonSchemaAdapter(StructuredJsonAdapter):
    def supports_json_schema_response_format(self) -> bool:
        return True


class ErrorAdapter(ChatAdapter):
    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(
            text="",
            errors=["OpenAI-compatible endpoint timed out: timed out"],
        )


class RaisingAdapter(ChatAdapter):
    def chat(self, request: ChatRequest) -> ChatResponse:
        raise RuntimeError("adapter failed")


class ErrorRecordingAdapter(ChatAdapter):
    def __init__(self, error_message: str = "OpenAI-compatible endpoint timed out: timed out") -> None:
        self.error_message = error_message
        self.request: ChatRequest | None = None

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        return ChatResponse(
            text="",
            model="fake-model",
            errors=[self.error_message],
        )


def ckl_weak_context_stub() -> dict[str, object]:
    return {
        "question": "Why is Shechem important in Joshua 24?",
        "query": "Shechem Joshua 24",
        "retrieved_object_ids": ["shechem"],
        "retrieved_topics": [
            {
                "id": "shechem",
                "title": "Shechem",
                "type": "place",
                "review_status": "approved",
                "content_status": "complete",
                "confidence": "weak",
                "match_type": "keyword",
                "reason": "Weak keyword overlap only.",
                "matched_fields": ["summary"],
                "matched_terms": ["shechem"],
                "score": 0.2,
                "aliases": ["Shechem"],
                "summary": "A covenant location in the hill country of Ephraim.",
                "scripture_references": [],
                "related_objects": [],
            }
        ],
        "metadata": {
            "retrieval_method": "keyword",
            "query": "Shechem Joshua 24",
            "retrieved_object_ids": ["shechem"],
            "topic_count": 1,
            "primary_topic_count": 0,
            "scripture_topic_count": 0,
            "expanded_topic_count": 0,
            "answer_mode": "study",
            "max_results": 5,
            "max_context_tokens": 1200,
        },
    }


def ckl_miss_gap(
    reason: str | list[str],
    *,
    normalized_question: str,
    answer_mode: str = "study",
    top_rejected_results: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rejection_reasons = [reason] if isinstance(reason, str) else list(reason)
    return {
        "normalized_question": normalized_question,
        "detected_scripture_references": [],
        "detected_books": [],
        "retrieval_terms": [],
        "top_rejected_results": top_rejected_results or [],
        "rejection_reasons": rejection_reasons,
        "timestamp": "2026-07-16T00:00:00Z",
        "answer_mode": answer_mode,
    }


class RecordingPublicAnswerCache:
    def __init__(self, entry: PublicCacheEntry | None = None) -> None:
        self.entry = entry
        self.lookup_calls: list[dict[str, str | None]] = []
        self.increment_calls: list[tuple[str, str]] = []
        self.last_lookup_status = "miss"
        self.last_lookup_reason: str | None = None
        self.last_lookup_key: str | None = None
        self.last_lookup_entry: PublicCacheEntry | None = None

    def lookup(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        *,
        ckl_version_fingerprint: str | None = None,
        framework_version_fingerprint: str | None = None,
    ) -> PublicCacheEntry | None:
        self.lookup_calls.append(
            {
                "normalized_question": normalized_question,
                "answer_mode": answer_mode,
                "ckl_version_fingerprint": ckl_version_fingerprint,
                "framework_version_fingerprint": framework_version_fingerprint,
            }
        )
        self.last_lookup_key = f"{normalized_question}\u0000{answer_mode}"
        if self.entry is None:
            self.last_lookup_status = "miss"
            self.last_lookup_reason = "no entry configured"
            self.last_lookup_entry = None
            return None
        self.last_lookup_status = "hit"
        self.last_lookup_reason = None
        self.last_lookup_entry = self.entry
        return self.entry

    def store(self, entry: PublicCacheEntry) -> None:
        self.entry = entry

    def increment_usage(self, normalized_question: str, answer_mode: str = "study") -> None:
        self.increment_calls.append((normalized_question, answer_mode))

    def update_review_status(self, normalized_question: str, answer_mode: str = "study", status: str = "") -> None:
        return None


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
    def make_agent(
        self,
        adapter: ChatAdapter,
        public_answer_cache=None,
        ckl_library=None,
        **config_overrides,
    ) -> BHFAgent:
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
        if ckl_library is not None and "canonical_library" not in values:
            values["canonical_library"] = CanonicalLibraryConfig(
                enabled=True,
                cache_enabled=False,
            )
        return BHFAgent(
            AgentConfig(**values),
            adapter=adapter,
            profile_loader=ProfileLoader(profiles_dir),
            public_answer_cache=public_answer_cache,
            canonical_library=ckl_library,
        )

    def make_ckl_agent(
        self,
        adapter: ChatAdapter,
        public_answer_cache=None,
        **config_overrides,
    ) -> BHFAgent:
        values = dict(config_overrides)
        values.setdefault(
            "canonical_library",
            CanonicalLibraryConfig(
                enabled=True,
                cache_enabled=False,
            ),
        )
        ckl_library = object()
        return self.make_agent(
            adapter,
            public_answer_cache=public_answer_cache,
            ckl_library=ckl_library,
            **values,
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

    def test_agent_retrieves_map_context_for_archaeology_questions(self):
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

            result = agent.ask("What archaeology is connected with John 9?")

        assert adapter.request is not None
        self.assertIn("map_tool_keys", adapter.request.metadata)
        self.assertIn("getArchaeologyForPassage", adapter.request.metadata["map_tool_keys"])
        self.assertIn("Retrieved Map / Archaeology Context", adapter.request.system_prompt)
        self.assertIn("Do not invent missing geography, archaeology, manuscript, or route claims", adapter.request.system_prompt)
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
        self.assertIn("validation_score", result.model_metadata["pipeline"])
        self.assertGreaterEqual(result.model_metadata["pipeline"]["validation_score"], 0)

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

    def test_agent_ask_works_without_status_callback(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(adapter)

        result = agent.ask("What is the hebrew word for the word spirit or wind?")

        self.assertIn("Short Answer", result.answer_text)
        self.assertIn("pipeline", result.model_metadata)
        self.assertIn(
            "finalize_result",
            result.model_metadata["pipeline"]["stages_completed"],
        )

    def test_status_callback_receives_ordered_pipeline_events(self):
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
        )

        agent.ask("What does Proverbs 3 mean?", status_callback=events.append)

        stages = [event["stage"] for event in events]
        required_order = [
            "queued",
            "preparing_request",
            "detecting_reference",
            "classifying_genre",
            "classifying_question_type",
            "loading_profile",
            "checking_local_knowledge",
            "building_prompt",
            "contacting_model_backend",
            "waiting_for_model_response",
            "model_response_received",
            "cleaning_output",
            "validating_response",
            "formatting_answer",
            "complete",
        ]
        positions = [stages.index(stage) for stage in required_order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Preparing request", [event["message"] for event in events])
        self.assertIn("Detecting biblical reference", [event["message"] for event in events])
        self.assertIn("Classifying genre", [event["message"] for event in events])
        self.assertIn("Classifying question type", [event["message"] for event in events])
        self.assertIn("Loading BHF profile", [event["message"] for event in events])
        self.assertIn("Checking local knowledge", [event["message"] for event in events])
        self.assertIn("Building BHF prompt", [event["message"] for event in events])
        self.assertIn("Contacting model backend", [event["message"] for event in events])
        self.assertIn("waiting_for_model_response", stages)
        self.assertIn("Waiting for model response", [event["message"] for event in events])
        self.assertIn("Model response received", [event["message"] for event in events])
        self.assertIn("Cleaning model output", [event["message"] for event in events])
        self.assertIn("Validating response", [event["message"] for event in events])
        self.assertIn("Finalizing answer", [event["message"] for event in events])
        self.assertTrue(all("timestamp" in event for event in events))
        self.assertTrue(all("step_index" in event for event in events))
        self.assertTrue(all("total_steps" in event for event in events))
        self.assertTrue(all("percent_complete" in event for event in events))
        self.assertTrue(all("elapsed_total_seconds" in event for event in events))
        self.assertTrue(all("elapsed_current_stage_seconds" in event for event in events))
        self.assertTrue(all("status" in event for event in events))
        self.assertEqual(stages[-1], "complete")
        self.assertEqual(events[-1]["percent_complete"], 100.0)
        self.assertEqual(events[-1]["status"], "complete")

    def test_model_unavailable_returns_deterministic_canonical_fallback_answer(self):
        events = []
        agent = self.make_agent(ErrorAdapter())

        result = agent.ask(
            "Why did Joshua renew the covenant at Shechem?",
            status_callback=events.append,
        )

        self.assertFalse(result.errors)
        self.assertTrue(result.model_metadata["pipeline"]["fallback_used"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_mode"], "canonical_summary")
        self.assertEqual(result.model_metadata["pipeline"]["fallback_kind"], "summary")
        self.assertTrue(result.model_metadata["pipeline"]["canonical_library_strong_match"])
        self.assertIn("shechem", result.model_metadata["pipeline"]["fallback_selected_entry_ids"])
        self.assertIn("Shechem", result.answer_text)
        self.assertIn("covenant", result.answer_text.lower())
        self.assertEqual(events[-1]["stage"], "complete")
        self.assertFalse(any(event["status"] == "error" for event in events))

    def test_exceptions_emit_error_status_before_raising(self):
        events = []
        agent = self.make_agent(RaisingAdapter())

        with self.assertRaisesRegex(RuntimeError, "adapter failed"):
            agent.ask("What does Proverbs 3 mean?", status_callback=events.append)

        self.assertEqual(events[-1]["stage"], "error")
        self.assertEqual(events[-1]["details"]["error_type"], "RuntimeError")

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

    def test_agent_runs_canonical_library_in_shadow_mode_without_injecting_context(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(
            adapter,
            profile="standard",
            canonical_library=CanonicalLibraryConfig(
                enabled=False,
                shadow_mode=True,
            ),
        )

        result = agent.ask(
            "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
        )

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertTrue(result.model_metadata["pipeline"]["canonical_library_loaded"])
        self.assertFalse(result.model_metadata["pipeline"]["canonical_library_enabled"])
        self.assertEqual(result.model_metadata["pipeline"]["canonical_library_rollout_mode"], "shadow")
        self.assertEqual(result.model_metadata["pipeline"]["canonical_library_prompt_mode"], "disabled")
        self.assertEqual(
            result.model_metadata["pipeline"]["canonical_library_shadow_prompt_mode"],
            "summary",
        )
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "shadow_mode")
        self.assertEqual(result.model_metadata["canonical_library_object_ids"], [])
        self.assertEqual(result.model_metadata["pipeline"]["canonical_library_object_ids"], [])
        self.assertEqual(result.model_metadata["pipeline"]["ckl_result_count"], 0)

    def test_agent_injects_canonical_library_context_and_debug_ids(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(adapter, profile="standard")

        result = agent.ask(
            "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
        )

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertIn("Use that context as your primary factual source", adapter.request.system_prompt)
        self.assertIn("Entry: Shechem", adapter.request.system_prompt)
        self.assertIn("Source ID: shechem", adapter.request.system_prompt)
        self.assertIn("# OUTPUT REQUIREMENTS", adapter.request.system_prompt)
        self.assertIn("Local Curated Knowledge", adapter.request.system_prompt)
        self.assertLess(
            adapter.request.system_prompt.index("# CANONICAL KNOWLEDGE CONTEXT"),
            adapter.request.system_prompt.index("Local Curated Knowledge"),
        )
        self.assertIn("shechem", result.model_metadata["canonical_library_object_ids"])
        self.assertIn("abraham", result.model_metadata["canonical_library_object_ids"])
        self.assertIn("joshua", result.model_metadata["canonical_library_object_ids"])
        self.assertIn(
            "shechem",
            result.model_metadata["pipeline"]["canonical_library_object_ids"],
        )
        self.assertEqual(
            result.model_metadata["canonical_library_retrieval_method"],
            result.model_metadata["pipeline"]["canonical_library_retrieval_method"],
        )
        self.assertTrue(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertFalse(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertGreater(result.model_metadata["pipeline"]["ckl_result_count"], 0)

    def test_agent_falls_back_to_model_when_ckl_has_no_strong_match(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(adapter, profile="standard")

        result = agent.ask("What does Proverbs 3 mean?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertNotIn("did not find a strong match", adapter.request.system_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertFalse(result.model_metadata["pipeline"]["canonical_library_strong_match"])
        self.assertEqual(
            result.model_metadata["pipeline"]["canonical_library_prompt_mode"],
            "fallback_to_model",
        )
        self.assertTrue(result.model_metadata["pipeline"]["ckl_attempted"])
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])

    def test_agent_returns_model_answer_when_ckl_returns_no_results(self):
        adapter = RecordingAdapter()
        agent = self.make_ckl_agent(adapter, profile="standard")

        with patch("bhf_agent.runner.build_canonical_context", return_value=None), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "no_relevant_ckl_results",
                normalized_question="What does it mean to follow Jesus?",
            ),
        ):
            result = agent.ask("What does it mean to follow Jesus?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertIn("What does it mean to follow Jesus?", adapter.request.user_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertTrue(result.model_metadata["pipeline"]["ckl_attempted"])
        self.assertEqual(result.model_metadata["pipeline"]["ckl_result_count"], 0)
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "no_relevant_ckl_results")
        self.assertEqual(
            result.model_metadata["pipeline"]["ckl_coverage_gap"]["rejection_reasons"],
            ["no_relevant_ckl_results"],
        )

    def test_agent_returns_model_answer_when_placeholder_ckl_results_are_filtered_out(self):
        adapter = RecordingAdapter()
        agent = self.make_ckl_agent(adapter, profile="standard")

        with patch("bhf_agent.runner.build_canonical_context", return_value=None), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "placeholder_content",
                normalized_question="What does it mean to follow Jesus?",
                top_rejected_results=[
                    {
                        "id": "placeholder-1",
                        "title": "Placeholder Entry",
                        "score": 0.12,
                        "rejection_reasons": ["placeholder_content"],
                    }
                ],
            ),
        ):
            result = agent.ask("What does it mean to follow Jesus?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertTrue(result.model_metadata["pipeline"]["ckl_attempted"])
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "placeholder_content")
        self.assertIn(
            "placeholder_content",
            result.model_metadata["pipeline"]["ckl_coverage_gap"]["rejection_reasons"],
        )

    def test_agent_returns_model_answer_when_unreviewed_or_disallowed_ckl_results_are_filtered_out(self):
        adapter = RecordingAdapter()
        agent = self.make_ckl_agent(adapter, profile="standard")

        with patch("bhf_agent.runner.build_canonical_context", return_value=None), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "disallowed_review_status",
                normalized_question="What does it mean to follow Jesus?",
                top_rejected_results=[
                    {
                        "id": "draft-entry",
                        "title": "Draft Entry",
                        "score": 0.18,
                        "rejection_reasons": ["disallowed_review_status"],
                    }
                ],
            ),
        ):
            result = agent.ask("What does it mean to follow Jesus?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertTrue(result.model_metadata["pipeline"]["ckl_attempted"])
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "disallowed_review_status")
        self.assertIn(
            "disallowed_review_status",
            result.model_metadata["pipeline"]["ckl_coverage_gap"]["rejection_reasons"],
        )

    def test_agent_returns_model_answer_when_ckl_retrieval_raises(self):
        adapter = RecordingAdapter()
        agent = self.make_ckl_agent(adapter, profile="standard")

        with patch(
            "bhf_agent.runner.build_canonical_context",
            side_effect=RuntimeError("CKL retrieval failed"),
        ), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "retrieval_failed",
                normalized_question="What does it mean to follow Jesus?",
            ),
        ):
            result = agent.ask("What does it mean to follow Jesus?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertTrue(result.model_metadata["pipeline"]["ckl_attempted"])
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "retrieval_failed")
        self.assertEqual(
            result.model_metadata["pipeline"]["ckl_coverage_gap"]["rejection_reasons"],
            ["retrieval_failed"],
        )

    def test_agent_calls_model_normally_when_ckl_is_disabled(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(
            adapter,
            profile="standard",
            canonical_library=CanonicalLibraryConfig(
                enabled=False,
            ),
        )

        result = agent.ask("What does it mean to follow Jesus?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertFalse(result.model_metadata["pipeline"]["ckl_attempted"])
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "ckl_disabled")

    def test_model_failure_after_ckl_miss_returns_model_error_path(self):
        adapter = ErrorRecordingAdapter()
        agent = self.make_ckl_agent(adapter, profile="standard")
        events = []

        with patch("bhf_agent.runner.build_canonical_context", return_value=None), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "no_relevant_ckl_results",
                normalized_question="What does it mean to follow Jesus?",
            ),
        ):
            result = agent.ask("What does it mean to follow Jesus?", status_callback=events.append)

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertTrue(result.errors)
        self.assertEqual(result.answer_text, "")
        self.assertFalse(result.model_metadata["pipeline"]["fallback_used"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(events[-1]["stage"], "error")
        self.assertEqual(events[-1]["status"], "error")

    def test_model_failure_for_identity_in_jesus_uses_ckl_fallback(self):
        adapter = ErrorRecordingAdapter(
            "Ollama endpoint returned HTTP 500: "
            '{"error":"llama-server process has terminated: signal: killed"}'
        )
        agent = self.make_agent(adapter, profile="standard")
        events = []

        result = agent.ask(
            "what verses show my identity in jesus?",
            status_callback=events.append,
        )

        self.assertFalse(result.errors)
        self.assertTrue(result.model_metadata["pipeline"]["fallback_used"])
        self.assertEqual(
            result.model_metadata["pipeline"]["fallback_mode"],
            "canonical_summary",
        )
        self.assertIn(
            "what-verses-show-identity-in-christ",
            result.model_metadata["pipeline"]["fallback_selected_entry_ids"],
        )
        self.assertIn("Identity in Christ", result.answer_text)
        self.assertIn("Romans 8:1", result.answer_text)
        self.assertIn("2 Corinthians 5:17", result.answer_text)
        self.assertEqual(events[-1]["stage"], "complete")
        self.assertFalse(any(event["status"] == "error" for event in events))

    def test_weak_ckl_results_do_not_block_model_fallback(self):
        adapter = RecordingAdapter()
        agent = self.make_ckl_agent(adapter, profile="standard")

        with patch("bhf_agent.runner.build_canonical_context", return_value=ckl_weak_context_stub()), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "below_relevance_threshold",
                normalized_question="Why is Shechem important in Joshua 24?",
                top_rejected_results=[
                    {
                        "id": "shechem",
                        "title": "Shechem",
                        "score": 0.2,
                        "rejection_reasons": ["below_relevance_threshold"],
                    }
                ],
            ),
        ):
            result = agent.ask("Why is Shechem important in Joshua 24?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.request.system_prompt)
        self.assertNotIn("Entry:", adapter.request.system_prompt)
        self.assertIn("Short Answer", result.answer_text)
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertTrue(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "below_relevance_threshold")
        self.assertEqual(
            result.model_metadata["pipeline"]["ckl_coverage_gap"]["rejection_reasons"],
            ["below_relevance_threshold"],
        )

    def test_strict_mode_keeps_no_match_instruction_for_weak_ckl_results(self):
        adapter = RecordingAdapter()
        agent = self.make_ckl_agent(
            adapter,
            profile="standard",
            canonical_library=CanonicalLibraryConfig(
                enabled=True,
                strict_mode=True,
            ),
        )

        with patch("bhf_agent.runner.build_canonical_context", return_value=ckl_weak_context_stub()), patch(
            "bhf_agent.runner._canonical_miss_reason",
            return_value=ckl_miss_gap(
                "below_relevance_threshold",
                normalized_question="Why is Shechem important in Joshua 24?",
                top_rejected_results=[
                    {
                        "id": "shechem",
                        "title": "Shechem",
                        "score": 0.2,
                        "rejection_reasons": ["below_relevance_threshold"],
                    }
                ],
            ),
        ):
            result = agent.ask("Why is Shechem important in Joshua 24?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertIn("did not find a strong match", adapter.request.system_prompt)
        self.assertFalse(result.model_metadata["pipeline"]["ckl_context_injected"])
        self.assertFalse(result.model_metadata["pipeline"]["fallback_to_model"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_reason"], "strict_mode")
        self.assertEqual(result.model_metadata["pipeline"]["canonical_library_prompt_mode"], "strict_no_match")

    def test_agent_serves_cached_answers_without_calling_adapter(self):
        adapter = RecordingAdapter()
        question = (
            "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
        )
        normalized_question = normalize_public_question(question)
        framework_version_fingerprint = load_framework_version_fingerprint()
        cache_entry = PublicCacheEntry(
            normalized_question=normalized_question,
            answer_mode="study",
            answer="The covenant renewal at Shechem reaffirms Israel's covenant identity.",
            quality_score=96.0,
            usage_count=3,
            review_status="approved",
            framework_version=load_framework_version(),
            framework_version_fingerprint=framework_version_fingerprint,
            ckl_version_fingerprint="ckl-fingerprint",
            object_dependency_ids=("shechem", "abraham", "joshua"),
            expires_at="2030-01-01T00:00:00Z",
        )
        cache = RecordingPublicAnswerCache(cache_entry)
        agent = self.make_agent(adapter, public_answer_cache=cache, profile="standard")

        result = agent.ask(question)

        self.assertIsNone(adapter.request)
        self.assertEqual(result.answer_text, cache_entry.answer)
        self.assertTrue(result.model_metadata["public_answer_cache"]["hit"])
        self.assertEqual(result.model_metadata["public_answer_cache"]["lookup_status"], "hit")
        self.assertEqual(result.model_metadata["public_answer_cache"]["usage_count"], 4)
        self.assertEqual(
            result.model_metadata["public_answer_cache"]["object_dependency_ids"],
            ["shechem", "abraham", "joshua"],
        )
        self.assertEqual(result.validation_result.score, 96)
        self.assertIn("lookup_local_knowledge", result.model_metadata["pipeline"]["stages_completed"])
        self.assertNotIn("build_prompts", result.model_metadata["pipeline"]["stages_completed"])
        self.assertNotIn("call_model", result.model_metadata["pipeline"]["stages_completed"])
        self.assertEqual(len(cache.lookup_calls), 1)
        self.assertEqual(len(cache.increment_calls), 1)
        self.assertIsNotNone(cache.lookup_calls[0]["ckl_version_fingerprint"])
        self.assertIsNotNone(cache.lookup_calls[0]["framework_version_fingerprint"])

    def test_agent_reuses_response_cache_for_identical_questions(self):
        adapter = SequenceAdapter(
            [
                "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                "semantic range can include wind, breath, or spirit. Context "
                "Matters: meaning depends on passage context. Cautions: this "
                "may not always refer to the Holy Spirit.",
            ]
        )
        agent = self.make_agent(adapter, profile="standard")
        question = "What is the Hebrew word for spirit or wind?"

        first_result = agent.ask(question)
        second_result = agent.ask(question)

        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(first_result.answer_text, second_result.answer_text)
        self.assertEqual(
            first_result.model_metadata["pipeline"]["canonical_library_response_cache_status"],
            "stored",
        )
        self.assertTrue(
            second_result.model_metadata["pipeline"]["canonical_library_response_cache_hit"]
        )
        self.assertEqual(
            second_result.model_metadata["pipeline"]["canonical_library_response_cache_status"],
            "hit",
        )
        self.assertNotIn("build_prompts", second_result.model_metadata["pipeline"]["stages_completed"])
        self.assertNotIn("call_model", second_result.model_metadata["pipeline"]["stages_completed"])

    def test_agent_reuses_response_cache_in_shadow_mode_without_prompt_injection(self):
        adapter = SequenceAdapter(
            [
                "Short Answer: The Hebrew word is ruach. Basic Meaning: its semantic range can include wind, breath, or spirit. Context Matters: meaning depends on passage context. Cautions: this may not always refer to the Holy Spirit.",
            ]
        )
        agent = self.make_agent(
            adapter,
            profile="standard",
            canonical_library=CanonicalLibraryConfig(
                enabled=False,
                shadow_mode=True,
            ),
        )
        question = "What is the Hebrew word for spirit or wind?"

        first_result = agent.ask(question)
        second_result = agent.ask(question)

        self.assertEqual(len(adapter.requests), 1)
        self.assertEqual(first_result.answer_text, second_result.answer_text)
        self.assertEqual(
            first_result.model_metadata["pipeline"]["canonical_library_rollout_mode"],
            "shadow",
        )
        self.assertEqual(
            second_result.model_metadata["pipeline"]["canonical_library_rollout_mode"],
            "shadow",
        )
        self.assertEqual(
            second_result.model_metadata["pipeline"]["canonical_library_prompt_mode"],
            "disabled",
        )
        self.assertTrue(
            second_result.model_metadata["pipeline"]["canonical_library_response_cache_hit"]
        )
        self.assertEqual(
            second_result.model_metadata["pipeline"]["canonical_library_response_cache_status"],
            "hit",
        )
        self.assertNotIn("# CANONICAL KNOWLEDGE CONTEXT", adapter.requests[0].system_prompt)

    def test_agent_emits_redacted_observability_log(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(
            adapter,
            profile="standard",
            observability=ObservabilityConfig(enabled=True, verbose=False, redact_sensitive=True),
        )

        with self.assertLogs("bhf_agent.observability", level="INFO") as captured:
            result = agent.ask(
                "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
            )

        self.assertIn("Shechem", result.answer_text)
        self.assertGreaterEqual(len(captured.records), 1)
        record = json.loads(captured.records[0].getMessage())
        self.assertEqual(record["status"], "success")
        self.assertIn("request_id", record)
        self.assertEqual(record["normalized_query"], "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?")
        self.assertGreaterEqual(record["retrieval_duration_ms"], 0)
        self.assertGreaterEqual(record["retrieval_result_count"], 0)
        self.assertIn("selected_entry_ids", record)
        self.assertIn("shechem", record["selected_entry_ids"])
        self.assertIn("cache", record)
        self.assertTrue(record["redacted"])
        self.assertNotIn("Short Answer", captured.records[0].getMessage())
        self.assertNotIn("raw_model_text", captured.records[0].getMessage())

    def test_agent_emits_verbose_observability_log_in_debug_mode(self):
        adapter = RecordingAdapter()
        agent = self.make_agent(
            adapter,
            profile="standard",
            debug=True,
            observability=ObservabilityConfig(enabled=True, verbose=True, redact_sensitive=False),
        )

        with self.assertLogs("bhf_agent.observability", level="DEBUG") as captured:
            agent.ask(
                "Why did Israel renew the covenant where Abraham first entered the land at Shechem in Joshua 24?"
            )

        messages = [json.loads(record.getMessage()) for record in captured.records]
        self.assertGreaterEqual(len(messages), 2)
        info_record = messages[0]
        debug_record = messages[-1]
        self.assertFalse(info_record["redacted"])
        self.assertEqual(debug_record["status"], "success")
        self.assertIn("pipeline", debug_record)
        self.assertIn("stages_completed", debug_record["pipeline"])
        self.assertIn("canonical_library_response_cache_key", debug_record["pipeline"])
        self.assertNotIn("raw_model_text", captured.output[0])

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

    def test_agent_extracts_structured_json_answer_before_display(self):
        adapter = StructuredJsonAdapter(
            json.dumps(
                {
                    "answer": (
                        "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                        "semantic range can include wind, breath, or spirit. Context "
                        "Matters: meaning depends on passage context. Cautions: this "
                        "may not always refer to the Holy Spirit."
                    ),
                    "analysis": "internal details should not be shown",
                }
            )
        )
        agent = self.make_agent(adapter)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertEqual(
            adapter.request.metadata["response_contract"],
            "answer",
        )
        self.assertEqual(
            adapter.request.response_format,
            {"type": "json_object"},
        )
        self.assertIn("STRUCTURED RESPONSE CONTRACT", adapter.request.system_prompt)
        self.assertIn('"answer"', adapter.request.system_prompt)
        self.assertEqual(
            result.answer_text,
            "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
            "semantic range can include wind, breath, or spirit. Context "
            "Matters: meaning depends on passage context. Cautions: this "
            "may not always refer to the Holy Spirit.",
        )
        self.assertNotIn("{", result.answer_text)
        self.assertNotIn("analysis", result.answer_text.lower())

    def test_schema_capable_adapter_receives_strict_schema(self):
        adapter = JsonSchemaAdapter(
            json.dumps(
                {
                    "answer": (
                        "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                        "semantic range includes wind, breath, or spirit. Context "
                        "Matters: meaning depends on passage context. Cautions: this "
                        "may vary by context."
                    )
                }
            )
        )
        result = self.make_agent(adapter).ask("What is the Hebrew word for spirit or wind?")

        self.assertTrue(result.validation_result.passed)
        assert adapter.request is not None
        self.assertEqual(adapter.request.response_format["type"], "json_schema")
        self.assertTrue(adapter.request.response_format["json_schema"]["strict"])

    def test_ollama_auto_mode_uses_prose_for_ordinary_answers(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return type(
                "Response",
                (),
                {
                    "__enter__": lambda self: self,
                    "__exit__": lambda self, exc_type, exc, traceback: False,
                    "read": lambda self: json.dumps(
                        {
                            "model": "gemma2:2b",
                            "message": {
                                "content": (
                                    "Short Answer: The Hebrew word is ruach. Basic Meaning: "
                                    "its semantic range includes wind, breath, or spirit. "
                                    "Context Matters: meaning depends on passage context. "
                                    "Cautions: this may vary by context."
                                )
                            },
                        }
                    ).encode("utf-8"),
                },
            )()

        agent = self.make_agent(
            OllamaAdapter("http://ollama:11434"),
            model="gemma2:2b",
        )
        with patch("urllib.request.urlopen", fake_urlopen):
            result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertTrue(result.validation_result.passed)
        self.assertNotIn("format", captured["body"])
        self.assertIn("# RESPONSE CONTRACT", captured["body"]["messages"][0]["content"])

    def test_agent_extracts_nested_json_answer_object_before_display(self):
        adapter = StructuredJsonAdapter(
            json.dumps(
                {
                    "result": {
                        "answer": (
                            "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
                            "semantic range can include wind, breath, or spirit. Context "
                            "Matters: meaning depends on passage context. Cautions: this "
                            "may not always refer to the Holy Spirit."
                        ),
                    },
                    "usage": {"total_tokens": 12},
                }
            )
        )
        agent = self.make_agent(adapter)

        result = agent.ask("What is the Hebrew word for spirit or wind?")

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertEqual(adapter.request.response_format, {"type": "json_object"})
        self.assertTrue(result.validation_result.passed)
        self.assertEqual(
            result.answer_text,
            "Short Answer: The Hebrew word is ruach. Basic Meaning: its "
            "semantic range can include wind, breath, or spirit. Context "
            "Matters: meaning depends on passage context. Cautions: this "
            "may not always refer to the Holy Spirit.",
        )

    def test_search_fallback_prompt_preserves_json_results_contract(self):
        adapter = StructuredJsonAdapter(
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
            )
        )
        agent = self.make_agent(adapter)
        prompt = "\n".join(
            [
                "Using BHF, identify likely Bible passages for the following search query.",
                "Query: Egypt in Exodus",
                "",
                "Return a JSON object with a results array.",
                "Each result should include book, chapter, optional verse_start, optional verse_end, reason, and confidence.",
                "Use only likely passages and keep the response concise.",
                "Do not include markdown fences or extra commentary.",
            ]
        )

        result = agent.ask(prompt)

        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertEqual(
            adapter.request.metadata["response_contract"],
            "search_results",
        )
        self.assertNotIn("STRUCTURED RESPONSE CONTRACT", adapter.request.system_prompt)
        payload = json.loads(result.answer_text)
        self.assertEqual(payload["results"][0]["book"], "Exodus")
        self.assertEqual(payload["results"][0]["chapter"], 1)
        self.assertEqual(adapter.request.response_format, {"type": "json_object"})

    def test_search_fallback_prompt_returns_empty_results_when_model_unavailable(self):
        adapter = ErrorAdapter()
        agent = self.make_agent(adapter)
        prompt = "\n".join(
            [
                "Using BHF, identify likely Bible passages for the following search query.",
                "Query: Egypt in Exodus",
                "",
                "Return a JSON object with a results array.",
                "Each result should include book, chapter, optional verse_start, optional verse_end, reason, and confidence.",
                "Use only likely passages and keep the response concise.",
                "Do not include markdown fences or extra commentary.",
            ]
        )

        result = agent.ask(prompt)

        self.assertFalse(result.errors)
        self.assertEqual(
            result.model_metadata["pipeline"]["fallback_mode"],
            "search_results_empty",
        )
        payload = json.loads(result.answer_text)
        self.assertEqual(payload["results"], [])
        self.assertIn(
            "could not identify likely passage candidates",
            payload["message"].lower(),
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

    def test_invalid_model_output_uses_canonical_fallback_after_retry(self):
        adapter = SequenceAdapter(
            [
                "The answer is not valid.",
                "Still not valid.",
            ]
        )
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("Why did Joshua renew the covenant at Shechem?")

        self.assertEqual(len(adapter.requests), 2)
        self.assertTrue(result.model_metadata["pipeline"]["repair_attempted"])
        self.assertFalse(result.repair_applied)
        self.assertTrue(result.model_metadata["pipeline"]["fallback_used"])
        self.assertEqual(result.model_metadata["pipeline"]["fallback_mode"], "canonical_summary")
        self.assertIn("shechem", result.model_metadata["pipeline"]["fallback_selected_entry_ids"])
        self.assertIn("Shechem", result.answer_text)
        self.assertIn("covenant", result.answer_text.lower())

    def test_empty_structured_output_uses_ckl_fallback_without_repair_retry(self):
        adapter = SequenceAdapter(["{}"])
        agent = self.make_agent(adapter, auto_repair=True)

        result = agent.ask("Why did Joshua renew the covenant at Shechem?")

        self.assertEqual(len(adapter.requests), 1)
        self.assertTrue(result.model_metadata["pipeline"]["fallback_used"])
        self.assertIn("Shechem", result.answer_text)

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
