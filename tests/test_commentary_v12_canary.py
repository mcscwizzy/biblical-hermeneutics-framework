"""Safety gates for the bounded Commentary v1.2 canary matrix."""

import json
from pathlib import Path

import pytest

import tools.commentary_v12_canary as canary
from tools.commentary_v12_canary import (
    CANARY_REFERENCES,
    CANDIDATE_ROOT,
    ROOT,
    _read_json,
    prepare,
)


@pytest.fixture
def isolated_candidate_state(tmp_path):
    """Keep canary authorization mutations outside the operational worktree."""

    path = tmp_path / "candidate-state.json"
    path.write_bytes((CANDIDATE_ROOT / "candidate-state.json").read_bytes())
    return path


def test_canary_matrix_contains_every_required_torture_case_and_data_gap_control():
    required = {
        ("Genesis", 1), ("Leviticus", 16), ("Ruth", 3), ("Psalms", 1),
        ("1 Samuel", 21), ("1 Samuel", 28), ("2 Samuel", 6), ("2 Samuel", 24),
        ("1 Chronicles", 8), ("John", 1), ("Isaiah", 6), ("Revelation", 12),
        ("Numbers", 3),
    }
    assert required.issubset(set(CANARY_REFERENCES))


def test_canary_packets_are_exact_and_reproducible(isolated_candidate_state):
    first = prepare(candidate_state_path=isolated_candidate_state)
    first_packets = {
        row["reference"]: (ROOT / row["prompt_path"]).read_bytes()
        for row in first["chapters"]
    }
    second = prepare(candidate_state_path=isolated_candidate_state)
    second_packets = {
        row["reference"]: (ROOT / row["prompt_path"]).read_bytes()
        for row in second["chapters"]
    }
    assert first_packets == second_packets
    assert first["chapters"] == second["chapters"]
    assert all(
        json.loads(packet)["commentary_prompt_version"] == "1.2"
        for packet in first_packets.values()
    )


def test_provider_unavailable_blocks_before_prose_and_writes_no_candidates(isolated_candidate_state):
    from tools.commentary_v12_canary import generate

    prepare(candidate_state_path=isolated_candidate_state)
    artifact = generate(candidate_state_path=isolated_candidate_state)
    assert artifact["status"] == "BLOCKED_BEFORE_PROSE"
    assert artifact["blocker"] == "APPROVED_RENDERER_REQUIRED"
    assert artifact["renderer_invoked"] is False
    assert artifact["fallback_provider_used"] is False
    assert not list((CANDIDATE_ROOT / "canary/commentary").glob("*.json"))


def test_generation_manifest_has_candidate_paths_only(isolated_candidate_state):
    prepare(candidate_state_path=isolated_candidate_state)
    manifest = _read_json(CANDIDATE_ROOT / "canary/canary-generation-manifest.json")
    assert manifest["status"] == "READY_FOR_RENDERER"
    assert manifest["renderer_is_repository_adapter"] is False
    assert len(manifest["chapters"]) == len(CANARY_REFERENCES)
    assert all("commentary-v1.1" not in row["expected_response_path"] for row in manifest["chapters"])
    assert all(row["packet_id"].startswith("commentary-v1.2-packet:") for row in manifest["chapters"])


def test_canary_authorization_state_is_unchanged_in_real_worktree(isolated_candidate_state):
    real_state = CANDIDATE_ROOT / "candidate-state.json"
    before = real_state.read_bytes()
    prepare(candidate_state_path=isolated_candidate_state)
    canary.generate(candidate_state_path=isolated_candidate_state)
    assert real_state.read_bytes() == before
