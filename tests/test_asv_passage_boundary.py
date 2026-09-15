import json
from pathlib import Path

from tools.commentary_v12_evidence_applicability_enforcement import asv_contamination_scan


ROOT = Path(__file__).resolve().parents[1]


def _psalm_19_14_text() -> str:
    data = json.loads((ROOT / "bhf_agent/data/asv_bible.json").read_text(encoding="utf-8"))
    for book in data["books"]:
        if book["name"] != "Psalms":
            continue
        for chapter in book["chapters"]:
            if int(chapter["chapter"]) != 19:
                continue
            for verse in chapter["verses"]:
                if int(verse["verse"]) == 14:
                    return verse["text"]
    raise AssertionError("Psalms 19:14 was not found")


def test_psalm_19_14_no_longer_contains_psalm_20_heading():
    text = _psalm_19_14_text()
    assert "Psalm 20 For the Chief Musician. A Psalm of David." not in text


def test_remaining_asv_heading_boundaries_are_systematic_and_psalm_19_is_clear():
    scan = asv_contamination_scan()
    assert scan["psalm_19_14_matches"] == []
    assert scan["total_matches"] == 115
    assert scan["psalms_matches"] == 115
    assert scan["psalms_next_boundary_matches"] == 115
    assert scan["classification"].startswith("systematic Psalms")
