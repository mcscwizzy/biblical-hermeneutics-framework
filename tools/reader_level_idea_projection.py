#!/usr/bin/env python3
"""Build the isolated reader-level idea projection diagnostic.

The tool reads the frozen prompt-1.7 packet authorities and current live
objects only to verify that their hashes match. It writes a new immutable
diagnostic namespace, never changes prompt 1.7/scoring/CKL/evidence routing,
and never calls a renderer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.commentary.production.models import canonical_json, sha256_bytes, sha256_json, write_immutable
from framework.commentary.production.inputs import prepare_chapter
from bhf_agent import bible
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_level_projection import (
    READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
    READER_LEVEL_IDEA_PROJECTION_VERSION,
    add_projection_to_prompt,
    project_reader_level_ideas,
    render_projection_input_section,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    cluster_synthesis_units,
)


PROMPT_17_ID = "renderer-remediation-prompt-1.7-selection-breadth-7e1f844705a27ef5d2a1"
PROMPT_17_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates" / PROMPT_17_ID
CHAPTERS = {
    "Revelation 21": {
        "book": "Revelation",
        "chapter": 21,
        "packet": "packets/005_revelation_021.json",
        "slug": "revelation_021",
        "baseline_evaluation": "evaluation/chapters/005_revelation_021.json",
        "baseline_raw": "responses/raw/005_revelation_021.json",
        "baseline_parsed": "parsed/005_revelation_021.json",
        "baseline_handoff": "handoff/005_revelation_021",
    },
    "Revelation 20": {
        "book": "Revelation",
        "chapter": 20,
        "packet": "packets/004_revelation_020.json",
        "slug": "revelation_020",
    },
    "Exodus 14": {
        "book": "Exodus",
        "chapter": 14,
        "packet": "packets/006_exodus_014.json",
        "slug": "exodus_014",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / ".bhf-data/bhf-commentary-candidates",
    )
    args = parser.parse_args()

    records = {reference: _build_record(reference, config) for reference, config in CHAPTERS.items()}
    implementation_hash = hashlib.sha256(
        (ROOT / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()
        + Path(__file__).read_bytes()
    ).hexdigest()
    input_fingerprint = sha256_json(
        {
            "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
            "implementation_identity": READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
            "implementation_sha256": implementation_hash,
            "prompt_17_id": PROMPT_17_ID,
            "chapters": {
                reference: {
                    "packet_id": record["packet"]["packet_id"],
                    "packet_hash": record["packet"]["packet_hash"],
                    "evidence_hash": record["packet"]["evidence_hash"],
                    "synthesis_hash": record["packet"]["synthesis_hash"],
                    "projection_hash": record["projection"]["projection_hash"],
                }
                for reference, record in records.items()
            },
        }
    )
    namespace = args.output_root / f"{READER_LEVEL_IDEA_PROJECTION_VERSION}-{input_fingerprint[:20]}"
    namespace.mkdir(parents=True, exist_ok=True)

    manifest = {
        "artifact_version": "reader-level-idea-projection-diagnostic-v1",
        "namespace": str(namespace.relative_to(ROOT)),
        "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "implementation_identity": READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
        "implementation_sha256": implementation_hash,
        "input_fingerprint": input_fingerprint,
        "source_branch": "feat/commentary-v1.2-enrichment",
        "source_head": "e8b8d737e8972dd4962e74014a01ce1eb01f4833",
        "prompt_17_diagnostic_id": PROMPT_17_ID,
        "frozen_contracts": {
            "core_classifier": CORE_CLASSIFIER_V2,
            "reader_relevance_eligibility": "reader-relevance-eligibility-v1",
            "richness_clusters": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
            "richness_policy": RICHNESS_POLICY_VERSION_V3,
            "gate": RICHNESS_GATE_V2_VERSION,
        },
        "chapters": {
            reference: {
                "slug": record["config"]["slug"],
                "projection_file": f"projections/{record['config']['slug']}.json",
                "report_file": f"chapter-reports/{record['config']['slug']}.md",
                "projection_hash": record["projection"]["projection_hash"],
                "source_packet_id": record["packet"]["packet_id"],
                "source_packet_hash": record["packet"]["packet_hash"],
                "original_user_prompt_sha256": record["original_user_prompt_sha256"],
                "variant_user_prompt_sha256": record.get("variant_user_prompt_sha256"),
            }
            for reference, record in records.items()
        },
        "renderer_experiment": "Revelation 21 only; prompt-1.7 + reader-level-idea-projection-v1",
        "candidate_generation_performed": False,
        "outcome": "READER_IDEA_PROJECTION_PREPARED_AWAITING_RENDERER",
    }
    _write_json(namespace / "manifest.json", manifest)

    for reference, record in records.items():
        slug = record["config"]["slug"]
        projection = record["projection"]
        _write_json(namespace / "projections" / f"{slug}.json", projection)
        _write_json(namespace / "grouping-audits" / f"{slug}.json", _grouping_audit(projection))
        _write_json(namespace / "ancestry-audits" / f"{slug}.json", projection["ancestry_audit"])
        _write_text(namespace / "chapter-reports" / f"{slug}.md", _chapter_report(reference, record))

    r21 = records["Revelation 21"]
    _write_renderer_handoff(namespace, r21)
    _write_json(namespace / "renderer-experiment" / "baseline-reference.json", _baseline_reference(r21))
    _write_json(namespace / "renderer-experiment" / "evaluation-comparison.json", _evaluation_comparison(r21))
    _write_json(namespace / "final-report.json", _final_report(namespace, records, input_fingerprint))

    print(json.dumps({
        "namespace": str(namespace.relative_to(ROOT)),
        "input_fingerprint": input_fingerprint,
        "outcome": "READER_IDEA_PROJECTION_PREPARED_AWAITING_RENDERER",
        "chapters": {
            reference: {
                "synthesis_units": record["projection"]["source_synthesis_unit_count"],
                "eligible_clusters": record["projection"]["eligible_cluster_count"],
                "projected_ideas": len(record["projection"]["ideas"]),
                "core_ideas": sum(idea["importance"] == "CORE" for idea in record["projection"]["ideas"]),
                "relevant_ideas": sum(idea["importance"] == "RELEVANT" for idea in record["projection"]["ideas"]),
                "grouped_pairs": sum(audit["decision"] == "GROUP" for audit in record["projection"]["pair_audit"]),
                "ambiguous_concepts": len(record["projection"]["ambiguous_cluster_ids"]),
                "ancestry_preserved": all(
                    record["projection"]["ancestry_audit"][key]
                    for key in (
                        "eligible_cluster_ids_preserved",
                        "synthesis_unit_ids_preserved",
                        "evidence_ids_preserved",
                    )
                ),
            }
            for reference, record in records.items()
        },
    }, indent=2, sort_keys=True))
    return 0


def _build_record(reference: str, config: dict[str, Any]) -> dict[str, Any]:
    packet = json.loads((PROMPT_17_ROOT / config["packet"]).read_text())
    prepared = prepare_chapter(config["book"], config["chapter"])
    chapter_text = bible.passage_text(
        bible.resolve_chapter(config["book"], config["chapter"])["verses"]
    )
    clusters = cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=chapter_text,
    )
    projection = project_reader_level_ideas(
        prepared.synthesis,
        clusters,
        prepared.bundle.evidence_items,
    ).to_dict()
    original_prompt = build_user_prompt(
        reference,
        config["book"],
        config["chapter"],
        chapter_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version="1.7",
    )
    original_system = system_prompt_for_version("1.7")
    _assert_frozen_packet(reference, packet, prepared, original_prompt, original_system)
    record: dict[str, Any] = {
        "config": config,
        "packet": packet,
        "projection": projection,
        "source_category_families": sorted(
            {
                category
                for cluster in clusters
                for category in getattr(cluster, "categories", [])
            }
        ),
        "projected_category_families": sorted(
            {category for idea in projection["ideas"] for category in idea["categories"]}
        ),
        "original_user_prompt": original_prompt,
        "original_system_prompt": original_system,
        "original_user_prompt_sha256": sha256_bytes(original_prompt.encode("utf-8")),
        "original_system_prompt_sha256": sha256_bytes(original_system.encode("utf-8")),
    }
    if reference == "Revelation 21":
        variant_prompt = add_projection_to_prompt(
            original_prompt,
            project_reader_level_ideas(
                prepared.synthesis,
                clusters,
                prepared.bundle.evidence_items,
            ),
        )
        record["variant_prompt"] = variant_prompt
        record["variant_user_prompt_sha256"] = sha256_bytes(variant_prompt.encode("utf-8"))
        record["projection_section_sha256"] = sha256_bytes(
            render_projection_input_section(
                project_reader_level_ideas(
                    prepared.synthesis,
                    clusters,
                    prepared.bundle.evidence_items,
                )
            ).encode("utf-8")
        )
    return record


def _assert_frozen_packet(reference: str, packet: dict[str, Any], prepared: Any, prompt: str, system: str) -> None:
    expected = {
        "evidence_hash": prepared.bundle.evidence_hash,
        "synthesis_hash": prepared.synthesis.synthesis_hash,
        "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
        "user_prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "system_prompt_sha256": sha256_bytes(system.encode("utf-8")),
    }
    for key, value in expected.items():
        if packet.get(key) != value:
            raise RuntimeError(f"{reference}: frozen packet mismatch for {key}: {packet.get(key)!r} != {value!r}")


def _grouping_audit(projection: dict[str, Any]) -> dict[str, Any]:
    audits = projection["pair_audit"]
    return {
        "reference": projection["reference"],
        "projection_version": projection["projection_version"],
        "source_eligible_cluster_count": projection["eligible_cluster_count"],
        "projected_idea_count": len(projection["ideas"]),
        "grouped_cluster_relationship_count": sum(audit["decision"] == "GROUP" for audit in audits),
        "ungrouped_ambiguous_concept_count": len(projection["ambiguous_cluster_ids"]),
        "ambiguous_cluster_ids": projection["ambiguous_cluster_ids"],
        "decisions": audits,
        "idea_membership": [
            {
                "idea_id": idea["idea_id"],
                "label": idea["label"],
                "cluster_ids": idea["cluster_ids"],
                "grouping_reason": idea["grouping_reason"],
            }
            for idea in projection["ideas"]
        ],
    }


def _chapter_report(reference: str, record: dict[str, Any]) -> str:
    projection = record["projection"]
    ancestry = projection["ancestry_audit"]
    lines = [
        f"# {reference} — reader-level idea projection",
        "",
        f"Projection: `{projection['projection_version']}`",
        f"Original synthesis units: **{projection['source_synthesis_unit_count']}**",
        f"Eligible clusters: **{projection['eligible_cluster_count']}**",
        f"Projected ideas: **{len(projection['ideas'])}**",
        f"CORE ideas: **{sum(idea['importance'] == 'CORE' for idea in projection['ideas'])}**",
        f"RELEVANT ideas: **{sum(idea['importance'] == 'RELEVANT' for idea in projection['ideas'])}**",
        f"Grouped cluster relationships: **{sum(audit['decision'] == 'GROUP' for audit in projection['pair_audit'])}**",
        f"Ungrouped ambiguous concepts: **{len(projection['ambiguous_cluster_ids'])}**",
        f"Category families preserved: **{record['source_category_families'] == record['projected_category_families']}** ({', '.join(record['projected_category_families'])})",
        "",
        "## Ancestry preservation",
        "",
        f"- Eligible clusters preserved: `{ancestry['eligible_cluster_ids_preserved']}`",
        f"- Synthesis units preserved: `{ancestry['synthesis_unit_ids_preserved']}`",
        f"- Evidence IDs preserved: `{ancestry['evidence_ids_preserved']}`",
        f"- Invented synthesis IDs: `{ancestry['invented_synthesis_ids']}`",
        f"- Invented evidence IDs: `{ancestry['invented_evidence_ids']}`",
        "",
        "## Projected ideas",
        "",
    ]
    for index, idea in enumerate(projection["ideas"], start=1):
        lines.extend(
            [
                f"### {index}. {idea['label']}",
                "",
                f"- Importance: `{idea['importance']}`",
                f"- Status/confidence: `{idea['status']}` / `{idea['confidence']}`",
                f"- Disputed: `{idea['disputed']}`",
                f"- Categories: `{', '.join(idea['categories'])}`",
                f"- Clusters: `{', '.join(idea['cluster_ids'])}`",
                f"- Synthesis units: `{', '.join(idea['synthesis_unit_ids'])}`",
                f"- Evidence ancestry: `{', '.join(idea['evidence_ids'])}`",
                f"- Source order: `{idea['source_order']}`",
                f"- Grouping rationale: `{idea['grouping_reason']}`",
                "",
            ]
        )
    return "\n".join(lines)


def _write_renderer_handoff(namespace: Path, record: dict[str, Any]) -> None:
    handoff = namespace / "renderer-input" / "revelation_021"
    _write_text(handoff / "system_prompt.txt", record["original_system_prompt"])
    _write_text(handoff / "user_prompt.txt", record["variant_prompt"])
    metadata = {
        "status": "AWAITING_EXTERNAL_RENDERER",
        "experiment_id": "prompt-1.7+reader-level-idea-projection-v1",
        "reference": "Revelation 21",
        "renderer": record["packet"]["renderer"],
        "renderer_effort": record["packet"]["renderer_effort"],
        "generation_policy": {
            "candidate_generation_count": 0,
            "one_generation_only": True,
            "selective_retries": False,
            "runtime_self_attestation": False,
        },
        "prompt_1_7_unchanged": True,
        "original_prompt_sha256": record["original_user_prompt_sha256"],
        "variant_prompt_sha256": record["variant_user_prompt_sha256"],
        "system_prompt_sha256": record["original_system_prompt_sha256"],
        "projection_hash": record["projection"]["projection_hash"],
        "projection_section_sha256": record["projection_section_sha256"],
        "full_synthesis_retained": "COMPILED CHAPTER SYNTHESIS:" in record["variant_prompt"],
        "synthesis_hash_retained": record["projection"]["synthesis_hash"] in record["variant_prompt"],
        "baseline_response_reused": True,
        "candidate_response_present": False,
    }
    _write_json(handoff / "metadata.json", metadata)


def _baseline_reference(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = json.loads((PROMPT_17_ROOT / record["config"]["baseline_evaluation"]).read_text())
    return {
        "status": "IMMUTABLE_HISTORICAL_BASELINE_REUSED",
        "diagnostic_id": PROMPT_17_ID,
        "packet_path": str((PROMPT_17_ROOT / record["config"]["packet"]).relative_to(ROOT)),
        "packet_sha256": sha256_bytes((PROMPT_17_ROOT / record["config"]["packet"]).read_bytes()),
        "raw_response_path": str((PROMPT_17_ROOT / record["config"]["baseline_raw"]).relative_to(ROOT)),
        "raw_response_sha256": sha256_bytes((PROMPT_17_ROOT / record["config"]["baseline_raw"]).read_bytes()),
        "parsed_response_path": str((PROMPT_17_ROOT / record["config"]["baseline_parsed"]).relative_to(ROOT)),
        "evaluation_path": str((PROMPT_17_ROOT / record["config"]["baseline_evaluation"]).relative_to(ROOT)),
        "metrics": evaluation["new_prompt_1_7"],
    }


def _evaluation_comparison(record: dict[str, Any]) -> dict[str, Any]:
    evaluation = json.loads((PROMPT_17_ROOT / record["config"]["baseline_evaluation"]).read_text())
    baseline = evaluation["new_prompt_1_7"]
    return {
        "artifact_version": "reader-level-idea-projection-renderer-comparison-v1",
        "reference": "Revelation 21",
        "baseline": {
            "experiment": "prompt-1.7 original synthesis presentation",
            "metrics": baseline,
            "response_reused": True,
        },
        "candidate": {
            "experiment": "prompt-1.7 + reader-level-idea-projection-v1",
            "status": "NOT_GENERATED",
            "metrics": None,
            "response_reused": False,
            "generation_count": 0,
        },
        "delta": None,
        "outcome": "READER_IDEA_PROJECTION_PREPARED_AWAITING_RENDERER",
        "comparison_contract": {
            "structural_validity": "existing frozen validator",
            "provenance": "existing frozen validator",
            "scoring": "commentary-richness-gate-v2.1",
            "prompt_version": "1.7",
            "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        },
    }


def _final_report(namespace: Path, records: dict[str, dict[str, Any]], fingerprint: str) -> dict[str, Any]:
    r21 = records["Revelation 21"]["projection"]
    r20 = records["Revelation 20"]["projection"]
    return {
        "outcome": "READER_IDEA_PROJECTION_PREPARED_AWAITING_RENDERER",
        "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "input_fingerprint": fingerprint,
        "namespace": str(namespace.relative_to(ROOT)),
        "revelation_21": {
            "synthesis_unit_count": r21["source_synthesis_unit_count"],
            "eligible_cluster_count": r21["eligible_cluster_count"],
            "projected_idea_count": len(r21["ideas"]),
            "core_idea_count": sum(idea["importance"] == "CORE" for idea in r21["ideas"]),
            "relevant_idea_count": sum(idea["importance"] == "RELEVANT" for idea in r21["ideas"]),
            "grouped_cluster_relationship_count": sum(audit["decision"] == "GROUP" for audit in r21["pair_audit"]),
            "ungrouped_ambiguous_concept_count": len(r21["ambiguous_cluster_ids"]),
            "ancestry_preserved": all(
                r21["ancestry_audit"][key]
                for key in (
                    "eligible_cluster_ids_preserved",
                    "synthesis_unit_ids_preserved",
                    "evidence_ids_preserved",
                )
            ),
            "compression_ratio_ideas_over_eligible_clusters": round(len(r21["ideas"]) / r21["eligible_cluster_count"], 4),
            "category_representation": {
                "source": records["Revelation 21"]["source_category_families"],
                "projected": records["Revelation 21"]["projected_category_families"],
                "preserved": records["Revelation 21"]["source_category_families"] == records["Revelation 21"]["projected_category_families"],
            },
        },
        "revelation_20_control": {
            "synthesis_unit_count": r20["source_synthesis_unit_count"],
            "eligible_cluster_count": r20["eligible_cluster_count"],
            "projected_idea_count": len(r20["ideas"]),
            "compression_ratio_ideas_over_eligible_clusters": round(len(r20["ideas"]) / r20["eligible_cluster_count"], 4),
            "category_representation": {
                "source": records["Revelation 20"]["source_category_families"],
                "projected": records["Revelation 20"]["projected_category_families"],
                "preserved": records["Revelation 20"]["source_category_families"] == records["Revelation 20"]["projected_category_families"],
            },
            "ancestry_preserved": all(
                r20["ancestry_audit"][key]
                for key in (
                    "eligible_cluster_ids_preserved",
                    "synthesis_unit_ids_preserved",
                    "evidence_ids_preserved",
                )
            ),
        },
        "candidate_renderer_result": None,
        "recommendation": "Run the one frozen Revelation 21 handoff once under GPT-5.6 Sol at medium effort, then evaluate with the existing scorer. Do not roll out until the 7-chapter diagnostic corpus is tested.",
    }


def _write_json(path: Path, value: Any) -> None:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    write_immutable(path, payload)


def _write_text(path: Path, value: str) -> None:
    write_immutable(path, value.encode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
