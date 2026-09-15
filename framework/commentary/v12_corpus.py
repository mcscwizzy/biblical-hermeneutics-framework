"""Bounded, resumable orchestration for Commentary v1.2 corpus generation.

This module owns selection and run receipts only.  Chapter generation remains
delegated to the existing CommentaryGenerator path; v1.1 and the packaged
v1.2 release are never used as writable output locations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from bhf_agent import bible
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
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    GeneratedMetadata,
)
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.chapter_commentary.output_conformance import parse_renderer_json
from bhf_agent.chapter_commentary.evidence_applicability import commentary_eligible_evidence
from bhf_agent.chapter_commentary.reader_level_projection import project_reader_level_ideas, add_projection_to_prompt
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import build_ancestry_envelope, add_ancestry_envelope_to_prompt, audit_ancestry_envelope
from bhf_agent.chapter_commentary.reader_provenance_binding_v2 import (
    ProvenanceBindingV2Error,
    build_provenance_binding_v2,
    normalize_renderer_payload_v2,
    add_provenance_binding_to_prompt_v2,
    audit_provenance_binding_v2,
    response_ancestry_audit_v2,
)
from bhf_agent.chapter_commentary.renderer_reference_presentation_v1 import present_binding, add_presentation_to_prompt, normalize_selected_chapter_scope_refs
from bhf_agent.chapter_commentary.richness_clusters import CORE_CLASSIFIER_V2, RICHNESS_POLICY_VERSION_V3, cluster_synthesis_units, score_synthesis_richness
from bhf_agent.chapter_commentary.richness import audit_chapter
from framework.commentary.production.inputs import prepare_chapter
from bhf_agent.config import AgentConfig
from framework.commentary.production.census import canonical_chapters
from framework.commentary.production.models import canonical_json, sha256_bytes, write_json
from framework.commentary.production.models import write_immutable
from framework.commentary.v12_config import V12_PIPELINE_VERSION


V12_CANDIDATE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment")
V12_RELEASE_ROOT = Path(".bhf-data/bhf-commentary-v1.2")
CORPUS_RUNNER_ROOT = V12_CANDIDATE_ROOT / "corpus-runner"
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 100
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
    {"pending", "generating", "awaiting_render", "ready"}
)


class V12CorpusError(RuntimeError):
    """A fail-closed corpus orchestration error."""


class V12AuthorizationError(V12CorpusError):
    """Generation was requested without explicit persisted authorization."""


class V12IntegrityError(V12CorpusError):
    """Persisted corpus state is inconsistent or ambiguous."""


_PROVENANCE_REF_RE = re.compile(r"(?:reader_path|render_path)_[a-z0-9_]+")


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


@dataclass(frozen=True)
class ChapterRenderability:
    """The evidence-owned decision about whether Terra may receive a chapter."""

    renderable: bool
    reason: str | None
    evidence_availability: str
    evidence_item_count: int
    synthesis_unit_count: int
    eligible_evidence_item_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "renderable": self.renderable,
            "reason": self.reason,
            "evidence_availability": self.evidence_availability,
            "evidence_item_count": self.evidence_item_count,
            "synthesis_unit_count": self.synthesis_unit_count,
            "eligible_evidence_item_count": self.eligible_evidence_item_count,
        }


def assess_chapter_renderability(prepared: Any) -> ChapterRenderability:
    """Decide renderability before any projection or ancestry is constructed.

    The synthesis compiler is the authority for whether evidence can support
    reader prose.  An empty synthesis is source-limited only when the existing
    applicability rules also found no current-chapter-eligible evidence.  If
    eligible evidence exists, an empty synthesis is an unexplained compiler
    regression and must stop the run rather than being hidden as a source gap.
    """

    evidence_items = list(prepared.bundle.evidence_items)
    synthesis = prepared.synthesis
    eligible_items = commentary_eligible_evidence(
        evidence_items, prepared.bundle.passage_ref
    )
    if synthesis.synthesis_units:
        return ChapterRenderability(
            renderable=True,
            reason=None,
            evidence_availability=synthesis.evidence_availability,
            evidence_item_count=len(evidence_items),
            synthesis_unit_count=len(synthesis.synthesis_units),
            eligible_evidence_item_count=len(eligible_items),
        )
    if eligible_items:
        raise V12IntegrityError(
            "synthesis compiler regression: empty synthesis despite "
            f"{len(eligible_items)} current-chapter-eligible evidence items "
            f"for {synthesis.reference}"
        )
    if synthesis.evidence_availability == "DATA_GAP" and not evidence_items:
        reason = (
            "existing evidence pipeline classified the chapter as DATA_GAP "
            "with zero evidence items and zero synthesis units"
        )
    else:
        reason = (
            "existing evidence applicability rules produced zero "
            "current-chapter-eligible evidence and zero synthesis units"
        )
    return ChapterRenderability(
        renderable=False,
        reason=reason,
        evidence_availability=synthesis.evidence_availability,
        evidence_item_count=len(evidence_items),
        synthesis_unit_count=0,
        eligible_evidence_item_count=0,
    )


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


CODEX_CLI = Path("/home/johnwalker/.local/bin/codex")
CODEX_TERRA_MODEL = "gpt-5.6-terra"
CODEX_TERRA_EFFORT = "high"
CODEX_PROMPT_VERSION = "1.8"


class CodexCliV12ChapterPipeline:
    """Render one chapter through an isolated, Codex-native CLI exchange."""

    def __init__(self, *, codex_path: str | Path = CODEX_CLI,
                 model: str = CODEX_TERRA_MODEL, effort: str = CODEX_TERRA_EFFORT,
                 timeout_seconds: int = 600, runner: Callable[..., subprocess.CompletedProcess[str]] | None = None):
        self.codex_path = str(codex_path)
        self.model = model
        self.effort = effort
        self.timeout_seconds = timeout_seconds
        self._runner = runner or subprocess.run

    def command(self, temp_dir: str | Path, output: str | Path) -> list[str]:
        """Build the hermetic Codex invocation used for every chapter."""

        return [
            self.codex_path, "exec", "--ephemeral", "--ignore-user-config",
            "-m", self.model, "-c", f'model_reasoning_effort="{self.effort}"',
            "-s", "read-only", "-C", str(temp_dir), "--skip-git-repo-check",
            "--output-last-message", str(output), "-",
        ]

    def _prepared(self, book: str, chapter: int, *, prepared: Any | None = None):
        prepared = prepared or prepare_chapter(book, chapter)
        assess_chapter_renderability(prepared)
        chapter_data = bible.resolve_chapter(book, chapter)
        passage_text = bible.passage_text(chapter_data.get("verses", []))
        clusters = cluster_synthesis_units(
            prepared.synthesis.synthesis_units, prepared.bundle.evidence_items,
            core_classifier=CORE_CLASSIFIER_V2,
            coverage_policy=RICHNESS_POLICY_VERSION_V3,
            passage_text=passage_text,
        )
        projection = project_reader_level_ideas(prepared.synthesis, clusters, prepared.bundle.evidence_items)
        envelope = build_ancestry_envelope(projection, prepared.synthesis, prepared.bundle.evidence_items)
        binding = build_provenance_binding_v2(envelope, prepared.synthesis, prepared.bundle.evidence_items)
        presentation = present_binding(binding, prepared.synthesis, prepared.bundle.evidence_items)
        prompt = build_user_prompt(
            prepared.packet["reference"], book, chapter, passage_text,
            prepared.synthesis, prepared.bundle, prepared.synthesis.evidence_availability,
            prompt_version=CODEX_PROMPT_VERSION,
        )
        prompt = add_projection_to_prompt(prompt, projection)
        prompt = add_ancestry_envelope_to_prompt(prompt, envelope)
        prompt = add_provenance_binding_to_prompt_v2(prompt, envelope, binding)
        prompt, _ = add_presentation_to_prompt(prompt, envelope, binding, prepared.synthesis, prepared.bundle.evidence_items)
        return prepared, binding, presentation, prompt

    def _failure(self, request: CommentaryGenerationRequest, prepared, reason: str, raw: bytes | None):
        bundle = prepared.bundle if prepared is not None else None
        metadata = GeneratedMetadata(
            evidence_hash=bundle.evidence_hash if bundle else request.evidence_hash,
            evidence_bundle_version=bundle.version if bundle else "1.0",
            commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
            commentary_prompt_version=CODEX_PROMPT_VERSION,
            model=self.model,
            synthesis_hash=prepared.synthesis.synthesis_hash if prepared else request.synthesis_hash,
            synthesis_schema_version=prepared.synthesis.synthesis_schema_version if prepared else None,
            synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version if prepared else None,
            renderer_label="commentary-v1.2-codex-cli",
        )
        commentary = ChapterCommentary(
            reference=request.reference, book=request.book, chapter=request.chapter,
            status="needs_review", sections=[], generated_metadata=metadata,
            failure_reason=reason, validation_errors=[reason],
        )
        return CommentaryGenerationResult(request.reference, "needs_review", commentary, reason, raw)

    def generate(self, book: str, chapter: int) -> CommentaryGenerationResult:
        request = CommentaryGenerationRequest(book=book, chapter=chapter, reference=f"{book} {chapter}", evidence_hash="")
        prepared = None
        raw: bytes | None = None
        try:
            prepared, binding, presentation, prompt = self._prepared(book, chapter)
            request = CommentaryGenerationRequest(book=book, chapter=chapter, reference=prepared.packet["reference"], evidence_hash=prepared.bundle.evidence_hash, synthesis_hash=prepared.synthesis.synthesis_hash)
            exchange = (
                "You are the selected GPT-5.6 Terra prose renderer at high reasoning effort. "
                "Use only the exact prompts below. Do not call tools, inspect files, browse, or use outside knowledge. "
                "Return only the requested raw JSON object.\n\nSYSTEM PROMPT\n" +
                system_prompt_for_version(CODEX_PROMPT_VERSION) + "\n\nUSER PROMPT\n" + prompt
            )
            with tempfile.TemporaryDirectory(prefix="bhf-v12-codex-") as temp_dir:
                output = Path(temp_dir) / "response.json"
                completed = self._runner(
                    self.command(temp_dir, output),
                    input=exchange, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    check=False, timeout=self.timeout_seconds,
                )
                if not output.is_file():
                    raise RuntimeError(f"Codex CLI produced no response (exit {completed.returncode}): {completed.stderr[-1000:]}")
                raw = output.read_bytes()
            payload, parse_status, parse_errors = parse_renderer_json(raw)
            if payload is None:
                return self._failure(request, prepared, "; ".join(parse_errors) or parse_status, raw)
            normalized, _ = normalize_renderer_payload_v2(payload, binding)
            normalized, _ = normalize_selected_chapter_scope_refs(normalized, binding, presentation)
            normalized["status"] = "pending"
            normalized["evidence_availability"] = prepared.synthesis.evidence_availability
            normalized["generated_metadata"] = GeneratedMetadata(
                evidence_hash=prepared.bundle.evidence_hash,
                evidence_bundle_version=prepared.bundle.version,
                commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
                commentary_prompt_version=CODEX_PROMPT_VERSION,
                model=self.model, synthesis_hash=prepared.synthesis.synthesis_hash,
                synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
                synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
                renderer_label="commentary-v1.2-codex-cli",
            ).to_dict()
            validation = validate_chapter_commentary(
                normalized, prepared.bundle, expected_evidence_hash=prepared.bundle.evidence_hash,
                expected_prompt_version=CODEX_PROMPT_VERSION, expected_reference=request.reference,
                expected_book=book, expected_chapter=chapter, synthesis=prepared.synthesis,
                expected_synthesis_hash=prepared.synthesis.synthesis_hash,
            )
            status = "validated" if validation.valid else "partial" if validation.partial else "needs_review"
            commentary = validation.commentary
            if commentary is not None:
                commentary = ChapterCommentary(
                    reference=commentary.reference, book=commentary.book, chapter=commentary.chapter,
                    status=status, evidence_availability=commentary.evidence_availability,
                    sections=list(validation.accepted_sections), generated_metadata=commentary.generated_metadata,
                    failure_reason=None if validation.valid else "Some generated material was rejected",
                    validation_errors=list(validation.errors),
                )
            else:
                return self._failure(request, prepared, "; ".join(validation.errors) or "validation failed", raw)
            return CommentaryGenerationResult(request.reference, status, commentary, None if validation.valid else "; ".join(validation.errors), raw)
        except Exception as exc:
            return self._failure(request, prepared, f"Generation failed: {exc}", raw)


def _slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{int(chapter):03d}"


def _reference(row: dict[str, Any]) -> str:
    return f"{row['book']} {int(row['chapter'])}"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise V12IntegrityError(f"invalid JSON artifact: {path}") from exc


def resolve_codex_cli(path: str | Path | None = None) -> Path:
    """Resolve the authenticated host-local Codex executable, never an API provider."""

    candidate = Path(path) if path is not None else CODEX_CLI
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate
    discovered = shutil.which("codex")
    if discovered:
        return Path(discovered)
    raise V12CorpusError(
        "host-local Codex executable is unavailable; install or expose the authenticated codex CLI"
    )


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
        generation_metadata: dict[str, Any] | None = None,
    ):
        self.repo_root = Path(repo_root)
        self.candidate_root = self._rooted(candidate_root)
        self.release_root = self._rooted(release_root)
        self.runner_root = self.candidate_root / "corpus-runner"
        self.canonical_loader = canonical_loader
        self.pipeline = pipeline
        self.generation_metadata = dict(generation_metadata or {})

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

    def _runner_records(self, canonical: dict[str, dict[str, Any]]) -> tuple[dict[str, str], dict[str, str], list[str]]:
        records: dict[str, str] = {}
        release_states: dict[str, str] = {}
        conflicts: list[str] = []
        runs_root = self.runner_root / "runs"
        if not runs_root.is_dir():
            return records, release_states, conflicts
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
            classification = result.get("classification")
            derived_release_state = {
                "published": "PUBLISHED",
                "source-limited": "NOT_RENDERABLE_SOURCE_LIMITED",
                "model-rejected": "MODEL_OUTPUT_REJECTED",
                "quality-review": "QUALITY_REVIEW_REQUIRED",
            }.get(classification)
            # The lightweight ChapterPipeline contract used by tests and
            # older local callers predates result classification. Preserve
            # its terminal-state behavior while treating persisted v1.2
            # corpus classifications as authoritative when present.
            if derived_release_state is None and classification is None:
                derived_release_state = (
                    "PUBLISHED"
                    if status == "validated"
                    else "QUALITY_REVIEW_REQUIRED"
                    if status in {"partial", "needs_review"}
                    else "MODEL_OUTPUT_REJECTED"
                )
            if derived_release_state is None:
                conflicts.append(f"runner result has unknown release classification for {reference}: {classification}")
            else:
                release_states[reference] = derived_release_state
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
                if status in NONTERMINAL_RESULT_STATES:
                    if status == "generating" and state.get("artifact_version") != "commentary-v1.2-corpus-runner-state-v1":
                        conflicts.append(f"runner chapter is in-flight: {reference}")
                    continue
                if status not in TERMINAL_RESULT_STATES:
                    conflicts.append(f"runner state has unknown status for {reference}: {status}")
                elif records.get(reference) != status:
                    conflicts.append(f"runner state/result disagreement: {reference}")
        return records, release_states, conflicts

    def _state(self) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
        rows, canonical, conflicts = self._canonical()
        release, release_conflicts = self._release_records(canonical)
        runner, runner_release_states, runner_conflicts = self._runner_records(canonical)
        conflicts.extend(release_conflicts)
        conflicts.extend(runner_conflicts)
        terminal = dict(release)
        for reference, status in runner.items():
            if reference in terminal:
                if terminal[reference] != runner_release_states.get(reference):
                    conflicts.append(f"conflicting v1.2 terminal sources: {reference}")
            else:
                terminal[reference] = runner_release_states[reference]
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

    def _selected_manifest(self, discovery: Discovery, *, run_id: str) -> dict[str, Any]:
        rows, _, conflicts = self._state()
        if conflicts:
            raise V12IntegrityError("; ".join(conflicts))
        selected_refs = set(discovery.next_chapters)
        selected = [row for row in rows if _reference(row) in selected_refs]
        finalized_batch_numbers = {
            int(manifest.get("batch_number", 0))
            for path in self.runner_root.glob("runs/*/manifest.json")
            if (manifest := _load_json(path)).get("workflow") == "prepare -> codex_session_render -> finalize"
            and (path.parent / "state.json").is_file()
            and _load_json(path.parent / "state.json").get("finalized") is True
        }
        manifest: dict[str, Any] = {
            "artifact_version": "commentary-v1.2-corpus-session-manifest-v1",
            "pipeline_version": V12_PIPELINE_VERSION,
            "workflow": "prepare -> codex_session_render -> finalize",
            "run_id": run_id,
            "batch_number": max(finalized_batch_numbers, default=0) + 1,
            "batch_size": discovery.requested_batch_size,
            "ordering": "canonical Bible order",
            "renderer_mode": "codex_session",
            "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT,
            "one_generation_per_chapter": True,
            "chapters": [
                {
                    "reference": _reference(row), "book": row["book"],
                    "chapter": int(row["chapter"]),
                    "canonical_ordinal": row["canonical_ordinal"],
                }
                for row in selected
            ],
        }
        if self.generation_metadata:
            manifest["generation"] = dict(self.generation_metadata)
        return manifest

    def _resumable_session(self) -> tuple[Path, dict[str, Any]] | None:
        """Return the earliest incomplete session, before fresh discovery."""

        candidates: list[tuple[int, str, Path, dict[str, Any]]] = []
        for manifest_path in self.runner_root.glob("runs/*/manifest.json"):
            manifest = _load_json(manifest_path)
            if manifest.get("workflow") != "prepare -> codex_session_render -> finalize":
                continue
            state_path = manifest_path.parent / "state.json"
            if not state_path.is_file():
                continue
            state = _load_json(state_path)
            if state.get("finalized") is True or state.get("retired") is True:
                continue
            chapters = state.get("chapters")
            if not isinstance(chapters, dict) or not any(
                isinstance(record, dict) and record.get("status") == "awaiting_render"
                for record in chapters.values()
            ):
                continue
            candidates.append((
                int(manifest.get("batch_number", 0)),
                str(manifest.get("run_id", manifest_path.parent.name)),
                manifest_path,
                manifest,
            ))
        if not candidates:
            return None
        _, _, manifest_path, manifest = min(candidates)
        return manifest_path, manifest

    def _incomplete_session(self) -> tuple[Path, dict[str, Any]] | None:
        """Return the oldest unfinalized session, including all-source batches."""

        candidates: list[tuple[int, str, Path, dict[str, Any]]] = []
        for manifest_path in self.runner_root.glob("runs/*/manifest.json"):
            manifest = _load_json(manifest_path)
            if manifest.get("workflow") != "prepare -> codex_session_render -> finalize":
                continue
            state_path = manifest_path.parent / "state.json"
            if not state_path.is_file():
                continue
            state = _load_json(state_path)
            if state.get("finalized") is True or state.get("retired") is True:
                continue
            candidates.append((
                int(manifest.get("batch_number", 0)),
                str(manifest.get("run_id", manifest_path.parent.name)),
                manifest_path,
                manifest,
            ))
        if not candidates:
            return None
        _, _, manifest_path, manifest = min(candidates)
        return manifest_path, manifest

    def retire_invalid_session(self, run_id: str, *, batch_size: int = MAX_BATCH_SIZE) -> dict[str, Any]:
        """Retire an unrendered, noncanonical frozen session without deleting it."""

        if not isinstance(run_id, str) or not run_id.startswith("session-batch-"):
            raise V12IntegrityError("retirement requires a concrete codex-session run id")
        run_root = self.runner_root / "runs" / run_id
        manifest_path = run_root / "manifest.json"
        state_path = run_root / "state.json"
        if not manifest_path.is_file() or not state_path.is_file():
            raise V12CorpusError(f"prepared session does not exist: {run_id}")
        manifest = _load_json(manifest_path)
        state = _load_json(state_path)
        if manifest.get("workflow") != "prepare -> codex_session_render -> finalize":
            raise V12IntegrityError(f"run is not a codex-session manifest: {run_id}")
        if state.get("finalized") is True:
            raise V12IntegrityError(f"cannot retire a finalized session: {run_id}")
        if state.get("retired") is True:
            raise V12IntegrityError(f"session is already retired: {run_id}")
        if state.get("manifest_sha256") != sha256_bytes(manifest_path.read_bytes()):
            raise V12IntegrityError(f"prepared manifest identity changed: {run_id}")
        entries = manifest.get("chapters")
        if not isinstance(entries, list) or not entries:
            raise V12IntegrityError(f"invalid prepared session chapter list: {run_id}")
        manifest_refs = tuple(entry.get("reference") for entry in entries)
        if any(not isinstance(reference, str) for reference in manifest_refs):
            raise V12IntegrityError(f"invalid prepared session chapter identity: {run_id}")
        chapter_states = state.get("chapters")
        if not isinstance(chapter_states, dict) or set(chapter_states) != set(manifest_refs):
            raise V12IntegrityError(f"prepared session state/manifest disagreement: {run_id}")
        if any(record.get("status") != "awaiting_render" for record in chapter_states.values() if isinstance(record, dict)):
            raise V12IntegrityError(f"only wholly unrendered sessions may be retired: {run_id}")
        if any(not isinstance(record, dict) for record in chapter_states.values()):
            raise V12IntegrityError(f"invalid prepared session state: {run_id}")
        if list(run_root.glob("chapters/*/raw-response.bin")) or list(run_root.glob("chapters/*/result.json")):
            raise V12IntegrityError(f"cannot retire a session with responses or results: {run_id}")
        discovery = self.discover(batch_size)
        if discovery.conflicts:
            raise V12IntegrityError("; ".join(discovery.conflicts))
        expected = discovery.next_chapters
        if manifest_refs == expected:
            raise V12IntegrityError(f"session matches the current canonical batch and must be resumed: {run_id}")
        rows, terminal, conflicts = self._state()
        if conflicts:
            raise V12IntegrityError("; ".join(conflicts))
        duplicate_terminal_refs = tuple(reference for reference in manifest_refs if reference in terminal)
        if not duplicate_terminal_refs:
            raise V12IntegrityError(f"session is not demonstrably superseded by terminal work: {run_id}")
        receipt = {
            "artifact_version": "commentary-v1.2-corpus-session-retirement-v1",
            "run_id": run_id,
            "batch_number": manifest.get("batch_number"),
            "status": "RETIRED",
            "reason": "superseded_duplicate_preparation_after_prior_batch_finalization",
            "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
            "manifest_chapters": list(manifest_refs),
            "canonical_next_chapters": list(expected),
            "duplicate_terminal_chapters": list(duplicate_terminal_refs),
            "raw_response_count": 0,
            "result_count": 0,
        }
        receipt_path = run_root / "retirement.json"
        write_json(receipt_path, receipt, immutable=True)
        state["retired"] = True
        state["retirement_path"] = receipt_path.relative_to(self.repo_root).as_posix()
        state["retirement_sha256"] = sha256_bytes(receipt_path.read_bytes())
        write_json(state_path, state)
        return receipt

    @staticmethod
    def _session_run_id(next_chapters: tuple[str, ...]) -> str:
        seed = canonical_json({"workflow": "codex_session", "chapters": next_chapters}).encode("utf-8")
        return "session-batch-" + hashlib.sha256(seed).hexdigest()[:16]

    def _renderer_context(self, entry: dict[str, Any], *, prepared: Any | None = None):
        """Build the exact v1.2 contract once, with no renderer invocation."""

        pipeline = CodexCliV12ChapterPipeline(
            model=CODEX_TERRA_MODEL, effort=CODEX_TERRA_EFFORT
        )
        prepared, binding, presentation, user_prompt = pipeline._prepared(
            entry["book"], int(entry["chapter"]), prepared=prepared
        )
        chapter_data = bible.resolve_chapter(entry["book"], int(entry["chapter"]))
        clusters = cluster_synthesis_units(
            prepared.synthesis.synthesis_units, prepared.bundle.evidence_items,
            core_classifier=CORE_CLASSIFIER_V2, coverage_policy=RICHNESS_POLICY_VERSION_V3,
            passage_text=bible.passage_text(chapter_data.get("verses", [])),
        )
        projection = project_reader_level_ideas(prepared.synthesis, clusters, prepared.bundle.evidence_items)
        envelope = build_ancestry_envelope(projection, prepared.synthesis, prepared.bundle.evidence_items)
        system_prompt = system_prompt_for_version(CODEX_PROMPT_VERSION)
        return prepared, projection, envelope, binding, presentation, system_prompt, user_prompt

    def _write_renderer_input(
        self, run_root: Path, entry: dict[str, Any], *, run_id: str,
        prepared: Any | None = None,
    ) -> dict[str, Any]:
        prepared, projection, envelope, binding, presentation, system_prompt, user_prompt = self._renderer_context(entry, prepared=prepared)
        input_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"])) / "renderer-input"
        system_bytes = system_prompt.encode("utf-8")
        user_bytes = user_prompt.encode("utf-8")
        contract = {
            "artifact_version": "commentary-v1.2-renderer-input-v1",
            "run_id": run_id,
            "reference": entry["reference"], "book": entry["book"],
            "chapter": int(entry["chapter"]),
            "canonical_ordinal": entry["canonical_ordinal"],
            "renderer_mode": "codex_session",
            "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT,
            "commentary_prompt_version": CODEX_PROMPT_VERSION,
            "system_prompt_sha256": sha256_bytes(system_bytes),
            "user_prompt_sha256": sha256_bytes(user_bytes),
            "renderer_input_sha256": sha256_bytes(system_bytes + b"\n\nUSER PROMPT\n" + user_bytes),
            "evidence_hash": prepared.bundle.evidence_hash,
            "synthesis_hash": prepared.synthesis.synthesis_hash,
            "source_packet_id": prepared.row["input_identity"]["packet_id"],
            "source_packet_hash": prepared.row["input_identity"]["packet_hash"],
            "projection_hash": projection.projection_hash,
            "ancestry_envelope_hash": envelope.get("envelope_hash"),
            "binding_hash": binding.get("binding_hash"),
            "response_path": f"chapters/{_slug(entry['book'], int(entry['chapter']))}/raw-response.bin",
            "generation_count": 0,
        }
        write_immutable(input_root / "system_prompt.txt", system_bytes)
        write_immutable(input_root / "user_prompt.txt", user_bytes)
        write_json(input_root / "metadata.json", contract, immutable=True)
        return contract

    @staticmethod
    def _source_limited_receipt(
        run_root: Path,
        entry: dict[str, Any],
        prepared: Any,
        assessment: ChapterRenderability,
    ) -> dict[str, Any]:
        """Persist a terminal evidence receipt without renderer artifacts."""

        chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
        receipt = {
            "artifact_version": "commentary-v1.2-corpus-result-v1",
            "reference": entry["reference"],
            "book": entry["book"],
            "chapter": int(entry["chapter"]),
            "canonical_ordinal": entry["canonical_ordinal"],
            "status": "validated",
            "classification": "source-limited",
            "release_state": "NOT_RENDERABLE_SOURCE_LIMITED",
            "reason": "commentary_source_limited",
            "source_limited_reason": assessment.reason,
            "evidence_availability": assessment.evidence_availability,
            "evidence_item_count": assessment.evidence_item_count,
            "synthesis_unit_count": assessment.synthesis_unit_count,
            "eligible_evidence_item_count": assessment.eligible_evidence_item_count,
            "evidence_hash": prepared.bundle.evidence_hash,
            "synthesis_hash": prepared.synthesis.synthesis_hash,
            "source_packet_id": prepared.row["input_identity"]["packet_id"],
            "source_packet_hash": prepared.row["input_identity"]["packet_hash"],
            "commentary_path": None,
            "raw_response_path": None,
        }
        write_json(chapter_root / "result.json", receipt, immutable=True)
        return receipt

    @staticmethod
    def _is_source_limited_receipt(receipt: Any) -> bool:
        return (
            isinstance(receipt, dict)
            and receipt.get("release_state") == "NOT_RENDERABLE_SOURCE_LIMITED"
            and receipt.get("classification") == "source-limited"
            and receipt.get("status") == "validated"
        )

    def _prepared_for_session(self, entry: dict[str, Any]):
        prepared = prepare_chapter(entry["book"], int(entry["chapter"]))
        return prepared, assess_chapter_renderability(prepared)

    def prepare(self, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
        """Freeze one bounded batch for direct rendering in this Codex session."""

        discovery = self.discover(batch_size)
        if discovery.conflicts:
            raise V12IntegrityError("; ".join(discovery.conflicts))
        if not discovery.full_bible_generation_authorized:
            raise V12AuthorizationError(
                f"{AUTHORIZATION_FIELD} is false; preparation requires explicit v1.2 authorization"
            )
        if not discovery.next_chapters:
            return {"status": "CORPUS_COMPLETE", **discovery.to_dict(), "chapters": []}
        resumable = self._resumable_session()
        if resumable is None:
            run_id = self._session_run_id(discovery.next_chapters)
            manifest = self._selected_manifest(discovery, run_id=run_id)
        else:
            manifest_path, manifest = resumable
            run_id = str(manifest.get("run_id") or manifest_path.parent.name)
        run_root = self.runner_root / "runs" / run_id
        manifest_path = run_root / "manifest.json"
        write_json(manifest_path, manifest, immutable=True)
        manifest_hash = sha256_bytes(manifest_path.read_bytes())
        state_path = run_root / "state.json"
        if state_path.is_file():
            state = _load_json(state_path)
            if state.get("manifest_sha256") != manifest_hash:
                raise V12IntegrityError(f"runner state belongs to a different manifest: {state_path}")
            if any(record.get("status") == "generating" for record in state.get("chapters", {}).values() if isinstance(record, dict)):
                # A prior nested transport can leave only its checkpoint behind.
                # It is recoverable only when no raw response exists yet.
                for entry in manifest["chapters"]:
                    chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
                    if (chapter_root / "raw-response.bin").exists():
                        raise V12IntegrityError(f"in-flight chapter already has a response: {entry['reference']}")
                state["chapters"] = {entry["reference"]: {"status": "awaiting_render", "attempt": 0} for entry in manifest["chapters"]}
        else:
            state = {
                "artifact_version": "commentary-v1.2-corpus-session-state-v1",
                "run_id": run_id, "manifest_sha256": manifest_hash,
                "renderer_mode": "codex_session", "requested_model": CODEX_TERRA_MODEL,
                "requested_effort": CODEX_TERRA_EFFORT,
                "chapters": {entry["reference"]: {"status": "awaiting_render", "attempt": 0} for entry in manifest["chapters"]},
            }
        renderable: list[str] = []
        source_limited: list[dict[str, Any]] = []
        for entry in manifest["chapters"]:
            record = state["chapters"].get(entry["reference"])
            if not isinstance(record, dict) or record.get("status") not in {"awaiting_render", *TERMINAL_RESULT_STATES}:
                raise V12IntegrityError(f"runner chapter state is not safely resumable: {entry['reference']}")
            if record.get("status") == "awaiting_render":
                prepared, assessment = self._prepared_for_session(entry)
                if not assessment.renderable:
                    receipt = self._source_limited_receipt(run_root, entry, prepared, assessment)
                    record.update({
                        "status": "validated",
                        "classification": "source-limited",
                        "release_state": receipt["release_state"],
                        "result_path": f"chapters/{_slug(entry['book'], int(entry['chapter']))}/result.json",
                    })
                    source_limited.append({
                        "reference": entry["reference"],
                        **assessment.to_dict(),
                    })
                else:
                    contract = self._write_renderer_input(
                        run_root, entry, run_id=run_id, prepared=prepared
                    )
                    record["renderer_input_path"] = f"chapters/{_slug(entry['book'], int(entry['chapter']))}/renderer-input"
                    record["renderer_input_sha256"] = contract["renderer_input_sha256"]
                    renderable.append(entry["reference"])
                # Checkpoint after every chapter so an interrupted preparation
                # can resume without losing the immutable identity proof.
                write_json(state_path, state)
            elif self._is_source_limited_receipt(
                _load_json(run_root / "chapters" / _slug(entry["book"], int(entry["chapter"])) / "result.json")
                if (run_root / "chapters" / _slug(entry["book"], int(entry["chapter"])) / "result.json").is_file()
                else None
            ):
                source_limited.append({"reference": entry["reference"], "status": "already_terminal"})
            elif record.get("status") == "awaiting_render":
                raise V12IntegrityError(f"runner chapter state is not safely resumable: {entry['reference']}")
        write_json(state_path, state)
        return {
            "status": "PREPARED", "run_id": run_id,
            "renderer_mode": "codex_session", "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT,
            "chapter_count": len(manifest["chapters"]),
            "renderable_count": len(renderable),
            "source_limited_count": len(source_limited),
            "renderable": renderable,
            "source_limited": source_limited,
            "chapters": [entry["reference"] for entry in manifest["chapters"]],
            "manifest_path": manifest_path.relative_to(self.repo_root).as_posix(),
        }

    def _prepared_run(self, run_id: str) -> tuple[Path, dict[str, Any], Path, dict[str, Any]]:
        """Load exactly one non-finalized prepared session, without discovery."""

        if not run_id or Path(run_id).name != run_id:
            raise V12CorpusError("render-local requires a concrete prepared session run id")
        run_root = self.runner_root / "runs" / run_id
        manifest_path = run_root / "manifest.json"
        state_path = run_root / "state.json"
        if not manifest_path.is_file() or not state_path.is_file():
            raise V12CorpusError(f"unknown prepared session run: {run_id}")
        manifest, state = _load_json(manifest_path), _load_json(state_path)
        if manifest.get("workflow") != "prepare -> codex_session_render -> finalize":
            raise V12IntegrityError(f"run is not a prepared Codex session: {run_id}")
        if manifest.get("run_id") != run_id or state.get("run_id") != run_id:
            raise V12IntegrityError(f"prepared run identity mismatch: {run_id}")
        if state.get("finalized") is True or state.get("retired") is True:
            raise V12IntegrityError(f"prepared run is not renderable: {run_id}")
        if state.get("manifest_sha256") != sha256_bytes(manifest_path.read_bytes()):
            raise V12IntegrityError(f"prepared manifest identity changed: {run_id}")
        entries = manifest.get("chapters")
        chapters = state.get("chapters")
        if not isinstance(entries, list) or not entries or not isinstance(chapters, dict):
            raise V12IntegrityError(f"prepared run is structurally invalid: {run_id}")
        references = {entry.get("reference") for entry in entries if isinstance(entry, dict)}
        if len(references) != len(entries) or set(chapters) != references:
            raise V12IntegrityError(f"prepared run manifest/state chapter disagreement: {run_id}")
        return run_root, manifest, state_path, state

    def _local_renderer_input(self, run_root: Path, entry: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        input_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"])) / "renderer-input"
        metadata = _load_json(input_root / "metadata.json")
        system_prompt = (input_root / "system_prompt.txt").read_text(encoding="utf-8")
        user_prompt = (input_root / "user_prompt.txt").read_text(encoding="utf-8")
        expected = sha256_bytes(
            system_prompt.encode("utf-8") + b"\n\nUSER PROMPT\n" + user_prompt.encode("utf-8")
        )
        if metadata.get("renderer_input_sha256") != expected:
            raise V12IntegrityError(f"frozen renderer-input identity changed for {entry['reference']}")
        checks = {
            "run_id": metadata.get("run_id"),
            "reference": metadata.get("reference"),
            "book": metadata.get("book"),
            "chapter": metadata.get("chapter"),
            "requested_model": metadata.get("requested_model"),
            "requested_effort": metadata.get("requested_effort"),
        }
        expected_contract = {
            "run_id": run_root.name,
            "reference": entry["reference"],
            "book": entry["book"],
            "chapter": int(entry["chapter"]),
            "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT,
        }
        if checks != expected_contract:
            raise V12IntegrityError(f"frozen renderer contract disagrees for {entry['reference']}")
        return system_prompt, user_prompt, metadata

    @staticmethod
    def _local_exchange(system_prompt: str, user_prompt: str) -> str:
        return (
            "You are the selected GPT-5.6 Terra prose renderer at high reasoning effort. "
            "Treat the supplied BHF SYSTEM PROMPT and USER PROMPT as the complete and authoritative "
            "generation contract. Do not call tools, inspect files, browse, use web research, outside "
            "commentary, unsupported facts, or additional theology. Return only the requested raw JSON "
            "object, with no Markdown fence or preamble.\n\nSYSTEM PROMPT\n"
            + system_prompt + "\n\nUSER PROMPT\n" + user_prompt
        )

    def _existing_local_response(self, run_root: Path, entry: dict[str, Any]) -> bool:
        chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
        raw_path, receipt_path = chapter_root / "raw-response.bin", chapter_root / "renderer-receipt.json"
        if not raw_path.exists():
            if receipt_path.exists():
                raise V12IntegrityError(f"response receipt exists without raw response for {entry['reference']}")
            return False
        if not receipt_path.is_file():
            raise V12IntegrityError(f"raw response has no host-local receipt for {entry['reference']}")
        receipt = _load_json(receipt_path)
        if receipt != {
            "artifact_version": "commentary-v1.2-host-local-render-receipt-v1",
            "run_id": run_root.name,
            "reference": entry["reference"],
            "book": entry["book"],
            "chapter": int(entry["chapter"]),
            "renderer_mode": "codex_cli_local",
            "transport": "local_codex_cli",
            "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT,
            "raw_response_sha256": sha256_bytes(raw_path.read_bytes()),
        }:
            raise V12IntegrityError(f"existing response identity conflicts for {entry['reference']}")
        return True

    def render_local(
        self,
        run_id: str,
        *,
        codex_path: str | Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        timeout_seconds: int = 600,
        finalize: bool = False,
    ) -> dict[str, Any]:
        """Render only missing responses from an existing frozen session on the host.

        This transport is deliberately for a normal authenticated local terminal.
        It does no discovery, does not call an API provider, and never rewrites a
        first response. Tests inject ``runner``; production uses ``subprocess.run``.
        """

        run_root, manifest, state_path, state = self._prepared_run(run_id)
        executable = resolve_codex_cli(codex_path)
        invoke = runner or subprocess.run
        rendered: list[str] = []
        skipped: list[str] = []
        source_limited: list[str] = []
        state["renderer"] = {
            "renderer_mode": "codex_cli_local",
            "transport": "local_codex_cli",
            "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT,
            "codex_executable": str(executable),
        }
        write_json(state_path, state)
        for index, entry in enumerate(manifest["chapters"], 1):
            reference = entry["reference"]
            record = state["chapters"][reference]
            if record.get("classification") == "source-limited":
                source_limited.append(reference)
                continue
            if record.get("status") != "awaiting_render":
                raise V12IntegrityError(f"unexpected render state for {reference}: {record.get('status')}")
            if self._existing_local_response(run_root, entry):
                skipped.append(reference)
                print(f"[{index}/{len(manifest['chapters'])}] {reference} SKIP already rendered", flush=True)
                continue
            system_prompt, user_prompt, metadata = self._local_renderer_input(run_root, entry)
            chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
            with tempfile.TemporaryDirectory(prefix="bhf-v12-local-render-") as temp_dir:
                output = Path(temp_dir) / "response.bin"
                transport = CodexCliV12ChapterPipeline(
                    codex_path=executable, model=CODEX_TERRA_MODEL,
                    effort=CODEX_TERRA_EFFORT, timeout_seconds=timeout_seconds,
                )
                completed = invoke(
                    transport.command(temp_dir, output), input=self._local_exchange(system_prompt, user_prompt),
                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=timeout_seconds,
                )
                if completed.returncode != 0 or not output.is_file():
                    attempt = int(record.get("transport_attempt", 0)) + 1
                    diagnostic = {
                        "artifact_version": "commentary-v1.2-host-local-render-failure-v1",
                        "run_id": run_id, "reference": reference, "attempt": attempt,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout or "", "stderr": completed.stderr or "",
                    }
                    write_json(chapter_root / "transport-failures" / f"attempt-{attempt:03d}.json", diagnostic, immutable=True)
                    record.update({"transport_attempt": attempt, "last_transport_error": f"exit {completed.returncode}; no response bytes"})
                    write_json(state_path, state)
                    raise V12CorpusError(f"host-local Codex rendering failed for {reference}: exit {completed.returncode}")
                raw = output.read_bytes()
            raw_path = chapter_root / "raw-response.bin"
            try:
                write_immutable(raw_path, raw)
            except Exception as exc:
                raise V12IntegrityError(f"raw response collision for {reference}") from exc
            receipt = {
                "artifact_version": "commentary-v1.2-host-local-render-receipt-v1",
                "run_id": run_id, "reference": reference, "book": entry["book"], "chapter": int(entry["chapter"]),
                "renderer_mode": "codex_cli_local", "transport": "local_codex_cli",
                "requested_model": CODEX_TERRA_MODEL, "requested_effort": CODEX_TERRA_EFFORT,
                "raw_response_sha256": sha256_bytes(raw),
            }
            write_json(chapter_root / "renderer-receipt.json", receipt, immutable=True)
            record.update({"transport_attempt": int(record.get("transport_attempt", 0)) + 1, "renderer_receipt_path": f"chapters/{_slug(entry['book'], int(entry['chapter']))}/renderer-receipt.json"})
            write_json(state_path, state)
            rendered.append(reference)
            print(f"[{index}/{len(manifest['chapters'])}] {reference} RENDER", flush=True)
        missing = [entry["reference"] for entry in manifest["chapters"] if state["chapters"][entry["reference"]].get("classification") != "source-limited" and not self._existing_local_response(run_root, entry)]
        if missing:
            raise V12CorpusError("host-local rendering remains incomplete: " + ", ".join(missing))
        result: dict[str, Any] = {
            "status": "RENDER_LOCAL_COMPLETE", "run_id": run_id,
            "renderer_mode": "codex_cli_local", "transport": "local_codex_cli",
            "codex_executable": str(executable), "requested_model": CODEX_TERRA_MODEL,
            "requested_effort": CODEX_TERRA_EFFORT, "rendered": rendered,
            "skipped": skipped, "source_limited": source_limited,
        }
        if finalize:
            result["finalize"] = self.finalize(run_id=run_id)
            result["next_dry_run"] = self.dry_run(MAX_BATCH_SIZE)
        return result

    def _prepared_for_finalize(self, entry: dict[str, Any], run_root: Path):
        prepared, projection, envelope, binding, presentation, system_prompt, user_prompt = self._renderer_context(entry)
        input_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"])) / "renderer-input"
        metadata = _load_json(input_root / "metadata.json")
        checks = {
            "system_prompt_sha256": sha256_bytes(system_prompt.encode("utf-8")),
            "user_prompt_sha256": sha256_bytes(user_prompt.encode("utf-8")),
            "evidence_hash": prepared.bundle.evidence_hash,
            "synthesis_hash": prepared.synthesis.synthesis_hash,
            "source_packet_id": prepared.row["input_identity"]["packet_id"],
            "source_packet_hash": prepared.row["input_identity"]["packet_hash"],
            "binding_hash": binding.get("binding_hash"),
            "projection_hash": projection.projection_hash,
            "ancestry_envelope_hash": envelope.get("envelope_hash"),
        }
        for key, expected in checks.items():
            # The first resumable prepare checkpoint predates recording the
            # two derived-view hashes. Its exact prompt bytes plus source
            # packet/evidence/synthesis identities remain frozen and are the
            # authoritative compatibility proof for that checkpoint.
            if key in {"projection_hash", "ancestry_envelope_hash"} and metadata.get(key) is None:
                continue
            if metadata.get(key) != expected:
                raise V12IntegrityError(f"frozen renderer identity changed for {entry['reference']}: {key}")
        return prepared, projection, envelope, binding, presentation

    @staticmethod
    def _offending_provenance_ref(error: str) -> str | None:
        match = _PROVENANCE_REF_RE.search(error)
        return match.group(0) if match else None

    def _model_rejected_receipt(
        self,
        run_root: Path,
        entry: dict[str, Any],
        raw: bytes,
        *,
        error: str,
        validator: str,
        classification: str = "model-rejected",
        reason: str = "renderer output failed validation",
        failure_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Persist an immutable, diagnostic terminal receipt for one bad output.

        This helper is intentionally limited to failures observed while
        interpreting the chapter's already-receipted raw response.  Frozen
        input, receipt, and run-integrity failures remain exceptions handled by
        finalization preflight.
        """

        chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
        raw_path = chapter_root / "raw-response.bin"
        raw_sha256 = sha256_bytes(raw)
        receipt_path = chapter_root / "renderer-receipt.json"
        renderer_receipt = _load_json(receipt_path) if receipt_path.is_file() else None
        diagnostic = {
            "artifact_version": "commentary-v1.2-model-output-diagnostic-v1",
            "reference": entry["reference"],
            "run_id": run_root.name,
            "validator": validator,
            "validator_error": error,
            "failure_codes": list(failure_codes or []),
            "offending_provenance_ref": self._offending_provenance_ref(error),
            "raw_response_sha256": raw_sha256,
            "raw_response_path": raw_path.relative_to(self.repo_root).as_posix(),
            "renderer_receipt": renderer_receipt,
        }
        result = {
            "artifact_version": "commentary-v1.2-corpus-result-v1",
            "reference": entry["reference"],
            "book": entry["book"],
            "chapter": int(entry["chapter"]),
            "status": "failed",
            "classification": classification,
            "release_state": "MODEL_OUTPUT_REJECTED",
            "reason": reason,
            "error": error,
            "commentary_path": None,
            "raw_response_sha256": raw_sha256,
            "raw_response_path": raw_path.relative_to(self.repo_root).as_posix(),
            "model_output_diagnostic": diagnostic,
        }
        result_path = chapter_root / "result.json"
        if result_path.is_file():
            existing = _load_json(result_path)
            if (
                existing.get("raw_response_sha256") != raw_sha256
                or existing.get("reference") != entry["reference"]
            ):
                raise V12IntegrityError(
                    f"conflicting existing result for {entry['reference']}"
                )
            return existing
        write_json(result_path, result, immutable=True)
        return result

    def _finalize_one(self, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
        chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
        raw_path = chapter_root / "raw-response.bin"
        response_candidates = list(chapter_root.glob("raw-response*"))
        if len(response_candidates) > 1:
            raise V12IntegrityError(f"duplicate/conflicting responses for {entry['reference']}")
        if not raw_path.is_file():
            raise V12CorpusError(f"missing raw response for {entry['reference']}: {raw_path}")
        raw = raw_path.read_bytes()
        prepared, projection, envelope, binding, presentation = self._prepared_for_finalize(entry, run_root)
        payload, parse_status, parse_errors = parse_renderer_json(raw)
        chapter_dir = chapter_root
        if payload is None:
            return self._model_rejected_receipt(
                run_root,
                entry,
                raw,
                error="; ".join(parse_errors) or parse_status,
                validator="parse_renderer_json",
                classification="malformed",
                reason="malformed renderer JSON",
                failure_codes=[parse_status],
            )
        try:
            normalized, binding_metadata = normalize_renderer_payload_v2(payload, binding)
            normalized, conformance_metadata = normalize_selected_chapter_scope_refs(normalized, binding, presentation)
        except ProvenanceBindingV2Error as exc:
            code = getattr(exc, "code", "PROVENANCE_VALIDATION_FAILED")
            reason = (
                "invalid provenance reference"
                if "PROVENANCE" in code
                else "renderer output failed validation"
            )
            return self._model_rejected_receipt(
                run_root,
                entry,
                raw,
                error=str(exc),
                validator="normalize_renderer_payload_v2",
                reason=reason,
                failure_codes=[code],
            )
        normalized["status"] = "pending"
        normalized["evidence_availability"] = prepared.synthesis.evidence_availability
        normalized["generated_metadata"] = GeneratedMetadata(
            evidence_hash=prepared.bundle.evidence_hash, evidence_bundle_version=prepared.bundle.version,
            commentary_schema_version=COMMENTARY_SCHEMA_VERSION, commentary_prompt_version=CODEX_PROMPT_VERSION,
            model=CODEX_TERRA_MODEL, synthesis_hash=prepared.synthesis.synthesis_hash,
            synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
            synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
            renderer_label="commentary-v1.2-codex-session",
        ).to_dict()
        validation = validate_chapter_commentary(
            normalized, prepared.bundle, expected_evidence_hash=prepared.bundle.evidence_hash,
            expected_prompt_version=CODEX_PROMPT_VERSION, expected_reference=entry["reference"],
            expected_book=entry["book"], expected_chapter=int(entry["chapter"]),
            synthesis=prepared.synthesis, expected_synthesis_hash=prepared.synthesis.synthesis_hash,
        )
        status = "validated" if validation.valid else "partial" if validation.partial else "needs_review"
        commentary = validation.commentary
        accepted_blocks = [block for section in validation.accepted_sections for block in section.blocks]
        ancestry_audit = response_ancestry_audit_v2(normalized, binding)
        binding_audit = audit_provenance_binding_v2(binding, envelope, prepared.synthesis, prepared.bundle.evidence_items)
        envelope_audit = audit_ancestry_envelope(envelope, projection, prepared.synthesis)
        quality_audit = audit_chapter(entry["book"], int(entry["chapter"]), commentary, prepared.bundle) if commentary is not None else {"richness_status": "missing"}
        richness_score = score_synthesis_richness(
            prepared.synthesis.synthesis_units, evidence_items=prepared.bundle.evidence_items,
            consumed_synthesis_ids=[sid for block in accepted_blocks for sid in getattr(block, "synthesis_ids", [])],
            blocks=accepted_blocks, passage_ref=prepared.bundle.passage_ref,
            core_classifier=CORE_CLASSIFIER_V2, coverage_policy=RICHNESS_POLICY_VERSION_V3,
            passage_text=bible.passage_text(bible.resolve_chapter(entry["book"], int(entry["chapter"])).get("verses", [])),
        )
        audits = {
            "ancestry": ancestry_audit,
            "provenance_binding": binding_audit,
            "envelope": envelope_audit,
            "quality": quality_audit,
            "richness": richness_score.to_dict(),
        }
        if validation.valid and not (ancestry_audit.get("valid") and binding_audit.get("valid") and envelope_audit.get("valid")):
            status = "needs_review"
        if commentary is not None:
            commentary = ChapterCommentary(
                reference=commentary.reference, book=commentary.book, chapter=commentary.chapter,
                status=status, evidence_availability=commentary.evidence_availability,
                sections=list(validation.accepted_sections), generated_metadata=commentary.generated_metadata,
                failure_reason=None if validation.valid else "Some generated material was rejected",
                validation_errors=list(validation.errors),
            )
            write_json(chapter_dir / "commentary.json", commentary.to_dict(), immutable=True)
        classification = "published" if status == "validated" else "quality-review" if status == "partial" else "model-rejected"
        receipt = {"artifact_version": "commentary-v1.2-corpus-result-v1", "reference": entry["reference"], "book": entry["book"], "chapter": int(entry["chapter"]), "status": status, "classification": classification, "error": None if validation.valid else "; ".join(validation.errors), "commentary_path": f"chapters/{_slug(entry['book'], int(entry['chapter']))}/commentary.json" if commentary is not None else None, "raw_response_sha256": sha256_bytes(raw), "raw_response_path": raw_path.relative_to(self.repo_root).as_posix(), "binding_metadata": binding_metadata, "normalization_metadata": conformance_metadata, "audits": audits}
        if classification == "model-rejected":
            receipt["release_state"] = "MODEL_OUTPUT_REJECTED"
            receipt["reason"] = "renderer output failed validation"
        if classification == "model-rejected":
            receipt["model_output_diagnostic"] = {
                "artifact_version": "commentary-v1.2-model-output-diagnostic-v1",
                "reference": entry["reference"],
                "run_id": run_root.name,
                "validator": "validate_chapter_commentary",
                "validator_error": receipt["error"],
                "failure_codes": sorted({error.split(":", 1)[0] for error in validation.errors}),
                "offending_provenance_ref": None,
                "raw_response_sha256": receipt["raw_response_sha256"],
                "raw_response_path": receipt["raw_response_path"],
                "renderer_receipt": _load_json(chapter_root / "renderer-receipt.json"),
            }
        result_path = chapter_dir / "result.json"
        if result_path.is_file():
            existing = _load_json(result_path)
            if existing.get("raw_response_sha256") != receipt["raw_response_sha256"] or existing.get("reference") != receipt["reference"]:
                raise V12IntegrityError(f"conflicting existing result for {entry['reference']}")
            receipt = {**existing, "audits": audits}
            # The original result receipt is immutable.  Preserve it and
            # carry newly added deterministic audits in a sidecar.
            write_json(chapter_dir / "finalize-audit.json", audits, immutable=True)
        else:
            write_json(result_path, receipt, immutable=True)
        return receipt

    @staticmethod
    def _batch_classification(manifest: dict[str, Any], outcomes: list[dict[str, Any]]) -> str:
        batch_number = int(manifest.get("batch_number", 1))
        prefix = f"V1_2_CORPUS_BATCH_{batch_number:02d}"
        renderable_outcomes = [
            item for item in outcomes if not V12CorpusRunner._is_source_limited_receipt(item)
        ]
        if any(item.get("classification") == "model-rejected" for item in renderable_outcomes):
            return f"V1_2_BATCH{batch_number:02d}_FINALIZED_WITH_MODEL_REJECTIONS"
        if any(item.get("status") in {"failed", "needs_review", "partial", "stale"} for item in renderable_outcomes):
            return f"{prefix}_REVIEW_REQUIRED"
        has_quality_warnings = any(
            item.get("audits", {}).get("quality", {}).get("richness_status") != "RICH_ENOUGH"
            for item in renderable_outcomes
        )
        return f"{prefix}_VALIDATED_WITH_WARNINGS" if has_quality_warnings else f"{prefix}_VALIDATED"

    def finalize(self, *, run_id: str | None = None) -> dict[str, Any]:
        """Validate frozen session responses without invoking any model."""

        if run_id is not None:
            run_root, selected_manifest, _, _ = self._prepared_run(run_id)
            incomplete = (run_root / "manifest.json", selected_manifest)
        else:
            incomplete = self._incomplete_session()
        if incomplete is None:
            raise V12CorpusError("no incomplete prepared codex_session run found")
        manifest_path, manifest = incomplete
        run_root = manifest_path.parent
        state_path = run_root / "state.json"
        state = _load_json(state_path)
        if state.get("manifest_sha256") != sha256_bytes(manifest_path.read_bytes()):
            raise V12IntegrityError("prepared manifest identity changed")
        entries = manifest.get("chapters")
        if not isinstance(entries, list) or not entries or len(entries) > MAX_BATCH_SIZE:
            raise V12IntegrityError("prepared session manifest has invalid bounded chapter list")
        # Preflight all corpus/run identities before writing any terminal
        # result.  A model payload is allowed to fail later, but a missing or
        # tampered artifact must leave the whole finalization untouched.
        source_limited_outcomes: dict[str, dict[str, Any]] = {}
        missing = []
        for entry in entries:
            chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
            result_path = chapter_root / "result.json"
            if result_path.is_file():
                receipt = _load_json(result_path)
                if self._is_source_limited_receipt(receipt):
                    source_limited_outcomes[entry["reference"]] = receipt
                    continue
            raw_path = chapter_root / "raw-response.bin"
            if not raw_path.is_file():
                missing.append(entry["reference"])
        if missing:
            raise V12CorpusError("missing raw responses: " + ", ".join(missing))
        for entry in entries:
            if entry["reference"] in source_limited_outcomes:
                continue
            chapter_root = run_root / "chapters" / _slug(entry["book"], int(entry["chapter"]))
            if len(list(chapter_root.glob("raw-response*"))) > 1:
                raise V12IntegrityError(
                    f"duplicate/conflicting responses for {entry['reference']}"
                )
            self._existing_local_response(run_root, entry)
            self._prepared_for_finalize(entry, run_root)
        outcomes = [
            source_limited_outcomes[entry["reference"]]
            if entry["reference"] in source_limited_outcomes
            else self._finalize_one(run_root, entry)
            for entry in entries
        ]
        for outcome in outcomes:
            record = state["chapters"].get(outcome["reference"])
            if not isinstance(record, dict):
                raise V12IntegrityError(f"missing runner state for {outcome['reference']}")
            record["status"] = outcome["status"]
            record["result_path"] = f"chapters/{_slug(outcome['book'], int(outcome['chapter']))}/result.json"
        state["finalized"] = True
        classification = self._batch_classification(manifest, outcomes)
        state["classification"] = classification
        write_json(state_path, state)
        report = {
            "status": "FINALIZED",
            "classification": classification,
            "run_id": manifest["run_id"],
            "chapters": outcomes,
            "counts": {
                status: sum(item["status"] == status for item in outcomes)
                for status in sorted(TERMINAL_RESULT_STATES)
            },
            "classification_counts": {
                classification: sum(
                    item.get("classification") == classification for item in outcomes
                )
                for classification in sorted(
                    {str(item.get("classification")) for item in outcomes}
                )
            },
            "source_limited": sum(
                self._is_source_limited_receipt(item) for item in outcomes
            ),
        }
        report_path = run_root / "finalize.json"
        if report_path.is_file() and _load_json(report_path) != report:
            version = 2
            while (run_root / f"finalize-v{version}.json").is_file() and _load_json(run_root / f"finalize-v{version}.json") != report:
                version += 1
            report_path = run_root / f"finalize-v{version}.json"
        write_json(report_path, report, immutable=True)
        return report

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
        if self.generation_metadata:
            manifest["generation"] = {
                "pipeline": self.generation_metadata.get("pipeline", V12_PIPELINE_VERSION),
                "model": self.generation_metadata.get("model"),
                "effort": self.generation_metadata.get("effort"),
                "prose_model": self.generation_metadata.get("prose_model"),
                "prose_effort": self.generation_metadata.get("prose_effort"),
                "config_path": self.generation_metadata.get("config_path"),
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
        raw_response = getattr(result, "raw_response", None)
        if raw_response is not None:
            raw_path = chapter_root / "raw-response.bin"
            from framework.commentary.production.models import write_immutable
            write_immutable(raw_path, raw_response)
            receipt["raw_response_path"] = raw_path.relative_to(self.repo_root).as_posix()
        if self.generation_metadata:
            receipt["generation"] = {
                "pipeline": self.generation_metadata.get("pipeline", V12_PIPELINE_VERSION),
                "model": self.generation_metadata.get("model"),
                "effort": self.generation_metadata.get("effort"),
                "prose_model": self.generation_metadata.get("prose_model"),
                "prose_effort": self.generation_metadata.get("prose_effort"),
            }
        result_path = chapter_root / "result.json"
        write_json(result_path, receipt, immutable=True)
        return {"reference": reference, "status": result.status, "result_path": result_path.relative_to(self.repo_root).as_posix()}


__all__ = [
    "ChapterRenderability",
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE",
    "assess_chapter_renderability",
    "ExistingV12ChapterPipeline",
    "V12AuthorizationError",
    "V12CorpusError",
    "V12CorpusRunner",
    "V12IntegrityError",
]
