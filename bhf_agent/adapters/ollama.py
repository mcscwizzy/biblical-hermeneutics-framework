"""Ollama HTTP adapter for local `/api/chat` calls."""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from bhf_agent.models import ChatRequest, ChatResponse

from .base import ChatAdapter


class OllamaAdapter(ChatAdapter):
    """Adapter for Ollama's native chat API."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: Optional[float] = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/api/chat"

    def supports_json_schema_response_format(self) -> bool:
        return False

    def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages()
            ],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "num_ctx": request.context_window,
            },
        }
        if request.response_format is not None:
            payload["format"] = "json"
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
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
            return ChatResponse(
                text="",
                provider="ollama",
                latency_ms=_elapsed_ms(started_at),
                errors=[
                    f"Ollama endpoint returned HTTP {exc.code}: "
                    f"{error_body or exc.reason}"
                ],
                raw_provider_response=error_body,
            )
        except (TimeoutError, socket.timeout) as exc:
            return ChatResponse(
                text="",
                provider="ollama",
                latency_ms=_elapsed_ms(started_at),
                errors=[f"Ollama endpoint timed out: {exc}"],
            )
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, ConnectionRefusedError):
                message = (
                    "Connection refused by Ollama endpoint. "
                    "Check that the Ollama service is running and the base URL is correct."
                )
            else:
                message = f"Could not connect to Ollama endpoint: {reason}"
            return ChatResponse(
                text="",
                provider="ollama",
                latency_ms=_elapsed_ms(started_at),
                errors=[message],
            )
        except OSError as exc:
            return ChatResponse(
                text="",
                provider="ollama",
                latency_ms=_elapsed_ms(started_at),
                errors=[f"Ollama endpoint request failed: {exc}"],
            )

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            return ChatResponse(
                text="",
                provider="ollama",
                latency_ms=_elapsed_ms(started_at),
                errors=[f"Ollama endpoint returned malformed JSON: {exc}"],
                raw_provider_response=raw_body,
            )

        text, extraction_error = _extract_text(data)
        if extraction_error:
            return ChatResponse(
                text="",
                model=data.get("model") if isinstance(data, dict) else None,
                provider="ollama",
                latency_ms=_elapsed_ms(started_at),
                raw_provider_response=data,
                errors=[extraction_error],
            )

        return ChatResponse(
            text=text,
            model=data.get("model"),
            provider="ollama",
            latency_ms=_elapsed_ms(started_at),
            raw_provider_response=data,
        )

    def health_check(self, model: Optional[str] = None) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(self._tags_request(), timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
            data = json.loads(raw_body)
        except Exception as exc:  # pragma: no cover - defensive health reporting
            return {
                "ok": False,
                "provider": "ollama",
                "model": model,
                "base_url": self.base_url,
                "error": str(exc),
            }

        models = data.get("models") if isinstance(data, dict) else None
        model_names = _model_names(models)
        return {
            "ok": True,
            "provider": "ollama",
            "model": model,
            "base_url": self.base_url,
            "model_present": model is None or model in model_names,
            "available_models": model_names,
        }

    def _tags_request(self) -> urllib.request.Request:
        return urllib.request.Request(f"{self.base_url}/api/tags", method="GET")


def _safe_read_error(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8")
    except Exception:
        return ""


def _elapsed_ms(started_at: float) -> int:
    return int(round((time.perf_counter() - started_at) * 1000))


def _extract_text(data: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(data, dict):
        return None, "Ollama endpoint returned malformed response: top-level JSON is not an object"
    message = data.get("message")
    if isinstance(message, dict):
        content = _extract_block_text(message.get("content"))
        if content:
            return content, None
    response = _extract_block_text(data.get("response"))
    if response:
        return response, None
    return None, "Ollama endpoint response did not include message text"


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


def _model_names(models: Any) -> list[str]:
    if not isinstance(models, list):
        return []
    names = []
    for model in models:
        if isinstance(model, dict) and isinstance(model.get("name"), str):
            names.append(model["name"])
    return names
