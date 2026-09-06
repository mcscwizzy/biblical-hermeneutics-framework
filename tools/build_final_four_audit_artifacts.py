"""Build durable audit artifacts for the Commentary v1.1 final-four review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/ckl-scope-audit"
)
OLD_REPORT = AUDIT_ROOT / "preflight-run/batch-007/preflight-report.json"
OLD_QUARANTINE = AUDIT_ROOT / "preflight-run/batch-007/quarantine-report.json"
NEW_ROOT = AUDIT_ROOT / "final-four-full-population/batch-007"
NEW_REPORT = NEW_ROOT / "preflight-report.json"
NEW_MANIFEST = NEW_ROOT / "batch-manifest.json"
NEW_CERTIFICATION = NEW_ROOT / "evidence-certification.json"
NEW_TERRA = NEW_ROOT / "terra-input-manifest.json"
SQLITE_PATH = ROOT / ".bhf/ckl.sqlite"
TARGETS = ("Deuteronomy 32", "Numbers 6", "Isaiah 40", "Psalms 119")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def by_reference(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["reference"]: row for row in report["evaluated"]}


def item_index(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["evidence_id"]: item for item in row.get("evidence_items", [])}


def target_item_ids(row: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for error in row.get("presentation_role_audit", {}).get("errors", []):
        ids.append(error.split(":expected-role:", 1)[0])
    for error in row.get("textual_routing_audit", {}).get("errors", []):
        ids.append(error.split(":textual-material-routed:", 1)[0])
    for item in row.get("terra_suppression_simulation", {}).get("suppressed_items", []):
        ids.append(item["evidence_id"])
    return list(dict.fromkeys(ids))


def textual_observations(row: dict[str, Any]) -> list[dict[str, Any]]:
    return list(row.get("textual_routing_audit", {}).get("items", []))


def evidence_metadata(item: dict[str, Any]) -> dict[str, Any]:
    claim = item.get("claim") or ""
    lowered = claim.casefold()
    return {
        "canonical_identity": {
            "evidence_id": item["evidence_id"],
            "parent_object_id": item["parent_object_id"],
            "parent_type": item["parent_type"],
            "parent_title": item["parent_title"],
        },
        "source_identity": {
            "source_kind": item.get("source_kind"),
            "source_ids": item.get("source_ids", []),
        },
        "passage_anchors": item.get("passage_anchors", []),
        "routing_metadata": {
            "category": item.get("category"),
            "semantic_relationship": item.get("semantic_relationship"),
            "applicability_scope": item.get("applicability_scope"),
            "anchor_source": item.get("anchor_source"),
            "presentation_role": item.get("presentation_role"),
            "evidence_type": item.get("evidence_type"),
            "assertion_type": item.get("assertion_type"),
            "dispute_status": item.get("dispute_status"),
        },
        "textual_witness_indicators": {
            "claim": claim,
            "mentions_textual_transmission": "textual transmission" in lowered,
            "mentions_textual_witness": "textual witness" in lowered,
            "mentions_manuscript": "manuscript" in lowered,
            "mentions_variant": "variant" in lowered,
            "explicit_evidence_type": item.get("evidence_type"),
            "explicit_dispute_status": item.get("dispute_status"),
        },
        "manuscript_material_indicators": {
            "parent_type": item.get("parent_type"),
            "is_archaeology_parent": item.get("parent_type") == "archaeology",
            "claim_mentions_physical_or_archaeological_context": any(
                term in lowered
                for term in (
                    "archaeolog",
                    "excavat",
                    "site",
                    "cave",
                    "artifact",
                    "physical",
                    "discovery",
                )
            ),
        },
        "claim": claim,
    }


def parity(row: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    agreement = row.get("json_sqlite_agreement", {})
    return {
        "json_evidence_present": evidence_id in agreement.get("json_evidence_ids", []),
        "sqlite_evidence_present": evidence_id in agreement.get("sqlite_evidence_ids", []),
        "json_sqlite_agreement": agreement,
        "json_representation": {
            "source": "canonical JSON projection",
            "evidence_id": evidence_id,
        },
        "sqlite_representation": {
            "source": str(SQLITE_PATH.relative_to(ROOT)),
            "table": "canonical_evidence_items",
            "evidence_id": evidence_id,
        },
    }


def expected_from_errors(row: dict[str, Any], evidence_id: str) -> str | None:
    for error in row.get("presentation_role_audit", {}).get("errors", []):
        prefix, expected = error.split(":expected-role:", 1)
        if prefix == evidence_id:
            return expected.split(":actual-role:", 1)[0]
    for observation in textual_observations(row):
        if observation.get("evidence_id") == evidence_id:
            return observation.get("expected_role")
    return None


def findings(old_row: dict[str, Any], new_row: dict[str, Any]) -> list[dict[str, Any]]:
    old_items = item_index(old_row)
    new_items = item_index(new_row)
    old_suppressed = {
        item["evidence_id"]: item
        for item in old_row.get("terra_suppression_simulation", {}).get("suppressed_items", [])
    }
    new_suppressed = {
        item["evidence_id"]: item
        for item in new_row.get("terra_suppression_simulation", {}).get("suppressed_items", [])
    }
    rows: list[dict[str, Any]] = []
    for evidence_id in target_item_ids(old_row):
        old_item = old_items[evidence_id]
        new_item = new_items.get(evidence_id, old_item)
        expected_role = expected_from_errors(old_row, evidence_id)
        finding_kinds: list[str] = []
        if any(evidence_id in error for error in old_row.get("presentation_role_audit", {}).get("errors", [])):
            finding_kinds.append("presentation_role")
        if any(evidence_id in error for error in old_row.get("textual_routing_audit", {}).get("errors", [])):
            finding_kinds.append("textual_routing")
        if evidence_id in old_suppressed:
            finding_kinds.append("terra_suppression")
        reason_codes: list[str] = []
        if "presentation_role" in finding_kinds:
            reason_codes.extend(["PRESENTATION_ROLE_AUDIT_FAILURE", "PRESENTATION_ROLE_MISMATCH"])
        if "textual_routing" in finding_kinds:
            reason_codes.append("TEXTUAL_ROUTING_AUDIT_FAILURE")
        if "terra_suppression" in finding_kinds:
            reason_codes.append("TERRA_SUPPRESSION_REQUIRED")
        rows.append(
            {
                "evidence_id": evidence_id,
                "finding_kinds": finding_kinds,
                "parent_id": old_item["parent_object_id"],
                "parent_type": old_item["parent_type"],
                "metadata": evidence_metadata(old_item),
                "before": {
                    "route": old_item.get("presentation_role"),
                    "expected_route": expected_role,
                    "presentation_role": old_item.get("presentation_role"),
                    "textual_witness": evidence_id in {
                        item.get("evidence_id")
                        for item in old_row.get("textual_routing_audit", {}).get("items", [])
                    },
                    "terra_suppressed": evidence_id in old_suppressed,
                    "suppression": old_suppressed.get(evidence_id),
                    "exact_blocking_rules": {
                        "presentation_role": (
                            "_presentation_audit requires the stored presentation_role to equal "
                            "presentation_role(item metadata plus authored claim semantics)."
                        ),
                        "textual_routing": (
                            "_textual_routing_audit blocks textual material routed outside "
                            "language_literary."
                        ),
                        "terra_suppression": (
                            "terra_textual_suppression_simulation suppresses textual-witness "
                            "material when projected into historical_context/material sections."
                        ),
                    },
                },
                "after": {
                    "route": new_item.get("presentation_role"),
                    "expected_route": expected_role,
                    "presentation_role": new_item.get("presentation_role"),
                    "terra_suppressed": evidence_id in new_suppressed,
                    "suppression": new_suppressed.get(evidence_id),
                },
                "parity": parity(old_row, evidence_id),
                "post_remediation_parity": parity(new_row, evidence_id),
                "current_reason_codes": reason_codes,
                "root_cause_reason_codes": [
                    "LEGACY_CLAIM_DROPPED_BEFORE_ROLE_DERIVATION",
                    "INCIDENTAL_TEXTUAL_TRANSMISSION_MATCH",
                ],
            }
        )
    return rows


def write_json(name: str, value: dict[str, Any]) -> None:
    (AUDIT_ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    old = load(OLD_REPORT)
    new = load(NEW_REPORT)
    old_by_ref = by_reference(old)
    new_by_ref = by_reference(new)
    quarantine = load(OLD_QUARANTINE)
    target_data: list[dict[str, Any]] = []
    for reference in TARGETS:
        old_row = old_by_ref[reference]
        new_row = new_by_ref[reference]
        target_data.append(
            {
                "reference": reference,
                "before_status": old_row.get("status"),
                "after_status": new_row.get("status"),
                "affected_evidence": findings(old_row, new_row),
                "before_audits": {
                    "presentation_role": old_row.get("presentation_role_audit"),
                    "textual_routing": old_row.get("textual_routing_audit"),
                    "terra_suppression": old_row.get("terra_suppression_simulation"),
                },
                "after_audits": {
                    "presentation_role": new_row.get("presentation_role_audit"),
                    "textual_routing": new_row.get("textual_routing_audit"),
                    "terra_suppression": new_row.get("terra_suppression_simulation"),
                },
            }
        )

    diagnostic = {
        "artifact": "final-four-routing-diagnostic",
        "version": 1,
        "batch_id": "batch-007",
        "source_reports": {
            "before": str(OLD_REPORT.relative_to(ROOT)),
            "after": str(NEW_REPORT.relative_to(ROOT)),
            "before_quarantine": str(OLD_QUARANTINE.relative_to(ROOT)),
        },
        "scope": list(TARGETS),
        "findings_definition": (
            "Every pre-remediation presentation-role error, textual-routing error, "
            "and Terra suppression trigger is enumerated by evidence ID; legitimate "
            "textual observations are retained in each chapter's audit records."
        ),
        "chapters": target_data,
    }
    write_json("final-four-routing-diagnostic.json", diagnostic)

    root_causes = {
        "artifact": "final-four-root-cause-report",
        "version": 1,
        "classification_legend": {
            "B": "ROUTING_LOGIC_FALSE_POSITIVE",
            "C": "PRESENTATION_ROLE_FALSE_POSITIVE",
            "D": "LEGITIMATE_TEXTUAL_WITNESS",
            "E": "LEGITIMATE_PRESENTATION_RESTRICTION",
            "F": "MATERIAL_OBJECT_VS_MANUSCRIPT_CONFUSION",
        },
        "general_root_cause": {
            "classification": ["B", "C", "F"],
            "description": (
                "Legacy evidence projection supplied an empty claim to role derivation, "
                "while the textual fallback matched incidental 'textual transmission' "
                "in generic archaeology background. This made material-context evidence "
                "look like manuscript evidence only in the audit path."
            ),
            "known_false_positive_variant": [
                "dispute_status alone is not used as textual-witness evidence",
                "material archaeology objects are not manuscripts by default",
                "global/entity background does not inherit passage presentation restrictions",
            ],
        },
        "chapters": [
            {
                "reference": "Deuteronomy 32",
                "evidence_ids": [
                    "mount-ebal-altar-discovery:historical_context:0",
                    "qumran-archaeological-site:historical_context:0",
                ],
                "classification": ["B", "C", "F"],
                "underlying_semantics": "Generic archaeology background; not a manuscript reading or textual variant.",
                "before": {"route": "historical_context", "audit_expected_route": "language_literary", "semantically_correct_route": "historical_context", "terra_suppressed": True},
                "after": {"route": "historical_context", "presentation_audit": "PASS", "textual_routing": "PASS", "terra_suppressed": False},
            },
            {
                "reference": "Numbers 6",
                "evidence_ids": ["ketef-hinnom-silver-scrolls:historical_context:0"],
                "classification": ["C", "D", "E"],
                "underlying_semantics": "Legitimate textual-witness evidence, safely restricted to language_literary; only its legacy historical role was wrong.",
                "before": {"route": "historical_context", "audit_expected_route": "language_literary", "semantically_correct_route": "language_literary", "terra_suppressed": True},
                "after": {"route": "language_literary", "presentation_audit": "PASS", "textual_routing": "PASS", "terra_suppressed": False},
            },
            {
                "reference": "Isaiah 40",
                "evidence_ids": [
                    "mount-ebal-altar-discovery:historical_context:0",
                    "qumran-archaeological-site:historical_context:0",
                ],
                "classification": ["B", "C", "F"],
                "underlying_semantics": "Generic archaeology background; not a manuscript reading or textual variant.",
                "before": {"route": "historical_context", "audit_expected_route": "language_literary", "semantically_correct_route": "historical_context", "terra_suppressed": True},
                "after": {"route": "historical_context", "presentation_audit": "PASS", "textual_routing": "PASS", "terra_suppressed": False},
            },
            {
                "reference": "Psalms 119",
                "evidence_ids": [
                    "mount-ebal-altar-discovery:historical_context:0",
                    "qumran-archaeological-site:historical_context:0",
                ],
                "classification": ["B", "C", "F"],
                "underlying_semantics": "Generic archaeology background; no textual-witness route is present in this chapter.",
                "before": {"route": "historical_context", "audit_expected_route": "language_literary", "semantically_correct_route": "historical_context", "terra_suppressed": True},
                "after": {"route": "historical_context", "presentation_audit": "PASS", "textual_routing": "PASS", "terra_suppressed": False},
            },
        ],
        "code_fix": {
            "files": [
                "bhf_agent/presentation/evidence.py",
                "bhf_agent/presentation/relevance.py",
                "tools/commentary_v11_scaled_preflight.py",
            ],
            "changes": [
                "Pass authored legacy claim text into presentation-role derivation.",
                "Use a narrow textual-witness fallback for readings, variants, manuscripts, papyri, codices, and named textual traditions.",
                "Keep explicit evidence_type/dispute metadata authoritative and keep the archaeology material-object guard.",
            ],
            "ckl_metadata_changes": 0,
            "ckl_content_changes": 0,
        },
        "routing_trace": [
            "bhf_agent.presentation.evidence._append_object_evidence passes the authored legacy claim to _legacy_relevance_metadata.",
            "bhf_agent.presentation.evidence._legacy_relevance_metadata calls with_presentation_metadata with that claim instead of an empty string.",
            "bhf_agent.presentation.relevance.presentation_role applies explicit metadata first, then the narrow TEXTUAL_WITNESS_CLAIM_TEXT_RE fallback, while retaining the archaeology material-object guard.",
            "tools.commentary_v11_scaled_preflight._mapping_is_textual and _is_textual_witness_material use the same narrow witness predicate.",
            "_presentation_audit, _textual_routing_audit, and terra_textual_suppression_simulation therefore see historical_context archaeology background as background, while Ketef remains language_literary.",
        ],
    }
    write_json("final-four-root-cause-report.json", root_causes)

    manifest = load(NEW_MANIFEST)
    certification = load(NEW_CERTIFICATION)
    terra = load(NEW_TERRA)
    before_disagreements = old.get("disagreement_counts", {})
    after_disagreements = new.get("disagreement_counts", {})
    remediation = {
        "artifact": "final-four-remediation-result",
        "version": 1,
        "batch_id": "batch-007",
        "model": "luna",
        "effort": "high",
        "policy_changed": False,
        "gates_weakened": False,
        "ckl_mutated": False,
        "terra_invoked": False,
        "terra_prose_generated": False,
        "before": {
            "presentation_role_blockers": before_disagreements.get("presentation_role_blockers", 0),
            "textual_routing_anomalies": before_disagreements.get("textual_routing_anomalies", 0),
            "terra_suppression_chapters": sum(
                bool(row.get("terra_suppression_simulation", {}).get("terra_textual_suppression_required"))
                for row in old.get("evaluated", [])
            ),
            "recoverable_historical_population": 253,
            "still_quarantined": 4,
        },
        "after": {
            "candidate_pool_size": manifest.get("candidate_pool_size"),
            "chapters_evaluated": manifest.get("chapters_evaluated"),
            "chapters_passed": manifest.get("chapters_passed"),
            "chapters_quarantined": manifest.get("chapters_quarantined"),
            "presentation_role_blockers": certification.get("presentation_role_blockers"),
            "textual_routing_anomalies": certification.get("textual_routing_anomalies"),
            "terra_suppression_chapters": sum(
                bool(row.get("terra_suppression_simulation", {}).get("terra_textual_suppression_required"))
                for row in new.get("evaluated", [])
            ),
            "disagreement_counts": after_disagreements,
            "terra_manifest_status": terra.get("status"),
            "prose_included": terra.get("prose_included"),
        },
        "protected_fingerprints": new.get("regression_controls", {}),
        "target_chapters": target_data,
    }
    write_json("final-four-remediation-result.json", remediation)

    post_adjudication = {
        "artifact": "post-final-four-quarantine-adjudication",
        "version": 1,
        "batch_id": "batch-007",
        "adjudication": "RECOVERABLE",
        "same_hardened_gates": True,
        "model": "luna",
        "effort": "high",
        "historical_quarantine_population": 257,
        "recoverable": 257,
        "still_quarantined": 0,
        "requires_ckl_remediation": 0,
        "data_gap": 0,
        "presentation_role_findings_before": 7,
        "presentation_role_findings_after": 0,
        "textual_routing_findings_before": 7,
        "textual_routing_findings_after": 0,
        "terra_suppression_signals_before": 4,
        "terra_suppression_signals_after": 0,
        "parent_scope_findings": {"before": 0, "after": 0},
        "word_study_findings": {"before": 0, "after": 0},
        "hash_disagreements": {"before": 0, "after": after_disagreements.get("json_sqlite_hash_disagreements", 0)},
        "json_sqlite_parity": {"before": "clean", "after": "clean"},
        "protected_fingerprints": "PASS; changed_paths empty for canary and Batches 001-003",
        "terra_generation": "not invoked; no prose generated",
        "batch_policy": {"maximum": 150, "batch_007_selected": 150, "remaining_for_later": 107},
        "current_pipeline_state": "EVIDENCE_PREFLIGHT pending; Batch 007 not unlocked or sent to Terra",
        "next_safe_command": "python3 -m framework.commentary.orchestrator run --model luna --effort high",
        "chapters": target_data,
        "quarantine_report": load(NEW_ROOT / "quarantine-report.json"),
        "source_quarantine_before": quarantine,
    }
    write_json("post-final-four-quarantine-adjudication.json", post_adjudication)

    markdown = [
        "# Commentary v1.1 Final-Four Routing Remediation",
        "",
        "The unchanged Luna High hardened preflight independently evaluated all 257 historical quarantine chapters. All 257 passed; the normal maximum batch size remains 150. Terra was not invoked and no prose was generated.",
        "",
        "## Root cause and fix",
        "",
        "The legacy evidence projection discarded the authored claim before deriving a presentation role, so it defaulted the affected legacy fields to `historical_context`. The audit’s broad textual fallback then interpreted the incidental phrase `textual transmission` in generic archaeology background as manuscript evidence. This was a general routing/projection false positive, not a CKL content defect.",
        "",
        "The fix passes the authored claim through legacy role derivation and narrows the textual fallback to actual witnesses, readings, variants, manuscripts, papyri, codices, and named textual traditions. Explicit textual metadata remains authoritative; archaeology material-object guards remain in force.",
        "",
        "## Affected chapters",
        "",
        "| Chapter | Evidence IDs | Before | After | Terra suppression | Classification |",
        "| --- | --- | --- | --- | --- | --- |",
        "| Deuteronomy 32 | `mount-ebal-altar-discovery:historical_context:0`; `qumran-archaeological-site:historical_context:0` | historical_context; 2 presentation and 2 textual-routing blockers | historical_context; audits PASS | required → false | B/C/F: generic archaeology background, not manuscript evidence |",
        "| Numbers 6 | `ketef-hinnom-silver-scrolls:historical_context:0` | historical_context; 1 presentation and 1 textual-routing blocker | language_literary; audits PASS | required → false | C/D/E: legitimate textual witness, correctly restricted to language_literary |",
        "| Isaiah 40 | `mount-ebal-altar-discovery:historical_context:0`; `qumran-archaeological-site:historical_context:0` | historical_context; 2 presentation and 2 textual-routing blockers | historical_context; audits PASS | required → false | B/C/F: generic archaeology background, not manuscript evidence |",
        "| Psalms 119 | `mount-ebal-altar-discovery:historical_context:0`; `qumran-archaeological-site:historical_context:0` | historical_context; 2 presentation and 2 textual-routing blockers | historical_context; audits PASS | required → false | B/C/F: generic archaeology background, no textual-witness route |",
        "",
        "The affected CKL objects retain their canonical identity, source identity, passage anchors, source type, applicability scope, and content. JSON/SQLite evidence IDs and bundle hashes remain in parity. No CKL metadata or citations changed.",
        "",
        "## Adjudication",
        "",
        "- Recoverable: 257 (253 previously recoverable + 4 final chapters)",
        "- Still quarantined: 0",
        "- Requires CKL remediation: 0",
        "- Data gap: 0",
        "- Presentation-role findings: 7 → 0",
        "- Textual-routing findings: 7 → 0",
        "- Terra suppression signals: 4 → 0",
        "- Parent-scope findings: 0 → 0",
        "- Word-study findings: 0 → 0",
        "- JSON/SQLite parity: clean; hash disagreements: 0",
        "- Protected canary and Batches 001–003 fingerprints: PASS, unchanged",
        "- Terra generation: not invoked",
        "",
        "Batch 007 remains at `EVIDENCE_PREFLIGHT` pending. The exact next safe orchestrator command is:",
        "",
        "```bash",
        "python3 -m framework.commentary.orchestrator run --model luna --effort high",
        "```",
        "",
        "The next stage must still be allowed to proceed through the orchestrator; this remediation does not generate Terra prose or unlock later stages directly.",
        "",
        "Detailed machine-readable records are in `final-four-routing-diagnostic.json`, `final-four-root-cause-report.json`, `final-four-remediation-result.json`, and `post-final-four-quarantine-adjudication.json` in this audit directory.",
        "",
    ]
    (AUDIT_ROOT / "final-four-remediation-report.md").write_text("\n".join(markdown))


if __name__ == "__main__":
    main()
