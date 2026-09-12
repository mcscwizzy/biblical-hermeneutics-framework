import hashlib
import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.release import release_chapter_state, release_diagnostics
from bhf_agent.runtime_paths import (
    DEFAULT_COMMENTARY_RELEASE,
    configured_commentary_release,
    default_commentary_storage_path,
)
from tools.commentary_v12_release_promotion import (
    DEFAULT_ARTIFACT,
    _row_is_publishable,
    verify_validation_artifact,
)


RELEASE_ROOT = Path(".bhf-data/bhf-commentary-v1.2")


def test_validation_intersection_is_calculated_from_per_chapter_records():
    info = verify_validation_artifact(DEFAULT_ARTIFACT)
    published = [row for row in info["population"] if _row_is_publishable(row)]

    assert len(published) == 62
    assert len(info["population"]) == 75
    assert {row["failure_classification"] for row in published} <= {
        None,
        "UNDER_EXPLANATION",
        "SOURCE_LIMITED",
    }


def test_packaged_v12_manifest_and_checksums_are_reader_safe():
    if not RELEASE_ROOT.is_dir():
        pytest.skip("the local release candidate has not been promoted")
    manifest = json.loads((RELEASE_ROOT / ".bhf-commentary-release.json").read_text())

    assert manifest["release"] == "commentary-v1.2"
    assert manifest["published_chapter_count"] == 62
    assert manifest["validated_population_count"] == 75
    assert manifest["unavailable_not_published_count"] == 13
    assert len(manifest["chapter_publication_index"]) == 75
    assert len(list(RELEASE_ROOT.glob("*.json"))) == 64
    assert release_diagnostics(RELEASE_ROOT, "commentary-v1.2")["checksum_status"] == "valid"


def test_v12_states_distinguish_rejected_and_outside_chapters():
    if not RELEASE_ROOT.is_dir():
        pytest.skip("the local release candidate has not been promoted")

    assert release_chapter_state(RELEASE_ROOT, "Romans", 3)["release_state"] == "MODEL_OUTPUT_REJECTED"
    assert release_chapter_state(RELEASE_ROOT, "Galatians", 3)["release_state"] == "QUALITY_REVIEW_REQUIRED"
    assert release_chapter_state(RELEASE_ROOT, "Genesis", 1)["release_state"] == "OUTSIDE_VALIDATED_V1_2_POPULATION"


def test_v12_is_opt_in_and_vercel_resolves_packaged_path():
    assert DEFAULT_COMMENTARY_RELEASE == "commentary-v1.1"
    assert configured_commentary_release({}) == "commentary-v1.1"
    assert configured_commentary_release({"BHF_COMMENTARY_RELEASE": "commentary-v1.2"}) == "commentary-v1.2"
    resolved = default_commentary_storage_path({"VERCEL": "1", "BHF_COMMENTARY_RELEASE": "commentary-v1.2"})
    assert resolved.name == "bhf-commentary-v1.2"
    assert "bhf-commentary-candidates" not in str(resolved)


def test_promotion_checksum_tampering_fails_closed(tmp_path):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    source = DEFAULT_ARTIFACT / "frozen-population.json"
    target = artifact / source.name
    target.write_bytes(source.read_bytes() + b"tamper")
    checksums = {"files": {source.name: hashlib.sha256(source.read_bytes()).hexdigest()}}
    (artifact / "checksums-v2.json").write_text(json.dumps(checksums))

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        verify_validation_artifact(artifact)
