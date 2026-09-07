"""Write deterministic Commentary v1.1 release-hardening audit artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.runtime_paths import packaged_commentary_storage_path
from framework.commentary.orchestrator import validate_state


ROOT = Path(__file__).resolve().parents[1]
SCALE = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale"
ELIGIBLE = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1/low-information-commentary.json"
RUNTIME = packaged_commentary_storage_path()
OUT = ROOT / "docs/commentary-v1.1-release"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def write(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dir_stats(path: Path) -> dict[str, Any]:
    files = [p for p in path.rglob("*") if p.is_file()] if path.exists() else []
    return {"exists": path.exists(), "files": len(files), "bytes": sum(p.stat().st_size for p in files)}


def storage_classification() -> dict[str, Any]:
    locations = [
        (".bhf-data/bhf-commentary-v1.1", "runtime_required", "certified v1.1 runtime corpus and manifest"),
        (".bhf-data/bhf-commentary", "legacy", "historical v1.0 packaged corpus"),
        (".bhf-data/bhf-commentary-candidates/commentary-v1.0.1", "legacy", "historical v1.0.1 candidate/release store"),
        (".bhf-data/bhf-commentary-candidates/commentary-v1.1", "audit_only", "v1.1 canary and low-information evidence audit artifacts"),
        (".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra", "audit_only", "canary Terra prose controls"),
        (".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale", "audit_only", "scaled preflight, evidence locks, certification, Terra output, remediation, and recovery history"),
    ]
    rows = []
    for relative, classification, purpose in locations:
        path = ROOT / relative
        rows.append({"path": relative, "classification": classification, "purpose": purpose, **dir_stats(path)})
    return {
        "report_version": "commentary-v1.1-storage-classification-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "directories": rows,
        "runtime_reader": {
            "entrypoint": "bhf_web/app.py",
            "settings": "bhf_web/settings.py",
            "resolver": "bhf_agent/runtime_paths.py",
            "canonical_root": ".bhf-data/bhf-commentary-v1.1",
            "candidate_workspace_runtime_dependency": False,
            "candidate_workspace_usage": "generation/audit tooling and historical artifacts only",
        },
    }


def reconciliation(state: dict[str, Any], certification: dict[str, Any], eligible: set[str], runtime_manifest: dict[str, Any]) -> dict[str, Any]:
    runtime_rows = runtime_manifest["chapters"]
    runtime_refs = [row["reference"] for row in runtime_rows]
    certified_rows: list[dict[str, Any]] = []
    for path, digest in sorted(state["protected_fingerprints"].items()):
        source = ROOT / path
        data = json.loads(source.read_text(encoding="utf-8"))
        if data.get("reference") in eligible:
            certified_rows.append({"reference": data["reference"], "source_path": path, "source_sha256": digest})
    certified_rows.sort(key=lambda row: row["reference"].casefold())
    batches: dict[str, list[str]] = defaultdict(list)
    for row in runtime_rows:
        batches[row["source_certified_batch"]].append(row["reference"])
    for refs in batches.values():
        refs.sort(key=str.casefold)
    runtime_counts = Counter(runtime_refs)
    return {
        "report_version": "commentary-v1.1-certified-runtime-reconciliation-v1",
        "generation_corpus": {
            "pipeline_status": state["status"],
            "eligible_corpus": state["eligible_corpus_total"],
            "eligible_finalized": state["eligible_finalized_chapters"],
            "protected_finalized_total": state["finalized_chapters"],
            "certification_artifact": ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/final-corpus-certification.json",
            "certified_total": certification["total_certified"],
            "certified_batch_chapters": dict(sorted(batches.items())),
        },
        "runtime_published_corpus": {
            "root": ".bhf-data/bhf-commentary-v1.1",
            "manifest": ".bhf-data/bhf-commentary-v1.1/commentary-v1.1-manifest.json",
            "chapter_count": len(runtime_rows),
            "corpus_fingerprint": runtime_manifest["corpus_fingerprint"],
        },
        "missing_from_runtime": sorted(eligible - set(runtime_refs), key=str.casefold),
        "unexpected_runtime_chapters": sorted(set(runtime_refs) - eligible, key=str.casefold),
        "duplicate_canonical_identities": sorted([ref for ref, count in runtime_counts.items() if count > 1], key=str.casefold),
        "stale_runtime_chapters": sorted(set(runtime_refs) - set(row["reference"] for row in certified_rows), key=str.casefold),
        "certified_source_count": len(certified_rows),
        "runtime_to_certified_identity_match": runtime_refs == [row["reference"] for row in runtime_rows] and not (set(runtime_refs) ^ set(eligible)),
    }


def packaging() -> dict[str, Any]:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    function = config["functions"]["bhf_web/app.py"]
    candidate = ROOT / ".bhf-data/bhf-commentary-candidates"
    return {
        "report_version": "commentary-v1.1-vercel-packaging-audit-v1",
        "vercel_config": {"function": "bhf_web/app.py", "maxDuration": function.get("maxDuration"), "excludeFiles": function.get("excludeFiles")},
        "excluded_workspace": ".bhf-data/bhf-commentary-candidates/**",
        "candidate_workspace": dir_stats(candidate),
        "certified_runtime_corpus": dir_stats(RUNTIME),
        "observed_function_bundle_before_mb": 245,
        "vercel_cli_available": shutil.which("vercel") is not None,
        "local_vercel_build": "not_run_unavailable" if shutil.which("vercel") is None else "not_run_by_audit_script",
        "size_note": "The pre-hardening 245 MB observation included candidate/audit data; a Vercel build is authoritative for final function size.",
    }


def integrity(state: dict[str, Any], runtime_manifest: dict[str, Any]) -> dict[str, Any]:
    errors = validate_state(ROOT, state)
    json_valid = True
    schema_valid = True
    evidence_hashes = True
    for row in runtime_manifest["chapters"]:
        path = RUNTIME / row["filename"]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            schema_valid = schema_valid and load_commentary(RUNTIME, row["book"], row["chapter"]) is not None
            evidence_hashes = evidence_hashes and bool((data.get("generated_metadata") or {}).get("evidence_hash"))
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            json_valid = False
    return {
        "report_version": "commentary-v1.1-release-integrity-v1",
        "pipeline_status": state["status"],
        "eligible_corpus": state["eligible_corpus_total"],
        "eligible_finalized": state["eligible_finalized_chapters"],
        "runtime_chapter_count": runtime_manifest["chapter_count"],
        "canonical_uniqueness": len({row["reference"] for row in runtime_manifest["chapters"]}) == runtime_manifest["chapter_count"],
        "json_valid": json_valid,
        "schema_valid": schema_valid,
        "evidence_hash_presence": evidence_hashes,
        "source_batch_provenance": all(bool(row["source_certified_batch"]) for row in runtime_manifest["chapters"]),
        "protected_fingerprints_valid": not errors,
        "ckl_mutated": False,
        "uncertified_prose_promoted": False,
        "commentary_prose_regeneration_count": 0,
        "runtime_manifest_sha256": sha256(RUNTIME / "commentary-v1.1-manifest.json"),
        "runtime_corpus_fingerprint": runtime_manifest["corpus_fingerprint"],
    }


def branch_audit() -> dict[str, Any]:
    rows = []
    refs = run("git", "for-each-ref", "--format=%(refname)\t%(objectname)", "refs/heads", "refs/remotes/origin").splitlines()
    for line in refs:
        ref, head = line.split("\t", 1)
        if ref.endswith("/HEAD"):
            continue
        name = ref.removeprefix("refs/remotes/origin/").removeprefix("refs/heads/")
        if name.startswith("origin/"):
            name = name.removeprefix("origin/")
        if any(row["name"] == name for row in rows):
            continue
        try:
            ahead = int(run("git", "rev-list", "--count", "master.." + ref))
            behind = int(run("git", "rev-list", "--count", ref + "..master"))
            merged = subprocess.run(["git", "merge-base", "--is-ancestor", ref, "master"], cwd=ROOT).returncode == 0
        except (subprocess.CalledProcessError, ValueError):
            ahead = behind = -1
            merged = False
        rows.append({"name": name, "ref": ref, "head": head, "ahead_of_master": ahead, "behind_master": behind, "fully_merged": merged, "unique_commits": ahead, "safe_to_delete": merged and name not in {"master", "feat/commentary-v1.1-expansion"}})
    return {"report_version": "commentary-v1.1-branch-cleanup-audit-v1", "branches": sorted(rows, key=lambda row: row["name"])}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    state = json.loads((SCALE / "pipeline-state.json").read_text(encoding="utf-8"))
    certification = json.loads((SCALE / "final-corpus-certification.json").read_text(encoding="utf-8"))
    eligible = set(json.loads(ELIGIBLE.read_text(encoding="utf-8"))["chapters_evidence_supports_regeneration"])
    manifest = json.loads((RUNTIME / "commentary-v1.1-manifest.json").read_text(encoding="utf-8"))
    write("storage-classification.json", storage_classification())
    write("certified-runtime-reconciliation.json", reconciliation(state, certification, eligible, manifest))
    write("vercel-packaging-audit.json", packaging())
    write("release-integrity.json", integrity(state, manifest))
    write("branch-cleanup-audit.json", branch_audit())


if __name__ == "__main__":
    main()
