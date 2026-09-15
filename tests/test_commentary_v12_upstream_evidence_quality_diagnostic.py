"""Focused deterministic tests for the v1.2 upstream quality diagnostic."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.commentary_v12_upstream_evidence_quality_diagnostic import (
    CASES,
    PRESENTATION_DIR,
    bundle_from_dict,
    compile_chapter_synthesis,
    current_ckl,
    classify,
    duplicate_groups,
    object_dict,
    read_json,
    retrieval_trace,
    selected_blocks,
    stable_json,
    verse_set,
)


def test_verse_interval_coverage_is_bounded_to_requested_chapter() -> None:
    assert verse_set("2 Kings 4:1-7", book="2 Kings", chapter=4) == set(range(1, 8))
    assert verse_set("Psalm 19:7-11", book="Psalms", chapter=19) == set(range(7, 12))
    assert verse_set("Psalm 20:1", book="Psalms", chapter=19) == set()


def test_duplicate_grouping_is_reproducible_and_explainable() -> None:
    rows = [
        {"evidence_item_id": "b", "claim": "Historically, grace is read across the canon.", "category": "history", "field": "historical_context", "ckl_title": "Grace"},
        {"evidence_item_id": "a", "claim": "Historically, mercy is read across the canon.", "category": "history", "field": "historical_context", "ckl_title": "Mercy"},
        {"evidence_item_id": "c", "claim": "A wholly different archaeological claim.", "category": "archaeology", "field": "", "ckl_title": "Artifact"},
    ]
    first = duplicate_groups(rows)
    assert first == duplicate_groups(list(reversed(rows)))
    assert first[0]["evidence_item_ids"] == ["a", "b"]


def test_inherited_source_items_remain_bundle_provenance_but_not_synthesis() -> None:
    raw = read_json(CASES["psalms_103"]["bundle"])
    bundle = bundle_from_dict(raw)
    synthesis = compile_chapter_synthesis(bundle, book="Psalms", chapter=103)
    evidence_ids = {item["id"] for item in raw["evidence_items"]}
    used_ids = {eid for unit in synthesis.synthesis_units for eid in unit.evidence_ids}
    assert used_ids == set()
    assert synthesis.coverage.unused_evidence_ids == sorted(evidence_ids)
    assert synthesis.evidence_hash == raw["evidence_hash"]


def test_serialization_and_renderer_selection_are_stable() -> None:
    parsed_path = next((PRESENTATION_DIR / "attempts").glob("*2_kings_004/attempt-001/parsed.json"))
    parsed = read_json(parsed_path)
    selected, blocks = selected_blocks(parsed)
    assert stable_json(selected) == stable_json(selected)
    assert len(selected) == 1
    assert blocks["block_1"]["final_block"]


def test_classification_serialization_preserves_explicit_label_and_reason() -> None:
    item = {"id": "what-does-torah-mean:historical_context:0", "related_entity_ids": ["what-does-torah-mean"], "relevance_metadata": {"parent_object_id": "what-does-torah-mean"}}
    label, reason = classify("psalms_019", item)
    encoded = json.dumps({"label": label, "reason": reason}, sort_keys=True)
    assert json.loads(encoded) == {"label": "DEFENSIBLE_CONTEXT", "reason": reason}


def test_diagnostic_reads_without_mutating_source_or_contract_inputs() -> None:
    paths = [
        CASES["2_kings_004"]["bundle"],
        PRESENTATION_DIR / "provenance-bindings-v2/2_kings_004.json",
        PRESENTATION_DIR / "renderer-reference-presentations/2_kings_004.json",
        next((PRESENTATION_DIR / "renderer-input").glob("*2_kings_004/user_prompt.txt")),
        PRESENTATION_DIR / "contract-identities.json",
        ROOT / "bhf_agent/data/asv_bible.json",
    ]
    before = {str(path): path.read_bytes() for path in paths}
    raw = read_json(CASES["2_kings_004"]["bundle"])
    original = copy.deepcopy(raw)
    _ = compile_chapter_synthesis(bundle_from_dict(raw), book="2 Kings", chapter=4)
    assert raw == original
    assert {str(path): path.read_bytes() for path in paths} == before


def test_current_ckl_object_is_not_mutated_by_retrieval_trace() -> None:
    library = current_ckl()
    result = library.retrieve_by_scripture_reference("2 Kings 4:1-44", limit=100, include_placeholders=False)[0]
    before = object_dict(result.object)
    _ = retrieval_trace(before, query="2 Kings 4:1-44", result=result, source_path=library.source_path_for(result.object.id))
    assert object_dict(result.object) == before


ROOT = Path(__file__).resolve().parents[1]
