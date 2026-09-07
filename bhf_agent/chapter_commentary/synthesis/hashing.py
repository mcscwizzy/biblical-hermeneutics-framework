"""Stable identity for compiled chapter synthesis artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from .models import CompiledChapterSynthesis


def synthesis_hash_payload(synthesis: CompiledChapterSynthesis) -> dict[str, Any]:
    """Return every meaning-bearing synthesis field except its own hash."""

    payload = synthesis.to_dict()
    payload.pop("synthesis_hash", None)
    return payload


def calculate_synthesis_hash(synthesis: CompiledChapterSynthesis) -> str:
    encoded = json.dumps(
        synthesis_hash_payload(synthesis),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def with_synthesis_hash(
    synthesis: CompiledChapterSynthesis,
) -> CompiledChapterSynthesis:
    return replace(synthesis, synthesis_hash=calculate_synthesis_hash(synthesis))
