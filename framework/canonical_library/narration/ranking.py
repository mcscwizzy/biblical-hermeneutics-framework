"""Evidence normalization and ranking for deterministic narration."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping, Sequence

from .provenance import as_mapping, merge_unique, source_ids_for, strings
from .roles import NarrativeRole, role_for


_FIELD_ORDER = (
    "historical_setting",
    "historical_context",
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


def _scripture_parts(reference: object) -> tuple[str, int, int] | None:
    text = str(reference or "").strip().replace("–", "-").replace("—", "-")
    match = re.match(
        r"^(?P<book>(?:[1-3]\s+)?[A-Za-z][A-Za-z ]*?)\s+"
        r"(?P<chapter>\d+)"
        r"(?::(?P<verse>\d+)(?:-(?P<endverse>\d+))?)?"
        r"(?:-(?P<endchapter>\d+)(?::(?P<endchapterverse>\d+))?)?$",
        text,
    )
    if not match:
        return None
    book = re.sub(r"\s+", " ", match.group("book")).strip().casefold()
    start = int(match.group("chapter"))
    end = int(match.group("endchapter") or start)
    return book, start, end


def references_overlap(left: object, right: object) -> bool:
    """Compare book/chapter ranges without introducing a Scripture engine."""

    left_parts = _scripture_parts(left)
    right_parts = _scripture_parts(right)
    if left_parts is None or right_parts is None:
        return str(left or "").strip().casefold() == str(right or "").strip().casefold()
    return left_parts[0] == right_parts[0] and left_parts[1] <= right_parts[2] and right_parts[1] <= left_parts[2]


def _reference_scope(reference: str, references: Sequence[str]) -> int:
    if not reference:
        return 3
    requested = _scripture_parts(reference)
    for candidate in references:
        candidate_parts = _scripture_parts(candidate)
        if not references_overlap(reference, candidate):
            continue
        # A whole-book claim is useful background, but it is not a direct
        # passage observation.  Narrow chapter/range matches get priority.
        if requested and candidate_parts and candidate_parts[0] == requested[0]:
            if candidate_parts[1] == candidate_parts[2] or (candidate_parts[2] - candidate_parts[1]) <= 2:
                return 0
            continue
        return 0
    if requested and any((_scripture_parts(candidate) or ("", 0, 0))[0] == requested[0] for candidate in references):
        return 2
    return 3


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
    score += max(0.0, 0.04 - (scope * 0.01))
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
        parent_refs = strings(topic.get("scripture_references"))
        selected = topic.get("selected_claims")
        claims = selected if isinstance(selected, list) and selected else topic.get("claims") or []
        for position, raw_claim in enumerate(claims):
            claim = as_mapping(raw_claim)
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

    return _merge_duplicates(candidates)


def _merge_duplicates(candidates: Iterable[EvidenceCandidate]) -> list[EvidenceCandidate]:
    merged: dict[str, EvidenceCandidate] = {}
    for candidate in candidates:
        key = re.sub(r"\s+", " ", candidate.text.casefold()).strip()
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue
        existing.claim_id = existing.claim_id or candidate.claim_id
        existing.source_ids = merge_unique(existing.source_ids, candidate.source_ids)
        existing_source_keys = {
            str(source.get("id") or source.get("title") or "").casefold()
            for source in existing.source_details
        }
        existing.source_details.extend(
            source
            for source in candidate.source_details
            if str(source.get("id") or source.get("title") or "").casefold() not in existing_source_keys
        )
        existing.scripture_references = merge_unique(existing.scripture_references, candidate.scripture_references)
        existing.evidence_id = existing.evidence_id or candidate.evidence_id
        existing.score = max(existing.score, candidate.score)
        if existing.scope > candidate.scope:
            existing.scope = candidate.scope
        existing.entities = merge_unique(existing.entities, candidate.entities)
        existing.cross_references = merge_unique(existing.cross_references, candidate.cross_references)
        if existing.role == NarrativeRole.BACKGROUND and candidate.role != NarrativeRole.BACKGROUND:
            existing.role = candidate.role
    return list(merged.values())


def rank_evidence(candidates: Sequence[EvidenceCandidate], *, reference: str = "") -> list[EvidenceCandidate]:
    """Use retrieval/review signals and Scripture scope, not a second search engine."""

    direct = any(candidate.scope == 0 for candidate in candidates) if reference else False
    filtered = [
                candidate
        for candidate in candidates
        if not direct
        or (
            candidate.field_name != "interpretive_disputes"
            and (candidate.scope < 2 or not candidate.scripture_references)
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
