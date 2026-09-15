#!/usr/bin/env python3
"""Exchange frozen Commentary production packets with an external renderer.

This tool intentionally has no model client.  It exports byte-for-byte copies
of the immutable production packets, imports one complete response bundle into
an isolated qualification namespace, and evaluates it with the frozen
validator and Gate v2.1 semantics.  It never writes production artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.models import GeneratedMetadata
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    ManifestError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)


SOURCE_RUN = "run-04109d5ff664ed80"
CANDIDATE_RENDERER = "gpt-5.6-sol"
ARTIFACT_VERSION = "commentary-renderer-qualification-v1"
RESPONSE_MANIFEST_VERSION = "commentary-renderer-qualification-response-manifest-v1"
EXPECTED_REFERENCES = (
    "Exodus 14", "Leviticus 8", "Numbers 36", "Deuteronomy 10", "Ruth 2",
    "2 Samuel 15", "Ezra 8", "Nehemiah 7", "Job 1", "Isaiah 13", "Amos 2",
    "Matthew 4", "Matthew 19", "Matthew 20", "Romans 3", "1 Corinthians 14",
    "Hebrews 8", "Revelation 4", "Revelation 19", "Revelation 20", "Revelation 21",
)
EXCLUDED_DATA_GAP_REFERENCES = ("2 Kings 11", "Psalms 30", "Psalms 105", "Ezekiel 12")
GENERATION_INSTRUCTIONS = """Process packets in manifest order.
Use each packet's exact system_prompt and user_prompt.
Return one raw JSON response per packet.
Do not use web or external sources.
Do not add Markdown fences.
Do not alter packet content.
"""


class QualificationError(RuntimeError):
    """The external exchange is incomplete, altered, or internally inconsistent."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationError(f"invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"JSON artifact must be an object: {path}")
    return value


def _root(repo_root: Path, qualification_root: Path | None = None) -> Path:
    return qualification_root or repo_root / ".bhf-data/bhf-commentary-candidates/renderer-qualification-v1/gpt-5.6-sol"


def _source_root(repo_root: Path) -> Path:
    return repo_root / ".bhf-data/bhf-commentary-production/v1/runs" / SOURCE_RUN


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_json_immutable(path: Path, value: Any) -> str:
    return write_immutable(path, _json_bytes(value))


def _qualification_id(source_manifest_identity: str) -> str:
    digest = hashlib.sha256(
        f"{ARTIFACT_VERSION}\0{CANDIDATE_RENDERER}\0{SOURCE_RUN}\0{source_manifest_identity}".encode("utf-8")
    ).hexdigest()[:20]
    return f"renderer-qualification-v1-{CANDIDATE_RENDERER}-{digest}"


def _packet_content_hash(packet: dict[str, Any]) -> str:
    # inputs.prepare_chapter defines packet_hash before execution provenance
    # (run_id, batch_id, packet_id, packet_hash) is added.
    excluded = {"run_id", "batch_id", "packet_id", "packet_hash"}
    return sha256_json({key: value for key, value in packet.items() if key not in excluded})


def _source_context(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = _source_root(repo_root)
    manifest = _read(source / "manifest.json")
    handoff = _read(source / "handoff/manifest.json")
    if manifest.get("run_id") != SOURCE_RUN:
        raise QualificationError("source production manifest run identity mismatch")
    if handoff.get("run_id") != SOURCE_RUN:
        raise QualificationError("source production handoff run identity mismatch")
    if handoff.get("manifest_identity") != manifest.get("manifest_identity"):
        raise QualificationError("source production handoff/manifest identity mismatch")
    by_reference = {row.get("reference"): row for row in manifest.get("chapters", [])}
    if set(EXPECTED_REFERENCES).difference(by_reference):
        raise QualificationError("source production manifest is missing a qualification chapter")
    if any(by_reference[reference].get("evidence_availability") == "DATA_GAP" for reference in EXPECTED_REFERENCES):
        raise QualificationError("renderer qualification contains a DATA_GAP chapter")
    if any(by_reference.get(reference, {}).get("evidence_availability") != "DATA_GAP" for reference in EXCLUDED_DATA_GAP_REFERENCES):
        raise QualificationError("expected true DATA_GAP exclusion no longer matches source manifest")
    return manifest, handoff, by_reference


def build_qualification_manifest(repo_root: Path = ROOT) -> dict[str, Any]:
    """Read and verify only frozen production packet inputs; make no writes."""

    manifest, handoff, by_reference = _source_context(repo_root)
    handoff_by_reference = {row.get("reference"): row for row in handoff.get("items", [])}
    rows: list[dict[str, Any]] = []
    for ordinal, reference in enumerate(EXPECTED_REFERENCES, 1):
        chapter = by_reference[reference]
        item = handoff_by_reference.get(reference)
        if not item:
            raise QualificationError(f"source handoff lacks renderer packet for {reference}")
        relative_packet = str(chapter["expected_artifacts"]["packet"])
        packet_path = repo_root / ".bhf-data/bhf-commentary-production/v1" / relative_packet
        raw = packet_path.read_bytes()
        packet = _read(packet_path)
        packet_sha256 = sha256_bytes(raw)
        expected_packet_hash = str(chapter["packet_hash"])
        if packet.get("packet_id") != chapter.get("packet_id") or packet.get("packet_hash") != expected_packet_hash:
            raise QualificationError(f"packet identity mismatch for {reference}")
        if _packet_content_hash(packet) != expected_packet_hash:
            raise QualificationError(f"packet content hash mismatch for {reference}")
        if item.get("packet_id") != chapter.get("packet_id") or item.get("packet_hash") != expected_packet_hash:
            raise QualificationError(f"handoff packet identity mismatch for {reference}")
        if item.get("packet_sha256") != packet_sha256:
            raise QualificationError(f"handoff packet file SHA-256 mismatch for {reference}")
        filename = f"{ordinal:03d}_{slug(chapter['book'], chapter['chapter'])}.json"
        rows.append({
            "ordinal": ordinal,
            "reference": reference,
            "book": chapter["book"],
            "chapter": chapter["chapter"],
            "evidence_availability": chapter["evidence_availability"],
            "source_packet_path": (Path(".bhf-data/bhf-commentary-production/v1") / relative_packet).as_posix(),
            "packet_filename": filename,
            "response_filename": filename,
            "packet_id": chapter["packet_id"],
            "packet_hash": expected_packet_hash,
            "packet_file_sha256": packet_sha256,
        })
    result = {
        "artifact_version": ARTIFACT_VERSION,
        "qualification_id": _qualification_id(str(manifest["manifest_identity"])),
        "candidate_renderer_identity": CANDIDATE_RENDERER,
        "source_production_run": SOURCE_RUN,
        "source_manifest_identity": manifest["manifest_identity"],
        "source_handoff_identity": handoff["handoff_identity"],
        "contract_versions": {
            "commentary_prompt_version": "1.5",
            "commentary_schema_version": "1.2",
            "synthesis_schema_version": "1.1",
            "synthesis_compiler_version": "1.1",
            "gate_version": "commentary-richness-gate-v2.1",
        },
        "generation_authorized": False,
        "dense_reader_authorized": False,
        "chapters": rows,
    }
    result["qualification_manifest_identity"] = sha256_json(result)
    return result


def _verify_qualification_manifest(manifest: dict[str, Any]) -> None:
    identity = manifest.get("qualification_manifest_identity")
    expected = sha256_json({key: value for key, value in manifest.items() if key != "qualification_manifest_identity"})
    if identity != expected:
        raise QualificationError("qualification manifest identity mismatch")
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise QualificationError("unsupported qualification artifact version")
    if manifest.get("candidate_renderer_identity") != CANDIDATE_RENDERER:
        raise QualificationError("candidate renderer identity mismatch")
    if manifest.get("source_production_run") != SOURCE_RUN:
        raise QualificationError("source production run mismatch")
    rows = manifest.get("chapters")
    if not isinstance(rows, list) or [row.get("reference") for row in rows] != list(EXPECTED_REFERENCES):
        raise QualificationError("qualification chapter order or membership mismatch")
    if len(rows) != 21 or any(row.get("reference") in EXCLUDED_DATA_GAP_REFERENCES for row in rows):
        raise QualificationError("qualification DATA_GAP exclusion mismatch")


def _zip_write(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    # Fixed timestamp and permissions make byte-for-byte repeated exports stable.
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content)


def export_bundle(*, repo_root: Path = ROOT, qualification_root: Path | None = None) -> dict[str, Any]:
    """Create the portable generation bundle, without reading baseline outputs."""

    root = _root(repo_root, qualification_root)
    manifest = build_qualification_manifest(repo_root)
    _verify_qualification_manifest(manifest)
    manifest_path = root / "qualification-manifest.json"
    _write_json_immutable(manifest_path, manifest)
    zip_path = root / "renderer-qualification-gpt-5.6-sol-input.zip"
    members = ["manifest.json", "GENERATION_INSTRUCTIONS.txt"] + [f"packets/{row['packet_filename']}" for row in manifest["chapters"]]
    from io import BytesIO
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _zip_write(archive, "manifest.json", _json_bytes(manifest))
        _zip_write(archive, "GENERATION_INSTRUCTIONS.txt", GENERATION_INSTRUCTIONS.encode("utf-8"))
        for row in manifest["chapters"]:
            source = repo_root / row["source_packet_path"]
            raw = source.read_bytes()
            if sha256_bytes(raw) != row["packet_file_sha256"]:
                raise QualificationError(f"source packet changed during export: {row['reference']}")
            _zip_write(archive, f"packets/{row['packet_filename']}", raw)
    write_immutable(zip_path, stream.getvalue())
    return {
        "status": "EXPORTED",
        "qualification_id": manifest["qualification_id"],
        "zip_path": str(zip_path),
        "file_count": len(members),
        "packet_count": len(manifest["chapters"]),
        "packet_sha256_verified": True,
        "baseline_outputs_included": False,
    }


def response_manifest_template(*, repo_root: Path = ROOT, qualification_root: Path | None = None) -> dict[str, Any]:
    """Return the response manifest that must accompany external raw JSON."""

    root = _root(repo_root, qualification_root)
    manifest = _read(root / "qualification-manifest.json")
    _verify_qualification_manifest(manifest)
    return {
        "artifact_version": RESPONSE_MANIFEST_VERSION,
        "qualification_id": manifest["qualification_id"],
        "candidate_renderer_identity": CANDIDATE_RENDERER,
        "responses": [
            {
                "ordinal": row["ordinal"],
                "reference": row["reference"],
                "packet_id": row["packet_id"],
                "packet_hash": row["packet_hash"],
                "response_filename": row["response_filename"],
            }
            for row in manifest["chapters"]
        ],
    }


def _read_zip(bundle: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    try:
        with zipfile.ZipFile(bundle) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise QualificationError("response bundle contains duplicate ZIP members")
            files = {name: archive.read(name) for name in names}
    except (OSError, zipfile.BadZipFile) as exc:
        raise QualificationError(f"invalid response bundle: {exc}") from exc
    if "manifest.json" not in files:
        raise QualificationError("response bundle lacks manifest.json")
    try:
        response_manifest = json.loads(files["manifest.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"invalid response manifest JSON: {exc}") from exc
    if not isinstance(response_manifest, dict):
        raise QualificationError("response manifest must be an object")
    return files, response_manifest


def _verify_response_bundle(files: dict[str, bytes], response_manifest: dict[str, Any], qualification: dict[str, Any]) -> list[dict[str, Any]]:
    if response_manifest.get("artifact_version") != RESPONSE_MANIFEST_VERSION:
        raise QualificationError("response manifest artifact version mismatch")
    if response_manifest.get("qualification_id") != qualification["qualification_id"]:
        raise QualificationError("response manifest qualification ID mismatch")
    if response_manifest.get("candidate_renderer_identity") != CANDIDATE_RENDERER:
        raise QualificationError("response manifest candidate renderer identity mismatch")
    responses = response_manifest.get("responses")
    expected = qualification["chapters"]
    if not isinstance(responses, list) or len(responses) != len(expected):
        raise QualificationError("response manifest must contain exactly 21 responses")
    expected_names = {"manifest.json"} | {f"responses/{row['response_filename']}" for row in expected}
    actual_names = set(files)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise QualificationError(f"response bundle filenames mismatch; missing={missing}; extra={extra}")
    for packet, response in zip(expected, responses, strict=True):
        required = {
            "ordinal": packet["ordinal"], "reference": packet["reference"],
            "packet_id": packet["packet_id"], "packet_hash": packet["packet_hash"],
            "response_filename": packet["response_filename"],
        }
        if not isinstance(response, dict) or any(response.get(key) != value for key, value in required.items()):
            raise QualificationError(f"response manifest packet identity mismatch for {packet['reference']}")
    return expected


def import_bundle(bundle: Path, *, repo_root: Path = ROOT, qualification_root: Path | None = None) -> dict[str, Any]:
    """Immutably import exactly one response for every locked packet."""

    root = _root(repo_root, qualification_root)
    qualification = _read(root / "qualification-manifest.json")
    _verify_qualification_manifest(qualification)
    files, response_manifest = _read_zip(Path(bundle))
    rows = _verify_response_bundle(files, response_manifest, qualification)
    response_manifest_path = root / "responses/response-manifest.json"
    write_immutable(response_manifest_path, files["manifest.json"])
    imported = []
    for row in rows:
        filename = row["response_filename"]
        raw = files[f"responses/{filename}"]
        raw_path = root / "responses/raw" / filename
        digest = write_immutable(raw_path, raw)
        imported.append({
            "reference": row["reference"], "response_filename": filename,
            "packet_id": row["packet_id"], "packet_hash": row["packet_hash"],
            "raw_path": raw_path.relative_to(root).as_posix(), "raw_sha256": digest,
        })
    receipt = {
        "artifact_version": "commentary-renderer-qualification-import-v1",
        "qualification_id": qualification["qualification_id"],
        "candidate_renderer_identity": CANDIDATE_RENDERER,
        "response_manifest_sha256": sha256_bytes(files["manifest.json"]),
        "response_count": len(imported),
        "responses": imported,
        "raw_responses_immutable": True,
    }
    _write_json_immutable(root / "responses/import-receipt.json", receipt)
    return {"status": "IMPORTED", "qualification_id": qualification["qualification_id"], "response_count": len(imported), "raw_responses_immutable": True}


def _codes(errors: Iterable[str]) -> list[str]:
    values = []
    for error in errors:
        code = str(error).split(":", 1)[0].strip()
        if code.isupper() and " " not in code:
            values.append(code)
    return sorted(set(values))


def _safe_gate(score, audit: dict[str, Any], availability: str):
    safety = {name: True for name in (
        "validation_clean", "provenance_complete", "hashes_valid", "chapter_boundaries_valid",
        "confidence_valid", "dispute_state_preserved", "unsupported_significance_absent",
    )}
    return assess_gate_v2(
        score=score, evidence_availability=availability,
        baseline_richness="SYNTHESIS_GAP" if availability == "AVAILABLE" else "EVIDENCE_GAP",
        after_richness=audit["richness_status"], safety_checks=safety,
        evidence_use_delta=audit["unique_evidence_ids_consumed"], section_delta=audit["section_count"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )


def _empty_metrics(row: dict[str, Any], codes: list[str]) -> dict[str, Any]:
    return {
        "reference": row["reference"], "validation_status": "rejected", "structural_result": "REJECTED",
        "rejection_codes": codes, "weighted_coverage": None, "core_coverage": None,
        "synthesis_utilization": None, "category_coverage": None, "dump_severity": None,
        "word_count": None, "block_count": None, "gate_v2_1": None,
    }


def _evaluate_one(row: dict[str, Any], raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"])
    if not isinstance(payload, dict):
        return _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"])
    prepared = prepare_chapter(row["book"], int(row["chapter"]))
    identity = prepared.row["input_identity"]
    for key in ("packet_id", "packet_hash"):
        if identity.get(key) != row.get(key):
            return _empty_metrics(row, ["FROZEN_INPUT_IDENTITY_MISMATCH"])
    payload = dict(payload)
    payload["generated_metadata"] = GeneratedMetadata(
        evidence_hash=prepared.bundle.evidence_hash, evidence_bundle_version=prepared.bundle.version,
        commentary_schema_version="1.2", commentary_prompt_version="1.5", model="external_handoff",
        generated_timestamp=None, synthesis_hash=prepared.synthesis.synthesis_hash,
        synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
        synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        renderer_label=CANDIDATE_RENDERER,
    ).to_dict()
    payload["evidence_availability"] = prepared.synthesis.evidence_availability
    payload["status"] = "pending"
    validation = validate_chapter_commentary(
        payload, prepared.bundle, expected_evidence_hash=prepared.bundle.evidence_hash,
        expected_prompt_version="1.5", expected_reference=row["reference"], expected_book=row["book"],
        expected_chapter=int(row["chapter"]), synthesis=prepared.synthesis,
        expected_synthesis_hash=prepared.synthesis.synthesis_hash,
    )
    if not validation.valid or validation.commentary is None:
        return _empty_metrics(row, _codes(validation.errors) or ["VALIDATION_FAILED"])
    blocks = [block for section in validation.commentary.sections for block in section.blocks]
    audit = audit_chapter(row["book"], int(row["chapter"]), validation.commentary, prepared.bundle)
    score = score_synthesis_richness(
        prepared.synthesis.synthesis_units, evidence_items=prepared.bundle.evidence_items,
        consumed_synthesis_ids=[sid for block in blocks for sid in block.synthesis_ids], blocks=blocks,
        passage_ref=row["reference"], core_classifier=CORE_CLASSIFIER_V2,
    )
    gate = _safe_gate(score, audit, prepared.synthesis.evidence_availability)
    return {
        "reference": row["reference"], "validation_status": "validated", "structural_result": "ACCEPTED",
        "rejection_codes": [], "weighted_coverage": score.weighted_idea_coverage,
        "core_coverage": score.core_cluster_coverage, "synthesis_utilization": score.raw_synthesis_coverage,
        "category_coverage": score.category_coverage, "dump_severity": score.dump_diagnostics.severity,
        "word_count": audit["commentary_prose_word_count"], "block_count": audit["commentary_block_count"],
        "gate_v2_1": gate.to_dict(), "score": score.to_dict(), "audit": audit,
    }


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    return round(sum(values) / len(values), 4) if values else None


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["validation_status"] == "validated"]
    evidence_bearing = [row for row in valid if row.get("evidence_availability") == "AVAILABLE"]
    return {
        "renderer_chapters": len(rows), "structurally_valid": len(valid), "structural_rejections": len(rows) - len(valid),
        "structural_rejection_codes": dict(Counter(code for row in rows for code in row["rejection_codes"])),
        "quality_fail": sum(row.get("gate_v2_1", {}).get("outcome") == "QUALITY_FAIL" for row in valid),
        "high_dump": sum(row.get("dump_severity") == "HIGH" for row in valid),
        "evidence_bearing_valid_chapters": len(evidence_bearing),
        "weighted_coverage": _mean(evidence_bearing, "weighted_coverage"),
        "core_coverage": _mean(evidence_bearing, "core_coverage"),
        "synthesis_utilization": _mean(evidence_bearing, "synthesis_utilization"),
        "category_coverage": _mean(evidence_bearing, "category_coverage"),
        "gate_distribution": dict(Counter(row.get("gate_v2_1", {}).get("outcome") for row in valid)),
        "dump_distribution": dict(Counter(row["dump_severity"] for row in valid)),
    }


def _baseline_rows(repo_root: Path) -> list[dict[str, Any]]:
    """Read production only during A/B comparison, never during export."""

    manifest, _, by_reference = _source_context(repo_root)
    state = _read(_source_root(repo_root) / "batches/batch-001/state.json")
    result = []
    for reference in EXPECTED_REFERENCES:
        chapter = by_reference[reference]
        record = state["chapters"][reference]
        gate_value = None
        if record.get("gate_path"):
            gate_value = _read(repo_root / record["gate_path"])
        rejection_codes: list[str] = []
        if record.get("historical_quarantines"):
            rejection_codes.extend(
                code for quarantine in record["historical_quarantines"]
                for code in quarantine.get("rejection_codes", [])
            )
        if record.get("state") == "QUARANTINED" and record.get("gate_status") is None:
            quarantine_path = chapter["expected_artifacts"]["quarantine"]
            rejection_codes.extend(_read(repo_root / ".bhf-data/bhf-commentary-production/v1" / quarantine_path).get("rejection_codes", []))
        score = (gate_value or {}).get("score", {})
        audit = (gate_value or {}).get("audit", {})
        accepted = bool(record.get("accepted_path"))
        result.append({
            "reference": reference,
            "structural_result": "ACCEPTED" if accepted else "REJECTED",
            "rejection_codes": sorted(set(rejection_codes)),
            "weighted_coverage": score.get("weighted_idea_coverage"),
            "core_coverage": score.get("core_cluster_coverage"),
            "synthesis_utilization": score.get("raw_synthesis_coverage"),
            "category_coverage": score.get("category_coverage"),
            "dump_severity": (score.get("dump_diagnostics") or {}).get("severity"),
            "word_count": audit.get("commentary_prose_word_count"),
            "block_count": audit.get("commentary_block_count"),
            "gate_v2_1": (gate_value or {}).get("assessment"),
        })
    return result


def evaluate(*, repo_root: Path = ROOT, qualification_root: Path | None = None) -> dict[str, Any]:
    """Validate imported raw bytes, without reader generation or production writes."""

    root = _root(repo_root, qualification_root)
    qualification = _read(root / "qualification-manifest.json")
    _verify_qualification_manifest(qualification)
    # Refuse to score a response if any source packet has changed since the
    # frozen exchange was made.  This is a read-only re-verification.
    current = build_qualification_manifest(repo_root)
    if current != qualification:
        raise QualificationError("frozen source packet or qualification identity changed before evaluation")
    receipt = _read(root / "responses/import-receipt.json")
    if receipt.get("qualification_id") != qualification["qualification_id"] or receipt.get("response_count") != 21:
        raise QualificationError("qualification response import is absent or mismatched")
    rows = []
    for chapter in qualification["chapters"]:
        raw_path = root / "responses/raw" / chapter["response_filename"]
        if not raw_path.is_file():
            raise QualificationError(f"missing immutable imported response: {chapter['reference']}")
        result = _evaluate_one(chapter, raw_path.read_bytes())
        result["evidence_availability"] = chapter["evidence_availability"]
        result["packet_id"] = chapter["packet_id"]
        result["packet_hash"] = chapter["packet_hash"]
        result["raw_sha256"] = sha256_bytes(raw_path.read_bytes())
        rows.append(result)
    candidate = _aggregate(rows)
    baseline_rows = _baseline_rows(repo_root)
    baseline = {
        "renderer_chapters": 21, "hard_content_provenance_rejects": 2, "structurally_accepted": 19,
        "quality_fail": 7, "weighted_coverage": 0.4024, "core_coverage": 0.9,
        "synthesis_utilization": 0.2268,
    }
    historical_pilot = {
        "structural_validity": "59/60", "quality_fail": 2, "weighted_coverage": 0.8249,
        "core_coverage": 0.9915, "synthesis_utilization": 0.8258,
    }
    hard_codes = {"UNKNOWN_EVIDENCE_ID", "SYNTHESIS_ANCESTRY_MISMATCH", "CONFIDENCE_EXCEEDS_EVIDENCE"}
    rejection_counts = Counter(code for row in rows for code in row["rejection_codes"])
    qualification_pass = (
        not any(rejection_counts[code] for code in hard_codes)
        and candidate["structural_rejections"] == 0
        and candidate["core_coverage"] is not None and candidate["core_coverage"] >= 0.98
        and candidate["weighted_coverage"] is not None and candidate["weighted_coverage"] >= 0.75
        and candidate["synthesis_utilization"] is not None and candidate["synthesis_utilization"] >= 0.70
        and candidate["high_dump"] == 0 and candidate["quality_fail"] <= 2
        and not any(count > 1 for code, count in rejection_counts.items())
    )
    report = {
        "artifact_version": "commentary-renderer-qualification-evaluation-v1",
        "qualification_id": qualification["qualification_id"], "candidate_renderer_identity": CANDIDATE_RENDERER,
        "source_production_run": SOURCE_RUN, "dense_reader_applied": False,
        "frozen_contracts": qualification["contract_versions"], "chapters": rows,
        "chapter_comparison": [
            {"reference": candidate_row["reference"], "codex_gpt_5": baseline_row, "gpt_5_6_sol": candidate_row}
            for baseline_row, candidate_row in zip(baseline_rows, rows, strict=True)
        ],
        "comparison": {"codex_gpt_5": baseline, "historical_commentary_1_5_pilot": historical_pilot, "gpt_5_6_sol": candidate},
        "thresholds": {"core_coverage_min": 0.98, "weighted_coverage_min": 0.75, "synthesis_utilization_min": 0.70, "high_dump_max": 0, "quality_fail_max": 2},
        "qualification_result": "QUALIFIED" if qualification_pass else "NOT_QUALIFIED",
    }
    _write_json_immutable(root / "evaluation/evaluation.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("export", help="export the 21 frozen packets; makes no model call")
    template = sub.add_parser("response-template", help="print the required return manifest")
    imported = sub.add_parser("import", help="immutably import one complete response bundle")
    imported.add_argument("--bundle", type=Path, required=True)
    sub.add_parser("evaluate", help="validate and compare imported raw responses; no reader")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            output = export_bundle(qualification_root=args.qualification_root)
        elif args.command == "response-template":
            output = response_manifest_template(qualification_root=args.qualification_root)
        elif args.command == "import":
            output = import_bundle(args.bundle, qualification_root=args.qualification_root)
        else:
            output = evaluate(qualification_root=args.qualification_root)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (QualificationError, ManifestError, ArtifactCollisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
