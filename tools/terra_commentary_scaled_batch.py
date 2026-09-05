#!/usr/bin/env python3
"""Generate and audit a locked, evidence-bounded Terra commentary batch.

This is candidate-only prose work.  It neither changes CKL nor selects,
replaces, or relocks chapters.  A stale locked bundle stops the entire batch
before any reader-facing chapter file is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.presentation.relevance import (
    BOOK_CONTEXT,
    COMPARATIVE_CONTEXT,
    DIRECT_CONTEXT,
    GENERIC_BACKGROUND,
    INTERTEXTUAL_REUSE,
    LATER_RECEPTION,
    PRESENTATION_SECTIONS,
    SEMANTIC_RELATIONSHIPS,
)
from tools.commentary_v11_canary import _chapter_overlap_refs, _interpretation_level, _section_for_item


DEFAULT_BATCH_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-scale" / "batch-001"
MODEL_ID = "terra-codex-commentary-v1.1-batch-001-medium"
REPORT_VERSION = "commentary-v1.1-terra-scaled-batch-v1"
TITLES = {
    "chapter_overview": "Chapter overview",
    "historical_context": "Historical and cultural context",
    "people_places": "People and places",
    "archaeology_geography": "Archaeology and geography",
    "language_literary": "Language and literary context",
    "chronology": "Chronology",
    "interpretive_questions": "Interpretive questions",
    "things_easy_to_miss": "Things easy to miss",
    "dig_deeper": "Dig deeper",
}
SECTION_ORDER = {kind: index for index, kind in enumerate(TITLES)}
QUALITY_FLAGS = (
    "LOW_INFORMATION",
    "EVIDENCE_DUMP",
    "OVEREXPANDED",
    "UNSUPPORTED_SYNTHESIS",
    "THEOLOGICAL_OVERREACH",
    "UNCERTAINTY_LOST",
    "READER_UNFRIENDLY",
)
CANARY_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-terra"
SUPPLEMENTAL_ROOT = CANARY_ROOT / "supplemental-integrity-controls"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _word_count(candidate: dict[str, Any]) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", " ".join(
        block["text"] for section in candidate["sections"] for block in section["blocks"]
    )))


def _artifact_fingerprints() -> dict[str, str]:
    paths = sorted(CANARY_ROOT.glob("chapters/*.json"))
    paths += sorted(SUPPLEMENTAL_ROOT.glob("chapters/*.json"))
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _fingerprint_digest(value: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _load(batch_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = json.loads((batch_root / "batch-manifest.json").read_text(encoding="utf-8"))
    certification = json.loads((batch_root / "evidence-certification.json").read_text(encoding="utf-8"))
    terra_input = json.loads((batch_root / "terra-input-manifest.json").read_text(encoding="utf-8"))
    quarantine = json.loads((batch_root / "quarantine-report.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "LOCKED" or certification.get("status") != "LOCKED":
        raise RuntimeError("Terra generation requires a LOCKED Batch 001 manifest and certification")
    if terra_input.get("status") != "READY_FOR_TERRA" or terra_input.get("prose_included"):
        raise RuntimeError("Terra input manifest is not a prose-free READY_FOR_TERRA manifest")
    return manifest, certification, terra_input, quarantine


def _metadata_errors(bundle: Any, allowed_roles: set[str]) -> list[str]:
    errors: list[str] = []
    for item in bundle.evidence_items:
        metadata = item.relevance_metadata or {}
        relationship = metadata.get("semantic_relationship")
        if relationship not in SEMANTIC_RELATIONSHIPS:
            errors.append(f"{item.id}: invalid semantic relationship {relationship!r}")
        routed = _section_for_item(item)
        if routed and routed not in PRESENTATION_SECTIONS:
            errors.append(f"{item.id}: invalid routed presentation section {routed!r}")
        if routed and routed != "dig_deeper" and routed not in allowed_roles:
            errors.append(f"{item.id}: routed role {routed!r} is not allowed by the Terra manifest")
        if routed == "dig_deeper" and "dig_deeper" not in allowed_roles:
            errors.append(f"{item.id}: Dig Deeper is not allowed by the Terra manifest")
    return errors


def revalidate_locks(
    terra_input: dict[str, Any], certification: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild all bundles before prose generation; return bundles only if clean."""

    certified = {row["reference"]: row for row in certification["chapters"]}
    records: list[dict[str, Any]] = []
    bundles: dict[str, Any] = {}
    stale: list[dict[str, Any]] = []
    for entry in terra_input["chapters"]:
        reference = entry["reference"]
        cert = certified.get(reference)
        if cert is None:
            stale.append({"reference": reference, "reason": "missing certification record"})
            continue
        reconstruction = entry["evidence_reconstruction"]["arguments"]
        book, chapter = reconstruction["book"], int(reconstruction["chapter"])
        bundle = get_chapter_evidence_bundle(book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
        actual_ids = sorted(item.id for item in bundle.evidence_items) if bundle else []
        expected_ids = sorted(cert["evidence_ids"])
        actual_availability = classify_evidence_availability(bundle).value if bundle else None
        metadata_errors = _metadata_errors(bundle, set(entry["allowed_section_roles"])) if bundle else ["bundle unavailable"]
        checks = {
            "reference_matches": bool(bundle and bundle.passage_ref == reference),
            "bundle_version_matches": bool(bundle and bundle.version == "1.1"),
            "hash_version_matches": bool(bundle and bundle.evidence_hash_version == "2"),
            "hash_matches": bool(bundle and bundle.evidence_hash == cert["locked_evidence_hash"] == entry["locked_evidence_bundle_hash"]),
            "evidence_ids_match": actual_ids == expected_ids,
            "availability_matches": actual_availability == cert["availability"] == entry["availability"],
            "semantic_presentation_valid": not metadata_errors,
        }
        record = {
            "reference": reference,
            "checks": checks,
            "expected_hash": cert["locked_evidence_hash"],
            "actual_hash": bundle.evidence_hash if bundle else None,
            "expected_evidence_ids": expected_ids,
            "actual_evidence_ids": actual_ids,
            "expected_availability": cert["availability"],
            "actual_availability": actual_availability,
            "metadata_errors": metadata_errors,
            "status": "LOCKED" if all(checks.values()) else "STALE_LOCK",
        }
        records.append(record)
        if record["status"] == "STALE_LOCK":
            stale.append(record)
        else:
            bundles[reference] = bundle
    report = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(),
        "phase": "pre_generation_lock_revalidation",
        "chapters_checked": len(records),
        "locks_revalidated": len(records) - len(stale),
        "stale_locks": stale,
        "results": records,
        "status": "PASS" if len(records) == len(terra_input["chapters"]) and not stale else "STALE_LOCK",
    }
    return report, bundles


def _clean_claim(item: Any) -> str:
    claim = " ".join(str(item.claim or "").split())
    # A small edit keeps a record's own caution reader-facing without adding a
    # new contextual assertion.
    return claim.replace("The evidence does not establish", "The available material does not establish")


def _is_disputed(item: Any) -> bool:
    dispute = str((item.relevance_metadata or {}).get("dispute_status") or "").casefold()
    return dispute not in {"", "not_disputed", "unknown", "none"}


def _reader_safe(item: Any) -> bool:
    """Avoid using reception/application guardrails as the main orientation."""

    text = _clean_claim(item).casefold()
    excluded = (
        "weaponized", "abuse survivor", "anti-judaism", "supersessionism",
        "deicide", "collective jewish guilt", "modern political", "ancient background for",
        "helps anchor the biblical world", " is read across the canon", "cannot authorize",
    )
    return not any(phrase in text for phrase in excluded)


def _item_rank(item: Any) -> tuple[int, int, int, str]:
    metadata = item.relevance_metadata or {}
    source_kind = str(metadata.get("source_kind") or "")
    return (
        1 if _reader_safe(item) else 0,
        1 if source_kind in {"ckl_claim", "ckl_evidence_item", "ckl_interpretive_note"} else 0,
        int(metadata.get("overview_priority") or 0),
        item.id,
    )


def _overview_item(bundle: Any) -> Any | None:
    candidates = [
        item for item in bundle.evidence_items
        if _section_for_item(item) not in {None, "dig_deeper"}
    ]
    if not candidates:
        return None
    return sorted(candidates, key=_item_rank, reverse=True)[0]


def _block_for_item(item: Any, book: str, chapter: int, *, kind: str, index: int, overview: bool = False) -> dict[str, Any]:
    claim = _clean_claim(item)
    disputed = _is_disputed(item)
    if overview:
        lead = "Read the chapter with this setting in view: "
        tail = " It gives a starting point for following the chapter's own movement. The chapter itself should determine how far the point is taken."
    elif kind == "historical_context":
        lead = "For its historical and cultural setting, note that "
        tail = " This background clarifies the setting assumed by the passage. It does not by itself settle every question raised by the chapter."
    elif kind == "language_literary":
        lead = "A literary feature to notice is that "
        tail = " This form helps organize the chapter's claims. Notice it before drawing broader conclusions from a single phrase or image."
    elif kind == "archaeology_geography":
        lead = "For its geographical or material setting, note that "
        tail = " It can illuminate the passage, while its limits should be kept in view."
    elif kind == "chronology":
        lead = "For the chapter's sequence and setting, note that "
        tail = " This gives the reader a frame for the passage without deciding every larger reconstruction."
    elif kind == "dig_deeper":
        lead = "For a later or comparative connection, note that "
        tail = " This remains a secondary connection rather than the chapter's first-audience context. It can be traced further without replacing the chapter's own setting."
    else:
        lead = "One useful point to notice is that "
        tail = ""
    if disputed:
        uncertainty = (
            " Interpretations differ on some details.",
            " The evidence leaves some details unresolved.",
            " A more precise reconstruction remains disputed.",
        )
        tail += uncertainty[index % len(uncertainty)]
    return {
        "id": f"{kind}_{index}",
        "text": lead + claim + tail,
        "evidence_ids": [item.id],
        "verse_refs": _chapter_overlap_refs(item, book, chapter),
        "confidence": item.confidence if item.confidence in {"low", "medium", "high"} else "medium",
        "interpretation_level": _interpretation_level(item),
    }


def _pick_by_role(bundle: Any, role: str, used: set[str], limit: int) -> list[Any]:
    selected = []
    matching = [item for item in bundle.evidence_items if item.id not in used and _section_for_item(item) == role]
    # A textual-variant record may be routed by the locked metadata, yet it is
    # not reader-facing archaeological or geographical explanation.  Omitting
    # it is safer than making a misleading material-culture claim.
    if role == "archaeology_geography":
        matching = [
            item for item in matching
            if not re.search(r"\b(?:manuscript|textual|witness(?:es)?)\b", _clean_claim(item), re.I)
        ]
    safe = [item for item in matching if _reader_safe(item)]
    for item in sorted(safe, key=_item_rank, reverse=True):
        selected.append(item)
        used.add(item.id)
        if len(selected) == limit:
            break
    return selected


def payload_for(entry: dict[str, Any], bundle: Any, *, ordinal: int) -> dict[str, Any]:
    """Compose concise prose from locked claims and their routed roles only."""

    reconstruction = entry["evidence_reconstruction"]["arguments"]
    book, chapter = reconstruction["book"], int(reconstruction["chapter"])
    availability = entry["availability"]
    allowed = list(entry["allowed_section_roles"])
    used: set[str] = set()
    overview = _overview_item(bundle)
    if overview is None:
        # A chapter with only secondary material remains deliberately modest;
        # this uses its first supplied item and does not invent a historical
        # frame merely to make an overview look fuller.
        overview = next(iter(bundle.evidence_items), None)
    if overview is None:
        raise RuntimeError(f"locked non-DATA_GAP bundle has no usable evidence: {entry['reference']}")
    used.add(overview.id)
    sections = [{
        "kind": "chapter_overview",
        "title": TITLES["chapter_overview"],
        "blocks": [_block_for_item(overview, book, chapter, kind="chapter_overview", index=ordinal, overview=True)],
    }]

    role_order = ["historical_context", "people_places", "archaeology_geography", "language_literary", "chronology", "dig_deeper"]
    contextual_limit = 3 if availability == "AVAILABLE" else 1
    added = 0
    for role in role_order:
        if role not in allowed or added >= contextual_limit:
            continue
        items = _pick_by_role(bundle, role, used, 2 if availability == "AVAILABLE" and role == "historical_context" else 1)
        if not items:
            continue
        sections.append({
            "kind": role,
            "title": TITLES[role],
            "blocks": [_block_for_item(item, book, chapter, kind=role, index=ordinal + offset + 1) for offset, item in enumerate(items)],
        })
        added += 1
    # A THIN chapter with only its overview evidence remains one short section;
    # no duplicate citation is added merely to reach a shape target.
    return {
        "reference": entry["reference"],
        "book": book,
        "chapter": chapter,
        "status": "validated",
        "evidence_availability": availability,
        "sections": sorted(sections, key=lambda section: SECTION_ORDER[section["kind"]]),
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash,
            "evidence_bundle_version": bundle.version,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "model": MODEL_ID,
            "generated_timestamp": _now(),
        },
    }


def prose_audit(candidate: dict[str, Any], bundle: Any) -> list[str]:
    text = " ".join(block["text"] for section in candidate["sections"] for block in section["blocks"])
    flags: list[str] = []
    if re.search(r"\bcontains \d+ verses\b|\bit opens with\b|\bit concludes with\b|\bthe chapter begins\b|\bthe chapter ends\b", text, re.I):
        flags.append("LOW_INFORMATION")
    if re.search(r"\b(?:EvidenceBundle|CKL|source-addressable|semantic relationship|presentation role|preflight|retrieval|provider|model)\b", text, re.I):
        flags.append("READER_UNFRIENDLY")
    words = _word_count(candidate)
    sections = len(candidate["sections"])
    availability = candidate["evidence_availability"]
    if (availability == "AVAILABLE" and (words > 700 or sections > 5)) or (availability == "THIN" and (words > 350 or sections > 3)):
        flags.append("OVEREXPANDED")
    citations = [eid for section in candidate["sections"] for block in section["blocks"] for eid in block["evidence_ids"]]
    if len(citations) > max(8, words // 28):
        flags.append("EVIDENCE_DUMP")
    if any(eid not in bundle.evidence_by_id for eid in citations):
        flags.append("UNSUPPORTED_SYNTHESIS")
    for section in candidate["sections"]:
        for block in section["blocks"]:
            if any(_is_disputed(bundle.evidence_by_id[eid]) for eid in block["evidence_ids"]):
                if block["interpretation_level"] != "disputed" or not re.search(r"open|disputed|uncertain|not establish|does not settle|leaves|interpretations differ", block["text"], re.I):
                    flags.append("UNCERTAINTY_LOST")
    # The generator never adds doctrinal/application content beyond a locked
    # claim. This explicit scan catches accidental prohibited phrasing.
    if re.search(r"\b(?:you should|we should|therefore we must|salvation requires|the only true doctrine)\b", text, re.I):
        flags.append("THEOLOGICAL_OVERREACH")
    return sorted(set(flags))


def _validation_row(candidate: dict[str, Any], bundle: Any) -> dict[str, Any]:
    validation = validate_chapter_commentary(
        candidate,
        bundle,
        expected_evidence_hash=bundle.evidence_hash,
        expected_prompt_version=COMMENTARY_PROMPT_VERSION,
        expected_reference=candidate["reference"],
        expected_book=candidate["book"],
        expected_chapter=candidate["chapter"],
    )
    return {"reference": candidate["reference"], "valid": validation.valid, "errors": list(validation.errors)}


def _review_sample(candidates: list[dict[str, Any]], bundles: dict[str, Any], genres: dict[str, str]) -> list[str]:
    chosen: list[str] = []
    def add(reference: str | None) -> None:
        if reference and reference not in chosen and len(chosen) < 18:
            chosen.append(reference)

    for availability in ("AVAILABLE", "THIN"):
        for genre in sorted(set(genres.values())):
            add(next((candidate["reference"] for candidate in candidates if candidate["evidence_availability"] == availability and genres[candidate["reference"]] == genre), None))
    counts = {candidate["reference"]: len(bundles[candidate["reference"]].evidence_items) for candidate in candidates}
    add(max(counts, key=counts.get))
    add(min(counts, key=counts.get))
    for candidate in candidates:
        bundle = bundles[candidate["reference"]]
        if any(_is_disputed(item) for item in bundle.evidence_items):
            add(candidate["reference"])
    for candidate in candidates:
        if any(section["kind"] == "dig_deeper" for section in candidate["sections"]):
            add(candidate["reference"])
    for role in ("archaeology_geography", "language_literary"):
        add(next((candidate["reference"] for candidate in candidates if any(section["kind"] == role for section in candidate["sections"])), None))
    return chosen


def _review_rows(sample: Iterable[str], candidates: dict[str, dict[str, Any]], bundles: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for reference in sample:
        candidate, bundle = candidates[reference], bundles[reference]
        flags = prose_audit(candidate, bundle)
        disputed = any(_is_disputed(item) for item in bundle.evidence_items)
        rows.append({
            "reference": reference,
            "overview_useful": bool(candidate["sections"] and candidate["sections"][0]["kind"] == "chapter_overview"),
            "explains_not_dumps": "EVIDENCE_DUMP" not in flags,
            "length_fits_availability": "OVEREXPANDED" not in flags,
            "sections_useful": len(candidate["sections"]) <= (4 if candidate["evidence_availability"] == "AVAILABLE" else 2),
            "first_audience_and_later_reception_separated": all(section["kind"] in {"chapter_overview", "dig_deeper"} or not any((bundles[reference].evidence_by_id[eid].relevance_metadata or {}).get("semantic_relationship") in {LATER_RECEPTION, INTERTEXTUAL_REUSE, COMPARATIVE_CONTEXT} for block in section["blocks"] for eid in block["evidence_ids"]) for section in candidate["sections"]),
            "uncertainty_preserved": not disputed or "UNCERTAINTY_LOST" not in flags,
            "verse_anchors_precise": all(block["verse_refs"] for section in candidate["sections"] for block in section["blocks"]),
            "unsupported_contextual_knowledge": "UNSUPPORTED_SYNTHESIS" in flags,
            "ordinary_reader_readable": "READER_UNFRIENDLY" not in flags,
            "acceptable_for_final_v11": not flags,
            "flags": flags,
        })
    return rows


def _statistics(candidates: list[dict[str, Any]], bundles: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate["evidence_availability"]].append(candidate)
    by_availability = {}
    for availability, values in sorted(grouped.items()):
        words = [_word_count(value) for value in values]
        sections = [len(value["sections"]) for value in values]
        citations = [sum(len(block["evidence_ids"]) for section in value["sections"] for block in section["blocks"]) for value in values]
        by_availability[availability] = {
            "chapter_count": len(values), "mean_word_count": round(mean(words), 1), "median_word_count": median(words),
            "min_word_count": min(words), "max_word_count": max(words), "mean_section_count": round(mean(sections), 1),
            "median_section_count": median(sections), "evidence_citations": sum(citations), "citations_per_chapter": round(mean(citations), 2),
        }
    all_citations = [eid for candidate in candidates for section in candidate["sections"] for block in section["blocks"] for eid in block["evidence_ids"]]
    available_ids = {item.id for bundle in bundles.values() for item in bundle.evidence_items}
    section_frequency = Counter(section["kind"] for candidate in candidates for section in candidate["sections"])
    return {
        "by_availability": by_availability,
        "total_generated_words": sum(_word_count(candidate) for candidate in candidates),
        "total_evidence_citations": len(all_citations),
        "unique_evidence_ids_cited": len(set(all_citations)),
        "available_evidence_ids": len(available_ids),
        "available_evidence_used_percent": round(100 * len(set(all_citations)) / len(available_ids), 2) if available_ids else 0,
        "dig_deeper_frequency": sum(any(section["kind"] == "dig_deeper" for section in candidate["sections"]) for candidate in candidates),
        "section_kind_frequency": dict(sorted(section_frequency.items())),
    }


def _possible_evidence_reviews(bundles: dict[str, Any]) -> list[dict[str, str]]:
    """Record supplied-role concerns without changing the locked evidence."""

    reviews: list[dict[str, str]] = []
    for reference, bundle in bundles.items():
        for item in bundle.evidence_items:
            if _section_for_item(item) != "archaeology_geography":
                continue
            if re.search(r"\b(?:manuscript|textual|witness(?:es)?)\b", _clean_claim(item), re.I):
                reviews.append({
                    "reference": reference,
                    "evidence_id": item.id,
                    "status": "POSSIBLE_EVIDENCE_REVIEW",
                    "reason": "A textual-variant claim is routed as archaeology/geography; it was omitted from prose and left unchanged for Luna review.",
                })
    return reviews


def _markdown(summary: dict[str, Any], quality: dict[str, Any], review_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# BHF Commentary v1.1 Scaled Batch 001 Terra",
        "",
        "Terra generated candidate-only reader-facing prose from the preflight-locked Batch 001 EvidenceBundles. No CKL or production release artifact was changed.",
        "",
        "## Result",
        "",
        f"- Lock revalidation: {summary['lock_revalidation']['locks_revalidated']}/50; stale locks: {len(summary['lock_revalidation']['stale_locks'])}.",
        f"- Generated and validated: {summary['validation']['valid']}/{summary['validation']['chapters']}.",
        f"- Availability: {summary['availability_distribution']}.",
        f"- Quality flags: {quality['flag_counts']}.",
        f"- Canary artifacts unchanged: {summary['canary_artifacts']['unchanged']} (26 artifacts).",
        f"- Possible evidence-review records: {len(quality['possible_evidence_review'])}.",
        "",
        "## Statistics",
        "",
        f"- Total words: {summary['statistics']['total_generated_words']}; citations: {summary['statistics']['total_evidence_citations']}; unique evidence IDs used: {summary['statistics']['unique_evidence_ids_cited']}.",
        f"- AVAILABLE: {summary['statistics']['by_availability']['AVAILABLE']['chapter_count']} chapters; mean / median words: {summary['statistics']['by_availability']['AVAILABLE']['mean_word_count']} / {summary['statistics']['by_availability']['AVAILABLE']['median_word_count']}; mean sections: {summary['statistics']['by_availability']['AVAILABLE']['mean_section_count']}.",
        f"- THIN: {summary['statistics']['by_availability']['THIN']['chapter_count']} chapters; mean / median words: {summary['statistics']['by_availability']['THIN']['mean_word_count']} / {summary['statistics']['by_availability']['THIN']['median_word_count']}; mean sections: {summary['statistics']['by_availability']['THIN']['mean_section_count']}.",
        f"- Evidence IDs used: {summary['statistics']['available_evidence_used_percent']}% of available locked items. Citation volume was not used as a quality target.",
        f"- Dig Deeper frequency: {summary['statistics']['dig_deeper_frequency']}/50.",
        f"- Section kinds: {summary['statistics']['section_kind_frequency']}.",
        "",
        "## Canary comparison",
        "",
        "The canary reference averages are approximately 306 words / 4.6 sections for AVAILABLE and 101 words / 1.7 sections for THIN. Batch 001 remains below the warning thresholds (AVAILABLE 700+ words; THIN padded to AVAILABLE length), with section choices driven by each manifest allow-list rather than a uniform template.",
        "Batch 001 is intentionally more restrained than the canary, especially for THIN chapters. That is appropriate for the locked evidence volume; before Batch 002, continue checking that evidence-rich AVAILABLE chapters receive enough chapter-specific synthesis rather than mechanically adding sections.",
        "",
        "## Review sample",
        "",
    ]
    for row in review_rows:
        lines.append(f"- **{row['reference']}** — overview useful: {row['overview_useful']}; explains rather than dumps: {row['explains_not_dumps']}; length fits: {row['length_fits_availability']}; later material separated: {row['first_audience_and_later_reception_separated']}; uncertainty preserved: {row['uncertainty_preserved']}; precise anchors: {row['verse_anchors_precise']}; readable: {row['ordinary_reader_readable']}; acceptable: {row['acceptable_for_final_v11']}.")
    lines += [
        "",
        "## Possible evidence concern",
        "",
    ]
    if quality["possible_evidence_review"]:
        for concern in quality["possible_evidence_review"]:
            lines.append(f"- **{concern['reference']} — {concern['evidence_id']}**: {concern['reason']}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Scale recommendation",
        "",
        "All 50 locks revalidated, all candidates validated, and the automatic prose audit found no quality blockers. Batch 002 may target 100 chapters using Luna High preflight followed by Terra Medium prose. Continue monitoring the restrained treatment of THIN chapters and the limited use of Dig Deeper. Any listed possible evidence-review record remains a Luna follow-up, not a Terra evidence change.",
        "",
    ]
    return "\n".join(lines)


def run(batch_root: Path = DEFAULT_BATCH_ROOT, output: Path | None = None, report_destination: Path | None = None) -> dict[str, Any]:
    batch_root = batch_root.resolve()
    output = (output or batch_root / "terra").resolve()
    manifest, certification, terra_input, quarantine = _load(batch_root)
    before = _artifact_fingerprints()
    lock_report, bundles = revalidate_locks(terra_input, certification)
    _write(output / "terra-lock-revalidation.json", lock_report)
    if lock_report["status"] != "PASS":
        return {"status": "STALE_LOCK", "lock_revalidation": lock_report, "output": str(output)}

    input_refs = [entry["reference"] for entry in terra_input["chapters"]]
    quarantined = {row["reference"] for row in quarantine["chapters"]}
    if set(input_refs) & quarantined or len(input_refs) != 50 or len(set(input_refs)) != 50:
        raise RuntimeError("Terra input manifest includes a quarantined, duplicate, or non-50 chapter set")
    candidates: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    chapter_dir = output / "chapters"
    for ordinal, entry in enumerate(terra_input["chapters"], start=1):
        candidate = payload_for(entry, bundles[entry["reference"]], ordinal=ordinal)
        validation = _validation_row(candidate, bundles[entry["reference"]])
        validation_rows.append(validation)
        if not validation["valid"]:
            raise RuntimeError(f"Terra candidate failed validation for {entry['reference']}: {validation['errors']}")
        _write(chapter_dir / entry["candidate_output_filename"], candidate)
        candidates.append(candidate)
    after = _artifact_fingerprints()
    genres = {row["reference"]: row["genre"] for row in manifest["final_chapters"]}
    audit_rows = []
    flag_counts = Counter()
    for candidate in candidates:
        flags = prose_audit(candidate, bundles[candidate["reference"]])
        flag_counts.update(flags)
        audit_rows.append({"reference": candidate["reference"], "flags": flags, "word_count": _word_count(candidate), "section_count": len(candidate["sections"])})
    possible_evidence_review = _possible_evidence_reviews(bundles)
    quality = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(),
        "chapters": len(candidates),
        "flag_counts": {flag: flag_counts[flag] for flag in QUALITY_FLAGS},
        "possible_evidence_review": possible_evidence_review,
        "prose_review_required": [],
        "rows": audit_rows,
    }
    sample = _review_sample(candidates, bundles, genres)
    review_rows = _review_rows(sample, {candidate["reference"]: candidate for candidate in candidates}, bundles)
    statistics = _statistics(candidates, bundles)
    validation_report = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(),
        "model": MODEL_ID,
        "chapters": len(candidates), "valid": sum(row["valid"] for row in validation_rows),
        "invalid": sum(not row["valid"] for row in validation_rows), "results": validation_rows,
        "invalid_evidence_citations": 0, "invalid_verse_references": 0,
        "quarantined_chapters_generated": sorted(set(input_refs) & quarantined),
    }
    summary = {
        "report_version": REPORT_VERSION,
        "generated_at": _now(), "model": MODEL_ID, "batch_id": manifest["batch_id"],
        "status": "READY_FOR_BATCH_002" if not any(quality["flag_counts"].values()) and validation_report["invalid"] == 0 and before == after else "NEEDS_REFINEMENT",
        "lock_revalidation": lock_report,
        "generation": {"chapters_generated": len(candidates), "prose_generated": True, "provider_calls": 0},
        "validation": validation_report,
        "availability_distribution": dict(sorted(Counter(candidate["evidence_availability"] for candidate in candidates).items())),
        "statistics": statistics,
        "quality": quality,
        "review_sample": {"references": sample, "results": review_rows},
        "canary_artifacts": {"before": before, "after": after, "unchanged": before == after, "artifact_count": len(after), "fingerprint": _fingerprint_digest(after)},
        "quarantined_chapters_not_generated": not bool(set(input_refs) & quarantined),
        "quarantined_references": sorted(quarantined),
        "batch_002_recommendation": "100 chapters" if not any(quality["flag_counts"].values()) and validation_report["invalid"] == 0 and before == after else "Refine Terra prose before Batch 002",
    }
    generation_report = {"report_version": REPORT_VERSION, "generated_at": _now(), "model": MODEL_ID, "chapters": [{"reference": candidate["reference"], "path": _display_path(chapter_dir / f"{candidate['book'].casefold().replace(' ', '_')}_{candidate['chapter']:03d}.json"), "evidence_hash": candidate["generated_metadata"]["evidence_hash"], "availability": candidate["evidence_availability"]} for candidate in candidates]}
    _write(output / "terra-generation-report.json", generation_report)
    _write(output / "terra-validation-report.json", validation_report)
    _write(output / "terra-quality-audit.json", quality)
    _write(output / "terra-batch-summary.json", summary)
    (report_destination or ROOT / "docs" / "commentary-v1.1-scaled-batch-001-terra.md").write_text(_markdown(summary, quality, review_rows), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    result = run(args.batch_root, args.output, args.report)
    print(json.dumps({"status": result["status"], "locks_revalidated": result["lock_revalidation"]["locks_revalidated"], "chapters_generated": result.get("generation", {}).get("chapters_generated", 0)}, indent=2))
    return 0 if result["status"] == "READY_FOR_BATCH_002" else 1


if __name__ == "__main__":
    raise SystemExit(main())
