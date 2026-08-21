"""Evidence normalization and ranking for deterministic narration."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .provenance import as_mapping, source_ids_for, strings
from .roles import NarrativeRole, role_for
from .scripture import PassageScope, parse_scripture_span, passage_scope, references_overlap


_FIELD_ORDER = (
    "historical_setting",
    "historical_context",
    "date_ranges",
    "original_audience",
    "cultural_context",
    "ancient_near_east_context",
    "hebraic_worldview",
    "second_temple_context",
    "literary_context",
    "canonical_context",
    "covenantal_significance",
    "archaeology",
    "interpretive_disputes",
    "summary",
)


@dataclass
class EvidenceCandidate:
    """A normalized fact; this is ephemeral and never persisted as CKL."""

    evidence_id: str
    text: str
    role: str
    parent_id: str = ""
    parent_title: str = ""
    claim_id: str = ""
    source_ids: list[str] = field(default_factory=list)
    source_details: list[dict[str, Any]] = field(default_factory=list)
    scripture_references: list[str] = field(default_factory=list)
    certainty: str = ""
    dispute_status: str = ""
    rationale: str = ""
    content_status: str = ""
    review_status: str = ""
    human_review_required: bool | None = None
    entities: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    score: float = 0.0
    scope: int = 3
    origin: str = "field"
    field_name: str = ""

    @property
    def is_caution(self) -> bool:
        return self.role in {NarrativeRole.INTERPRETIVE_CAUTION, NarrativeRole.DISPUTED_VIEW}


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _reference_scope(reference: str, references: Sequence[str]) -> int:
    requested = parse_scripture_span(reference)
    if requested is None or not references:
        return int(PassageScope.SAME_BOOK)
    scopes = [
        passage_scope(requested, candidate)
        for value in references
        if (candidate := parse_scripture_span(value)) is not None
    ]
    return int(min(scopes, default=PassageScope.UNRELATED))


def _topics(context: Any) -> list[Any]:
    if context is None:
        return []
    if isinstance(context, Mapping):
        if isinstance(context.get("retrieved_topics"), list):
            return list(context["retrieved_topics"])
        if isinstance(context.get("topics"), list):
            return list(context["topics"])
        if isinstance(context.get("results"), list):
            return list(context["results"])
        return [context]
    if isinstance(context, (list, tuple, set)):
        return list(context)
    return [context]


def _is_foreign_book_topic(topic: Mapping[str, Any], reference: str) -> bool:
    """Identify book records reached only through another book's cross-reference.

    A book record can legitimately carry cross-book Scripture anchors (for
    example, John links its Logos prologue to Genesis 1).  Those anchors make
    the record retrievable for canonical/intertextual evidence, but they do
    not make John's unscoped literary notes evidence about Genesis.  Explicitly
    referenced claims remain eligible and are filtered by passage scope later.
    """

    if _key(topic.get("type")) != "book":
        return False
    requested = parse_scripture_span(reference)
    if requested is None:
        return False
    topic_book = re.sub(r"\s+", " ", str(topic.get("title") or "").strip()).casefold()
    if not topic_book or topic_book == requested.book:
        return False
    for raw_reference in topic.get("scripture_references") or []:
        data = as_mapping(raw_reference)
        candidate_reference = (
            data.get("reference")
            if data
            else raw_reference if isinstance(raw_reference, str) else ""
        )
        relationship = _key(data.get("relationship")) if data else ""
        if references_overlap(reference, candidate_reference) and relationship in {
            "",
            "direct",
            "primary",
        }:
            return False
    return True


def _topic_and_result(item: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    result = as_mapping(item)
    raw_object = result.get("object") or getattr(item, "object", None)
    topic = as_mapping(raw_object) if raw_object is not None else result
    if raw_object is not None:
        for key in ("score", "ranking_score", "match_type", "matched_fields", "matched_terms"):
            if key in result and key not in topic:
                topic[key] = result[key]
    return topic, result


def _source_ids(raw: Any, topic: Mapping[str, Any]) -> list[str]:
    source_ids = source_ids_for(raw)
    if not source_ids:
        source_ids = source_ids_for(topic.get("sources"))
    return source_ids


def _source_details(raw: Any, topic: Mapping[str, Any], source_ids: Sequence[str]) -> list[dict[str, Any]]:
    """Hydrate only source records explicitly linked to this evidence."""

    linked = {value.casefold() for value in source_ids}
    details: list[dict[str, Any]] = []
    for source in raw if isinstance(raw, (list, tuple)) else []:
        data = as_mapping(source)
        source_id = str(data.get("id") or data.get("source_id") or data.get("title") or "").strip()
        if source_id and (not linked or source_id.casefold() in linked):
            details.append(data)
    if details:
        return details
    for source in topic.get("sources") or []:
        data = as_mapping(source)
        source_id = str(data.get("id") or data.get("source_id") or data.get("title") or "").strip()
        if source_id and source_id.casefold() in linked:
            details.append(data)
    return details


def _candidate(
    *,
    text: Any,
    role: str,
    topic: Mapping[str, Any],
    raw: Mapping[str, Any] | None,
    result: Mapping[str, Any],
    reference: str,
    origin: str,
    field_name: str = "",
    fallback_references: Sequence[str] = (),
    position: int = 0,
) -> EvidenceCandidate | None:
    value = str(text or "").strip()
    if not value:
        return None
    data = raw or {}
    parent_id = str(topic.get("id") or data.get("parent_object_id") or "").strip()
    parent_title = str(topic.get("title") or data.get("parent_title") or parent_id).strip()
    claim_id = str(data.get("id") or data.get("claim_id") or "").strip() if origin == "claim" else ""
    refs = strings(data.get("scripture_references")) if raw is not None else []
    if not refs:
        refs = list(fallback_references)
    if origin == "field":
        # A free-text field has no source relationship unless the CKL source
        # explicitly declares support for that field.  Do not imply that all
        # object sources support every legacy paragraph.
        source_ids = []
        for source in topic.get("sources") or []:
            source_data = as_mapping(source)
            supports = {_key(value) for value in source_data.get("supports") or []}
            if _key(field_name) in supports:
                source_id = str(source_data.get("id") or source_data.get("title") or "").strip()
                if source_id:
                    source_ids.append(source_id)
    else:
        source_ids = _source_ids(data.get("source_ids") or data.get("sources"), topic)
    source_details = _source_details(
        data.get("sources") if raw is not None else None,
        topic,
        source_ids,
    )
    certainty = str(data.get("certainty") or "").strip()
    dispute = str(data.get("dispute_status") or "").strip()
    scope = _reference_scope(reference, refs)
    raw_score = float(
        result.get("ranking_score")
        or result.get("score")
        or data.get("retrieval_score")
        or data.get("score")
        or 0.0
    )
    governance = {"approved": 0.08, "reviewed": 0.06, "in_review": 0.03, "unreviewed": 0.0, "draft": 0.0}
    review_status = str(topic.get("review_status") or "").strip()
    score = raw_score + governance.get(review_status, 0.0)
    score += max(0.0, 0.12 - (scope * 0.025))
    score -= position * 0.0001
    evidence_id = claim_id or f"{parent_id}:{field_name or origin}:{position}"
    candidate_role = role
    if origin == "note" and _key(data.get("dispute_status")) in {
        "textual_variant",
        "major_scholarly_disagreement",
        "historical_uncertainty",
        "chronological_uncertainty",
        "archaeological_uncertainty",
    } and role == NarrativeRole.OBSERVATION:
        candidate_role = NarrativeRole.DISPUTED_VIEW
    return EvidenceCandidate(
        evidence_id=evidence_id,
        text=value,
        role=candidate_role,
        parent_id=parent_id,
        parent_title=parent_title,
        claim_id=claim_id,
        source_ids=source_ids,
        source_details=source_details,
        scripture_references=refs,
        certainty=certainty,
        dispute_status=dispute,
        rationale=str(data.get("rationale") or data.get("notes") or "").strip(),
        content_status=str(topic.get("content_status") or "").strip(),
        review_status=review_status,
        human_review_required=topic.get("human_review_required") if "human_review_required" in topic else None,
        entities=strings(
            [
                *(topic.get("key_people") or []),
                *(topic.get("key_places") or []),
                *(topic.get("key_events") or []),
                *(topic.get("related_people") or []),
                *(topic.get("related_places") or []),
                *(topic.get("related_events") or []),
            ]
        ),
        cross_references=strings(
            [
                *(topic.get("cross_references") or []),
                *(topic.get("intertextuality") or []),
                *(topic.get("new_testament_connections") or []),
            ]
        ),
        score=score,
        scope=scope,
        origin=origin,
        field_name=field_name,
    )


def collect_evidence(context: Any, *, reference: str = "") -> list[EvidenceCandidate]:
    """Normalize only supplied CKL topics, claims, notes, and context fields."""

    candidates: list[EvidenceCandidate] = []
    for topic_item in _topics(context):
        topic, result = _topic_and_result(topic_item)
        foreign_book_topic = _is_foreign_book_topic(topic, reference)
        parent_refs = strings(topic.get("scripture_references"))
        selected = topic.get("selected_claims")
        claims = selected if isinstance(selected, list) and selected else topic.get("claims") or []
        for position, raw_claim in enumerate(claims):
            claim = as_mapping(raw_claim)
            if foreign_book_topic and not strings(claim.get("scripture_references")):
                continue
            claim_text = claim.get("claim") or claim.get("claim_text")
            candidate = _candidate(
                text=claim_text,
                role=role_for(claim_type=claim.get("claim_type"), object_type=topic.get("type")),
                topic=topic,
                raw=claim,
                result=result,
                reference=reference,
                origin="claim",
                fallback_references=(),
                position=position,
            )
            if candidate:
                candidates.append(candidate)

        notes = topic.get("interpretive_notes") or []
        for position, raw_note in enumerate(notes):
            note = as_mapping(raw_note)
            if foreign_book_topic and not strings(note.get("scripture_references")):
                continue
            note_text = note.get("note") or note.get("text") or (raw_note if isinstance(raw_note, str) else "")
            candidate = _candidate(
                text=note_text,
                role=role_for(note_type=note.get("note_type"), object_type=topic.get("type")),
                topic=topic,
                raw=note,
                result=result,
                reference=reference,
                origin="note",
                fallback_references=parent_refs,
                position=position,
            )
            if candidate:
                candidates.append(candidate)

        for position, field_name in enumerate(_FIELD_ORDER):
            if field_name not in topic:
                continue
            if foreign_book_topic:
                continue
            values = topic.get(field_name)
            if isinstance(values, (list, tuple)):
                values = [item for item in values if str(item or "").strip()]
            else:
                values = [values]
            for value_index, value in enumerate(values):
                candidate = _candidate(
                    text=value,
                    role=role_for(field_name=field_name, object_type=topic.get("type")),
                    topic=topic,
                    raw=None,
                    result=result,
                    reference=reference,
                    origin="field",
                    field_name=field_name,
                    fallback_references=() if field_name == "interpretive_disputes" else parent_refs,
                    position=position * 10 + value_index,
                )
                if candidate:
                    candidates.append(candidate)

    # Exact and near duplicates are retained until the discourse layer, where
    # they can be collapsed without discarding either record's provenance.
    return candidates


def rank_evidence(candidates: Sequence[EvidenceCandidate], *, reference: str = "") -> list[EvidenceCandidate]:
    """Use retrieval/review signals and Scripture scope, not a second search engine."""

    direct = any(candidate.scope <= PassageScope.SAME_CHAPTER for candidate in candidates) if reference else False
    filtered = [
                candidate
        for candidate in candidates
        if not direct
        or (
            candidate.field_name != "interpretive_disputes"
            and (candidate.scope < PassageScope.NEARBY_CHAPTER or not candidate.scripture_references)
        )
    ]
    return sorted(
        filtered,
        key=lambda candidate: (
            candidate.scope,
            0 if candidate.origin == "claim" else 1 if candidate.origin == "note" else 2,
            0 if candidate.review_status in {"approved", "reviewed"} else 1,
            -candidate.score,
            candidate.role,
            candidate.parent_id,
            candidate.evidence_id,
        ),
    )
