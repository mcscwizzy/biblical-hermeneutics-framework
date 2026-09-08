#!/usr/bin/env python3
"""Prepare the frozen Commentary 1.5 Batch 3 pilot packets.

This command copies no prose and does not invoke a renderer.  It rebuilds the
current prompt around the locked v1.3 pilot EvidenceBundle/synthesis inputs,
then asserts that the evidence, synthesis, and canonical text identities are
unchanged before writing a new candidate-only packet set.
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
from bhf_agent.chapter_commentary.richness_clusters import CORE_CLASSIFIER_V2, RICHNESS_GATE_V2_VERSION, cluster_synthesis_units
from bhf_agent.chapter_commentary.synthesis import load_synthesis, validate_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v14_calibration import _ckl_snapshot, _protected_v11_errors


SOURCE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.3-pilot"
TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-batch-3"
PACKET_ROOT = TARGET_ROOT / "canary/prompts"
SYNTHESIS_ROOT = TARGET_ROOT / "canary/synthesis"
V11_STATE_PATH = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json"

TARGETS = (
    "Judges 12",
    "Nehemiah 2",
    "Ecclesiastes 4",
    "Proverbs 6",
    "Ezekiel 7",
    "Zechariah 5",
    "Acts 6",
    "Luke 5",
    "James 3",
    "2 Chronicles 8",
)


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
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
    return f"commentary-v1.5-packet:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _source_row(reference: str) -> dict[str, Any]:
    manifest = _read(SOURCE_ROOT / "pilot-manifest.json")
    for row in manifest["chapters"]:
        if row["reference"] == reference:
            return row
    raise RuntimeError(f"missing historical v1.3 row for {reference}")


def _source_packet(row: dict[str, Any]) -> dict[str, Any]:
    return _read(ROOT / row["packet_path"])


def _canonical_from_prompt(prompt: str) -> str:
    return prompt.split("CANONICAL TEXT:\n", 1)[1].split("\n\nCOMPILED CHAPTER SYNTHESIS:", 1)[0]


def _density(unit_count: int) -> str:
    if unit_count == 0:
        return "0"
    if unit_count <= 5:
        return "1-5"
    if unit_count <= 10:
        return "6-10"
    if unit_count <= 20:
        return "11-20"
    if unit_count <= 40:
        return "21-40"
    return "41+"


def prepare() -> dict[str, Any]:
    if COMMENTARY_PROMPT_VERSION != "1.5" or COMMENTARY_SCHEMA_VERSION != "1.2":
        raise RuntimeError("frozen Commentary 1.5/schema 1.2 contract is not active")
    before_v11 = _protected_v11_errors()
    if before_v11:
        raise RuntimeError("protected v1.1 fingerprints changed")
    before_ckl = _ckl_snapshot()
    rows: list[dict[str, Any]] = []
    for reference in TARGETS:
        book, chapter_text = reference.rsplit(" ", 1)
        chapter = int(chapter_text)
        historical = _source_row(reference)
        source_packet = _source_packet(historical)
        if source_packet.get("commentary_prompt_version") != "1.3":
            raise RuntimeError(f"historical packet is not Prompt 1.3: {reference}")
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        synthesis = load_synthesis(SOURCE_ROOT / "synthesis", book, chapter)
        if bundle is None or synthesis is None:
            raise RuntimeError(f"missing locked input for {reference}")
        errors = validate_synthesis(synthesis, bundle)
        if errors:
            raise RuntimeError(f"invalid locked synthesis for {reference}: {'; '.join(errors)}")
        if bundle.evidence_hash != historical["evidence_hash"] or synthesis.synthesis_hash != historical["synthesis_hash"]:
            raise RuntimeError(f"locked hash disagreement for {reference}")
        chapter_data = bible.resolve_chapter(book, chapter)
        canonical_text = bible.passage_text(chapter_data.get("verses", []))
        if canonical_text != _canonical_from_prompt(source_packet["user_prompt"]):
            raise RuntimeError(f"canonical text changed for {reference}")
        user_prompt = build_user_prompt(reference, book, chapter, canonical_text, synthesis, bundle, synthesis.evidence_availability)
        clusters = cluster_synthesis_units(synthesis.synthesis_units, bundle.evidence_items, core_classifier=CORE_CLASSIFIER_V2)
        packet = {
            "artifact_version": "commentary-v1.5-batch-3-generation-packet-v1",
            "pilot_version": "commentary-v1.5-frozen-batch-3-pilot-v1",
            "reference": reference,
            "literary_category": historical["literary_category"],
            "selection_rationale": historical["selection_rationale"],
            "renderer_requirement": "APPROVED_RENDERER_REQUIRED",
            "execution_path": "conversational",
            "expected_response_path": (TARGET_ROOT / "canary/responses/raw" / f"{_slug(book)}_{chapter:03d}.json").relative_to(ROOT).as_posix(),
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
            "refined_core_count": sum(cluster.quality_class == "CORE" for cluster in clusters),
            "synthesis_density_bucket": _density(len(synthesis.synthesis_units)),
            "gate_v2": {"status": "CANDIDATE_ONLY", "activated_globally": False, "version": RICHNESS_GATE_V2_VERSION, "core_classifier": CORE_CLASSIFIER_V2, "evaluation_deferred_until": "EXTERNAL_PROSE_IMPORTED"},
            "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
        }
        packet["packet_id"] = _packet_id(packet)
        filename = f"{_slug(book)}_{chapter:03d}.json"
        _write(PACKET_ROOT / filename, packet)
        _write(SYNTHESIS_ROOT / filename, synthesis.to_dict())
        rows.append({
            "reference": reference,
            "book": book,
            "chapter": chapter,
            "literary_category": historical["literary_category"],
            "selection_rationale": historical["selection_rationale"],
            "source_packet_id": source_packet["packet_id"],
            "packet_id": packet["packet_id"],
            "source_prompt_version": "1.3",
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "evidence_availability": synthesis.evidence_availability,
            "evidence_count": len(bundle.evidence_items),
            "evidence_hash": bundle.evidence_hash,
            "synthesis_hash": synthesis.synthesis_hash,
            "synthesis_schema_version": synthesis.synthesis_schema_version,
            "synthesis_compiler_version": synthesis.synthesis_compiler_version,
            "raw_synthesis_unit_count": len(synthesis.synthesis_units),
            "idea_cluster_count": len(clusters),
            "refined_core_count": sum(cluster.quality_class == "CORE" for cluster in clusters),
            "synthesis_density_bucket": _density(len(synthesis.synthesis_units)),
            "packet_path": (PACKET_ROOT / filename).relative_to(ROOT).as_posix(),
            "synthesis_path": (SYNTHESIS_ROOT / filename).relative_to(ROOT).as_posix(),
            "expected_response_path": packet["expected_response_path"],
            "accepted_candidate_path": (TARGET_ROOT / "canary/responses/accepted" / filename).relative_to(ROOT).as_posix(),
            "evidence_locked": True,
            "synthesis_locked": True,
            "canonical_text_unchanged": True,
        })
    after_v11 = _protected_v11_errors()
    after_ckl = _ckl_snapshot()
    if after_v11 or before_ckl != after_ckl:
        raise RuntimeError("v1.1 or CKL identity changed during packet preparation")
    preflight = {
        "artifact_version": "commentary-v1.5-batch-3-preflight-v1",
        "status": "READY_FOR_RENDERER",
        "candidate_only": True,
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "source_pilot": "commentary-v1.3-pilot",
        "source_responses_preserved": True,
        "v1_1_protected_fingerprints_verified": True,
        "ckl_unchanged": True,
        "evidence_locked": True,
        "synthesis_locked": True,
        "chapters": rows,
    }
    manifest = {
        "artifact_version": "commentary-v1.5-batch-3-manifest-v1",
        "status": "READY_FOR_RENDERER",
        "candidate_only": True,
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "synthesis_schema_version": "1.1",
        "synthesis_compiler_version": "1.1",
        "gate_version": RICHNESS_GATE_V2_VERSION,
        "renderer_identity": preflight["renderer_identity"],
        "batch_number": 3,
        "chapter_count": len(rows),
        "source_pilot_preserved": True,
        "bulk_authorization": False,
        "chapters": rows,
    }
    _write(TARGET_ROOT / "canary/canary-preflight.json", preflight)
    _write(TARGET_ROOT / "canary/canary-generation-manifest.json", {**preflight, "artifact_version": "commentary-v1.5-batch-3-generation-manifest-v1"})
    _write(TARGET_ROOT / "batch-3-manifest.json", manifest)
    _write(TARGET_ROOT / "candidate-state.json", {"pipeline_version": "commentary-v1.5-batch-3", "current_stage": "READY_FOR_RENDERER", "commentary_prompt_version": "1.5", "commentary_schema_version": "1.2", "gate_version": RICHNESS_GATE_V2_VERSION, "batch_3_chapter_count": len(rows), "bulk_authorization": False})
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
