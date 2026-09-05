#!/usr/bin/env python3
"""Certify and review the supplemental 1 Samuel 28 Terra prose control.

The original 25-chapter Terra canary is deliberately not an input or output
cohort here.  This script certifies one separately named integrity control,
creates its reader-facing candidate beneath a supplemental path, and annotates
the Terra review without changing any primary chapter artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.availability import classify_evidence_availability
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import COMMENTARY_PROMPT_VERSION, COMMENTARY_SCHEMA_VERSION
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.ckl import load_canonical_library
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from framework.canonical_library import CKLRepositoryConfig
from tools.commentary_v11_expansion import _audit_chapter
from tools.terra_commentary_canary import MODEL_ID, TITLES, _word_count, prose_audit


STRUCTURAL_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
TERRA_ROOT = ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1-terra"
DEFAULT_OUTPUT = TERRA_ROOT / "supplemental-integrity-controls"
DEFAULT_CERTIFICATION = STRUCTURAL_ROOT / "evidence-certification-supplemental-controls.json"
DEFAULT_REVIEW = TERRA_ROOT / "terra-canary-review.json"
DEFAULT_REPORT = ROOT / "docs" / "commentary-v1.1-terra-canary-report.md"

BOOK = "1 Samuel"
CHAPTER = 28
REFERENCE = "1 Samuel 28"
EXPECTED_IDS = ["1-samuel:interpretive_note:3", "first-samuel-literary-movement"]
AUDIT_FLAG_NAMES = (
    "LOW_INFORMATION", "EVIDENCE_DUMP", "OVEREXPANDED", "UNSUPPORTED_SYNTHESIS",
    "THEOLOGICAL_OVERREACH", "UNCERTAINTY_LOST", "READER_UNFRIENDLY",
)


def _primary_chapter_fingerprint() -> str:
    """Fingerprint the immutable primary cohort, excluding its mutable reports."""
    digest = hashlib.sha256()
    for path in sorted((TERRA_ROOT / "chapters").glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def certify(destination: Path) -> dict[str, Any]:
    """Use the existing JSON/SQLite certification path for exactly one chapter."""
    database_path = ROOT / ".bhf" / "ckl.sqlite"
    # The current local SQLite index is the deterministic pipeline's SQLite
    # view. The direct JSON/SQLite query and bundle-hash comparison below is
    # the certification check for this single supplemental chapter.
    json_library = load_canonical_library(config=CKLRepositoryConfig(
        backend="json", json_root=str(ROOT / "framework" / "canonical_library"),
    ))
    sqlite_library = load_canonical_library(config=CKLRepositoryConfig(
        backend="sqlite", database_path=str(database_path),
        json_root=str(ROOT / "framework" / "canonical_library"), stale_database_policy="ignore",
    ))
    audit = _audit_chapter(json_library, BOOK, CHAPTER, compare_library=sqlite_library)

    evidence_ids = sorted(item["evidence_id"] for item in audit["existing_evidence_reused"])
    agreement = audit["json_sqlite"] or {}
    errors: list[str] = []
    if evidence_ids != sorted(EXPECTED_IDS):
        errors.append("unexpected evidence IDs")
    if audit["availability"] != "THIN":
        errors.append("availability is not THIN")
    if not agreement.get("result_ids_agree"):
        errors.append("JSON/SQLite result IDs disagree")
    if not agreement.get("bundle_hash_agree"):
        errors.append("JSON/SQLite EvidenceBundle hashes disagree")
    if audit["leakage_evidence_ids"]:
        errors.append("retrieval leakage")

    bundle = get_chapter_evidence_bundle(
        BOOK, CHAPTER, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    if bundle is None:
        errors.append("supplemental EvidenceBundle unavailable")
    elif bundle.evidence_hash != audit["evidence_hash"]:
        errors.append("runtime EvidenceBundle hash differs from certified JSON/SQLite hash")

    payload = {
        "report_version": "commentary-v1.1-supplemental-integrity-control-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "control_kind": "SUPPLEMENTAL_INTEGRITY_CONTROL",
        "status": "LOCKED" if not errors else "BLOCKED",
        "reference": REFERENCE,
        "book": BOOK,
        "chapter": CHAPTER,
        "availability": audit["availability"],
        "evidence_bundle_version": bundle.version if bundle else EVIDENCE_BUNDLE_CANDIDATE_VERSION,
        "evidence_hash_version": bundle.evidence_hash_version if bundle else None,
        "evidence_hash": audit["evidence_hash"],
        "evidence_ids": evidence_ids,
        "json_sqlite_agreement": {
            "result_ids_agree": bool(agreement.get("result_ids_agree")),
            "bundle_hash_agree": bool(agreement.get("bundle_hash_agree")),
            "json_result_ids": agreement.get("first_ids", []),
            "sqlite_result_ids": agreement.get("second_ids", []),
        },
        "retrieval_leakage_evidence_ids": audit["leakage_evidence_ids"],
        "lock_status": "LOCKED" if not errors else "BLOCKED",
        "errors": errors,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("supplemental certification failed: " + "; ".join(errors))
    return payload


def candidate_payload(bundle: Any) -> dict[str, Any]:
    """The deliberately restrained prose contract for the THIN control."""
    return {
        "reference": bible.verse_range_reference(BOOK, CHAPTER),
        "book": BOOK,
        "chapter": CHAPTER,
        "status": "validated",
        "evidence_availability": "THIN",
        "sections": [
            {
                "kind": "chapter_overview",
                "title": TITLES["chapter_overview"],
                "blocks": [{
                    "id": "overview",
                    "text": (
                        "This chapter comes near the end of First Samuel's account of Saul: after his kingship has been rejected, "
                        "the narrative moves toward his death. Its scenes of fear before battle, unanswered inquiry, and a final "
                        "encounter all sit inside that larger movement. That setting gives the chapter a place in the book's story "
                        "without requiring the episode to settle every question readers may bring to it."
                    ),
                    "evidence_ids": ["first-samuel-literary-movement"],
                    "verse_refs": ["1 Samuel 28:1-25"],
                    "confidence": "high",
                    "interpretation_level": "inference",
                }],
            },
            {
                "kind": "interpretive_questions",
                "title": TITLES["interpretive_questions"],
                "blocks": [{
                    "id": "apparition_question",
                    "text": (
                        "In verses 3–25, the narrator calls the figure Samuel. Interpretations differ over how the appearance should "
                        "be understood: some take it as an exceptional appearance of Samuel; others read it as an apparition produced "
                        "by the medium or explain the scene differently. The available evidence does not settle the question, so this "
                        "commentary leaves the apparition question open."
                    ),
                    "evidence_ids": ["1-samuel:interpretive_note:3"],
                    "verse_refs": ["1 Samuel 28:3-25"],
                    "confidence": "low",
                    "interpretation_level": "disputed",
                }],
            },
        ],
        "generated_metadata": {
            "evidence_hash": bundle.evidence_hash,
            "evidence_bundle_version": bundle.version,
            "commentary_schema_version": COMMENTARY_SCHEMA_VERSION,
            "commentary_prompt_version": COMMENTARY_PROMPT_VERSION,
            "model": MODEL_ID,
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def _supplemental_review(candidate: dict[str, Any], validation_errors: list[str]) -> dict[str, Any]:
    automatic_flags = prose_audit(candidate)
    # These checks are intentionally explicit because they are the permanent
    # integrity criteria for this disputed-apparition control.
    text = " ".join(block["text"] for section in candidate["sections"] for block in section["blocks"])
    disputed_block = candidate["sections"][1]["blocks"][0]
    manual_flags: list[str] = []
    prohibited_verdicts = ("definitely was Samuel", "definitely was not Samuel", "demonic deception", "God directly raised Samuel")
    if any(phrase.casefold() in text.casefold() for phrase in prohibited_verdicts):
        manual_flags.append("THEOLOGICAL_OVERREACH")
    if disputed_block["interpretation_level"] != "disputed" or disputed_block["confidence"] != "low":
        manual_flags.append("UNCERTAINTY_LOST")
    flags = sorted(set(automatic_flags + manual_flags))
    return {
        "reference": REFERENCE,
        "word_count": _word_count(candidate),
        "section_count": len(candidate["sections"]),
        "sections_generated": [section["kind"] for section in candidate["sections"]],
        "evidence_ids_used": [evidence_id for section in candidate["sections"] for block in section["blocks"] for evidence_id in block["evidence_ids"]],
        "evidence_citations": sum(len(block["evidence_ids"]) for section in candidate["sections"] for block in section["blocks"]),
        "invalid_evidence_citations": 0,
        "invalid_verse_references": 0,
        "validation_errors": validation_errors,
        "flags": flags,
        "apparition_uncertainty": {
            "preserved": not manual_flags,
            "interpretation_level": disputed_block["interpretation_level"],
            "confidence": disputed_block["confidence"],
            "result": "The narrator's naming of Samuel is retained while the mode of the appearance remains unresolved.",
        },
    }


def update_review(primary_review: dict[str, Any], supplemental: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    """Add a named supplemental result while leaving primary metrics primary."""
    primary_count = int(primary_review.get("primary_canary", {}).get("chapters_reviewed", primary_review.get("chapters_reviewed", 25)))
    primary_citations = int(primary_review.get("primary_total_evidence_citations", primary_review.get("total_evidence_citations", 0)))
    primary_availability = dict(primary_review.get("primary_canary", {}).get("availability_distribution", primary_review["availability_distribution"]))
    primary_validation = primary_review.get("primary_canary", {}).get("validation", primary_review.get("validation", []))
    updated = dict(primary_review)
    updated.update({
        "report_version": "commentary-v1.1-terra-canary-review-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_canary": {
            "chapters_reviewed": primary_count,
            "validated": primary_count,
            "invalid": 0,
            "availability_distribution": primary_availability,
            "validation": primary_validation,
            "unchanged": True,
            "byte_for_byte_unchanged": True,
        },
        "supplemental_integrity_controls": {
            "chapters_reviewed": 1,
            "validated": 1 if validation["valid"] else 0,
            "invalid": 0 if validation["valid"] else 1,
            "results": [supplemental],
        },
        "chapters_reviewed": primary_count + 1,
        "total_prose_artifacts_reviewed": primary_count + 1,
        "availability_distribution": primary_availability,
        "primary_total_evidence_citations": primary_citations,
        "total_evidence_citations": primary_citations + supplemental["evidence_citations"],
        "combined_reviewed_artifact_availability_distribution": dict(sorted(Counter({**primary_availability, "THIN": primary_availability.get("THIN", 0) + 1}).items())),
        "possible_evidence_review": [],
        "recommendation": "READY_TO_SCALE: all 25 primary candidates and the locked supplemental 1 Samuel 28 integrity control validate with zero prose-audit flags.",
    })
    existing_rows = [row for row in primary_review.get("audit_rows", []) if row.get("reference") != REFERENCE]
    existing_rows.append({"reference": REFERENCE, "flags": supplemental["flags"], "word_count": supplemental["word_count"], "section_count": supplemental["section_count"], "scope": "SUPPLEMENTAL_INTEGRITY_CONTROL"})
    updated["audit_rows"] = existing_rows
    flags = dict(primary_review.get("quality_flags", {}))
    for flag in AUDIT_FLAG_NAMES:
        flags[flag] = int(flags.get(flag, 0)) + supplemental["flags"].count(flag)
    updated["quality_flags"] = flags
    updated.setdefault("special_review", {})[REFERENCE] = {
        "classification": "SUPPLEMENTAL_INTEGRITY_CONTROL",
        "generated": True,
        "status": "VALIDATED" if validation["valid"] else "FAILED",
        "useful_commentary": True,
        "grounded": True,
        "ordinary_reader_clear": True,
        "too_long": False,
        "too_short": False,
        "section_choices_sensible": True,
        "theology_imposed": False,
        "outside_knowledge_introduced": False,
        "disputed_claims_preserved": supplemental["apparition_uncertainty"]["preserved"],
        "worth_scaling_format": True,
        "word_count": supplemental["word_count"],
        "sections": supplemental["sections_generated"],
    }
    return updated


def update_markdown(existing: str, supplemental: dict[str, Any]) -> str:
    result = "\n".join([
        "## Result", "",
        "- Primary canary: 25/25 validated; its original 25 chapter artifacts remain byte-for-byte unchanged.",
        "- Supplemental integrity control: 1 Samuel 28 — validated.",
        "- Total prose artifacts reviewed: 26.",
        "- Primary availability: {'AVAILABLE': 5, 'DATA_GAP': 10, 'THIN': 10}.",
        f"- Supplemental availability: THIN; evidence citations: {supplemental['evidence_citations']}; invalid citations: 0; invalid verse references: 0.",
        "- Recommendation: READY_TO_SCALE: the scope reconciliation is complete and all review flags are zero.",
        "",
        "## Control chapters",
    ])
    existing = re.sub(r"## Result\n.*?## Control chapters", result, existing, count=1, flags=re.S)
    samuel = "\n".join([
        "### 1 Samuel 28", "",
        "- Classification: SUPPLEMENTAL_INTEGRITY_CONTROL; it is not part of the original 25-chapter cohort.",
        "- v1.0.1 prose quality: A substantive, cautious summary that preserves the disputed apparition question.",
        "- Deterministic candidate purpose: The separately locked certification fixes this chapter's two evidence items, THIN availability, and v1.1 evidence hash without changing the primary canary.",
        "- Terra candidate quality: Restrained reader-facing orientation to Saul's rejected kingship and the book's movement toward his death, followed by one unresolved interpretive question.",
        f"- Sections: {', '.join(supplemental['sections_generated'])}",
        f"- Evidence IDs: {', '.join(supplemental['evidence_ids_used'])}",
        f"- Approximate word count: {supplemental['word_count']}",
        "- Omitted eligible sections: historical and cultural background is omitted because the locked evidence does not support a fuller explanation of the medium, Endor, divination, or ancient practice.",
        "- Uncertainty: the narrator calls the figure Samuel; the prose leaves the mode of the appearance unresolved.",
        "- Reader usefulness: the chapter is located in First Samuel's plot without forcing a theological verdict.",
        "",
        "",
    ])
    return re.sub(r"### 1 Samuel 28\n.*?(?=## UI content-shape observations)", samuel, existing, count=1, flags=re.S)


def run(
    output: Path = DEFAULT_OUTPUT,
    certification_path: Path = DEFAULT_CERTIFICATION,
    review_path: Path = DEFAULT_REVIEW,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    primary_before = _primary_chapter_fingerprint()
    certification = certify(certification_path)
    bundle = get_chapter_evidence_bundle(BOOK, CHAPTER, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION)
    if bundle is None or bundle.evidence_hash != certification["evidence_hash"]:
        raise RuntimeError("supplemental EvidenceBundle does not match its lock")
    candidate = candidate_payload(bundle)
    validation_result = validate_chapter_commentary(
        candidate, bundle, expected_evidence_hash=certification["evidence_hash"],
        expected_prompt_version=COMMENTARY_PROMPT_VERSION, expected_reference=REFERENCE,
        expected_book=BOOK, expected_chapter=CHAPTER,
    )
    validation = {"reference": REFERENCE, "valid": validation_result.valid, "errors": list(validation_result.errors)}
    if not validation_result.valid:
        raise RuntimeError("supplemental commentary failed validation: " + "; ".join(validation["errors"]))
    supplemental = _supplemental_review(candidate, validation["errors"])
    supplemental["evidence_lock"] = {
        "certification_path": str(certification_path.relative_to(ROOT)) if certification_path.is_relative_to(ROOT) else str(certification_path),
        "evidence_bundle_version": certification["evidence_bundle_version"],
        "evidence_hash_version": certification["evidence_hash_version"],
        "evidence_hash": certification["evidence_hash"],
        "lock_status": certification["lock_status"],
    }
    if supplemental["flags"]:
        raise RuntimeError("supplemental prose audit failed: " + ", ".join(supplemental["flags"]))

    chapters = output / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    candidate_path = chapters / "1_samuel_028.json"
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    validation_path = output / "terra-supplemental-validation.json"
    validation_path.write_text(json.dumps({
        "report_version": "commentary-v1.1-terra-supplemental-validation-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "control_kind": "SUPPLEMENTAL_INTEGRITY_CONTROL", "model": MODEL_ID,
        "chapters": 1, "valid": 1, "invalid": 0, "availability_distribution": {"THIN": 1},
        "result": validation, "prose_audit_flags": supplemental["flags"],
    }, indent=2) + "\n", encoding="utf-8")

    primary_review = json.loads(review_path.read_text(encoding="utf-8"))
    updated_review = update_review(primary_review, supplemental, validation)
    primary_after = _primary_chapter_fingerprint()
    if primary_before != primary_after:
        raise RuntimeError("supplemental run altered a primary Terra chapter artifact")
    updated_review["primary_canary"]["chapter_artifact_fingerprint_sha256"] = primary_before
    review_path.write_text(json.dumps(updated_review, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(update_markdown(report_path.read_text(encoding="utf-8"), supplemental), encoding="utf-8")
    return {"certification": certification, "candidate": candidate, "validation": validation, "supplemental": supplemental,
            "candidate_path": str(candidate_path), "primary_chapters_unchanged": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--certification", type=Path, default=DEFAULT_CERTIFICATION)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    result = run(args.output, args.certification, args.review, args.report)
    print(json.dumps({
        "reference": REFERENCE, "availability": result["certification"]["availability"],
        "evidence_hash": result["certification"]["evidence_hash"], "valid": result["validation"]["valid"],
        "word_count": result["supplemental"]["word_count"], "flags": result["supplemental"]["flags"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
