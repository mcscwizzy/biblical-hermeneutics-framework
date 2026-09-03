"""Strict validation for generated chapter commentary."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .models import (
    SUPPORTED_SECTION_KINDS,
    ChapterCommentary,
    CommentaryBlock,
    CommentarySection,
    GeneratedMetadata,
)
from bhf_agent.presentation.models import EvidenceBundle


_DATE_RE = re.compile(
    r"(?<!\w)(?:(?:c\.?|ca\.?|circa|approximately|about)\s+)?"
    r"(?:(?:AD|CE|BC|BCE)\s+[1-9]\d{0,3}|[1-9]\d{0,3}\s*(?:AD|CE|BC|BCE))(?!\w)",
    re.IGNORECASE,
)
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


class CommentaryRejectionCode(str, Enum):
    """Stable codes for rejected commentary blocks/sections."""

    MALFORMED_BLOCK = "MALFORMED_BLOCK"
    MALFORMED_SECTION = "MALFORMED_SECTION"
    INVALID_CONFIDENCE = "INVALID_CONFIDENCE"
    INVALID_INTERPRETATION_LEVEL = "INVALID_INTERPRETATION_LEVEL"
    BLOCK_LENGTH_EXCEEDED = "BLOCK_LENGTH_EXCEEDED"
    UNKNOWN_EVIDENCE_ID = "UNKNOWN_EVIDENCE_ID"
    CONFIDENCE_EXCEEDS_EVIDENCE = "CONFIDENCE_EXCEEDS_EVIDENCE"
    DISPUTED_AS_FACT = "DISPUTED_AS_FACT"
    UNSUPPORTED_DATE = "UNSUPPORTED_DATE"
    UNSUPPORTED_SECTION_KIND = "UNSUPPORTED_SECTION_KIND"
    INVENTED_SIGNIFICANCE = "INVENTED_SIGNIFICANCE"
    UNSUPPORTED_ENTITY = "UNSUPPORTED_ENTITY"
    UNANCHORED_CLAIM = "UNANCHORED_CLAIM"


@dataclass(frozen=True)
class CommentaryBlockValidationResult:
    """Result of validating a single block."""

    valid: bool
    block: CommentaryBlock | None
    errors: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommentarySectionValidationResult:
    """Result of validating a section."""

    valid: bool
    section: CommentarySection | None
    errors: tuple[str, ...] = ()
    block_results: tuple[CommentaryBlockValidationResult, ...] = ()


@dataclass(frozen=True)
class CommentaryValidationResult:
    """Result of validating complete chapter commentary."""

    valid: bool
    commentary: ChapterCommentary | None
    errors: tuple[str, ...]
    section_results: tuple[CommentarySectionValidationResult, ...] = ()
    partial: bool = False

    @property
    def accepted_sections(self) -> tuple[CommentarySection, ...]:
        if self.commentary is None:
            return ()
        return tuple(self.commentary.sections)


def validate_chapter_commentary(
    value: Any,
    bundle: EvidenceBundle,
    *,
    expected_evidence_hash: str | None = None,
    expected_prompt_version: str | None = None,
) -> CommentaryValidationResult:
    """Validate chapter commentary with partial salvage support.

    Returns a result with valid sections even if some are rejected.
    Packet-level validation failures may return no commentary at all.
    """

    errors: list[str] = []
    if not isinstance(value, Mapping):
        return CommentaryValidationResult(
            False, None, ("chapter commentary must be an object",)
        )

    _check_unknown_fields(
        value,
        {"reference", "book", "chapter", "status", "sections", "generated_metadata"},
        "root",
        errors,
    )

    reference = _required_text(value, "reference", "root", errors)
    book = _required_text(value, "book", "root", errors)
    chapter_raw = value.get("chapter")
    if not isinstance(chapter_raw, int) or chapter_raw <= 0:
        errors.append("root.chapter must be a positive integer")
        chapter_num = 0
    else:
        chapter_num = chapter_raw

    if not reference or not book or chapter_num <= 0:
        return CommentaryValidationResult(False, None, tuple(errors))

    status = _required_text(value, "status", "root", errors)
    if status not in {"pending", "generating", "validated", "partial", "needs_review", "failed", "stale"}:
        errors.append(f"root.status is unsupported: {status}")

    metadata_result = _validate_generated_metadata(
        value.get("generated_metadata"),
        bundle,
        expected_evidence_hash=expected_evidence_hash,
        expected_prompt_version=expected_prompt_version,
    )
    errors.extend(metadata_result[0])
    if not metadata_result[1]:
        return CommentaryValidationResult(False, None, tuple(errors))
    generated_metadata = metadata_result[1]

    sections_raw = value.get("sections", [])
    if not isinstance(sections_raw, list):
        errors.append("root.sections must be a list")
        sections_raw = []

    section_results: list[CommentarySectionValidationResult] = []
    sections: list[CommentarySection] = []

    for index, raw_section in enumerate(sections_raw):
        section_result = _validate_section(raw_section, index, bundle)
        section_results.append(section_result)
        if section_result.section is not None:
            sections.append(section_result.section)

    section_errors = tuple(
        error for result in section_results for error in result.errors
    )
    all_errors = tuple(errors) + section_errors

    if sections:
        commentary = ChapterCommentary(
            reference=reference,
            book=book,
            chapter=chapter_num,
            status=status if not section_errors else "partial",
            sections=sections,
            generated_metadata=generated_metadata,
        )
        return CommentaryValidationResult(
            not section_errors,
            commentary,
            all_errors,
            tuple(section_results),
            partial=bool(section_errors),
        )
    else:
        return CommentaryValidationResult(False, None, all_errors, tuple(section_results))


def _validate_generated_metadata(
    raw: Any,
    bundle: EvidenceBundle,
    *,
    expected_evidence_hash: str | None = None,
    expected_prompt_version: str | None = None,
) -> tuple[list[str], GeneratedMetadata | None]:
    """Validate generation metadata."""

    errors: list[str] = []
    if not isinstance(raw, Mapping):
        errors.append("generated_metadata must be an object")
        return errors, None

    fields = {
        "evidence_hash",
        "evidence_bundle_version",
        "commentary_schema_version",
        "commentary_prompt_version",
        "model",
    }
    _check_unknown_fields(raw, fields, "generated_metadata", errors)

    values = {
        field: _required_text(raw, field, "generated_metadata", errors)
        for field in fields
    }

    if values.get("evidence_hash") != bundle.evidence_hash:
        errors.append("generated_metadata.evidence_hash is stale")
    if values.get("evidence_bundle_version") != "1.0":
        errors.append("generated_metadata.evidence_bundle_version is unsupported")
    if values.get("commentary_schema_version") != "1.0":
        errors.append("generated_metadata.commentary_schema_version is unsupported")
    if (
        expected_prompt_version
        and values.get("commentary_prompt_version") != expected_prompt_version
    ):
        errors.append("generated_metadata.commentary_prompt_version does not match")
    if any(not v for v in values.values()):
        return errors, None

    if errors:
        return errors, None

    return (
        errors,
        GeneratedMetadata(**values),
    )


def _validate_section(
    raw: Any,
    index: int,
    bundle: EvidenceBundle,
) -> CommentarySectionValidationResult:
    """Validate a single section with block salvage."""

    label = f"section[{index}]"
    if not isinstance(raw, Mapping):
        return CommentarySectionValidationResult(
            False,
            None,
            (f"{label} must be an object",),
        )

    errors: list[str] = []
    _check_unknown_fields(raw, {"kind", "title", "blocks"}, label, errors)

    kind = _required_text(raw, "kind", label, errors)
    title = _required_text(raw, "title", label, errors)

    if kind not in SUPPORTED_SECTION_KINDS:
        errors.append(f"{label}.kind is unsupported: {kind}")

    if not title:
        errors.append(f"{label}.title is required")

    blocks_raw = raw.get("blocks", [])
    if not isinstance(blocks_raw, list):
        errors.append(f"{label}.blocks must be a list")
        blocks_raw = []

    block_results: list[CommentaryBlockValidationResult] = []
    blocks: list[CommentaryBlock] = []

    for block_index, raw_block in enumerate(blocks_raw):
        block_result = _validate_block(raw_block, block_index, label, bundle)
        block_results.append(block_result)
        if block_result.block is not None:
            blocks.append(block_result.block)

    block_errors = tuple(error for result in block_results for error in result.errors)
    all_errors = tuple(errors) + block_errors

    if kind and title and blocks:
        section = CommentarySection(kind=kind, title=title, blocks=blocks)
        return CommentarySectionValidationResult(
            not block_errors,
            section,
            all_errors,
            tuple(block_results),
        )
    else:
        return CommentarySectionValidationResult(False, None, all_errors, tuple(block_results))


def _validate_block(
    raw: Any,
    index: int,
    section_label: str,
    bundle: EvidenceBundle,
) -> CommentaryBlockValidationResult:
    """Validate a single block."""

    label = f"{section_label}.block[{index}]"
    if not isinstance(raw, Mapping):
        return CommentaryBlockValidationResult(
            False,
            None,
            (f"{label} must be an object",),
            (CommentaryRejectionCode.MALFORMED_BLOCK.value,),
        )

    errors: list[str] = []
    reason_codes: list[str] = []

    _check_unknown_fields(
        raw,
        {"id", "text", "verse_refs", "evidence_ids", "confidence", "interpretation_level"},
        label,
        errors,
    )

    block_id = _required_text(raw, "id", label, errors)
    text = _required_text(raw, "text", label, errors)
    confidence = _required_text(raw, "confidence", label, errors) or "medium"
    interpretation = _required_text(raw, "interpretation_level", label, errors) or "inference"

    verse_refs = _string_list(raw.get("verse_refs", []), f"{label}.verse_refs", errors)
    evidence_ids = _string_list(raw.get("evidence_ids", []), f"{label}.evidence_ids", errors)

    if len(text) > 2000:
        errors.append(f"{label}.text exceeds 2000 characters")
        reason_codes.append(CommentaryRejectionCode.BLOCK_LENGTH_EXCEEDED.value)

    if confidence not in {"low", "medium", "high"}:
        errors.append(f"{label}.confidence is invalid")
        reason_codes.append(CommentaryRejectionCode.INVALID_CONFIDENCE.value)

    if interpretation not in {"fact", "inference", "disputed"}:
        errors.append(f"{label}.interpretation_level is invalid")
        reason_codes.append(CommentaryRejectionCode.INVALID_INTERPRETATION_LEVEL.value)

    if not evidence_ids:
        errors.append(f"{label} must cite at least one evidence item")
        reason_codes.append(CommentaryRejectionCode.UNANCHORED_CLAIM.value)

    unknown_evidence = [
        item_id for item_id in evidence_ids if item_id not in bundle.evidence_by_id
    ]
    if unknown_evidence:
        errors.append(f"{label} cites unsupported evidence IDs: {', '.join(unknown_evidence)}")
        reason_codes.append(CommentaryRejectionCode.UNKNOWN_EVIDENCE_ID.value)

    supplied = [
        bundle.evidence_by_id[item_id]
        for item_id in evidence_ids
        if item_id in bundle.evidence_by_id
    ]
    if supplied and confidence in _CONFIDENCE_RANK:
        maximum_supported = min(
            _CONFIDENCE_RANK.get(item.confidence, 0) for item in supplied
        )
        if _CONFIDENCE_RANK[confidence] > maximum_supported:
            errors.append(f"{label}.confidence exceeds its cited evidence")
            reason_codes.append(CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value)

    if interpretation == "fact" and any(
        item.relevance_metadata.get("disputed") for item in supplied
    ):
        errors.append(f"{label} turns disputed evidence into fact")
        reason_codes.append(CommentaryRejectionCode.DISPUTED_AS_FACT.value)

    if not block_id or not text:
        return CommentaryBlockValidationResult(
            False,
            None,
            tuple(errors),
            tuple(reason_codes),
        )

    if errors:
        return CommentaryBlockValidationResult(
            False,
            None,
            tuple(errors),
            tuple(reason_codes),
        )

    block = CommentaryBlock(
        id=block_id,
        text=text,
        verse_refs=verse_refs,
        evidence_ids=evidence_ids,
        confidence=confidence,
        interpretation_level=interpretation,
    )
    return CommentaryBlockValidationResult(True, block, ())


def _required_text(value: Mapping[str, Any], field: str, label: str, errors: list[str]) -> str:
    text = str(value.get(field) or "").strip()
    if not text:
        errors.append(f"{label}.{field} is required")
    return text


def _string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return []
    result = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        else:
            errors.append(f"{label} contains non-string item")
    return result


def _check_unknown_fields(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = set(value.keys()) - expected
    if unknown:
        errors.append(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
