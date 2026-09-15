"""Build and verify the explicitly versioned current Commentary v1.2 lineage.

Historical renderer qualification artifacts are immutable observations.  This
module creates a separate source-contract baseline after intentional changes
to evidence applicability and canonical Scripture boundaries.  It never calls
a model or mutates historical artifact namespaces.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from bhf_agent import bible
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    audit_ancestry_envelope,
    build_ancestry_envelope,
)
from bhf_agent.chapter_commentary.reader_level_projection import (
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.reader_provenance_binding import (
    audit_provenance_binding,
    build_provenance_binding,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_POLICY_VERSION_V3,
    cluster_synthesis_units,
)
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import canonical_json, sha256_bytes, sha256_json, slug, write_immutable


CURRENT_LINEAGE_VERSION = "commentary-v1.2-current-source-lineage-v2"
CURRENT_LINEAGE_REL = Path(".bhf-data/bhf-commentary-candidates") / CURRENT_LINEAGE_VERSION
HISTORICAL_QUALIFICATION_REL = Path(
    ".bhf-data/bhf-commentary-candidates/"
    "renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31"
)
HISTORICAL_SCALE_REL = Path(
    ".bhf-data/bhf-commentary-candidates/"
    "commentary-v1.2-scale-pilot-922472547555015a3ced"
)
EVIDENCE_APPLICABILITY_COMMIT = "5c00d961809dbdfe652af0d5908d53831a05c8ca"
ASV_BOUNDARY_COMMIT = "3522c0dbf748e2edca2f2ce68d52dcf3ea584833"


class CurrentLineageError(RuntimeError):
    """The current source baseline cannot be built or verified safely."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentLineageError(f"invalid lineage input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CurrentLineageError(f"lineage input must be an object: {path}")
    return value


def load_manifest(repo_root: Path) -> dict[str, Any]:
    """Load the frozen current baseline without reconstructing it.

    Consumers of the current qualification contract deliberately use this
    function rather than an historical pilot namespace.  Rebuilding is an
    explicit operator action (`verify`), never an implicit fixture refresh.
    """

    manifest = _read(repo_root / CURRENT_LINEAGE_REL / "manifest.json")
    expected = sha256_json({key: value for key, value in manifest.items() if key != "manifest_identity"})
    if manifest.get("manifest_identity") != expected:
        raise CurrentLineageError("current lineage manifest identity mismatch")
    if manifest.get("artifact_version") != CURRENT_LINEAGE_VERSION:
        raise CurrentLineageError("unsupported current lineage artifact version")
    if manifest.get("current_source_contract") is not True:
        raise CurrentLineageError("lineage is not marked as the current source contract")
    return manifest


def record_context(repo_root: Path, kind: str, reference: str) -> dict[str, Any]:
    """Load one immutable current-lineage record and verify its local hashes."""

    if kind not in {"qualification", "scale_pilot"}:
        raise CurrentLineageError(f"unsupported lineage population: {kind}")
    manifest = load_manifest(repo_root)
    try:
        row = next(item for item in manifest[kind]["chapters"] if item["reference"] == reference)
    except StopIteration as exc:
        raise CurrentLineageError(f"{reference} is not in current {kind} lineage") from exc
    record_root = repo_root / CURRENT_LINEAGE_REL / ("scale-pilot" if kind == "scale_pilot" else kind) / "chapters" / slug(row["book"], int(row["chapter"]))
    values = {
        "source_packet": _read(record_root / "source-packet.json"),
        "projection": _read(record_root / "projection.json"),
        "envelope": _read(record_root / "ancestry-envelope.json"),
        "envelope_audit": _read(record_root / "ancestry-audit.json"),
        "binding": _read(record_root / "provenance-binding.json"),
        "binding_audit": _read(record_root / "provenance-binding-audit.json"),
        "receipt": _read(record_root / "receipt.json"),
        "system_prompt": (record_root / "system_prompt.txt").read_text(encoding="utf-8"),
        "source_prompt": (record_root / "source-user-prompt.txt").read_text(encoding="utf-8"),
        "candidate_prompt": (record_root / "user_prompt.txt").read_text(encoding="utf-8"),
    }
    if values["receipt"] != row:
        raise CurrentLineageError(f"current lineage receipt disagrees for {reference}")
    checks = {
        "projection_hash": values["projection"].get("projection_hash"),
        "ancestry_envelope_hash": values["envelope"].get("envelope_hash"),
        "provenance_binding_hash": values["binding"].get("binding_hash"),
        "system_prompt_sha256": sha256_bytes(values["system_prompt"].encode("utf-8")),
        "source_user_prompt_sha256": sha256_bytes(values["source_prompt"].encode("utf-8")),
        "candidate_input_sha256": sha256_bytes(values["candidate_prompt"].encode("utf-8")),
    }
    if any(row.get(key) != value for key, value in checks.items()):
        raise CurrentLineageError(f"current lineage record identity mismatch for {reference}")
    if not values["envelope_audit"].get("valid") or not values["binding_audit"].get("valid"):
        raise CurrentLineageError(f"current lineage audit is invalid for {reference}")
    return {"manifest": manifest, "row": row, "root": record_root, **values}


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _projection(prepared: Any) -> Any:
    chapter = bible.resolve_chapter(prepared.synthesis.book, prepared.synthesis.chapter)
    text = bible.passage_text(chapter["verses"])
    clusters = cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=text,
    )
    return project_reader_level_ideas(
        prepared.synthesis, clusters, prepared.bundle.evidence_items
    )


def _current_contract(old: dict[str, Any]) -> dict[str, Any]:
    prepared = prepare_chapter(old["book"], int(old["chapter"]))
    projection = _projection(prepared)
    projection_dict = projection.to_dict()
    envelope = build_ancestry_envelope(
        projection_dict, prepared.synthesis, prepared.bundle.evidence_items
    )
    envelope_audit = audit_ancestry_envelope(
        envelope, projection_dict, prepared.synthesis
    )
    if not envelope_audit.get("valid"):
        raise CurrentLineageError(f"current ancestry envelope is invalid for {old['reference']}")
    binding = build_provenance_binding(envelope)
    binding_audit = audit_provenance_binding(binding, envelope)
    if not binding_audit.get("valid"):
        raise CurrentLineageError(f"current provenance binding is invalid for {old['reference']}")
    chapter = bible.resolve_chapter(old["book"], int(old["chapter"]))
    canonical_text = bible.passage_text(chapter["verses"])
    prompt_version = str(old.get("prompt_version") or "1.7")
    system_prompt = system_prompt_for_version(prompt_version)
    source_prompt = build_user_prompt(
        old["reference"], old["book"], int(old["chapter"]), canonical_text,
        prepared.synthesis, prepared.bundle, prepared.synthesis.evidence_availability,
        prompt_version=prompt_version,
    )
    candidate_prompt = add_projection_to_prompt(source_prompt, projection)
    identity = prepared.row["input_identity"]
    return {
        "prepared": prepared,
        "projection": projection_dict,
        "envelope": envelope,
        "envelope_audit": envelope_audit,
        "binding": binding,
        "binding_audit": binding_audit,
        "system_prompt": system_prompt,
        "source_prompt": source_prompt,
        "candidate_prompt": candidate_prompt,
        "identity": identity,
    }


def _reason(old: dict[str, Any], current: dict[str, Any]) -> str:
    evidence_changed = old.get("evidence_hash") != current["identity"]["evidence_hash"]
    synthesis_changed = old.get("synthesis_hash") != current["identity"]["synthesis_hash"]
    if evidence_changed and synthesis_changed:
        return "SOURCE_BOUNDARY_REBASE"
    if synthesis_changed:
        return "EVIDENCE_APPLICABILITY_REBASE"
    return "UNCHANGED"


def _row(old: dict[str, Any], current: dict[str, Any], *, qualification: bool) -> dict[str, Any]:
    identity = current["identity"]
    packet = current["prepared"].packet
    result = {
        **{key: value for key, value in old.items() if key not in {
            "source_packet_id", "source_packet_hash", "source_packet_file_sha256",
            "evidence_hash", "synthesis_hash", "projection_hash", "ancestry_envelope_hash",
            "candidate_input_sha256", "system_prompt_sha256", "packet_id", "packet_hash",
        }},
        "source_packet_id": identity["packet_id"],
        "source_packet_hash": identity["packet_hash"],
        "source_packet_file_sha256": sha256_bytes((canonical_json(packet) + "\n").encode("utf-8")),
        "evidence_hash": identity["evidence_hash"],
        "synthesis_hash": identity["synthesis_hash"],
        "synthesis_unit_count": len(current["prepared"].synthesis.synthesis_units),
        "evidence_availability": current["prepared"].synthesis.evidence_availability,
        "evidence_count": len(current["prepared"].bundle.evidence_items),
        "projection_hash": current["projection"]["projection_hash"],
        "ancestry_envelope_hash": current["envelope"]["envelope_hash"],
        "provenance_binding_hash": current["binding"]["binding_hash"],
        "system_prompt_sha256": sha256_bytes(current["system_prompt"].encode("utf-8")),
        "source_user_prompt_sha256": sha256_bytes(current["source_prompt"].encode("utf-8")),
        "candidate_input_sha256": sha256_bytes(current["candidate_prompt"].encode("utf-8")),
        "migration_reason": _reason(old, current),
        "historical_identity": {
            key: old.get(key) for key in (
                "evidence_hash", "synthesis_hash", "source_packet_id", "source_packet_hash",
                "projection_hash", "ancestry_envelope_hash",
            )
        },
    }
    if qualification:
        result["qualification_candidate"] = True
    return result


def build(repo_root: Path) -> dict[str, Any]:
    old_qualification = _read(repo_root / HISTORICAL_QUALIFICATION_REL / "qualification-manifest.json")
    old_scale = _read(repo_root / HISTORICAL_SCALE_REL / "manifest.json")
    qualification_records = [
        (row, _current_contract(row)) for row in old_qualification["chapters"]
    ]
    scale_records = [(row, _current_contract(row)) for row in old_scale["chapters"]]
    qualification_rows = [_row(old, current, qualification=True) for old, current in qualification_records]
    scale_rows = [_row(old, current, qualification=False) for old, current in scale_records]
    source_hashes = {
        "prompt": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/prompts.py").read_bytes()),
        "projection": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()),
        "ancestry_envelope": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py").read_bytes()),
        "provenance_binding": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_provenance_binding.py").read_bytes()),
        "synthesis_compiler": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/synthesis/compiler.py").read_bytes()),
        "canonical_asv": sha256_bytes((repo_root / "bhf_agent/data/asv_bible.json").read_bytes()),
    }
    manifest = {
        "artifact_version": CURRENT_LINEAGE_VERSION,
        "pipeline_version": "commentary-v1.2-enrichment",
        "current_source_contract": True,
        "historical_artifacts_preserved": True,
        "supersedes": {
            "qualification_id": old_qualification["qualification_id"],
            "qualification_manifest_identity": old_qualification["manifest_identity"],
            "scale_pilot_namespace": old_scale["namespace"],
            "scale_pilot_manifest_identity": old_scale["manifest_identity"],
            "reason": "current deterministic source semantics changed after the historical snapshots",
            "lineage_commits": [EVIDENCE_APPLICABILITY_COMMIT, ASV_BOUNDARY_COMMIT],
        },
        "contracts": {
            "synthesis_compiler_version": "1.1",
            "evidence_applicability_policy": "commentary-evidence-applicability-v1",
            "prompt_version": "1.7",
            "source_hashes": source_hashes,
            "qualification_contracts": old_qualification["contract_versions"],
            "frozen_scoring_contracts": old_scale["frozen_scoring_contracts"],
            "projection_version": old_scale["projection_version"],
            "ancestry_envelope_version": old_scale["ancestry_envelope_version"],
            "provenance_binding_version": "reader-provenance-binding-v1",
        },
        "qualification": {
            "baseline_id": "commentary-v1.2-current-qualification-v1",
            "chapter_count": len(qualification_rows),
            "chapters": qualification_rows,
        },
        "scale_pilot": {
            "baseline_id": "commentary-v1.2-current-scale-pilot-v1",
            "chapter_count": len(scale_rows),
            "batch_sizes": old_scale["batch_sizes"],
            "chapters": scale_rows,
        },
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {
        "manifest": manifest,
        "qualification_records": qualification_records,
        "scale_records": scale_records,
    }


def prepare(repo_root: Path) -> dict[str, Any]:
    context = build(repo_root)
    root = repo_root / CURRENT_LINEAGE_REL
    manifest = context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "supersession.json", {
        "artifact_version": f"{CURRENT_LINEAGE_VERSION}-supersession-v1",
        "manifest_identity": manifest["manifest_identity"],
        **manifest["supersedes"],
    })
    for kind, records in (("qualification", context["qualification_records"]), ("scale-pilot", context["scale_records"])):
        for old, current in records:
            stem = slug(old["book"], int(old["chapter"]))
            row = next(item for item in manifest["qualification" if kind == "qualification" else "scale_pilot"]["chapters"] if item["reference"] == old["reference"])
            record_root = root / kind / "chapters" / stem
            _write_json(record_root / "source-packet.json", current["prepared"].packet)
            _write_json(record_root / "projection.json", current["projection"])
            _write_json(record_root / "ancestry-envelope.json", current["envelope"])
            _write_json(record_root / "ancestry-audit.json", current["envelope_audit"])
            _write_json(record_root / "provenance-binding.json", current["binding"])
            _write_json(record_root / "provenance-binding-audit.json", current["binding_audit"])
            _write_text(record_root / "system_prompt.txt", current["system_prompt"])
            _write_text(record_root / "source-user-prompt.txt", current["source_prompt"])
            _write_text(record_root / "user_prompt.txt", current["candidate_prompt"])
            _write_json(record_root / "receipt.json", row)
    changes = {
        kind: Counter(row["migration_reason"] for row in manifest[key]["chapters"])
        for kind, key in (("qualification", "qualification"), ("scale_pilot", "scale_pilot"))
    }
    report = {
        "artifact_version": f"{CURRENT_LINEAGE_VERSION}-migration-report-v1",
        "manifest_identity": manifest["manifest_identity"],
        "qualification": {"changes": dict(sorted(changes["qualification"].items())), "chapters": manifest["qualification"]["chapters"]},
        "scale_pilot": {"changes": dict(sorted(changes["scale_pilot"].items())), "chapters": manifest["scale_pilot"]["chapters"]},
        "unexplained_differences": [],
    }
    _write_json(root / "migration-report.json", report)
    return {"root": str(root), "manifest_identity": manifest["manifest_identity"], "report": report}


def verify(repo_root: Path) -> dict[str, Any]:
    stored = load_manifest(repo_root)
    current = build(repo_root)["manifest"]
    if stored != current:
        raise CurrentLineageError("current deterministic source no longer matches the frozen lineage baseline")
    return {"status": "CURRENT_LINEAGE_VALID", "manifest_identity": stored["manifest_identity"]}
