#!/usr/bin/env python3
"""Freeze and audit the seven-chapter reader-idea projection validation.

This harness is deliberately downstream of the existing prompt-1.7 diagnostic.
It creates immutable projection inputs and a fail-closed comparison record.  It
does not call a renderer, change prompt 1.7, alter synthesis/evidence routing,
or change scoring.  The previously generated Revelation 21 projection
candidate may be reused; all other candidate responses remain absent until an
authorized GPT-5.6 Sol medium renderer exchange supplies them.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_level_projection import (
    READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
    READER_LEVEL_IDEA_PROJECTION_VERSION,
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    cluster_synthesis_units,
)
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from tools import commentary_renderer_selection_breadth_diagnostic as prompt17


ARTIFACT_VERSION = "reader-level-idea-projection-seven-chapter-validation-v1"
PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
START_SHA = "cc4b485c529b7a67597be471418b72669bdf6e2e"
BRANCH = "feat/commentary-v1.2-enrichment"
PROMPT_17_ID = "renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1"
PROMPT_17_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates" / PROMPT_17_ID
EXPECTED_REFERENCES = prompt17.EXPECTED_REFERENCES
FROZEN_CONTRACTS = {
    "essential_passage_context": CORE_CLASSIFIER_V2,
    "reader_relevance_eligibility": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    "richness_clusters": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    "richness_policy": RICHNESS_POLICY_VERSION_V3,
    "gate": RICHNESS_GATE_V2_VERSION,
}
REUSED_REVELATION_21_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates"
    / "reader-level-idea-projection-v1-1d7761ad8f69c739e395"
    / "renderer-experiment"
)
REUSED_REVELATION_21_RESPONSE = REUSED_REVELATION_21_ROOT / "responses/raw/revelation_021.json"
REUSED_REVELATION_21_SHA256 = (
    "6ef87cb24cd3bec64653019ccbe8f4ac47e9320b6b8e0614c252c66caef88080"
)
HARD_PROVENANCE_CODES = frozenset(
    {
        "UNKNOWN_EVIDENCE_ID",
        "UNKNOWN_SYNTHESIS_ID",
        "SYNTHESIS_ANCESTRY_MISMATCH",
        "SYNTHESIS_HASH_MISMATCH",
        "CONFIDENCE_EXCEEDS_EVIDENCE",
        "DISPUTED_AS_FACT",
        "INVENTED_SIGNIFICANCE",
        "UNSUPPORTED_DATE",
        "UNSUPPORTED_ENTITY",
        "UNANCHORED_CLAIM",
        "OUT_OF_CHAPTER_SYNTHESIS_REFERENCE",
    }
)


class ValidationError(RuntimeError):
    """The frozen validation inputs or reused candidate are inconsistent."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON artifact must be an object: {path}")
    return value


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    expected = sha256_json({k: v for k, v in value.items() if k != key})
    if value.get(key) != expected:
        raise ValidationError(f"{label} identity mismatch")


def _baseline_context(repo_root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _read(PROMPT_17_ROOT / "manifest.json")
    _verify_identity(manifest, "manifest_identity", "prompt-1.7 baseline")
    if manifest.get("diagnostic_id") != PROMPT_17_ID:
        raise ValidationError("prompt-1.7 diagnostic identity changed")
    if manifest.get("chapter_count") != 7:
        raise ValidationError("prompt-1.7 baseline is not exactly seven chapters")
    if [row.get("reference") for row in manifest.get("chapters", [])] != list(EXPECTED_REFERENCES):
        raise ValidationError("prompt-1.7 baseline chapter order or membership changed")
    contracts = manifest.get("contract_versions", {})
    expected_contracts = {
        "renderer_prompt_version": PROMPT_VERSION,
        "commentary_schema_version": "1.2",
        "synthesis_schema_version": "1.1",
        "synthesis_compiler_version": "1.1",
        "core_classifier_version": CORE_CLASSIFIER_V2,
        "reader_relevance_eligibility_classifier_version": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
        "richness_clustering_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
        "richness_policy_version": RICHNESS_POLICY_VERSION_V3,
        "gate_version": RICHNESS_GATE_V2_VERSION,
    }
    if contracts != expected_contracts:
        raise ValidationError(f"frozen prompt/scoring contracts changed: {contracts!r}")
    current, _ = prompt17.build_manifest(repo_root)
    if current != manifest:
        raise ValidationError("prompt-1.7 baseline inputs changed before projection validation")
    evaluation = _read(PROMPT_17_ROOT / "evaluation/evaluation.json")
    if evaluation.get("diagnostic_id") != PROMPT_17_ID:
        raise ValidationError("prompt-1.7 baseline evaluation identity changed")
    return manifest, evaluation


def _projection_for(prepared: Any) -> Any:
    chapter_text = bible.passage_text(
        bible.resolve_chapter(prepared.synthesis.book, prepared.synthesis.chapter)["verses"]
    )
    clusters = cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=chapter_text,
    )
    return project_reader_level_ideas(
        prepared.synthesis,
        clusters,
        prepared.bundle.evidence_items,
    )


def build_records(repo_root: Path = ROOT) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Rebuild all seven projections and verify every original prompt hash."""

    baseline_manifest, baseline_evaluation = _baseline_context(repo_root)
    baseline_by_ref = {row["reference"]: row for row in baseline_manifest["chapters"]}
    baseline_eval_by_ref = {
        row["reference"]: row for row in baseline_evaluation.get("chapters", [])
    }
    system_prompt = system_prompt_for_version(PROMPT_VERSION)
    system_hash = sha256_bytes(system_prompt.encode("utf-8"))
    records: list[dict[str, Any]] = []
    for ordinal, reference in enumerate(EXPECTED_REFERENCES, 1):
        row = baseline_by_ref[reference]
        prepared = prepare_chapter(row["book"], int(row["chapter"]))
        chapter = bible.resolve_chapter(row["book"], int(row["chapter"]))
        chapter_text = bible.passage_text(chapter["verses"])
        original_prompt = build_user_prompt(
            reference,
            row["book"],
            int(row["chapter"]),
            chapter_text,
            prepared.synthesis,
            prepared.bundle,
            prepared.synthesis.evidence_availability,
            prompt_version=PROMPT_VERSION,
        )
        if sha256_bytes(original_prompt.encode("utf-8")) != row["user_prompt_sha256"]:
            raise ValidationError(f"prompt 1.7 user prompt changed for {reference}")
        if system_hash != row["system_prompt_sha256"]:
            raise ValidationError(f"prompt 1.7 system prompt changed for {reference}")
        projection = _projection_for(prepared)
        variant_prompt = add_projection_to_prompt(original_prompt, projection)
        if "DISTINCT READER-LEVEL IDEAS" not in variant_prompt:
            raise ValidationError(f"projection section missing for {reference}")
        if "COMPILED CHAPTER SYNTHESIS:" not in variant_prompt:
            raise ValidationError(f"full synthesis missing from variant for {reference}")
        if "1.8" in variant_prompt or "1.8" in system_prompt:
            raise ValidationError("prompt 1.8 content entered the experiment")
        projection_dict = projection.to_dict()
        reused = reference == "Revelation 21"
        # The overall prompt-1.7 evaluation stores the candidate metrics
        # directly on each chapter row; the per-chapter files store the
        # before/after comparison wrapper instead.
        baseline_eval = baseline_eval_by_ref[reference]
        records.append(
            {
                "ordinal": ordinal,
                "reference": reference,
                "book": row["book"],
                "chapter": int(row["chapter"]),
                "slug": slug(row["book"], int(row["chapter"])),
                "baseline": {
                    "diagnostic_id": PROMPT_17_ID,
                    "packet_filename": row["packet_filename"],
                    "packet_id": row["packet_id"],
                    "packet_hash": row["packet_hash"],
                    "packet_file_sha256": row["packet_file_sha256"],
                    "system_prompt_sha256": row["system_prompt_sha256"],
                    "user_prompt_sha256": row["user_prompt_sha256"],
                    "response_path": str(
                        (PROMPT_17_ROOT / "responses/raw" / row["response_filename"]).relative_to(ROOT)
                    ),
                    "response_sha256": sha256_bytes(
                        (PROMPT_17_ROOT / "responses/raw" / row["response_filename"]).read_bytes()
                    ),
                    "parsed_path": str(
                        (PROMPT_17_ROOT / "parsed" / row["response_filename"]).relative_to(ROOT)
                    ),
                    "evaluation_path": str(
                        (PROMPT_17_ROOT / "evaluation/chapters" / row["response_filename"]).relative_to(ROOT)
                    ),
                    "metrics": baseline_eval,
                },
                "source": {
                    "evidence_hash": prepared.bundle.evidence_hash,
                    "synthesis_hash": prepared.synthesis.synthesis_hash,
                    "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
                    "evidence_availability": prepared.synthesis.evidence_availability,
                },
                "prompt": {
                    "version": PROMPT_VERSION,
                    "system_prompt_sha256": system_hash,
                    "original_user_prompt_sha256": sha256_bytes(original_prompt.encode("utf-8")),
                    "variant_user_prompt_sha256": sha256_bytes(variant_prompt.encode("utf-8")),
                },
                "projection": {
                    "projection_hash": projection.projection_hash,
                    "projection_version": projection.projection_version,
                    "implementation_identity": projection.implementation_identity,
                    "synthesis_unit_count": projection.source_synthesis_unit_count,
                    "eligible_cluster_count": projection.eligible_cluster_count,
                    "projected_idea_count": len(projection.ideas),
                    "core_idea_count": sum(idea.importance == "CORE" for idea in projection.ideas),
                    "relevant_idea_count": sum(idea.importance == "RELEVANT" for idea in projection.ideas),
                    "grouped_relationship_count": sum(
                        audit.decision == "GROUP" for audit in projection.pair_audit
                    ),
                    "ambiguous_cluster_count": len(projection.ambiguous_cluster_ids),
                    "ancestry_preserved": all(
                        projection.ancestry_audit[key]
                        for key in (
                            "eligible_cluster_ids_preserved",
                            "synthesis_unit_ids_preserved",
                            "evidence_ids_preserved",
                        )
                    ),
                },
                "candidate": {
                    "status": "REUSED_EXISTING_IMMUTABLE" if reused else "AWAITING_EXTERNAL_RENDERER",
                    "renderer": RENDERER,
                    "renderer_effort": RENDERER_EFFORT,
                    "generation_count": 1 if reused else 0,
                    "response_path": (
                        str(REUSED_REVELATION_21_RESPONSE.relative_to(ROOT)) if reused else None
                    ),
                    "response_sha256": REUSED_REVELATION_21_SHA256 if reused else None,
                    "candidate_id": (
                        f"{READER_LEVEL_IDEA_PROJECTION_VERSION}-candidate:{REUSED_REVELATION_21_SHA256}"
                        if reused
                        else None
                    ),
                    "selective_retry": False,
                },
                "_prepared": prepared,
                "_projection": projection,
                "_original_prompt": original_prompt,
                "_variant_prompt": variant_prompt,
            }
        )
    seed = sha256_json(
        {
            "artifact_version": ARTIFACT_VERSION,
            "start_sha": START_SHA,
            "branch": BRANCH,
            "prompt_17_diagnostic_id": PROMPT_17_ID,
            "prompt_17_manifest_identity": baseline_manifest["manifest_identity"],
            "prompt_version": PROMPT_VERSION,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
            "validation_harness_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "projection_implementation_sha256": _projection_implementation_sha256(),
            "projection_hashes": [record["projection"]["projection_hash"] for record in records],
            "variant_prompt_hashes": [record["prompt"]["variant_user_prompt_sha256"] for record in records],
            "contracts": FROZEN_CONTRACTS,
        }
    )
    public_manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "namespace": f".bhf-data/bhf-commentary-candidates/{READER_LEVEL_IDEA_PROJECTION_VERSION}-seven-chapter-{seed[:20]}",
        "immutable_id": seed[:20],
        "source_branch": BRANCH,
        "source_head": START_SHA,
        "prompt_17_diagnostic_id": PROMPT_17_ID,
        "prompt_17_manifest_identity": baseline_manifest["manifest_identity"],
        "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "projection_implementation_identity": READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
        "projection_implementation_sha256": _projection_implementation_sha256(),
        "validation_harness_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "frozen_contracts": FROZEN_CONTRACTS,
        "chapter_count": len(records),
        "chapters": [
            {
                key: value
                for key, value in record.items()
                if not key.startswith("_")
            }
            for record in records
        ],
        "generation_policy": {
            "one_generation_per_chapter": True,
            "selective_retries": False,
            "runtime_self_attestation": False,
            "external_renderer_required": True,
        },
    }
    public_manifest["manifest_identity"] = sha256_json(public_manifest)
    return public_manifest, records


def _projection_implementation_sha256() -> str:
    return sha256_bytes(
        (ROOT / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()
    )


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def _candidate_eval(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = REUSED_REVELATION_21_RESPONSE.read_bytes()
    if sha256_bytes(raw) != REUSED_REVELATION_21_SHA256:
        raise ValidationError("reused Revelation 21 candidate response hash changed")
    result, parsed = prompt17._evaluate_one(
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
    return result, parsed


def _projected_representation(record: dict[str, Any], candidate_result: dict[str, Any]) -> dict[str, Any]:
    raw = REUSED_REVELATION_21_RESPONSE.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    consumed = {
        synthesis_id
        for section in payload.get("sections", [])
        for block in section.get("blocks", [])
        for synthesis_id in block.get("synthesis_ids", [])
    }
    ideas = record["_projection"].ideas
    represented = [
        idea.idea_id
        for idea in ideas
        if consumed.intersection(idea.synthesis_unit_ids)
    ]
    absent = [idea.idea_id for idea in ideas if idea.idea_id not in represented]
    return {
        "projected_idea_count": len(ideas),
        "represented_by_consumed_synthesis_ancestry": represented,
        "meaningfully_absent": absent,
        "represented_count": len(represented),
        "meaningfully_absent_count": len(absent),
        "interpretation": (
            "The prior immutable qualitative audit confirms substantive representation; "
            "this ancestry intersection is an auditable lower-level check."
            if not absent
            else "No substantive representation claim is made for absent ideas."
        ),
        "candidate_word_count": candidate_result.get("word_count"),
    }


def _comparison_markdown(records: list[dict[str, Any]], evaluated: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# Seven-chapter reader-level idea projection comparison",
        "",
        "Candidate generation was incomplete because no authorized GPT-5.6 Sol renderer endpoint or response bundle was available. Revelation 21 reuses its immutable prior candidate; the other six candidate rows remain pending.",
        "",
        "| Chapter | Baseline weighted | Candidate weighted | Baseline eligible | Candidate eligible | Core | Category | Dump | Gate | Result |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for record in records:
        baseline = record["baseline"]["metrics"]
        candidate = evaluated.get(record["reference"])
        def fmt(value: Any) -> str:
            return f"{value:.4f}" if isinstance(value, (int, float)) else "—"
        if candidate:
            result = "REUSED_PRIOR_CANDIDATE"
            candidate_weighted = candidate.get("weighted_coverage")
            candidate_eligible = candidate.get("eligible_idea_utilization")
            core = fmt(candidate.get("core_coverage"))
            category = fmt(candidate.get("category_coverage"))
            dump = candidate.get("dump_severity") or "—"
            gate = candidate.get("quality_gate_outcome") or "—"
        else:
            result = "AWAITING_EXTERNAL_RENDERER"
            candidate_weighted = None
            candidate_eligible = None
            core = category = dump = gate = "—"
        lines.append(
            f"| {record['reference']} | {fmt(baseline.get('weighted_coverage'))} | {fmt(candidate_weighted)} | {fmt(baseline.get('eligible_idea_utilization'))} | {fmt(candidate_eligible)} | {core} | {category} | {dump} | {gate} | {result} |"
        )
    return "\n".join(lines) + "\n"


def prepare(*, repo_root: Path = ROOT, output_root: Path | None = None) -> dict[str, Any]:
    manifest, records = build_records(repo_root)
    root = output_root or repo_root / manifest["namespace"]
    _write_json(root / "manifest.json", manifest)
    _write_json(
        root / "frozen-identities.json",
        {
            "source_head": START_SHA,
            "source_branch": BRANCH,
            "prompt_version": PROMPT_VERSION,
            "prompt_17_diagnostic_id": PROMPT_17_ID,
            "prompt_17_manifest_identity": manifest["prompt_17_manifest_identity"],
            "system_prompt_sha256": records[0]["prompt"]["system_prompt_sha256"],
            "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
            "projection_implementation_sha256": manifest["projection_implementation_sha256"],
            "frozen_contracts": FROZEN_CONTRACTS,
        },
    )
    evaluations: dict[str, dict[str, Any]] = {}
    qualitative: dict[str, dict[str, Any]] = {}
    for record in records:
        public = _public_record(record)
        _write_json(root / "projections" / f"{record['slug']}.json", record["_projection"].to_dict())
        _write_json(
            root / "grouping-audits" / f"{record['slug']}.json",
            {
                "reference": record["reference"],
                "projection_hash": record["projection"]["projection_hash"],
                "grouped_relationship_count": record["projection"]["grouped_relationship_count"],
                "projected_idea_count": record["projection"]["projected_idea_count"],
                "ambiguous_cluster_count": record["projection"]["ambiguous_cluster_count"],
                "decisions": [audit.to_dict() for audit in record["_projection"].pair_audit],
            },
        )
        _write_json(root / "ancestry-audits" / f"{record['slug']}.json", record["_projection"].ancestry_audit)
        handoff = root / "renderer-input" / f"{record['ordinal']:03d}_{record['slug']}"
        _write_text(handoff / "system_prompt.txt", system_prompt_for_version(PROMPT_VERSION))
        _write_text(handoff / "user_prompt.txt", record["_variant_prompt"])
        _write_json(
            handoff / "metadata.json",
            {
                **public,
                "status": record["candidate"]["status"],
                "full_original_synthesis_retained": True,
                "projection_input_is_additional_layer": True,
                "prompt_1_7_unchanged": True,
            },
        )
        if record["reference"] == "Revelation 21":
            raw = REUSED_REVELATION_21_RESPONSE.read_bytes()
            write_immutable(root / "responses/raw" / "005_revelation_021.json", raw)
            result, parsed = _candidate_eval(record)
            evaluations[record["reference"]] = result
            _write_json(
                root / "parsed" / "005_revelation_021.json",
                {
                    "artifact_version": f"{ARTIFACT_VERSION}-parsed-v1",
                    "source_response_sha256": REUSED_REVELATION_21_SHA256,
                    "reused_from": str(REUSED_REVELATION_21_RESPONSE.relative_to(ROOT)),
                    **parsed,
                },
            )
            _write_json(
                root / "evaluation/chapters" / "005_revelation_021.json",
                {
                    "reference": record["reference"],
                    "baseline": record["baseline"]["metrics"],
                    "candidate": result,
                    "prose_length_delta": result.get("word_count") - record["baseline"]["metrics"].get("word_count")
                    if isinstance(result.get("word_count"), int)
                    and isinstance(record["baseline"]["metrics"].get("word_count"), int)
                    else None,
                    "projection_representation": _projected_representation(record, result),
                    "result": "REUSED_PRIOR_IMMUTABLE_CANDIDATE",
                },
            )
            prior_review = _read(REUSED_REVELATION_21_ROOT / "final-report-v2.json")["qualitative_review"]
            qualitative[record["reference"]] = {
                "status": "REUSED_PRIOR_IMMUTABLE_REVIEW",
                **prior_review,
                "source_report": str((REUSED_REVELATION_21_ROOT / "final-report-v2.json").relative_to(ROOT)),
            }
        else:
            qualitative[record["reference"]] = {
                "status": "NOT_REVIEWED_CANDIDATE_NOT_GENERATED",
                "readability": None,
                "natural_english": None,
                "repetition": None,
                "evidence_inventory_feel": None,
                "checklist_like": None,
                "abrupt_transitions": None,
                "over_expansion": None,
                "under_explanation": None,
                "projection_helpfulness": None,
            }
    response_identity = {
        "artifact_version": f"{ARTIFACT_VERSION}-response-identity-v1",
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "one_generation_per_chapter": True,
        "responses": [record["candidate"] for record in records],
    }
    _write_json(root / "responses/response-identity.json", response_identity)
    _write_json(
        root / "responses/import-receipt.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-import-v1",
            "status": "PARTIAL_REUSE_EXTERNAL_RENDERER_REQUIRED",
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "imported_response_count": 1,
            "missing_response_count": 6,
            "raw_responses_immutable": True,
            "reused_reference": "Revelation 21",
            "missing_references": [
                record["reference"]
                for record in records
                if record["candidate"]["status"] == "AWAITING_EXTERNAL_RENDERER"
            ],
            "selective_retries": False,
        },
    )
    _write_json(
        root / "evaluation/qualitative-review.json",
        {
            "artifact_version": f"{ARTIFACT_VERSION}-qualitative-v1",
            "status": "INCOMPLETE_EXTERNAL_RENDERER_REQUIRED",
            "reviewed_candidate_count": sum(
                review["status"] == "REUSED_PRIOR_IMMUTABLE_REVIEW"
                for review in qualitative.values()
            ),
            "chapters": qualitative,
        },
    )
    _write_text(root / "comparison/before-after.md", _comparison_markdown(records, evaluations))
    aggregate = {
        "chapter_count": 7,
        "candidate_generation_count": sum(
            record["candidate"]["generation_count"] for record in records
        ),
        "candidate_evaluated_count": len(evaluations),
        "candidate_missing_count": 6,
        "candidate_validation_complete": False,
        "structural_validity": "INCOMPLETE_NOT_ASSESSED_FOR_SIX_CHAPTERS",
        "hard_provenance_errors": "INCOMPLETE_NOT_ASSESSED_FOR_SIX_CHAPTERS",
        "high_dump_count": "INCOMPLETE_NOT_ASSESSED_FOR_SIX_CHAPTERS",
        "core_regressions": "INCOMPLETE_NOT_ASSESSED_FOR_SIX_CHAPTERS",
        "sparse_controls": "INCOMPLETE_NOT_ASSESSED_FOR_SIX_CHAPTERS",
        "aggregate_weighted_coverage": None,
        "aggregate_eligible_idea_utilization": None,
    }
    final_report = {
        "artifact_version": f"{ARTIFACT_VERSION}-report-v1",
        "namespace": manifest["namespace"],
        "source_head": START_SHA,
        "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "prompt_version": PROMPT_VERSION,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "frozen_contracts": FROZEN_CONTRACTS,
        "chapters": [
            {
                **_public_record(record),
                "candidate_evaluation": evaluations.get(record["reference"]),
                "qualitative_review": qualitative[record["reference"]],
            }
            for record in records
        ],
        "aggregate": aggregate,
        "blocking_condition": (
            "No authorized GPT-5.6 Sol medium renderer endpoint or complete external response bundle is available in this workspace; six candidate generations were not attempted or substituted."
        ),
        "final_classification": "READER_IDEA_PROJECTION_7_CHAPTER_NOT_READY",
        "recommended_next_step": "Supply one exact GPT-5.6 Sol medium response for each of the six missing variant prompts, then create a fresh immutable evaluation namespace; do not reuse baseline responses as candidate responses and do not retry selectively.",
    }
    _write_json(root / "evaluation/evaluation.json", final_report)
    _write_json(root / "final-report.json", final_report)
    return {
        "status": "PREPARED_INCOMPLETE",
        "namespace": manifest["namespace"],
        "chapter_count": 7,
        "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "candidate_generated_count": aggregate["candidate_generation_count"],
        "candidate_missing_count": aggregate["candidate_missing_count"],
        "final_classification": final_report["final_classification"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="freeze seven projections and the authorized prior R21 candidate")
    sub.add_parser("status", help="show the immutable validation report status")
    args = parser.parse_args(argv)
    try:
        manifest, _ = build_records()
        root = args.output_root or ROOT / manifest["namespace"]
        if args.command == "prepare":
            result = prepare(output_root=args.output_root)
        else:
            if not (root / "final-report.json").is_file():
                result = {"status": "NOT_PREPARED", "namespace": manifest["namespace"]}
            else:
                report = _read(root / "final-report.json")
                result = {
                    "status": report["final_classification"],
                    "namespace": report["namespace"],
                    "candidate_generated_count": report["aggregate"]["candidate_generation_count"],
                    "candidate_missing_count": report["aggregate"]["candidate_missing_count"],
                }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, ArtifactCollisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
