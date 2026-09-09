#!/usr/bin/env python3
"""Freeze and evaluate the prompt 1.6 Commentary renderer qualification.

The harness deliberately has no model client.  It creates a fresh, immutable
21-chapter GPT-5.6 Sol request bundle, accepts exactly one externally rendered
response for every frozen packet, and evaluates those bytes with the existing
validator, v3 reader-relevance scoring contract, and Gate v2.1.  It never
mutates production, CKL, the historical qualification, or the scoring
remediation namespace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    GeneratedMetadata,
)
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    assess_gate_v2,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from framework.commentary.production.models import (
    ArtifactCollisionError,
    ManifestError,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from framework.commentary.production.inputs import prepare_chapter
from tools import commentary_renderer_qualification as historical_qualification


ARTIFACT_VERSION = "commentary-renderer-qualification-v2"
PACKET_VERSION = "commentary-renderer-qualification-v2-packet-v1"
HANDOFF_VERSION = "commentary-renderer-qualification-v2-handoff-v1"
RESPONSE_MANIFEST_VERSION = "commentary-renderer-qualification-v2-response-manifest-v1"
IMPORT_VERSION = "commentary-renderer-qualification-v2-import-v1"
PARSED_VERSION = "commentary-renderer-qualification-v2-parsed-output-v1"
EVALUATION_VERSION = "commentary-renderer-qualification-v2-evaluation-v1"
CHECKSUM_VERSION = "commentary-renderer-qualification-v2-checksums-v1"

PREVIOUS_QUALIFICATION_ID = "renderer-qualification-v1-gpt-5.6-sol-a0f4063638cf9730958a"
HISTORICAL_QUALIFICATION_ROOT = (
    ROOT / ".bhf-data/bhf-commentary-candidates/renderer-qualification-v1/gpt-5.6-sol"
)
SCORING_REMEDIATION_ROOT = (
    ROOT / ".bhf-data/bhf-commentary-candidates/richness-scoring-remediation-v1"
)
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
PROMPT_VERSION = COMMENTARY_RENDERER_REMEDIATION_PROMPT_VERSION

EXPECTED_REFERENCES = historical_qualification.EXPECTED_REFERENCES
EXCLUDED_DATA_GAP_REFERENCES = historical_qualification.EXCLUDED_DATA_GAP_REFERENCES

FROZEN_CONTRACTS = {
    "renderer_prompt_version": PROMPT_VERSION,
    "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
    "synthesis_schema_version": "1.1",
    "synthesis_compiler_version": "1.1",
    "core_classifier_version": CORE_CLASSIFIER_V2,
    "reader_relevance_eligibility_classifier_version": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    "richness_clustering_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    "richness_policy_version": RICHNESS_POLICY_VERSION_V3,
    "gate_version": RICHNESS_GATE_V2_VERSION,
}

# These are the accepted qualification thresholds.  The v3 scorer supplies
# ``idea_cluster_coverage`` as the reader-facing eligible-idea utilization
# metric; raw unit coverage is retained only as a diagnostic.
QUALIFICATION_THRESHOLDS = {
    "core_coverage_min": 1.0,
    "reader_relevance_weighted_coverage_min": 0.75,
    "eligible_idea_utilization_min": 0.70,
    "high_dump_max": 0,
    "quality_fail_max": 2,
    "category_coverage_min_per_chapter": 1.0,
}

HARD_PROVENANCE_CODES = frozenset(
    {
        "UNKNOWN_EVIDENCE_ID",
        "UNKNOWN_SYNTHESIS_ID",
        "SYNTHESIS_ANCESTRY_MISMATCH",
        "SYNTHESIS_HASH_MISMATCH",
        "CONFIDENCE_EXCEEDS_EVIDENCE",
        "DISPUTED_AS_FACT",
        "INVENTED_SIGNIFICANCE",
        "UNSUPPORTED_DATE",
        "UNSUPPORTED_ENTITY",
        "UNANCHORED_CLAIM",
        "OUT_OF_CHAPTER_SYNTHESIS_REFERENCE",
    }
)

GENERATION_INSTRUCTIONS = """Process packets in manifest order.
Use each packet's exact system_prompt and user_prompt without modification.
Renderer identity: gpt-5.6-sol.
Renderer effort: medium.
Renderer prompt contract: 1.6.
Return one raw JSON chapter-commentary object per packet.
Do not use web or external sources.
Do not add Markdown fences, envelopes, commentary, or explanations around a response.
Do not alter packet content or synthesize evidence not present in the packet.
After rendering, return a response bundle containing manifest.json and exactly
one responses/<response_filename> member for each manifest row.  Use the
response manifest template supplied by the qualification harness; preserve
packet_id, packet_hash, ordinal, and response_filename exactly.
"""


class QualificationError(RuntimeError):
    """The frozen exchange is incomplete, altered, or internally inconsistent."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationError(f"invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"JSON artifact must be an object: {path}")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_json_immutable(path: Path, value: Any) -> str:
    return write_immutable(path, _json_bytes(value))


def _source_manifest(repo_root: Path) -> dict[str, Any]:
    historical_path = repo_root / HISTORICAL_QUALIFICATION_ROOT.relative_to(ROOT) / "qualification-manifest.json"
    historical = _read(historical_path)
    historical_qualification._verify_qualification_manifest(historical)
    if historical.get("qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise QualificationError("historical qualification ID mismatch")
    current = historical_qualification.build_qualification_manifest(repo_root)
    if current != historical:
        raise QualificationError(
            "historical frozen corpus changed: source packets no longer match the immutable qualification manifest"
        )
    return historical


def _scoring_baseline(repo_root: Path) -> tuple[dict[str, Any], str]:
    path = repo_root / SCORING_REMEDIATION_ROOT.relative_to(ROOT) / "evaluation/counterfactual-rescore-v3.json"
    baseline = _read(path)
    contracts = baseline.get("contracts")
    expected = {
        "new_core_classifier_version": CORE_CLASSIFIER_V2,
        "new_richness_policy_version": RICHNESS_POLICY_VERSION_V3,
        "coverage_eligibility_classifier_version": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "gate_behavior_changed": False,
    }
    if not isinstance(contracts, dict) or any(contracts.get(key) != value for key, value in expected.items()):
        raise QualificationError("accepted v3 scoring baseline contract is missing or differs")
    original = baseline.get("original_21_chapter_qualification")
    if not isinstance(original, dict) or len(original.get("comparison", [])) != 21:
        raise QualificationError("accepted v3 scoring baseline lacks the complete 21-chapter comparison")
    if baseline.get("qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise QualificationError("scoring baseline qualification ID mismatch")
    digest = sha256_bytes(path.read_bytes())
    return baseline, digest


def _candidate_packet(
    repo_root: Path,
    source_row: dict[str, Any],
) -> tuple[dict[str, Any], Any]:
    prepared = prepare_chapter(source_row["book"], int(source_row["chapter"]))
    source_identity = prepared.row["input_identity"]
    if source_identity.get("packet_id") != source_row.get("packet_id"):
        raise QualificationError(f"source packet ID mismatch for {source_row['reference']}")
    if source_identity.get("packet_hash") != source_row.get("packet_hash"):
        raise QualificationError(f"source packet hash mismatch for {source_row['reference']}")
    if source_identity.get("gate_version") != RICHNESS_GATE_V2_VERSION:
        raise QualificationError(f"source gate identity mismatch for {source_row['reference']}")

    chapter_data = bible.resolve_chapter(source_row["book"], int(source_row["chapter"]))
    passage_text = bible.passage_text(chapter_data.get("verses", []))
    system_prompt = system_prompt_for_version(PROMPT_VERSION)
    user_prompt = build_user_prompt(
        source_row["reference"],
        source_row["book"],
        int(source_row["chapter"]),
        passage_text,
        prepared.synthesis,
        prepared.bundle,
        prepared.synthesis.evidence_availability,
        prompt_version=PROMPT_VERSION,
    )
    packet_base = {
        "artifact_version": PACKET_VERSION,
        "qualification_candidate": True,
        "generation_authorized": False,
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "reference": source_row["reference"],
        "book": source_row["book"],
        "chapter": int(source_row["chapter"]),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "commentary_prompt_version": PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "evidence_bundle_version": prepared.bundle.version,
        "evidence_availability": prepared.synthesis.evidence_availability,
        "evidence_count": len(prepared.bundle.evidence_items),
        "evidence_hash": prepared.bundle.evidence_hash,
        "synthesis_hash": prepared.synthesis.synthesis_hash,
        "synthesis_schema_version": prepared.synthesis.synthesis_schema_version,
        "synthesis_compiler_version": prepared.synthesis.synthesis_compiler_version,
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "validator_identity": source_identity["validator_identity"],
        "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
        "source_qualification_ordinal": source_row["ordinal"],
        "source_packet_id": source_row["packet_id"],
        "source_packet_hash": source_row["packet_hash"],
        "source_packet_file_sha256": source_row["packet_file_sha256"],
        "qualification_contract": FROZEN_CONTRACTS,
    }
    packet_hash = sha256_json(packet_base)
    packet = {
        **packet_base,
        "packet_id": f"{ARTIFACT_VERSION}-packet:{packet_hash}",
        "packet_hash": packet_hash,
    }
    return packet, prepared


def build_manifest(repo_root: Path = ROOT) -> tuple[dict[str, Any], list[tuple[dict[str, Any], Any]]]:
    """Rebuild the candidate packets from the exact historical corpus."""

    source_manifest = _source_manifest(repo_root)
    _, baseline_sha256 = _scoring_baseline(repo_root)
    source_by_reference = {row["reference"]: row for row in source_manifest["chapters"]}
    packets: list[tuple[dict[str, Any], Any]] = []
    rows: list[dict[str, Any]] = []
    system_prompt = system_prompt_for_version(PROMPT_VERSION)
    system_prompt_sha256 = sha256_bytes(system_prompt.encode("utf-8"))
    for ordinal, reference in enumerate(EXPECTED_REFERENCES, 1):
        source_row = source_by_reference.get(reference)
        if source_row is None:
            raise QualificationError(f"historical corpus lacks {reference}")
        packet, prepared = _candidate_packet(repo_root, source_row)
        filename = f"{ordinal:03d}_{slug(packet['book'], packet['chapter'])}.json"
        packet_bytes = _json_bytes(packet)
        rows.append(
            {
                "ordinal": ordinal,
                "source_qualification_ordinal": source_row["ordinal"],
                "reference": reference,
                "book": packet["book"],
                "chapter": packet["chapter"],
                "evidence_availability": packet["evidence_availability"],
                "packet_filename": filename,
                "response_filename": filename,
                "packet_id": packet["packet_id"],
                "packet_hash": packet["packet_hash"],
                "packet_file_sha256": sha256_bytes(packet_bytes),
                "source_packet_id": source_row["packet_id"],
                "source_packet_hash": source_row["packet_hash"],
                "source_packet_file_sha256": source_row["packet_file_sha256"],
                "evidence_hash": packet["evidence_hash"],
                "synthesis_hash": packet["synthesis_hash"],
                "system_prompt_sha256": system_prompt_sha256,
                "user_prompt_sha256": sha256_bytes(packet["user_prompt"].encode("utf-8")),
            }
        )
        packets.append((packet, prepared))

    seed = sha256_json(
        {
            "artifact_version": ARTIFACT_VERSION,
            "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "contracts": FROZEN_CONTRACTS,
            "source_manifest_identity": source_manifest["qualification_manifest_identity"],
            "source_handoff_identity": source_manifest.get("source_handoff_identity"),
            "scoring_baseline_sha256": baseline_sha256,
            "system_prompt_sha256": system_prompt_sha256,
            "packet_hashes": [row["packet_hash"] for row in rows],
        }
    )
    qualification_id = f"renderer-qualification-v2-prompt-1.6-{RENDERER}-{seed[:20]}"
    manifest = {
        "artifact_version": ARTIFACT_VERSION,
        "qualification_id": qualification_id,
        "previous_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "generation_authorized": False,
        "external_response_required": True,
        "contract_versions": FROZEN_CONTRACTS,
        "source_qualification_manifest_identity": source_manifest["qualification_manifest_identity"],
        "source_handoff_identity": source_manifest["source_handoff_identity"],
        "source_scoring_baseline": "richness-scoring-remediation-v1/evaluation/counterfactual-rescore-v3.json",
        "source_scoring_baseline_sha256": baseline_sha256,
        "renderer_prompt_source": {
            "module": "bhf_agent.chapter_commentary.prompts",
            "resolver": "system_prompt_for_version",
            "prompt_version": PROMPT_VERSION,
            "system_prompt_sha256": system_prompt_sha256,
        },
        "chapter_count": len(rows),
        "chapters": rows,
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return manifest, packets


def _default_root(repo_root: Path = ROOT) -> Path:
    manifest, _ = build_manifest(repo_root)
    return (
        repo_root
        / ".bhf-data/bhf-commentary-candidates"
        / manifest["qualification_id"]
    )


def _root(repo_root: Path, qualification_root: Path | None) -> Path:
    return qualification_root or _default_root(repo_root)


def _verify_manifest(manifest: dict[str, Any]) -> None:
    identity = manifest.get("manifest_identity")
    expected_identity = sha256_json(
        {key: value for key, value in manifest.items() if key != "manifest_identity"}
    )
    if identity != expected_identity:
        raise QualificationError("qualification v2 manifest identity mismatch")
    if manifest.get("artifact_version") != ARTIFACT_VERSION:
        raise QualificationError("unsupported qualification v2 artifact version")
    if manifest.get("previous_qualification_id") != PREVIOUS_QUALIFICATION_ID:
        raise QualificationError("previous qualification identity mismatch")
    if manifest.get("renderer") != RENDERER or manifest.get("renderer_effort") != RENDERER_EFFORT:
        raise QualificationError("renderer identity or effort mismatch")
    if manifest.get("contract_versions") != FROZEN_CONTRACTS:
        raise QualificationError("frozen scoring or renderer contract differs")
    rows = manifest.get("chapters")
    if not isinstance(rows, list) or len(rows) != 21:
        raise QualificationError("qualification v2 must contain exactly 21 chapters")
    if [row.get("reference") for row in rows] != list(EXPECTED_REFERENCES):
        raise QualificationError("qualification v2 chapter order or membership mismatch")
    if any(row.get("reference") in EXCLUDED_DATA_GAP_REFERENCES for row in rows):
        raise QualificationError("qualification v2 DATA_GAP exclusion mismatch")
    if any(
        row.get("system_prompt_sha256") != manifest["renderer_prompt_source"]["system_prompt_sha256"]
        for row in rows
    ):
        raise QualificationError("qualification v2 prompt identity mismatch")


def _zip_write(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content)


def _write_checksum_index(root: Path, name: str) -> str:
    files = {}
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        if path.name == name:
            continue
        files[path.relative_to(root).as_posix()] = sha256_bytes(path.read_bytes())
    payload = {
        "artifact_version": CHECKSUM_VERSION,
        "qualification_id": _read(root / "qualification-manifest.json")["qualification_id"],
        "excluded_self": name,
        "files": files,
    }
    payload["index_sha256"] = sha256_json(payload)
    return _write_json_immutable(root / name, payload)


def prepare(*, repo_root: Path = ROOT, qualification_root: Path | None = None) -> dict[str, Any]:
    """Freeze the 21 exact prompt-1.6 packets and external handoff."""

    root = _root(repo_root, qualification_root)
    manifest, material = build_manifest(repo_root)
    _verify_manifest(manifest)
    _write_json_immutable(root / "qualification-manifest.json", manifest)

    handoff_items = []
    for row, (packet, _) in zip(manifest["chapters"], material, strict=True):
        packet_bytes = _json_bytes(packet)
        if sha256_bytes(packet_bytes) != row["packet_file_sha256"]:
            raise QualificationError(f"candidate packet serialization drift for {row['reference']}")
        write_immutable(root / "packets" / row["packet_filename"], packet_bytes)
        stem = Path(row["packet_filename"]).stem
        handoff_dir = root / "handoff" / stem
        system_bytes = packet["system_prompt"].encode("utf-8")
        user_bytes = packet["user_prompt"].encode("utf-8")
        if sha256_bytes(system_bytes) != row["system_prompt_sha256"]:
            raise QualificationError(f"prompt 1.6 system prompt drift for {row['reference']}")
        if sha256_bytes(user_bytes) != row["user_prompt_sha256"]:
            raise QualificationError(f"prompt 1.6 user prompt drift for {row['reference']}")
        write_immutable(handoff_dir / "system_prompt.txt", system_bytes)
        write_immutable(handoff_dir / "user_prompt.txt", user_bytes)
        metadata = {
            **row,
            "qualification_id": manifest["qualification_id"],
            "renderer": RENDERER,
            "renderer_effort": RENDERER_EFFORT,
            "commentary_prompt_version": PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        }
        _write_json_immutable(handoff_dir / "metadata.json", metadata)
        handoff_items.append(
            {
                "ordinal": row["ordinal"],
                "reference": row["reference"],
                "directory": f"handoff/{stem}",
                "response_filename": row["response_filename"],
                "packet_id": row["packet_id"],
                "packet_hash": row["packet_hash"],
                "system_prompt_sha256": row["system_prompt_sha256"],
                "user_prompt_sha256": row["user_prompt_sha256"],
            }
        )

    handoff_manifest = {
        "artifact_version": HANDOFF_VERSION,
        "qualification_id": manifest["qualification_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "items": handoff_items,
    }
    handoff_manifest["handoff_identity"] = sha256_json(handoff_manifest)
    _write_json_immutable(root / "handoff/manifest.json", handoff_manifest)
    if handoff_manifest["handoff_identity"] != sha256_json(
        {key: value for key, value in handoff_manifest.items() if key != "handoff_identity"}
    ):
        raise QualificationError("qualification v2 handoff identity calculation failed")
    metadata = {
        "artifact_version": "commentary-renderer-qualification-v2-metadata-v1",
        "qualification_id": manifest["qualification_id"],
        "status": "AWAITING_EXTERNAL_RESPONSE_BUNDLE",
        "chapter_count": 21,
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "contracts": FROZEN_CONTRACTS,
        "source_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "response_import_command": (
            f".venv/bin/python tools/commentary_renderer_qualification_v2.py import "
            f"--qualification-root {root} --bundle <PATH_TO_VERIFIED_SOL_RESPONSE_BUNDLE.zip>"
        ),
    }
    _write_json_immutable(root / "qualification-metadata.json", metadata)

    bundle_bytes = BytesIO()
    with zipfile.ZipFile(bundle_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _zip_write(archive, "manifest.json", _json_bytes(manifest))
        _zip_write(archive, "GENERATION_INSTRUCTIONS.txt", GENERATION_INSTRUCTIONS.encode("utf-8"))
        for row, (packet, _) in zip(manifest["chapters"], material, strict=True):
            _zip_write(archive, f"packets/{row['packet_filename']}", _json_bytes(packet))
    input_zip = root / "renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-input.zip"
    write_immutable(input_zip, bundle_bytes.getvalue())
    _write_checksum_index(root, "checksums-prepared.json")
    return {
        "status": "PREPARED_AWAITING_EXTERNAL_RENDERER",
        "qualification_id": manifest["qualification_id"],
        "qualification_root": str(root),
        "input_bundle": str(input_zip),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "chapter_count": len(manifest["chapters"]),
        "packet_count": len(material),
        "packet_identities_verified": True,
        "scoring_contract_frozen": True,
        "response_import_command": (
            f".venv/bin/python tools/commentary_renderer_qualification_v2.py import "
            f"--qualification-root {root} --bundle <PATH_TO_VERIFIED_SOL_RESPONSE_BUNDLE.zip>"
        ),
    }


def response_manifest_template(
    *, repo_root: Path = ROOT, qualification_root: Path | None = None
) -> dict[str, Any]:
    root = _root(repo_root, qualification_root)
    manifest = _read(root / "qualification-manifest.json")
    _verify_manifest(manifest)
    return {
        "artifact_version": RESPONSE_MANIFEST_VERSION,
        "qualification_id": manifest["qualification_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
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


def _verify_response_bundle(
    files: dict[str, bytes], response_manifest: dict[str, Any], qualification: dict[str, Any]
) -> list[dict[str, Any]]:
    if response_manifest.get("artifact_version") != RESPONSE_MANIFEST_VERSION:
        raise QualificationError("response manifest artifact version mismatch")
    for key, value in (
        ("qualification_id", qualification["qualification_id"]),
        ("renderer", RENDERER),
        ("renderer_effort", RENDERER_EFFORT),
        ("prompt_version", PROMPT_VERSION),
    ):
        if response_manifest.get(key) != value:
            raise QualificationError(f"response manifest {key} mismatch")
    responses = response_manifest.get("responses")
    expected = qualification["chapters"]
    if not isinstance(responses, list) or len(responses) != len(expected):
        raise QualificationError("response manifest must contain exactly 21 responses")
    expected_names = {"manifest.json"} | {
        f"responses/{row['response_filename']}" for row in expected
    }
    actual_names = set(files)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise QualificationError(
            f"response bundle filenames mismatch; missing={missing}; extra={extra}"
        )
    for packet, response in zip(expected, responses, strict=True):
        required = {
            "ordinal": packet["ordinal"],
            "reference": packet["reference"],
            "packet_id": packet["packet_id"],
            "packet_hash": packet["packet_hash"],
            "response_filename": packet["response_filename"],
        }
        if not isinstance(response, dict) or any(
            response.get(key) != value for key, value in required.items()
        ):
            raise QualificationError(f"response manifest packet identity mismatch for {packet['reference']}")
        raw = files[f"responses/{packet['response_filename']}"]
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise QualificationError(
                f"response bundle contains corrupt JSON for {packet['reference']}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise QualificationError(
                f"response bundle contains a non-object response for {packet['reference']}"
            )
    return expected


def import_bundle(
    bundle: Path,
    *,
    repo_root: Path = ROOT,
    qualification_root: Path | None = None,
) -> dict[str, Any]:
    """Import exactly one complete, identity-matched external response bundle."""

    root = _root(repo_root, qualification_root)
    qualification = _read(root / "qualification-manifest.json")
    _verify_manifest(qualification)
    current, _ = build_manifest(repo_root)
    if current != qualification:
        raise QualificationError("frozen v2 source inputs changed before response import")
    files, response_manifest = _read_zip(bundle)
    rows = _verify_response_bundle(files, response_manifest, qualification)
    write_immutable(root / "responses/response-manifest.json", files["manifest.json"])
    imported = []
    for row in rows:
        raw = files[f"responses/{row['response_filename']}"]
        raw_path = root / "responses/raw" / row["response_filename"]
        digest = write_immutable(raw_path, raw)
        imported.append(
            {
                "ordinal": row["ordinal"],
                "reference": row["reference"],
                "packet_id": row["packet_id"],
                "packet_hash": row["packet_hash"],
                "response_filename": row["response_filename"],
                "raw_sha256": digest,
            }
        )
    receipt = {
        "artifact_version": IMPORT_VERSION,
        "qualification_id": qualification["qualification_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "response_bundle_sha256": sha256_bytes(bundle.read_bytes()),
        "response_manifest_sha256": sha256_bytes(files["manifest.json"]),
        "response_count": len(imported),
        "responses": imported,
        "raw_responses_immutable": True,
    }
    _write_json_immutable(root / "responses/import-receipt.json", receipt)
    _write_checksum_index(root, "checksums-imported.json")
    return {
        "status": "IMPORTED",
        "qualification_id": qualification["qualification_id"],
        "response_count": len(imported),
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "prompt_version": PROMPT_VERSION,
        "raw_responses_immutable": True,
    }


def _codes(errors: Iterable[str]) -> list[str]:
    values = []
    for error in errors:
        code = str(error).split(":", 1)[0].strip()
        if code.isupper() and " " not in code:
            values.append(code)
    return sorted(set(values))


def _empty_metrics(
    row: dict[str, Any], codes: list[str], errors: Iterable[str] = ()
) -> dict[str, Any]:
    return {
        "reference": row["reference"],
        "renderer_prompt_version": PROMPT_VERSION,
        "validation_status": "rejected",
        "structural_result": "REJECTED",
        "rejection_codes": codes,
        "validation_errors": list(errors),
        "eligible_cluster_count": None,
        "eligible_weighted_denominator": None,
        "weighted_coverage": None,
        "core_coverage": None,
        "eligible_idea_utilization": None,
        "eligible_unit_utilization": None,
        "raw_synthesis_utilization": None,
        "category_coverage": None,
        "dump_severity": None,
        "word_count": None,
        "block_count": None,
        "gate_v2_1": None,
        "renderer_qualification_result": "STRUCTURAL_REJECTION",
    }


def _safe_gate(score: Any, audit: dict[str, Any], availability: str) -> Any:
    safety = {
        name: True
        for name in (
            "validation_clean",
            "provenance_complete",
            "hashes_valid",
            "chapter_boundaries_valid",
            "confidence_valid",
            "dispute_state_preserved",
            "unsupported_significance_absent",
        )
    }
    return assess_gate_v2(
        score=score,
        evidence_availability=availability,
        baseline_richness="SYNTHESIS_GAP" if availability == "AVAILABLE" else "EVIDENCE_GAP",
        after_richness=audit["richness_status"],
        safety_checks=safety,
        evidence_use_delta=audit["unique_evidence_ids_consumed"],
        section_delta=audit["section_count"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )


def _evaluate_one(
    row: dict[str, Any], raw: bytes, prepared: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"], [str(exc)])
        return result, {
            "artifact_version": PARSED_VERSION,
            "reference": row["reference"],
            "raw_sha256": sha256_bytes(raw),
            "parse_status": "MALFORMED_JSON",
            "renderer_payload": None,
            "validated_commentary": None,
            "validation_errors": [str(exc)],
        }
    if not isinstance(payload, dict):
        result = _empty_metrics(row, ["MALFORMED_RESPONSE_JSON"], ["response must be an object"])
        return result, {
            "artifact_version": PARSED_VERSION,
            "reference": row["reference"],
            "raw_sha256": sha256_bytes(raw),
            "parse_status": "NON_OBJECT_JSON",
            "renderer_payload": payload,
            "validated_commentary": None,
            "validation_errors": ["response must be an object"],
        }

    renderer_payload = dict(payload)
    renderer_payload["generated_metadata"] = GeneratedMetadata(
        evidence_hash=prepared.bundle.evidence_hash,
        evidence_bundle_version=prepared.bundle.version,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=PROMPT_VERSION,
        model=RENDERER,
        generated_timestamp=None,
        synthesis_hash=prepared.synthesis.synthesis_hash,
        synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
        synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        renderer_label=RENDERER,
    ).to_dict()
    renderer_payload["evidence_availability"] = prepared.synthesis.evidence_availability
    renderer_payload["status"] = "pending"
    validation = validate_chapter_commentary(
        renderer_payload,
        prepared.bundle,
        expected_evidence_hash=prepared.bundle.evidence_hash,
        expected_prompt_version=PROMPT_VERSION,
        expected_reference=row["reference"],
        expected_book=row["book"],
        expected_chapter=int(row["chapter"]),
        synthesis=prepared.synthesis,
        expected_synthesis_hash=prepared.synthesis.synthesis_hash,
    )
    parsed = {
        "artifact_version": PARSED_VERSION,
        "reference": row["reference"],
        "raw_sha256": sha256_bytes(raw),
        "parse_status": "JSON_OBJECT",
        "renderer_payload": payload,
        "validated_commentary": None,
        "validation_errors": list(validation.errors),
    }
    if not validation.valid or validation.commentary is None:
        result = _empty_metrics(row, _codes(validation.errors) or ["VALIDATION_FAILED"], validation.errors)
        return result, parsed

    parsed["validated_commentary"] = validation.commentary.to_dict()
    blocks = [
        block
        for section in validation.commentary.sections
        for block in section.blocks
    ]
    audit = audit_chapter(
        row["book"], int(row["chapter"]), validation.commentary, prepared.bundle
    )
    passage_text = bible.passage_text(
        bible.resolve_chapter(row["book"], int(row["chapter"])).get("verses", [])
    )
    score = score_synthesis_richness(
        prepared.synthesis.synthesis_units,
        evidence_items=prepared.bundle.evidence_items,
        consumed_synthesis_ids=[
            synthesis_id for block in blocks for synthesis_id in block.synthesis_ids
        ],
        blocks=blocks,
        passage_ref=row["reference"],
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=passage_text,
    )
    if score.coverage_policy_version != RICHNESS_POLICY_VERSION_V3:
        raise QualificationError("v3 scorer did not execute the frozen reader-relevance policy")
    if score.coverage_eligibility_classifier_version != COVERAGE_ELIGIBILITY_CLASSIFIER_V1:
        raise QualificationError("v3 scorer did not execute the frozen eligibility classifier")
    gate = _safe_gate(score, audit, prepared.synthesis.evidence_availability)
    target_result = (
        "PASS"
        if score.weighted_idea_coverage >= QUALIFICATION_THRESHOLDS["reader_relevance_weighted_coverage_min"]
        else "BELOW_TARGET"
    )
    result = {
        "reference": row["reference"],
        "renderer_prompt_version": PROMPT_VERSION,
        "validation_status": "validated",
        "structural_result": "ACCEPTED",
        "rejection_codes": [],
        "validation_errors": [],
        "eligible_cluster_count": score.meaningful_cluster_count,
        "eligible_weighted_denominator": score.eligible_weighted_denominator,
        "weighted_coverage": score.weighted_idea_coverage,
        "core_coverage": score.core_cluster_coverage,
        "eligible_idea_utilization": score.idea_cluster_coverage,
        "eligible_unit_utilization": score.eligible_synthesis_coverage,
        "raw_synthesis_utilization": score.raw_synthesis_coverage,
        "category_coverage": score.category_coverage,
        "dump_severity": score.dump_diagnostics.severity,
        "word_count": audit["commentary_prose_word_count"],
        "block_count": audit["commentary_block_count"],
        "quality_gate_outcome": gate.outcome,
        "gate_v2_1": gate.to_dict(),
        "renderer_qualification_result": target_result,
        "score": score.to_dict(),
        "audit": audit,
    }
    return result, parsed


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    return round(sum(values) / len(values), 4) if values else None


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["structural_result"] == "ACCEPTED"]
    evidence_bearing = [
        row for row in valid if row.get("evidence_availability") == "AVAILABLE"
    ]
    return {
        "renderer_chapters": len(rows),
        "structurally_valid": len(valid),
        "structural_rejections": len(rows) - len(valid),
        "structural_rejection_codes": dict(
            Counter(code for row in rows for code in row["rejection_codes"])
        ),
        "quality_fail": sum(
            row.get("quality_gate_outcome") == "QUALITY_FAIL" for row in valid
        ),
        "high_dump": sum(row.get("dump_severity") == "HIGH" for row in valid),
        "evidence_bearing_valid_chapters": len(evidence_bearing),
        "weighted_coverage": _mean(evidence_bearing, "weighted_coverage"),
        "core_coverage": _mean(evidence_bearing, "core_coverage"),
        "eligible_idea_utilization": _mean(evidence_bearing, "eligible_idea_utilization"),
        "eligible_unit_utilization": _mean(evidence_bearing, "eligible_unit_utilization"),
        "raw_synthesis_utilization": _mean(evidence_bearing, "raw_synthesis_utilization"),
        "category_coverage": _mean(evidence_bearing, "category_coverage"),
        "qualification_target_pass": sum(
            row.get("renderer_qualification_result") == "PASS" for row in evidence_bearing
        ),
        "qualification_target_shortfall": sum(
            row.get("renderer_qualification_result") == "BELOW_TARGET" for row in evidence_bearing
        ),
        "gate_distribution": dict(
            Counter(row.get("quality_gate_outcome") for row in valid)
        ),
        "dump_distribution": dict(Counter(row.get("dump_severity") for row in valid)),
        "category_coverage_below_per_chapter_target": sum(
            isinstance(row.get("category_coverage"), (int, float))
            and row["category_coverage"] < QUALIFICATION_THRESHOLDS["category_coverage_min_per_chapter"]
            for row in evidence_bearing
        ),
    }


def _numeric_delta(value: Any, baseline: Any) -> float | None:
    if isinstance(value, (int, float)) and isinstance(baseline, (int, float)):
        return round(value - baseline, 4)
    return None


def _diagnostic_label(result: dict[str, Any], historical: dict[str, Any]) -> str:
    if result["structural_result"] != "ACCEPTED":
        if "SYNTHESIS_ANCESTRY_MISMATCH" in result["rejection_codes"]:
            return "ANCESTRY_FAILURE"
        return "STRUCTURAL_REGRESSION"
    if result.get("dump_severity") == "HIGH" and historical.get("dump_severity") != "HIGH":
        return "DUMP_REGRESSION"
    if (
        isinstance(result.get("core_coverage"), (int, float))
        and isinstance(historical.get("core_coverage"), (int, float))
        and result["core_coverage"] < historical["core_coverage"]
    ):
        return "CORE_REGRESSION"
    if (
        isinstance(result.get("category_coverage"), (int, float))
        and isinstance(historical.get("category_coverage"), (int, float))
        and result["category_coverage"] < historical["category_coverage"]
    ):
        return "CATEGORY_REGRESSION"
    if (
        isinstance(result.get("weighted_coverage"), (int, float))
        and result["weighted_coverage"] < QUALIFICATION_THRESHOLDS["reader_relevance_weighted_coverage_min"]
    ):
        return "RICHNESS_SHORTFALL"
    if historical.get("structural_result") == "REJECTED":
        return "IMPROVED_RENDERER"
    if (
        isinstance(result.get("weighted_coverage"), (int, float))
        and isinstance(historical.get("weighted_coverage"), (int, float))
        and result["weighted_coverage"] > historical["weighted_coverage"]
    ):
        return "IMPROVED_RENDERER"
    return "STABLE_PASS"


def _historical_rows(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    baseline, baseline_sha256 = _scoring_baseline(repo_root)
    original = baseline["original_21_chapter_qualification"]
    full = {row["reference"]: row["new"] for row in original["comparison"]}
    old = {row["reference"]: row["old"] for row in original["comparison"]}
    priority = {
        row["reference"]: row["new"]
        for row in baseline["five_chapter_remediation"]["comparison"]
    }
    return full, old, {"priority_prompt_1_6": priority, "baseline_sha256": baseline_sha256}


def evaluate(
    *, repo_root: Path = ROOT, qualification_root: Path | None = None
) -> dict[str, Any]:
    """Evaluate imported response bytes under the frozen v1.6/v3 contract."""

    root = _root(repo_root, qualification_root)
    qualification = _read(root / "qualification-manifest.json")
    _verify_manifest(qualification)
    current, material = build_manifest(repo_root)
    if current != qualification:
        raise QualificationError("frozen v2 source inputs changed before evaluation")
    receipt = _read(root / "responses/import-receipt.json")
    if (
        receipt.get("qualification_id") != qualification["qualification_id"]
        or receipt.get("response_count") != 21
        or receipt.get("renderer") != RENDERER
        or receipt.get("prompt_version") != PROMPT_VERSION
    ):
        raise QualificationError("qualification v2 response import is absent or mismatched")

    historical_full, historical_old, baseline_metadata = _historical_rows(repo_root)
    results = []
    comparisons = []
    for row, (_, prepared) in zip(qualification["chapters"], material, strict=True):
        raw_path = root / "responses/raw" / row["response_filename"]
        if not raw_path.is_file():
            raise QualificationError(f"missing immutable imported response: {row['reference']}")
        raw = raw_path.read_bytes()
        receipt_row = next(
            item for item in receipt["responses"] if item["reference"] == row["reference"]
        )
        if sha256_bytes(raw) != receipt_row.get("raw_sha256"):
            raise QualificationError(f"raw response changed after import for {row['reference']}")
        result, parsed = _evaluate_one(row, raw, prepared)
        result["evidence_availability"] = row["evidence_availability"]
        result["packet_id"] = row["packet_id"]
        result["packet_hash"] = row["packet_hash"]
        result["raw_sha256"] = sha256_bytes(raw)
        parsed.update(
            {
                "qualification_id": qualification["qualification_id"],
                "packet_id": row["packet_id"],
                "packet_hash": row["packet_hash"],
            }
        )
        stem = Path(row["response_filename"]).stem
        _write_json_immutable(root / "parsed" / f"{stem}.json", parsed)
        results.append(result)

        historical = historical_full[row["reference"]]
        priority = baseline_metadata["priority_prompt_1_6"].get(row["reference"])
        comparison = {
            "reference": row["reference"],
            "renderer_prompt_version": PROMPT_VERSION,
            "historical_prompt_1_5_original": historical_old[row["reference"]],
            "historical_prompt_1_5_v3_counterfactual": historical,
            "historical_prompt_1_6_priority_case": priority,
            "new_prompt_1_6": {
                key: result.get(key)
                for key in (
                    "structural_result",
                    "rejection_codes",
                    "eligible_cluster_count",
                    "eligible_weighted_denominator",
                    "weighted_coverage",
                    "core_coverage",
                    "eligible_idea_utilization",
                    "eligible_unit_utilization",
                    "raw_synthesis_utilization",
                    "category_coverage",
                    "dump_severity",
                    "word_count",
                    "block_count",
                    "quality_gate_outcome",
                    "renderer_qualification_result",
                )
            },
            "delta_vs_historical_prompt_1_5_v3": {
                key: _numeric_delta(result.get(new_key), historical.get(old_key))
                for key, new_key, old_key in (
                    ("weighted_coverage", "weighted_coverage", "weighted_coverage"),
                    ("core_coverage", "core_coverage", "core_coverage"),
                    ("category_coverage", "category_coverage", "category_coverage"),
                )
            },
            "diagnostic_classification": _diagnostic_label(result, historical),
        }
        comparisons.append(comparison)
        _write_json_immutable(
            root / "evaluation/chapters" / f"{stem}.json",
            {"artifact_version": EVALUATION_VERSION, **comparison, "full_result": result},
        )

    aggregate = _aggregate(results)
    rejection_counts = Counter(code for row in results for code in row["rejection_codes"])
    hard_codes = sorted(code for code in rejection_counts if code in HARD_PROVENANCE_CODES)
    category_regression = aggregate["category_coverage_below_per_chapter_target"] > 0
    qualification_pass = (
        aggregate["structural_rejections"] == 0
        and not hard_codes
        and aggregate["core_coverage"] is not None
        and aggregate["core_coverage"] >= QUALIFICATION_THRESHOLDS["core_coverage_min"]
        and all(
            row.get("core_coverage") == QUALIFICATION_THRESHOLDS["core_coverage_min"]
            for row in results
            if row["structural_result"] == "ACCEPTED"
        )
        and aggregate["weighted_coverage"] is not None
        and aggregate["weighted_coverage"] >= QUALIFICATION_THRESHOLDS["reader_relevance_weighted_coverage_min"]
        and aggregate["eligible_idea_utilization"] is not None
        and aggregate["eligible_idea_utilization"] >= QUALIFICATION_THRESHOLDS["eligible_idea_utilization_min"]
        and aggregate["high_dump"] <= QUALIFICATION_THRESHOLDS["high_dump_max"]
        and aggregate["quality_fail"] <= QUALIFICATION_THRESHOLDS["quality_fail_max"]
        and not category_regression
        and not any(count > 1 for count in rejection_counts.values())
    )
    baseline_sha256 = baseline_metadata["baseline_sha256"]
    baseline, _ = _scoring_baseline(repo_root)
    report = {
        "artifact_version": EVALUATION_VERSION,
        "qualification_id": qualification["qualification_id"],
        "renderer": RENDERER,
        "renderer_effort": RENDERER_EFFORT,
        "source_production_qualification_id": PREVIOUS_QUALIFICATION_ID,
        "frozen_contracts": qualification["contract_versions"],
        "source_scoring_baseline_sha256": baseline_sha256,
        "dense_reader_applied": False,
        "chapters": results,
        "chapter_comparison": comparisons,
        "aggregate": aggregate,
        "historical_comparison": {
            "original_prompt_1_5": baseline["original_21_chapter_qualification"]["old_aggregate"],
            "prompt_1_5_v3_counterfactual": baseline["original_21_chapter_qualification"]["new_aggregate"],
            "prompt_1_6_priority_case_scope": "Exodus 14, Deuteronomy 10, Job 1, 1 Corinthians 14, Revelation 21",
            "prompt_1_6_priority_case_results": baseline["five_chapter_remediation"]["new_summary"],
        },
        "outcome_transitions": dict(
            Counter(
                f"{comparison['historical_prompt_1_5_v3_counterfactual'].get('gate_result') or comparison['historical_prompt_1_5_v3_counterfactual'].get('structural_result')}->"
                f"{comparison['new_prompt_1_6'].get('quality_gate_outcome') or comparison['new_prompt_1_6'].get('structural_result')}"
                for comparison in comparisons
            )
        ),
        "thresholds": QUALIFICATION_THRESHOLDS,
        "qualification_target_semantics": (
            "weighted reader-relevance coverage and eligible idea utilization are arithmetic means over structurally valid AVAILABLE chapters;"
            " structural validity, core coverage, dump severity, and category floors are also checked per chapter"
        ),
        "qualification_result": (
            "RENDERER_QUALIFICATION_PASS" if qualification_pass else "RENDERER_QUALIFICATION_NOT_QUALIFIED"
        ),
    }
    _write_json_immutable(root / "evaluation/evaluation.json", report)
    _write_checksum_index(root, "checksums-evaluation.json")
    return report


def status(*, repo_root: Path = ROOT, qualification_root: Path | None = None) -> dict[str, Any]:
    root = _root(repo_root, qualification_root)
    manifest_path = root / "qualification-manifest.json"
    if not manifest_path.is_file():
        return {"status": "NOT_PREPARED", "qualification_root": str(root)}
    manifest = _read(manifest_path)
    _verify_manifest(manifest)
    receipt_path = root / "responses/import-receipt.json"
    evaluation_path = root / "evaluation/evaluation.json"
    return {
        "status": (
            _read(evaluation_path).get("qualification_result")
            if evaluation_path.is_file()
            else "IMPORTED_AWAITING_EVALUATION" if receipt_path.is_file() else "AWAITING_EXTERNAL_RESPONSE_BUNDLE"
        ),
        "qualification_id": manifest["qualification_id"],
        "qualification_root": str(root),
        "renderer": manifest["renderer"],
        "renderer_effort": manifest["renderer_effort"],
        "prompt_version": manifest["contract_versions"]["renderer_prompt_version"],
        "chapter_count": manifest["chapter_count"],
        "response_count": _read(receipt_path).get("response_count") if receipt_path.is_file() else 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualification-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser(
        "prepare", help="freeze packets and create the external Sol request bundle"
    )
    response_template_parser = sub.add_parser(
        "response-template", help="print the required response manifest"
    )
    imported = sub.add_parser("import", help="immutably import one complete Sol response bundle")
    imported.add_argument("--bundle", type=Path, required=True)
    evaluate_parser = sub.add_parser("evaluate", help="validate and score imported responses")
    status_parser = sub.add_parser("status", help="show the isolated qualification state")
    # Accept the root after the subcommand too, matching the import command
    # printed in qualification-metadata.json.  SUPPRESS avoids overwriting a
    # root supplied before the subcommand with a subparser default of None.
    for command_parser in (
        prepare_parser,
        response_template_parser,
        imported,
        evaluate_parser,
        status_parser,
    ):
        command_parser.add_argument(
            "--qualification-root", type=Path, default=argparse.SUPPRESS
        )
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            output = prepare(qualification_root=args.qualification_root)
        elif args.command == "response-template":
            output = response_manifest_template(qualification_root=args.qualification_root)
        elif args.command == "import":
            output = import_bundle(args.bundle, qualification_root=args.qualification_root)
        elif args.command == "evaluate":
            output = evaluate(qualification_root=args.qualification_root)
        else:
            output = status(qualification_root=args.qualification_root)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (QualificationError, ManifestError, ArtifactCollisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
