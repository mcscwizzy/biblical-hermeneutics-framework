"""Scope, validate, and present CKL evidence for reader context panels.

The reader context feature intentionally has a smaller contract than a general
BHF answer.  Retrieval decides what belongs to the selected passage; an AI
presenter may only organize that already-validated packet.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping

from .models import ChatRequest


LOGGER = logging.getLogger(__name__)

EVIDENCE_SCOPES = frozenset(
    {
        "direct_passage",
        "same_chapter",
        "same_book",
        "historical_background",
        "cultural_background",
        "ancient_world_background",
        "original_audience",
        "covenant_context",
        "explicit_cross_reference",
        "quotation",
        "allusion",
        "canonical_theme",
        "weak_or_unverified",
    }
)

_CROSS_BOOK_RELATIONSHIPS = frozenset(
    {
        "quotation",
        "allusion",
        "explicit_cross_reference",
        "canonical_theme",
        "typology",
        "fulfillment",
        "parallel",
        # CKL uses ``supporting`` for curated scripture references.  It is
        # eligible as a later connection only when it is attached to a
        # target-passage record and carries relationship metadata.
        "supporting",
    }
)
_BOOKS = (
    "1 Chronicles",
    "2 Chronicles",
    "1 Corinthians",
    "2 Corinthians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "1 Peter",
    "2 Peter",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 John",
    "2 John",
    "3 John",
    "Song of Songs",
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "Ezra",
    "Nehemiah",
    "Esther",
    "Job",
    "Psalms",
    "Proverbs",
    "Ecclesiastes",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "Hebrews",
    "James",
    "Jude",
    "Revelation",
)
_BOOK_RE = re.compile(
    r"\b(" + "|".join(re.escape(book) for book in sorted(_BOOKS, key=len, reverse=True)) + r")\s+\d+(?::\d+(?:[-–]\d+)?)?",
    re.IGNORECASE,
)

_FIELD_SCOPES: dict[str, str] = {
    "summary": "same_book",
    "historical_context": "historical_background",
    "historical_setting": "historical_background",
    "date_ranges": "historical_background",
    "timeline": "historical_background",
    "ancient_near_east_context": "ancient_world_background",
    "hebraic_worldview": "cultural_background",
    "second_temple_context": "cultural_background",
    "original_audience": "original_audience",
    "covenantal_significance": "covenant_context",
    "literary_context": "same_book",
    "canonical_context": "canonical_theme",
    "canonical_placement": "canonical_theme",
    "canonical_role": "canonical_theme",
    "intertextuality": "canonical_theme",
    "scripture_references": "canonical_theme",
    "cross_references": "canonical_theme",
    "new_testament_connections": "canonical_theme",
}

_ACTION_SCOPES: dict[str, frozenset[str]] = {
    "historical_context": frozenset({"historical_background", "same_book", "direct_passage", "same_chapter"}),
    "cultural_context": frozenset({"cultural_background", "ancient_world_background", "same_book", "direct_passage", "same_chapter"}),
    "original_audience": frozenset({"original_audience", "historical_background", "same_book", "direct_passage", "same_chapter"}),
    "covenant_context": frozenset({"covenant_context", "same_book", "direct_passage", "same_chapter"}),
    "literary_context": frozenset({"same_book", "direct_passage", "same_chapter"}),
    "full_context": frozenset(_FIELD_SCOPES.values()) | frozenset({"direct_passage", "same_chapter"}),
}

_ACTION_FIELDS: dict[str, tuple[str, ...]] = {
    "historical_context": ("historical_context", "historical_setting", "date_ranges", "timeline", "summary", "scripture_references", "cross_references", "new_testament_connections"),
    "cultural_context": ("ancient_near_east_context", "hebraic_worldview", "second_temple_context", "summary", "scripture_references", "cross_references", "new_testament_connections"),
    "original_audience": ("original_audience", "historical_setting", "summary", "scripture_references", "cross_references", "new_testament_connections"),
    "covenant_context": ("covenantal_significance", "summary", "scripture_references", "cross_references", "new_testament_connections"),
    "literary_context": ("literary_context", "summary", "scripture_references", "cross_references", "new_testament_connections"),
    "full_context": tuple(_FIELD_SCOPES),
}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("note", "summary", "claim", "title", "reference"):
            if value.get(key):
                return str(value[key]).strip()
        return ""
    return str(value).strip() if value is not None else ""


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _object_field(obj: Any, field_name: str) -> Any:
    value = getattr(obj, field_name, None)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _reference_book(value: str) -> str | None:
    match = _BOOK_RE.search(value or "")
    return match.group(1) if match else None


def _same_book(left: str | None, right: str) -> bool:
    return bool(left and right and left.casefold() == right.casefold())


def _confidence(obj: Any, relationship: str = "") -> str:
    value = str(getattr(obj, "confidence", "") or "").lower()
    if value in {"high", "medium", "low"}:
        return value
    if relationship in {"quotation", "allusion", "explicit_cross_reference", "canonical_theme"}:
        return "high"
    return "medium"


def _log(decision: str, *, target_book: str, candidate_book: str | None, relationship: str, reason: str, record_id: str) -> None:
    LOGGER.debug(
        "context_evidence target_book=%s candidate_book=%s relationship=%s decision=%s reason=%s record_id=%s",
        target_book,
        candidate_book or "unknown",
        relationship or "none",
        decision,
        reason,
        record_id,
    )


def _is_cross_book_record(obj: Any, target_book: str) -> bool:
    title = str(getattr(obj, "title", "") or "")
    object_book = _reference_book(title)
    if object_book:
        return not _same_book(object_book, target_book)
    candidate_books: set[str] = set()
    for value in _items(getattr(obj, "scripture_references", None)):
        candidate_book = _reference_book(_text(value))
        if candidate_book:
            candidate_books.add(candidate_book)
    return bool(candidate_books) and not any(_same_book(book, target_book) for book in candidate_books)


def _append_evidence(
    evidence: list[dict[str, Any]],
    *,
    obj: Any,
    target_book: str,
    field_name: str,
    item: Any,
    index: int,
    scope: str,
    relationship: str = "",
    reference: str = "",
    candidate_book: str | None = None,
) -> None:
    fact = _text(item)
    if not fact:
        return
    record_id = str(getattr(obj, "id", "") or "unknown")
    evidence_id = f"ckl:{record_id}:{field_name}:{index}"
    if scope not in EVIDENCE_SCOPES:
        scope = "weak_or_unverified"
    if candidate_book and not _same_book(candidate_book, target_book):
        if relationship not in _CROSS_BOOK_RELATIONSHIPS:
            _log(
                "rejected",
                target_book=target_book,
                candidate_book=candidate_book,
                relationship=relationship or "generic_keyword_match",
                reason="cross_book_record_without_explicit_relationship",
                record_id=record_id,
            )
            return
        scope = relationship if relationship in {"quotation", "allusion", "explicit_cross_reference"} else "canonical_theme"
        _log(
            "categorized_later_connection",
            target_book=target_book,
            candidate_book=candidate_book,
            relationship=relationship,
            reason="curated_cross_book_relationship",
            record_id=record_id,
        )
    evidence.append(
        {
            "evidence_id": evidence_id,
            "record_id": record_id,
            "source_id": record_id,
            "title": str(getattr(obj, "title", "") or record_id),
            "fact": fact,
            "evidence_type": field_name,
            "scope": scope,
            "relationship": relationship or None,
            "reference": reference or None,
            "candidate_book": candidate_book or target_book,
            "confidence": _confidence(obj, relationship),
            "retrieval_reason": "target_book_or_passage_match",
        }
    )


def _dedupe_evidence(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        key = re.sub(r"\W+", " ", str(item.get("fact") or "").lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def build_context_evidence_packet(
    objects: Iterable[Any],
    *,
    target_book: str,
    reference: str,
    action: str,
    selected_text: str = "",
    trusted_record_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build the only evidence packet permitted to reach presentation."""

    evidence: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    target_chapter = re.search(r"\s(\d+)(?::|$)", reference)
    chapter_text = target_chapter.group(1) if target_chapter else ""
    if selected_text:
        evidence.append(
            {
                "evidence_id": f"scripture:{reference}",
                "record_id": f"scripture:{reference}",
                "source_id": f"scripture:{reference}",
                "title": "Selected Scripture",
                "fact": selected_text,
                "evidence_type": "selected_scripture",
                "scope": "direct_passage",
                "relationship": "primary",
                "reference": reference,
                "candidate_book": target_book,
                "confidence": "high",
                "retrieval_reason": "selected_passage",
            }
        )

    allowed_fields = _ACTION_FIELDS.get(action, _ACTION_FIELDS["full_context"])
    for obj in objects:
        record_id = str(getattr(obj, "id", "") or "unknown")
        if _is_cross_book_record(obj, target_book):
            excluded.append({"record_id": record_id, "reason": "cross_book_record_without_explicit_relationship"})
            _log(
                "rejected",
                target_book=target_book,
                candidate_book=_reference_book(str(getattr(obj, "title", "") or "")),
                relationship="generic_keyword_match",
                reason="cross_book_record_without_explicit_relationship",
                record_id=record_id,
            )
            continue
        is_trusted_record = trusted_record_ids is None or record_id in trusted_record_ids
        for field_name in allowed_fields:
            if not is_trusted_record and field_name not in {
                "scripture_references",
                "cross_references",
                "new_testament_connections",
                "intertextuality",
            }:
                _log(
                    "downgraded",
                    target_book=target_book,
                    candidate_book=target_book,
                    relationship="supporting_record",
                    reason="non_primary_record_cannot_supply_original_context",
                    record_id=record_id,
                )
                continue
            value = _object_field(obj, field_name)
            for index, item in enumerate(_items(value)):
                if hasattr(item, "to_dict"):
                    item = item.to_dict()
                if isinstance(item, Mapping):
                    reference_value = _text(item.get("reference"))
                    relationship = str(item.get("relationship") or "").strip().lower().replace("-", "_")
                    fact = _text(item.get("notes") or item.get("summary") or item.get("note") or item.get("claim") or reference_value)
                    candidate_book = _reference_book(reference_value or fact)
                    item = {"reference": reference_value, "note": fact}
                else:
                    reference_value = ""
                    relationship = ""
                    fact = _text(item)
                    candidate_book = _reference_book(fact)
                scope = _FIELD_SCOPES.get(field_name, "weak_or_unverified")
                # A reference to the selected chapter is passage evidence;
                # references elsewhere in the same book are still book-level
                # evidence, not historical background from another passage.
                if candidate_book and _same_book(candidate_book, target_book):
                    candidate_chapter = re.search(r"\s(\d+)(?::|$)", reference_value or fact)
                    if candidate_chapter and candidate_chapter.group(1) == chapter_text:
                        scope = "direct_passage" if _reference_overlaps_target(reference_value, reference) else "same_chapter"
                    else:
                        scope = "same_book"
                elif candidate_book and not _same_book(candidate_book, target_book):
                    if relationship not in _CROSS_BOOK_RELATIONSHIPS:
                        excluded.append({"record_id": record_id, "field": field_name, "reason": "cross_book_record_without_explicit_relationship", "fact": fact})
                        _log(
                            "rejected",
                            target_book=target_book,
                            candidate_book=candidate_book,
                            relationship=relationship or "generic_keyword_match",
                            reason="cross_book_record_without_explicit_relationship",
                            record_id=record_id,
                        )
                        continue
                _append_evidence(
                    evidence,
                    obj=obj,
                    target_book=target_book,
                    field_name=field_name,
                    item=item if isinstance(item, Mapping) and item.get("note") else fact,
                    index=index,
                    scope=scope,
                    relationship=relationship,
                    reference=reference_value,
                    candidate_book=candidate_book,
                )

    evidence = _dedupe_evidence(evidence)
    allowed_scopes = _ACTION_SCOPES.get(action, _ACTION_SCOPES["full_context"])
    evidence = [item for item in evidence if item["scope"] in allowed_scopes or item["scope"] in {"quotation", "allusion", "explicit_cross_reference", "canonical_theme"}]
    later = [item for item in evidence if item["candidate_book"] and not _same_book(item["candidate_book"], target_book)]
    primary = [
        item
        for item in evidence
        if item not in later
        and item["scope"] not in {"weak_or_unverified", "canonical_theme"}
    ]
    return {
        "target": {"book": target_book, "reference": reference, "action": action},
        "evidence": evidence,
        "primary_evidence": primary,
        "later_biblical_connections": later,
        "allowed_references": sorted({item["reference"] for item in evidence if item.get("reference")}),
        "excluded": excluded,
    }


def _why(scope: str) -> str:
    return {
        "historical_background": "It helps place the passage in its time and setting.",
        "cultural_background": "It explains a social or cultural detail the first readers may have recognized.",
        "ancient_world_background": "It gives relevant background from the surrounding ancient world.",
        "original_audience": "It helps us hear the passage as its first audience may have heard it.",
        "covenant_context": "It shows how the passage fits its stated covenant setting.",
        "same_book": "It keeps the explanation anchored in the book containing the passage.",
        "direct_passage": "It comes directly from the selected passage.",
    }.get(scope, "It is included because the CKL marked it as relevant evidence.")


def deterministic_context_presentation(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Create a concise reader view without making new factual claims."""

    primary = list(packet.get("primary_evidence") or [])[:6]
    later = list(packet.get("later_biblical_connections") or [])[:6]
    if primary:
        summary = " ".join(str(item["fact"]) for item in primary[:2])
    else:
        summary = "No validated original-context evidence was found for this selection."
    return {
        "mode": "deterministic_fallback",
        "summary": summary,
        "summary_evidence_ids": [item["evidence_id"] for item in primary[:2]],
        "key_facts": [
            {
                "fact": item["fact"],
                "why_it_matters": _why(item["scope"]),
                "evidence_ids": [item["evidence_id"]],
                "confidence": item.get("confidence", "medium"),
            }
            for item in primary
        ],
        "later_biblical_connections": [
            {
                "connection": (
                    f"{item['reference']}: {item['fact']}"
                    if item.get("reference") and item["reference"] not in item["fact"]
                    else item["fact"]
                ),
                "relationship": item.get("relationship") or "canonical_theme",
                "evidence_ids": [item["evidence_id"]],
                "confidence": item.get("confidence", "medium"),
                "reference": item.get("reference"),
            }
            for item in later
        ],
        "important_caution": None,
        "caution_evidence_ids": [],
        "sources": [
            {
                "evidence_id": item["evidence_id"],
                "record_id": item["record_id"],
                "evidence_type": item["evidence_type"],
                "scope": item["scope"],
                "confidence": item["confidence"],
                "relationship": item.get("relationship"),
                "retrieval_reason": item.get("retrieval_reason"),
            }
            for item in evidence_for_sources(packet)
        ],
    }


def evidence_for_sources(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(packet.get("evidence") or [])


def _reference_overlaps_target(candidate: str, target: str) -> bool:
    candidate_verse = re.search(r":(\d+)", candidate or "")
    target_verse = re.search(r":(\d+)", target or "")
    if not candidate_verse or not target_verse:
        return False
    selected = int(target_verse.group(1))
    range_match = re.search(r":(\d+)(?:[-–](\d+))?", candidate)
    if not range_match:
        return False
    start = int(range_match.group(1))
    end = int(range_match.group(2) or start)
    return start <= selected <= end


def validate_context_presentation(
    presentation: Mapping[str, Any], packet: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    """Validate IDs, scopes, and references in an AI presentation."""

    errors: list[str] = []
    evidence = {str(item.get("evidence_id")): item for item in packet.get("evidence") or []}
    allowed_refs = {str(value).casefold() for value in packet.get("allowed_references") or []}
    if not isinstance(presentation.get("summary"), str) or not presentation.get("summary", "").strip():
        errors.append("summary is required")
    summary_ids = [str(value) for value in presentation.get("summary_evidence_ids") or []]
    if presentation.get("summary", "").strip() and not summary_ids:
        errors.append("summary must cite evidence IDs")
    for evidence_id in summary_ids:
        if evidence_id not in evidence:
            errors.append(f"unknown summary evidence ID: {evidence_id}")
    for list_name in ("key_facts", "later_biblical_connections"):
        values = presentation.get(list_name)
        if not isinstance(values, list):
            errors.append(f"{list_name} must be a list")
            continue
        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                errors.append(f"{list_name}[{index}] must be an object")
                continue
            text_key = "connection" if list_name == "later_biblical_connections" else "fact"
            if not str(item.get(text_key) or "").strip():
                errors.append(f"{list_name}[{index}] has no {text_key}")
            ids = [str(value) for value in item.get("evidence_ids") or []]
            if not ids:
                errors.append(f"{list_name}[{index}] must cite evidence IDs")
            for evidence_id in ids:
                source = evidence.get(evidence_id)
                if source is None:
                    errors.append(f"unknown evidence ID: {evidence_id}")
                    continue
                is_later = source.get("candidate_book") and not _same_book(source.get("candidate_book"), packet.get("target", {}).get("book", ""))
                if list_name == "key_facts" and is_later:
                    errors.append(f"cross-book evidence {evidence_id} cannot appear in key_facts")
                if list_name == "later_biblical_connections" and not is_later:
                    errors.append(f"later connection {evidence_id} is not cross-book evidence")
            if list_name == "later_biblical_connections" and item.get("relationship") not in _CROSS_BOOK_RELATIONSHIPS:
                errors.append(f"unsupported later relationship: {item.get('relationship')}")
    caution = str(presentation.get("important_caution") or "").strip()
    caution_ids = [str(value) for value in presentation.get("caution_evidence_ids") or []]
    if caution and not caution_ids:
        errors.append("important_caution must cite evidence IDs")
    if any(evidence_id not in evidence for evidence_id in caution_ids):
        errors.append("important_caution cites an unknown evidence ID")
    rendered_text = json.dumps(presentation, ensure_ascii=False)
    for match in _BOOK_RE.finditer(rendered_text):
        reference = match.group(0).replace("–", "-").casefold()
        if not any(reference == allowed or reference.startswith(f"{allowed} ") or allowed.startswith(f"{reference} ") for allowed in allowed_refs):
            errors.append(f"unsupported Bible reference: {match.group(0)}")
    return not errors, errors


CONTEXT_PRESENTATION_SYSTEM_PROMPT = """You organize validated biblical-study evidence for a general reader.
Use only the supplied evidence packet. Do not add facts, references, interpretations, or theological claims.
Separate the passage's original context from later biblical connections. Explain technical ideas in ordinary language.
Every summary, fact, connection, and caution must cite supplied evidence IDs.
Return JSON only with summary, summary_evidence_ids, key_facts, later_biblical_connections,
important_caution, caution_evidence_ids, and sources. Do not write a sermon or tell the reader what to believe."""


def present_context_with_ai(
    packet: Mapping[str, Any],
    *,
    adapter: Any,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 900,
    context_window: int = 4096,
) -> dict[str, Any]:
    """Attempt narrow structured presentation, falling back on any failure."""

    fallback = deterministic_context_presentation(packet)
    if adapter is None or not packet.get("evidence"):
        return fallback
    model_packet = {
        "target": packet.get("target", {}),
        "allowed_references": list(packet.get("allowed_references") or []),
        "evidence": list(packet.get("evidence") or []),
    }
    request = ChatRequest(
        system_prompt=CONTEXT_PRESENTATION_SYSTEM_PROMPT,
        user_prompt=json.dumps(model_packet, ensure_ascii=False, separators=(",", ":")),
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        context_window=context_window,
        response_format={"type": "json_object"},
        metadata={"response_contract": "context_presentation"},
    )
    try:
        response = adapter.chat(request)
        parsed = json.loads(str(getattr(response, "text", "") or "").strip())
        if not isinstance(parsed, Mapping):
            raise ValueError("presentation response was not an object")
        valid, errors = validate_context_presentation(parsed, packet)
        if not valid:
            raise ValueError("; ".join(errors))
        return {**dict(parsed), "mode": "ai"}
    except Exception as exc:  # noqa: BLE001 - the deterministic view is safe
        LOGGER.warning("context presentation fell back to deterministic rendering: %s", exc)
        return fallback
