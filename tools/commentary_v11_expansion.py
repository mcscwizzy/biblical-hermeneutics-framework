#!/usr/bin/env python3
"""Plan and certify the evidence-first BHF Commentary v1.1 expansion.

This tool is deliberately deterministic.  It uses canonical text only for
transparent prioritization signals, and uses CKL Scripture retrieval plus the
production EvidenceBundle builder for certification.  It never calls a model
provider and it never writes released commentary or CKL source objects.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent import bible
from bhf_agent.ckl import load_canonical_library
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.presentation import build_evidence_bundle
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.database_builder import build_database, verify_database
from framework.canonical_library.scripture import (
    parse_scripture_references,
    scripture_reference_overlaps,
)
from tools.ckl_coverage_report import scan
from tools.diagnose_scripture_retrieval import _raw_candidate_ids, _reference_entries


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
DEFAULT_REPORT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1" / "data-gap-priority.json"
REPORT_VERSION = "commentary-v1.1-expansion-v2-semantic"

P1_CHAPTERS = {
    ("Numbers", 3), ("Numbers", 5), ("Numbers", 7), ("Numbers", 8),
    ("Luke", 5), ("Luke", 8), ("Luke", 13),
}

SIGNALS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    ("priesthood", ("priest", "levite", "aaron", "holy place", "sanctuary"), 8.0),
    ("sacrifice_ritual", ("sacrifice", "offering", "altar", "incense", "blood", "burnt", "ritual"), 8.0),
    ("purity", ("unclean", "clean", "defile", "purity", "impure", "holy"), 7.0),
    ("law_social_order", ("law", "statute", "judgment", "inheritance", "servant", "slave", "widow", "vow"), 6.0),
    ("warfare", ("war", "battle", "army", "sword", "enemy", "siege", "fought"), 6.0),
    ("kingship_succession", ("king", "queen", "throne", "crown", "reign", "successor", "royal"), 6.0),
    ("prophetic_symbol", ("vision", "sign", "symbol", "act", "eagle", "wheel", "yoke"), 7.0),
    ("temple_tabernacle", ("temple", "tabernacle", "tent of meeting", "curtain", "ark", "glory"), 8.0),
    ("family_marriage", ("wife", "husband", "marry", "marriage", "daughter", "son", "bride", "concubine"), 5.0),
    ("geography", ("river", "mountain", "wilderness", "city", "gate", "road", "sea", "valley"), 4.0),
    ("supernatural_disputed", ("angel", "spirit", "demon", "dead", "miracle", "resurrection", "satan"), 7.0),
)

GENRE_GUIDANCE = {
    "narrative": {
        "evidence": ["history", "culture", "archaeology", "geography", "politics", "institutions", "chronology"],
        "questions": ["What setting, institution, custom, or sequence does the scene assume?", "Which claims are tied to this episode rather than the whole book?"]
    },
    "law": {
        "evidence": ["ritual and purity", "priesthood", "sacrifice", "social order", "covenant setting", "language"],
        "questions": ["What function does the instruction have inside Israel's covenant life?", "Is the claim anchored to the law unit rather than generalized across the book?"]
    },
    "poetry": {
        "evidence": ["literary form", "parallelism", "worship context", "royal imagery", "temple imagery", "language", "superscription when sourced"],
        "questions": ["How do paired lines and images work together?", "What is textual observation, and what is later interpretation?"]
    },
    "wisdom": {
        "evidence": ["literary form", "household instruction", "education", "rhetoric", "parallelism", "metaphor", "social and economic context", "language"],
        "questions": ["Is this a maxim, reflection, dialogue, or rhetorical challenge?", "Does the supporting evidence clarify the social setting without turning a saying into a guarantee?"]
    },
    "prophecy": {
        "evidence": ["historical setting", "politics", "geography", "symbolic actions", "temple context", "covenant/law background", "literary structure", "sourced ANE context"],
        "questions": ["Who is addressed and what pressure is visible in the passage?", "Which symbolic or historical claims are actually source-supported?"]
    },
    "gospel": {
        "evidence": ["Second Temple setting", "geography", "social custom", "politics", "literary structure", "chronology"],
        "questions": ["What does this scene assume about its social setting?", "How does the Gospel's own narrative design constrain the contextual claim?"]
    },
}


def _book_genre(book: str) -> str:
    if book in {"Leviticus", "Numbers", "Deuteronomy", "Exodus"}:
        return "law"
    if book in {"Psalms", "Isaiah", "Jeremiah", "Ezekiel", "Lamentations", "Song of Solomon"}:
        return "poetry" if book in {"Psalms", "Lamentations", "Song of Solomon"} else "prophecy"
    if book in {"Proverbs", "Ecclesiastes", "Job"}:
        return "wisdom"
    if book in {"Matthew", "Mark", "Luke", "John"}:
        return "gospel"
    if book in {"Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Acts"}:
        return "narrative"
    return "narrative"


def _chapter_text(book: str, chapter: int) -> str:
    data = bible.resolve_chapter(book, chapter)
    return " ".join(str(verse.get("text", "")) for verse in data.get("verses", [])).casefold()


def _signal_score(book: str, chapter: int) -> tuple[float, list[dict[str, Any]]]:
    text = _chapter_text(book, chapter)
    matched: list[dict[str, Any]] = []
    score = 0.0
    for name, terms, weight in SIGNALS:
        hits = sorted({term for term in terms if term in text})
        if hits:
            score += weight + min(len(hits), 4) * 0.5
            matched.append({"factor": name, "weight": weight, "matched_terms": hits})
    return round(score, 2), matched


def _object_type_audit(library: Any, book: str, chapter: int) -> dict[str, Any]:
    reference = bible.verse_range_reference(book, chapter)
    results = list(library.retrieve_by_scripture_reference(reference, limit=100, include_placeholders=False))
    types = Counter(result.object.type for result in results)
    return {
        "reference": reference,
        "candidate_count": len(results),
        "candidate_types": dict(sorted(types.items())),
        "object_only_structural": bool(types) and set(types) <= {"book"},
        "candidate_ids": sorted(result.object.id for result in results),
    }


def _base_row(row: dict[str, Any], library: Any) -> dict[str, Any]:
    book, chapter = row["book"], int(row["chapter"])
    signal_score, factors = _signal_score(book, chapter)
    audit = _object_type_audit(library, book, chapter)
    genre = _book_genre(book)
    priority = signal_score
    if (book, chapter) in P1_CHAPTERS:
        priority += 40
    if book in {"1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezekiel"} and row["status"] == "DATA_GAP":
        priority += 14
    if genre in {"law", "prophecy", "gospel"}:
        priority += 3
    return {
        "book": book,
        "chapter": chapter,
        "reference": row["reference"],
        "status": row["status"],
        "genre": genre,
        "priority_score": round(priority, 2),
        "contextual_factors": factors,
        "p1_reason": "explicit v1.1 Priority 1 request" if (book, chapter) in P1_CHAPTERS else None,
        "valid_anchored_evidence": row["valid_anchored_evidence"],
        "raw_ckl_candidates": row["raw_ckl_candidates"],
        "rejected_candidates": row["rejected_candidates"],
        "object_type_audit": audit,
    }


def _sort(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (-float(r["priority_score"]), r["book"].casefold(), int(r["chapter"])))


def _available_canary_rows(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # These controls are intentionally known low-information v1.0.1 artifacts.
    # Zephaniah 1 is required because its released text is the canonical
    # "contains/open/concludes" example.
    wanted = [("Leviticus", 1), ("Psalms", 1), ("Zephaniah", 1), ("Luke", 1), ("Genesis", 1)]
    by_ref = {(r["book"], r["chapter"]): r for r in all_rows}
    selected = [
        {**by_ref[item], "low_information_control": True}
        for item in wanted
        if item in by_ref and by_ref[item]["status"] == "AVAILABLE"
    ]
    if len(selected) < 5:
        selected.extend(r for r in all_rows if r["status"] == "AVAILABLE" and r not in selected)
    return selected[:5]


def build_priority_report(coverage: dict[str, Any]) -> dict[str, Any]:
    library = load_canonical_library(config=CKLRepositoryConfig())
    all_rows = [_base_row(row, library) for row in coverage["chapter_results"]]
    structural = [r for r in all_rows if r["status"] == "DATA_GAP" and r["object_type_audit"]["object_only_structural"]]
    true_gaps = [r for r in all_rows if r["status"] == "DATA_GAP" and not r["object_type_audit"]["object_only_structural"]]
    thin = [r for r in all_rows if r["status"] == "THIN"]
    confusion = []
    for r in all_rows:
        confusion_score = float(r["priority_score"])
        if (r["book"], r["chapter"]) == ("1 Samuel", 28):
            confusion_score += 35
            r["known_example"] = True
        else:
            r["known_example"] = False
        confusion.append({**r, "confusion_score": round(confusion_score, 2)})
    confusion = sorted(confusion, key=lambda r: (-r["confusion_score"], r["book"].casefold(), r["chapter"]))[:50]
    dg_batch = _sort(true_gaps)[:10]
    thin_batch = _sort(thin)[:20]
    canary = dg_batch + thin_batch[:10] + _available_canary_rows(all_rows)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "current CKL inventory and 1,189 canonical chapters",
        "release_boundary": {
            "production_release": "commentary-v1.0.1",
            "production_selection": "BHF_COMMENTARY_RELEASE=commentary-v1.0.1",
            "candidate_release": "commentary-v1.1",
            "released_artifacts_modified": False,
        },
        "baseline": coverage["coverage_totals"],
        "data_gap_scope": {
            "strict_data_gaps": len([r for r in all_rows if r["status"] == "DATA_GAP"]),
            "object_only_structural_cases": len(structural),
            "likely_true_ckl_data_gaps": len(true_gaps),
            "structural_cases": structural,
        },
        "data_gap_priority": _sort(true_gaps),
        "thin_priority": _sort(thin),
        "high_confusion_priority": confusion,
        "selected_batches": {
            "data_gap_initial": dg_batch,
            "thin_initial": thin_batch,
            "commentary_canary": canary,
        },
        "low_information_canary_controls": [
            f"{row['book']} {row['chapter']}"
            for row in canary
            if row.get("low_information_control")
        ],
        "genre_guidance": GENRE_GUIDANCE,
        "method": {
            "deterministic": True,
            "model_knowledge_used_as_evidence": False,
            "signals_are_search_or_prioritization_factors_only": True,
            "adjacent_evidence_inherited": False,
            "object_only_records_count_as_context": False,
        },
    }


def _audit_chapter(library: Any, book: str, chapter: int, *, compare_library: Any | None = None) -> dict[str, Any]:
    reference = bible.verse_range_reference(book, chapter)
    query_results = list(library.retrieve_by_scripture_reference(reference, limit=100, include_placeholders=False))
    bundle = build_evidence_bundle(
        reference,
        canonical_results=query_results,
        bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    entries: list[dict[str, Any]] = []
    examined_records: list[dict[str, Any]] = []
    for result in query_results:
        data = result.object.to_dict()
        record_entries = _reference_entries(library, result.object)
        entries.extend(record_entries)
        examined_records.append(
            {
                "id": result.object.id,
                "type": result.object.type,
                "title": result.object.title,
                "anchor_layers": sorted({entry["source"].split("[", 1)[0] for entry in record_entries}),
                "source_metadata_count": len(data.get("sources") or []),
                "related_record_count": len(data.get("related_objects") or []) + len(data.get("related_entries") or []),
            }
        )
    ids = sorted(result.object.id for result in query_results)
    json_sqlite = None
    if compare_library is not None:
        other_results = list(compare_library.retrieve_by_scripture_reference(reference, limit=100, include_placeholders=False))
        other_bundle = build_evidence_bundle(
            reference,
            canonical_results=other_results,
            bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
        )
        json_sqlite = {
            "result_ids_agree": ids == sorted(result.object.id for result in other_results),
            "bundle_hash_agree": bundle.evidence_hash == other_bundle.evidence_hash,
            "first_ids": ids,
            "second_ids": sorted(result.object.id for result in other_results),
        }
    leakage = []
    for item in bundle.evidence_items:
        if not any(
            scripture_reference_overlaps(target, span)
            for anchor in item.passage_anchors
            for span in parse_scripture_references(anchor, book_alias_lookup=library._book_alias_lookup)
            for target in parse_scripture_references(reference, book_alias_lookup=library._book_alias_lookup)
        ):
            leakage.append(item.id)
    return {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "retrieval_result_ids": ids,
        "existing_ckl_audit": {
            "records_examined": examined_records,
            "anchor_layer_counts": dict(sorted(Counter(entry["source"].split("[", 1)[0] for entry in entries).items())),
            "source_metadata_records_examined": sum(item["source_metadata_count"] for item in examined_records),
            "related_record_links_examined": sum(item["related_record_count"] for item in examined_records),
        },
        "existing_evidence_reused": [
            {
                "evidence_id": item.id,
                "category": item.category,
                "claim": item.claim,
                "source_ids": item.source_ids,
                "passage_anchors": item.passage_anchors,
                "confidence": item.confidence,
                "semantic_relationship": item.relevance_metadata.get("semantic_relationship"),
            }
            for item in bundle.evidence_items
        ],
        "evidence_item_count": len(bundle.evidence_items),
        "evidence_categories": sorted({item.category for item in bundle.evidence_items}),
        "availability": classify_evidence_availability(bundle).value,
        "evidence_hash": bundle.evidence_hash,
        "source_gaps": [
            "no source-addressable evidence survived strict Scripture-anchor validation"
        ] if not bundle.evidence_items else [],
        "leakage_evidence_ids": leakage,
        "json_sqlite": json_sqlite,
        "all_retrieved_records_had_anchor_entries": bool(query_results) and all(entries),
    }


def certify(report: dict[str, Any], batch_name: str, output: Path) -> dict[str, Any]:
    chapters = report["selected_batches"][batch_name]
    with tempfile.TemporaryDirectory(prefix="bhf-v11-ckl-") as temp_dir:
        db_path = Path(temp_dir) / "ckl.sqlite"
        build_database(REPO_ROOT / "framework" / "canonical_library", db_path)
        verify_database(db_path, root=REPO_ROOT / "framework" / "canonical_library")
        json_library = load_canonical_library(config=CKLRepositoryConfig(backend="json", json_root=str(REPO_ROOT / "framework" / "canonical_library")))
        sqlite_library = load_canonical_library(config=CKLRepositoryConfig(backend="sqlite", database_path=str(db_path), json_root=str(REPO_ROOT / "framework" / "canonical_library"), stale_database_policy="ignore"))
        chapter_audits = [_audit_chapter(json_library, r["book"], r["chapter"], compare_library=sqlite_library) for r in chapters]
    errors = [
        {"reference": row["reference"], "error": "JSON/SQLite disagreement"}
        for row in chapter_audits if not row["json_sqlite"] or not row["json_sqlite"]["result_ids_agree"] or not row["json_sqlite"]["bundle_hash_agree"]
    ]
    errors.extend({"reference": row["reference"], "error": "evidence leakage"} for row in chapter_audits if row["leakage_evidence_ids"])
    payload = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "batch": batch_name,
        "workflow": ["select", "audit_existing_ckl", "validate_anchors", "rebuild_json_indexes", "verify_sqlite_indexes", "compare_json_sqlite", "build_evidence_bundles", "classify_availability", "leakage_audit", "lock"],
        "status": "LOCKED" if not errors else "BLOCKED",
        "chapters": chapter_audits,
        "json_sqlite_agreement": {
            "chapters": len(chapter_audits),
            "result_id_disagreements": sum(not (r["json_sqlite"] or {}).get("result_ids_agree", False) for r in chapter_audits),
            "bundle_hash_disagreements": sum(not (r["json_sqlite"] or {}).get("bundle_hash_agree", False) for r in chapter_audits),
        },
        "retrieval_leakage_audit": {
            "chapters_with_leakage": sum(bool(r["leakage_evidence_ids"]) for r in chapter_audits),
            "leaked_evidence_ids": sorted({item for r in chapter_audits for item in r["leakage_evidence_ids"]}),
        },
        "locked_evidence_bundle_hashes": {r["reference"]: r["evidence_hash"] for r in chapter_audits},
        "errors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return payload


def write_human_report(report: dict[str, Any], path: Path) -> None:
    def refs(rows: list[dict[str, Any]]) -> str:
        return ", ".join(f"{r['book']} {r['chapter']}" for r in rows)
    lines = [
        "# BHF Commentary v1.1 — Context Expansion",
        "",
        "This is development/candidate work on `feat/commentary-v1.1-expansion`. `commentary-v1.0` and `commentary-v1.0.1` remain immutable, and production selection remains `commentary-v1.0.1`.",
        "",
        "## Baseline and scope",
        "",
        f"Strict baseline: {report['baseline']['evidence_available']} AVAILABLE, {report['baseline']['thin']} THIN, {report['baseline']['data_gaps']} DATA_GAP across {report['baseline']['chapters_analyzed']} chapters.",
        f"The strict DATA_GAP set contains {report['data_gap_scope']['strict_data_gaps']} chapters. {report['data_gap_scope']['object_only_structural_cases']} are object-only structural cases, leaving {report['data_gap_scope']['likely_true_ckl_data_gaps']} likely true CKL DATA_GAP chapters for expansion.",
        "Prioritization signals are deterministic text/search factors only; they are not evidence and do not promote availability.",
        "",
        "## Initial batches",
        "",
        f"DATA_GAP batch ({len(report['selected_batches']['data_gap_initial'])}): {refs(report['selected_batches']['data_gap_initial'])}",
        f"THIN batch ({len(report['selected_batches']['thin_initial'])}): {refs(report['selected_batches']['thin_initial'])}",
        f"25-chapter canary ({len(report['selected_batches']['commentary_canary'])}): {refs(report['selected_batches']['commentary_canary'])}",
        "",
        "## High-confusion pass",
        "",
        "The ranked list is stored in `data-gap-priority.json`. 1 Samuel 28 is explicitly retained as a known context-thin example; the list does not decide whether the apparition was Samuel.",
        "",
        "## Genre-aware evidence guidance",
        "",
    ]
    for genre, guidance in report["genre_guidance"].items():
        lines.append(f"- **{genre}** — prefer {', '.join(guidance['evidence'])}. Ask: {' '.join(guidance['questions'])}")
    lines.extend([
        "",
        "## Evidence-first lock boundary",
        "",
        "Each batch must be audited against existing CKL first, then Scripture anchors are validated, JSON and SQLite are rebuilt/compared, EvidenceBundles are hashed, availability is classified, and leakage is checked before commentary candidates are generated. A source gap remains a DATA_GAP.",
        "",
        "## Reports",
        "",
        "- Machine-readable prioritization: `.bhf-data/bhf-commentary-candidates/commentary-v1.1/data-gap-priority.json`",
        "- Certified batch reports are written beside it as `evidence-certification-<batch>.json`.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    priority = sub.add_parser("prioritize")
    priority.add_argument("--coverage", type=Path, help="Existing ckl_coverage_report JSON; avoids rescanning")
    priority.add_argument("--json-output", type=Path, default=DEFAULT_REPORT)
    priority.add_argument("--markdown-output", type=Path, default=REPO_ROOT / "docs" / "commentary-v1.1-expansion-plan.md")
    certify_parser = sub.add_parser("certify")
    certify_parser.add_argument("--priority-report", type=Path, default=DEFAULT_REPORT)
    certify_parser.add_argument("--batch", choices=("data_gap_initial", "thin_initial", "commentary_canary"), default="data_gap_initial")
    certify_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "prioritize":
        coverage = json.loads(args.coverage.read_text(encoding="utf-8")) if args.coverage else scan()
        report = build_priority_report(coverage)
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        write_human_report(report, args.markdown_output)
        print(json.dumps({"data_gap": len(report["selected_batches"]["data_gap_initial"]), "thin": len(report["selected_batches"]["thin_initial"]), "canary": len(report["selected_batches"]["commentary_canary"]), "report": str(args.json_output)}, indent=2))
        return 0
    report = json.loads(args.priority_report.read_text(encoding="utf-8"))
    output = args.output or args.priority_report.parent / f"evidence-certification-{args.batch}.json"
    payload = certify(report, args.batch, output)
    print(json.dumps({"batch": args.batch, "status": payload["status"], "chapters": len(payload["chapters"]), "output": str(output)}, indent=2))
    return 0 if payload["status"] == "LOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
