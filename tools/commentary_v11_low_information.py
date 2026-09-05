#!/usr/bin/env python3
"""Audit low-information commentary without changing availability state.

The audit is intentionally separate from DATA_GAP/THIN/AVAILABLE.  It reads
the immutable v1.0.1 commentary corpus, rebuilds the current validated
EvidenceBundle for each detected artifact, and reports whether a grounded
regeneration is supported.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.storage import load_commentary, list_commentaries


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.0.1"
DEFAULT_OUTPUT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1" / "low-information-commentary.json"
DEFAULT_MARKDOWN = REPO_ROOT / "docs" / "commentary-v1.1-low-information-audit.md"
AUDIT_VERSION = "low-information-commentary-v1"
REQUIRED_CONTROL = ("Zephaniah", 1)

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("verse_count_boilerplate", re.compile(r"\b(?:contains|has)\s+\d+\s+verses\b", re.IGNORECASE)),
    ("opening_quotation_label", re.compile(r"\b(?:it\s+)?(?:opens|begins)\s+with\s*:", re.IGNORECASE)),
    ("closing_quotation_label", re.compile(r"\b(?:it\s+)?(?:concludes|ends)\s+with\s*:", re.IGNORECASE)),
    ("first_last_quotation_label", re.compile(r"\b(?:first|last)\s+verse\b.{0,80}\b(?:quote|says|reads)", re.IGNORECASE | re.DOTALL)),
)
CONTEXTUAL_SECTION_KINDS = {
    "historical_context",
    "people_places",
    "archaeology_geography",
    "language_literary",
    "chronology",
    "interpretive_questions",
    "things_easy_to_miss",
    "dig_deeper",
}


def _commentary_text(commentary: Any) -> str:
    return " ".join(
        block.text
        for section in commentary.sections
        for block in section.blocks
    )


def detect_low_information(commentary: Any) -> dict[str, Any]:
    text = _commentary_text(commentary)
    markers = [name for name, pattern in MARKERS if pattern.search(text)]
    section_kinds = [section.kind for section in commentary.sections]
    contextual_sections = sorted(set(section_kinds).intersection(CONTEXTUAL_SECTION_KINDS))
    cited_ids = sorted({evidence_id for section in commentary.sections for block in section.blocks for evidence_id in block.evidence_ids})
    # Two or more explicit canonical-summary markers are required.  This keeps
    # a genuine contextual paragraph that happens to mention an opening verse
    # outside the internal classification.
    is_low_information = len(markers) >= 2 and (
        {"verse_count_boilerplate", "opening_quotation_label"}.issubset(markers)
        or {"opening_quotation_label", "closing_quotation_label"}.issubset(markers)
        or "first_last_quotation_label" in markers
    )
    if not is_low_information:
        return {"is_low_information": False, "markers": markers}
    return {
        "is_low_information": True,
        "classification": "LOW_INFORMATION_COMMENTARY",
        "markers": markers,
        "section_kinds": section_kinds,
        "contextual_section_kinds": contextual_sections,
        "cited_evidence_ids": cited_ids,
        "canonical_summary_only": not contextual_sections,
        "text_length": len(text),
    }


def _bundle_assessment(commentary: Any, detection: dict[str, Any]) -> dict[str, Any]:
    bundle = get_chapter_evidence_bundle(commentary.book, commentary.chapter)
    if bundle is None:
        return {
            "evidence_bundle_available": False,
            "evidence_hash": None,
            "evidence_item_count": 0,
            "useful_contextual_evidence_count": 0,
            "evidence_supports_regeneration": False,
            "evidence_limitation": "EvidenceBundle unavailable",
            "recomputed_availability": None,
            "cited_evidence_resolved": False,
            "unused_evidence_ids": [],
        }
    useful = [
        item for item in bundle.evidence_items
        if item.claim.strip() and item.source_ids and item.passage_anchors
    ]
    cited_ids = set(detection.get("cited_evidence_ids", []))
    bundle_ids = {item.id for item in bundle.evidence_items}
    return {
        "evidence_bundle_available": True,
        "evidence_hash": bundle.evidence_hash,
        "evidence_item_count": len(bundle.evidence_items),
        "useful_contextual_evidence_count": len(useful),
        "evidence_categories": sorted({item.category for item in useful}),
        "evidence_supports_regeneration": bool(useful),
        "evidence_limitation": None if useful else "No source-addressable anchored contextual evidence",
        "recomputed_availability": classify_evidence_availability(bundle).value,
        "cited_evidence_resolved": cited_ids.issubset(bundle_ids),
        "unused_evidence_ids": sorted(bundle_ids - cited_ids),
        "current_commentary_uses_contextual_section": bool(detection.get("contextual_section_kinds")),
    }


def audit(source: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for book, chapter in list_commentaries(source):
        commentary = load_commentary(source, book, chapter)
        if commentary is None or commentary.status != "validated":
            continue
        detection = detect_low_information(commentary)
        if not detection.get("is_low_information"):
            continue
        assessment = _bundle_assessment(commentary, detection)
        records.append({
            "book": book,
            "chapter": chapter,
            "reference": commentary.reference,
            "classification": "LOW_INFORMATION_COMMENTARY",
            "stored_availability": commentary.evidence_availability,
            "stored_status": commentary.status,
            "detection": detection,
            "bundle_assessment": assessment,
            "regeneration_decision": "REGENERATE_FROM_LOCKED_EVIDENCE" if assessment["evidence_supports_regeneration"] else "KEEP_CONSERVATIVE_AND_REPORT_LIMITATION",
        })
    by_state = Counter(record["stored_availability"] for record in records)
    by_book: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["book"]].append(record)
    for book, rows in sorted(grouped.items()):
        by_book[book] = {
            "total": len(rows),
            "by_availability": dict(sorted(Counter(row["stored_availability"] for row in rows).items())),
            "evidence_supports_regeneration": sum(row["bundle_assessment"]["evidence_supports_regeneration"] for row in rows),
            "evidence_insufficient": sum(not row["bundle_assessment"]["evidence_supports_regeneration"] for row in rows),
            "chapters": [row["chapter"] for row in sorted(rows, key=lambda item: item["chapter"])],
        }
    control = next((record for record in records if (record["book"], record["chapter"]) == REQUIRED_CONTROL), None)
    if control is None:
        raise RuntimeError("required LOW_INFORMATION_COMMENTARY control Zephaniah 1 was not detected")
    return {
        "audit_version": AUDIT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_corpus": str(source),
        "source_release": "commentary-v1.0.1",
        "availability_mutated": False,
        "classification": "LOW_INFORMATION_COMMENTARY",
        "total_validated_commentary_artifacts": len(list_commentaries(source)),
        "total_low_information_commentary": len(records),
        "counts_by_availability": dict(sorted(by_state.items())),
        "counts_by_book": by_book,
        "chapters_evidence_supports_regeneration": [
            record["reference"] for record in records if record["bundle_assessment"]["evidence_supports_regeneration"]
        ],
        "chapters_evidence_insufficient": [
            record["reference"] for record in records if not record["bundle_assessment"]["evidence_supports_regeneration"]
        ],
        "required_controls": {
            "Zephaniah 1": control,
        },
        "records": sorted(records, key=lambda item: (item["book"].casefold(), item["chapter"])),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# BHF v1.1 Low-Information Commentary Audit",
        "",
        "This internal quality classification is separate from `DATA_GAP`, `THIN`, and `AVAILABLE`. It does not mutate evidence availability.",
        "",
        f"- Source: `{report['source_release']}`",
        f"- Validated artifacts audited: {report['total_validated_commentary_artifacts']}",
        f"- `LOW_INFORMATION_COMMENTARY`: {report['total_low_information_commentary']}",
        f"- Evidence supports regeneration: {len(report['chapters_evidence_supports_regeneration'])}",
        f"- Evidence insufficient: {len(report['chapters_evidence_insufficient'])}",
        "",
        "## Counts by availability",
        "",
        "| Availability | Low-information chapters |",
        "|---|---:|",
    ]
    for state, count in report["counts_by_availability"].items():
        lines.append(f"| {state} | {count} |")
    lines.extend([
        "",
        "## Required control",
        "",
        "Zephaniah 1 is included as a required control. Its v1.0.1 artifact uses the generic verse-count/opening/closing quotation pattern; its v1.1 candidate must be synthesized only from its locked EvidenceBundle and must not decide disputed authorship/composition questions as settled fact.",
        "",
        "## Regeneration sets",
        "",
        "Evidence-supported chapters are listed in `low-information-commentary.json` under `chapters_evidence_supports_regeneration`; chapters without source-addressable anchored evidence are listed under `chapters_evidence_insufficient` and remain conservative.",
        "",
        "## Counts by book",
        "",
        "| Book | Total | AVAILABLE | THIN | DATA_GAP | Regenerate | Insufficient |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for book, data in report["counts_by_book"].items():
        states = data["by_availability"]
        lines.append(
            f"| {book} | {data['total']} | {states.get('AVAILABLE', 0)} | {states.get('THIN', 0)} | {states.get('DATA_GAP', 0)} | {data['evidence_supports_regeneration']} | {data['evidence_insufficient']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    report = audit(args.source)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_markdown(report, args.markdown_output)
    print(json.dumps({
        "total_low_information_commentary": report["total_low_information_commentary"],
        "counts_by_availability": report["counts_by_availability"],
        "evidence_supports_regeneration": len(report["chapters_evidence_supports_regeneration"]),
        "evidence_insufficient": len(report["chapters_evidence_insufficient"]),
        "zephaniah_1": report["required_controls"]["Zephaniah 1"]["bundle_assessment"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
