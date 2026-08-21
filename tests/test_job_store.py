import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bhf_agent.models import (
    AgentResult,
    GenreContext,
    QuestionContext,
    ReferenceContext,
    ValidationResult,
)
from bhf_web.jobs import AskJobStore


class AskJobStoreTests(unittest.TestCase):
    def test_job_and_result_are_visible_from_another_store_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"
            writer = AskJobStore(path)
            job = writer.create()
            job.question = "What does John 3:16 mean?"
            job.reader_reference = "John 3:16"
            job.emit(
                {
                    "stage": "waiting_for_model_response",
                    "message": "Waiting for model response",
                    "timestamp": "2026-08-21T12:00:00Z",
                    "step_index": 12,
                    "total_steps": 17,
                    "percent_complete": 70.6,
                    "status": "running",
                }
            )
            job.complete(
                AgentResult(
                    answer_text="God's love is expressed through the gift of the Son.",
                    reference_context=ReferenceContext(
                        book="John",
                        chapter=3,
                        verse=16,
                        is_reference_based=True,
                    ),
                    genre_context=GenreContext(primary_genre="gospel"),
                    question_context=QuestionContext(question_type="definition"),
                    profile_used="standard",
                    validation_result=ValidationResult(passed=True, score=95),
                    model_metadata={"provider": "openrouter"},
                )
            )

            loaded = AskJobStore(path).get(job.job_id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertTrue(loaded.done)
            self.assertEqual(loaded.reader_reference, "John 3:16")
            self.assertEqual(
                loaded.result.public_response()["answer"],
                "God's love is expressed through the gift of the Son.",
            )
            self.assertEqual(loaded.result.reference_context.book, "John")
            self.assertEqual(loaded.result.model_metadata["provider"], "openrouter")

    def test_running_job_reports_live_elapsed_time(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AskJobStore(Path(directory) / "jobs.sqlite")
            job = store.create()
            five_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=5)
            job.created_at = five_seconds_ago.isoformat().replace("+00:00", "Z")
            job.stage_started_at = job.created_at

            status = job.to_dict()

            self.assertGreaterEqual(status["elapsed_total_seconds"], 4.9)
            self.assertGreaterEqual(status["elapsed_current_stage_seconds"], 4.9)

    def test_expired_job_is_failed_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"
            store = AskJobStore(path)
            job = store.create(deadline_seconds=30)
            job.deadline_at = "2000-01-01T00:00:00Z"
            job.emit(
                {
                    "stage": "waiting_for_model_response",
                    "message": "Waiting for model response",
                    "status": "running",
                }
            )

            loaded = AskJobStore(path).get(job.job_id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertTrue(loaded.done)
            self.assertEqual(loaded.status_code, 504)
            self.assertIn("configured deadline", loaded.error)


if __name__ == "__main__":
    unittest.main()
