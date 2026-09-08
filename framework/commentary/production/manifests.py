"""Immutable run and batch manifests for Commentary production."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

from .models import (
    AUTHORIZATION_STATUS,
    MANIFEST_STATUS,
    PRODUCTION_VERSION,
    InputIdentity,
    ManifestError,
    PreparedChapter,
    canonical_json,
    production_root,
    read_json,
    sha256_json,
    slug,
    write_json,
)


def _manifest_identity(value: dict[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "manifest_identity"}
    return sha256_json(payload)


def _row_for_manifest(prepared: PreparedChapter, *, run_id: str, batch_id: str) -> dict[str, Any]:
    row = dict(prepared.row)
    row["run_id"] = run_id
    row["batch_id"] = batch_id
    row["expected_artifacts"] = {
        "packet": f"runs/{run_id}/batches/{batch_id}/packets/{slug(row['book'], row['chapter'])}.json",
        "raw": f"runs/{run_id}/batches/{batch_id}/raw/attempt-001/{slug(row['book'], row['chapter'])}.json",
        "accepted": f"runs/{run_id}/batches/{batch_id}/accepted/attempt-001/{slug(row['book'], row['chapter'])}.json",
        "rejected": f"runs/{run_id}/batches/{batch_id}/rejected/attempt-001/{slug(row['book'], row['chapter'])}.json",
        "gate": f"runs/{run_id}/batches/{batch_id}/gate/attempt-001/{slug(row['book'], row['chapter'])}.json",
        "reader": f"runs/{run_id}/batches/{batch_id}/reader/attempt-001/{slug(row['book'], row['chapter'])}.json",
        "quarantine": f"runs/{run_id}/batches/{batch_id}/quarantine/attempt-001/{slug(row['book'], row['chapter'])}.json",
    }
    row["initial_state"] = "READY"
    row["input_identity"] = dict(row["input_identity"])
    row["packet_id"] = prepared.packet.get("packet_id")
    row["packet_hash"] = prepared.row["input_identity"]["packet_hash"]
    return row


def build_manifest(
    prepared_chapters: Iterable[PreparedChapter],
    *,
    batch_size: int = 25,
    run_id: str | None = None,
    status: str = MANIFEST_STATUS,
    generation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prepared = sorted(list(prepared_chapters), key=lambda item: int(item.row["canonical_ordinal"]))
    if not prepared:
        raise ManifestError("cannot create an empty production manifest")
    if batch_size <= 0:
        raise ManifestError("batch_size must be positive")
    references = [item.row["reference"] for item in prepared]
    if len(set(references)) != len(references):
        raise ManifestError("production manifest contains duplicate chapters")
    seed_payload = {
        "production_version": PRODUCTION_VERSION,
        "references": references,
        "input_identities": [item.row["input_identity"] for item in prepared],
        "batch_size": batch_size,
        "generation_config": generation_config or {},
    }
    computed_run_id = "run-" + hashlib.sha256(canonical_json(seed_payload).encode("utf-8")).hexdigest()[:16]
    run_id = run_id or computed_run_id
    chapters: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    for index in range(0, len(prepared), batch_size):
        batch_id = f"batch-{index // batch_size + 1:03d}"
        batch_rows = [_row_for_manifest(item, run_id=run_id, batch_id=batch_id) for item in prepared[index:index + batch_size]]
        batches.append({
            "batch_id": batch_id,
            "canonical_ordinals": [row["canonical_ordinal"] for row in batch_rows],
            "references": [row["reference"] for row in batch_rows],
            "chapter_count": len(batch_rows),
        })
        chapters.extend(batch_rows)
    manifest = {
        "artifact_version": "commentary-production-manifest-v1",
        "production_version": PRODUCTION_VERSION,
        "status": status,
        "run_id": run_id,
        "batch_size": batch_size,
        "ordering": "canonical Bible order by canonical_ordinal",
        "chapters": chapters,
        "batches": batches,
        "contract_versions": {
            "commentary_prompt_version": "1.5",
            "commentary_schema_version": "1.2",
            "synthesis_schema_version": "1.1",
            "synthesis_compiler_version": "1.1",
            "gate_version": "commentary-richness-gate-v2.1",
            "dense_reader_version": "commentary-dense-reader-v0.1",
        },
        "generation_config": generation_config or {},
        "historical_artifacts_are_not_promoted": True,
        "full_corpus_authorized": False,
    }
    manifest["manifest_identity"] = _manifest_identity(manifest)
    return manifest


def save_manifest(manifest: dict[str, Any], path: Path, *, immutable: bool = True) -> Path:
    expected = _manifest_identity(manifest)
    if manifest.get("manifest_identity") != expected:
        raise ManifestError("manifest identity does not match immutable content")
    write_json(path, manifest, immutable=immutable)
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict) or value.get("manifest_identity") != _manifest_identity(value):
        raise ManifestError(f"manifest identity mismatch: {path}")
    if value.get("production_version") != PRODUCTION_VERSION:
        raise ManifestError("unsupported production orchestration version")
    references = [row.get("reference") for row in value.get("chapters", [])]
    if len(references) != len(set(references)):
        raise ManifestError("manifest chapter membership is not unique")
    return value


def batch_manifest(manifest: dict[str, Any], batch_id: str) -> dict[str, Any]:
    rows = [row for row in manifest["chapters"] if row.get("batch_id") == batch_id]
    if not rows:
        raise ManifestError(f"unknown or empty production batch: {batch_id}")
    result = {
        "artifact_version": "commentary-production-batch-manifest-v1",
        "production_version": manifest["production_version"],
        "run_id": manifest["run_id"],
        "batch_id": batch_id,
        "status": manifest["status"],
        "manifest_identity": manifest["manifest_identity"],
        "chapters": rows,
        "contract_versions": manifest["contract_versions"],
        "generation_config": manifest.get("generation_config", {}),
    }
    result["batch_manifest_identity"] = sha256_json(result)
    return result


def save_batch_manifests(manifest: dict[str, Any], repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for batch in manifest["batches"]:
        batch_id = batch["batch_id"]
        path = production_root(repo_root) / "runs" / manifest["run_id"] / "batches" / batch_id / "manifest.json"
        write_json(path, batch_manifest(manifest, batch_id), immutable=True)
        paths.append(path)
    return paths
