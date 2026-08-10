#!/usr/bin/env python3
"""Report deterministic archaeology-corpus coverage from a BHF study database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

# Support direct ``python3 tools/report_archaeology_coverage.py`` execution.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent.study_db import initialize_database


OT_BOOKS = {
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
    "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
    "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
}


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower() or "(missing)"


def build_report(database: str | Path) -> dict[str, object]:
    """Return corpus metrics suitable for terminal display or JSON automation."""

    initialize_database(database)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        items = connection.execute(
            "SELECT id, item_type, period, periods, source_url, evidence_details FROM archaeology_items"
        ).fetchall()
        sites = connection.execute("SELECT id FROM archaeology_sites").fetchall()
        media = connection.execute("SELECT archaeology_item_id FROM archaeology_media").fetchall()
        scripture = connection.execute("SELECT item_id, book FROM archaeology_scripture_links").fetchall()
        ckl = connection.execute("SELECT DISTINCT archaeology_item_id FROM archaeology_ckl_links").fetchall()

    item_ids = {row["id"] for row in items}
    media_ids = {row["archaeology_item_id"] for row in media if row["archaeology_item_id"]}
    scripture_ids = {row["item_id"] for row in scripture}
    ckl_ids = {row["archaeology_item_id"] for row in ckl}
    books = Counter(row["book"] for row in scripture)
    periods: Counter[str] = Counter()
    for row in items:
        values = json.loads(row["periods"] or "[]")
        for value in values or [row["period"]]:
            periods[str(value)] += 1

    linked_ot = {row["item_id"] for row in scripture if row["book"] in OT_BOOKS}
    linked_nt = scripture_ids - linked_ot
    return {
        "total_archaeology_records": len(items),
        "total_sites": len(sites),
        "media_records": len(media),
        "records_with_media": len(media_ids),
        "media_coverage_percent": round(100 * len(media_ids) / len(items), 1) if items else 0,
        "records_without_images": sorted(item_ids - media_ids),
        "records_without_scripture_links": sorted(item_ids - scripture_ids),
        "records_without_ckl_links": sorted(item_ids - ckl_ids),
        "ot_linked_records": len(linked_ot),
        "nt_linked_records": len(linked_nt),
        "records_by_period": dict(sorted(periods.items())),
        "records_by_item_type": dict(sorted(Counter(row["item_type"] for row in items).items())),
        "books_with_archaeology_coverage": dict(sorted(books.items())),
        "books_without_archaeology_coverage": sorted(OT_BOOKS.union({
            "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
            "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
            "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
            "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
            "3 John", "Jude", "Revelation",
        }) - set(books)),
        "disputed_records": sorted(
            row["id"] for row in items
            if json.loads(row["evidence_details"] or "{}").get("dispute_status", "not_disputed")
            != "not_disputed"
        ),
        "source_domain_counts": dict(sorted(Counter(_domain(row["source_url"]) for row in items).items())),
    }
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=".bhf/study.sqlite", help="SQLite study database path")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a compact report")
    args = parser.parse_args()
    report = build_report(args.database)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    for key in (
        "total_archaeology_records", "total_sites", "media_records", "records_with_media",
        "media_coverage_percent", "ot_linked_records", "nt_linked_records",
    ):
        print(f"{key.replace('_', ' ')}: {report[key]}")
    print(f"records by period: {report['records_by_period']}")
    print(f"records by item type: {report['records_by_item_type']}")
    print(f"books with archaeology coverage: {report['books_with_archaeology_coverage']}")
    print(f"disputed records: {len(report['disputed_records'])}")
    print(f"source-domain counts: {report['source_domain_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
