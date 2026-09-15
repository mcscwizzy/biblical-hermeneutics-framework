"""Apply the isolated, deterministic Psalm 19:14 ASV boundary repair."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASV_PATH = ROOT / "bhf_agent/data/asv_bible.json"
CONTAMINATED_SUFFIX = " Psalm 20 For the Chief Musician. A Psalm of David."


def _psalm_19_14(data: dict) -> dict:
    for book in data.get("books", []):
        if book.get("name") != "Psalms":
            continue
        for chapter in book.get("chapters", []):
            if int(chapter.get("chapter", 0)) != 19:
                continue
            for verse in chapter.get("verses", []):
                if int(verse.get("verse", 0)) == 14:
                    return verse
    raise RuntimeError("Psalms 19:14 was not found")


def repair(path: Path = ASV_PATH) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    verse = _psalm_19_14(data)
    text = str(verse.get("text", ""))
    if text.count(CONTAMINATED_SUFFIX) != 1:
        raise RuntimeError(
            "Psalm 19:14 did not contain exactly one expected Psalm 20 boundary suffix"
        )
    verse["text"] = text.removesuffix(CONTAMINATED_SUFFIX)
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    repair()
