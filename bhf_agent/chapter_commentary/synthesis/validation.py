"""Deterministic integrity checks for compiled synthesis artifacts."""

from __future__ import annotations

from bhf_agent.presentation.models import EvidenceBundle
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import (
    ScriptureReferenceSpan,
    parse_scripture_reference,
    parse_scripture_references,
)
from collections import Counter

from .hashing import calculate_synthesis_hash
from .models import (
    SYNTHESIS_PASSAGE_SCOPES,
    SYNTHESIS_UNIT_KINDS,
    CompiledChapterSynthesis,
)


class SynthesisValidationError(ValueError):
    """Raised when synthesis cannot be proven to descend from its bundle."""


def validate_synthesis(
    synthesis: CompiledChapterSynthesis,
    bundle: EvidenceBundle,
) -> tuple[str, ...]:
    errors: list[str] = []
    if synthesis.evidence_hash != bundle.evidence_hash:
        errors.append("synthesis evidence_hash does not match its EvidenceBundle")
    if synthesis.evidence_bundle_version != bundle.version:
        errors.append("synthesis evidence_bundle_version does not match")
    if synthesis.synthesis_hash != calculate_synthesis_hash(synthesis):
        errors.append("synthesis_hash does not match deterministic content")
    if len(synthesis.units_by_id) != len(synthesis.synthesis_units):
        errors.append("synthesis unit IDs are not unique")

    evidence_by_id = bundle.evidence_by_id
    entity_ids = set(bundle.entities_by_id)
    unit_ids = set(synthesis.units_by_id)
    for unit in synthesis.synthesis_units:
        if unit.kind not in SYNTHESIS_UNIT_KINDS:
            errors.append(f"{unit.id} has unsupported kind {unit.kind}")
        if unit.passage_scope not in SYNTHESIS_PASSAGE_SCOPES:
            errors.append(f"{unit.id} has unsupported passage scope {unit.passage_scope}")
        unknown_evidence = sorted(set(unit.evidence_ids) - set(evidence_by_id))
        if unknown_evidence:
            errors.append(f"{unit.id} has unknown evidence IDs: {unknown_evidence}")
        unknown_entities = sorted(set(unit.entity_ids) - entity_ids)
        if unknown_entities:
            errors.append(f"{unit.id} leaks unknown entity IDs: {unknown_entities}")
        supported_entities = {
            entity_id
            for evidence_id in unit.evidence_ids
            if evidence_id in evidence_by_id
            for entity_id in evidence_by_id[evidence_id].related_entity_ids
        }
        unsupported_entities = sorted(set(unit.entity_ids) - supported_entities)
        if unsupported_entities:
            errors.append(
                f"{unit.id} has entities outside its evidence ancestry: {unsupported_entities}"
            )
        unknown_units = sorted(set(unit.related_unit_ids) - unit_ids)
        if unknown_units:
            errors.append(f"{unit.id} has unknown related unit IDs: {unknown_units}")
        supported_facts = {
            evidence_by_id[evidence_id].claim
            for evidence_id in unit.evidence_ids
            if evidence_id in evidence_by_id
        }
        if set(unit.facts) - supported_facts:
            errors.append(f"{unit.id} contains facts absent from its evidence ancestry")
        supported_anchors = {
            anchor
            for evidence_id in unit.evidence_ids
            if evidence_id in evidence_by_id
            for anchor in evidence_by_id[evidence_id].passage_anchors
        }
        if set(unit.verse_refs) - supported_anchors and not all(
            _reference_derived_from_source(reference, unit.source_anchors)
            for reference in unit.verse_refs
        ):
            errors.append(f"{unit.id} has passage anchors outside its evidence ancestry")
        if set(unit.source_anchors) - supported_anchors:
            errors.append(f"{unit.id} has source anchors outside its evidence ancestry")
        if unit.passage_scope == "CURRENT_CHAPTER":
            for reference in unit.verse_refs:
                if not _is_current_chapter_reference(
                    reference, synthesis.book, synthesis.chapter
                ):
                    errors.append(
                        f"{unit.id} exposes an out-of-chapter reference in CURRENT_CHAPTER scope"
                    )
        elif unit.kind != "surrounding_passages":
            errors.append(
                f"{unit.id} has SURROUNDING_PASSAGE scope without surrounding_passages kind"
            )
        supported_confidence = min(
            (_confidence_rank(evidence_by_id[evidence_id].confidence) for evidence_id in unit.evidence_ids if evidence_id in evidence_by_id),
            default=0,
        )
        if _confidence_rank(unit.confidence) > supported_confidence:
            errors.append(f"{unit.id} confidence exceeds its evidence ancestry")
        if unit.interpretation_level == "fact" and any(
            _is_disputed(evidence_by_id[evidence_id])
            for evidence_id in unit.evidence_ids
            if evidence_id in evidence_by_id
        ):
            errors.append(f"{unit.id} turns disputed evidence into fact")
        if unit.kind == "why_it_matters" and not unit.metadata.get("safe_for_significance"):
            errors.append(f"{unit.id} is not marked safe for significance")
        if unit.kind == "why_it_matters":
            explicit = bool(unit.metadata.get("explicit_significance"))
            if len(set(unit.evidence_ids)) < 2 and not explicit:
                errors.append(f"{unit.id} lacks multi-evidence or explicitly authored significance support")

    used = sorted({evidence_id for unit in synthesis.synthesis_units for evidence_id in unit.evidence_ids})
    all_evidence = sorted(evidence_by_id)
    expected_categories = dict(sorted(Counter(item.category for item in bundle.evidence_items).items()))
    expected_entities = {
        bucket: len(bundle.entities.get(bucket, []))
        for bucket in ("people", "places", "groups", "events", "artifacts")
    }
    if synthesis.coverage.evidence_item_count != len(all_evidence):
        errors.append("synthesis coverage evidence_item_count is incorrect")
    if synthesis.coverage.used_evidence_ids != used:
        errors.append("synthesis coverage used_evidence_ids is incorrect")
    if synthesis.coverage.unused_evidence_ids != sorted(set(all_evidence) - set(used)):
        errors.append("synthesis coverage unused_evidence_ids is incorrect")
    if synthesis.coverage.evidence_categories != expected_categories:
        errors.append("synthesis coverage evidence_categories is incorrect")
    if synthesis.coverage.entity_counts != expected_entities:
        errors.append("synthesis coverage entity_counts is incorrect")
    return tuple(errors)


def _confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(value, 0)


def _is_disputed(item) -> bool:
    metadata = item.relevance_metadata or {}
    if metadata.get("disputed") is True:
        return True
    dispute = str(metadata.get("dispute_status") or "").casefold()
    certainty = str(metadata.get("certainty") or "").casefold()
    disputed_values = {"disputed", "speculative", "insufficient_evidence", "contested", "uncertain"}
    undisputed_values = {"", "not_disputed", "undisputed", "supported", "established", "none", "unknown"}
    return dispute not in undisputed_values or certainty in disputed_values


def require_valid_synthesis(
    synthesis: CompiledChapterSynthesis,
    bundle: EvidenceBundle,
) -> None:
    errors = validate_synthesis(synthesis, bundle)
    if errors:
        raise SynthesisValidationError("; ".join(errors))


def _is_current_chapter_reference(reference: str, book: str, chapter: int) -> bool:
    """Keep this integrity check strict without accepting compound syntax."""

    import re

    match = re.match(
        r"^(?P<book>.+?)\s+(?P<chapter>\d+)(?::(?P<start>\d+)(?:-(?:(?P<end_chapter>\d+):)?(?P<end>\d+))?)?$",
        " ".join(reference.split()),
    )
    if not match:
        return False
    try:
        from bhf_agent import bible

        canonical = bible.resolve_chapter(match.group("book"), int(match.group("chapter")))["book"]
    except (ValueError, TypeError, KeyError):
        return False
    return (
        canonical == book
        and int(match.group("chapter")) == chapter
        and int(match.group("end_chapter") or match.group("chapter")) == chapter
    )


def _reference_derived_from_source(reference: str, source_anchors: list[str]) -> bool:
    candidate = parse_scripture_reference(reference, book_alias_lookup=_BOOK_ALIASES)
    if candidate is None:
        return False
    candidate_start, candidate_end = _span_bounds(candidate)
    for source in source_anchors:
        for source_span in parse_scripture_references(
            source, book_alias_lookup=_BOOK_ALIASES
        ):
            if source_span.book != candidate.book:
                continue
            source_start, source_end = _span_bounds(source_span)
            if source_start <= candidate_start and candidate_end <= source_end:
                return True
    return False


def _span_bounds(span: ScriptureReferenceSpan) -> tuple[tuple[int, int], tuple[int, int]]:
    start_chapter = span.start_chapter or 1
    start_verse = span.start_verse or 1
    end_chapter = span.end_chapter or start_chapter
    end_verse = span.end_verse or (999 if span.start_verse is None else span.start_verse)
    return (start_chapter, start_verse), (end_chapter, end_verse)
