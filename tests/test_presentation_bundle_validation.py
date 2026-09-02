from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bhf_agent.presentation import (
    PresentationBundleError,
    build_evidence_bundle,
    build_presentation_bundle,
    deterministic_presentation,
    inspect_presentation_bundle,
)
from bhf_agent.presentation.fallback import DETERMINISTIC_PROMPT_VERSION


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "validate_presentation_bundle.py"


def _write_bundle(path: Path) -> dict[str, object]:
    evidence = build_evidence_bundle(
        "Mark 5:1",
        geography={
            "places": [
                {
                    "id": "gerasa",
                    "title": "Gerasa",
                    "summary": "Gerasa lies east of the Sea of Galilee.",
                    "confidence": "likely",
                }
            ],
            "routes": [],
        },
    )
    packet = deterministic_presentation(evidence).to_dict()
    bundle = build_presentation_bundle([packet])
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return packet


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_inspection_reports_metadata_without_card_content(tmp_path):
    path = tmp_path / "presentation-bundle.json"
    packet = _write_bundle(path)

    result = inspect_presentation_bundle(path, require_packets=True)
    summary = result.to_dict()

    assert result.packet_count == 1
    assert result.prompt_versions == (DETERMINISTIC_PROMPT_VERSION,)
    assert result.models == ("deterministic",)
    assert packet["cards"][0]["body"] not in json.dumps(summary)


def test_inspection_can_enforce_prompt_and_model_metadata(tmp_path):
    path = tmp_path / "presentation-bundle.json"
    _write_bundle(path)

    inspect_presentation_bundle(
        path,
        expected_prompt_version=DETERMINISTIC_PROMPT_VERSION,
        expected_model="deterministic",
    )
    with pytest.raises(PresentationBundleError, match="prompt version"):
        inspect_presentation_bundle(path, expected_prompt_version="provider-v2")
    with pytest.raises(PresentationBundleError, match="model"):
        inspect_presentation_bundle(path, expected_model="different-model")


def test_validation_cli_reports_valid_bundle_as_json(tmp_path):
    path = tmp_path / "presentation-bundle.json"
    _write_bundle(path)

    completed = _run(
        "--bundle",
        str(path),
        "--expect-prompt-version",
        DETERMINISTIC_PROMPT_VERSION,
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["valid"] is True
    assert report["packet_count"] == 1
    assert report["prompt_versions"] == [DETERMINISTIC_PROMPT_VERSION]


def test_validation_cli_fails_closed_for_invalid_or_empty_bundle(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{}", encoding="utf-8")
    invalid = _run("--bundle", str(invalid_path), "--json")

    assert invalid.returncode == 1
    assert json.loads(invalid.stdout)["valid"] is False

    empty_path = tmp_path / "empty.json"
    empty_path.write_text(
        json.dumps(build_presentation_bundle([])),
        encoding="utf-8",
    )
    empty = _run("--bundle", str(empty_path))
    allowed = _run("--bundle", str(empty_path), "--allow-empty")

    assert empty.returncode == 1
    assert "contains no packets" in empty.stderr
    assert allowed.returncode == 0
