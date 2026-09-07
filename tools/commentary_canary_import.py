#!/usr/bin/env python3
"""Import isolated external renderer responses into the Commentary v1.2 canary."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    CommentaryStatus,
    ExternalCommentaryResponse,
)
from bhf_agent.chapter_commentary.storage import get_commentary_filename, save_commentary
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis, validate_synthesis
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v12_canary import (
    CANDIDATE_ROOT,
    CANARY_ROOT,
    V11_STATE,
    _protected_v11_errors,
    _read_json,
    _write_json,
    calculate_packet_id,
)


RESPONSES_ROOT = CANARY_ROOT / "responses"
RAW_RESPONSE_ROOT = RESPONSES_ROOT / "raw"
ACCEPTED_RESPONSE_ROOT = RESPONSES_ROOT / "accepted"
REJECTED_RESPONSE_ROOT = RESPONSES_ROOT / "rejected"
IMPORT_ARTIFACT_PATH = CANARY_ROOT / "canary-import.json"

_ENVELOPE_FIELDS = frozenset(
    {
        "reference",
        "packet_id",
        "prompt_version",
        "evidence_hash",
        "synthesis_hash",
        "renderer_label",
        "response_payload",
    }
)


class ExternalResponseRejectionCode(str, Enum):
    MALFORMED_RESPONSE_JSON = "MALFORMED_RESPONSE_JSON"
    MALFORMED_RESPONSE_ENVELOPE = "MALFORMED_RESPONSE_ENVELOPE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    NON_CANARY_RESPONSE = "NON_CANARY_RESPONSE"
    UNKNOWN_PACKET = "UNKNOWN_PACKET"
    PACKET_ID_MISMATCH = "PACKET_ID_MISMATCH"
    PACKET_CONTENT_MISMATCH = "PACKET_CONTENT_MISMATCH"
    DUPLICATE_RESPONSE = "DUPLICATE_RESPONSE"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    PROMPT_VERSION_MISMATCH = "PROMPT_VERSION_MISMATCH"
    EVIDENCE_HASH_MISMATCH = "EVIDENCE_HASH_MISMATCH"
    SYNTHESIS_HASH_MISMATCH = "SYNTHESIS_HASH_MISMATCH"
    STALE_RESPONSE = "STALE_RESPONSE"
    MALFORMED_COMMENTARY_JSON = "MALFORMED_COMMENTARY_JSON"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PROTECTED_ARTIFACT_CHANGED = "PROTECTED_ARTIFACT_CHANGED"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"


def import_responses(
    input_dir: str | Path | None = None,
    *,
    candidate_root: str | Path = CANDIDATE_ROOT,
    repo_root: str | Path = ROOT,
    imported_at: str | None = None,
    bundle_loader: Callable[..., Any] = get_chapter_evidence_bundle,
) -> dict[str, Any]:
    """Validate raw envelopes independently and promote only fully valid commentary."""

    candidate_root = Path(candidate_root)
    repo_root = Path(repo_root)
    canary_root = candidate_root / "canary"
    raw_root = Path(input_dir) if input_dir is not None else canary_root / "responses/raw"
    accepted_root = canary_root / "responses/accepted"
    rejected_root = canary_root / "responses/rejected"
    import_path = canary_root / "canary-import.json"
    manifest = _read_json(canary_root / "canary-generation-manifest.json")
    preflight = _read_json(canary_root / "canary-preflight.json")
    manifest_rows = list(manifest.get("chapters", []))
    locked_by_reference = {row["reference"]: row for row in preflight.get("chapters", [])}
    packets_by_reference = {row["reference"]: row for row in manifest_rows}
    packets_by_id = {row.get("packet_id"): row for row in manifest_rows if row.get("packet_id")}
    expected_by_filename = {
        Path(row["expected_response_path"]).name: row["reference"]
        for row in manifest_rows
    }
    required_references = [row["reference"] for row in manifest_rows]

    raw_root.mkdir(parents=True, exist_ok=True)
    accepted_root.mkdir(parents=True, exist_ok=True)
    rejected_root.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(path for path in raw_root.glob("*.json") if path.is_file())
    parsed: dict[Path, ExternalCommentaryResponse] = {}
    parse_failures: dict[Path, tuple[list[str], list[str]]] = {}
    for path in raw_files:
        envelope, codes, errors = _parse_envelope(path)
        if envelope is None:
            parse_failures[path] = (codes, errors)
        else:
            parsed[path] = envelope

    reference_counts = Counter(value.reference for value in parsed.values())
    packet_counts = Counter(value.packet_id for value in parsed.values())
    protected_errors = _protected_errors(repo_root, V11_STATE)
    timestamp = imported_at or datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for path in raw_files:
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if path in parse_failures:
            codes, errors = parse_failures[path]
            row = _rejected_row(
                path, raw_root, raw_hash, expected_by_filename.get(path.name), codes, errors
            )
        else:
            envelope = parsed[path]
            codes: list[str] = []
            errors: list[str] = []
            if reference_counts[envelope.reference] > 1 or packet_counts[envelope.packet_id] > 1:
                _reject(codes, errors, ExternalResponseRejectionCode.DUPLICATE_RESPONSE, "more than one raw response targets this chapter or packet")
            packet = packets_by_reference.get(envelope.reference)
            locked = locked_by_reference.get(envelope.reference)
            if packet is None or locked is None:
                _reject(codes, errors, ExternalResponseRejectionCode.NON_CANARY_RESPONSE, "response reference is outside the bounded canary set")
            elif envelope.packet_id != packet.get("packet_id"):
                code = ExternalResponseRejectionCode.PACKET_ID_MISMATCH
                if envelope.packet_id not in packets_by_id:
                    code = ExternalResponseRejectionCode.UNKNOWN_PACKET
                _reject(codes, errors, code, "response packet_id does not identify the locked packet for this reference")
            elif packets_by_id.get(envelope.packet_id, {}).get("reference") != envelope.reference:
                _reject(codes, errors, ExternalResponseRejectionCode.REFERENCE_MISMATCH, "packet_id belongs to another canonical reference")
            if packet is not None:
                _verify_envelope_locks(envelope, packet, codes, errors)
                _verify_packet_file(packet, repo_root, codes, errors)
            if protected_errors:
                _reject(codes, errors, ExternalResponseRejectionCode.PROTECTED_ARTIFACT_CHANGED, "protected Commentary v1.1 fingerprints changed")

            if not codes and packet is not None and locked is not None:
                try:
                    row = _validate_and_store(
                        path=path,
                        raw_root=raw_root,
                        raw_hash=raw_hash,
                        envelope=envelope,
                        packet=packet,
                        locked=locked,
                        accepted_root=accepted_root,
                        timestamp=timestamp,
                        bundle_loader=bundle_loader,
                    )
                except Exception as exc:  # isolate failures to one canary
                    _reject(codes, errors, ExternalResponseRejectionCode.INFRASTRUCTURE_ERROR, str(exc))
                    row = _rejected_row(
                        path, raw_root, raw_hash, envelope.reference, codes, errors,
                        structurally_parsed=True,
                    )
            else:
                row = _rejected_row(
                    path, raw_root, raw_hash, envelope.reference, codes, errors,
                    structurally_parsed=True,
                )

        if row["import_status"] == "rejected":
            receipt_path = rejected_root / path.name
            _write_json(receipt_path, {"artifact_version": "commentary-v1.2-rejection-v1", **row})
            row["rejection_path"] = receipt_path.relative_to(repo_root).as_posix() if receipt_path.is_relative_to(repo_root) else str(receipt_path)
        rows.append(row)

    accepted_references = {row["reference"] for row in rows if row["import_status"] == "accepted"}
    responded_references = {
        expected_by_filename[path.name]
        for path in raw_files
        if path.name in expected_by_filename
    }
    responded_references.update(
        value.reference for value in parsed.values() if value.reference in packets_by_reference
    )
    missing = [reference for reference in required_references if reference not in responded_references]
    if not raw_files:
        status = "BLOCKED_BEFORE_PROSE"
    elif missing:
        status = "PARTIAL_RESPONSES"
    elif accepted_references != set(required_references):
        status = "VALIDATION_FAILED"
    else:
        status = "RESPONSES_IMPORTED"

    artifact = {
        "artifact_version": "commentary-v1.2-canary-import-v1",
        "status": status,
        "required_response_count": len(required_references),
        "raw_response_count": len(raw_files),
        "matched_response_count": len(responded_references),
        "accepted_count": sum(row["import_status"] == "accepted" for row in rows),
        "rejected_count": sum(row["import_status"] == "rejected" for row in rows),
        "missing_references": missing,
        "raw_response_directory": _relative_or_text(raw_root, repo_root),
        "accepted_response_directory": _relative_or_text(accepted_root, repo_root),
        "rejected_response_directory": _relative_or_text(rejected_root, repo_root),
        "v1_1_protected_fingerprints_verified": not protected_errors,
        "full_bible_generation_authorized": False,
        "chapters": rows,
    }
    _write_json(import_path, artifact)
    _write_json(
        candidate_root / "candidate-state.json",
        {
            "pipeline_version": "commentary-v1.2-enrichment",
            "current_stage": f"CANARY_{status}",
            "current_gate_state": status,
            "required_renderer": "approved_external_renderer",
            "required_effort": "medium",
            "full_bible_generation_authorized": False,
            "v1_1_mutated": False,
            "ckl_mutated": False,
            "canary_chapter_count": len(required_references),
        },
    )
    return artifact


def _parse_envelope(path: Path) -> tuple[ExternalCommentaryResponse | None, list[str], list[str]]:
    codes: list[str] = []
    errors: list[str] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _reject(codes, errors, ExternalResponseRejectionCode.MALFORMED_RESPONSE_JSON, str(exc))
        return None, codes, errors
    if not isinstance(raw, Mapping):
        _reject(codes, errors, ExternalResponseRejectionCode.MALFORMED_RESPONSE_ENVELOPE, "response envelope must be a JSON object")
        return None, codes, errors
    unknown = sorted(set(raw) - _ENVELOPE_FIELDS)
    if unknown:
        _reject(codes, errors, ExternalResponseRejectionCode.MALFORMED_RESPONSE_ENVELOPE, f"unknown envelope fields: {', '.join(unknown)}")
    missing = sorted(field for field in _ENVELOPE_FIELDS if field not in raw)
    if missing:
        _reject(codes, errors, ExternalResponseRejectionCode.MISSING_REQUIRED_FIELD, f"missing envelope fields: {', '.join(missing)}")
    for field in _ENVELOPE_FIELDS - {"response_payload"}:
        if field in raw and (not isinstance(raw[field], str) or not raw[field].strip()):
            _reject(codes, errors, ExternalResponseRejectionCode.MALFORMED_RESPONSE_ENVELOPE, f"{field} must be non-empty text")
    if "response_payload" in raw and not isinstance(raw["response_payload"], Mapping):
        _reject(codes, errors, ExternalResponseRejectionCode.MALFORMED_COMMENTARY_JSON, "response_payload must be a commentary JSON object")
    if codes:
        return None, list(dict.fromkeys(codes)), errors
    return ExternalCommentaryResponse(**{field: raw[field] for field in _ENVELOPE_FIELDS}), [], []


def _verify_envelope_locks(envelope, packet, codes, errors) -> None:
    checks = (
        ("prompt_version", "commentary_prompt_version", ExternalResponseRejectionCode.PROMPT_VERSION_MISMATCH),
        ("evidence_hash", "evidence_hash", ExternalResponseRejectionCode.EVIDENCE_HASH_MISMATCH),
        ("synthesis_hash", "synthesis_hash", ExternalResponseRejectionCode.SYNTHESIS_HASH_MISMATCH),
    )
    for response_field, packet_field, code in checks:
        if getattr(envelope, response_field) != packet.get(packet_field):
            _reject(codes, errors, code, f"{response_field} does not match the locked packet")
            if code in {
                ExternalResponseRejectionCode.PROMPT_VERSION_MISMATCH,
                ExternalResponseRejectionCode.EVIDENCE_HASH_MISMATCH,
                ExternalResponseRejectionCode.SYNTHESIS_HASH_MISMATCH,
            }:
                _reject(codes, errors, ExternalResponseRejectionCode.STALE_RESPONSE, "response was rendered from stale inputs")


def _verify_packet_file(packet: Mapping[str, Any], repo_root: Path, codes: list[str], errors: list[str]) -> None:
    path = repo_root / str(packet.get("packet_path", ""))
    try:
        value = _read_json(path)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        _reject(codes, errors, ExternalResponseRejectionCode.INFRASTRUCTURE_ERROR, f"cannot read locked prompt packet: {exc}")
        return
    if value.get("packet_id") != packet.get("packet_id") or calculate_packet_id(value) != packet.get("packet_id"):
        _reject(codes, errors, ExternalResponseRejectionCode.PACKET_CONTENT_MISMATCH, "prompt packet content no longer matches packet_id")


def _validate_and_store(*, path, raw_root, raw_hash, envelope, packet, locked, accepted_root, timestamp, bundle_loader):
    codes: list[str] = []
    errors: list[str] = []
    bundle = bundle_loader(
        locked["book"], locked["chapter"],
        evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    if bundle is None:
        raise RuntimeError("unable to rebuild locked EvidenceBundle")
    synthesis = compile_chapter_synthesis(bundle, book=locked["book"], chapter=locked["chapter"])
    synthesis_errors = list(validate_synthesis(synthesis, bundle))
    if synthesis_errors:
        raise RuntimeError("compiled synthesis failed validation: " + "; ".join(synthesis_errors))
    if bundle.evidence_hash != locked["evidence_hash"] or bundle.evidence_hash != packet["evidence_hash"]:
        _reject(codes, errors, ExternalResponseRejectionCode.EVIDENCE_HASH_MISMATCH, "rebuilt evidence does not match the locked packet")
        _reject(codes, errors, ExternalResponseRejectionCode.STALE_RESPONSE, "locked evidence changed after packet creation")
    if synthesis.synthesis_hash != locked["synthesis_hash"] or synthesis.synthesis_hash != packet["synthesis_hash"]:
        _reject(codes, errors, ExternalResponseRejectionCode.SYNTHESIS_HASH_MISMATCH, "rebuilt synthesis does not match the locked packet")
        _reject(codes, errors, ExternalResponseRejectionCode.STALE_RESPONSE, "locked synthesis changed after packet creation")
    payload = dict(envelope.response_payload)
    if payload.get("reference") != locked["reference"] or payload.get("book") != locked["book"] or payload.get("chapter") != locked["chapter"]:
        _reject(codes, errors, ExternalResponseRejectionCode.REFERENCE_MISMATCH, "commentary payload canonical identity does not match the packet")
    if codes:
        return _rejected_row(
            path, raw_root, raw_hash, envelope.reference, codes, errors,
            structurally_parsed=True,
        )

    candidate_id = _candidate_id(envelope.packet_id, raw_hash)
    metadata = {
        "evidence_hash": bundle.evidence_hash,
        "evidence_bundle_version": bundle.version,
        "synthesis_hash": synthesis.synthesis_hash,
        "synthesis_schema_version": synthesis.synthesis_schema_version,
        "synthesis_compiler_version": synthesis.synthesis_compiler_version,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "model": "external-renderer",
        "renderer_label": envelope.renderer_label,
        "generated_timestamp": timestamp,
        "imported_timestamp": timestamp,
        "candidate_id": candidate_id,
    }
    # These fields are application-owned even if an external renderer supplied values.
    payload["generated_metadata"] = metadata
    payload["evidence_availability"] = classify_evidence_availability(bundle).value
    payload["status"] = CommentaryStatus.PENDING.value
    result = validate_chapter_commentary(
        payload,
        bundle,
        expected_evidence_hash=bundle.evidence_hash,
        expected_prompt_version=COMMENTARY_PROMPT_VERSION,
        expected_reference=locked["reference"],
        expected_book=locked["book"],
        expected_chapter=locked["chapter"],
        synthesis=synthesis,
        expected_synthesis_hash=synthesis.synthesis_hash,
    )
    if not result.valid or result.commentary is None:
        _reject(codes, errors, ExternalResponseRejectionCode.VALIDATION_FAILED, "Commentary v1.2 validation rejected the response")
        errors.extend(result.errors)
        codes.extend(_validation_codes(result))
        return _rejected_row(
            path, raw_root, raw_hash, envelope.reference,
            list(dict.fromkeys(codes)), errors, structurally_parsed=True,
        )

    accepted = ChapterCommentary(
        reference=result.commentary.reference,
        book=result.commentary.book,
        chapter=result.commentary.chapter,
        status=CommentaryStatus.VALIDATED.value,
        evidence_availability=result.commentary.evidence_availability,
        sections=list(result.accepted_sections),
        generated_metadata=result.commentary.generated_metadata,
        validation_errors=[],
        validation_warnings=[],
    )
    accepted_path = save_commentary(accepted, accepted_root)
    return {
        "reference": envelope.reference,
        "packet_id": envelope.packet_id,
        "raw_path": _relative_or_text(path, ROOT),
        "raw_sha256": raw_hash,
        "import_status": "accepted",
        "structurally_parsed": True,
        "validation_status": "validated",
        "candidate_id": candidate_id,
        "accepted_path": _relative_or_text(accepted_path, ROOT),
        "rejection_codes": [],
        "validation_errors": [],
    }


def _validation_codes(result) -> list[str]:
    codes: list[str] = []
    for section in result.section_results:
        codes.extend(section.reason_codes)
        for block in section.block_results:
            codes.extend(block.reason_codes)
    for error in result.errors:
        prefix = error.split(":", 1)[0]
        if prefix.isupper() and " " not in prefix:
            codes.append(prefix)
    return list(dict.fromkeys(codes))


def _rejected_row(
    path, raw_root, raw_hash, reference, codes, errors, *, structurally_parsed=False
) -> dict[str, Any]:
    return {
        "reference": reference,
        "packet_id": None,
        "raw_path": _relative_or_text(path, ROOT),
        "raw_sha256": raw_hash,
        "import_status": "rejected",
        "structurally_parsed": structurally_parsed,
        "validation_status": "rejected",
        "candidate_id": None,
        "accepted_path": None,
        "rejection_codes": list(dict.fromkeys(codes)),
        "validation_errors": errors,
    }


def _candidate_id(packet_id: str, raw_hash: str) -> str:
    digest = hashlib.sha256(f"{packet_id}\0{raw_hash}".encode("utf-8")).hexdigest()
    return f"commentary-v1.2-candidate:{digest}"


def _protected_errors(repo_root: Path, state_path: Path) -> list[str]:
    if repo_root == ROOT and state_path == V11_STATE:
        return _protected_v11_errors()
    state = _read_json(state_path)
    errors = []
    for relative, expected in state.get("protected_fingerprints", {}).items():
        path = repo_root / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            errors.append(relative)
    return errors


def _reject(codes: list[str], errors: list[str], code: ExternalResponseRejectionCode, message: str) -> None:
    codes.append(code.value)
    errors.append(f"{code.value}: {message}")


def _relative_or_text(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", nargs="?", type=Path, default=RAW_RESPONSE_ROOT)
    args = parser.parse_args(argv)
    result = import_responses(args.input_dir)
    print(json.dumps({key: result[key] for key in (
        "status", "required_response_count", "raw_response_count",
        "accepted_count", "rejected_count", "missing_references",
    )}, indent=2))
    return 0 if result["status"] in {"BLOCKED_BEFORE_PROSE", "PARTIAL_RESPONSES", "RESPONSES_IMPORTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
