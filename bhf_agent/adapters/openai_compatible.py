"""OpenAI-compatible HTTP adapter for local model runtimes."""

from __future__ import annotations

import json
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
        max_rate_limit_retries: int = 0,
        rate_limit_retry_seconds: float = 1.0,
        max_rate_limit_retry_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.provider_name = provider_name
        self.extra_headers = dict(extra_headers or {})
        self.max_rate_limit_retries = max(0, int(max_rate_limit_retries))
        self.rate_limit_retry_seconds = max(0.0, float(rate_limit_retry_seconds))
        self.max_rate_limit_retry_seconds = max(
            self.rate_limit_retry_seconds,
            float(max_rate_limit_retry_seconds),
        )

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
        rate_limit_retries = 0

        while True:
            try:
                with urllib.request.urlopen(
                    http_request,
                    timeout=self.timeout_seconds,
                ) as response:
                    raw_body = response.read().decode("utf-8")
                break
            except urllib.error.HTTPError as exc:
                error_detail, error_diagnostics = _safe_read_error(exc)
                rate_limit = (
                    _classify_rate_limit(
                        error_detail,
                        exc.headers,
                        error_diagnostics,
                        requested_model=request.model,
                    )
                    if exc.code == 429
                    else None
                )
                if (
                    exc.code == 429
                    and _should_retry_rate_limit(rate_limit)
                    and rate_limit_retries < self.max_rate_limit_retries
                ):
                    delay = _rate_limit_retry_delay(
                        exc.headers,
                        retry_number=rate_limit_retries,
                        base_delay_seconds=self.rate_limit_retry_seconds,
                        max_delay_seconds=self.max_rate_limit_retry_seconds,
                    )
                    rate_limit_retries += 1
                    time.sleep(delay)
                    continue
                hint = _http_error_hint(exc.code, self.base_url)
                provider_label = _provider_label(self.provider_name)
                if rate_limit is not None:
                    error_diagnostics["rate_limit"] = rate_limit
                    error_diagnostics["requested_model"] = request.model
                    rate_limit_context = _format_rate_limit_context(rate_limit)
                else:
                    rate_limit_context = ""
                return ChatResponse(
                    text="",
                    provider=self.provider_name,
                    latency_ms=_elapsed_ms(started_at),
                    errors=[
                        f"{provider_label} request failed: HTTP {exc.code}: "
                        f"{_friendly_http_error(exc.code, error_detail, exc.reason)}"
                        f"{rate_limit_context}{hint}"
                    ],
                    raw_provider_response=error_diagnostics,
                    error_category=(
                        "provider_rate_limit"
                        if exc.code == 429
                        else "provider_failure"
                    ),
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
            warnings=(
                [
                    "The provider briefly rate-limited this request; BHF retried automatically."
                ]
                if rate_limit_retries
                else []
            ),
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


def _safe_read_error(exc: urllib.error.HTTPError) -> tuple[str, dict[str, Any]]:
    """Return a display-safe reason and structured provider diagnostics."""

    safe_headers = _safe_response_headers(exc.headers)
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            detail = _sanitize_provider_detail(raw) if raw.strip() else ""
            diagnostics: dict[str, Any] = {"error": {"message": detail}}
            if safe_headers:
                diagnostics["response_headers"] = safe_headers
            return detail, diagnostics
        if isinstance(payload, dict):
            diagnostics = _safe_error_diagnostics(payload, safe_headers)
            detail = _error_detail_from_diagnostics(diagnostics)
            return detail, diagnostics
        diagnostics = {"error": {"message": ""}}
        if safe_headers:
            diagnostics["response_headers"] = safe_headers
        return "", diagnostics
    except Exception:
        diagnostics = {"error": {"message": ""}}
        if safe_headers:
            diagnostics["response_headers"] = safe_headers
        return "", diagnostics
    finally:
        exc.close()


def _sanitize_provider_detail(detail: object) -> str:
    """Keep a short provider message while redacting common credential forms."""

    message = str(detail).strip()[:240]
    message = re.sub(r"(?i)\bbearer\s+[^\s,;]+", "Bearer [redacted]", message)
    message = re.sub(
        r"(?i)\b(authorization|api[-_ ]?key|access[-_ ]?token)\b\s*[:=]\s*[^\s,;]+",
        r"\1: [redacted]",
        message,
    )
    message = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[redacted]", message)
    return message


def _safe_response_headers(headers: Any) -> dict[str, str]:
    """Keep only non-secret response headers useful for rate-limit diagnosis."""

    if not headers:
        return {}
    safe: dict[str, str] = {}
    try:
        items = headers.items()
    except AttributeError:
        return safe
    for name, value in items:
        normalized = str(name).strip().lower()
        if normalized in {
            "retry-after",
            "x-generation-id",
            "x-request-id",
            "x-openrouter-request-id",
        } or "ratelimit" in normalized or "rate-limit" in normalized:
            safe[str(name)] = _sanitize_provider_detail(value)
    return safe


def _safe_error_diagnostics(
    payload: dict[str, Any],
    safe_headers: dict[str, str],
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    error = payload.get("error")
    safe_error: dict[str, Any] = {}
    if isinstance(error, dict):
        for key in ("code", "type", "param"):
            value = error.get(key)
            if isinstance(value, (str, int, float, bool)):
                safe_error[key] = (
                    _sanitize_provider_detail(value) if isinstance(value, str) else value
                )
        message = error.get("message")
        if message:
            safe_error["message"] = _sanitize_provider_detail(message)
        metadata = _safe_error_metadata(error.get("metadata"))
        if metadata:
            safe_error["metadata"] = metadata
    elif isinstance(error, str):
        safe_error["message"] = _sanitize_provider_detail(error)
    else:
        message = payload.get("message")
        if message:
            safe_error["message"] = _sanitize_provider_detail(message)
    diagnostics["error"] = safe_error or {"message": ""}

    router_metadata = _safe_openrouter_metadata(payload.get("openrouter_metadata"))
    if router_metadata:
        diagnostics["openrouter_metadata"] = router_metadata
    if safe_headers:
        diagnostics["response_headers"] = safe_headers
    return diagnostics


def _safe_error_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    safe: dict[str, Any] = {}
    for key in ("provider_name", "provider", "model", "status", "status_code"):
        value = metadata.get(key)
        if isinstance(value, (str, int, float, bool)):
            safe[key] = _sanitize_provider_detail(value) if isinstance(value, str) else value

    upstream_error = _safe_upstream_error(metadata.get("raw"))
    if upstream_error:
        safe["upstream_error"] = upstream_error
    metadata_headers = _safe_response_headers(metadata.get("headers"))
    if metadata_headers:
        safe["response_headers"] = metadata_headers
    return safe


def _safe_upstream_error(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    parsed = raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            message = _sanitize_provider_detail(raw)
            return {"message": message} if message else {}
    if not isinstance(parsed, dict):
        return {}
    error = parsed.get("error", parsed)
    if isinstance(error, dict):
        safe: dict[str, Any] = {}
        code = error.get("code")
        if isinstance(code, (str, int, float)):
            safe["code"] = _sanitize_provider_detail(code) if isinstance(code, str) else code
        message = error.get("message") or error.get("detail")
        if message:
            safe["message"] = _sanitize_provider_detail(message)
        return safe
    if isinstance(error, str):
        return {"message": _sanitize_provider_detail(error)}
    return {}


def _safe_openrouter_metadata(metadata: Any) -> dict[str, Any]:
    """Summarize routing metadata without retaining prompts or provider headers."""

    if not isinstance(metadata, dict):
        return {}
    safe: dict[str, Any] = {}
    for key in ("requested", "strategy", "attempt"):
        value = metadata.get(key)
        if isinstance(value, (str, int, float, bool)):
            safe[key] = _sanitize_provider_detail(value) if isinstance(value, str) else value

    attempts = _safe_routing_entries(metadata.get("attempts"))
    if attempts:
        safe["attempts"] = attempts
    endpoints = metadata.get("endpoints")
    if isinstance(endpoints, dict):
        available = _safe_routing_entries(endpoints.get("available"))
        safe_endpoints: dict[str, Any] = {}
        if isinstance(endpoints.get("total"), int):
            safe_endpoints["total"] = endpoints["total"]
        if available:
            safe_endpoints["available"] = available
        if safe_endpoints:
            safe["endpoints"] = safe_endpoints
    return safe


def _safe_routing_entries(entries: Any) -> list[dict[str, Any]]:
    if not isinstance(entries, list):
        return []
    safe_entries: list[dict[str, Any]] = []
    for entry in entries[:10]:
        if not isinstance(entry, dict):
            continue
        safe_entry: dict[str, Any] = {}
        for key in (
            "provider",
            "provider_name",
            "model",
            "status",
            "status_code",
            "code",
            "selected",
        ):
            value = entry.get(key)
            if isinstance(value, (str, int, float, bool)):
                safe_entry[key] = (
                    _sanitize_provider_detail(value) if isinstance(value, str) else value
                )
        error = entry.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("detail")
            if message:
                safe_entry["error"] = _sanitize_provider_detail(message)
        elif isinstance(error, str):
            safe_entry["error"] = _sanitize_provider_detail(error)
        if safe_entry:
            safe_entries.append(safe_entry)
    return safe_entries


def _error_detail_from_diagnostics(diagnostics: dict[str, Any]) -> str:
    error = diagnostics.get("error")
    if not isinstance(error, dict):
        return ""
    detail = str(error.get("message") or error.get("code") or "").strip()
    metadata = error.get("metadata")
    upstream_error = metadata.get("upstream_error") if isinstance(metadata, dict) else None
    upstream_detail = (
        str(upstream_error.get("message") or upstream_error.get("code") or "").strip()
        if isinstance(upstream_error, dict)
        else ""
    )
    if upstream_detail and upstream_detail.lower() not in detail.lower():
        if detail:
            return f"{detail} Upstream provider reason: {upstream_detail}"
        return upstream_detail
    return detail


def _provider_label(provider_name: str) -> str:
    if provider_name.strip().lower() == "openrouter":
        return "OpenRouter"
    return provider_name.replace("_", " ").title()


def _classify_rate_limit(
    detail: str,
    headers: Any,
    diagnostics: dict[str, Any],
    *,
    requested_model: str,
) -> dict[str, Any]:
    """Classify 429 origin conservatively, favoring provider routing evidence."""

    normalized = " ".join(str(detail or "").lower().replace("-", " ").split())
    provider_names = _rate_limit_provider_names(diagnostics)
    upstream_evidence = bool(provider_names) or "upstream provider" in normalized
    is_free_model = requested_model.lower().endswith(":free")
    capacity_markers = (
        "capacity",
        "overloaded",
        "provider busy",
        "temporarily throttled",
        "temporarily unavailable",
    )
    account_markers = ("account", "workspace", "organization", "credits", "credit balance")
    api_key_markers = ("api key", "per key", "key quota", "key limit")
    daily_free_quota = any(
        marker in normalized
        for marker in (
            "free model daily request limit",
            "daily free model limit",
            "free model requests per day",
        )
    )
    quota_markers = (
        "quota",
        "daily limit",
        "free model limit",
        "free tier",
        "requests per day",
        "request per day",
        "allowance exhausted",
        "exhausted allowance",
    )

    if upstream_evidence:
        scope = (
            "free_model_provider_capacity"
            if is_free_model and any(marker in normalized for marker in capacity_markers)
            else "upstream_provider"
        )
        kind = "transient_rate_limit"
        retryable = True
    elif any(marker in normalized for marker in api_key_markers):
        scope = "openrouter_api_key"
        kind = "quota_exhausted"
        retryable = False
    elif daily_free_quota or any(marker in normalized for marker in account_markers):
        scope = "openrouter_account"
        kind = "quota_exhausted"
        retryable = False
    elif any(marker in normalized for marker in capacity_markers):
        scope = "free_model_provider_capacity" if is_free_model else "upstream_provider"
        kind = "transient_rate_limit"
        retryable = True
    elif any(marker in normalized for marker in quota_markers):
        scope = "unknown"
        kind = "quota_exhausted"
        retryable = False
    elif (
        "rate limit" in normalized
        or "too many requests" in normalized
        or (headers and headers.get("Retry-After") is not None)
    ):
        scope = "unknown"
        kind = "transient_rate_limit"
        retryable = True
    else:
        scope = "unknown"
        kind = "unknown_rate_limit"
        retryable = True

    result: dict[str, Any] = {
        "kind": kind,
        "scope": scope,
        "retryable": retryable,
        "model": requested_model,
    }
    if provider_names:
        result["providers"] = provider_names
    return result


def _rate_limit_provider_names(diagnostics: dict[str, Any]) -> list[str]:
    names: list[str] = []
    error = diagnostics.get("error")
    metadata = error.get("metadata") if isinstance(error, dict) else None
    if isinstance(metadata, dict):
        for key in ("provider_name", "provider"):
            value = metadata.get(key)
            if value and str(value) not in names:
                names.append(str(value))
    router = diagnostics.get("openrouter_metadata")
    if isinstance(router, dict):
        for entry in router.get("attempts") or []:
            if not isinstance(entry, dict):
                continue
            value = entry.get("provider_name") or entry.get("provider")
            if value and str(value) not in names:
                names.append(str(value))
    return [name[:80] for name in names[:5]]


def _should_retry_rate_limit(rate_limit: dict[str, Any] | None) -> bool:
    return bool(rate_limit and rate_limit.get("retryable"))


def _format_rate_limit_context(rate_limit: dict[str, Any]) -> str:
    scope_labels = {
        "openrouter_account": "OpenRouter account/free-tier quota",
        "openrouter_api_key": "OpenRouter API-key quota",
        "upstream_provider": "upstream provider",
        "free_model_provider_capacity": "free-model upstream provider/capacity",
        "unknown": "undetermined",
    }
    source = scope_labels.get(str(rate_limit.get("scope")), "undetermined")
    providers = ", ".join(str(value) for value in rate_limit.get("providers") or [])
    model = str(rate_limit.get("model") or "").strip()
    details = [f"rate-limit source: {source}"]
    if providers:
        details.append(f"provider: {providers}")
    if model:
        details.append(f"model: {model}")
    return f" ({'; '.join(details)})"


def _rate_limit_retry_delay(
    headers: Any,
    *,
    retry_number: int,
    base_delay_seconds: float,
    max_delay_seconds: float,
) -> float:
    """Choose a bounded delay, preferring a provider-provided Retry-After."""

    fallback_delay = base_delay_seconds * (2**retry_number)
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after:
        try:
            delay = float(str(retry_after).strip())
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(retry_after))
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, IndexError, OverflowError):
                delay = fallback_delay
    else:
        delay = fallback_delay
    return min(max(0.0, delay), max_delay_seconds)


def _friendly_http_error(status_code: int, detail: str, reason: object) -> str:
    if detail:
        return detail
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
