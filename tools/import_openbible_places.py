#!/usr/bin/env python3
"""Build the compact BHF biblical places dataset from OpenBible JSONL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bhf_agent.references import BOOK_ALIASES


OSIS_BOOKS = {
    "Gen": "Genesis",
    "Exod": "Exodus",
    "Lev": "Leviticus",
    "Num": "Numbers",
    "Deut": "Deuteronomy",
    "Josh": "Joshua",
    "Judg": "Judges",
    "Ruth": "Ruth",
    "1Sam": "1 Samuel",
    "2Sam": "2 Samuel",
    "1Kgs": "1 Kings",
    "2Kgs": "2 Kings",
    "1Chr": "1 Chronicles",
    "2Chr": "2 Chronicles",
    "Ezra": "Ezra",
    "Neh": "Nehemiah",
    "Esth": "Esther",
    "Job": "Job",
    "Ps": "Psalms",
    "Prov": "Proverbs",
    "Eccl": "Ecclesiastes",
    "Song": "Song of Songs",
    "Isa": "Isaiah",
    "Jer": "Jeremiah",
    "Lam": "Lamentations",
    "Ezek": "Ezekiel",
    "Dan": "Daniel",
    "Hos": "Hosea",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obad": "Obadiah",
    "Jonah": "Jonah",
    "Mic": "Micah",
    "Nah": "Nahum",
    "Hab": "Habakkuk",
    "Zeph": "Zephaniah",
    "Hag": "Haggai",
    "Zech": "Zechariah",
    "Mal": "Malachi",
    "Matt": "Matthew",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Rom": "Romans",
    "1Cor": "1 Corinthians",
    "2Cor": "2 Corinthians",
    "Gal": "Galatians",
    "Eph": "Ephesians",
    "Phil": "Philippians",
    "Col": "Colossians",
    "1Thess": "1 Thessalonians",
    "2Thess": "2 Thessalonians",
    "1Tim": "1 Timothy",
    "2Tim": "2 Timothy",
    "Titus": "Titus",
    "Phlm": "Philemon",
    "Heb": "Hebrews",
    "Jas": "James",
    "1Pet": "1 Peter",
    "2Pet": "2 Peter",
    "1John": "1 John",
    "2John": "2 John",
    "3John": "3 John",
    "Jude": "Jude",
    "Rev": "Revelation",
}


def normalize_text(value: str) -> str:
    normalized = value.lower().replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def parse_lonlat(value: str | None) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        return None, None
    try:
        longitude = float(parts[0])
        latitude = float(parts[1])
    except ValueError:
        return None, None
    return latitude, longitude


def confidence_from_score(score: int) -> tuple[str, int]:
    if score >= 750:
        return "strong", 5
    if score >= 500:
        return "likely", 4
    if score >= 200:
        return "possible", 3
    if score > 0:
        return "uncertain", 2
    return "unknown", 1


def best_resolution(record: dict[str, Any]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for identification in record.get("identifications", []):
        for resolution in identification.get("resolutions", []):
            latitude, longitude = parse_lonlat(resolution.get("lonlat"))
            if latitude is None or longitude is None:
                continue
            candidates.append(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "score": int(resolution.get("best_time_score") or resolution.get("best_path_score") or 0),
                    "type": resolution.get("type") or "",
                    "lonlat_type": resolution.get("lonlat_type") or "",
                    "description": strip_tags(resolution.get("description") or ""),
                    "modern_basis_id": resolution.get("modern_basis_id") or "",
                }
            )
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item["score"], item["lonlat_type"] != "point"))[0]


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def parse_osis(value: str) -> dict[str, int | str] | None:
    parts = value.split(".")
    if len(parts) < 3:
        return None
    book = OSIS_BOOKS.get(parts[0]) or BOOK_ALIASES.get(parts[0].lower())
    if not book:
        return None
    try:
        chapter = int(parts[1])
        verse = int(parts[2].split("-")[0])
    except ValueError:
        return None
    return {"book": book, "chapter": chapter, "verse_start": verse, "verse_end": verse}


def aliases_for(record: dict[str, Any], name: str) -> list[str]:
    aliases = set()
    for candidate in record.get("translation_name_counts", {}):
        candidate_text = str(candidate).strip()
        if candidate_text and normalize_text(candidate_text) != normalize_text(name):
            aliases.add(candidate_text)
    for association in record.get("modern_associations", {}).values():
        candidate_text = str(association.get("name") or "").strip()
        if candidate_text and normalize_text(candidate_text) != normalize_text(name):
            aliases.add(candidate_text)
    return sorted(aliases, key=lambda item: (normalize_text(item), item))


def references_for(record: dict[str, Any]) -> list[dict[str, int | str]]:
    seen = set()
    references = []
    for verse in record.get("verses", []):
        parsed = parse_osis(str(verse.get("osis") or ""))
        if not parsed:
            continue
        key = (parsed["book"], parsed["chapter"], parsed["verse_start"], parsed["verse_end"])
        if key in seen:
            continue
        seen.add(key)
        references.append(parsed)
    return references


def build_places(ancient_path: Path) -> list[dict[str, Any]]:
    places = []
    for line in ancient_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        resolution = best_resolution(record)
        if not resolution:
            continue
        name = str(record.get("friendly_id") or "").strip()
        if not name:
            continue
        confidence, confidence_rank = confidence_from_score(int(resolution["score"]))
        description = f"{name} ({', '.join(record.get('types', []) or ['biblical place'])})."
        if resolution["description"]:
            description = f"{description} Best OpenBible location: {resolution['description']}."
        places.append(
            {
                "id": f"openbible-{record['id']}",
                "openbible_id": record["id"],
                "name": name,
                "aliases": aliases_for(record, name),
                "latitude": resolution["latitude"],
                "longitude": resolution["longitude"],
                "modern_location": resolution["description"] or name,
                "ancient_region": ", ".join(record.get("types", []) or []),
                "description": description,
                "confidence": confidence,
                "confidence_rank": confidence_rank,
                "source_name": "OpenBible.info Bible Geocoding Data",
                "source_url": f"https://www.openbible.info/geo/atlas/{record.get('url_slug') or record['id']}",
                "license": "CC-BY-4.0",
                "notes": (
                    "Imported from OpenBible.info Bible-Geocoding-Data. "
                    f"Location type: {resolution['type'] or 'unknown'}; coordinate type: {resolution['lonlat_type'] or 'unknown'}; "
                    f"OpenBible confidence score: {resolution['score']}."
                ),
                "references": references_for(record),
            }
        )
    return sorted(places, key=lambda item: (normalize_text(item["name"]), item["id"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ancient", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    places = build_places(args.ancient)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(places, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(places)} places to {args.output}")


if __name__ == "__main__":
    main()
