"""Integrity checks for the deterministic Genesis G0 evidence census."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-g0-evidence-census"


def _census():
    return json.loads((AUDIT / "genesis-evidence-census.json").read_text(encoding="utf-8"))


def test_census_covers_each_genesis_chapter_once_with_production_inputs():
    census = _census()
    rows = census["chapters"]

    assert census["status"] == "GENESIS_G0_EVIDENCE_CENSUS_COMPLETE"
    assert census["total_chapters_audited"] == 50
    assert [row["chapter"] for row in rows] == list(range(1, 51))
    assert census["coverage_totals"] == {"GAP": 38, "GOOD": 3, "SPARSE": 6, "THIN": 3}
    assert all(row["current_input_identity"]["evidence_hash"] for row in rows)
    assert all(row["current_input_identity"]["synthesis_hash"] for row in rows)
    assert all(row["raw_candidate_count"] == len(row["raw_candidate_ids"]) for row in rows)
    assert all("commentary" in row and "dimension_assessment" in row for row in rows)


def test_primeval_audit_preserves_divine_council_dispute_and_comparison_foundation():
    census = _census()
    genesis_six = census["chapters"][5]
    comparison = json.loads((AUDIT / "genesis-existing-object-reuse.json").read_text(encoding="utf-8"))
    comparison_rows = [row for row in comparison["objects"] if row["object_id"] == "mesopotamian-creation-and-flood-comparisons"]

    assert genesis_six["reference"] == "Genesis 6"
    assert genesis_six["dimension_assessment"]["divine_council_spiritual_worldview"]["status"] != "NOT_APPLICABLE"
    assert any(item["relevance_metadata"].get("dispute_status") not in {None, "not_disputed"} for item in genesis_six["evidence_items"])
    assert len(comparison_rows) == 1
    assert comparison_rows[0]["reuse_classification"] in {"REUSE_AS_IS", "ENRICH", "LINK_TO_MORE_CHAPTERS"}


def test_geography_and_unrelated_controls_are_recorded_without_entering_genesis_population():
    census = _census()
    controls = {row["reference"]: row for row in census["controls"]}

    assert set(controls) == {"Isaiah 36", "Acts 16", "Revelation 18"}
    assert controls["Isaiah 36"]["role"] == "recent geography impact"
    assert controls["Acts 16"]["role"] == "unrelated unchanged control"
    assert controls["Revelation 18"]["role"] == "unrelated unchanged control"
    assert all(row["identity_matches_release_lineage"] for row in controls.values())
    assert len(census["chapters"]) == 50
    assert not any(row["reference"] in controls for row in census["chapters"])


def test_frozen_release_and_ckl_identities_match_at_start_and_finish():
    identities = _census()["frozen_identities"]

    assert identities["unchanged"] is True
    assert identities["before"] == identities["after"]
    assert identities["before"]["release"]["release"] == "commentary-v1.2"
    assert identities["before"]["release"]["all_indexed_files_valid"] is True
    assert identities["before"]["ckl"]["object_count"] == identities["before"]["ckl"]["manifest_object_count"]
    assert identities["before"]["ckl"]["byte_signature"] == "0bd8259ce0af2a8cd748d1c82cda732010954ee98173e72238950f8de2661c40"


def test_expansion_plan_is_domain_grouped_and_marks_g0_as_plan_only():
    plan = json.loads((AUDIT / "genesis-expansion-plan.json").read_text(encoding="utf-8"))

    assert plan["status"] == "PLAN_ONLY_NO_PRODUCTION_CHANGES"
    assert plan["recommended_first_production_batch"] == "primeval_origins"
    assert [batch["batch_id"] for batch in plan["batches"]] == [
        "primeval_origins", "flood_post_flood", "nations_babel",
        "abraham_cycle", "jacob_esau_cycle", "joseph_judah_cycle",
    ]
    covered = {chapter for batch in plan["batches"] for chapter in batch["chapters"]}
    assert covered == {f"Genesis {chapter}" for chapter in range(1, 51)}
