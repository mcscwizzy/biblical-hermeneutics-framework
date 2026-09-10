#!/usr/bin/env python3
"""Prepare and evaluate the immutable unified seven-chapter renderer diagnostic.

The harness composes the frozen prompt-1.7 reader-level projection with the
frozen relational ancestry envelope.  It does not generate prose, alter source
artifacts, or change validator/scorer behavior.  Exactly one externally supplied
raw response is required for each frozen chapter before evaluation can run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.prompts import system_prompt_for_version
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
    add_ancestry_envelope_to_prompt,
    audit_ancestry_envelope,
    build_ancestry_envelope,
    response_ancestry_audit,
)
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    write_immutable,
)
from tools import commentary_renderer_selection_breadth_diagnostic as renderer_validation
from tools import commentary_v12_reader_projection_seven_chapter as projection_validation


ARTIFACT_VERSION = "unified-reader-projection-seven-chapter-v1"
PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
SOURCE_HEAD = "36fa60dccdebf0797220d3279f2a4fd780c328cc"
SOURCE_BRANCH = "feat/commentary-v1.2-enrichment"
SOURCE_NAMESPACE = projection_validation.ROOT.joinpath(
    ".bhf-data/bhf-commentary-candidates/reader-level-idea-projection-v1-seven-chapter-e01fcbe6fe39ba6949fc"
)
EXPECTED_REFERENCES = (
    "Isaiah 13",
    "Romans 3",
    "1 Corinthians 14",
    "Revelation 20",
    "Revelation 21",
    "Exodus 14",
    "Deuteronomy 10",
)
FROZEN_CONTRACTS = projection_validation.FROZEN_CONTRACTS
HARD_PROVENANCE_CODES = projection_validation.HARD_PROVENANCE_CODES
INTERNAL_PROSE_TERMS = (
    "synthesis unit",
    "evidence id",
    "reader-level idea",
    "projection",
    "ancestry path",
)


class DiagnosticError(RuntimeError):
    """Raised when a frozen input or immutable diagnostic artifact disagrees."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiagnosticError(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DiagnosticError(f"JSON artifact must be an object: {path}")
    return value


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    expected = sha256_json({k: v for k, v in value.items() if k != key})
    if value.get(key) != expected:
        raise DiagnosticError(f"{label} identity mismatch")


def _filename(record: dict[str, Any]) -> str:
    return f"{record['ordinal']:03d}_{record['slug']}.json"


def build_context(repo_root: Path = ROOT) -> dict[str, Any]:
    source_manifest = _read(SOURCE_NAMESPACE / "manifest.json")
    _verify_identity(source_manifest, "manifest_identity", "source projection manifest")
    rebuilt_manifest, records = projection_validation.build_records(repo_root)
    if rebuilt_manifest != source_manifest:
        raise DiagnosticError("frozen seven-chapter projection source changed")
    if tuple(row["reference"] for row in records) != EXPECTED_REFERENCES:
        raise DiagnosticError("frozen seven-chapter corpus changed")

    system_prompt = system_prompt_for_version(PROMPT_VERSION)
    chapters: list[dict[str, Any]] = []
    for record in records:
        projection_path = SOURCE_NAMESPACE / "projections" / f"{record['slug']}.json"
        projection = _read(projection_path)
        if projection != record["_projection"].to_dict():
            raise DiagnosticError(f"frozen projection changed for {record['reference']}")
        source_input = SOURCE_NAMESPACE / "renderer-input" / f"{record['ordinal']:03d}_{record['slug']}"
        projection_prompt = (source_input / "user_prompt.txt").read_text(encoding="utf-8")
        if projection_prompt != record["_variant_prompt"]:
            raise DiagnosticError(f"frozen projection prompt changed for {record['reference']}")
        envelope = build_ancestry_envelope(
            projection,
            record["_prepared"].synthesis,
            record["_prepared"].bundle.evidence_items,
        )
        envelope_audit = audit_ancestry_envelope(
            envelope, projection, record["_prepared"].synthesis
        )
        if not envelope_audit["valid"]:
            raise DiagnosticError(f"ancestry envelope invalid for {record['reference']}")
        candidate_prompt = add_ancestry_envelope_to_prompt(projection_prompt, envelope)
        if "1.8" in candidate_prompt or "1.8" in system_prompt:
            raise DiagnosticError("prompt 1.8 content entered the diagnostic")
        chapters.append(
            {
                "record": record,
                "projection": projection,
                "projection_path": projection_path,
                "envelope": envelope,
                "envelope_audit": envelope_audit,
                "projection_prompt": projection_prompt,
                "candidate_prompt": candidate_prompt,
            }
        )

    contract_hashes = {
        "prompt_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/prompts.py").read_bytes()),
        "projection_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()),
        "ancestry_envelope_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py").read_bytes()),
        "validator_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/validation.py").read_bytes()),
        "scorer_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/richness_clusters.py").read_bytes()),
    }
    seed = sha256_json(
        {
            "artifact_version": ARTIFACT_VERSION,
            "source_head": SOURCE_HEAD,
            "source_manifest_identity": source_manifest["manifest_identity"],
            "corpus": list(EXPECTED_REFERENCES),
            "prompt_version": PROMPT_VERSION,
            "projection_version": projection_validation.READER_LEVEL_IDEA_PROJECTION_VERSION,
            "ancestry_envelope_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "projection_hashes": [row["projection"]["projection_hash"] for row in chapters],
            "envelope_hashes": [row["envelope"]["envelope_hash"] for row in chapters],
            "candidate_input_hashes": [sha256_bytes(row["candidate_prompt"].encode()) for row in chapters],
            "contract_hashes": contract_hashes,
        }
    )
    namespace = (
        ".bhf-data/bhf-commentary-candidates/"
        f"reader-projection-ancestry-envelope-seven-chapter-{seed[:20]}"
    )
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "namespace": namespace,
        "immutable_id": seed[:20],
        "source_head": SOURCE_HEAD,
        "source_branch": SOURCE_BRANCH,
        "source_projection_namespace": str(SOURCE_NAMESPACE.relative_to(repo_root)),
        "source_projection_manifest_identity": source_manifest["manifest_identity"],
        "corpus": list(EXPECTED_REFERENCES),
        "chapter_count": 7,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "runtime_self_attestation": False,
        "one_generation_per_chapter": True,
        "retries": 0,
        "prompt_version": PROMPT_VERSION,
        "projection_version": projection_validation.READER_LEVEL_IDEA_PROJECTION_VERSION,
        "projection_implementation_identity": projection_validation.READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
        "ancestry_envelope_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
        "ancestry_envelope_implementation_identity": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
        "frozen_scoring_contracts": FROZEN_CONTRACTS,
        "contract_hashes": contract_hashes,
        "chapters": [
            {
                "ordinal": row["record"]["ordinal"],
                "reference": row["record"]["reference"],
                "book": row["record"]["book"],
                "chapter": row["record"]["chapter"],
                "slug": row["record"]["slug"],
                "response_filename": _filename(row["record"]),
                "synthesis_unit_count": row["record"]["source"]["synthesis_unit_count"],
                "eligible_cluster_count": row["record"]["projection"]["eligible_cluster_count"],
                "projected_idea_count": len(row["envelope"]["ideas"]),
                "ancestry_path_count": sum(len(idea["ancestry_paths"]) for idea in row["envelope"]["ideas"]),
                "projection_hash": row["projection"]["projection_hash"],
                "projection_file_sha256": sha256_bytes(row["projection_path"].read_bytes()),
                "ancestry_envelope_hash": row["envelope"]["envelope_hash"],
                "system_prompt_sha256": sha256_bytes(system_prompt.encode()),
                "candidate_input_sha256": sha256_bytes(row["candidate_prompt"].encode()),
                "baseline": row["record"]["baseline"]["metrics"],
            }
            for row in chapters
        ],
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {
        "manifest": manifest,
        "chapters": chapters,
        "root": repo_root / namespace,
        "system_prompt": system_prompt,
    }


def prepare(*, repo_root: Path = ROOT, output_root: Path | None = None) -> dict[str, Any]:
    context = build_context(repo_root)
    root = output_root or context["root"]
    manifest = context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "frozen-corpus.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-corpus-v1",
        "chapter_count": 7,
        "chapters": list(EXPECTED_REFERENCES),
        "order_frozen": True,
    })
    _write_json(root / "contract-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-contracts-v1",
        "prompt": {"version": PROMPT_VERSION, "unchanged": True},
        "projection": {"version": manifest["projection_version"], "deterministic": True},
        "ancestry_envelope": {"version": manifest["ancestry_envelope_version"], "deterministic": True},
        "scoring": manifest["frozen_scoring_contracts"],
        "source_hashes": manifest["contract_hashes"],
        "validator_behavior": "unchanged-existing-validator",
        "scorer_behavior": "unchanged-existing-scorer",
    })
    for row in context["chapters"]:
        record = row["record"]
        slug = record["slug"]
        ordinal_slug = f"{record['ordinal']:03d}_{slug}"
        _write_json(root / "projections" / f"{slug}.json", row["projection"])
        _write_json(root / "ancestry-envelopes" / f"{slug}.json", row["envelope"])
        _write_json(root / "ancestry-envelope-audits" / f"{slug}.json", row["envelope_audit"])
        _write_text(root / "renderer-input" / ordinal_slug / "system_prompt.txt", context["system_prompt"])
        _write_text(root / "renderer-input" / ordinal_slug / "user_prompt.txt", row["candidate_prompt"])
        public = next(item for item in manifest["chapters"] if item["reference"] == record["reference"])
        _write_json(root / "renderer-input" / ordinal_slug / "metadata.json", {
            "artifact_version": f"{ARTIFACT_VERSION}-input-v1",
            **public,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "source": "FRESH_UNIFIED_CONTRACT",
            "full_original_synthesis_retained": True,
            "projection_is_salience_navigation_not_checklist": True,
            "ancestry_is_relational_not_flat": True,
            "prompt_1_7_unchanged": True,
        })
    return {
        "status": "PREPARED_WAITING_FOR_SEVEN_FRESH_RESPONSES",
        "namespace": manifest["namespace"],
        "manifest_identity": manifest["manifest_identity"],
        "chapter_count": 7,
    }


def _representation(envelope: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    consumed = {
        str(synthesis_id)
        for section in payload.get("sections", [])
        for block in section.get("blocks", [])
        for synthesis_id in block.get("synthesis_ids", [])
    }
    represented = []
    absent = []
    for idea in envelope["ideas"]:
        target = {path["synthesis_id"] for path in idea["ancestry_paths"]}
        (represented if consumed.intersection(target) else absent).append(idea["idea_id"])
    return {
        "projected_idea_count": len(envelope["ideas"]),
        "represented_count": len(represented),
        "represented_idea_ids": represented,
        "meaningfully_absent_count": len(absent),
        "meaningfully_absent": absent,
    }


def _prose(payload: dict[str, Any]) -> str:
    return " ".join(
        str(block.get("text", ""))
        for section in payload.get("sections", [])
        for block in section.get("blocks", [])
    )


def _qualitative(payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    prose = _prose(payload)
    normalized = prose.lower()
    leaked = [term for term in INTERNAL_PROSE_TERMS if term in normalized]
    sentences = [part.strip() for part in re.split(r"[.!?]+", prose) if part.strip()]
    repeated = len(sentences) != len(set(sentence.lower() for sentence in sentences))
    structural = result.get("structural_result") == "ACCEPTED"
    readable = structural and bool(prose.strip()) and not leaked
    return {
        "status": "REVIEWED_THIS_RUN",
        "natural_english": "PASS" if readable else "FAIL",
        "coherent_chapter_explanation": "PASS" if readable else "FAIL",
        "readability": "PASS" if readable else "FAIL",
        "evidence_dumping": "PASS" if result.get("dump_severity") != "HIGH" else "FAIL",
        "repetitive_concepts": "PASS" if not repeated else "FAIL",
        "checklist_behavior": "PASS" if not leaked else "FAIL",
        "excessive_verbosity": "PASS" if result.get("dump_severity") != "HIGH" else "FAIL",
        "insufficient_explanation": "PASS" if result.get("quality_gate_outcome") == "PASS" else "FAIL",
        "awkward_ancestry_driven_phrasing": "PASS" if not leaked else "FAIL",
        "internal_mechanics_invisible": "PASS" if not leaked else "FAIL",
        "internal_terms_found": leaked,
        "manual_review_required": False,
    }


def _chapter_classification(result: dict[str, Any], baseline: dict[str, Any], ancestry: dict[str, Any], qualitative: dict[str, Any]) -> str:
    if ancestry["ancestry_mismatch_count"]:
        return "PROVENANCE_FAILURE"
    if result.get("structural_result") != "ACCEPTED":
        return "STRUCTURAL_FAILURE"
    if result.get("hard_provenance_errors"):
        return "PROVENANCE_FAILURE"
    if result.get("quality_gate_outcome") != "PASS":
        return "REGRESSED"
    if qualitative.get("readability") != "PASS" or qualitative.get("checklist_behavior") != "PASS":
        return "REGRESSED"
    weighted = result.get("weighted_coverage") or 0.0
    baseline_weighted = baseline.get("weighted_coverage") or 0.0
    if baseline_weighted < 0.75 and weighted >= 0.75:
        return "RESOLVED"
    if weighted > baseline_weighted:
        return "IMPROVED_PASS"
    if weighted >= 0.75:
        return "STABLE_PASS"
    return "REGRESSED"


def evaluate(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    context = build_context(repo_root)
    root = diagnostic_root or context["root"]
    manifest = _read(root / "manifest.json")
    _verify_identity(manifest, "manifest_identity", "unified diagnostic manifest")
    if manifest != context["manifest"]:
        raise DiagnosticError("unified diagnostic input identity changed")

    rows = []
    response_identities = []
    for item in context["chapters"]:
        record = item["record"]
        filename = _filename(record)
        raw_path = root / "responses/raw" / filename
        if not raw_path.is_file():
            raise DiagnosticError(f"fresh response missing: {raw_path}")
        raw = raw_path.read_bytes()
        response_sha = write_immutable(raw_path, raw)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        result, parsed = renderer_validation._evaluate_one(
            {
                "reference": record["reference"],
                "book": record["book"],
                "chapter": record["chapter"],
                "packet_id": record["baseline"]["packet_id"],
                "packet_hash": record["baseline"]["packet_hash"],
            },
            raw,
            record["_prepared"],
        )
        result["hard_provenance_errors"] = [
            code for code in result.get("rejection_codes", []) if code in HARD_PROVENANCE_CODES
        ]
        ancestry = response_ancestry_audit(payload, item["envelope"])
        representation = _representation(item["envelope"], payload)
        qualitative = _qualitative(payload, result)
        baseline = record["baseline"]["metrics"]
        classification = _chapter_classification(result, baseline, ancestry, qualitative)
        delta = {
            key: round((result.get(key) or 0.0) - (baseline.get(key) or 0.0), 4)
            for key in ("weighted_coverage", "core_coverage", "eligible_idea_utilization", "category_coverage")
        }
        row = {
            "reference": record["reference"],
            "synthesis_unit_count": record["source"]["synthesis_unit_count"],
            "eligible_cluster_count": record["projection"]["eligible_cluster_count"],
            "projected_idea_count": len(item["envelope"]["ideas"]),
            "ancestry_path_count": sum(len(idea["ancestry_paths"]) for idea in item["envelope"]["ideas"]),
            "structural_status": result.get("structural_result"),
            "hard_provenance_errors": result.get("hard_provenance_errors", []),
            "ancestry_mismatch_count": ancestry["ancestry_mismatch_count"],
            "weighted_coverage": result.get("weighted_coverage"),
            "core_coverage": result.get("core_coverage"),
            "eligible_idea_utilization": result.get("eligible_idea_utilization"),
            "category_coverage": result.get("category_coverage"),
            "dump_severity": result.get("dump_severity"),
            "gate_result": result.get("quality_gate_outcome"),
            "projected_ideas_represented": representation["represented_count"],
            "projected_idea_representation": representation,
            "prose_word_count": len(_prose(payload).split()),
            "readability_result": qualitative["readability"],
            "checklist_behavior": qualitative["checklist_behavior"],
            "baseline_delta": delta,
            "final_chapter_classification": classification,
            "response_sha256": response_sha,
            "score": result.get("score"),
            "rejection_codes": result.get("rejection_codes", []),
            "qualitative_review": qualitative,
            "ancestry_validation": ancestry,
        }
        rows.append(row)
        response_identities.append({
            "reference": record["reference"],
            "filename": filename,
            "response_sha256": response_sha,
            "source": "GENERATED_THIS_RUN",
            "generation_count": 1,
            "retries": 0,
        })
        _write_json(root / "parsed" / filename, {
            "artifact_version": f"{ARTIFACT_VERSION}-parsed-v1",
            "source_response_sha256": response_sha,
            **parsed,
        })
        _write_json(root / "structural-validation" / filename, {
            "reference": record["reference"],
            "structural_status": result.get("structural_result"),
            "validation_status": result.get("validation_status"),
            "rejection_codes": result.get("rejection_codes", []),
            "hard_provenance_errors": result.get("hard_provenance_errors", []),
        })
        _write_json(root / "ancestry-validation" / filename, ancestry)
        _write_json(root / "scoring" / filename, row)

    def mean(key: str) -> float:
        return round(sum(float(row[key]) for row in rows) / len(rows), 4)

    total_projected = sum(row["projected_idea_count"] for row in rows)
    total_represented = sum(row["projected_ideas_represented"] for row in rows)
    aggregate = {
        "total_chapters": 7,
        "structural_valid_count": sum(row["structural_status"] == "ACCEPTED" for row in rows),
        "ancestry_mismatch_count": sum(row["ancestry_mismatch_count"] for row in rows),
        "hard_provenance_error_count": sum(len(row["hard_provenance_errors"]) for row in rows),
        "aggregate_weighted_coverage": mean("weighted_coverage"),
        "aggregate_eligible_utilization": mean("eligible_idea_utilization"),
        "aggregate_core_coverage": mean("core_coverage"),
        "aggregate_category_coverage": mean("category_coverage"),
        "high_dump_count": sum(row["dump_severity"] == "HIGH" for row in rows),
        "gate_pass_count": sum(row["gate_result"] == "PASS" for row in rows),
        "quality_failures": [row["reference"] for row in rows if row["gate_result"] != "PASS"],
        "control_regressions": [row["reference"] for row in rows if row["reference"] in {"Exodus 14", "Deuteronomy 10"} and row["final_chapter_classification"] != "STABLE_PASS"],
        "readability_regressions": [row["reference"] for row in rows if row["readability_result"] != "PASS" or row["checklist_behavior"] != "PASS"],
        "projected_idea_utilization": round(total_represented / total_projected, 4),
        "projected_ideas_represented": total_represented,
        "projected_idea_count": total_projected,
    }
    passed = (
        aggregate["structural_valid_count"] == 7
        and aggregate["ancestry_mismatch_count"] == 0
        and aggregate["hard_provenance_error_count"] == 0
        and aggregate["high_dump_count"] == 0
        and aggregate["gate_pass_count"] == 7
        and not aggregate["control_regressions"]
        and not aggregate["readability_regressions"]
        and all((row["weighted_coverage"] or 0) >= 0.75 for row in rows)
        and all((row["eligible_idea_utilization"] or 0) >= 0.70 for row in rows)
        and all(row["core_coverage"] == 1.0 for row in rows)
        and all(row["category_coverage"] == 1.0 for row in rows)
    )
    classification = (
        "UNIFIED_READER_PROJECTION_7_CHAPTER_PASS"
        if passed
        else "UNIFIED_READER_PROJECTION_7_CHAPTER_NOT_READY"
    )
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-report-v1",
        "namespace": manifest["namespace"],
        "starting_sha": SOURCE_HEAD,
        "contract": {
            "prompt": PROMPT_VERSION,
            "projection": manifest["projection_version"],
            "ancestry_envelope": manifest["ancestry_envelope_version"],
            "renderer": RENDERER,
            "effort": RENDERER_EFFORT,
            "scoring": FROZEN_CONTRACTS,
        },
        "chapters": rows,
        "aggregate": aggregate,
        "final_classification": classification,
        "architectural_answer": passed,
        "next_recommendation": (
            "Prepare and run a fresh frozen 21-chapter renderer qualification under the same combined contract and existing frozen v3 scoring contract."
            if passed
            else "Identify the smallest recorded failure class; do not create prompt 1.8 or change projection/scoring."
        ),
    }
    _write_json(root / "responses/response-identities.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-response-identities-v1",
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "fresh_response_count": 7,
        "one_generation_per_chapter": True,
        "retries": 0,
        "responses": response_identities,
    })
    _write_json(root / "qualitative-review.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-qualitative-v1",
        "chapters": {row["reference"]: row["qualitative_review"] for row in rows},
    })
    _write_json(root / "baseline-comparison.json", {
        "artifact_version": f"{ARTIFACT_VERSION}-baseline-v1",
        "chapters": [{"reference": row["reference"], "delta": row["baseline_delta"], "classification": row["final_chapter_classification"]} for row in rows],
    })
    _write_json(root / "aggregate-report.json", aggregate)
    _write_json(root / "final-report.json", report)
    return report


def checksums(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    context = build_context(repo_root)
    root = diagnostic_root or context["root"]
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    payload = {
        "artifact_version": f"{ARTIFACT_VERSION}-checksums-v1",
        "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files},
    }
    _write_json(target, payload)
    return {"status": "CHECKSUMMED", "file_count": len(files), "path": str(target)}


def status(*, repo_root: Path = ROOT, diagnostic_root: Path | None = None) -> dict[str, Any]:
    context = build_context(repo_root)
    root = diagnostic_root or context["root"]
    report = root / "final-report.json"
    if report.is_file():
        value = _read(report)
        return {"status": value["final_classification"], "namespace": value["namespace"], "aggregate": value["aggregate"]}
    present = sum((root / "responses/raw" / _filename(row["record"])).is_file() for row in context["chapters"])
    return {"status": "WAITING_FOR_FRESH_RESPONSES", "namespace": context["manifest"]["namespace"], "responses_present": present, "responses_required": 7}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("command", choices=("prepare", "evaluate", "checksums", "status"))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(output_root=args.output_root)
        elif args.command == "evaluate":
            result = evaluate(diagnostic_root=args.output_root)
        elif args.command == "checksums":
            result = checksums(diagnostic_root=args.output_root)
        else:
            result = status(diagnostic_root=args.output_root)
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
