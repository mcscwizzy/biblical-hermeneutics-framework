import json
import unittest
import urllib.error
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

    def close(self):
        pass


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

    def test_retries_rate_limit_with_provider_delay(self):
        calls = 0

        def fake_urlopen(request, timeout=None):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "rate limited",
                    hdrs={"Retry-After": "3"},
                    fp=FakeHTTPResponse(b'{"error":{"message":"busy"}}'),
                )
            return FakeHTTPResponse(
                b'{"model":"openai/gpt-4o-mini","choices":[{"message":{"content":"answer"}}]}'
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep") as sleep,
        ):
            response = adapter.chat(ChatRequest("system", "user", "openai/gpt-4o-mini"))

        self.assertEqual(calls, 2)
        sleep.assert_called_once_with(3.0)
        self.assertEqual(response.text, "answer")
        self.assertEqual(
            response.warnings,
            ["The provider briefly rate-limited this request; BHF retried automatically."],
        )


if __name__ == "__main__":
    unittest.main()
