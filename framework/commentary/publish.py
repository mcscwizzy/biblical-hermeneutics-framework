"""Publish the certified Commentary v1.1 corpus for runtime use.

This module is deliberately separate from generation and audit workspaces. It
only consumes protected, certified artifacts recorded by the completed
orchestrator state and writes an immutable runtime snapshot atomically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.runtime_paths import DEFAULT_COMMENTARY_RELEASE, packaged_commentary_storage_path
from framework.commentary.orchestrator import validate_state


SCALE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale")
ELIGIBLE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1")
MANIFEST_VERSION = "commentary-v1.1-runtime-manifest-v1"


class CertifiedCorpusError(RuntimeError):
    """Raised when publication cannot prove the certified corpus boundary."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CertifiedCorpusError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise CertifiedCorpusError(f"expected JSON object: {path}")
    return value


def _source_batch(relative_path: str) -> str:
    parts = Path(relative_path).parts
    for part in parts:
        if part.startswith("batch-") and part[6:].isdigit():
            return part
    if "commentary-v1.1-terra" in parts:
        return "canary"
    raise CertifiedCorpusError(f"protected artifact has no certified batch: {relative_path}")


def _validate_certified_sources(repo_root: Path, protected: dict[str, str], eligible: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_references: dict[str, str] = {}
    for relative_path, expected_hash in sorted(protected.items()):
        source = repo_root / relative_path
        if not source.is_file():
            raise CertifiedCorpusError(f"protected artifact is missing: {relative_path}")
        actual_hash = _sha256(source)
        if actual_hash != expected_hash:
            raise CertifiedCorpusError(f"protected fingerprint changed: {relative_path}")
        record = _read_json(source)
        reference = str(record.get("reference") or "").strip()
        if not reference:
            raise CertifiedCorpusError(f"protected artifact has no reference: {relative_path}")
        prior = seen_references.get(reference)
        if prior is not None:
            raise CertifiedCorpusError(f"duplicate protected chapter identity: {reference} ({prior}, {relative_path})")
        seen_references[reference] = relative_path
        if reference not in eligible:
            continue
        if record.get("status") != "validated":
            raise CertifiedCorpusError(f"eligible artifact is not validated: {reference}")
        if record.get("evidence_availability") not in {"AVAILABLE", "THIN"}:
            raise CertifiedCorpusError(f"eligible artifact has unsupported availability: {reference}")
        metadata = record.get("generated_metadata")
        if not isinstance(metadata, dict) or not str(metadata.get("evidence_hash") or ""):
            raise CertifiedCorpusError(f"eligible artifact has no evidence hash: {reference}")
        if load_commentary(source.parent, str(record["book"]), int(record["chapter"])) is None:
            raise CertifiedCorpusError(f"eligible artifact failed commentary schema deserialization: {reference}")
        rows.append(
            {
                "reference": reference,
                "book": str(record["book"]),
                "chapter": int(record["chapter"]),
                "filename": source.name,
                "source_certified_batch": _source_batch(relative_path),
                "prose_sha256": actual_hash,
                "evidence_hash": str(metadata["evidence_hash"]),
                "commentary_schema_version": str(metadata.get("commentary_schema_version") or ""),
                "commentary_prompt_version": str(metadata.get("commentary_prompt_version") or ""),
                "evidence_bundle_version": str(metadata.get("evidence_bundle_version") or ""),
                "_source_path": relative_path,
            }
        )
    return rows


def _load_certification(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], set[str]]:
    scale = repo_root / SCALE_ROOT
    state = _read_json(scale / "pipeline-state.json")
    if state.get("status") != "CORPUS_COMPLETE" or state.get("current_stage") != "CORPUS_COMPLETE":
        raise CertifiedCorpusError("Commentary v1.1 pipeline is not CORPUS_COMPLETE")
    errors = validate_state(repo_root, state)
    if errors:
        raise CertifiedCorpusError(f"orchestrator validation failed: {errors[:3]}")
    final = _read_json(scale / "final-corpus-certification.json")
    if final.get("status") != "CORPUS_COMPLETE" or final.get("protected_fingerprints_verified") is not True:
        raise CertifiedCorpusError("final corpus certification is not valid")
    eligible_artifact = _read_json(repo_root / ELIGIBLE_ROOT / "low-information-commentary.json")
    if eligible_artifact.get("availability_mutated") is not False:
        raise CertifiedCorpusError("eligible population artifact reports mutated availability")
    eligible = {str(value).strip() for value in eligible_artifact.get("chapters_evidence_supports_regeneration", []) if str(value).strip()}
    if not eligible:
        raise CertifiedCorpusError("eligible population is empty")
    if len(eligible) != int(state.get("eligible_corpus_total", 0)):
        raise CertifiedCorpusError("eligible population and pipeline state disagree")
    return state, final, eligible


def publish_certified_corpus(repo_root: str | Path = ".", output_dir: str | Path | None = None) -> dict[str, Any]:
    """Atomically publish the exact eligible subset of protected artifacts."""

    root = Path(repo_root).resolve()
    output = (root / packaged_commentary_storage_path(DEFAULT_COMMENTARY_RELEASE).relative_to(Path(__file__).resolve().parents[2])) if output_dir is None else (root / output_dir)
    output = output.resolve()
    if "bhf-commentary-candidates" in output.parts:
        raise CertifiedCorpusError("runtime publication cannot target a candidate workspace")
    state, certification, eligible = _load_certification(root)
    protected = state.get("protected_fingerprints")
    if not isinstance(protected, dict):
        raise CertifiedCorpusError("pipeline state has no protected fingerprints")
    rows = _validate_certified_sources(root, {str(k): str(v) for k, v in protected.items()}, eligible)
    if len(rows) != len(eligible) or len(rows) != int(state["eligible_finalized_chapters"]):
        raise CertifiedCorpusError(f"certified/runtime source accounting mismatch: {len(rows)} vs {len(eligible)}")
    rows.sort(key=lambda row: (row["book"].casefold(), row["chapter"], row["reference"]))
    corpus_fingerprint = hashlib.sha256(_canonical_json(rows)).hexdigest()
    if output.exists():
        raise CertifiedCorpusError(f"refusing to overwrite existing runtime corpus: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.publishing-", dir=output.parent))
    try:
        for row in rows:
            source_path = root / row.pop("_source_path")
            shutil.copyfile(source_path, staging / row["filename"])
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "corpus_version": "commentary-v1.1",
            "commentary_version": "1.1",
            "schema_version": "1.0",
            "prompt_version": "1.1",
            "chapter_count": len(rows),
            "chapters": rows,
            "corpus_fingerprint": corpus_fingerprint,
            "source_certification_artifact": str((root / SCALE_ROOT / "final-corpus-certification.json").relative_to(root)),
            "published_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "protected_fingerprint_count": len(protected),
            "certified_total": int(certification["total_certified"]),
            "eligible_total": int(certification["total_eligible_chapters"]),
        }
        (staging / "commentary-v1.1-manifest.json").write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the certified Commentary v1.1 runtime corpus")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    manifest = publish_certified_corpus(args.repo_root, args.output_dir)
    print(json.dumps({key: manifest[key] for key in ("manifest_version", "chapter_count", "corpus_fingerprint", "published_at")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
