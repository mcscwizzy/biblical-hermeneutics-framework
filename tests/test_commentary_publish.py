import json
from pathlib import Path

import pytest

from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.runtime_paths import packaged_commentary_storage_path
from framework.commentary.publish import CertifiedCorpusError, publish_certified_corpus


ROOT = Path(__file__).resolve().parents[1]


def test_published_v11_manifest_reconciles_to_certified_runtime_corpus():
    storage = packaged_commentary_storage_path()
    manifest = json.loads((storage / "commentary-v1.1-manifest.json").read_text())

    chapter_files = [path for path in storage.glob("*.json") if path.name != "commentary-v1.1-manifest.json"]
    assert manifest["chapter_count"] == 1189
    assert len(chapter_files) == manifest["chapter_count"]
    assert manifest["eligible_total"] == 935
    assert manifest["v1_1_certified_count"] == 935
    assert manifest["baseline_fallback_count"] == 254
    assert manifest["runtime_completion_status"] == "RUNTIME_CANONICAL_COMPLETE"
    assert all(load_commentary(storage, row["book"], row["chapter"]) is not None for row in manifest["chapters"])
    assert all("bhf-commentary-candidates" not in row["filename"] for row in manifest["chapters"])


def test_publication_rejects_candidate_workspace_destination(tmp_path):
    with pytest.raises(CertifiedCorpusError, match="candidate workspace"):
        publish_certified_corpus(ROOT, tmp_path / "bhf-commentary-candidates")
