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
from pathlib import Path
from typing import Any

from bhf_agent.runtime_paths import DEFAULT_COMMENTARY_RELEASE, packaged_commentary_storage_path
from framework.commentary.orchestrator import validate_state
from framework.commentary.reconciliation import (
    CANONICAL_RUNTIME_STATUS,
    ReconciliationError,
    UPGRADE_POPULATION_STATUS,
    canonical_inventory_fingerprint,
    reconcile_release,
    validate_runtime_reference_set,
)


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


def publish_certified_corpus(
    repo_root: str | Path = ".",
    output_dir: str | Path | None = None,
    *,
    replace_existing: bool = False,
) -> dict[str, Any]:
    """Atomically publish the canonical baseline/v1.1 overlay.

    The v1.1 eligible population is intentionally not treated as the complete
    runtime corpus.  Existing output is replaced only when explicitly requested
    by the release operation; source populations remain immutable.
    """

    root = Path(repo_root).resolve()
    output = (root / packaged_commentary_storage_path(DEFAULT_COMMENTARY_RELEASE).relative_to(Path(__file__).resolve().parents[2])) if output_dir is None else (root / output_dir)
    output = output.resolve()
    if "bhf-commentary-candidates" in output.parts:
        raise CertifiedCorpusError("runtime publication cannot target a candidate workspace")
    state, certification, eligible = _load_certification(root)
    protected = state.get("protected_fingerprints")
    if not isinstance(protected, dict):
        raise CertifiedCorpusError("pipeline state has no protected fingerprints")
    try:
        reconciliation = reconcile_release(root)
    except ReconciliationError as exc:
        raise CertifiedCorpusError(str(exc)) from exc
    if reconciliation.invalid_source_records:
        raise CertifiedCorpusError(
            "canonical reconciliation found invalid source records: "
            + json.dumps(list(reconciliation.invalid_source_records[:3]), ensure_ascii=False)
        )
    if reconciliation.conflicts:
        raise CertifiedCorpusError(f"canonical reconciliation found conflicts: {list(reconciliation.conflicts[:5])}")
    if reconciliation.missing:
        raise CertifiedCorpusError(f"canonical reconciliation found missing chapters: {list(reconciliation.missing[:5])}")
    if len(reconciliation.v1_1_certified) != len(eligible):
        raise CertifiedCorpusError(
            "certified upgrade accounting mismatch: "
            f"{len(reconciliation.v1_1_certified)} vs {len(eligible)}"
        )
    try:
        validate_runtime_reference_set(reconciliation.selected_sources)
    except ReconciliationError as exc:
        raise CertifiedCorpusError(str(exc)) from exc

    rows: list[dict[str, Any]] = []
    for reference in reconciliation.canonical_references:
        candidate = reconciliation.selected_sources[reference]
        record = _read_json(candidate.path)
        metadata = record.get("generated_metadata") or {}
        relative_source = candidate.path.relative_to(root).as_posix()
        rows.append(
            {
                "reference": candidate.reference,
                "book": candidate.book,
                "chapter": candidate.chapter,
                "filename": candidate.path.name,
                "provenance": candidate.provenance,
                "source_release": candidate.source_release,
                "source_path": relative_source,
                "source_certified_batch": candidate.source_certified_batch,
                "prose_sha256": candidate.sha256,
                "evidence_hash": str(metadata.get("evidence_hash") or ""),
                "commentary_schema_version": str(metadata.get("commentary_schema_version") or ""),
                "commentary_prompt_version": str(metadata.get("commentary_prompt_version") or ""),
                "evidence_bundle_version": str(metadata.get("evidence_bundle_version") or ""),
            }
        )
    corpus_fingerprint = hashlib.sha256(_canonical_json(rows)).hexdigest()
    if output.exists() and not replace_existing:
        raise CertifiedCorpusError(f"refusing to overwrite existing runtime corpus: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.publishing-", dir=output.parent))
    try:
        for row in rows:
            source_path = root / row["source_path"]
            # Runtime metadata exposes provenance without rewriting prose or
            # mutating either immutable source population.
            runtime_record = _read_json(source_path)
            runtime_record["release_provenance"] = {
                "provenance": row["provenance"],
                "source_release": row["source_release"],
                "source_path": row["source_path"],
            }
            (staging / row["filename"]).write_bytes(
                json.dumps(runtime_record, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
            )
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "corpus_version": "commentary-v1.1",
            "commentary_version": "1.1",
            "schema_version": "1.0",
            "prompt_version": "1.1",
            "completion_scope": "canonical_runtime",
            "upgrade_completion_status": UPGRADE_POPULATION_STATUS,
            "runtime_completion_status": CANONICAL_RUNTIME_STATUS,
            "canonical_total": reconciliation.canonical_total,
            "canonical_inventory_fingerprint": canonical_inventory_fingerprint(reconciliation.canonical_references),
            "chapter_count": len(rows),
            "chapters": rows,
            "corpus_fingerprint": corpus_fingerprint,
            "source_certification_artifact": str((root / SCALE_ROOT / "final-corpus-certification.json").relative_to(root)),
            # The source state timestamp keeps repeated builds byte-stable.
            "published_at": str(state.get("updated_at") or ""),
            "protected_fingerprint_count": len(protected),
            "certified_total": int(certification["total_certified"]),
            "eligible_total": int(certification["total_eligible_chapters"]),
            "v1_1_certified_count": len(reconciliation.v1_1_certified),
            "baseline_fallback_count": len(reconciliation.baseline_fallback),
            "missing_count": len(reconciliation.missing),
            "conflict_count": len(reconciliation.conflicts),
            "invalid_source_count": len(reconciliation.invalid_source_records),
            "final_publishable_count": reconciliation.final_publishable_count,
        }
        (staging / "commentary-v1.1-manifest.json").write_bytes(json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        if output.exists():
            previous = output.parent / f".{output.name}.previous"
            if previous.exists():
                shutil.rmtree(previous)
            os.replace(output, previous)
            try:
                os.replace(staging, output)
            except Exception:
                os.replace(previous, output)
                raise
            shutil.rmtree(previous)
        else:
            os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the certified Commentary v1.1 runtime corpus")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir")
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args()
    manifest = publish_certified_corpus(args.repo_root, args.output_dir, replace_existing=args.replace_existing)
    print(json.dumps({key: manifest[key] for key in ("manifest_version", "chapter_count", "corpus_fingerprint", "published_at")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
