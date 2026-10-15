"""Regression coverage for renderer selection sufficiency v1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bhf_agent import bible
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    audit_provenance_binding_v2,
    response_ancestry_audit_v2,
)
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_POLICY_VERSION_V3,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.selection_sufficiency import (
    LEGACY_SELECTION_EXCEPTION_DECISION,
    LEGACY_SELECTION_EXCEPTION_VERSION,
    RENDERER_SELECTION_COLLAPSE,
    SELECTION_SUFFICIENCY_VERSION,
    assess_selection_sufficiency,
    validate_legacy_selection_exception,
    validate_selection_assessment,
)
from bhf_agent.chapter_commentary.synthesis.models import (
    CompiledChapterSynthesis,
    SynthesisCoverage,
    SynthesisGap,
    SynthesisUnit,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem
from framework.commentary.production.manifests import batch_manifest, build_manifest
from framework.commentary.production.models import (
    GATE_QUALITY_FAIL,
    InputIdentity,
    PreparedChapter,
    sha256_bytes,
    sha256_json,
    write_json,
)
from framework.commentary.production.recovery import reconcile_chapter
from framework.commentary.production.runner import ProductionRunner


FIXTURE_ROOT = Path(__file__).parent / "fixtures/commentary_selection_sufficiency/genesis1"
HISTORICAL_SHA256 = "8090b554273c56561c0fbe3a3c7b96a67fb79901475ff1e39081b22f3c40134e"
CORRECTIVE_SHA256 = "02bede74dce10a2b9e88a9cc6871325c2eac91aa861a76b301e05352524c8710"
FOUR_DISTINCT_FACTS = (
    "Amber altar establishes flame as covenant boundary.",
    "Cedar ark stores tablets beside the sanctuary.",
    "Dune gate opens toward the eastern court.",
    "Ember lamp marks watchfulness during the night.",
)
DENSE_DISTINCT_FACTS = (
    "Amber altar establishes flame as covenant boundary.",
    "Cedar ark stores tablets beside the sanctuary.",
    "Dune gate opens toward the eastern court.",
    "Ember lamp marks watchfulness during the night.",
    "Fjord bridge joins two settlements across water.",
    "Grove well supplies travelers with drinking water.",
    "Harbor walls protect ships from winter storms.",
    "Island shrine receives offerings during harvest.",
    "Jade seal identifies the governor's official order.",
    "Kiln bricks strengthen the southern city wall.",
    "Lagoon reeds provide material for woven baskets.",
    "Meadow pasture supports the herds in spring.",
    "North tower signals approaching danger to the town.",
    "Olive press extracts oil for lamps and cooking.",
    "Prairie road connects the village with market towns.",
    "Quartz stone marks the boundary of the estate.",
    "Ridge path crosses the mountain above the river.",
    "Summit altar commemorates the covenant meal.",
    "Thicket shelter hides the scouts from view.",
    "Umber dye colors the cloth used for the curtain.",
)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _genesis1_context():
    raw_bundle = _read(FIXTURE_ROOT / "source/evidence-bundle.json")
    raw_synthesis = _read(FIXTURE_ROOT / "source/compiled-synthesis.json")
    bundle = EvidenceBundle(
        passage_ref=raw_bundle["passage_ref"],
        entities={
            key: [EntityRef(**item) for item in values]
            for key, values in raw_bundle["entities"].items()
        },
        evidence_items=[EvidenceItem(**item) for item in raw_bundle["evidence_items"]],
        geography=raw_bundle["geography"],
        provenance=raw_bundle["provenance"],
        version=raw_bundle["version"],
        evidence_hash=raw_bundle["evidence_hash"],
    )
    synthesis = CompiledChapterSynthesis(
        reference=raw_synthesis["reference"],
        book=raw_synthesis["book"],
        chapter=raw_synthesis["chapter"],
        evidence_hash=raw_synthesis["evidence_hash"],
        evidence_bundle_version=raw_synthesis["evidence_bundle_version"],
        synthesis_schema_version=raw_synthesis["synthesis_schema_version"],
        synthesis_compiler_version=raw_synthesis["synthesis_compiler_version"],
        synthesis_hash=raw_synthesis["synthesis_hash"],
        evidence_availability=raw_synthesis["evidence_availability"],
        synthesis_units=[SynthesisUnit(**item) for item in raw_synthesis["synthesis_units"]],
        evidence_gaps=[SynthesisGap(**item) for item in raw_synthesis["evidence_gaps"]],
        coverage=SynthesisCoverage(**raw_synthesis["coverage"]),
    )
    packet = _read(FIXTURE_ROOT / "source/source-packet.json")
    source_identity = {
        "reference": packet["reference"],
        "packet_id": packet["packet_id"],
        "packet_hash": packet["packet_hash"],
        "evidence_hash": packet["evidence_hash"],
        "synthesis_hash": packet["synthesis_hash"],
    }
    chapter = bible.resolve_chapter("Genesis", 1)
    passage_text = bible.passage_text(chapter["verses"])
    return bundle, synthesis, source_identity, passage_text


def _compatible_schema_payload(raw: dict) -> dict:
    allowed = {
        "reference", "book", "chapter", "status", "sections",
        "generated_metadata", "evidence_availability", "data_gap_fallback",
    }
    return {key: value for key, value in raw.items() if key in allowed}


def _validate_genesis1(raw: dict, bundle, synthesis):
    payload = _compatible_schema_payload(raw)
    metadata = payload["generated_metadata"]
    return validate_chapter_commentary(
        payload,
        bundle,
        expected_evidence_hash=bundle.evidence_hash,
        expected_prompt_version=metadata["commentary_prompt_version"],
        expected_reference="Genesis 1",
        expected_book="Genesis",
        expected_chapter=1,
        synthesis=synthesis,
        expected_synthesis_hash=synthesis.synthesis_hash,
    )


def _assessment(context, commentary):
    bundle, synthesis, source_identity, passage_text = context
    metadata = commentary.generated_metadata
    return assess_selection_sufficiency(
        synthesis,
        bundle,
        commentary,
        passage_text=passage_text,
        source_identity=source_identity,
        renderer_prompt_version=metadata.commentary_prompt_version,
        renderer_schema_version=metadata.commentary_schema_version,
    )


def _evidence(
    ident: str,
    *,
    category: str = "history",
    parent: str | None = None,
    parent_title: str | None = None,
    semantic_relationship: str = "DIRECT_CONTEXT",
    inherited: bool = False,
    scope: str = "passage",
    disputed: str = "not_disputed",
) -> EvidenceItem:
    return EvidenceItem(
        id=ident,
        claim=f"Evidence supports {ident}.",
        category=category,
        source_ids=[f"source-{ident}"],
        related_entity_ids=[],
        passage_anchors=["Genesis 1:1"],
        confidence="high",
        relevance_metadata={
            "applicability_scope": scope,
            "source_kind": "ckl_legacy_field" if inherited else "ckl_evidence_item",
            "anchor_source": "parent" if inherited else "child",
            "anchor_specificity": "verse",
            "inherited_from_parent": inherited,
            "parent_object_id": parent or ident,
            "parent_title": parent_title or ident,
            "semantic_relationship": semantic_relationship,
            "passage_relationship": "direct",
            "dispute_status": disputed,
        },
    )


def _unit(
    ident: str,
    fact: str,
    evidence_id: str,
    *,
    kind: str = "chapter_overview",
    scope: str = "CURRENT_CHAPTER",
    disputed: bool = False,
    parent: str | None = None,
    explicit_significance: bool = False,
) -> SynthesisUnit:
    return SynthesisUnit(
        id=ident,
        kind=kind,
        facts=[fact],
        verse_refs=["Genesis 1:1"],
        evidence_ids=[evidence_id],
        entity_ids=[],
        confidence="high",
        interpretation_level="disputed" if disputed else "fact",
        passage_scope=scope,
        metadata={"explicit_significance": explicit_significance},
    )


def _context(units, evidence, *, availability="AVAILABLE", reference="Genesis 1", passage_text="Genesis 1:1"):
    items = list(evidence)
    bundle = EvidenceBundle(
        passage_ref=reference,
        entities={},
        evidence_items=items,
        geography={},
        provenance={},
        version="1.1",
        evidence_hash="locked-evidence-hash",
    )
    synthesis = CompiledChapterSynthesis(
        reference=reference,
        book="Test",
        chapter=1,
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        synthesis_schema_version="1.1",
        synthesis_compiler_version="1.1",
        synthesis_hash="locked-synthesis-hash",
        evidence_availability=availability,
        synthesis_units=list(units),
        evidence_gaps=[],
        coverage=SynthesisCoverage(
            evidence_item_count=len(items),
            used_evidence_ids=[item.id for item in items],
            unused_evidence_ids=[],
            evidence_categories={},
            category_diversity=0,
            specific_evidence_count=len(items),
            entity_counts={},
            unit_kind_counts={},
            relationship_unit_count=0,
        ),
    )
    return (
        bundle,
        synthesis,
        {"reference": reference, "evidence_hash": bundle.evidence_hash, "synthesis_hash": synthesis.synthesis_hash},
        passage_text,
    )


def _commentary(reference, block_rows):
    return {
        "reference": reference,
        "book": "Test",
        "chapter": 1,
        "sections": [
            {
                "kind": "chapter_overview",
                "title": "Overview",
                "blocks": [
                    {
                        "id": f"block-{index}",
                        "text": text,
                        "verse_refs": ["Genesis 1:1"],
                        "evidence_ids": list(evidence_ids),
                        "synthesis_ids": list(synthesis_ids),
                    }
                    for index, (text, evidence_ids, synthesis_ids) in enumerate(block_rows)
                ],
            }
        ],
    }


def _assess_synthetic(context, raw):
    bundle, synthesis, source_identity, passage_text = context
    return assess_selection_sufficiency(
        synthesis,
        bundle,
        raw,
        passage_text=passage_text,
        source_identity=source_identity,
        renderer_prompt_version="1.8",
        renderer_schema_version="1.2",
    )


def test_historical_genesis1_is_technically_valid_but_selection_collapsed():
    historical_path = FIXTURE_ROOT / "historical-commentary.json"
    assert hashlib.sha256(historical_path.read_bytes()).hexdigest() == HISTORICAL_SHA256
    context = _genesis1_context()
    raw = _read(historical_path)
    validation = _validate_genesis1(raw, context[0], context[1])
    assert validation.valid is True

    assessment = _assessment(context, validation.commentary)
    assert assessment.status == "FAIL"
    assert assessment.diagnostic_code == RENDERER_SELECTION_COLLAPSE
    assert assessment.counts["evidence_records_in_bundle"] == 58
    assert assessment.counts["eligible_evidence_ids"] == 15
    assert len(assessment.eligible_evidence_ids) == 15
    assert assessment.counts["excluded_inherited_background_ids"] == 43
    assert not set(assessment.eligible_evidence_ids).intersection(
        assessment.excluded_inherited_evidence_ids
    )
    assert assessment.counts["available_synthesis_units"] == 12
    assert assessment.counts["eligible_idea_clusters"] == 6
    assert assessment.omitted_core_cluster_ids
    assert assessment.omitted_cluster_ids
    assert assessment.weighted_eligible_coverage < 0.75


def test_approved_genesis1_passes_technical_provenance_selection_and_presentation():
    corrective_path = FIXTURE_ROOT / "corrective-commentary.json"
    assert hashlib.sha256(corrective_path.read_bytes()).hexdigest() == CORRECTIVE_SHA256
    context = _genesis1_context()
    raw = _read(corrective_path)
    validation = _validate_genesis1(raw, context[0], context[1])
    assert validation.valid is True

    binding = _read(FIXTURE_ROOT / "source/provenance-binding.json")
    envelope = _read(FIXTURE_ROOT / "source/ancestry-envelope.json")
    assert audit_provenance_binding_v2(binding, envelope, context[1], context[0].evidence_items)["valid"] is True
    assert response_ancestry_audit_v2(raw, binding)["valid"] is True

    assessment = _assessment(context, validation.commentary)
    assert assessment.status == "PASS"
    assert assessment.diagnostic_code is None
    assert len(assessment.represented_cluster_ids) == 6
    assert len(assessment.consumed_synthesis_ids) == 7
    assert len(assessment.directly_cited_evidence_ids) == 11
    assert assessment.excluded_inherited_cited_ids == []
    assert assessment.weighted_eligible_coverage >= 0.75
    assert assessment.dimensions["technical_validity"] == "NOT_ASSESSED_BY_SELECTION_GATE"
    assert assessment.dimensions["presentation_quality"] == "NOT_ASSESSED_BY_SELECTION_GATE"

    blocks = [block for section in validation.commentary.sections for block in section.blocks]
    quality_audit = audit_chapter("Genesis", 1, validation.commentary, context[0])
    v3_score = score_synthesis_richness(
        context[1].synthesis_units,
        evidence_items=context[0].evidence_items,
        consumed_synthesis_ids=[
            synthesis_id for block in blocks for synthesis_id in block.synthesis_ids
        ],
        blocks=blocks,
        passage_ref="Genesis 1",
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=context[3],
    )
    presentation = assess_gate_v2(
        score=v3_score,
        evidence_availability=context[1].evidence_availability,
        baseline_richness="SYNTHESIS_GAP",
        after_richness=quality_audit["richness_status"],
        safety_checks={
            name: True
            for name in (
                "validation_clean",
                "provenance_complete",
                "hashes_valid",
                "chapter_boundaries_valid",
                "confidence_valid",
                "dispute_state_preserved",
                "unsupported_significance_absent",
            )
        },
        evidence_use_delta=quality_audit["unique_evidence_ids_consumed"],
        section_delta=quality_audit["section_count"],
        commentary_word_count=quality_audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=quality_audit["unique_evidence_ids_consumed"],
    )
    assert presentation.outcome == "PASS"


def test_dense_chapter_collapses_when_only_one_of_several_core_ideas_is_expressed():
    evidence = [_evidence(f"e{i}", parent=f"idea-{i}") for i in range(4)]
    units = [_unit(f"u{i}", FOUR_DISTINCT_FACTS[i], f"e{i}") for i in range(4)]
    context = _context(units, evidence)
    raw = _commentary("Genesis 1", [(units[0].facts[0], ["e0"], ["u0"])])
    result = _assess_synthetic(context, raw)
    assert result.status == "FAIL"
    assert len(result.omitted_core_cluster_ids) == 3
    assert "OMITTED_CORE_IDEA_CLUSTERS" in " ".join(result.reasons)


def test_one_block_passes_for_one_genuinely_important_idea_in_a_thin_chapter():
    evidence = [_evidence("e1", parent="garden", parent_title="Garden")]
    units = [_unit("u1", "The garden is the setting for the first human story.", "e1")]
    context = _context(units, evidence, availability="THIN", passage_text="A garden is planted in Eden.")
    raw = _commentary("Genesis 1", [(units[0].facts[0], ["e1"], ["u1"])])
    result = _assess_synthetic(context, raw)
    assert result.status == "PASS"
    assert len(result.represented_cluster_ids) == 1
    assert result.counts["eligible_idea_clusters"] == 1


@pytest.mark.parametrize("availability", ["THIN", "EVIDENCE_GAP", "DATA_GAP"])
def test_evidence_gap_and_data_gap_contexts_are_not_padded(availability):
    context = _context([], [], availability=availability)
    result = _assess_synthetic(context, _commentary("Genesis 1", []))
    assert result.status == "PASS"
    assert result.counts["eligible_idea_clusters"] == 0
    assert result.weighted_eligible_coverage == 1.0


def test_duplicate_or_parallel_units_are_one_idea_for_coverage():
    evidence = [
        _evidence("e1", parent="what-is-the-sanctuary"),
        _evidence("e2", parent="sanctuary"),
    ]
    units = [
        _unit("u1", "A sanctuary marked the meeting place between God and Israel.", "e1", kind="historical_context"),
        _unit("u2", "The sanctuary was a meeting place between God and Israel.", "e2", kind="historical_context"),
    ]
    context = _context(units, evidence, passage_text="The sanctuary stood in the center of the camp.")
    raw = _commentary("Genesis 1", [(units[0].facts[0], ["e1"], ["u1"])])
    result = _assess_synthetic(context, raw)
    assert result.status == "PASS"
    assert result.counts["available_synthesis_units"] == 2
    assert result.counts["eligible_idea_clusters"] == 1
    assert len(result.redundant_or_parallel_cluster_ids) == 1


def test_surrounding_reception_is_reported_separately_from_current_chapter_claims():
    evidence = [
        _evidence("current", parent="creation", semantic_relationship="DIRECT_CONTEXT"),
        _evidence("reception", parent="later-reception", semantic_relationship="LATER_RECEPTION"),
    ]
    units = [
        _unit("current-unit", "The chapter orders creation through light and darkness.", "current"),
        _unit("reception-unit", "A later letter receives creation as new life in Christ.", "reception", kind="surrounding_passages", scope="SURROUNDING_PASSAGE", disputed=True),
    ]
    context = _context(units, evidence, passage_text="God called the light Day and the darkness Night.")
    raw = _commentary(
        "Genesis 1",
        [
            (units[0].facts[0], ["current"], ["current-unit"]),
            ("A later letter receives creation as new life in Christ, a disputed reception reading.", ["reception"], ["reception-unit"]),
        ],
    )
    result = _assess_synthetic(context, raw)
    assert result.counts["available_idea_clusters"] == 2
    assert result.surrounding_cluster_ids
    assert result.counts["eligible_idea_clusters"] == 2
    assert len(result.represented_cluster_ids) == 2


def test_disputed_reader_relevant_idea_is_counted_without_losing_its_uncertainty():
    evidence = [_evidence("e1", parent="disputed-reading", disputed="major_scholarly_disagreement")]
    units = [_unit("u1", "The disputed reading links the image to royal status.", "e1", disputed=True)]
    context = _context(units, evidence)
    raw = _commentary("Genesis 1", [("The disputed reading links the image to royal status.", ["e1"], ["u1"])])
    result = _assess_synthetic(context, raw)
    assert result.status == "PASS"
    assert result.disputed_cluster_ids
    assert result.counts["disputed_idea_clusters"] == 1


def test_many_citations_do_not_represent_ideas_that_the_commentary_does_not_express():
    evidence = [_evidence(f"e{i}", parent=f"idea-{i}") for i in range(4)]
    units = [_unit(f"u{i}", FOUR_DISTINCT_FACTS[i], f"e{i}") for i in range(4)]
    context = _context(units, evidence)
    raw = _commentary(
        "Genesis 1",
        [("The amber altar marks idea 0.", [f"e{i}" for i in range(4)], [f"u{i}" for i in range(4)])],
    )
    result = _assess_synthetic(context, raw)
    assert len(result.consumed_synthesis_ids) == 4
    assert len(result.represented_cluster_ids) == 1
    assert result.status == "FAIL"
    assert "IDEA_CITATIONS_NOT_EXPRESSED" in " ".join(result.reasons)


def test_high_dump_is_a_separate_presentation_failure_even_when_selection_is_complete():
    evidence = [_evidence(f"e{i}", parent=f"idea-{i}") for i in range(20)]
    units = [_unit(f"u{i}", DENSE_DISTINCT_FACTS[i], f"e{i}") for i in range(20)]
    blocks = [
        (
            unit.facts[0]
            + " This explanation adds supported context about the setting and function "
            + "for readers who are following the chapter. " * 7,
            [unit.evidence_ids[0]],
            [unit.id],
        )
        for unit in units
    ]
    context = _context(units, evidence)
    result = _assess_synthetic(context, _commentary("Genesis 1", blocks))
    assert result.status == "PASS"
    score = score_synthesis_richness(
        units,
        evidence_items=evidence,
        consumed_synthesis_ids=[unit.id for unit in units],
        blocks=[SimpleNamespace(text=text, evidence_ids=eids, synthesis_ids=sids) for text, eids, sids in blocks],
        passage_ref="Genesis 1",
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text="Genesis 1:1",
    )
    presentation = assess_gate_v2(
        score=score,
        evidence_availability="AVAILABLE",
        baseline_richness="SYNTHESIS_GAP",
        after_richness="RICH_ENOUGH",
        safety_checks={"validation_clean": True, "provenance_complete": True},
        evidence_use_delta=20,
        section_delta=1,
        commentary_word_count=200,
        unique_evidence_ids_consumed=20,
    )
    assert score.dump_diagnostics.severity == "HIGH"
    assert presentation.outcome == "QUALITY_FAIL"


def test_missing_locked_context_is_assessment_unavailable_not_inferred():
    result = assess_selection_sufficiency(
        None,
        None,
        {"reference": "Genesis 1", "sections": []},
        source_identity={"reference": "Genesis 1"},
        renderer_prompt_version="1.8",
        renderer_schema_version="1.2",
    )
    assert result.status == "ASSESSMENT_UNAVAILABLE"
    assert result.diagnostic_code == "RENDERER_SELECTION_ASSESSMENT_UNAVAILABLE"
    assert result.weighted_eligible_coverage is None


def test_persisted_selection_assessment_is_hash_and_output_identity_bound():
    context = _genesis1_context()
    raw = _read(FIXTURE_ROOT / "corrective-commentary.json")
    validation = _validate_genesis1(raw, context[0], context[1])
    assessment = _assessment(context, validation.commentary).to_dict()
    expected = {
        "reference": "Genesis 1",
        "evidence_hash": context[0].evidence_hash,
        "synthesis_hash": context[1].synthesis_hash,
    }
    assert validate_selection_assessment(assessment, expected)["valid"] is True

    changed_output = dict(expected, commentary_sha256="different-output")
    invalid = validate_selection_assessment(assessment, changed_output)
    assert invalid["valid"] is False
    assert "SELECTION_ASSESSMENT_SOURCE_IDENTITY_MISMATCH:commentary_sha256" in invalid["reasons"]

    tampered = dict(assessment, weighted_eligible_coverage=0.1)
    assert "SELECTION_ASSESSMENT_HASH_MISMATCH" in validate_selection_assessment(tampered)["reasons"]


def test_legacy_selection_exception_is_versioned_and_bound_to_exact_source():
    identity = {
        "reference": "Genesis 1",
        "evidence_hash": "locked-evidence",
        "synthesis_hash": "locked-synthesis",
        "raw_response_sha256": "raw-output",
        "commentary_sha256": "normalized-output",
    }
    exception = {
        "artifact_version": LEGACY_SELECTION_EXCEPTION_VERSION,
        "decision": LEGACY_SELECTION_EXCEPTION_DECISION,
        "reviewer": "reviewer@example.org",
        "reviewed_at": "2026-10-14T12:00:00Z",
        "rationale": "Reviewed this frozen legacy chapter against the source packet and presentation criteria.",
        "source_identity": identity,
    }
    assert validate_legacy_selection_exception(exception, identity)["valid"] is True
    changed = dict(identity, commentary_sha256="another-artifact")
    result = validate_legacy_selection_exception(exception, changed)
    assert result["valid"] is False
    assert "LEGACY_REVIEW_SOURCE_IDENTITY_MISMATCH" in result["reasons"]


@pytest.mark.parametrize(
    ("fixture_name", "expected_selection_status"),
    [
        ("historical-commentary.json", "FAIL"),
        ("corrective-commentary.json", "PASS"),
    ],
)
def test_production_acceptance_requires_selection_and_presentation_pass(
    tmp_path, fixture_name, expected_selection_status
):
    context = _genesis1_context()
    bundle, synthesis, _, _ = context
    payload = _compatible_schema_payload(_read(FIXTURE_ROOT / fixture_name))
    metadata = payload["generated_metadata"]
    packet = _read(FIXTURE_ROOT / "source/source-packet.json")
    identity = InputIdentity(
        evidence_hash=bundle.evidence_hash,
        synthesis_hash=synthesis.synthesis_hash,
        prompt_version=metadata["commentary_prompt_version"],
        commentary_schema_version=metadata["commentary_schema_version"],
        synthesis_schema_version=synthesis.synthesis_schema_version,
        synthesis_compiler_version=synthesis.synthesis_compiler_version,
        gate_version="commentary-richness-gate-v2.1",
        validator_identity="fixture-validator",
        packet_hash=packet["packet_hash"],
        packet_id=packet["packet_id"],
    )
    prepared = PreparedChapter(
        row={
            "reference": "Genesis 1",
            "book": "Genesis",
            "chapter": 1,
            "canonical_ordinal": 1,
            "input_identity": identity.to_dict(),
        },
        bundle=bundle,
        synthesis=synthesis,
        packet=packet,
    )
    manifest = build_manifest([prepared], batch_size=1, run_id="run-selection-collapse")
    chapter = manifest["chapters"][0]
    batch = batch_manifest(manifest, "batch-001")
    state_path = tmp_path / "state.json"
    state = {
        "state_path": str(state_path),
        "run_id": manifest["run_id"],
        "batch_id": "batch-001",
        "chapters": {"Genesis 1": {"state": "RAW_CAPTURED", "attempt": 1}},
    }
    record = state["chapters"]["Genesis 1"]
    record["raw_sha256"] = sha256_bytes(b"historical fixture renderer bytes")
    runner = ProductionRunner(tmp_path)
    result = runner._evaluate_payload(
        manifest,
        batch,
        chapter,
        prepared,
        record,
        state,
        False,
        payload=payload,
        normalization={"applied": False},
    )

    accepted_path = tmp_path / ".bhf-data/bhf-commentary-production/v1" / chapter["expected_artifacts"]["accepted"]
    selection_path = tmp_path / ".bhf-data/bhf-commentary-production/v1" / chapter["expected_artifacts"]["selection_assessment"]
    receipt = _read(selection_path)
    assert receipt["selection_sufficiency"]["status"] == expected_selection_status
    if expected_selection_status == "FAIL":
        assert result["state"] == GATE_QUALITY_FAIL
        assert result["rejection_codes"] == [RENDERER_SELECTION_COLLAPSE]
        assert receipt["selection_sufficiency"]["diagnostic_code"] == RENDERER_SELECTION_COLLAPSE
        assert accepted_path.is_file() is False
    else:
        assert result["state"] in {"COMPLETE", "GATE_PASS", "GATE_WARNING"}
        assert result["gate_status"] in {"PASS", "PASS_WITH_WARNING"}
        assert accepted_path.is_file() is True


def test_recovery_does_not_complete_accepted_output_without_bound_selection_pass(tmp_path):
    context = _genesis1_context()
    bundle, synthesis, source_identity, _ = context
    corrective = _read(FIXTURE_ROOT / "corrective-commentary.json")
    validation = _validate_genesis1(corrective, bundle, synthesis)
    accepted_payload = validation.commentary.to_dict()
    accepted_payload["status"] = "validated"
    commentary_hash = sha256_json(accepted_payload)
    input_identity = {
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
        "prompt_version": corrective["generated_metadata"]["commentary_prompt_version"],
        "commentary_schema_version": corrective["generated_metadata"]["commentary_schema_version"],
    }
    input_identity.update(source_identity)
    chapter = {
        "reference": "Genesis 1",
        "expected_artifacts": {
            "raw": "runs/recovery/raw/attempt-001/genesis_001.json",
            "accepted": "runs/recovery/accepted/attempt-001/genesis_001.json",
            "gate": "runs/recovery/gate/attempt-001/genesis_001.json",
            "selection_assessment": "runs/recovery/selection-assessments/attempt-001/genesis_001.json",
            "quarantine": "runs/recovery/quarantine/attempt-001/genesis_001.json",
        },
        "input_identity": input_identity,
    }
    raw_sha = sha256_bytes(b"fixture raw")
    accepted_path = tmp_path / ".bhf-data/bhf-commentary-production/v1" / chapter["expected_artifacts"]["accepted"]
    gate_path = tmp_path / ".bhf-data/bhf-commentary-production/v1" / chapter["expected_artifacts"]["gate"]
    selection_path = tmp_path / ".bhf-data/bhf-commentary-production/v1" / chapter["expected_artifacts"]["selection_assessment"]
    write_json(accepted_path, accepted_payload)
    write_json(gate_path, {"assessment": {"outcome": "PASS"}})
    assessment = _assessment(context, validation.commentary).to_dict()
    assessment["source_identity"].update(
        input_identity
        | {"commentary_sha256": commentary_hash, "raw_response_sha256": raw_sha}
    )
    # Rebuild the assessment hash after adding the immutable output binding.
    assessment.pop("assessment_hash")
    from bhf_agent.chapter_commentary.selection_sufficiency import _hash_json

    assessment["assessment_hash"] = _hash_json(assessment)
    write_json(
        selection_path,
        {
            "artifact_version": f"{SELECTION_SUFFICIENCY_VERSION}-receipt-v1",
            "reference": "Genesis 1",
            "input_identity": input_identity,
            "selection_sufficiency": assessment,
        },
    )
    result = reconcile_chapter(
        tmp_path,
        chapter,
        {"state": "ACCEPTED", "raw_sha256": raw_sha, "attempt": 1},
    )
    assert result["state"] == "COMPLETE"

    accepted_payload["sections"][0]["blocks"][0]["text"] += " changed"
    write_json(accepted_path, accepted_payload)
    result = reconcile_chapter(
        tmp_path,
        chapter,
        {"state": "ACCEPTED", "raw_sha256": raw_sha, "attempt": 1},
    )
    assert result["state"] == "QUARANTINED"
    assert "assessment hash is invalid" in result["recovery_error"] or "identity" in result["recovery_error"]
