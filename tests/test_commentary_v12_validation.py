"""Synthesis-aware Commentary v1.2 validation tests."""

from dataclasses import replace

from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.builder import CommentaryBuilder
from bhf_agent.chapter_commentary.models import ChapterCommentary, GeneratedMetadata
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.chapter_commentary.synthesis import validate_synthesis
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT,
    build_user_prompt,
)
from bhf_agent.chapter_commentary.validation import CommentaryRejectionCode, validate_chapter_commentary
from bhf_agent.presentation.models import EvidenceBundle, EvidenceItem
from bhf_agent.config import AgentConfig


def _bundle(*, disputed=False, confidence="high"):
    metadata = {"dispute_status": "disputed"} if disputed else {}
    items = [
        EvidenceItem(
            id="e1", claim="Gath was a Philistine city.", category="geography",
            source_ids=["s"], related_entity_ids=[], passage_anchors=["1 Samuel 21:10"],
            confidence=confidence, relevance_metadata=metadata,
        ),
        EvidenceItem(
            id="e2", claim="David fled to Gath.", category="geography",
            source_ids=["s"], related_entity_ids=[], passage_anchors=["1 Samuel 21:10"],
            confidence=confidence, relevance_metadata=metadata,
        ),
    ]
    return EvidenceBundle(
        passage_ref="1 Samuel 21", entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=items, geography={}, provenance={}, version="1.1", evidence_hash="e" * 64,
    )


def _raw(bundle, synthesis, *, synthesis_ids=None, evidence_ids=None, kind="chapter_overview", confidence="high", interpretation="fact"):
    synthesis_ids = synthesis_ids if synthesis_ids is not None else [synthesis.synthesis_units[0].id]
    evidence_ids = evidence_ids if evidence_ids is not None else list(synthesis.units_by_id[synthesis_ids[0]].evidence_ids)
    return {
        "reference": "1 Samuel 21", "book": "1 Samuel", "chapter": 21, "status": "pending",
        "sections": [{"kind": kind, "title": "Context", "blocks": [{
            "id": "b1", "text": "Supported explanation.", "verse_refs": ["1 Samuel 21:10"],
            "evidence_ids": evidence_ids, "synthesis_ids": synthesis_ids,
            "confidence": confidence, "interpretation_level": interpretation,
        }]}],
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash,
            "evidence_bundle_version": bundle.version,
            "synthesis_hash": synthesis.synthesis_hash,
            "synthesis_schema_version": synthesis.synthesis_schema_version,
            "synthesis_compiler_version": synthesis.synthesis_compiler_version,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "model": "test",
        },
    }


def test_valid_synthesis_ids_and_evidence_ancestry_are_accepted():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    assert validate_chapter_commentary(_raw(bundle, synthesis), bundle, synthesis=synthesis).valid


def test_multiple_valid_synthesis_ids_can_share_one_traceable_block():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    synthesis_ids = [unit.id for unit in synthesis.synthesis_units]
    evidence_ids = sorted({evidence_id for unit in synthesis.synthesis_units for evidence_id in unit.evidence_ids})
    assert len(synthesis_ids) >= 2
    result = validate_chapter_commentary(
        _raw(bundle, synthesis, synthesis_ids=synthesis_ids, evidence_ids=evidence_ids),
        bundle,
        synthesis=synthesis,
    )
    assert result.valid


def test_unsupported_synthesis_id_is_rejected():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    result = validate_chapter_commentary(
        _raw(bundle, synthesis, synthesis_ids=["missing"], evidence_ids=["e1"]),
        bundle, synthesis=synthesis,
    )
    assert not result.valid
    assert CommentaryRejectionCode.UNKNOWN_SYNTHESIS_ID.value in result.section_results[0].block_results[0].reason_codes


def test_evidence_outside_cited_synthesis_ancestry_is_rejected():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    first = next(unit for unit in synthesis.synthesis_units if unit.evidence_ids == ["e1"])
    result = validate_chapter_commentary(
        _raw(bundle, synthesis, synthesis_ids=[first.id], evidence_ids=["e2"]),
        bundle, synthesis=synthesis,
    )
    assert not result.valid
    assert CommentaryRejectionCode.SYNTHESIS_ANCESTRY_MISMATCH.value in result.section_results[0].block_results[0].reason_codes


def test_synthesis_hash_mismatch_rejects_stale_commentary():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    raw["generated_metadata"]["synthesis_hash"] = "0" * 64
    result = validate_chapter_commentary(raw, bundle, synthesis=synthesis)
    assert not result.valid
    assert any(CommentaryRejectionCode.SYNTHESIS_HASH_MISMATCH.value in error for error in result.errors)


def test_disputed_synthesis_cannot_become_fact_and_confidence_cannot_increase():
    bundle = _bundle(disputed=True, confidence="low")
    synthesis = compile_chapter_synthesis(bundle)
    result = validate_chapter_commentary(
        _raw(bundle, synthesis, confidence="high", interpretation="fact"),
        bundle, synthesis=synthesis,
    )
    codes = result.section_results[0].block_results[0].reason_codes
    assert CommentaryRejectionCode.DISPUTED_AS_FACT.value in codes
    assert CommentaryRejectionCode.CONFIDENCE_EXCEEDS_EVIDENCE.value in codes


def test_why_it_matters_requires_safe_relationship_unit():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    ordinary = synthesis.synthesis_units[0]
    result = validate_chapter_commentary(
        _raw(bundle, synthesis, kind="why_it_matters", synthesis_ids=[ordinary.id]),
        bundle, synthesis=synthesis,
    )
    assert not result.valid
    assert CommentaryRejectionCode.INVENTED_SIGNIFICANCE.value in result.section_results[0].block_results[0].reason_codes


def test_adaptive_minimal_output_does_not_require_padding():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    assert len(raw["sections"]) == 1
    assert validate_chapter_commentary(raw, bundle, synthesis=synthesis).valid


def test_single_normalized_verse_reference_is_accepted():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    raw["sections"][0]["blocks"][0]["verse_refs"] = ["1 Samuel 21:10"]
    assert validate_chapter_commentary(raw, bundle, synthesis=synthesis).valid


def test_normalized_contiguous_range_is_accepted():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    raw["sections"][0]["blocks"][0]["verse_refs"] = ["1 Samuel 21:10-11"]
    assert validate_chapter_commentary(raw, bundle, synthesis=synthesis).valid


def test_non_contiguous_ranges_are_separate_array_entries():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    raw["sections"][0]["blocks"][0]["verse_refs"] = [
        "1 Samuel 21:10",
        "1 Samuel 21:12-13",
    ]
    assert validate_chapter_commentary(raw, bundle, synthesis=synthesis).valid


def test_compound_comma_reference_is_rejected():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    raw["sections"][0]["blocks"][0]["verse_refs"] = ["1 Samuel 21:10, 12-13"]
    result = validate_chapter_commentary(raw, bundle, synthesis=synthesis)
    assert CommentaryRejectionCode.MALFORMED_VERSE_REFERENCE.value in result.section_results[0].block_results[0].reason_codes


def test_cross_chapter_ordinary_reference_is_rejected():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    raw = _raw(bundle, synthesis)
    raw["sections"][0]["blocks"][0]["verse_refs"] = ["1 Samuel 21:10-22:1"]
    result = validate_chapter_commentary(raw, bundle, synthesis=synthesis)
    assert CommentaryRejectionCode.OUT_OF_CHAPTER_VERSE_REFERENCE.value in result.section_results[0].block_results[0].reason_codes


def test_data_gap_fallback_is_exact_and_cannot_contain_model_prose():
    from bhf_agent.chapter_commentary.models import data_gap_fallback_payload

    bundle = EvidenceBundle(
        passage_ref="Numbers 3",
        entities={"people": [], "places": [], "groups": [], "events": [], "artifacts": []},
        evidence_items=[],
        geography={},
        provenance={},
        version="1.1",
        evidence_hash="e" * 64,
    )
    raw = data_gap_fallback_payload("Numbers 3", "Numbers", 3)
    raw["generated_metadata"] = {
        "evidence_hash": bundle.evidence_hash,
        "evidence_bundle_version": bundle.version,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "model": "test",
    }
    assert validate_chapter_commentary(
        raw, bundle, expected_reference="Numbers 3",
        expected_book="Numbers", expected_chapter=3,
    ).valid
    raw["sections"][0]["blocks"][0]["text"] = "Renderer-added unsupported prose."
    result = validate_chapter_commentary(
        raw, bundle, expected_reference="Numbers 3",
        expected_book="Numbers", expected_chapter=3,
    )
    assert not result.valid
    assert CommentaryRejectionCode.DATA_GAP_FALLBACK_REQUIRED.value in " ".join(result.errors)


def test_synthesis_projection_separates_genesis_2_boundary():
    from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
    from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION

    bundle = get_chapter_evidence_bundle(
        "Genesis", 1, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    assert bundle is not None
    synthesis = compile_chapter_synthesis(bundle, book="Genesis", chapter=1)
    assert validate_synthesis(synthesis, bundle) == ()
    surrounding = [
        unit for unit in synthesis.synthesis_units
        if unit.passage_scope == "SURROUNDING_PASSAGE"
    ]
    assert any(
        unit.kind == "surrounding_passages"
        and "Genesis 2:1-3" in unit.verse_refs
        and "Genesis 1:1-2:3" in unit.source_anchors
        for unit in surrounding
    )
    assert compile_chapter_synthesis(bundle, book="Genesis", chapter=1).synthesis_hash == synthesis.synthesis_hash


def test_renderer_prompt_has_strict_verse_and_data_gap_contract():
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    prompt = build_user_prompt(
        "1 Samuel 21", "1 Samuel", 21, "canonical text", synthesis, bundle,
        "AVAILABLE",
    )
    assert "Never cross a chapter boundary" in prompt
    assert "one canonical contiguous reference" in prompt
    assert "Never expose implementation vocabulary in reader prose" in CHAPTER_COMMENTARY_SYSTEM_PROMPT
    assert "application-owned availability notice" in build_user_prompt(
        "Numbers 3", "Numbers", 3, "", synthesis, bundle, "DATA_GAP"
    )


def test_builder_marks_synthesis_hash_or_compiler_drift_stale(tmp_path):
    bundle = _bundle()
    synthesis = compile_chapter_synthesis(bundle)
    builder = CommentaryBuilder(tmp_path, config=AgentConfig())
    commentary = ChapterCommentary(
        reference="1 Samuel 21", book="1 Samuel", chapter=21, status="validated",
        generated_metadata=GeneratedMetadata(
            evidence_hash=bundle.evidence_hash,
            evidence_bundle_version=bundle.version,
            commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
            commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
            model="test",
            synthesis_hash="0" * 64,
            synthesis_schema_version=synthesis.synthesis_schema_version,
            synthesis_compiler_version=synthesis.synthesis_compiler_version,
        ),
    )
    assert builder._effective_status(commentary, "1 Samuel", 21, bundle) == "stale"

    compiler_drift = replace(
        commentary,
        generated_metadata=replace(
            commentary.generated_metadata,
            synthesis_hash=synthesis.synthesis_hash,
            synthesis_compiler_version="older",
        ),
    )
    assert builder._effective_status(compiler_drift, "1 Samuel", 21, bundle) == "stale"
