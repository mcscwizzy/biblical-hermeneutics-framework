import json
import unittest
from unittest.mock import patch

from bhf_agent.adapters.openrouter import OPENROUTER_BASE_URL, OpenRouterAdapter
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


class OpenRouterAdapterTests(unittest.TestCase):
    def test_uses_openrouter_chat_endpoint_and_bearer_token(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(
                b'{"model":"openai/gpt-4o-mini","choices":[{"message":{"content":"answer"}}]}'
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with patch("urllib.request.urlopen", fake_urlopen):
            response = adapter.chat(ChatRequest("system", "user", "openai/gpt-4o-mini"))

        self.assertEqual(captured["url"], f"{OPENROUTER_BASE_URL}/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer or-secret")
        self.assertEqual(captured["body"]["model"], "openai/gpt-4o-mini")
        self.assertEqual(response.provider, "openrouter")
        self.assertEqual(response.text, "answer")


if __name__ == "__main__":
    unittest.main()
