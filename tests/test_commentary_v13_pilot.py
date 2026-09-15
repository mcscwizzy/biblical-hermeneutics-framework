"""Focused deterministic tests for the Commentary 1.3 real-world pilot."""

import json
from collections import Counter

from tools.commentary_v13_pilot import (
    MANIFEST_PATH,
    ORIGINAL_CANARIES,
    PILOT_SELECTION,
    ROOT,
    calculate_packet_id,
    prepare,
    validate_selection,
)


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_selection_is_deterministic_and_excludes_original_canaries():
    validate_selection()
    first = [(book, chapter, category) for book, chapter, category, _ in PILOT_SELECTION]
    second = [(book, chapter, category) for book, chapter, category, _ in PILOT_SELECTION]
    assert first == second
    assert not {f"{book} {chapter}" for book, chapter, _, _ in PILOT_SELECTION}.intersection(ORIGINAL_CANARIES)


def test_pilot_literary_stratification_is_exact():
    expected = {
        "Pentateuch": 5,
        "Historical narrative": 5,
        "Poetry/Wisdom": 4,
        "Prophets": 5,
        "Gospels/Acts": 4,
        "Epistles": 4,
        "Apocalyptic / highly symbolic": 1,
        "Genealogy/list/administrative": 2,
    }
    assert Counter(category for _, _, category, _ in PILOT_SELECTION) == expected


def test_pilot_manifest_has_availability_and_all_density_buckets():
    artifact = prepare()
    assert artifact["status"] == "PILOT_PACKETS_READY"
    assert set(artifact["stratification_summary"]["availability_distribution"]) == {
        "AVAILABLE", "THIN", "DATA_GAP"
    }
    assert set(artifact["stratification_summary"]["density_distribution"]) == {
        "0", "1-5", "6-10", "11-20", "21-40", "41+"
    }


def test_every_pilot_packet_is_v13_reproducible_and_gate_v2_candidate_only():
    first = prepare()
    first_bytes = {
        row["reference"]: (ROOT / row["packet_path"]).read_bytes()
        for row in first["chapters"]
    }
    second = prepare()
    second_bytes = {
        row["reference"]: (ROOT / row["packet_path"]).read_bytes()
        for row in second["chapters"]
    }
    assert first_bytes == second_bytes
    assert first["chapters"] == second["chapters"]
    for row in second["chapters"]:
        packet = json.loads((ROOT / row["packet_path"]).read_text(encoding="utf-8"))
        assert packet["commentary_prompt_version"] == "1.3"
        assert packet["commentary_schema_version"] == "1.2"
        assert packet["packet_id"] == calculate_packet_id(packet)
        assert packet["gate_v2"]["status"] == "CANDIDATE_ONLY"
        assert row["status"] == "READY_FOR_EXTERNAL_RENDERER"


def test_pilot_integrity_and_renderer_boundary_are_explicit():
    prepare()
    manifest = _manifest()
    assert manifest["external_renderer_boundary"]["renderer_invoked"] is False
    assert manifest["integrity"]["v1_1_protected_fingerprints_unchanged"] is True
    assert manifest["integrity"]["ckl_unchanged"] is True
    assert manifest["integrity"]["evidence_locked"] is True
    assert manifest["integrity"]["synthesis_locked"] is True
    assert manifest["integrity"]["existing_canary_or_raw_artifacts_overwritten"] is False
    assert manifest["genesis_1_3"]["status"] == "RENDER_PENDING"
    assert manifest["bulk_authorization"]["full_bible_generation_authorized"] is False
