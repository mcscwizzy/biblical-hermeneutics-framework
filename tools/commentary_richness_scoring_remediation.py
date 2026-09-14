#!/usr/bin/env python3
"""Freeze and audit the bounded Commentary v1.2 richness-score remediation.

The historical renderer evaluations and response bytes remain immutable.  This
tool records their identities and emits a cluster-level denominator audit
before any candidate scoring policy is applied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bhf_agent import bible
from bhf_agent.chapter_commentary.models import COMMENTARY_SCHEMA_VERSION, GeneratedMetadata
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.richness import audit_chapter
from bhf_agent.chapter_commentary.richness_clusters import (
    CORE_CLASSIFIER_V2,
    COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
    RICHNESS_CLUSTER_AUDIT_VERSION_V2,
    RICHNESS_GATE_V2_VERSION,
    RICHNESS_POLICY_VERSION,
    RICHNESS_POLICY_VERSION_V3,
    QualityClass,
    assess_gate_v2,
    cluster_synthesis_units,
    score_synthesis_richness,
)
from bhf_agent.chapter_commentary.validation import validate_chapter_commentary
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION
from framework.commentary.production.inputs import prepare_chapter
from framework.commentary.production.models import (
    ArtifactCollisionError,
    sha256_bytes,
    write_immutable,
)


ARTIFACT_VERSION = "commentary-richness-scoring-remediation-v1"
FREEZE_VERSION = "commentary-richness-scoring-remediation-freeze-v1"
DENOMINATOR_AUDIT_VERSION = "commentary-richness-denominator-audit-v3"
COUNTERFACTUAL_EVALUATION_VERSION = "commentary-richness-counterfactual-evaluation-v3"
CALIBRATION_VERSION = "commentary-richness-scoring-calibration-v1"
OVERLAP_AUDIT_VERSION = "commentary-richness-overlap-audit-v1"
QUALIFICATION_ID = "renderer-qualification-v1-gpt-5.6-sol-a0f4063638cf9730958a"
REMEDIATION_ID = "renderer-remediation-v1-gpt-5.6-sol-2d03bb002c24cdbcca72"
TARGETS = (
    ("Exodus 14", "Exodus", 14),
    ("Deuteronomy 10", "Deuteronomy", 10),
    ("Job 1", "Job", 1),
    ("Revelation 21", "Revelation", 21),
)
DEFAULT_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates"
    / "richness-scoring-remediation-v1"
)
QUALIFICATION_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates"
    / "renderer-qualification-v1/gpt-5.6-sol"
)
REMEDIATION_ROOT = (
    ROOT
    / ".bhf-data/bhf-commentary-candidates"
    / "renderer-contract-remediation-v1/gpt-5.6-sol/prompt-1.6"
)

_WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")
_TITLE_STOPWORDS = frozenset(
    "a an and does framework is of significance story storyline symbol the theme what why".split()
)
_LOW_INFORMATION_PATTERNS = (
    "as the relevant passages require",
    "belongs to a social world",
    "entry connects that setting",
    "entry ties that world",
    "is located by its canonical setting",
    "is read across the canon as scripture develops this theme",
    "this feature belongs to the landscapes",
    "this figure is associated with",
)


class ScoringRemediationError(RuntimeError):
    """A frozen input is missing, changed, or internally inconsistent."""


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoringRemediationError(f"invalid JSON artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScoringRemediationError(f"JSON artifact must be an object: {path}")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _write_json_immutable(path: Path, value: Any) -> str:
    return write_immutable(path, _json_bytes(value))


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _hashed_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ScoringRemediationError(f"missing historical artifact: {path}")
    raw = path.read_bytes()
    return {
        "path": _relative(path),
        "sha256": sha256_bytes(raw),
        "byte_count": len(raw),
    }


def _historical_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    qualification_manifest = _read(QUALIFICATION_ROOT / "qualification-manifest.json")
    qualification_evaluation = _read(QUALIFICATION_ROOT / "evaluation/evaluation.json")
    remediation_manifest = _read(REMEDIATION_ROOT / "manifest.json")
    remediation_evaluation = _read(REMEDIATION_ROOT / "evaluation/evaluation.json")
    if qualification_manifest.get("qualification_id") != QUALIFICATION_ID:
        raise ScoringRemediationError("historical qualification ID mismatch")
    if qualification_evaluation.get("qualification_id") != QUALIFICATION_ID:
        raise ScoringRemediationError("historical qualification evaluation ID mismatch")
    if remediation_manifest.get("remediation_id") != REMEDIATION_ID:
        raise ScoringRemediationError("historical remediation ID mismatch")
    if remediation_evaluation.get("remediation_id") != REMEDIATION_ID:
        raise ScoringRemediationError("historical remediation evaluation ID mismatch")
    return (
        qualification_manifest,
        qualification_evaluation,
        remediation_manifest,
        remediation_evaluation,
    )


def freeze(*, output_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Record immutable identities for both historical evaluations and all raw bytes."""

    q_manifest, q_evaluation, r_manifest, r_evaluation = _historical_inputs()
    files = [
        _hashed_file(QUALIFICATION_ROOT / "qualification-manifest.json"),
        _hashed_file(QUALIFICATION_ROOT / "evaluation/evaluation.json"),
        _hashed_file(QUALIFICATION_ROOT / "responses/import-receipt.json"),
        _hashed_file(REMEDIATION_ROOT / "manifest.json"),
        _hashed_file(REMEDIATION_ROOT / "evaluation/evaluation.json"),
        _hashed_file(REMEDIATION_ROOT / "responses/import-receipt.json"),
    ]
    for row in q_manifest["chapters"]:
        files.append(_hashed_file(QUALIFICATION_ROOT / "responses/raw" / row["response_filename"]))
    for row in r_manifest["chapters"]:
        files.append(_hashed_file(REMEDIATION_ROOT / "responses/raw" / row["response_filename"]))
    result = {
        "artifact_version": FREEZE_VERSION,
        "namespace_version": ARTIFACT_VERSION,
        "bounded_scope": "Commentary v1.2 richness/coverage scoring only",
        "qualification_id": QUALIFICATION_ID,
        "remediation_id": REMEDIATION_ID,
        "historical_contracts": {
            "qualification": q_evaluation["frozen_contracts"],
            "remediation": r_evaluation["contracts"],
        },
        "historical_results": {
            "qualification_result": q_evaluation["qualification_result"],
            "qualification_summary": q_evaluation["comparison"]["gpt_5_6_sol"],
            "remediation_result": r_evaluation["bounded_result"],
            "remediation_summary": r_evaluation["summary"],
        },
        "file_count": len(files),
        "files": sorted(files, key=lambda row: row["path"]),
    }
    result["freeze_identity"] = hashlib.sha256(_json_bytes(result)).hexdigest()
    _write_json_immutable(output_root / "freeze/historical-results.json", result)
    return result


def _consumed_ids(raw_path: Path) -> set[str]:
    payload = _read(raw_path)
    return {
        str(synthesis_id)
        for section in payload.get("sections", [])
        for block in section.get("blocks", [])
        for synthesis_id in block.get("synthesis_ids", [])
    }


def _words(value: str) -> set[str]:
    return set(_WORD_RE.findall(value.casefold()))


def _title_words(value: str) -> tuple[str, ...]:
    return tuple(
        word
        for word in _WORD_RE.findall(value.casefold())
        if word not in _TITLE_STOPWORDS and not word.isdigit() and len(word) >= 3
    )


def _raw_inventory(facts: Iterable[str]) -> bool:
    values = [str(value).strip() for value in facts if str(value).strip()]
    return bool(values) and all(
        len(value.split()) <= 4 and not re.search(r"[.!?]", value)
        for value in values
    )


def _low_information(facts: Iterable[str]) -> bool:
    text = " ".join(str(value) for value in facts).casefold()
    return any(pattern in text for pattern in _LOW_INFORMATION_PATTERNS)


def _central_parent_ratio(cluster: Any, evidence: dict[str, Any], passage_text: str) -> float:
    passage_words = _WORD_RE.findall(passage_text.casefold())
    parent_groups: dict[str, tuple[str, ...]] = {}
    for evidence_id in cluster.evidence_ids:
        item = evidence.get(evidence_id)
        metadata = getattr(item, "relevance_metadata", {}) or {}
        parent_id = str(metadata.get("parent_object_id") or "").strip()
        parent_title = str(metadata.get("parent_title") or "").strip()
        if not parent_id or not parent_title:
            continue
        parent_groups.setdefault(parent_id, _title_words(parent_title))
    if not parent_groups:
        return 0.0
    matches = sum(
        bool(words)
        and any(
            tuple(passage_words[index : index + len(words)]) == words
            for index in range(len(passage_words) - len(words) + 1)
        )
        for words in parent_groups.values()
    )
    return round(matches / len(parent_groups), 4)


def _reader_relevance_judgment(
    cluster: Any,
    *,
    evidence: dict[str, Any],
    facts: list[str],
    passage_text: str,
) -> tuple[bool, str]:
    """Pre-policy audit judgment; this does not participate in scoring."""

    bases = set(cluster.importance_basis)
    if cluster.quality_class == QualityClass.CORE.value:
        return True, "direct passage context, explicit significance, or a passage-understanding unit"
    if cluster.quality_class == QualityClass.DISPUTED.value:
        return True, "bounded interpretive uncertainty or reception materially informs reader understanding"
    if "specific_contextual_support" in bases:
        if _raw_inventory(facts):
            return False, "raw related-entity inventory is available context, not a reader-level explanatory idea"
        return True, "specific contextual contribution supplies a distinct explanatory idea"
    if "entity_background_not_direct_passage_context" in bases:
        ratio = _central_parent_ratio(cluster, evidence, passage_text)
        if ratio >= 0.5 and not _low_information(facts) and not _raw_inventory(facts):
            return True, "non-template entity context is tied to a majority of parent entities named in the chapter"
        return False, "generic, template-like, inventory-like, or non-central entity association is not required commentary coverage"
    if "general_contextual_support" in bases:
        ratio = _central_parent_ratio(cluster, evidence, passage_text)
        if ratio >= 0.5 and not _low_information(facts) and not _raw_inventory(facts):
            return True, "non-template contextual explanation concerns a chapter-named central concept"
        return False, "general or global background lacks a strong deterministic chapter-specific contribution"
    if "surrounding_passage_scope" in bases:
        return False, "surrounding-passage material is valid context but not required chapter coverage without a stronger signal"
    return False, "no deterministic reader-relevance signal stronger than technical association"


def _basis_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Split a cluster's weight equally across listed bases to avoid double counting."""

    weights: defaultdict[str, float] = defaultdict(float)
    total = sum(float(row["weight"]) for row in rows)
    for row in rows:
        bases = row["importance_basis"] or ["other"]
        share = float(row["weight"]) / len(bases)
        for basis in bases:
            weights[str(basis)] += share
    expected_bases = (
        "direct_passage_context",
        "explicit_passage_significance",
        "passage_understanding_unit_kind",
        "specific_contextual_support",
        "general_contextual_support",
        "entity_background_not_direct_passage_context",
        "surrounding_passage_scope",
        "disputed_or_contested_evidence",
        "other",
    )
    known = set(expected_bases) - {"other"}
    weights["other"] += sum(
        weight for basis, weight in list(weights.items()) if basis not in known and basis != "other"
    )
    ordered = {}
    for basis in expected_bases:
        weight = weights[basis]
        ordered[basis] = {
            "attributed_weight": round(weight, 4),
            "denominator_percentage": round(100.0 * weight / total, 2) if total else 0.0,
        }
    return {
        "attribution_method": "equal split across a cluster's recorded importance_basis values",
        "weighted_denominator": round(total, 4),
        "by_importance_basis": ordered,
    }


def denominator_audit(*, output_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Emit the required pre-change audit for every currently weighted target cluster."""

    q_manifest, q_evaluation, r_manifest, r_evaluation = _historical_inputs()
    q_rows = {row["reference"]: row for row in q_manifest["chapters"]}
    q_scores = {row["reference"]: row for row in q_evaluation["chapters"]}
    r_rows = {row["reference"]: row for row in r_manifest["chapters"]}
    r_scores = {row["reference"]: row for row in r_evaluation["chapters"]}
    chapters = []
    for reference, book, chapter in TARGETS:
        prepared = prepare_chapter(book, chapter)
        units = {unit.id: unit for unit in prepared.synthesis.synthesis_units}
        evidence = {item.id: item for item in prepared.bundle.evidence_items}
        live_clusters = cluster_synthesis_units(
            units.values(), evidence, core_classifier=CORE_CLASSIFIER_V2
        )
        historical_clusters = (q_scores[reference].get("score") or {}).get("clusters") or []
        comparable_live = [
            {key: cluster.to_dict().get(key) for key in historical.keys()}
            for cluster, historical in zip(live_clusters, historical_clusters, strict=True)
        ]
        if comparable_live != historical_clusters:
            raise ScoringRemediationError(f"historical cluster assignments changed for {reference}")
        q_raw = QUALIFICATION_ROOT / "responses/raw" / q_rows[reference]["response_filename"]
        r_raw = REMEDIATION_ROOT / "responses/raw" / r_rows[reference]["response_filename"]
        original_consumed = _consumed_ids(q_raw)
        remediation_consumed = _consumed_ids(r_raw)
        passage_text = bible.passage_text(bible.resolve_chapter(book, chapter).get("verses", []))
        cluster_rows = []
        for cluster in live_clusters:
            if cluster.quality_class == QualityClass.OPTIONAL.value:
                continue
            facts = [
                fact
                for synthesis_id in cluster.synthesis_ids
                for fact in units[synthesis_id].facts
            ]
            relevant, reason = _reader_relevance_judgment(
                cluster,
                evidence=evidence,
                facts=facts,
                passage_text=passage_text,
            )
            cluster_rows.append(
                {
                    "cluster_id": cluster.id,
                    "synthesis_ids": cluster.synthesis_ids,
                    "evidence_ids": cluster.evidence_ids,
                    "quality_class": cluster.quality_class,
                    "weight": cluster.importance_weight,
                    "importance_basis": cluster.importance_basis,
                    "categories": cluster.categories,
                    "passage_scope": cluster.passage_scope,
                    "consumed_original_prompt_1_5": bool(
                        set(cluster.synthesis_ids).intersection(original_consumed)
                    ),
                    "consumed_remediation_prompt_1_6": bool(
                        set(cluster.synthesis_ids).intersection(remediation_consumed)
                    ),
                    "concept_signature": cluster.concept_signature,
                    "facts": facts,
                    "central_parent_ratio": _central_parent_ratio(cluster, evidence, passage_text),
                    "should_contribute_to_reader_facing_coverage": relevant,
                    "determination_reason": reason,
                }
            )
        chapters.append(
            {
                "reference": reference,
                "book": book,
                "chapter": chapter,
                "evidence_hash": prepared.bundle.evidence_hash,
                "synthesis_hash": prepared.synthesis.synthesis_hash,
                "current_cluster_audit_version": "commentary-richness-clusters-v1",
                "current_core_classifier_version": CORE_CLASSIFIER_V2,
                "current_richness_policy_version": "commentary-richness-policy-v2-proposed",
                "current_gate_version": "commentary-richness-gate-v2.1",
                "current_meaningful_cluster_count": len(cluster_rows),
                "reader_relevant_judgment_count": sum(
                    row["should_contribute_to_reader_facing_coverage"] for row in cluster_rows
                ),
                "importance_basis_breakdown": _basis_breakdown(cluster_rows),
                "clusters": cluster_rows,
            }
        )
    result = {
        "artifact_version": DENOMINATOR_AUDIT_VERSION,
        "namespace_version": ARTIFACT_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "remediation_id": REMEDIATION_ID,
        "scoring_behavior_changed": False,
        "note": "This is the required pre-policy denominator audit. Reader-relevance judgments are diagnostic and do not alter historical scores.",
        "chapters": chapters,
    }
    _write_json_immutable(output_root / "audit/denominator-audit-v3.json", result)
    return result


def _verify_freeze(output_root: Path) -> dict[str, Any]:
    frozen = _read(output_root / "freeze/historical-results.json")
    if frozen.get("qualification_id") != QUALIFICATION_ID:
        raise ScoringRemediationError("frozen qualification identity mismatch")
    if frozen.get("remediation_id") != REMEDIATION_ID:
        raise ScoringRemediationError("frozen remediation identity mismatch")
    for row in frozen.get("files", []):
        path = ROOT / row["path"]
        current = _hashed_file(path)
        if current != row:
            raise ScoringRemediationError(f"frozen historical artifact changed: {path}")
    return frozen


def _codes(errors: Iterable[str]) -> list[str]:
    result = []
    for error in errors:
        code = str(error).split(":", 1)[0].strip()
        if code.isupper() and " " not in code:
            result.append(code)
    return sorted(set(result))


def _rejected_result(reference: str, codes: list[str]) -> dict[str, Any]:
    return {
        "reference": reference,
        "structural_result": "REJECTED",
        "rejection_codes": codes,
        "meaningful_cluster_count": None,
        "eligible_weighted_denominator": None,
        "weighted_coverage": None,
        "core_coverage": None,
        "category_coverage": None,
        "raw_synthesis_utilization": None,
        "synthesis_utilization": None,
        "dump_severity": None,
        "gate_v2_1": None,
    }


def _evaluate_raw_response(
    *,
    manifest_row: dict[str, Any],
    raw: bytes,
    prompt_version: str,
    renderer_label: str,
) -> dict[str, Any]:
    reference = manifest_row["reference"]
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _rejected_result(reference, ["MALFORMED_RESPONSE_JSON"])
    if not isinstance(payload, dict):
        return _rejected_result(reference, ["MALFORMED_RESPONSE_JSON"])
    prepared = prepare_chapter(manifest_row["book"], int(manifest_row["chapter"]))
    expected_packet_id = manifest_row.get("source_packet_id") or manifest_row.get("packet_id")
    prepared_packet_id = prepared.row.get("input_identity", {}).get("packet_id")
    if expected_packet_id and prepared_packet_id and expected_packet_id != prepared_packet_id:
        raise ScoringRemediationError(f"packet identity changed for {reference}")
    if manifest_row.get("evidence_hash") and prepared.bundle.evidence_hash != manifest_row.get("evidence_hash"):
        raise ScoringRemediationError(f"evidence identity changed for {reference}")
    if manifest_row.get("synthesis_hash") and prepared.synthesis.synthesis_hash != manifest_row.get("synthesis_hash"):
        raise ScoringRemediationError(f"synthesis identity changed for {reference}")
    payload = dict(payload)
    payload["generated_metadata"] = GeneratedMetadata(
        evidence_hash=prepared.bundle.evidence_hash,
        evidence_bundle_version=prepared.bundle.version,
        commentary_schema_version=COMMENTARY_SCHEMA_VERSION,
        commentary_prompt_version=prompt_version,
        model="counterfactual_existing_response",
        generated_timestamp=None,
        synthesis_hash=prepared.synthesis.synthesis_hash,
        synthesis_schema_version=prepared.synthesis.synthesis_schema_version,
        synthesis_compiler_version=prepared.synthesis.synthesis_compiler_version,
        renderer_label=renderer_label,
    ).to_dict()
    payload["evidence_availability"] = prepared.synthesis.evidence_availability
    payload["status"] = "pending"
    validation = validate_chapter_commentary(
        payload,
        prepared.bundle,
        expected_evidence_hash=prepared.bundle.evidence_hash,
        expected_prompt_version=prompt_version,
        expected_reference=reference,
        expected_book=manifest_row["book"],
        expected_chapter=int(manifest_row["chapter"]),
        synthesis=prepared.synthesis,
        expected_synthesis_hash=prepared.synthesis.synthesis_hash,
    )
    if not validation.valid or validation.commentary is None:
        return _rejected_result(
            reference, _codes(validation.errors) or ["VALIDATION_FAILED"]
        )
    blocks = [
        block
        for section in validation.commentary.sections
        for block in section.blocks
    ]
    audit = audit_chapter(
        manifest_row["book"],
        int(manifest_row["chapter"]),
        validation.commentary,
        prepared.bundle,
    )
    passage_text = bible.passage_text(
        bible.resolve_chapter(
            manifest_row["book"], int(manifest_row["chapter"])
        ).get("verses", [])
    )
    score = score_synthesis_richness(
        prepared.synthesis.synthesis_units,
        evidence_items=prepared.bundle.evidence_items,
        consumed_synthesis_ids=[
            synthesis_id
            for block in blocks
            for synthesis_id in block.synthesis_ids
        ],
        blocks=blocks,
        passage_ref=reference,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=passage_text,
    )
    safety = {
        name: True
        for name in (
            "validation_clean",
            "provenance_complete",
            "hashes_valid",
            "chapter_boundaries_valid",
            "confidence_valid",
            "dispute_state_preserved",
            "unsupported_significance_absent",
        )
    }
    baseline = (
        "SYNTHESIS_GAP"
        if prepared.synthesis.evidence_availability == "AVAILABLE"
        else "EVIDENCE_GAP"
    )
    gate = assess_gate_v2(
        score=score,
        evidence_availability=prepared.synthesis.evidence_availability,
        baseline_richness=baseline,
        after_richness=audit["richness_status"],
        safety_checks=safety,
        evidence_use_delta=audit["unique_evidence_ids_consumed"],
        section_delta=audit["section_count"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )
    return {
        "reference": reference,
        "structural_result": "ACCEPTED",
        "rejection_codes": [],
        "evidence_availability": prepared.synthesis.evidence_availability,
        "meaningful_cluster_count": score.meaningful_cluster_count,
        "eligible_weighted_denominator": score.eligible_weighted_denominator,
        "consumed_eligible_weight": score.consumed_eligible_weight,
        "weighted_coverage": score.weighted_idea_coverage,
        "core_coverage": score.core_cluster_coverage,
        "category_coverage": score.category_coverage,
        "raw_synthesis_utilization": score.raw_synthesis_coverage,
        # Qualification utilization is versioned to reader-level eligible idea
        # clusters. Counting raw units here would reintroduce duplicate and
        # contextually optional inventory through a second denominator.
        "synthesis_utilization": score.idea_cluster_coverage,
        "eligible_unit_utilization": score.eligible_synthesis_coverage,
        "eligible_synthesis_count": score.eligible_synthesis_count,
        "consumed_eligible_synthesis_count": score.consumed_eligible_synthesis_count,
        "dump_severity": score.dump_diagnostics.severity,
        "word_count": audit["commentary_prose_word_count"],
        "block_count": audit["commentary_block_count"],
        "gate_v2_1": gate.to_dict(),
        "score": score.to_dict(),
        "audit": audit,
    }


def _old_metrics(row: dict[str, Any]) -> dict[str, Any]:
    score = row.get("score") or {}
    clusters = score.get("clusters") or []
    weighted_denominator = sum(
        float(cluster["importance_weight"])
        for cluster in clusters
        if cluster.get("quality_class") != QualityClass.OPTIONAL.value
    )
    return {
        "structural_result": row["structural_result"],
        "rejection_codes": row["rejection_codes"],
        "meaningful_cluster_count": score.get("meaningful_cluster_count"),
        "eligible_weighted_denominator": (
            round(weighted_denominator, 4) if clusters else None
        ),
        "weighted_coverage": row.get("weighted_coverage"),
        "core_coverage": row.get("core_coverage"),
        "category_coverage": row.get("category_coverage"),
        "synthesis_utilization": row.get("synthesis_utilization"),
        "dump_severity": row.get("dump_severity"),
        "gate_result": (row.get("gate_v2_1") or {}).get("outcome"),
    }


def _new_metrics(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "structural_result": row["structural_result"],
        "rejection_codes": row["rejection_codes"],
        "meaningful_cluster_count": row.get("meaningful_cluster_count"),
        "eligible_weighted_denominator": row.get("eligible_weighted_denominator"),
        "weighted_coverage": row.get("weighted_coverage"),
        "core_coverage": row.get("core_coverage"),
        "category_coverage": row.get("category_coverage"),
        "synthesis_utilization": row.get("synthesis_utilization"),
        "raw_synthesis_utilization": row.get("raw_synthesis_utilization"),
        "eligible_unit_utilization": row.get("eligible_unit_utilization"),
        "dump_severity": row.get("dump_severity"),
        "gate_result": (row.get("gate_v2_1") or {}).get("outcome"),
    }


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    return round(sum(values) / len(values), 4) if values else None


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["structural_result"] == "ACCEPTED"]
    evidence_bearing = [
        row for row in valid if row.get("evidence_availability") == "AVAILABLE"
    ]
    return {
        "renderer_chapters": len(rows),
        "structurally_valid": len(valid),
        "structural_rejections": len(rows) - len(valid),
        "structural_rejection_codes": dict(
            Counter(code for row in rows for code in row["rejection_codes"])
        ),
        "quality_fail": sum(
            (row.get("gate_v2_1") or {}).get("outcome") == "QUALITY_FAIL"
            for row in valid
        ),
        "high_dump": sum(row.get("dump_severity") == "HIGH" for row in valid),
        "evidence_bearing_valid_chapters": len(evidence_bearing),
        "weighted_coverage": _mean(evidence_bearing, "weighted_coverage"),
        "core_coverage": _mean(evidence_bearing, "core_coverage"),
        "synthesis_utilization": _mean(evidence_bearing, "synthesis_utilization"),
        "raw_synthesis_utilization": _mean(
            evidence_bearing, "raw_synthesis_utilization"
        ),
        "category_coverage": _mean(evidence_bearing, "category_coverage"),
        "gate_distribution": dict(
            Counter(
                (row.get("gate_v2_1") or {}).get("outcome") for row in valid
            )
        ),
        "dump_distribution": dict(
            Counter(row["dump_severity"] for row in valid)
        ),
    }


def _rescore_set(
    *,
    manifest: dict[str, Any],
    historical_evaluation: dict[str, Any],
    response_root: Path,
    prompt_version: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    old_by_reference = {
        row["reference"]: row for row in historical_evaluation["chapters"]
    }
    rows = []
    comparisons = []
    for manifest_row in manifest["chapters"]:
        raw_path = response_root / manifest_row["response_filename"]
        raw = raw_path.read_bytes()
        result = _evaluate_raw_response(
            manifest_row=manifest_row,
            raw=raw,
            prompt_version=prompt_version,
            renderer_label="gpt-5.6-sol",
        )
        result["raw_sha256"] = sha256_bytes(raw)
        rows.append(result)
        comparisons.append(
            {
                "reference": manifest_row["reference"],
                "old": _old_metrics(old_by_reference[manifest_row["reference"]]),
                "new": _new_metrics(result),
            }
        )
    return rows, comparisons


def counterfactual_rescore(*, output_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Re-score both immutable response sets without any model generation."""

    _verify_freeze(output_root)
    q_manifest, q_evaluation, r_manifest, r_evaluation = _historical_inputs()
    qualification_rows, qualification_comparison = _rescore_set(
        manifest=q_manifest,
        historical_evaluation=q_evaluation,
        response_root=QUALIFICATION_ROOT / "responses/raw",
        prompt_version="1.5",
    )
    remediation_rows, remediation_comparison = _rescore_set(
        manifest=r_manifest,
        historical_evaluation=r_evaluation,
        response_root=REMEDIATION_ROOT / "responses/raw",
        prompt_version="1.6",
    )
    original_aggregate = q_evaluation["comparison"]["gpt_5_6_sol"]
    new_aggregate = _aggregate(qualification_rows)
    transitions = Counter(
        f"{row['old']['gate_result'] or row['old']['structural_result']}->{row['new']['gate_result'] or row['new']['structural_result']}"
        for row in qualification_comparison
    )
    thresholds = q_evaluation["thresholds"]
    hard_codes = {
        "UNKNOWN_EVIDENCE_ID",
        "SYNTHESIS_ANCESTRY_MISMATCH",
        "CONFIDENCE_EXCEEDS_EVIDENCE",
    }
    rejection_counts = Counter(
        code for row in qualification_rows for code in row["rejection_codes"]
    )
    qualification_pass = (
        not any(rejection_counts[code] for code in hard_codes)
        and new_aggregate["structural_rejections"] == 0
        and new_aggregate["core_coverage"] is not None
        and new_aggregate["core_coverage"] >= thresholds["core_coverage_min"]
        and new_aggregate["weighted_coverage"] is not None
        and new_aggregate["weighted_coverage"] >= thresholds["weighted_coverage_min"]
        and new_aggregate["synthesis_utilization"] is not None
        and new_aggregate["synthesis_utilization"]
        >= thresholds["synthesis_utilization_min"]
        and new_aggregate["high_dump"] <= thresholds["high_dump_max"]
        and new_aggregate["quality_fail"] <= thresholds["quality_fail_max"]
        and not any(count > 1 for count in rejection_counts.values())
    )
    result = {
        "artifact_version": COUNTERFACTUAL_EVALUATION_VERSION,
        "namespace_version": ARTIFACT_VERSION,
        "qualification_id": QUALIFICATION_ID,
        "remediation_id": REMEDIATION_ID,
        "model_generation_performed": False,
        "contracts": {
            "old_cluster_audit_version": "commentary-richness-clusters-v1",
            "new_cluster_audit_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
            "old_core_classifier_version": CORE_CLASSIFIER_V2,
            "new_core_classifier_version": CORE_CLASSIFIER_V2,
            "old_richness_policy_version": RICHNESS_POLICY_VERSION,
            "new_richness_policy_version": RICHNESS_POLICY_VERSION_V3,
            "coverage_eligibility_classifier_version": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
            "gate_version": RICHNESS_GATE_V2_VERSION,
            "gate_behavior_changed": False,
        },
        "thresholds_unchanged": thresholds,
        "five_chapter_remediation": {
            "old_summary": r_evaluation["summary"],
            "new_summary": _aggregate(remediation_rows),
            "comparison": remediation_comparison,
            "chapters": remediation_rows,
        },
        "original_21_chapter_qualification": {
            "old_aggregate": original_aggregate,
            "new_aggregate": new_aggregate,
            "outcome_transitions": dict(sorted(transitions.items())),
            "counterfactual_qualification_result": (
                "QUALIFIED" if qualification_pass else "NOT_QUALIFIED"
            ),
            "comparison": qualification_comparison,
            "chapters": qualification_rows,
        },
    }
    _write_json_immutable(
        output_root / "evaluation/counterfactual-rescore-v3.json", result
    )
    return result


def _gate_for_control(
    *,
    score: Any,
    baseline_richness: str,
    audit: dict[str, Any],
) -> Any:
    safety = {
        name: True
        for name in (
            "validation_clean",
            "provenance_complete",
            "hashes_valid",
            "chapter_boundaries_valid",
            "confidence_valid",
            "dispute_state_preserved",
            "unsupported_significance_absent",
        )
    }
    return assess_gate_v2(
        score=score,
        evidence_availability=audit["evidence_availability"],
        baseline_richness=baseline_richness,
        after_richness=audit["richness_status"],
        safety_checks=safety,
        boilerplate_detected=audit["boilerplate_detected"],
        evidence_use_delta=audit["unique_evidence_ids_consumed"],
        section_delta=audit["section_count"],
        boundary_repetition_ratio=audit["opening_closing_lexical_overlap"],
        commentary_word_count=audit["commentary_prose_word_count"],
        unique_evidence_ids_consumed=audit["unique_evidence_ids_consumed"],
    )


def _score_control(
    *,
    accepted_path: Path,
    synthesis_root: Path,
    baseline_richness: str,
    control_source: str,
) -> dict[str, Any]:
    payload = _read(accepted_path)
    book = str(payload["book"])
    chapter = int(payload["chapter"])
    reference = str(payload["reference"])
    commentary = load_commentary(accepted_path.parent, book, chapter)
    synthesis = load_synthesis(synthesis_root, book, chapter)
    bundle = get_chapter_evidence_bundle(
        book,
        chapter,
        evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION,
    )
    if commentary is None or synthesis is None or bundle is None:
        raise ScoringRemediationError(f"incomplete historical control: {reference}")
    if synthesis.evidence_hash != bundle.evidence_hash:
        raise ScoringRemediationError(f"control evidence/synthesis hash mismatch: {reference}")
    blocks = [block for section in commentary.sections for block in section.blocks]
    consumed = [sid for block in blocks for sid in block.synthesis_ids]
    passage_text = bible.passage_text(
        bible.resolve_chapter(book, chapter).get("verses", [])
    )
    old_score = score_synthesis_richness(
        synthesis.synthesis_units,
        evidence_items=bundle.evidence_items,
        consumed_synthesis_ids=consumed,
        blocks=blocks,
        passage_ref=reference,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION,
    )
    new_score = score_synthesis_richness(
        synthesis.synthesis_units,
        evidence_items=bundle.evidence_items,
        consumed_synthesis_ids=consumed,
        blocks=blocks,
        passage_ref=reference,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=passage_text,
    )
    audit = audit_chapter(book, chapter, commentary, bundle)
    old_gate = _gate_for_control(
        score=old_score, baseline_richness=baseline_richness, audit=audit
    )
    new_gate = _gate_for_control(
        score=new_score, baseline_richness=baseline_richness, audit=audit
    )
    return {
        "reference": reference,
        "source": control_source,
        "baseline_richness": baseline_richness,
        "evidence_availability": audit["evidence_availability"],
        "after_richness": audit["richness_status"],
        "old": {
            "meaningful_clusters": old_score.meaningful_cluster_count,
            "weighted_coverage": old_score.weighted_idea_coverage,
            "core_coverage": old_score.core_cluster_coverage,
            "category_coverage": old_score.category_coverage,
            "synthesis_utilization": old_score.raw_synthesis_coverage,
            "dump_severity": old_score.dump_diagnostics.severity,
            "gate_outcome": old_gate.outcome,
        },
        "new": {
            "meaningful_clusters": new_score.meaningful_cluster_count,
            "eligible_weighted_denominator": new_score.eligible_weighted_denominator,
            "weighted_coverage": new_score.weighted_idea_coverage,
            "core_coverage": new_score.core_cluster_coverage,
            "category_coverage": new_score.category_coverage,
            "synthesis_utilization": new_score.idea_cluster_coverage,
            "raw_synthesis_utilization": new_score.raw_synthesis_coverage,
            "dump_severity": new_score.dump_diagnostics.severity,
            "gate_outcome": new_gate.outcome,
            "eligibility_distribution": new_score.eligibility_distribution,
        },
    }


def calibrate_controls(*, output_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Check v3 against canary and Commentary 1.5 historical controls."""

    _verify_freeze(output_root)
    controls = []
    canary_root = (
        ROOT
        / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary"
    )
    baseline_audit = _read(
        ROOT
        / ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/audit/commentary-richness-audit.json"
    )
    baseline_by_reference = {
        row["reference"]: row for row in baseline_audit["chapters"]
    }
    for accepted_path in sorted((canary_root / "responses/accepted").glob("*.json")):
        payload = _read(accepted_path)
        reference = payload["reference"]
        controls.append(
            _score_control(
                accepted_path=accepted_path,
                synthesis_root=canary_root / "synthesis",
                baseline_richness=baseline_by_reference[reference]["richness_status"],
                control_source="commentary-v1.2-canary-control",
            )
        )

    batch_root = (
        ROOT
        / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-batch-3"
    )
    batch_report = _read(
        batch_root / "evaluation/batch-3-and-30-chapter-report.json"
    )
    report_rows = {
        row["reference"]: row for row in batch_report["batch3"]["chapters"]
    }
    baseline_for_gate = {
        "ENRICHMENT_TARGET": "SYNTHESIS_GAP",
        "RICH_CONTROL": "RICH_ENOUGH",
        "EVIDENCE_LIMITED_CONTROL": "EVIDENCE_GAP",
        "DATA_GAP_CONTROL": "EVIDENCE_GAP",
    }
    for accepted_path in sorted(
        (batch_root / "canary/responses/accepted").glob("*.json")
    ):
        payload = _read(accepted_path)
        historical = report_rows[payload["reference"]]
        gate_class = historical["gate_v2_1"]["gate_class"]
        row = _score_control(
            accepted_path=accepted_path,
            synthesis_root=batch_root / "canary/synthesis",
            baseline_richness=baseline_for_gate[gate_class],
            control_source="commentary-v1.5-batch-3",
        )
        for key, historical_key in (
            ("weighted_coverage", "weighted_coverage"),
            ("core_coverage", "core_coverage"),
            ("category_coverage", "category_coverage"),
            ("dump_severity", "dump_severity"),
        ):
            if row["old"][key] != historical[historical_key]:
                raise ScoringRemediationError(
                    f"historical control score changed for {payload['reference']}: {key}"
                )
        controls.append(row)

    transitions = Counter(
        f"{row['old']['gate_outcome']}->{row['new']['gate_outcome']}"
        for row in controls
    )
    by_baseline = defaultdict(list)
    for row in controls:
        by_baseline[row["baseline_richness"]].append(row)
    result = {
        "artifact_version": CALIBRATION_VERSION,
        "namespace_version": ARTIFACT_VERSION,
        "contracts": {
            "old_richness_policy_version": RICHNESS_POLICY_VERSION,
            "new_richness_policy_version": RICHNESS_POLICY_VERSION_V3,
            "core_classifier_version": CORE_CLASSIFIER_V2,
            "coverage_eligibility_classifier_version": COVERAGE_ELIGIBILITY_CLASSIFIER_V1,
            "gate_version": RICHNESS_GATE_V2_VERSION,
            "gate_behavior_changed": False,
        },
        "control_count": len(controls),
        "sources": dict(Counter(row["source"] for row in controls)),
        "baseline_distribution": dict(
            Counter(row["baseline_richness"] for row in controls)
        ),
        "evidence_availability_distribution": dict(
            Counter(row["evidence_availability"] for row in controls)
        ),
        "outcome_transitions": dict(sorted(transitions.items())),
        "core_coverage_regressions": sum(
            row["new"]["core_coverage"] < row["old"]["core_coverage"]
            for row in controls
        ),
        "dump_severity_changes": sum(
            row["new"]["dump_severity"] != row["old"]["dump_severity"]
            for row in controls
        ),
        "rich_control_regressions": [
            row["reference"]
            for row in controls
            if row["baseline_richness"] == "RICH_ENOUGH"
            and row["new"]["gate_outcome"] not in {"PASS", "PASS_WITH_WARNING"}
        ],
        "data_gap_regressions": [
            row["reference"]
            for row in controls
            if row["evidence_availability"] == "DATA_GAP"
            and row["new"]["gate_outcome"] != "PASS"
        ],
        "high_dump_controls": [
            {
                "reference": row["reference"],
                "old_gate": row["old"]["gate_outcome"],
                "new_gate": row["new"]["gate_outcome"],
            }
            for row in controls
            if row["old"]["dump_severity"] == "HIGH"
            or row["new"]["dump_severity"] == "HIGH"
        ],
        "controls": controls,
    }
    _write_json_immutable(output_root / "calibration/controls-v1.json", result)
    return result


def overlap_audit(*, output_root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    """Audit Revelation 21 overlap without changing duplicate clustering."""

    prepared = prepare_chapter("Revelation", 21)
    units = {unit.id: unit for unit in prepared.synthesis.synthesis_units}
    evidence = {item.id: item for item in prepared.bundle.evidence_items}
    clusters = cluster_synthesis_units(
        units.values(),
        evidence,
        core_classifier=CORE_CLASSIFIER_V2,
        coverage_policy=RICHNESS_POLICY_VERSION_V3,
        passage_text=bible.passage_text(
            bible.resolve_chapter("Revelation", 21).get("verses", [])
        ),
    )
    stop = {
        "what", "is", "the", "significance", "of", "theme", "doctrine",
        "framework", "symbol", "prophecy", "storyline", "and", "a",
    }

    def concept(value: str) -> str:
        words = [word for word in _WORD_RE.findall(value.casefold()) if word not in stop]
        return "-".join(words)

    rows = []
    for cluster in clusters:
        parents = sorted(
            {
                str((evidence[eid].relevance_metadata or {}).get("parent_object_id") or "")
                for eid in cluster.evidence_ids
                if eid in evidence
            }
        )
        rows.append(
            {
                "cluster_id": cluster.id,
                "quality_class": cluster.quality_class,
                "coverage_eligibility": cluster.coverage_eligibility,
                "duplicate_reason": cluster.duplicate_reason,
                "unit_kinds": cluster.unit_kinds,
                "synthesis_ids": cluster.synthesis_ids,
                "evidence_ids": cluster.evidence_ids,
                "parent_families": sorted({concept(parent) for parent in parents if parent}),
                "parent_ids": parents,
                "related_unit_ids": sorted(
                    {
                        related
                        for synthesis_id in cluster.synthesis_ids
                        for related in units[synthesis_id].related_unit_ids
                    }
                ),
                "facts": [
                    fact
                    for synthesis_id in cluster.synthesis_ids
                    for fact in units[synthesis_id].facts
                ],
            }
        )

    def fact_words(row: dict[str, Any]) -> set[str]:
        return set(
            word
            for fact in row["facts"]
            for word in _WORD_RE.findall(str(fact).casefold())
            if word not in {"the", "a", "an", "and", "of", "to", "in", "is"}
        )

    candidates = []
    for left, right in combinations(rows, 2):
        shared = sorted(set(left["parent_families"]).intersection(right["parent_families"]))
        if not shared:
            continue
        left_words, right_words = fact_words(left), fact_words(right)
        overlap = len(left_words.intersection(right_words)) / max(
            1, min(len(left_words), len(right_words))
        )
        same_kind = bool(set(left["unit_kinds"]).intersection(right["unit_kinds"]))
        candidates.append(
            {
                "left_cluster_id": left["cluster_id"],
                "right_cluster_id": right["cluster_id"],
                "shared_parent_families": shared,
                "same_unit_kind": same_kind,
                "fact_containment_overlap": round(overlap, 4),
                "current_duplicate_reasons": [
                    left["duplicate_reason"], right["duplicate_reason"]
                ],
                "deterministic_reading": (
                    "already_consolidated_inside_existing_clusters"
                    if overlap >= 0.70
                    else "distinct_or_insufficiently_equivalent_reader_dimensions"
                ),
            }
        )
    exact_candidate_count = sum(
        row["same_unit_kind"]
        and row["fact_containment_overlap"] >= 0.70
        for row in candidates
    )
    result = {
        "artifact_version": OVERLAP_AUDIT_VERSION,
        "namespace_version": ARTIFACT_VERSION,
        "reference": "Revelation 21",
        "cluster_audit_version": RICHNESS_CLUSTER_AUDIT_VERSION_V2,
        "duplicate_rule_version": "commentary-richness-duplicate-rules-v1",
        "cluster_count": len(clusters),
        "duplicate_reason_distribution": dict(
            Counter(cluster.duplicate_reason for cluster in clusters)
        ),
        "thematic_parent_family_groups": dict(
            sorted(
                (
                    family,
                    sum(family in row["parent_families"] for row in rows),
                )
                for family in sorted(
                    {
                        family
                        for row in rows
                        for family in row["parent_families"]
                    }
                )
            )
        ),
        "same_family_pairs": candidates,
        "safe_new_merge_candidate_count": exact_candidate_count,
        "conclusion": (
            "NO_SAFE_NEW_MERGE_RULE"
            if exact_candidate_count == 0
            else "REVIEW_REQUIRED"
        ),
        "conclusion_reason": (
            "Creation, resurrection, exile, Jerusalem, temple, and theme records span different unit kinds, evidence ancestries, and non-equivalent facts. Existing exact/ancestry/parent-parallel/high-fact-overlap rules already consolidate redundant representations; eligibility removes generic inventory from coverage without transitive semantic merging."
        ),
        "clusters": rows,
    }
    _write_json_immutable(output_root / "audit/revelation-21-overlap-v1.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze", help="freeze identities for historical results and raw responses")
    sub.add_parser("audit-denominator", help="write the pre-change four-chapter denominator audit")
    sub.add_parser("rescore", help="counterfactually re-score both immutable response sets")
    sub.add_parser("calibrate", help="run historical controls without generation")
    sub.add_parser("overlap-audit", help="audit deterministic Revelation 21 overlap")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            result = freeze(output_root=args.output_root)
        elif args.command == "audit-denominator":
            result = denominator_audit(output_root=args.output_root)
        elif args.command == "rescore":
            result = counterfactual_rescore(output_root=args.output_root)
        elif args.command == "calibrate":
            result = calibrate_controls(output_root=args.output_root)
        else:
            result = overlap_audit(output_root=args.output_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ScoringRemediationError, ArtifactCollisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
