"""Focused contract tests for the immutable Commentary v1.2 scale pilot."""

from collections import Counter

from bhf_agent.chapter_commentary.prompts import system_prompt_for_version
from tools import commentary_v12_scale_pilot as pilot
from tools import commentary_v12_scale_render as renderer


def test_frozen_contract_versions_and_no_prompt_18():
    assert pilot.PROMPT_VERSION == "1.7"
    assert "1.8" not in system_prompt_for_version(pilot.PROMPT_VERSION)
    assert pilot.FROZEN_CONTRACTS == {
        "essential_passage_context": "essential-passage-context-v2",
        "reader_relevance_eligibility": "reader-relevance-eligibility-v1",
        "richness_clusters": "commentary-richness-clusters-v2",
        "richness_policy": "commentary-richness-policy-v3-reader-relevance",
        "gate": "commentary-richness-gate-v2.1",
    }


def test_pilot_corpus_is_deterministic_stratified_and_out_of_sample():
    rows, _ = pilot._selection_metadata()
    first = pilot.select_corpus(rows)
    second = pilot.select_corpus(rows)
    assert [row["reference"] for row in first] == [row["reference"] for row in second]
    assert len(first) == 75 == sum(pilot.BATCH_SIZES)
    assert Counter(row["literary_stratum"] for row in first) == pilot.STRATUM_TARGETS
    assert set(pilot.ANCHORS) <= {row["reference"] for row in first}
    assert sum(row["seen_status"] == "unseen" for row in first) / len(first) >= 0.70
    assert {row["density_class"] for row in first} == {"sparse", "medium", "dense"}
    assert sum(row["content_shape"] == "genealogy/list/administrative" for row in first) >= 3
    assert not any(
        row["book"] == "Song of Songs" and row["literary_stratum"] != "Poetry/Wisdom"
        for row in first
    )


def test_projection_and_ancestry_envelope_are_deterministic():
    prepared = pilot.prepare_chapter("Exodus", 14)
    clusters = pilot._clusters(prepared)
    one = pilot.project_reader_level_ideas(prepared.synthesis, clusters, prepared.bundle.evidence_items)
    two = pilot.project_reader_level_ideas(prepared.synthesis, pilot._clusters(prepared), prepared.bundle.evidence_items)
    assert one.to_dict() == two.to_dict()
    envelope_one = pilot.build_ancestry_envelope(one, prepared.synthesis, prepared.bundle.evidence_items)
    envelope_two = pilot.build_ancestry_envelope(two, prepared.synthesis, prepared.bundle.evidence_items)
    assert envelope_one == envelope_two


def test_percentiles_and_failure_classification_are_deterministic():
    assert pilot._percentile([0, 1, 2, 3, 4], 25) == 1.0
    row = {
        "reference": "Example 1", "structural_validity": True,
        "hard_provenance_errors": [], "ancestry_mismatch_count": 0,
        "dump_severity": "NONE", "readability_result": "PASS",
        "checklist_behavior": "PASS", "core_coverage": 1.0,
        "category_coverage": 1.0, "gate_result": "FAIL",
        "weighted_coverage": 0.6, "eligible_idea_utilization": 0.5,
        "projected_concepts_represented": 1, "projected_idea_count": 1,
    }
    assert pilot._classification(row) == "RICHNESS_SHORTFALL"


def test_batch_shape_and_quarantine_labels_are_fixed():
    assert pilot.BATCH_SIZES == (13, 13, 13, 12, 12, 12)
    assert pilot.KNOWN_EDGE_CASES == {"Revelation 20": "KNOWN_SCORER_RENDERER_EDGE_CASE"}
    assert pilot.TARGET_COUNT == 75
    assert renderer.CODEX.name == "codex"
    assert renderer._valid_json(b'{"sections": []}')
    assert not renderer._valid_json(b"not json")


def test_aggregate_metrics_count_ancestry_separately_from_hard_provenance():
    row = {
        "structural_validity": True, "hard_provenance_errors": [],
        "ancestry_mismatch_count": 1, "gate_result": "PASS",
        "weighted_coverage": 1.0, "eligible_idea_utilization": 1.0,
        "core_coverage": 1.0, "category_coverage": 1.0,
        "dump_severity": "NONE", "final_chapter_classification": "PROVENANCE_FAILURE",
        "prose_word_count": 100,
    }
    result = pilot._summary([row])
    assert result["provenance_safe_percentage"] == 100.0
    assert result["ancestry_safe_percentage"] == 0.0
    assert result["genuine_renderer_failure_rate"] == 100.0


def test_frozen_manifest_batches_and_checksums_reproduce():
    context = pilot.build_context()
    stored = pilot._read(context["root"] / "manifest.json")
    assert stored == context["manifest"]
    pilot._verify_identity(stored, "manifest_identity", "test manifest")
    for batch, size in enumerate(pilot.BATCH_SIZES, 1):
        batch_manifest = pilot._read(context["root"] / f"batch-{batch:03d}/batch-manifest.json")
        assert len(batch_manifest["chapters"]) == size
        assert batch_manifest["chapters"] == [row for row in stored["chapters"] if row["batch"] == batch]
    checksum_artifact = pilot._read(context["root"] / "checksums.json")
    for relative, expected in checksum_artifact["files"].items():
        assert pilot.sha256_bytes((context["root"] / relative).read_bytes()) == expected
