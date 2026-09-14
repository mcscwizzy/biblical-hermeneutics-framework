"""Focused contract tests for the seven-chapter reader-projection validation."""

from functools import lru_cache

import pytest

from bhf_agent.chapter_commentary.reader_level_projection import (
    READER_LEVEL_IDEA_PROJECTION_VERSION,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
)
from tools import commentary_v12_reader_projection_seven_chapter as validation


@lru_cache(maxsize=1)
def _records():
    return validation.build_records()


def test_exact_seven_chapter_corpus_and_frozen_contracts():
    manifest, records = _records()
    assert manifest["source_head"] == validation.START_SHA
    assert manifest["prompt_version"] == "1.7"
    assert manifest["projection_version"] == READER_LEVEL_IDEA_PROJECTION_VERSION
    assert [record["reference"] for record in records] == list(validation.EXPECTED_REFERENCES)
    assert manifest["chapter_count"] == 7
    assert manifest["frozen_contracts"] == {
        "essential_passage_context": "essential-passage-context-v2",
        "reader_relevance_eligibility": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
        "richness_clusters": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
        "richness_policy": RICHNESS_POLICY_VERSION_V3,
        "gate": RICHNESS_GATE_V2_VERSION,
    }
    assert "1.8" not in validation.system_prompt_for_version("1.7")


def test_projection_shapes_and_ancestry_cover_dense_and_sparse_controls():
    _, records = _records()
    expected = {
        "Isaiah 13": (7, 2, 2, 0),
        "Romans 3": (25, 4, 4, 0),
        "1 Corinthians 14": (33, 7, 7, 0),
        "Revelation 20": (21, 6, 4, 3),
        "Revelation 21": (119, 16, 8, 23),
        "Exodus 14": (34, 2, 2, 0),
        "Deuteronomy 10": (40, 1, 1, 0),
    }
    for record in records:
        projection = record["projection"]
        assert (
            projection["synthesis_unit_count"],
            projection["eligible_cluster_count"],
            projection["projected_idea_count"],
            projection["grouped_relationship_count"],
        ) == expected[record["reference"]]
        assert projection["ancestry_preserved"] is True


def test_prompt_17_is_unchanged_and_variant_is_additive():
    _, records = _records()
    for record in records:
        assert record["prompt"]["original_user_prompt_sha256"] == record["baseline"]["user_prompt_sha256"]
        assert record["prompt"]["system_prompt_sha256"] == record["baseline"]["system_prompt_sha256"]
        assert record["prompt"]["variant_user_prompt_sha256"] != record["prompt"]["original_user_prompt_sha256"]
        assert "COMPILED CHAPTER SYNTHESIS:" in record["_variant_prompt"]
        assert "DISTINCT READER-LEVEL IDEAS" in record["_variant_prompt"]
        assert record["prompt"]["version"] == "1.7"
        assert "1.8" not in record["_variant_prompt"]


def test_revelation_21_reused_candidate_import_and_evaluation_remain_exact():
    _, records = _records()
    record = next(record for record in records if record["reference"] == "Revelation 21")
    result, _ = validation._candidate_eval(record)
    assert record["candidate"]["status"] == "REUSED_EXISTING_IMMUTABLE"
    assert record["candidate"]["generation_count"] == 1
    assert record["candidate"]["response_sha256"] == validation.REUSED_REVELATION_21_SHA256
    assert result["structural_result"] == "ACCEPTED"
    assert result["hard_provenance_errors"] == []
    assert result["weighted_coverage"] == 1.0
    assert result["eligible_idea_utilization"] == 1.0
    assert result["core_coverage"] == 1.0
    assert result["category_coverage"] == 1.0
    assert result["dump_severity"] == "NONE"
    assert result["quality_gate_outcome"] == "PASS"
    assert result["word_count"] == 457


def test_candidate_generation_is_fail_closed_until_all_six_missing_responses_exist():
    _, records = _records()
    missing = [
        record["reference"]
        for record in records
        if record["candidate"]["status"] == "AWAITING_EXTERNAL_RENDERER"
    ]
    assert missing == [
        "Isaiah 13",
        "Romans 3",
        "1 Corinthians 14",
        "Revelation 20",
        "Exodus 14",
        "Deuteronomy 10",
    ]
    assert all(record["candidate"]["generation_count"] == 0 for record in records if record["reference"] != "Revelation 21")


def test_projection_manifest_reproducibility():
    first, _ = _records()
    second, _ = validation.build_records()
    assert first == second
