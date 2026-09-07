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
from bhf_agent.presentation.relevance import (
    BOOK_CONTEXT,
    COMPARATIVE_CONTEXT,
    DIRECT_CONTEXT,
    GENERIC_BACKGROUND,
    INTERTEXTUAL_REUSE,
    LATER_RECEPTION,
    SEMANTICALLY_MISANCHORED,
    WEAKLY_RELATED,
)
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import parse_scripture_references


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
    "interpretive_questions": "Interpretive questions",
    "dig_deeper": "Dig deeper",
}


def _reference(book: str, chapter: int) -> str:
    return bible.verse_range_reference(book, chapter)


def _verse_reference(book: str, chapter: int) -> str:
    chapter_data = bible.resolve_chapter(book, chapter)
    return f"{book} {chapter}:1-{len(chapter_data['verses'])}"


def _interpretation_level(item: Any) -> str:
    metadata = item.relevance_metadata or {}
    dispute = str(metadata.get("dispute_status") or "").casefold()
    if dispute not in {"", "not_disputed", "unknown", "none"}:
        return "disputed"
    assertion = str(metadata.get("assertion_type") or "").casefold().replace("_", "-")
    if assertion in {
        "fact",
        "factual",
        "explicit",
        "explicit-fact",
        "historical-fact",
        "textual-observation",
        "primary-evidence",
    } or str(metadata.get("certainty") or "").casefold() == "textually_explicit":
        return "fact"
    return "inference"


def _chapter_overlap_refs(item: Any, book: str | None, chapter: int | None) -> list[str]:
    if not book or chapter is None:
        return list(item.passage_anchors)
    try:
        verse_count = len(bible.resolve_chapter(book, chapter)["verses"])
    except bible.BibleError:
        return list(item.passage_anchors)
    refs: list[str] = []
    for anchor in item.passage_anchors:
        spans = parse_scripture_references(anchor, book_alias_lookup=_BOOK_ALIASES)
        for span in spans:
            if span.book != book or span.start_chapter is None:
                continue
            end_chapter = span.end_chapter or span.start_chapter
            if not (span.start_chapter <= chapter <= end_chapter):
                continue
            same_chapter = span.start_chapter == chapter and end_chapter == chapter
            start_verse = span.start_verse if same_chapter and span.start_verse else 1
            if same_chapter and span.start_verse is not None:
                end_verse = span.end_verse or span.start_verse
            else:
                end_verse = span.end_verse if end_chapter == chapter and span.end_verse else verse_count
            ref = f"{book} {chapter}:{start_verse}"
            if end_verse != start_verse:
                ref += f"-{end_verse}"
            if ref not in refs:
                refs.append(ref)
    return refs or list(item.passage_anchors)


def _block_for_item(item: Any, index: int, book: str | None = None, chapter: int | None = None) -> CommentaryBlock:
    confidence = item.confidence if item.confidence in {"low", "medium", "high"} else "medium"
    text = f"Locked CKL evidence: {item.claim}"
    return CommentaryBlock(
        id=f"evidence_{index + 1}",
        text=text,
        verse_refs=_chapter_overlap_refs(item, book, chapter),
        evidence_ids=[item.id],
        confidence=confidence,
        interpretation_level=_interpretation_level(item),
    )


def _role(item: Any) -> str:
    return str((item.relevance_metadata or {}).get("semantic_relationship") or WEAKLY_RELATED)


def _section_for_item(item: Any) -> str | None:
    metadata = item.relevance_metadata or {}
    role = _role(item)
    category = str(item.category or "").casefold()
    if role in {SEMANTICALLY_MISANCHORED, WEAKLY_RELATED}:
        return None
    if "presentation_role" in metadata:
        preferred = metadata.get("presentation_role")
        return preferred if preferred in SECTION_TITLES and preferred != "chapter_overview" else None
    if role in {LATER_RECEPTION, INTERTEXTUAL_REUSE, COMPARATIVE_CONTEXT}:
        return "dig_deeper"
    if category in {"language"}:
        return "language_literary"
    if category in {"archaeology", "geography"}:
        return "archaeology_geography" if role == DIRECT_CONTEXT else None
    return SECTION_BY_CATEGORY.get(category, "historical_context")


def eligible_for_section(item: Any, section_kind: str) -> bool:
    """Return whether an evidence item may ground a deterministic section."""

    if section_kind == "chapter_overview":
        if "presentation_role" in (item.relevance_metadata or {}):
            return bool((item.relevance_metadata or {}).get("presentation_role")) and _role(item) in {
                DIRECT_CONTEXT,
                BOOK_CONTEXT,
                GENERIC_BACKGROUND,
            }
        return _role(item) in {DIRECT_CONTEXT, BOOK_CONTEXT, GENERIC_BACKGROUND} and not (
            item.category in {"archaeology", "geography"}
            and _role(item) == GENERIC_BACKGROUND
        )
    if section_kind == "historical_context":
        if "presentation_role" in (item.relevance_metadata or {}):
            return (item.relevance_metadata or {}).get("presentation_role") == section_kind
        return _role(item) in {DIRECT_CONTEXT, BOOK_CONTEXT, GENERIC_BACKGROUND} and item.category not in {
            "archaeology", "geography", "language",
        }
    if section_kind == "archaeology_geography":
        if "presentation_role" in (item.relevance_metadata or {}):
            return (item.relevance_metadata or {}).get("presentation_role") == section_kind
        return _role(item) == DIRECT_CONTEXT and item.category in {"archaeology", "geography"}
    if section_kind == "language_literary":
        if "presentation_role" in (item.relevance_metadata or {}):
            return (item.relevance_metadata or {}).get("presentation_role") == section_kind
        return _role(item) in {DIRECT_CONTEXT, BOOK_CONTEXT, GENERIC_BACKGROUND} and item.category in {
            "language",
            "culture",
        }
    if section_kind == "chronology":
        if "presentation_role" in (item.relevance_metadata or {}):
            return (item.relevance_metadata or {}).get("presentation_role") == section_kind
        return _role(item) in {DIRECT_CONTEXT, BOOK_CONTEXT} and item.category == "chronology"
    if section_kind == "interpretive_questions":
        return _role(item) not in {SEMANTICALLY_MISANCHORED, WEAKLY_RELATED}
    if section_kind == "dig_deeper":
        if "presentation_role" in (item.relevance_metadata or {}):
            return (item.relevance_metadata or {}).get("presentation_role") == section_kind
        return _role(item) in {
            INTERTEXTUAL_REUSE,
            LATER_RECEPTION,
            COMPARATIVE_CONTEXT,
            GENERIC_BACKGROUND,
        }
    return False


def select_overview_item(bundle: Any) -> Any | None:
    """Choose the strongest semantically appropriate overview item."""

    candidates = [
        item
        for item in bundle.evidence_items
        if eligible_for_section(item, "chapter_overview")
    ]
    if not candidates:
        return None

    def key(item: Any) -> tuple[int, int, int, int, int, str]:
        role_rank = {DIRECT_CONTEXT: 5, BOOK_CONTEXT: 4, GENERIC_BACKGROUND: 2}.get(_role(item), 0)
        specificity = str((item.relevance_metadata or {}).get("anchor_specificity") or "unknown")
        specificity_rank = {"verse": 4, "chapter": 3, "multi_chapter": 2, "book": 1}.get(specificity, 0)
        category_rank = {"history": 4, "culture": 4, "social": 4, "politics": 4, "economics": 3, "language": 2, "chronology": 1}.get(item.category, 0)
        confidence_rank = {"high": 3, "medium": 2, "low": 1}.get(item.confidence, 0)
        overview_rank = int((item.relevance_metadata or {}).get("overview_priority") or 0)
        return (overview_rank, role_rank, category_rank, specificity_rank, confidence_rank, item.id)

    return max(candidates, key=key)


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
        overview_item = select_overview_item(bundle)
        if overview_item is None:
            sections.append(
                CommentarySection(
                    kind="chapter_overview",
                    title=SECTION_TITLES["chapter_overview"],
                    blocks=[
                        CommentaryBlock(
                            id="overview",
                            text=(
                                f"BHF has anchored material for {reference}, but no item is eligible to ground a first-audience chapter overview. "
                                "This v1.1 candidate preserves the semantic limitation."
                            ),
                            verse_refs=[verse_reference],
                            evidence_ids=[],
                            confidence="high",
                            interpretation_level="inference",
                        )
                    ],
                )
            )
            overview_item = None
        else:
            sections.append(
                CommentarySection(
                    kind="chapter_overview",
                    title=SECTION_TITLES["chapter_overview"],
                    blocks=[
                        CommentaryBlock(
                            id="overview",
                            text=(
                                f"This chapter's locked contextual evidence includes {len(bundle.evidence_items)} "
                                f"source-addressable item(s). The strongest eligible contextual observation is: {overview_item.claim}"
                            ),
                            verse_refs=_chapter_overlap_refs(overview_item, book, chapter),
                            evidence_ids=[overview_item.id],
                            confidence=overview_item.confidence if overview_item.confidence in {"low", "medium", "high"} else "medium",
                            interpretation_level=_interpretation_level(overview_item),
                        )
                    ],
                )
            )
        grouped: dict[str, list[Any]] = defaultdict(list)
        for item in bundle.evidence_items:
            if overview_item is not None and item.id == overview_item.id:
                continue
            kind = _section_for_item(item)
            if kind is not None and eligible_for_section(item, kind):
                grouped[kind].append(item)
        max_sections = 2 if availability == "THIN" else 4
        order = ["historical_context", "archaeology_geography", "language_literary", "chronology", "interpretive_questions", "dig_deeper"]
        selected_kinds = _select_section_kinds(grouped, max_sections)
        for kind in selected_kinds:
            items = grouped[kind][:2]
            sections.append(
                CommentarySection(
                    kind=kind,
                    title=SECTION_TITLES[kind],
                    blocks=[_block_for_item(item, index, book, chapter) for index, item in enumerate(items)],
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


def _select_section_kinds(grouped: dict[str, list[Any]], max_sections: int) -> list[str]:
    """Choose a bounded, deterministic section set while reserving reception space."""

    order = [
        "historical_context",
        "archaeology_geography",
        "language_literary",
        "chronology",
        "interpretive_questions",
        "dig_deeper",
    ]
    available = [kind for kind in order if grouped.get(kind)]
    if len(available) <= max_sections:
        return available
    if "dig_deeper" in available and max_sections > 0:
        contextual = [kind for kind in available if kind != "dig_deeper"]
        return contextual[: max_sections - 1] + ["dig_deeper"]
    return available[:max_sections]


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
        bundle = get_chapter_evidence_bundle(
            book,
            chapter,
            evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
        )
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
        "availability_distribution": dict(
            sorted(
                __import__("collections").Counter(
                    result.get("availability") or "INVALID"
                    for result in results
                ).items()
            )
        ),
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
