"""Deterministic claim-level evidence ranking and source hydration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Iterable, Mapping, Sequence

from .normalization import STOP_WORDS, normalize_text, tokenize_query


_LOW_INFERENCE_PRIORITY = {
    "biblical_text": 0,
    "textual": 0,
    "manuscript": 1,
    "lexical": 1,
    "literary": 2,
    "historical_cultural": 2,
    "historical-cultural": 2,
    "ancient_near_eastern": 3,
    "ancient-near-eastern": 3,
    "canonical": 4,
    "biblical_theology": 5,
    "biblical-theology": 5,
    "theological": 6,
    "reception_history": 7,
    "reception-history": 7,
}

_DIMENSION_CLAIM_TYPES: dict[str, tuple[str, ...]] = {
    "direct textual explanation": ("biblical_text", "textual", "literary"),
    "historical setting": ("historical_cultural", "historical-cultural"),
    "cultural practice": ("historical_cultural", "historical-cultural", "ancient_near_eastern"),
    "ancient near eastern background": ("ancient_near_eastern", "ancient-near-eastern", "historical_cultural"),
    "second temple context": ("second_temple", "historical_cultural"),
    "greco roman context": ("greco_roman", "historical_cultural"),
    "lexical evidence": ("lexical",),
    "manuscript textual evidence": ("manuscript", "textual"),
    "literary structure": ("literary",),
    "canonical connection": ("canonical", "biblical_theology"),
    "covenant context": ("canonical", "biblical_theology", "theological"),
    "biblical theology": ("biblical_theology", "canonical", "theological"),
    "competing interpretations": ("interpretive", "theological", "reception_history"),
    "reception history": ("reception_history", "reception-history"),
    "translation differences": ("lexical", "textual", "manuscript"),
    "evidence supporting an interpretation": ("biblical_text", "textual", "historical_cultural", "literary"),
}


@dataclass(frozen=True)
class RetrievedClaimEvidence:
    parent_object_id: str
    parent_title: str
    parent_type: str
    claim_id: str
    claim_text: str
    claim_type: str
    certainty: str
    dispute_status: str
    rationale: str = ""
    notes: str = ""
    scripture_references: tuple[str, ...] = ()
    sources: tuple[dict[str, Any], ...] = ()
    retrieval_score: float = 0.0
    retrieval_reason: tuple[str, ...] = ()
    matched_terms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scripture_references"] = list(self.scripture_references)
        data["sources"] = [dict(source) for source in self.sources]
        data["retrieval_reason"] = list(self.retrieval_reason)
        data["matched_terms"] = list(self.matched_terms)
        return data


def rank_claims(
    question: str,
    parent: Any,
    *,
    parent_relevance: float = 0.0,
    requested_dimensions: Sequence[str] = (),
    scripture_references: Sequence[str] = (),
    limit: int = 3,
) -> list[RetrievedClaimEvidence]:
    """Rank a candidate object's authored claims against the actual question."""

    if limit <= 0:
        return []
    parent_data = _as_mapping(parent)
    claims = _as_sequence(parent_data.get("claims"))
    sources = _as_sequence(parent_data.get("sources"))
    query_terms = _meaningful_terms(question)
    normalized_question = normalize_text(question)
    requested = tuple(normalize_text(value) for value in requested_dimensions if str(value).strip())
    query_refs = tuple(str(value) for value in scripture_references if str(value).strip())
    ranked: list[RetrievedClaimEvidence] = []

    for position, raw_claim in enumerate(claims):
        claim = _as_mapping(raw_claim)
        claim_text = str(claim.get("claim") or claim.get("claim_text") or "").strip()
        claim_id = str(claim.get("id") or claim.get("claim_id") or "").strip()
        if not claim_text or not claim_id:
            continue
        claim_type = str(claim.get("claim_type") or "").strip()
        rationale = str(claim.get("rationale") or "").strip()
        notes = str(claim.get("notes") or "").strip()
        searchable = normalize_text(" ".join((claim_text, rationale, notes, claim_type)))
        claim_terms = set(_meaningful_terms(searchable))
        matched_terms = tuple(sorted(set(query_terms) & claim_terms))
        reasons: list[str] = []
        score = 0.0

        if query_terms and matched_terms:
            overlap = len(matched_terms) / max(len(set(query_terms)), 1)
            score += min(0.55, 0.22 + (0.45 * overlap))
            reasons.append("query token overlap: " + ", ".join(matched_terms))
        phrase = _longest_query_phrase(normalized_question, searchable)
        if phrase:
            score += min(0.20, 0.06 + (0.025 * len(phrase.split())))
            reasons.append(f'phrase overlap: "{phrase}"')

        dimension_matches = [
            dimension
            for dimension in requested
            if claim_type in _DIMENSION_CLAIM_TYPES.get(dimension, ())
        ]
        if dimension_matches:
            score += min(0.18, 0.09 + 0.03 * len(dimension_matches))
            reasons.append("requested dimension: " + ", ".join(dimension_matches))

        claim_refs = tuple(str(value) for value in _as_sequence(claim.get("scripture_references")) if str(value).strip())
        reference_matches = _matching_references(query_refs, claim_refs, question)
        if reference_matches:
            score += min(0.22, 0.12 + 0.03 * len(reference_matches))
            reasons.append("Scripture overlap: " + ", ".join(reference_matches))

        if parent_relevance > 0:
            score += min(0.14, max(0.0, float(parent_relevance)) * 0.14)
            reasons.append("relevant parent object")

        layer_rank = _LOW_INFERENCE_PRIORITY.get(claim_type, 4)
        score += max(0.0, 0.055 - (0.007 * layer_rank))
        if layer_rank <= 2:
            reasons.append("lower-inference evidence layer")

        claim_sources = hydrate_claim_sources(claim, sources, question=question, limit=4)
        if claim_sources:
            score += 0.04
            reasons.append("source support available")
        if claim_refs:
            score += 0.035
            reasons.append("Scripture support available")

        certainty = str(claim.get("certainty") or "").strip()
        if certainty in {"textually_explicit", "strong_consensus"}:
            score += 0.015

        ranked.append(
            RetrievedClaimEvidence(
                parent_object_id=str(parent_data.get("id") or ""),
                parent_title=str(parent_data.get("title") or parent_data.get("id") or ""),
                parent_type=str(parent_data.get("type") or ""),
                claim_id=claim_id,
                claim_text=claim_text,
                claim_type=claim_type,
                certainty=certainty,
                dispute_status=str(claim.get("dispute_status") or "").strip(),
                rationale=rationale,
                notes=notes,
                scripture_references=claim_refs,
                sources=tuple(claim_sources),
                retrieval_score=round(min(score, 1.0), 4),
                retrieval_reason=tuple(reasons or ("object-level fallback ordering",)),
                matched_terms=matched_terms,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.retrieval_score,
            _LOW_INFERENCE_PRIORITY.get(item.claim_type, 4),
            item.claim_id,
        )
    )
    return ranked[:limit]


def hydrate_claim_sources(
    claim: Any,
    sources: Iterable[Any],
    *,
    question: str = "",
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Hydrate explicit claim sources before support metadata and fallbacks."""

    if limit <= 0:
        return []
    claim_data = _as_mapping(claim)
    source_data = [_as_mapping(source) for source in sources]
    source_by_id = {str(source.get("id") or source.get("source_id") or ""): source for source in source_data}
    claim_id = str(claim_data.get("id") or claim_data.get("claim_id") or "")
    claim_type = str(claim_data.get("claim_type") or "")
    explicit_ids = [str(value) for value in _as_sequence(claim_data.get("source_ids"))]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(source: Mapping[str, Any], reason: str) -> None:
        source_id = str(source.get("id") or source.get("source_id") or "").strip()
        if not source_id or source_id in seen or len(selected) >= limit:
            return
        value = dict(source)
        value["support_reason"] = reason
        selected.append(value)
        seen.add(source_id)

    for source_id in explicit_ids:
        source = source_by_id.get(source_id)
        if source:
            add(source, "explicitly attached to selected claim")
    for source in source_data:
        supports = {str(value) for value in _as_sequence(source.get("supports"))}
        if claim_id and claim_id in supports:
            add(source, "source supports selected claim")
    for source in source_data:
        supports = {str(value) for value in _as_sequence(source.get("supports"))}
        if supports.intersection({claim_type, "claims", "interpretive_notes"}):
            add(source, "source supports selected evidence field")

    if not selected:
        question_terms = set(_meaningful_terms(question))
        ordered = sorted(
            source_data,
            key=lambda source: (
                -len(question_terms & set(_meaningful_terms(" ".join(str(value) for value in source.values())))),
                str(source.get("id") or source.get("source_id") or ""),
            ),
        )
        for source in ordered:
            add(source, "parent-object fallback source")
    return selected[:limit]


def _meaningful_terms(value: str) -> list[str]:
    return [
        _evidence_term(term)
        for term in tokenize_query(value)
        if len(term) > 1 and term not in STOP_WORDS
    ]


def _evidence_term(term: str) -> str:
    normalized = normalize_text(term)
    families = {
        "redeem": ("redeem", "redeems", "redeemed", "redeeming", "redeemer", "redemption"),
        "inherit": ("inherit", "inherits", "inherited", "inheritance"),
        "conceive": ("conceive", "conceived", "conception"),
        "represent": ("represent", "represents", "represented", "representation"),
        "interpret": ("interpret", "interprets", "interpretation", "interpretations"),
    }
    for canonical, values in families.items():
        if normalized in values:
            return canonical
    return normalized


def _longest_query_phrase(question: str, searchable: str) -> str:
    terms = _meaningful_terms(question)
    for size in range(min(6, len(terms)), 1, -1):
        for start in range(0, len(terms) - size + 1):
            phrase = " ".join(terms[start : start + size])
            if phrase in searchable:
                return phrase
    return ""


def _matching_references(query_refs: Sequence[str], claim_refs: Sequence[str], question: str) -> tuple[str, ...]:
    normalized_query_refs = [normalize_text(value) for value in query_refs]
    question_reference_tokens = set(re.findall(r"[a-z]+|\d+", normalize_text(question)))
    matches: list[str] = []
    for reference in claim_refs:
        normalized = normalize_text(reference)
        tokens = set(re.findall(r"[a-z]+|\d+", normalized))
        if any(_reference_prefix_overlap(normalized, query_ref) for query_ref in normalized_query_refs):
            matches.append(reference)
        elif len(tokens & question_reference_tokens) >= 2 and any(token.isdigit() for token in tokens):
            matches.append(reference)
    return tuple(dict.fromkeys(matches))


def _reference_prefix_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    left_parts = re.findall(r"[a-z]+|\d+", left)
    right_parts = re.findall(r"[a-z]+|\d+", right)
    return bool(left_parts and right_parts and left_parts[:2] == right_parts[:2])


def _as_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value) if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return []
