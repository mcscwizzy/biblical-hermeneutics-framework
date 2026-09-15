"""Focused integrity tests for the isolated Dense Reader v0.1 contract."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

from bhf_agent.chapter_commentary.dense_reader import (
    DENSE_READER_EXPERIMENT_VERSION,
    DenseReaderUnit,
    build_reader_artifact,
    calculate_artifact_identity,
    load_reader_artifact,
    save_reader_artifact,
    validate_reader_artifact,
)
from bhf_agent.presentation.models import EvidenceItem
from bhf_agent.chapter_commentary.synthesis.models import SynthesisUnit


def _source() -> dict:
    return {
        "reference": "Genesis 1",
        "book": "Genesis",
        "chapter": 1,
        "status": "validated",
        "generated_metadata": {
            "commentary_prompt_version": "1.5",
            "commentary_schema_version": "1.2",
            "synthesis_schema_version": "1.1",
            "synthesis_compiler_version": "1.1",
        },
        "sections": [
            {
                "kind": "historical_context",
                "title": "Historical Context",
                "blocks": [
                    {
                        "id": "block_001",
                        "text": "Historically, this chapter is read within the following setting: The first claim matters. The first claim matters.",
                        "verse_refs": ["Genesis 1:1"],
                        "evidence_ids": ["ev_1"],
                        "synthesis_ids": ["syn_1"],
                    },
                    {
                        "id": "block_002",
                        "text": "Historically, this chapter is read within the following setting: The second claim adds context.",
                        "verse_refs": ["Genesis 1:2"],
                        "evidence_ids": ["ev_2"],
                        "synthesis_ids": ["syn_2"],
                    },
                ],
            }
        ],
    }


def _synthesis() -> SimpleNamespace:
    return SimpleNamespace(
        synthesis_units=[
            SynthesisUnit(
                id="syn_1",
                kind="chapter_overview",
                facts=["Claim one"],
                verse_refs=["Genesis 1:1"],
                evidence_ids=["ev_1"],
                entity_ids=[],
                source_anchors=["Genesis 1:1"],
            ),
            SynthesisUnit(
                id="syn_2",
                kind="historical_context",
                facts=["Claim two"],
                verse_refs=["Genesis 1:2"],
                evidence_ids=["ev_2"],
                entity_ids=[],
                source_anchors=["Genesis 1:2"],
            ),
        ]
    )


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem("ev_1", "Claim one", "history", [], [], ["Genesis 1:1"], "high"),
        EvidenceItem("ev_2", "Claim two", "history", [], [], ["Genesis 1:2"], "medium"),
    ]


def _artifact(tmp_path, *, force=True):
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(_source()), encoding="utf-8")
    return build_reader_artifact(
        _source(),
        source_path=source_path,
        source_root=tmp_path,
        synthesis=_synthesis(),
        evidence_items=_evidence(),
        source_word_count=20,
        source_dump_severity="MODERATE",
        source_quality_metrics={"weighted_coverage": 1.0, "synthesis_utilization": 1.0},
        force_consolidation=force,
    ), source_path


def _valid_errors(artifact, source_path):
    return validate_reader_artifact(
        artifact,
        source_payload=_source(),
        source_path=source_path,
        source_root=source_path.parent,
        synthesis=_synthesis(),
        evidence_items=_evidence(),
    )


def test_source_block_mapping_and_union_preserve_ancestry(tmp_path):
    artifact, source_path = _artifact(tmp_path)

    assert len(artifact.units) == 2
    assert not _valid_errors(artifact, source_path)
    assert artifact.units[0].source_block_ids == ["block_001"]
    assert artifact.units[0].verse_refs == ["Genesis 1:1"]
    assert artifact.units[0].evidence_ids == ["ev_1"]


def test_evidence_union_and_verse_references_are_exact_for_merged_units(tmp_path):
    source = _source()
    source["sections"][0]["blocks"][1]["evidence_ids"] = ["ev_1", "ev_2"]
    source["sections"][0]["blocks"][1]["synthesis_ids"] = ["syn_1", "syn_2"]
    source_path = tmp_path / "source.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    artifact = build_reader_artifact(
        source,
        source_path=source_path,
        source_root=tmp_path,
        synthesis=_synthesis(),
        evidence_items=_evidence(),
        force_consolidation=True,
    )

    assert len(artifact.units) == 1
    assert artifact.units[0].source_block_ids == ["block_001", "block_002"]
    assert artifact.units[0].evidence_ids == ["ev_1", "ev_2"]
    assert artifact.units[0].verse_refs == ["Genesis 1:1", "Genesis 1:2"]


def test_source_hash_mismatch_is_rejected(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    source_path.write_text(json.dumps({**_source(), "status": "changed"}), encoding="utf-8")

    errors = _valid_errors(artifact, source_path)

    assert "source Commentary artifact hash mismatch" in errors


def test_fabricated_evidence_id_is_rejected(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    unit = replace(artifact.units[0], evidence_ids=["fabricated"])
    bad = replace(artifact, units=[unit, artifact.units[1]])

    errors = _valid_errors(bad, source_path)

    assert "evidence ancestry is not the mapped union" in " ".join(errors)
    assert "fabricated evidence IDs" in " ".join(errors)


def test_fabricated_source_block_id_is_rejected(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    unit = replace(artifact.units[0], source_block_ids=["fabricated"])
    bad = replace(artifact, units=[unit, artifact.units[1]])

    errors = _valid_errors(bad, source_path)

    assert "fabricated source block IDs" in " ".join(errors)


def test_fabricated_verse_reference_is_rejected(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    unit = replace(artifact.units[0], verse_refs=["Genesis not-a-reference"])
    bad = replace(artifact, units=[unit, artifact.units[1]])

    errors = _valid_errors(bad, source_path)

    assert "verse-reference ancestry is not the mapped union" in " ".join(errors)
    assert "invalid verse reference" in " ".join(errors)


def test_duplicate_reader_unit_and_empty_output_are_rejected(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    duplicate = replace(artifact.units[1], id=artifact.units[0].id)
    errors = _valid_errors(replace(artifact, units=[artifact.units[0], duplicate]), source_path)
    assert "duplicate reader unit IDs" in errors

    empty_errors = _valid_errors(replace(artifact, units=[]), source_path)
    assert "reader output has no units" in empty_errors


def test_core_omission_is_rejected(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    unit = replace(artifact.units[0], source_synthesis_ids=[])
    errors = _valid_errors(replace(artifact, units=[unit, artifact.units[1]]), source_path)

    assert "reader omitted one or more source CORE synthesis IDs" in errors


def test_grouping_is_deterministic_and_versioned(tmp_path):
    first, source_path = _artifact(tmp_path)
    second, _ = _artifact(tmp_path)

    assert first.to_dict() == second.to_dict()
    assert first.experiment_version == DENSE_READER_EXPERIMENT_VERSION
    assert calculate_artifact_identity(first) == calculate_artifact_identity(second)


def test_serialization_round_trip_preserves_identity(tmp_path):
    artifact, _ = _artifact(tmp_path)
    path = tmp_path / "reader.json"
    save_reader_artifact(artifact, path)
    loaded = load_reader_artifact(path)

    assert loaded.artifact_identity == calculate_artifact_identity(loaded)
    assert loaded.to_dict() == json.loads(path.read_text(encoding="utf-8"))


def test_experimental_version_identity_is_strict(tmp_path):
    artifact, source_path = _artifact(tmp_path)
    bad = replace(artifact, experiment_version="other-experiment")

    errors = _valid_errors(bad, source_path)

    assert "unsupported dense reader experiment version" in errors
