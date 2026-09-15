"""Focused tests for the immutable two-chapter prompt-1.7 omission audit."""

import hashlib
import json
from pathlib import Path

from tools import commentary_v12_two_chapter_omission_audit as audit


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_audit_is_deterministic_and_uses_immutable_namespace():
    first = audit.build_audit(REPO_ROOT)
    second = audit.build_audit(REPO_ROOT)

    assert first == second
    assert first["audit_id"] == "prompt-1.7-omission-audit-5166b2b6065bee070ee7"
    assert first["immutable_namespace"].endswith(first["audit_id"])
    expected_identity = hashlib.sha256(
        json.dumps(
            {key: value for key, value in first.items() if key != "audit_identity"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert first["audit_identity"] == expected_identity


def test_audit_covers_every_relevant_cluster_and_frozen_hashes():
    result = audit.build_audit(REPO_ROOT)
    chapters = {chapter["reference"]: chapter for chapter in result["chapters"]}

    assert len(chapters["1 Corinthians 14"]["eligible_idea_audit"]) == 7
    assert len(chapters["Revelation 21"]["eligible_idea_audit"]) == 16
    assert all(
        chapter["identities"]["evidence_hash"]
        and chapter["identities"]["synthesis_hash"]
        and chapter["structural_validation"]["validation_errors"] == []
        for chapter in chapters.values()
    )
    assert all(
        row["prompt_placement"]["synthesis_unit_ordinals"]
        for chapter in chapters.values()
        for row in chapter["eligible_idea_audit"]
    )


def test_audit_preserves_the_forensic_diagnosis_without_production_changes():
    result = audit.build_audit(REPO_ROOT)
    one_cor = result["cross_chapter_diagnosis"]["1 Corinthians 14"]
    rev21 = result["cross_chapter_diagnosis"]["Revelation 21"]

    assert one_cor["primary_cause"] == "POSSIBLE_SCORING_MISMATCH"
    assert rev21["primary_cause"] == "SYNTHESIS_PRESENTATION_WEAKNESS"
    assert result["recommendation"]["choice"] == "B"
    assert "no_prompt_1_8" in result["prohibited_actions_confirmed"]
    assert "no_scoring_change" in result["prohibited_actions_confirmed"]

