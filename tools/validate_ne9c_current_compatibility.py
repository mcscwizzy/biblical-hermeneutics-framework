#!/usr/bin/env python3
"""Read-only current-state compatibility checks for protected NE-9C/NE-10 data.

This validator is intentionally separate from ``scripts/ne9c_bulk_curation.py
validate``. It preserves hashes of the reviewed curation artifacts and checks
their exact identities against current CKL relationships while allowing
unrelated CKL evidence/source metadata to evolve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from bhf_agent.presentation.narrative_explorer_curations import (
    _identity as curation_identity,
    validate_curation,
)
from bhf_agent.presentation.narrative_explorer_passages import (
    validate_passage_bridge_registry,
)
from scripts.ne9c_bulk_curation import (
    DISPOSITIONS,
    _canonical_json,
    _identity,
    _load_decisions,
    _load_object_records,
    _load_waves,
    _object_tree_hash,
    _validate_curation_provenance,
    build_authored_object_relationships,
    validate_disposition_decision,
)


HISTORICAL_OBJECT_TREE_SHA256 = (
    "e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766"
)
EXPECTED_SHA256 = {
    "docs/narrative-explorer/ne9c-bulk-curation/checkpoint.json":
        "0f8e4f690bd701be2856fc5af1a304f864163f7a8adc896b760d0c95b349c6f9",
    "docs/narrative-explorer/ne9c-bulk-curation/decisions.jsonl":
        "5aefd69b89c69f0d941babbd5ea4f7e8fbb5c8065907cfeab1025c2f1fd41826",
    "framework/canonical_library/curations/narrative-explorer/ne10/passage-bridges.json":
        "8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b",
    "framework/canonical_library/curations/narrative-explorer/ne10/research-candidates-held.json":
        "15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3",
}
EXPECTED_NE9C_TREE_SHA256 = (
    "623acf40bc03c9689387164679802716dec7436aec8baec0ba8d791b45171676"
)
EXPECTED_AUTHORED_EDGE_ID_SHA256 = (
    "1c14dfa5f306ff8e649564ca7bab6abf3b784ad15217da333ffc38306fd76dcd"
)
EXPECTED_HELD_CANDIDATE_IDS = {
    "deuteronomy-32-psalm-82-job-1-divine-assembly",
    "exodus-12-1-corinthians-5-passover",
    "ezekiel-37-john-3-water-spirit",
    "ezekiel-40-48-revelation-21-22-temple",
    "genesis-2-3-revelation-21-22-eden-tree-life",
    "isaiah-43-exodus-12-15-new-exodus",
    "psalm-110-acts-2-enthronement",
}
EXPECTED_COUNTS = {
    "authored_relationships": 4061,
    "reviewed_relationships": 3925,
    "initial_curated_object_relationships": 23,
    "object_curations": 431,
    "all_runtime_curations": 433,
    "verified_bridges": 44,
    "held_candidates": 7,
}
EXPECTED_DISPOSITION_COUNTS = {"curated": 408, "excluded": 1622, "held": 1895}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path, repository_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.json")):
        if path.is_file():
            digest.update(path.relative_to(repository_root).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _load_runtime_curations(root: Path) -> list[dict[str, Any]]:
    curation_root = root / "framework/canonical_library/curations/narrative-explorer/ne9c"
    entries: list[dict[str, Any]] = []
    for path in sorted(curation_root.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, Mapping) or document.get("schema_version") != 1:
            raise ValueError(f"unsupported NE-9C runtime curation document: {path}")
        curations = document.get("curations")
        if not isinstance(curations, list):
            raise ValueError(f"NE-9C runtime curation document has no curation list: {path}")
        for entry in curations:
            if not isinstance(entry, Mapping):
                raise ValueError(f"malformed NE-9C runtime curation entry: {path}")
            validate_curation(entry, require_authored_direction=True)
            entries.append(dict(entry))
    identities = [curation_identity(entry) for entry in entries]
    if len(identities) != len(set(identities)):
        raise ValueError("NE-9C runtime registry repeats an exact relationship identity")
    return entries


def _verify_protected_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative, expected in EXPECTED_SHA256.items():
        path = root / relative
        if not path.is_file():
            raise ValueError(f"protected artifact is missing: {relative}")
        observed = _file_sha256(path)
        if observed != expected:
            raise ValueError(f"protected artifact hash changed: {Path(relative).name}")
        hashes[relative] = observed
    curation_root = root / "framework/canonical_library/curations/narrative-explorer/ne9c"
    if not curation_root.is_dir():
        raise ValueError("protected NE-9C runtime registry directory is missing")
    ne9c_hash = _tree_sha256(curation_root, root)
    if ne9c_hash != EXPECTED_NE9C_TREE_SHA256:
        raise ValueError("protected artifact hash changed: NE-9C runtime registry")
    hashes["framework/canonical_library/curations/narrative-explorer/ne9c/"] = ne9c_hash
    return hashes


def validate_current_compatibility(repository_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Validate protected curation state against current CKL without writes."""

    root = Path(repository_root).resolve()
    protected_hashes = _verify_protected_hashes(root)
    state_root = root / "docs/narrative-explorer/ne9c-bulk-curation"
    checkpoint = json.loads((state_root / "checkpoint.json").read_text(encoding="utf-8"))
    expected_decisions = _load_decisions(state_root)
    waves = _load_waves(state_root, checkpoint)
    rows = [row for number in sorted(waves) for row in waves[number]]
    row_by_id = {row["edge_id"]: row for row in rows}
    if len(rows) != checkpoint.get("backlog_relationship_count"):
        raise ValueError("historical wave identities do not match the protected checkpoint count")
    if len(row_by_id) != len(rows):
        raise ValueError("historical wave files repeat a reviewed relationship identity")
    if len(expected_decisions) != EXPECTED_COUNTS["reviewed_relationships"]:
        raise ValueError("protected review ledger has an unexpected decision count")
    decision_by_id = {decision["edge_id"]: decision for decision in expected_decisions}
    if set(decision_by_id) != set(row_by_id):
        raise ValueError("reviewed decision identities do not equal the protected wave identities")

    current_objects = _load_object_records(root / "framework/canonical_library")
    current_relationships = build_authored_object_relationships(current_objects)
    current_by_id = {edge["edge_id"]: edge for edge in current_relationships}
    if len(current_by_id) != EXPECTED_COUNTS["authored_relationships"]:
        raise ValueError("current CKL authored relationship count changed")
    authored_id_digest = hashlib.sha256(
        _canonical_json(sorted(current_by_id)).encode("utf-8")
    ).hexdigest()
    if authored_id_digest != EXPECTED_AUTHORED_EDGE_ID_SHA256:
        raise ValueError("stable authored relationship ID set changed")

    disposition_counts: Counter[str] = Counter()
    for edge_id, decision in decision_by_id.items():
        historical_edge = row_by_id[edge_id]
        current_edge = current_by_id.get(edge_id)
        if current_edge is None:
            raise ValueError(f"reviewed authored relationship no longer exists: {edge_id}")
        if decision.get("authored_identity") != historical_edge.get("identity"):
            raise ValueError(f"review ledger identity differs from its historical row: {edge_id}")
        if current_edge.get("identity") != historical_edge.get("identity"):
            raise ValueError(f"reviewed authored identity changed in current CKL: {edge_id}")
        validate_disposition_decision(current_edge, decision)
        if decision.get("human_scholarly_approval") != "not_recorded":
            raise ValueError(f"machine curation claims human approval: {edge_id}")
        disposition_counts[str(decision["disposition"])] += 1
    normalized_counts = {key: disposition_counts.get(key, 0) for key in sorted(DISPOSITIONS)}
    if normalized_counts != EXPECTED_DISPOSITION_COUNTS:
        raise ValueError("protected held/excluded/curated dispositions changed")
    if checkpoint.get("disposition_counts") != EXPECTED_DISPOSITION_COUNTS:
        raise ValueError("protected checkpoint disposition counts disagree with the ledger")
    if checkpoint.get("reviewed_relationship_count") != EXPECTED_COUNTS["reviewed_relationships"]:
        raise ValueError("protected checkpoint reviewed relationship count changed")

    runtime_curations = _load_runtime_curations(root)
    runtime_object_curations = {
        _identity(entry): entry
        for entry in runtime_curations
        if entry.get("relationship_kind") == "object"
    }
    runtime_object_ids = {
        "edge:" + hashlib.sha256(_canonical_json(list(identity)).encode("utf-8")).hexdigest()
        for identity in runtime_object_curations
    }
    initial_ids = set(checkpoint.get("initial_curated_object_edge_ids", []))
    if len(initial_ids) != EXPECTED_COUNTS["initial_curated_object_relationships"]:
        raise ValueError("protected initial curation identity count changed")
    ledger_curated_ids = {
        edge_id
        for edge_id, decision in decision_by_id.items()
        if decision["disposition"] == "curated"
    }
    if runtime_object_ids != initial_ids | ledger_curated_ids:
        raise ValueError("current runtime curation identities disagree with reviewed curation dispositions")
    for edge_id in initial_ids:
        if edge_id not in runtime_object_ids:
            raise ValueError(f"protected initial runtime curation is missing: {edge_id}")
    for edge_id in ledger_curated_ids:
        runtime_entry = runtime_object_curations.get(_identity(decision_by_id[edge_id]["curation"]))
        if runtime_entry is None or _canonical_json(runtime_entry) != _canonical_json(
            decision_by_id[edge_id]["curation"]
        ):
            raise ValueError(f"reviewed curation payload differs from runtime registry: {edge_id}")
    for entry in runtime_curations:
        _validate_curation_provenance(entry, current_objects)
    if len(runtime_object_ids) != EXPECTED_COUNTS["object_curations"]:
        raise ValueError("current runtime object curation count changed")
    if len(runtime_curations) != EXPECTED_COUNTS["all_runtime_curations"]:
        raise ValueError("current runtime curation record count changed")

    object_map = {record["id"]: record for record in current_objects}
    bridge_path = root / "framework/canonical_library/curations/narrative-explorer/ne10/passage-bridges.json"
    bridge_document = json.loads(bridge_path.read_text(encoding="utf-8"))
    if bridge_document.get("schema_version") != 1 or not isinstance(bridge_document.get("bridges"), list):
        raise ValueError("NE-10 bridge registry schema is invalid")
    verified_bridge_count = validate_passage_bridge_registry(
        bridge_document["bridges"], object_map.get
    )
    if verified_bridge_count != EXPECTED_COUNTS["verified_bridges"]:
        raise ValueError("verified NE-10 bridge identity count changed")

    held_path = root / "framework/canonical_library/curations/narrative-explorer/ne10/research-candidates-held.json"
    held_document = json.loads(held_path.read_text(encoding="utf-8"))
    held_ids = {
        candidate.get("id")
        for candidate in held_document.get("candidates", [])
        if isinstance(candidate, Mapping)
    }
    if held_document.get("status") != "research_candidates_only_excluded_from_confirmed_passage_graph":
        raise ValueError("NE-10 held candidates no longer remain excluded from the confirmed passage graph")
    if held_ids != EXPECTED_HELD_CANDIDATE_IDS:
        raise ValueError("protected NE-10 held candidate identities changed")

    current_object_hash = _object_tree_hash(root / "framework/canonical_library")
    historical_hash = checkpoint.get("object_source_tree_sha256")
    if historical_hash != HISTORICAL_OBJECT_TREE_SHA256:
        raise ValueError("frozen historical CKL fingerprint in the checkpoint changed")
    return {
        "validation_status": "passed",
        "validator": "current-state-ne9c-ne10-compatibility-v1",
        "read_only": True,
        "historical_ckl_fingerprint_matches": current_object_hash == historical_hash,
        "historical_ckl_fingerprint": historical_hash,
        "current_ckl_object_tree_sha256": current_object_hash,
        "protected_artifact_hashes": protected_hashes,
        "authored_relationship_count": len(current_relationships),
        "authored_relationship_id_sha256": authored_id_digest,
        "reviewed_relationship_count": len(expected_decisions),
        "disposition_counts": normalized_counts,
        "runtime_object_curation_count": len(runtime_object_ids),
        "runtime_curation_record_count": len(runtime_curations),
        "verified_bridge_count": verified_bridge_count,
        "held_candidate_count": len(held_ids),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT, help="repository root")
    args = parser.parse_args(argv)
    try:
        report = validate_current_compatibility(args.root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Current curation compatibility failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
