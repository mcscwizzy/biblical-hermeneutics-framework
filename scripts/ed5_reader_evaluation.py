#!/usr/bin/env python3
"""Reproducible, scripted ED-5 passage-projection and retrieval evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from bhf_agent.presentation.narrative_explorer import DomainLookup
from bhf_web.services.narrative_explorer import NarrativeExplorerService
from framework.canonical_library.loader import CanonicalLibrary
from framework.canonical_library.retrieval import CKLRetrievalService


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = REPOSITORY_ROOT / "framework/canonical_library"
STUDY_DB = REPOSITORY_ROOT / ".bhf-data/study.sqlite"

JOURNEYS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "genesis-6-sons-of-god",
        "book": "Genesis", "chapter": 6,
        "expected_item_id": "ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions",
        "expected_anchor": "Genesis 6:1-4",
        "expected_sources": ["g2r2-local-sarna-genesis", "g2-doedens-sons-god"],
        "expected_certainty": "disputed",
        "expected_dispute_status": "major_scholarly_disagreement",
    },
    {
        "case_id": "genesis-12-abraham-context",
        "book": "Genesis", "chapter": 12,
        "expected_item_id": "ckl:genesis#claim:genesis-blessing-for-families",
        "expected_anchor": "Genesis 12:1-3",
        "expected_sources": ["genesis-1-50", "hamilton-genesis-1-17"],
    },
    {
        "case_id": "psalm-145-13-witness-variant",
        "book": "Psalm", "chapter": 145, "verse_start": 13, "verse_end": 13,
        "expected_item_id": "ckl:psalms#evidence:psalm-145-nun-verse-witness",
        "expected_anchor": "Psalm 145:13",
        "expected_sources": ["sanders-11qpsa-1965", "rahlfs-hanhart-septuaginta-2006"],
        "expected_dispute_status": "textual_variant",
    },
    {
        "case_id": "psalm-82-divine-assembly",
        "book": "Psalm", "chapter": 82,
        "expected_item_id": "ckl:ancient-divine-assembly-imagery#claim:psalm-82-assembly-text",
        "expected_anchor": "Psalm 82:1-8",
        "expected_sources": ["psalm-82-hebrew-text", "lewis-origin-character-god-2020"],
    },
    {
        "case_id": "deuteronomy-32-8-9-textual-witnesses",
        "book": "Deuteronomy", "chapter": 32, "verse_start": 8, "verse_end": 9,
        "expected_item_id": "ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant",
        "expected_anchor": "Deuteronomy 32:8-9",
        "expected_sources": ["deuteronomy-32-text", "ulrich-biblical-qumran-scrolls-2010"],
        "expected_dispute_status": "textual_variant",
    },
    {
        "case_id": "jonah-matthew-bridge",
        "kind": "bridge",
        "endpoints": [
            {"book": "Jonah", "chapter": 1, "verse_start": 17, "verse_end": 17, "reference": "Jonah 1:17"},
            {"book": "Matthew", "chapter": 12, "verse_start": 40, "verse_end": 40, "reference": "Matthew 12:40"},
        ],
        "expected_route_id": "jonah-1-17-matthew-12-40-sign-of-jonah",
        "expected_source_passage": "Jonah 1:17",
        "expected_receiving_passage": "Matthew 12:40",
        "expected_direction": "source_to_receiving_text",
        "expected_support_id": "ckl:jonah#claim:jonah-three-days",
    },
    {
        "case_id": "1-corinthians-11-3-kephale",
        "book": "1 Corinthians", "chapter": 11, "verse_start": 3, "verse_end": 3,
        "expected_item_id": "ckl:1-corinthians#claim:1cor-kephale",
        "expected_anchor": "1 Corinthians 11:3",
        "expected_sources": ["bdag", "thiselton-1cor"],
        "expected_certainty": "disputed",
        "expected_dispute_status": "lexical_uncertainty",
    },
    {
        "case_id": "1-john-ordinary-question",
        "book": "1 John", "chapter": 3, "verse_start": 19, "verse_end": 24,
        "expected_item_id": "ckl:1-john#claim:1jn-heart",
        "expected_anchor": "1 John 3:19-24",
        "expected_sources": ["1jn-greek", "brown", "smalley"],
        "retrieval_question": "What if our heart condemns us?",
        "retrieval_expected_first_result": "1-john",
    },
    {
        "case_id": "john-10-22-festival-context",
        "book": "John", "chapter": 10, "verse_start": 22, "verse_end": 22,
        "expected_item_id": "ckl:john#evidence:john-10-22-dedication-term-and-winter",
        "expected_anchor": "John 10:22",
        "expected_sources": ["john-greek", "foerster-john10-enkainia-2016"],
        "expected_dispute_status": "interpretive_uncertainty",
    },
    {
        "case_id": "obadiah-1-7-exact-scope",
        "book": "Obadiah", "chapter": 1, "verse_start": 7, "verse_end": 7,
        "expected_item_id": "ckl:obadiah#interpretive-note:sha256-b9c2e9d3224b9cec78d0ed51b5167898f7cda70e186801cd2c5f7a1df2708812",
        "expected_anchor": "Obadiah 1:7",
        "expected_sources": ["obadiah-masoretic", "nogalski-obadiah"],
    },
    {
        "case_id": "2-kings-18-13-sennacherib-prism",
        "book": "2 Kings", "chapter": 18, "verse_start": 13, "verse_end": 13,
        "expected_item_id": "ckl:sennacherib-prism#claim:prism-judah-campaign",
        "expected_anchor": "2 Kings 18:13-37",
        "expected_sources": ["taylor-prism"],
    },
    {
        "case_id": "empty-1-kings-2",
        "book": "1 Kings", "chapter": 2,
        "expected_empty": True,
    },
)


def _empty_lookup(domain: str):
    def lookup(**_request: Any) -> DomainLookup:
        return DomainLookup(domain=domain, records=(), query_status="complete")

    return lookup


def build_service() -> tuple[NarrativeExplorerService, CanonicalLibrary]:
    """Build an in-process service using checked-in CKL and completed empty domain lookups."""

    library = CanonicalLibrary(root=CKL_ROOT).load()
    service = NarrativeExplorerService(
        study_db_path=STUDY_DB,
        canonical_library_provider=lambda: library,
        maps_lookup_provider=_empty_lookup("maps"),
        archaeology_lookup_provider=_empty_lookup("archaeology"),
    )
    return service, library


def _passage_payload(service: NarrativeExplorerService, passage: Mapping[str, Any]) -> dict[str, Any]:
    return service.build(
        str(passage["book"]),
        int(passage["chapter"]),
        verse_start=int(passage["verse_start"]) if passage.get("verse_start") is not None else None,
        verse_end=int(passage["verse_end"]) if passage.get("verse_end") is not None else None,
    )


def _evaluate_item_case(
    service: NarrativeExplorerService,
    retrieval: CKLRetrievalService,
    case: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _passage_payload(service, case)
    ckl_items = [item for item in payload.get("items", []) if item.get("domain") == "ckl"]
    ckl_coverage = next(
        (entry for entry in payload.get("coverage", []) if entry.get("source_domain") == "canonical_knowledge_library"),
        {},
    )
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "passage": payload.get("passage", {}).get("reference"),
        "expected_item_id": case.get("expected_item_id"),
        "ckl_coverage_state": ckl_coverage.get("state"),
        "ckl_query_status": ckl_coverage.get("query_status"),
        "ckl_projected_items": len(ckl_items),
        "source_ids": [],
        "applicable_anchors": [],
        "failures": [],
    }
    if case.get("expected_empty"):
        if ckl_items:
            result["failures"].append("expected no passage-eligible CKL items")
        if ckl_coverage.get("state") != "not_represented" or ckl_coverage.get("query_status") != "complete":
            result["failures"].append("empty state is not a completed no-eligible-records result")
    else:
        matches = [candidate for candidate in ckl_items if candidate.get("id") == case["expected_item_id"]]
        result["expected_item_matches"] = len(matches)
        if len(matches) != 1:
            result["failures"].append(
                f"expected exactly one projected record with the stable ID; found {len(matches)}"
            )
        item = matches[0] if matches else None
        if item is None:
            result["failures"].append("exact expected CKL record was not projected")
        else:
            result["source_ids"] = item.get("source_ids", [])
            result["applicable_anchors"] = [
                anchor.get("reference") for anchor in item.get("applicable_passage_anchors", [])
            ]
            for field in ("certainty", "dispute_status"):
                expected = case.get(f"expected_{field}")
                if expected and item.get(field) != expected:
                    result["failures"].append(f"{field} changed: expected {expected}, got {item.get(field)}")
    expected_anchor = case.get("expected_anchor")
    if expected_anchor and expected_anchor not in result["applicable_anchors"]:
        result["failures"].append(f"expected exact anchor missing: {expected_anchor}")
    missing_sources = sorted(set(case.get("expected_sources", [])) - set(result["source_ids"]))
    if missing_sources:
        result["failures"].append(f"expected source IDs missing: {', '.join(missing_sources)}")
    if case.get("retrieval_question"):
        response = retrieval.search(case["retrieval_question"], limit=5)
        first_result = response.results[0].id if response.results else None
        result["retrieval_question"] = case["retrieval_question"]
        result["retrieval_first_result"] = first_result
        if first_result != case["retrieval_expected_first_result"]:
            result["failures"].append(
                f"ordinary-language retrieval ranked {first_result!r}; expected {case['retrieval_expected_first_result']!r}"
            )
    return result


def _evaluate_bridge_case(service: NarrativeExplorerService, case: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "endpoints_checked": [],
        "relationship_direction": f"{case['expected_source_passage']} → {case['expected_receiving_passage']}",
        "failures": [],
    }
    for endpoint in case["endpoints"]:
        payload = _passage_payload(service, endpoint)
        reference = payload.get("passage", {}).get("reference")
        result["endpoints_checked"].append(reference)
        routes = payload.get("related_passages", {}).get("evidence_backed_bridges", [])
        matches = [route for route in routes if route.get("id") == case["expected_route_id"]]
        if len(matches) != 1:
            result["failures"].append(f"{reference}: expected one exact verified bridge route")
            continue
        route = matches[0]
        for field, expected in (
            ("source_text_passage", case["expected_source_passage"]),
            ("receiving_text_passage", case["expected_receiving_passage"]),
            ("direction", case["expected_direction"]),
        ):
            if route.get(field) != expected:
                result["failures"].append(f"{reference}: {field} was {route.get(field)!r}, expected {expected!r}")
        support_ids = [record.get("id") for record in route.get("supporting_records", [])]
        if case["expected_support_id"] not in support_ids:
            result["failures"].append(f"{reference}: exact supporting CKL record was not disclosed")
        if not route.get("explanation") or not route.get("uncertainty"):
            result["failures"].append(f"{reference}: route explanation or uncertainty is missing")
    if result["endpoints_checked"] != [endpoint["reference"] for endpoint in case["endpoints"]]:
        result["failures"].append("one or more canonical endpoints did not resolve as requested")
    return result


def evaluate_journeys(
    service: NarrativeExplorerService,
    library: CanonicalLibrary | None = None,
    cases: Sequence[Mapping[str, Any]] = JOURNEYS,
) -> dict[str, Any]:
    retrieval = CKLRetrievalService(library=library) if library is not None else None
    if retrieval is None:
        provider = service.canonical_library_provider
        library_value = provider() if callable(provider) else None
        if library_value is None:
            raise RuntimeError("the reader evaluation requires a canonical library")
        retrieval = CKLRetrievalService(library=library_value)
    results = [
        _evaluate_bridge_case(service, case)
        if case.get("kind") == "bridge"
        else _evaluate_item_case(service, retrieval, case)
        for case in cases
    ]
    failed = sum(bool(case["failures"]) for case in results)
    return {
        "suite": "ED-5 scripted reader journey projection evaluation",
        "case_count": len(results),
        "summary": {"passed": len(results) - failed, "failed": failed},
        "interpretation": "Scripted projection and retrieval checks; no human comprehension or satisfaction measure.",
        "cases": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write JSON report to this path instead of stdout")
    args = parser.parse_args(argv)
    service, library = build_service()
    report = evaluate_journeys(service, library)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Wrote {report['case_count']} journey results to {args.output}")
    else:
        print(serialized, end="")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
