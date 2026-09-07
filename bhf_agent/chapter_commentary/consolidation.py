"""Deterministic diagnostics for reader-level commentary consolidation.

This module measures the shape of generated commentary.  It is intentionally
read-only: it does not alter compiled synthesis, commentary, validation, or
the candidate gate.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping

from .richness_clusters import (
    CORE_CLASSIFIER_V2,
    DuplicateReason,
    QualityClass,
    SynthesisIdeaCluster,
    cluster_synthesis_units,
)


CONSOLIDATION_AUDIT_VERSION = "commentary-consolidation-audit-v1"
_WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?", re.IGNORECASE)
_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his in is it its of on or "
    "that the their them they this to was were which who with".split()
)


@dataclass(frozen=True)
class BlockConsolidationRecord:
    section_kind: str
    block_id: str
    verse_refs: list[str]
    synthesis_ids: list[str]
    evidence_ids: list[str]
    word_count: int
    idea_cluster_ids: list[str]
    synthesis_unit_count: int
    evidence_record_count: int
    quality_classes: list[str]
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("text", None)
        return result


@dataclass(frozen=True)
class ProseOverlap:
    left_block_id: str
    right_block_id: str
    classification: str
    shared_terms: list[str]
    jaccard: float
    containment: float
    sequence_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def map_commentary_blocks(
    commentary: Any,
    units: Iterable[Any],
    evidence_items: Iterable[Any] | Mapping[str, Any] | None = None,
    *,
    core_classifier: str = CORE_CLASSIFIER_V2,
) -> tuple[list[BlockConsolidationRecord], list[SynthesisIdeaCluster]]:
    """Map every block to its units, evidence, and deterministic idea clusters."""

    sections = _value(commentary, "sections") or []
    unit_list = list(units)
    clusters = cluster_synthesis_units(
        unit_list, evidence_items, core_classifier=core_classifier
    )
    cluster_by_unit = {
        synthesis_id: cluster
        for cluster in clusters
        for synthesis_id in cluster.synthesis_ids
    }
    records: list[BlockConsolidationRecord] = []
    for section in sections:
        section_kind = _text(section, "kind")
        for block in _value(section, "blocks") or []:
            synthesis_ids = _unique(_sequence(block, "synthesis_ids"))
            evidence_ids = _unique(_sequence(block, "evidence_ids"))
            cluster_ids = _unique(
                cluster_by_unit[synthesis_id].id
                for synthesis_id in synthesis_ids
                if synthesis_id in cluster_by_unit
            )
            quality_classes = _unique(
                cluster_by_unit[synthesis_id].quality_class
                for synthesis_id in synthesis_ids
                if synthesis_id in cluster_by_unit
            )
            records.append(
                BlockConsolidationRecord(
                    section_kind=section_kind,
                    block_id=_text(block, "id"),
                    verse_refs=_sequence(block, "verse_refs"),
                    synthesis_ids=synthesis_ids,
                    evidence_ids=evidence_ids,
                    word_count=len(_words(_text(block, "text"))),
                    idea_cluster_ids=cluster_ids,
                    synthesis_unit_count=len(synthesis_ids),
                    evidence_record_count=len(evidence_ids),
                    quality_classes=quality_classes,
                    text=_text(block, "text"),
                )
            )
    return records, clusters


def audit_prose_overlap(
    blocks: Iterable[Any] | Iterable[BlockConsolidationRecord],
) -> list[ProseOverlap]:
    """Classify every block pair using lexical signals only.

    The thresholds deliberately distinguish related topical vocabulary from
    repetition.  No semantic model or external knowledge is used.
    """

    values = sorted(
        list(blocks), key=lambda value: _text(value, "block_id") or _text(value, "id")
    )
    result: list[ProseOverlap] = []
    for index, left in enumerate(values):
        left_id = _text(left, "block_id") or _text(left, "id")
        left_text = _text(left, "text")
        left_terms = _term_set(left_text)
        for right in values[index + 1 :]:
            right_id = _text(right, "block_id") or _text(right, "id")
            right_text = _text(right, "text")
            right_terms = _term_set(right_text)
            shared = sorted(left_terms & right_terms)
            union = left_terms | right_terms
            jaccard = len(shared) / len(union) if union else 0.0
            containment = len(shared) / max(1, min(len(left_terms), len(right_terms)))
            sequence = SequenceMatcher(
                None, " ".join(sorted(left_terms)), " ".join(sorted(right_terms))
            ).ratio()
            classification = _classify_overlap(
                shared_count=len(shared),
                jaccard=jaccard,
                containment=containment,
                sequence=sequence,
            )
            result.append(
                ProseOverlap(
                    left_block_id=left_id,
                    right_block_id=right_id,
                    classification=classification,
                    shared_terms=shared,
                    jaccard=round(jaccard, 4),
                    containment=round(containment, 4),
                    sequence_ratio=round(sequence, 4),
                )
            )
    return result


def consolidation_metrics(
    records: Iterable[BlockConsolidationRecord],
    clusters: Iterable[SynthesisIdeaCluster],
    overlaps: Iterable[ProseOverlap] = (),
) -> dict[str, Any]:
    """Return density-normalized metrics and the duplicate/overlap indexes."""

    blocks = list(records)
    cluster_list = list(clusters)
    overlap_list = list(overlaps)
    consumed_units = _unique(
        synthesis_id for block in blocks for synthesis_id in block.synthesis_ids
    )
    consumed_cluster_ids = _unique(
        cluster_id for block in blocks for cluster_id in block.idea_cluster_ids
    )
    cluster_by_id = {cluster.id: cluster for cluster in cluster_list}
    words = sum(block.word_count for block in blocks)
    block_count = len(blocks)
    meaningful_consumed = [
        cluster_by_id[cluster_id]
        for cluster_id in consumed_cluster_ids
        if cluster_id in cluster_by_id
        and cluster_by_id[cluster_id].quality_class != QualityClass.OPTIONAL.value
    ]
    pair_counts = Counter(overlap.classification for overlap in overlap_list)
    repetitive_pairs = [
        overlap
        for overlap in overlap_list
        if overlap.classification in {"REDUNDANT", "NEAR_DUPLICATE"}
    ]
    repetitive_block_ids = _unique(
        block_id
        for overlap in repetitive_pairs
        for block_id in (overlap.left_block_id, overlap.right_block_id)
    )
    duplicate_parallel = []
    for cluster in cluster_list:
        if cluster.duplicate_reason == DuplicateReason.DISTINCT.value:
            continue
        member_blocks = [
            block.block_id
            for block in blocks
            if set(block.synthesis_ids).intersection(cluster.synthesis_ids)
        ]
        if len(set(member_blocks)) > 1:
            duplicate_parallel.append(
                {
                    "cluster_id": cluster.id,
                    "duplicate_reason": cluster.duplicate_reason,
                    "synthesis_ids": cluster.synthesis_ids,
                    "block_ids": _unique(member_blocks),
                }
            )

    core_words = 0.0
    optional_words = 0.0
    for block in blocks:
        classes = [
            cluster_by_id[cluster_id].quality_class
            for cluster_id in block.idea_cluster_ids
            if cluster_id in cluster_by_id
        ]
        if not classes:
            continue
        share = block.word_count / len(classes)
        core_words += share * sum(value == QualityClass.CORE.value for value in classes)
        optional_words += share * sum(
            value == QualityClass.OPTIONAL.value for value in classes
        )

    return {
        "SYNTHESIS_UNITS_PER_BLOCK": _ratio(len(consumed_units), block_count),
        "IDEA_CLUSTERS_PER_BLOCK": _ratio(len(consumed_cluster_ids), block_count),
        "EVIDENCE_IDS_PER_BLOCK": _ratio(
            sum(block.evidence_record_count for block in blocks), block_count
        ),
        "BLOCKS_PER_IDEA_CLUSTER": _ratio(block_count, len(consumed_cluster_ids)),
        "PROSE_WORDS_PER_IDEA_CLUSTER": _ratio(words, len(meaningful_consumed)),
        "REDUNDANT_BLOCK_RATIO": _ratio(len(repetitive_block_ids), block_count),
        "CORE_TO_OPTIONAL_PROSE_RATIO": (
            round(core_words / optional_words, 4) if optional_words else None
        ),
        "block_count": block_count,
        "word_count": words,
        "consumed_synthesis_unit_count": len(consumed_units),
        "consumed_idea_cluster_count": len(consumed_cluster_ids),
        "meaningful_consumed_idea_cluster_count": len(meaningful_consumed),
        "exactly_one_synthesis_unit_blocks": sum(
            block.synthesis_unit_count == 1 for block in blocks
        ),
        "multi_synthesis_unit_blocks": sum(
            block.synthesis_unit_count >= 2 for block in blocks
        ),
        "mean_synthesis_units_per_block": _ratio(
            sum(block.synthesis_unit_count for block in blocks), block_count
        ),
        "median_synthesis_units_per_block": _median(
            block.synthesis_unit_count for block in blocks
        ),
        "mean_idea_clusters_per_block": _ratio(
            sum(len(block.idea_cluster_ids) for block in blocks), block_count
        ),
        "mean_evidence_records_per_block": _ratio(
            sum(block.evidence_record_count for block in blocks), block_count
        ),
        "overlap_pair_counts": dict(sorted(pair_counts.items())),
        "substantially_overlapping_pairs": [
            overlap.to_dict() for overlap in repetitive_pairs
        ],
        "repetitive_block_ids": repetitive_block_ids,
        "duplicate_parallel_clusters": duplicate_parallel,
    }


def _classify_overlap(
    *, shared_count: int, jaccard: float, containment: float, sequence: float
) -> str:
    if sequence >= 0.90 or (containment >= 0.88 and shared_count >= 8):
        return "NEAR_DUPLICATE"
    if jaccard >= 0.55 or (containment >= 0.70 and shared_count >= 6):
        return "REDUNDANT"
    if jaccard >= 0.30 or (containment >= 0.45 and shared_count >= 4):
        return "RELATED"
    return "DISTINCT"


def _term_set(value: str) -> set[str]:
    return {
        token
        for token in (word.casefold() for word in _WORD_RE.findall(value))
        if token not in _STOPWORDS and not token.isdigit()
    }


def _words(value: str) -> list[str]:
    return _WORD_RE.findall(value)


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _median(values: Iterable[int]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return round((ordered[middle - 1] + ordered[middle]) / 2, 4)


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _text(value: Any, field: str) -> str:
    if isinstance(value, Mapping):
        return str(value.get(field) or "")
    return str(getattr(value, field, "") or "")


def _value(value: Any, field: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)


def _sequence(value: Any, field: str) -> list[str]:
    result = _value(value, field) or []
    return [str(item) for item in result]
