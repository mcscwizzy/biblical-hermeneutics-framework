from __future__ import annotations

import json
from pathlib import Path

import pytest

from bhf_agent.presentation import (
    evaluate_presentation_case,
    evaluate_presentation_fixtures,
    format_presentation_eval,
    load_presentation_fixtures,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "presentation_passages.json"


def test_presentation_fixture_suite_passes_without_a_provider():
    result = evaluate_presentation_fixtures(FIXTURE_PATH)

    assert result.passed
    assert result.passed_count == 3
    assert result.failed_count == 0
    assert {case.passage_ref for case in result.cases} == {
        "1 Samuel 25",
        "Mark 5:1-20",
        "1 Corinthians 8",
    }
    assert all(case.presentation_mode == "deterministic_fallback" for case in result.cases)
    assert all(case.evidence_hash for case in result.cases)
    assert all(case.ranked_evidence for case in result.cases)
    assert all(case.cards for case in result.cases)


def test_presentation_eval_reports_grounded_card_and_map_expectations():
    result = evaluate_presentation_fixtures(FIXTURE_PATH, references=["  MARK   5:1-20 "])
    case = result.cases[0]

    assert result.passed
    assert case.passage_ref == "Mark 5:1-20"
    assert {card["type"] for card in case.cards} == {"walk_the_land", "did_you_know"}
    assert any("open_map" in card["action_types"] for card in case.cards)
    assert all(check.passed for check in case.checks)
    assert "Ranked: gerasene-eastern-shore" in format_presentation_eval(result)


def test_presentation_eval_fails_an_unmet_fixture_expectation():
    result = evaluate_presentation_case(
        {
            "reference": "Genesis 1",
            "objects": [],
            "presentation_expectations": {"minimum_cards": 1},
        }
    )

    assert not result.passed
    checks = {check.id: check for check in result.checks}
    assert checks["source_provenance_complete"].passed
    assert checks["packet_validation"].passed
    assert not checks["minimum_cards"].passed
    assert result.cards == []


def test_presentation_eval_json_is_content_inspectable_and_serializable():
    result = evaluate_presentation_fixtures(FIXTURE_PATH, references=["1 Samuel 25"])
    payload = json.loads(json.dumps(result.to_dict()))

    assert payload["passed"] is True
    assert payload["cases"][0]["ranked_evidence"][0]["id"] == "abigail-gift-economics"
    assert payload["cases"][0]["cards"][0]["evidence_ids"] == [
        "abigail-gift-economics"
    ]


def test_presentation_fixture_loader_rejects_unknown_reference(tmp_path):
    assert len(load_presentation_fixtures(FIXTURE_PATH)) == 3

    with pytest.raises(ValueError, match="reference not found"):
        evaluate_presentation_fixtures(FIXTURE_PATH, references=["Ruth 1"])

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"cases": "not-a-list"}', encoding="utf-8")
    with pytest.raises(ValueError, match="must be a list"):
        load_presentation_fixtures(invalid)


def test_presentation_fixture_loader_rejects_unknown_expectation(tmp_path):
    invalid = tmp_path / "invalid-expectation.json"
    invalid.write_text(
        json.dumps(
            [
                {
                    "reference": "Ruth 1",
                    "objects": [],
                    "presentation_expectations": {"requred_card_types": []},
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown expectation"):
        load_presentation_fixtures(invalid)
