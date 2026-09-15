"""Provider-free preparation, import, and recovery for Commentary production.

The external renderer never receives a production authority.  It receives the
immutable packet selected by this module; ProductionRunner remains responsible
for importing bytes and executing the normal validator, Gate, reader, and
ledger path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifests import batch_manifest, load_manifest, save_batch_manifests
from .inputs import prepare_chapter
from .models import (
    BLOCKED,
    COMPLETE,
    DEFAULT_CANARY_LIMIT,
    GATE_QUALITY_FAIL,
    ManifestError,
    ProductionError,
    QUARANTINED,
    RAW_CAPTURED,
    READY,
    STALE_INPUT,
    TERMINAL_STATES,
    VALIDATING,
    ArtifactCollisionError,
    PreparedChapter,
    read_json,
    production_root,
    sha256_bytes,
    sha256_json,
    slug,
    write_json,
    write_immutable,
)
from .recovery import reconcile_batch
from .ledger import rebuild_ledger
from .runner import ProductionRunner, _relative
from .runner import _parse_response
from .runtime import (
    EXTERNAL_HANDOFF_MODE,
    handoff_generation_receipt,
    validate_handoff_renderer,
    validate_manifest_for_handoff,
)


HANDOFF_MANIFEST_VERSION = "commentary-production-handoff-manifest-v1"


def _identity(value: dict[str, Any]) -> str:
    return sha256_json({key: item for key, item in value.items() if key != "handoff_identity"})


def _rooted(repo_root: Path, relative: str) -> Path:
    return production_root(repo_root) / relative


def _packet_for(prepared: PreparedChapter, *, run_id: str, batch_id: str) -> dict[str, Any]:
    return {
        **prepared.packet,
        "run_id": run_id,
        "batch_id": batch_id,
    }


class HandoffRunner(ProductionRunner):
    """ProductionRunner variant that has no renderer and no API config."""

    def __init__(self, repo_root: Path, *, renderer_identity: str, input_loader=None):
        super().__init__(
            repo_root,
            input_loader=input_loader or prepare_chapter,
            config=None,
            generation_mode=EXTERNAL_HANDOFF_MODE,
            renderer_identity=validate_handoff_renderer(renderer_identity),
        )

    def _handoff_paths(self, run_id: str) -> tuple[Path, Path]:
        run_root = production_root(self.repo_root) / "runs" / run_id
        return run_root / "manifest.json", run_root / "handoff" / "manifest.json"

    def _load_handoff(self, run_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        run_manifest_path, handoff_path = self._handoff_paths(run_id)
        manifest = load_manifest(run_manifest_path)
        handoff = read_json(handoff_path)
        if not isinstance(handoff, dict) or handoff.get("handoff_identity") != _identity(handoff):
            raise ManifestError(f"handoff manifest identity mismatch: {handoff_path}")
        if handoff.get("run_id") != run_id or handoff.get("manifest_identity") != manifest.get("manifest_identity"):
            raise ManifestError("handoff manifest is not tied to the requested production run")
        if handoff.get("generation_mode") != EXTERNAL_HANDOFF_MODE:
            raise ManifestError("production run is not an external handoff run")
        if handoff.get("renderer_identity") != self.renderer_identity:
            raise ProductionError("RENDERER_IDENTITY_MISMATCH: handoff renderer differs from the run")
        auth_path = production_root(self.repo_root) / "runs" / run_id / "authorization.json"
        authorization = read_json(auth_path)
        if authorization.get("generation_mode") != EXTERNAL_HANDOFF_MODE:
            raise ProductionError("GENERATION_MODE_MISMATCH: run was authorized for direct provider mode")
        if authorization.get("renderer_identity") != self.renderer_identity or authorization.get("generation_identity") != handoff.get("generation_identity"):
            raise ProductionError("RENDERER_IDENTITY_MISMATCH: authorization differs from handoff")
        return manifest, handoff, authorization

    def _prepare_locked(self, manifest: dict[str, Any], chapter: dict[str, Any]) -> PreparedChapter:
        prepared = self.input_loader(chapter["book"], int(chapter["chapter"]))
        if prepared.row.get("input_identity") != chapter.get("input_identity"):
            raise ManifestError(f"PRODUCTION_PREFLIGHT_FAILED: input identity mismatch for {chapter['reference']}")
        packet = _packet_for(prepared, run_id=manifest["run_id"], batch_id=chapter["batch_id"])
        packet_path = _rooted(self.repo_root, chapter["expected_artifacts"]["packet"])
        write_json(packet_path, packet, immutable=True)
        stored = read_json(packet_path)
        if stored.get("packet_id") != chapter.get("packet_id") or stored.get("packet_hash") != chapter.get("packet_hash"):
            raise ManifestError(f"packet identity mismatch for {chapter['reference']}")
        return PreparedChapter(
            row={**prepared.row, "canonical_ordinal": chapter["canonical_ordinal"]},
            bundle=prepared.bundle,
            synthesis=prepared.synthesis,
            packet=packet,
        )

    def handoff_preflight(self, manifest_path: Path, *, enable_reader: bool = False, authorized_full_corpus: bool = False) -> dict[str, Any]:
        manifest = load_manifest(Path(manifest_path))
        errors = validate_manifest_for_handoff(manifest, canary_limit=DEFAULT_CANARY_LIMIT, allow_full_corpus=authorized_full_corpus)
        if len(manifest.get("chapters", [])) > DEFAULT_CANARY_LIMIT and not (authorized_full_corpus and manifest.get("full_corpus_authorized", False)):
            errors.append("more than 50 chapters requires --authorized-full-corpus and manifest full_corpus_authorized")
        if errors:
            raise ManifestError("PRODUCTION_PREFLIGHT_FAILED: " + "; ".join(errors))
        # Preparation, not a renderer, is the frozen-input check.  It may read
        # CKL/evidence and compile synthesis, but it cannot make a provider call.
        for chapter in manifest["chapters"]:
            prepared = self.input_loader(chapter["book"], int(chapter["chapter"]))
            if prepared.row.get("input_identity") != chapter.get("input_identity"):
                raise ManifestError(f"PRODUCTION_PREFLIGHT_FAILED: input identity mismatch for {chapter['reference']}")
        receipt = handoff_generation_receipt(
            self.renderer_identity,
            reader_enabled=enable_reader,
            contract_versions=manifest["contract_versions"],
        )
        return {
            "status": "READY",
            "generation_mode": EXTERNAL_HANDOFF_MODE,
            "renderer_identity": self.renderer_identity,
            "generation_identity": receipt["generation_identity"],
            "manifest_identity": manifest["manifest_identity"],
            "run_id": manifest["run_id"],
            "chapter_count": len(manifest["chapters"]),
            "reader_enabled": bool(enable_reader),
            "provider_called": False,
            "provider_calls": 0,
        }

    def prepare(self, manifest_path: Path, *, authorized_run: bool, enable_reader: bool = False, authorized_full_corpus: bool = False) -> dict[str, Any]:
        manifest = load_manifest(Path(manifest_path))
        errors = validate_manifest_for_handoff(manifest, canary_limit=DEFAULT_CANARY_LIMIT, allow_full_corpus=authorized_full_corpus)
        if errors:
            raise ManifestError("PRODUCTION_PREFLIGHT_FAILED: " + "; ".join(errors))
        if not authorized_run:
            raise ManifestError("handoff preparation requires explicit --authorized-run")
        if len(manifest.get("chapters", [])) > DEFAULT_CANARY_LIMIT and not (authorized_full_corpus and manifest.get("full_corpus_authorized", False)):
            raise ManifestError(f"manifest has more than {DEFAULT_CANARY_LIMIT} chapters; full-corpus authorization is required")

        # Freeze-check every selected chapter before authorizing or creating
        # any run artifact.  This is still local evidence/synthesis work, not
        # a model invocation.
        for chapter in manifest["chapters"]:
            prepared = self.input_loader(chapter["book"], int(chapter["chapter"]))
            if prepared.row.get("input_identity") != chapter.get("input_identity"):
                raise ManifestError(f"PRODUCTION_PREFLIGHT_FAILED: input identity mismatch for {chapter['reference']}")

        receipt = handoff_generation_receipt(
            self.renderer_identity,
            reader_enabled=enable_reader,
            contract_versions=manifest["contract_versions"],
        )
        run_root = production_root(self.repo_root) / "runs" / manifest["run_id"]
        auth_path = run_root / "authorization.json"
        authorization = {
            "artifact_version": "commentary-production-authorization-v1",
            "status": "AUTHORIZED",
            "run_id": manifest["run_id"],
            "manifest_identity": manifest["manifest_identity"],
            "generation_mode": EXTERNAL_HANDOFF_MODE,
            "renderer_identity": self.renderer_identity,
            "generation_identity": receipt["generation_identity"],
            "generation": receipt["parameters"],
            "chapter_count": len(manifest["chapters"]),
            "provider_calls": 0,
            "explicit_flag": "--authorized-run",
        }
        if auth_path.exists():
            existing = read_json(auth_path)
            if any(existing.get(key) != authorization.get(key) for key in ("manifest_identity", "generation_mode", "renderer_identity", "generation_identity")) or existing.get("generation", {}).get("reader_enabled") != bool(enable_reader):
                raise ProductionError("HANDOFF_IDENTITY_MISMATCH: existing run authorization differs")
        else:
            write_json(auth_path, authorization, immutable=True)
        write_json(run_root / "manifest.json", manifest, immutable=True)
        save_batch_manifests(manifest, self.repo_root)

        items: list[dict[str, Any]] = []
        for chapter in manifest["chapters"]:
            prepared = self._prepare_locked(manifest, chapter)
            state = self._load_state(manifest, chapter["batch_id"])
            state["generation_mode"] = EXTERNAL_HANDOFF_MODE
            state["renderer_identity"] = self.renderer_identity
            state["generation_identity"] = receipt["generation_identity"]
            record = state["chapters"][chapter["reference"]]
            if self._is_true_data_gap(prepared) and record.get("state") not in TERMINAL_STATES:
                batch = batch_manifest(manifest, chapter["batch_id"])
                self._complete_application_fallback(
                    manifest, batch, chapter, prepared, record, state, enable_reader
                )
                record["handoff_status"] = "APPLICATION_FALLBACK_COMPLETE"
                self._save_state(state)
            if record.get("state") in TERMINAL_STATES:
                # A true source-empty DATA_GAP has no renderer work and no
                # raw response.  It is completed through the same validator
                # and Gate path as a rendered chapter, but never enters the
                # handoff queue.
                continue
            packet_path = _rooted(self.repo_root, chapter["expected_artifacts"]["packet"])
            packet = read_json(packet_path)
            prompt_identity = {
                "prompt_version": chapter["input_identity"]["prompt_version"],
                "system_prompt_sha256": sha256_bytes(str(packet["system_prompt"]).encode("utf-8")),
                "user_prompt_sha256": sha256_bytes(str(packet["user_prompt"]).encode("utf-8")),
            }
            item = {
                "run_id": manifest["run_id"],
                "batch_id": chapter["batch_id"],
                "reference": chapter["reference"],
                "packet_id": chapter["packet_id"],
                "packet_hash": chapter["packet_hash"],
                "packet_sha": chapter["packet_hash"],
                "packet_sha256": sha256_bytes(packet_path.read_bytes()),
                "packet_path": chapter["expected_artifacts"]["packet"],
                "prompt_version": chapter["input_identity"]["prompt_version"],
                "commentary_schema_version": chapter["input_identity"]["commentary_schema_version"],
                "evidence_hash": chapter["input_identity"]["evidence_hash"],
                "synthesis_hash": chapter["input_identity"]["synthesis_hash"],
                "prompt_identity": prompt_identity,
                "system_prompt_identity": prompt_identity["system_prompt_sha256"],
                "expected_raw_path": chapter["expected_artifacts"]["raw"],
                "renderer_identity": self.renderer_identity,
                "attempt": 1,
                "status": "READY",
            }
            items.append(item)
            if not record.get("raw_path"):
                record["handoff_status"] = "AWAITING_GENERATION"
            self._save_state(state)

        handoff = {
            "artifact_version": HANDOFF_MANIFEST_VERSION,
            "production_version": manifest["production_version"],
            "generation_mode": EXTERNAL_HANDOFF_MODE,
            "renderer_identity": self.renderer_identity,
            "generation_identity": receipt["generation_identity"],
            "run_id": manifest["run_id"],
            "manifest_identity": manifest["manifest_identity"],
            "batch_ids": [batch["batch_id"] for batch in manifest["batches"]],
            "contract_versions": manifest["contract_versions"],
            "prompt_version": manifest["contract_versions"]["commentary_prompt_version"],
            "schema_version": manifest["contract_versions"]["commentary_schema_version"],
            "reader_enabled": bool(enable_reader),
            "provider_calls": 0,
            "items": items,
        }
        handoff["handoff_identity"] = _identity(handoff)
        handoff_path = run_root / "handoff" / "manifest.json"
        write_json(handoff_path, handoff, immutable=True)
        return {
            "status": "HANDOFF_PREPARED",
            "generation_mode": EXTERNAL_HANDOFF_MODE,
            "renderer_identity": self.renderer_identity,
            "generation_identity": receipt["generation_identity"],
            "run_id": manifest["run_id"],
            "manifest_identity": manifest["manifest_identity"],
            "handoff_manifest_path": _relative(self.repo_root, handoff_path),
            "task_count": len(items),
            "provider_calls": 0,
            "tasks": items,
        }

    def _find_item(self, handoff: dict[str, Any], reference: str) -> dict[str, Any]:
        matches = [item for item in handoff.get("items", []) if item.get("reference") == reference]
        if len(matches) != 1:
            raise ManifestError(f"unknown or ambiguous handoff chapter: {reference}")
        return matches[0]

    def _verify_response_envelope(self, raw: bytes, item: dict[str, Any], *, batch_id: str | None) -> None:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return  # The immutable malformed raw is intentionally quarantined by validation.
        if not isinstance(value, dict) or "response_payload" not in value:
            return
        expected = {
            "run_id": item["run_id"],
            "batch_id": item["batch_id"],
            "reference": item["reference"],
            "packet_id": item["packet_id"],
            "attempt": item["attempt"],
        }
        for key, wanted in expected.items():
            if key in value and value[key] != wanted:
                raise ManifestError(f"HANDOFF_{key.upper()}_MISMATCH: response envelope is not for this task")
        if batch_id is not None and item["batch_id"] != batch_id:
            raise ManifestError("HANDOFF_BATCH_MISMATCH: chapter is not in the requested batch")
        if value.get("renderer_identity", value.get("renderer_label")) not in (None, self.renderer_identity):
            raise ProductionError("RENDERER_IDENTITY_MISMATCH: response envelope renderer differs from the run")
        if value.get("packet_hash") not in (None, item["packet_hash"]):
            raise ManifestError("HANDOFF_PACKET_HASH_MISMATCH: response envelope packet hash differs")
        if value.get("packet_sha256") not in (None, item["packet_sha256"]):
            raise ManifestError("HANDOFF_PACKET_SHA256_MISMATCH: response envelope packet bytes differ")
        if value.get("packet_sha") not in (None, item["packet_hash"], item["packet_sha256"]):
            raise ManifestError("HANDOFF_PACKET_SHA_MISMATCH: response envelope packet differs")
        for key in ("prompt_version", "evidence_hash", "synthesis_hash"):
            if value.get(key) not in (None, item[key]):
                raise ManifestError(f"HANDOFF_{key.upper()}_MISMATCH: response envelope input differs")
        if not isinstance(value.get("response_payload"), dict):
            raise ManifestError("HANDOFF_RESPONSE_PAYLOAD_INVALID: response_payload must be an object")

    def import_response(self, run_id: str, reference: str, response_path: Path, *, batch_id: str | None = None) -> dict[str, Any]:
        manifest, handoff, authorization = self._load_handoff(run_id)
        item = self._find_item(handoff, reference)
        if batch_id is not None and item["batch_id"] != batch_id:
            raise ManifestError("HANDOFF_BATCH_MISMATCH: chapter is not in the requested batch")
        batch = batch_manifest(manifest, item["batch_id"])
        chapter = next(row for row in batch["chapters"] if row["reference"] == reference)
        state = self._load_state(manifest, item["batch_id"])
        state = reconcile_batch(self.repo_root, batch, state)
        record = state["chapters"][reference]
        raw_path = _rooted(self.repo_root, item["expected_raw_path"])

        raw = Path(response_path).read_bytes()
        if record.get("state") in TERMINAL_STATES:
            if raw_path.exists() and raw_path.read_bytes() != raw:
                raise ArtifactCollisionError(f"HANDOFF_RAW_COLLISION: immutable raw artifact differs: {raw_path}")
            return {"status": "SKIPPED", "reference": reference, "state": record["state"], "reason": "terminal chapter"}
        self._verify_response_envelope(raw, item, batch_id=batch_id)
        if raw_path.exists() and raw_path.read_bytes() != raw:
            raise ArtifactCollisionError(f"HANDOFF_RAW_COLLISION: immutable raw artifact differs: {raw_path}")
        prepared = self._prepare_locked(manifest, chapter)
        if record.get("state") == READY:
            self._set_record(state, reference, "GENERATING")
        if int(record.get("attempt", 0)) == 0:
            record["attempt"] = item["attempt"]
        if int(record.get("attempt", 0)) != item["attempt"]:
            raise ProductionError("HANDOFF_ATTEMPT_MISMATCH: expected attempt differs from state")
        record["raw_sha256"] = write_immutable(raw_path, raw)
        record["raw_path"] = _relative(self.repo_root, raw_path)
        self._set_record(state, reference, RAW_CAPTURED)
        record["handoff_status"] = "IMPORTED"
        self._save_state(state)
        outcome = self._import_and_evaluate(manifest, batch, chapter, prepared, record, state, authorization.get("generation", {}).get("reader_enabled", False))
        self._finish_batch_state(state)
        ledger = rebuild_ledger(self.repo_root)
        return {"status": "IMPORTED", **outcome, "raw_sha256": record["raw_sha256"], "provider_calls": 0, "ledger_counts": ledger["counts"]}

    def reconcile_run(self, run_id: str) -> dict[str, Any]:
        manifest, handoff, authorization = self._load_handoff(run_id)
        outcomes: list[dict[str, Any]] = []
        for batch_info in manifest["batches"]:
            batch = batch_manifest(manifest, batch_info["batch_id"])
            state = self._load_state(manifest, batch_info["batch_id"])
            state = reconcile_batch(self.repo_root, batch, state)
            for chapter in batch["chapters"]:
                reference = chapter["reference"]
                record = state["chapters"][reference]
                prepared = self._prepare_locked(manifest, chapter)
                if self._is_true_data_gap(prepared):
                    if record.get("state") not in TERMINAL_STATES:
                        outcome = self._complete_application_fallback(
                            manifest, batch, chapter, prepared, record, state,
                            authorization.get("generation", {}).get("reader_enabled", False),
                        )
                        record["handoff_status"] = "APPLICATION_FALLBACK_COMPLETE"
                        outcomes.append(outcome)
                    self._reconcile_data_gap_reader_record(
                        manifest, batch, chapter, prepared, record, state
                    )
                    continue
                if record.get("state") in TERMINAL_STATES:
                    outcomes.append({"reference": reference, "state": record["state"], "skipped": True})
                    continue
                raw_path = _rooted(self.repo_root, chapter["expected_artifacts"]["raw"])
                if record.get("state") != RAW_CAPTURED or not raw_path.is_file():
                    continue
                item = self._find_item(handoff, reference)
                self._verify_response_envelope(raw_path.read_bytes(), item, batch_id=batch_info["batch_id"])
                outcome = self._import_and_evaluate(manifest, batch, chapter, prepared, record, state, authorization.get("generation", {}).get("reader_enabled", False))
                outcomes.append(outcome)
            self._finish_batch_state(state)
        ledger = rebuild_ledger(self.repo_root)
        return {"status": "RECONCILED", "run_id": run_id, "generation_mode": EXTERNAL_HANDOFF_MODE, "renderer_identity": self.renderer_identity, "provider_calls": 0, "chapters": outcomes, "ledger_counts": ledger["counts"]}

    def _reconcile_data_gap_reader_record(
        self,
        manifest: dict[str, Any],
        batch: dict[str, Any],
        chapter: dict[str, Any],
        prepared: PreparedChapter,
        record: dict[str, Any],
        state: dict[str, Any],
    ) -> bool:
        """Retire an obsolete Reader sidecar without deleting audit history."""

        if not self._is_true_data_gap(prepared):
            return False
        accepted_path = self.repo_root / str(record.get("accepted_path", ""))
        if not accepted_path.is_file():
            return False
        accepted = read_json(accepted_path)
        if accepted.get("data_gap_fallback") is not True:
            return False
        reader_path = str(record.get("reader_path") or "")
        if reader_path:
            history = record.setdefault("historical_reader_artifacts", [])
            if not any(item.get("path") == reader_path for item in history):
                history.append({
                    "path": reader_path,
                    "status": "HISTORICAL_NON_CURRENT",
                    "reason": "DATA_GAP_APPLICATION_FALLBACK",
                })
            record.pop("reader_path", None)
        record["production_disposition"] = "APPLICATION_GENERATED_FALLBACK"
        record["raw_response_disposition"] = "MODEL_GENERATED_RAW" if record.get("raw_path") else "NO_MODEL_RAW"
        record["reader_activation"] = {
            "active": False,
            "signal": "DATA_GAP_APPLICATION_FALLBACK",
            "signals": ["data_gap_application_fallback"],
        }
        record["reader_status"] = "NOT_ELIGIBLE"
        receipt_path = (
            production_root(self.repo_root) / "runs" / manifest["run_id"] / "batches" / batch["batch_id"]
            / "reader-adjudications" / f"attempt-{int(record.get('attempt', 0)):03d}"
            / f"{slug(chapter['book'], chapter['chapter'])}.json"
        )
        receipt = {
            "artifact_version": "commentary-production-data-gap-reader-adjudication-v1",
            "reference": chapter["reference"],
            "attempt": record.get("attempt", 0),
            "reason": "DATA_GAP_APPLICATION_FALLBACK",
            "reader_status": "NOT_ELIGIBLE",
            "historical_reader_artifacts": record.get("historical_reader_artifacts", []),
            "raw_response_disposition": record["raw_response_disposition"],
            "production_disposition": record["production_disposition"],
        }
        write_json(receipt_path, receipt, immutable=True)
        record["reader_adjudication_receipt_path"] = _relative(self.repo_root, receipt_path)
        self._save_state(state)
        return True

    def reconcile_data_gap_reader_state(self, run_id: str) -> dict[str, Any]:
        """Explicitly apply the no-Reader derived-state correction to a run."""

        manifest, _, _ = self._load_handoff(run_id)
        corrected: list[str] = []
        for batch_info in manifest["batches"]:
            batch = batch_manifest(manifest, batch_info["batch_id"])
            state = self._load_state(manifest, batch_info["batch_id"])
            for chapter in batch["chapters"]:
                prepared = self._prepare_locked(manifest, chapter)
                if self._reconcile_data_gap_reader_record(
                    manifest, batch, chapter, prepared,
                    state["chapters"][chapter["reference"]], state,
                ):
                    corrected.append(chapter["reference"])
        ledger = rebuild_ledger(self.repo_root)
        return {"status": "DATA_GAP_READER_RECONCILED", "run_id": run_id, "references": corrected, "provider_calls": 0, "ledger_counts": ledger["counts"]}

    def reprocess_derived(self, run_id: str, references: list[str]) -> dict[str, Any]:
        """Re-evaluate explicit terminal DATA_GAP cases from immutable raw.

        This is adjudication, never a retry: it cannot call a provider, write a
        new raw path, or increment an attempt.  The original quarantine receipt
        remains immutable and is linked from a second adjudication receipt.
        """

        if not references:
            raise ManifestError("REPROCESS_REFERENCE_REQUIRED: specify one or more chapters")
        manifest, handoff, authorization = self._load_handoff(run_id)
        outcomes: list[dict[str, Any]] = []
        for reference in references:
            item = self._find_item(handoff, reference)
            batch = batch_manifest(manifest, item["batch_id"])
            chapter = next(row for row in batch["chapters"] if row["reference"] == reference)
            state = self._load_state(manifest, item["batch_id"])
            record = state["chapters"][reference]
            raw_path = _rooted(self.repo_root, item["expected_raw_path"])
            quarantine_path = _rooted(self.repo_root, chapter["expected_artifacts"]["quarantine"])
            if record.get("state") != QUARANTINED or not quarantine_path.is_file():
                if record.get("adjudication_receipt_path") and raw_path.is_file():
                    raw_sha = sha256_bytes(raw_path.read_bytes())
                    if raw_sha == record.get("raw_sha256"):
                        outcomes.append({"reference": reference, "status": "SKIPPED_ALREADY_ADJUDICATED", "raw_sha256": raw_sha, "state": record.get("state"), "adjudication_receipt_path": record["adjudication_receipt_path"]})
                        continue
                raise ProductionError(f"REPROCESS_NOT_QUARANTINED: {reference} is not an auditable terminal quarantine")
            original = read_json(quarantine_path)
            if "DATA_GAP_FALLBACK_REQUIRED" not in original.get("rejection_codes", []):
                raise ProductionError(f"REPROCESS_NOT_DATA_GAP_FALLBACK: {reference} was not quarantined for DATA_GAP fallback")
            if not raw_path.is_file():
                raise ProductionError(f"REPROCESS_RAW_MISSING: {reference}")
            raw_sha = sha256_bytes(raw_path.read_bytes())
            if raw_sha != record.get("raw_sha256"):
                raise ProductionError(f"REPROCESS_RAW_HASH_MISMATCH: {reference}")
            raw_payload = _parse_response(raw_path.read_text(encoding="utf-8"))
            if raw_payload is None:
                raise ProductionError(f"REPROCESS_RAW_NOT_JSON_OBJECT: {reference}")
            prepared = self._prepare_locked(manifest, chapter)
            # Preview through the exact shared path before reopening state.
            from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
            from .normalization import normalize_data_gap_fallback
            from bhf_agent.chapter_commentary.models import GeneratedMetadata
            payload, normalization = normalize_data_gap_fallback(
                dict(raw_payload), expected_evidence_availability=prepared.synthesis.evidence_availability,
                evidence_item_count=len(prepared.bundle.evidence_items), synthesis_unit_count=len(prepared.synthesis.synthesis_units),
            )
            payload["generated_metadata"] = GeneratedMetadata(
                evidence_hash=prepared.bundle.evidence_hash, evidence_bundle_version=prepared.bundle.version,
                commentary_schema_version=chapter["input_identity"]["commentary_schema_version"], commentary_prompt_version=chapter["input_identity"]["prompt_version"],
                model="external_handoff", generated_timestamp=None, synthesis_hash=prepared.synthesis.synthesis_hash,
                synthesis_schema_version=prepared.synthesis.synthesis_schema_version, synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
                renderer_label=self.renderer_identity,
            ).to_dict()
            payload["evidence_availability"] = prepared.synthesis.evidence_availability
            payload["status"] = "pending"
            preview = validate_chapter_commentary(payload, prepared.bundle, expected_evidence_hash=prepared.bundle.evidence_hash, expected_prompt_version=chapter["input_identity"]["prompt_version"], expected_reference=reference, expected_book=chapter["book"], expected_chapter=int(chapter["chapter"]), synthesis=prepared.synthesis, expected_synthesis_hash=prepared.synthesis.synthesis_hash)
            if not normalization["applied"] or not preview.valid:
                outcomes.append({"reference": reference, "status": "NOT_REOPENED", "raw_sha256": raw_sha, "normalization": normalization, "validator_messages": list(preview.errors)})
                continue
            # This explicit, hash-checked transition is the only reopening
            # operation. It preserves attempt=1 and leaves the old receipt in
            # place while moving its reference into durable history.
            record.setdefault("historical_quarantines", []).append({
                "path": _relative(self.repo_root, quarantine_path), "raw_sha256": raw_sha,
                "rejection_codes": original.get("rejection_codes", []),
            })
            record["historical_quarantine_path"] = record.pop("quarantine_path", _relative(self.repo_root, quarantine_path))
            record.pop("rejection_codes", None)
            record["state"] = RAW_CAPTURED
            self._save_state(state)
            outcome = self._import_and_evaluate(manifest, batch, chapter, prepared, record, state, authorization.get("generation", {}).get("reader_enabled", False))
            receipt_path = production_root(self.repo_root) / "runs" / run_id / "batches" / item["batch_id"] / "adjudications" / "attempt-001" / f"{slug(chapter['book'], chapter['chapter'])}.json"
            receipt = {
                "artifact_version": "commentary-production-derived-adjudication-v1",
                "reference": reference, "attempt": record["attempt"], "provider_calls": 0,
                "raw_path": record.get("raw_path"), "raw_sha256_before": raw_sha, "raw_sha256_after": record.get("raw_sha256"),
                "original_quarantine_path": _relative(self.repo_root, quarantine_path),
                "original_rejection_codes": original.get("rejection_codes", []),
                "application_normalization": normalization,
                "derived_status_before": QUARANTINED, "derived_status_after": record.get("state"),
                "outcome": outcome,
            }
            write_json(receipt_path, receipt, immutable=True)
            record["adjudication_receipt_path"] = _relative(self.repo_root, receipt_path)
            self._save_state(state)
            outcomes.append({"reference": reference, "status": "READJUDICATED", "raw_sha256": raw_sha, "state": record.get("state"), "adjudication_receipt_path": record["adjudication_receipt_path"]})
        ledger = rebuild_ledger(self.repo_root)
        return {"status": "DERIVED_REPROCESS_COMPLETE", "run_id": run_id, "provider_calls": 0, "chapters": outcomes, "ledger_counts": ledger["counts"]}

    def next_work(self, run_id: str) -> dict[str, Any]:
        manifest, handoff, _ = self._load_handoff(run_id)
        self.reconcile_run(run_id)
        work: list[dict[str, Any]] = []
        for item in handoff["items"]:
            state = self._load_state(manifest, item["batch_id"])["chapters"][item["reference"]]
            if state.get("state") in TERMINAL_STATES:
                continue
            kind = "VALIDATE_CAPTURED_RAW" if state.get("state") == RAW_CAPTURED else "RENDER_PACKET"
            work.append({
                "work": kind,
                "run_id": run_id,
                "batch_id": item["batch_id"],
                "reference": item["reference"],
                "packet_path": item["packet_path"],
                "packet_id": item["packet_id"],
                "packet_hash": item["packet_hash"],
                "expected_raw_path": item["expected_raw_path"],
                "attempt": item["attempt"],
                "state": state.get("state"),
                "renderer_identity": self.renderer_identity,
            })
        return {"status": "NEXT_HANDOFF_WORK" if work else "HANDOFF_COMPLETE", "run_id": run_id, "generation_mode": EXTERNAL_HANDOFF_MODE, "renderer_identity": self.renderer_identity, "provider_calls": 0, "next": work[0] if work else None, "remaining": len(work)}

    def _finish_batch_state(self, state: dict[str, Any]) -> None:
        terminal_or_in_progress = state.get("chapters", {}).values()
        state["status"] = "COMPLETE" if all(row.get("state") in TERMINAL_STATES for row in terminal_or_in_progress) else "IN_PROGRESS"
        self._save_state(state)


__all__ = ["HandoffRunner", "HANDOFF_MANIFEST_VERSION"]
