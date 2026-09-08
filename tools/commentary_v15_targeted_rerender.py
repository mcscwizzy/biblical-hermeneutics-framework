#!/usr/bin/env python3
"""Prepare locked Prompt 1.5 packets for the preserved Batch 2 failures.

The target set is read from the deterministic within-family audit.  This keeps
the rerender bounded to the audited failures without embedding chapter-specific
selection behavior in the renderer prompt.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


SOURCE_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.4-pilot-batch-2/canary"
AUDIT_PATH = SOURCE_ROOT.parent / "evaluation/within-family-audit.json"
TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-targeted-rerender"
CANARY_ROOT = TARGET_ROOT / "canary"
PACKET_ROOT = CANARY_ROOT / "prompts"
SYNTHESIS_ROOT = CANARY_ROOT / "synthesis"


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
    return f"commentary-v1.5-packet:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def _source_row(reference: str) -> dict[str, Any]:
    manifest = json.loads((SOURCE_ROOT.parent / "batch-2-manifest.json").read_text(encoding="utf-8"))
    for row in manifest["chapters"]:
        if row["reference"] == reference:
            return row
    raise RuntimeError(f"missing preserved Batch 2 manifest row for {reference}")


def prepare() -> dict[str, Any]:
    if COMMENTARY_PROMPT_VERSION != "1.5":
        raise RuntimeError(f"expected Prompt 1.5, found {COMMENTARY_PROMPT_VERSION}")
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    references = list(audit["failure_references"])
    if not references:
        raise RuntimeError("within-family audit did not identify targeted failures")

    rows: list[dict[str, Any]] = []
    for reference in references:
        book, chapter_text = reference.rsplit(" ", 1)
        chapter = int(chapter_text)
        source = _source_row(reference)
        source_packet_path = ROOT / source["packet_path"]
        source_packet = json.loads(source_packet_path.read_text(encoding="utf-8"))
        if source_packet["commentary_prompt_version"] != "1.4":
            raise RuntimeError(f"source packet is not preserved Prompt 1.4: {reference}")
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        synthesis = load_synthesis(SOURCE_ROOT / "synthesis", book, chapter)
        if bundle is None or synthesis is None:
            raise RuntimeError(f"unable to rebuild locked inputs for {reference}")
        if bundle.evidence_hash != source["evidence_hash"] or synthesis.synthesis_hash != source["synthesis_hash"]:
            raise RuntimeError(f"locked identity mismatch for {reference}")
        chapter_data = bible.resolve_chapter(book, chapter)
        canonical_text = bible.passage_text(chapter_data.get("verses", []))
        packet = {
            "artifact_version": "commentary-v1.5-targeted-generation-packet-v1",
            "rerender_version": "commentary-v1.5-within-family-rerender-v1",
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
            "idea_cluster_count": source_packet["idea_cluster_count"],
            "core_cluster_count": source_packet["core_cluster_count"],
            "gate_v2": source_packet["gate_v2"],
            "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
            "user_prompt": build_user_prompt(
                reference, book, chapter, canonical_text, synthesis, bundle,
                synthesis.evidence_availability,
            ),
        }
        packet["gate_v2"] = {
            **packet["gate_v2"],
            "evaluation_deferred_until": "PROMPT_1_5_PROSE_IMPORTED",
        }
        packet["packet_id"] = _packet_id(packet)
        filename = f"{_slug(book)}_{chapter:03d}.json"
        packet_path = PACKET_ROOT / filename
        synthesis_path = SYNTHESIS_ROOT / filename
        _write_json(packet_path, packet)
        synthesis_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_ROOT / "synthesis" / filename, synthesis_path)
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
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "evidence_availability": synthesis.evidence_availability,
            "raw_synthesis_unit_count": len(synthesis.synthesis_units),
            "idea_cluster_count": source_packet["idea_cluster_count"],
            "core_cluster_count": source_packet["core_cluster_count"],
            "synthesis_path": synthesis_path.relative_to(ROOT).as_posix(),
            "source_packet_id": source_packet["packet_id"],
            "source_prompt_version": source_packet["commentary_prompt_version"],
            "evidence_locked": True,
            "synthesis_locked": True,
        })

    preflight = {
        "artifact_version": "commentary-v1.5-targeted-preflight-v1",
        "status": "READY_FOR_RENDERER",
        "candidate_only": True,
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "prompt_change": "1.4 -> 1.5",
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "gate_version": "commentary-richness-gate-v2.1",
        "gate_changed": False,
        "evidence_locked": True,
        "synthesis_locked": True,
        "chapters": rows,
    }
    manifest = {
        **preflight,
        "artifact_version": "commentary-v1.5-targeted-rerender-manifest-v1",
        "source_batch": "commentary-v1.4-pilot-batch-2",
        "historical_responses_preserved": True,
        "bulk_authorization": False,
        "batch_3_authorized": False,
    }
    _write_json(CANARY_ROOT / "canary-preflight.json", preflight)
    _write_json(CANARY_ROOT / "canary-generation-manifest.json", {**preflight, "artifact_version": "commentary-v1.5-targeted-generation-manifest-v1"})
    _write_json(TARGET_ROOT / "targeted-rerender-manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
