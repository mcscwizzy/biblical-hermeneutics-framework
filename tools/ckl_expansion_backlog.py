#!/usr/bin/env python3
"""Report a prioritized CKL expansion backlog for people, places, and things."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.canonical_library.authoring import DEFAULT_AUTHORING_ROOT, scan_library
from framework.canonical_library.schema import CATEGORY_FOLDERS, CanonicalObject


THING_TYPES: tuple[str, ...] = (
    "archaeology",
    "biblical_theology",
    "covenant",
    "cultural_background",
    "doctrine",
    "event",
    "institution",
    "literary_device",
    "prophecy",
    "symbol",
    "theme",
    "theology",
    "timeline",
    "word_study",
)

MATURE_REVIEW_STATUSES: frozenset[str] = frozenset({"reviewed", "approved"})

SUBSTANTIVE_TEXT_FIELDS: tuple[str, ...] = (
    "summary",
    "canonical_role",
    "historical_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "canonical_context",
    "literary_context",
    "covenantal_significance",
)

SUBSTANTIVE_COLLECTION_FIELDS: tuple[str, ...] = (
    "aliases",
    "scripture_references",
    "related_objects",
    "related_people",
    "related_places",
    "related_events",
    "interpretive_notes",
    "common_questions",
    "sources",
)


@dataclass(frozen=True)
class ExpansionCandidate:
    lane: str
    object_id: str
    object_type: str
    title: str
    importance: int
    score: int
    content_status: str
    review_status: str
    missing_text_fields: list[str]
    missing_collection_fields: list[str]
    source_count: int
    scripture_reference_count: int
    related_object_count: int
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def lane_for(obj: CanonicalObject) -> str | None:
    if obj.type == "person":
        return "people"
    if obj.type == "place":
        return "places"
    if obj.type in THING_TYPES:
        return "things"
    return None


def _missing_text_fields(obj: CanonicalObject) -> list[str]:
    missing: list[str] = []
    for field_name in SUBSTANTIVE_TEXT_FIELDS:
        value = getattr(obj, field_name, "")
        if not isinstance(value, str) or not value.strip():
            missing.append(field_name)
    return missing


def _missing_collection_fields(obj: CanonicalObject) -> list[str]:
    missing: list[str] = []
    for field_name in SUBSTANTIVE_COLLECTION_FIELDS:
        value = getattr(obj, field_name, [])
        if not value:
            missing.append(field_name)
    return missing


def _score_candidate(
    obj: CanonicalObject,
    *,
    missing_text_fields: list[str],
    missing_collection_fields: list[str],
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = int(obj.importance or 0)

    content_status = obj.content_status.strip().lower()
    review_status = obj.review_status.strip().lower()

    if content_status == "placeholder":
        score += 120
        reasons.append("placeholder")
    elif content_status == "draft":
        score += 80
        reasons.append("draft")
    elif content_status != "complete":
        score += 40
        reasons.append(f"content_status={content_status}")

    if review_status == "unreviewed":
        score += 90
        reasons.append("unreviewed")
    elif review_status not in MATURE_REVIEW_STATUSES:
        score += 45
        reasons.append(f"review_status={review_status}")

    if obj.human_review_required:
        score += 20
        reasons.append("human_review_required")

    source_count = len(obj.sources or [])
    if source_count == 0:
        score += 35
        reasons.append("no_sources")
    elif source_count < 3:
        score += 15
        reasons.append("few_sources")

    scripture_count = len(obj.scripture_references or [])
    if scripture_count == 0:
        score += 30
        reasons.append("no_scripture_references")

    related_count = len(obj.related_objects or [])
    if related_count == 0:
        score += 30
        reasons.append("no_related_objects")
    elif related_count < 3:
        score += 12
        reasons.append("thin_related_objects")

    if missing_text_fields:
        score += min(60, len(missing_text_fields) * 8)
        reasons.append(f"missing_text={len(missing_text_fields)}")

    if missing_collection_fields:
        score += min(40, len(missing_collection_fields) * 5)
        reasons.append(f"missing_collections={len(missing_collection_fields)}")

    return score, reasons


def build_candidates(objects: list[CanonicalObject]) -> list[ExpansionCandidate]:
    candidates: list[ExpansionCandidate] = []
    for obj in objects:
        lane = lane_for(obj)
        if lane is None:
            continue

        missing_text = _missing_text_fields(obj)
        missing_collections = _missing_collection_fields(obj)
        score, reasons = _score_candidate(
            obj,
            missing_text_fields=missing_text,
            missing_collection_fields=missing_collections,
        )
        candidates.append(
            ExpansionCandidate(
                lane=lane,
                object_id=obj.id,
                object_type=obj.type,
                title=obj.title,
                importance=int(obj.importance or 0),
                score=score,
                content_status=obj.content_status,
                review_status=obj.review_status,
                missing_text_fields=missing_text,
                missing_collection_fields=missing_collections,
                source_count=len(obj.sources or []),
                scripture_reference_count=len(obj.scripture_references or []),
                related_object_count=len(obj.related_objects or []),
                reasons=reasons,
            )
        )
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score,
            -candidate.importance,
            candidate.lane,
            candidate.object_id,
        ),
    )


def summarize(
    candidates: list[ExpansionCandidate],
    *,
    all_objects: list[CanonicalObject],
) -> dict[str, Any]:
    lane_counts = Counter(candidate.lane for candidate in candidates)
    lane_status_counts: dict[str, dict[str, int]] = {}
    lane_review_counts: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        lane_status_counts.setdefault(candidate.lane, {})
        lane_review_counts.setdefault(candidate.lane, {})
        lane_status_counts[candidate.lane][candidate.content_status] = (
            lane_status_counts[candidate.lane].get(candidate.content_status, 0) + 1
        )
        lane_review_counts[candidate.lane][candidate.review_status] = (
            lane_review_counts[candidate.lane].get(candidate.review_status, 0) + 1
        )

    existing_type_counts = Counter(obj.type for obj in all_objects)
    empty_thing_categories = [
        CATEGORY_FOLDERS[object_type]
        for object_type in THING_TYPES
        if existing_type_counts.get(object_type, 0) == 0
    ]

    return {
        "total_candidates": len(candidates),
        "lane_counts": dict(sorted(lane_counts.items())),
        "lane_content_status_counts": {
            lane: dict(sorted(counts.items()))
            for lane, counts in sorted(lane_status_counts.items())
        },
        "lane_review_status_counts": {
            lane: dict(sorted(counts.items()))
            for lane, counts in sorted(lane_review_counts.items())
        },
        "empty_thing_categories": sorted(empty_thing_categories),
    }


def format_text_report(
    summary: dict[str, Any],
    candidates: list[ExpansionCandidate],
    *,
    limit: int,
) -> str:
    lines = [
        "CKL People, Places, and Things Expansion Backlog",
        f"- Candidates: {summary['total_candidates']}",
        "- Lanes: "
        + ", ".join(f"{lane}={count}" for lane, count in summary["lane_counts"].items()),
    ]

    empty_thing_categories = summary["empty_thing_categories"]
    if empty_thing_categories:
        lane_counts = summary["lane_counts"]
        if "things" in lane_counts or len(lane_counts) != 1:
            lines.append("- Empty thing categories: " + ", ".join(empty_thing_categories))

    lines.append("")
    lines.append("Status by lane:")
    for lane, counts in summary["lane_content_status_counts"].items():
        lines.append(f"- {lane}: " + ", ".join(f"{key}={value}" for key, value in counts.items()))

    lines.append("")
    lines.append(f"Top {limit} expansion candidates:")
    for index, candidate in enumerate(candidates[:limit], start=1):
        reasons = ", ".join(candidate.reasons[:5])
        if len(candidate.reasons) > 5:
            reasons += ", ..."
        lines.append(
            f"{index}. [{candidate.lane}] {candidate.title} "
            f"({candidate.object_type}/{candidate.object_id}) "
            f"score={candidate.score} importance={candidate.importance}; {reasons}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report a prioritized CKL expansion backlog for people, places, and things."
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_AUTHORING_ROOT),
        help="CKL root directory",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of top candidates to print in text mode",
    )
    parser.add_argument(
        "--lane",
        choices=("people", "places", "things"),
        help="Limit the backlog to one expansion lane",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the expansion backlog as JSON instead of text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    audit = scan_library(args.root)
    objects = list(audit.valid_objects.values())
    candidates = build_candidates(objects)
    if args.lane:
        candidates = [candidate for candidate in candidates if candidate.lane == args.lane]
    summary = summarize(candidates, all_objects=objects)

    if args.json:
        payload = {
            "summary": summary,
            "candidates": [candidate.to_dict() for candidate in candidates],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(format_text_report(summary, candidates, limit=max(0, args.limit)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
