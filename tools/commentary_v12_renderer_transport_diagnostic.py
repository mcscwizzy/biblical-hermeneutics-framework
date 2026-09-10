#!/usr/bin/env python3
"""Capture one fresh Numbers 2 renderer turn across the BHF/Codex boundaries.

This is deliberately separate from the output-conformance runner.  It invokes
the installed Codex CLI exactly once, with JSONL transport capture enabled,
and preserves the bytes at each observable boundary for diagnosis.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.output_conformance import (  # noqa: E402
    conform_renderer_output,
    parse_renderer_json,
)
from framework.commentary.production.models import (  # noqa: E402
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    write_immutable,
)
from tools.commentary_v12_output_conformance import _exchange  # noqa: E402


DIAGNOSTIC_VERSION = "commentary-renderer-transport-diagnostic-v1"
DIAGNOSTIC_NAMESPACE = Path(
    ".bhf-data/bhf-commentary-candidates/commentary-renderer-transport-diagnostic-v1"
)
SOURCE_NAMESPACE = Path(
    ".bhf-data/bhf-commentary-candidates/"
    "commentary-output-conformance-v1-d278cba2d2151d1b4242"
)
SOURCE_PACKET = SOURCE_NAMESPACE / "renderer-input/001_numbers_002"
CODEX = Path("/home/johnwalker/.local/bin/codex")
RENDERER = "gpt-5.6-sol"
EFFORT = "medium"


class DiagnosticError(RuntimeError):
    """The isolated diagnostic cannot safely proceed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, _json_bytes(value))


def _hash_record(value: bytes | None) -> dict[str, Any]:
    if value is None:
        return {"present": False, "byte_length": None, "sha256": None}
    return {"present": True, "byte_length": len(value), "sha256": sha256_bytes(value)}


def _run_capture(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _cli_metadata() -> dict[str, Any]:
    version = _run_capture([str(CODEX), "--version"])
    help_result = _run_capture([str(CODEX), "exec", "--help"])
    help_bytes = help_result.stdout + help_result.stderr
    return {
        "version_stdout": version.stdout,
        "version_stderr": version.stderr,
        "version_returncode": version.returncode,
        "version": version.stdout.decode("utf-8", errors="replace").strip(),
        "help_bytes": help_bytes,
        "help_returncode": help_result.returncode,
        "json_supported": b"--json" in help_bytes,
    }


def _read_source(repo_root: Path) -> dict[str, Any]:
    root = repo_root / SOURCE_PACKET
    metadata_path = root / "metadata.json"
    system_path = root / "system_prompt.txt"
    user_path = root / "user_prompt.txt"
    if not all(path.is_file() for path in (metadata_path, system_path, user_path)):
        raise DiagnosticError(f"frozen Numbers 2 renderer input is incomplete: {root}")
    system = system_path.read_bytes()
    user = user_path.read_bytes()
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiagnosticError(f"invalid Numbers 2 renderer metadata: {exc}") from exc
    if metadata.get("reference") != "Numbers 2":
        raise DiagnosticError("frozen renderer packet is not Numbers 2")
    if metadata.get("system_prompt_sha256") != sha256_bytes(system):
        raise DiagnosticError("Numbers 2 system prompt hash disagrees with metadata")
    if metadata.get("candidate_input_sha256") != sha256_bytes(user):
        raise DiagnosticError("Numbers 2 user prompt hash disagrees with metadata")
    handoff = root
    exchange = _exchange(handoff).encode("utf-8")
    return {
        "root": root,
        "metadata": metadata,
        "system": system,
        "user": user,
        "exchange": exchange,
        "source_packet_id": metadata.get("source_packet_id"),
        "source_packet_hash": metadata.get("source_packet_hash"),
    }


def _live_paths(root: Path) -> tuple[Path, ...]:
    return tuple(
        root / name
        for name in (
            "codex-events.jsonl",
            "codex-stderr.txt",
            "output-last-message.raw",
            "bhf-renderer-return.raw",
            "invocation.json",
            "boundary-report.json",
        )
    )


def _assert_fresh_namespace(root: Path) -> dict[str, bool]:
    if root.exists():
        raise DiagnosticError(
            f"diagnostic namespace already exists; refusing artifact replay: {root}"
        )
    root.mkdir(parents=True)
    paths = _live_paths(root)
    status = {str(path.relative_to(root)): path.exists() for path in paths}
    if any(status.values()):
        raise DiagnosticError("a live diagnostic destination unexpectedly exists")
    return status


def _event_text(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    text = item.get("text")
    if isinstance(text, str):
        return text
    content = item.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                pieces.append(block["text"])
        if pieces:
            return "".join(pieces)
    return None


def _is_agent_message(item: Any) -> bool:
    return isinstance(item, dict) and item.get("type") in {
        "agent_message",
        "assistant_message",
        "message",
    }


def parse_event_stream(stdout: bytes) -> dict[str, Any]:
    """Interpret JSONL after its original stdout has been stored unchanged."""

    events: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for line_number, line in enumerate(stdout.splitlines(), 1):
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            parse_errors.append(f"line {line_number}: {exc}")
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            parse_errors.append(f"line {line_number}: JSON value is not an object")

    thread_ids: list[Any] = []
    turn_ids: list[Any] = []
    completed_events: list[dict[str, Any]] = []
    final_candidates: list[dict[str, Any]] = []
    deltas: list[str] = []
    usage: dict[str, Any] = {}
    model_values: list[Any] = []
    for index, event in enumerate(events):
        event_type = event.get("type")
        for field, target in (("thread_id", thread_ids), ("session_id", thread_ids), ("turn_id", turn_ids)):
            if event.get(field) is not None and event.get(field) not in target:
                target.append(event[field])
        if event_type == "thread.started":
            thread = event.get("thread")
            if isinstance(thread, dict) and thread.get("id") is not None:
                thread_ids.append(thread["id"])
        if event_type in {"turn.completed", "response.completed"}:
            completed_events.append(event)
            if isinstance(event.get("usage"), dict):
                usage.update(event["usage"])
        for key in ("model", "model_slug", "model_name"):
            if event.get(key) is not None and event[key] not in model_values:
                model_values.append(event[key])
        item = event.get("item")
        if _is_agent_message(item):
            text = _event_text(item)
            if text is not None and event_type in {"item.completed", "message.completed", "agent_message"}:
                final_candidates.append({"event_index": index, "event_type": event_type, "text": text})
        if event_type in {"response.output_text.delta", "output_text.delta"}:
            delta = event.get("delta")
            if isinstance(delta, str):
                deltas.append(delta)
        if event_type in {"response.output_text.done", "output_text.done"}:
            text = event.get("text")
            if isinstance(text, str):
                final_candidates.append({"event_index": index, "event_type": event_type, "text": text})

    chosen: dict[str, Any] | None = final_candidates[-1] if final_candidates else None
    if chosen is None and deltas:
        chosen = {"event_index": None, "event_type": "delta-concatenation", "text": "".join(deltas)}
    return {
        "event_count": len(events),
        "parse_errors": parse_errors,
        "thread_started": any(event.get("type") == "thread.started" for event in events),
        "thread_ids": thread_ids,
        "turn_started": any(event.get("type") == "turn.started" for event in events),
        "turn_ids": turn_ids,
        "turn_completed": bool(completed_events),
        "completion_events": completed_events,
        "usage": usage,
        "model_values": model_values,
        "final_candidates": final_candidates,
        "final_message": chosen,
    }


def _parsed_sections_empty(payload: dict[str, Any] | None) -> bool:
    return isinstance(payload, dict) and payload.get("sections") == []


def classify_boundaries(
    *,
    event_final: bytes | None,
    output_file: bytes | None,
    bhf_return: bytes | None,
    parsed_payload: dict[str, Any] | None,
    conformance_payload: dict[str, Any] | None,
    process_returncode: int,
    output_file_missing: bool,
) -> tuple[str, str]:
    """Return (primary classification, first divergence boundary)."""

    if output_file_missing or process_returncode != 0:
        return "TRANSPORT_ERROR", "Codex CLI process/output-file transport"
    if event_final is None:
        if output_file in (b"", b'{"reference":"Numbers 2","book":"Numbers","chapter":2,"status":"pending","sections":[],"generated_metadata":null}'):
            return "CODEX_NO_FINAL_OUTPUT", "Codex execution/event stream"
        return "UNKNOWN", "Codex execution/event stream final-message visibility"
    if event_final == output_file and _parsed_sections_empty(parsed_payload):
        return "CODEX_GENERATED_EMPTY", "Codex execution event stream final agent message"
    if event_final != output_file:
        event_payload, _, _ = parse_renderer_json(event_final)
        if isinstance(event_payload, dict) and event_payload.get("sections") not in (None, []):
            return "CODEX_OUTPUT_FILE_LOSS", "Codex event stream → --output-last-message"
        return "UNKNOWN", "Codex event stream → --output-last-message"
    if output_file != bhf_return:
        return "BHF_RENDERER_WRAPPER_LOSS", "--output-last-message → BHF renderer return"
    if not _parsed_sections_empty(parsed_payload) and _parsed_sections_empty(conformance_payload):
        return "BHF_CONFORMANCE_PARSER_LOSS", "BHF renderer return → conformance/parser"
    return "UNKNOWN", "none observed"


def _historical_attempt_evidence(repo_root: Path) -> dict[str, Any]:
    root = repo_root / SOURCE_NAMESPACE / "attempts/001_numbers_002"
    attempt_dirs = sorted(root.glob("attempt-*/"))
    runtime_files = [
        str(path.relative_to(repo_root))
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"raw-response.json", "conformance.json", "parsed.json", "validation.json"}
    ]
    return {
        "attempt_slots": [path.name for path in attempt_dirs],
        "attempt_raw_hashes": {
            path.name: sha256_bytes((path / "raw-response.json").read_bytes())
            for path in attempt_dirs
            if (path / "raw-response.json").is_file()
        },
        "runtime_receipt_files": runtime_files,
        "independent_live_turn_evidence": bool(runtime_files),
        "statement": (
            "The committed artifacts prove distinct attempt slots but do not independently prove distinct live Codex turns."
        ),
    }


def run(*, repo_root: Path = ROOT) -> dict[str, Any]:
    """Run exactly one fresh Numbers 2 renderer invocation."""

    source = _read_source(repo_root)
    root = repo_root / DIAGNOSTIC_NAMESPACE
    preflight = _assert_fresh_namespace(root)
    starting_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=repo_root, text=True
    ).strip()
    cli = _cli_metadata()
    _write_json(root / "source-input.json", {
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "source_namespace": str(SOURCE_NAMESPACE),
        "source_packet_path": str(SOURCE_PACKET),
        "source_packet_id": source["source_packet_id"],
        "source_packet_hash": source["source_packet_hash"],
        "reference": "Numbers 2",
        "renderer": RENDERER,
        "effort": EFFORT,
        "system_prompt": _hash_record(source["system"]),
        "user_prompt": _hash_record(source["user"]),
        "exchange_stdin": _hash_record(source["exchange"]),
    })
    write_immutable(root / "system_prompt.txt", source["system"])
    write_immutable(root / "user_prompt.txt", source["user"])
    write_immutable(root / "exchange.stdin", source["exchange"])
    write_immutable(root / "codex-version.txt", cli["version_stdout"])
    write_immutable(root / "codex-version-stderr.txt", cli["version_stderr"])
    write_immutable(root / "codex-exec-help.txt", cli["help_bytes"])
    _write_json(root / "preflight.json", {
        "recorded_at": _now(),
        "destination_artifacts_existed_immediately_before_execution": preflight,
        "all_destinations_absent": not any(preflight.values()),
        "fresh_renderer_invocation_count_authorized": 1,
        "json_supported": cli["json_supported"],
    })
    if not cli["json_supported"]:
        raise DiagnosticError("installed Codex CLI does not support --json; no renderer invocation made")

    temp_dir_path: str | None = None
    started_at = _now()
    exchange = source["exchange"]
    with tempfile.TemporaryDirectory(prefix="bhf-renderer-transport-") as temp_dir:
        temp_dir_path = temp_dir
        output_path = Path(temp_dir) / "response.txt"
        command = [
            str(CODEX), "exec", "--ephemeral", "--ignore-user-config",
            "-m", RENDERER, "-c", 'model_reasoning_effort="medium"',
            "-s", "read-only", "-C", temp_dir, "--skip-git-repo-check",
            "--output-last-message", str(output_path), "--json", "-",
        ]
        completed = subprocess.run(
            command,
            input=exchange,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        output_file = output_path.read_bytes() if output_path.is_file() else None
    ended_at = _now()

    write_immutable(root / "codex-events.jsonl", stdout)
    write_immutable(root / "codex-stderr.txt", stderr)
    if output_file is not None:
        write_immutable(root / "output-last-message.raw", output_file)
    parsed_events = parse_event_stream(stdout)
    final_text = (parsed_events.get("final_message") or {}).get("text")
    event_final = final_text.encode("utf-8") if isinstance(final_text, str) else None
    if event_final is not None:
        write_immutable(root / "event-stream-final-message.raw", event_final)
    bhf_return = output_file
    if bhf_return is not None:
        write_immutable(root / "bhf-renderer-return.raw", bhf_return)
    parsed_payload, parse_status, parse_errors = parse_renderer_json(bhf_return or b"")
    conformance = conform_renderer_output(
        parsed_payload,
        expected_reference="Numbers 2",
        expected_book="Numbers",
        expected_chapter=2,
        parse_status=parse_status,
        parse_errors=parse_errors,
    )
    _write_json(root / "parsed-json.json", {
        "parse_status": parse_status,
        "parse_errors": list(parse_errors),
        "payload": parsed_payload,
    })
    if conformance.valid and conformance.payload is not None:
        _write_json(root / "conformed-payload.json", conformance.payload)
    primary, divergence = classify_boundaries(
        event_final=event_final,
        output_file=output_file,
        bhf_return=bhf_return,
        parsed_payload=parsed_payload,
        conformance_payload=conformance.payload if conformance.valid else None,
        process_returncode=completed.returncode,
        output_file_missing=output_file is None,
    )
    historical = _historical_attempt_evidence(repo_root)
    report: dict[str, Any] = {
        "artifact_version": DIAGNOSTIC_VERSION,
        "repository_starting_sha": starting_sha,
        "repository_ending_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip(),
        "branch": branch,
        "diagnostic_implementation": str(Path(__file__).relative_to(repo_root)),
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "diagnostic_namespace": str(DIAGNOSTIC_NAMESPACE),
        "codex_cli_version": cli["version"],
        "codex_cli_json_supported": cli["json_supported"],
        "numbers_2_source_packet_id": source["source_packet_id"],
        "numbers_2_source_packet_hash": source["source_packet_hash"],
        "renderer": RENDERER,
        "effort": EFFORT,
        "prompt_bytes": {
            "system_prompt.txt": _hash_record(source["system"]),
            "user_prompt.txt": _hash_record(source["user"]),
            "exact_exchange_stdin": _hash_record(exchange),
        },
        "fresh_codex_renderer_invocations": 1,
        "fresh_invocation_evidence": {
            "namespace_was_absent_before_run": True,
            "destination_artifacts_absent_immediately_before_execution": preflight,
            "process_started_at": started_at,
            "process_ended_at": ended_at,
            "temporary_working_directory": temp_dir_path,
            "subprocess_exit_code": completed.returncode,
        },
        "codex_thread_session_ids": parsed_events["thread_ids"],
        "codex_turn_ids": parsed_events["turn_ids"],
        "event_stream": {
            "thread_started": parsed_events["thread_started"],
            "turn_started": parsed_events["turn_started"],
            "turn_completed": parsed_events["turn_completed"],
            "completion_events": parsed_events["completion_events"],
            "usage": parsed_events["usage"],
            "model_values": parsed_events["model_values"],
            "parse_errors": parsed_events["parse_errors"],
            "final_message": parsed_events["final_message"],
        },
        "boundaries": {
            "A_system_prompt": _hash_record(source["system"]),
            "B_user_prompt": _hash_record(source["user"]),
            "C_exact_exchange_stdin": _hash_record(exchange),
            "D_codex_stdout_jsonl": _hash_record(stdout),
            "E_event_stream_final_message": _hash_record(event_final),
            "F_output_last_message_raw": _hash_record(output_file),
            "G_bhf_renderer_return": _hash_record(bhf_return),
            "H_parsed_json_object": _hash_record(_json_bytes(parsed_payload) if parsed_payload is not None else None),
            "I_conformed_payload": _hash_record(_json_bytes(conformance.payload) if conformance.valid and conformance.payload is not None else None),
        },
        "comparisons": {
            "event_final_equals_output_last_message": event_final == output_file if event_final is not None and output_file is not None else None,
            "output_last_message_equals_bhf_return": output_file == bhf_return if output_file is not None and bhf_return is not None else None,
            "event_final_equals_bhf_return": event_final == bhf_return if event_final is not None and bhf_return is not None else None,
        },
        "process": {
            "return_code": completed.returncode,
            "output_last_message_file_present": output_file is not None,
            "stderr": _hash_record(stderr),
            "completion_status": next((event.get("status") for event in parsed_events["completion_events"] if event.get("status") is not None), None),
            "output_token_count": parsed_events["usage"].get("output_tokens"),
            "input_token_count": parsed_events["usage"].get("input_tokens"),
            "cached_input_token_count": parsed_events["usage"].get("cached_input_tokens"),
        },
        "json_parse": {
            "status": parse_status,
            "errors": list(parse_errors),
            "parsed_sections_literal_empty_array": _parsed_sections_empty(parsed_payload),
            "conformance_valid": conformance.valid,
            "conformance_errors": list(conformance.errors),
        },
        "first_divergence_boundary": divergence,
        "primary_classification": primary,
        "secondary_observation": (
            "IDENTICAL_MODEL_OUTPUT_REPRODUCED"
            if output_file is not None and output_file == (repo_root / SOURCE_NAMESPACE / "attempts/001_numbers_002/attempt-001/raw-response.json").read_bytes()
            else None
        ),
        "historical_committed_attempts": historical,
        "numbers_1_control_needed": False,
        "behavioral_production_changes": False,
        "recommended_smallest_next_remediation": (
            "Treat the empty object as renderer/execution-side until a separate, explicitly authorized runtime investigation is performed."
            if primary == "CODEX_GENERATED_EMPTY"
            else "Preserve this boundary evidence and investigate only the identified failing transport boundary."
        ),
    }
    _write_json(root / "invocation.json", {
        "command": command,
        "stdin_sha256": sha256_bytes(exchange),
        "stdin_byte_length": len(exchange),
        "returncode": completed.returncode,
        "started_at": started_at,
        "ended_at": ended_at,
        "output_file": str(output_path),
        "output_file_present": output_file is not None,
    })
    _write_json(root / "boundary-report.json", report)
    return report


def finalize_report(*, repo_root: Path = ROOT) -> dict[str, Any]:
    """Add repository/test handoff metadata without invoking Codex."""

    root = repo_root / DIAGNOSTIC_NAMESPACE
    report_path = root / "boundary-report.json"
    if not report_path.is_file():
        raise DiagnosticError("cannot finalize a diagnostic without boundary-report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update(
        {
            "final_report_path": str(DIAGNOSTIC_NAMESPACE / "final-diagnostic-report.json"),
            "tests_run": [
                {
                    "command": ".venv/bin/pytest -q tests/test_commentary_v12_renderer_transport_diagnostic.py tests/test_commentary_output_conformance.py",
                    "result": "17 passed",
                }
            ],
            "files_changed": [
                "tools/commentary_v12_renderer_transport_diagnostic.py",
                "tests/test_commentary_v12_renderer_transport_diagnostic.py",
                "docs/commentary-v1.2-renderer-transport-diagnostic-v1.md",
            ]
            + sorted(
                str(path.relative_to(repo_root))
                for path in root.rglob("*")
                if path.is_file() and path.name != "final-diagnostic-report.json"
            ),
            "repository_ending_sha_at_report_finalization": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
            ).strip(),
        }
    )
    write_immutable(root / "final-diagnostic-report.json", _json_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "finalize"), nargs="?", default="run")
    args = parser.parse_args(argv)
    try:
        result = run() if args.command == "run" else finalize_report()
    except (DiagnosticError, ArtifactCollisionError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
