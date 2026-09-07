"""Tests for canonical Commentary v1.1 runtime composition and release gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bhf_agent.bible import list_books
from bhf_agent.chapter_commentary.storage import get_commentary_filename
from bhf_agent.runtime_paths import packaged_commentary_storage_path
from framework.commentary.reconciliation import (
    ReconciliationError,
    SourceCandidate,
    canonical_chapter_references,
    reconcile_candidates,
    reconcile_release,
    load_validated_baseline,
    validate_runtime_reference_set,
)


ROOT = Path(__file__).resolve().parents[1]


def _payload(book: str, chapter: int, *, status: str = "validated", provenance: str = "baseline") -> dict:
    return {
        "reference": f"{book} {chapter}",
        "book": book,
        "chapter": chapter,
        "status": status,
        "evidence_availability": "THIN",
        "sections": [],
        "generated_metadata": {
            "evidence_hash": "e" * 64,
            "evidence_bundle_version": "1.0",
            "commentary_schema_version": "1.0",
            "commentary_prompt_version": "1.1",
            "model": "fixture",
        },
        "release_provenance": {"provenance": provenance},
    }


def _candidate(tmp_path: Path, book: str, chapter: int, *, provenance: str = "baseline") -> SourceCandidate:
    path = tmp_path / get_commentary_filename(book, chapter)
    path.write_text(json.dumps(_payload(book, chapter, provenance=provenance)), encoding="utf-8")
    return SourceCandidate(
        reference=f"{book} {chapter}",
        book=book,
        chapter=chapter,
        path=path,
        provenance=provenance,
        source_release="commentary-v1.1" if "v1.1" in provenance else "commentary-v1.0.1",
    )


def test_authoritative_canonical_inventory_has_1189_unique_references():
    references = canonical_chapter_references()
    assert len(references) == 1189
    assert len(set(references)) == 1189
    assert references[:3] == ("Genesis 1", "Genesis 2", "Genesis 3")
    assert references[-1] == "Revelation 22"
    assert sum(book["chapters"] for book in list_books()) == 1189


def test_actual_release_reconciles_genesis_exodus_and_leviticus_baseline_fallbacks():
    result = reconcile_release(ROOT)
    assert result.to_dict() == json.loads(
        (ROOT / "docs/commentary-v1.1-canonical-runtime-reconciliation.json").read_text()
    )
    assert result.canonical_total == 1189
    assert len(result.v1_1_certified) == 935
    assert len(result.baseline_fallback) == 254
    assert not result.missing
    assert not result.conflicts
    assert not result.invalid_source_records
    assert {"Genesis 1", "Exodus 1", "Leviticus 1"}.issubset(set(result.baseline_fallback))


def test_upgrade_completion_is_distinct_from_runtime_canonical_completion():
    from framework.commentary.orchestrator import status

    pipeline = status(ROOT)
    assert pipeline["upgrade_completion"] == {
        "status": "UPGRADE_CORPUS_COMPLETE",
        "completed": 935,
        "total": 935,
    }
    assert pipeline["runtime_completion"]["status"] == "RUNTIME_CANONICAL_COMPLETE"
    assert pipeline["runtime_completion"]["publishable"] == 1189


def test_v11_overrides_baseline_and_unselected_canonical_chapter_falls_back(tmp_path):
    canonical = ("Genesis 1", "Genesis 2")
    baseline = [_candidate(tmp_path, "Genesis", 1), _candidate(tmp_path, "Genesis", 2)]
    v11 = [_candidate(tmp_path, "Genesis", 1, provenance="certified Commentary v1.1")]
    result = reconcile_candidates(canonical, v11, baseline)
    assert result.selected_sources["Genesis 1"].provenance == "certified Commentary v1.1"
    assert result.selected_sources["Genesis 2"].provenance == "baseline"
    assert result.v1_1_certified == ("Genesis 1",)
    assert result.baseline_fallback == ("Genesis 2",)


def test_invalid_v11_record_cannot_override_validated_baseline(tmp_path):
    baseline = _candidate(tmp_path, "Genesis", 1)
    invalid_v11 = {"population": "v1.1", "reference": "Genesis 1", "reason": "source status is 'stale'"}
    result = reconcile_candidates(("Genesis 1",), (), (baseline,), [invalid_v11])
    assert result.selected_sources["Genesis 1"].provenance == "baseline"
    assert result.baseline_fallback == ("Genesis 1",)
    assert result.invalid_source_records == (invalid_v11,)


@pytest.mark.parametrize("status", ["partial", "needs_review", "failed", "stale", "generating"])
def test_unvalidated_baseline_records_are_not_publishable(tmp_path, monkeypatch, status):
    import framework.commentary.reconciliation as reconciliation_module

    relative = Path("baseline")
    monkeypatch.setattr(reconciliation_module, "BASELINE_RELATIVE_ROOT", relative)
    baseline = tmp_path / relative
    baseline.mkdir(parents=True)
    (baseline / "manifest.json").write_text(
        json.dumps({
            "release": "commentary-v1.0.1",
            "chapters_total": 1,
            "validation_summary": {"validated": 1, "partial": 0, "needs_review": 0, "failed": 0},
        }),
        encoding="utf-8",
    )
    (baseline / "genesis_001.json").write_text(
        json.dumps(_payload("Genesis", 1, status=status)), encoding="utf-8"
    )
    candidates, invalid = load_validated_baseline(tmp_path, ("Genesis 1",))
    assert not candidates
    assert any("source status" in row["reason"] for row in invalid)


def test_duplicate_canonical_references_fail_release_validation(tmp_path):
    first = _candidate(tmp_path, "Genesis", 1)
    second_path = tmp_path / "duplicate.json"
    second_path.write_text(first.path.read_text(), encoding="utf-8")
    second = SourceCandidate(
        reference="Genesis 1", book="Genesis", chapter=1, path=second_path,
        provenance="baseline", source_release="commentary-v1.0.1",
    )
    result = reconcile_candidates(("Genesis 1",), (), (first, second))
    assert result.conflicts == ("Genesis 1",)
    assert result.final_publishable_count == 0


@pytest.mark.parametrize(
    ("runtime", "expected"),
    [
        (["Genesis 1"], {"missing_canonical_refs": ["Genesis 2"], "unexpected_refs": [], "duplicate_refs": []}),
        (["Genesis 1", "Genesis 1", "Genesis 2"], {"missing_canonical_refs": [], "unexpected_refs": [], "duplicate_refs": ["Genesis 1"]}),
        (["Genesis 1", "Genesis 2", "Jubilees 1"], {"missing_canonical_refs": [], "unexpected_refs": ["Jubilees 1"], "duplicate_refs": []}),
    ],
)
def test_runtime_gate_compares_exact_reference_sets(runtime, expected):
    assert validate_runtime_reference_set(runtime, ("Genesis 1", "Genesis 2"), allow_partial=True) == expected
    with pytest.raises(ReconciliationError):
        validate_runtime_reference_set(runtime, ("Genesis 1", "Genesis 2"))


def test_runtime_package_has_exact_set_and_provenance_for_regression_chapters():
    storage = packaged_commentary_storage_path()
    manifest = json.loads((storage / "commentary-v1.1-manifest.json").read_text())
    references = [row["reference"] for row in manifest["chapters"]]
    validate_runtime_reference_set(references)
    assert manifest["chapter_count"] == 1189
    assert len(list(storage.glob("*.json"))) - 1 == 1189
    for reference in ("Genesis 1", "Exodus 1", "Leviticus 1"):
        row = next(row for row in manifest["chapters"] if row["reference"] == reference)
        assert row["provenance"] == "validated baseline fallback"
        record = json.loads((storage / row["filename"]).read_text())
        assert record["release_provenance"]["provenance"] == "validated baseline fallback"


def test_application_api_reports_genesis_exodus_and_leviticus_as_available():
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")
    from fastapi import FastAPI
    from bhf_web.routes.bhf_commentary import register_bhf_commentary_routes

    app = FastAPI()
    register_bhf_commentary_routes(app, storage_dir=packaged_commentary_storage_path())

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return [
                await client.get(f"/api/bhf-commentary/{book}/{chapter}")
                for book, chapter in (("Genesis", 1), ("Exodus", 1), ("Leviticus", 1))
            ]

    import asyncio

    responses = asyncio.run(request())
    assert all(response.status_code == 200 and response.json()["available"] for response in responses)


def test_protected_fingerprints_and_baseline_sources_remain_unchanged():
    state = json.loads((ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json").read_text())
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in state["protected_fingerprints"].items())
    for path in ("genesis_001.json", "exodus_001.json", "leviticus_001.json"):
        source = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.0.1" / path
        assert source.exists()
