"""Approximate token estimation helpers for runtime diagnostics."""

from __future__ import annotations


def estimate_tokens(text: str | None) -> int:
    """Return a tokenizer-agnostic rough token count for prompt accounting."""

    if not text:
        return 0
    return max(1, round(len(text) / 4))


def estimate_text_size(text: str | None) -> dict[str, int]:
    """Return compact size diagnostics for text without exposing its content."""

    value = text or ""
    return {
        "characters": len(value),
        "estimated_tokens": estimate_tokens(value),
    }
