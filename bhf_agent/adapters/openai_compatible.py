"""OpenAI-compatible HTTP adapter for local model runtimes."""

from __future__ import annotations

import json
import socket
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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

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
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                http_request,
                timeout=self.timeout_seconds,
            ) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = _safe_read_error(exc)
            hint = _http_error_hint(exc.code, self.base_url)
            return ChatResponse(
                text="",
                errors=[
                    f"OpenAI-compatible endpoint returned HTTP {exc.code}: "
                    f"{error_body or exc.reason}{hint}"
                ],
                raw_provider_response=error_body,
            )
        except (TimeoutError, socket.timeout) as exc:
            return ChatResponse(
                text="",
                errors=[f"OpenAI-compatible endpoint timed out: {exc}"],
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
                errors=[message],
            )
        except OSError as exc:
            return ChatResponse(
                text="",
                errors=[f"OpenAI-compatible endpoint request failed: {exc}"],
            )

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            return ChatResponse(
                text="",
                errors=[f"OpenAI-compatible endpoint returned malformed JSON: {exc}"],
                raw_provider_response=raw_body,
            )

        text, extraction_error = _extract_text(data)
        if extraction_error:
            return ChatResponse(
                text="",
                model=data.get("model") if isinstance(data, dict) else None,
                usage=data.get("usage") if isinstance(data, dict) else None,
                raw_provider_response=data,
                errors=[extraction_error],
            )

        return ChatResponse(
            text=text,
            model=data.get("model"),
            usage=data.get("usage"),
            raw_provider_response=data,
        )


def _safe_read_error(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8")
    except Exception:
        return ""


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
    first = choices[0]
    if not isinstance(first, dict):
        return None, "OpenAI-compatible endpoint returned malformed response: first choice is not an object"
    message = first.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        content = message["content"]
        if not content.strip():
            return None, "OpenAI-compatible endpoint returned empty message content"
        return content, None
    if isinstance(first.get("text"), str):
        text = first["text"]
        if not text.strip():
            return None, "OpenAI-compatible endpoint returned empty text content"
        return text, None
    return None, "OpenAI-compatible endpoint response did not include message text"
