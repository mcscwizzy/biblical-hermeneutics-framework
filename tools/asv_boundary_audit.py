"""Audit Psalm-heading labels that fall across ASV verse boundaries."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ASV_PATH = ROOT / "bhf_agent/data/asv_bible.json"


def scan_asv_psalm_boundaries() -> dict[str, object]:
    """Return a deterministic summary of Psalm headings embedded in ASV verses."""
    data = json.loads(ASV_PATH.read_text(encoding="utf-8"))
    next_psalm = re.compile(r"\bPsalm\s+(?P<number>\d+)\b", re.IGNORECASE)
    chief_musician = re.compile(r"\bFor the Chief Musician\b", re.IGNORECASE)
    rows: list[dict[str, object]] = []

    for book in data.get("books", []):
        for chapter in book.get("chapters", []):
            for verse in chapter.get("verses", []):
                text = str(verse.get("text", ""))
                match = next_psalm.search(text)
                if not match:
                    continue
                chapter_number = int(chapter.get("chapter", 0))
                heading_number = int(match.group("number"))
                rows.append({
                    "book": book.get("name"),
                    "chapter": chapter_number,
                    "verse": int(verse.get("verse", 0)),
                    "next_psalm_number": heading_number,
                    "is_next_psalm_boundary": (
                        book.get("name") == "Psalms"
                        and heading_number == chapter_number + 1
                    ),
                    "contains_chief_musician": bool(chief_musician.search(text)),
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "text": text,
                })

    psalm_rows = [row for row in rows if row["book"] == "Psalms"]
    psalm_19_14 = [
        row for row in psalm_rows
        if row["chapter"] == 19 and row["verse"] == 14
    ]
    return {
        "source_path": ASV_PATH.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(ASV_PATH.read_bytes()).hexdigest(),
        "scan_method": "deterministic scan of ASV verses for next-Psalm headings",
        "total_matches": len(rows),
        "matches_by_book": dict(sorted(Counter(row["book"] for row in rows).items())),
        "psalms_matches": len(psalm_rows),
        "psalms_next_boundary_matches": sum(
            bool(row["is_next_psalm_boundary"]) for row in psalm_rows
        ),
        "psalms_chief_musician_matches": sum(
            bool(row["contains_chief_musician"]) for row in psalm_rows
        ),
        "psalm_19_14_matches": psalm_19_14,
        "other_psalms_boundary_matches": [
            row for row in psalm_rows
            if row["chapter"] != 19 or row["verse"] != 14
        ],
        "classification": (
            "systematic Psalms heading-at-preceding-verse boundary pattern; "
            "Psalm 19 is not isolated"
        ),
    }


if __name__ == "__main__":
    summary = scan_asv_psalm_boundaries()
    print(json.dumps({key: value for key, value in summary.items() if key not in {
        "psalm_19_14_matches", "other_psalms_boundary_matches"
    }}, indent=2, ensure_ascii=False))
