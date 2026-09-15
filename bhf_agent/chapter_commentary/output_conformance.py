"""Strict, deterministic renderer-output conformance for Commentary v1.2.

This boundary is intentionally narrower than commentary validation.  It may
repair only mechanically unambiguous JSON shapes and reference serialization;
it never creates prose, evidence, synthesis, or reader ideas.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Mapping

from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import (
    format_scripture_reference,
    parse_scripture_reference,
)

from .models import VERSE_OPTIONAL_SECTION_KINDS


COMMENTARY_OUTPUT_CONFORMANCE_VERSION = "commentary-output-conformance-v1"
COMMENTARY_OUTPUT_CONFORMANCE_IMPLEMENTATION = (
    "bhf_agent.chapter_commentary.output_conformance"
)
MAX_STRUCTURAL_ATTEMPTS = 2


STRUCTURAL_RETRY_CODES = frozenset(
    {
        "MALFORMED_RESPONSE_JSON",
        "NON_OBJECT_JSON",
        "MALFORMED_REQUIRED_FIELD",
        "EMPTY_REQUIRED_SECTIONS",
        "EMPTY_REQUIRED_BLOCKS",
        "MALFORMED_SECTION",
        "MALFORMED_BLOCK",
        "MALFORMED_VERSE_REFERENCE",
        "AMBIGUOUS_VERSE_REFERENCE",
        "MALFORMED_PROVENANCE_REFERENCE",
        "MISSING_PROVENANCE_REFERENCES",
        "DUPLICATE_PROVENANCE_REFERENCE",
        "UNKNOWN_PROVENANCE_PATH",
        "OUT_OF_CHAPTER_PROVENANCE_PATH",
    }
)


@dataclass(frozen=True)
class ConformanceResult:
    """Result of strict parsing and deterministic output conformance."""

    valid: bool
    payload: dict[str, Any] | None
    parse_status: str
    errors: tuple[str, ...]
    events: tuple[dict[str, Any], ...]

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(error.split(":", 1)[0] for error in self.errors))

    @property
    def retry_eligible(self) -> bool:
        return any(code in STRUCTURAL_RETRY_CODES for code in self.codes)


def parse_renderer_json(raw: bytes) -> tuple[dict[str, Any] | None, str, tuple[str, ...]]:
    """Strictly parse raw renderer bytes without repairing or stripping prose."""

    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, "MALFORMED_JSON", (f"MALFORMED_RESPONSE_JSON: {exc}",)
    if not isinstance(value, dict):
        return None, "NON_OBJECT_JSON", ("NON_OBJECT_JSON: renderer response must be an object",)
    return value, "JSON_OBJECT", ()


def conform_renderer_output(
    payload: Mapping[str, Any] | None,
    *,
    expected_reference: str | None = None,
    expected_book: str | None = None,
    expected_chapter: int | None = None,
    parse_status: str = "JSON_OBJECT",
    parse_errors: tuple[str, ...] = (),
) -> ConformanceResult:
    """Apply only deterministic machine-output normalization.

    A renderer response with no sections or no usable blocks is rejected.  A
    chapter-only reference in a section that requires verse-level anchoring is
    also rejected as ambiguous: conformance has no authority to guess a verse
    range.  The existing canonical validator remains authoritative for the
    accepted canonical payload.
    """

    if payload is None:
        return ConformanceResult(False, None, parse_status, parse_errors, ())

    normalized = copy.deepcopy(dict(payload))
    errors: list[str] = list(parse_errors)
    events: list[dict[str, Any]] = []

    required_top_level = ("reference", "book", "chapter", "status", "sections")
    for field in required_top_level:
        if field not in normalized:
            errors.append(f"MALFORMED_REQUIRED_FIELD: root.{field} is required")

    if expected_reference is not None and normalized.get("reference") != expected_reference:
        errors.append(
            f"CHAPTER_IDENTITY_MISMATCH: expected root reference {expected_reference!r}, "
            f"received {normalized.get('reference')!r}"
        )
    if expected_book is not None and normalized.get("book") != expected_book:
        errors.append(
            f"CHAPTER_IDENTITY_MISMATCH: expected root book {expected_book!r}, "
            f"received {normalized.get('book')!r}"
        )
    if expected_chapter is not None and normalized.get("chapter") != expected_chapter:
        errors.append(
            f"CHAPTER_IDENTITY_MISMATCH: expected root chapter {expected_chapter}, "
            f"received {normalized.get('chapter')!r}"
        )

    sections = normalized.get("sections")
    if not isinstance(sections, list):
        errors.append("MALFORMED_REQUIRED_FIELD: root.sections must be a list")
        sections = []
    elif not sections:
        errors.append("EMPTY_REQUIRED_SECTIONS: root.sections must be non-empty")

    for section_index, section in enumerate(sections):
        section_label = f"section[{section_index}]"
        if not isinstance(section, Mapping):
            errors.append(f"MALFORMED_SECTION: {section_label} must be an object")
            continue
        for field in ("kind", "title", "blocks"):
            if field not in section:
                errors.append(f"MALFORMED_REQUIRED_FIELD: {section_label}.{field} is required")
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            errors.append(f"MALFORMED_SECTION: {section_label}.blocks must be a list")
            continue
        if not blocks:
            errors.append(f"EMPTY_REQUIRED_BLOCKS: {section_label}.blocks must be non-empty")
        for block_index, block in enumerate(blocks):
            block_label = f"{section_label}.block[{block_index}]"
            if not isinstance(block, Mapping):
                errors.append(f"MALFORMED_BLOCK: {block_label} must be an object")
                continue
            for field in ("id", "text", "verse_refs", "provenance_refs"):
                if field not in block:
                    errors.append(f"MALFORMED_REQUIRED_FIELD: {block_label}.{field} is required")
            if not isinstance(block.get("id"), str) or not block.get("id", "").strip():
                errors.append(f"MALFORMED_BLOCK: {block_label}.id must be non-empty text")
            if not isinstance(block.get("text"), str) or not block.get("text", "").strip():
                errors.append(f"MALFORMED_BLOCK: {block_label}.text must be non-empty text")
            if "provenance_refs" in block:
                _check_nonempty_string_list(
                    block.get("provenance_refs"),
                    f"{block_label}.provenance_refs",
                    errors,
                    code="MALFORMED_PROVENANCE_REFERENCE",
                )
            if "verse_refs" in block:
                _normalize_verse_refs(
                    block,
                    block_label,
                    section.get("kind"),
                    errors,
                    events,
                )

    unique_errors = tuple(dict.fromkeys(errors))
    return ConformanceResult(
        not unique_errors,
        normalized if not unique_errors else normalized,
        parse_status,
        unique_errors,
        tuple(events),
    )


def _check_nonempty_string_list(
    value: Any,
    label: str,
    errors: list[str],
    *,
    code: str,
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{code}: {label} must be a non-empty array")
        return
    if any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{code}: {label} must contain non-empty strings")


def _normalize_verse_refs(
    block: Mapping[str, Any],
    label: str,
    section_kind: Any,
    errors: list[str],
    events: list[dict[str, Any]],
) -> None:
    value = block.get("verse_refs")
    if isinstance(value, str):
        if not value.strip():
            errors.append(f"MALFORMED_VERSE_REFERENCE: {label}.verse_refs contains an empty string")
            return
        block["verse_refs"] = [value]  # type: ignore[index]
        events.append(
            {
                "code": "VERSE_REFS_STRING_TO_ARRAY",
                "path": f"{label}.verse_refs",
                "before": value,
                "after": [value],
                "reason": "single unambiguous reference wrapper shape",
            }
        )
        value = block["verse_refs"]
    if not isinstance(value, list):
        errors.append(f"MALFORMED_VERSE_REFERENCE: {label}.verse_refs must be an array")
        return
    for index, raw_ref in enumerate(value):
        ref_label = f"{label}.verse_refs[{index}]"
        if not isinstance(raw_ref, str) or not raw_ref.strip():
            errors.append(f"MALFORMED_VERSE_REFERENCE: {ref_label} must be non-empty text")
            continue
        span = parse_scripture_reference(raw_ref, book_alias_lookup=_BOOK_ALIASES)
        if span is None:
            errors.append(f"MALFORMED_VERSE_REFERENCE: {ref_label} is not parseable: {raw_ref!r}")
            continue
        canonical = format_scripture_reference(span)
        if canonical != raw_ref:
            block["verse_refs"][index] = canonical  # type: ignore[index]
            events.append(
                {
                    "code": "CANONICAL_VERSE_REFERENCE_SERIALIZATION",
                    "path": ref_label,
                    "before": raw_ref,
                    "after": canonical,
                    "reason": "canonical parser/serializer produced one unambiguous reference",
                }
            )
        if (
            span.start_verse is None
            and section_kind not in VERSE_OPTIONAL_SECTION_KINDS
        ):
            errors.append(
                f"AMBIGUOUS_VERSE_REFERENCE: {ref_label} is chapter-only in a section requiring a verse-level reference: {raw_ref!r}"
            )


def structural_retry_allowed(*, attempt_ordinal: int, codes: Any) -> bool:
    """Return whether exactly one more mechanical retry is permitted."""

    if attempt_ordinal >= MAX_STRUCTURAL_ATTEMPTS:
        return False
    return bool(set(codes) & STRUCTURAL_RETRY_CODES)

