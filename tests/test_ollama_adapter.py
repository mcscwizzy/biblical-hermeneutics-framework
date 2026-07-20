import json
import unittest
import urllib.error
from unittest.mock import patch

from bhf_agent.adapters.ollama import OllamaAdapter
from bhf_agent.models import ChatRequest


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload

    def close(self):
        pass


class OllamaAdapterTests(unittest.TestCase):
    def test_formats_chat_request_for_native_api(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "model": "qwen2.5:0.5b",
                        "message": {"content": "answer"},
                        "done_reason": "stop",
                        "prompt_eval_count": 12,
                        "eval_count": 3,
                        "total_duration": 1000,
                    }
                ).encode("utf-8")
            )

        adapter = OllamaAdapter("http://ollama:11434", timeout_seconds=5)
        request = ChatRequest(
            system_prompt="system",
            user_prompt="user",
            model="qwen2.5:0.5b",
            temperature=0.2,
            max_tokens=128,
            context_window=12288,
            response_format={"type": "json_object"},
        )

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(captured["url"], "http://ollama:11434/api/chat")
        self.assertEqual(captured["timeout"], 5)
        self.assertEqual(captured["body"]["model"], "qwen2.5:0.5b")
        self.assertFalse(captured["body"]["stream"])
        self.assertEqual(captured["body"]["options"]["temperature"], 0.2)
        self.assertEqual(captured["body"]["options"]["num_predict"], 128)
        self.assertEqual(captured["body"]["options"]["num_ctx"], 12288)
        self.assertEqual(captured["body"]["format"], "json")
        self.assertEqual(response.text, "answer")
        self.assertEqual(response.model, "qwen2.5:0.5b")
        self.assertEqual(response.provider, "ollama")
        self.assertEqual(
            response.raw_provider_response,
            {
                "metadata": {
                    "done_reason": "stop",
                    "prompt_eval_count": 12,
                    "eval_count": 3,
                    "total_duration": 1000,
                }
            },
        )
        self.assertEqual(response.raw_response, response.raw_provider_response)
        self.assertIsNotNone(response.latency_ms)

    def test_ordinary_request_omits_native_json_format(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(
                b'{"model":"gemma2:2b","message":{"content":"Markdown answer"}}'
            )

        adapter = OllamaAdapter("http://ollama:11434")
        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(ChatRequest("system", "user", "gemma2:2b"))

        self.assertNotIn("format", captured["body"])
        self.assertEqual(response.text, "Markdown answer")

    def test_captures_safe_generation_metadata(self):
        payload = {
            "model": "gemma2:2b",
            "message": {"content": "answer"},
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "prompt_eval_duration": 20,
            "eval_count": 4,
            "eval_duration": 30,
            "total_duration": 50,
            "prompt": "must not be retained",
        }

        with patch(
            "urllib.request.urlopen",
            lambda request, timeout=None: FakeHTTPResponse(json.dumps(payload).encode("utf-8")),
        ):
            response = OllamaAdapter("http://ollama:11434").chat(
                ChatRequest("system", "user", "gemma2:2b")
            )

        self.assertEqual(response.usage["done_reason"], "stop")
        self.assertEqual(response.usage["eval_count"], 4)
        self.assertNotIn("prompt", response.raw_provider_response)

    def test_preserves_json_string_assistant_content(self):
        payload = {
            "model": "qwen2.5:0.5b",
            "created_at": "2026-07-17T00:00:00Z",
            "message": {
                "role": "assistant",
                "content": '{"answer":"Valid answer"}',
            },
            "done": True,
        }

        def fake_urlopen(request, timeout=None):
            return FakeHTTPResponse(json.dumps(payload).encode("utf-8"))

        adapter = OllamaAdapter("http://ollama:11434", timeout_seconds=5)
        request = ChatRequest("system", "user", "qwen2.5:0.5b")

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(response.text, '{"answer":"Valid answer"}')
        self.assertEqual(response.raw_provider_response, {"metadata": {}})

    def test_health_check_reports_installed_model(self):
        def fake_urlopen(request, timeout=None):
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "models": [
                            {"name": "qwen2.5:0.5b"},
                            {"name": "llama3.2:1b"},
                        ]
                    }
                ).encode("utf-8")
            )

        adapter = OllamaAdapter("http://ollama:11434")

        with patch("urllib.request.urlopen", fake_urlopen):
            report = adapter.health_check("qwen2.5:0.5b")

        self.assertTrue(report["ok"])
        self.assertTrue(report["model_present"])
        self.assertIn("qwen2.5:0.5b", report["available_models"])

    def test_http_error_returns_chat_response_error(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url,
                500,
                "server error",
                hdrs=None,
                fp=FakeHTTPResponse(b"boom"),
            )

        adapter = OllamaAdapter("http://ollama:11434")
        request = ChatRequest("system", "user", "qwen2.5:0.5b")

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(response.text, "")
        self.assertIn("HTTP 500", response.errors[0])
        self.assertEqual(response.error_category, "provider_failure")


if __name__ == "__main__":
    unittest.main()
