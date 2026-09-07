#!/usr/bin/env python3
"""Audit and certify semantic roles for the v1.1 commentary canary."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.presentation.relevance import (
    COMPARATIVE_CONTEXT,
    DIRECT_CONTEXT,
    GENERIC_BACKGROUND,
    INTERTEXTUAL_REUSE,
    LATER_RECEPTION,
    SEMANTICALLY_MISANCHORED,
    WEAKLY_RELATED,
    is_semantically_relevant,
)
from tools.commentary_v11_canary import select_overview_item


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
REPORT_PATH = ROOT / "semantic-relevance-audit.json"
PRIORITY_PATH = ROOT / "data-gap-priority.json"
CERTIFICATION_PATH = ROOT / "evidence-certification-commentary_canary.json"

CONFIRMED_CKL_REPAIRS = [
    {
        "record_id": record_id,
        "old_anchor": "Genesis 1:1-2",
        "new_anchor": None,
        "reason": "The archaeology record is not materially or historically specific to the primeval Genesis 1 context; the anchor was a generic theological/context tag.",
        "source_support": "The record's own site-specific title, summary, and archaeology source metadata support a later historical/material context, not Genesis 1 first-audience context.",
        "semantic_relationship": SEMANTICALLY_MISANCHORED,
        "affected_chapters": ["Genesis 1"],
    }
    for record_id in (
        "arad-ostraca",
        "caesarea-maritima-excavations",
        "ein-gedi-scroll",
        "herodium-excavations",
        "kurkh-monolith",
        "masada-excavations",
        "pool-of-bethesda-excavation",
        "samaria-ostraca",
        "samaria-palace",
        "shiloh-excavations",
    )
]


def _rows() -> list[dict[str, Any]]:
    return json.loads(PRIORITY_PATH.read_text(encoding="utf-8"))["selected_batches"]["commentary_canary"]


def _item_record(item: Any) -> dict[str, Any]:
    return {
        "evidence_id": item.id,
        "parent_object_id": item.relevance_metadata.get("parent_object_id"),
        "parent_type": item.relevance_metadata.get("parent_type"),
        "category": item.category,
        "claim": item.claim,
        "passage_anchors": list(item.passage_anchors),
        "source_ids": list(item.source_ids),
        "confidence": item.confidence,
        "assertion_type": item.relevance_metadata.get("assertion_type"),
        "dispute_status": item.relevance_metadata.get("dispute_status"),
        "semantic_relationship": item.relevance_metadata.get("semantic_relationship"),
        "source_kind": item.relevance_metadata.get("source_kind"),
    }


def _control(bundle: Any, *, before_count: int | None = None) -> dict[str, Any]:
    overview = select_overview_item(bundle)
    roles = Counter(item.relevance_metadata.get("semantic_relationship") for item in bundle.evidence_items)
    return {
        "availability": classify_evidence_availability(bundle).value,
        "evidence_count": len(bundle.evidence_items),
        "before_evidence_count": before_count,
        "overview_evidence_id": overview.id if overview else None,
        "overview_anchors": list(overview.passage_anchors) if overview else [],
        "semantic_relationship_counts": dict(sorted(roles.items())),
        "precise_anchors": sorted({anchor for item in bundle.evidence_items for anchor in item.passage_anchors}),
        "disputed_evidence_ids": sorted(
            item.id
            for item in bundle.evidence_items
            if item.relevance_metadata.get("dispute_status") not in {None, "", "not_disputed", "unknown"}
        ),
        "regeneration_eligible": any(is_semantically_relevant(item) for item in bundle.evidence_items),
    }


def build_report() -> dict[str, Any]:
    rows = _rows()
    certification = json.loads(CERTIFICATION_PATH.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    chapters: list[dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    parent_ids: set[str] = set()
    for row in rows:
        bundle = get_chapter_evidence_bundle(
            row["book"],
            int(row["chapter"]),
            evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
        )
        chapter_items = [_item_record(item) for item in bundle.evidence_items]
        items.extend(chapter_items)
        role_counts.update(item["semantic_relationship"] for item in chapter_items)
        parent_ids.update(item["parent_object_id"] for item in chapter_items if item["parent_object_id"])
        overview = select_overview_item(bundle)
        candidate_path = ROOT / "chapters" / f"{row['book'].casefold().replace(' ', '_')}_{int(row['chapter']):03d}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8")) if candidate_path.exists() else {}
        chapters.append(
            {
                "reference": bundle.passage_ref,
                "availability": classify_evidence_availability(bundle).value,
                "evidence_count": len(bundle.evidence_items),
                "overview_evidence_id": overview.id if overview else None,
                "overview_anchors": list(overview.passage_anchors) if overview else [],
                "section_kinds": [section["kind"] for section in candidate.get("sections", [])],
                "semantic_relationships": dict(sorted(Counter(item["semantic_relationship"] for item in chapter_items).items())),
                "precise_anchor_count": len({anchor for item in bundle.evidence_items for anchor in item.passage_anchors}),
                "disputed_evidence_ids": [item["evidence_id"] for item in chapter_items if item["dispute_status"] not in {None, "", "not_disputed", "unknown"}],
                "regeneration_eligible": any(is_semantically_relevant(item) for item in bundle.evidence_items),
                "evidence_hash": bundle.evidence_hash,
            }
        )

    before_by_ref = {
        "Genesis 1": 90,
        "Leviticus 1": 26,
        "Psalms 1": 15,
        "Zephaniah 1": 17,
        "Deuteronomy 21": 3,
        "Numbers 3": 0,
        "1 Samuel 28": 2,
    }
    controls = {}
    for book, chapter in (("Genesis", 1), ("Leviticus", 1), ("Psalms", 1), ("Zephaniah", 1), ("Deuteronomy", 21), ("Numbers", 3), ("1 Samuel", 28)):
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        controls[bundle.passage_ref] = _control(bundle, before_count=before_by_ref[bundle.passage_ref])

    genesis_ids = {item["evidence_id"] for item in items if item["parent_object_id"]}
    controls["Genesis 1"]["detailed_findings"] = {
        "2-corinthians:interpretive_note:21": {
            "anchor": "Genesis 1:3",
            "anchor_correct": True,
            "decision": "retain",
            "semantic_relationship": LATER_RECEPTION,
            "allowed_sections": ["dig_deeper", "interpretive_questions"],
            "excluded_sections": ["chapter_overview", "historical_context", "archaeology_geography"],
        },
        "archaeology_records": {
            "decision": "remove_confirmed_bad_genesis_anchor",
            "record_ids": [entry["record_id"] for entry in CONFIRMED_CKL_REPAIRS],
            "remaining_evidence_ids": sorted(
                evidence_id for evidence_id in genesis_ids
                if any(evidence_id.startswith(f"{entry['record_id']}:") for entry in CONFIRMED_CKL_REPAIRS)
            ),
        },
        "cross_testament_and_canonical_reuse": {
            "decision": "retain_as_reception_or_intertextual_reuse",
            "examples": ["col-image", "col-new-humanity", "john-logos", "zephaniah-creation-reversal"],
            "overview_eligible": False,
        },
        "generic_archaeology": {
            "decision": "not_first_audience_context",
            "excluded_from": ["chapter_overview", "historical_context", "archaeology_geography"],
        },
    }

    return {
        "report_version": "commentary-v1.1-semantic-relevance-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "canary_chapters_audited": len(rows),
            "full_canonical_cleanup_attempted": False,
            "production_release_modified": False,
            "provider_calls": 0,
        },
        "summary": {
            "evidence_items_examined": len(items),
            "direct_context_items": role_counts[DIRECT_CONTEXT],
            "book_context_items": role_counts["BOOK_CONTEXT"],
            "later_intertextual_items": role_counts[LATER_RECEPTION] + role_counts[INTERTEXTUAL_REUSE],
            "comparative_items": role_counts[COMPARATIVE_CONTEXT],
            "generic_background_items": role_counts[GENERIC_BACKGROUND],
            "weakly_related_items": role_counts[WEAKLY_RELATED],
            "semantically_misanchored_items": role_counts[SEMANTICALLY_MISANCHORED],
            "confirmed_misanchored_ckl_records": len(CONFIRMED_CKL_REPAIRS),
        },
        "ckl_changes": {
            "anchors_removed": CONFIRMED_CKL_REPAIRS,
            "anchors_narrowed": [],
            "anchors_retyped_or_reclassified": [
                {
                    "evidence_id": "2-corinthians:interpretive_note:21",
                    "old_relationship": "direct Scripture overlap",
                    "new_relationship": LATER_RECEPTION,
                    "reason": "2 Corinthians is later New Testament reception of Genesis 1:3, not first-audience Genesis historical context.",
                    "affected_chapter": "Genesis 1",
                }
            ],
            "records_examined": len(parent_ids),
            "records_unchanged": max(0, len(parent_ids) - len(CONFIRMED_CKL_REPAIRS)),
        },
        "chapters": chapters,
        "controls": controls,
        "json_sqlite_agreement": certification.get("json_sqlite_agreement", {}),
        "leakage_audit": certification.get("retrieval_leakage_audit", {}),
        "regeneration_eligibility": {
            "before_low_information_audit": 936,
            "after_low_information_audit": 935,
            "changed_chapters": [
                {
                    "reference": "Psalms 24",
                    "before": True,
                    "after": False,
                    "reason": "No semantically relevant section-eligible evidence remained after role filtering.",
                }
            ],
        },
        "evidence_items": items,
    }


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "chapters": report["scope"]["canary_chapters_audited"],
        "evidence_items": report["summary"]["evidence_items_examined"],
        "summary": report["summary"],
        "report": str(REPORT_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
