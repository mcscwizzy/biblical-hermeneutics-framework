import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from bhf_agent.adapters.openai_compatible import OpenAICompatibleAdapter
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


class OpenAICompatibleAdapterTests(unittest.TestCase):
    def test_formats_chat_completion_request(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "model": "local-model",
                        "choices": [{"message": {"content": "answer"}}],
                        "usage": {"total_tokens": 3},
                    }
                ).encode("utf-8")
            )

        adapter = OpenAICompatibleAdapter(
            "http://localhost:1234/v1",
            api_key="local",
            timeout_seconds=5,
        )
        request = ChatRequest(
            system_prompt="system",
            user_prompt="user",
            model="local-model",
            temperature=0.3,
            max_tokens=2048,
        )

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(captured["url"], "http://localhost:1234/v1/chat/completions")
        self.assertEqual(captured["timeout"], 5)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer local")
        self.assertEqual(captured["body"]["model"], "local-model")
        self.assertEqual(captured["body"]["messages"][0]["role"], "system")
        self.assertEqual(captured["body"]["messages"][1]["content"], "user")
        self.assertEqual(response.text, "answer")
        self.assertEqual(response.model, "local-model")

    def test_omits_authorization_without_api_key(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["headers"] = dict(request.header_items())
            return FakeHTTPResponse(
                b'{"choices":[{"message":{"content":"answer"}}]}'
            )

        adapter = OpenAICompatibleAdapter("http://localhost:1234/v1")
        request = ChatRequest("system", "user", "local-model")

        with patch("urllib.request.urlopen", fake_urlopen):
            adapter.chat(request)

        self.assertNotIn("Authorization", captured["headers"])

    def test_http_error_returns_chat_response_error(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url,
                500,
                "server error",
                hdrs=None,
                fp=FakeHTTPResponse(b"boom"),
            )

        adapter = OpenAICompatibleAdapter("http://localhost:1234/v1")
        request = ChatRequest("system", "user", "local-model")

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(response.text, "")
        self.assertIn("HTTP 500", response.errors[0])

    def test_timeout_returns_chat_response_error(self):
        def fake_urlopen(request, timeout=None):
            raise socket.timeout("timed out")

        adapter = OpenAICompatibleAdapter("http://localhost:1234/v1")
        request = ChatRequest("system", "user", "local-model")

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(response.text, "")
        self.assertIn("timed out", response.errors[0])

    def test_malformed_response_returns_chat_response_error(self):
        def fake_urlopen(request, timeout=None):
            return FakeHTTPResponse(b'{"choices":[]}')

        adapter = OpenAICompatibleAdapter("http://localhost:1234/v1")
        request = ChatRequest("system", "user", "local-model")

        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(request)

        self.assertEqual(response.text, "")
        self.assertIn("did not include message text", response.errors[0])


if __name__ == "__main__":
    unittest.main()
