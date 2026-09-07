#!/usr/bin/env python3
"""Prepare the isolated Commentary 1.3 Genesis 1 Luna-Medium packet.

This tool deliberately stops at the external-renderer boundary. It writes a
new experiment directory and never rewrites the historical Commentary 1.2
packet, response, candidate, or diagnostic artifacts.
"""

from __future__ import annotations

import argparse
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
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
)
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT,
    build_user_prompt,
)
from bhf_agent.chapter_commentary.synthesis import (
    compile_chapter_synthesis,
    validate_synthesis,
)
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


REFERENCE = "Genesis 1"
BOOK = "Genesis"
CHAPTER = 1
EXPERIMENT_ID = "genesis-1-prompt-1.3-consolidation"
HISTORICAL_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary"
HISTORICAL_PACKET_PATH = HISTORICAL_ROOT / "prompts/genesis_001.json"
EXPERIMENT_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.3-consolidation"
PACKET_PATH = EXPERIMENT_ROOT / "prompt/genesis_001.json"
MANIFEST_PATH = EXPERIMENT_ROOT / "experiment-manifest.json"


def prepare() -> dict[str, Any]:
    """Build and persist exactly one new, externally renderable packet."""

    historical = _read_json(HISTORICAL_PACKET_PATH)
    if historical.get("commentary_prompt_version") != "1.2":
        raise RuntimeError("historical Genesis 1 packet is not Commentary 1.2")

    bundle = get_chapter_evidence_bundle(
        BOOK, CHAPTER, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    if bundle is None:
        raise RuntimeError("unable to build the Genesis 1 evidence bundle")
    synthesis = compile_chapter_synthesis(bundle, book=BOOK, chapter=CHAPTER)
    errors = validate_synthesis(synthesis, bundle)
    if errors:
        raise RuntimeError("invalid compiled synthesis: " + "; ".join(errors))
    if bundle.evidence_hash != historical.get("evidence_hash"):
        raise RuntimeError("Genesis 1 evidence hash changed")
    if synthesis.synthesis_hash != historical.get("synthesis_hash"):
        raise RuntimeError("Genesis 1 synthesis hash changed")
    if len(synthesis.synthesis_units) != historical.get("synthesis_unit_count", 49):
        raise RuntimeError("Genesis 1 synthesis unit count changed")

    try:
        chapter_data = bible.resolve_chapter(BOOK, CHAPTER)
        canonical_text = bible.passage_text(chapter_data.get("verses", []))
    except bible.BibleError as exc:
        raise RuntimeError(f"unable to load canonical text for {REFERENCE}: {exc}") from exc

    user_prompt = build_user_prompt(
        REFERENCE,
        BOOK,
        CHAPTER,
        canonical_text,
        synthesis,
        bundle,
        synthesis.evidence_availability,
    )
    packet = {
        "artifact_version": "commentary-v1.3-generation-packet-v1",
        "experiment_id": EXPERIMENT_ID,
        "reference": REFERENCE,
        "renderer_requirement": "APPROVED_RENDERER_REQUIRED",
        "execution_path": "external_or_conversational",
        "renderer_label": "Luna Medium",
        "model": "luna",
        "reasoning_effort": "medium",
        "candidate_only": True,
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
        "synthesis_schema_version": synthesis.synthesis_schema_version,
        "synthesis_compiler_version": synthesis.synthesis_compiler_version,
        "synthesis_unit_count": len(synthesis.synthesis_units),
        "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
        "user_prompt": user_prompt,
    }
    packet["packet_id"] = calculate_packet_id(packet)
    _write_json(PACKET_PATH, packet)

    manifest = {
        "artifact_version": "commentary-v1.3-genesis-experiment-manifest-v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "READY_FOR_EXTERNAL_RENDERER",
        "candidate_only": True,
        "renderer_requirement": {
            "status": "APPROVED_RENDERER_REQUIRED",
            "renderer": "Luna",
            "model": "Luna Medium",
            "reasoning_effort": "medium",
            "execution_path": "external_or_conversational",
        },
        "historical_v1_2": {
            "packet_id": historical.get("packet_id"),
            "packet_path": HISTORICAL_PACKET_PATH.relative_to(ROOT).as_posix(),
            "prompt_version": historical.get("commentary_prompt_version"),
            "evidence_hash": historical.get("evidence_hash"),
            "synthesis_hash": historical.get("synthesis_hash"),
        },
        "experimental_v1_3": {
            "packet_id": packet["packet_id"],
            "packet_path": PACKET_PATH.relative_to(ROOT).as_posix(),
            "prompt_version": packet["commentary_prompt_version"],
            "evidence_hash": packet["evidence_hash"],
            "synthesis_hash": packet["synthesis_hash"],
            "synthesis_unit_count": packet["synthesis_unit_count"],
        },
        "identity_checks": {
            "evidence_hash_unchanged": packet["evidence_hash"] == historical.get("evidence_hash"),
            "synthesis_hash_unchanged": packet["synthesis_hash"] == historical.get("synthesis_hash"),
            "synthesis_unit_count_unchanged": packet["synthesis_unit_count"] == historical.get("synthesis_unit_count", 49),
            "schema_unchanged": packet["commentary_schema_version"] == "1.2",
            "packet_id_changed": packet["packet_id"] != historical.get("packet_id"),
        },
        "external_renderer_boundary": {
            "status": "NOT_INVOKED",
            "renderer_invoked": False,
            "fallback_provider_used": False,
        },
    }
    _write_json(MANIFEST_PATH, manifest)
    return manifest


def calculate_packet_id(packet: dict[str, Any]) -> str:
    identity_payload = {key: value for key, value in packet.items() if key != "packet_id"}
    encoded = json.dumps(
        identity_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"commentary-v1.3-packet:{hashlib.sha256(encoded).hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare",))
    parser.parse_args(argv)
    try:
        result = prepare()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": result["status"],
        "packet_id": result["experimental_v1_3"]["packet_id"],
        "packet_path": result["experimental_v1_3"]["packet_path"],
        "renderer_boundary": result["external_renderer_boundary"]["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
