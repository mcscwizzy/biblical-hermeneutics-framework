"""Focused tests for the isolated Commentary v1.2 transport diagnostic."""

from __future__ import annotations

import json

import pytest

from tools.commentary_v12_renderer_transport_diagnostic import (
    DiagnosticError,
    _assert_fresh_namespace,
    _hash_record,
    classify_boundaries,
    parse_event_stream,
)


def test_jsonl_event_capture_preserves_thread_turn_usage_and_final_message():
    stdout = b"\n".join(
        [
            b'{"type":"thread.started","thread_id":"thread-1"}',
            b'{"type":"turn.started","turn_id":"turn-1"}',
            b'{"type":"item.completed","item":{"type":"agent_message","text":"{\\"sections\\":[]}"}}',
            b'{"type":"turn.completed","usage":{"input_tokens":12,"cached_input_tokens":3,"output_tokens":4}}',
        ]
    ) + b"\n"
    parsed = parse_event_stream(stdout)
    assert parsed["thread_started"] is True
    assert parsed["thread_ids"] == ["thread-1"]
    assert parsed["turn_completed"] is True
    assert parsed["usage"]["output_tokens"] == 4
    assert parsed["final_message"]["text"] == '{"sections":[]}'


def test_hash_record_reports_exact_bytes_without_normalization():
    value = b'{"sections":[]}\r\n'
    record = _hash_record(value)
    assert record["present"] is True
    assert record["byte_length"] == len(value)
    assert record["sha256"] == "e8b195cb1210f47cdc1fbb5f0ea5f45dbc6952162eeeb718dfde611c010d6875"


def test_output_last_message_and_event_message_classify_generated_empty():
    raw = b'{"reference":"Numbers 2","sections":[]}'
    classification = classify_boundaries(
        event_final=raw,
        output_file=raw,
        bhf_return=raw,
        parsed_payload={"reference": "Numbers 2", "sections": []},
        conformance_payload=None,
        process_returncode=0,
        output_file_missing=False,
    )
    assert classification == (
        "CODEX_GENERATED_EMPTY",
        "Codex execution event stream final agent message",
    )


def test_populated_event_message_lost_in_output_file_is_precisely_classified():
    event = b'{"reference":"Numbers 2","sections":[{"blocks":[]}]}'
    empty = b'{"reference":"Numbers 2","sections":[]}'
    assert classify_boundaries(
        event_final=event,
        output_file=empty,
        bhf_return=empty,
        parsed_payload=json.loads(empty),
        conformance_payload=None,
        process_returncode=0,
        output_file_missing=False,
    )[0] == "CODEX_OUTPUT_FILE_LOSS"


def test_bhf_wrapper_loss_and_parser_loss_classify_first_boundary():
    populated = b'{"reference":"Numbers 2","sections":[{"blocks":[]}]}'
    empty = b'{"reference":"Numbers 2","sections":[]}'
    assert classify_boundaries(
        event_final=populated,
        output_file=populated,
        bhf_return=empty,
        parsed_payload=json.loads(populated),
        conformance_payload=None,
        process_returncode=0,
        output_file_missing=False,
    )[0] == "BHF_RENDERER_WRAPPER_LOSS"
    assert classify_boundaries(
        event_final=populated,
        output_file=populated,
        bhf_return=populated,
        parsed_payload={"reference": "Numbers 2", "sections": [{"blocks": []}]},
        conformance_payload={"reference": "Numbers 2", "sections": []},
        process_returncode=0,
        output_file_missing=False,
    )[0] == "BHF_CONFORMANCE_PARSER_LOSS"


def test_missing_output_file_is_a_transport_error_even_on_success_exit():
    assert classify_boundaries(
        event_final=b'{"sections":[]}',
        output_file=None,
        bhf_return=None,
        parsed_payload=None,
        conformance_payload=None,
        process_returncode=0,
        output_file_missing=True,
    )[0] == "TRANSPORT_ERROR"


def test_existing_diagnostic_namespace_is_rejected_to_prevent_replay(tmp_path):
    root = tmp_path / "diagnostic"
    root.mkdir()
    (root / "output-last-message.raw").write_bytes(b"prior")
    with pytest.raises(DiagnosticError, match="artifact replay"):
        _assert_fresh_namespace(root)
