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
            state = self._load_state(manifest, chapter["batch_id"])
            state["generation_mode"] = EXTERNAL_HANDOFF_MODE
            state["renderer_identity"] = self.renderer_identity
            state["generation_identity"] = receipt["generation_identity"]
            record = state["chapters"][chapter["reference"]]
            if record.get("state") not in TERMINAL_STATES and not record.get("raw_path"):
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
                if record.get("state") in TERMINAL_STATES:
                    outcomes.append({"reference": reference, "state": record["state"], "skipped": True})
                    continue
                raw_path = _rooted(self.repo_root, chapter["expected_artifacts"]["raw"])
                if record.get("state") != RAW_CAPTURED or not raw_path.is_file():
                    continue
                item = self._find_item(handoff, reference)
                self._verify_response_envelope(raw_path.read_bytes(), item, batch_id=batch_info["batch_id"])
                prepared = self._prepare_locked(manifest, chapter)
                outcome = self._import_and_evaluate(manifest, batch, chapter, prepared, record, state, authorization.get("generation", {}).get("reader_enabled", False))
                outcomes.append(outcome)
            self._finish_batch_state(state)
        ledger = rebuild_ledger(self.repo_root)
        return {"status": "RECONCILED", "run_id": run_id, "generation_mode": EXTERNAL_HANDOFF_MODE, "renderer_identity": self.renderer_identity, "provider_calls": 0, "chapters": outcomes, "ledger_counts": ledger["counts"]}

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
