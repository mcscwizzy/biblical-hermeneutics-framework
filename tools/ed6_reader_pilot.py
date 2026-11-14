#!/usr/bin/env python3
"""Validate, import, and summarize local BHF ED-6 reader-pilot records.

The normal CLI accepts only authentic, de-identified participant records. Test
fixtures are marked synthetic and are rejected unless the Python API is called
with ``allow_synthetic=True`` explicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = REPOSITORY_ROOT / ".bhf-data/ed6-reader-pilot/sessions.jsonl"
SCHEMA_VERSION = "ed6-reader-pilot-v1"

TASK_IDS = (
    "discover-genesis6",
    "understand-genesis12",
    "interpret-psalm82",
    "verify-deuteronomy32",
    "verify-psalm145",
    "continue-jonah-matthew",
    "verify-1corinthians11",
    "retrieve-1john3",
    "empty-1kings2",
)
VERIFICATION_FIELDS = (
    "source_found",
    "claim_linked_to_source",
    "source_locator_found",
    "uncertainty_recognized",
    "review_status_recognized",
)
ALLOWED_ORIGINS = {"participant_session", "synthetic_test_fixture"}
FORBIDDEN_FIELDS = {
    "name", "full_name", "first_name", "last_name", "email", "phone",
    "church", "congregation", "denomination", "ip", "ip_address",
    "address", "street_address", "city", "date_of_birth", "birth_date",
    "account", "account_id", "user_id", "recording", "recording_path",
    "audio_path", "video_path",
}
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d{1,2}[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\d)")
IP_PATTERN = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")

ENUMS: dict[str, set[str]] = {
    "session_status": {"complete", "incomplete", "stopped"},
    "device_class": {"desktop", "mobile", "tablet", "unknown"},
    "study_experience_band": {"regular", "some", "limited_or_none", "prefer_not_to_say"},
    "task_type": {"discover", "understand", "interpret", "verify", "continue", "retrieve", "negative"},
    "completion": {"completed", "partially_completed", "not_completed", "not_attempted"},
    "assistance": {"none", "minor_prompt", "substantial_assistance", "not_observed"},
    "observation_status": {"yes", "partial", "no", "not_applicable", "not_observed"},
    "follow_up_question_emerged": {"yes", "no", "unclear", "not_observed"},
    "problem_category": {
        "critical_integrity", "accessibility_barrier", "navigation", "terminology",
        "evidence_density", "subjective_preference", "out_of_mission", "other",
    },
}


def _issue(code: str, field: str, message: str, *, severity: str = "error") -> dict[str, str]:
    return {"code": code, "field": field, "message": message, "severity": severity}


def _scan_identifiers(value: Any, field_path: str, issues: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = str(key).strip().lower()
            child_path = f"{field_path}.{key_name}" if field_path else key_name
            if key_name in FORBIDDEN_FIELDS:
                issues.append(_issue("forbidden_field", child_path, "This field may contain a direct identifier and is not part of the study schema."))
            _scan_identifiers(child, child_path, issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_identifiers(child, f"{field_path}[{index}]", issues)
    elif isinstance(value, str) and (
        field_path.endswith((".note", ".participant_quote", ".direct_observations", ".facilitator_interpretations", ".confusing_language", ".exploration_interest_response", ".most_confusing", ".suggested_change"))
        or "[" in field_path
    ):
        if EMAIL_PATTERN.search(value) or PHONE_PATTERN.search(value) or IP_PATTERN.search(value):
            issues.append(_issue("possible_identifier", field_path, "Possible contact or network identifier found; review and redact locally before import."))


def _is_enum(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def validate_session(record: dict[str, Any], allow_synthetic: bool = False) -> list[dict[str, str]]:
    """Return field-level issues; warnings do not make the record invalid."""

    issues: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return [_issue("record_not_object", "$", "Each JSONL line must contain one object.")]

    _scan_identifiers(record, "", issues)
    allowed_top = {
        "schema_version", "record_origin", "participant_code", "session_status",
        "device_class", "study_experience_band", "quote_consent", "assigned_task_ids",
        "tasks", "post_session",
    }
    for key in record:
        if key not in allowed_top and key.lower() not in FORBIDDEN_FIELDS:
            issues.append(_issue("unknown_field", str(key), "Field is not part of the ED-6 record schema."))
    for key in sorted(allowed_top - set(record)):
        issues.append(_issue("required_field_missing", key, "Required field is missing."))

    if record.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("schema_version", "schema_version", "Unsupported schema version."))
    origin = record.get("record_origin")
    if not _is_enum(origin, ALLOWED_ORIGINS):
        issues.append(_issue("record_origin", "record_origin", "Record origin must be participant_session or synthetic_test_fixture."))
    elif origin == "synthetic_test_fixture" and not allow_synthetic:
        issues.append(_issue("synthetic_record_rejected", "record_origin", "Synthetic test fixtures cannot be imported as participant data."))

    participant_code = record.get("participant_code")
    if not isinstance(participant_code, str) or not re.fullmatch(r"P\d{2,3}", participant_code):
        issues.append(_issue("participant_code", "participant_code", "Use an anonymous code such as P01."))

    for field in ("session_status", "device_class"):
        if not _is_enum(record.get(field), ENUMS[field]):
            issues.append(_issue("invalid_value", field, "Value is outside the allowed choices."))
    experience = record.get("study_experience_band")
    if experience is not None and not _is_enum(experience, ENUMS["study_experience_band"]):
        issues.append(_issue("invalid_value", "study_experience_band", "Use a broad optional category or null."))
    if not isinstance(record.get("quote_consent"), bool):
        issues.append(_issue("invalid_value", "quote_consent", "quote_consent must be true or false."))

    assigned = record.get("assigned_task_ids")
    assigned_set: set[str] = set()
    if not isinstance(assigned, list) or not 1 <= len(assigned) <= 4 or any(not isinstance(item, str) for item in assigned):
        issues.append(_issue("assigned_task_ids", "assigned_task_ids", "Record one to four unique assigned task IDs."))
    elif len(set(assigned)) != len(assigned):
        issues.append(_issue("assigned_task_ids", "assigned_task_ids", "Assigned task IDs must be unique."))
    else:
        for index, task_id in enumerate(assigned):
            if task_id not in TASK_IDS:
                issues.append(_issue("unknown_task_id", f"assigned_task_ids[{index}]", "Task ID is not in the ED-6 task bank."))
            else:
                assigned_set.add(task_id)

    tasks = record.get("tasks")
    if not isinstance(tasks, list):
        issues.append(_issue("invalid_value", "tasks", "tasks must be a list."))
        tasks = []
    seen_task_ids: set[str] = set()
    for index, task in enumerate(tasks):
        path = f"tasks[{index}]"
        if not isinstance(task, dict):
            issues.append(_issue("task_not_object", path, "Each task observation must be an object."))
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or task_id not in TASK_IDS:
            issues.append(_issue("unknown_task_id", f"{path}.task_id", "Task ID is not in the ED-6 task bank."))
        elif task_id not in assigned_set:
            issues.append(_issue("unassigned_task", f"{path}.task_id", "Observed task must be listed in assigned_task_ids."))
        if isinstance(task_id, str) and task_id in seen_task_ids:
            issues.append(_issue("duplicate_task_observation", f"{path}.task_id", "Each assigned task may have one observation per session."))
        if isinstance(task_id, str):
            seen_task_ids.add(task_id)

        allowed_task = {
            "task_id", "task_type", "completion", "assistance", "duration_minutes",
            "verification", "follow_up_question_emerged", "observed_problems",
            "confusing_language", "direct_observations", "facilitator_interpretations",
            "participant_quote",
        }
        for key in task:
            if key not in allowed_task and key.lower() not in FORBIDDEN_FIELDS:
                issues.append(_issue("unknown_field", f"{path}.{key}", "Field is not part of the task schema."))
        for key in sorted(allowed_task - {"participant_quote"} - set(task)):
            issues.append(_issue("required_field_missing", f"{path}.{key}", "Required task field is missing."))
        for field in ("task_type", "completion", "assistance", "follow_up_question_emerged"):
            if not _is_enum(task.get(field), ENUMS[field]):
                issues.append(_issue("invalid_value", f"{path}.{field}", "Value is outside the allowed choices."))
        duration = task.get("duration_minutes")
        if duration is not None and (
            isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 <= duration <= 180
        ):
            issues.append(_issue("invalid_value", f"{path}.duration_minutes", "Use a number from 0 to 180 or null."))

        verification = task.get("verification")
        if not isinstance(verification, dict):
            issues.append(_issue("invalid_value", f"{path}.verification", "verification must be an object."))
        else:
            for key in verification:
                if key not in VERIFICATION_FIELDS:
                    issues.append(_issue("unknown_field", f"{path}.verification.{key}", "Field is not part of the verification schema."))
            for field in VERIFICATION_FIELDS:
                if not _is_enum(verification.get(field), ENUMS["observation_status"]):
                    issues.append(_issue("invalid_value", f"{path}.verification.{field}", "Use yes, partial, no, not_applicable, or not_observed."))

        problems = task.get("observed_problems")
        if not isinstance(problems, list):
            issues.append(_issue("invalid_value", f"{path}.observed_problems", "observed_problems must be a list."))
        else:
            for problem_index, problem in enumerate(problems):
                problem_path = f"{path}.observed_problems[{problem_index}]"
                if (
                    not isinstance(problem, dict)
                    or not _is_enum(problem.get("category"), ENUMS["problem_category"])
                    or not isinstance(problem.get("note"), str)
                ):
                    issues.append(_issue("invalid_value", problem_path, "Each problem needs a recognized category and a text note."))
                elif set(problem) != {"category", "note"}:
                    issues.append(_issue("unknown_field", problem_path, "Problem fields must be category and note only."))
        for field in ("confusing_language", "direct_observations", "facilitator_interpretations"):
            values = task.get(field)
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                issues.append(_issue("invalid_value", f"{path}.{field}", "Field must be a list of strings."))
        if "participant_quote" in task and not record.get("quote_consent"):
            issues.append(_issue("quote_consent_required", f"{path}.participant_quote", "A participant quote requires separate explicit consent."))
        if "participant_quote" in task and not isinstance(task["participant_quote"], str):
            issues.append(_issue("invalid_value", f"{path}.participant_quote", "participant_quote must be text."))

    if record.get("session_status") == "complete":
        for task_id in sorted(assigned_set - seen_task_ids):
            issues.append(_issue("assigned_task_not_observed", f"tasks.{task_id}", "Assigned task has no observation; record it as not_observed if known.", severity="warning"))

    post = record.get("post_session")
    if not isinstance(post, dict):
        issues.append(_issue("invalid_value", "post_session", "post_session must be an object."))
    else:
        expected = {"exploration_interest_response", "most_confusing", "suggested_change"}
        for key in post:
            if key not in expected and key.lower() not in FORBIDDEN_FIELDS:
                issues.append(_issue("unknown_field", f"post_session.{key}", "Field is not part of the post-session schema."))
        for key in sorted(expected - set(post)):
            issues.append(_issue("required_field_missing", f"post_session.{key}", "Required field is missing."))
        for key, value in post.items():
            if key in expected and not isinstance(value, str):
                issues.append(_issue("invalid_value", f"post_session.{key}", "Response must be text."))

    return issues


def read_jsonl(path: Path, allow_synthetic: bool = False) -> dict[str, Any]:
    """Read every physical input line and return records plus non-content diagnostics."""

    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    input_lines = blank_lines = invalid_records = incomplete_records = synthetic_records = 0
    seen_codes: set[str] = set()
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            input_lines += 1
            if not line.strip():
                blank_lines += 1
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                issues.append({"line": line_number, **_issue("malformed_json", "$", "Line is not valid JSON; source text is not echoed.")})
                invalid_records += 1
                continue
            if not isinstance(record, dict):
                issues.append({"line": line_number, **_issue("record_not_object", "$", "Each JSONL line must contain one object.")})
                invalid_records += 1
                continue

            if record.get("record_origin") == "synthetic_test_fixture":
                synthetic_records += 1
            record_issues = validate_session(record, allow_synthetic=allow_synthetic)
            code = record.get("participant_code")
            if isinstance(code, str) and code in seen_codes:
                record_issues.append(_issue("duplicate_participant_code", "participant_code", "Participant code already appears in this input."))
            elif isinstance(code, str):
                seen_codes.add(code)
            errors = [issue for issue in record_issues if issue.get("severity") == "error"]
            issues.extend({"line": line_number, **issue} for issue in record_issues)
            if errors:
                invalid_records += 1
                continue
            records.append(record)
            if record.get("session_status") != "complete":
                incomplete_records += 1

    summary = {
        "input_lines": input_lines,
        "blank_lines": blank_lines,
        "valid_records": len(records),
        "invalid_records": invalid_records,
        "incomplete_records": incomplete_records,
        "synthetic_records": synthetic_records,
    }
    return {"records": records, "issues": issues, "summary": summary}


def _distribution(values: list[str]) -> dict[str, Any]:
    return {"counts": dict(sorted(Counter(values).items())), "denominator": len(values)}


def analyze_records(records: list[dict[str, Any]], input_summary: dict[str, Any]) -> dict[str, Any]:
    """Create aggregate counts only; raw notes and participant codes are excluded."""

    status_counts = Counter(record.get("session_status", "unknown") for record in records)
    task_results: dict[str, Any] = {}
    for task_id in TASK_IDS:
        assigned = [record for record in records if task_id in record.get("assigned_task_ids", [])]
        observations = {
            record.get("participant_code"): next(
                (task for task in record.get("tasks", []) if task.get("task_id") == task_id), None
            )
            for record in assigned
        }
        task_observations = [task for task in observations.values() if task is not None]
        completion_values = [task.get("completion", "not_observed") if task else "not_observed" for task in observations.values()]
        assistance_values = [task.get("assistance", "not_observed") for task in task_observations]
        followup_values = [task.get("follow_up_question_emerged", "not_observed") for task in task_observations]
        duration_values = [
            task["duration_minutes"] for task in task_observations
            if isinstance(task.get("duration_minutes"), (int, float)) and not isinstance(task.get("duration_minutes"), bool)
        ]
        verification = {
            field: _distribution([
                task.get("verification", {}).get(field, "not_observed")
                for task in task_observations
                if task.get("verification", {}).get(field, "not_observed") != "not_observed"
            ])
            for field in VERIFICATION_FIELDS
        }
        problems = Counter(
            problem.get("category", "other")
            for task in task_observations
            for problem in task.get("observed_problems", [])
            if isinstance(problem, dict)
        )
        observation_denominator = len(task_observations)
        task_results[task_id] = {
            "assigned_sessions": len(assigned),
            "completion": _distribution(completion_values),
            "assistance": _distribution(assistance_values),
            "duration_minutes": {
                "denominator": len(duration_values),
                "minimum": min(duration_values) if duration_values else None,
                "median": statistics.median(duration_values) if duration_values else None,
                "maximum": max(duration_values) if duration_values else None,
            },
            "verification": verification,
            "follow_up_question_emerged": _distribution(followup_values),
            "observed_problem_categories": {
                "counts": dict(sorted(problems.items())),
                "denominator": sum(problems.values()),
            },
            "direct_observation_entries": {
                "count": sum(len(task.get("direct_observations", [])) for task in task_observations),
                "denominator": observation_denominator,
            },
            "confusing_language_entries": {
                "count": sum(len(task.get("confusing_language", [])) for task in task_observations),
                "denominator": observation_denominator,
            },
            "facilitator_interpretation_entries": {
                "count": sum(len(task.get("facilitator_interpretations", [])) for task in task_observations),
                "denominator": observation_denominator,
            },
            "consented_quote_entries": {
                "count": sum(bool(task.get("participant_quote")) for task in task_observations),
                "denominator": observation_denominator,
            },
        }

    post_fields = ("exploration_interest_response", "most_confusing", "suggested_change")
    post_session_counts = {
        field: {
            "sessions_with_response": sum(bool(record.get("post_session", {}).get(field, "").strip()) for record in records),
            "denominator": len(records),
        }
        for field in post_fields
    }
    return {
        "report_type": "aggregate_only",
        "interpretation": "Exploratory convenience-sample usability observations; not statistically representative and not a scholarly approval measure.",
        "input_quality": {key: input_summary.get(key, 0) for key in (
            "input_lines", "blank_lines", "valid_records", "invalid_records", "incomplete_records", "synthetic_records"
        )},
        "participant_sessions": {"denominator": len(records), "status_counts": dict(sorted(status_counts.items()))},
        "task_results": task_results,
        "post_session_response_counts": post_session_counts,
        "privacy": "No participant codes or raw free-text observations are included in this report.",
    }


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def import_records(input_path: Path, output_path: Path, allow_synthetic: bool = False) -> dict[str, Any]:
    """Append a fully valid batch atomically, keeping the local store mode 0600."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    if input_path.resolve() == output_path.resolve():
        return {"imported": False, "issues": [_issue("same_input_output", "$", "Input and output paths must be different.")], "summary": {}}
    batch = read_jsonl(input_path, allow_synthetic=allow_synthetic)
    if batch["summary"]["invalid_records"] or not batch["records"]:
        if not batch["records"] and batch["summary"]["invalid_records"] == 0:
            batch["issues"].append({"line": 0, **_issue("empty_import", "$", "No session records were provided.")})
        return {"imported": False, "issues": batch["issues"], "summary": batch["summary"]}

    existing_records: list[dict[str, Any]] = []
    if output_path.exists():
        existing = read_jsonl(output_path)
        if existing["summary"]["invalid_records"]:
            return {"imported": False, "issues": existing["issues"], "summary": batch["summary"]}
        existing_records = existing["records"]
    known_codes = {record["participant_code"] for record in existing_records}
    duplicate_codes = known_codes & {record["participant_code"] for record in batch["records"]}
    if duplicate_codes:
        batch["issues"].extend(
            _issue("participant_code_already_imported", "participant_code", "Participant code already exists in the local store.")
            for _code in sorted(duplicate_codes)
        )
        return {"imported": False, "issues": batch["issues"], "summary": batch["summary"]}

    all_records = existing_records + batch["records"]
    serialized = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in all_records)
    _atomic_write(output_path, serialized)
    return {"imported": True, "issues": batch["issues"], "summary": batch["summary"], "output": str(output_path)}


def _serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="Validate JSONL records without modifying them.")
    validate_parser.add_argument("input", type=Path)
    import_parser = subparsers.add_parser("import", help="Validate and atomically append records to the ignored local store.")
    import_parser.add_argument("input", type=Path)
    import_parser.add_argument("--output", type=Path, default=DEFAULT_DATA_FILE)
    report_parser = subparsers.add_parser("report", help="Generate aggregate JSON from valid local records.")
    report_parser.add_argument("input", type=Path, nargs="?", default=DEFAULT_DATA_FILE)
    report_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            result = read_jsonl(args.input)
            print(_serialize({"summary": result["summary"], "issues": result["issues"]}), end="")
            return 1 if result["summary"]["invalid_records"] else 0
        if args.command == "import":
            result = import_records(args.input, args.output)
            print(_serialize(result), end="")
            return 0 if result["imported"] else 1
        result = read_jsonl(args.input)
        if result["summary"]["invalid_records"]:
            print(_serialize({"summary": result["summary"], "issues": result["issues"]}), end="")
            return 1
        report = analyze_records(result["records"], result["summary"])
        serialized = _serialize(report)
        if args.output:
            _atomic_write(args.output, serialized)
        else:
            print(serialized, end="")
        return 0
    except (OSError, UnicodeError) as exc:
        print(f"I/O error: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
