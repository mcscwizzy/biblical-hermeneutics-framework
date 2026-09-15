"""Bounded, deterministic v1.2 applicability-enforcement recompile.

This tool reads the CKL and ASV data, writes a new immutable diagnostic
namespace, and makes no model calls.  It deliberately does not alter CKL,
commentary prose, reader contracts, or Gate inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import (
    classify_evidence_availability,
    evidence_contribution_diagnostic,
)
from bhf_agent.chapter_commentary.evidence_applicability import (
    COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
    evaluate_evidence_applicability,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.ckl import load_canonical_library
from bhf_agent.presentation.evidence import build_evidence_bundle
from bhf_agent.presentation.evidence_normalization import LEGACY_FIELDS
from bhf_agent.presentation.models import EntityRef, EvidenceBundle, EvidenceItem
from bhf_agent.presentation.references import _BOOK_ALIASES, anchor_specificity, references_overlap
from framework.canonical_library.repository import CKLRepositoryConfig
from framework.canonical_library.scripture import parse_scripture_references


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_NAMESPACE = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-upstream-evidence-quality-diagnostic-v1-4bf89c81144e13aad6eae6b3"
CONTRACT_FREEZE = ROOT / "docs/commentary-v1.2-evidence-applicability-contract-freeze-v1.json"
CANONICAL_PATH = ROOT / "bhf_agent/data/asv_bible.json"
CASES = {
    "2_kings_004": {"book": "2 Kings", "chapter": 4, "reference": "2 Kings 4", "before_bundle": "commentary-v1.1-scale/batch-007/evidence-bundles/2_kings_004.json", "spans": [(1, 7), (8, 17), (18, 37), (38, 41), (42, 44)]},
    "psalms_103": {"book": "Psalms", "chapter": 103, "reference": "Psalms 103", "before_bundle": "commentary-v1.1-scale/batch-007/evidence-bundles/psalms_103.json", "spans": [(1, 5), (6, 7), (8, 13), (14, 18), (19, 22)]},
    "psalms_019": {"book": "Psalms", "chapter": 19, "reference": "Psalms 19", "before_bundle": "commentary-v1.1-scale/batch-007/evidence-bundles/psalms_019.json", "spans": [(1, 6), (7, 11), (12, 14)]},
    "numbers_002": {"book": "Numbers", "chapter": 2, "reference": "Numbers 2", "before_bundle": "commentary-v1.5-scale-pilot/wave-a/canary/evidence-bundles/numbers_002.json", "spans": [(1, 34)]},
    "numbers_001": {"book": "Numbers", "chapter": 1, "reference": "Numbers 1", "before_bundle": "commentary-v1.1-scale/batch-008/evidence-bundles/numbers_001.json", "spans": [(1, 54)]},
}
BEFORE_AVAILABILITY = {
    "2_kings_004": "AVAILABLE",
    "psalms_103": "AVAILABLE",
    "psalms_019": "AVAILABLE",
    "numbers_002": "THIN",
    "numbers_001": "AVAILABLE",
}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bundle_from_dict(data: dict[str, Any]) -> EvidenceBundle:
    return EvidenceBundle(
        passage_ref=data["passage_ref"],
        entities={bucket: [EntityRef(**value) for value in data.get("entities", {}).get(bucket, [])] for bucket in ("people", "places", "groups", "events", "artifacts")},
        evidence_items=[EvidenceItem(**value) for value in data.get("evidence_items", [])],
        geography=data.get("geography", {}),
        provenance=data.get("provenance", {}),
        version=data.get("version", "1.0"),
        evidence_hash=data.get("evidence_hash", ""),
    )


def current_ckl() -> Any:
    return load_canonical_library(
        config=CKLRepositoryConfig(
            backend="sqlite",
            database_path=str(ROOT / ".bhf/ckl.sqlite"),
            json_root=str(ROOT / "framework/canonical_library"),
            stale_database_policy="ignore",
            read_only=True,
        )
    )


def max_verse(book: str, chapter: int) -> int:
    return max(int(value["verse"]) for value in bible.resolve_chapter(book, chapter)["verses"])


def verse_set(reference: str, *, book: str, chapter: int) -> set[int]:
    spans = parse_scripture_references(reference, book_alias_lookup=_BOOK_ALIASES)
    result: set[int] = set()
    max_value = max_verse(book, chapter)
    for span in spans:
        if span.book != bible.normalize_book_name(book):
            continue
        end_chapter = span.end_chapter or span.start_chapter
        if span.start_chapter != chapter or end_chapter != chapter:
            continue
        first = span.start_verse or 1
        last = span.end_verse or max_value
        result.update(range(first, min(last, max_value) + 1))
    return result


def coverage(bundle: EvidenceBundle, spec: dict[str, Any]) -> dict[str, Any]:
    eligible = [
        item for item in bundle.evidence_items
        if evaluate_evidence_applicability(item, bundle.passage_ref).current_chapter_eligible
    ]
    all_verses = set(range(1, max_verse(spec["book"], spec["chapter"]) + 1))
    any_verses = set().union(*(verse_set(anchor, book=spec["book"], chapter=spec["chapter"]) for item in eligible for anchor in item.passage_anchors)) if eligible else set()
    spans = []
    for first, last in spec["spans"]:
        requested = set(range(first, last + 1))
        spans.append({
            "requested_interval": f"{spec['book']} {spec['chapter']}:{first}-{last}",
            "eligible_evidence_verses": sorted(requested & any_verses),
            "covered": bool(requested & any_verses),
        })
    return {
        "chapter_verse_count": len(all_verses),
        "useful_verse_ancestry_coverage": sorted(any_verses),
        "useful_verse_ancestry_coverage_count": len(any_verses),
        "useful_verse_ancestry_coverage_percentage": round(100 * len(any_verses) / len(all_verses), 2),
        "spans": spans,
    }


def chapter_report(key: str, lib: Any) -> tuple[dict[str, Any], EvidenceBundle, Any, list[Any]]:
    spec = CASES[key]
    results = list(lib.retrieve_by_scripture_reference(spec["reference"], limit=100, include_placeholders=False))
    bundle = build_evidence_bundle(spec["reference"], canonical_results=results)
    synthesis = compile_chapter_synthesis(bundle, book=spec["book"], chapter=spec["chapter"])
    decisions = [evidence_contribution_diagnostic(item, bundle.passage_ref) for item in bundle.evidence_items]
    reason_breakdown = Counter(row["reason"] for row in decisions)
    eligible_count = sum(row["new_specific"] for row in decisions)
    current_count = sum(row["status"] == "eligible" for row in decisions)
    before_raw = read_json(ROOT / ".bhf-data/bhf-commentary-candidates" / spec["before_bundle"])
    before_synthesis = read_json(PREVIOUS_NAMESPACE / "chapter-reports" / f"{key}.json")
    before_hash = before_raw.get("evidence_hash", "")
    after_hash = bundle.evidence_hash
    before_synthesis_hash = before_synthesis.get("reproduced_synthesis", {}).get("synthesis_hash", "")
    after_current = sum(unit.passage_scope == "CURRENT_CHAPTER" for unit in synthesis.synthesis_units)
    after_surrounding = sum(unit.passage_scope == "SURROUNDING_PASSAGE" for unit in synthesis.synthesis_units)
    report = {
        "reference": spec["reference"],
        "source": {
            "retrieved_ckl_object_count": len(results),
            "fresh_bundle_version": bundle.version,
            "fresh_evidence_hash": after_hash,
            "fresh_synthesis_hash": synthesis.synthesis_hash,
        },
        "before": {
            "bundle_path": str((ROOT / ".bhf-data/bhf-commentary-candidates" / spec["before_bundle"]).relative_to(ROOT)),
            "evidence_count": len(before_raw.get("evidence_items", [])),
            "evidence_hash": before_hash,
            "availability": BEFORE_AVAILABILITY[key],
            "synthesis_hash": before_synthesis_hash,
            "synthesis_unit_count": before_synthesis.get("metrics", {}).get("raw_synthesis_count", len(before_synthesis.get("synthesis_units", []))),
            "current_chapter_synthesis_count": sum(unit.get("passage_scope") == "CURRENT_CHAPTER" for unit in before_synthesis.get("synthesis_units", [])),
            "surrounding_passage_count": sum(unit.get("passage_scope") == "SURROUNDING_PASSAGE" for unit in before_synthesis.get("synthesis_units", [])),
        },
        "after": {
            "evidence_count": len(bundle.evidence_items),
            "current_chapter_eligible_evidence_count": current_count,
            "availability": classify_evidence_availability(bundle).value,
            "synthesis_unit_count": len(synthesis.synthesis_units),
            "current_chapter_synthesis_count": after_current,
            "surrounding_passage_count": after_surrounding,
            "excluded_from_commentary_count": len(bundle.evidence_items) - current_count,
            "reason_breakdown": dict(sorted(reason_breakdown.items())),
            "synthesis_coverage": coverage(bundle, spec),
            "evidence_hash_changed": before_hash != after_hash,
            "synthesis_hash_changed": before_synthesis_hash != synthesis.synthesis_hash,
        },
        "evidence_diagnostics": decisions,
        "controls": {"numbers_1_or_2": key in {"numbers_001", "numbers_002"}},
    }
    return report, bundle, synthesis, results


def asv_contamination_scan() -> dict[str, Any]:
    data = read_json(CANONICAL_PATH)
    next_psalm = re.compile(r"\bPsalm\s+(?P<number>\d+)\b", re.IGNORECASE)
    chief = re.compile(r"\bFor the Chief Musician\b", re.IGNORECASE)
    rows: list[dict[str, Any]] = []
    for book in data.get("books", []):
        for chapter in book.get("chapters", []):
            for verse in chapter.get("verses", []):
                text = str(verse.get("text", ""))
                match = next_psalm.search(text)
                if not match:
                    continue
                rows.append({
                    "book": book.get("name"),
                    "chapter": int(chapter.get("chapter", 0)),
                    "verse": int(verse.get("verse", 0)),
                    "next_psalm_number": int(match.group("number")),
                    "is_next_psalm_boundary": book.get("name") == "Psalms" and int(match.group("number")) == int(chapter.get("chapter", 0)) + 1,
                    "contains_chief_musician": bool(chief.search(text)),
                    "text_sha256": sha256_bytes(text.encode("utf-8")),
                    "text": text,
                })
    psalm_rows = [row for row in rows if row["book"] == "Psalms"]
    ps19 = [row for row in psalm_rows if row["chapter"] == 19 and row["verse"] == 14]
    return {
        "source_path": str(CANONICAL_PATH.relative_to(ROOT)),
        "source_sha256": sha256_file(CANONICAL_PATH),
        "scan_method": "deterministic regex scan of every ASV verse for next-Psalm labels and For the Chief Musician headings",
        "total_matches": len(rows),
        "matches_by_book": dict(sorted(Counter(row["book"] for row in rows).items())),
        "psalms_matches": len(psalm_rows),
        "psalms_next_boundary_matches": sum(row["is_next_psalm_boundary"] for row in psalm_rows),
        "psalms_chief_musician_matches": sum(row["contains_chief_musician"] for row in psalm_rows),
        "psalm_19_14_matches": ps19,
        "other_psalms_boundary_matches": [row for row in psalm_rows if not (row["chapter"] == 19 and row["verse"] == 14)],
        "classification": "systematic Psalms heading-at-preceding-verse boundary pattern; Psalm 19 is not isolated",
        "safe_repair_decision": "defer systematic heading representation migration; preserve all legitimate superscription text while this isolated Psalm 19 correction removes only the demonstrably adjacent Psalm 20 suffix",
    }


def ckl_pollution_inventory() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    object_root = ROOT / "framework/canonical_library/objects"
    for path in sorted(object_root.rglob("*.json")):
        raw = read_json(path)
        anchors = raw.get("scripture_references") or []
        if not isinstance(anchors, list):
            anchors = [anchors]
        structured_children = [
            child
            for field in ("evidence_items", "claims", "interpretive_notes")
            for child in (raw.get(field) or [])
            if isinstance(child, dict)
        ]
        if any(
            any(
                references_overlap(
                    str(child_anchor.get("reference") if isinstance(child_anchor, dict) else child_anchor),
                    str(parent_anchor.get("reference") if isinstance(parent_anchor, dict) else parent_anchor),
                )
                for child_anchor in (child.get("scripture_references") or child.get("passage_anchors") or [])
                for parent_anchor in anchors
            )
            for child in structured_children
        ):
            continue
        fields = [field for field in LEGACY_FIELDS if raw.get(field)]
        for raw_anchor in anchors:
            anchor = raw_anchor.get("reference") if isinstance(raw_anchor, dict) else str(raw_anchor)
            anchor = " ".join(str(anchor or "").split())
            specificity = anchor_specificity(anchor)
            if specificity not in {"verse", "chapter"}:
                continue
            parsed = parse_scripture_references(anchor, book_alias_lookup=_BOOK_ALIASES)
            for span in parsed:
                for field in fields:
                    rows.append({
                        "object_id": raw.get("id"),
                        "parent_object_type": raw.get("type"),
                        "title": raw.get("title"),
                        "legacy_field": field,
                        "book": span.book,
                        "anchor": anchor,
                        "anchor_specificity": specificity,
                        "semantic_relationship": "legacy_parent_inheritance",
                        "review_status": raw.get("review_status"),
                        "source_status": raw.get("source_status"),
                        "path": str(path.relative_to(ROOT)),
                    })
    dimensions = {
        "parent_object_type": Counter(row["parent_object_type"] for row in rows),
        "legacy_field": Counter(row["legacy_field"] for row in rows),
        "book": Counter(row["book"] for row in rows),
        "anchor_specificity": Counter(row["anchor_specificity"] for row in rows),
        "semantic_relationship": Counter(row["semantic_relationship"] for row in rows),
        "review_status": Counter(str(row["review_status"] or "unspecified") for row in rows),
        "source_status": Counter(str(row["source_status"] or "unspecified") for row in rows),
    }
    family_counts = Counter((row["parent_object_type"], row["legacy_field"], row["book"]) for row in rows)
    highest = [
        {"parent_object_type": key[0], "legacy_field": key[1], "book": key[2], "count": count}
        for key, count in sorted(family_counts.items(), key=lambda item: (-item[1], item[0]))[:25]
    ]
    return {
        "criteria": ["no structured child evidence/claims/interpretive notes", "legacy field present", "parent Scripture anchor has verse/chapter specificity"],
        "suspicious_inherited_anchor_count": len(rows),
        "distinct_parent_object_count": len({row["object_id"] for row in rows}),
        "counts_by_dimension": {key: dict(sorted(value.items())) for key, value in dimensions.items()},
        "highest_volume_pollution_families": highest,
        "rows": rows,
    }


def contract_hashes() -> dict[str, Any]:
    frozen = read_json(CONTRACT_FREEZE)
    after = {}
    for key, value in frozen["contracts"].items():
        path = ROOT / value["path"]
        after[key] = {"path": value["path"], "before_sha256": value["sha256"], "after_sha256": sha256_file(path)}
    return {
        "before": frozen["contracts"],
        "after": after,
        "unchanged_non_asv": all(value["before_sha256"] == value["after_sha256"] for key, value in after.items() if key != "asv_bible"),
    }


def run(output_dir: Path | None = None) -> Path:
    lib = current_ckl()
    reports: dict[str, dict[str, Any]] = {}
    packets: dict[str, tuple[EvidenceBundle, Any, list[Any]]] = {}
    for key in CASES:
        report, bundle, synthesis, results = chapter_report(key, lib)
        reports[key] = report
        packets[key] = (bundle, synthesis, results)
    inventory = ckl_pollution_inventory()
    scan = asv_contamination_scan()
    identity_payload = {
        "implementation": COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
        "starting_sha": "d6dfa57307a60a4e0e042b4705f7b68e0cf03b72",
        "before_diagnostic": "4bf89c81144e13aad6eae6b3",
        "cases": {key: {"evidence": value["source"]["fresh_evidence_hash"], "synthesis": value["source"]["fresh_synthesis_hash"]} for key, value in reports.items()},
        "asv_before": read_json(CONTRACT_FREEZE)["contracts"]["asv_bible"]["sha256"],
    }
    identity = sha256_bytes(stable_json(identity_payload).encode("utf-8"))[:24]
    target = output_dir or ROOT / f".bhf-data/bhf-commentary-candidates/commentary-v1.2-applicability-enforcement-v1-{identity}"
    (target / "chapter-reports").mkdir(parents=True, exist_ok=True)
    (target / "evidence-bundles").mkdir(exist_ok=True)
    (target / "synthesis").mkdir(exist_ok=True)
    (target / "evidence-diagnostics").mkdir(exist_ok=True)
    for key, report in reports.items():
        bundle, synthesis, results = packets[key]
        (target / "chapter-reports" / f"{key}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / "evidence-bundles" / f"{key}.json").write_text(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / "synthesis" / f"{key}.json").write_text(json.dumps(synthesis.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (target / "evidence-diagnostics" / f"{key}.json").write_text(json.dumps(report["evidence_diagnostics"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "ckl-pollution-inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target / "asv-contamination-scan.json").write_text(json.dumps(scan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    contracts = contract_hashes()
    (target / "contract-identities.json").write_text(json.dumps(contracts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "artifact_version": "commentary-v1.2-applicability-enforcement-v1",
        "identity": identity,
        "branch": "feat/commentary-v1.2-enrichment",
        "starting_sha": "d6dfa57307a60a4e0e042b4705f7b68e0cf03b72",
        "previous_diagnostic_identity": "4bf89c81144e13aad6eae6b3",
        "implementation_version": COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
        "model_calls_performed": 0,
        "commentary_generated": False,
        "five_case_sol_regression_run": False,
        "seventy_five_chapter_pilot_started": False,
        "contracts_unchanged": contracts["unchanged_non_asv"],
        "canonical_ckl_database_sha256": sha256_file(ROOT / ".bhf/ckl.sqlite"),
        "asv_sha256": scan["source_sha256"],
        "source_packets_are_fresh_and_deterministic": True,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final = {
        "artifact_version": manifest["artifact_version"],
        "identity": identity,
        "previous_diagnostic": str(PREVIOUS_NAMESPACE.relative_to(ROOT)),
        "implementation_version": COMMENTARY_EVIDENCE_APPLICABILITY_VERSION,
        "chapters": reports,
        "controls": {"numbers_1": reports["numbers_001"], "numbers_2": reports["numbers_002"]},
        "ckl_pollution_inventory_summary": {key: value for key, value in inventory.items() if key != "rows"},
        "asv_contamination_scan": {key: value for key, value in scan.items() if key != "other_psalms_boundary_matches"},
        "contract_hashes": contracts,
        "canonical_ckl_database": {"path": ".bhf/ckl.sqlite", "sha256": sha256_file(ROOT / ".bhf/ckl.sqlite")},
        "tests": {"model_calls": 0, "generic_synthetic_tests": "tests/test_commentary_evidence_applicability.py", "status": "pending-until-test-run"},
    }
    (target / "final-report.json").write_text(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = {str(path.relative_to(target)): sha256_file(path) for path in sorted(target.rglob("*")) if path.is_file() and path.name != "checksums.json"}
    (target / "checksums.json").write_text(json.dumps(checksums, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    print(run(args.output_dir))


if __name__ == "__main__":
    main()
