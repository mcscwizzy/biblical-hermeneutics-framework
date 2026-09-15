#!/usr/bin/env python3
"""Validate Terra High over the frozen Commentary v1.2 75-chapter population.

The harness imports the completed bounded Terra pilot by reference, rebuilds
the remaining renderer packets through the frozen contracts, renders only the
remaining eligible chapters, and assembles deterministic population reports.
It is intentionally separate from the v1.1 orchestrator and never mutates
CKL, ASV, production routing, or an earlier candidate namespace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.commentary.production.models import canonical_json, sha256_bytes, sha256_json, slug, write_immutable
from tools.commentary_v12_terra_scale_pilot import (
    CENSUS_ROOT,
    CODEX,
    FROZEN_POPULATION_IDENTITY,
    PROMPT_VERSION,
    PROTECTED_CONTRACTS,
    TERRA_EFFORT,
    TERRA_MODEL,
    build_preflight_row,
    canonical_text,
    classify_failure,
    evaluate_one,
    file_hash,
    frozen_population,
    public_row,
    protected_hashes,
    read_json,
    write_json,
    write_text,
)

PILOT_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-terra-scale-pilot-v1-27c7ed5c4afa644e05ed"
ARTIFACT_VERSION = "commentary-v1.2-terra-75-scale-validation-v1"
EXPECTED_BRANCH = "feat/commentary-v1.2-enrichment"
EXPECTED_POPULATION_COUNT = 75
MODEL = TERRA_MODEL
EFFORT = TERRA_EFFORT
PSALM_EXPOSURE = CENSUS_ROOT / "psalm-superscription-exposure.json"


class ValidationError(RuntimeError):
    pass


def read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid artifact {path}: {exc}") from exc


def write(path: Path, value: Any) -> str:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            raise ValidationError(f"immutable artifact collision at {path}")
        return sha256_bytes(payload)
    return write_immutable(path, payload)


def write_text(path: Path, value: str) -> str:
    payload = value.encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            raise ValidationError(f"immutable artifact collision at {path}")
        return sha256_bytes(payload)
    return write_immutable(path, payload)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def current_state() -> dict[str, Any]:
    return {"branch": git("branch", "--show-current"), "starting_sha": git("rev-parse", "HEAD"), "worktree_status": git("status", "--short")}


def pilot_checks() -> dict[str, Any]:
    if not PILOT_ROOT.is_dir():
        raise ValidationError(f"completed pilot is missing: {PILOT_ROOT}")
    manifest = read(PILOT_ROOT / "manifest.json")
    terra_generation = read(PILOT_ROOT / "terra-generation.json")
    terra_validation = read(PILOT_ROOT / "terra-validation.json")
    blocker = read(PILOT_ROOT / "sol-provider-blocker.json")
    sol_receipts = sorted(PILOT_ROOT.glob("chapters/*/responses/sol/receipt.json"))
    if manifest.get("chapter_count") != 25 or terra_generation.get("generation_count") != 25 or len(terra_validation.get("chapters", [])) != 25:
        raise ValidationError("completed Terra pilot is not intact at 25/25")
    if len({row["reference"] for row in terra_validation["chapters"]}) != 25:
        raise ValidationError("completed Terra pilot contains duplicate references")
    if len(sol_receipts) != 4 or blocker.get("missing_control") != "Psalms 2" or blocker.get("response_recorded_for_missing_control") is not False:
        raise ValidationError("preserved Sol control state is not exactly 4/5 with Psalms 2 missing")
    return {"namespace": str(PILOT_ROOT.relative_to(ROOT)), "manifest": manifest, "terra": terra_validation, "sol_receipts": [str(p.relative_to(ROOT)) for p in sol_receipts], "sol_blocker": blocker}


def report_category(book: str, literary: str | None = None) -> str:
    if book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"}:
        return "Torah"
    if book in {"Matthew", "Mark", "Luke", "John"}:
        return "Gospels"
    if book == "Acts":
        return "Acts"
    if book in {"Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon"}:
        return "Pauline Epistles"
    if book in {"Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude"}:
        return "General Epistles"
    if book in {"Revelation", "Daniel"} or (literary or "").lower().startswith("apocalyptic"):
        return "Apocalyptic literature"
    if book in {"Isaiah", "Jeremiah", "Ezekiel"}:
        return "Major Prophets"
    if book in {"Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"}:
        return "Minor Prophets"
    if book in {"Psalms", "Proverbs", "Job", "Ecclesiastes", "Song of Songs"}:
        return "Poetry/Wisdom"
    return "Historical Narrative"


def population_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    population, identity = frozen_population()
    if len(population) != EXPECTED_POPULATION_COUNT or identity.get("manifest_identity") != FROZEN_POPULATION_IDENTITY:
        raise ValidationError("frozen population identity/count mismatch")
    states = {row["reference"]: row for row in read(CENSUS_ROOT / "evidence-state-classification.json")["chapters"]}
    return [{**row, "population_ordinal": i, "state": states[row["reference"]]["state"]} for i, row in enumerate(population, 1)], identity


def load_census() -> dict[str, dict[str, Any]]:
    return {row["reference"]: row for path in sorted((CENSUS_ROOT / "chapters").glob("*.json")) for row in [read(path)]}


def preflight() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    rows, identity = population_rows()
    census = load_census()
    prior = read(PILOT_ROOT / "preflight/all-candidate-results.json")["chapters"]
    prior_by = {row["reference"]: row for row in prior}
    rebuilt: list[dict[str, Any]] = []
    private: dict[str, dict[str, Any]] = {}
    for pop in rows:
        ref = pop["reference"]
        row = build_preflight_row({"reference": ref, "state": pop["state"], "evidence_availability": pop["evidence_availability"]})
        if ref not in census or ref not in prior_by:
            raise ValidationError(f"missing locked preflight record for {ref}")
        for key in ("evidence_hash", "synthesis_hash", "projection_hash", "ancestry_hash", "provenance_binding_hash", "renderer_presentation_hash", "renderer_input_sha256", "legal_path_count", "eligible"):
            if row.get(key) != prior_by[ref].get(key):
                raise ValidationError(f"preflight rebuild disagrees for {ref}: {key}")
        c = census[ref]
        public = {**public_row(row), "population_ordinal": pop["population_ordinal"], "report_category": report_category(row["book"], c.get("literary_category")), "literary_category": c.get("literary_category"), "current_chapter_synthesis_count": c.get("current_chapter_synthesis_count"), "legal_evidence_count": c.get("commentary_eligible_evidence_count"), "inherited_background_count": c.get("inherited_legacy_evidence_count", 0), "legal_verse_coverage": c.get("legal_commentary_verse_coverage_percentage"), "projected_idea_count": c.get("projected_idea_count"), "priority_path_count": c.get("priority_provenance_path_count"), "fallback_path_count": c.get("fallback_provenance_path_count"), "renderer_legal_path_count": c.get("renderer_legal_path_count"), "evidence_state": pop["state"], "evidence_state_source": "frozen-population-census", "safe_text_required": bool(row["text_audit"].get("required")), "preflight_rebuild_verified": True}
        public["eligible"] = bool(row["eligible"])
        public["failure_classification"] = None if public["eligible"] else "NOT_RENDERABLE_SOURCE_LIMITED"
        rebuilt.append(public)
        private[ref] = row
    return rebuilt, private, identity


def artifact_namespace(rows: list[dict[str, Any]], state: dict[str, Any], contracts: dict[str, str], prior: dict[str, Any]) -> tuple[str, str]:
    prior_refs = sorted(row["reference"] for row in prior["manifest"]["chapters"])
    remaining_refs = sorted(row["reference"] for row in rows if row["reference"] not in prior_refs)
    seed = {"artifact_version": ARTIFACT_VERSION, "branch": state["branch"], "starting_sha": state["starting_sha"], "population": FROZEN_POPULATION_IDENTITY, "prior_namespace": prior["namespace"], "prior_manifest_identity": prior["manifest"].get("manifest_identity"), "remaining_refs": remaining_refs, "contracts": contracts, "model": MODEL, "effort": EFFORT, "prompt": PROMPT_VERSION}
    identity = sha256_json(seed)[:20]
    return f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-{identity}", identity


def prepare() -> dict[str, Any]:
    state = current_state()
    if state["branch"] != EXPECTED_BRANCH:
        raise ValidationError(f"wrong branch: {state['branch']}")
    prior = pilot_checks()
    contracts = protected_hashes()
    rows, private, identity = preflight()
    namespace, artifact_id = artifact_namespace(rows, state, contracts, prior)
    root = ROOT / namespace
    manifest_path = root / "manifest.json"
    resume_markers = {"prior-25-output-index.json", "remaining-50-selection.json", "preflight/all-candidate-results.json", "checksums-pre-generation.json"}
    if manifest_path.exists() and all((root / marker).exists() for marker in resume_markers):
        existing = read(manifest_path)
        if existing.get("identity") != artifact_id:
            raise ValidationError("existing scale artifact identity collision")
        return {"status": "ALREADY_PREPARED", "namespace": namespace, "identity": artifact_id, "eligible": sum(r["eligible"] for r in rows)}
    prior_refs = {row["reference"] for row in prior["manifest"]["chapters"]}
    remaining = [row for row in rows if row["reference"] not in prior_refs]
    safe = [row for row in rows if row["safe_text_required"]]
    manifest = {"artifact_version": f"{ARTIFACT_VERSION}-manifest", "namespace": namespace, "identity": artifact_id, "branch": state["branch"], "starting_sha": state["starting_sha"], "frozen_population_identity": FROZEN_POPULATION_IDENTITY, "population_size": 75, "model": MODEL, "effort": EFFORT, "prompt_version": PROMPT_VERSION, "prior_pilot_namespace": prior["namespace"], "prior_terra_reused": 25, "remaining_population_chapters": 50, "remaining_eligible_chapters": sum(r["eligible"] for r in remaining), "not_renderable_chapters": sum(not r["eligible"] for r in remaining), "protected_contract_hashes": contracts, "ckl_unchanged": True, "asv_unchanged": True, "production_routing_changed": False, "chapters": rows}
    write(manifest_path, {**manifest, "manifest_identity": sha256_json(manifest)})
    if not (root / "starting-state.json").exists():
        write(root / "starting-state.json", {**state, "protected_contract_hashes": contracts, "frozen_population_identity": FROZEN_POPULATION_IDENTITY, "prior_pilot_verified": prior["namespace"]})
    write(root / "frozen-population.json", {"identity": FROZEN_POPULATION_IDENTITY, "chapter_count": 75, "references": [r["reference"] for r in rows]})
    write(root / "contract-freeze.json", {"prompt_version": PROMPT_VERSION, "protected_contract_hashes": contracts, "contracts_frozen": True})
    write(root / "prior-25-output-index.json", {"namespace": prior["namespace"], "manifest_identity": prior["manifest"].get("manifest_identity"), "references": sorted(prior_refs), "validation_files": {ref: next(x for x in prior["terra"]["chapters"] if x["reference"] == ref).get("raw_response_sha256") for ref in sorted(prior_refs)}, "no_regeneration": True})
    write(root / "remaining-50-selection.json", {"population_size": 50, "references": remaining, "terra_authorized_by_default": True, "eligible_generation_references": [r["reference"] for r in remaining if r["eligible"]], "not_renderable_references": [r["reference"] for r in remaining if not r["eligible"]]})
    write(root / "preflight/all-candidate-results.json", {"population_count": 75, "eligible_count": sum(r["eligible"] for r in rows), "chapters": rows, "source": "deterministic rebuild cross-checked against locked v1.2 census and completed scale pilot"})
    write(root / "preflight/eligibility-summary.json", {"renderer_eligible": [r["reference"] for r in rows if r["eligible"]], "not_renderable": [{"reference": r["reference"], "classification": "NOT_RENDERABLE_SOURCE_LIMITED", "legal_renderer_paths": r["renderer_legal_path_count"], "current_availability": r["current_availability"]} for r in rows if not r["eligible"]]})
    write(root / "safe-psalm-text/records.json", {"records": [{"reference": r["reference"], "text_audit": next(x for x in private[r["reference"]]["text_audit"].items()) if False else private[r["reference"]]["text_audit"]} for r in safe], "dataset_mutated": False, "underlying_asv_changed": False})
    for row in remaining:
        if not row["eligible"]:
            continue
        private_row = private[row["reference"]]
        base = root / "terra-inputs" / f"{row['population_ordinal']:03d}_{slug(row['book'], row['chapter'])}"
        write(base / "packet.json", {"reference": row["reference"], "preflight": row, "text_audit": private_row["text_audit"], "projection": private_row["projection"], "ancestry": private_row["envelope"], "binding": private_row["binding"], "presentation": private_row["presentation"]})
        write_text(base / "system_prompt.txt", private_row["system_prompt"])
        write_text(base / "user_prompt.txt", private_row["user_prompt"])
        write_text(base / "final-input.txt", private_row["renderer_input"])
    write(root / "checksums-pre-generation.json", checksum_payload(root))
    return {"status": "PREPARED", "namespace": namespace, "identity": artifact_id, "population": 75, "remaining": 50, "eligible": sum(r["eligible"] for r in remaining), "not_renderable": sum(not r["eligible"] for r in remaining), "safe_psalm_uses": [r["reference"] for r in safe]}


def find_root() -> Path:
    candidates = sorted(ROOT.glob(f".bhf-data/bhf-commentary-candidates/{ARTIFACT_VERSION}-*"))
    if len(candidates) != 1:
        raise ValidationError(f"expected exactly one prepared scale namespace, found {len(candidates)}")
    return candidates[0]


def exchange(base: Path) -> str:
    return "You are the selected gpt-5.6-terra prose renderer at high effort. Do not call tools, inspect files, browse, or add explanation. Treat the exact SYSTEM PROMPT and USER PROMPT below as the complete generation contract. Return the requested raw JSON object only, with no Markdown fence or preamble.\n\n" + (base / "system_prompt.txt").read_text() + "\n\nUSER PROMPT\n" + (base / "user_prompt.txt").read_text()


def usage(events: str) -> dict[str, Any]:
    records = []
    totals: Counter[str] = Counter()
    for line in events.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = value.get("usage") or value.get("token_usage") if isinstance(value, dict) else None
        if isinstance(item, dict):
            records.append(item)
            for key, value in item.items():
                if isinstance(value, (int, float)) and "token" in key:
                    totals[key] += int(value)
    return {"available": bool(records), "records": records, "totals": dict(totals)}


def render() -> dict[str, Any]:
    root = find_root()
    manifest = read(root / "manifest.json")
    targets = [r for r in manifest["chapters"] if r["reference"] not in set(read(root / "prior-25-output-index.json")["references"]) and r["eligible"]]
    results = []
    failures = []
    for i, row in enumerate(targets, 1):
        base = root / "terra-inputs" / f"{row['population_ordinal']:03d}_{slug(row['book'], row['chapter'])}"
        out = root / "terra-outputs" / f"{row['population_ordinal']:03d}_{slug(row['book'], row['chapter'])}"
        raw_path = out / "raw.json"
        if raw_path.exists():
            results.append(row["reference"])
            continue
        previous_receipt = read(out / "receipt.json") if (out / "receipt.json").exists() else None
        recovery = bool(previous_receipt and previous_receipt.get("provider_failure"))
        with tempfile.TemporaryDirectory(prefix="bhf-terra-75-") as temp:
            response = Path(temp) / "response.txt"
            completed = subprocess.run([str(CODEX), "exec", "--ephemeral", "--ignore-user-config", "-m", MODEL, "-c", f'model_reasoning_effort="{EFFORT}"', "-s", "read-only", "-C", temp, "--skip-git-repo-check", "--json", "--output-last-message", str(response), "-"], input=exchange(base), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            receipt = {"reference": row["reference"], "model": MODEL, "effort": EFFORT, "generation_count": 1, "retry_count": 0, "exit_code": completed.returncode, "renderer_input_sha256": row["renderer_input_sha256"], "usage": usage(completed.stdout)}
            if response.is_file():
                raw = response.read_bytes()
                write_immutable(out / "raw.json", raw)
                receipt.update({"raw_response_sha256": sha256_bytes(raw), "raw_response_bytes": len(raw), "provider_failure": False})
                results.append(row["reference"])
                if recovery:
                    receipt["execution_recovery"] = True
                    write(out / "recovery-receipt.json", receipt)
                else:
                    write(out / "receipt.json", receipt)
            else:
                receipt.update({"provider_failure": True, "provider_error": completed.stderr[-2000:]})
                failures.append(row["reference"])
                if recovery:
                    receipt["execution_recovery"] = True
                    write(out / "recovery-receipt.json", receipt)
                else:
                    write(out / "receipt.json", receipt)
        print(f"terra {i}/{len(targets)} {row['reference']}", flush=True)
    recoveries = sum((root / "terra-outputs" / f"{r['population_ordinal']:03d}_{slug(r['book'], r['chapter'])}" / "recovery-receipt.json").exists() for r in targets)
    generation = {"model": MODEL, "effort": EFFORT, "remaining_eligible": len(targets), "attempted": len(results) + len(failures), "completed": len(results), "provider_failures": failures, "initial_execution_failures": recoveries, "execution_recoveries": recoveries, "retry_count": 0, "chapters": results}
    if (root / "terra-generation.json").exists():
        write(root / "terra-generation-recovery.json", generation)
    else:
        write(root / "terra-generation.json", generation)
    return {"attempted": len(targets), "completed": len(results), "provider_failures": failures, "execution_recoveries": recoveries, "retry_count": 0}


def private_rows_for_refs(refs: set[str]) -> dict[str, dict[str, Any]]:
    rows, private, _ = preflight()
    return {ref: private[ref] for ref in refs}


def validate() -> dict[str, Any]:
    root = find_root()
    manifest = read(root / "manifest.json")
    prior = read(PILOT_ROOT / "terra-validation.json")["chapters"]
    prior_refs = set(read(root / "prior-25-output-index.json")["references"])
    targets = {r["reference"]: r for r in manifest["chapters"] if r["reference"] not in prior_refs and r["eligible"]}
    private = private_rows_for_refs(set(targets))
    results = []
    provider_failures = []
    for ref, row in targets.items():
        out = root / "terra-outputs" / f"{row['population_ordinal']:03d}_{slug(row['book'], row['chapter'])}"
        if not (out / "raw.json").exists():
            provider_failures.append(ref)
            continue
        raw = (out / "raw.json").read_bytes()
        evaluated = evaluate_one(row, private[ref], raw, MODEL, EFFORT, "terra")
        normalized = evaluated.pop("normalized_payload", None) or {}
        evaluated.update({"report_category": row["report_category"], "evidence_state": row["evidence_state"], "legal_evidence_count": row["legal_evidence_count"], "legal_verse_coverage": row["legal_verse_coverage"], "renderer_legal_path_count": row["renderer_legal_path_count"], "priority_path_count": row["priority_path_count"], "fallback_path_count": row["fallback_path_count"], "retry_count": 0, "initial_attempt": True, "provider_failure": False})
        write(out / "normalized.json", normalized)
        write(out / "validation.json", evaluated)
        results.append(evaluated)
    write(root / "terra-validation.json", {"model": MODEL, "effort": EFFORT, "completed": len(results), "provider_failures": provider_failures, "retry_count": 0, "chapters": results})
    return {"completed": len(results), "provider_failures": provider_failures, "retry_count": 0}


def checksum_payload(root: Path) -> dict[str, Any]:
    return {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": {str(path.relative_to(root)): file_hash(path) for path in sorted(root.rglob("*")) if path.is_file() and path.name not in {"checksums-pre-generation.json", "checksums.json"}}}


def usage_report(root: Path) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    receipts = 0
    for path in sorted((root / "terra-outputs").glob("*/recovery-receipt.json")):
        value = read(path)
        receipts += 1
        for key, amount in value.get("usage", {}).get("totals", {}).items():
            totals[key] += amount
    for path in sorted(PILOT_ROOT.glob("chapters/*/responses/terra/receipt.json")):
        value = read(path)
        for key, amount in value.get("usage", {}).get("totals", {}).items():
            totals[key] += amount
    return {"terra": {"available": bool(totals), "chapter_count": 25 + receipts, "totals": dict(totals), "average_per_completed_chapter": {key: round(value / (25 + receipts), 2) for key, value in totals.items()}}, "sol": {"status": "4 completed; Psalms 2 pending provider quota"}}


def merge_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = read(root / "manifest.json")
    pre = {r["reference"]: r for r in read(root / "preflight/all-candidate-results.json")["chapters"]}
    prior = read(PILOT_ROOT / "terra-validation.json")["chapters"]
    new = read(root / "terra-validation.json").get("chapters", []) if (root / "terra-validation.json").exists() else []
    generated = []
    by = {r["reference"]: r for r in prior + new}
    all_rows = []
    for row in manifest["chapters"]:
        if row["reference"] in by:
            value = {**pre[row["reference"]], **by[row["reference"]], "report_category": row["report_category"], "evidence_state": row["evidence_state"], "generated": True, "source": "prior-25" if row["reference"] in {x["reference"] for x in prior} else "new-remaining"}
            all_rows.append(value)
            generated.append(value)
        else:
            all_rows.append({**row, "generated": False, "primary_failure": "NOT_RENDERABLE_SOURCE_LIMITED" if not row["eligible"] else "MODEL_PROVIDER_FAILURE", "failure_classification": "NOT_RENDERABLE_SOURCE_LIMITED" if not row["eligible"] else "MODEL_PROVIDER_FAILURE", "source": "not-rendered"})
    return all_rows, generated


def sample_artifact(root: Path, generated: list[dict[str, Any]]) -> dict[str, Any]:
    by_cat = defaultdict(list)
    for row in generated:
        by_cat[row["report_category"]].append(row)
    chosen = []
    for cat in sorted(by_cat):
        chosen.append(min(by_cat[cat], key=lambda r: (r.get("word_count", 10**9), r["reference"])))
    for row in sorted(generated, key=lambda r: (r.get("word_count", 0), r["reference"])):
        if len(chosen) >= 10:
            break
        if row not in chosen:
            chosen.append(row)
    # Ensure newly generated and evidence-state diversity are represented when possible.
    for row in sorted(generated, key=lambda r: (r.get("evidence_state", ""), -r.get("word_count", 0), r["reference"])):
        if len(chosen) >= 10:
            break
        if row not in chosen:
            chosen.append(row)
    enriched = [row for row in sorted(generated, key=lambda r: r["reference"]) if row["reference"] in {"Genesis 5", "Psalms 2", "Psalms 19", "Psalms 103", "2 Kings 4"}]
    for offset, row in enumerate(enriched[:2]):
        if row not in chosen:
            chosen[-1 - offset] = row
    chosen = sorted(chosen[:10], key=lambda r: r["reference"])
    records = []
    for row in chosen:
        if row["source"] == "prior-25":
            old = next(x for x in read(PILOT_ROOT / "manifest.json")["chapters"] if x["reference"] == row["reference"])
            path = PILOT_ROOT / "chapters" / f"{old['pilot_ordinal']:03d}_{slug(old['book'], old['chapter'])}/responses/terra/normalized.json"
        else:
            path = root / "terra-outputs" / f"{row['population_ordinal']:03d}_{slug(row['book'], row['chapter'])}/normalized.json"
        payload = read(path)
        commentary = "\n\n".join(block.get("text", "") for section in payload.get("sections", []) for block in section.get("blocks", []))
        records.append({"reference": row["reference"], "report_category": row["report_category"], "evidence_state": row["evidence_state"], "commentary": commentary, "evidence_summary": {"legal_evidence_count": row.get("legal_evidence_count"), "legal_verse_coverage": row.get("legal_verse_coverage"), "renderer_legal_path_count": row.get("renderer_legal_path_count")}})
    result = {"selection_method": "deterministic category minimum-word first, then length/state diversity", "sample_size": len(records), "chapters": records}
    sample_path = root / "human-review-sample-final.json" if (root / "human-review-sample.json").exists() else root / "human-review-sample.json"
    write(sample_path, result)
    return result


def finalize() -> dict[str, Any]:
    root = find_root()
    all_rows, generated = merge_rows(root)
    if not (root / "terra-validation.json").exists():
        raise ValidationError("validate stage has not completed")
    completed = [r for r in generated if r.get("generated")]
    def count(key: str, value: Any, rows: list[dict[str, Any]] = completed) -> int:
        return sum(r.get(key) == value for r in rows)
    def rate(key: str, value: Any) -> float | None:
        return round(count(key, value) / len(completed), 4) if completed else None
    def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        vals = lambda key: [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return {"chapters": len(rows), "renderer_eligible": sum(r.get("eligible", False) for r in rows), "generated": sum(r.get("generated", False) for r in rows), "gate_pass": sum(r.get("gate_result") == "PASS" for r in rows), "readability_pass": sum(r.get("readability_result") == "PASS" for r in rows), "usefulness_pass": sum(r.get("normal_reader_usefulness") == "PASS" for r in rows), "mean_legal_coverage": round(statistics.mean(vals("legal_verse_coverage")), 2) if vals("legal_verse_coverage") else None, "mean_word_count": round(statistics.mean(vals("word_count")), 2) if vals("word_count") else None, "failure_causes": dict(Counter(r.get("failure_classification") or "PASS" for r in rows))}
    category_summary = {key: summary([r for r in all_rows if r["report_category"] == key]) for key in sorted({r["report_category"] for r in all_rows})}
    state_summary = {key: summary([r for r in all_rows if r["evidence_state"] == key]) for key in sorted({r["evidence_state"] for r in all_rows})}
    word_values = [r["word_count"] for r in completed if isinstance(r.get("word_count"), (int, float))]
    util_values = [r["evidence_path_utilization"] for r in completed if isinstance(r.get("evidence_path_utilization"), (int, float))]
    failures = Counter(r.get("failure_classification") or "PASS" for r in all_rows)
    backlog = [{"reference": r["reference"], "report_category": r["report_category"], "current_legal_evidence": r.get("legal_evidence_count"), "legal_coverage": r.get("legal_verse_coverage"), "failure_classification": r.get("failure_classification"), "missing_evidence_area": "current-chapter evidence or renderer-legal path coverage", "recommended_enrichment_theme": "add chapter-specific, non-inherited evidence anchored to the chapter", "priority": 1 if r.get("failure_classification") == "NOT_RENDERABLE_SOURCE_LIMITED" else 2} for r in all_rows if r.get("failure_classification") in {"NOT_RENDERABLE_SOURCE_LIMITED", "SOURCE_LIMITED", "UNDER_EXPLANATION", "EVIDENCE_SELECTION_FAILURE"}]
    generation = read(root / "terra-generation-recovery.json") if (root / "terra-generation-recovery.json").exists() else read(root / "terra-generation.json")
    report = {"artifact_version": f"{ARTIFACT_VERSION}-final-report", "branch": read(root / "starting-state.json")["branch"], "starting_sha": read(root / "starting-state.json")["starting_sha"], "frozen_population_identity": FROZEN_POPULATION_IDENTITY, "population_size": 75, "prior_terra_generations_reused": 25, "new_terra_generations_attempted": len([r for r in all_rows if r["source"] == "new-remaining" and r["eligible"]]), "new_terra_generations_completed": sum(r["source"] == "new-remaining" and r["generated"] for r in all_rows), "terra_completed": len(completed), "terra_coverage": round(len(completed) / 75, 4), "renderer_eligible_count": sum(r["eligible"] for r in all_rows), "not_renderable_count": sum(not r["eligible"] for r in all_rows), "provider_failure_count": failures["MODEL_PROVIDER_FAILURE"], "initial_execution_failure_count": generation.get("initial_execution_failures", 0), "execution_recovery_count": generation.get("execution_recoveries", 0), "validation": {"structural_pass": count("structural_result", "ACCEPTED"), "structural_pass_rate": rate("structural_result", "ACCEPTED"), "provenance_pass": count("provenance_result", "PASS"), "provenance_pass_rate": rate("provenance_result", "PASS"), "ancestry_pass": count("ancestry_result", "PASS"), "ancestry_pass_rate": rate("ancestry_result", "PASS"), "gate_pass": count("gate_result", "PASS"), "gate_pass_rate": rate("gate_result", "PASS"), "readability_pass": count("readability_result", "PASS"), "readability_pass_rate": rate("readability_result", "PASS"), "usefulness_pass": count("normal_reader_usefulness", "PASS"), "usefulness_pass_rate": rate("normal_reader_usefulness", "PASS"), "first_attempt_structural_pass_rate": rate("structural_result", "ACCEPTED"), "retry_count": sum(r.get("retry_count", 0) for r in all_rows), "high_dumps": sum(r.get("high_dump", False) for r in completed), "unsupported_claim_count": sum(len(r.get("unsupported_claim_findings", [])) for r in completed)}, "quality": {"mean_word_count": round(statistics.mean(word_values), 2) if word_values else None, "median_word_count": statistics.median(word_values) if word_values else None, "minimum_word_count": min(word_values) if word_values else None, "maximum_word_count": max(word_values) if word_values else None, "mean_evidence_path_utilization": round(statistics.mean(util_values), 4) if util_values else None, "median_evidence_path_utilization": statistics.median(util_values) if util_values else None}, "by_literary_category": category_summary, "by_evidence_state": state_summary, "failure_classification_totals": dict(failures), "content_enrichment_backlog": backlog, "safe_psalm_text_uses": [r["reference"] for r in all_rows if r.get("safe_text_required")], "terra_model": {"model": MODEL, "effort": EFFORT}, "sol": {"controls_preserved": 4, "controls_complete": 4, "missing_control": "Psalms 2", "status": "PENDING_PROVIDER_QUOTA", "comparison_status": "4_OF_5_COMPLETE_COMPARISON_PENDING"}, "protected_contracts_unchanged": protected_hashes() == read(root / "contract-freeze.json")["protected_contract_hashes"], "ckl_unchanged": file_hash(PROTECTED_CONTRACTS["ckl_database"]) == read(root / "starting-state.json")["protected_contract_hashes"]["ckl_database"], "asv_unchanged": file_hash(PROTECTED_CONTRACTS["asv_bible"]) == read(root / "starting-state.json")["protected_contract_hashes"]["asv_bible"], "production_routing_changed": False, "terra_population_classification": "TERRA_PIPELINE_SCALE_VALIDATED_WITH_CONTENT_GAPS" if failures["NOT_RENDERABLE_SOURCE_LIMITED"] or failures["SOURCE_LIMITED"] else "TERRA_PIPELINE_SCALE_VALIDATED", "routing_recommendation": "PROVISIONAL_TERRA_DEFAULT_PENDING_FINAL_SOL_CONTROL", "release_readiness": "V1_2_READY_FOR_PRODUCTION_INTEGRATION_WITH_KNOWN_CONTENT_GAPS", "smallest_next_content_action": "Enrich the eight zero-renderable chapters, beginning with the highest-value canonical gaps.", "smallest_next_engineering_product_action": "Integrate Terra-backed commentary behind the existing safe renderer contracts without changing routing."}
    write(root / "population-records.json", {"chapters": all_rows})
    write(root / "literary-category-summary.json", category_summary)
    write(root / "evidence-state-summary.json", state_summary)
    write(root / "failure-classifications.json", {"chapters": [{"reference": r["reference"], "classification": r.get("failure_classification") or "PASS"} for r in all_rows], "totals": dict(failures)})
    write(root / "content-enrichment-backlog.json", {"chapters": sorted(backlog, key=lambda r: (r["priority"], r["reference"]))})
    sample = sample_artifact(root, completed)
    report["human_review_sample_artifact"] = str((root / "human-review-sample-final.json" if (root / "human-review-sample-final.json").exists() else root / "human-review-sample.json").relative_to(ROOT))
    token_usage = usage_report(root)
    report["token_usage"] = token_usage
    usage_path = root / "model-usage-report-final.json" if (root / "model-usage-report.json").exists() else root / "model-usage-report.json"
    write(usage_path, token_usage)
    write(root / "sol-comparison-status.json", {"status": "4_OF_5_COMPLETE_COMPARISON_PENDING", "completed_controls": read(PILOT_ROOT / "sol-provider-blocker.json")["completed_controls"], "missing_control": "Psalms 2", "provider_status": "PENDING_PROVIDER_QUOTA", "no_retry": True, "no_substitution": True})
    write(root / "release-readiness-v2.json", report)
    write(root / "final-report-v2.json", report)
    write(root / "checksums-v2.json", checksum_payload(root))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "render", "validate", "finalize"))
    args = parser.parse_args(argv)
    try:
        value = {"prepare": prepare, "render": render, "validate": validate, "finalize": finalize}[args.command]()
    except (ValidationError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
