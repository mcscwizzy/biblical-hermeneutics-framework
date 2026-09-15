"""Regression tests for Commentary 1.5 scale-pilot report wording."""

from tools.commentary_v15_scale_evaluate import _markdown, _report_state


def _report(*, repeated: bool, complete: bool) -> dict:
    return {
        "status": "IN_PROGRESS" if not complete else "COMPLETE",
        "classification": "INCOMPLETE_SCALE_PILOT",
        "renderer_identity": {
            "renderer_label": "GPT-5 Codex",
            "reasoning_effort": "NOT_EXPOSED",
        },
        "wave_results": {},
        "structural_reference_variance": {
            "repeated": repeated,
            "codes": {},
        },
        "scale_pilot_complete": complete,
    }


def test_incomplete_report_does_not_claim_repeated_structural_variance():
    markdown = _markdown(_report(repeated=False, complete=False))

    assert "no repeated structural-reference variance was observed" in markdown
    assert "unrelated repeated malformed verse/section references" not in markdown


def test_report_explains_structural_stop_only_when_variance_repeats():
    markdown = _markdown(_report(repeated=True, complete=False))

    assert "repeated structural-reference variance indicates contract variance" in markdown


def test_completed_report_describes_completion():
    markdown = _markdown(_report(repeated=False, complete=True))

    assert "All planned waves completed without repeated structural-reference variance" in markdown


def test_completed_pilot_report_state_is_complete():
    assert _report_state(
        completed_wave_count=3,
        expected_wave_count=3,
        repeated_contract_variance=False,
    ) == ("COMPLETE", "COMMENTARY_1_5_SCALE_PILOT_COMPLETE", True)


def test_incomplete_pilot_report_state_remains_in_progress():
    assert _report_state(
        completed_wave_count=2,
        expected_wave_count=3,
        repeated_contract_variance=False,
    ) == ("IN_PROGRESS", "INCOMPLETE_SCALE_PILOT", False)


def test_repeated_variance_stops_report_even_if_all_waves_exist():
    assert _report_state(
        completed_wave_count=3,
        expected_wave_count=3,
        repeated_contract_variance=True,
    ) == ("STOPPED_AFTER_WAVE_A", "COMMENTARY_1_5_SCALE_NEEDS_CONTRACT_HARDENING", False)
