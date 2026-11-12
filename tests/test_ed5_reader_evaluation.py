from __future__ import annotations

from scripts.ed5_reader_evaluation import JOURNEYS, build_service, evaluate_journeys


def test_ed5_journey_evaluation_covers_representative_discovery_and_negative_cases():
    service, library = build_service()
    report = evaluate_journeys(service, library)

    assert len(JOURNEYS) == 12
    assert report["summary"]["passed"] == 12
    assert report["summary"]["failed"] == 0
    assert report["interpretation"] == (
        "Scripted projection and retrieval checks; no human comprehension or satisfaction measure."
    )
    projected_cases = [case for case in report["cases"] if case.get("expected_item_id")]
    assert len(projected_cases) == 10
    assert all(case["expected_item_matches"] == 1 for case in projected_cases)
    obadiah = next(case for case in projected_cases if case["case_id"] == "obadiah-1-7-exact-scope")
    assert obadiah["expected_item_id"] == (
        "ckl:obadiah#interpretive-note:sha256-b9c2e9d3224b9cec78d0ed51b5167898f7cda70e186801cd2c5f7a1df2708812"
    )
    empty = next(case for case in report["cases"] if case["case_id"] == "empty-1-kings-2")
    assert empty["ckl_coverage_state"] == "not_represented"
    assert empty["ckl_projected_items"] == 0
    jonah = next(case for case in report["cases"] if case["case_id"] == "jonah-matthew-bridge")
    assert jonah["relationship_direction"] == "Jonah 1:17 → Matthew 12:40"
    assert jonah["endpoints_checked"] == ["Jonah 1:17", "Matthew 12:40"]
    ordinary_question = next(case for case in report["cases"] if case["case_id"] == "1-john-ordinary-question")
    assert ordinary_question["retrieval_first_result"] == "1-john"
