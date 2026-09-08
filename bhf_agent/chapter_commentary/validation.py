"""Deterministic validation and partial salvage for generated chapter commentary.

Validation guarantees structural integrity, current chapter identity, canonical
verse anchoring, evidence IDs/confidence, dispute labeling, and supported dates.
Significance is admitted only through traceable synthesis relationship units.
Free-text unsupported-entity detection remains deferred because reliable entity
recognition is outside this structural validator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from bhf_agent import bible

from .models import (
    COMMENTARY_SCHEMA_VERSION,
    DATA_GAP_FALLBACK_TEXT,
    SUPPORTED_SECTION_KINDS,
    VERSE_OPTIONAL_SECTION_KINDS,
    ChapterCommentary,
    CommentaryBlock,
    CommentarySection,
    GeneratedMetadata,
)
from .availability import EvidenceAvailability, classify_evidence_availability
from bhf_agent.presentation.models import EvidenceBundle
from .synthesis.models import CompiledChapterSynthesis


_DATE_RE = re.compile(
    r"(?<!\w)(?:(?:c\.?|ca\.?|circa|approximately|about)\s+)?"
    r"(?:(?:AD|CE|BC|BCE)\s+[1-9]\d{0,3}|[1-9]\d{0,3}\s*(?:AD|CE|BC|BCE))(?!\w)",
    re.IGNORECASE,
)
_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
_IMPLEMENTATION_LANGUAGE = (
    "supplied synthesis",
    "evidence bundle",
    "evidence item",
    "synthesis unit",
    "metadata",
    "provided evidence",
    "input context",
)
_VERSE_REF_RE = re.compile(
    r"^(?P<book>.+?)\s+(?P<chapter>\d+):(?P<start>\d+)"
    r"(?:-(?:(?P<end_chapter>\d+):)?(?P<end>\d+))?$"
)
_DEFERRED_REJECTION_CODES = frozenset(
    {
        "UNSUPPORTED_ENTITY",
    }
)
DEFERRED_REJECTION_CODES = _DEFERRED_REJECTION_CODES


class CommentaryRejectionCode(str, Enum):
    """Stable rejection codes for reader-commentary validation."""

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
    MALFORMED_VERSE_REFERENCE = "MALFORMED_VERSE_REFERENCE"
    OUT_OF_CHAPTER_VERSE_REFERENCE = "OUT_OF_CHAPTER_VERSE_REFERENCE"
    CHAPTER_IDENTITY_MISMATCH = "CHAPTER_IDENTITY_MISMATCH"
    UNKNOWN_SYNTHESIS_ID = "UNKNOWN_SYNTHESIS_ID"
    SYNTHESIS_ANCESTRY_MISMATCH = "SYNTHESIS_ANCESTRY_MISMATCH"
    SYNTHESIS_HASH_MISMATCH = "SYNTHESIS_HASH_MISMATCH"
    OUT_OF_CHAPTER_SYNTHESIS_REFERENCE = "OUT_OF_CHAPTER_SYNTHESIS_REFERENCE"
    DATA_GAP_FALLBACK_REQUIRED = "DATA_GAP_FALLBACK_REQUIRED"
    DATA_GAP_RENDERER_PROSE = "DATA_GAP_RENDERER_PROSE"
    IMPLEMENTATION_LANGUAGE = "IMPLEMENTATION_LANGUAGE"


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
    reason_codes: tuple[str, ...] = ()


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
    expected_reference: str | None = None,
    expected_book: str | None = None,
    expected_chapter: int | None = None,
    synthesis: CompiledChapterSynthesis | None = None,
    expected_synthesis_hash: str | None = None,
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
        {
            "reference", "book", "chapter", "status", "sections",
            "generated_metadata", "evidence_availability", "data_gap_fallback",
        },
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

    expected_book, expected_chapter, expected_reference = _expected_identity(
        bundle,
        expected_reference=expected_reference,
        expected_book=expected_book,
        expected_chapter=expected_chapter,
    )
    identity_errors = _validate_identity(
        reference,
        book,
        chapter_num,
        expected_reference=expected_reference,
        expected_book=expected_book,
        expected_chapter=expected_chapter,
    )
    errors.extend(identity_errors)
    if identity_errors:
        return CommentaryValidationResult(False, None, tuple(errors))

    status = _required_text(value, "status", "root", errors)
    if status not in {"pending", "generating", "validated", "partial", "needs_review", "failed", "stale"}:
        errors.append(f"root.status is unsupported: {status}")

    metadata_result = _validate_generated_metadata(
        value.get("generated_metadata"),
        bundle,
        expected_evidence_hash=expected_evidence_hash,
        expected_prompt_version=expected_prompt_version,
        synthesis=synthesis,
        expected_synthesis_hash=expected_synthesis_hash,
    )
    errors.extend(metadata_result[0])
    if not metadata_result[1]:
        return CommentaryValidationResult(False, None, tuple(errors))
    generated_metadata = metadata_result[1]

    expected_availability = classify_evidence_availability(bundle).value
    availability = value.get("evidence_availability") or expected_availability
    if value.get("evidence_availability") not in (None, expected_availability):
        errors.append("evidence_availability is not application-derived")
        return CommentaryValidationResult(False, None, tuple(errors))

    sections_raw = value.get("sections", [])
    if not isinstance(sections_raw, list):
        errors.append("root.sections must be a list")
        sections_raw = []

    is_true_data_gap = (
        availability == EvidenceAvailability.DATA_GAP.value
        and not bundle.evidence_items
        and (synthesis is None or not synthesis.synthesis_units)
    )
    if is_true_data_gap:
        if value.get("data_gap_fallback") is not True:
            error = (
                f"{CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value}: "
                "true DATA_GAP chapters require the application-owned fallback"
            )
            return CommentaryValidationResult(False, None, tuple(errors) + (error,))
        fallback_errors = _validate_data_gap_fallback(sections_raw)
        if fallback_errors:
            return CommentaryValidationResult(False, None, tuple(errors) + tuple(fallback_errors))
        fallback_block = CommentaryBlock(
            id="data_gap_notice",
            text=DATA_GAP_FALLBACK_TEXT,
            verse_refs=[],
            evidence_ids=[],
            synthesis_ids=[],
            confidence="high",
            interpretation_level="fact",
        )
        fallback_section = CommentarySection(
            kind="chapter_overview",
            title="Context availability",
            blocks=[fallback_block],
        )
        commentary = ChapterCommentary(
            reference=reference,
            book=book,
            chapter=chapter_num,
            status=status,
            sections=[fallback_section],
            generated_metadata=generated_metadata,
            evidence_availability=availability,
            data_gap_fallback=True,
        )
        return CommentaryValidationResult(True, commentary, tuple(errors), ())
    if availability == EvidenceAvailability.DATA_GAP.value and value.get("data_gap_fallback"):
        error = (
            f"{CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value}: "
            "the fallback is valid only when evidence and synthesis are both empty"
        )
        return CommentaryValidationResult(False, None, tuple(errors) + (error,))

    section_results: list[CommentarySectionValidationResult] = []
    sections: list[CommentarySection] = []

    for index, raw_section in enumerate(sections_raw):
        section_result = _validate_section(
            raw_section,
            index,
            bundle,
            expected_book=expected_book,
            expected_chapter=expected_chapter,
            evidence_availability=availability,
            synthesis=synthesis,
        )
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
            status=status if not all_errors else "partial",
            sections=sections,
            generated_metadata=generated_metadata,
            evidence_availability=availability,
        )
        return CommentaryValidationResult(
            not all_errors,
            commentary,
            all_errors,
            tuple(section_results),
            partial=bool(all_errors),
        )
    else:
        return CommentaryValidationResult(False, None, all_errors, tuple(section_results))


def _validate_generated_metadata(
    raw: Any,
    bundle: EvidenceBundle,
    *,
    expected_evidence_hash: str | None = None,
    expected_prompt_version: str | None = None,
    synthesis: CompiledChapterSynthesis | None = None,
    expected_synthesis_hash: str | None = None,
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
        "generated_timestamp",
        "synthesis_hash",
        "synthesis_schema_version",
        "synthesis_compiler_version",
        "renderer_label",
        "imported_timestamp",
        "candidate_id",
    }
    _check_unknown_fields(raw, fields, "generated_metadata", errors)

    optional_fields = {
        "generated_timestamp",
        "synthesis_hash",
        "synthesis_schema_version",
        "synthesis_compiler_version",
        "renderer_label",
        "imported_timestamp",
        "candidate_id",
    }
    required_fields = fields - optional_fields
    values = {
        field: _required_text(raw, field, "generated_metadata", errors)
        for field in required_fields
    }
    timestamp = raw.get("generated_timestamp")
    if timestamp is not None and not isinstance(timestamp, str):
        errors.append("generated_metadata.generated_timestamp must be text or null")
    values["generated_timestamp"] = timestamp if isinstance(timestamp, str) else None
    for field in (
        "synthesis_hash",
        "synthesis_schema_version",
        "synthesis_compiler_version",
        "renderer_label",
        "imported_timestamp",
        "candidate_id",
    ):
        raw_value = raw.get(field)
        if raw_value is not None and not isinstance(raw_value, str):
            errors.append(f"generated_metadata.{field} must be text or null")
        values[field] = raw_value if isinstance(raw_value, str) else None

    expected_hash = expected_evidence_hash or bundle.evidence_hash
    if values.get("evidence_hash") != expected_hash:
        errors.append("generated_metadata.evidence_hash is stale")
    if values.get("evidence_bundle_version") != bundle.version:
        errors.append("generated_metadata.evidence_bundle_version is unsupported")
    if values.get("commentary_schema_version") != COMMENTARY_SCHEMA_VERSION:
        errors.append("generated_metadata.commentary_schema_version is unsupported")
    if (
        expected_prompt_version
        and values.get("commentary_prompt_version") != expected_prompt_version
    ):
        errors.append("generated_metadata.commentary_prompt_version does not match")
    if synthesis is not None:
        wanted_hash = expected_synthesis_hash or synthesis.synthesis_hash
        if values.get("synthesis_hash") != wanted_hash:
            errors.append(
                f"{CommentaryRejectionCode.SYNTHESIS_HASH_MISMATCH.value}: "
                "generated_metadata.synthesis_hash is stale"
            )
        if values.get("synthesis_schema_version") != synthesis.synthesis_schema_version:
            errors.append("generated_metadata.synthesis_schema_version is unsupported")
        if values.get("synthesis_compiler_version") != synthesis.synthesis_compiler_version:
            errors.append("generated_metadata.synthesis_compiler_version is unsupported")
    if any(not values[field] for field in required_fields):
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
    *,
    expected_book: str,
    expected_chapter: int,
    evidence_availability: str,
    synthesis: CompiledChapterSynthesis | None,
) -> CommentarySectionValidationResult:
    """Validate a single section with block salvage."""

    label = f"section[{index}]"
    if not isinstance(raw, Mapping):
        return CommentarySectionValidationResult(
            False,
            None,
            (f"{CommentaryRejectionCode.MALFORMED_SECTION.value}: {label} must be an object",),
            (),
            (CommentaryRejectionCode.MALFORMED_SECTION.value,),
        )

    errors: list[str] = []
    expected_fields = {"kind", "title", "blocks"}
    _check_unknown_fields(raw, expected_fields, label, errors)

    kind = _required_text(raw, "kind", label, errors)
    title = _required_text(raw, "title", label, errors)

    reason_codes: list[str] = []
    if set(raw) - expected_fields or errors:
        reason_codes.append(CommentaryRejectionCode.MALFORMED_SECTION.value)

    if kind not in SUPPORTED_SECTION_KINDS:
        errors.append(
            f"{CommentaryRejectionCode.UNSUPPORTED_SECTION_KIND.value}: "
            f"{label}.kind is unsupported: {kind}"
        )
        reason_codes.append(CommentaryRejectionCode.UNSUPPORTED_SECTION_KIND.value)

    if evidence_availability == EvidenceAvailability.DATA_GAP.value and kind not in {"chapter_overview", "things_easy_to_miss"}:
        errors.append(f"{CommentaryRejectionCode.UNANCHORED_CLAIM.value}: DATA_GAP permits canonical observation sections only")
        reason_codes.append(CommentaryRejectionCode.UNANCHORED_CLAIM.value)

    if not title:
        errors.append(f"{CommentaryRejectionCode.MALFORMED_SECTION.value}: {label}.title is required")
        reason_codes.append(CommentaryRejectionCode.MALFORMED_SECTION.value)

    blocks_raw = raw.get("blocks", [])
    if not isinstance(blocks_raw, list):
        errors.append(f"{CommentaryRejectionCode.MALFORMED_SECTION.value}: {label}.blocks must be a list")
        reason_codes.append(CommentaryRejectionCode.MALFORMED_SECTION.value)
        blocks_raw = []

    # A bad section envelope cannot be salvaged from valid-looking blocks.
    if errors or kind not in SUPPORTED_SECTION_KINDS or not title:
        return CommentarySectionValidationResult(
            False, None, tuple(errors), (), tuple(dict.fromkeys(reason_codes))
        )

    block_results: list[CommentaryBlockValidationResult] = []
    blocks: list[CommentaryBlock] = []

    for block_index, raw_block in enumerate(blocks_raw):
        block_result = _validate_block(
            raw_block,
            block_index,
            label,
            bundle,
            expected_book=expected_book,
            expected_chapter=expected_chapter,
            section_kind=kind,
            evidence_availability=evidence_availability,
            synthesis=synthesis,
        )
        block_results.append(block_result)
        if block_result.block is not None:
            blocks.append(block_result.block)

    block_errors = tuple(error for result in block_results for error in result.errors)
    all_errors = tuple(errors) + block_errors

    if kind and title and blocks:
        section = CommentarySection(kind=kind, title=title, blocks=blocks)
        return CommentarySectionValidationResult(
            not all_errors,
            section,
            all_errors,
            tuple(block_results),
            (),
        )
    return CommentarySectionValidationResult(
        False,
        None,
        all_errors,
        tuple(block_results),
        (CommentaryRejectionCode.MALFORMED_SECTION.value,),
    )


def _validate_block(
    raw: Any,
    index: int,
    section_label: str,
    bundle: EvidenceBundle,
    *,
    expected_book: str,
    expected_chapter: int,
    section_kind: str,
    evidence_availability: str,
    synthesis: CompiledChapterSynthesis | None,
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

    expected_fields = {"id", "text", "verse_refs", "evidence_ids", "synthesis_ids", "confidence", "interpretation_level"}
    _check_unknown_fields(
        raw,
        expected_fields,
        label,
        errors,
    )

    block_id = _required_text(raw, "id", label, errors)
    text = _required_text(raw, "text", label, errors)
    confidence = _required_text(raw, "confidence", label, errors) or "medium"
    interpretation = _required_text(raw, "interpretation_level", label, errors) or "inference"

    verse_refs = _string_list(raw.get("verse_refs", []), f"{label}.verse_refs", errors)
    evidence_ids = _string_list(raw.get("evidence_ids", []), f"{label}.evidence_ids", errors)
    synthesis_ids = _string_list(raw.get("synthesis_ids", []), f"{label}.synthesis_ids", errors)

    structural_malformed = bool(set(raw) - expected_fields)
    structural_malformed = structural_malformed or any(
        field in raw and not isinstance(raw[field], str)
        for field in ("id", "text", "confidence", "interpretation_level")
    )
    structural_malformed = structural_malformed or any(
        field in raw
        and (
            not isinstance(raw[field], list)
            or any(not isinstance(item, str) for item in raw[field])
        )
        for field in ("verse_refs", "evidence_ids", "synthesis_ids")
    )
    if structural_malformed or not block_id or not text:
        reason_codes.append(CommentaryRejectionCode.MALFORMED_BLOCK.value)
    if not isinstance(raw.get("verse_refs", []), list):
        reason_codes.append(CommentaryRejectionCode.MALFORMED_BLOCK.value)

    if len(text) > 2000:
        errors.append(
            f"{CommentaryRejectionCode.BLOCK_LENGTH_EXCEEDED.value}: "
            f"{label}.text exceeds 2000 characters"
        )
        reason_codes.append(CommentaryRejectionCode.BLOCK_LENGTH_EXCEEDED.value)

    implementation_terms = [
        phrase for phrase in _IMPLEMENTATION_LANGUAGE if phrase in text.casefold()
    ]
    if implementation_terms:
        errors.append(
            f"{CommentaryRejectionCode.IMPLEMENTATION_LANGUAGE.value}: "
            f"{label} exposes internal renderer vocabulary: {', '.join(implementation_terms)}"
        )
        reason_codes.append(CommentaryRejectionCode.IMPLEMENTATION_LANGUAGE.value)

    if confidence not in {"low", "medium", "high"}:
        errors.append(f"{CommentaryRejectionCode.INVALID_CONFIDENCE.value}: {label}.confidence is invalid")
        reason_codes.append(CommentaryRejectionCode.INVALID_CONFIDENCE.value)

    if interpretation not in {"fact", "inference", "disputed"}:
        errors.append(
            f"{CommentaryRejectionCode.INVALID_INTERPRETATION_LEVEL.value}: "
            f"{label}.interpretation_level is invalid"
        )
        reason_codes.append(CommentaryRejectionCode.INVALID_INTERPRETATION_LEVEL.value)

    if not evidence_ids and evidence_availability != EvidenceAvailability.DATA_GAP.value:
        errors.append(
            f"{CommentaryRejectionCode.UNANCHORED_CLAIM.value}: "
            f"{label} must cite at least one evidence item"
        )
        reason_codes.append(CommentaryRejectionCode.UNANCHORED_CLAIM.value)

    unknown_evidence = [
        item_id for item_id in evidence_ids if item_id not in bundle.evidence_by_id
    ]
    if unknown_evidence:
        errors.append(
            f"{CommentaryRejectionCode.UNKNOWN_EVIDENCE_ID.value}: "
            f"{label} cites unsupported evidence IDs: {', '.join(unknown_evidence)}"
        )
        reason_codes.append(CommentaryRejectionCode.UNKNOWN_EVIDENCE_ID.value)

    if evidence_availability == EvidenceAvailability.DATA_GAP.value and evidence_ids:
        errors.append(
            f"{CommentaryRejectionCode.UNKNOWN_EVIDENCE_ID.value}: DATA_GAP blocks cannot cite evidence"
        )
        reason_codes.append(CommentaryRejectionCode.UNKNOWN_EVIDENCE_ID.value)

    supplied = [
        bundle.evidence_by_id[item_id]
        for item_id in evidence_ids
        if item_id in bundle.evidence_by_id
    ]
    supplied_units = []
    if synthesis is not None:
        if not synthesis_ids and evidence_availability != EvidenceAvailability.DATA_GAP.value:
            errors.append(
                f"{CommentaryRejectionCode.UNKNOWN_SYNTHESIS_ID.value}: "
                f"{label} must cite at least one synthesis unit"
            )
            reason_codes.append(CommentaryRejectionCode.UNKNOWN_SYNTHESIS_ID.value)
        unknown_synthesis = [
            unit_id for unit_id in synthesis_ids if unit_id not in synthesis.units_by_id
        ]
        if unknown_synthesis:
            errors.append(
                f"{CommentaryRejectionCode.UNKNOWN_SYNTHESIS_ID.value}: "
                f"{label} cites unsupported synthesis IDs: {', '.join(unknown_synthesis)}"
            )
            reason_codes.append(CommentaryRejectionCode.UNKNOWN_SYNTHESIS_ID.value)
        supplied_units = [
            synthesis.units_by_id[unit_id]
            for unit_id in synthesis_ids
            if unit_id in synthesis.units_by_id
        ]
        ancestry = {
            evidence_id for unit in supplied_units for evidence_id in unit.evidence_ids
        }
        if set(evidence_ids) - ancestry:
            errors.append(
                f"{CommentaryRejectionCode.SYNTHESIS_ANCESTRY_MISMATCH.value}: "
                f"{label} cites evidence outside its synthesis ancestry"
            )
            reason_codes.append(CommentaryRejectionCode.SYNTHESIS_ANCESTRY_MISMATCH.value)
        if section_kind != "surrounding_passages" and any(
            unit.passage_scope == "SURROUNDING_PASSAGE" for unit in supplied_units
        ):
            errors.append(
                f"{CommentaryRejectionCode.OUT_OF_CHAPTER_SYNTHESIS_REFERENCE.value}: "
                f"{label} uses surrounding-passage synthesis in an ordinary section"
            )
            reason_codes.append(
                CommentaryRejectionCode.OUT_OF_CHAPTER_SYNTHESIS_REFERENCE.value
            )
        scopes = {unit.passage_scope for unit in supplied_units}
        if {"CURRENT_CHAPTER", "SURROUNDING_PASSAGE"}.issubset(scopes):
            errors.append(
                f"{CommentaryRejectionCode.OUT_OF_CHAPTER_SYNTHESIS_REFERENCE.value}: "
                f"{label} mixes current-chapter and surrounding-passage synthesis in one block"
            )
            reason_codes.append(
                CommentaryRejectionCode.OUT_OF_CHAPTER_SYNTHESIS_REFERENCE.value
            )
        if section_kind == "why_it_matters" and not any(
            unit.kind == "why_it_matters" and unit.metadata.get("safe_for_significance")
            for unit in supplied_units
        ):
            errors.append(
                f"{CommentaryRejectionCode.INVENTED_SIGNIFICANCE.value}: "
                f"{label} has no supported why_it_matters relationship unit"
            )
            reason_codes.append(CommentaryRejectionCode.INVENTED_SIGNIFICANCE.value)
    if supplied and confidence in _CONFIDENCE_RANK:
        maximum_supported = min(
            _CONFIDENCE_RANK.get(item.confidence, 0) for item in supplied
        )
        if _CONFIDENCE_RANK[confidence] > maximum_supported:
            errors.append(
                f"{CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value}: "
                f"{label}.confidence exceeds its cited evidence"
            )
            reason_codes.append(CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value)
    if supplied_units and confidence in _CONFIDENCE_RANK:
        maximum_synthesis = min(
            _CONFIDENCE_RANK.get(unit.confidence, 0) for unit in supplied_units
        )
        if _CONFIDENCE_RANK[confidence] > maximum_synthesis:
            errors.append(
                f"{CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value}: "
                f"{label}.confidence exceeds its cited synthesis"
            )
            reason_codes.append(CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value)

    if interpretation == "fact" and any(
        _evidence_is_disputed(item) for item in supplied
    ):
        errors.append(
            f"{CommentaryRejectionCode.DISPUTED_AS_FACT.value}: "
            f"{label} turns disputed evidence into fact"
        )
        reason_codes.append(CommentaryRejectionCode.DISPUTED_AS_FACT.value)
    if interpretation == "fact" and any(
        unit.interpretation_level == "disputed" for unit in supplied_units
    ):
        errors.append(
            f"{CommentaryRejectionCode.DISPUTED_AS_FACT.value}: "
            f"{label} turns disputed synthesis into fact"
        )
        reason_codes.append(CommentaryRejectionCode.DISPUTED_AS_FACT.value)

    verse_errors = _validate_verse_refs(
        verse_refs,
        label,
        expected_book=expected_book,
        expected_chapter=expected_chapter,
        optional=section_kind in VERSE_OPTIONAL_SECTION_KINDS,
        allow_surrounding=section_kind == "surrounding_passages",
    )
    errors.extend(verse_errors[0])
    reason_codes.extend(verse_errors[1])

    for date_text in _DATE_RE.findall(text):
        if not _date_is_supported(date_text, supplied):
            errors.append(
                f"{CommentaryRejectionCode.UNSUPPORTED_DATE.value}: "
                f"{label} contains unsupported date {date_text!r}"
            )
            reason_codes.append(CommentaryRejectionCode.UNSUPPORTED_DATE.value)

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
        synthesis_ids=synthesis_ids,
        confidence=confidence,
        interpretation_level=interpretation,
    )
    return CommentaryBlockValidationResult(True, block, ())


def _required_text(value: Mapping[str, Any], field: str, label: str, errors: list[str]) -> str:
    raw = value.get(field)
    if raw is not None and not isinstance(raw, str):
        errors.append(f"{label}.{field} must be text")
        return ""
    text = str(raw or "").strip()
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


def _validate_data_gap_fallback(sections: list[Any]) -> list[str]:
    """Validate the exact application-owned DATA_GAP notice shape."""

    if len(sections) != 1 or not isinstance(sections[0], Mapping):
        return [
            f"{CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value}: "
            "DATA_GAP fallback must contain exactly one application-owned section"
        ]
    section = sections[0]
    if set(section) != {"kind", "title", "blocks"}:
        return [
            f"{CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value}: "
            "DATA_GAP fallback section shape is not application-owned"
        ]
    blocks = section.get("blocks")
    if (
        section.get("kind") != "chapter_overview"
        or section.get("title") != "Context availability"
        or not isinstance(blocks, list)
        or len(blocks) != 1
        or not isinstance(blocks[0], Mapping)
    ):
        return [
            f"{CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value}: "
            "DATA_GAP fallback section is not canonical"
        ]
    block = blocks[0]
    expected = {
        "id", "text", "verse_refs", "evidence_ids", "synthesis_ids",
        "confidence", "interpretation_level",
    }
    if set(block) != expected or any(
        (
            block.get("id") != "data_gap_notice",
            block.get("text") != DATA_GAP_FALLBACK_TEXT,
            block.get("verse_refs") != [],
            block.get("evidence_ids") != [],
            block.get("synthesis_ids") != [],
            block.get("confidence") != "high",
            block.get("interpretation_level") != "fact",
        )
    ):
        return [
            f"{CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value}: "
            "DATA_GAP fallback block is not canonical"
        ]
    return []


def _check_unknown_fields(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = set(value.keys()) - expected
    if unknown:
        errors.append(f"{label} has unknown fields: {', '.join(sorted(unknown))}")


def _expected_identity(
    bundle: EvidenceBundle,
    *,
    expected_reference: str | None,
    expected_book: str | None,
    expected_chapter: int | None,
) -> tuple[str, int, str]:
    """Derive the expected chapter when callers only provide an evidence bundle."""
    reference = " ".join(str(expected_reference or bundle.passage_ref).split())
    match = re.match(r"^(?P<book>.+?)\s+(?P<chapter>\d+)(?::\d+(?:-\d+)?)?$", reference)
    derived_book = expected_book or (match.group("book") if match else "")
    derived_chapter = expected_chapter or (int(match.group("chapter")) if match else 0)
    if not expected_reference and derived_book and derived_chapter:
        try:
            reference = bible.verse_range_reference(derived_book, derived_chapter)
        except bible.BibleError:
            pass
    try:
        canonical_book = bible.resolve_chapter(derived_book, derived_chapter)["book"]
    except (bible.BibleError, KeyError, TypeError):
        canonical_book = derived_book
    if canonical_book and derived_chapter:
        try:
            reference = bible.verse_range_reference(canonical_book, derived_chapter)
        except bible.BibleError:
            pass
    return canonical_book, derived_chapter, reference


def _validate_identity(
    reference: str,
    book: str,
    chapter: int,
    *,
    expected_reference: str,
    expected_book: str,
    expected_chapter: int,
) -> list[str]:
    errors: list[str] = []
    try:
        actual_book = bible.resolve_chapter(book, chapter)["book"]
    except (bible.BibleError, KeyError, TypeError):
        actual_book = ""
    if actual_book != expected_book or chapter != expected_chapter:
        errors.append(
            f"{CommentaryRejectionCode.CHAPTER_IDENTITY_MISMATCH.value}: "
            f"expected {expected_book} {expected_chapter}, "
            f"received {book} {chapter}"
        )
    if " ".join(reference.split()).casefold() != " ".join(expected_reference.split()).casefold():
        errors.append(
            f"{CommentaryRejectionCode.CHAPTER_IDENTITY_MISMATCH.value}: "
            f"expected root reference {expected_reference}, "
            f"received {reference}"
        )
    return errors


def _validate_verse_refs(
    verse_refs: list[str],
    label: str,
    *,
    expected_book: str,
    expected_chapter: int,
    optional: bool,
    allow_surrounding: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    codes: list[str] = []
    if not verse_refs and not optional:
        errors.append(
            f"{CommentaryRejectionCode.UNANCHORED_CLAIM.value}: "
            f"{label} requires at least one verse reference"
        )
        codes.append(CommentaryRejectionCode.UNANCHORED_CLAIM.value)
        return errors, codes

    for verse_ref in verse_refs:
        match = _VERSE_REF_RE.match(" ".join(verse_ref.split()))
        if not match:
            errors.append(
                f"{CommentaryRejectionCode.MALFORMED_VERSE_REFERENCE.value}: "
                f"{label} has malformed verse reference {verse_ref!r}"
            )
            codes.append(CommentaryRejectionCode.MALFORMED_VERSE_REFERENCE.value)
            continue
        ref_book = match.group("book")
        ref_chapter = int(match.group("chapter"))
        end_chapter = int(match.group("end_chapter") or ref_chapter)
        start_verse = int(match.group("start"))
        end_verse = int(match.group("end") or start_verse)
        try:
            canonical_ref_book = bible.resolve_chapter(ref_book, ref_chapter)["book"]
            chapter_data = bible.resolve_chapter(ref_book, ref_chapter)
            max_verse = max(int(item["verse"]) for item in chapter_data.get("verses", []))
        except (bible.BibleError, KeyError, TypeError, ValueError):
            canonical_ref_book = ""
            max_verse = 0
        outside_current = (
            canonical_ref_book != expected_book
            or ref_chapter != expected_chapter
            or end_chapter != expected_chapter
        )
        if allow_surrounding:
            invalid = (
                not canonical_ref_book
                or start_verse <= 0
                or end_verse < start_verse
                or end_verse > max_verse
            )
        else:
            invalid = (
                outside_current
                or start_verse <= 0
                or end_verse < start_verse
                or end_verse > max_verse
            )
        if invalid:
            errors.append(
                f"{CommentaryRejectionCode.OUT_OF_CHAPTER_VERSE_REFERENCE.value}: "
                f"{label} verse reference is outside {expected_book} {expected_chapter}: {verse_ref!r}"
            )
            codes.append(CommentaryRejectionCode.OUT_OF_CHAPTER_VERSE_REFERENCE.value)
    return errors, codes


def _evidence_is_disputed(item: Any) -> bool:
    metadata = item.relevance_metadata or {}
    if metadata.get("disputed") is True:
        return True
    status = str(metadata.get("dispute_status") or "").casefold()
    return status not in {"", "not_disputed", "undisputed", "supported", "established"}


def _date_is_supported(date_text: str, supplied: list[Any]) -> bool:
    normalized = date_text.casefold().replace("bce", "bc").replace("ce", "ad")
    numbers = re.findall(r"\d+", normalized)
    era = "bc" if "bc" in normalized else "ad" if "ad" in normalized else ""
    if not numbers or not era:
        return False
    for item in supplied:
        evidence_text = " ".join(
            [item.claim, repr(item.relevance_metadata), " ".join(item.passage_anchors)]
        ).casefold().replace("bce", "bc").replace("ce", "ad")
        if era in evidence_text and all(number in evidence_text for number in numbers):
            return True
    return False
