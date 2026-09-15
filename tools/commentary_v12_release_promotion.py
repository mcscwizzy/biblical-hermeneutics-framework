#!/usr/bin/env python3
"""Promote the immutable Terra v1.2 validation artifact into a runtime release.

This command consumes already-normalized, already-validated responses.  It does
not call a model, regenerate prose, or merge the v1.1 corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_NAME = "commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2"
DEFAULT_ARTIFACT = ROOT / ".bhf-data/bhf-commentary-candidates" / ARTIFACT_NAME
DEFAULT_OUTPUT = ROOT / ".bhf-data/bhf-commentary-v1.2"
RELEASE = "commentary-v1.2"
MODEL = "gpt-5.6-terra"
EFFORT = "high"
POLICY_VERSION = "commentary-v1.2-publication-eligibility-v1"
ROUTING_STATUS = "PROVISIONAL_TERRA_DEFAULT_PENDING_FINAL_SOL_CONTROL"
SOL_STATUS = "4_OF_5_COMPLETE_COMPARISON_PENDING"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent.chapter_commentary.release import (
    RELEASE_CHECKSUMS_FILENAME,
    RELEASE_MANIFEST_FILENAME,
)
from bhf_agent.chapter_commentary.storage import load_commentary, save_commentary
from framework.commentary.production.models import canonical_json, sha256_json


class PromotionError(RuntimeError):
    """Raised whenever release promotion cannot prove a safe source identity."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"invalid JSON artifact: {path}") from exc


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise PromotionError(f"cannot read artifact file: {path}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _verify_checksum_index(root: Path, filename: str) -> None:
    payload = _read(root / filename)
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, dict):
        raise PromotionError(f"checksum index is malformed: {filename}")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise PromotionError(f"checksum index contains malformed entry: {filename}")
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise PromotionError(f"checksum mismatch in {filename}: {relative}")


def verify_validation_artifact(artifact: Path) -> dict[str, Any]:
    """Verify immutable artifact checksums, identities, and protected contracts."""

    if not artifact.is_dir():
        raise PromotionError(f"validation artifact is missing: {artifact}")
    checksum_name = "checksums-v2.json" if (artifact / "checksums-v2.json").is_file() else "checksums-final.json"
    _verify_checksum_index(artifact, checksum_name)

    manifest = _read(artifact / "manifest.json")
    manifest_identity = manifest.get("manifest_identity")
    manifest_without_identity = dict(manifest)
    manifest_without_identity.pop("manifest_identity", None)
    if not isinstance(manifest_identity, str) or sha256_json(manifest_without_identity) != manifest_identity:
        raise PromotionError("validation manifest identity mismatch")
    frozen = _read(artifact / "frozen-population.json")
    population = _read(artifact / "population-records.json").get("chapters")
    if not isinstance(population, list) or len(population) != 75 or len({row.get("reference") for row in population}) != 75:
        raise PromotionError("frozen population is not exactly 75 unique chapters")
    if frozen.get("identity") != manifest.get("frozen_population_identity"):
        raise PromotionError("frozen population identity mismatch")
    if frozen.get("references") != [row.get("reference") for row in population]:
        raise PromotionError("population ordering does not match frozen population")
    if manifest.get("population_size") != 75:
        raise PromotionError("validation artifact population size is not 75")

    freeze = _read(artifact / "contract-freeze.json")
    contracts = manifest.get("protected_contract_hashes")
    if not isinstance(contracts, dict) or contracts != freeze.get("protected_contract_hashes"):
        raise PromotionError("protected contract identities disagree in artifact")
    current_contracts = _current_protected_contract_hashes(artifact)
    if current_contracts != contracts:
        raise PromotionError("protected contract identity changed since validation")

    report = _read(artifact / "final-report-v2.json")
    if report.get("frozen_population_identity") != frozen.get("identity"):
        raise PromotionError("final report frozen population identity mismatch")
    if report.get("terra_model", {}).get("model") != MODEL or report.get("terra_model", {}).get("effort") != EFFORT:
        raise PromotionError("validation artifact is not Terra High")
    if report.get("protected_contracts_unchanged") is not True or report.get("ckl_unchanged") is not True or report.get("asv_unchanged") is not True:
        raise PromotionError("validation artifact does not certify protected inputs unchanged")
    return {"manifest": manifest, "population": population, "report": report, "checksum_index": checksum_name}


def _current_protected_contract_hashes(artifact: Path) -> dict[str, str]:
    """Use the same protected source identities that created the artifact."""

    prompt_files = sorted((artifact / "terra-inputs").glob("*/system_prompt.txt"))
    if not prompt_files:
        raise PromotionError("protected prompt source is missing")
    paths = {
        "prompt_1_8_system": prompt_files[0],
        "evidence_applicability": ROOT / "bhf_agent/chapter_commentary/evidence_applicability.py",
        "reader_level_projection": ROOT / "bhf_agent/chapter_commentary/reader_level_projection.py",
        "reader_ancestry_envelope": ROOT / "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py",
        "reader_provenance_binding_v2": ROOT / "bhf_agent/chapter_commentary/reader_provenance_binding_v2.py",
        "renderer_reference_presentation_v1": ROOT / "bhf_agent/chapter_commentary/renderer_reference_presentation_v1.py",
        "output_conformance": ROOT / "bhf_agent/chapter_commentary/output_conformance.py",
        "structural_validator": ROOT / "bhf_agent/chapter_commentary/validation.py",
        "richness_gate": ROOT / "bhf_agent/chapter_commentary/richness_clusters.py",
        "ckl_database": ROOT / ".bhf/ckl.sqlite",
        "asv_bible": ROOT / "bhf_agent/data/asv_bible.json",
    }
    return {name: _sha256(path) for name, path in paths.items()}


def _source_roots(artifact: Path, prior_namespace: Path) -> tuple[Path, Path]:
    return artifact / "terra-outputs", prior_namespace / "chapters"


def _find_source_dirs(artifact: Path, prior_namespace: Path, reference: str, source: str) -> list[Path]:
    roots = _source_roots(artifact, prior_namespace)
    root = roots[0] if source == "new-remaining" else roots[1]
    candidates = []
    normalized = root.glob("*/normalized.json") if source == "new-remaining" else root.glob("*/responses/terra/normalized.json")
    for normalized_path in normalized:
        try:
            data = _read(normalized_path)
        except PromotionError:
            continue
        if isinstance(data, dict) and data.get("reference") == reference:
            candidates.append(normalized_path.parent)
    if len(candidates) != 1:
        raise PromotionError(f"source identity is ambiguous or missing for {reference}")
    return candidates


def _prior_namespace(artifact: Path, manifest: dict[str, Any]) -> Path:
    value = manifest.get("prior_pilot_namespace")
    if not isinstance(value, str) or not value:
        raise PromotionError("prior Terra namespace is missing")
    path = ROOT / value
    if not path.is_dir():
        raise PromotionError(f"prior Terra namespace is missing: {path}")
    prior_manifest = _read(path / "manifest.json")
    if prior_manifest.get("manifest_identity") != _read(artifact / "prior-25-output-index.json").get("manifest_identity"):
        raise PromotionError("prior Terra manifest identity mismatch")
    return path


def _row_is_publishable(row: dict[str, Any]) -> bool:
    return all(
        (
            row.get("generated") is True,
            row.get("structural_result") == "ACCEPTED",
            row.get("provenance_result") == "PASS",
            row.get("ancestry_result") == "PASS",
            row.get("gate_result") == "PASS",
            row.get("readability_result") == "PASS",
            row.get("normal_reader_usefulness") == "PASS",
            row.get("high_dump") in (False, None),
            row.get("provider_failure") in (False, None),
            row.get("unsupported_claim_findings") in ([], None),
            row.get("parse_status") == "JSON_OBJECT",
        )
    )


def _public_state(row: dict[str, Any], publishable: bool) -> tuple[str, str]:
    if publishable:
        return "PUBLISHED", "published"
    if row.get("failure_classification") == "NOT_RENDERABLE_SOURCE_LIMITED" or not row.get("generated"):
        return "NOT_RENDERABLE_SOURCE_LIMITED", "commentary_source_limited"
    if row.get("structural_result") != "ACCEPTED":
        return "MODEL_OUTPUT_REJECTED", "commentary_model_output_rejected"
    return "QUALITY_REVIEW_REQUIRED", "commentary_quality_review_required"


def _validate_source(
    row: dict[str, Any],
    source_dir: Path,
    source: str,
    current_evidence_loader: Callable[[str, int], Any],
) -> Any:
    normalized_path = source_dir / "normalized.json"
    validation_path = source_dir / "validation.json"
    raw_path = source_dir / "raw.json"
    if not normalized_path.is_file() or not validation_path.is_file() or not raw_path.is_file():
        raise PromotionError(f"incomplete validated Terra source for {row['reference']}")
    data = _read(normalized_path)
    validation = _read(validation_path)
    if not isinstance(data, dict) or data.get("reference") != row["reference"]:
        raise PromotionError(f"commentary identity mismatch for {row['reference']}")
    _validate_normalized_shape(data, row["reference"])
    if data.get("book") != row.get("book") or data.get("chapter") != row.get("chapter"):
        raise PromotionError(f"commentary book/chapter mismatch for {row['reference']}")
    if validation.get("reference") != row["reference"]:
        raise PromotionError(f"validation identity mismatch for {row['reference']}")
    for key in ("generated", "structural_result", "provenance_result", "ancestry_result", "gate_result", "readability_result", "normal_reader_usefulness", "high_dump", "provider_failure", "parse_status", "raw_response_sha256"):
        if key in row and key in validation and validation.get(key) != row.get(key):
            # The aggregate rows intentionally omit provider_failure for the
            # reused pilot; absence and false are equivalent, never true.
            if key == "provider_failure" and row.get(key) is None and validation.get(key) is False:
                continue
            raise PromotionError(f"validation outcome mismatch for {row['reference']}: {key}")
    if row.get("unsupported_claim_findings") not in ([], None) or validation.get("unsupported_claim_findings") not in ([], None):
        raise PromotionError(f"unsupported claims recorded for {row['reference']}")

    metadata = data.get("generated_metadata")
    if not isinstance(metadata, dict) or metadata.get("model") != MODEL or metadata.get("commentary_prompt_version") != "1.8":
        raise PromotionError(f"generated metadata mismatch for {row['reference']}")
    for key in ("evidence_hash", "synthesis_hash"):
        if metadata.get(key) != row.get(key):
            raise PromotionError(f"source identity mismatch for {row['reference']}: {key}")

    chapter_root = (
        source_dir.parent.parent / "terra-inputs" / source_dir.name
        if source == "new-remaining"
        else source_dir.parents[1]
    )
    packet_path = chapter_root / "packet.json"
    metadata_path = chapter_root / "renderer-input/metadata.json"
    if not packet_path.is_file() or (source != "new-remaining" and not metadata_path.is_file()):
        raise PromotionError(f"renderer identity records are missing for {row['reference']}")
    packet = _read(packet_path)
    renderer_metadata = packet.get("preflight", {}) if source == "new-remaining" else _read(metadata_path)
    if packet.get("reference") != row["reference"] or renderer_metadata.get("reference") != row["reference"]:
        raise PromotionError(f"renderer packet identity mismatch for {row['reference']}")
    if renderer_metadata.get("renderer_input_sha256") != row.get("renderer_input_sha256"):
        raise PromotionError(f"renderer input identity mismatch for {row['reference']}")
    input_path = chapter_root / "final-input.txt" if source == "new-remaining" else chapter_root / "renderer-input/final-input.txt"
    if not input_path.is_file() or _sha256(input_path) != row.get("renderer_input_sha256"):
        raise PromotionError(f"renderer input bytes mismatch for {row['reference']}")
    presentation_hash = packet.get("presentation", {}).get("presentation_hash")
    if presentation_hash != row.get("renderer_presentation_hash") or renderer_metadata.get("renderer_presentation_hash") != row.get("renderer_presentation_hash"):
        raise PromotionError(f"renderer presentation identity mismatch for {row['reference']}")
    packet_identity = packet if packet.get("evidence_hash") else renderer_metadata
    if packet_identity.get("evidence_hash") != row.get("evidence_hash") or packet_identity.get("synthesis_hash") != row.get("synthesis_hash"):
        raise PromotionError(f"renderer packet source identity mismatch for {row['reference']}")

    raw_hash = _sha256(raw_path)
    if raw_hash != row.get("raw_response_sha256") or raw_hash != validation.get("raw_response_sha256"):
        raise PromotionError(f"renderer output identity mismatch for {row['reference']}")
    receipt_path = source_dir / "recovery-receipt.json"
    if not receipt_path.is_file():
        receipt_path = source_dir / "receipt.json"
    receipt = _read(receipt_path)
    if receipt.get("provider_failure") is True or receipt.get("exit_code") != 0 or receipt.get("raw_response_sha256") not in (None, raw_hash):
        raise PromotionError(f"Terra generation was not completed cleanly for {row['reference']}")

    with tempfile.TemporaryDirectory(prefix="bhf-v12-source-") as temp:
        temp_dir = Path(temp)
        source_file = temp_dir / "source.json"
        source_file.write_bytes(normalized_path.read_bytes())
        # load_commentary uses the normal filename contract; a temporary
        # source directory prevents any candidate file from being modified.
        normal = temp_dir / f"{str(row['book']).lower().replace(' ', '_')}_{int(row['chapter']):03d}.json"
        normal.write_bytes(source_file.read_bytes())
        commentary = load_commentary(temp_dir, str(row["book"]), int(row["chapter"]))
    if commentary is None or commentary.reference != row["reference"]:
        raise PromotionError(f"normalized commentary cannot round-trip for {row['reference']}")
    cited_ids = {
        evidence_id
        for section in commentary.sections
        for block in section.blocks
        for evidence_id in block.evidence_ids
    }
    bundle = current_evidence_loader(str(row["book"]), int(row["chapter"]))
    if bundle is None or not cited_ids.issubset(set(bundle.evidence_by_id)):
        missing = sorted(cited_ids - set(bundle.evidence_by_id)) if bundle is not None else sorted(cited_ids)
        raise PromotionError(f"current evidence cannot resolve citations for {row['reference']}: {missing}")
    return commentary


def _validate_normalized_shape(data: dict[str, Any], reference: str) -> None:
    """Reject malformed stored responses instead of letting the loader default them."""

    allowed_root = {
        "reference", "book", "chapter", "status", "evidence_availability",
        "sections", "generated_metadata", "data_gap_fallback",
    }
    if set(data) - allowed_root or not isinstance(data.get("sections"), list):
        raise PromotionError(f"normalized commentary shape is invalid for {reference}")
    metadata = data.get("generated_metadata")
    required_metadata = {
        "evidence_hash", "evidence_bundle_version", "commentary_schema_version",
        "commentary_prompt_version", "model",
    }
    if not isinstance(metadata, dict) or not required_metadata.issubset(metadata):
        raise PromotionError(f"generated metadata shape is invalid for {reference}")
    allowed_metadata = {
        "evidence_hash", "evidence_bundle_version", "commentary_schema_version",
        "commentary_prompt_version", "model", "generated_timestamp", "synthesis_hash",
        "synthesis_schema_version", "synthesis_compiler_version", "renderer_label",
        "imported_timestamp", "candidate_id",
    }
    if set(metadata) - allowed_metadata:
        raise PromotionError(f"generated metadata shape is invalid for {reference}")
    allowed_section = {"kind", "title", "blocks"}
    allowed_block = {
        "id", "text", "verse_refs", "evidence_ids", "synthesis_ids",
        "confidence", "interpretation_level",
    }
    for section in data["sections"]:
        if not isinstance(section, dict) or set(section) - allowed_section or not isinstance(section.get("blocks"), list):
            raise PromotionError(f"normalized section shape is invalid for {reference}")
        for block in section["blocks"]:
            if not isinstance(block, dict) or set(block) - allowed_block or not {"id", "text"}.issubset(block):
                raise PromotionError(f"normalized block shape is invalid for {reference}")
            for field in ("verse_refs", "evidence_ids", "synthesis_ids"):
                if field in block and not isinstance(block[field], list):
                    raise PromotionError(f"normalized block shape is invalid for {reference}")


def _source_dir_for(row: dict[str, Any], artifact: Path, prior: Path) -> Path:
    return _find_source_dirs(artifact, prior, str(row["reference"]), str(row.get("source") or ""))[0]


def _manifest(
    rows: list[dict[str, Any]],
    published: dict[str, tuple[str, str]],
    source_data: dict[str, dict[str, Any]],
    artifact: Path,
    artifact_info: dict[str, Any],
    corpus_files: dict[str, str],
) -> dict[str, Any]:
    states = []
    for row in rows:
        ref = str(row["reference"])
        publishable = ref in published
        state, reason = _public_state(row, publishable)
        item: dict[str, Any] = {
            "reference": ref,
            "book": row["book"],
            "chapter": row["chapter"],
            "release_state": state,
            "reason": reason,
            "evidence_availability": row.get("current_availability"),
            "validated": True,
            "failure_classification": row.get("failure_classification"),
        }
        if publishable:
            filename = published[ref][0]
            item["filename"] = filename
            item["source"] = row.get("source")
            item["source_normalized_sha256"] = published[ref][1]
            if row.get("failure_classification") == "UNDER_EXPLANATION":
                item["content_gap"] = "UNDER_EXPLANATION"
        states.append(item)
    counts = Counter(item["release_state"] for item in states)
    gaps = Counter(
        str(row.get("failure_classification"))
        for row in rows
        if row.get("failure_classification") in {"UNDER_EXPLANATION", "SOURCE_LIMITED"}
    )
    base = {
        "release": RELEASE,
        "release_scope": "validated_population_only",
        "source_validation_artifact": str(artifact.relative_to(ROOT)),
        "source_validation_artifact_identity": artifact_info["manifest"].get("identity"),
        "source_validation_manifest_sha256": _sha256(artifact / "manifest.json"),
        "frozen_population_identity": artifact_info["manifest"].get("frozen_population_identity"),
        "source_commit_sha": artifact_info["manifest"].get("starting_sha"),
        "protected_contract_hashes": artifact_info["manifest"].get("protected_contract_hashes"),
        "model": MODEL,
        "effort": EFFORT,
        "validated_population_count": len(rows),
        "terra_generated_count": artifact_info["report"].get("terra_completed"),
        "published_chapter_count": len(published),
        "unavailable_not_published_count": len(rows) - len(published),
        "publication_eligibility_policy_version": POLICY_VERSION,
        "corpus_checksum_root_identity": sha256_json(corpus_files),
        "chapter_publication_index": states,
        "content_gap_summary": {
            "under_explanation_evaluated": gaps.get("UNDER_EXPLANATION", 0),
            "source_limited_evaluated": gaps.get("SOURCE_LIMITED", 0),
            "under_explanation_published": sum(item.get("content_gap") == "UNDER_EXPLANATION" for item in states),
            "publication_states": dict(sorted(counts.items())),
        },
        "routing_status": ROUTING_STATUS,
        "sol_comparison_status": SOL_STATUS,
        "checksums": RELEASE_CHECKSUMS_FILENAME,
    }
    base["manifest_identity"] = sha256_json(base)
    return base


def promote_release(
    artifact: Path = DEFAULT_ARTIFACT,
    output: Path = DEFAULT_OUTPUT,
    *,
    current_evidence_loader: Callable[[str, int], Any] | None = None,
) -> dict[str, Any]:
    """Promote exactly the proven publication intersection into ``output``."""

    info = verify_validation_artifact(artifact)
    manifest = info["manifest"]
    rows = info["population"]

    if output.exists():
        existing = output / RELEASE_MANIFEST_FILENAME
        if not existing.is_file():
            raise PromotionError(f"release output already exists without an immutable manifest: {output}")
        existing_manifest = _read(existing)
        if existing_manifest.get("release") != RELEASE or existing_manifest.get("frozen_population_identity") != manifest.get("frozen_population_identity"):
            raise PromotionError("release output identity collision")
        # Existing release directories are immutable.  Re-verify rather than
        # overwrite them; this makes a second invocation safe and explicit.
        _verify_checksum_index(output, RELEASE_CHECKSUMS_FILENAME)
        return {"status": "ALREADY_PROMOTED", "release": RELEASE, "output": str(output), "manifest": existing_manifest}

    prior = _prior_namespace(artifact, manifest)
    if current_evidence_loader is None:
        from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle

        current_evidence_loader = get_chapter_evidence_bundle

    staged_commentaries: dict[str, Any] = {}
    published: dict[str, tuple[str, str]] = {}
    for row in rows:
        if not _row_is_publishable(row):
            continue
        source_dir = _source_dir_for(row, artifact, prior)
        commentary = _validate_source(row, source_dir, str(row.get("source") or ""), current_evidence_loader)
        filename = f"{str(row['book']).lower().replace(' ', '_')}_{int(row['chapter']):03d}.json"
        staged_commentaries[str(row["reference"])] = commentary
        published[str(row["reference"])] = (filename, _sha256(source_dir / "normalized.json"))

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".commentary-v1.2-stage-", dir=output.parent))
    try:
        for reference, commentary in staged_commentaries.items():
            save_commentary(commentary, stage)
            if load_commentary(stage, commentary.book, commentary.chapter) is None:
                raise PromotionError(f"staged commentary did not round-trip for {reference}")
        corpus_files = {
            path.name: _sha256(path)
            for path in sorted(stage.glob("*.json"))
        }
        release_manifest = _manifest(rows, published, {}, artifact, info, corpus_files)
        _write_json(stage / RELEASE_MANIFEST_FILENAME, release_manifest)
        checksum_files = {
            path.name: _sha256(path)
            for path in sorted(stage.glob("*.json"))
        }
        _write_json(
            stage / RELEASE_CHECKSUMS_FILENAME,
            {"artifact_version": "commentary-v1.2-runtime-release-checksums-v1", "files": checksum_files},
        )
        os.replace(stage, output)
    except Exception:
        # The stage is private and outside the runtime path; leave no partial
        # release behind while preserving any pre-existing target.
        if stage.exists():
            for path in sorted(stage.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            stage.rmdir()
        raise
    return {"status": "PROMOTED", "release": RELEASE, "output": str(output), "manifest": release_manifest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = promote_release(args.artifact, args.output)
    print(json.dumps({"status": result["status"], "release": RELEASE, "output": result["output"], "published": result["manifest"].get("published_chapter_count")}, sort_keys=True))


if __name__ == "__main__":
    main()
