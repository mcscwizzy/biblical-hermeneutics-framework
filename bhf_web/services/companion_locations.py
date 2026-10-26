"""Source-grounded location selection and paging for Study Companion."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from bhf_agent.presentation.models import mapping
from bhf_agent.presentation.references import references_overlap


_DIRECT_RELATIONSHIPS = {"direct", "primary", "directly-named", "directly-anchored"}
_SOURCE_LOCK = re.compile(
    r"Source-lock identity:\s*([^;]+);\s*status:\s*([A-Za-z_-]+)",
    re.IGNORECASE,
)


def select_ckl_locations(passage_reference: str, results: Sequence[Any]) -> list[dict[str, Any]]:
    """Select directly anchored, source-backed CKL place records.

    CKL object review status and source-lock status are independent. In
    particular, ``in_review`` and ``unreviewed`` objects are not rejected by
    an ``approved`` gate. A locked geography evidence item can supply a direct
    passage anchor, but it does not approve the whole object or add geography
    fields to an identity-only draft.
    """

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        raw = getattr(result, "object", result)
        record = mapping(raw)
        if not record or str(record.get("type") or "").casefold() != "place":
            continue
        object_id = str(record.get("id") or "").strip()
        title = str(record.get("title") or "").strip()
        review_status = str(record.get("review_status") or "unreviewed").strip().casefold()
        content_status = str(record.get("content_status") or "draft").strip().casefold()
        if not object_id or not title or object_id in seen:
            continue
        if review_status == "rejected" or content_status in {"deprecated", "placeholder"}:
            continue

        source_records = [mapping(source) for source in _sequence(record.get("sources"))]
        source_records = [source for source in source_records if _has_source_identity(source)]
        source_ids = {
            str(source.get("id") or "").strip()
            for source in source_records
            if str(source.get("id") or "").strip()
        }
        direct_references = _direct_references(
            passage_reference,
            _sequence(record.get("scripture_references")),
        )
        geography_evidence = _direct_geography_evidence(
            passage_reference,
            _sequence(record.get("evidence_items")),
            source_ids,
        )
        locked = [item for item in geography_evidence if item["status"] == "locked"]
        restricted_lock = next(
            (item for item in geography_evidence if item["status"] != "locked"),
            None,
        )
        if not source_records or not (direct_references or locked):
            continue

        anchors: list[str] = []
        for anchor in [*direct_references, *[item["reference"] for item in locked]]:
            if anchor and anchor not in anchors:
                anchors.append(anchor)
        # A source-locked anchor may support an object whose general CKL
        # reference is only contextual, so prefer a directly anchored lock
        # only when no direct object anchor is present.
        reference = direct_references[0] if direct_references else locked[0]["reference"]
        source_lock = next(
            (
                {"status": item["status"], "id": item["id"]}
                for item in geography_evidence
                if item["status"] != "locked"
            ),
            {"status": "locked", "id": locked[0]["id"]} if locked else {"status": "not_recorded"},
        )
        item: dict[str, Any] = {
            "id": object_id,
            "origin": "ckl",
            "title": title,
            "reference": reference,
            "references": anchors,
            "review_status": review_status,
            "content_status": content_status,
            "source_lock": source_lock,
            "provenance": {
                "name": "Canonical Knowledge Library",
                "sources": [
                    str(source.get("title") or source.get("id") or "CKL source")
                    for source in source_records[:3]
                ],
            },
            "canonical_href": f"/api/canonical/objects/{object_id}",
        }

        # Draft and unreviewed CKL place records may be identity-only. Keep
        # their display to the CKL name and exact anchor rather than borrowing
        # coordinates, modern identifications, summaries, or descriptions.
        if (
            content_status != "draft"
            and review_status not in {"unreviewed", "rejected"}
            and restricted_lock is None
        ):
            if _summary_is_source_supported(record, source_records):
                item["description"] = str(record.get("summary") or "").strip()
            role = _anchor_notes(
                passage_reference,
                _sequence(record.get("scripture_references")),
            )
            if role:
                item["passage_role"] = role
            uncertainty = _direct_uncertainty(
                passage_reference,
                _sequence(record.get("interpretive_notes")),
                source_ids,
            )
            if uncertainty:
                item["identification_uncertainty"] = uncertainty

        candidates.append(item)
        seen.add(object_id)

    return sorted(
        candidates,
        key=lambda item: (item["title"].casefold(), item["id"].casefold()),
    )


def compose_location_page(
    *,
    map_page: Mapping[str, Any],
    ckl_items: Sequence[dict[str, Any]],
    cursor: str | int | None = None,
    limit: int = 5,
    reference: str = "",
) -> dict[str, Any]:
    """Page stable map and CKL streams without fuzzy identity joins."""

    bounded_limit = max(1, min(int(limit), 25))
    offset = _parse_cursor(cursor)
    map_total = max(0, int(map_page.get("total") or 0))
    map_items = [dict(item) for item in _sequence(map_page.get("items"))]
    all_ckl = list(ckl_items)
    total = map_total + len(all_ckl)
    offset = min(offset, total)

    items: list[dict[str, Any]] = []
    if offset < map_total:
        map_start = max(0, offset - int(map_page.get("offset") or 0))
        # ``map_page`` was requested at the same offset and limit; these are
        # already the exact bounded rows for this portion of the response.
        items.extend(map_items[map_start : map_start + bounded_limit])
        remaining = bounded_limit - len(items)
        next_offset = offset + len(items)
        if remaining and next_offset >= map_total:
            ckl_start = max(0, next_offset - map_total)
            items.extend(all_ckl[ckl_start : ckl_start + remaining])
    else:
        ckl_start = offset - map_total
        items.extend(all_ckl[ckl_start : ckl_start + bounded_limit])

    next_offset = offset + len(items)
    return {
        "reference": reference,
        "items": items,
        "total": total,
        "page_size": bounded_limit,
        "next_cursor": str(next_offset) if next_offset < total else None,
    }


def _parse_cursor(cursor: str | int | None) -> int:
    if cursor in (None, ""):
        return 0
    try:
        value = int(cursor)
    except (TypeError, ValueError) as exc:
        raise ValueError("location cursor must be a non-negative integer") from exc
    if value < 0:
        raise ValueError("location cursor must be a non-negative integer")
    return value


def _direct_references(passage_reference: str, values: Sequence[Any]) -> list[str]:
    matched = []
    for value in values:
        record = mapping(value)
        reference = str(record.get("reference") or "").strip()
        relationship = str(record.get("relationship") or "").strip().casefold().replace("_", "-")
        if reference and relationship in _DIRECT_RELATIONSHIPS and references_overlap(passage_reference, reference):
            if reference not in matched:
                matched.append(reference)
    return matched


def _direct_geography_evidence(
    passage_reference: str,
    values: Sequence[Any],
    available_source_ids: set[str],
) -> list[dict[str, str]]:
    matched: list[dict[str, str]] = []
    for value in values:
        evidence = mapping(value)
        if str(evidence.get("evidence_type") or "").casefold() not in {
            "geography-environment",
            "geography_environment",
        }:
            continue
        lock = _SOURCE_LOCK.search(str(evidence.get("notes") or ""))
        if not lock:
            continue
        direct = _direct_references(passage_reference, _sequence(evidence.get("scripture_references")))
        evidence_source_ids = {
            str(source_id).strip()
            for source_id in _sequence(evidence.get("source_ids"))
            if str(source_id).strip()
        }
        if not direct or not available_source_ids.intersection(evidence_source_ids):
            continue
        matched.append({
            "id": lock.group(1).strip(),
            "reference": direct[0],
            "status": lock.group(2).casefold().replace("_", "-"),
        })
    return sorted(matched, key=lambda item: (item["reference"], item["id"], item["status"]))


def _summary_is_source_supported(
    record: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
) -> bool:
    summary = str(record.get("summary") or "").strip()
    if not summary:
        return False
    supported_fields = {"summary", "canonical-context"}
    return any(
        supported_fields.intersection(
            str(value).strip().casefold().replace("_", "-")
            for value in _sequence(source.get("supports"))
        )
        for source in sources
    )


def _anchor_notes(passage_reference: str, values: Sequence[Any]) -> str:
    for value in values:
        record = mapping(value)
        reference = str(record.get("reference") or "").strip()
        relationship = str(record.get("relationship") or "").strip().casefold().replace("_", "-")
        notes = str(record.get("notes") or "").strip()
        if (
            reference
            and relationship in _DIRECT_RELATIONSHIPS
            and references_overlap(passage_reference, reference)
            and notes
        ):
            return notes
    return ""


def _direct_uncertainty(
    passage_reference: str,
    values: Sequence[Any],
    available_source_ids: set[str],
) -> str:
    uncertain_certainties = {
        "probable", "plausible", "disputed", "tradition_dependent",
        "speculative", "insufficient_evidence", "medium", "low",
    }
    uncertain_disputes = {
        "minor_scholarly_disagreement", "major_scholarly_disagreement",
        "denominational_disagreement", "textual_variant", "historical_uncertainty",
        "chronological_uncertainty", "archaeological_uncertainty", "lexical_uncertainty",
        "disputed", "minority", "confessional",
    }
    for value in values:
        note = mapping(value)
        references = _direct_references(passage_reference, _sequence(note.get("scripture_references")))
        certainty = str(note.get("certainty") or "").casefold()
        dispute = str(note.get("dispute_status") or "").casefold()
        note_source_ids = {
            str(source_id).strip()
            for source_id in _sequence(note.get("sources"))
            if str(source_id).strip()
        }
        if not references or not available_source_ids.intersection(note_source_ids):
            continue
        if certainty in uncertain_certainties or dispute in uncertain_disputes:
            if certainty in uncertain_certainties and dispute in uncertain_disputes:
                label = f"CKL certainty: {certainty}; dispute status: {dispute}."
            elif certainty in uncertain_certainties:
                label = f"CKL certainty: {certainty}."
            else:
                label = f"CKL dispute status: {dispute}."
            return str(note.get("note") or label).strip()
    return ""


def _has_source_identity(source: Mapping[str, Any]) -> bool:
    return any(str(source.get(key) or "").strip() for key in ("id", "title", "url", "author"))


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


__all__ = ["compose_location_page", "select_ckl_locations"]
