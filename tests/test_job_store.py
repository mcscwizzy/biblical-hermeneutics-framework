import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from bhf_agent.models import (
    AgentResult,
    GenreContext,
    QuestionContext,
    ReferenceContext,
    ValidationResult,
)
from bhf_web.jobs import AskJobStore, JobStoreUnavailableError, LazyAskJobStore


class AskJobStoreTests(unittest.TestCase):
    def test_lazy_store_initializes_once_under_concurrent_first_use(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"
            factory_calls = []

            def factory():
                factory_calls.append(True)
                return AskJobStore(path)

            lazy_store = LazyAskJobStore(factory)
            self.assertEqual(
                lazy_store.diagnostics(),
                {
                    "backend": "sqlite",
                    "initialized": False,
                    "available": None,
                    "error_type": None,
                },
            )

            with ThreadPoolExecutor(max_workers=8) as executor:
                stores = list(executor.map(lambda _: lazy_store.get_store(), range(24)))

            self.assertEqual(len(factory_calls), 1)
            self.assertTrue(all(store is stores[0] for store in stores))
            self.assertTrue(lazy_store.diagnostics()["available"])

    def test_lazy_store_caches_initialization_failure_without_sensitive_details(self):
        factory_calls = []

        def factory():
            factory_calls.append(True)
            raise RuntimeError("secret-path/provider-input")

        lazy_store = LazyAskJobStore(factory)

        for _ in range(2):
            with self.assertRaisesRegex(
                JobStoreUnavailableError,
                "Durable job persistence is unavailable",
            ) as raised:
                lazy_store.get_store()
            self.assertNotIn("secret-path", str(raised.exception))

        self.assertEqual(len(factory_calls), 1)
        self.assertEqual(lazy_store.diagnostics()["error_type"], "RuntimeError")

    def test_lazy_store_disables_persistence_after_operational_failure(self):
        class BrokenStore:
            def create(self, *, deadline_seconds=None):
                raise sqlite3.OperationalError("disk became read-only")

        lazy_store = LazyAskJobStore(lambda: BrokenStore())

        with self.assertRaises(JobStoreUnavailableError):
            lazy_store.create()
        with self.assertRaises(JobStoreUnavailableError):
            lazy_store.get_store()

        diagnostics = lazy_store.diagnostics()
        self.assertTrue(diagnostics["initialized"])
        self.assertFalse(diagnostics["available"])
        self.assertEqual(diagnostics["error_type"], "OperationalError")

    def test_initialization_creates_ask_and_presentation_schemas(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"

            AskJobStore(path)

            with sqlite3.connect(path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            self.assertIn("ask_jobs", tables)
            self.assertIn("presentation_jobs", tables)

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

    def test_unwritable_job_directory_fails_clearly(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "bhf_web.jobs.os.access",
            return_value=False,
        ):
            path = Path(directory) / "jobs.sqlite"

            with self.assertRaisesRegex(
                RuntimeError,
                f"BHF job database directory is not writable: {directory}",
            ):
                AskJobStore(path)

    def test_invalid_sqlite_database_fails_initialization_clearly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"
            path.write_text("not a sqlite database", encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError,
                "BHF job database could not be opened or initialized",
            ):
                AskJobStore(path)

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
            self.assertEqual(loaded.error_category, "provider_timeout")
            self.assertEqual(loaded.failed_stage, "waiting_for_model_response")
            self.assertEqual(loaded.status, "error")

    def test_job_status_exposes_only_provider_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AskJobStore(Path(directory) / "jobs.sqlite")
            job = store.create()
            job.complete(
                AgentResult(
                    answer_text="answer",
                    reference_context=ReferenceContext(),
                    genre_context=GenreContext(primary_genre="epistle"),
                    question_context=QuestionContext(question_type="context"),
                    profile_used="standard",
                    validation_result=ValidationResult(passed=True, score=90),
                    model_metadata={
                        "provider_diagnostics": {
                            "requested_model": "openrouter/free",
                            "selected_model": "google/gemma-4-26b-a4b-it:free",
                            "selected_provider": "Google AI Studio",
                        },
                        "raw_provider_response": {"private": "do not expose"},
                    },
                )
            )

            status = store.get(job.job_id).to_dict()

            self.assertEqual(
                status["provider_diagnostics"]["selected_model"],
                "google/gemma-4-26b-a4b-it:free",
            )
            self.assertNotIn("raw_provider_response", status)


if __name__ == "__main__":
    unittest.main()
