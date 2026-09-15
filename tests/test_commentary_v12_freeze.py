"""Fail-closed verification tests for the immutable Commentary v1.2 release."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import tools.commentary_v12_freeze as freeze
from bhf_agent.chapter_commentary.release import release_diagnostics
from bhf_agent.chapter_commentary.storage import load_commentary
from framework.commentary.v12_corpus import V12CorpusRunner, V12FrozenReleaseError


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".bhf-data/bhf-commentary-v1.2"
DESCRIPTOR = ROOT / "docs/commentary-v1.2-release.json"


@pytest.fixture
def isolated_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    release = tmp_path / "release"
    descriptor = tmp_path / "commentary-v1.2-release.json"
    shutil.copytree(RELEASE, release)
    shutil.copy2(DESCRIPTOR, descriptor)
    monkeypatch.setattr(freeze, "RELEASE_ROOT", release)
    monkeypatch.setattr(freeze, "DESCRIPTOR", descriptor)
    return release


def test_frozen_release_verifies_exact_inventory(isolated_release: Path):
    result = freeze.verify_frozen_release()

    assert result["status"] == "COMMENTARY_V1_2_FROZEN_READY"
    assert result["canonical_chapters"] == 1189
    assert result["manifest_entries"] == 1189
    assert result["state_counts"] == {
        "MODEL_OUTPUT_REJECTED": 26,
        "NOT_RENDERABLE_SOURCE_LIMITED": 185,
        "PUBLISHED": 972,
        "QUALITY_REVIEW_REQUIRED": 6,
    }


def test_frozen_artifact_byte_mutation_fails_closed(isolated_release: Path):
    artifact = isolated_release / "genesis_001.json"
    artifact.write_bytes(artifact.read_bytes() + b"x")

    with pytest.raises(freeze.FrozenReleaseError, match="FROZEN_RELEASE_MUTATION_DETECTED"):
        freeze.verify_frozen_release()


def test_missing_published_artifact_fails_closed(isolated_release: Path):
    (isolated_release / "genesis_001.json").unlink()

    with pytest.raises(freeze.FrozenReleaseError, match="FROZEN_RELEASE_MUTATION_DETECTED"):
        freeze.verify_frozen_release()


@pytest.mark.parametrize("mutation", ["checksum", "duplicate", "unknown", "provenance", "ancestry"])
def test_release_identity_mutations_fail_closed(isolated_release: Path, mutation: str):
    manifest_path = isolated_release / ".bhf-commentary-release.json"
    manifest = json.loads(manifest_path.read_text())
    rows = manifest["chapter_publication_index"]
    if mutation == "checksum":
        checksums = json.loads((isolated_release / ".bhf-commentary-release-checksums.json").read_text())
        checksums["files"]["genesis_001.json"] = "0" * 64
        (isolated_release / ".bhf-commentary-release-checksums.json").write_text(json.dumps(checksums))
    elif mutation == "duplicate":
        rows[1]["reference"] = rows[0]["reference"]
    elif mutation == "unknown":
        rows[0]["release_state"] = "UNKNOWN"
    elif mutation == "provenance":
        next(row for row in rows if row.get("source") == "corpus-runner")["source_lineage"]["evidence_hash"] = "0" * 64
    else:
        next(row for row in rows if row.get("source") == "corpus-runner")["source_lineage"]["synthesis_hash"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(freeze.FrozenReleaseError, match="FROZEN_RELEASE_MUTATION_DETECTED"):
        freeze.verify_frozen_release()


def test_provider_absence_keeps_all_terminal_states_readable(monkeypatch: pytest.MonkeyPatch):
    for key in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST"):
        monkeypatch.delenv(key, raising=False)

    diagnostics = release_diagnostics(RELEASE, "commentary-v1.2")
    assert diagnostics["checksum_status"] == "valid"
    assert load_commentary(RELEASE, "Genesis", 1) is not None
    manifest = json.loads((RELEASE / ".bhf-commentary-release.json").read_text())
    states = {row["release_state"] for row in manifest["chapter_publication_index"]}
    assert states == {
        "PUBLISHED",
        "NOT_RENDERABLE_SOURCE_LIMITED",
        "MODEL_OUTPUT_REJECTED",
        "QUALITY_REVIEW_REQUIRED",
    }


def test_candidate_state_cannot_override_frozen_package(tmp_path: Path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "genesis_001.json").write_text('{"reference":"Genesis 1"}')

    result = freeze.verify_frozen_release()
    assert result["status"] == "COMMENTARY_V1_2_FROZEN_READY"
    assert load_commentary(RELEASE, "Genesis", 1) is not None


def test_normal_v12_generation_is_disabled_after_freeze():
    runner = V12CorpusRunner(ROOT)

    with pytest.raises(V12FrozenReleaseError, match="commentary-v1.2 is frozen"):
        runner.prepare()
    with pytest.raises(V12FrozenReleaseError, match="commentary-v1.2 is frozen"):
        runner.run()
