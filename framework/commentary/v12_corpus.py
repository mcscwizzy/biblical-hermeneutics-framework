"""Bounded, resumable orchestration for Commentary v1.2 corpus generation.

This module owns selection and run receipts only.  Chapter generation remains
delegated to the existing CommentaryGenerator path; v1.1 and the packaged
v1.2 release are never used as writable output locations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.generator import CommentaryGenerator
from bhf_agent.chapter_commentary.models import (
    CommentaryGenerationRequest,
    CommentaryGenerationResult,
)
from bhf_agent.chapter_commentary.release import (
    RELEASE_CHECKSUMS_FILENAME,
    RELEASE_MANIFEST_FILENAME,
    release_diagnostics,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis
from bhf_agent.config import AgentConfig
from framework.commentary.production.census import canonical_chapters
from framework.commentary.production.models import canonical_json, sha256_bytes, write_json


V12_CANDIDATE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment")
V12_RELEASE_ROOT = Path(".bhf-data/bhf-commentary-v1.2")
CORPUS_RUNNER_ROOT = V12_CANDIDATE_ROOT / "corpus-runner"
DEFAULT_BATCH_SIZE = 25
MAX_BATCH_SIZE = 50
AUTHORIZATION_FIELD = "full_bible_generation_authorized"

TERMINAL_RELEASE_STATES = frozenset(
    {
        "PUBLISHED",
        "NOT_RENDERABLE_SOURCE_LIMITED",
        "MODEL_OUTPUT_REJECTED",
        "QUALITY_REVIEW_REQUIRED",
    }
)
TERMINAL_RESULT_STATES = frozenset(
    {"validated", "partial", "needs_review", "failed", "stale"}
)
NONTERMINAL_RESULT_STATES = frozenset(
    {"pending", "generating"}
)


class V12CorpusError(RuntimeError):
    """A fail-closed corpus orchestration error."""


class V12AuthorizationError(V12CorpusError):
    """Generation was requested without explicit persisted authorization."""


class V12IntegrityError(V12CorpusError):
    """Persisted corpus state is inconsistent or ambiguous."""


class ChapterPipeline(Protocol):
    def generate(self, book: str, chapter: int) -> CommentaryGenerationResult: ...


@dataclass(frozen=True)
class Discovery:
    canonical_chapters_total: int
    terminal_v1_2_chapters: int
    chapters_remaining: int
    requested_batch_size: int
    next_chapters: tuple[str, ...]
    full_bible_generation_authorized: bool
    conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_chapters_total": self.canonical_chapters_total,
            "terminal_v1_2_chapters": self.terminal_v1_2_chapters,
            "chapters_remaining": self.chapters_remaining,
            "requested_batch_size": self.requested_batch_size,
            "next_chapters": list(self.next_chapters),
            "full_bible_generation_authorized": self.full_bible_generation_authorized,
            "conflicts": list(self.conflicts),
        }


class ExistingV12ChapterPipeline:
    """Adapter around the existing evidence/synthesis/commentary generator."""

    def __init__(self, config: AgentConfig):
        self.generator = CommentaryGenerator(config)

    def generate(self, book: str, chapter: int) -> CommentaryGenerationResult:
        bundle = get_chapter_evidence_bundle(book, chapter)
        evidence_hash = bundle.evidence_hash if bundle is not None else ""
        synthesis_hash = (
            compile_chapter_synthesis(bundle, book=book, chapter=chapter).synthesis_hash
            if bundle is not None
            else None
        )
        return self.generator.generate(
            CommentaryGenerationRequest(
                book=book,
                chapter=chapter,
                reference=f"{book} {chapter}",
                evidence_hash=evidence_hash,
                synthesis_hash=synthesis_hash,
            )
        )


def _slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{int(chapter):03d}"


def _reference(row: dict[str, Any]) -> str:
    return f"{row['book']} {int(row['chapter'])}"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise V12IntegrityError(f"invalid JSON artifact: {path}") from exc


class V12CorpusRunner:
    """Discover and execute one bounded v1.2 batch at a time."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        candidate_root: str | Path = V12_CANDIDATE_ROOT,
        release_root: str | Path = V12_RELEASE_ROOT,
        canonical_loader: Callable[[], list[dict[str, Any]]] = canonical_chapters,
        pipeline: ChapterPipeline | None = None,
    ):
        self.repo_root = Path(repo_root)
        self.candidate_root = self._rooted(candidate_root)
        self.release_root = self._rooted(release_root)
        self.runner_root = self.candidate_root / "corpus-runner"
        self.canonical_loader = canonical_loader
        self.pipeline = pipeline

    def _rooted(self, path: str | Path) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else self.repo_root / candidate

    def _authorized(self) -> bool:
        state_path = self.candidate_root / "candidate-state.json"
        state = _load_json(state_path)
        if not isinstance(state, dict) or state.get("pipeline_version") != "commentary-v1.2-enrichment":
            raise V12IntegrityError(f"invalid v1.2 candidate state: {state_path}")
        value = state.get(AUTHORIZATION_FIELD)
        if not isinstance(value, bool):
            raise V12IntegrityError(f"v1.2 authorization field must be boolean: {state_path}")
        return value

    def _canonical(self) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
        rows = list(self.canonical_loader())
        by_reference: dict[str, dict[str, Any]] = {}
        conflicts: list[str] = []
        for row in rows:
            reference = _reference(row)
            if reference in by_reference:
                conflicts.append(f"duplicate canonical chapter: {reference}")
            else:
                by_reference[reference] = row
        return rows, by_reference, conflicts

    def _release_records(self, canonical: dict[str, dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
        manifest_path = self.release_root / RELEASE_MANIFEST_FILENAME
        if not manifest_path.is_file():
            return {}, []
        diagnostics = release_diagnostics(self.release_root, "commentary-v1.2")
        conflicts: list[str] = []
        if diagnostics.get("checksum_status") != "valid":
            conflicts.append(
                f"v1.2 release integrity is {diagnostics.get('checksum_status', 'unknown')}"
            )
        manifest = _load_json(manifest_path)
        if not isinstance(manifest, dict) or manifest.get("release") != "commentary-v1.2":
            conflicts.append(f"unexpected v1.2 release identity: {manifest.get('release') if isinstance(manifest, dict) else 'invalid'}")
        rows = manifest.get("chapter_publication_index") if isinstance(manifest, dict) else None
        if not isinstance(rows, list):
            raise V12IntegrityError(f"v1.2 release index is malformed: {manifest_path}")
        records: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, dict):
                conflicts.append("v1.2 release index contains a non-object row")
                continue
            try:
                reference = _reference(row)
            except (KeyError, TypeError, ValueError):
                conflicts.append("v1.2 release index contains an invalid chapter identity")
                continue
            if reference not in canonical:
                conflicts.append(f"release chapter is not canonical: {reference}")
            state = row.get("release_state")
            if state not in TERMINAL_RELEASE_STATES or row.get("validated") is not True:
                conflicts.append(f"release chapter is not terminal/validated: {reference}")
                continue
            if reference in records:
                conflicts.append(f"duplicate release state: {reference}")
                continue
            records[reference] = str(state)
        return records, conflicts

    def _runner_records(self, canonical: dict[str, dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
        records: dict[str, str] = {}
        conflicts: list[str] = []
        runs_root = self.runner_root / "runs"
        if not runs_root.is_dir():
            return records, conflicts
        for result_path in sorted(runs_root.glob("*/chapters/*/result.json")):
            result = _load_json(result_path)
            if not isinstance(result, dict):
                conflicts.append(f"runner result is not an object: {result_path}")
                continue
            reference = result.get("reference")
            if not isinstance(reference, str) or reference not in canonical:
                conflicts.append(f"runner result has invalid chapter identity: {result_path}")
                continue
            expected = canonical[reference]
            if result.get("book") != expected.get("book") or int(result.get("chapter", -1)) != int(expected.get("chapter", -2)):
                conflicts.append(f"runner result identity fields disagree: {reference}")
                continue
            status = result.get("status")
            if status in NONTERMINAL_RESULT_STATES:
                conflicts.append(f"runner result is non-terminal: {reference}")
                continue
            if status not in TERMINAL_RESULT_STATES:
                conflicts.append(f"runner result has unknown status for {reference}: {status}")
                continue
            if reference in records:
                conflicts.append(f"duplicate runner result: {reference}")
                continue
            records[reference] = str(status)
        for state_path in sorted(runs_root.glob("*/state.json")):
            state = _load_json(state_path)
            chapter_states = state.get("chapters") if isinstance(state, dict) else None
            if not isinstance(chapter_states, dict):
                conflicts.append(f"runner state has no chapter map: {state_path}")
                continue
            for reference, record in chapter_states.items():
                if reference not in canonical or not isinstance(record, dict):
                    conflicts.append(f"runner state has invalid chapter identity: {state_path}")
                    continue
                status = record.get("status")
                if status in NONTERMINAL_RESULT_STATES or status == "ready":
                    if status == "generating":
                        conflicts.append(f"runner chapter is in-flight: {reference}")
                    continue
                if status not in TERMINAL_RESULT_STATES:
                    conflicts.append(f"runner state has unknown status for {reference}: {status}")
                elif records.get(reference) != status:
                    conflicts.append(f"runner state/result disagreement: {reference}")
        return records, conflicts

    def _state(self) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
        rows, canonical, conflicts = self._canonical()
        release, release_conflicts = self._release_records(canonical)
        runner, runner_conflicts = self._runner_records(canonical)
        conflicts.extend(release_conflicts)
        conflicts.extend(runner_conflicts)
        terminal = dict(release)
        for reference, status in runner.items():
            if reference in terminal:
                conflicts.append(f"conflicting v1.2 terminal sources: {reference}")
            else:
                terminal[reference] = status
        return rows, terminal, sorted(set(conflicts))

    @staticmethod
    def _validate_batch_size(batch_size: int) -> int:
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            raise V12CorpusError("batch size must be an integer")
        if batch_size <= 0 or batch_size > MAX_BATCH_SIZE:
            raise V12CorpusError(f"batch size must be between 1 and {MAX_BATCH_SIZE}")
        return batch_size

    def discover(self, batch_size: int = DEFAULT_BATCH_SIZE) -> Discovery:
        batch_size = self._validate_batch_size(batch_size)
        rows, terminal, conflicts = self._state()
        remaining = [row for row in rows if _reference(row) not in terminal]
        return Discovery(
            canonical_chapters_total=len(rows),
            terminal_v1_2_chapters=len(terminal),
            chapters_remaining=len(remaining),
            requested_batch_size=batch_size,
            next_chapters=tuple(_reference(row) for row in remaining[:batch_size]) if not conflicts else (),
            full_bible_generation_authorized=self._authorized(),
            conflicts=tuple(conflicts),
        )

    def dry_run(self, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
        """Return discovery data without creating a run or calling a model."""

        return {"status": "DRY_RUN", **self.discover(batch_size).to_dict()}

    def run(self, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
        """Execute one bounded batch through the existing chapter pipeline."""

        discovery = self.discover(batch_size)
        if discovery.conflicts:
            raise V12IntegrityError("; ".join(discovery.conflicts))
        if not discovery.full_bible_generation_authorized:
            raise V12AuthorizationError(
                f"{AUTHORIZATION_FIELD} is false; generation requires explicit v1.2 authorization"
            )
        if not discovery.next_chapters:
            return {"status": "CORPUS_COMPLETE", **discovery.to_dict(), "chapters": []}

        rows, _, _ = self._state()
        selected = [row for row in rows if _reference(row) in set(discovery.next_chapters)]
        seed = canonical_json(discovery.next_chapters).encode("utf-8")
        run_id = "batch-" + hashlib.sha256(seed).hexdigest()[:16]
        run_root = self.runner_root / "runs" / run_id
        manifest = {
            "artifact_version": "commentary-v1.2-corpus-runner-manifest-v1",
            "pipeline_version": "commentary-v1.2-enrichment",
            "run_id": run_id,
            "batch_size": discovery.requested_batch_size,
            "ordering": "canonical Bible order",
            "chapters": [
                {"reference": _reference(row), "book": row["book"], "chapter": int(row["chapter"]), "canonical_ordinal": row["canonical_ordinal"]}
                for row in selected
            ],
        }
        manifest_path = run_root / "manifest.json"
        write_json(manifest_path, manifest, immutable=True)
        state_path = run_root / "state.json"
        state = (
            _load_json(state_path)
            if state_path.is_file()
            else {
                "artifact_version": "commentary-v1.2-corpus-runner-state-v1",
                "run_id": run_id,
                "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
                "chapters": {entry["reference"]: {"status": "ready", "attempt": 0} for entry in manifest["chapters"]},
            }
        )
        if state.get("manifest_sha256") != sha256_bytes(manifest_path.read_bytes()):
            raise V12IntegrityError(f"runner state belongs to a different manifest: {state_path}")

        pipeline = self.pipeline
        if pipeline is None:
            raise V12CorpusError("generation pipeline is not configured; supply an approved model configuration")
        outcomes: list[dict[str, Any]] = []
        for entry in manifest["chapters"]:
            reference = entry["reference"]
            record = state["chapters"].get(reference)
            if not isinstance(record, dict) or record.get("status") not in {"ready", *TERMINAL_RESULT_STATES}:
                raise V12IntegrityError(f"runner chapter state is not safely resumable: {reference}")
            if record.get("status") in TERMINAL_RESULT_STATES:
                outcomes.append({"reference": reference, "status": record["status"], "skipped": True})
                continue
            record["status"] = "generating"
            record["attempt"] = int(record.get("attempt", 0)) + 1
            write_json(state_path, state)
            result = pipeline.generate(entry["book"], int(entry["chapter"]))
            outcome = self._persist_result(run_root, entry, result)
            record["status"] = outcome["status"]
            record["result_path"] = outcome["result_path"]
            write_json(state_path, state)
            outcomes.append(outcome)
        return {
            "status": "BATCH_COMPLETE",
            "run_id": run_id,
            "chapters": outcomes,
            "discovery": self.discover(batch_size).to_dict(),
        }

    def _persist_result(
        self,
        run_root: Path,
        entry: dict[str, Any],
        result: CommentaryGenerationResult,
    ) -> dict[str, Any]:
        reference = entry["reference"]
        if result.reference != reference:
            raise V12IntegrityError(f"chapter pipeline identity mismatch: expected {reference}, got {result.reference}")
        if result.status not in TERMINAL_RESULT_STATES:
            raise V12IntegrityError(f"chapter pipeline returned non-terminal status for {reference}: {result.status}")
        commentary = result.commentary
        if commentary is not None:
            if (commentary.reference, commentary.book, int(commentary.chapter)) != (reference, entry["book"], int(entry["chapter"])):
                raise V12IntegrityError(f"commentary identity mismatch: {reference}")
            if commentary.status != result.status:
                raise V12IntegrityError(f"chapter pipeline status mismatch: {reference}")
        chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
        if commentary is not None:
            payload = commentary.to_dict()
            write_json(chapter_root / "commentary.json", payload, immutable=True)
        receipt = {
            "artifact_version": "commentary-v1.2-corpus-runner-result-v1",
            "reference": reference,
            "book": entry["book"],
            "chapter": int(entry["chapter"]),
            "status": result.status,
            "error": result.error,
            "commentary_path": f"chapters/{_slug(entry['book'], int(entry['chapter']))}/commentary.json" if commentary is not None else None,
        }
        result_path = chapter_root / "result.json"
        write_json(result_path, receipt, immutable=True)
        return {"reference": reference, "status": result.status, "result_path": result_path.relative_to(self.repo_root).as_posix()}


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE",
    "ExistingV12ChapterPipeline",
    "V12AuthorizationError",
    "V12CorpusError",
    "V12CorpusRunner",
    "V12IntegrityError",
]
