"""Experimental reader-side consolidation for accepted Commentary 1.5.

The dense reader is deliberately downstream of Commentary schema 1.2.  It is
an extractive, deterministic presentation transform: it can remove repeated
framing, remove exact repeated sentences, and join related source blocks, but
it cannot add claims, references, evidence IDs, or source blocks.

This module is candidate-only.  It does not participate in Commentary
generation, synthesis compilation, Gate v2.1, CKL retrieval, or runtime UI
projection.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from bhf_agent import bible
from bhf_agent.chapter_commentary.models import SUPPORTED_SECTION_KINDS
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    QualityClass,
    cluster_synthesis_units,
)
from bhf_agent.presentation.models import EvidenceItem
from bhf_agent.presentation.references import _BOOK_ALIASES
from framework.canonical_library.scripture import parse_scripture_references


DENSE_READER_SCHEMA_VERSION = "0.1"
DENSE_READER_EXPERIMENT_VERSION = "commentary-dense-reader-v0.1"
DENSE_READER_ARTIFACT_VERSION = "dense-reader-synthesis-v0.1"
WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?", re.IGNORECASE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = frozenset(
    "a an and are as at be but by for from has have he her his in is it its of on or "
    "that the their them they this to was were which who with".split()
)

_FRAMING_PREFIXES = (
    r"A cultural detail that clarifies the passage is this:\s*",
    r"Historically, this chapter is read within the following setting:\s*",
    r"This helps frame an interpretive question raised by the passage:\s*",
    r"The surrounding passage context adds this comparison:\s*",
    r"The material or geographical setting adds this bounded context:\s*",
    r"A literary feature to notice is this:\s*",
)


@dataclass(frozen=True)
class DenseReaderUnit:
    """One reader-facing paragraph with complete source ancestry."""

    id: str
    section_kind: str
    section_title: str
    text: str
    verse_refs: list[str]
    evidence_ids: list[str]
    source_block_ids: list[str]
    source_synthesis_ids: list[str]
    source_cluster_ids: list[str] = field(default_factory=list)
    source_quality_classes: list[str] = field(default_factory=list)

    @property
    def synthesis_ids(self) -> list[str]:
        """Compatibility view for existing read-only dump diagnostics."""

        return self.source_synthesis_ids

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DenseReaderArtifact:
    """Versioned sidecar artifact for a single accepted Commentary chapter."""

    artifact_version: str
    schema_version: str
    experiment_version: str
    reference: str
    book: str
    chapter: int
    status: str
    source_commentary: dict[str, Any]
    generation: dict[str, Any]
    diagnostics: dict[str, Any]
    units: list[DenseReaderUnit]
    validation: dict[str, Any]
    artifact_identity: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = {
            "artifact_version": self.artifact_version,
            "schema_version": self.schema_version,
            "experiment_version": self.experiment_version,
            "reference": self.reference,
            "book": self.book,
            "chapter": self.chapter,
            "status": self.status,
            "source_commentary": self.source_commentary,
            "generation": self.generation,
            "diagnostics": self.diagnostics,
            "units": [unit.to_dict() for unit in self.units],
            "validation": self.validation,
        }
        if self.artifact_identity:
            value["artifact_identity"] = self.artifact_identity
        return value


class DenseReaderValidationError(ValueError):
    """Raised when a reader sidecar cannot be proven to descend from its source."""


def calculate_artifact_identity(artifact: DenseReaderArtifact | Mapping[str, Any]) -> str:
    """Calculate the stable identity, excluding the identity field itself."""

    payload = _as_mapping(artifact)
    payload.pop("artifact_identity", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_reader_artifact(path: str | Path) -> DenseReaderArtifact:
    """Deserialize one experimental reader artifact."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _artifact_from_dict(data)


def save_reader_artifact(artifact: DenseReaderArtifact, path: str | Path) -> Path:
    """Write one reader artifact with its deterministic identity."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    identity = calculate_artifact_identity(artifact)
    payload = artifact.to_dict()
    payload["artifact_identity"] = identity
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def build_reader_artifact(
    source_payload: Mapping[str, Any],
    *,
    source_path: str | Path,
    source_root: str | Path,
    synthesis: Any | None = None,
    evidence_items: Iterable[EvidenceItem] = (),
    source_word_count: int | None = None,
    source_dump_severity: str = "UNKNOWN",
    source_quality_metrics: Mapping[str, Any] | None = None,
    force_consolidation: bool = False,
) -> DenseReaderArtifact:
    """Build a deterministic reader sidecar from one accepted source object.

    All source blocks are represented.  The reader transform therefore keeps
    exact source evidence and reference unions even when multiple blocks are
    joined.  Future experiments may omit low-priority blocks only by adding a
    separate explicit retention contract; this v0.1 experiment does not make
    that lossy choice.
    """

    source = _validate_source_shape(source_payload)
    source_path = Path(source_path)
    source_root = Path(source_root).resolve()
    source_hash = _sha256_file(source_path)
    source_relative = _relative_or_absolute(source_path, source_root)
    source_metadata = dict(source.get("generated_metadata") or {})
    source_blocks = _source_blocks(source)
    source_words = source_word_count if source_word_count is not None else _word_count(
        block["text"] for block in source_blocks
    )

    items = list(evidence_items)
    cluster_by_unit: dict[str, Any] = {}
    if synthesis is not None:
        clusters = cluster_synthesis_units(
            synthesis.synthesis_units,
            items,
            core_classifier=CORE_CLASSIFIER_V2,
        )
        cluster_by_unit = {
            synthesis_id: cluster
            for cluster in clusters
            for synthesis_id in cluster.synthesis_ids
        }

    activation = _activation_decision(
        source_words=source_words,
        source_block_count=len(source_blocks),
        source_dump_severity=source_dump_severity,
        source_quality_metrics=source_quality_metrics or {},
        force_consolidation=force_consolidation,
    )
    selected_blocks = _select_source_blocks(source_blocks, cluster_by_unit, active=activation["active"])
    selected_ids = {str(block["id"]) for block in selected_blocks}
    omitted_ids = [str(block["id"]) for block in source_blocks if str(block["id"]) not in selected_ids]
    groups = _group_blocks(selected_blocks, cluster_by_unit, active=activation["active"])
    units: list[DenseReaderUnit] = []
    for unit_index, indexes in enumerate(groups, start=1):
        grouped = [selected_blocks[index] for index in indexes]
        first = grouped[0]
        text = _consolidate_text(
            (block["text"] for block in grouped),
            deduplicate=activation["active"],
        )
        if not text:
            # This is defensive only; source validation already rejects empty
            # blocks and the transform is not permitted to create an empty unit.
            text = _normalize_text(first["text"])
        synthesis_ids = _unique(
            synthesis_id
            for block in grouped
            for synthesis_id in block.get("synthesis_ids", [])
        )
        cluster_ids = _unique(
            cluster_by_unit[synthesis_id].id
            for synthesis_id in synthesis_ids
            if synthesis_id in cluster_by_unit
        )
        quality_classes = _ordered_quality_classes(
            cluster_by_unit[synthesis_id].quality_class
            for synthesis_id in synthesis_ids
            if synthesis_id in cluster_by_unit
        )
        units.append(
            DenseReaderUnit(
                id=f"reader_unit_{unit_index:03d}",
                section_kind=str(first["section_kind"]),
                section_title=str(first["section_title"]),
                text=text,
                verse_refs=_unique(ref for block in grouped for ref in block.get("verse_refs", [])),
                evidence_ids=_unique(
                    evidence_id for block in grouped for evidence_id in block.get("evidence_ids", [])
                ),
                source_block_ids=_unique(block["id"] for block in grouped),
                source_synthesis_ids=synthesis_ids,
                source_cluster_ids=cluster_ids,
                source_quality_classes=quality_classes,
            )
        )

    generation = {
        "transform_version": DENSE_READER_EXPERIMENT_VERSION,
        "method": "deterministic_extract_and_group",
        "source_input_sha256": source_hash,
        "generation_identity": f"{DENSE_READER_EXPERIMENT_VERSION}:{source_hash}",
    }
    diagnostics = {
        "activation": activation,
        "source_word_count": source_words,
        "source_block_count": len(source_blocks),
        "omitted_source_block_ids": omitted_ids,
        "omission_reasons": {
            block_id: "low_value_repetitive_background"
            for block_id in omitted_ids
        },
        "reader_word_count": _word_count(unit.text for unit in units),
        "reader_unit_count": len(units),
        "grouping_strategy": "same-section cluster/evidence/text relationship; exact sentence deduplication",
        "lossy_block_selection": False,
        "warnings": [],
    }
    artifact = DenseReaderArtifact(
        artifact_version=DENSE_READER_ARTIFACT_VERSION,
        schema_version=DENSE_READER_SCHEMA_VERSION,
        experiment_version=DENSE_READER_EXPERIMENT_VERSION,
        reference=str(source["reference"]),
        book=str(source["book"]),
        chapter=int(source["chapter"]),
        status="pending_validation",
        source_commentary={
            "artifact_path": source_relative,
            "artifact_sha256": source_hash,
            "artifact_identity": f"sha256:{source_hash}",
            "prompt_version": source_metadata.get("commentary_prompt_version"),
            "schema_version": source_metadata.get("commentary_schema_version"),
            "synthesis_schema_version": source_metadata.get("synthesis_schema_version"),
            "synthesis_compiler_version": source_metadata.get("synthesis_compiler_version"),
            "status": source.get("status"),
        },
        generation=generation,
        diagnostics=diagnostics,
        units=units,
        validation={"status": "pending", "errors": [], "warnings": []},
    )
    return artifact


def validate_reader_artifact(
    artifact: DenseReaderArtifact | Mapping[str, Any],
    *,
    source_payload: Mapping[str, Any],
    source_path: str | Path,
    source_root: str | Path,
    synthesis: Any | None = None,
    evidence_items: Iterable[EvidenceItem] = (),
) -> tuple[str, ...]:
    """Strictly validate identity, ancestry, references, and CORE retention."""

    value = _artifact_from_dict(_as_mapping(artifact)) if not isinstance(artifact, DenseReaderArtifact) else artifact
    source = _validate_source_shape(source_payload)
    errors: list[str] = []
    if value.artifact_version != DENSE_READER_ARTIFACT_VERSION:
        errors.append("unsupported dense reader artifact version")
    if value.schema_version != DENSE_READER_SCHEMA_VERSION:
        errors.append("unsupported dense reader schema version")
    if value.experiment_version != DENSE_READER_EXPERIMENT_VERSION:
        errors.append("unsupported dense reader experiment version")
    if value.artifact_identity and value.artifact_identity != calculate_artifact_identity(value):
        errors.append("artifact_identity does not match deterministic content")
    if value.reference != source.get("reference") or value.book != source.get("book") or value.chapter != int(source.get("chapter", 0)):
        errors.append("reader chapter identity does not match source Commentary artifact")
    try:
        resolved = bible.resolve_chapter(value.book, value.chapter)
        if resolved["book"] != value.book:
            errors.append("reader book is not canonical")
    except (KeyError, TypeError, ValueError):
        errors.append("reader chapter is not canonical")

    source_path = Path(source_path)
    source_root = Path(source_root).resolve()
    expected_hash = _sha256_file(source_path)
    source_meta = value.source_commentary
    if source_meta.get("artifact_sha256") != expected_hash:
        errors.append("source Commentary artifact hash mismatch")
    if source_meta.get("artifact_identity") != f"sha256:{expected_hash}":
        errors.append("source Commentary artifact identity mismatch")
    expected_path = _relative_or_absolute(source_path, source_root)
    if source_meta.get("artifact_path") != expected_path:
        errors.append("source Commentary artifact path mismatch")
    source_metadata = dict(source.get("generated_metadata") or {})
    if source_meta.get("prompt_version") != source_metadata.get("commentary_prompt_version"):
        errors.append("source prompt identity mismatch")
    if source_meta.get("schema_version") != source_metadata.get("commentary_schema_version"):
        errors.append("source Commentary schema identity mismatch")
    if value.generation.get("source_input_sha256") != expected_hash:
        errors.append("generation source hash mismatch")

    source_blocks = _source_blocks(source)
    source_by_id = {block["id"]: block for block in source_blocks}
    unit_ids = [unit.id for unit in value.units]
    if len(unit_ids) != len(set(unit_ids)):
        errors.append("duplicate reader unit IDs")
    if not value.units:
        errors.append("reader output has no units")

    mapped_block_ids: list[str] = []
    source_synthesis_by_block: dict[str, set[str]] = {}
    source_evidence_by_block: dict[str, set[str]] = {}
    source_refs_by_block: dict[str, set[str]] = {}
    for block in source_blocks:
        block_id = str(block["id"])
        source_synthesis_by_block[block_id] = set(_sequence(block, "synthesis_ids"))
        source_evidence_by_block[block_id] = set(_sequence(block, "evidence_ids"))
        source_refs_by_block[block_id] = set(_sequence(block, "verse_refs"))

    for unit in value.units:
        if unit.section_kind not in SUPPORTED_SECTION_KINDS:
            errors.append(f"{unit.id} has unsupported section kind")
        if not unit.text.strip():
            errors.append(f"{unit.id} has empty reader text")
        if not unit.source_block_ids:
            errors.append(f"{unit.id} has no source block mapping")
        unknown_blocks = sorted(set(unit.source_block_ids) - set(source_by_id))
        if unknown_blocks:
            errors.append(f"{unit.id} has fabricated source block IDs: {unknown_blocks}")
            continue
        mapped_block_ids.extend(unit.source_block_ids)
        expected_synthesis = set().union(*(source_synthesis_by_block[block_id] for block_id in unit.source_block_ids))
        expected_evidence = set().union(*(source_evidence_by_block[block_id] for block_id in unit.source_block_ids))
        expected_refs = set().union(*(source_refs_by_block[block_id] for block_id in unit.source_block_ids))
        if set(unit.source_synthesis_ids) != expected_synthesis:
            errors.append(f"{unit.id} source synthesis ancestry is not the mapped union")
        if set(unit.evidence_ids) != expected_evidence:
            errors.append(f"{unit.id} evidence ancestry is not the mapped union")
        if set(unit.verse_refs) != expected_refs:
            errors.append(f"{unit.id} verse-reference ancestry is not the mapped union")
        for evidence_id in unit.evidence_ids:
            if not isinstance(evidence_id, str) or not evidence_id.strip():
                errors.append(f"{unit.id} has an invalid evidence ID")
        for reference in unit.verse_refs:
            if not _valid_reference(reference):
                errors.append(f"{unit.id} has invalid verse reference: {reference}")
    if len(mapped_block_ids) != len(set(mapped_block_ids)):
        errors.append("source block is mapped to more than one reader unit")
    omitted_ids = set(str(value) for value in value.diagnostics.get("omitted_source_block_ids") or [])
    if omitted_ids - set(source_by_id):
        errors.append("omitted source block list contains unknown IDs")
    if set(mapped_block_ids).intersection(omitted_ids):
        errors.append("source block is both mapped and omitted")
    if set(mapped_block_ids) | omitted_ids != set(source_by_id):
        errors.append("source block mapping and omission accounting is incomplete")

    if synthesis is not None:
        items = list(evidence_items)
        valid_synthesis_ids = {unit.id for unit in synthesis.synthesis_units}
        valid_evidence_ids = {item.id for item in items}
        mapped_synthesis_ids = {sid for unit in value.units for sid in unit.source_synthesis_ids}
        mapped_evidence_ids = {eid for unit in value.units for eid in unit.evidence_ids}
        if mapped_synthesis_ids - valid_synthesis_ids:
            errors.append("reader contains fabricated synthesis IDs")
        if mapped_evidence_ids - valid_evidence_ids:
            errors.append("reader contains fabricated evidence IDs")
        clusters = cluster_synthesis_units(synthesis.synthesis_units, items, core_classifier=CORE_CLASSIFIER_V2)
        cluster_by_unit = {sid: cluster for cluster in clusters for sid in cluster.synthesis_ids}
        valid_cluster_ids = {cluster.id for cluster in clusters}
        for unit in value.units:
            expected_cluster_ids = {
                cluster_by_unit[sid].id
                for sid in unit.source_synthesis_ids
                if sid in cluster_by_unit
            }
            if set(unit.source_cluster_ids) != expected_cluster_ids:
                errors.append(f"{unit.id} source cluster ancestry is not the synthesis union")
            if set(unit.source_cluster_ids) - valid_cluster_ids:
                errors.append(f"{unit.id} contains fabricated source cluster IDs")
        required_core = {
            sid
            for block in source_blocks
            for sid in _sequence(block, "synthesis_ids")
            if sid in cluster_by_unit and cluster_by_unit[sid].quality_class == QualityClass.CORE.value
        }
        if not required_core.issubset(mapped_synthesis_ids):
            errors.append("reader omitted one or more source CORE synthesis IDs")
        core_block_ids = {
            str(block["id"])
            for block in source_blocks
            if any(
                sid in cluster_by_unit
                and cluster_by_unit[sid].quality_class == QualityClass.CORE.value
                for sid in _sequence(block, "synthesis_ids")
            )
        }
        if omitted_ids.intersection(core_block_ids):
            errors.append("reader omission list contains a source CORE block")
    return tuple(errors)


def require_valid_reader_artifact(*args: Any, **kwargs: Any) -> None:
    errors = validate_reader_artifact(*args, **kwargs)
    if errors:
        raise DenseReaderValidationError("; ".join(errors))


def _activation_decision(
    *,
    source_words: int,
    source_block_count: int,
    source_dump_severity: str,
    source_quality_metrics: Mapping[str, Any],
    force_consolidation: bool,
) -> dict[str, Any]:
    if force_consolidation:
        return {"active": True, "signal": "EXPLICIT_EXPERIMENT_ACTIVATION", "signals": ["explicit"]}
    signals: list[str] = []
    if str(source_dump_severity).upper() in {"LOW", "MODERATE", "HIGH"}:
        signals.append("dump_severity")
    if source_block_count >= 20:
        signals.append("high_block_count")
    if source_words >= 2200:
        signals.append("high_word_count")
    weighted = source_quality_metrics.get("weighted_coverage")
    utilization = source_quality_metrics.get("synthesis_utilization")
    if isinstance(weighted, (int, float)) and weighted < 0.70:
        signals.append("low_weighted_coverage")
    if isinstance(utilization, (int, float)) and utilization < 0.75:
        signals.append("low_utilization")
    # Density/length alone does not activate the transform.  At least one
    # dump/fragmentation signal and a second stress signal are required.
    active = (
        bool(signals)
        and ("dump_severity" in signals or "low_weighted_coverage" in signals or "low_utilization" in signals)
        and len(signals) >= 2
    )
    return {
        "active": active,
        "signal": "multi_signal_stress" if active else "adaptive_restraint",
        "signals": signals,
    }


def _group_blocks(
    blocks: Sequence[Mapping[str, Any]],
    cluster_by_unit: Mapping[str, Any],
    *,
    active: bool,
) -> list[list[int]]:
    if not active:
        return [[index] for index in range(len(blocks))]
    parent = list(range(len(blocks)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left_index, left in enumerate(blocks):
        left_clusters = {
            cluster_by_unit[synthesis_id].id
            for synthesis_id in _sequence(left, "synthesis_ids")
            if synthesis_id in cluster_by_unit
        }
        left_evidence = set(_sequence(left, "evidence_ids"))
        left_terms = _terms(_normalize_text(str(left.get("text") or "")))
        for right_index in range(left_index):
            right = blocks[right_index]
            if left.get("section_index") != right.get("section_index"):
                continue
            right_clusters = {
                cluster_by_unit[synthesis_id].id
                for synthesis_id in _sequence(right, "synthesis_ids")
                if synthesis_id in cluster_by_unit
            }
            if left_clusters.intersection(right_clusters):
                union(left_index, right_index)
                continue
            shared_evidence = left_evidence.intersection(_sequence(right, "evidence_ids"))
            right_terms = _terms(_normalize_text(str(right.get("text") or "")))
            shared_terms = left_terms.intersection(right_terms)
            union_terms = left_terms.union(right_terms)
            jaccard = len(shared_terms) / len(union_terms) if union_terms else 0.0
            sequence = SequenceMatcher(None, " ".join(sorted(left_terms)), " ".join(sorted(right_terms))).ratio()
            if shared_evidence and (jaccard >= 0.22 or len(shared_terms) >= 3):
                union(left_index, right_index)
            elif sequence >= 0.90:
                union(left_index, right_index)

    grouped: dict[int, list[int]] = {}
    for index in range(len(blocks)):
        grouped.setdefault(find(index), []).append(index)
    return sorted(grouped.values(), key=lambda indexes: min(indexes))


def _select_source_blocks(
    blocks: Sequence[Mapping[str, Any]],
    cluster_by_unit: Mapping[str, Any],
    *,
    active: bool,
) -> list[Mapping[str, Any]]:
    """Omit only low-value, single-record repetition in active chapters.

    The selection is intentionally conservative.  A block with a CORE
    cluster, multiple source records, disputed interpretation, or a specific
    contextual shape remains.  The omission list is part of the artifact and
    is checked against CORE ancestry by the validator.
    """

    if not active:
        return list(blocks)
    selected: list[Mapping[str, Any]] = []
    for block in blocks:
        synthesis_ids = _sequence(block, "synthesis_ids")
        classes = {
            cluster_by_unit[synthesis_id].quality_class
            for synthesis_id in synthesis_ids
            if synthesis_id in cluster_by_unit
        }
        if QualityClass.CORE.value in classes or QualityClass.DISPUTED.value in classes:
            selected.append(block)
            continue
        text = _normalize_text(str(block.get("text") or "")).casefold()
        if len(synthesis_ids) >= 2 or len(_sequence(block, "evidence_ids")) >= 2:
            selected.append(block)
            continue
        if str(block.get("section_kind") or "") in {
            "archaeology_geography",
            "chronology",
            "language_literary",
        }:
            selected.append(block)
            continue
        generic_background = any(
            phrase in text
            for phrase in (
                "ancient background for",
                "belongs to a social world",
                "is located by its canonical setting",
                "historically, ",
            )
        )
        if not generic_background:
            selected.append(block)
    return selected


def _consolidate_text(values: Iterable[str], *, deduplicate: bool = True) -> str:
    sentences: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        for sentence in SENTENCE_RE.split(normalized):
            sentence = sentence.strip()
            if not sentence:
                continue
            key = " ".join(WORD_RE.findall(sentence.casefold()))
            if deduplicate and key and key in seen:
                continue
            if deduplicate and any(_repeated_template_sentence(sentence, prior) for prior in sentences):
                continue
            sentences.append(sentence)
            seen.add(key)
    return " ".join(sentences).strip()


def _repeated_template_sentence(candidate: str, prior: str) -> bool:
    """Recognize repeated generated background templates without new prose."""

    candidate_lower = candidate.casefold()
    prior_lower = prior.casefold()
    markers = (
        "ancient background for",
        "belongs to a social world",
        "historically, ",
        "is located by its canonical setting",
    )
    marker = next((value for value in markers if value in candidate_lower and value in prior_lower), None)
    if marker is None:
        return False
    candidate_terms = _terms(candidate)
    prior_terms = _terms(prior)
    shared = candidate_terms.intersection(prior_terms)
    union = candidate_terms.union(prior_terms)
    similarity = len(shared) / len(union) if union else 0.0
    return similarity >= 0.70


def _normalize_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    for pattern in _FRAMING_PREFIXES:
        text = re.sub(r"^" + pattern, "", text, count=1, flags=re.IGNORECASE)
    text = _collapse_exact_halves(text)
    return text.strip()


def _collapse_exact_halves(value: str) -> str:
    tokens = value.split()
    if len(tokens) >= 4 and len(tokens) % 2 == 0:
        midpoint = len(tokens) // 2
        if [token.casefold() for token in tokens[:midpoint]] == [token.casefold() for token in tokens[midpoint:]]:
            return " ".join(tokens[:midpoint])
    return value


def _source_blocks(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for section_index, section in enumerate(source.get("sections") or []):
        if not isinstance(section, Mapping):
            continue
        for block in section.get("blocks") or []:
            if not isinstance(block, Mapping):
                continue
            value = dict(block)
            value["section_index"] = section_index
            value["section_kind"] = section.get("kind")
            value["section_title"] = section.get("title")
            blocks.append(value)
    return blocks


def _validate_source_shape(source: Mapping[str, Any]) -> Mapping[str, Any]:
    required = ("reference", "book", "chapter", "sections")
    missing = [key for key in required if key not in source]
    if missing:
        raise DenseReaderValidationError(f"source Commentary artifact missing fields: {missing}")
    for block in _source_blocks(source):
        if not str(block.get("id") or "").strip():
            raise DenseReaderValidationError("source Commentary artifact contains a block without an ID")
        if not str(block.get("text") or "").strip():
            raise DenseReaderValidationError(f"source block {block.get('id')} is empty")
    return source


def _artifact_from_dict(data: Mapping[str, Any]) -> DenseReaderArtifact:
    return DenseReaderArtifact(
        artifact_version=str(data["artifact_version"]),
        schema_version=str(data["schema_version"]),
        experiment_version=str(data["experiment_version"]),
        reference=str(data["reference"]),
        book=str(data["book"]),
        chapter=int(data["chapter"]),
        status=str(data["status"]),
        source_commentary=dict(data.get("source_commentary") or {}),
        generation=dict(data.get("generation") or {}),
        diagnostics=dict(data.get("diagnostics") or {}),
        units=[DenseReaderUnit(**unit) for unit in data.get("units") or []],
        validation=dict(data.get("validation") or {}),
        artifact_identity=str(data.get("artifact_identity") or ""),
    )


def _as_mapping(value: DenseReaderArtifact | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, DenseReaderArtifact):
        return value.to_dict()
    return json.loads(json.dumps(dict(value)))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _valid_reference(value: str) -> bool:
    try:
        spans = parse_scripture_references(value, book_alias_lookup=_BOOK_ALIASES)
    except (TypeError, ValueError):
        return False
    return bool(spans)


def _word_count(values: Iterable[str]) -> int:
    return sum(len(WORD_RE.findall(str(value or ""))) for value in values)


def _terms(value: str) -> set[str]:
    return {
        token.casefold()
        for token in WORD_RE.findall(value)
        if token.casefold() not in STOPWORDS and not token.isdigit()
    }


def _sequence(value: Mapping[str, Any], key: str) -> list[str]:
    return [str(item) for item in value.get(key) or []]


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _ordered_quality_classes(values: Iterable[str]) -> list[str]:
    order = {
        QualityClass.CORE.value: 0,
        QualityClass.DISPUTED.value: 1,
        QualityClass.SUPPORTING.value: 2,
        QualityClass.SURROUNDING.value: 3,
        QualityClass.OPTIONAL.value: 4,
    }
    return sorted(_unique(values), key=lambda value: (order.get(value, 99), value))


__all__ = [
    "DENSE_READER_ARTIFACT_VERSION",
    "DENSE_READER_EXPERIMENT_VERSION",
    "DENSE_READER_SCHEMA_VERSION",
    "DenseReaderArtifact",
    "DenseReaderUnit",
    "DenseReaderValidationError",
    "build_reader_artifact",
    "calculate_artifact_identity",
    "load_reader_artifact",
    "require_valid_reader_artifact",
    "save_reader_artifact",
    "validate_reader_artifact",
]
