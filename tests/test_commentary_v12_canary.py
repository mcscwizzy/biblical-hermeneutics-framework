"""Safety gates for the bounded Commentary v1.2 canary matrix."""

import json
from pathlib import Path

from tools.commentary_v12_canary import (
    CANARY_REFERENCES,
    CANDIDATE_ROOT,
    ROOT,
    _read_json,
    prepare,
)


def test_canary_matrix_contains_every_required_torture_case_and_data_gap_control():
    required = {
        ("Genesis", 1), ("Leviticus", 16), ("Ruth", 3), ("Psalms", 1),
        ("1 Samuel", 21), ("1 Samuel", 28), ("2 Samuel", 6), ("2 Samuel", 24),
        ("1 Chronicles", 8), ("John", 1), ("Isaiah", 6), ("Revelation", 12),
        ("Numbers", 3),
    }
    assert required.issubset(set(CANARY_REFERENCES))


def test_canary_packets_are_exact_and_reproducible():
    first = prepare()
    first_packets = {
        row["reference"]: (ROOT / row["prompt_path"]).read_bytes()
        for row in first["chapters"]
    }
    second = prepare()
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


def test_provider_unavailable_blocks_before_prose_and_writes_no_candidates():
    from tools.commentary_v12_canary import generate

    prepare()
    artifact = generate()
    assert artifact["status"] == "BLOCKED_BEFORE_PROSE"
    assert artifact["blocker"] == "APPROVED_RENDERER_REQUIRED"
    assert artifact["renderer_invoked"] is False
    assert artifact["fallback_provider_used"] is False
    assert not list((CANDIDATE_ROOT / "canary/commentary").glob("*.json"))


def test_generation_manifest_has_candidate_paths_only():
    prepare()
    manifest = _read_json(CANDIDATE_ROOT / "canary/canary-generation-manifest.json")
    assert manifest["status"] == "READY_FOR_RENDERER"
    assert manifest["renderer_is_repository_adapter"] is False
    assert len(manifest["chapters"]) == len(CANARY_REFERENCES)
    assert all("commentary-v1.1" not in row["expected_response_path"] for row in manifest["chapters"])
    assert all(row["packet_id"].startswith("commentary-v1.2-packet:") for row in manifest["chapters"])
