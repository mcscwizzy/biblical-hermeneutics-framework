"""Request-level observability helpers for the BHF agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ObservabilityConfig:
    enabled: bool = True
    verbose: bool = False
    redact_sensitive: bool = True

    def validate(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("observability.enabled must be true or false")
        if not isinstance(self.verbose, bool):
            raise ValueError("observability.verbose must be true or false")
        if not isinstance(self.redact_sensitive, bool):
            raise ValueError("observability.redact_sensitive must be true or false")


def summarize_usage(usage: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "estimated_cost": None,
        "cached": False,
        "cache_layer": None,
    }
    if not isinstance(usage, Mapping):
        return summary

    summary["cached"] = bool(usage.get("cached", False))
    cache_layer = usage.get("cache_layer")
    if cache_layer is not None:
        summary["cache_layer"] = str(cache_layer)

    input_tokens = _optional_int(usage.get("input_tokens"))
    if input_tokens is None:
        input_tokens = _optional_int(usage.get("prompt_tokens"))

    output_tokens = _optional_int(usage.get("output_tokens"))
    if output_tokens is None:
        output_tokens = _optional_int(usage.get("completion_tokens"))

    total_tokens = _optional_int(usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    estimated_cost = _optional_float(usage.get("estimated_cost"))
    if estimated_cost is None:
        estimated_cost = _optional_float(usage.get("cost"))
    if estimated_cost is None:
        estimated_cost = _optional_float(usage.get("total_cost"))

    summary["input_tokens"] = input_tokens
    summary["output_tokens"] = output_tokens
    summary["total_tokens"] = total_tokens
    summary["estimated_cost"] = estimated_cost
    return summary


def render_log_record(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
