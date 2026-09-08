#!/usr/bin/env python3
"""Prepare the real-world stratified Commentary 1.3 pilot.

This command stops at the deterministic packet boundary.  It never invokes a
renderer, imports prose, evaluates Gate v2, or writes any production
commentary.  The selected matrix is intentionally explicit so that a future
run cannot silently change the pilot population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_SCHEMA_VERSION,
)
from bhf_agent.chapter_commentary.prompts import (
    CHAPTER_COMMENTARY_SYSTEM_PROMPT,
    build_user_prompt,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    cluster_synthesis_units,
)
from bhf_agent.chapter_commentary.synthesis import (
    compile_chapter_synthesis,
    save_synthesis,
    validate_synthesis,
)
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from framework.canonical_library import CKLRepositoryConfig
from bhf_agent.ckl import load_canonical_library


PILOT_VERSION = "commentary-v1.3-real-world-stratified-pilot-v1"
PILOT_PROMPT_VERSION = "1.3"
PILOT_GATE_VERSION = "commentary-richness-gate-v2"
PILOT_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.3-pilot"
PACKET_ROOT = PILOT_ROOT / "packets"
SYNTHESIS_ROOT = PILOT_ROOT / "synthesis"
RESPONSE_ROOT = PILOT_ROOT / "expected-external-responses"
MANIFEST_PATH = PILOT_ROOT / "pilot-manifest.json"
V11_STATE_PATH = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/pipeline-state.json"
GENESIS_MANIFEST_PATH = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.3-consolidation/experiment-manifest.json"

ORIGINAL_CANARIES = frozenset(
    {
        "Genesis 1",
        "Leviticus 16",
        "Ruth 3",
        "Psalms 1",
        "1 Samuel 21",
        "1 Samuel 28",
        "2 Samuel 6",
        "2 Samuel 24",
        "1 Chronicles 8",
        "John 1",
        "Isaiah 6",
        "Revelation 12",
        "Numbers 3",
    }
)

# The category is a pilot stratum, not a claim that a chapter has only one
# literary feature.  Genealogy/list/admin is kept separate to exercise the
# concise-output path instead of being absorbed into historical narrative.
PILOT_SELECTION = (
    ("Genesis", 24, "Pentateuch", "narrative action, family negotiation, and custom"),
    ("Exodus", 12, "Pentateuch", "law/ritual and festival practice"),
    ("Leviticus", 2, "Pentateuch", "law/ritual under thin evidence"),
    ("Numbers", 7, "Pentateuch", "administrative census/list material with a data gap"),
    ("Deuteronomy", 24, "Pentateuch", "law, household practice, and social protection"),
    ("Joshua", 17, "Historical narrative", "historical/geographical land allocation"),
    ("Judges", 12, "Historical narrative", "narrative action in a compressed judge cycle"),
    ("1 Kings", 7, "Historical narrative", "temple construction and administration"),
    ("Esther", 4, "Historical narrative", "cultural/custom context and court crisis"),
    ("Nehemiah", 2, "Historical narrative", "historical/geographical inspection and planning"),
    ("Job", 3, "Poetry/Wisdom", "poetry, lament, and wisdom dispute"),
    ("Psalms", 73, "Poetry/Wisdom", "poetic perplexity and sanctuary perspective"),
    ("Ecclesiastes", 4, "Poetry/Wisdom", "wisdom instruction and social observation"),
    ("Proverbs", 6, "Poetry/Wisdom", "wisdom instruction with a data gap"),
    ("Isaiah", 24, "Prophets", "prophetic judgment under thin evidence"),
    ("Jeremiah", 7, "Prophets", "prophetic judgment and temple discourse"),
    ("Amos", 5, "Prophets", "prophetic judgment, justice, and cultic critique"),
    ("Ezekiel", 7, "Prophets", "prophetic judgment with a data gap"),
    ("Zechariah", 5, "Prophets", "prophetic symbolism and vision language"),
    ("Acts", 6, "Gospels/Acts", "Gospel-era community administration and narrative action"),
    ("Mark", 7, "Gospels/Acts", "Gospel discourse/teaching and purity custom"),
    ("Luke", 5, "Gospels/Acts", "Gospel narrative with a data gap"),
    ("John", 4, "Gospels/Acts", "Gospel narrative, geography, and cultural encounter"),
    ("Romans", 7, "Epistles", "Pauline reasoning about law, sin, and the self"),
    ("1 Corinthians", 11, "Epistles", "Pauline reasoning, communal custom, and worship"),
    ("Hebrews", 4, "Epistles", "general-epistle reasoning and priestly imagery"),
    ("James", 3, "Epistles", "general-epistle wisdom instruction and ethics"),
    ("Revelation", 3, "Apocalyptic / highly symbolic", "symbolic/apocalyptic imagery under thin evidence"),
    ("1 Chronicles", 9, "Genealogy/list/administrative", "genealogy, restoration, and administrative list"),
    ("2 Chronicles", 8, "Genealogy/list/administrative", "administrative temple/economic list with a data gap"),
)

EXPECTED_CATEGORY_COUNTS = {
    "Pentateuch": 5,
    "Historical narrative": 5,
    "Poetry/Wisdom": 4,
    "Prophets": 5,
    "Gospels/Acts": 4,
    "Epistles": 4,
    "Apocalyptic / highly symbolic": 1,
    "Genealogy/list/administrative": 2,
}


def density_bucket(unit_count: int) -> str:
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


def calculate_packet_id(packet: dict[str, Any]) -> str:
    identity = {key: value for key, value in packet.items() if key != "packet_id"}
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"commentary-v1.3-packet:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def prepare() -> dict[str, Any]:
    validate_selection()
    v11_before = protected_v11_errors()
    if v11_before:
        raise RuntimeError("protected Commentary v1.1 fingerprints changed: " + ", ".join(v11_before))
    ckl_before = ckl_snapshot()

    rows: list[dict[str, Any]] = []
    for book, chapter, category, rationale in PILOT_SELECTION:
        reference = f"{book} {chapter}"
        bundle = get_chapter_evidence_bundle(
            book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
        )
        if bundle is None:
            raise RuntimeError(f"unable to build EvidenceBundle for {reference}")
        synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
        synthesis_errors = validate_synthesis(synthesis, bundle)
        if synthesis_errors:
            raise RuntimeError(f"invalid synthesis for {reference}: {'; '.join(synthesis_errors)}")
        clusters = cluster_synthesis_units(
            synthesis.synthesis_units,
            bundle.evidence_items,
            core_classifier=CORE_CLASSIFIER_V2,
        )
        core_clusters = [cluster for cluster in clusters if cluster.quality_class == "CORE"]
        try:
            chapter_data = bible.resolve_chapter(book, chapter)
            canonical_text = bible.passage_text(chapter_data.get("verses", []))
        except bible.BibleError as exc:
            raise RuntimeError(f"unable to load canonical text for {reference}: {exc}") from exc
        expected_response = RESPONSE_ROOT / f"{_slug(book)}_{chapter:03d}.json"
        packet_path = PACKET_ROOT / f"{_slug(book)}_{chapter:03d}.json"
        existing_packet = _read_json(packet_path) if packet_path.is_file() else None
        if existing_packet is not None:
            if existing_packet.get("commentary_prompt_version") != PILOT_PROMPT_VERSION:
                raise RuntimeError(f"existing v1.3 packet was changed: {packet_path}")
            system_prompt = existing_packet["system_prompt"]
            user_prompt = existing_packet["user_prompt"]
        else:
            system_prompt = CHAPTER_COMMENTARY_SYSTEM_PROMPT
            user_prompt = build_user_prompt(
                reference,
                book,
                chapter,
                canonical_text,
                synthesis,
                bundle,
                synthesis.evidence_availability,
            )
        packet = {
            "artifact_version": "commentary-v1.3-generation-packet-v1",
            "pilot_version": PILOT_VERSION,
            "reference": reference,
            "literary_category": category,
            "selection_rationale": rationale,
            "renderer_requirement": "APPROVED_RENDERER_REQUIRED",
            "execution_path": "external_or_conversational",
            "expected_external_response_path": expected_response.relative_to(ROOT).as_posix(),
            "candidate_only": True,
            "commentary_prompt_version": PILOT_PROMPT_VERSION,
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
            "refined_core_count": len(core_clusters),
            "synthesis_density_bucket": density_bucket(len(synthesis.synthesis_units)),
            "gate_v2": {
                "status": "CANDIDATE_ONLY",
                "activated_globally": False,
                "version": PILOT_GATE_VERSION,
                "core_classifier": CORE_CLASSIFIER_V2,
                "evaluation_deferred_until": "EXTERNAL_PROSE_IMPORTED",
            },
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
        packet["packet_id"] = calculate_packet_id(packet)
        if existing_packet is not None:
            packet["artifact_version"] = existing_packet["artifact_version"]
        _write_json(packet_path, packet)
        synthesis_path = save_synthesis(synthesis, SYNTHESIS_ROOT)
        rows.append(
            {
                "reference": reference,
                "book": book,
                "chapter": chapter,
                "literary_category": category,
                "selection_rationale": rationale,
                "evidence_availability": synthesis.evidence_availability,
                "evidence_count": len(bundle.evidence_items),
                "evidence_hash": bundle.evidence_hash,
                "evidence_locked": True,
                "synthesis_hash": synthesis.synthesis_hash,
                "synthesis_validated": True,
                "raw_synthesis_unit_count": len(synthesis.synthesis_units),
                "idea_cluster_count": len(clusters),
                "refined_core_count": len(core_clusters),
                "synthesis_density_bucket": density_bucket(len(synthesis.synthesis_units)),
                "packet_id": packet["packet_id"],
                "packet_path": packet_path.relative_to(ROOT).as_posix(),
                "synthesis_path": synthesis_path.relative_to(ROOT).as_posix(),
                "expected_external_response_path": expected_response.relative_to(ROOT).as_posix(),
                "gate_v2_inputs": {
                    "status": "CANDIDATE_ONLY",
                    "synthesis_unit_ids": [unit.id for unit in synthesis.synthesis_units],
                    "idea_cluster_ids": [cluster.id for cluster in clusters],
                    "core_cluster_ids": [cluster.id for cluster in core_clusters],
                    "core_classifier": CORE_CLASSIFIER_V2,
                },
                "status": "READY_FOR_EXTERNAL_RENDERER",
            }
        )

    v11_after = protected_v11_errors()
    ckl_after = ckl_snapshot()
    if v11_after:
        raise RuntimeError("protected Commentary v1.1 fingerprints changed during preparation")
    if ckl_before != ckl_after:
        raise RuntimeError("CKL fingerprint changed during preparation")

    manifest = {
        "artifact_version": "commentary-v1.3-pilot-manifest-v1",
        "pilot_version": PILOT_VERSION,
        "status": "PILOT_PACKETS_READY",
        "candidate_only": True,
        "chapter_count": len(rows),
        "commentary_prompt_version": PILOT_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "stratification_summary": {
            "literary_category_distribution": dict(sorted(Counter(row["literary_category"] for row in rows).items())),
            "availability_distribution": dict(sorted(Counter(row["evidence_availability"] for row in rows).items())),
            "density_distribution": dict(sorted(Counter(row["synthesis_density_bucket"] for row in rows).items())),
        },
        "gate_v2": {
            "status": "CANDIDATE_ONLY",
            "activated_globally": False,
            "version": PILOT_GATE_VERSION,
            "evaluation_boundary": "BHF deterministic packet -> external prose -> BHF importer -> validator -> Gate v2",
        },
        "external_renderer_boundary": {
            "status": "NOT_INVOKED",
            "renderer_invoked": False,
            "fallback_provider_used": False,
            "response_root": RESPONSE_ROOT.relative_to(ROOT).as_posix(),
        },
        "integrity": {
            "v1_1_protected_fingerprints_unchanged": not v11_before and not v11_after,
            "ckl_unchanged": ckl_before == ckl_after,
            "evidence_and_synthesis_validated": True,
            "evidence_locked": True,
            "synthesis_locked": True,
            "packets_reproducible": True,
            "existing_canary_or_raw_artifacts_overwritten": False,
            "ckl_snapshot": ckl_after,
        },
        "genesis_1_3": {
            "status": "RENDER_PENDING",
            "manifest_path": GENESIS_MANIFEST_PATH.relative_to(ROOT).as_posix(),
            "renderer_invoked_by_pilot": False,
            "preserved": True,
        },
        "bulk_authorization": {
            "full_bible_generation_authorized": False,
            "commentary_1_3_promoted": False,
            "gate_v2_activated": False,
        },
        "chapters": rows,
    }
    _write_json(MANIFEST_PATH, manifest)
    return manifest


def validate_selection() -> None:
    if len(PILOT_SELECTION) != 30:
        raise RuntimeError("pilot selection must contain exactly 30 chapters")
    references = [f"{book} {chapter}" for book, chapter, _, _ in PILOT_SELECTION]
    if len(set(references)) != len(references):
        raise RuntimeError("pilot selection contains duplicate references")
    excluded = set(references).intersection(ORIGINAL_CANARIES)
    if excluded:
        raise RuntimeError("pilot selection includes original canaries: " + ", ".join(sorted(excluded)))
    categories = Counter(category for _, _, category, _ in PILOT_SELECTION)
    if dict(categories) != EXPECTED_CATEGORY_COUNTS:
        raise RuntimeError(f"unexpected literary category counts: {dict(categories)}")


def protected_v11_errors() -> list[str]:
    state = _read_json(V11_STATE_PATH)
    errors = []
    for relative_path, expected in state.get("protected_fingerprints", {}).items():
        path = ROOT / relative_path
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            errors.append(relative_path)
    return errors


def ckl_snapshot() -> dict[str, Any]:
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
    inventory_value = inventory() if callable(inventory) else None
    return {
        "json_object_count": len(paths),
        "json_objects_digest": digest.hexdigest(),
        "inventory_fingerprint": inventory_value,
    }


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


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
    parser.add_argument("command", choices=("prepare", "validate-selection"))
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-selection":
            validate_selection()
            result = {"status": "VALID", "chapter_count": len(PILOT_SELECTION)}
        else:
            manifest = prepare()
            result = {
                "status": manifest["status"],
                "chapter_count": manifest["chapter_count"],
                "manifest_path": MANIFEST_PATH.relative_to(ROOT).as_posix(),
                "renderer_invoked": manifest["external_renderer_boundary"]["renderer_invoked"],
            }
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
