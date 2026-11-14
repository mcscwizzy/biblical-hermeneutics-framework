from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ed6_reader_pilot import analyze_records, import_records, read_jsonl, validate_session


FIXTURE = Path("tests/fixtures/ed6_reader_pilot/synthetic_sessions.jsonl")


def session(
    code: str = "P01",
    *,
    origin: str = "participant_session",
    status: str = "complete",
    task_completion: str = "completed",
    source_found: str = "yes",
    direct_observations: list[str] | None = None,
    facilitator_interpretations: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "ed6-reader-pilot-v1",
        "record_origin": origin,
        "participant_code": code,
        "session_status": status,
        "device_class": "desktop",
        "study_experience_band": "prefer_not_to_say",
        "quote_consent": False,
        "assigned_task_ids": ["interpret-genesis6"],
        "tasks": [
            {
                "task_id": "interpret-genesis6",
                "task_type": "interpret",
                "completion": task_completion,
                "assistance": "none",
                "duration_minutes": 4,
                "verification": {
                    "source_found": source_found,
                    "claim_linked_to_source": "yes",
                    "source_locator_found": "yes",
                    "uncertainty_recognized": "yes",
                    "review_status_recognized": "yes",
                },
                "follow_up_question_emerged": "yes",
                "observed_problems": [],
                "confusing_language": [],
                "direct_observations": direct_observations or [],
                "facilitator_interpretations": facilitator_interpretations or [],
            }
        ],
        "post_session": {
            "exploration_interest_response": "",
            "most_confusing": "",
            "suggested_change": "",
        },
    }


def write_jsonl(path: Path, records: list[dict], *, malformed_line: str | None = None) -> None:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    if malformed_line is not None:
        lines.insert(0, malformed_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_valid_complete_record_is_accepted(tmp_path):
    path = tmp_path / "sessions.jsonl"
    write_jsonl(path, [session()])

    result = read_jsonl(path)

    assert result["summary"] == {
        "input_lines": 1,
        "blank_lines": 0,
        "valid_records": 1,
        "invalid_records": 0,
        "incomplete_records": 0,
        "synthetic_records": 0,
    }
    assert result["issues"] == []
    assert result["records"][0]["participant_code"] == "P01"


def test_incomplete_session_is_retained_and_counted(tmp_path):
    path = tmp_path / "sessions.jsonl"
    write_jsonl(path, [session(status="incomplete", task_completion="partially_completed")])

    result = read_jsonl(path)
    report = analyze_records(result["records"], result["summary"])

    assert result["summary"]["incomplete_records"] == 1
    assert report["participant_sessions"]["denominator"] == 1
    assert report["task_results"]["interpret-genesis6"]["completion"]["counts"]["partially_completed"] == 1
    assert report["task_results"]["interpret-genesis6"]["completion"]["denominator"] == 1


def test_malformed_jsonl_line_is_reported_without_echoing_source(tmp_path):
    path = tmp_path / "sessions.jsonl"
    write_jsonl(path, [session()], malformed_line='{"email":"reader@example.invalid"')

    result = read_jsonl(path)

    assert result["summary"]["input_lines"] == 2
    assert result["summary"]["valid_records"] == 1
    assert result["summary"]["invalid_records"] == 1
    assert result["issues"][0]["line"] == 1
    assert result["issues"][0]["field"] == "$"
    assert "reader@example.invalid" not in json.dumps(result["issues"])


def test_duplicate_participant_codes_block_input(tmp_path):
    path = tmp_path / "sessions.jsonl"
    write_jsonl(path, [session("P01"), session("P01")])

    result = read_jsonl(path)

    assert result["summary"]["invalid_records"] == 1
    assert any(issue["code"] == "duplicate_participant_code" and issue["line"] == 2 for issue in result["issues"])


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (lambda record: record.update(email="reader@example.invalid"), "forbidden_field"),
        (lambda record: record["tasks"][0]["direct_observations"].append("Contact reader@example.invalid"), "possible_identifier"),
        (lambda record: record["tasks"][0]["direct_observations"].append("Call 312-555-0101"), "possible_identifier"),
        (lambda record: record["tasks"][0]["direct_observations"].append("IP 192.0.2.10"), "possible_identifier"),
    ],
)
def test_identifier_fields_and_free_text_are_flagged_without_echoing_values(mutate, expected_code):
    record = session()
    mutate(record)

    issues = validate_session(record)

    assert expected_code in {issue["code"] for issue in issues}
    assert "reader@example.invalid" not in json.dumps(issues)
    assert "312-555-0101" not in json.dumps(issues)
    assert "192.0.2.10" not in json.dumps(issues)


def test_quotes_require_separate_explicit_consent():
    record = session()
    record["tasks"][0]["participant_quote"] = "I would explore this more."

    issues = validate_session(record)

    assert any(issue["code"] == "quote_consent_required" for issue in issues)


def test_familiar_discovery_requires_the_participant_selected_passage():
    record = session()
    record["assigned_task_ids"] = ["discover-familiar-passage"]
    task = record["tasks"][0]
    task["task_id"] = "discover-familiar-passage"
    task["task_type"] = "discover"
    task["starting_passage"] = "Psalm 23:1-6"

    assert validate_session(record) == []

    del task["starting_passage"]
    assert any(issue["code"] == "selected_passage_required" for issue in validate_session(record))


def test_task_type_must_match_the_assigned_task():
    record = session()
    record["tasks"][0]["task_type"] = "discover"

    assert any(issue["code"] == "task_type_mismatch" for issue in validate_session(record))


def test_synthetic_fixture_is_separated_from_authentic_input():
    result = read_jsonl(FIXTURE)

    assert result["summary"]["synthetic_records"] == 2
    assert result["summary"]["invalid_records"] == 2
    assert {issue["code"] for issue in result["issues"]} == {"synthetic_record_rejected"}

    allowed = read_jsonl(FIXTURE, allow_synthetic=True)
    assert allowed["summary"]["valid_records"] == 2
    assert allowed["summary"]["incomplete_records"] == 1


def test_aggregate_metrics_show_observed_denominators_and_no_raw_notes():
    first = session(
        "P01",
        direct_observations=["Reader opened the source disclosure after reading the claim."],
        facilitator_interpretations=["The source label may be unclear."],
    )
    second = session("P02", status="incomplete", task_completion="partially_completed", source_found="not_observed")
    result = analyze_records([first, second], {"input_lines": 2, "invalid_records": 0})
    task = result["task_results"]["interpret-genesis6"]

    assert task["completion"]["denominator"] == 2
    assert task["completion"]["counts"] == {"completed": 1, "partially_completed": 1}
    assert task["verification"]["source_found"]["denominator"] == 1
    assert task["verification"]["source_found"]["counts"] == {"yes": 1}
    assert task["duration_minutes"] == {"denominator": 2, "minimum": 4, "median": 4, "maximum": 4}
    assert task["direct_observation_entries"] == {"count": 1, "denominator": 2}
    assert task["facilitator_interpretation_entries"] == {"count": 1, "denominator": 2}
    serialized = json.dumps(result)
    assert "Reader opened the source disclosure" not in serialized
    assert "The source label may be unclear" not in serialized


def test_invalid_import_writes_nothing(tmp_path):
    source = tmp_path / "invalid.jsonl"
    output = tmp_path / "local" / "sessions.jsonl"
    record = session()
    record["church"] = "Example Church"
    write_jsonl(source, [record])

    result = import_records(source, output)

    assert result["imported"] is False
    assert result["summary"]["invalid_records"] == 1
    assert not output.exists()


def test_import_creates_private_file_appends_new_codes_and_blocks_duplicates(tmp_path):
    source = tmp_path / "sessions.jsonl"
    output = tmp_path / "local" / "sessions.jsonl"
    write_jsonl(source, [session()])

    result = import_records(source, output)

    assert result["imported"] is True
    assert output.exists()
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_text(encoding="utf-8"))["participant_code"] == "P01"

    second_source = tmp_path / "second.jsonl"
    write_jsonl(second_source, [session("P02")])
    assert import_records(second_source, output)["imported"] is True
    before_duplicate = output.read_bytes()
    duplicate_result = import_records(second_source, output)
    assert duplicate_result["imported"] is False
    assert any(issue["code"] == "participant_code_already_imported" for issue in duplicate_result["issues"])
    assert output.read_bytes() == before_duplicate
    assert output.stat().st_mode & 0o777 == 0o600


def test_session_record_schema_matches_validator_fields():
    schema = json.loads(Path("docs/evidence-depth/ed6/session-record.schema.json").read_text(encoding="utf-8"))
    record = session()

    assert schema["properties"]["schema_version"]["const"] == record["schema_version"]
    assert set(schema["required"]) == set(record)
    assert validate_session(record) == []
