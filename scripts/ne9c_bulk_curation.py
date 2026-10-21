#!/usr/bin/env python3
"""Deterministic, resumable inventory and disposition workflow for NE-9C."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


WAVE_SIZE = 500
TRIAGE_ALGORITHM_VERSION = 2
DISPOSITIONS = {"curated", "held", "excluded"}
GENERIC_LABELS = {"related", "related-concept", "connection", "association", "same-as"}
TOPIC_TERMS = (
    ("creation_new_creation", ("creation", "eden", "chaos", "new creation", "new-creation")),
    ("covenant_exile_restoration", ("covenant", "exile", "restoration", "return", "new exodus")),
    ("temple_priesthood_presence", ("temple", "tabernacle", "sanctuary", "priest", "presence", "sacred space")),
    ("divine_assembly_nations", ("assembly", "heavenly", "divine", "angel", "nation", "sons of god")),
    ("kingship_messiah_kingdom", ("king", "messiah", "christ", "kingdom", "david", "royal")),
    ("prophetic_reception_motifs", ("prophet", "quotation", "quote", "allusion", "echo", "reception", "motif")),
    ("second_temple_reception", ("second temple", "qumran", "apocalyptic", "intertestamental")),
    ("historical_people_places_events", ("person", "place", "event", "chronology", "historical")),
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity(edge: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        edge["relationship_kind"], edge["source_id"], edge["target_id"],
        edge["original_relationship_type"], edge.get("original_notes"), edge["original_weight"],
    )


def _edge_id(identity: Sequence[Any]) -> str:
    return "edge:" + hashlib.sha256(_canonical_json(list(identity)).encode("utf-8")).hexdigest()


def _source_ids(record: Mapping[str, Any]) -> list[str]:
    values: set[str] = set()
    for source in record.get("sources", []) or []:
        if isinstance(source, Mapping) and isinstance(source.get("id"), str):
            values.add(source["id"])
    for field in ("claims", "evidence_items", "interpretive_notes"):
        for child in record.get(field, []) or []:
            if not isinstance(child, Mapping):
                continue
            for source_id in child.get("source_ids", child.get("sources", [])) or []:
                if isinstance(source_id, str) and source_id:
                    values.add(source_id)
    return sorted(values)


def _passage_context(record: Mapping[str, Any]) -> list[str]:
    references: set[str] = set()
    candidates: list[Any] = list(record.get("scripture_references", []) or [])
    for field in ("claims", "evidence_items", "interpretive_notes"):
        for child in record.get(field, []) or []:
            if isinstance(child, Mapping):
                candidates.extend(child.get("scripture_references", []) or [])
    for value in candidates:
        reference = value.get("reference") if isinstance(value, Mapping) else value
        if isinstance(reference, str) and reference.strip():
            references.add(reference.strip())
    return sorted(references)


def _topic_cluster(source: Mapping[str, Any], target: Mapping[str, Any], relation: Mapping[str, Any]) -> str:
    text = " ".join(str(value or "") for value in (
        source.get("id"), source.get("title"), source.get("type"),
        target.get("id"), target.get("title"), target.get("type"),
        relation.get("relationship"), relation.get("notes"),
    )).casefold()
    for cluster, terms in TOPIC_TERMS:
        if any(term in text for term in terms):
            return cluster
    return "other_authored_relationships"


def _priority_score(
    source: Mapping[str, Any], target: Mapping[str, Any], relation: Mapping[str, Any], source_ids: Sequence[str]
) -> int:
    label = str(relation.get("relationship") or "").casefold().replace("_", "-")
    note = str(relation.get("notes") or "").strip()
    score = 0
    if source_ids:
        score += 2
    if note:
        score += 1
    if label not in GENERIC_LABELS:
        score += 1
    types = {record.get("type") for record in (source, target)}
    if "book" not in types and types & {"event", "person", "place", "theme", "prophecy", "covenant", "biblical_theology"}:
        score += 1
    if set(_passage_context(source)) & set(_passage_context(target)):
        score += 1
    return score


def build_authored_object_relationships(objects: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Extract unique top-level object relationships without projection rows."""

    object_map = {str(record["id"]): record for record in objects if isinstance(record.get("id"), str)}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for source_id in sorted(object_map):
        source = object_map[source_id]
        for relation in source.get("related_objects", []) or []:
            if not isinstance(relation, Mapping) or not isinstance(relation.get("id"), str):
                raise ValueError(f"malformed authored object relationship on {source_id}")
            target_id = relation["id"]
            label = relation.get("relationship")
            if not isinstance(label, str) or not label:
                raise ValueError(f"authored object relationship has no label on {source_id}")
            if type(relation.get("weight")) is not int:
                raise ValueError(f"authored object relationship has invalid weight on {source_id}")
            target = object_map.get(target_id, {"id": target_id, "type": "unresolved"})
            identity = ("object", f"ckl:{source_id}", f"ckl:{target_id}", label, relation.get("notes"), relation["weight"])
            if identity in seen:
                raise ValueError(f"duplicate exact authored relationship identity: {identity!r}")
            seen.add(identity)
            reverse = any(
                isinstance(candidate, Mapping)
                and candidate.get("id") == source_id
                and candidate.get("relationship") == label
                for candidate in target.get("related_objects", []) or []
            )
            source_sources = _source_ids(source)
            target_sources = _source_ids(target)
            source_passages = _passage_context(source)
            target_passages = _passage_context(target)
            cluster = _topic_cluster(source, target, relation)
            rows.append({
                "edge_id": _edge_id(identity),
                "identity": {
                    "relationship_kind": identity[0], "source_id": identity[1], "target_id": identity[2],
                    "original_relationship_type": identity[3], "original_notes": identity[4],
                    "original_weight": identity[5],
                },
                "relationship_kind": identity[0],
                "source_id": identity[1],
                "target_id": identity[2],
                "source_type": source.get("type", "unknown"),
                "target_type": target.get("type", "unknown"),
                "original_relationship_type": label,
                "original_notes": relation.get("notes"),
                "original_weight": relation["weight"],
                "authored_direction": "reciprocal" if reverse else "one_way",
                "source_available": bool(source_sources),
                "target_available": bool(target_sources),
                "source_record_source_ids": source_sources,
                "target_record_source_ids": target_sources,
                "source_passage_context": source_passages,
                "target_passage_context": target_passages,
                "passage_context_basis": "owner-record context only; not relationship applicability",
                "topic_cluster": cluster,
                "priority_score": _priority_score(source, target, relation, source_sources + target_sources),
                "reader_relevance_basis": "deterministic triage heuristic only; not a scholarly classification",
            })
    return rows


def partition_relationship_waves(
    relationships: Iterable[Mapping[str, Any]], wave_size: int = WAVE_SIZE
) -> list[list[dict[str, Any]]]:
    """Return deterministic waves, each containing at most ``wave_size`` edges."""

    if type(wave_size) is not int or wave_size <= 0:
        raise ValueError("wave size must be a positive integer")
    ordered = sorted((dict(edge) for edge in relationships), key=lambda edge: (
        -int(edge.get("priority_score", 0)),
        str(edge.get("topic_cluster", "")),
        min(edge.get("source_passage_context", []) + edge.get("target_passage_context", []) or [""]),
        not bool(edge.get("source_available") or edge.get("target_available")),
        str(edge.get("source_type", "")), str(edge.get("target_type", "")),
        str(edge.get("original_relationship_type", "")), str(edge.get("edge_id", "")),
    ))
    ids = [edge.get("edge_id") for edge in ordered]
    if any(not isinstance(edge_id, str) or not edge_id for edge_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("inventory contains a missing or duplicate edge ID")
    return [ordered[offset:offset + wave_size] for offset in range(0, len(ordered), wave_size)]


def validate_disposition_decision(edge: Mapping[str, Any], decision: Mapping[str, Any]) -> None:
    """Validate a reviewed disposition and exact curation identity if curated."""

    disposition = decision.get("disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError("review disposition must be curated, held, or excluded")
    if not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
        raise ValueError("review disposition requires a reason")
    if not isinstance(decision.get("research_notes"), str) or not decision["research_notes"].strip():
        raise ValueError("review disposition requires research notes")
    research_sources = decision.get("research_sources", [])
    if not isinstance(research_sources, list) or any(not isinstance(source, str) or not source for source in research_sources):
        raise ValueError("review disposition has invalid research source references")
    if disposition != "curated":
        if decision.get("curation") is not None:
            raise ValueError("held and excluded decisions cannot carry a curation payload")
        return
    curation = decision.get("curation")
    if not isinstance(curation, Mapping):
        raise ValueError("curated disposition requires a curation payload with exact authored identity")
    expected = _identity(edge)
    actual = _identity(curation) if all(key in curation for key in (
        "relationship_kind", "source_id", "target_id", "original_relationship_type", "original_weight"
    )) else None
    if actual != expected or curation.get("authored_direction") != edge.get("authored_direction"):
        raise ValueError("curation payload does not match the exact authored identity and direction")
    from bhf_agent.presentation.narrative_explorer_curations import validate_curation

    validate_curation(curation, require_authored_direction=True)


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def _object_tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((root / "objects").rglob("*.json")):
        if not path.is_file() or path.name.startswith("_"):
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_object_records(root: Path) -> list[dict[str, Any]]:
    objects = []
    for path in sorted((root / "objects").rglob("*.json")):
        if path.name.startswith("_"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError(f"malformed CKL object record: {path}")
        objects.append(record)
    if len({record["id"] for record in objects}) != len(objects):
        raise ValueError("CKL object inventory contains duplicate IDs")
    return objects


def _current_curation_identities() -> set[tuple[Any, ...]]:
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS, _identity as curation_identity

    return {curation_identity(entry) for entry in CURATED_RELATIONSHIPS if entry["relationship_kind"] == "object"}


def _current_object_curation_edge_ids() -> list[str]:
    return sorted(_edge_id(identity) for identity in _current_curation_identities())


def _baseline_object_curation_edge_ids(source_root: Path) -> list[str]:
    legacy_root = source_root / "framework/canonical_library/curations/narrative-explorer/ne9c/wave-legacy"
    identities = []
    for path in sorted(legacy_root.glob("batch-*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for entry in document.get("curations", []):
            if entry.get("relationship_kind") == "object":
                identities.append(_edge_id(_identity(entry)))
    if len(identities) != len(set(identities)):
        raise ValueError("legacy curation files contain duplicate exact identities")
    return sorted(identities)


def _upgrade_checkpoint(source_root: Path, state_dir: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    if "initial_curated_object_edge_ids" not in checkpoint:
        baseline = _baseline_object_curation_edge_ids(source_root)
        if len(baseline) != checkpoint.get("existing_curation_count"):
            raise ValueError("checkpoint lacks its starting curation identities and legacy baseline count disagrees")
        checkpoint["initial_curated_object_edge_ids"] = baseline
        _atomic_write(state_dir / "checkpoint.json", json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return checkpoint


def _persist_curation_entry(
    source_root: Path, wave_number: int, topic_cluster: str, entry: Mapping[str, Any]
) -> str:
    curation_root = source_root / "framework/canonical_library/curations/narrative-explorer/ne9c"
    identity = _identity(entry)
    for path in sorted(curation_root.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for existing in document.get("curations", []):
            if _identity(existing) == identity:
                if _canonical_json(existing) != _canonical_json(entry):
                    raise ValueError("curation data already contains conflicting metadata for this exact identity")
                return path.relative_to(source_root).as_posix()
    safe_cluster = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in topic_cluster.casefold()
    ).strip("-") or "other"
    path = curation_root / f"wave-{wave_number:04d}" / f"{safe_cluster}.json"
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
    else:
        document = {"schema_version": 1, "wave": wave_number, "topic_cluster": topic_cluster, "curations": []}
    document["curations"].append(dict(entry))
    document["curations"].sort(key=lambda item: _canonical_json(list(_identity(item))))
    _atomic_write(path, json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return path.relative_to(source_root).as_posix()


def _curation_relative_path(wave_number: int, topic_cluster: str) -> str:
    safe_cluster = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in topic_cluster.casefold()
    ).strip("-") or "other"
    return (Path("framework/canonical_library/curations/narrative-explorer/ne9c")
            / f"wave-{wave_number:04d}" / f"{safe_cluster}.json").as_posix()


def _normalize_decision(
    edge: Mapping[str, Any], wave_number: int, decision: Mapping[str, Any]
) -> dict[str, Any]:
    normalized = dict(decision)
    validate_disposition_decision(edge, normalized)
    normalized.update({
        "edge_id": edge["edge_id"],
        "authored_identity": edge["identity"],
        "authored_direction": edge["authored_direction"],
        "reviewer_type": "machine_assisted",
        "human_scholarly_approval": "not_recorded",
    })
    if normalized["disposition"] == "curated":
        normalized["curation_data_path"] = _curation_relative_path(wave_number, edge["topic_cluster"])
        normalized["curation_topic_cluster"] = edge["topic_cluster"]
    return normalized


def _persist_curation_batch(source_root: Path, decisions: Sequence[Mapping[str, Any]]) -> None:
    """Persist curation payloads grouped by wave and topic cluster."""

    root = source_root / "framework/canonical_library/curations/narrative-explorer/ne9c"
    documents: dict[Path, dict[str, Any]] = {}
    identities: dict[tuple[Any, ...], tuple[dict[str, Any], Path]] = {}
    for path in sorted(root.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        documents[path] = document
        for entry in document.get("curations", []):
            identity = _identity(entry)
            if identity in identities:
                raise ValueError("curation data contains duplicate exact authored identities")
            identities[identity] = (entry, path)

    changed: set[Path] = set()
    for decision in decisions:
        if decision["disposition"] != "curated":
            continue
        entry = dict(decision["curation"])
        identity = _identity(entry)
        target = source_root / decision["curation_data_path"]
        existing = identities.get(identity)
        if existing:
            if _canonical_json(existing[0]) != _canonical_json(entry):
                raise ValueError("curation data already contains conflicting metadata for this exact identity")
            if existing[1].relative_to(source_root).as_posix() != decision["curation_data_path"]:
                raise ValueError("curation data path changed while recovering a batch transaction")
            continue
        if target not in documents:
            documents[target] = {
                "schema_version": 1,
                "wave": int(Path(decision["curation_data_path"]).parent.name.removeprefix("wave-")),
                "topic_cluster": decision["curation_topic_cluster"],
                "curations": [],
            }
        document = documents[target]
        document["curations"].append(entry)
        document["curations"].sort(key=lambda item: _canonical_json(list(_identity(item))))
        identities[identity] = (entry, target)
        changed.add(target)

    for path in sorted(changed):
        _atomic_write(path, json.dumps(documents[path], ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _commit_batch_transaction(source_root: Path, state_dir: Path) -> dict[str, Any]:
    transaction_path = state_dir / "pending-batch.json"
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    decisions = transaction["decisions"]
    _persist_curation_batch(source_root, decisions)
    current = _load_decisions(state_dir)
    by_id = {item["edge_id"]: item for item in current}
    for decision in decisions:
        existing = by_id.get(decision["edge_id"])
        if existing is not None:
            if existing != decision:
                raise ValueError(f"relationship already has a conflicting disposition: {decision['edge_id']}")
            continue
        current.append(decision)
        by_id[decision["edge_id"]] = decision
    current.sort(key=lambda item: item["edge_id"])
    _atomic_write(state_dir / "decisions.jsonl", "".join(_canonical_json(item) + "\n" for item in current))
    checkpoint = json.loads((state_dir / "checkpoint.json").read_text(encoding="utf-8"))
    refreshed = _refresh_checkpoint(state_dir, checkpoint)
    transaction_path.unlink()
    return refreshed


def record_decisions(
    source_root: Path,
    state_dir: Path,
    submissions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate and checkpoint a resumable slice of reviewed dispositions."""

    transaction_path = state_dir / "pending-batch.json"
    if transaction_path.exists():
        _commit_batch_transaction(source_root, state_dir)
    checkpoint = json.loads((state_dir / "checkpoint.json").read_text(encoding="utf-8"))
    waves = _load_waves(state_dir, checkpoint)
    edge_map = {
        row["edge_id"]: (number, row)
        for number, rows in waves.items()
        for row in rows
    }
    current = _load_decisions(state_dir)
    current_by_id = {item["edge_id"]: item for item in current}
    normalized: list[dict[str, Any]] = []
    submitted_ids: set[str] = set()
    for submission in submissions:
        if not isinstance(submission, Mapping):
            raise ValueError("batch submission must contain edge_id and decision")
        edge_id = submission.get("edge_id")
        if not isinstance(edge_id, str) or edge_id not in edge_map:
            raise ValueError(f"unknown uncategorized authored relationship: {edge_id}")
        if edge_id in submitted_ids:
            raise ValueError(f"batch repeats a relationship identity: {edge_id}")
        submitted_ids.add(edge_id)
        wave_number, edge = edge_map[edge_id]
        decision = submission.get("decision")
        if not isinstance(decision, Mapping):
            raise ValueError(f"batch decision is malformed: {edge_id}")
        item = _normalize_decision(edge, wave_number, decision)
        existing = current_by_id.get(edge_id)
        if existing is not None and existing != item:
            raise ValueError(f"relationship already has a conflicting disposition: {edge_id}")
        normalized.append(item)

    if not normalized:
        return _refresh_checkpoint(state_dir, checkpoint)
    pending = [item for item in normalized if item["edge_id"] not in current_by_id]
    if not pending:
        return _refresh_checkpoint(state_dir, checkpoint)
    _atomic_write(transaction_path, json.dumps({"schema_version": 1, "decisions": pending},
                                                ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return _commit_batch_transaction(source_root, state_dir)


def _base_connection_type(label: str) -> str:
    from bhf_agent.presentation.narrative_explorer import _CONNECTION_TYPE_BY_LABEL, _normalized_label

    return _CONNECTION_TYPE_BY_LABEL.get(_normalized_label(label), "uncategorized")


def _load_decisions(state_dir: Path) -> list[dict[str, Any]]:
    path = state_dir / "decisions.jsonl"
    if not path.exists():
        return []
    decisions = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [decision.get("edge_id") for decision in decisions]
    if len(ids) != len(set(ids)):
        raise ValueError("checkpoint contains duplicate relationship decisions")
    return decisions


def _load_waves(state_dir: Path, checkpoint: Mapping[str, Any]) -> dict[int, list[dict[str, Any]]]:
    waves: dict[int, list[dict[str, Any]]] = {}
    for manifest in checkpoint["waves"]:
        number = int(manifest["wave"])
        path = state_dir / manifest["path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
            raise ValueError(f"wave {number} has changed since checkpoint creation")
        waves[number] = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        if len(waves[number]) != manifest["relationship_count"]:
            raise ValueError(f"wave {number} row count differs from checkpoint")
    return waves


def _refresh_checkpoint(state_dir: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    waves = _load_waves(state_dir, checkpoint)
    decisions = _load_decisions(state_dir)
    decisions_by_id = {decision["edge_id"]: decision for decision in decisions}
    counts = collections.Counter(decision["disposition"] for decision in decisions)
    all_wave_ids: set[str] = set()
    completed: list[int] = []
    current = None
    for number, rows in sorted(waves.items()):
        ids = {row["edge_id"] for row in rows}
        if all_wave_ids & ids:
            raise ValueError("wave inventory repeats an edge identity")
        all_wave_ids.update(ids)
        if ids <= decisions_by_id.keys():
            completed.append(number)
        elif current is None:
            current = number
    unknown = decisions_by_id.keys() - all_wave_ids
    if unknown:
        raise ValueError(f"checkpoint contains decisions for unknown edges: {sorted(unknown)[:3]}")
    checkpoint.update({
        "reviewed_relationship_count": len(decisions),
        "disposition_counts": {key: counts.get(key, 0) for key in sorted(DISPOSITIONS)},
        "completed_wave_numbers": completed,
        "current_wave": current,
        "review_complete": len(decisions) == checkpoint["backlog_relationship_count"],
    })
    _atomic_write(state_dir / "checkpoint.json", json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return checkpoint


def initialize_inventory(source_root: Path, state_dir: Path, wave_size: int = WAVE_SIZE) -> dict[str, Any]:
    """Inventory CKL relationships and persist immutable deterministic waves."""

    ckl_root = source_root / "framework" / "canonical_library"
    object_hash = _object_tree_hash(ckl_root)
    checkpoint_path = state_dir / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("object_source_tree_sha256") != object_hash:
            raise ValueError("protected CKL source fingerprint changed since the checkpoint")
        if checkpoint.get("triage_algorithm_version") == TRIAGE_ALGORITHM_VERSION:
            checkpoint = _upgrade_checkpoint(source_root, state_dir, checkpoint)
            return _refresh_checkpoint(state_dir, checkpoint)
        if _load_decisions(state_dir):
            raise ValueError("triage algorithm changed after review began; preserve the current checkpoint")
        for manifest in checkpoint.get("waves", []):
            (state_dir / manifest["path"]).unlink(missing_ok=True)
        checkpoint_path.unlink()

    objects = _load_object_records(ckl_root)
    rows = build_authored_object_relationships(objects)
    if len(rows) != 4061:
        raise ValueError(f"expected the audited 4,061 authored object relationships, found {len(rows)}")
    curated = _current_curation_identities()
    mapped_counts: collections.Counter[str] = collections.Counter()
    backlog = []
    curation_covered = 0
    curation_overlay_classified = 0
    for row in rows:
        base_type = _base_connection_type(row["original_relationship_type"])
        mapped_counts[base_type] += 1
        if _identity(row) in curated:
            curation_covered += 1
            if base_type == "uncategorized":
                curation_overlay_classified += 1
        elif base_type == "uncategorized":
            backlog.append(row)
    expected_backlog = mapped_counts.get("uncategorized", 0) - curation_overlay_classified
    if len(backlog) != expected_backlog:
        raise ValueError("derived uncategorized relationship count disagrees with exact curation identities")

    wave_groups = partition_relationship_waves(backlog, wave_size=wave_size)
    manifests = []
    for number, group in enumerate(wave_groups, 1):
        relative = Path("waves") / f"wave-{number:04d}.jsonl"
        raw = "".join(_canonical_json(row) + "\n" for row in group).encode("utf-8")
        path = state_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        manifests.append({
            "wave": number, "path": relative.as_posix(), "relationship_count": len(group),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "topic_cluster_counts": dict(sorted(collections.Counter(row["topic_cluster"] for row in group).items())),
        })
    checkpoint = {
        "schema_version": 1,
        "workflow": "ne9c-scholarly-relationship-curation",
        "triage_algorithm_version": TRIAGE_ALGORITHM_VERSION,
        "inventory_complete": True,
        "review_complete": False,
        "inventory_relationship_count": len(rows),
        "backlog_relationship_count": len(backlog),
        "base_taxonomy_classified_count": len(rows) - mapped_counts.get("uncategorized", 0),
        "existing_curation_count": curation_covered,
        "curation_overlay_classified_count": curation_overlay_classified,
        "initial_curated_object_edge_ids": _current_object_curation_edge_ids(),
        "base_projection_type_counts": dict(sorted(mapped_counts.items())),
        "object_source_tree_sha256": object_hash,
        "wave_size": wave_size,
        "waves": manifests,
        "reviewed_relationship_count": 0,
        "disposition_counts": {key: 0 for key in sorted(DISPOSITIONS)},
        "completed_wave_numbers": [],
        "current_wave": 1 if manifests else None,
    }
    _atomic_write(checkpoint_path, json.dumps(checkpoint, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return checkpoint


def record_decision(source_root: Path, state_dir: Path, edge_id: str, decision: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint = json.loads((state_dir / "checkpoint.json").read_text(encoding="utf-8"))
    waves = _load_waves(state_dir, checkpoint)
    edge = next((row for rows in waves.values() for row in rows if row["edge_id"] == edge_id), None)
    if edge is None:
        raise ValueError(f"unknown uncategorized authored relationship: {edge_id}")
    normalized = dict(decision)
    validate_disposition_decision(edge, normalized)
    normalized.update({
        "edge_id": edge_id,
        "authored_identity": edge["identity"],
        "authored_direction": edge["authored_direction"],
        "reviewer_type": "machine_assisted",
        "human_scholarly_approval": "not_recorded",
    })
    if normalized["disposition"] == "curated":
        wave = next(number for number, rows in waves.items() if any(row["edge_id"] == edge_id for row in rows))
        normalized["curation_data_path"] = _persist_curation_entry(
            source_root, wave, edge["topic_cluster"], normalized["curation"]
        )
    current = _load_decisions(state_dir)
    existing = next((item for item in current if item["edge_id"] == edge_id), None)
    if existing is not None:
        if existing == normalized:
            return _refresh_checkpoint(state_dir, checkpoint)
        raise ValueError(f"relationship already has a conflicting disposition: {edge_id}")
    current.append(normalized)
    current.sort(key=lambda item: item["edge_id"])
    _atomic_write(state_dir / "decisions.jsonl", "".join(_canonical_json(item) + "\n" for item in current))
    return _refresh_checkpoint(state_dir, checkpoint)


def _validate_curation_provenance(entry: Mapping[str, Any], objects: Sequence[Mapping[str, Any]]) -> None:
    from framework.canonical_library.scripture import build_book_alias_lookup, parse_scripture_references

    object_map = {str(obj["id"]): obj for obj in objects}
    source_records: dict[tuple[str, str], Mapping[str, Any]] = {}
    known_records = {f"ckl:{object_id}" for object_id in object_map}
    for object_id, obj in object_map.items():
        for source in obj.get("sources", []) or []:
            if isinstance(source, Mapping) and isinstance(source.get("id"), str):
                source_records[(object_id, source["id"])] = source
                known_records.add(f"ckl:{object_id}#source:{source['id']}")
        for kind in ("claims", "evidence_items"):
            record_kind = "claim" if kind == "claims" else "evidence"
            for child in obj.get(kind, []) or []:
                if isinstance(child, Mapping) and isinstance(child.get("id"), str):
                    known_records.add(f"ckl:{object_id}#{record_kind}:{child['id']}")
    bibliography_ids: set[str] = set()
    for support in entry["supporting_ckl_sources"]:
        object_id, source_id = support["object_id"], support["source_id"]
        source = source_records.get((object_id, source_id))
        if source is None:
            raise ValueError(f"supporting CKL source does not resolve: {object_id}/{source_id}")
        bibliography_ids.add(source_id)
        for field in ("title", "author", "year"):
            if field in support and source.get(field) != support[field]:
                raise ValueError(f"supporting CKL bibliography disagrees with source record {object_id}/{source_id}")
    for record_id in entry["supporting_records"]:
        if record_id not in known_records:
            raise ValueError(f"supporting CKL record does not resolve: {record_id}")
    for material in entry.get("supporting_comparative_material", []):
        if material.get("source_id") not in bibliography_ids:
            raise ValueError("comparative material source does not resolve through supporting CKL bibliography")
    aliases = build_book_alias_lookup(())
    for reference in entry["applicable_passages"] + entry["supporting_passages"]:
        if not parse_scripture_references(reference, book_alias_lookup=aliases):
            raise ValueError(f"invalid Scripture passage reference: {reference}")


def validate_inventory(source_root: Path, state_dir: Path) -> dict[str, Any]:
    checkpoint = json.loads((state_dir / "checkpoint.json").read_text(encoding="utf-8"))
    checkpoint = _upgrade_checkpoint(source_root, state_dir, checkpoint)
    current_hash = _object_tree_hash(source_root / "framework" / "canonical_library")
    if checkpoint.get("object_source_tree_sha256") != current_hash:
        raise ValueError("protected CKL source fingerprint changed")
    waves = _load_waves(state_dir, checkpoint)
    all_rows = [row for rows in waves.values() for row in rows]
    if len(all_rows) != checkpoint["backlog_relationship_count"]:
        raise ValueError("wave inventory count differs from checkpoint")
    if len({row["edge_id"] for row in all_rows}) != len(all_rows):
        raise ValueError("wave inventory contains duplicate authored relationship IDs")
    decisions = _load_decisions(state_dir)
    by_id = {row["edge_id"]: row for row in all_rows}
    decisions_by_id = {decision["edge_id"]: decision for decision in decisions}
    for decision in decisions:
        edge = by_id.get(decision.get("edge_id"))
        if edge is None or decision.get("authored_identity") != edge["identity"]:
            raise ValueError("disposition identity disagrees with the current wave inventory")
        validate_disposition_decision(edge, decision)
    from bhf_agent.presentation.narrative_explorer_curations import CURATED_RELATIONSHIPS

    current_curations = {
        _edge_id(_identity(entry)): entry
        for entry in CURATED_RELATIONSHIPS
        if entry["relationship_kind"] == "object"
    }
    initial_ids = set(checkpoint.get("initial_curated_object_edge_ids", []))
    object_records = _load_object_records(source_root / "framework/canonical_library")
    for curated_id, entry in current_curations.items():
        if curated_id not in initial_ids:
            decision = decisions_by_id.get(curated_id)
            if decision is None or decision.get("disposition") != "curated":
                raise ValueError(f"new machine curation lacks a reviewed checkpoint disposition: {curated_id}")
        _validate_curation_provenance(entry, object_records)
    for decision in decisions:
        if decision.get("disposition") == "curated":
            entry = current_curations.get(decision["edge_id"])
            if entry is None or _canonical_json(entry) != _canonical_json(decision.get("curation")):
                raise ValueError("curated disposition and version-controlled curation data disagree")
    refreshed = _refresh_checkpoint(state_dir, checkpoint)
    return {
        "validation_status": "passed",
        "inventory_relationship_count": checkpoint["inventory_relationship_count"],
        "backlog_relationship_count": len(all_rows),
        "reviewed_relationship_count": refreshed["reviewed_relationship_count"],
        "disposition_counts": refreshed["disposition_counts"],
        "current_wave": refreshed["current_wave"],
    }


def _status(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {key: checkpoint.get(key) for key in (
        "inventory_complete", "review_complete", "inventory_relationship_count",
        "backlog_relationship_count", "reviewed_relationship_count", "disposition_counts",
        "completed_wave_numbers", "current_wave", "object_source_tree_sha256",
    )}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--state-dir", type=Path, default=Path("docs/narrative-explorer/ne9c-bulk-curation"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inventory", help="create or verify deterministic 500-edge waves")
    commands.add_parser("status", help="show durable inventory and review checkpoint")
    next_parser = commands.add_parser("next", help="show the first incomplete wave")
    next_parser.add_argument("--limit", type=int, default=20)
    record_parser = commands.add_parser("record", help="record one reviewed edge disposition from JSON")
    record_parser.add_argument("edge_id")
    record_parser.add_argument("--decision-json", type=Path, required=True)
    batch_parser = commands.add_parser("record-batch", help="record a validated resumable slice from JSON")
    batch_parser.add_argument("--submissions-json", type=Path, required=True)
    commands.add_parser("validate", help="validate fingerprints, identities, waves, and decisions")
    args = parser.parse_args(argv)
    source_root = args.source_root.resolve()
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    state_dir = args.state_dir
    try:
        if args.command == "inventory":
            result = initialize_inventory(source_root, state_dir)
        else:
            checkpoint_path = state_dir / "checkpoint.json"
            if not checkpoint_path.exists():
                raise ValueError("inventory checkpoint is missing; run the inventory command first")
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if args.command == "status":
                result = _status(_refresh_checkpoint(state_dir, checkpoint))
            elif args.command == "next":
                checkpoint = _refresh_checkpoint(state_dir, checkpoint)
                number = checkpoint.get("current_wave")
                if number is None:
                    result = {"status": "complete", "review_complete": True}
                else:
                    wave = next(item for item in checkpoint["waves"] if item["wave"] == number)
                    rows = _load_waves(state_dir, checkpoint)[number]
                    decisions = {item["edge_id"] for item in _load_decisions(state_dir)}
                    result = {
                        "wave": number, "relationship_count": len(rows),
                        "reviewed_count": sum(row["edge_id"] in decisions for row in rows),
                        "remaining_count": sum(row["edge_id"] not in decisions for row in rows),
                        "path": wave["path"], "sample": [row for row in rows if row["edge_id"] not in decisions][:max(0, args.limit)],
                    }
            elif args.command == "record":
                decision = json.loads(args.decision_json.read_text(encoding="utf-8"))
                result = _status(record_decision(source_root, state_dir, args.edge_id, decision))
            elif args.command == "record-batch":
                payload = json.loads(args.submissions_json.read_text(encoding="utf-8"))
                if not isinstance(payload, Mapping) or not isinstance(payload.get("decisions"), list):
                    raise ValueError("batch JSON must contain a decisions array")
                result = _status(record_decisions(source_root, state_dir, payload["decisions"]))
            else:
                result = validate_inventory(source_root, state_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"NE-9C bulk curation stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
