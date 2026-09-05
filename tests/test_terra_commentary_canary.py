from __future__ import annotations

import json

from tools.terra_commentary_canary import PROSE, run


def test_terra_canary_uses_only_locked_chapters_and_validates(tmp_path):
    result = run(tmp_path, report_destination=tmp_path / "terra-canary-report.md")

    validation = result["validation"]
    review = result["review"]
    assert validation["chapters"] == 25
    assert validation["valid"] == 25
    assert validation["invalid"] == 0
    assert "1 Samuel 28" not in PROSE
    assert review["special_review"]["1 Samuel 28"]["status"] == "POSSIBLE_EVIDENCE_REVIEW"
    assert review["quality_flags"]["LOW_INFORMATION"] == 0

    saved = list((tmp_path / "chapters").glob("*.json"))
    assert len(saved) == 25
    numbers_three = json.loads((tmp_path / "chapters" / "numbers_003.json").read_text())
    assert numbers_three["evidence_availability"] == "DATA_GAP"
    assert numbers_three["sections"][0]["blocks"][0]["evidence_ids"] == []
