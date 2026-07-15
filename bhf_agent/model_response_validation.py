"""Validation and normalization for model-generated output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .models import Serializable
from .output_cleaner import clean_model_output


ANSWER_CONTRACT = "answer"
SEARCH_RESULTS_CONTRACT = "search_results"
STRUCTURED_RESPONSE_FORMAT = {"type": "json_object"}

CKL_PATH_RE = re.compile(
    r"(?i)\b(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:json|ya?ml|md)\b"
)
PROVIDER_ERROR_RE = re.compile(
    r"(?i)\b("
    r"openai-compatible endpoint returned http\s+\d+|"
    r"ollama endpoint returned http\s+\d+|"
    r"model backend returned an error|"
    r"could not connect to .*endpoint|"
    r"connection refused|"
    r"timed out|"
    r"provider error"
    r")\b"
)
RETRIEVAL_SCORE_RE = re.compile(
    r"(?i)\b(?:retrieval|relevance|match)\s+score\b|\bscore\s*[:=]\s*(?:0(?:\.\d+)?|1(?:\.0+)?)\b"
)
JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$", re.IGNORECASE)
@dataclass
class ModelResponseValidationResult(Serializable):
    passed: bool
    sanitized_text: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    response_contract: str = ANSWER_CONTRACT
    structured_output: bool = False
    parsed_payload: dict[str, Any] | None = None
    removed_headings: list[str] = field(default_factory=list)
    raw_text_was_json: bool = False


def structured_response_format() -> dict[str, Any]:
    return dict(STRUCTURED_RESPONSE_FORMAT)


def normalize_model_response(
    text: str,
    *,
    raw_provider_response: Any = None,
    response_contract: str = ANSWER_CONTRACT,
) -> ModelResponseValidationResult:
    """Normalize model output into a safe, user-facing string.

    The answer contract is strict: structured JSON is parsed and reduced to the
    `answer` field, internal prompt blocks are stripped, and any remaining
    retrieval/debug leakage is rejected or removed before display.

    The search-results contract is intentionally lighter-weight so the existing
    Bible-search fallback can keep returning structured JSON payloads.
    """

    contract = response_contract or ANSWER_CONTRACT
    raw_text = (text or "").strip()
    warnings: list[str] = []
    errors: list[str] = []
    removed_headings: list[str] = []
    structured_output = False
    parsed_payload: dict[str, Any] | None = None
    raw_text_was_json = False

    provider_error = _provider_error_message(raw_provider_response)
    if provider_error:
        errors.append(provider_error)

    if contract == SEARCH_RESULTS_CONTRACT:
        sanitized_text, contract_warnings = _normalize_search_results(raw_text)
        warnings.extend(contract_warnings)
        parsed = _parse_json_candidate(raw_text)
        is_valid_results_json = isinstance(parsed, dict) and isinstance(
            parsed.get("results"), list
        )
        if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
            structured_output = True
            parsed_payload = parsed
            raw_text_was_json = True
        if provider_error:
            sanitized_text = ""
        return ModelResponseValidationResult(
            passed=is_valid_results_json and not errors,
            sanitized_text=sanitized_text,
            warnings=warnings,
            errors=errors,
            response_contract=contract,
            structured_output=structured_output,
            parsed_payload=parsed_payload,
            removed_headings=removed_headings,
            raw_text_was_json=raw_text_was_json,
        )

    if not raw_text:
        errors.append("Model response was empty.")
        return ModelResponseValidationResult(
            passed=False,
            sanitized_text="",
            warnings=warnings,
            errors=errors,
            response_contract=contract,
        )

    parsed = _parse_json_candidate(raw_text)
    if parsed is not None:
        raw_text_was_json = True
        parsed_payload = parsed if isinstance(parsed, dict) else None
        if isinstance(parsed, dict):
            answer = _extract_answer_from_payload(parsed)
            if answer is None:
                errors.append("Model response returned JSON without an answer field.")
                return ModelResponseValidationResult(
                    passed=False,
                    sanitized_text="",
                    warnings=warnings,
                    errors=errors,
                    response_contract=contract,
                    parsed_payload=parsed_payload,
                    raw_text_was_json=True,
                )
            structured_output = True
            if _has_extra_keys(parsed):
                warnings.append("Structured response envelope was removed.")
            raw_text = answer
        else:
            errors.append("Model response returned JSON that was not an object.")
            return ModelResponseValidationResult(
                passed=False,
                sanitized_text="",
                warnings=warnings,
                errors=errors,
                response_contract=contract,
                raw_text_was_json=True,
            )

    cleanup_result = clean_model_output(raw_text)
    sanitized_text = cleanup_result.text.strip()
    if cleanup_result.applied:
        warnings.append("Removed leaked runtime instruction headings.")
    removed_headings.extend(cleanup_result.removed_headings)

    if not sanitized_text:
        errors.append("Model response was empty after cleanup.")
        return ModelResponseValidationResult(
            passed=False,
            sanitized_text="",
            warnings=warnings,
            errors=errors,
            response_contract=contract,
            structured_output=structured_output,
            parsed_payload=parsed_payload,
            removed_headings=removed_headings,
            raw_text_was_json=raw_text_was_json,
        )

    sanitized_text, section_headings = _truncate_internal_sections(sanitized_text)
    if section_headings:
        removed_headings.extend(section_headings)
        warnings.append("Removed internal analysis sections from model output.")

    sanitized_text = sanitized_text.strip()
    if not sanitized_text:
        errors.append("Model response was empty after removing internal sections.")
        return ModelResponseValidationResult(
            passed=False,
            sanitized_text="",
            warnings=warnings,
            errors=errors,
            response_contract=contract,
            structured_output=structured_output,
            parsed_payload=parsed_payload,
            removed_headings=removed_headings,
            raw_text_was_json=raw_text_was_json,
        )

    if _looks_like_json(sanitized_text):
        errors.append("Model response returned raw JSON when prose was requested.")

    if _contains_forbidden_patterns(sanitized_text):
        errors.append("Model response still contains internal prompt content.")

    if PROVIDER_ERROR_RE.search(sanitized_text):
        errors.append("Model response appears to contain a provider error message.")

    if CKL_PATH_RE.search(sanitized_text):
        errors.append("Model response exposes a CKL file path.")

    if RETRIEVAL_SCORE_RE.search(sanitized_text):
        errors.append("Model response exposes retrieval scoring metadata.")

    return ModelResponseValidationResult(
        passed=not errors,
        sanitized_text=sanitized_text,
        warnings=warnings,
        errors=errors,
        response_contract=contract,
        structured_output=structured_output,
        parsed_payload=parsed_payload,
        removed_headings=removed_headings,
        raw_text_was_json=raw_text_was_json,
    )


def _normalize_search_results(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not text:
        return "", warnings

    cleaned = _strip_code_fence(text)
    if cleaned != text:
        warnings.append("Removed markdown code fences from search results.")

    parsed = _parse_json_candidate(cleaned)
    if parsed is None:
        warnings.append("Search results response was not valid JSON.")
        return cleaned, warnings
    if not isinstance(parsed, dict):
        warnings.append("Search results response was not a JSON object.")
        return cleaned, warnings
    if not isinstance(parsed.get("results"), list):
        warnings.append("Search results response did not include a results array.")
        return cleaned, warnings
    return json.dumps(parsed, ensure_ascii=False), warnings


def _parse_json_candidate(text: str) -> Any:
    candidate = _strip_code_fence(text)
    if not candidate:
        return None
    if candidate[0] not in "{[":
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _strip_code_fence(text: str) -> str:
    match = JSON_FENCE_RE.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_answer_from_payload(payload: dict[str, Any]) -> str | None:
    for key in ("answer", "text", "content", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    message = payload.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def _has_extra_keys(payload: dict[str, Any]) -> bool:
    allowed = {"answer", "text", "content", "output", "message"}
    return any(key not in allowed for key in payload)


def _truncate_internal_sections(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    removed: list[str] = []
    kept: list[str] = []
    for line in lines:
        heading = _internal_heading(line)
        if heading:
            removed.append(heading)
            break
        kept.append(line)
    if not removed:
        return text, []
    return "\n".join(kept).strip(), removed


def _looks_like_json(text: str) -> bool:
    candidate = _strip_code_fence(text)
    return bool(candidate) and candidate[0] in "{["


def _internal_heading(line: str) -> str | None:
    normalized = line.strip().lstrip("#").strip().rstrip(":").lower()
    for heading in _internal_headings():
        if normalized == heading:
            return heading
    return None


def _internal_headings() -> tuple[str, ...]:
    return (
        "analysis",
        "thought process",
        "retrieved context",
        "search results",
        "sources used",
        "internal notes",
        "system instructions",
        "canonical knowledge context",
        "optional conversation context",
        "output requirements",
        "debug",
    )


def _contains_forbidden_patterns(text: str) -> bool:
    for line in text.splitlines():
        if _internal_heading(line):
            return True
    return False


def _provider_error_message(raw_provider_response: Any) -> str | None:
    if isinstance(raw_provider_response, dict):
        for key in ("error", "message", "detail", "details"):
            value = raw_provider_response.get(key)
            if isinstance(value, str) and PROVIDER_ERROR_RE.search(value):
                return value
        nested = raw_provider_response.get("errors")
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, str) and PROVIDER_ERROR_RE.search(item):
                    return item
    if isinstance(raw_provider_response, str) and PROVIDER_ERROR_RE.search(raw_provider_response):
        return raw_provider_response
    return None
