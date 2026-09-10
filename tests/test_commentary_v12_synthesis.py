"""Deterministic compiler tests for Commentary v1.2."""

from dataclasses import replace

from bhf_agent.chapter_commentary.synthesis import (
    compile_chapter_synthesis,
    validate_synthesis,
)
from bhf_agent.presentation.evidence_hash import calculate_evidence_hash
from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem


def _item(
    item_id: str,
    claim: str,
    *,
    entity: str = "gath",
    confidence: str = "high",
    metadata=None,
    anchor: str = "1 Samuel 21:10",
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        claim=claim,
        category="geography",
        source_ids=["source"],
        related_entity_ids=[entity] if entity else [],
        passage_anchors=[anchor],
        confidence=confidence,
        relevance_metadata={
            "source_kind": "ckl_evidence_item",
            "applicability_scope": "passage",
            "anchor_source": "child",
            "anchor_specificity": "verse",
            **dict(metadata or {}),
        },
    )


def _bundle(*items: EvidenceItem) -> EvidenceBundle:
    entities = {
        "people": [],
        "places": [EntityRef("gath", "Gath", "place")],
        "groups": [],
        "events": [],
        "artifacts": [],
    }
    bundle = EvidenceBundle(
        passage_ref="1 Samuel 21",
        entities=entities,
        evidence_items=list(items),
        geography={},
        provenance={},
        version="1.1",
    )
    return replace(bundle, evidence_hash=calculate_evidence_hash(bundle))


def test_same_evidence_produces_identical_synthesis_and_hash():
    bundle = _bundle(
        _item("gath-city", "Gath was a Philistine city."),
        _item("david-gath", "David fled from Saul to Gath."),
    )
    first = compile_chapter_synthesis(bundle)
    second = compile_chapter_synthesis(bundle)
    assert first == second
    assert first.synthesis_hash == second.synthesis_hash
    assert validate_synthesis(first, bundle) == ()


def test_changed_evidence_changes_synthesis_hash():
    first_bundle = _bundle(_item("gath-city", "Gath was a Philistine city."))
    second_bundle = _bundle(_item("gath-city", "Gath was a Philistine stronghold."))
    assert compile_chapter_synthesis(first_bundle).synthesis_hash != compile_chapter_synthesis(second_bundle).synthesis_hash


def test_schema_or_compiler_version_changes_synthesis_identity():
    bundle = _bundle(_item("gath-city", "Gath was a Philistine city."))
    baseline = compile_chapter_synthesis(bundle)
    schema_changed = compile_chapter_synthesis(bundle, schema_version="1.0")
    compiler_changed = compile_chapter_synthesis(bundle, compiler_version="1.0")
    assert baseline.synthesis_hash != schema_changed.synthesis_hash
    assert baseline.synthesis_hash != compiler_changed.synthesis_hash


def test_dispute_and_confidence_are_propagated_without_upgrade():
    bundle = _bundle(
        _item(
            "disputed-gath",
            "The identification is disputed.",
            confidence="low",
            metadata={"dispute_status": "disputed"},
        )
    )
    unit = compile_chapter_synthesis(bundle).synthesis_units[0]
    assert unit.confidence == "low"
    assert unit.interpretation_level == "disputed"
    assert unit.kind == "interpretive_questions"


def test_passage_anchors_are_preserved_and_unrelated_entities_do_not_leak():
    item = _item("gath-city", "Gath was a Philistine city.", anchor="1 Samuel 21:10-11")
    bundle = _bundle(item)
    synthesis = compile_chapter_synthesis(bundle)
    unit = synthesis.synthesis_units[0]
    assert unit.verse_refs == ["1 Samuel 21:10-11"]
    assert unit.entity_ids == ["gath"]
    assert all("unrelated" not in entry.entity_ids for entry in synthesis.synthesis_units)


def test_shared_entity_relationship_can_create_traceable_why_it_matters_unit():
    bundle = _bundle(
        _item("gath-city", "Gath was a Philistine city."),
        _item("goliath-gath", "Goliath was associated with Gath."),
        _item("david-gath", "David fled from Saul to Gath."),
    )
    synthesis = compile_chapter_synthesis(bundle)
    unit = next(value for value in synthesis.synthesis_units if value.kind == "why_it_matters")
    assert unit.interpretation_level == "inference"
    assert unit.metadata["relationship_basis"] == "shared_entities"
    assert unit.metadata["safe_for_significance"] is True
    assert set(unit.evidence_ids) == {"gath-city", "goliath-gath", "david-gath"}
    assert set(unit.facts) == {item.claim for item in bundle.evidence_items}


def test_unrelated_items_are_not_combined_into_significance():
    bundle = _bundle(
        _item("gath-city", "Gath was a Philistine city."),
        _item("unrelated", "An unrelated supplied fact.", entity=""),
    )
    synthesis = compile_chapter_synthesis(bundle)
    why_units = [unit for unit in synthesis.synthesis_units if unit.kind == "why_it_matters"]
    assert not why_units


def test_synthesis_validator_rejects_unknown_entity_and_unsupported_fact():
    bundle = _bundle(_item("gath-city", "Gath was a Philistine city."))
    synthesis = compile_chapter_synthesis(bundle)
    unit = replace(synthesis.synthesis_units[0], entity_ids=["unrelated"], facts=["Invented."])
    tampered = replace(synthesis, synthesis_units=[unit])
    errors = validate_synthesis(tampered, bundle)
    assert any("unknown entity" in error for error in errors)
    assert any("absent from its evidence ancestry" in error for error in errors)
    assert any("synthesis_hash" in error for error in errors)
