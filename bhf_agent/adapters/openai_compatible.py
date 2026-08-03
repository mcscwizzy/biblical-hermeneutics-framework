"""OpenAI-compatible HTTP adapter for local model runtimes."""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from bhf_agent.models import ChatRequest, ChatResponse

from .base import ChatAdapter


class OpenAICompatibleAdapter(ChatAdapter):
    """Adapter for local `/v1/chat/completions` compatible endpoints."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = 120,
        provider_name: str = "openai_compatible",
        extra_headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.provider_name = provider_name
        self.extra_headers = dict(extra_headers or {})

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def supports_json_schema_response_format(self) -> bool:
        return False

    def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages()
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_format is not None:
            payload["response_format"] = request.response_format
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        headers.update(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        started_at = time.perf_counter()

        try:
            with urllib.request.urlopen(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = _safe_read_error(exc)
            hint = _http_error_hint(exc.code, self.base_url)
            provider_label = self.provider_name.replace("_", " ").title()
            return ChatResponse(
                text="",
                provider=self.provider_name,
                latency_ms=_elapsed_ms(started_at),
                errors=[
                    f"{provider_label} request failed: HTTP {exc.code}: "
                    f"{_friendly_http_error(exc.code, error_body, exc.reason)}{hint}"
                ],
                raw_provider_response=error_body,
                error_category="provider_failure",
            )
        except (TimeoutError, socket.timeout) as exc:
            return ChatResponse(
                text="",
                provider=self.provider_name,
                latency_ms=_elapsed_ms(started_at),
                errors=[f"OpenAI-compatible endpoint timed out: {exc}"],
                error_category="provider_timeout",
            )
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, ConnectionRefusedError):
                message = (
                    "Connection refused by OpenAI-compatible endpoint. "
                    "Check that the local model server is running and the base URL is correct."
                )
            else:
                message = f"Could not connect to OpenAI-compatible endpoint: {reason}"
            return ChatResponse(
                text="",
                provider=self.provider_name,
                latency_ms=_elapsed_ms(started_at),
                errors=[message],
                error_category="provider_connection",
            )
        except OSError as exc:
            return ChatResponse(
                text="",
                provider=self.provider_name,
                latency_ms=_elapsed_ms(started_at),
                errors=[f"OpenAI-compatible endpoint request failed: {exc}"],
                error_category="provider_failure",
            )

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            return ChatResponse(
                text="",
                provider=self.provider_name,
                latency_ms=_elapsed_ms(started_at),
                errors=[f"OpenAI-compatible endpoint returned malformed JSON: {exc}"],
                raw_provider_response=raw_body,
                error_category="provider_failure",
            )

        text, extraction_error = _extract_text(data)
        if extraction_error:
            return ChatResponse(
                text="",
                model=data.get("model") if isinstance(data, dict) else None,
                provider=self.provider_name,
                latency_ms=_elapsed_ms(started_at),
                usage=data.get("usage") if isinstance(data, dict) else None,
                raw_provider_response=data,
                errors=[extraction_error],
                error_category="response_extraction",
            )

        return ChatResponse(
            text=text,
            model=data.get("model"),
            provider=self.provider_name,
            latency_ms=_elapsed_ms(started_at),
            usage=data.get("usage"),
            raw_provider_response=data,
        )

    def health_check(self, model: Optional[str] = None) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                    method="GET",
                ),
                timeout=self.timeout_seconds,
            ) as response:
                raw_body = response.read().decode("utf-8")
            data = json.loads(raw_body)
        except Exception as exc:  # pragma: no cover - defensive health reporting
            return {
                "ok": False,
                "provider": self.provider_name,
                "model": model,
                "base_url": self.base_url,
                "error": str(exc),
            }

        available_models = _available_models(data)
        return {
            "ok": True,
            "provider": self.provider_name,
            "model": model,
            "base_url": self.base_url,
            "model_present": model is None or model in available_models,
            "available_models": available_models,
        }

    def _headers(self) -> dict[str, str]:
        headers = dict(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _safe_read_error(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return ""
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message") or error.get("code")
                return str(message)[:240] if message else ""
            if isinstance(error, str):
                return error[:240]
        return ""
    except Exception:
        return ""


def _friendly_http_error(status_code: int, detail: str, reason: object) -> str:
    if status_code == 401:
        return "the saved credential was rejected"
    if status_code == 402:
        return "the provider account needs credits"
    if status_code == 403:
        return "the provider denied this request"
    if status_code == 404:
        return detail or "the selected model or endpoint was not found"
    if status_code == 429:
        return "rate limit reached; try again shortly"
    if status_code in {502, 503}:
        return "the selected model is temporarily unavailable"
    return detail or "the provider returned an error"


def _elapsed_ms(started_at: float) -> int:
    return int(round((time.perf_counter() - started_at) * 1000))


def _http_error_hint(status_code: int, base_url: str) -> str:
    if status_code == 404 and not base_url.rstrip("/").endswith("/v1"):
        return (
            " Hint: OpenAI-compatible endpoints usually need a base URL ending "
            "in /v1, such as http://host:11434/v1."
        )
    if status_code == 404:
        return " Hint: check that the local server exposes /chat/completions under this base URL."
    return ""


def _extract_text(data: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(data, dict):
        return None, "OpenAI-compatible endpoint returned malformed response: top-level JSON is not an object"
    choices = data.get("choices")
    if not isinstance(choices, list):
        return None, "OpenAI-compatible endpoint returned malformed response: choices is missing or not a list"
    if not choices:
        return None, "OpenAI-compatible endpoint returned empty choices; response did not include message text"
    empty_error: Optional[str] = None
    for choice in choices:
        text, error = _extract_choice_text(choice)
        if text:
            return text, None
        if error and empty_error is None:
            empty_error = error
    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            text = _extract_block_text(item)
            if text:
                return text, None
    return None, empty_error or "OpenAI-compatible endpoint response did not include message text"


def _extract_choice_text(choice: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(choice, dict):
        return None, None
    for key in ("message", "delta", "text", "content", "output"):
        value = choice.get(key)
        if value is None:
            continue
        if key == "message" and isinstance(value, dict):
            content = value.get("content")
            if isinstance(content, str) and not content.strip():
                return None, "OpenAI-compatible endpoint returned empty message content"
        if key in {"text", "content"} and isinstance(value, str) and not value.strip():
            return None, "OpenAI-compatible endpoint returned empty text content"
        text = _extract_block_text(value)
        if text:
            return text, None
    return None, None


def _extract_block_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, list):
        blocks: list[str] = []
        for item in value:
            text = _extract_block_text(item)
            if text:
                blocks.append(text)
        return "\n".join(blocks) if blocks else None
    if isinstance(value, dict):
        block_type = str(value.get("type") or value.get("role") or "").strip().lower()
        if block_type in {"analysis", "debug", "reasoning", "tool_call", "tool_calls"}:
            return None
        for key in ("content", "text", "output_text", "answer", "response", "delta"):
            if key in value:
                text = _extract_block_text(value.get(key))
                if text:
                    return text
        return None
    return None


def _available_models(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    models = data.get("data")
    if not isinstance(models, list):
        models = data.get("models")
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for model in models:
        if isinstance(model, dict):
            name = model.get("id") or model.get("name")
            if isinstance(name, str):
                names.append(name)
    return names
