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
        self.assertEqual(captured["headers"]["X-openrouter-metadata"], "enabled")
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

    def test_persistent_temporary_rate_limit_preserves_message_and_category(self):
        calls = 0

        def fake_urlopen(request, timeout=None):
            nonlocal calls
            calls += 1
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                hdrs={"Retry-After": "2"},
                fp=FakeHTTPResponse(
                    b'{"error":{"message":"Too many requests for this model."}}'
                ),
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep") as sleep,
        ):
            response = adapter.chat(ChatRequest("system", "user", "openai/gpt-4o-mini"))

        self.assertEqual(calls, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(response.error_category, "provider_rate_limit")
        self.assertIn("Too many requests for this model.", response.errors[0])
        self.assertIn("rate-limit source: undetermined", response.errors[0])

    def test_daily_free_tier_quota_is_not_retried(self):
        calls = 0

        def fake_urlopen(request, timeout=None):
            nonlocal calls
            calls += 1
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                hdrs={"Retry-After": "60"},
                fp=FakeHTTPResponse(
                    b'{"error":{"message":"Free-model daily request limit reached."}}'
                ),
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep") as sleep,
        ):
            response = adapter.chat(ChatRequest("system", "user", "openai/gpt-4o-mini"))

        self.assertEqual(calls, 1)
        sleep.assert_not_called()
        self.assertEqual(response.error_category, "provider_rate_limit")
        self.assertIn("Free-model daily request limit reached.", response.errors[0])
        self.assertIn("OpenRouter account/free-tier quota", response.errors[0])
        self.assertEqual(
            response.raw_provider_response["rate_limit"]["scope"],
            "openrouter_account",
        )

    def test_api_key_quota_is_distinguished_from_account_quota(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                hdrs={"Retry-After": "60"},
                fp=FakeHTTPResponse(
                    b'{"error":{"message":"API key quota exceeded."}}'
                ),
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep") as sleep,
        ):
            response = adapter.chat(ChatRequest("system", "user", "openai/gpt-4o-mini"))

        sleep.assert_not_called()
        self.assertIn("OpenRouter API-key quota", response.errors[0])
        self.assertEqual(
            response.raw_provider_response["rate_limit"]["scope"],
            "openrouter_api_key",
        )

    def test_upstream_provider_rate_limit_preserves_provider_attribution(self):
        calls = 0

        def fake_urlopen(request, timeout=None):
            nonlocal calls
            calls += 1
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                hdrs={"Retry-After": "2", "X-Generation-Id": "gen-upstream-1"},
                fp=FakeHTTPResponse(
                    b'{"error":{"message":"Provider returned error",'
                    b'"metadata":{"provider_name":"Google AI Studio",'
                    b'"raw":"{\\"error\\":{\\"code\\":429,\\"message\\":'
                    b'\\"Too many requests at the upstream provider.\\"}}"}}}'
                ),
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep"),
        ):
            response = adapter.chat(ChatRequest("system", "user", "google/gemini-2.5-flash"))

        self.assertEqual(calls, 3)
        self.assertIn("Upstream provider reason: Too many requests", response.errors[0])
        self.assertIn("rate-limit source: upstream provider", response.errors[0])
        self.assertIn("provider: Google AI Studio", response.errors[0])
        diagnostics = response.raw_provider_response
        self.assertEqual(diagnostics["rate_limit"]["scope"], "upstream_provider")
        self.assertEqual(
            diagnostics["error"]["metadata"]["upstream_error"]["code"],
            429,
        )
        self.assertEqual(
            diagnostics["response_headers"]["X-Generation-Id"],
            "gen-upstream-1",
        )

    def test_free_model_provider_capacity_is_not_mislabeled_as_account_quota(self):
        calls = 0
        payload = {
            "error": {
                "message": "Provider returned error",
                "metadata": {
                    "provider_name": "Google AI Studio",
                    "raw": json.dumps(
                        {
                            "api_key": "sk-never-display-this",
                            "error": {
                                "code": 429,
                                "message": "Model capacity is temporarily unavailable.",
                            }
                        }
                    ),
                    "headers": {
                        "Authorization": "Bearer never-display-this",
                        "X-RateLimit-Remaining": "0",
                    },
                },
            },
            "request": {"messages": [{"content": "private prompt"}]},
            "openrouter_metadata": {
                "requested": "google/gemma-4-26b-a4b-it:free",
                "strategy": "direct",
                "attempt": 1,
                "attempts": [
                    {
                        "provider": "Google AI Studio",
                        "model": "google/gemma-4-26b-a4b-it:free",
                        "status_code": 429,
                    }
                ],
            },
        }

        def fake_urlopen(request, timeout=None):
            nonlocal calls
            calls += 1
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                hdrs={"Retry-After": "1"},
                fp=FakeHTTPResponse(json.dumps(payload).encode("utf-8")),
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep"),
        ):
            response = adapter.chat(
                ChatRequest("system", "user", "google/gemma-4-26b-a4b-it:free")
            )

        self.assertEqual(calls, 3)
        self.assertIn("Model capacity is temporarily unavailable.", response.errors[0])
        self.assertIn("free-model upstream provider/capacity", response.errors[0])
        self.assertNotIn("account/free-tier quota", response.errors[0])
        diagnostics = response.raw_provider_response
        self.assertEqual(
            diagnostics["rate_limit"]["scope"],
            "free_model_provider_capacity",
        )
        self.assertEqual(
            diagnostics["openrouter_metadata"]["attempts"][0]["provider"],
            "Google AI Studio",
        )
        serialized_diagnostics = json.dumps(diagnostics)
        self.assertNotIn("never-display-this", serialized_diagnostics)
        self.assertNotIn("private prompt", serialized_diagnostics)
        self.assertEqual(
            diagnostics["error"]["metadata"]["response_headers"][
                "X-RateLimit-Remaining"
            ],
            "0",
        )

    def test_rate_limit_without_provider_detail_uses_generic_message(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "rate limited",
                hdrs=None,
                fp=FakeHTTPResponse(b'{"error":{}}'),
            )

        adapter = OpenRouterAdapter(api_key="or-secret", timeout_seconds=7)
        with (
            patch("urllib.request.urlopen", fake_urlopen),
            patch("bhf_agent.adapters.openai_compatible.time.sleep"),
        ):
            response = adapter.chat(ChatRequest("system", "user", "openai/gpt-4o-mini"))

        self.assertEqual(response.error_category, "provider_rate_limit")
        self.assertIn("rate limit reached; try again shortly", response.errors[0])
        self.assertIn("rate-limit source: undetermined", response.errors[0])


if __name__ == "__main__":
    unittest.main()
