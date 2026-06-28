import asyncio
import json
import os
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch

from bhf_agent.config import AgentConfig, ConfigError
from bhf_agent.models import (
    AgentResult,
    GenreContext,
    QuestionContext,
    ReferenceContext,
    ValidationResult,
)
from bhf_web.forms import config_from_form
from bhf_web.forms import load_web_defaults

try:
    from bhf_web.app import AskJob, app

    HAS_WEB_DEPS = True
except ModuleNotFoundError:
    app = None
    AskJob = None
    HAS_WEB_DEPS = False


class WebFormTests(unittest.TestCase):
    def test_config_creation_from_form_validates(self):
        defaults = AgentConfig(
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
            api_key="local-secret",
        )

        config = config_from_form(
            {
                "profile": "standard",
                "answer_mode": "teaching",
                "model": "local-model",
                "base_url": "http://localhost:1234/v1",
                "temperature": "0.4",
                "max_tokens": "1024",
                "show_method_notes": "on",
                "memory_enabled": "on",
                "session_id": "lesson-1",
                "memory_path": ".bhf/sessions",
                "memory_max_turns": "4",
            },
            defaults,
        )

        self.assertEqual(config.profile, "standard")
        self.assertEqual(config.answer_mode, "teaching")
        self.assertEqual(config.model, "local-model")
        self.assertEqual(config.base_url, "http://localhost:1234/v1")
        self.assertEqual(config.temperature, 0.4)
        self.assertEqual(config.max_tokens, 1024)
        self.assertTrue(config.show_method_notes)
        self.assertTrue(config.memory_enabled)
        self.assertEqual(config.session_id, "lesson-1")
        self.assertEqual(config.memory_max_turns, 4)
        self.assertEqual(config.api_key, "local-secret")

    def test_invalid_form_config_returns_clear_error(self):
        defaults = AgentConfig(
            base_url="http://localhost:11434/v1",
            model="llama3.1:8b",
        )

        with self.assertRaisesRegex(ConfigError, "temperature must be between 0 and 2"):
            config_from_form(
                {
                    "profile": "standard",
                    "answer_mode": "study",
                    "model": "local-model",
                    "base_url": "http://localhost:1234/v1",
                    "temperature": "3",
                    "max_tokens": "1024",
                    "memory_max_turns": "4",
                },
                defaults,
            )

    def test_web_defaults_read_environment_variables(self):
        env = {
            "BHF_BASE_URL": "http://host.docker.internal:11434/v1",
            "BHF_MODEL": "qwen2.5:7b",
            "BHF_PROFILE": "standard",
            "BHF_ANSWER_MODE": "concise",
            "BHF_TEMPERATURE": "0.2",
            "BHF_MAX_TOKENS": "1024",
            "BHF_TIMEOUT_SECONDS": "45",
            "BHF_SHOW_METHOD_NOTES": "false",
            "BHF_MEMORY_ENABLED": "true",
            "BHF_MEMORY_PATH": "/app/.bhf/sessions",
        }

        with patch.dict(os.environ, env, clear=False):
            loaded = load_web_defaults(path="/tmp/bhf-web-config-does-not-exist.json")

        config = loaded.config
        self.assertEqual(config.base_url, "http://host.docker.internal:11434/v1")
        self.assertEqual(config.model, "qwen2.5:7b")
        self.assertEqual(config.profile, "standard")
        self.assertEqual(config.answer_mode, "concise")
        self.assertEqual(config.temperature, 0.2)
        self.assertEqual(config.max_tokens, 1024)
        self.assertEqual(config.timeout_seconds, 45)
        self.assertFalse(config.show_method_notes)
        self.assertTrue(config.memory_enabled)
        self.assertEqual(config.memory_path, "/app/.bhf/sessions")

    def test_web_defaults_use_360_second_timeout(self):
        loaded = load_web_defaults(path="/tmp/bhf-web-config-does-not-exist.json")

        self.assertEqual(loaded.config.timeout_seconds, 360)

    def test_form_values_override_environment_defaults(self):
        env = {
            "BHF_BASE_URL": "http://host.docker.internal:11434/v1",
            "BHF_MODEL": "qwen2.5:7b",
            "BHF_PROFILE": "standard",
            "BHF_ANSWER_MODE": "study",
        }

        with patch.dict(os.environ, env, clear=False):
            defaults = load_web_defaults(
                path="/tmp/bhf-web-config-does-not-exist.json"
            ).config
            config = config_from_form(
                {
                    "profile": "minimal-7b",
                    "answer_mode": "concise",
                    "model": "form-model",
                    "base_url": "http://localhost:1234/v1",
                    "temperature": "0.1",
                    "max_tokens": "512",
                    "memory_max_turns": "4",
                },
                defaults,
            )

        self.assertEqual(config.base_url, "http://localhost:1234/v1")
        self.assertEqual(config.model, "form-model")
        self.assertEqual(config.profile, "minimal-7b")
        self.assertEqual(config.answer_mode, "concise")
        self.assertEqual(config.timeout_seconds, 360)


class WebAssetTests(unittest.TestCase):
    def test_status_script_collapses_active_panel_after_success(self):
        script = Path("bhf_web/static/htmx-lite.js").read_text(encoding="utf-8")

        self.assertIn("function markStatusComplete", script)
        self.assertIn('querySelector(".status-active").hidden = true', script)
        self.assertIn("stopWaiting();", script)
        self.assertIn("setRunning(form, submitButton, false);", script)

    def test_status_script_uses_rotating_waiting_text(self):
        script = Path("bhf_web/static/htmx-lite.js").read_text(encoding="utf-8")

        self.assertIn("WAITING_MESSAGES", script)
        self.assertIn("deflibberlating", script.lower())
        self.assertIn("shenaniganizing", script.lower())
        self.assertIn("calling the schwartz", script.lower())
        self.assertIn("WAITING_MESSAGE_BASE_DELAY_MS", script)
        self.assertIn("Math.random()", script)
        self.assertNotIn("The agent is running. Status updates will appear above.", script)
        self.assertNotIn("progress-track", script)
        self.assertNotIn("toFixed(3)", script)


@unittest.skipUnless(HAS_WEB_DEPS, "FastAPI test dependencies are not installed")
class WebAppTests(unittest.TestCase):
    def setUp(self):
        assert app is not None
        assert AskJob is not None

    def test_get_index_returns_200(self):
        response = asgi_request("GET", "/")

        self.assertEqual(response["status"], 200)
        self.assertIn("BHF Agent", response["body"])
        self.assertIn("name=\"question\"", response["body"])
        self.assertIn("status-summary", response["body"])
        self.assertIn("status-current", response["body"])
        self.assertNotIn("progress-track", response["body"])
        self.assertNotIn("data-total-elapsed", response["body"])
        self.assertNotIn("status-percent", response["body"])

    def test_health_route_returns_ok(self):
        response = asgi_request("GET", "/api/health")

        self.assertEqual(response["status"], 200)
        self.assertIn('"status":"ok"', response["body"])
        self.assertIn('"service":"bhf-web"', response["body"])

    def test_post_ask_handles_mocked_agent_result(self):
        with patch("bhf_web.app.BHFAgent", FakeAgent):
            response = asgi_request("POST", "/ask", data=_valid_form())

        self.assertEqual(response["status"], 200)
        self.assertIn("Answer", response["body"])
        self.assertIn("Short Answer", response["body"])
        self.assertIn("Profile used", response["body"])
        self.assertIn("minimal-7b", response["body"])
        self.assertIn("Local knowledge used", response["body"])
        self.assertIn("ruach", response["body"])
        self.assertNotIn("local-secret", response["body"])

    def test_post_ask_invalid_config_returns_friendly_error(self):
        data = _valid_form()
        data["max_tokens"] = "0"

        response = asgi_request("POST", "/ask", data=data)

        self.assertEqual(response["status"], 400)
        self.assertIn("Could not ask BHF", response["body"])
        self.assertIn("max_tokens must be greater than 0", response["body"])

    def test_ask_job_reports_status_and_returns_result(self):
        with patch("bhf_web.app.BHFAgent", SuccessfulJobAgent):
            response = asgi_request("POST", "/ask/jobs", data=_valid_form())

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_job(job["job_id"])

        self.assertTrue(status["done"])
        self.assertIsNone(status["error"])
        self.assertEqual(status["stage"], "complete")
        self.assertIn("Waiting for model response", _history_messages(status))
        self.assertEqual(status["percent_complete"], 100.0)
        self.assertEqual(status["status"], "complete")
        self.assertIn("elapsed_total_seconds", status)
        self.assertTrue(
            all("step_index" in entry for entry in status["history"])
        )
        self.assertTrue(
            all("elapsed_current_stage_seconds" in entry for entry in status["history"])
        )

        result = asgi_request("GET", f"/ask/result/{job['job_id']}")
        self.assertEqual(result["status"], 200)
        self.assertIn("Short Answer", result["body"])
        self.assertIn("Metadata", result["body"])

    def test_ask_job_marks_previous_running_step_complete(self):
        job = AskJob(job_id="job-1")
        job.emit(status_event("queued", "Queued", 1, status="running"))
        job.emit(
            status_event(
                "loading_profile",
                "Loading BHF profile",
                6,
                status="running",
            )
        )

        self.assertEqual(job.history[0].status, "complete")
        self.assertEqual(job.history[1].status, "running")

    def test_ask_job_surfaces_agent_errors_with_failed_stage(self):
        with patch("bhf_web.app.BHFAgent", ErrorAgent):
            response = asgi_request("POST", "/ask/jobs", data=_valid_form())

        self.assertEqual(response["status"], 202)
        job = json.loads(response["body"])
        status = wait_for_job(job["job_id"])

        self.assertTrue(status["done"])
        self.assertIn("timed out", status["error"])
        self.assertEqual(status["failed_stage"], "waiting_for_model_response")
        self.assertEqual(status["status"], "error")

        result = asgi_request("GET", f"/ask/result/{job['job_id']}")
        self.assertEqual(result["status"], 502)
        self.assertIn("timed out", result["body"])
        self.assertIn("failed during waiting for model response", result["body"])


class FakeAgent:
    def __init__(self, config):
        self.config = config

    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(status_event("loading_profile", "Loading BHF profile", 6))
            status_callback(
                status_event(
                    "contacting_model_backend",
                    "Contacting model backend",
                    10,
                    status="running",
                )
            )
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(status_event("validating_response", "Validating response", 14))
            status_callback(status_event("formatting_answer", "Finalizing answer", 15))
            status_callback(status_event("complete", "Complete", 16, status="complete"))
        return fake_result(self.config, errors=["example adapter error"])


class ErrorAgent(FakeAgent):
    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(
                status_event(
                    "contacting_model_backend",
                    "Contacting model backend",
                    10,
                    status="running",
                )
            )
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(
                {
                    "stage": "error",
                    "message": "Model backend error",
                    "step_index": 11,
                    "total_steps": 16,
                    "percent_complete": 68.8,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "elapsed_total_seconds": 1.0,
                    "elapsed_current_stage_seconds": 0.5,
                    "status": "error",
                    "details": {
                        "failed_stage": "waiting_for_model_response",
                        "errors": ["OpenAI-compatible endpoint timed out: timed out"],
                    },
                }
            )
        return fake_result(
            self.config,
            errors=["OpenAI-compatible endpoint timed out: timed out"],
        )


class SuccessfulJobAgent(FakeAgent):
    def ask(self, question, status_callback=None):
        if status_callback is not None:
            status_callback(status_event("loading_profile", "Loading BHF profile", 6))
            status_callback(
                status_event(
                    "contacting_model_backend",
                    "Contacting model backend",
                    10,
                    status="running",
                )
            )
            status_callback(
                status_event(
                    "waiting_for_model_response",
                    "Waiting for model response",
                    11,
                    status="running",
                )
            )
            status_callback(status_event("complete", "Complete", 16, status="complete"))
        return fake_result(self.config, errors=[])


def status_event(stage, message, step_index, status="complete"):
    return {
        "stage": stage,
        "message": message,
        "step_index": step_index,
        "total_steps": 16,
        "percent_complete": round((step_index / 16) * 100, 1),
        "timestamp": "2026-01-01T00:00:00Z",
        "elapsed_total_seconds": float(step_index),
        "elapsed_current_stage_seconds": 0.25,
        "status": status,
    }


def fake_result(config, errors):
    return AgentResult(
        answer_text="## Short Answer\nAnswer with **method**.",
        reference_context=ReferenceContext(
            book="Romans",
            chapter=12,
            verse=1,
            testament="NT",
            is_reference_based=True,
            confidence=0.9,
        ),
        genre_context=GenreContext(primary_genre="epistle"),
        question_context=QuestionContext(question_type="context", confidence=0.8),
        profile_used=config.profile,
        validation_result=ValidationResult(
            passed=True,
            score=90,
            warnings=["example warning"],
        ),
        model_metadata={
            "answer_mode": config.answer_mode,
            "local_knowledge_keys": ["ruach"],
        },
        errors=errors,
    )


def _valid_form():
    return {
        "question": "What does Romans 12:1 mean?",
        "profile": "minimal-7b",
        "answer_mode": "study",
        "model": "local-model",
        "base_url": "http://localhost:1234/v1",
        "temperature": "0.3",
        "max_tokens": "1024",
        "timeout_seconds": "600",
        "show_method_notes": "on",
        "memory_max_turns": "8",
    }


def wait_for_job(job_id):
    for _attempt in range(20):
        response = asgi_request("GET", f"/ask/status/{job_id}")
        status = json.loads(response["body"])
        if status.get("done"):
            return status
        time.sleep(0.01)
    raise AssertionError(f"job did not complete: {job_id}")


def _history_messages(status):
    return [entry["message"] for entry in status["history"]]


def asgi_request(method, path, data=None):
    assert app is not None
    return asyncio.run(_asgi_request(method, path, data))


async def _asgi_request(method, path, data=None):
    body = urlencode(data or {}).encode("utf-8")
    headers = [(b"host", b"testserver")]
    if body:
        headers.extend(
            [
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 123),
        "server": ("testserver", 80),
    }
    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(0)
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    status = next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )
    chunks = [
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    ]
    return {
        "status": status,
        "body": b"".join(chunks).decode("utf-8"),
    }


if __name__ == "__main__":
    unittest.main()
