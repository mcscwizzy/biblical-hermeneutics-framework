"""Focused checks for the frozen unified seven-chapter renderer diagnostic."""

from __future__ import annotations

import json
from pathlib import Path

from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    response_ancestry_audit,
)
from tools import commentary_v12_unified_reader_projection_seven_chapter as diagnostic


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".bhf-data/bhf-commentary-candidates/reader-projection-ancestry-envelope-seven-chapter-ee44d0e3507b66a10aab"


def test_frozen_corpus_and_renderer_contract_are_exact():
    context = diagnostic.build_context(ROOT)
    manifest = context["manifest"]

    assert tuple(manifest["corpus"]) == diagnostic.EXPECTED_REFERENCES
    assert manifest["chapter_count"] == 7
    assert manifest["prompt_version"] == "1.7"
    assert manifest["projection_version"] == "reader-level-idea-projection-v1"
    assert manifest["ancestry_envelope_version"] == "reader-level-idea-ancestry-envelope-v1"
    assert manifest["renderer"] == "gpt-5.6-sol"
    assert manifest["renderer_effort"] == "medium"
    assert manifest["runtime_self_attestation"] is False


def test_prompt_17_is_unchanged_and_layers_are_additive():
    context = diagnostic.build_context(ROOT)
    for chapter in context["chapters"]:
        source = chapter["projection_prompt"]
        candidate = chapter["candidate_prompt"]
        assert "DISTINCT READER-LEVEL IDEAS" in source
        assert "READER-LEVEL IDEA ANCESTRY ENVELOPE" not in source
        assert "READER-LEVEL IDEA ANCESTRY ENVELOPE" in candidate
        assert "COMPILED CHAPTER SYNTHESIS:" in candidate
        assert "1.8" not in candidate


def test_projection_and_envelope_are_deterministic_for_all_seven():
    first = diagnostic.build_context(ROOT)
    second = diagnostic.build_context(ROOT)

    assert first["manifest"] == second["manifest"]
    assert [row["projection"] for row in first["chapters"]] == [
        row["projection"] for row in second["chapters"]
    ]
    assert [row["envelope"] for row in first["chapters"]] == [
        row["envelope"] for row in second["chapters"]
    ]


def test_every_envelope_path_retains_exact_unit_ancestry():
    context = diagnostic.build_context(ROOT)
    for chapter in context["chapters"]:
        audit = chapter["envelope"]["ancestry_audit"]
        assert audit["paths_have_exact_unit_ancestry"] is True
        assert audit["cross_synthesis_evidence_leakage"] == []
        assert audit["invented_synthesis_ids"] == []
        assert audit["invented_evidence_ids"] == []
        assert chapter["envelope_audit"]["valid"] is True


def test_scoring_contract_is_frozen():
    manifest = diagnostic.build_context(ROOT)["manifest"]
    assert manifest["frozen_scoring_contracts"] == {
        "essential_passage_context": "essential-passage-context-v2",
        "reader_relevance_eligibility": "reader-relevance-eligibility-v1",
        "richness_clusters": "commentary-richness-clusters-v2",
        "richness_policy": "commentary-richness-policy-v3-reader-relevance",
        "gate": "commentary-richness-gate-v2.1",
    }


def test_prepared_artifacts_are_reproducible(tmp_path):
    result = diagnostic.prepare(output_root=tmp_path)
    expected = diagnostic.build_context(ROOT)["manifest"]

    assert result["manifest_identity"] == expected["manifest_identity"]
    assert json.loads((tmp_path / "manifest.json").read_text()) == expected
    assert len(list((tmp_path / "renderer-input").glob("*/user_prompt.txt"))) == 7
    assert len(list((tmp_path / "ancestry-envelopes").glob("*.json"))) == 7


def test_fresh_response_set_is_complete_unique_and_not_historical():
    identities = json.loads((TARGET / "responses/response-identities.json").read_text())
    historical = diagnostic.SOURCE_NAMESPACE / "responses/raw"
    historical_hashes = {
        diagnostic.sha256_bytes(path.read_bytes()) for path in historical.glob("*.json")
    }

    assert identities["fresh_response_count"] == 7
    assert identities["one_generation_per_chapter"] is True
    assert identities["retries"] == 0
    hashes = [row["response_sha256"] for row in identities["responses"]]
    assert len(hashes) == len(set(hashes)) == 7
    assert not set(hashes).intersection(historical_hashes)


def test_all_fresh_responses_have_legal_ancestry_and_no_internal_terms():
    context = diagnostic.build_context(ROOT)
    for chapter in context["chapters"]:
        record = chapter["record"]
        raw = json.loads((TARGET / "responses/raw" / diagnostic._filename(record)).read_text())
        audit = response_ancestry_audit(raw, chapter["envelope"])
        prose = diagnostic._prose(raw).lower()
        assert audit["valid"] is True
        assert audit["ancestry_mismatch_count"] == 0
        assert not [term for term in diagnostic.INTERNAL_PROSE_TERMS if term in prose]


def test_final_report_preserves_dense_failure_and_sparse_controls():
    report = json.loads((TARGET / "final-report.json").read_text())
    rows = {row["reference"]: row for row in report["chapters"]}

    assert report["final_classification"] == "UNIFIED_READER_PROJECTION_7_CHAPTER_NOT_READY"
    assert rows["Revelation 20"]["final_chapter_classification"] == "REGRESSED"
    assert rows["Revelation 20"]["weighted_coverage"] == 0.6111
    assert rows["Revelation 20"]["eligible_idea_utilization"] == 0.6667
    assert rows["Exodus 14"]["final_chapter_classification"] == "STABLE_PASS"
    assert rows["Deuteronomy 10"]["final_chapter_classification"] == "STABLE_PASS"
    assert report["aggregate"]["structural_valid_count"] == 7
    assert report["aggregate"]["ancestry_mismatch_count"] == 0
    assert report["aggregate"]["hard_provenance_error_count"] == 0

