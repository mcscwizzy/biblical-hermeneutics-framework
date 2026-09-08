"""Canonical inventory and historical-versus-production census."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from bhf_agent import bible

from .models import (
    BLOCKED,
    COMPLETE,
    GATE_QUALITY_FAIL,
    GATE_WARNING,
    PENDING,
    QUARANTINED,
    STALE_INPUT,
    production_root,
)


def canonical_chapters() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for book in bible.list_books():
        for chapter in range(1, int(book.get("chapters", 0)) + 1):
            ordinal += 1
            rows.append(
                {
                    "reference": bible.verse_range_reference(book["name"], chapter),
                    "book": book["name"],
                    "chapter": chapter,
                    "canonical_ordinal": ordinal,
                    "chapter_count_in_book": int(book.get("chapters", 0)),
                    "status": PENDING,
                }
            )
    return rows


def _references_in_json(value: Any, known: set[str], found: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "reference" and isinstance(child, str) and child in known:
                found.add(child)
            _references_in_json(child, known, found)
    elif isinstance(value, list):
        for child in value:
            _references_in_json(child, known, found)


def historical_experiment_references(repo_root: Path, known: set[str]) -> dict[str, set[str]]:
    candidates = repo_root / ".bhf-data" / "bhf-commentary-candidates"
    result: dict[str, set[str]] = {
        "scale_pilot": set(),
        "dense_reader": set(),
        "other_experiments": set(),
    }
    if not candidates.is_dir():
        return result
    for directory in sorted(candidates.iterdir()):
        if not directory.is_dir():
            continue
        if directory.name == "commentary-v1.5-scale-pilot":
            bucket = "scale_pilot"
        elif directory.name == "commentary-dense-reader-v0.1":
            bucket = "dense_reader"
        elif directory.name.startswith(("commentary-v1.2", "commentary-v1.3", "commentary-v1.4", "commentary-v1.5")):
            bucket = "other_experiments"
        else:
            continue
        for path in sorted(directory.rglob("*.json")):
            if bucket == "scale_pilot" and path != directory / "scale-pilot-manifest.json":
                continue
            if bucket == "dense_reader" and path != directory / "manifest.json":
                continue
            relative_parts = path.relative_to(directory).parts
            # Evaluation summaries can describe the whole eligible corpus;
            # they are not generation artifacts and must not make every
            # chapter look experimental.  Keep the same narrow rule used by
            # the completed scale-pilot selector.
            if "manifest" not in path.name and not any(
                part in {"packets", "prompts", "synthesis", "responses", "manual-render"}
                for part in relative_parts
            ):
                continue
            try:
                _references_in_json(json.loads(path.read_text(encoding="utf-8")), known, result[bucket])
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
    return result


def _production_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    runs = root / "runs"
    if not runs.is_dir():
        return records
    for state_path in sorted(runs.glob("*/batches/*/state.json")):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for reference, record in (state.get("chapters") or {}).items():
            candidate = {**record, "run_id": state.get("run_id"), "batch_id": state.get("batch_id")}
            previous = records.get(reference)
            if previous is None or (str(candidate.get("run_id")), str(candidate.get("batch_id"))) > (str(previous.get("run_id")), str(previous.get("batch_id"))):
                records[reference] = candidate
    return records


def build_census(repo_root: Path, *, canonical: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = [dict(row) for row in (canonical or canonical_chapters())]
    known = {row["reference"] for row in rows}
    historical = historical_experiment_references(repo_root, known)
    production = _production_records(production_root(repo_root))
    for row in rows:
        reference = row["reference"]
        history: list[str] = []
        if reference in historical["scale_pilot"]:
            history.append("scale_pilot")
        if reference in historical["dense_reader"]:
            history.append("dense_reader")
        if reference in historical["other_experiments"]:
            history.append("other_experiment")
        record = production.get(reference)
        row["historical_status"] = (
            "scale_pilot_and_experimental" if "scale_pilot" in history and len(history) > 1
            else "scale_pilot_only" if history == ["scale_pilot"]
            else "experimental_only" if history else "none"
        )
        row["historical_artifacts"] = history
        row["production_complete"] = bool(record and record.get("state") == COMPLETE)
        if record:
            row["status"] = record.get("state", PENDING)
            row["production"] = record
        else:
            row["status"] = PENDING
    counts = Counter(row["status"] for row in rows)
    history_counts = Counter(row["historical_status"] for row in rows)
    return {
        "artifact_version": "commentary-production-census-v1",
        "canonical_chapter_count": len(rows),
        "counts": dict(sorted(counts.items())),
        "historical_counts": dict(sorted(history_counts.items())),
        "production_complete_count": sum(row["production_complete"] for row in rows),
        "experimental_chapter_count": sum(bool(row["historical_artifacts"]) for row in rows),
        "chapters": rows,
    }


def status_summary(census: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_chapters": census["canonical_chapter_count"],
        "production_complete": census["production_complete_count"],
        "pending": census["counts"].get(PENDING, 0),
        "gate_warnings": census["counts"].get(GATE_WARNING, 0),
        "quality_fails": census["counts"].get(GATE_QUALITY_FAIL, 0),
        "quarantined": census["counts"].get(QUARANTINED, 0),
        "stale": census["counts"].get(STALE_INPUT, 0),
        "blocked": census["counts"].get(BLOCKED, 0),
        "historical_experimental_only": census["historical_counts"].get("experimental_only", 0),
        "historical_scale_pilot_only": census["historical_counts"].get("scale_pilot_only", 0),
    }
