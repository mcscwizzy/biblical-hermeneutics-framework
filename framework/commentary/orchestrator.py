"""Deterministic Commentary v1.1 pipeline orchestration.

The evidence and prose tools remain the authorities for their respective
artifacts.  This module owns only workflow state, stage gates, handoffs, and
safe transitions between those tools.  State is content-addressed and written
atomically so an interrupted invocation cannot look like a completed stage.

The command line entry point is::

    python -m framework.commentary.orchestrator status

Long-running evidence work is delegated to the existing resumable
``tools.commentary_v11_scaled_preflight`` runner.  The orchestrator records a
RUNNING stage before delegation and only promotes the state after artifact
validation succeeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
SCALE_ROOT_REL = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale")
STATE_REL = SCALE_ROOT_REL / "pipeline-state.json"
SCHEMA_VERSION = 1
PIPELINE_VERSION = "commentary-v1.1"
STATE_HASH_FIELD = "state_hash"
BATCH_RE = re.compile(r"^batch-(\d{3,})$")

ACTIVE = "ACTIVE"
BLOCKED = "BLOCKED"
CORPUS_COMPLETE = "CORPUS_COMPLETE"

PENDING = "PENDING"
RUNNING = "RUNNING"
OUTPUT_WRITTEN = "OUTPUT_WRITTEN"
OUTPUT_VALIDATED = "OUTPUT_VALIDATED"
COMPLETE = "COMPLETE"

STAGE_ORDER = (
    "BATCH_PENDING",
    "CANDIDATE_SELECTION",
    "EVIDENCE_PREFLIGHT",
    "EVIDENCE_CERTIFICATION",
    "EVIDENCE_LOCKED",
    "READY_FOR_GENERATION",
    "PROSE_GENERATION",
    "POST_GENERATION_AUDIT",
    "PROSE_CERTIFICATION",
    "BATCH_COMPLETE",
)
TERMINAL_STAGES = {CORPUS_COMPLETE}

EXIT_CODES = {
    "ADVANCED": 0,
    "STAGE_COMPLETE": 0,
    "RESUME_REQUIRED": 10,
    "MODEL_HANDOFF_REQUIRED": 11,
    "BLOCKED": 12,
    "CORPUS_COMPLETE": 13,
}


class PipelineError(RuntimeError):
    """A safe, actionable orchestration error."""


class StateCorruptionError(PipelineError):
    """The state file failed its content-addressed integrity check."""


@dataclass(frozen=True)
class StageDefinition:
    name: str
    prerequisite: str | None
    expected_inputs: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    mutates_prose: bool
    mutates_evidence: bool
    resumable: bool
    requires_llm: bool
    required_model: str
    required_effort: str
    blocking_gates: tuple[str, ...]
    completion_criteria: str


STAGES: dict[str, StageDefinition] = {
    "BATCH_PENDING": StageDefinition(
        "BATCH_PENDING", None, (), (), False, False, False, False,
        "none", "none", (), "A batch number and work directory exist.",
    ),
    "CANDIDATE_SELECTION": StageDefinition(
        "CANDIDATE_SELECTION", "BATCH_PENDING", ("prior protected fingerprints",),
        ("work/selection.json",), False, False, True, True, "luna", "high",
        ("candidate identity", "exclusion policy", "stable ordering"),
        "A complete selection checkpoint or a validated final candidate pool exists.",
    ),
    "EVIDENCE_PREFLIGHT": StageDefinition(
        "EVIDENCE_PREFLIGHT", "CANDIDATE_SELECTION", ("work/selection.json",),
        ("preflight-report.json",), False, True, True, True, "luna", "high",
        ("all candidates evaluated", "routing", "provenance", "semantic audit", "hash integrity"),
        "Every selected candidate has a deterministic PASS, QUARANTINE, or DATA_GAP disposition.",
    ),
    "EVIDENCE_CERTIFICATION": StageDefinition(
        "EVIDENCE_CERTIFICATION", "EVIDENCE_PREFLIGHT", ("preflight-report.json",),
        ("evidence-certification.json",), False, True, True, True, "luna", "high",
        ("JSON/SQLite identity", "locked evidence IDs", "backend hashes", "availability"),
        "The evidence certification is LOCKED and contains only final passing chapters.",
    ),
    "EVIDENCE_LOCKED": StageDefinition(
        "EVIDENCE_LOCKED", "EVIDENCE_CERTIFICATION", ("evidence-certification.json",),
        ("batch-manifest.json", "terra-input-manifest.json"), False, True, True, True,
        "luna", "high", ("final lock", "protected fingerprints", "prose-free Terra input"),
        "The batch manifest is LOCKED and the Terra input is READY_FOR_TERRA.",
    ),
    "READY_FOR_GENERATION": StageDefinition(
        "READY_FOR_GENERATION", "EVIDENCE_LOCKED", ("terra-input-manifest.json",),
        (), False, False, False, True, "terra", "medium", ("locked evidence",),
        "A structured Terra handoff is emitted without invoking a generation adapter.",
    ),
    "PROSE_GENERATION": StageDefinition(
        "PROSE_GENERATION", "READY_FOR_GENERATION", ("terra-input-manifest.json",),
        ("terra/chapters/*.json",), True, False, False, True, "terra", "medium",
        ("locked evidence only", "no new evidence", "prose provenance"),
        "The externally executed Terra stage has produced outputs for every locked chapter.",
    ),
    "POST_GENERATION_AUDIT": StageDefinition(
        "POST_GENERATION_AUDIT", "PROSE_GENERATION", ("terra/chapters/*.json",),
        ("post-generation-report.json",), False, False, True, False,
        "existing-certification-policy", "existing", ("provenance", "unsupported claims", "duplicates"),
        "The existing post-generation audit reports GO or an explicit terminal disposition.",
    ),
    "PROSE_CERTIFICATION": StageDefinition(
        "PROSE_CERTIFICATION", "POST_GENERATION_AUDIT", ("post-generation-report.json",),
        ("prose-certification.json",), False, False, True, False,
        "existing-certification-policy", "existing", ("protected fingerprints", "lock revalidation"),
        "Every selected final chapter reaches the release policy's allowed terminal state.",
    ),
    "BATCH_COMPLETE": StageDefinition(
        "BATCH_COMPLETE", "PROSE_CERTIFICATION", ("prose-certification.json",), (), False, False,
        False, False, "none", "none", (), "The certified batch is recorded before the next batch is initialized.",
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _state_hash(state: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in state.items() if key != STATE_HASH_FIELD}
    return _sha256_bytes(_canonical(payload).encode("utf-8"))


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_text(path, _canonical(payload) + "\n")


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def state_path(repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / STATE_REL


def _batch_id(number: int) -> str:
    return f"batch-{number:03d}"


def _batch_root(repo_root: Path, number: int) -> Path:
    return repo_root / SCALE_ROOT_REL / _batch_id(number)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PipelineError(f"expected JSON object: {path}")
    return value


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PipelineError(f"pipeline state does not exist: {path}; run init") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise StateCorruptionError(f"pipeline state cannot be parsed: {path}: {exc}") from exc
    if not isinstance(state, dict) or state.get(STATE_HASH_FIELD) != _state_hash(state):
        raise StateCorruptionError(f"pipeline state hash mismatch: {path}")
    _validate_state_shape(state)
    return state


def save_state(path: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(state)
    stage = updated.get("current_stage")
    if stage in STAGES:
        definition = STAGES[stage]
        updated["required_model"] = definition.required_model
        updated["required_effort"] = definition.required_effort
        updated["resumable"] = definition.resumable
    updated["can_advance"] = updated.get("status") == ACTIVE and updated.get("current_stage") != CORPUS_COMPLETE
    updated["human_intervention_required"] = updated.get("status") == BLOCKED or updated.get("current_stage") in {"READY_FOR_GENERATION", "PROSE_GENERATION"}
    updated["updated_at"] = _now()
    updated[STATE_HASH_FIELD] = _state_hash(updated)
    _atomic_json(path, updated)
    return updated


def _validate_state_shape(state: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "pipeline_version", "status", "current_batch", "current_stage",
        "stage_status", "last_completed_batch", "eligible_corpus_total", "finalized_chapters",
        "remaining_chapters", "required_model", "required_effort", "resumable",
        "resume_token", "last_successful_checkpoint", "blocked_reason", "protected_fingerprints",
        "history", "completed_stages", "can_advance", "human_intervention_required",
        "updated_at", STATE_HASH_FIELD,
    }
    missing = sorted(required.difference(state))
    if missing:
        raise StateCorruptionError(f"pipeline state missing fields: {', '.join(missing)}")
    if state["schema_version"] != SCHEMA_VERSION or state["pipeline_version"] != PIPELINE_VERSION:
        raise StateCorruptionError("unsupported pipeline state schema or version")
    if state["status"] not in {ACTIVE, BLOCKED, CORPUS_COMPLETE}:
        raise StateCorruptionError(f"invalid pipeline status: {state['status']}")
    if state["current_stage"] not in set(STAGE_ORDER) | TERMINAL_STAGES:
        raise StateCorruptionError(f"invalid current stage: {state['current_stage']}")
    if state["stage_status"] not in {PENDING, RUNNING, OUTPUT_WRITTEN, OUTPUT_VALIDATED, COMPLETE}:
        raise StateCorruptionError(f"invalid stage status: {state['stage_status']}")
    for key in ("current_batch", "last_completed_batch", "eligible_corpus_total", "finalized_chapters", "remaining_chapters"):
        if not isinstance(state[key], int) or state[key] < 0:
            raise StateCorruptionError(f"invalid non-negative integer field: {key}")
    if not isinstance(state["protected_fingerprints"], dict):
        raise StateCorruptionError("protected_fingerprints must be an object")
    if not isinstance(state["completed_stages"], list):
        raise StateCorruptionError("completed_stages must be a list")
    if not isinstance(state["can_advance"], bool) or not isinstance(state["human_intervention_required"], bool):
        raise StateCorruptionError("can_advance and human_intervention_required must be booleans")
    if state["status"] == CORPUS_COMPLETE and state["current_stage"] != CORPUS_COMPLETE:
        raise StateCorruptionError("CORPUS_COMPLETE status requires CORPUS_COMPLETE stage")


def _batch_numbers(repo_root: Path) -> list[int]:
    root = repo_root / SCALE_ROOT_REL
    if not root.exists():
        return []
    numbers = []
    for path in root.iterdir():
        match = BATCH_RE.match(path.name)
        if match and path.is_dir():
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def _protected_roots(repo_root: Path) -> list[Path]:
    roots = [
        repo_root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra/chapters",
        repo_root / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-terra/supplemental-integrity-controls/chapters",
    ]
    completed_batches = [
        number for number in _batch_numbers(repo_root)
        if (_read_json(_batch_root(repo_root, number) / "prose-certification.json") or {}).get("status") == "GO"
    ]
    latest_certified = max(completed_batches, default=0)
    for number in _batch_numbers(repo_root):
        batch = _batch_root(repo_root, number)
        # Batch 001 and Batch 002 predate the standalone prose-certification
        # report, but their Terra chapter files are protected release prose.
        # Once a later batch is certified, numbered earlier Terra roots are
        # protected as well.  A current unfinished batch is never included.
        if latest_certified and number <= latest_certified and list((batch / "terra/chapters").glob("*.json")):
            roots.append(batch / "terra/chapters")
    return roots


def collect_protected_fingerprints(repo_root: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for root in _protected_roots(repo_root):
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            fingerprints[str(path.relative_to(repo_root))] = _sha256_file(path)
    return fingerprints


def _protected_changes(repo_root: Path, expected: Mapping[str, str]) -> list[dict[str, str]]:
    changes = []
    for relative, digest in sorted(expected.items()):
        path = repo_root / relative
        actual = _sha256_file(path) if path.exists() else None
        if actual != digest:
            changes.append({"path": relative, "expected": digest, "actual": actual or "MISSING"})
    return changes


def _current_population(repo_root: Path) -> int:
    values: list[int] = []
    for number in _batch_numbers(repo_root):
        manifest = _read_json(_batch_root(repo_root, number) / "batch-manifest.json")
        population = (manifest or {}).get("current_population", {})
        if isinstance(population, dict) and isinstance(population.get("eligible"), int):
            values.append(population["eligible"])
    return values[-1] if values else 0


def _finalized_count(repo_root: Path, fingerprints: Mapping[str, str]) -> int:
    return len(fingerprints)


def _stage_from_artifacts(repo_root: Path, number: int) -> str:
    batch = _batch_root(repo_root, number)
    manifest = _read_json(batch / "batch-manifest.json")
    preflight = _read_json(batch / "preflight-report.json")
    certification = _read_json(batch / "evidence-certification.json")
    terra_input = _read_json(batch / "terra-input-manifest.json")
    prose_certification = _read_json(batch / "prose-certification.json")
    post_generation = _read_json(batch / "post-generation-report.json")
    if prose_certification and prose_certification.get("status") == "GO":
        return "BATCH_COMPLETE"
    if post_generation and post_generation.get("status") in {"GO", "NO_GO"}:
        return "PROSE_CERTIFICATION"
    if prose_certification is not None or (batch / "terra/chapters").exists():
        return "POST_GENERATION_AUDIT"
    if terra_input and terra_input.get("status") == "READY_FOR_TERRA" and not terra_input.get("prose_included"):
        return "READY_FOR_GENERATION"
    if certification and certification.get("status") == "LOCKED":
        return "EVIDENCE_LOCKED"
    if preflight is not None:
        return "EVIDENCE_CERTIFICATION"
    if manifest and manifest.get("status") not in {"LOCKED", None}:
        return "EVIDENCE_PREFLIGHT"
    work = repo_root / SCALE_ROOT_REL / f".{_batch_id(number)}.work"
    if (work / "selection.json").exists():
        return "EVIDENCE_PREFLIGHT"
    return "CANDIDATE_SELECTION"


def _stage_requirements(stage: str) -> StageDefinition:
    try:
        return STAGES[stage]
    except KeyError as exc:
        raise PipelineError(f"no stage definition for {stage}") from exc


def _expected_model(stage: str) -> tuple[str, str]:
    definition = _stage_requirements(stage)
    return definition.required_model, definition.required_effort


def _batch_evidence_refs(batch: Path) -> set[str]:
    certification = _read_json(batch / "evidence-certification.json") or {}
    return {str(row.get("reference")) for row in certification.get("chapters", []) if row.get("reference")}


def _validate_batch_artifacts(repo_root: Path, number: int, stage: str) -> list[str]:
    """Validate only deterministic local gates; do not rebuild CKL evidence here."""

    batch = _batch_root(repo_root, number)
    errors: list[str] = []
    manifest = _read_json(batch / "batch-manifest.json")
    preflight = _read_json(batch / "preflight-report.json")
    certification = _read_json(batch / "evidence-certification.json")
    terra_input = _read_json(batch / "terra-input-manifest.json")

    if stage in {"EVIDENCE_PREFLIGHT", "EVIDENCE_CERTIFICATION", "EVIDENCE_LOCKED", "READY_FOR_GENERATION"}:
        if manifest is None:
            errors.append("missing batch-manifest.json")
        if preflight is None:
            errors.append("missing preflight-report.json")
    if stage in {"EVIDENCE_CERTIFICATION", "EVIDENCE_LOCKED", "READY_FOR_GENERATION"}:
        if certification is None:
            errors.append("missing evidence-certification.json")
        elif certification.get("status") != "LOCKED":
            errors.append("evidence-certification.json is not LOCKED")
        elif any(row.get("status") is not None and row.get("status") != "PASS" for row in certification.get("chapters", [])):
            errors.append("final evidence certification contains a non-PASS chapter")
    if stage in {"EVIDENCE_LOCKED", "READY_FOR_GENERATION"}:
        if manifest is None or manifest.get("status") != "LOCKED":
            errors.append("batch-manifest.json is not LOCKED")
        if terra_input is None:
            errors.append("missing terra-input-manifest.json")
        else:
            if terra_input.get("status") != "READY_FOR_TERRA":
                errors.append("Terra input is not READY_FOR_TERRA")
            if terra_input.get("prose_included") is not False:
                errors.append("Terra input must be prose-free")
            expected = _batch_evidence_refs(batch)
            actual = {str(row.get("reference")) for row in terra_input.get("chapters", []) if row.get("reference")}
            if expected != actual:
                errors.append("Terra input references disagree with evidence certification")
    if stage == "CANDIDATE_SELECTION":
        work = repo_root / SCALE_ROOT_REL / f".{_batch_id(number)}.work"
        selection = _read_json(work / "selection.json")
        pool = (manifest or {}).get("candidate_pool", []) if manifest else []
        if not selection and not pool:
            errors.append("candidate selection checkpoint is incomplete")
    if stage == "PROSE_GENERATION":
        if terra_input is None or terra_input.get("prose_included") is not False:
            errors.append("locked prose-free Terra input is missing")
        expected = _batch_evidence_refs(batch)
        actual = set()
        for path in sorted((batch / "terra/chapters").glob("*.json")):
            record = _read_json(path)
            if record and record.get("reference"):
                actual.add(str(record["reference"]))
        if expected != actual:
            errors.append(f"Terra output coverage mismatch: expected {len(expected)}, found {len(actual)}")
    if stage in {"POST_GENERATION_AUDIT", "PROSE_CERTIFICATION"}:
        report = _read_json(batch / "post-generation-report.json")
        if report is None:
            errors.append("missing post-generation-report.json")
    if stage == "PROSE_CERTIFICATION":
        report = _read_json(batch / "prose-certification.json")
        if report is None:
            errors.append("missing prose-certification.json")
        elif report.get("status") != "GO":
            errors.append(f"prose certification status is {report.get('status')!r}, not GO")
    if stage == "BATCH_COMPLETE":
        report = _read_json(batch / "prose-certification.json")
        if not report or report.get("status") != "GO":
            errors.append("batch prose certification is not GO")
    return errors


def _validate_stage_prerequisites(repo_root: Path, number: int, stage: str) -> list[str]:
    """Validate inputs for a pending stage without requiring its outputs yet."""

    batch = _batch_root(repo_root, number)
    errors: list[str] = []
    preflight = _read_json(batch / "preflight-report.json")
    certification = _read_json(batch / "evidence-certification.json")
    terra_input = _read_json(batch / "terra-input-manifest.json")
    if stage == "EVIDENCE_PREFLIGHT":
        work = repo_root / SCALE_ROOT_REL / f".{_batch_id(number)}.work"
        manifest = _read_json(batch / "batch-manifest.json")
        if not (work / "selection.json").exists() and not (manifest and manifest.get("candidate_pool")):
            errors.append("candidate selection checkpoint is incomplete")
    elif stage == "EVIDENCE_CERTIFICATION":
        if preflight is None:
            errors.append("missing preflight-report.json")
    elif stage == "EVIDENCE_LOCKED":
        if not certification or certification.get("status") != "LOCKED":
            errors.append("locked evidence certification is missing")
    elif stage == "READY_FOR_GENERATION":
        errors.extend(_validate_batch_artifacts(repo_root, number, "EVIDENCE_LOCKED"))
    elif stage == "PROSE_GENERATION":
        if not terra_input or terra_input.get("status") != "READY_FOR_TERRA" or terra_input.get("prose_included") is not False:
            errors.append("prose-free READY_FOR_TERRA input is missing")
    elif stage in {"POST_GENERATION_AUDIT", "PROSE_CERTIFICATION"}:
        errors.extend(_validate_batch_artifacts(repo_root, number, "PROSE_GENERATION"))
        if stage == "PROSE_CERTIFICATION" and _read_json(batch / "post-generation-report.json") is None:
            errors.append("missing post-generation-report.json")
    elif stage == "BATCH_COMPLETE":
        if not (_read_json(batch / "prose-certification.json") or {}).get("status") == "GO":
            errors.append("batch prose certification is not GO")
    return errors


def validate_state(repo_root: Path, state: Mapping[str, Any]) -> list[str]:
    _validate_state_shape(state)
    errors = [{"path": row["path"], "reason": "protected fingerprint changed", "expected": row["expected"], "actual": row["actual"]} for row in _protected_changes(repo_root, state["protected_fingerprints"])]
    if state["status"] == CORPUS_COMPLETE:
        return [str(row) for row in errors]
    if state["status"] == BLOCKED:
        return [str(row) for row in errors]
    stage = str(state["current_stage"])
    if stage in STAGES:
        if state["stage_status"] in {PENDING, RUNNING}:
            errors.extend(_validate_stage_prerequisites(repo_root, int(state["current_batch"]), stage))
        else:
            errors.extend(_validate_batch_artifacts(repo_root, int(state["current_batch"]), stage))
    return [str(row) for row in errors]


def _base_state(repo_root: Path) -> dict[str, Any]:
    numbers = _batch_numbers(repo_root)
    completed = 0
    for number in numbers:
        report = _read_json(_batch_root(repo_root, number) / "prose-certification.json")
        if report and report.get("status") == "GO":
            completed = max(completed, number)
    in_progress = [
        number for number in numbers
        if number > completed and _stage_from_artifacts(repo_root, number) != "BATCH_COMPLETE"
    ]
    current = max(in_progress, default=completed + 1)
    current_stage = _stage_from_artifacts(repo_root, current) if current in numbers else "CANDIDATE_SELECTION"
    fingerprints = collect_protected_fingerprints(repo_root)
    eligible = _current_population(repo_root)
    finalized = _finalized_count(repo_root, fingerprints)
    remaining = max(0, eligible - finalized) if eligible else 0
    definition = _stage_requirements(current_stage)
    work_root = repo_root / SCALE_ROOT_REL / f".{_batch_id(current)}.work"
    work_root.mkdir(parents=True, exist_ok=True)
    checkpoint = None
    preflight = _read_json(_batch_root(repo_root, current) / "preflight-report.json")
    if preflight and preflight.get("resumability") and current_stage in {"CANDIDATE_SELECTION", "EVIDENCE_PREFLIGHT"} and any(work_root.iterdir()):
        checkpoint = preflight["resumability"]
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "status": ACTIVE if remaining or current_stage != "BATCH_COMPLETE" else CORPUS_COMPLETE,
        "current_batch": current,
        "current_stage": current_stage if remaining or current_stage != "BATCH_COMPLETE" else CORPUS_COMPLETE,
        "stage_status": PENDING,
        "last_completed_batch": completed,
        "last_completed_stage": "PROSE_CERTIFICATION" if completed else None,
        "eligible_corpus_total": eligible,
        "finalized_chapters": finalized,
        "remaining_chapters": remaining,
        "required_model": definition.required_model,
        "required_effort": definition.required_effort,
        "resumable": definition.resumable,
        "resume_token": checkpoint,
        "last_successful_checkpoint": None,
        "blocked_reason": None,
        "protected_fingerprints": fingerprints,
        "completed_stages": [
            {"batch": current, "stage": previous}
            for previous in (STAGE_ORDER[:STAGE_ORDER.index(current_stage)] if current_stage in STAGE_ORDER else STAGE_ORDER)
        ],
        "can_advance": True,
        "human_intervention_required": current_stage in {"READY_FOR_GENERATION", "PROSE_GENERATION"},
        "history": [{"event": "INITIALIZED_FROM_REPOSITORY", "batch": current, "stage": current_stage, "at": _now()}],
        "observed_repository": {"head": _git_head(repo_root), "branch": _git_branch(repo_root)},
        "updated_at": _now(),
    }


def initialize(repo_root: Path = REPO_ROOT, *, overwrite: bool = False) -> dict[str, Any]:
    path = state_path(repo_root)
    if path.exists() and not overwrite:
        return load_state(path)
    state = _base_state(repo_root)
    if state["status"] == CORPUS_COMPLETE:
        state = _write_corpus_certification(repo_root, state)
    return save_state(path, state)


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _git_branch(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "branch", "--show-current"], cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _state_path_from_args(repo_root: Path) -> Path:
    return state_path(repo_root)


def _transition(state: dict[str, Any], *, next_stage: str, event: str, checkpoint: Any = None) -> dict[str, Any]:
    if next_stage not in STAGES and next_stage not in TERMINAL_STAGES:
        raise PipelineError(f"illegal transition target: {next_stage}")
    current = state["current_stage"]
    allowed = {
        "BATCH_PENDING": {"CANDIDATE_SELECTION"},
        "CANDIDATE_SELECTION": {"EVIDENCE_PREFLIGHT"},
        "EVIDENCE_PREFLIGHT": {"EVIDENCE_CERTIFICATION"},
        "EVIDENCE_CERTIFICATION": {"EVIDENCE_LOCKED"},
        "EVIDENCE_LOCKED": {"READY_FOR_GENERATION"},
        "READY_FOR_GENERATION": {"PROSE_GENERATION"},
        "PROSE_GENERATION": {"POST_GENERATION_AUDIT"},
        "POST_GENERATION_AUDIT": {"PROSE_CERTIFICATION"},
        "PROSE_CERTIFICATION": {"BATCH_COMPLETE"},
        "BATCH_COMPLETE": {"CANDIDATE_SELECTION", CORPUS_COMPLETE},
    }
    if next_stage not in allowed.get(current, set()):
        raise PipelineError(f"illegal transition: {current} -> {next_stage}")
    state["current_stage"] = next_stage
    state["stage_status"] = PENDING
    definition = STAGES.get(next_stage)
    if definition:
        state["required_model"] = definition.required_model
        state["required_effort"] = definition.required_effort
        state["resumable"] = definition.resumable
    else:
        state["required_model"] = "none"
        state["required_effort"] = "none"
        state["resumable"] = False
    state["resume_token"] = checkpoint
    state["last_successful_checkpoint"] = checkpoint
    state["history"].append({"event": event, "from": current, "to": next_stage, "batch": state["current_batch"], "at": _now()})
    return state


def _mark_output_validated(state: dict[str, Any], checkpoint: Any) -> dict[str, Any]:
    state["stage_status"] = OUTPUT_VALIDATED
    state["last_successful_checkpoint"] = checkpoint
    return state


def _complete_stage(repo_root: Path, state: dict[str, Any], *, checkpoint: Any = None) -> dict[str, Any]:
    stage = str(state["current_stage"])
    errors = _validate_batch_artifacts(repo_root, int(state["current_batch"]), stage)
    if errors:
        raise PipelineError("stage output validation failed: " + "; ".join(errors))
    _mark_output_validated(state, checkpoint)
    state["stage_status"] = COMPLETE
    state.setdefault("completed_stages", []).append({"batch": state["current_batch"], "stage": stage})
    if stage == "PROSE_CERTIFICATION":
        state["last_completed_batch"] = int(state["current_batch"])
        state["finalized_chapters"] = len(collect_protected_fingerprints(repo_root))
        state["remaining_chapters"] = max(0, int(state["eligible_corpus_total"]) - int(state["finalized_chapters"]))
    next_stage = "BATCH_COMPLETE" if stage == "PROSE_CERTIFICATION" else {
        "CANDIDATE_SELECTION": "EVIDENCE_PREFLIGHT",
        "EVIDENCE_PREFLIGHT": "EVIDENCE_CERTIFICATION",
        "EVIDENCE_CERTIFICATION": "EVIDENCE_LOCKED",
        "EVIDENCE_LOCKED": "READY_FOR_GENERATION",
        "READY_FOR_GENERATION": "PROSE_GENERATION",
        "PROSE_GENERATION": "POST_GENERATION_AUDIT",
        "POST_GENERATION_AUDIT": "PROSE_CERTIFICATION",
        "BATCH_PENDING": "CANDIDATE_SELECTION",
    }.get(stage)
    if next_stage:
        return _transition(state, next_stage=next_stage, event="STAGE_COMPLETE", checkpoint=checkpoint)
    return state


def _handoff(state: dict[str, Any]) -> dict[str, Any]:
    if state["current_stage"] != "READY_FOR_GENERATION":
        raise PipelineError("model handoff is only available after evidence is locked")
    return _transition(state, next_stage="PROSE_GENERATION", event="TERRA_HANDOFF_ACCEPTED", checkpoint={"model": "terra", "effort": "medium"})


def _resume_result(state: Mapping[str, Any], action: str, *, message: str = "") -> dict[str, Any]:
    result = {
        "action": action,
        "status": action,
        "batch": state.get("current_batch"),
        "stage": state.get("current_stage"),
        "model": state.get("required_model"),
        "effort": state.get("required_effort"),
        "message": message,
    }
    if state.get("resume_token") is not None:
        result["checkpoint"] = state["resume_token"]
    return result


def _preflight_command(repo_root: Path, state: Mapping[str, Any]) -> list[str]:
    return [
        sys.executable,
        str(repo_root / "tools/commentary_v11_scaled_preflight.py"),
        "--batch-id", _batch_id(int(state["current_batch"])),
        "--target-count", str(min(150, max(1, int(state["remaining_chapters"]) or 150))),
        "--candidate-pool-size", "250",
        "--sqlite-database", str(repo_root / ".bhf/ckl.sqlite"),
    ]


def _terra_staging_root(repo_root: Path, number: int) -> Path:
    return repo_root / SCALE_ROOT_REL / f".{_batch_id(number)}.terra.finalizing"


def _terra_command(repo_root: Path, state: Mapping[str, Any], staging: Path, report: Path) -> list[str]:
    return [
        sys.executable,
        str(repo_root / "tools/terra_commentary_scaled_batch.py"),
        "--batch-root", str(_batch_root(repo_root, int(state["current_batch"]))),
        "--output", str(staging),
        "--report", str(report),
    ]


def _validate_terra_staging(repo_root: Path, state: Mapping[str, Any], staging: Path) -> list[str]:
    errors: list[str] = []
    summary = _read_json(staging / "terra-batch-summary.json")
    validation = _read_json(staging / "terra-validation-report.json")
    quality = _read_json(staging / "terra-quality-audit.json")
    lock = (summary or {}).get("lock_revalidation", {})
    expected = _batch_evidence_refs(_batch_root(repo_root, int(state["current_batch"])))
    actual: set[str] = set()
    for path in sorted((staging / "chapters").glob("*.json")):
        candidate = _read_json(path)
        if candidate and candidate.get("reference"):
            actual.add(str(candidate["reference"]))
    if not summary:
        errors.append("missing Terra batch summary")
    elif summary.get("status") not in {f"READY_FOR_BATCH_{int(state['current_batch']) + 1:03d}", "NEEDS_REFINEMENT"}:
        errors.append(f"Terra runner status is {summary.get('status')!r}, not a completed generation status")
    if not validation:
        errors.append("missing Terra validation report")
    elif validation.get("invalid", 0) or validation.get("valid") != len(expected):
        errors.append("Terra validation did not pass for every locked chapter")
    if not quality:
        errors.append("missing Terra quality audit")
    # Quality flags are preserved as raw signals for POST_GENERATION_AUDIT;
    # that stage applies the established PASS/REGENERATE/QUARANTINE policy.
    if lock.get("status") != "PASS" or lock.get("stale_locks"):
        errors.append("Terra lock revalidation is not PASS")
    if actual != expected:
        errors.append(f"Terra output coverage mismatch: expected {len(expected)}, found {len(actual)}")
    if (summary or {}).get("quarantined_chapters_not_generated") is not True:
        errors.append("Terra reports quarantined chapters in generation input")
    if (summary or {}).get("canary_artifacts", {}).get("unchanged") is not True:
        errors.append("Terra changed protected canary artifacts")
    if (summary or {}).get("batch_001_terra_artifacts", {}).get("unchanged") is not True:
        errors.append("Terra changed protected Batch 001 artifacts")
    return errors


def _run_terra(repo_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    number = int(state["current_batch"])
    staging = _terra_staging_root(repo_root, number)
    report = repo_root / "docs" / f".commentary-v1.1-scaled-{_batch_id(number)}-terra.finalizing.md"
    staging.mkdir(parents=True, exist_ok=True)
    command = _terra_command(repo_root, state, staging, report)
    state["stage_status"] = RUNNING
    state["resume_token"] = {"command": command, "staging_root": str(staging.relative_to(repo_root)), "model": "terra", "effort": "medium"}
    save_state(state_path(repo_root), state)
    existing_summary = staging / "terra-batch-summary.json"
    completed = None
    if not existing_summary.exists():
        completed = subprocess.run(command, cwd=repo_root, check=False)
    state = load_state(state_path(repo_root))
    if completed is not None and completed.returncode != 0:
        return _resume_result(state, "RESUME_REQUIRED", message="Terra stage was interrupted or failed; temporary output remains unpromoted")
    errors = _validate_terra_staging(repo_root, state, staging)
    if errors:
        return _set_blocker(repo_root, state, "NON_RETRYABLE", "Terra output validation failed", errors)
    final_output = _batch_root(repo_root, number) / "terra"
    if final_output.exists():
        return _set_blocker(repo_root, state, "HUMAN_REVIEW_REQUIRED", "final Terra output already exists; refusing overwrite", [str(final_output)])
    staging.replace(final_output)
    final_report = repo_root / "docs" / f"commentary-v1.1-scaled-{_batch_id(number)}-terra.md"
    if report.exists():
        os.replace(report, final_report)
    state = load_state(state_path(repo_root))
    state["stage_status"] = OUTPUT_WRITTEN
    checkpoint = {"stage": "PROSE_GENERATION", "output": str(final_output.relative_to(repo_root)), "summary_hash": _sha256_file(final_output / "terra-batch-summary.json")}
    state = _complete_stage(repo_root, state, checkpoint=checkpoint)
    save_state(state_path(repo_root), state)
    return _resume_result(state, "STAGE_COMPLETE", message="Terra output validated and atomically promoted")


def _run_post_generation(repo_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Run the proven certifier against a temporary batch copy before promotion."""

    number = int(state["current_batch"])
    batch = _batch_root(repo_root, number)
    staging = repo_root / SCALE_ROOT_REL / f".{_batch_id(number)}.certifying"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(batch, staging)
    state["stage_status"] = RUNNING
    state["resume_token"] = {"staging_root": str(staging.relative_to(repo_root)), "policy": "existing-certification-policy"}
    save_state(state_path(repo_root), state)
    from tools.commentary_v11_post_generation import markdown as post_markdown
    from tools.commentary_v11_post_generation import run as post_run

    try:
        post_report = post_run(staging)
    except Exception as exc:
        return _resume_result(load_state(state_path(repo_root)), "RESUME_REQUIRED", message=f"post-generation audit interrupted: {exc}")
    _atomic_json(staging / "post-generation-report.json", post_report)
    _atomic_json(staging / "prose-certification.json", post_report)
    _atomic_text(staging / "post-generation.md", post_markdown(post_report))
    if post_report.get("status") != "GO":
        for name in ("post-generation-report.json", "prose-certification.json"):
            os.replace(staging / name, batch / name)
        return _set_blocker(repo_root, load_state(state_path(repo_root)), "HUMAN_REVIEW_REQUIRED", "post-generation certification did not reach GO", [post_report.get("status")])
    for name in ("post-generation-report.json", "prose-certification.json"):
        os.replace(staging / name, batch / name)
    final_doc = repo_root / "docs" / f"commentary-v1.1-scaled-{_batch_id(number)}-post-generation.md"
    os.replace(staging / "post-generation.md", final_doc)
    shutil.rmtree(staging)
    state = load_state(state_path(repo_root))
    state["stage_status"] = OUTPUT_WRITTEN
    state = _complete_stage(repo_root, state, checkpoint={"stage": "POST_GENERATION_AUDIT", "status": "GO"})
    save_state(state_path(repo_root), state)
    return _resume_result(state, "STAGE_COMPLETE", message="post-generation certification output validated and promoted")


def _run_external_preflight(repo_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    command = _preflight_command(repo_root, state)
    state["stage_status"] = RUNNING
    state["resume_token"] = {"command": command, "work_root": f"{SCALE_ROOT_REL}/.{_batch_id(int(state['current_batch']))}.work"}
    return state


def run_stage(repo_root: Path, *, model: str | None = None, effort: str | None = None) -> dict[str, Any]:
    path = state_path(repo_root)
    state = load_state(path)
    if state["status"] == BLOCKED:
        return _resume_result(state, "BLOCKED", message=str(state.get("blocked_reason")))
    errors = validate_state(repo_root, state)
    if errors:
        return _set_blocker(repo_root, state, "NON_RETRYABLE", "state/artifact validation failed", errors)
    stage = str(state["current_stage"])
    definition = _stage_requirements(stage) if stage in STAGES else None
    if definition and definition.requires_llm:
        if model != definition.required_model or effort != definition.required_effort:
            return _resume_result(state, "MODEL_HANDOFF_REQUIRED", message="the supplied model/effort does not satisfy this stage") | {
                "action": "MODEL_HANDOFF_REQUIRED", "run_stage": stage,
                "model": definition.required_model, "effort": definition.required_effort,
            }
    if stage == "READY_FOR_GENERATION":
        return _resume_result(state, "MODEL_HANDOFF_REQUIRED", message="accept this handoff before any Terra invocation") | {
            "action": "MODEL_HANDOFF_REQUIRED", "run_stage": "PROSE_GENERATION",
            "model": "terra", "effort": "medium",
        }
    if stage == "PROSE_GENERATION":
        return _run_terra(repo_root, state)
    if stage in {"CANDIDATE_SELECTION", "EVIDENCE_PREFLIGHT"}:
        state = _run_external_preflight(repo_root, state)
        state = save_state(path, state)
        completed = subprocess.run(_preflight_command(repo_root, state), cwd=repo_root, check=False)
        if completed.returncode != 0:
            state = load_state(path)
            return _resume_result(state, "RESUME_REQUIRED", message="preflight did not reach a validated final lock; checkpoint remains reusable")
        state = load_state(path)
        state["stage_status"] = OUTPUT_WRITTEN
        state = _complete_stage(repo_root, state, checkpoint=state.get("resume_token"))
        save_state(path, state)
        return _resume_result(state, "STAGE_COMPLETE", message="existing resumable preflight output validated")
    if stage in {"EVIDENCE_CERTIFICATION", "EVIDENCE_LOCKED", "POST_GENERATION_AUDIT", "PROSE_CERTIFICATION", "BATCH_COMPLETE"}:
        if stage == "BATCH_COMPLETE":
            return advance_batch(repo_root)
        if stage == "POST_GENERATION_AUDIT":
            return _run_post_generation(repo_root, state)
        state["stage_status"] = RUNNING
        save_state(path, state)
        state = load_state(path)
        state["stage_status"] = OUTPUT_WRITTEN
        state = _complete_stage(repo_root, state, checkpoint={"validated_at": _now()})
        save_state(path, state)
        return _resume_result(state, "STAGE_COMPLETE", message="deterministic stage output validated")
    raise PipelineError(f"stage cannot be run: {stage}")


def resume(repo_root: Path) -> dict[str, Any]:
    path = state_path(repo_root)
    state = load_state(path)
    if state["status"] == BLOCKED:
        return _resume_result(state, "BLOCKED", message=str(state.get("blocked_reason")))
    stage = str(state["current_stage"])
    if stage in {"CANDIDATE_SELECTION", "EVIDENCE_PREFLIGHT"}:
        return run_stage(repo_root, model="luna", effort="high")
    if stage == "PROSE_GENERATION":
        return run_stage(repo_root, model="terra", effort="medium")
    if stage == "POST_GENERATION_AUDIT":
        return run_stage(repo_root)
    try:
        state = _complete_stage(repo_root, state, checkpoint=state.get("resume_token"))
    except PipelineError as exc:
        return _resume_result(state, "RESUME_REQUIRED", message=str(exc))
    save_state(path, state)
    return _resume_result(state, "STAGE_COMPLETE", message="validated checkpoint resumed idempotently")


def accept_handoff(repo_root: Path, *, model: str, effort: str) -> dict[str, Any]:
    path = state_path(repo_root)
    state = load_state(path)
    if model != "terra" or effort != "medium":
        return _resume_result(state, "MODEL_HANDOFF_REQUIRED", message="only Terra Medium may accept this handoff") | {
            "action": "MODEL_HANDOFF_REQUIRED", "model": "terra", "effort": "medium",
        }
    state = _handoff(state)
    save_state(path, state)
    return _resume_result(state, "ADVANCED", message="Terra handoff recorded; generation remains external")


def _write_corpus_certification(repo_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    batches = []
    availability: Counter[str] = Counter()
    genres: Counter[str] = Counter()
    books: Counter[str] = Counter()
    evidence_counts: list[int] = []
    prose_counts: list[int] = []
    regenerations = quarantines = data_gaps = 0
    for number in _batch_numbers(repo_root):
        batch = _batch_root(repo_root, number)
        manifest = _read_json(batch / "batch-manifest.json") or {}
        certification = _read_json(batch / "evidence-certification.json") or {}
        prose = _read_json(batch / "prose-certification.json") or {}
        rows = manifest.get("final_chapters", [])
        for row in rows:
            availability[str(row.get("availability", "UNKNOWN"))] += 1
            genres[str(row.get("genre", "UNKNOWN"))] += 1
            books[str(row.get("book", "UNKNOWN"))] += 1
            if isinstance(row.get("evidence_count"), int): evidence_counts.append(row["evidence_count"])
        batches.append({"batch": _batch_id(number), "status": manifest.get("status"), "prose_status": prose.get("status"), "chapter_count": len(rows)})
        dispositions = prose.get("disposition_counts", {})
        regenerations += int(prose.get("regeneration_attempts", 0) or 0)
        quarantines += int(dispositions.get("QUARANTINE", 0) or 0)
        data_gaps += int(dispositions.get("DATA_GAP", 0) or 0)
        if certification.get("status") == "LOCKED":
            prose_counts.append(int(prose.get("chapters_generated", 0) or 0))
    stats = {}
    if evidence_counts:
        ordered = sorted(evidence_counts)
        stats = {"min": min(ordered), "median": ordered[len(ordered) // 2], "mean": round(sum(ordered) / len(ordered), 2), "max": max(ordered)}
    artifact = {
        "artifact_version": "commentary-v1.1-final-corpus-certification-v1",
        "status": CORPUS_COMPLETE,
        "created_at": _now(),
        "total_eligible_chapters": state["eligible_corpus_total"],
        "total_generated": sum(prose_counts),
        "total_certified": state["finalized_chapters"],
        "availability_distribution": dict(sorted(availability.items())),
        "genre_distribution": dict(sorted(genres.items())),
        "book_distribution": dict(sorted(books.items())),
        "evidence_statistics": stats,
        "prose_statistics": {"generated_by_batch": prose_counts},
        "total_regenerations": regenerations,
        "total_quarantines": quarantines,
        "total_data_gaps": data_gaps,
        "protected_fingerprint_count": len(state["protected_fingerprints"]),
        "protected_fingerprints_verified": not _protected_changes(repo_root, state["protected_fingerprints"]),
        "batches": batches,
        "known_ckl_concerns": ["broad-parent reuse", "cross-book parent reuse", "evidence-count outliers", "backend hash disagreements", "corpus ambiguity"],
    }
    output = repo_root / SCALE_ROOT_REL / "final-corpus-certification.json"
    _atomic_json(output, artifact)
    markdown = repo_root / "docs/commentary-v1.1-final-corpus-certification.md"
    markdown.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(markdown, "# Commentary v1.1 final corpus certification\n\nStatus: **CORPUS_COMPLETE**.\n\n" + _canonical(artifact) + "\n")
    state["corpus_certification_artifact"] = str(output.relative_to(repo_root))
    return state


def advance_batch(repo_root: Path) -> dict[str, Any]:
    path = state_path(repo_root)
    state = load_state(path)
    if state["current_stage"] != "BATCH_COMPLETE":
        raise PipelineError("batch advancement requires BATCH_COMPLETE")
    fingerprints = collect_protected_fingerprints(repo_root)
    state["protected_fingerprints"] = fingerprints
    state["finalized_chapters"] = len(fingerprints)
    state["remaining_chapters"] = max(0, int(state["eligible_corpus_total"]) - len(fingerprints))
    if state["remaining_chapters"] == 0:
        state = _transition(state, next_stage=CORPUS_COMPLETE, event="CORPUS_COMPLETED")
        state["status"] = CORPUS_COMPLETE
        state = _write_corpus_certification(repo_root, state)
        save_state(path, state)
        return _resume_result(state, "CORPUS_COMPLETE", message="all derived eligible chapters are finalized")
    state["current_batch"] = int(state["current_batch"]) + 1
    new_batch = int(state["current_batch"])
    (repo_root / SCALE_ROOT_REL / f".{_batch_id(new_batch)}.work").mkdir(parents=True, exist_ok=True)
    state["status"] = ACTIVE
    state = _transition(state, next_stage="CANDIDATE_SELECTION", event="NEXT_BATCH_INITIALIZED")
    save_state(path, state)
    return _resume_result(state, "ADVANCED", message="next batch initialized")


def _set_blocker(repo_root: Path, state: dict[str, Any], error_class: str, reason: str, diagnostics: Iterable[Any]) -> dict[str, Any]:
    blocker = {
        "batch": state.get("current_batch"),
        "stage": state.get("current_stage"),
        "timestamp": _now(),
        "error_class": error_class,
        "reason": reason,
        "affected_chapters": [],
        "affected_evidence_ids": [],
        "expected_vs_actual_hashes": [],
        "diagnostics": list(diagnostics),
        "recommended_next_action": "human review required before retry" if error_class != "RETRYABLE" else "resume after the checkpoint is available",
        "retry_allowed": error_class == "RETRYABLE",
    }
    state["status"] = BLOCKED
    state["blocked_reason"] = blocker
    save_state(state_path(repo_root), state)
    return _resume_result(state, "BLOCKED", message=reason) | {"blocker": blocker}


def clear_blocker(repo_root: Path, *, resolution: str) -> dict[str, Any]:
    path = state_path(repo_root)
    state = load_state(path)
    if state["status"] != BLOCKED:
        return _resume_result(state, "ADVANCED", message="no blocker is set")
    state["status"] = ACTIVE
    state["blocked_reason"] = None
    state["stage_status"] = PENDING
    state["history"].append({"event": "BLOCKER_CLEARED", "resolution": resolution, "at": _now()})
    save_state(path, state)
    return _resume_result(state, "ADVANCED", message="blocker cleared; no stage was implicitly retried")


def status(repo_root: Path) -> dict[str, Any]:
    state = load_state(state_path(repo_root))
    errors = validate_state(repo_root, state)
    return {
        "pipeline": PIPELINE_VERSION,
        "status": state["status"],
        "batch": state["current_batch"],
        "stage": state["current_stage"],
        "stage_status": state["stage_status"],
        "progress": {"finalized": state["finalized_chapters"], "eligible": state["eligible_corpus_total"], "remaining": state["remaining_chapters"]},
        "required_model": state["required_model"],
        "required_effort": state["required_effort"],
        "last_completed_batch": state["last_completed_batch"],
        "resumable": state["resumable"],
        "can_advance": state["can_advance"],
        "human_intervention_required": state["human_intervention_required"],
        "checkpoint": state.get("resume_token"),
        "blocker": state.get("blocked_reason"),
        "validation_errors": errors,
        "next_action": ("BLOCKED" if state["status"] == BLOCKED else "RESUME_REQUIRED" if errors else "MODEL_HANDOFF_REQUIRED" if state["current_stage"] in {"READY_FOR_GENERATION", "PROSE_GENERATION"} else "RUN_STAGE"),
    }


def report(repo_root: Path) -> str:
    data = status(repo_root)
    progress = data["progress"]
    lines = [
        "COMMENTARY V1.1 PIPELINE",
        f"Status: {data['status']}",
        f"Batch: {data['batch']:03d}",
        f"Stage: {data['stage']}",
        f"Progress: {progress['finalized']} finalized / {progress['eligible']} eligible ({progress['remaining']} remaining)",
        f"Required Model: {data['required_model']}",
        f"Effort: {data['required_effort']}",
        f"Last Certified Batch: {data['last_completed_batch']:03d}",
        f"Checkpoint: {data['checkpoint'] or 'none'}",
        f"Blockers: {len(data['validation_errors']) if data['validation_errors'] else ('1' if data['blocker'] else 'none')}",
        "",
        f"NEXT ACTION: {data['next_action']}",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BHF Commentary v1.1 state-machine orchestrator")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable output")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="derive and atomically write state from repository artifacts")
    init.add_argument("--reconcile", action="store_true", help="rebuild state from validated repository artifacts")
    commands.add_parser("status", help="show machine-readable current state summary")
    commands.add_parser("report", help="show concise human-readable current state")
    commands.add_parser("validate", help="validate state, protected fingerprints, and current-stage artifacts")
    commands.add_parser("next", help="show the next safe action without executing it")
    run = commands.add_parser("run", help="execute at most one safe stage")
    run.add_argument("--model", help="model actually executing the requested stage")
    run.add_argument("--effort", help="effort actually used by that model")
    commands.add_parser("resume", help="resume one validated checkpoint or external stage")
    handoff = commands.add_parser("handoff", help="record acceptance of a model-specific handoff without invoking it")
    handoff.add_argument("--model", required=True)
    handoff.add_argument("--effort", required=True)
    clear = commands.add_parser("clear-blocker", help="clear a reviewed blocker without retrying a stage")
    clear.add_argument("--resolution", required=True)
    return parser


def _next(repo_root: Path) -> dict[str, Any]:
    state = load_state(state_path(repo_root))
    if state["status"] == BLOCKED:
        return _resume_result(state, "BLOCKED", message=str(state.get("blocked_reason")))
    errors = validate_state(repo_root, state)
    if errors:
        return _resume_result(state, "BLOCKED", message="validation required: " + "; ".join(errors))
    if state["current_stage"] in {"READY_FOR_GENERATION", "PROSE_GENERATION"}:
        return _resume_result(state, "MODEL_HANDOFF_REQUIRED", message="model-specific stage requires explicit handoff") | {
            "run_stage": "PROSE_GENERATION", "model": "terra", "effort": "medium",
        }
    return _resume_result(state, "RUN_STAGE", message="run exactly one stage with the required model/effort")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "init": result: Any = initialize(repo_root, overwrite=args.reconcile)
        elif args.command == "status": result = status(repo_root)
        elif args.command == "report":
            print(report(repo_root))
            return 0
        elif args.command == "validate":
            state = load_state(state_path(repo_root))
            errors = validate_state(repo_root, state)
            result = {"action": "VALID" if not errors else "BLOCKED", "errors": errors, "state": status(repo_root)}
        elif args.command == "next": result = _next(repo_root)
        elif args.command == "run": result = run_stage(repo_root, model=args.model, effort=args.effort)
        elif args.command == "resume": result = resume(repo_root)
        elif args.command == "handoff": result = accept_handoff(repo_root, model=args.model, effort=args.effort)
        elif args.command == "clear-blocker": result = clear_blocker(repo_root, resolution=args.resolution)
        else: raise PipelineError(f"unsupported command: {args.command}")
    except StateCorruptionError as exc:
        result = {"action": "BLOCKED", "status": "BLOCKED", "error_class": "CORRUPT_STATE", "message": str(exc)}
    except PipelineError as exc:
        result = {"action": "BLOCKED", "status": "BLOCKED", "error_class": "PIPELINE_ERROR", "message": str(exc)}
    if args.as_json or args.command != "report":
        print(json.dumps(result, indent=2, sort_keys=True))
    action = result.get("action", result.get("status")) if isinstance(result, dict) else "BLOCKED"
    return EXIT_CODES.get(str(action), 2)


if __name__ == "__main__":
    raise SystemExit(main())
