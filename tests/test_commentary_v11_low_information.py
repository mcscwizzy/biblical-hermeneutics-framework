from __future__ import annotations

from types import SimpleNamespace

from tools.commentary_v11_low_information import detect_low_information


def _commentary(text: str, *section_kinds: str):
    kinds = section_kinds or ("chapter_overview",)
    return SimpleNamespace(
        sections=[
            SimpleNamespace(
                kind=kind,
                blocks=[SimpleNamespace(text=text, evidence_ids=["evidence-1"])],
            )
            for kind in kinds
        ]
    )


def test_explicit_verse_count_opening_and_closing_boilerplate_is_classified():
    result = detect_low_information(
        _commentary(
            "Zephaniah 1 contains 18 verses. It opens with: ... "
            "It concludes with: ..."
        )
    )

    assert result["is_low_information"] is True
    assert result["classification"] == "LOW_INFORMATION_COMMENTARY"
    assert result["canonical_summary_only"] is True


def test_contextual_section_is_recorded_without_changing_classification_rule():
    result = detect_low_information(
        _commentary(
            "This chapter contains 18 verses. It opens with: ... "
            "It concludes with: ...",
            "chapter_overview",
            "historical_context",
        )
    )

    assert result["is_low_information"] is True
    assert result["contextual_section_kinds"] == ["historical_context"]
    assert result["canonical_summary_only"] is False


def test_single_opening_reference_is_not_enough_for_internal_classification():
    result = detect_low_information(
        _commentary("The chapter opens with a historical setting that frames the oracle.")
    )

    assert result["is_low_information"] is False
