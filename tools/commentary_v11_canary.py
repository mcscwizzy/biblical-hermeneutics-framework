#!/usr/bin/env python3
"""Materialize and validate the locked Commentary v1.1 canary.

The canary is a provider-independent candidate compiler: it may quote and
organize locked CKL claims, but it cannot create contextual claims.  A future
Luna or Terra prose pass can consume the same canonical chapter, locked bundle,
section allow-list, and grounding constraints without changing this boundary.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bhf_agent import bible
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.models import (
    COMMENTARY_PROMPT_VERSION,
    COMMENTARY_SCHEMA_VERSION,
    ChapterCommentary,
    CommentaryBlock,
    CommentarySection,
    CommentaryStatus,
    GeneratedMetadata,
)
from bhf_agent.chapter_commentary.storage import save_commentary
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / ".bhf-data" / "bhf-commentary-candidates" / "commentary-v1.1"
MODEL_ID = "deterministic-v1.1-evidence-candidate"

SECTION_BY_CATEGORY = {
    "culture": "historical_context",
    "history": "historical_context",
    "politics": "historical_context",
    "social": "historical_context",
    "economics": "historical_context",
    "geography": "archaeology_geography",
    "archaeology": "archaeology_geography",
    "language": "language_literary",
    "chronology": "chronology",
}
SECTION_TITLES = {
    "chapter_overview": "Chapter overview",
    "historical_context": "Historical and social context",
    "archaeology_geography": "Archaeology and geography",
    "language_literary": "Language and literary context",
    "chronology": "Chronology",
}


def _reference(book: str, chapter: int) -> str:
    return bible.verse_range_reference(book, chapter)


def _verse_reference(book: str, chapter: int) -> str:
    chapter_data = bible.resolve_chapter(book, chapter)
    return f"{book} {chapter}:1-{len(chapter_data['verses'])}"


def _block_for_item(item: Any, reference: str, index: int) -> CommentaryBlock:
    dispute = str(item.relevance_metadata.get("dispute_status") or "").casefold()
    interpretation = "disputed" if dispute not in {"", "not_disputed"} else "fact"
    confidence = item.confidence if item.confidence in {"low", "medium", "high"} else "medium"
    text = f"Locked CKL evidence: {item.claim}"
    return CommentaryBlock(
        id=f"evidence_{index + 1}",
        text=text,
        verse_refs=[reference],
        evidence_ids=[item.id],
        confidence=confidence,
        interpretation_level=interpretation,
    )


def _candidate_payload(book: str, chapter: int, bundle: Any) -> dict[str, Any]:
    reference = _reference(book, chapter)
    verse_reference = _verse_reference(book, chapter)
    availability = __import__(
        "bhf_agent.chapter_commentary.availability",
        fromlist=["classify_evidence_availability"],
    ).classify_evidence_availability(bundle).value
    sections: list[CommentarySection] = []
    if availability == "DATA_GAP":
        sections.append(
            CommentarySection(
                kind="chapter_overview",
                title=SECTION_TITLES["chapter_overview"],
                blocks=[
                    CommentaryBlock(
                        id="overview",
                        text=(
                            f"BHF does not currently have source-addressable contextual evidence for {reference}. "
                            "This v1.1 candidate preserves the gap rather than supplying historically plausible but unsupported context."
                        ),
                        verse_refs=[verse_reference],
                        evidence_ids=[],
                        confidence="high",
                        interpretation_level="fact",
                    )
                ],
            )
        )
    else:
        overview_item = bundle.evidence_items[0]
        sections.append(
            CommentarySection(
                kind="chapter_overview",
                title=SECTION_TITLES["chapter_overview"],
                blocks=[
                    CommentaryBlock(
                        id="overview",
                        text=(
                            f"This chapter's locked contextual evidence is limited to {len(bundle.evidence_items)} "
                            f"source-addressable item(s) across {', '.join(sorted({item.category for item in bundle.evidence_items}))}. "
                            f"The first anchored observation is: {overview_item.claim}"
                        ),
                        verse_refs=[verse_reference],
                        evidence_ids=[overview_item.id],
                        confidence=overview_item.confidence if overview_item.confidence in {"low", "medium", "high"} else "medium",
                        interpretation_level="disputed" if overview_item.relevance_metadata.get("dispute_status") not in {None, "", "not_disputed"} else "fact",
                    )
                ],
            )
        )
        grouped: dict[str, list[Any]] = defaultdict(list)
        for item in bundle.evidence_items:
            kind = SECTION_BY_CATEGORY.get(item.category, "historical_context")
            if item.id != overview_item.id:
                grouped[kind].append(item)
        max_sections = 2 if availability == "THIN" else 4
        for kind in sorted(grouped):
            if len(sections) - 1 >= max_sections:
                break
            items = grouped[kind][:2]
            sections.append(
                CommentarySection(
                    kind=kind,
                    title=SECTION_TITLES[kind],
                    blocks=[_block_for_item(item, verse_reference, index) for index, item in enumerate(items)],
                )
            )
    metadata = GeneratedMetadata(
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=COMMENTARY_PROMPT_VERSION,
        model=MODEL_ID,
        generated_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return {
        "reference": reference,
        "book": book,
        "chapter": chapter,
        "status": CommentaryStatus.VALIDATED.value,
        "evidence_availability": availability,
        "sections": [section.to_dict() for section in sections],
        "generated_metadata": metadata.to_dict(),
    }


def run(priority_report: Path, certification: Path, output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    report = json.loads(priority_report.read_text(encoding="utf-8"))
    locked = json.loads(certification.read_text(encoding="utf-8"))
    if locked.get("status") != "LOCKED":
        raise RuntimeError("commentary canary requires a LOCKED evidence certification")
    locked_hashes = locked.get("locked_evidence_bundle_hashes", {})
    rows = report["selected_batches"]["commentary_canary"]
    results = []
    for row in rows:
        book, chapter = row["book"], int(row["chapter"])
        bundle = get_chapter_evidence_bundle(book, chapter)
        if bundle is None:
            raise RuntimeError(f"unable to rebuild locked EvidenceBundle for {book} {chapter}")
        reference = _reference(book, chapter)
        if locked_hashes.get(reference) != bundle.evidence_hash:
            raise RuntimeError(f"EvidenceBundle changed after lock for {reference}")
        payload = _candidate_payload(book, chapter, bundle)
        validation = validate_chapter_commentary(
            payload,
            bundle,
            expected_evidence_hash=bundle.evidence_hash,
            expected_prompt_version=COMMENTARY_PROMPT_VERSION,
            expected_reference=reference,
            expected_book=book,
            expected_chapter=chapter,
        )
        if not validation.valid or validation.commentary is None:
            results.append({"reference": reference, "valid": False, "errors": list(validation.errors)})
            continue
        commentary = ChapterCommentary(
            reference=reference,
            book=book,
            chapter=chapter,
            status=CommentaryStatus.VALIDATED.value,
            evidence_availability=validation.commentary.evidence_availability,
            sections=list(validation.accepted_sections),
            generated_metadata=validation.commentary.generated_metadata,
            validation_errors=[],
            validation_warnings=[],
        )
        path = save_commentary(commentary, output_root)
        results.append({
            "reference": reference,
            "valid": True,
            "availability": commentary.evidence_availability,
            "section_kinds": [section.kind for section in commentary.sections],
            "evidence_ids": sorted({evidence_id for section in commentary.sections for block in section.blocks for evidence_id in block.evidence_ids}),
            "path": str(path),
        })
    summary = {
        "report_version": "commentary-v1.1-canary-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_boundary": {
            "provider": "none",
            "model": MODEL_ID,
            "future_prompt_inputs": ["canonical chapter text", "locked EvidenceBundle", "allowed section kinds", "grounding constraints"],
        },
        "candidate_root": str(output_root),
        "chapters": len(results),
        "valid": sum(result["valid"] for result in results),
        "invalid": sum(not result["valid"] for result in results),
        "availability_distribution": dict(sorted(__import__("collections").Counter(result.get("availability") for result in results).items())),
        "results": results,
    }
    (output_root / "commentary-canary-validation.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority-report", type=Path, default=DEFAULT_ROOT / "data-gap-priority.json")
    parser.add_argument("--certification", type=Path, default=DEFAULT_ROOT / "evidence-certification-commentary_canary.json")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT / "chapters")
    args = parser.parse_args(argv)
    summary = run(args.priority_report, args.certification, args.output_root)
    print(json.dumps({key: summary[key] for key in ("chapters", "valid", "invalid", "availability_distribution", "candidate_root")}, indent=2))
    return 0 if summary["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
