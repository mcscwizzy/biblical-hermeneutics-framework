#!/usr/bin/env python3
"""Plan and operate Commentary production without changing Commentary contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from framework.commentary.production.census import build_census, canonical_chapters, status_summary
from framework.commentary.production.inputs import attach_ordinal, prepare_chapter
from framework.commentary.production.ledger import rebuild_ledger
from framework.commentary.production.manifests import build_manifest, save_manifest
from framework.commentary.production.models import DEFAULT_CANARY_LIMIT, ManifestError, PRODUCTION_VERSION, production_root
from framework.commentary.production.manifests import load_manifest
from framework.commentary.production.runner import ProductionRunner
from framework.commentary.production.sampling import sample_audit_records


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_start(value: str) -> tuple[str, int]:
    if ":" in value:
        book, chapter = value.rsplit(":", 1)
    else:
        book, chapter = value.rsplit(" ", 1)
    return bible.normalize_book_name(book), int(chapter)


def _select_canary(count: int, seed: str) -> list[dict]:
    rows = canonical_chapters()
    census = build_census(ROOT, canonical=rows)
    historical = {row["reference"] for row in census["chapters"] if row["historical_artifacts"]}
    candidates = [row for row in rows if row["reference"] not in historical]
    # Stable hash ranking plus round-robin literary families gives a compact,
    # mixed canary without pretending to be a research-scale stratified sample.
    families = {}
    from framework.commentary.production.inputs import literary_category
    for row in candidates:
        families.setdefault(literary_category(row["book"], row["chapter"]), []).append(row)
    ranked = {key: sorted(value, key=lambda row: hashlib.sha256(f"{seed}:{row['reference']}".encode()).hexdigest()) for key, value in families.items()}
    selected = []
    keys = sorted(ranked)
    index = 0
    while len(selected) < count:
        made_progress = False
        for key in keys:
            if index < len(ranked[key]) and len(selected) < count:
                selected.append(ranked[key][index])
                made_progress = True
        if not made_progress:
            break
        index += 1
    return sorted(selected, key=lambda row: row["canonical_ordinal"])


def plan(args: argparse.Namespace) -> dict:
    rows = canonical_chapters()
    by_ref = {row["reference"]: row for row in rows}
    if args.start:
        start_book, start_chapter = _parse_start(args.start)
        start_ref = bible.verse_range_reference(start_book, start_chapter)
        start_index = next(index for index, row in enumerate(rows) if row["reference"] == start_ref)
        selected = rows[start_index:start_index + args.count]
    else:
        selected = _select_canary(args.count, args.seed)
    if len(selected) > DEFAULT_CANARY_LIMIT and not args.allow_full_corpus_plan:
        raise ManifestError(f"planning more than {DEFAULT_CANARY_LIMIT} chapters requires --allow-full-corpus-plan")
    prepared = []
    for row in selected:
        item = prepare_chapter(row["book"], row["chapter"])
        prepared.append(attach_ordinal(item, row["canonical_ordinal"]))
    manifest = build_manifest(prepared, batch_size=args.batch_size, status="PLANNED_NOT_AUTHORIZED", generation_config={"provider_adapter": "configured-at-run", "model": "configured-at-run", "reader_enabled": False, "selection_seed": args.seed})
    manifest["selection"] = {"strategy": "deterministic category round-robin hash rank", "seed": args.seed, "canary": not args.allow_full_corpus_plan, "status": "PLANNED_NOT_AUTHORIZED"}
    # Add the selection before calculating the immutable identity.
    from framework.commentary.production.manifests import _manifest_identity
    manifest["manifest_identity"] = _manifest_identity(manifest)
    output = production_root(ROOT) / "planned" / ("canary-001-manifest.json" if not args.start else f"{manifest['run_id']}-manifest.json")
    save_manifest(manifest, output)
    return {"manifest_path": str(output.relative_to(ROOT)), "status": manifest["status"], "run_id": manifest["run_id"], "chapter_count": len(selected), "chapters": [{key: row[key] for key in ("reference", "book", "chapter", "canonical_ordinal", "literary_category", "evidence_availability", "evidence_count", "synthesis_unit_count", "density_bucket", "input_identity", "expected_artifacts")} for row in manifest["chapters"]]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commentary production planner and guarded runner")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    census = sub.add_parser("census")
    census.add_argument("--json", action="store_true")
    p = sub.add_parser("plan")
    p.add_argument("--batch-size", type=int, default=25)
    p.add_argument("--count", type=int, default=25)
    p.add_argument("--start")
    p.add_argument("--seed", default="20260908")
    p.add_argument("--allow-full-corpus-plan", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--authorized-run", action="store_true")
    run.add_argument("--enable-reader", action="store_true")
    run.add_argument("--new-attempt", action="store_true")
    resume = sub.add_parser("resume")
    resume.add_argument("--run", required=True)
    resume.add_argument("--authorized-run", action="store_true")
    resume.add_argument("--enable-reader", action="store_true")
    led = sub.add_parser("ledger")
    led.add_argument("--json", action="store_true")
    drift = sub.add_parser("drift")
    drift.add_argument("--json", action="store_true")
    sample = sub.add_parser("audit-sample")
    sample.add_argument("--count", type=int, default=25)
    sample.add_argument("--seed", default="20260908")
    args = parser.parse_args(argv)
    try:
        if args.command in {"status", "census"}:
            value = build_census(ROOT)
            output = value if args.command == "census" or args.json else status_summary(value)
        elif args.command == "plan":
            output = plan(args)
        elif args.command == "ledger":
            output = rebuild_ledger(ROOT)
        elif args.command == "audit-sample":
            ledger_path = production_root(ROOT) / "ledger.json"
            ledger = _read(ledger_path) if ledger_path.exists() else rebuild_ledger(ROOT)
            output = sample_audit_records(ledger.get("current", {}).values(), count=args.count, seed=args.seed)
        elif args.command == "drift":
            manifests = sorted((production_root(ROOT) / "runs").glob("*/manifest.json"))
            rows = []
            for manifest_path in manifests:
                manifest = load_manifest(manifest_path)
                for locked in manifest.get("chapters", []):
                    current = prepare_chapter(locked["book"], int(locked["chapter"]))
                    if current.row.get("input_identity") != locked.get("input_identity"):
                        rows.append({"reference": locked["reference"], "run_id": manifest["run_id"], "locked": locked.get("input_identity"), "current": current.row.get("input_identity"), "status": "STALE_INPUT"})
            output = {"artifact_version": "commentary-production-drift-report-v1", "status": "NO_PRODUCTION_RUNS" if not manifests else "DRIFT_FOUND" if rows else "NO_DRIFT", "chapters": rows}
        elif args.command == "run":
            output = ProductionRunner(ROOT).run_manifest(args.manifest, authorized_run=args.authorized_run, enable_reader=args.enable_reader, new_attempt=args.new_attempt)
        else:
            manifest_path = production_root(ROOT) / "runs" / args.run / "manifest.json"
            output = ProductionRunner(ROOT).run_manifest(manifest_path, authorized_run=args.authorized_run, enable_reader=args.enable_reader)
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
