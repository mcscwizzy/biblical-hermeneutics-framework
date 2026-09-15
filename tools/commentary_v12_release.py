#!/usr/bin/env python3
"""Reconcile and promote the finalized Commentary v1.2 corpus.

This command is deliberately a packaging-only operation.  It consumes the
validated historical 75-chapter release and finalized corpus-runner receipts;
it has no model, renderer, prompt, or provider dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RELEASE = "commentary-v1.2"
RELEASE_ROOT = ROOT / ".bhf-data/bhf-commentary-v1.2"
RUNNER_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/corpus-runner"
HISTORICAL_ARTIFACT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2"
MANIFEST_NAME = ".bhf-commentary-release.json"
CHECKSUMS_NAME = ".bhf-commentary-release-checksums.json"
TERMINAL_STATES = {
    "PUBLISHED",
    "NOT_RENDERABLE_SOURCE_LIMITED",
    "MODEL_OUTPUT_REJECTED",
    "QUALITY_REVIEW_REQUIRED",
}
CLASSIFICATIONS = {"published", "source-limited", "model-rejected", "quality-review"}
RESULT_STATES = {"validated", "partial", "needs_review", "failed", "stale"}


class ReconciliationError(RuntimeError):
    """Raised when a release invariant cannot be proven."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"invalid JSON: {path}") from exc


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ReconciliationError(f"cannot read: {path}") from exc


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reference(row: dict[str, Any]) -> str:
    return f"{row['book']} {int(row['chapter'])}"


def _slug(row: dict[str, Any]) -> str:
    return f"{str(row['book']).lower().replace(' ', '_')}_{int(row['chapter']):03d}"


def _check_index(root: Path) -> None:
    index = _read(root / CHECKSUMS_NAME)
    files = index.get("files") if isinstance(index, dict) else None
    if not isinstance(files, dict):
        raise ReconciliationError("release checksum index is malformed")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ReconciliationError("release checksum index contains malformed data")
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise ReconciliationError(f"release checksum mismatch: {relative}")


def _validate_existing_release(canonical: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    manifest = _read(RELEASE_ROOT / MANIFEST_NAME)
    if manifest.get("release") != RELEASE:
        raise ReconciliationError("existing package has the wrong release identity")
    identity = manifest.get("manifest_identity")
    unsigned = dict(manifest)
    unsigned.pop("manifest_identity", None)
    if not isinstance(identity, str) or _sha256_json(unsigned) != identity:
        raise ReconciliationError("existing v1.2 manifest identity mismatch")
    _check_index(RELEASE_ROOT)
    rows = manifest.get("chapter_publication_index")
    full_reconciliation = manifest.get("reconciliation_version") == "commentary-v1.2-corpus-reconciliation-v1"
    expected_population = 1189 if full_reconciliation else 75
    if not isinstance(rows, list) or len(rows) != expected_population:
        raise ReconciliationError(f"existing v1.2 package is not the expected {expected_population}-chapter population")
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ReconciliationError("existing package contains a non-object chapter row")
        ref = _reference(row)
        if ref not in canonical or ref in records:
            raise ReconciliationError(f"invalid or duplicate existing package identity: {ref}")
        state = row.get("release_state")
        if state not in TERMINAL_STATES or row.get("validated") is not True:
            raise ReconciliationError(f"existing package has non-terminal state: {ref}")
        if state == "PUBLISHED":
            filename = row.get("filename")
            if not isinstance(filename, str) or filename != _slug(row) + ".json":
                raise ReconciliationError(f"existing package filename mismatch: {ref}")
            artifact = RELEASE_ROOT / filename
            if not artifact.is_file() or _sha256(artifact) != _read(RELEASE_ROOT / CHECKSUMS_NAME)["files"].get(filename):
                raise ReconciliationError(f"existing package artifact mismatch: {ref}")
            data = _read(artifact)
            if data.get("reference") != ref or data.get("book") != row["book"] or int(data.get("chapter", -1)) != int(row["chapter"]):
                raise ReconciliationError(f"existing package artifact identity mismatch: {ref}")
            row = {**row, "artifact_sha256": _sha256(artifact)}
        records[ref] = dict(row)
    published_files = {row.get("filename") for row in rows if row.get("release_state") == "PUBLISHED"}
    actual_files = {path.name for path in RELEASE_ROOT.glob("*.json") if path.name not in {MANIFEST_NAME, CHECKSUMS_NAME}}
    if actual_files != published_files:
        raise ReconciliationError("existing package has orphan or missing published artifacts")
    return records, manifest


def _effective_audits(result_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    audits = result.get("audits")
    if not isinstance(audits, dict):
        sidecar = result_path.parent / "finalize-audit.json"
        audits = _read(sidecar) if sidecar.is_file() else {}
    return audits if isinstance(audits, dict) else {}


def _validate_audits(reference: str, audits: dict[str, Any]) -> None:
    for key in ("ancestry", "provenance_binding", "envelope"):
        item = audits.get(key)
        if not isinstance(item, dict) or item.get("valid") is not True:
            raise ReconciliationError(f"{reference}: {key} audit did not pass")
    envelope = audits["envelope"].get("ancestry_audit", {})
    if envelope.get("invented_evidence_ids") or envelope.get("invented_synthesis_ids"):
        raise ReconciliationError(f"{reference}: provenance envelope invented an identity")


def _validate_runner_result(
    result_path: Path,
    canonical: dict[str, dict[str, Any]],
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = _read(result_path)
    if not isinstance(result, dict) or result.get("artifact_version") != "commentary-v1.2-corpus-result-v1":
        raise ReconciliationError(f"invalid corpus result: {result_path}")
    ref = result.get("reference")
    if not isinstance(ref, str) or ref not in canonical:
        raise ReconciliationError(f"invalid canonical identity in result: {result_path}")
    if ref in records:
        raise ReconciliationError(f"conflicting finalized results: {ref}")
    expected = canonical[ref]
    if result.get("book") != expected["book"] or int(result.get("chapter", -1)) != int(expected["chapter"]):
        raise ReconciliationError(f"result identity mismatch: {ref}")
    status = result.get("status")
    classification = result.get("classification")
    if status not in RESULT_STATES or classification not in CLASSIFICATIONS:
        raise ReconciliationError(f"unknown terminal state: {ref}")
    state_root = result_path.parents[2]
    manifest_path = state_root / "manifest.json"
    state_path = state_root / "state.json"
    manifest = _read(manifest_path)
    state = _read(state_path)
    if manifest.get("pipeline_version") != "commentary-v1.2-enrichment" or manifest.get("artifact_version") != "commentary-v1.2-corpus-session-manifest-v1":
        raise ReconciliationError(f"wrong corpus-runner contract: {ref}")
    if state.get("manifest_sha256") != _sha256(manifest_path) or state.get("finalized") is not True:
        raise ReconciliationError(f"unfinalized or changed corpus session: {ref}")
    entries = [entry for entry in manifest.get("chapters", []) if entry.get("reference") == ref]
    if len(entries) != 1 or entries[0].get("book") != expected["book"] or int(entries[0].get("chapter", -1)) != int(expected["chapter"]):
        raise ReconciliationError(f"session manifest identity mismatch: {ref}")
    chapter_root = result_path.parent
    expected_result_path = f"chapters/{chapter_root.name}/result.json"
    chapter_state = state.get("chapters", {}).get(ref, {})
    if chapter_state.get("status") != status or chapter_state.get("result_path") != expected_result_path:
        raise ReconciliationError(f"session state/result disagreement: {ref}")
    finalize_reports = [_read(path) for path in state_root.glob("finalize*.json")]
    if not any(report.get("status") == "FINALIZED" and any(item.get("reference") == ref for item in report.get("chapters", [])) for report in finalize_reports):
        raise ReconciliationError(f"missing finalization receipt: {ref}")

    result_hash = _sha256(result_path)
    raw_path_value = result.get("raw_response_path")
    raw_path = ROOT / raw_path_value if isinstance(raw_path_value, str) else chapter_root / "raw-response.bin"
    if classification == "source-limited":
        if status != "validated" or result.get("release_state") != "NOT_RENDERABLE_SOURCE_LIMITED" or result.get("commentary_path") is not None or raw_path_value is not None:
            raise ReconciliationError(f"invalid source-limited receipt: {ref}")
    else:
        if not raw_path.is_file():
            raise ReconciliationError(f"missing renderer output: {ref}")
        raw_hash = _sha256(raw_path)
        if result.get("raw_response_sha256") not in (None, raw_hash):
            raise ReconciliationError(f"raw response checksum mismatch: {ref}")
        renderer_receipt = chapter_root / "renderer-receipt.json"
        if renderer_receipt.is_file():
            receipt = _read(renderer_receipt)
            for key, value in (("reference", ref), ("book", expected["book"]), ("chapter", int(expected["chapter"])), ("run_id", state_root.name), ("requested_model", "gpt-5.6-terra"), ("requested_effort", "high"), ("raw_response_sha256", raw_hash)):
                if receipt.get(key) != value:
                    raise ReconciliationError(f"renderer receipt mismatch: {ref}")

    artifact_hash = None
    commentary_path_value = result.get("commentary_path")
    if classification in {"published", "quality-review"}:
        if not isinstance(commentary_path_value, str) or Path(commentary_path_value).parts[:1] != ("chapters",):
            raise ReconciliationError(f"missing finalized commentary artifact: {ref}")
        commentary_path = state_root / commentary_path_value
        if commentary_path != chapter_root / "commentary.json" or not commentary_path.is_file():
            raise ReconciliationError(f"commentary artifact path mismatch: {ref}")
        commentary = _read(commentary_path)
        if commentary.get("reference") != ref or commentary.get("book") != expected["book"] or int(commentary.get("chapter", -1)) != int(expected["chapter"]):
            raise ReconciliationError(f"commentary artifact identity mismatch: {ref}")
        if classification == "published" and status != "validated":
            raise ReconciliationError(f"published result is not validated: {ref}")
        metadata = commentary.get("generated_metadata", {})
        if metadata.get("commentary_schema_version") != "1.2" or metadata.get("commentary_prompt_version") != "1.8" or metadata.get("model") != "gpt-5.6-terra":
            raise ReconciliationError(f"commentary source contract mismatch: {ref}")
        audits = _effective_audits(result_path, result)
        _validate_audits(ref, audits)
        binding = result.get("binding_metadata", {})
        input_metadata_path = chapter_root / "renderer-input/metadata.json"
        input_metadata = _read(input_metadata_path) if input_metadata_path.is_file() else {}
        for key in ("evidence_hash", "synthesis_hash"):
            if metadata.get(key) != input_metadata.get(key):
                raise ReconciliationError(f"source lineage mismatch: {ref} {key}")
        if binding.get("binding_hash") != input_metadata.get("binding_hash"):
            raise ReconciliationError(f"provenance binding mismatch: {ref}")
        artifact_hash = _sha256(commentary_path)
    elif classification == "model-rejected":
        if result.get("release_state") not in (None, "MODEL_OUTPUT_REJECTED") or result.get("commentary_path") is not None:
            raise ReconciliationError(f"invalid model-rejected receipt: {ref}")

    public_state = {
        "published": "PUBLISHED",
        "source-limited": "NOT_RENDERABLE_SOURCE_LIMITED",
        "model-rejected": "MODEL_OUTPUT_REJECTED",
        "quality-review": "QUALITY_REVIEW_REQUIRED",
    }[classification]
    row = {
        "reference": ref,
        "book": expected["book"],
        "chapter": int(expected["chapter"]),
        "canonical_ordinal": expected["canonical_ordinal"],
        "release_state": public_state,
        "reason": {
            "PUBLISHED": "published",
            "NOT_RENDERABLE_SOURCE_LIMITED": "commentary_source_limited",
            "MODEL_OUTPUT_REJECTED": "commentary_model_output_rejected",
            "QUALITY_REVIEW_REQUIRED": "commentary_quality_review_required",
        }[public_state],
        "validated": True,
        "corpus_runner_result": str(result_path.relative_to(ROOT)),
        "result_sha256": result_hash,
        "source_lineage": {
            "evidence_hash": result.get("evidence_hash") or (_read(chapter_root / "commentary.json").get("generated_metadata", {}).get("evidence_hash") if (chapter_root / "commentary.json").is_file() else None),
            "synthesis_hash": result.get("synthesis_hash") or (_read(chapter_root / "commentary.json").get("generated_metadata", {}).get("synthesis_hash") if (chapter_root / "commentary.json").is_file() else None),
        },
    }
    if artifact_hash:
        row["artifact_sha256"] = artifact_hash
        if classification == "published":
            row["filename"] = _slug(expected) + ".json"
    if raw_path.is_file():
        row["raw_response_sha256"] = _sha256(raw_path)
    records[ref] = row
    return row


def build_reconciliation_inventory() -> dict[str, Any]:
    """Perform the complete read-only scan used by promotion."""
    from framework.commentary.production.census import canonical_chapters
    from tools.commentary_v12_release_promotion import verify_validation_artifact, _row_is_publishable

    canonical_rows = canonical_chapters()
    canonical = {_reference(row): row for row in canonical_rows}
    if len(canonical) != 1189:
        raise ReconciliationError(f"canonical inventory is not 1189 chapters: {len(canonical)}")
    historical_info = verify_validation_artifact(HISTORICAL_ARTIFACT)
    historical, historical_manifest = _validate_existing_release(canonical)
    if historical_manifest.get("reconciliation_version") == "commentary-v1.2-corpus-reconciliation-v1":
        runner: dict[str, dict[str, Any]] = {}
        result_paths = sorted(RUNNER_ROOT.glob("runs/*/chapters/*/result.json"))
        for result_path in result_paths:
            _validate_runner_result(result_path, canonical, runner)
        for ref, runner_row in runner.items():
            if historical.get(ref, {}).get("release_state") != runner_row.get("release_state"):
                raise ReconciliationError(f"promoted package disagrees with corpus-runner state: {ref}")
            # Rebuild runner-backed rows from immutable receipts so an
            # idempotent rerun also applies corrected inventory fields.
            historical[ref] = {**runner_row, "source": "corpus-runner"}
        counts = Counter(row["release_state"] for row in historical.values())
        rows = []
        for ref in sorted(canonical, key=lambda value: canonical[value]["canonical_ordinal"]):
            row = dict(historical[ref])
            row["canonical_ordinal"] = canonical[ref]["canonical_ordinal"]
            rows.append(row)
        return {
            "canonical": canonical_rows,
            "historical_manifest": historical_manifest,
            "rows": rows,
            "runner_result_count": len(runner),
            "counts": dict(sorted(counts.items())),
            "result_paths": result_paths,
        }
    by_historical = {row["reference"]: row for row in historical_info["population"]}
    for ref, row in historical.items():
        source_row = by_historical.get(ref)
        expected_state = "PUBLISHED" if source_row and _row_is_publishable(source_row) else source_row and ("NOT_RENDERABLE_SOURCE_LIMITED" if source_row.get("failure_classification") == "NOT_RENDERABLE_SOURCE_LIMITED" or not source_row.get("generated") else "MODEL_OUTPUT_REJECTED" if source_row.get("structural_result") != "ACCEPTED" else "QUALITY_REVIEW_REQUIRED")
        if row.get("release_state") != expected_state:
            raise ReconciliationError(f"historical package mismatch: {ref}")
    runner: dict[str, dict[str, Any]] = {}
    result_paths = sorted(RUNNER_ROOT.glob("runs/*/chapters/*/result.json"))
    for result_path in result_paths:
        _validate_runner_result(result_path, canonical, runner)
    if set(historical) & set(runner):
        raise ReconciliationError("historical package and corpus-runner results overlap")
    if set(historical) | set(runner) != set(canonical):
        missing = sorted(set(canonical) - set(historical) - set(runner))
        raise ReconciliationError("missing finalized corpus results: " + ", ".join(missing))
    rows = []
    for ref in sorted(canonical, key=lambda value: canonical[value]["canonical_ordinal"]):
        if ref in historical:
            row = dict(historical[ref])
            row["canonical_ordinal"] = canonical[ref]["canonical_ordinal"]
            row["source"] = "historical-75-release"
        else:
            row = dict(runner[ref])
            row["source"] = "corpus-runner"
        rows.append(row)
    counts = Counter(row["release_state"] for row in rows)
    return {
        "canonical": canonical_rows,
        "historical_manifest": historical_manifest,
        "rows": rows,
        "runner_result_count": len(runner),
        "counts": dict(sorted(counts.items())),
        "result_paths": result_paths,
    }


def _release_manifest(inventory: dict[str, Any], corpus_files: dict[str, str]) -> dict[str, Any]:
    historical_manifest = inventory["historical_manifest"]
    rows = inventory["rows"]
    counts = inventory["counts"]
    manifest: dict[str, Any] = {
        "release": RELEASE,
        "release_scope": "full_corpus_reconciliation_candidate",
        "reconciliation_version": "commentary-v1.2-corpus-reconciliation-v1",
        "canonical_chapter_count": len(rows),
        "validated_population_count": len(rows),
        "published_chapter_count": counts.get("PUBLISHED", 0),
        "unavailable_not_published_count": len(rows) - counts.get("PUBLISHED", 0),
        "terminal_state_counts": counts,
        "chapter_publication_index": rows,
        "historical_release_manifest_identity": historical_manifest.get("manifest_identity"),
        "source_validation_artifact": historical_manifest.get("source_validation_artifact"),
        "source_validation_artifact_identity": historical_manifest.get("source_validation_artifact_identity"),
        "source_validation_manifest_sha256": historical_manifest.get("source_validation_manifest_sha256"),
        "protected_contract_hashes": historical_manifest.get("protected_contract_hashes"),
        "model": "gpt-5.6-terra",
        "effort": "high",
        "publication_eligibility_policy_version": historical_manifest.get("publication_eligibility_policy_version"),
        "source_runner_root": str(RUNNER_ROOT.relative_to(ROOT)),
        "source_runner_result_count": inventory["runner_result_count"],
        "generation_performed": False,
        "promotion_mode": "deterministic_finalized_artifact_reconciliation",
        "corpus_checksum_root_identity": _sha256_json(corpus_files),
        "checksums": CHECKSUMS_NAME,
    }
    manifest["manifest_identity"] = _sha256_json(manifest)
    return manifest


def promote_full_corpus(output: Path = RELEASE_ROOT) -> dict[str, Any]:
    inventory = build_reconciliation_inventory()
    stage = Path(tempfile.mkdtemp(prefix=".commentary-v1.2-reconcile-", dir=output.parent))
    try:
        for row in inventory["rows"]:
            if row.get("release_state") != "PUBLISHED":
                continue
            ref = row["reference"]
            if row["source"] == "historical-75-release":
                source = RELEASE_ROOT / row["filename"]
            else:
                source_result = ROOT / row["corpus_runner_result"]
                source = source_result.parent / "commentary.json"
            if not source.is_file() or _sha256(source) != row.get("artifact_sha256"):
                raise ReconciliationError(f"promotion source changed: {ref}")
            shutil.copy2(source, stage / row["filename"])
        corpus_files = {path.name: _sha256(path) for path in sorted(stage.glob("*.json"))}
        manifest = _release_manifest(inventory, corpus_files)
        (stage / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checksums = {path.name: _sha256(path) for path in sorted(stage.glob("*.json"))}
        (stage / CHECKSUMS_NAME).write_text(json.dumps({"artifact_version": "commentary-v1.2-runtime-release-checksums-v2", "files": checksums}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # The complete staged package is verified before touching the runtime
        # directory. Existing published bytes are preserved byte-for-byte.
        _check_index(stage)
        output.mkdir(parents=True, exist_ok=True)
        expected_names = set(checksums)
        actual_names = {
            path.name
            for path in output.glob("*.json")
            if path.name not in {MANIFEST_NAME, CHECKSUMS_NAME}
        }
        if actual_names - expected_names:
            raise ReconciliationError("runtime release contains unexpected JSON artifacts")
        for source in sorted(stage.glob("*.json")):
            target = output / source.name
            if target.is_file() and source.name not in {MANIFEST_NAME, CHECKSUMS_NAME} and target.read_bytes() != source.read_bytes():
                raise ReconciliationError(f"historical published artifact would be rewritten: {source.name}")
            os.replace(source, target)
        return {"status": "PROMOTED", "manifest": manifest, "inventory": inventory}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "promote"))
    args = parser.parse_args()
    if args.command == "inventory":
        inventory = build_reconciliation_inventory()
        print(json.dumps({"status": "RECONCILIATION_PASS", "canonical_chapters": len(inventory["canonical"]), "runner_terminal_results": inventory["runner_result_count"], "state_counts": inventory["counts"]}, sort_keys=True))
    else:
        result = promote_full_corpus()
        print(json.dumps({"status": result["status"], "release": RELEASE, "published": result["manifest"]["published_chapter_count"], "manifest_entries": len(result["manifest"]["chapter_publication_index"])}, sort_keys=True))


if __name__ == "__main__":
    main()
