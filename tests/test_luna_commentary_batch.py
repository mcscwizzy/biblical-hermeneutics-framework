from __future__ import annotations

from tools.luna_commentary_batch import block


def test_data_gap_batch_fallback_is_transparent_and_not_first_last_verse_boilerplate() -> None:
    value = block("1 Samuel", 28, "")

    assert value["text"] == (
        "BHF does not currently have anchored contextual evidence for 1 Samuel 28."
    )
    assert "contains 25 verses" not in value["text"]
    assert "It opens with" not in value["text"]
    assert "It concludes with" not in value["text"]
    assert value["evidence_ids"] == []
