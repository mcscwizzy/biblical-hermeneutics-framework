import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bhf_agent.adapters import ChatAdapter
from bhf_agent.config import AgentConfig
from bhf_agent.memory import (
    SessionMemory,
    append_session_turn,
    load_session_memory,
    save_session_memory,
    session_file_path,
)
from bhf_agent.models import ChatRequest, ChatResponse, GenreContext, QuestionContext, ReferenceContext
from bhf_agent.profiles import ProfileLoader
from bhf_agent.runner import BHFAgent


class MemoryRecordingAdapter(ChatAdapter):
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or [
            "Genre: wisdom literature. Observation before interpretation. Application follows context.",
        ]
        self.requests: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        index = len(self.requests) - 1
        text = self.responses[index] if index < len(self.responses) else self.responses[-1]
        return ChatResponse(text=text, model="fake-model")


class MemoryTests(unittest.TestCase):
    def make_agent(self, adapter: MemoryRecordingAdapter, **overrides) -> BHFAgent:
        profiles_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, profiles_dir, ignore_errors=True)
        (profiles_dir / "standard.md").write_text("PROFILE", encoding="utf-8")
        values = {
            "base_url": "http://localhost:1234/v1",
            "model": "fake-model",
            "profile": "standard",
        }
        values.update(overrides)
        return BHFAgent(
            AgentConfig(**values),
            adapter=adapter,
            profile_loader=ProfileLoader(profiles_dir),
        )

    def test_memory_disabled_by_default(self):
        config = AgentConfig(base_url="http://localhost:1234/v1", model="fake-model")

        self.assertFalse(config.memory_enabled)
        self.assertIsNone(config.session_id)
        self.assertIsNone(config.memory_path)
        self.assertEqual(config.memory_max_turns, 8)

    def test_enabling_memory_creates_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = MemoryRecordingAdapter()
            agent = self.make_agent(
                adapter,
                memory_enabled=True,
                session_id="lesson-1",
                memory_path=tmp,
            )

            result = agent.ask("What does Proverbs 3 mean?")

            path = Path(tmp) / "lesson-1.json"
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["session_id"], "lesson-1")
            self.assertEqual(len(data["turns"]), 1)
            self.assertEqual(data["turns"][0]["answer_mode"], "study")
            self.assertTrue(result.model_metadata["memory_enabled"])
            self.assertEqual(result.model_metadata["memory_turns_saved"], 1)

    def test_second_question_in_same_session_includes_prior_summary_in_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = MemoryRecordingAdapter(
                [
                    "First answer summary about Proverbs wisdom.",
                    "Second answer.",
                ]
            )
            agent = self.make_agent(
                adapter,
                memory_enabled=True,
                session_id="lesson-2",
                memory_path=tmp,
            )

            agent.ask("What does Proverbs 3 mean?")
            agent.ask("How should I teach this?")

            self.assertEqual(len(adapter.requests), 2)
            second_prompt = adapter.requests[1].system_prompt
            self.assertIn("Local Session Memory", second_prompt)
            self.assertIn(
                "The following is local session context from prior turns. Use it only to maintain continuity.",
                second_prompt,
            )
            self.assertIn("First answer summary about Proverbs wisdom.", second_prompt)
            self.assertIn("Do not treat previous answers as authoritative", second_prompt)

    def test_memory_trims_to_memory_max_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = SessionMemory(session_id="trim")
            reference = ReferenceContext(topic="topic")
            genre = GenreContext(primary_genre=None)
            question = QuestionContext(question_type="topic_study")
            for index in range(5):
                append_session_turn(
                    memory,
                    question=f"Question {index}",
                    answer_text=f"Answer {index}",
                    reference_context=reference,
                    genre_context=genre,
                    question_context=question,
                    profile="standard",
                    answer_mode="study",
                    max_turns=3,
                )
            save_session_memory(memory, tmp, max_turns=3)

            loaded, warnings = load_session_memory(tmp, "trim", max_turns=3)

        self.assertEqual(warnings, [])
        self.assertEqual(len(loaded.turns), 3)
        self.assertEqual(loaded.turns[0].question, "Question 2")
        self.assertEqual(loaded.turns[-1].question, "Question 4")

    def test_corrupt_memory_file_produces_warning_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not valid json", encoding="utf-8")

            memory, warnings = load_session_memory(tmp, "bad", max_turns=8)

        self.assertEqual(memory.turns, [])
        self.assertTrue(warnings)
        self.assertIn("ignored", warnings[0])

    def test_unsafe_session_id_cannot_escape_memory_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "unsafe session_id"):
                session_file_path(tmp, "../escape")


if __name__ == "__main__":
    unittest.main()
