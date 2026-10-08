#!/usr/bin/env python3
"""Build the read-only, deterministic Genesis G0 CKL evidence census."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.ckl import load_canonical_library
from framework.canonical_library.database_builder import database_info
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.retrieval.indexer import inventory_content_signature, inventory_signature
from framework.canonical_library.scripture import format_scripture_reference, parse_scripture_query, parse_scripture_references, scripture_reference_overlaps
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import sha256_json
from tools.diagnose_scripture_retrieval import _raw_candidate_ids, _reference_entries


AUDIT_REL = Path(".bhf-data/bhf-commentary-candidates/genesis-g0-evidence-census")
RELEASE_REL = Path(".bhf-data/bhf-commentary-v1.2")
CKL_ROOT = ROOT / "framework/canonical_library"
COMMENTARY_REF = "Genesis"
CONTROLS = (("Isaiah", 36, "recent geography impact"), ("Acts", 16, "unrelated unchanged control"), ("Revelation", 18, "unrelated unchanged control"))
DIMENSIONS = (
    "immediate_literary_context", "ancient_near_eastern_context", "cultural_social_context",
    "geography", "archaeology_material_culture", "historical_context",
    "hebrew_worldview_concepts", "divine_council_spiritual_worldview", "covenant_context",
    "intertextual_canonical_connections", "textual_manuscript_issues", "lexical_concepts",
    "interpretive_disputes",
)

SOURCE_CLASSES = {
    "scripture": "PRIMARY",
    "ancient-primary-source": "PRIMARY",
    "excavation-report": "PRIMARY",
    "museum-collection": "PRIMARY",
    "academic-book": "SECONDARY",
    "journal-article": "SECONDARY",
    "reference-work": "SECONDARY",
    "lexicon": "SECONDARY",
    "grammar": "SECONDARY",
    "confessional-source": "SECONDARY",
    "other": "UNRESOLVED",
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_inventory() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    objects: dict[str, dict[str, Any]] = {}
    paths: dict[str, dict[str, Any]] = {}
    for path in sorted((CKL_ROOT / "objects").rglob("*.json")):
        try:
            value = read(path)
        except (OSError, json.JSONDecodeError):
            continue
        object_id = str(value.get("id") or "")
        if object_id:
            objects[object_id] = value
            paths[object_id] = {"path": path.relative_to(ROOT).as_posix(), "sha256": file_sha(path)}
    return objects, paths


def _source_class(source: dict[str, Any]) -> str:
    kind = str(source.get("source_type") or source.get("type") or "other").lower()
    return SOURCE_CLASSES.get(kind, "UNRESOLVED")


def freeze_identities(objects: dict[str, dict[str, Any]], paths: dict[str, dict[str, Any]]) -> dict[str, Any]:
    release_dir = ROOT / RELEASE_REL
    release_manifest_path = release_dir / ".bhf-commentary-release.json"
    release_checksums_path = release_dir / ".bhf-commentary-release-checksums.json"
    release_manifest = read(release_manifest_path)
    checksums = read(release_checksums_path)
    release_files = checksums.get("files", {})
    release_files_valid = all(
        (release_dir / relative).is_file() and file_sha(release_dir / relative) == digest
        for relative, digest in release_files.items()
    )
    ck_manifest = read(CKL_ROOT / "manifest.json")
    inventory_rows = [
        {"object_id": object_id, "path": paths[object_id]["path"], "sha256": paths[object_id]["sha256"]}
        for object_id in sorted(objects)
    ]
    byte_signature = hashlib.sha256(
        "\n".join(f"{row['path']}\0{row['sha256']}" for row in inventory_rows).encode("utf-8")
    ).hexdigest()
    try:
        library = load_canonical_library(config=CKLRepositoryConfig())
        inventory_fingerprint = library.inventory_fingerprint()
    except Exception:
        inventory_fingerprint = None
    runtime_db_path = ROOT / ".bhf/ckl.sqlite"
    try:
        runtime_db = database_info(runtime_db_path)
        runtime_db["file_sha256"] = file_sha(runtime_db_path)
        runtime_db["matches_json_inventory"] = runtime_db.get("inventory_fingerprint") == inventory_fingerprint
        runtime_db["configured_stale_policy"] = "fallback_to_json"
    except (OSError, RuntimeError, ValueError):
        runtime_db = {"available": False}
    release_rows = release_manifest.get("chapter_publication_index", [])
    genesis_rows = [row for row in release_rows if row.get("book") == "Genesis"]
    return {
        "release": {
            "release": release_manifest.get("release"),
            "manifest_identity": release_manifest.get("manifest_identity"),
            "descriptor_identity": release_manifest.get("source_validation_artifact_identity"),
            "corpus_checksum_root_identity": release_manifest.get("corpus_checksum_root_identity"),
            "manifest_sha256": file_sha(release_manifest_path),
            "reconciliation_version": release_manifest.get("reconciliation_version"),
            "checksum_index_version": checksums.get("artifact_version"),
            "checksum_index_sha256": file_sha(release_checksums_path),
            "indexed_file_count": len(release_files),
            "all_indexed_files_valid": release_files_valid,
            "chapter_tree_identity": sha256_json(genesis_rows),
            "genesis_publication_rows": len(genesis_rows),
        },
        "ckl": {
            "manifest_sha256": file_sha(CKL_ROOT / "manifest.json"),
            "manifest_object_count": ck_manifest.get("object_count"),
            "object_count": len(objects),
            "inventory_fingerprint": inventory_fingerprint,
            "byte_signature": inventory_content_signature(CKL_ROOT),
            "stat_signature": inventory_signature(CKL_ROOT),
            "object_file_sha256_root": sha256_json(inventory_rows),
            "runtime_database": runtime_db,
        },
    }


def _commentary(book: str, chapter: int) -> tuple[dict[str, Any], dict[str, Any]]:
    slug = f"{book.lower().replace(' ', '_')}_{chapter:03d}"
    artifact = read(ROOT / RELEASE_REL / f"{slug}.json")
    manifest = read(ROOT / RELEASE_REL / ".bhf-commentary-release.json")
    row = next(row for row in manifest["chapter_publication_index"] if row.get("reference") == f"{book} {chapter}")
    sections = artifact.get("sections", [])
    blocks = [block for section in sections for block in section.get("blocks", [])]
    return artifact, {
        "release_state": row.get("release_state"),
        "section_count": len(sections),
        "block_count": len(blocks),
        "section_categories": sorted({str(section.get("kind") or "unknown") for section in sections}),
        "evidence_ids_consumed": sorted({str(eid) for block in blocks for eid in block.get("evidence_ids", [])}),
        "synthesis_ids_consumed": sorted({str(sid) for block in blocks for sid in block.get("synthesis_ids", [])}),
        "source_lineage": row.get("source_lineage", {}),
    }


def _dim_matches(item: dict[str, Any]) -> set[str]:
    text = " ".join(str(item.get(key) or "") for key in ("claim", "category", "source_kind", "semantic_relationship", "note_type", "parent_title")).lower()
    category = str(item.get("category") or "").lower()
    metadata = item.get("relevance_metadata", {})
    found: set[str] = set()
    patterns = {
        "immediate_literary_context": r"literary|narrative|genealog|toledot|speech|blessing|oracle|reversal|scene|formula|story",
        "ancient_near_eastern_context": r"mesopotam|ancient near east|akkadian|sumerian|babylonian|ugaritic|egyptian|hittite|treaty|ziggurat|enuma|gilgamesh|atr[a-h]asis",
        "cultural_social_context": r"household|kinship|inherit|birthright|bride|marriage|betroth|dowry|surrogate|concubin|hospitality|mourning|burial|slave|servant|pastoral|well|famine|custom|social",
        "geography": r"geograph|place|route|travel|river|land|canaan|egypt|haran|shechem|bethel|hebron|mamre|beersheba|paddan|peniel|succoth|dothan|goshen|machpelah|shinar|ararat|eden",
        "archaeology_material_culture": r"archaeolog|artifact|excavat|material culture|inscription|brick|bitumen|altar|well|city gate|tomb|burial|embalm|seal|tablet",
        "historical_context": r"historical|composition|dating|historicity|period|chronolog|empire|king|court|administration|reception",
        "hebrew_worldview_concepts": r"image of god|bless|curse|name|seed|offspring|presence|exile|land|life|dust|covenant|firstborn|ancestral|providence|hebra|worldview",
        "divine_council_spiritual_worldview": r"sons of god|divine council|nephilim|serpent|cherub|theophan|angel|divine being|spiritual|heavenly host",
        "covenant_context": r"covenant|oath|promise|circumcis|land grant|offspring|blessing to nations|noahic|abrahamic",
        "intertextual_canonical_connections": r"intertext|canonical|quotation|quotes|allusion|reuse|reception|new testament|prophet|psalm|hebrews|romans|galatians",
        "textual_manuscript_issues": r"manuscript|masoretic|septuagint|samaritan|textual variant|variant reading|textual tradition|number tradition",
        "lexical_concepts": r"lexical|hebrew term|word study|semantic range|meaning of|bara|tselem|zera|berit|toledot|ezer|nephesh|adam",
        "interpretive_disputes": r"disput|interpret|debate|uncertain|uncertainty|alternative|reading|confidence",
    }
    for dimension, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.add(dimension)
    if category == "geography":
        found.add("geography")
    if category in {"culture", "politics"}:
        found.add("cultural_social_context")
    if category == "history":
        found.add("historical_context")
    if str(metadata.get("semantic_relationship", "")).upper() in {"INTERTEXTUAL_REUSE", "LATER_RECEPTION"}:
        found.add("intertextual_canonical_connections")
    if str(metadata.get("dispute_status", "")).lower() not in {"", "not_disputed", "not-disputed", "none"}:
        found.add("interpretive_disputes")
    return found


def _is_passage_specific(item: dict[str, Any], chapter: int) -> bool:
    anchors = item.get("passage_anchors", [])
    ref = f"Genesis {chapter}"
    return any(str(anchor).startswith(ref + ":") or str(anchor) == ref for anchor in anchors)


def _meaningful_passage_evidence(item: dict[str, Any], chapter: int) -> bool:
    relationship = str(item.get("relevance_metadata", {}).get("semantic_relationship", "")).upper()
    return _is_passage_specific(item, chapter) and relationship not in {"LATER_RECEPTION", "GENERIC_BACKGROUND"}


def _candidate_anchors(library: Any) -> dict[str, list[dict[str, Any]]]:
    query = parse_scripture_query("Genesis 1", book_alias_lookup=library._book_alias_lookup)
    result: dict[str, list[dict[str, Any]]] = {}
    for object_id in _raw_candidate_ids(library, query):
        obj = library.objects_by_id[object_id]
        entries = _reference_entries(library, obj)
        result[object_id] = [
            {
                "source": entry["source"],
                "raw": entry["raw"],
                "spans": parse_scripture_references(entry["raw"], book_alias_lookup=library._book_alias_lookup),
            }
            for entry in entries
        ]
    return result


def _chapter_retrieval(library: Any, reference: str, evidence: list[dict[str, Any]], anchors_by_object: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    query = parse_scripture_query(reference, book_alias_lookup=library._book_alias_lookup)
    retrieved = library.retrieve_by_scripture_reference(reference, limit=100)
    retrieved_ids = {result.object.id for result in retrieved}
    admitted: dict[str, list[str]] = {}
    for item in evidence:
        parent = str(item.get("relevance_metadata", {}).get("parent_object_id") or "")
        if parent:
            admitted.setdefault(parent, []).append(str(item["id"]))
    candidates = []
    for object_id, entries in anchors_by_object.items():
        obj = library.objects_by_id[object_id]
        overlaps = [
            {"source": entry["source"], "raw": entry["raw"], "normalized": [format_scripture_reference(span) for span in entry["spans"]]}
            for entry in entries
            if any(scripture_reference_overlaps(query, span) for span in entry["spans"])
        ]
        if not overlaps:
            continue
        candidates.append({
            "record_id": object_id,
            "record_type": obj.type,
            "title": obj.title,
            "overlapping_anchor_entries": overlaps,
            "match": "scripture" if object_id in retrieved_ids else "rejected",
            "admissible_for_chapter_commentary": bool(admitted.get(object_id)),
            "admitted_evidence_ids": sorted(admitted.get(object_id, [])),
        })
    candidates.sort(key=lambda row: row["record_id"])
    return {
        "requested_reference": reference,
        "book_index_candidate_count": len(anchors_by_object),
        "chapter_overlapping_candidate_count": len(candidates),
        "valid_scripture_anchored_result_count": len(retrieved_ids),
        "rejected_candidate_count": sum(row["match"] == "rejected" for row in candidates),
        "candidates": candidates,
    }


def _dimension_applicability(chapter: int, text: str) -> dict[str, str]:
    lower = text.lower()
    applies = {"immediate_literary_context", "historical_context"}
    if chapter <= 11 or re.search(r"\b(?:marriage|wife|husband|brother|sister|son|daughter|father|mother|household|inherit|birthright|bless|slave|servant|well|famine|mour|bury|prison|court|dream|city|altar|sacrifice|treaty|journey|travel)\b", lower):
        applies |= {"ancient_near_eastern_context", "hebrew_worldview_concepts"}
    if chapter in {1, 3, 6, 10, 11, 16, 18, 21, 22, 28, 32}:
        applies.add("divine_council_spiritual_worldview")
    if chapter in {1, 6, 8, 9, 12, 13, 15, 17, 22, 26, 28, 31, 35, 46, 47, 50}:
        applies.add("covenant_context")
    if chapter in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50} and re.search(r"\b(?:canaan|egypt|haran|shechem|bethel|hebron|mamre|beersheba|paddan|peniel|succoth|dothan|goshen|machpelah|shinar|ararat|eden|jordan|gerar|moriah|well|river|land)\b", lower):
        applies.add("geography")
    if re.search(r"\b(?:marriage|wife|husband|brother|sister|son|daughter|father|mother|household|inherit|birthright|bless|slave|servant|well|famine|mour|bury|burying|prison|court|dream|city|altar|sacrifice|treaty|journey|travel)\b", lower):
        applies.add("cultural_social_context")
    if re.search(r"\b(?:altar|well|city|brick|bitumen|tomb|bury|burying|embalm|seal|tablet|prison)\b", lower):
        applies.add("archaeology_material_culture")
    if chapter in {1, 2, 3, 4, 5, 6, 10, 11, 12, 14, 15, 17, 19, 20, 21, 22, 24, 25, 27, 29, 30, 31, 32, 34, 35, 37, 38, 40, 41, 42, 43, 45, 47, 48, 49, 50}:
        applies.add("intertextual_canonical_connections")
    if chapter in {1, 3, 4, 5, 6, 10, 11, 14, 15, 16, 18, 19, 22, 24, 25, 27, 28, 30, 31, 32, 34, 35, 38, 46, 47, 48, 49, 50}:
        applies |= {"lexical_concepts", "interpretive_disputes"}
    if chapter in {1, 4, 5, 6, 10, 11}:
        applies.add("textual_manuscript_issues")
    return {dimension: ("APPLICABLE" if dimension in applies else "NOT_APPLICABLE") for dimension in DIMENSIONS}


def _classify(chapter: int, items: list[dict[str, Any]], units: list[dict[str, Any]], dimension_status: dict[str, Any]) -> str:
    specific_non_reception = [
        item for item in items
        if _meaningful_passage_evidence(item, chapter)
    ]
    used_ids = {evidence_id for unit in units for evidence_id in unit.get("evidence_ids", [])}
    used_specific = [item for item in specific_non_reception if item["id"] in used_ids]
    covered = sum(status.get("status") == "COVERED" for status in dimension_status.values())
    if not used_specific or not units:
        return "GAP"
    if len(used_specific) <= 2 or covered <= 2:
        return "SPARSE"
    if len(used_specific) >= 6 and covered >= 5:
        return "GOOD"
    return "THIN"


def _coverage_taxonomy(overall: str, dims: dict[str, Any], commentary: dict[str, Any], *, retrieval: dict[str, Any], unused_specific: list[str], relevant_objects: list[str], source_classes: dict[str, Any]) -> list[str]:
    gaps = [row for row in dims.values() if row.get("status") == "GAP"]
    actions: set[str] = set()
    if overall == "GOOD" and not gaps:
        actions.add("NO_ACTION_REQUIRED")
    if any(candidate.get("overlapping_anchor_entries") and (candidate.get("match") == "rejected" or not candidate.get("admissible_for_chapter_commentary")) for candidate in retrieval.get("candidates", [])):
        actions.add("PASSAGE_APPLICABILITY_REQUIRED")
    if unused_specific:
        actions.add("SYNTHESIS_APPLICABILITY_ISSUE")
    if commentary.get("synthesis_units_not_consumed"):
        actions.add("COMMENTARY_ONLY_ISSUE")
    if gaps:
        actions.add("EXISTING_OBJECT_ENRICHMENT_REQUIRED" if relevant_objects else "NEW_CKL_EVIDENCE_REQUIRED")
    if source_classes.get("UNRESOLVED"):
        actions.add("SOURCE_PROVENANCE_REPAIR_REQUIRED")
    return sorted(actions or {"NO_ACTION_REQUIRED"})


def chapter_row(book: str, chapter: int, library: Any, objects: dict[str, dict[str, Any]], anchors_by_object: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    prepared = prepare_chapter(book, chapter)
    artifact, commentary = _commentary(book, chapter)
    evidence = [item.to_dict() for item in prepared.bundle.evidence_items]
    units = [unit.to_dict() for unit in prepared.synthesis.synthesis_units]
    used_ids = {eid for unit in units for eid in unit.get("evidence_ids", [])}
    cited = set(commentary["evidence_ids_consumed"])
    lineage = commentary.get("source_lineage", {})
    lineage_matches = (
        lineage.get("evidence_hash") == prepared.row["input_identity"]["evidence_hash"]
        and lineage.get("synthesis_hash") == prepared.row["input_identity"]["synthesis_hash"]
    )
    commentary["lineage_matches_current_preparation"] = lineage_matches
    used_unit_ids = {unit["id"] for unit in units if set(unit.get("evidence_ids", [])) & cited}
    commentary["synthesis_units_not_consumed"] = sorted({unit["id"] for unit in units} - used_unit_ids) if lineage_matches else []
    src_map: dict[str, dict[str, Any]] = {}
    for obj in objects.values():
        for source in obj.get("sources", []) or []:
            sid = str(source.get("id") or "")
            if sid and sid not in src_map:
                src_map[sid] = source
    source_ids = {sid for item in evidence for sid in item.get("source_ids", [])}
    source_classes = {sid: _source_class(src_map.get(sid, {})) for sid in source_ids}
    category_counts = Counter(str(item.get("category") or "unknown") for item in evidence)
    confidence_counts = Counter(str(item.get("confidence") or "unrated") for item in evidence)
    dispute_counts = Counter(str(item.get("relevance_metadata", {}).get("dispute_status") or "unrated") for item in evidence)
    dimension_app = _dimension_applicability(chapter, bible.passage_text(bible.resolve_chapter(book, chapter).get("verses", [])))
    by_dimension: dict[str, list[dict[str, Any]]] = {dimension: [] for dimension in DIMENSIONS}
    for item in evidence:
        for dimension in _dim_matches(item):
            if dimension in by_dimension and _meaningful_passage_evidence(item, chapter):
                by_dimension[dimension].append(item)
    dimension_status: dict[str, Any] = {}
    for dimension in DIMENSIONS:
        if dimension_app[dimension] == "NOT_APPLICABLE":
            dimension_status[dimension] = {"status": "NOT_APPLICABLE", "evidence_ids": []}
        else:
            applicable = by_dimension[dimension]
            used = [item for item in applicable if item["id"] in used_ids]
            dimension_status[dimension] = {
                "status": "COVERED" if len(used) >= 2 else "THIN" if used else "GAP",
                "evidence_ids": sorted(item["id"] for item in applicable),
                "synthesis_evidence_ids": sorted(item["id"] for item in used),
            }
    coverage = _classify(chapter, evidence, units, dimension_status)
    ref = f"{book} {chapter}"
    retrieval = _chapter_retrieval(library, bible.verse_range_reference(book, chapter), evidence, anchors_by_object)
    raw_candidate_records = retrieval.get("candidates", [])
    raw_candidates = [row["record_id"] for row in raw_candidate_records]
    evidence_details = []
    for item in evidence:
        metadata = item.get("relevance_metadata", {})
        parent = str(metadata.get("parent_object_id") or "")
        evidence_details.append({
            **item,
            "object_type": metadata.get("parent_type"),
            "applicability": {
                "scope": metadata.get("applicability_scope"),
                "semantic_relationship": metadata.get("semantic_relationship"),
                "anchor_source": metadata.get("anchor_source"),
                "anchor_specificity": metadata.get("anchor_specificity"),
                "accepted_by_production_bundle": True,
                "used_by_synthesis": item["id"] in used_ids,
                "consumed_by_published_commentary": item["id"] in cited,
            },
            "source_support": {sid: source_classes.get(sid, "UNRESOLVED") for sid in item.get("source_ids", [])},
            "generic_book_level_context": (
                item.get("passage_anchors") == ["Genesis 1-50"]
                or (str(metadata.get("semantic_relationship", "")).upper() == "GENERIC_BACKGROUND" and not _is_passage_specific(item, chapter))
                or (parent == "genesis" and not _is_passage_specific(item, chapter))
            ),
            "object_exists": parent in objects,
        })
    return {
        "reference": ref,
        "chapter": chapter,
        "evidence_count": len(evidence),
        "synthesis_unit_count": len(units),
        "current_input_identity": prepared.row["input_identity"],
        "evidence_availability": prepared.synthesis.evidence_availability,
        "evidence_categories": dict(sorted(category_counts.items())),
        "source_count": len(source_ids),
        "source_classes": dict(sorted(Counter(source_classes.values()).items())),
        "confidence_distribution": dict(sorted(confidence_counts.items())),
        "dispute_distribution": dict(sorted(dispute_counts.items())),
        "raw_candidate_count": len(raw_candidate_records),
        "book_index_candidate_count": retrieval["book_index_candidate_count"],
        "chapter_overlapping_candidate_count": retrieval["chapter_overlapping_candidate_count"],
        "raw_candidate_ids": raw_candidate_records,
        "retrieval_diagnostic": {
            key: retrieval[key] for key in ("book_index_candidate_count", "chapter_overlapping_candidate_count", "valid_scripture_anchored_result_count", "rejected_candidate_count")
        },
        "evidence_items": evidence_details,
        "synthesis_units": units,
        "synthesis_unused_evidence_ids": sorted({item["id"] for item in evidence} - used_ids),
        "commentary": commentary,
        "dimension_assessment": dimension_status,
        "coverage_classification": coverage,
        "gap_taxonomy": _coverage_taxonomy(
            coverage, dimension_status, commentary, retrieval=retrieval,
            unused_specific=sorted(item["id"] for item in evidence if _meaningful_passage_evidence(item, chapter) and item["id"] not in used_ids),
            relevant_objects=sorted({str(item.get("relevance_metadata", {}).get("parent_object_id") or "") for item in evidence if _meaningful_passage_evidence(item, chapter)}),
            source_classes=dict(Counter(source_classes.values())),
        ),
        "remediation_summary": ", ".join(sorted({d for d, row in dimension_status.items() if row["status"] in {"GAP", "THIN"}})) or "Current evidence reaches enough applicable dimensions for this classification.",
        "commentary_later_reception_without_immediate_context": bool(cited) and all(
            str(next((item for item in evidence if item["id"] == eid), {}).get("relevance_metadata", {}).get("semantic_relationship", "")).upper() == "LATER_RECEPTION"
            for eid in cited
        ),
        "commentary_artifact_identity": file_sha(ROOT / RELEASE_REL / f"{book.lower()}_{chapter:03d}.json"),
    }


def related_objects(objects: dict[str, dict[str, Any]], paths: dict[str, dict[str, Any]], chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    genesis_book = objects.get("genesis", {})
    linked = {str(row.get("id")) for row in genesis_book.get("related_objects", []) if row.get("id")}
    linked.update(str(row.get("id")) for row in genesis_book.get("related_people", []) if isinstance(row, dict) and row.get("id"))
    reaching = {item["relevance_metadata"].get("parent_object_id") for chapter in chapters for item in chapter["evidence_items"]}
    output = []
    for object_id, obj in sorted(objects.items()):
        refs = obj.get("scripture_references", []) or []
        genesis_refs = [ref for ref in refs if "genesis" in str(ref.get("reference", ref) if isinstance(ref, dict) else ref).lower()]
        child_refs = []
        for collection in ("evidence_items", "claims", "interpretive_notes"):
            for child in obj.get(collection, []) or []:
                values = child.get("scripture_references") or child.get("scripture_anchors") or []
                if not isinstance(values, (list, tuple)):
                    values = [values]
                for value in values:
                    reference = value.get("reference") if isinstance(value, dict) else value
                    if "genesis" in str(reference or "").lower():
                        child_refs.append(reference)
        if object_id not in linked and object_id not in reaching and not genesis_refs:
            continue
        sources = obj.get("sources", []) or []
        has_locks = any("source-lock" in str(item.get("id", "")) or "locked" in str(item.get("status", "")).lower() for item in obj.get("evidence_items", []))
        broken_source = any(not item.get("id") or not item.get("title") for item in sources)
        broad_only = not genesis_refs and object_id in linked and object_id not in reaching
        if broken_source:
            classification = "PROVENANCE_REPAIR"
            why = "One or more source records lack a stable ID or title."
        elif object_id in reaching and genesis_refs:
            classification = "REUSE_AS_IS" if has_locks or sources else "ENRICH"
            why = "Passage-linked CKL object already reaches at least one Genesis chapter through current retrieval."
        elif object_id in reaching and child_refs:
            classification = "REUSE_AS_IS"
            why = "The parent has no broad Genesis anchor, but its child evidence already carries chapter-specific Genesis anchors; preserve the child-level scope."
        elif object_id in reaching:
            classification = "LINK_TO_MORE_CHAPTERS"
            why = "Object reaches Genesis but has no explicit Genesis scripture reference on the parent object."
        elif broad_only:
            classification = "ENRICH"
            why = "Book-object relationship is broad orientation but does not itself reach a chapter in the audited bundle."
        elif genesis_refs and not sources:
            classification = "PROVENANCE_REPAIR"
            why = "Genesis-anchored object has no source records."
        else:
            classification = "REUSE_AS_IS"
            why = "Object has Genesis scripture references and a source record."
        output.append({
            "object_id": object_id,
            "title": obj.get("title"),
            "type": obj.get("type") or obj.get("category"),
            "path": paths[object_id]["path"],
            "object_sha256": paths[object_id]["sha256"],
            "genesis_scripture_references": genesis_refs,
            "genesis_child_scripture_references": sorted(set(str(value) for value in child_refs)),
            "source_ids": sorted(str(item.get("id")) for item in sources if item.get("id")),
            "source_count": len(sources),
            "evidence_item_count": len(obj.get("evidence_items", []) or []),
            "confidence_distribution": dict(sorted(Counter(str(item.get("confidence") or "unrated") for item in obj.get("evidence_items", []) or []).items())),
            "dispute_distribution": dict(sorted(Counter(str(item.get("dispute_status") or "unrated") for item in obj.get("evidence_items", []) or []).items())),
            "source_locked_evidence_present": has_locks,
            "reached_chapters": sorted(chapter["reference"] for chapter in chapters if any(item["relevance_metadata"].get("parent_object_id") == object_id for item in chapter["evidence_items"])),
            "reuse_classification": classification,
            "reason": why,
        })
    return output


def expansion_plan(chapters: list[dict[str, Any]], reuse: list[dict[str, Any]]) -> dict[str, Any]:
    domains = [
        ("primeval_origins", list(range(1, 6)), "Primeval Origins"),
        ("flood_post_flood", list(range(6, 10)), "Flood / Post-Flood"),
        ("nations_babel", list(range(10, 12)), "Nations / Babel"),
        ("abraham_cycle", list(range(12, 26)), "Abraham Cycle"),
        ("jacob_esau_cycle", list(range(25, 37)), "Jacob / Esau Cycle"),
        ("joseph_judah_cycle", list(range(37, 51)), "Joseph / Judah Cycle"),
    ]
    by_chapter = {int(chapter["chapter"]): chapter for chapter in chapters}
    batches = []
    for key, numbers, title in domains:
        rows = [by_chapter[number] for number in numbers]
        missing = sorted({dimension for row in rows for dimension, status in row["dimension_assessment"].items() if status["status"] in {"GAP", "THIN"}})
        domain_refs = {f"Genesis {number}" for number in numbers}
        reusable = sorted(obj["object_id"] for obj in reuse if obj["reached_chapters"] and any(ref in domain_refs for ref in obj["reached_chapters"]))
        candidates = sorted(obj["object_id"] for obj in reuse if obj["reuse_classification"] in {"ENRICH", "LINK_TO_MORE_CHAPTERS", "PROVENANCE_REPAIR"} and (not obj["reached_chapters"] or any(ref in domain_refs for ref in obj["reached_chapters"])))
        candidate_details = []
        reuse_by_id = {obj["object_id"]: obj for obj in reuse}
        remediation_for = {
            "ENRICH": "EXISTING_OBJECT_ENRICHMENT_REQUIRED",
            "LINK_TO_MORE_CHAPTERS": "RELATIONSHIP_LINK_REQUIRED",
            "PROVENANCE_REPAIR": "SOURCE_PROVENANCE_REPAIR_REQUIRED",
        }
        for object_id in candidates:
            obj = reuse_by_id[object_id]
            candidate_details.append({
                "object_id": object_id,
                "reuse_classification": obj["reuse_classification"],
                "remediation_taxonomy": remediation_for[obj["reuse_classification"]],
            })
        batch_taxonomy = sorted({action for row in rows for action in row["gap_taxonomy"]})
        batch_taxonomy.extend(item["remediation_taxonomy"] for item in candidate_details if item["remediation_taxonomy"] not in batch_taxonomy)
        batches.append({
            "batch_id": key,
            "title": title,
            "chapters": [f"Genesis {number}" for number in numbers],
            "missing_evidence_dimensions": missing,
            "existing_reusable_ckl_objects": reusable,
            "new_or_enriched_object_candidates": candidate_details,
            "recommended_remediation_taxonomy": sorted(set(batch_taxonomy)),
            "proposed_source_classes": ["Scripture textual observations", "primary ancient texts/artifacts for bounded comparison", "archaeological publications/museum/excavation records where materially relevant", "academic reference works/commentaries"],
            "estimated_source_lock_work": "HIGH" if len(missing) >= 7 else "MEDIUM" if len(missing) >= 4 else "LOW",
            "expected_commentary_impact": "Selective synthesis and Commentary impact assessment only after passage applicability, source provenance, CKL validation, and impact dry-run pass.",
        })
    return {
        "transaction": "GENESIS_G0_EVIDENCE_CENSUS",
        "status": "PLAN_ONLY_NO_PRODUCTION_CHANGES",
        "recommended_first_production_batch": "primeval_origins",
        "recommendation_rationale": "Genesis 2–4 form a contiguous high-priority gap immediately after the opening chapter; assess existing creation/fall/people objects together and retain the separately sourced Genesis 1 and 5 foundations.",
        "batches": batches,
    }


def build() -> dict[str, Any]:
    objects, paths = object_inventory()
    initial = freeze_identities(objects, paths)
    library = load_canonical_library(config=CKLRepositoryConfig())
    anchors_by_object = _candidate_anchors(library)
    chapters = [chapter_row("Genesis", number, library, objects, anchors_by_object) for number in range(1, 51)]
    control_rows = []
    for book, number, role in CONTROLS:
        prepared = prepare_chapter(book, number)
        _artifact, published = _commentary(book, number)
        identity = prepared.row["input_identity"]
        release_lineage = published["source_lineage"]
        control_rows.append({
            "reference": f"{book} {number}", "role": role, "input_identity": identity,
            "release_source_lineage": release_lineage,
            "identity_matches_release_lineage": release_lineage.get("evidence_hash") == identity["evidence_hash"] and release_lineage.get("synthesis_hash") == identity["synthesis_hash"],
            "evidence_count": len(prepared.bundle.evidence_items),
            "synthesis_unit_count": len(prepared.synthesis.synthesis_units),
        })
    reuse = related_objects(objects, paths, chapters)
    end_objects, end_paths = object_inventory()
    final = freeze_identities(end_objects, end_paths)
    return {"initial_identities": initial, "final_identities": final, "chapters": chapters, "controls": control_rows, "existing_objects": reuse}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize-existing", action="store_true", help="recompute derived census summaries from a completed 50-chapter audit without rerunning preparation")
    args = parser.parse_args()
    if args.finalize_existing:
        return finalize_existing()
    data = build()
    if data["initial_identities"] != data["final_identities"]:
        raise SystemExit("frozen release or CKL identity changed during read-only census")
    out = ROOT / AUDIT_REL
    out.mkdir(parents=True, exist_ok=True)
    census = {
        "transaction": "GENESIS_G0_EVIDENCE_CENSUS",
        "status": "GENESIS_G0_EVIDENCE_CENSUS_COMPLETE",
        "base_commit": "3cf8990a3e0384fddc11b273dde7f4c82645f893",
        "coverage_totals": dict(sorted(Counter(row["coverage_classification"] for row in data["chapters"]).items())),
        "total_chapters_audited": len(data["chapters"]),
        "current_genesis_evidence_total": sum(row["evidence_count"] for row in data["chapters"]),
        "unique_genesis_evidence_id_count": len({item["id"] for row in data["chapters"] for item in row["evidence_items"]}),
        "unique_genesis_source_id_count": len({sid for row in data["chapters"] for item in row["evidence_items"] for sid in item.get("source_ids", [])}),
        "category_distribution": dict(sorted(sum_counters(row["evidence_categories"] for row in data["chapters"]).items())),
        "source_class_distribution": dict(sorted(sum_counters(row["source_classes"] for row in data["chapters"]).items())),
        "controls": data["controls"],
        "frozen_identities": {"before": data["initial_identities"], "after": data["final_identities"], "unchanged": data["initial_identities"] == data["final_identities"]},
        "runtime_diagnostics": {
            "ckl_retrieval_backend": "JSON fallback under CKLRepositoryConfig.stale_database_policy=fallback_to_json",
            "stale_runtime_database": data["initial_identities"]["ckl"]["runtime_database"].get("matches_json_inventory") is False,
            "production_database_modified": False,
        },
        "commentary_lineage_match_count": sum(row["commentary"].get("lineage_matches_current_preparation", False) for row in data["chapters"]),
        "retrieval_applicability_gap_chapters": [row["reference"] for row in data["chapters"] if "PASSAGE_APPLICABILITY_REQUIRED" in row["gap_taxonomy"]],
        "chapters": data["chapters"],
    }
    reuse = {"transaction": census["transaction"], "objects": data["existing_objects"], "classification_counts": dict(sorted(Counter(obj["reuse_classification"] for obj in data["existing_objects"]).items()))}
    plan = expansion_plan(data["chapters"], data["existing_objects"])
    (out / "genesis-evidence-census.json").write_text(json.dumps(census, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out / "genesis-existing-object-reuse.json").write_text(json.dumps(reuse, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out / "genesis-expansion-plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out / "genesis-evidence-gap-report.md").write_text(render_report(census, reuse, plan), encoding="utf-8")
    print(json.dumps({"status": census["status"], "chapters": census["total_chapters_audited"], "counts": census["coverage_totals"], "evidence_total": census["current_genesis_evidence_total"], "controls": [row["reference"] for row in data["controls"]]}, sort_keys=True))
    return 0


def finalize_existing() -> int:
    """Recompute deterministic summaries from the last complete chapter pass."""
    out = ROOT / AUDIT_REL
    census = read(out / "genesis-evidence-census.json")
    reuse = read(out / "genesis-existing-object-reuse.json")
    chapters = census["chapters"]
    for row in chapters:
        chapter_number = int(row["chapter"])
        used_by_synthesis = {eid for unit in row["synthesis_units"] for eid in unit.get("evidence_ids", [])}
        detected: dict[str, list[dict[str, Any]]] = {dimension: [] for dimension in DIMENSIONS}
        for item in row["evidence_items"]:
            if not _meaningful_passage_evidence(item, chapter_number):
                continue
            for dimension in _dim_matches(item):
                if dimension in detected:
                    detected[dimension].append(item)
        reassessed: dict[str, Any] = {}
        for dimension, old_status in row["dimension_assessment"].items():
            if old_status.get("status") == "NOT_APPLICABLE":
                reassessed[dimension] = {"status": "NOT_APPLICABLE", "evidence_ids": []}
                continue
            supporting = detected[dimension]
            used = [item for item in supporting if item["id"] in used_by_synthesis]
            reassessed[dimension] = {
                "status": "COVERED" if len(used) >= 2 else "THIN" if used else "GAP",
                "evidence_ids": sorted(item["id"] for item in supporting),
                "synthesis_evidence_ids": sorted(item["id"] for item in used),
            }
        row["dimension_assessment"] = reassessed
        row["coverage_classification"] = _classify(chapter_number, row["evidence_items"], row["synthesis_units"], reassessed)
        lineage = row["commentary"].get("source_lineage", {})
        identity = row["current_input_identity"]
        matches = lineage.get("evidence_hash") == identity["evidence_hash"] and lineage.get("synthesis_hash") == identity["synthesis_hash"]
        row["commentary"]["lineage_matches_current_preparation"] = matches
        cited = set(row["commentary"]["evidence_ids_consumed"])
        used_units = {unit["id"] for unit in row["synthesis_units"] if set(unit.get("evidence_ids", [])) & cited}
        row["commentary"]["synthesis_units_not_consumed"] = sorted({unit["id"] for unit in row["synthesis_units"]} - used_units) if matches else []
        candidates = row["raw_candidate_ids"]
        retrieval = {
            "book_index_candidate_count": row["book_index_candidate_count"],
            "chapter_overlapping_candidate_count": len(candidates),
            "valid_scripture_anchored_result_count": sum(candidate.get("match") == "scripture" for candidate in candidates),
            "rejected_candidate_count": sum(candidate.get("match") == "rejected" for candidate in candidates),
            "candidates": candidates,
        }
        compiled_evidence = {eid for unit in row["synthesis_units"] for eid in unit.get("evidence_ids", [])}
        unused_specific = [
            item["id"] for item in row["evidence_items"]
            if _meaningful_passage_evidence(item, int(row["chapter"]))
            and item["id"] not in compiled_evidence
        ]
        relevant_objects = sorted({str(item.get("relevance_metadata", {}).get("parent_object_id") or "") for item in row["evidence_items"] if _meaningful_passage_evidence(item, chapter_number)})
        classes: Counter[str] = Counter()
        for item in row["evidence_items"]:
            classes.update(item.get("source_support", {}).values())
        row["gap_taxonomy"] = _coverage_taxonomy(
            row["coverage_classification"], row["dimension_assessment"], row["commentary"],
            retrieval=retrieval, unused_specific=unused_specific,
            relevant_objects=relevant_objects, source_classes=dict(classes),
        )
    for control in census["controls"]:
        book, chapter_text = control["reference"].rsplit(" ", 1)
        _artifact, published = _commentary(book, int(chapter_text))
        lineage = published["source_lineage"]
        identity = control["input_identity"]
        control["release_source_lineage"] = lineage
        control["identity_matches_release_lineage"] = lineage.get("evidence_hash") == identity["evidence_hash"] and lineage.get("synthesis_hash") == identity["synthesis_hash"]
    before = freeze_identities(*object_inventory())
    try:
        db_path = ROOT / ".bhf/ckl.sqlite"
        db_info = database_info(db_path)
        db_info["file_sha256"] = file_sha(db_path)
        db_info["matches_json_inventory"] = db_info.get("inventory_fingerprint") == before["ckl"]["inventory_fingerprint"]
        db_info["configured_stale_policy"] = "fallback_to_json"
    except (OSError, RuntimeError, ValueError):
        db_info = {"available": False}
    before["ckl"]["runtime_database"] = db_info
    after = freeze_identities(*object_inventory())
    census["frozen_identities"] = {"before": before, "after": after, "unchanged": before == after}
    census["coverage_totals"] = dict(sorted(Counter(row["coverage_classification"] for row in chapters).items()))
    census["current_genesis_evidence_total"] = sum(row["evidence_count"] for row in chapters)
    census["unique_genesis_evidence_id_count"] = len({item["id"] for row in chapters for item in row["evidence_items"]})
    census["unique_genesis_source_id_count"] = len({sid for row in chapters for item in row["evidence_items"] for sid in item.get("source_ids", [])})
    census["category_distribution"] = dict(sorted(sum_counters(row["evidence_categories"] for row in chapters).items()))
    census["source_class_distribution"] = dict(sorted(sum_counters(row["source_classes"] for row in chapters).items()))
    census["commentary_lineage_match_count"] = sum(row["commentary"]["lineage_matches_current_preparation"] for row in chapters)
    census["retrieval_applicability_gap_chapters"] = [row["reference"] for row in chapters if "PASSAGE_APPLICABILITY_REQUIRED" in row["gap_taxonomy"]]
    census["runtime_diagnostics"] = {
        "ckl_retrieval_backend": "JSON fallback under CKLRepositoryConfig.stale_database_policy=fallback_to_json",
        "stale_runtime_database": db_info.get("matches_json_inventory") is False,
        "production_database_modified": False,
    }
    objects, paths = object_inventory()
    reuse["objects"] = related_objects(objects, paths, chapters)
    reuse["classification_counts"] = dict(sorted(Counter(obj["reuse_classification"] for obj in reuse["objects"]).items()))
    plan = expansion_plan(chapters, reuse["objects"])
    (out / "genesis-evidence-census.json").write_text(json.dumps(census, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out / "genesis-existing-object-reuse.json").write_text(json.dumps(reuse, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out / "genesis-expansion-plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (out / "genesis-evidence-gap-report.md").write_text(render_report(census, reuse, plan), encoding="utf-8")
    print(json.dumps({"status": census["status"], "chapters": len(chapters), "coverage": census["coverage_totals"], "evidence_total": census["current_genesis_evidence_total"], "lineage_matches": census["commentary_lineage_match_count"], "retrieval_applicability_gap_chapters": len(census["retrieval_applicability_gap_chapters"])}, sort_keys=True))
    return 0


def sum_counters(rows: Any) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in rows:
        result.update(row)
    return result


def render_report(census: dict[str, Any], reuse: dict[str, Any], plan: dict[str, Any]) -> str:
    rows = census["chapters"]
    class_counts = census["coverage_totals"]
    lines = [
        "# Genesis Evidence Gap Report — G0", "",
        "Transaction: `GENESIS_G0_EVIDENCE_CENSUS`", "",
        "This is a read-only baseline. It measures current CKL retrieval, compiled synthesis, and published Commentary v1.2 separately. It does not authorize evidence generation or Commentary regeneration.", "",
        "## Whole-book totals", "",
        f"- Chapters audited: {len(rows)} / 50", f"- CKL evidence items across chapter bundles (chapter-local counts; cross-chapter reuse is counted per chapter): {census['current_genesis_evidence_total']}",
        f"- Distinct evidence IDs: {census.get('unique_genesis_evidence_id_count', 0)}; distinct source IDs: {census.get('unique_genesis_source_id_count', 0)}.",
        f"- Coverage: GOOD {class_counts.get('GOOD', 0)}, THIN {class_counts.get('THIN', 0)}, SPARSE {class_counts.get('SPARSE', 0)}, GAP {class_counts.get('GAP', 0)}",
        f"- Evidence categories: `{json.dumps(census['category_distribution'], sort_keys=True)}`", "",
        f"- CKL runtime: {census.get('runtime_diagnostics', {}).get('ckl_retrieval_backend', 'production retrieval backend recorded in JSON')}; local SQLite fingerprint matches JSON inventory: {not census.get('runtime_diagnostics', {}).get('stale_runtime_database', False)}. The SQLite database was not changed.", "",
        "## Chapter census", "",
        "| Chapter | CKL items | Synthesis units | Categories | Sources | Commentary sections / blocks | Status | Main gap taxonomy |",
        "|---:|---:|---:|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['chapter']} | {row['evidence_count']} | {row['synthesis_unit_count']} | {', '.join(row['evidence_categories']) or '—'} | {row['source_count']} | {row['commentary']['section_count']} / {row['commentary']['block_count']} | {row['coverage_classification']} | {', '.join(row['gap_taxonomy'])} |")
    ordered = sorted(rows, key=lambda row: (row["coverage_classification"] != "GAP", row["coverage_classification"] != "SPARSE", row["evidence_count"], row["chapter"]))
    strongest = sorted(rows, key=lambda row: (row["coverage_classification"] != "GOOD", -row["synthesis_unit_count"], -row["evidence_count"]))[:10]
    unadmitted = [(row["reference"], candidate["record_id"]) for row in rows for candidate in row["raw_candidate_ids"] if candidate.get("match") == "scripture" and not candidate.get("admissible_for_chapter_commentary")]
    rejected = [(row["reference"], candidate["record_id"]) for row in rows for candidate in row["raw_candidate_ids"] if candidate.get("match") == "rejected"]
    lineage_matches = [row["reference"] for row in rows if row["commentary"].get("lineage_matches_current_preparation")]
    rendering_gap = [row["reference"] for row in rows if row["commentary"].get("synthesis_units_not_consumed")]
    sparse_ckl = [row["reference"] for row in rows if row["coverage_classification"] in {"THIN", "SPARSE", "GAP"}]
    later_only = [row["reference"] for row in rows if row["commentary_later_reception_without_immediate_context"]]
    unadmitted_text = ", ".join(f"{reference} → {object_id}" for reference, object_id in unadmitted) or "none"
    lines.extend(["", "## Strongest and weakest chapters", "", "Strongest by status, synthesis breadth, then retrieved count: " + ", ".join(f"{row['reference']} ({row['coverage_classification']}, {row['evidence_count']} items / {row['synthesis_unit_count']} units)" for row in strongest) + ".", "", "Weakest by classification and current retrieval: " + ", ".join(f"{row['reference']} ({row['coverage_classification']}, {row['evidence_count']} items / {row['synthesis_unit_count']} units)" for row in ordered[:10]) + ".", "", "## Retrieval and rendering distinctions", "", f"- Genesis evidence occurrences across chapter bundles: {census['current_genesis_evidence_total']}; shared items are counted once for every chapter to which the bundle admits them.", f"- Chapter-overlapping objects returned by CKL but yielding no admissible bundle item: {len(unadmitted)} candidate/chapter pairs across {len(set(ref for ref, _ in unadmitted))} chapters.", f"- Chapter-overlapping objects rejected by the scripture retrieval index: {len(rejected)}.", f"- Published Commentary lineage exactly matches current prepared CKL+synthesis identities in {len(lineage_matches)} chapters: {', '.join(lineage_matches) or 'none'}.", f"- Exact-lineage chapters with current synthesis units absent from published Commentary: {len(rendering_gap)} ({', '.join(rendering_gap) or 'none'}).", f"- Chapters classified below GOOD because usable CKL context remains thin or sparse: {len(sparse_ckl)} ({', '.join(sparse_ckl) or 'none'}).", f"- Chapters whose published Commentary citations are entirely later-reception evidence: {len(later_only)} ({', '.join(later_only) or 'none'}).", "", "Candidates with chapter-overlapping anchors but no admitted bundle item: " + unadmitted_text + ".", "The diagnostic exposes overlapping anchors, CKL retrieval match, and whether each parent admitted a Commentary bundle item. It does not expose a named reason for every filtered item; no rejection reason is invented. Synthesis-unused and Commentary-unused IDs remain separate from CKL absence.", "", "## Existing objects and priority gaps", "", f"Relevant CKL object reuse classifications: `{json.dumps(reuse['classification_counts'], sort_keys=True)}`.", ""])
    priorities = []
    for row in rows:
        if row["coverage_classification"] in {"GAP", "SPARSE", "THIN"}:
            missing = [dimension for dimension, value in row["dimension_assessment"].items() if value["status"] in {"GAP", "THIN"}]
            priorities.append((row["evidence_count"], row["chapter"], missing))
    lines.extend(["Top 10 chapter-level evidence gaps (ordered by current bundle count; dimensions need human review):", ""])
    for count, chapter, missing in sorted(priorities)[:10]:
        lines.append(f"- Genesis {chapter}: {count} items; review {', '.join(missing) or 'passage-specificity and source provenance'}.")
    lines.extend(["", "## Proposed expansion order", "", f"Recommended first production batch after review: **{plan['recommended_first_production_batch']}**. {plan['recommendation_rationale']}", ""])
    for batch in plan["batches"]:
        lines.append(f"- **{batch['title']} ({batch['chapters'][0]}–{batch['chapters'][-1]}):** {', '.join(batch['missing_evidence_dimensions']) or 'validate current breadth'}; source-lock effort {batch['estimated_source_lock_work']}.")
    lines.extend(["", "Future work should begin with the batch that combines the weakest current coverage with the most reusable, sourceable CKL additions. No batch is approved for production changes by this report.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
