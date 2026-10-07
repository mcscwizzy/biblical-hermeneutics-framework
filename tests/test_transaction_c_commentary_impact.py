"""Integrity checks for Transaction C1's selective impact record."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPACT_PATH = ROOT / ".bhf-data/bhf-commentary-candidates/transaction-c-commentary-impact/impact-manifest.json"
RELEASE_ROOT = ROOT / ".bhf-data/bhf-commentary-v1.2"
SPEC_PATH = ROOT / "docs/superpowers/specs/2026-10-06-ckl-geography-commentary-selective-recompile.md"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_CANDIDATES = {
    "1 Samuel 17", "2 Kings 5", "Acts 27", "Genesis 13", "Genesis 34",
    "Isaiah 36", "John 4", "Joshua 6", "Judges 20", "Matthew 2",
    "Numbers 18", "Ruth 1",
}
EXPECTED_CONTROLS = {"Psalms 76", "Revelation 18", "Acts 16"}


def _impact() -> dict:
    return json.loads(IMPACT_PATH.read_text(encoding="utf-8"))


def test_c1_candidate_and_control_sets_are_exact():
    impact = _impact()
    assert set(impact["candidate_chapter_set"]) == EXPECTED_CANDIDATES
    assert len(impact["candidate_chapter_set"]) == 12
    assert set(impact["control_chapter_set"]) == EXPECTED_CONTROLS


def test_rendered_c1_table_contains_only_complete_lowercase_sha256_identities():
    lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| Reference | Old evidence hash"))
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 6:
            hashes = [value.strip("`") for value in cells[1:5]]
            assert len(hashes) == 4
            assert all(SHA256_RE.fullmatch(value) for value in hashes), line
            rows.append(cells[0])
    assert set(rows) == EXPECTED_CANDIDATES | EXPECTED_CONTROLS


def test_isaiah_36_published_baseline_hash_agrees_across_authoritative_sources():
    impact = _impact()
    impact_row = next(row for row in impact["chapters"] if row["reference"] == "Isaiah 36")
    release = json.loads((RELEASE_ROOT / ".bhf-commentary-release.json").read_text(encoding="utf-8"))
    release_row = next(row for row in release["chapter_publication_index"] if row["reference"] == "Isaiah 36")
    artifact = json.loads((RELEASE_ROOT / "isaiah_036.json").read_text(encoding="utf-8"))

    expected = "d0a416ef62843e2a5bfd6b7afbc00b28e47e21663011b89e638f79bfa31faedb"
    sources = [
        impact_row["old_identity"]["evidence_hash"],
        release_row["source_lineage"]["evidence_hash"],
        artifact["generated_metadata"]["evidence_hash"],
    ]
    assert all(SHA256_RE.fullmatch(value) for value in sources)
    assert sources == [expected] * 3


def test_controls_have_no_input_drift_and_are_not_candidates():
    impact = _impact()
    controls = {
        row["reference"]: row
        for row in impact["chapters"]
        if row["role"] == "control"
    }
    assert set(controls) == EXPECTED_CONTROLS
    for row in controls.values():
        assert row["candidate_required"] is False
        assert row["classification"] == "UNCHANGED"
        assert row["old_identity"]["evidence_hash"] == row["new_identity"]["evidence_hash"]
        assert row["old_identity"]["synthesis_hash"] == row["new_identity"]["synthesis_hash"]
