#!/usr/bin/env python3
"""Prepare, validate, and report the frozen Commentary v1.2 scale prose pilot.

The harness never changes prompt, projection, ancestry, synthesis, evidence, or
scoring behavior.  Prose is supplied once by the selected conversational
renderer in six deterministic batches and is then treated as immutable input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.prompts import build_user_prompt, system_prompt_for_version
from bhf_agent.chapter_commentary.reader_idea_ancestry_envelope import (
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
    READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
    add_ancestry_envelope_to_prompt,
    audit_ancestry_envelope,
    build_ancestry_envelope,
    response_ancestry_audit,
)
from bhf_agent.chapter_commentary.reader_level_projection import (
    READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
    READER_LEVEL_IDEA_PROJECTION_VERSION,
    add_projection_to_prompt,
    project_reader_level_ideas,
)
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    cluster_synthesis_units,
)
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    canonical_json,
    sha256_bytes,
    sha256_json,
    slug,
    write_immutable,
)
from tools import commentary_renderer_qualification as qualification
from tools import commentary_renderer_selection_breadth_diagnostic as validator


ARTIFACT_VERSION = "commentary-v1.2-scale-pilot-v1"
PROMPT_VERSION = "1.7"
RENDERER = "gpt-5.6-sol"
RENDERER_EFFORT = "medium"
SOURCE_HEAD = "07778940c159449443fd8d47ffeeca00b2732483"
SOURCE_BRANCH = "feat/commentary-v1.2-enrichment"
SELECTION_SEED = 20260909
TARGET_COUNT = 75
BATCH_SIZES = (13, 13, 13, 12, 12, 12)
ANCHORS = ("Exodus 14", "Romans 3", "1 Corinthians 14", "Revelation 20", "Revelation 21")
KNOWN_EDGE_CASES = {"Revelation 20": "KNOWN_SCORER_RENDERER_EDGE_CASE"}
SEEN_REFERENCES = frozenset(qualification.EXPECTED_REFERENCES)
FROZEN_CONTRACTS = {
    "essential_passage_context": CORE_CLASSIFIER_V2,
    "reader_relevance_eligibility": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    "richness_clusters": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    "richness_policy": RICHNESS_POLICY_VERSION_V3,
    "gate": RICHNESS_GATE_V2_VERSION,
}
STRATUM_TARGETS = {
    "Torah": 8,
    "Historical Narrative": 10,
    "Poetry/Wisdom": 8,
    "Major Prophets": 8,
    "Minor Prophets": 8,
    "Gospels": 8,
    "Acts": 4,
    "Pauline Epistles": 8,
    "General Epistles": 7,
    "Apocalyptic literature": 6,
}
DENSITY_CLASS_TARGETS = {"sparse": 18, "medium": 32, "dense": 25}
HARD_PROVENANCE_CODES = validator.HARD_PROVENANCE_CODES
INTERNAL_PROSE_TERMS = (
    "synthesis unit", "evidence id", "reader-level idea", "projection",
    "ancestry path", "cluster id", "coverage score",
)
CHECKPOINT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot/selection-metadata-checkpoint.json"


class ScalePilotError(RuntimeError):
    """Raised when a frozen pilot input or immutable output disagrees."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScalePilotError(f"invalid JSON artifact {path}: {exc}") from exc


def _write_json(path: Path, value: Any) -> str:
    return write_immutable(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_text(path: Path, value: str) -> str:
    return write_immutable(path, value.encode("utf-8"))


def _verify_identity(value: dict[str, Any], key: str, label: str) -> None:
    if value.get(key) != sha256_json({k: v for k, v in value.items() if k != key}):
        raise ScalePilotError(f"{label} identity mismatch")


def density_bucket(count: int) -> str:
    if count == 0:
        return "0"
    if count <= 5:
        return "1-5"
    if count <= 10:
        return "6-10"
    if count <= 20:
        return "11-20"
    if count <= 40:
        return "21-40"
    return "41+"


def density_class(count: int) -> str:
    if count <= 5:
        return "sparse"
    if count <= 20:
        return "medium"
    return "dense"


def literary_stratum(book: str) -> str:
    if book in {"Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"}:
        return "Torah"
    if book in {"Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther"}:
        return "Historical Narrative"
    if book in {"Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Song of Songs"}:
        return "Poetry/Wisdom"
    if book in {"Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel"}:
        return "Major Prophets"
    if book in {"Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"}:
        return "Minor Prophets"
    if book in {"Matthew", "Mark", "Luke", "John"}:
        return "Gospels"
    if book == "Acts":
        return "Acts"
    if book in {"Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon"}:
        return "Pauline Epistles"
    if book == "Revelation":
        return "Apocalyptic literature"
    return "General Epistles"


ADMINISTRATIVE = {
    *(f"Numbers {n}" for n in (1, 2, 3, 7, 26, 31, 33, 36)),
    *(f"1 Chronicles {n}" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 23, 24, 25, 26, 27)),
    *(f"Ezra {n}" for n in (2, 7, 8, 10)),
    *(f"Nehemiah {n}" for n in (3, 7, 10, 11, 12)),
    "Matthew 1", "Luke 3",
}


def _selection_metadata() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    checkpoint = _read(CHECKPOINT)
    rows = list(checkpoint.get("candidate_metadata", []))
    if checkpoint.get("completed_count") != len(rows):
        raise ScalePilotError("selection metadata checkpoint is incomplete")
    by_ref = {row["reference"]: dict(row) for row in rows}
    for reference in ANCHORS:
        if reference not in by_ref:
            book, chapter_text = reference.rsplit(" ", 1)
            prepared = prepare_chapter(book, int(chapter_text))
            clusters = _clusters(prepared)
            by_ref[reference] = {
                "reference": reference, "book": book, "chapter": int(chapter_text),
                "evidence_availability": prepared.synthesis.evidence_availability,
                "evidence_count": len(prepared.bundle.evidence_items),
                "evidence_hash": prepared.bundle.evidence_hash,
                "synthesis_hash": prepared.synthesis.synthesis_hash,
                "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
                "density_bucket": density_bucket(len(prepared.synthesis.synthesis_units)),
                "meaningful_idea_cluster_count": sum(c.coverage_eligibility in {"REQUIRED", "RELEVANT"} for c in clusters),
            }
    canonical = {
        f"{book['name']} {int(chapter['chapter'])}"
        for book in bible.load_asv_bible()["books"] for chapter in book.get("chapters", [])
    }
    data_gaps = sorted(
        ({row["reference"] for row in by_ref.values() if row.get("evidence_availability") == "DATA_GAP"})
        | set(qualification.EXCLUDED_DATA_GAP_REFERENCES)
    )
    exclusions = [{"reference": ref, "reason": "true DATA_GAP under existing production rules"} for ref in data_gaps]
    available = []
    for row in by_ref.values():
        if row["reference"] not in canonical or row.get("evidence_availability") == "DATA_GAP":
            continue
        row["literary_stratum"] = literary_stratum(row["book"])
        row["density_class"] = density_class(int(row["synthesis_unit_count"]))
        row["content_shape"] = "genealogy/list/administrative" if row["reference"] in ADMINISTRATIVE else "ordinary"
        row["seen_status"] = "seen" if row["reference"] in SEEN_REFERENCES else "unseen"
        available.append(row)
    return sorted(available, key=lambda row: row["reference"]), exclusions


def _hash_order(reference: str) -> str:
    return hashlib.sha256(f"{SELECTION_SEED}:{reference}".encode()).hexdigest()


def select_corpus(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select fixed genre quotas, anchors, density spread, and list material."""
    by_ref = {row["reference"]: row for row in rows}
    missing = set(ANCHORS) - set(by_ref)
    if missing:
        raise ScalePilotError(f"anchor chapters unavailable: {sorted(missing)}")
    selected = [by_ref[ref] for ref in ANCHORS]
    selected_refs = set(ANCHORS)
    remaining_targets = Counter(STRATUM_TARGETS)
    for row in selected:
        remaining_targets[row["literary_stratum"]] -= 1
    remaining_density = Counter(DENSITY_CLASS_TARGETS)
    for row in selected:
        remaining_density[row["density_class"]] -= 1
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["reference"] in selected_refs or row["reference"] in SEEN_REFERENCES:
            continue
        pools[row["literary_stratum"]].append(row)
    for values in pools.values():
        values.sort(key=lambda row: _hash_order(row["reference"]))
    # Greedy deficit selection is deterministic and favors the requested
    # density spread plus a bounded administrative/list representation.
    admin_needed = 5
    for stratum in STRATUM_TARGETS:
        for _ in range(remaining_targets[stratum]):
            candidates = [row for row in pools[stratum] if row["reference"] not in selected_refs]
            if not candidates:
                raise ScalePilotError(f"insufficient eligible unseen chapters in {stratum}")
            candidates.sort(key=lambda row: (
                -(1 if remaining_density[row["density_class"]] > 0 else 0),
                -(1 if admin_needed > 0 and row["content_shape"] == "genealogy/list/administrative" else 0),
                -remaining_density[row["density_class"]],
                _hash_order(row["reference"]),
            ))
            chosen = candidates[0]
            selected.append(chosen)
            selected_refs.add(chosen["reference"])
            remaining_density[chosen["density_class"]] -= 1
            if chosen["content_shape"] == "genealogy/list/administrative":
                admin_needed -= 1
    if len(selected) != TARGET_COUNT:
        raise ScalePilotError(f"selection produced {len(selected)} chapters, expected {TARGET_COUNT}")
    ordered = sorted(selected, key=lambda row: _hash_order(row["reference"]))
    cursor = 0
    for batch, size in enumerate(BATCH_SIZES, 1):
        for row in ordered[cursor:cursor + size]:
            row["batch"] = batch
        cursor += size
    return ordered


def _clusters(prepared: Any) -> list[Any]:
    chapter = bible.resolve_chapter(prepared.synthesis.book, prepared.synthesis.chapter)
    return cluster_synthesis_units(
        prepared.synthesis.synthesis_units,
        prepared.bundle.evidence_items,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=bible.passage_text(chapter["verses"]),
    )


def build_context(repo_root: Path = ROOT) -> dict[str, Any]:
    metadata, exclusions = _selection_metadata()
    selected = select_corpus(metadata)
    system_prompt = system_prompt_for_version(PROMPT_VERSION)
    chapters = []
    for ordinal, selection in enumerate(selected, 1):
        prepared = prepare_chapter(selection["book"], int(selection["chapter"]))
        if prepared.synthesis.evidence_availability == "DATA_GAP":
            raise ScalePilotError(f"selected ineligible DATA_GAP chapter: {selection['reference']}")
        if prepared.synthesis.synthesis_hash != selection["synthesis_hash"] or prepared.bundle.evidence_hash != selection["evidence_hash"]:
            raise ScalePilotError(f"source identity changed for {selection['reference']}")
        projection = project_reader_level_ideas(prepared.synthesis, _clusters(prepared), prepared.bundle.evidence_items)
        envelope = build_ancestry_envelope(projection, prepared.synthesis, prepared.bundle.evidence_items)
        envelope_audit = audit_ancestry_envelope(envelope, projection, prepared.synthesis)
        if not envelope_audit["valid"]:
            raise ScalePilotError(f"ancestry envelope invalid for {selection['reference']}")
        chapter_text = bible.passage_text(bible.resolve_chapter(selection["book"], int(selection["chapter"]))["verses"])
        original = build_user_prompt(selection["reference"], selection["book"], int(selection["chapter"]), chapter_text, prepared.synthesis, prepared.bundle, prepared.synthesis.evidence_availability, prompt_version=PROMPT_VERSION)
        candidate = add_ancestry_envelope_to_prompt(add_projection_to_prompt(original, projection), envelope)
        if "1.8" in candidate or "1.8" in system_prompt:
            raise ScalePilotError("prompt 1.8 content entered the pilot")
        chapters.append({"ordinal": ordinal, "selection": selection, "prepared": prepared, "projection": projection.to_dict(), "envelope": envelope, "envelope_audit": envelope_audit, "candidate_prompt": candidate})
    contract_hashes = {
        "prompt_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/prompts.py").read_bytes()),
        "projection_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_level_projection.py").read_bytes()),
        "ancestry_envelope_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/reader_idea_ancestry_envelope.py").read_bytes()),
        "validator_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/validation.py").read_bytes()),
        "scorer_source_sha256": sha256_bytes((repo_root / "bhf_agent/chapter_commentary/richness_clusters.py").read_bytes()),
    }
    public = []
    for item in chapters:
        row, projection, envelope = item["selection"], item["projection"], item["envelope"]
        public.append({
            "ordinal": item["ordinal"], "reference": row["reference"], "book": row["book"], "chapter": row["chapter"],
            "slug": slug(row["book"], row["chapter"]), "batch": row["batch"], "literary_stratum": row["literary_stratum"],
            "density_bucket": row["density_bucket"], "density_class": row["density_class"], "content_shape": row["content_shape"],
            "seen_status": row["seen_status"], "synthesis_unit_count": len(item["prepared"].synthesis.synthesis_units),
            "eligible_cluster_count": projection["eligible_cluster_count"], "projected_idea_count": len(envelope["ideas"]),
            "ancestry_path_count": sum(len(idea["ancestry_paths"]) for idea in envelope["ideas"]),
            "evidence_availability": item["prepared"].synthesis.evidence_availability,
            "evidence_hash": item["prepared"].bundle.evidence_hash, "synthesis_hash": item["prepared"].synthesis.synthesis_hash,
            "source_packet_id": item["prepared"].row["input_identity"]["packet_id"], "source_packet_hash": item["prepared"].row["input_identity"]["packet_hash"],
            "projection_hash": projection["projection_hash"], "ancestry_envelope_hash": envelope["envelope_hash"],
            "system_prompt_sha256": sha256_bytes(system_prompt.encode()), "candidate_input_sha256": sha256_bytes(item["candidate_prompt"].encode()),
            "response_filename": f"{item['ordinal']:03d}_{slug(row['book'], row['chapter'])}.json",
        })
    seed = sha256_json({"artifact_version": ARTIFACT_VERSION, "source_head": SOURCE_HEAD, "selection_seed": SELECTION_SEED, "chapters": public, "renderer": RENDERER, "effort": RENDERER_EFFORT, "contracts": FROZEN_CONTRACTS, "contract_hashes": contract_hashes})
    namespace = f".bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-{seed[:20]}"
    manifest = {
        "artifact_version": f"{ARTIFACT_VERSION}-manifest", "namespace": namespace, "immutable_id": seed[:20],
        "source_head": SOURCE_HEAD, "source_branch": SOURCE_BRANCH, "selection_seed": SELECTION_SEED,
        "selection_method": "fixed genre quotas; five frozen controls; all other selections unseen; deterministic SHA-256 ordering with density-deficit and administrative-shape preference",
        "chapter_count": TARGET_COUNT, "batch_sizes": list(BATCH_SIZES), "renderer": RENDERER, "renderer_effort": RENDERER_EFFORT,
        "runtime_self_attestation": False, "one_generation_per_chapter": True, "retries": 0,
        "prompt_version": PROMPT_VERSION, "projection_version": READER_LEVEL_IDEA_PROJECTION_VERSION,
        "projection_implementation_identity": READER_LEVEL_IDEA_PROJECTION_IMPLEMENTATION,
        "ancestry_envelope_version": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION,
        "ancestry_envelope_implementation_identity": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_IMPLEMENTATION,
        "frozen_scoring_contracts": FROZEN_CONTRACTS, "contract_hashes": contract_hashes,
        "seen_definition": "frozen 21-chapter GPT-5.6 Sol renderer qualification corpus",
        "seen_count": sum(row["seen_status"] == "seen" for row in public),
        "unseen_count": sum(row["seen_status"] == "unseen" for row in public),
        "unseen_percentage": round(100 * sum(row["seen_status"] == "unseen" for row in public) / TARGET_COUNT, 2),
        "stratum_targets": STRATUM_TARGETS, "density_class_targets": DENSITY_CLASS_TARGETS,
        "known_edge_cases": KNOWN_EDGE_CASES, "chapters": public,
    }
    manifest["manifest_identity"] = sha256_json(manifest)
    return {"manifest": manifest, "chapters": chapters, "root": repo_root / namespace, "system_prompt": system_prompt, "exclusions": exclusions}


def prepare(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    _write_json(root / "manifest.json", manifest)
    _write_json(root / "frozen-corpus.json", {"artifact_version": f"{ARTIFACT_VERSION}-corpus", "selection_seed": SELECTION_SEED, "order_frozen": True, "chapters": [{k: row[k] for k in ("ordinal", "reference", "batch", "seen_status", "literary_stratum", "density_bucket", "density_class", "content_shape")} for row in manifest["chapters"]]})
    _write_json(root / "exclusions.json", {"artifact_version": f"{ARTIFACT_VERSION}-exclusions", "scope": "production-rule exclusions considered before sample selection", "exclusions": context["exclusions"], "exclusion_count": len(context["exclusions"])})
    _write_json(root / "contract-identities.json", {"artifact_version": f"{ARTIFACT_VERSION}-contracts", "prompt": PROMPT_VERSION, "projection": READER_LEVEL_IDEA_PROJECTION_VERSION, "ancestry_envelope": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION, "scoring": FROZEN_CONTRACTS, "source_hashes": manifest["contract_hashes"]})
    for item, public in zip(context["chapters"], manifest["chapters"], strict=True):
        batch_root = root / f"batch-{public['batch']:03d}"
        stem = f"{public['ordinal']:03d}_{public['slug']}"
        _write_json(root / "projections" / f"{public['slug']}.json", item["projection"])
        _write_json(root / "ancestry-envelopes" / f"{public['slug']}.json", item["envelope"])
        _write_json(root / "ancestry-envelope-audits" / f"{public['slug']}.json", item["envelope_audit"])
        _write_text(batch_root / "renderer-input" / stem / "system_prompt.txt", context["system_prompt"])
        _write_text(batch_root / "renderer-input" / stem / "user_prompt.txt", item["candidate_prompt"])
        _write_json(batch_root / "renderer-input" / stem / "metadata.json", {"artifact_version": f"{ARTIFACT_VERSION}-renderer-input", **public, "renderer": RENDERER, "renderer_effort": RENDERER_EFFORT, "generation_count": 0, "response_path": str((batch_root / "responses/raw" / public["response_filename"]).relative_to(repo_root))})
    for batch in range(1, len(BATCH_SIZES) + 1):
        rows = [row for row in manifest["chapters"] if row["batch"] == batch]
        _write_json(root / f"batch-{batch:03d}" / "batch-manifest.json", {"artifact_version": f"{ARTIFACT_VERSION}-batch-manifest", "batch": batch, "status": "READY_FOR_ONE_GENERATION_EACH", "contract_manifest_identity": manifest["manifest_identity"], "chapters": rows})
    return {"status": "PREPARED", "namespace": manifest["namespace"], "chapter_count": TARGET_COUNT, "batch_count": len(BATCH_SIZES), "seen_count": manifest["seen_count"], "unseen_percentage": manifest["unseen_percentage"]}


def _prose(payload: dict[str, Any]) -> str:
    return " ".join(str(block.get("text", "")) for section in payload.get("sections", []) for block in section.get("blocks", []))


def _representation(envelope: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    consumed = {str(value) for section in payload.get("sections", []) for block in section.get("blocks", []) for value in block.get("synthesis_ids", [])}
    represented = []
    absent = []
    for idea in envelope["ideas"]:
        target = {path["synthesis_id"] for path in idea["ancestry_paths"]}
        (represented if consumed.intersection(target) else absent).append(idea["idea_id"])
    return {"projected_idea_count": len(envelope["ideas"]), "represented_count": len(represented), "represented_idea_ids": represented, "absent_idea_ids": absent}


def _qualitative(payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    prose = _prose(payload)
    leaked = [term for term in INTERNAL_PROSE_TERMS if term in prose.casefold()]
    sentences = [part.strip().casefold() for part in re.split(r"[.!?]+", prose) if part.strip()]
    repeated = len(sentences) != len(set(sentences))
    readable = result.get("structural_result") == "ACCEPTED" and bool(prose.strip()) and not leaked
    return {
        "natural_english": "PASS" if readable else "FAIL", "coherence": "PASS" if readable else "FAIL",
        "readability": "PASS" if readable else "FAIL", "evidence_dump_feel": "FAIL" if result.get("dump_severity") == "HIGH" else "PASS",
        "checklist_behavior": "FAIL" if leaked or repeated else "PASS", "awkward_ancestry_phrasing": "FAIL" if leaked else "PASS",
        "unnecessary_verbosity": "FAIL" if result.get("dump_severity") == "HIGH" else "PASS",
        "under_explanation": "FAIL" if result.get("quality_gate_outcome") != "PASS" else "PASS",
        "normal_reader_usefulness": "PASS" if readable and result.get("quality_gate_outcome") == "PASS" else "REVIEW",
        "internal_terms_found": leaked, "repeated_sentence": repeated,
    }


def _classification(row: dict[str, Any]) -> str:
    if row["structural_validity"] is False:
        return "STRUCTURAL_FAILURE"
    if row["hard_provenance_errors"] or row["ancestry_mismatch_count"]:
        return "PROVENANCE_FAILURE"
    if row["dump_severity"] == "HIGH":
        return "DUMP_FAILURE"
    if row["readability_result"] != "PASS" or row["checklist_behavior"] != "PASS":
        return "READABILITY_REGRESSION"
    if (row["core_coverage"] or 0) < 1.0:
        return "CORE_OMISSION"
    if (row["category_coverage"] or 0) < 1.0:
        return "CATEGORY_SHORTFALL"
    if row["reference"] == "Revelation 20" and row["gate_result"] == "PASS" and row["projected_concepts_represented"] == row["projected_idea_count"] and (row["weighted_coverage"] or 0) < 0.75:
        return "SCORER_RENDERER_EDGE_CASE"
    if row["gate_result"] != "PASS" or (row["weighted_coverage"] or 0) < 0.75 or (row["eligible_idea_utilization"] or 0) < 0.70:
        return "RICHNESS_SHORTFALL"
    return "CLEAN_PASS"


def validate_batch(batch: int, *, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    stored = _read(root / "manifest.json")
    _verify_identity(stored, "manifest_identity", "scale pilot manifest")
    if stored != manifest:
        raise ScalePilotError("frozen scale-pilot inputs changed")
    results = []
    by_ref = {item["selection"]["reference"]: item for item in context["chapters"]}
    for public in [row for row in manifest["chapters"] if row["batch"] == batch]:
        item = by_ref[public["reference"]]
        raw_path = root / f"batch-{batch:03d}" / "responses/raw" / public["response_filename"]
        if not raw_path.is_file():
            raise ScalePilotError(f"response missing: {raw_path}")
        raw = raw_path.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        result, parsed = validator._evaluate_one({"reference": public["reference"], "book": public["book"], "chapter": public["chapter"], "packet_id": public["source_packet_id"], "packet_hash": public["source_packet_hash"]}, raw, item["prepared"])
        hard = [code for code in result.get("rejection_codes", []) if code in HARD_PROVENANCE_CODES]
        ancestry = response_ancestry_audit(payload, item["envelope"])
        represented = _representation(item["envelope"], payload)
        qualitative = _qualitative(payload, result)
        row = {
            **{key: public[key] for key in ("reference", "seen_status", "literary_stratum", "density_bucket", "density_class", "content_shape", "synthesis_unit_count", "eligible_cluster_count", "projected_idea_count", "ancestry_path_count")},
            "structural_validity": result.get("structural_result") == "ACCEPTED", "structural_status": result.get("structural_result"),
            "hard_provenance_errors": hard, "ancestry_mismatch_count": ancestry["ancestry_mismatch_count"],
            "weighted_coverage": result.get("weighted_coverage"), "core_coverage": result.get("core_coverage"),
            "eligible_idea_utilization": result.get("eligible_idea_utilization"), "category_coverage": result.get("category_coverage"),
            "dump_severity": result.get("dump_severity"), "gate_result": result.get("quality_gate_outcome"),
            "prose_word_count": len(_prose(payload).split()), "projected_concepts_represented": represented["represented_count"],
            "projected_concept_representation": represented, "readability_result": qualitative["readability"],
            "checklist_behavior": qualitative["checklist_behavior"], "qualitative_review": qualitative,
            "response_sha256": sha256_bytes(raw), "rejection_codes": result.get("rejection_codes", []), "ancestry_validation": ancestry,
        }
        row["final_chapter_classification"] = _classification(row)
        results.append(row)
        out = root / f"batch-{batch:03d}"
        _write_json(out / "parsed" / public["response_filename"], {"artifact_version": f"{ARTIFACT_VERSION}-parsed", "response_sha256": row["response_sha256"], **parsed})
        _write_json(out / "validation" / public["response_filename"], row)
    catastrophic = (
        sum(not row["structural_validity"] for row in results) >= math.ceil(len(results) / 3)
        or sum(bool(row["hard_provenance_errors"] or row["ancestry_mismatch_count"]) for row in results) >= math.ceil(len(results) / 3)
    )
    report = {"artifact_version": f"{ARTIFACT_VERSION}-batch-validation", "batch": batch, "chapter_count": len(results), "catastrophic_stop": catastrophic, "classification_distribution": dict(sorted(Counter(row["final_chapter_classification"] for row in results).items())), "chapters": results}
    _write_json(root / f"batch-{batch:03d}" / "batch-validation.json", report)
    return report


def _percentile(values: Iterable[float], percentile: int) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile / 100
    lower, upper = math.floor(position), math.ceil(position)
    value = ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(value, 4)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    weighted = [row["weighted_coverage"] or 0.0 for row in rows]
    eligible = [row["eligible_idea_utilization"] or 0.0 for row in rows]
    rate = lambda predicate: round(100 * sum(predicate(row) for row in rows) / total, 2) if total else 0.0
    return {
        "chapter_count": total, "structurally_valid_percentage": rate(lambda r: r["structural_validity"]),
        "provenance_safe_percentage": rate(lambda r: not r["hard_provenance_errors"]), "ancestry_safe_percentage": rate(lambda r: r["ancestry_mismatch_count"] == 0),
        "gate_pass_percentage": rate(lambda r: r["gate_result"] == "PASS"), "weighted_coverage_mean": round(statistics.mean(weighted), 4),
        "weighted_coverage_median": round(statistics.median(weighted), 4), "weighted_coverage_percentiles": {f"P{p}": _percentile(weighted, p) for p in (10, 25, 50, 75, 90)},
        "eligible_utilization_mean": round(statistics.mean(eligible), 4), "eligible_utilization_median": round(statistics.median(eligible), 4),
        "core_coverage_rate": rate(lambda r: r["core_coverage"] == 1.0), "category_coverage_rate": rate(lambda r: r["category_coverage"] == 1.0),
        "high_dump_rate": rate(lambda r: r["dump_severity"] == "HIGH"), "clean_pass_rate": rate(lambda r: r["final_chapter_classification"] == "CLEAN_PASS"),
        "edge_case_rate": rate(lambda r: r["final_chapter_classification"] == "SCORER_RENDERER_EDGE_CASE"),
        "genuine_renderer_failure_rate": rate(lambda r: r["final_chapter_classification"] in {"RICHNESS_SHORTFALL", "CORE_OMISSION", "CATEGORY_SHORTFALL", "STRUCTURAL_FAILURE", "PROVENANCE_FAILURE", "DUMP_FAILURE", "READABILITY_REGRESSION"}),
        "average_prose_word_count": round(statistics.mean(row["prose_word_count"] for row in rows), 1),
        "classification_distribution": dict(sorted(Counter(row["final_chapter_classification"] for row in rows).items())),
    }


def _qualitative_sample(rows: list[dict[str, Any]]) -> list[str]:
    chosen: list[str] = []
    def add(candidates: Iterable[dict[str, Any]], limit: int) -> None:
        for row in candidates:
            if row["reference"] not in chosen:
                chosen.append(row["reference"])
            if len(chosen) >= limit:
                return
    add(sorted(rows, key=lambda r: (r["weighted_coverage"] or 0, r["reference"]))[:4], 4)
    add(sorted(rows, key=lambda r: (-(r["weighted_coverage"] or 0), r["reference"]))[:3], 7)
    for density in ("sparse", "medium", "dense"):
        add([r for r in rows if r["density_class"] == density and r["seen_status"] == "unseen"], len(chosen) + 2)
    add([r for r in rows if r["final_chapter_classification"] == "SCORER_RENDERER_EDGE_CASE"], 13)
    add([r for r in rows if r["seen_status"] == "unseen"], 13)
    return chosen[:13]


def finalize(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    if _read(root / "manifest.json") != manifest:
        raise ScalePilotError("frozen manifest changed before finalization")
    rows = []
    batch_reports = []
    for batch in range(1, len(BATCH_SIZES) + 1):
        report = _read(root / f"batch-{batch:03d}" / "batch-validation.json")
        rows.extend(report["chapters"])
        batch_reports.append({"batch": batch, "catastrophic_stop": report["catastrophic_stop"], "classification_distribution": report["classification_distribution"]})
    if len(rows) != TARGET_COUNT or len({row["reference"] for row in rows}) != TARGET_COUNT:
        raise ScalePilotError("pilot validation population is incomplete or duplicated")
    aggregate = _summary(rows)
    stratified = {}
    for field in ("seen_status", "density_class", "literary_stratum"):
        stratified[field] = {value: _summary([row for row in rows if row[field] == value]) for value in sorted({row[field] for row in rows})}
    low_weighted = sorted(rows, key=lambda r: ((r["weighted_coverage"] or 0), r["reference"]))[:10]
    low_eligible = sorted(rows, key=lambda r: ((r["eligible_idea_utilization"] or 0), r["reference"]))[:10]
    exception_labels = {"RICHNESS_SHORTFALL", "CORE_OMISSION", "CATEGORY_SHORTFALL", "STRUCTURAL_FAILURE", "PROVENANCE_FAILURE", "DUMP_FAILURE", "READABILITY_REGRESSION", "SCORER_RENDERER_EDGE_CASE"}
    exceptions = [row for row in rows if row["final_chapter_classification"] in exception_labels]
    seen, unseen = stratified["seen_status"].get("seen", {}), stratified["seen_status"].get("unseen", {})
    unseen_comparable = abs((seen.get("weighted_coverage_mean", 0) - unseen.get("weighted_coverage_mean", 0))) <= 0.10 and abs((seen.get("gate_pass_percentage", 0) - unseen.get("gate_pass_percentage", 0))) <= 5.0
    criteria = {
        "structural_at_least_98": aggregate["structurally_valid_percentage"] >= 98,
        "provenance_at_least_98": aggregate["provenance_safe_percentage"] >= 98,
        "ancestry_at_least_98": aggregate["ancestry_safe_percentage"] >= 98,
        "core_at_least_98": aggregate["core_coverage_rate"] >= 98,
        "gate_at_least_95": aggregate["gate_pass_percentage"] >= 95,
        "high_dump_near_zero": aggregate["high_dump_rate"] <= 1.5,
        "unseen_broadly_comparable": unseen_comparable,
        "no_widespread_readability_regression": sum(row["final_chapter_classification"] == "READABILITY_REGRESSION" for row in rows) <= 2,
        "no_catastrophic_batch": not any(report["catastrophic_stop"] for report in batch_reports),
    }
    if all(criteria.values()):
        decision = "SCALE_PILOT_PASS_WITH_EDGE_CASE_MONITORING" if exceptions else "SCALE_PILOT_PASS_BULK_GENERATION_READY"
    else:
        decision = "SCALE_PILOT_NOT_READY"
    sample_refs = _qualitative_sample(rows)
    qualitative = {"artifact_version": f"{ARTIFACT_VERSION}-qualitative-sample", "selection_method": "deterministic lowest four, highest three, then unseen density representatives and edge cases without duplication", "references": sample_refs, "chapters": {row["reference"]: row["qualitative_review"] for row in rows if row["reference"] in sample_refs}}
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-final-report", "namespace": manifest["namespace"], "starting_sha": SOURCE_HEAD,
        "contract": {"prompt": PROMPT_VERSION, "projection": READER_LEVEL_IDEA_PROJECTION_VERSION, "ancestry_envelope": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION, "renderer": RENDERER, "effort": RENDERER_EFFORT, "scoring": FROZEN_CONTRACTS},
        "aggregate": aggregate, "stratified": stratified, "batch_reports": batch_reports,
        "lowest_10_weighted": [{"reference": r["reference"], "weighted_coverage": r["weighted_coverage"], "classification": r["final_chapter_classification"]} for r in low_weighted],
        "lowest_10_eligible": [{"reference": r["reference"], "eligible_idea_utilization": r["eligible_idea_utilization"], "classification": r["final_chapter_classification"]} for r in low_eligible],
        "exceptions": [{"reference": r["reference"], "classification": r["final_chapter_classification"], "weighted_coverage": r["weighted_coverage"], "eligible_idea_utilization": r["eligible_idea_utilization"], "gate_result": r["gate_result"]} for r in exceptions],
        "qualitative_sample": sample_refs, "success_criteria": criteria, "final_readiness_decision": decision,
        "bulk_generation_answer": decision != "SCALE_PILOT_NOT_READY", "full_corpus_generation_started": False,
        "next_strategy": "Use controlled 25-50 chapter batches; validate automatically; accept clean chapters; quarantine exceptions without score-driven regeneration; analyze failure clusters periodically." if decision != "SCALE_PILOT_NOT_READY" else "Identify one bounded population-level remediation from the dominant failure cluster; do not create prompt 1.8 from an isolated chapter.",
        "chapters": rows,
    }
    _write_json(root / "aggregate-metrics.json", aggregate)
    _write_json(root / "stratified-analysis.json", stratified)
    _write_json(root / "qualitative-review.json", qualitative)
    _write_json(root / "exception-queue.json", {"artifact_version": f"{ARTIFACT_VERSION}-exceptions", "count": len(exceptions), "exceptions": report["exceptions"]})
    _write_json(root / "final-report.json", report)
    return report


def stop_early(*, repo_root: Path = ROOT) -> dict[str, Any]:
    """Close the pilot after the explicit catastrophic-stop condition fires."""
    context = build_context(repo_root)
    root, manifest = context["root"], context["manifest"]
    if _read(root / "manifest.json") != manifest:
        raise ScalePilotError("frozen manifest changed before early-stop report")
    first = _read(root / "batch-001/batch-validation.json")
    rows = first["chapters"]
    later_responses = list(root.glob("batch-00[2-6]/responses/raw/*.json"))
    if later_responses:
        raise ScalePilotError("later-batch responses exist; early-stop population is not clean")
    aggregate = _summary(rows)
    stratified = {}
    for field in ("seen_status", "density_class", "literary_stratum"):
        stratified[field] = {value: _summary([row for row in rows if row[field] == value]) for value in sorted({row[field] for row in rows})}
    low_weighted = sorted(rows, key=lambda r: ((r["weighted_coverage"] or 0), r["reference"]))[:10]
    low_eligible = sorted(rows, key=lambda r: ((r["eligible_idea_utilization"] or 0), r["reference"]))[:10]
    exceptions = [row for row in rows if row["final_chapter_classification"] != "CLEAN_PASS"]
    sample_refs = [row["reference"] for row in rows]
    qualitative = {
        "artifact_version": f"{ARTIFACT_VERSION}-qualitative-sample",
        "selection_method": "all 13 generated chapters in the catastrophic-stop batch",
        "references": sample_refs,
        "review_scope": "natural English, coherence, dump feel, checklist behavior, ancestry phrasing, verbosity, under-explanation, and normal-reader usefulness",
        "overall": {
            "natural_english": "PASS_13_OF_13", "coherence": "PASS_13_OF_13",
            "high_dump_feel": "NONE", "checklist_behavior": "NONE_OBSERVED",
            "awkward_ancestry_phrasing": "NONE_OBSERVED", "widespread_readability_regression": False,
            "finding": "The prose is generally natural and useful; failures are metadata ancestry and one core-coverage omission, not visible inventory prose.",
        },
        "chapter_notes": {
            "Isaiah 3": "Very concise but proportionate to its one projected eligible idea.",
            "Galatians 3": "Natural and substantial, but the frozen scorer identifies one omitted CORE cluster.",
            "Romans 3": "Natural prose with complete scorer coverage; two blocks use legal source ancestry that was not present in the projected envelope.",
            "Joshua 10": "Natural and coherent; one block goes outside the projected envelope.",
            "Leviticus 1": "Natural and coherent; three blocks go outside the projected envelope.",
            "Genesis 5": "Natural and appropriately concise for genealogy material; two blocks go outside the projected envelope.",
        },
        "chapters": {row["reference"]: row["qualitative_review"] for row in rows},
    }
    mismatch_chapters = [row["reference"] for row in rows if row["ancestry_mismatch_count"]]
    report = {
        "artifact_version": f"{ARTIFACT_VERSION}-final-report", "namespace": manifest["namespace"],
        "starting_sha": SOURCE_HEAD, "pilot_status": "STOPPED_EARLY_CATASTROPHIC_ANCESTRY_FAILURE",
        "planned_chapter_count": TARGET_COUNT, "generated_chapter_count": len(rows), "ungenerated_chapter_count": TARGET_COUNT - len(rows),
        "completed_batch_count": 1, "planned_batch_count": len(BATCH_SIZES), "population_complete": False,
        "contract": {"prompt": PROMPT_VERSION, "projection": READER_LEVEL_IDEA_PROJECTION_VERSION, "ancestry_envelope": READER_LEVEL_IDEA_ANCESTRY_ENVELOPE_VERSION, "renderer": RENDERER, "effort": RENDERER_EFFORT, "scoring": FROZEN_CONTRACTS},
        "catastrophic_stop": {
            "triggered": True, "kind": "WIDESPREAD_ANCESTRY_CORRUPTION",
            "affected_chapters": mismatch_chapters, "affected_chapter_count": len(mismatch_chapters),
            "affected_chapter_percentage": round(100 * len(mismatch_chapters) / len(rows), 2),
            "ancestry_mismatch_count": sum(row["ancestry_mismatch_count"] for row in rows),
            "interpretation": "The structural validator accepted the underlying synthesis/evidence pairs, but the renderer used paths outside the frozen reader-level ancestry envelope in four chapters. This is systemic enough to stop the pilot under the user-specified catastrophic policy.",
        },
        "aggregate_completed_population": aggregate, "stratified_completed_population": stratified,
        "lowest_10_weighted": [{"reference": r["reference"], "weighted_coverage": r["weighted_coverage"], "classification": r["final_chapter_classification"]} for r in low_weighted],
        "lowest_10_eligible": [{"reference": r["reference"], "eligible_idea_utilization": r["eligible_idea_utilization"], "classification": r["final_chapter_classification"]} for r in low_eligible],
        "exceptions": [{"reference": r["reference"], "classification": r["final_chapter_classification"], "weighted_coverage": r["weighted_coverage"], "eligible_idea_utilization": r["eligible_idea_utilization"], "gate_result": r["gate_result"], "ancestry_mismatch_count": r["ancestry_mismatch_count"]} for r in exceptions],
        "qualitative_sample": sample_refs,
        "success_criteria": {
            "structural_at_least_98": aggregate["structurally_valid_percentage"] >= 98,
            "hard_provenance_at_least_98": aggregate["provenance_safe_percentage"] >= 98,
            "ancestry_at_least_98": aggregate["ancestry_safe_percentage"] >= 98,
            "core_at_least_98": aggregate["core_coverage_rate"] >= 98,
            "gate_at_least_95": aggregate["gate_pass_percentage"] >= 95,
            "high_dump_near_zero": aggregate["high_dump_rate"] <= 1.5,
            "no_widespread_readability_regression": True,
            "unseen_broadly_comparable": "NOT_ASSESSABLE_FROM_TRUNCATED_POPULATION",
            "population_complete": False,
        },
        "renderer_execution_warning": "Two operationally overlapping renderer returns (Romans 3 and Hebrews 1) were discarded on immutable collision; the first response bytes were preserved, no output was selected by score, and no persisted response was regenerated.",
        "final_readiness_decision": "SCALE_PILOT_NOT_READY", "bulk_generation_answer": False,
        "full_corpus_generation_started": False,
        "bounded_next_recommendation": "Audit why prompt 1.7 plus the relational envelope still permits the renderer to cite valid full-synthesis ancestry paths absent from the envelope. Harden only that presentation/consumption boundary, then rerun a fresh scale pilot; do not create prompt 1.8 or tune scoring from this result.",
        "chapters": rows,
    }
    _write_json(root / "aggregate-metrics.json", aggregate)
    _write_json(root / "stratified-analysis.json", stratified)
    _write_json(root / "qualitative-review.json", qualitative)
    _write_json(root / "exception-queue.json", {"artifact_version": f"{ARTIFACT_VERSION}-exceptions", "count": len(exceptions), "exceptions": report["exceptions"]})
    _write_json(root / "final-report.json", report)
    return report


def checksums(*, repo_root: Path = ROOT) -> dict[str, Any]:
    root = build_context(repo_root)["root"]
    target = root / "checksums.json"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path != target)
    payload = {"artifact_version": f"{ARTIFACT_VERSION}-checksums", "files": {str(path.relative_to(root)): sha256_bytes(path.read_bytes()) for path in files}}
    _write_json(target, payload)
    return {"status": "CHECKSUMMED", "file_count": len(files), "path": str(target.relative_to(repo_root))}


def status(*, repo_root: Path = ROOT) -> dict[str, Any]:
    context = build_context(repo_root)
    root = context["root"]
    batches = []
    for batch in range(1, len(BATCH_SIZES) + 1):
        expected = [row for row in context["manifest"]["chapters"] if row["batch"] == batch]
        present = sum((root / f"batch-{batch:03d}" / "responses/raw" / row["response_filename"]).is_file() for row in expected)
        batches.append({"batch": batch, "responses_present": present, "responses_required": len(expected), "validated": (root / f"batch-{batch:03d}" / "batch-validation.json").is_file()})
    return {"status": "FINALIZED" if (root / "final-report.json").is_file() else "IN_PROGRESS", "namespace": context["manifest"]["namespace"], "batches": batches}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "validate-batch", "finalize", "stop-early", "checksums", "status"))
    parser.add_argument("--batch", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare()
        elif args.command == "validate-batch":
            if args.batch not in range(1, len(BATCH_SIZES) + 1):
                raise ScalePilotError("--batch must be 1-6")
            result = validate_batch(args.batch)
        elif args.command == "finalize":
            result = finalize()
        elif args.command == "stop-early":
            result = stop_early()
        elif args.command == "checksums":
            result = checksums()
        else:
            result = status()
    except (ScalePilotError, ArtifactCollisionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
