#!/usr/bin/env python3
"""Prepare the fresh, candidate-only Commentary 1.5 scale pilot.

The selector is deterministic: it derives metadata from the current local
EvidenceBundle and synthesis compiler, excludes all prior v1.2-v1.5
experimental references, then uses a fixed seed to optimize the requested
strata while preserving the category quotas.  No renderer is invoked here.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.prompts import CHAPTER_COMMENTARY_SYSTEM_PROMPT, build_user_prompt
from bhf_agent.chapter_commentary.richness_clusters import CORE_CLASSIFIER_V2, cluster_synthesis_units
from bhf_agent.chapter_commentary.synthesis import compile_chapter_synthesis, validate_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from tools.commentary_v13_pilot import density_bucket
from tools.commentary_v14_calibration import _ckl_snapshot, _protected_v11_errors


TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot"
SEED = 20260908
TARGET_COUNT = 60
AVAILABILITY_TARGET = {"AVAILABLE": 40, "THIN": 12, "DATA_GAP": 8}
DENSITY_TARGET = {"0": 8, "1-5": 12, "6-10": 10, "11-20": 10, "21-40": 10, "41+": 10}
CATEGORY_TARGET = {
    "Pentateuch": 8,
    "Historical narrative": 9,
    "Poetry/Wisdom": 7,
    "Prophets": 10,
    "Gospels/Acts": 8,
    "Epistles": 10,
    "Apocalyptic / highly symbolic": 2,
    "Genealogy/list/administrative": 6,
}
WAVES = ("A", "B", "C")

# These are the same broad pilot categories used by the earlier stratified
# pilot.  The explicit administrative overrides keep list/genealogy material
# in its own stratum instead of absorbing it into the book-level genre.
ADMINISTRATIVE_OVERRIDES = {
    ("Numbers", chapter) for chapter in (1, 2, 3, 7, 26, 31, 33, 36)
} | {
    ("1 Chronicles", chapter) for chapter in (1, 8, 9, 23, 24, 25, 26, 27, 28, 29)
} | {
    ("2 Chronicles", chapter) for chapter in (2, 8, 9, 29, 30, 31)
} | {
    ("Ezra", chapter) for chapter in (2, 3, 7, 8, 10)
} | {
    ("Nehemiah", chapter) for chapter in (3, 7, 10, 11, 12, 13)
}

EXPERIMENT_PREFIXES = (
    "commentary-v1.2",
    "commentary-v1.3",
    "commentary-v1.4",
    "commentary-v1.5",
)
REFERENCE_RE = re.compile(r"^(?P<book>(?:[123] )?[A-Za-z ]+) (?P<chapter>[1-9][0-9]*)$")


def _slug(book: str) -> str:
    return book.lower().replace(" ", "_")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _all_references() -> list[str]:
    return [
        f"{book['name']} {int(chapter['chapter'])}"
        for book in bible.load_asv_bible()["books"]
        for chapter in book.get("chapters", [])
    ]


def _references_in_value(value: Any, known: set[str], found: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "reference" and isinstance(child, str) and child in known:
                found.add(child)
            _references_in_value(child, known, found)
    elif isinstance(value, list):
        for child in value:
            _references_in_value(child, known, found)


def prior_experimental_references(known: set[str]) -> set[str]:
    found: set[str] = set()
    candidates_root = ROOT / ".bhf-data/bhf-commentary-candidates"
    for directory in sorted(candidates_root.iterdir()):
        if directory.name == TARGET_ROOT.name:
            continue
        if not directory.is_dir() or not directory.name.startswith(EXPERIMENT_PREFIXES):
            continue
        for path in sorted(directory.rglob("*.json")):
            relative_parts = path.relative_to(directory).parts
            # Evaluation/audit reports may summarize the production corpus;
            # they do not make those chapters experimental.  Only artifacts
            # that identify an experiment's manifest, locked packet, synthesis,
            # or rendered response contribute to the exclusion set.
            is_experimental_artifact = (
                "manifest" in path.name
                or any(part in {"packets", "prompts", "synthesis", "responses", "manual-render"} for part in relative_parts)
            )
            if not is_experimental_artifact:
                continue
            try:
                _references_in_value(_read(path), known, found)
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            match = REFERENCE_RE.match(path.stem.replace("_", " "))
            if match:
                candidate = f"{match.group('book')} {match.group('chapter')}"
                if candidate in known:
                    found.add(candidate)
    return found


def literary_category(book: str, chapter: int) -> str:
    if (book, chapter) in ADMINISTRATIVE_OVERRIDES:
        return "Genealogy/list/administrative"
    if book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"}:
        return "Pentateuch"
    if book in {"Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther"}:
        return "Historical narrative"
    if book in {"Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon"}:
        return "Poetry/Wisdom"
    if book in {"Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"}:
        return "Prophets"
    if book in {"Matthew", "Mark", "Luke", "John", "Acts"}:
        return "Gospels/Acts"
    if book == "Revelation":
        return "Apocalyptic / highly symbolic"
    return "Epistles"


def _metadata(reference: str) -> dict[str, Any]:
    book, chapter_text = reference.rsplit(" ", 1)
    chapter = int(chapter_text)
    bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    if bundle is None:
        raise RuntimeError(f"unable to build EvidenceBundle for {reference}")
    synthesis = compile_chapter_synthesis(bundle, book=book, chapter=chapter)
    errors = validate_synthesis(synthesis, bundle)
    if errors:
        raise RuntimeError(f"invalid synthesis for {reference}: {'; '.join(errors)}")
    clusters = cluster_synthesis_units(synthesis.synthesis_units, bundle.evidence_items, core_classifier=CORE_CLASSIFIER_V2)
    category = literary_category(book, chapter)
    kinds = sorted({unit.kind for unit in synthesis.synthesis_units})
    evidence_categories = sorted({item.category for item in bundle.evidence_items})
    return {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "literary_category": category,
        "evidence_availability": synthesis.evidence_availability,
        "evidence_count": len(bundle.evidence_items),
        "evidence_hash": bundle.evidence_hash,
        "synthesis_hash": synthesis.synthesis_hash,
            "synthesis_schema_version": synthesis.synthesis_schema_version,
            "synthesis_compiler_version": synthesis.synthesis_compiler_version,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "gate_version": "commentary-richness-gate-v2.1",
            "synthesis_unit_count": len(synthesis.synthesis_units),
        "density_bucket": density_bucket(len(synthesis.synthesis_units)),
        "meaningful_idea_cluster_count": len(clusters),
        "refined_core_count": sum(cluster.quality_class == "CORE" for cluster in clusters),
        "stress_surfaces": sorted(set(kinds + evidence_categories)),
        "_bundle": bundle,
        "_synthesis": synthesis,
    }


def _public_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _hash_order(reference: str) -> str:
    return hashlib.sha256(f"{SEED}:{reference}".encode()).hexdigest()


def _objective(rows: list[dict[str, Any]]) -> int:
    availability = Counter(row["evidence_availability"] for row in rows)
    density = Counter(row["density_bucket"] for row in rows)
    return (
        sum(8 * (availability[key] - target) ** 2 for key, target in AVAILABILITY_TARGET.items())
        + sum(5 * (density[key] - target) ** 2 for key, target in DENSITY_TARGET.items())
        + 2 * sum(row["density_bucket"] in {"21-40", "41+"} and row["evidence_availability"] == "AVAILABLE" for row in rows) * -1
    )


def select(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[row["literary_category"]].append(row)
    for category, target in CATEGORY_TARGET.items():
        if len(by_category[category]) < target:
            raise RuntimeError(f"category {category} has only {len(by_category[category])} eligible chapters; need {target}")

    rng = random.Random(SEED)
    best: list[dict[str, Any]] | None = None
    best_score: int | None = None
    categories = list(CATEGORY_TARGET)
    for restart in range(32):
        chosen: list[dict[str, Any]] = []
        for category in categories:
            pool = sorted(by_category[category], key=lambda row: row["reference"])
            rng.shuffle(pool)
            chosen.extend(pool[:CATEGORY_TARGET[category]])
        current_score = _objective(chosen)
        for _ in range(12000):
            category = rng.choice(categories)
            category_rows = [row for row in chosen if row["literary_category"] == category]
            selected_refs = {row["reference"] for row in chosen}
            replacement_pool = [row for row in by_category[category] if row["reference"] not in selected_refs]
            if not replacement_pool:
                continue
            outgoing = rng.choice(category_rows)
            incoming = rng.choice(replacement_pool)
            candidate = [incoming if row["reference"] == outgoing["reference"] else row for row in chosen]
            score = _objective(candidate)
            if score <= current_score:
                chosen, current_score = candidate, score
        if best_score is None or current_score < best_score or (current_score == best_score and sorted(row["reference"] for row in chosen) < sorted(row["reference"] for row in best or [])):
            best, best_score = chosen, current_score
    assert best is not None and best_score is not None
    selected = sorted(best, key=lambda row: _hash_order(row["reference"]))
    for index, row in enumerate(selected):
        row["wave"] = WAVES[index % len(WAVES)]
    summary = {
        "seed": SEED,
        "ordering": "sha256(seed:reference), ascending; wave assignment is round-robin A/B/C after this ordering",
        "objective_score": best_score,
        "target_count": TARGET_COUNT,
        "actual_count": len(selected),
        "availability_distribution": dict(sorted(Counter(row["evidence_availability"] for row in selected).items())),
        "density_distribution": {bucket: sum(row["density_bucket"] == bucket for row in selected) for bucket in DENSITY_TARGET},
        "literary_category_distribution": {category: sum(row["literary_category"] == category for row in selected) for category in CATEGORY_TARGET},
        "wave_distribution": {wave: sum(row["wave"] == wave for row in selected) for wave in WAVES},
    }
    return selected, summary


def _packet(row: dict[str, Any]) -> dict[str, Any]:
    bundle = row["_bundle"]
    synthesis = row["_synthesis"]
    reference = row["reference"]
    canonical_text = bible.passage_text(bible.resolve_chapter(row["book"], row["chapter"])["verses"])
    packet = {
        "artifact_version": "commentary-v1.5-scale-pilot-packet-v1",
        "pilot_version": "commentary-v1.5-stratified-scale-pilot-v1",
        "reference": reference,
        "book": row["book"],
        "chapter": row["chapter"],
        "literary_category": row["literary_category"],
        "selection_seed": SEED,
        "selection_order": _hash_order(reference),
        "selection_rationale": "fresh deterministic scale sample covering current evidence, synthesis density, and library-derived literary strata; stress surfaces: " + ", ".join(row["stress_surfaces"]),
        "renderer_requirement": "CURRENT_CODEX_CONVERSATIONAL_RENDERER",
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
        "density_bucket": density_bucket(len(synthesis.synthesis_units)),
        "idea_cluster_count": row["meaningful_idea_cluster_count"],
        "refined_core_count": row["refined_core_count"],
        "gate_v2": {"status": "CANDIDATE_ONLY", "activated_globally": False, "version": "commentary-richness-gate-v2.1", "core_classifier": CORE_CLASSIFIER_V2, "evaluation_deferred_until": "CONVERSATIONAL_PROSE_IMPORTED"},
        "system_prompt": CHAPTER_COMMENTARY_SYSTEM_PROMPT,
        "user_prompt": build_user_prompt(reference, row["book"], row["chapter"], canonical_text, synthesis, bundle, synthesis.evidence_availability),
    }
    identity = {key: value for key, value in packet.items() if key != "packet_id"}
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    packet["packet_id"] = f"commentary-v1.5-packet:{hashlib.sha256(encoded.encode()).hexdigest()}"
    return packet


def prepare() -> dict[str, Any]:
    if COMMENTARY_PROMPT_VERSION != "1.5" or COMMENTARY_SCHEMA_VERSION != "1.2":
        raise RuntimeError("frozen Commentary 1.5/schema 1.2 contract is not active")
    before_v11 = _protected_v11_errors()
    if before_v11:
        raise RuntimeError("protected v1.1 fingerprints changed")
    before_ckl = _ckl_snapshot()
    known = set(_all_references())
    excluded = prior_experimental_references(known)
    eligible = sorted(known - excluded)
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    checkpoint_path = TARGET_ROOT / "selection-metadata-checkpoint.json"
    checkpoint = _read(checkpoint_path) if checkpoint_path.is_file() else None
    metadata: list[dict[str, Any]] = []
    if checkpoint and checkpoint.get("seed") == SEED and checkpoint.get("eligible_references") == eligible:
        metadata = list(checkpoint.get("candidate_metadata", []))
        print(f"Resuming metadata checkpoint: {len(metadata)}/{len(eligible)}", flush=True)
    if len(metadata) != len(eligible):
        completed = {row["reference"] for row in metadata}
        for index, reference in enumerate(eligible, start=1):
            if reference in completed:
                continue
            metadata.append(_public_metadata(_metadata(reference)))
            metadata.sort(key=lambda row: eligible.index(row["reference"]))
            if index % 25 == 0 or index == len(eligible):
                _write(checkpoint_path, {"artifact_version": "commentary-v1.5-scale-metadata-checkpoint-v1", "seed": SEED, "eligible_references": eligible, "completed_count": len(metadata), "candidate_metadata": metadata})
                print(f"Metadata checkpoint: {len(metadata)}/{len(eligible)}", flush=True)
        if len(metadata) != len(eligible):
            raise RuntimeError("metadata checkpoint is incomplete; no scale selection is authorized")
    # Rehydrate only the selected rows after selection.  The checkpoint is a
    # resumable audit aid, while packet writing still uses the live objects
    # from the current deterministic EvidenceBundle/synthesis pass.
    selected, summary = select(metadata)
    selected_waves = {row["reference"]: row["wave"] for row in selected}
    selected = [_metadata(row["reference"]) for row in selected]
    for row in selected:
        row["wave"] = selected_waves[row["reference"]]

    for wave in WAVES:
        (TARGET_ROOT / f"wave-{wave.lower()}" / "canary/prompts").mkdir(parents=True, exist_ok=True)
        (TARGET_ROOT / f"wave-{wave.lower()}" / "canary/synthesis").mkdir(parents=True, exist_ok=True)
        (TARGET_ROOT / f"wave-{wave.lower()}" / "canary/evidence-bundles").mkdir(parents=True, exist_ok=True)
        (TARGET_ROOT / f"wave-{wave.lower()}" / "canary/responses/raw").mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for row in selected:
        packet = _packet(row)
        wave_root = TARGET_ROOT / f"wave-{row['wave'].lower()}" / "canary"
        filename = f"{_slug(row['book'])}_{row['chapter']:03d}.json"
        packet_path = wave_root / "prompts" / filename
        synthesis_path = wave_root / "synthesis" / filename
        bundle_path = wave_root / "evidence-bundles" / filename
        raw_path = wave_root / "responses/raw" / filename
        _write(packet_path, packet)
        _write(synthesis_path, row["_synthesis"].to_dict())
        _write(bundle_path, row["_bundle"].to_dict())
        manifest_rows.append({
            **{key: row[key] for key in ("reference", "book", "chapter", "literary_category", "evidence_availability", "evidence_count", "evidence_hash", "synthesis_hash", "synthesis_schema_version", "synthesis_compiler_version", "synthesis_unit_count", "density_bucket", "meaningful_idea_cluster_count", "refined_core_count", "wave")},
            "packet_id": packet["packet_id"],
            "packet_path": packet_path.relative_to(ROOT).as_posix(),
            "expected_raw_response_path": raw_path.relative_to(ROOT).as_posix(),
            "expected_response_path": raw_path.relative_to(ROOT).as_posix(),
            "synthesis_path": synthesis_path.relative_to(ROOT).as_posix(),
            "evidence_bundle_path": bundle_path.relative_to(ROOT).as_posix(),
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "gate_version": "commentary-richness-gate-v2.1",
            "status": "READY_FOR_CONVERSATIONAL_RENDER",
        })

    after_v11 = _protected_v11_errors()
    after_ckl = _ckl_snapshot()
    if after_v11 or before_ckl != after_ckl:
        raise RuntimeError("v1.1 or CKL identity changed during scale-pilot preparation")

    for wave in WAVES:
        wave_root = TARGET_ROOT / f"wave-{wave.lower()}"
        wave_rows = [row for row in manifest_rows if row["wave"] == wave]
        wave_manifest = {"artifact_version": "commentary-v1.5-scale-wave-manifest-v1", "wave": wave, "status": "READY_FOR_CONVERSATIONAL_RENDER", "chapters": wave_rows, "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"}}
        wave_preflight = {"artifact_version": "commentary-v1.5-scale-wave-preflight-v1", "wave": wave, "status": "READY_FOR_CONVERSATIONAL_RENDER", "candidate_only": True, "evidence_locked": True, "synthesis_locked": True, "v1_1_protected_fingerprints_verified": True, "ckl_unchanged": True, "chapters": wave_rows}
        _write(wave_root / "canary/canary-generation-manifest.json", wave_manifest)
        _write(wave_root / "canary/canary-preflight.json", wave_preflight)

    public_rows = [{**{key: value for key, value in row.items() if not key.startswith("_")}, "status": "READY_FOR_CONVERSATIONAL_RENDER"} for row in selected]
    artifact = {
        "artifact_version": "commentary-v1.5-scale-pilot-manifest-v1",
        "status": "READY_FOR_CONVERSATIONAL_RENDER",
        "candidate_only": True,
        "selection_method": "all canonical ASV chapters minus prior v1.2-v1.5 experimental references; metadata from current EvidenceBundle, availability classifier, synthesis compiler 1.1, cluster classifier, and fixed literary rules; seeded constrained swap optimization",
        "selection_seed": SEED,
        "prior_experimental_reference_count": len(excluded),
        "eligible_corpus_count": len(eligible),
        "target_summary": summary,
        "renderer_identity": {"renderer_label": "GPT-5 Codex", "reasoning_effort": "NOT_EXPOSED"},
        "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
        "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
        "synthesis_schema_version": "1.1",
        "synthesis_compiler_version": "1.1",
        "gate_version": "commentary-richness-gate-v2.1",
        "gate_state": "CANDIDATE_ONLY",
        "reader_synthesis_plan": "NOT IMPLEMENTED / NOT REQUIRED",
        "full_bible_generation_authorized": False,
        "chapters": public_rows,
        "integrity": {"v1_1_protected_fingerprints_verified": True, "ckl_unchanged": True, "prompt_and_gate_frozen": True},
    }
    _write(TARGET_ROOT / "scale-pilot-manifest.json", artifact)
    _write(TARGET_ROOT / "selection-candidates-summary.json", {"seed": SEED, "eligible_corpus_count": len(eligible), "excluded_references": sorted(excluded), "candidate_metadata": [_public_metadata(row) for row in metadata]})
    return artifact


if __name__ == "__main__":
    result = prepare()
    print(json.dumps({"status": result["status"], "selection": result["target_summary"], "manifest": str(TARGET_ROOT / "scale-pilot-manifest.json")}, indent=2))
