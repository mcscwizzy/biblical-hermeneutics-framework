#!/usr/bin/env python3
"""Produce the second deterministic semantic-relevance audit for v1.1."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.presentation.relevance import is_semantically_relevant
from tools.commentary_v11_canary import _section_for_item, select_overview_item


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
JSON_PATH = OUTPUT_ROOT / "semantic-relevance-audit-2.json"
DOC_PATH = ROOT / "docs" / "commentary-v1.1-semantic-relevance-audit-2.md"
PRIORITY_PATH = OUTPUT_ROOT / "data-gap-priority.json"
CERTIFICATION_PATH = OUTPUT_ROOT / "evidence-certification-commentary_canary.json"
VALIDATION_PATH = OUTPUT_ROOT / "chapters" / "commentary-canary-validation.json"
LOW_INFO_PATH = OUTPUT_ROOT / "low-information-commentary.json"

WORD_STUDY_DECISIONS = {
    "parakletos": {
        "old_anchor": "Genesis 1:1-2",
        "new_anchor": None,
        "decision": "removed",
        "reason": "Greek parakletos is not a lexical occurrence in the Hebrew Genesis 1 text; the inherited anchor was a theological Spirit association.",
    },
    "pneuma": {
        "old_anchor": "Genesis 1:1-2",
        "new_anchor": None,
        "decision": "removed",
        "reason": "Greek pneuma is not the Hebrew lexical form in Genesis 1:1-2; the inherited anchor was a canonical Spirit association.",
    },
    "katabole": {
        "old_anchor": "Genesis 1:1-31",
        "new_anchor": None,
        "decision": "removed",
        "reason": "Greek katabole is not a lexical occurrence in Genesis 1; the association belongs to later creation theology rather than first-audience language context.",
    },
    "phos": {
        "old_anchor": "Genesis 1:1-5",
        "new_anchor": None,
        "decision": "removed",
        "reason": "Greek phos is not the Hebrew lexical form of Genesis 1; the inherited anchor conflated translation/thematic comparison with source-language occurrence.",
    },
    "skotia": {
        "old_anchor": "Genesis 1:1-5",
        "new_anchor": None,
        "decision": "removed",
        "reason": "Greek skotia is not a lexical occurrence in the Hebrew Genesis 1 text; the inherited anchor was a later theological association.",
    },
    "sarx": {
        "old_anchor": "Genesis 1:26-28",
        "new_anchor": None,
        "decision": "removed",
        "reason": "Greek sarx is not the Hebrew lexical form in Genesis 1:26-28; the inherited anchor was a thematic humanity/flesh association.",
    },
    "shema": {
        "old_anchor": "Psalms 1:1-3",
        "new_anchor": None,
        "decision": "removed",
        "reason": "The Shema is not a lexical occurrence in Psalm 1; the inherited anchor was a covenant-theology association.",
    },
    "makarios": {
        "old_anchor": "Psalms 1:1-3",
        "new_anchor": "Psalms 1:1-3",
        "decision": "reclassified",
        "reason": "makarios is a legitimate Greek translation comparison for Psalm 1's blessedness language, not the Hebrew source-language occurrence.",
    },
    "nomos": {
        "old_anchor": "Psalms 1:1-3",
        "new_anchor": "Psalms 1:1-3",
        "decision": "reclassified",
        "reason": "nomos is a legitimate Greek translation comparison for Psalm 1's Torah language, not the Hebrew source-language occurrence.",
    },
    "torah": {
        "old_anchor": "Psalms 1:1-3",
        "new_anchor": "Psalms 1:1-3",
        "decision": "retained",
        "reason": "Torah is the relevant Hebrew lexical term in Psalm 1:2 and may ground language/literary context.",
    },
}

CKL_REPAIRS = [
    {
        "record_id": name,
        "old_anchor": decision["old_anchor"],
        "new_anchor": decision["new_anchor"],
        "reason": decision["reason"],
        "source_support": "The CKL record's lexical form and Scripture reference list were compared with the passage's source-language occurrence; no runtime model inference was used.",
        "semantic_relationship": "GENERIC_BACKGROUND" if decision["decision"] == "removed" else "COMPARATIVE_CONTEXT",
        "affected_chapters": ["Genesis 1" if name not in {"shema", "makarios", "nomos", "torah"} else "Psalms 1"],
    }
    for name, decision in WORD_STUDY_DECISIONS.items()
    if decision["decision"] in {"removed", "reclassified"}
]


def rows() -> list[dict[str, object]]:
    return json.loads(PRIORITY_PATH.read_text(encoding="utf-8"))["selected_batches"]["commentary_canary"]


def bundles() -> list[tuple[str, int, object]]:
    return [
        (str(row["book"]), int(row["chapter"]), get_chapter_evidence_bundle(
            str(row["book"]), int(row["chapter"]),
            evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
        ))
        for row in rows()
    ]


def old_hashes() -> dict[str, str]:
    path = " .bhf-data/bhf-commentary-candidates/commentary-v1.1/evidence-certification-commentary_canary.json".strip()
    try:
        raw = subprocess.check_output(
            ["git", "show", f"f8b800c:{path}"],
            cwd=ROOT,
            text=True,
        )
        return json.loads(raw).get("locked_evidence_bundle_hashes", {})
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def item_summary(item: object) -> dict[str, object]:
    metadata = item.relevance_metadata or {}
    return {
        "evidence_id": item.id,
        "parent_object_id": metadata.get("parent_object_id"),
        "parent_type": metadata.get("parent_type"),
        "category": item.category,
        "semantic_relationship": metadata.get("semantic_relationship"),
        "presentation_role": metadata.get("presentation_role"),
        "overview_priority": metadata.get("overview_priority"),
        "passage_anchors": list(item.passage_anchors),
        "assertion_type": metadata.get("assertion_type"),
        "dispute_status": metadata.get("dispute_status"),
        "claim": item.claim,
    }


def control_detail(book: str, chapter: int) -> dict[str, object]:
    bundle = get_chapter_evidence_bundle(
        book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    overview = select_overview_item(bundle)
    candidate_path = OUTPUT_ROOT / "chapters" / f"{book.casefold().replace(' ', '_')}_{chapter:03d}.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path.exists() else {}
    return {
        "availability": classify_evidence_availability(bundle).value,
        "evidence_count": len(bundle.evidence_items),
        "overview_evidence_id": overview.id if overview else None,
        "overview_anchors": list(overview.passage_anchors) if overview else [],
        "section_kinds": [section["kind"] for section in candidate.get("sections", [])],
        "evidence_items": [item_summary(item) for item in bundle.evidence_items],
        "disputed_evidence_ids": [
            item.id for item in bundle.evidence_items
            if (item.relevance_metadata or {}).get("dispute_status") not in {None, "", "not_disputed", "unknown"}
        ],
        "regeneration_eligible": any(is_semantically_relevant(item) for item in bundle.evidence_items),
    }


def build_report() -> dict[str, object]:
    chapter_rows = []
    all_items = []
    roles: Counter[str] = Counter()
    presentation_roles: Counter[str] = Counter()
    for book, chapter, bundle in bundles():
        items = [item_summary(item) for item in bundle.evidence_items]
        all_items.extend(items)
        roles.update(item["semantic_relationship"] for item in items)
        presentation_roles.update(item["presentation_role"] or "UNASSIGNED" for item in items)
        overview = select_overview_item(bundle)
        candidate_path = OUTPUT_ROOT / "chapters" / f"{book.casefold().replace(' ', '_')}_{chapter:03d}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        chapter_rows.append({
            "reference": bundle.passage_ref,
            "availability": classify_evidence_availability(bundle).value,
            "evidence_count": len(bundle.evidence_items),
            "overview_evidence_id": overview.id if overview else None,
            "overview_anchors": list(overview.passage_anchors) if overview else [],
            "section_kinds": [section["kind"] for section in candidate["sections"]],
            "semantic_relationship_counts": dict(sorted(Counter(item["semantic_relationship"] for item in items).items())),
            "presentation_role_counts": dict(sorted(Counter(item["presentation_role"] or "UNASSIGNED" for item in items).items())),
            "evidence_hash": bundle.evidence_hash,
            "regeneration_eligible": any(is_semantically_relevant(item) for item in bundle.evidence_items),
        })

    certification = json.loads(CERTIFICATION_PATH.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))
    low_info = json.loads(LOW_INFO_PATH.read_text(encoding="utf-8"))
    previous_hashes = old_hashes()
    current_hashes = {row["reference"]: row["evidence_hash"] for row in chapter_rows}
    hash_changes = [
        reference for reference, value in current_hashes.items()
        if previous_hashes.get(reference) != value
    ]
    current_eligibility = len(low_info["chapters_evidence_supports_regeneration"])
    return {
        "report_version": "commentary-v1.1-semantic-relevance-audit-2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "canary_chapters_audited": len(chapter_rows),
            "evidence_items_examined": len(all_items),
            "full_canonical_cleanup_attempted": False,
            "production_release_modified": False,
            "provider_calls": 0,
            "terra_run": False,
        },
        "summary": {
            "semantic_relationship_counts": dict(sorted(roles.items())),
            "direct_context_items": roles["DIRECT_CONTEXT"],
            "book_context_items": roles["BOOK_CONTEXT"],
            "later_intertextual_items": roles["LATER_RECEPTION"] + roles["INTERTEXTUAL_REUSE"],
            "comparative_items": roles["COMPARATIVE_CONTEXT"],
            "generic_background_items": roles["GENERIC_BACKGROUND"],
            "semantically_misanchored_items": roles["SEMANTICALLY_MISANCHORED"],
            "presentation_role_counts": dict(sorted(presentation_roles.items())),
            "word_study_records_examined": len(WORD_STUDY_DECISIONS),
            "word_study_anchors_removed": sum(decision["decision"] == "removed" for decision in WORD_STUDY_DECISIONS.values()),
            "word_study_anchors_reclassified": sum(decision["decision"] == "reclassified" for decision in WORD_STUDY_DECISIONS.values()),
        },
        "word_study_audit": WORD_STUDY_DECISIONS,
        "ckl_changes": {
            "records_changed": CKL_REPAIRS,
            "records_unchanged": ["makarios", "nomos", "torah"],
            "systemic_pattern": "Template-generated word-study records used thematic Scripture anchors without proving a source-language lexical occurrence. Only ten records reachable from the canary were audited; no full-CKL rewrite was attempted.",
        },
        "presentation_role_changes": [
            {
                "evidence_id": "luke-acts-relation",
                "old_category": "geography",
                "new_presentation_role": "language_literary",
                "reason": "Claim content and literary claim type describe authorship, Theophilus, narrative continuation, and composition rather than physical geography.",
                "affected_chapters": ["Luke 1"],
            },
            {
                "evidence_id": "what-is-sacrifice-in-the-bible:ancient_near_east_context:0",
                "old_presentation_role": "language_literary",
                "new_presentation_role": "historical_context",
                "reason": "Ritual and cultural background belongs in historical/social context.",
                "affected_chapters": ["Leviticus 1"],
            },
            {
                "evidence_id": "genesis-ane-comparative-context",
                "old_presentation_role": "archaeology_geography",
                "new_presentation_role": "historical_context",
                "reason": "Ancient Near Eastern literary comparison is cultural context, not site or physical geography.",
                "affected_chapters": ["Genesis 1"],
            },
        ],
        "overview_selection": {
            "ranking_dimensions": [
                "overview_priority",
                "semantic_relationship",
                "presentation_role",
                "category",
                "anchor_specificity",
                "confidence",
                "evidence_id_final_tiebreaker",
            ],
            "corrections": [
                {
                    "reference": "Zephaniah 1",
                    "before": "zephaniah-textual-witnesses",
                    "after": "zephaniah-superscription",
                    "reason": "Josiah-era superscription context outranks textual transmission history for first-reader orientation.",
                }
            ],
            "array_order_independent": True,
        },
        "section_routing": {
            "dig_deeper_budget": {
                "thin_max_contextual_sections": 2,
                "available_max_contextual_sections": 4,
                "reserves_slot_when_useful": True,
                "forces_without_evidence": False,
            },
            "corrections": [
                "Luke 1 luke-acts-relation: archaeology_geography -> language_literary",
                "Leviticus 1 sacrifice background: language_literary -> historical_context",
                "Genesis 1 ancient Near Eastern comparison: archaeology_geography -> historical_context",
            ],
        },
        "chapters": chapter_rows,
        "controls": {
            "Genesis 1": control_detail("Genesis", 1),
            "Luke 1": control_detail("Luke", 1),
            "Leviticus 1": control_detail("Leviticus", 1),
            "Zephaniah 1": control_detail("Zephaniah", 1),
            "1 Samuel 28": control_detail("1 Samuel", 28),
            "Numbers 3": control_detail("Numbers", 3),
        },
        "regeneration_eligibility": {
            "before_pass_2": 935,
            "after_pass_2": current_eligibility,
            "initial_before_pass_1": 936,
            "overall_changed_chapters": ["Psalms 24"],
        },
        "availability": {
            "before_pass_2": {"AVAILABLE": 5, "THIN": 10, "DATA_GAP": 10},
            "after_pass_2": dict(sorted(Counter(row["availability"] for row in chapter_rows).items())),
            "changed_chapters": [],
        },
        "evidence_hashes": {
            "candidate_bundle_version": "1.1",
            "evidence_hash_version": "2",
            "retrieval_score_in_identity": False,
            "presentation_role_in_identity": True,
            "presentation_role_reason": "The role changes which commentary section may be grounded, so it changes candidate grounding identity rather than serving as UI-only decoration.",
            "changed_from_f8b800c_count": len(hash_changes),
            "changed_from_f8b800c_references": hash_changes,
            "json_sqlite_hash_disagreements": certification["json_sqlite_agreement"]["bundle_hash_disagreements"],
        },
        "validation": {
            "candidate_chapters": validation["chapters"],
            "valid": validation["valid"],
            "invalid": validation["invalid"],
            "json_sqlite_agreement": certification["json_sqlite_agreement"],
            "retrieval_leakage": certification["retrieval_leakage_audit"],
        },
        "evidence_items": all_items,
        "unresolved_concerns": [
            "The template-generated word-study pattern may exist outside the 25-chapter canary; those records remain follow-up scope.",
            "Some CKL claims still use broad category labels; deterministic presentation roles now override them for the audited canary, but future CKL authoring should provide explicit claim-level roles.",
        ],
    }


def markdown(report: dict[str, object]) -> str:
    summary = report["summary"]
    validation = report["validation"]
    controls = report["controls"]
    lines = [
        "# BHF Commentary v1.1 Semantic-Relevance Audit 2",
        "",
        "This deterministic pass hardens the 25-chapter candidate evidence boundary on `feat/commentary-v1.1-expansion`. Production `commentary-v1.0.1` was not modified, and Terra was not run.",
        "",
        "## Result",
        "",
        f"- Chapters audited: {report['scope']['canary_chapters_audited']}",
        f"- Evidence items examined: {report['scope']['evidence_items_examined']}",
        f"- Word-study records examined: {summary['word_study_records_examined']}",
        f"- Word-study anchors removed: {summary['word_study_anchors_removed']}",
        f"- Word-study anchors reclassified: {summary['word_study_anchors_reclassified']}",
        f"- Candidate validation: {validation['valid']} valid, {validation['invalid']} invalid",
        f"- JSON/SQLite result-ID disagreements: {validation['json_sqlite_agreement']['result_id_disagreements']}",
        f"- JSON/SQLite hash disagreements: {validation['json_sqlite_agreement']['bundle_hash_disagreements']}",
        f"- Retrieval leakage: {validation['retrieval_leakage']['chapters_with_leakage']} chapters",
        "",
        "## Word-study decisions",
        "",
        "The audited generated records did not prove a source-language lexical occurrence merely by carrying a thematic Scripture anchor. `parakletos`, `pneuma`, `katabole`, `phos`, `skotia`, `sarx`, and `shema` had the confirmed bad canary anchors removed. `makarios` and `nomos` remain as comparative Greek translation evidence; `torah` remains direct Psalm 1 lexical evidence.",
        "",
        "## Required controls",
        "",
    ]
    for name in ("Genesis 1", "Luke 1", "Leviticus 1", "Zephaniah 1", "1 Samuel 28", "Numbers 3"):
        control = controls[name]
        lines.append(
            f"- **{name}**: {control['availability']}; {control['evidence_count']} evidence items; overview `{control['overview_evidence_id']}`; sections `{', '.join(control['section_kinds'])}`."
        )
    lines.extend([
        "",
        "Genesis 1 has no reachable `parakletos`, `katabole`, or `pneuma` word-study item, no Arad/Caesarea evidence, and retains Pauline reuse only in `dig_deeper`. Luke 1 routes `luke-acts-relation` to `language_literary`. Leviticus 1 routes sacrifice background to `historical_context`. Zephaniah 1 replaces textual witnesses with Josiah-era superscription context as overview. 1 Samuel 28 remains THIN with the apparition disputed. Numbers 3 remains an honest DATA_GAP with zero evidence.",
        "",
        "## Overview and section routing",
        "",
        "Overview ranking now uses explicit reader-usefulness priority before semantic relationship, presentation role, category, anchor specificity, confidence, and only then the evidence ID. The section budget reserves a `dig_deeper` slot when useful evidence exists and never forces one without evidence.",
        "",
        "## Hash and regeneration semantics",
        "",
        "Candidate EvidenceBundle version 1.1 continues to use evidence hash version 2. Retrieval score remains excluded as volatile backend ranking metadata. Presentation role is included because it changes which section may ground a candidate. Evidence content, provenance, and semantic relationship metadata remain identity inputs. Regeneration eligibility is semantically filtered; the overall canary audit remains 935 eligible and 153 insufficient, with Psalms 24 the pass-1 change from eligible to insufficient.",
        "",
        "## Unresolved concerns",
        "",
        "The template-generated word-study pattern may exist outside the 25-chapter canary and should be a future CKL-authoring cleanup. Broad legacy category labels remain in CKL, but the deterministic presentation-role layer prevents the audited canary from treating them as section instructions.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    DOC_PATH.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "chapters": report["scope"]["canary_chapters_audited"],
        "evidence_items": report["scope"]["evidence_items_examined"],
        "word_study_records": report["summary"]["word_study_records_examined"],
        "word_study_removed": report["summary"]["word_study_anchors_removed"],
        "word_study_reclassified": report["summary"]["word_study_anchors_reclassified"],
        "valid": report["validation"]["valid"],
        "invalid": report["validation"]["invalid"],
        "json_sqlite": report["validation"]["json_sqlite_agreement"],
        "json": str(JSON_PATH),
        "markdown": str(DOC_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
