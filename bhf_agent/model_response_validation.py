"""Validation and normalization for model-generated output."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .models import Serializable
from .observability import render_log_record
from .output_cleaner import clean_model_output


ANSWER_CONTRACT = "answer"
SEARCH_RESULTS_CONTRACT = "search_results"
STRUCTURED_RESPONSE_FORMAT = {"type": "json_object"}
STRICT_ANSWER_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "bhf_answer",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "minLength": 1},
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}
LOGGER = logging.getLogger(__name__)

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
# CKL prompt entries are research serialization, not user-facing prose.  The
# combined shape is deliberately strict so an ordinary use of "entry" or
# "summary" in an answer is not rejected.
CKL_ENTRY_HEADING_RE = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?entry\s*:")
CKL_FIELD_RE = re.compile(r"(?im)^\s*(?:category|summary|source id(?:s)?)\s*:")
JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$", re.IGNORECASE)
FORBIDDEN_RESPONSE_KEYS = {
    "analysis",
    "reasoning",
    "thought_process",
    "chain_of_thought",
    "debug",
    "metadata",
    "usage",
    "tool_calls",
    "tools",
    "retrieval",
    "canonical_context",
    "prompt",
    "system",
}
ANSWER_PRIORITY_KEYS = (
    "answer",
    "answer_text",
    "final_answer",
    "assistant_answer",
    "assistant_response",
    "final",
    "response",
    "reply",
    "text",
    "content",
    "body",
    "markdown",
    "output_text",
    "output",
    "outputs",
    "result",
    "message",
    "data",
    "choices",
    "candidates",
    "parts",
    "sections",
)
ANSWER_SECTION_KEYS = (
    "short_answer",
    "summary",
    "explanation",
    "details",
    "application",
    "context",
    "conclusion",
)
SAFE_RECOVERY_KEYS = {"generated_text", "completion"}
IGNORED_BLOCK_TYPES = {"analysis", "debug", "reasoning", "tool_call", "tool_calls"}
TEXT_BLOCK_TYPES = {"text", "output_text"}


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
    diagnostics: dict[str, Any] = field(default_factory=dict)


def structured_response_format(*, prefer_json_schema: bool = False) -> dict[str, Any]:
    if prefer_json_schema:
        return json.loads(json.dumps(STRICT_ANSWER_RESPONSE_FORMAT))
    return dict(STRUCTURED_RESPONSE_FORMAT)


def normalize_model_response(
    text: str,
    *,
    raw_provider_response: Any = None,
    response_contract: str = ANSWER_CONTRACT,
    diagnostics: Mapping[str, Any] | None = None,
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
    payload_diagnostics: dict[str, Any] = dict(diagnostics or {})

    provider_error = _provider_error_message(raw_provider_response)
    if provider_error:
        errors.append(provider_error)

    if contract == SEARCH_RESULTS_CONTRACT:
        sanitized_text, contract_warnings = _normalize_search_results(raw_text)
        warnings.extend(contract_warnings)
        parsed = _parse_json_candidate(raw_text)
        if parsed is not None:
            payload_diagnostics.update(_payload_diagnostics(parsed, payload_diagnostics))
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
            diagnostics=payload_diagnostics,
        )

    if not raw_text:
        errors.append("Model response was empty.")
        return ModelResponseValidationResult(
            passed=False,
            sanitized_text="",
            warnings=warnings,
            errors=errors,
            response_contract=contract,
            diagnostics=payload_diagnostics,
        )

    parsed = _parse_json_candidate(raw_text)
    if parsed is not None:
        raw_text_was_json = True
        parsed_payload = parsed if isinstance(parsed, dict) else None
        if isinstance(parsed, dict):
            payload_diagnostics.update(_payload_diagnostics(parsed, payload_diagnostics))
            answer = _extract_answer_from_payload(parsed)
            if answer is None:
                recovered_answer, recovered_field = _recover_answer_from_payload(parsed)
                if recovered_answer is None:
                    error_message = "Model response JSON contained no extractable answer text."
                    errors.append(error_message)
                    payload_diagnostics["normalization_error"] = error_message
                    LOGGER.warning(
                        "Model response normalization failed: %s",
                        render_log_record(payload_diagnostics),
                    )
                    return ModelResponseValidationResult(
                        passed=False,
                        sanitized_text="",
                        warnings=warnings,
                        errors=errors,
                        response_contract=contract,
                        parsed_payload=parsed_payload,
                        raw_text_was_json=True,
                        diagnostics=payload_diagnostics,
                    )
                answer = recovered_answer
                recovered_warning = (
                    f"Recovered answer text from an unrecognized JSON field: {recovered_field}"
                )
                warnings.append(recovered_warning)
                payload_diagnostics["recovered_from"] = recovered_field
                payload_diagnostics["recovered"] = True
                LOGGER.warning(
                    "Recovered model response text: %s",
                    render_log_record(payload_diagnostics),
                )
            structured_output = True
            if _has_extra_keys(parsed):
                warnings.append("Structured response envelope was removed.")
            raw_text = answer
        elif isinstance(parsed, list):
            payload_diagnostics.update(_payload_diagnostics(parsed, payload_diagnostics))
            answer = _extract_text_value(parsed)
            if answer is None:
                error_message = "Model response JSON contained no extractable answer text."
                errors.append(error_message)
                payload_diagnostics["normalization_error"] = error_message
                LOGGER.warning(
                    "Model response normalization failed: %s",
                    render_log_record(payload_diagnostics),
                )
                return ModelResponseValidationResult(
                    passed=False,
                    sanitized_text="",
                    warnings=warnings,
                    errors=errors,
                    response_contract=contract,
                    raw_text_was_json=True,
                    diagnostics=payload_diagnostics,
                )
            structured_output = True
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
                diagnostics=payload_diagnostics,
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
            diagnostics=payload_diagnostics,
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
            diagnostics=payload_diagnostics,
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

    if _looks_like_ckl_entry_dump(sanitized_text):
        errors.append("Model response exposes raw Canonical Knowledge Library entries.")

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
        diagnostics=payload_diagnostics,
    )


def _looks_like_ckl_entry_dump(text: str) -> bool:
    """Detect the CKL prompt layout without confusing it with normal prose."""

    return bool(CKL_ENTRY_HEADING_RE.search(text) and CKL_FIELD_RE.search(text))


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
    for key in ANSWER_PRIORITY_KEYS:
        if _is_forbidden_key(key):
            continue
        actual_key = _matching_key(payload, key)
        if actual_key is None:
            continue
        value = payload.get(actual_key)
        if key == "choices" and isinstance(value, list):
            for choice in value:
                choice_answer = _extract_answer_from_choice(choice)
                if choice_answer:
                    return choice_answer
            continue
        extracted = _extract_text_value(value)
        if extracted:
            return extracted
    section_answer = _extract_dict_sections(payload)
    if section_answer:
        return section_answer
    return None


def _extract_answer_from_choice(choice: Any) -> str | None:
    if not isinstance(choice, dict):
        return None
    for key in ("message", "delta", "text", "content", "output"):
        actual_key = _matching_key(choice, key)
        if actual_key is not None and not _is_forbidden_key(actual_key):
            extracted = _extract_text_value(choice.get(actual_key))
            if extracted:
                return extracted
    return None


def _extract_dict_sections(payload: dict[str, Any]) -> str | None:
    sections: list[str] = []
    for key in ANSWER_SECTION_KEYS:
        actual_key = _matching_key(payload, key)
        if actual_key is None or _is_forbidden_key(actual_key):
            continue
        value = payload.get(actual_key)
        section_text = _extract_text_value(value)
        if section_text:
            heading = key.replace("_", " ").title()
            sections.append(f"## {heading}\n{section_text}")
    return "\n\n".join(sections) if sections else None


def _has_extra_keys(payload: dict[str, Any]) -> bool:
    allowed = {
        *(_normalized_key(key) for key in ANSWER_PRIORITY_KEYS),
        *(_normalized_key(key) for key in ANSWER_SECTION_KEYS),
    }
    return any(_normalized_key(str(key)) not in allowed for key in payload)


def _extract_text_value(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 6,
) -> str | None:
    if depth > max_depth:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (list, tuple)):
        return _extract_text_blocks(value, depth=depth, max_depth=max_depth)
    if not isinstance(value, dict):
        return None

    block_type = _normalized_block_type(
        _mapping_get(value, "type") or _mapping_get(value, "role")
    )
    if block_type in IGNORED_BLOCK_TYPES:
        return None

    section_text = _extract_dict_sections(value)
    if section_text:
        return section_text

    for key in ANSWER_PRIORITY_KEYS:
        actual_key = _matching_key(value, key)
        if actual_key is None or _is_forbidden_key(actual_key):
            continue
        extracted = _extract_text_value(
            value.get(actual_key),
            depth=depth + 1,
            max_depth=max_depth,
        )
        if extracted:
            return extracted

    if block_type in TEXT_BLOCK_TYPES:
        for key in (
            "text",
            "content",
            "output",
            "answer",
            "response",
            "generated_text",
            "completion",
        ):
            actual_key = _matching_key(value, key)
            if actual_key is not None and not _is_forbidden_key(actual_key):
                extracted = _extract_text_value(
                    value.get(actual_key),
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                if extracted:
                    return extracted

    return None


def _extract_text_blocks(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 6,
) -> str | None:
    if depth > max_depth:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, dict):
        block_type = _normalized_block_type(
            _mapping_get(value, "type") or _mapping_get(value, "role")
        )
        if block_type in IGNORED_BLOCK_TYPES:
            return None
        if block_type in TEXT_BLOCK_TYPES:
            for key in ("text", "content", "output", "answer", "response"):
                actual_key = _matching_key(value, key)
                if actual_key is not None and not _is_forbidden_key(actual_key):
                    extracted = _extract_text_value(
                        value.get(actual_key),
                        depth=depth + 1,
                        max_depth=max_depth,
                    )
                    if extracted:
                        return extracted
        for key in ("message", "delta", "content", "text", "output", "parts", "body"):
            actual_key = _matching_key(value, key)
            if actual_key is not None and not _is_forbidden_key(actual_key):
                extracted = _extract_text_value(
                    value.get(actual_key),
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                if extracted:
                    return extracted
        return None
    if not isinstance(value, (list, tuple)):
        return None

    blocks: list[str] = []
    for item in value:
        if isinstance(item, dict):
            block_type = _normalized_block_type(
                _mapping_get(item, "type") or _mapping_get(item, "role")
            )
            if block_type in IGNORED_BLOCK_TYPES:
                continue
        extracted = _extract_text_value(item, depth=depth + 1, max_depth=max_depth)
        if extracted:
            blocks.append(extracted)
    return "\n".join(blocks) if blocks else None


def _collect_safe_leaf_strings(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = 6,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], str]]:
    if depth > max_depth:
        return []
    if isinstance(value, str):
        text = value.strip()
        if text and _is_recoverable_text(text):
            return [(path, text)]
        return []
    if isinstance(value, (list, tuple)):
        collected: list[tuple[tuple[str, ...], str]] = []
        for index, item in enumerate(value):
            if isinstance(item, dict):
                block_type = _normalized_block_type(
                    _mapping_get(item, "type") or _mapping_get(item, "role")
                )
                if block_type in IGNORED_BLOCK_TYPES:
                    continue
            collected.extend(
                _collect_safe_leaf_strings(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    path=path + (str(index),),
                )
            )
        return collected
    if not isinstance(value, dict):
        return []

    collected: list[tuple[tuple[str, ...], str]] = []
    for key in (*ANSWER_PRIORITY_KEYS, *ANSWER_SECTION_KEYS, *SAFE_RECOVERY_KEYS):
        actual_key = _matching_key(value, key)
        if actual_key is None or _is_forbidden_key(actual_key):
            continue
        child = value.get(actual_key)
        if isinstance(child, str):
            text = child.strip()
            if text and _is_recoverable_text(text):
                collected.append((path + (actual_key,), text))
            continue
        collected.extend(
            _collect_safe_leaf_strings(
                child,
                depth=depth + 1,
                max_depth=max_depth,
                path=path + (actual_key,),
            )
        )
    return collected


def _recover_answer_from_payload(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    candidates = _collect_safe_leaf_strings(payload)
    unique: list[tuple[tuple[str, ...], str]] = []
    seen: set[str] = set()
    for path, text in candidates:
        if text in seen:
            continue
        seen.add(text)
        unique.append((path, text))
    if len(unique) != 1:
        return None, None
    path, text = unique[0]
    return text, (path[-1] if path else "unknown")


def _is_recoverable_text(text: str) -> bool:
    if not text.strip():
        return False
    if PROVIDER_ERROR_RE.search(text):
        return False
    if CKL_PATH_RE.search(text):
        return False
    if RETRIEVAL_SCORE_RE.search(text):
        return False
    if _contains_forbidden_patterns(text):
        return False
    return True


def _normalized_block_type(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalized_key(value: str) -> str:
    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value).strip())
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", camel_spaced).strip("_").lower()
    return normalized


NORMALIZED_FORBIDDEN_RESPONSE_KEYS = {
    _normalized_key(key) for key in FORBIDDEN_RESPONSE_KEYS
}


def _is_forbidden_key(key: str) -> bool:
    return _normalized_key(key) in NORMALIZED_FORBIDDEN_RESPONSE_KEYS


def _matching_key(payload: Mapping[str, Any], wanted: str) -> str | None:
    if wanted in payload:
        return wanted
    normalized_wanted = _normalized_key(wanted)
    for key in payload:
        if _normalized_key(str(key)) == normalized_wanted:
            return str(key)
    return None


def _mapping_get(payload: Mapping[str, Any], wanted: str) -> Any:
    key = _matching_key(payload, wanted)
    return payload.get(key) if key is not None else None


def _payload_diagnostics(
    payload: Any,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "response_contract": diagnostics.get("response_contract") if diagnostics else None,
        "structured_output_requested": diagnostics.get("structured_output_requested") if diagnostics else None,
        "adapter": diagnostics.get("adapter") if diagnostics else None,
        "provider": diagnostics.get("provider") if diagnostics else None,
        "model": diagnostics.get("model") if diagnostics else None,
        "request_id": diagnostics.get("request_id") if diagnostics else None,
        "raw_text_length": diagnostics.get("raw_text_length") if diagnostics else None,
        "top_level_keys": list(payload.keys()) if isinstance(payload, dict) else None,
        "payload_shape": summarize_payload_shape(payload),
    }
    return {key: value for key, value in summary.items() if value is not None}


def summarize_payload_shape(value: Any, *, depth: int = 0, max_depth: int = 6) -> Any:
    if depth > max_depth:
        return {"type": "depth_limit"}
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": {
                str(key): summarize_payload_shape(child, depth=depth + 1, max_depth=max_depth)
                for key, child in value.items()
            },
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "items": [
                summarize_payload_shape(item, depth=depth + 1, max_depth=max_depth)
                for item in value[:3]
            ],
        }
    if isinstance(value, str):
        return {"type": "string", "length": len(value)}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, (int, float)):
        return {"type": "number"}
    return {"type": type(value).__name__}


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
