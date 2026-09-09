"""Focused contract tests for the isolated prompt 1.7 diagnostic."""

import hashlib
from pathlib import Path

from bhf_agent.chapter_commentary.models import (
    COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION,
)
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16,
    CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17,
    CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16,
    CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17,
    system_prompt_for_version,
)
from tools import commentary_renderer_selection_breadth_diagnostic as diagnostic


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_prompt_1_6_identity_and_literal_contract_remain_frozen():
    assert COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION == "1.6"
    assert system_prompt_for_version("1.6") == CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16
    assert _sha256(CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16) == (
        "befaadae050b039ee61d475fa7c8ddd2dfc4e3fc22bf85f93bb5efd571e2f52b"
    )
    assert _sha256(CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16) == (
        "95c667e14f0cbfb77fdbbf13c971f28fffa69bf673ac48cbd7dae7835d9737e8"
    )
    assert "distinct CORE" not in CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16
    assert "distinct CORE" not in CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16


def test_prompt_1_7_resolves_with_distinct_deterministic_identity():
    assert COMMENTARY_RENDERER_SELECTION_BREADTH_PROMPT_VERSION == "1.7"
    assert system_prompt_for_version("1.7") == CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17
    assert CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17 != CHAPTER_COMMENTARY_SYSTEM_PROMPT_V16
    assert CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17 != CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16
    assert _sha256(CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17) == (
        "cbe6a47cb9ec7b7186347aa3e25ff05d2b9387f72e6297ce0bce44515283f614"
    )
    assert _sha256(CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17) != _sha256(
        CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V16
    )


def test_prompt_1_7_retains_ancestry_provenance_and_no_dump_safeguards():
    for prompt in (CHAPTER_COMMENTARY_SYSTEM_PROMPT_V17, CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17):
        assert "evidence ancestry" in prompt
        assert "Do not invent" in prompt or "do not invent" in prompt
        assert "records" in prompt
        assert "no-dump" in prompt or "evidence inventory" in prompt
    assert "same-chapter membership does not establish ancestry compatibility" in (
        CHAPTER_COMMENTARY_USER_PROMPT_TEMPLATE_V17.lower()
    )


def test_prompt_version_selection_and_seven_case_manifest_are_deterministic():
    first, material_first = diagnostic.build_manifest(REPO_ROOT)
    second, material_second = diagnostic.build_manifest(REPO_ROOT)
    assert first == second
    assert len(material_first) == len(material_second) == 7
    assert first["diagnostic_id"].startswith("renderer-remediation-prompt-1.7-selection-breadth-")
    assert first["renderer"] == "gpt-5.6-sol"
    assert first["renderer_effort"] == "medium"
    assert first["contract_versions"]["renderer_prompt_version"] == "1.7"
    assert first["contract_versions"]["richness_policy_version"] == "commentary-richness-policy-v3-reader-relevance"
    assert first["contract_versions"]["gate_version"] == "commentary-richness-gate-v2.1"
    assert [row["reference"] for row in first["chapters"]] == list(diagnostic.EXPECTED_REFERENCES)
    assert first["chapter_count"] == 7
    assert all(row["evidence_hash"] and row["synthesis_hash"] for row in first["chapters"])
    assert all(row["source_packet_id"] for row in first["chapters"])


def test_prompt_1_7_manifest_verifier_rejects_wrong_corpus():
    manifest, _ = diagnostic.build_manifest(REPO_ROOT)
    altered = dict(manifest)
    altered["chapters"] = list(manifest["chapters"][:-1])
    altered["chapter_count"] = 6
    altered["manifest_identity"] = diagnostic.sha256_json(
        {key: value for key, value in altered.items() if key != "manifest_identity"}
    )
    try:
        diagnostic._verify_manifest(altered)
    except diagnostic.DiagnosticError as exc:
        assert "exactly seven" in str(exc)
    else:
        raise AssertionError("six-chapter diagnostic unexpectedly verified")
