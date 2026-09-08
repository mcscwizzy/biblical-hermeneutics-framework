#!/usr/bin/env python3
"""Prepare the bounded Commentary 1.4 calibration set.

This artifact is deliberately separate from the Commentary 1.3 pilot.  It
rebuilds and locks the same EvidenceBundle and compiled synthesis for the four
requested chapters, then writes only new v1.4 prompt packets and importer
manifests.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.prompts import CHAPTER_COMMENTARY_SYSTEM_PROMPT, build_user_prompt
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    RICHNESS_GATE_V2_VERSION,
    cluster_synthesis_units,
)
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis, save_synthesis, validate_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from framework.canonical_library import CKLRepositoryConfig
from bhf_agent.ckl import load_canonical_library


CALIBRATION_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-calibration"
CANARY_ROOT = CALIBRATION_ROOT / "canary"
PACKET_ROOT = CANARY_ROOT / "prompts"
SYNTHESIS_ROOT = CANARY_ROOT / "synthesis"
TARGETS = (("Exodus", 12), ("Esther", 4), ("Jeremiah", 7), ("1 Chronicles", 9))
V11_STATE_PATH = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json"


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _packet_id(packet: dict[str, Any]) -> str:
    identity = {key: value for key, value in packet.items() if key != "packet_id"}
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"commentary-v1.4-packet:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _protected_v11_errors() -> list[str]:
    state = json.loads(V11_STATE_PATH.read_text(encoding="utf-8"))
    errors = []
    for relative, expected in state.get("protected_fingerprints", {}).items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            errors.append(relative)
    return errors


def _ckl_snapshot() -> dict[str, Any]:
    objects_root = ROOT / "framework/canonical_library/objects"
    digest = hashlib.sha256()
    paths = sorted(path for path in objects_root.rglob("*.json") if path.is_file())
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    library = load_canonical_library(config=CKLRepositoryConfig())
    inventory = getattr(library, "inventory_fingerprint", None)
    return {
        "json_object_count": len(paths),
        "json_objects_digest": digest.hexdigest(),
        "inventory_fingerprint": inventory() if callable(inventory) else None,
    }


def prepare() -> dict[str, Any]:
    before_v11 = _protected_v11_errors()
    if before_v11:
        raise RuntimeError("protected Commentary v1.1 fingerprints changed")
    before_ckl = _ckl_snapshot()
    rows = []
    for book, chapter in TARGETS:
        reference = f"{book} {chapter}"
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        if bundle is None:
            raise RuntimeError(f"unable to build EvidenceBundle for {reference}")
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
        errors = validate_synthesis(synthesis, bundle)
        if errors:
            raise RuntimeError(f"invalid synthesis for {reference}: {'; '.join(errors)}")
        synthesis_path = save_synthesis(synthesis, SYNTHESIS_ROOT)
        chapter_data = bible.resolve_chapter(book, chapter)
        canonical_text = bible.passage_text(chapter_data.get("verses", []))
        user_prompt = build_user_prompt(
            reference, book, chapter, canonical_text, synthesis, bundle,
            synthesis.evidence_availability,
        )
        clusters = cluster_synthesis_units(
            synthesis.synthesis_units, bundle.evidence_items,
            core_classifier=CORE_CLASSIFIER_V2,
        )
        packet = {
            "artifact_version": "commentary-v1.4-calibration-generation-packet-v1",
            "calibration_version": "commentary-v1.4-selectivity-calibration-v1",
            "reference": reference,
            "renderer_requirement": "APPROVED_RENDERER_REQUIRED",
            "execution_path": "conversational",
            "candidate_only": True,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "evidence_bundle_version": bundle.version,
            "evidence_availability": synthesis.evidence_availability,
            "evidence_count": len(bundle.evidence_items),
            "evidence_hash": bundle.evidence_hash,
            "synthesis_hash": synthesis.synthesis_hash,
            "synthesis_schema_version": synthesis.synthesis_schema_version,
            "synthesis_compiler_version": synthesis.synthesis_compiler_version,
            "raw_synthesis_unit_count": len(synthesis.synthesis_units),
            "idea_cluster_count": len(clusters),
            "core_cluster_count": sum(cluster.quality_class == "CORE" for cluster in clusters),
            "gate_v2": {
                "status": "CANDIDATE_ONLY",
                "activated_globally": False,
                "version": RICHNESS_GATE_V2_VERSION,
                "core_classifier": CORE_CLASSIFIER_V2,
                "evaluation_deferred_until": "EXTERNAL_PROSE_IMPORTED",
            },
            "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
        }
        packet["packet_id"] = _packet_id(packet)
        packet_path = PACKET_ROOT / f"{_slug(book)}_{chapter:03d}.json"
        _write_json(packet_path, packet)
        filename = packet_path.name
        rows.append({
            "reference": reference,
            "book": book,
            "chapter": chapter,
            "packet_id": packet["packet_id"],
            "packet_path": packet_path.relative_to(ROOT).as_posix(),
            "expected_response_path": (CANARY_ROOT / "responses/raw" / filename).relative_to(ROOT).as_posix(),
            "accepted_candidate_path": (CANARY_ROOT / "responses/accepted" / filename).relative_to(ROOT).as_posix(),
            "evidence_hash": bundle.evidence_hash,
            "synthesis_hash": synthesis.synthesis_hash,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "evidence_availability": synthesis.evidence_availability,
            "evidence_ids": sorted(bundle.evidence_by_id),
            "synthesis_path": synthesis_path.relative_to(ROOT).as_posix(),
            "evidence_locked": True,
            "synthesis_locked": True,
        })
    after_v11 = _protected_v11_errors()
    after_ckl = _ckl_snapshot()
    if after_v11 or before_ckl != after_ckl:
        raise RuntimeError("protected v1.1 or CKL identity changed during calibration preparation")
    preflight = {
        "artifact_version": "commentary-v1.4-calibration-preflight-v1",
        "status": "READY_FOR_RENDERER",
        "renderer_requirement": {"status": "APPROVED_RENDERER_REQUIRED", "execution_path": "conversational"},
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "candidate_only": True,
        "v1_1_protected_fingerprints_verified": True,
        "ckl_unchanged": True,
        "evidence_locked": True,
        "synthesis_locked": True,
        "chapters": rows,
    }
    manifest = {
        "artifact_version": "commentary-v1.4-calibration-manifest-v1",
        "calibration_version": "commentary-v1.4-selectivity-calibration-v1",
        "status": "READY_FOR_RENDERER",
        "candidate_only": True,
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "source_pilot": "commentary-v1.3-pilot",
        "source_responses_preserved": True,
        "bulk_authorization": {"full_bible_generation_authorized": False, "pilot_batch_2_authorized": False},
        "integrity": {"v1_1_protected_fingerprints_unchanged": True, "ckl_unchanged": True, "evidence_locked": True, "synthesis_locked": True},
        "chapters": rows,
    }
    _write_json(CANARY_ROOT / "canary-preflight.json", preflight)
    _write_json(CANARY_ROOT / "canary-generation-manifest.json", {**preflight, "artifact_version": "commentary-v1.4-calibration-generation-manifest-v1"})
    _write_json(CALIBRATION_ROOT / "calibration-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
