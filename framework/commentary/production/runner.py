"""Sequential, restartable production execution around frozen BHF contracts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from bhf_agent import bible
from bhf_agent.chapter_commentary.dense_reader import (
    _activation_decision,
    build_reader_artifact,
    save_reader_artifact,
    validate_reader_artifact,
)
from bhf_agent.chapter_commentary.generator import CommentaryGenerator
from bhf_agent.chapter_commentary.models import GeneratedMetadata
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import assess_gate_v2, score_synthesis_richness
from bhf_agent.config import AgentConfig

from .inputs import prepare_chapter
from .ledger import rebuild_ledger
from .manifests import batch_manifest, load_manifest, save_batch_manifests
from .models import (
    ACCEPTED,
    BLOCKED,
    COMPLETE,
    DEFAULT_CANARY_LIMIT,
    DEFAULT_SYSTEMIC_PROVIDER_FAILURE_THRESHOLD,
    DENSE_READER_COMPLETE,
    DENSE_READER_PENDING,
    GATE_PASS,
    GATE_QUALITY_FAIL,
    GATE_WARNING,
    GENERATING,
    InputIdentity,
    ManifestError,
    PENDING,
    QUARANTINED,
    RAW_CAPTURED,
    REJECTED,
    STALE_INPUT,
    SystemicBatchFailure,
    VALIDATING,
    ArtifactCollisionError,
    ProductionError,
    PreparedChapter,
    read_json,
    production_root,
    sha256_bytes,
    transition,
    write_json,
    write_immutable,
    slug,
)
from .recovery import reconcile_batch


class ProviderFailure(RuntimeError):
    """A provider/API failure, kept separate from model-content validation."""

    def __init__(self, message: str, code: str = "PROVIDER_FAILURE"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RawResponse:
    text: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class Renderer(Protocol):
    def render(self, chapter: dict[str, Any], prepared: PreparedChapter) -> RawResponse | str: ...


class DefaultRenderer:
    """Adapter to the mature CommentaryGenerator call path, without its storage."""

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.generator = CommentaryGenerator(self.config)

    def render(self, chapter: dict[str, Any], prepared: PreparedChapter) -> RawResponse:
        try:
            return RawResponse(text=self.generator._call_model(prepared.packet["user_prompt"]))
        except Exception as exc:
            raise ProviderFailure(str(exc), "PROVIDER_FAILURE") from exc


def _relative(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _parse_response(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    candidate = text.strip()
    if "```json" in candidate:
        start = candidate.find("```json") + len("```json")
        end = candidate.find("```", start)
        if end > start:
            candidate = candidate[start:end]
    try:
        value = json.loads(candidate.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _codes(messages: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    for message in messages:
        code = str(message).split(":", 1)[0].strip()
        if re.fullmatch(r"[A-Z][A-Z0-9_]+", code):
            result.append(code)
    return sorted(set(result))


class ProductionRunner:
    def __init__(
        self,
        repo_root: Path,
        *,
        renderer: Renderer | None = None,
        input_loader: Callable[[str, int], PreparedChapter] = prepare_chapter,
        config: AgentConfig | None = None,
        systemic_provider_failure_threshold: int = DEFAULT_SYSTEMIC_PROVIDER_FAILURE_THRESHOLD,
    ):
        self.repo_root = Path(repo_root)
        self.config = config or AgentConfig()
        self.renderer = renderer or DefaultRenderer(self.config)
        self.input_loader = input_loader
        self.systemic_provider_failure_threshold = systemic_provider_failure_threshold

    def run_manifest(
        self,
        manifest_path: Path,
        *,
        authorized_run: bool = False,
        enable_reader: bool | None = None,
        new_attempt: bool = False,
    ) -> dict[str, Any]:
        manifest = load_manifest(Path(manifest_path))
        if not authorized_run:
            raise ManifestError("production execution requires explicit --authorized-run")
        if new_attempt:
            raise ProductionError("content retries are designed but disabled in production v1")
        if len(manifest.get("chapters", [])) > DEFAULT_CANARY_LIMIT and not manifest.get("full_corpus_authorized", False):
            raise ManifestError(f"manifest has more than {DEFAULT_CANARY_LIMIT} chapters; full-corpus authorization is required")
        authorization = {
            "artifact_version": "commentary-production-authorization-v1",
            "status": "AUTHORIZED",
            "run_id": manifest["run_id"],
            "manifest_identity": manifest["manifest_identity"],
            "chapter_count": len(manifest["chapters"]),
            "explicit_flag": "--authorized-run",
        }
        run_manifest_path = production_root(self.repo_root) / "runs" / manifest["run_id"] / "manifest.json"
        write_json(run_manifest_path, manifest, immutable=True)
        auth_path = production_root(self.repo_root) / "runs" / manifest["run_id"] / "authorization.json"
        write_json(auth_path, authorization, immutable=True)
        save_batch_manifests(manifest, self.repo_root)
        results: list[dict[str, Any]] = []
        provider_failures = 0
        for batch in manifest["batches"]:
            try:
                result = self._run_batch(manifest, batch["batch_id"], enable_reader=enable_reader)
                results.append(result)
                provider_failures += int(result.get("provider_failures", 0))
            except SystemicBatchFailure as exc:
                results.append({"batch_id": batch["batch_id"], "status": "STOPPED_SYSTEMIC", "error": str(exc)})
                break
            if provider_failures >= self.systemic_provider_failure_threshold:
                break
        ledger = rebuild_ledger(self.repo_root)
        return {"run_id": manifest["run_id"], "batches": results, "ledger_counts": ledger["counts"]}

    def _state_path(self, manifest: dict[str, Any], batch_id: str) -> Path:
        return production_root(self.repo_root) / "runs" / manifest["run_id"] / "batches" / batch_id / "state.json"

    def _load_state(self, manifest: dict[str, Any], batch_id: str) -> dict[str, Any]:
        path = self._state_path(manifest, batch_id)
        if path.exists():
            state = read_json(path)
            if state.get("manifest_identity") != manifest["manifest_identity"]:
                raise ManifestError(f"batch state belongs to another manifest: {path}")
            state["state_path"] = str(path)
            return state
        batch = batch_manifest(manifest, batch_id)
        state = {
            "artifact_version": "commentary-production-batch-state-v1",
            "production_version": manifest["production_version"],
            "run_id": manifest["run_id"],
            "batch_id": batch_id,
            "manifest_identity": manifest["manifest_identity"],
            "status": "READY",
            "provider_failures": 0,
            "chapters": {row["reference"]: {"state": "READY", "attempt": 0, "reader_status": "NOT_ELIGIBLE"} for row in batch["chapters"]},
            "state_path": str(path),
        }
        write_json(path, state)
        return state

    def _run_batch(self, manifest: dict[str, Any], batch_id: str, *, enable_reader: bool | None) -> dict[str, Any]:
        batch = batch_manifest(manifest, batch_id)
        state = self._load_state(manifest, batch_id)
        state = reconcile_batch(self.repo_root, batch, state)
        provider_failures = int(state.get("provider_failures", 0))
        outcomes: list[dict[str, Any]] = []
        for chapter in batch["chapters"]:
            reference = chapter["reference"]
            record = state["chapters"][reference]
            if record.get("state") in {COMPLETE, GATE_QUALITY_FAIL, QUARANTINED, STALE_INPUT, BLOCKED}:
                outcomes.append({"reference": reference, "state": record["state"], "skipped": True})
                continue
            prepared = self.input_loader(chapter["book"], int(chapter["chapter"]))
            if prepared.row.get("input_identity") != chapter.get("input_identity"):
                self._mark_stale(manifest, batch, chapter, record, prepared)
                outcomes.append({"reference": reference, "state": STALE_INPUT})
                continue
            prepared = PreparedChapter(row={**prepared.row, "canonical_ordinal": chapter["canonical_ordinal"]}, bundle=prepared.bundle, synthesis=prepared.synthesis, packet={**prepared.packet, "run_id": manifest["run_id"], "batch_id": batch_id})
            packet_path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["packet"]
            write_json(packet_path, prepared.packet, immutable=True)
            raw_path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["raw"]
            if raw_path.is_file() and record.get("state") == RAW_CAPTURED:
                outcome = self._import_and_evaluate(manifest, batch, chapter, prepared, record, state, enable_reader)
                outcomes.append(outcome)
                continue
            self._set_record(state, reference, GENERATING)
            attempt = int(record.get("attempt", 0)) + 1
            record["attempt"] = attempt
            self._save_state(state)
            try:
                rendered = self.renderer.render(chapter, prepared)
            except ProviderFailure as exc:
                provider_failures += 1
                self._capture_provider_failure(manifest, batch, chapter, record, raw_path, attempt, exc)
                outcomes.append({"reference": reference, "state": QUARANTINED, "failure_kind": "PROVIDER_FAILURE"})
                if provider_failures >= self.systemic_provider_failure_threshold:
                    state["provider_failures"] = provider_failures
                    state["status"] = "STOPPED_SYSTEMIC"
                    self._save_state(state)
                    raise SystemicBatchFailure(f"provider failure threshold reached in {batch_id}")
                continue
            except Exception as exc:
                raise SystemicBatchFailure(f"unexpected renderer harness failure for {reference}: {exc}") from exc
            response = rendered if isinstance(rendered, RawResponse) else RawResponse(text=str(rendered))
            if response.failure_code:
                exc = ProviderFailure(response.failure_message or "provider failure", response.failure_code)
                provider_failures += 1
                self._capture_provider_failure(manifest, batch, chapter, record, raw_path, attempt, exc)
                outcomes.append({"reference": reference, "state": QUARANTINED, "failure_kind": "PROVIDER_FAILURE"})
                if provider_failures >= self.systemic_provider_failure_threshold:
                    state["provider_failures"] = provider_failures
                    state["status"] = "STOPPED_SYSTEMIC"
                    self._save_state(state)
                    raise SystemicBatchFailure(f"provider failure threshold reached in {batch_id}")
                continue
            raw_bytes = (response.text or "").encode("utf-8")
            record["raw_sha256"] = write_immutable(raw_path, raw_bytes)
            record["raw_path"] = _relative(self.repo_root, raw_path)
            self._set_record(state, reference, RAW_CAPTURED)
            self._save_state(state)
            outcome = self._import_and_evaluate(manifest, batch, chapter, prepared, record, state, enable_reader)
            outcomes.append(outcome)
        state["provider_failures"] = provider_failures
        state["status"] = "COMPLETE" if all(value.get("state") in {COMPLETE, GATE_QUALITY_FAIL, QUARANTINED, STALE_INPUT, BLOCKED} for value in state["chapters"].values()) else "IN_PROGRESS"
        self._save_state(state)
        return {"batch_id": batch_id, "status": state["status"], "provider_failures": provider_failures, "chapters": outcomes}

    def _import_and_evaluate(self, manifest: dict[str, Any], batch: dict[str, Any], chapter: dict[str, Any], prepared: PreparedChapter, record: dict[str, Any], state: dict[str, Any], enable_reader: bool | None) -> dict[str, Any]:
        reference = chapter["reference"]
        raw_path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["raw"]
        self._set_record(state, reference, VALIDATING)
        self._save_state(state)
        raw_document = None
        try:
            raw_document = read_json(raw_path)
        except ProductionError:
            raw_document = None
        if isinstance(raw_document, dict) and raw_document.get("raw_kind") == "PROVIDER_FAILURE":
            code = str(raw_document.get("failure_code") or "PROVIDER_FAILURE")
            message = str(raw_document.get("failure_message") or "provider failure")
            self._quarantine(manifest, batch, chapter, record, [code], [message], generation_failure=True, gate_failure=False)
            self._set_record(state, reference, QUARANTINED)
            self._save_state(state)
            return {"reference": reference, "state": QUARANTINED, "failure_kind": "PROVIDER_FAILURE", "rejection_codes": [code]}
        payload = _parse_response(raw_path.read_text(encoding="utf-8"))
        if payload is None:
            messages = ["CONTENT_MALFORMED_JSON: model response was not a JSON object"]
            self._reject(manifest, batch, chapter, record, state, messages, generation_failure=False)
            return {"reference": reference, "state": QUARANTINED, "failure_kind": "CONTENT_FAILURE", "rejection_codes": ["CONTENT_MALFORMED_JSON"]}
        payload = dict(payload)
        payload["generated_metadata"] = GeneratedMetadata(
            evidence_hash=prepared.bundle.evidence_hash,
            evidence_bundle_version=prepared.bundle.version,
            commentary_schema_version=chapter["input_identity"]["commentary_schema_version"],
            commentary_prompt_version=chapter["input_identity"]["prompt_version"],
            model=self.config.model or "unknown",
            generated_timestamp=None,
            synthesis_hash=prepared.synthesis.synthesis_hash,
            synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
            synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        ).to_dict()
        payload["evidence_availability"] = prepared.synthesis.evidence_availability
        payload["status"] = "pending"
        from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
        validation = validate_chapter_commentary(payload, prepared.bundle, expected_evidence_hash=prepared.bundle.evidence_hash, expected_prompt_version=chapter["input_identity"]["prompt_version"], expected_reference=reference, expected_book=chapter["book"], expected_chapter=int(chapter["chapter"]), synthesis=prepared.synthesis, expected_synthesis_hash=prepared.synthesis.synthesis_hash)
        if not validation.valid:
            messages = list(validation.errors)
            self._reject(manifest, batch, chapter, record, state, messages, generation_failure=False)
            return {"reference": reference, "state": QUARANTINED, "failure_kind": "CONTENT_FAILURE", "rejection_codes": _codes(messages)}
        accepted_payload = validation.commentary.to_dict() if validation.commentary else payload
        accepted_payload["status"] = "validated"
        accepted_path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["accepted"]
        record["accepted_path"] = _relative(self.repo_root, accepted_path)
        write_json(accepted_path, accepted_payload, immutable=True)
        self._set_record(state, reference, ACCEPTED)
        self._save_state(state)
        blocks = [block for section in validation.commentary.sections for block in section.blocks] if validation.commentary else []
        audit = audit_chapter(chapter["book"], int(chapter["chapter"]), validation.commentary, prepared.bundle)
        score = score_synthesis_richness(prepared.synthesis.synthesis_units, evidence_items=prepared.bundle.evidence_items, consumed_synthesis_ids=[sid for block in blocks for sid in block.synthesis_ids], blocks=blocks, passage_ref=reference)
        assessment = assess_gate_v2(score=score, evidence_availability=prepared.synthesis.evidence_availability, baseline_richness="SYNTHESIS_GAP" if prepared.synthesis.evidence_availability == "AVAILABLE" else "EVIDENCE_GAP", after_richness=audit["richness_status"], safety_checks={name: True for name in ("validation_clean", "provenance_complete", "hashes_valid", "chapter_boundaries_valid", "confidence_valid", "dispute_state_preserved", "unsupported_significance_absent")}, evidence_use_delta=audit["unique_evidence_ids_consumed"], section_delta=audit["section_count"], commentary_word_count=audit["commentary_prose_word_count"], unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"])
        gate_value = {"artifact_version": "commentary-production-gate-v1", "reference": reference, "input_identity": chapter["input_identity"], "audit": audit, "score": score.to_dict(), "assessment": assessment.to_dict()}
        gate_path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["gate"]
        write_json(gate_path, gate_value, immutable=True)
        record["gate_path"] = _relative(self.repo_root, gate_path)
        record["gate_status"] = assessment.outcome
        if assessment.outcome == "QUALITY_FAIL":
            self._set_record(state, reference, GATE_QUALITY_FAIL)
            self._quarantine(manifest, batch, chapter, record, ["GATE_QUALITY_FAIL"], ["Gate v2.1 quality failure"], generation_failure=False, gate_failure=True)
            self._save_state(state)
            return {"reference": reference, "state": GATE_QUALITY_FAIL, "gate_status": assessment.outcome}
        if assessment.outcome == "SAFETY_FAIL":
            self._quarantine(manifest, batch, chapter, record, ["GATE_SAFETY_FAIL"], assessment.reasons, generation_failure=False, gate_failure=True)
            self._set_record(state, reference, QUARANTINED)
            self._save_state(state)
            return {"reference": reference, "state": QUARANTINED, "gate_status": assessment.outcome}
        gate_state = GATE_WARNING if assessment.outcome == "PASS_WITH_WARNING" else GATE_PASS
        self._set_record(state, reference, gate_state)
        reader_decision = _activation_decision(source_words=audit["commentary_prose_word_count"], source_block_count=audit["commentary_block_count"], source_dump_severity=assessment.dump_severity, source_quality_metrics={"weighted_coverage": score.weighted_idea_coverage, "synthesis_utilization": audit["evidence_consumption_ratio"]}, force_consolidation=False)
        record["reader_activation"] = reader_decision
        if not reader_decision["active"]:
            record["reader_status"] = "NOT_ELIGIBLE"
            self._set_record(state, reference, COMPLETE)
            self._save_state(state)
            return {"reference": reference, "state": COMPLETE, "gate_status": assessment.outcome, "reader_status": "NOT_ELIGIBLE"}
        record["reader_status"] = "ELIGIBLE"
        if enable_reader is not True:
            self._set_record(state, reference, COMPLETE)
            self._save_state(state)
            return {"reference": reference, "state": COMPLETE, "gate_status": assessment.outcome, "reader_status": "ELIGIBLE"}
        self._set_record(state, reference, DENSE_READER_PENDING)
        self._save_state(state)
        try:
            accepted_root = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1"
            artifact = build_reader_artifact(accepted_payload, source_path=accepted_path, source_root=accepted_root, synthesis=prepared.synthesis, evidence_items=prepared.bundle.evidence_items, source_word_count=audit["commentary_prose_word_count"], source_dump_severity=assessment.dump_severity, source_quality_metrics={"weighted_coverage": score.weighted_idea_coverage, "synthesis_utilization": audit["evidence_consumption_ratio"]})
            errors = validate_reader_artifact(artifact, source_payload=accepted_payload, source_path=accepted_path, source_root=accepted_root, synthesis=prepared.synthesis, evidence_items=prepared.bundle.evidence_items)
            if errors:
                raise ProductionError("; ".join(errors))
            reader_path = accepted_root / chapter["expected_artifacts"]["reader"]
            save_reader_artifact(artifact, reader_path)
            record["reader_status"] = "GENERATED"
            record["reader_path"] = _relative(self.repo_root, reader_path)
            self._set_record(state, reference, DENSE_READER_COMPLETE)
        except Exception as exc:
            record["reader_status"] = "FAILED"
            reader_path = accepted_root / chapter["expected_artifacts"]["reader"]
            write_json(reader_path, {"artifact_version": "commentary-production-reader-receipt-v1", "reference": reference, "status": "FAILED", "error": str(exc), "commentary_remains_valid": True}, immutable=True)
        self._set_record(state, reference, COMPLETE)
        self._save_state(state)
        return {"reference": reference, "state": COMPLETE, "gate_status": assessment.outcome, "reader_status": record["reader_status"]}

    def _reject(self, manifest: dict[str, Any], batch: dict[str, Any], chapter: dict[str, Any], record: dict[str, Any], state: dict[str, Any], messages: list[str], *, generation_failure: bool) -> None:
        self._set_record(state, chapter["reference"], REJECTED)
        rejected_path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["rejected"]
        write_json(rejected_path, {"artifact_version": "commentary-production-rejected-v1", "reference": chapter["reference"], "attempt": record["attempt"], "raw_path": record.get("raw_path"), "raw_sha256": record.get("raw_sha256"), "rejection_codes": _codes(messages), "validator_messages": messages, "input_identity": chapter["input_identity"], "production_run_id": manifest["run_id"], "batch_id": batch["batch_id"], "generation_failure": generation_failure}, immutable=True)
        self._quarantine(manifest, batch, chapter, record, _codes(messages), messages, generation_failure=generation_failure, gate_failure=False)
        self._set_record(state, chapter["reference"], QUARANTINED)
        self._save_state(state)

    def _capture_provider_failure(self, manifest: dict[str, Any], batch: dict[str, Any], chapter: dict[str, Any], record: dict[str, Any], raw_path: Path, attempt: int, exc: ProviderFailure) -> None:
        envelope = {"artifact_version": "commentary-production-provider-failure-v1", "raw_kind": "PROVIDER_FAILURE", "reference": chapter["reference"], "attempt": attempt, "failure_code": exc.code, "failure_message": str(exc), "input_identity": chapter["input_identity"], "production_run_id": manifest["run_id"], "batch_id": batch["batch_id"]}
        record["raw_sha256"] = write_json(raw_path, envelope, immutable=True)
        record["raw_path"] = _relative(self.repo_root, raw_path)
        record["failure_kind"] = "PROVIDER_FAILURE"
        record["failure_code"] = exc.code
        self._quarantine(manifest, batch, chapter, record, [exc.code], [str(exc)], generation_failure=True, gate_failure=False)
        record["state"] = QUARANTINED

    def _quarantine(self, manifest: dict[str, Any], batch: dict[str, Any], chapter: dict[str, Any], record: dict[str, Any], codes: list[str], messages: list[str], *, generation_failure: bool, gate_failure: bool) -> None:
        path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / chapter["expected_artifacts"]["quarantine"]
        write_json(path, {"artifact_version": "commentary-production-quarantine-v1", "reference": chapter["reference"], "attempt": record.get("attempt"), "raw_path": record.get("raw_path"), "raw_sha256": record.get("raw_sha256"), "rejection_codes": sorted(set(codes)), "validator_messages": messages, "packet_identity": chapter["input_identity"]["packet_id"], "input_identity": chapter["input_identity"], "production_run_id": manifest["run_id"], "batch_id": batch["batch_id"], "generation_failure": generation_failure, "validation_failure": not generation_failure and not gate_failure, "gate_failure": gate_failure}, immutable=True)
        record["quarantine_path"] = _relative(self.repo_root, path)
        record["rejection_codes"] = sorted(set(codes))

    def _mark_stale(self, manifest: dict[str, Any], batch: dict[str, Any], chapter: dict[str, Any], record: dict[str, Any], prepared: PreparedChapter) -> None:
        record["state"] = STALE_INPUT
        record["drift"] = {"locked": chapter["input_identity"], "current": prepared.row.get("input_identity")}
        path = self.repo_root / ".bhf-data" / "bhf-commentary-production" / "v1" / "runs" / manifest["run_id"] / "batches" / batch["batch_id"] / "quarantine" / "attempt-001" / f"{slug(chapter['book'], chapter['chapter'])}.json"
        write_json(path, {"artifact_version": "commentary-production-input-drift-v1", "reference": chapter["reference"], "status": STALE_INPUT, "locked_input_identity": chapter["input_identity"], "current_input_identity": prepared.row.get("input_identity"), "production_run_id": manifest["run_id"], "batch_id": batch["batch_id"]}, immutable=True)
        record["quarantine_path"] = _relative(self.repo_root, path)

    def _set_record(self, state: dict[str, Any], reference: str, target: str) -> None:
        record = state["chapters"][reference]
        record["state"] = transition(str(record.get("state", PENDING)), target)

    def _save_state(self, state: dict[str, Any]) -> None:
        write_json(Path(state["state_path"]), state)
