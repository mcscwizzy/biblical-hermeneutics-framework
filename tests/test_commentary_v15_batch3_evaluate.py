"""Regression tests for deterministic Commentary 1.5 report metrics."""

from types import SimpleNamespace

from tools.commentary_v15_batch3_evaluate import _metric_row


def _row(packet, unit_count):
    synthesis = SimpleNamespace(synthesis_units=[object() for _ in range(unit_count)])
    return _metric_row(
        "Test 1",
        packet,
        synthesis,
        None,
        source="test",
        gate=None,
    )


def test_density_is_derived_from_locked_synthesis_across_packet_schema_drift():
    historical = _row(
        {
            "evidence_availability": "AVAILABLE",
            "literary_category": "Historical narrative",
            "synthesis_density_bucket": "1-5",
        },
        6,
    )
    newer = _row(
        {
            "evidence_availability": "AVAILABLE",
            "literary_category": "Historical narrative",
            "density_bucket": "0",
        },
        41,
    )

    assert historical["density_bucket"] == "6-10"
    assert newer["density_bucket"] == "41+"


def test_density_zero_is_reserved_for_true_zero_unit_synthesis():
    row = _row(
        {
            "evidence_availability": "DATA_GAP",
            "literary_category": "Poetry/Wisdom",
            "density_bucket": "41+",
        },
        0,
    )

    assert row["synthesis_units"] == 0
    assert row["density_bucket"] == "0"
