from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from bhf_agent.presentation.narrative_explorer_passages import (
    build_related_passages,
    load_passage_bridges,
    validate_passage_bridge_registry,
)


def _claim_object() -> dict:
    return {
        "id": "john",
        "claims": [
            {
                "id": "john-logos",
                "claim": "John 1 depicts the Logos with God in the beginning and active in creation and life.",
                "scripture_references": ["John 1:1-18", "Genesis 1:1-5"],
                "source_ids": ["john-greek", "boyarin-logos"],
                "certainty": "textually_explicit",
                "dispute_status": "major_scholarly_disagreement",
                "claim_type": "literary",
            }
        ],
        "sources": [
            {"id": "john-greek", "title": "Greek New Testament", "source_type": "scripture"},
            {"id": "boyarin-logos", "title": "The Jewish Gospels", "author": "Daniel Boyarin", "year": 2012},
            {"id": "unrelated", "title": "Unrelated bibliography"},
        ],
    }


def _bridge() -> dict:
    return {
        "id": "genesis-1-john-1-logos",
        "passages": ["Genesis 1:1-5", "John 1:1-18"],
        "direction": "source_to_receiving_text",
        "relationship_category": "interpretive_association",
        "evidence_layer": "thematic_interpretation",
        "explanation": "John's prologue uses beginning, creation, and life language in a scriptural setting that includes Genesis 1.",
        "uncertainty": "The conceptual genealogy of the Logos remains debated; this does not establish direct borrowing.",
        "supporting_records": [
            {
                "object_id": "john",
                "record_kind": "claim",
                "record_id": "john-logos",
                "source_ids": ["john-greek", "boyarin-logos"],
            }
        ],
    }


def _resolver(*objects):
    by_id = {item["id"]: item for item in objects}
    return by_id.get


def test_explicit_ckl_claim_creates_a_separate_scoped_passage_bridge():
    object_record = _claim_object()
    result = build_related_passages(
        "Genesis 1",
        connections=[],
        bridge_records=[_bridge()],
        source_resolver=_resolver(object_record),
        query_status="complete",
    )

    assert result["state"] == "available"
    assert result["authored_relationships"] == []
    assert len(result["evidence_backed_bridges"]) == 1
    bridge = result["evidence_backed_bridges"][0]
    assert bridge["provenance"] == "ckl_documented_claim"
    assert bridge["source_passage"] == "Genesis 1:1-5"
    assert bridge["destination_passage"] == "John 1:1-18"
    assert bridge["relationship_category"] == "interpretive_association"
    assert bridge["uncertainty"] == _bridge()["uncertainty"]
    assert bridge["supporting_records"][0]["id"] == "ckl:john#claim:john-logos"
    assert [source["id"] for source in bridge["supporting_sources"]] == ["john-greek", "boyarin-logos"]
    assert all(source["id"] != "unrelated" for source in bridge["supporting_sources"])


def test_shared_parent_source_keyword_or_anchor_does_not_infer_a_bridge():
    source = _claim_object()
    unrelated = {
        "id": "genesis",
        "claims": [
            {
                "id": "creation-note",
                "claim": "Creation is a theme.",
                "scripture_references": ["Genesis 1:1-5"],
                "source_ids": ["john-greek"],
            }
        ],
        "sources": [{"id": "john-greek", "title": "Greek New Testament"}],
    }
    before = deepcopy((source, unrelated))
    result = build_related_passages(
        "Genesis 1",
        connections=[],
        bridge_records=[],
        source_resolver=_resolver(source, unrelated),
        query_status="complete",
    )

    assert result["state"] == "not_represented"
    assert result["evidence_backed_bridges"] == []
    assert result["authored_relationships"] == []
    assert (source, unrelated) == before


def test_two_passage_claims_in_one_ckl_parent_do_not_create_a_route_without_a_bridge_record():
    same_parent = {
        "id": "shared-topic",
        "claims": [
            {"id": "genesis-claim", "claim": "Creation and word language.", "scripture_references": ["Genesis 1:1-5"], "source_ids": ["shared-source"]},
            {"id": "john-claim", "claim": "Word and creation language.", "scripture_references": ["John 1:1-18"], "source_ids": ["shared-source"]},
        ],
        "sources": [{"id": "shared-source", "title": "Shared bibliography"}],
    }

    result = build_related_passages(
        "Genesis 1",
        connections=[],
        bridge_records=[],
        source_resolver=_resolver(same_parent),
        query_status="complete",
    )

    assert result["state"] == "not_represented"
    assert result["evidence_backed_bridges"] == []
    assert result["authored_relationships"] == []


def test_partial_overlap_with_a_passage_scope_does_not_verify_the_full_bridge_scope():
    object_record = _claim_object()
    object_record["claims"][0]["claim"] = "A note compares the creation account with John's opening."
    object_record["claims"][0]["scripture_references"] = ["Genesis 1:3-5", "John 1:1-18"]

    result = build_related_passages(
        "Genesis 1",
        connections=[],
        bridge_records=[_bridge()],
        source_resolver=_resolver(object_record),
        query_status="complete",
    )

    assert result["evidence_backed_bridges"] == []
    assert result["state"] == "unknown"


def test_missing_support_record_is_unknown_instead_of_a_confirmed_bridge():
    result = build_related_passages(
        "Genesis 1",
        connections=[],
        bridge_records=[_bridge()],
        source_resolver=_resolver(),
        query_status="complete",
    )

    assert result["state"] == "unknown"
    assert result["evidence_backed_bridges"] == []
    assert result["reason_code"] == "bridge_support_unavailable"


@pytest.mark.parametrize("query_status, expected", [("partial", "partial"), ("failed", "unknown")])
def test_incomplete_source_lookup_never_claims_no_passage_connections(query_status, expected):
    result = build_related_passages(
        "Genesis 1",
        connections=[],
        bridge_records=[],
        source_resolver=_resolver(),
        query_status=query_status,
    )

    assert result["state"] == expected
    assert result["evidence_backed_bridges"] == []
    assert result["description"] != "No biblical passage connection exists."


def test_authored_curated_pathway_preserves_original_ckl_identity_and_direction():
    connection = {
        "id": "ckl:creation#evidence:new-creation→ckl:new-creation-theme",
        "source_id": "ckl:creation#evidence:new-creation",
        "target_id": "ckl:new-creation-theme",
        "connection_type": "thematic_relationship",
        "original_relationship_type": "canonical-fulfillment",
        "relationship_mode": "inferred",
        "temporal_layer": "later_reception",
        "direction": "one_way",
        "basis": {"kind": "ckl_related_object", "notes": "source edge rationale", "weight": 9},
        "curation": {
            "classification": "thematic_relationship",
            "applicable_passages": ["Genesis 1:1-31"],
            "supporting_passages": ["Genesis 1:1-31", "Revelation 21:1-5"],
            "supporting_records": ["ckl:creation#evidence:new-creation"],
            "supporting_ckl_sources": [{"object_id": "creation", "source_id": "genesis-1-2"}],
            "why": "This is a reader-facing thematic comparison.",
            "uncertainty": "This does not assert direct quotation.",
            "human_scholarly_approval": "not_recorded",
            "curation_confidence": "moderate",
        },
    }

    result = build_related_passages(
        "Genesis 1",
        connections=[connection],
        bridge_records=[],
        source_resolver=_resolver(),
        query_status="complete",
    )

    assert result["state"] == "available"
    assert len(result["authored_relationships"]) == 1
    pathway = result["authored_relationships"][0]
    assert pathway["provenance"] == "authored_ckl_relationship"
    assert pathway["destination_passage"] == "Revelation 21:1-5"
    assert pathway["original_relationship_type"] == "canonical-fulfillment"
    assert pathway["source_id"] == connection["source_id"]
    assert pathway["target_id"] == connection["target_id"]
    assert pathway["direction"] == "one_way"
    assert pathway["curation"]["human_scholarly_approval"] == "not_recorded"


def test_projection_exposes_verified_bridges_separately_from_ckl_edges():
    from bhf_agent.presentation.narrative_explorer import DomainLookup, project_narrative_explorer

    object_root = Path(__file__).resolve().parents[1] / "framework" / "canonical_library" / "objects" / "books"
    genesis = json.loads((object_root / "genesis.json").read_text(encoding="utf-8"))
    john = _claim_object()
    by_id = {"genesis": genesis, "john": john}
    projected = project_narrative_explorer(
        "Genesis 1",
        canonical_lookup=DomainLookup(domain="ckl", records=[genesis], query_status="complete"),
        source_resolver=by_id.get,
        passage_bridge_records=[_bridge()],
    ).to_dict()

    routes = projected["related_passages"]
    assert routes["state"] == "available"
    assert routes["authored_relationships"] == []
    assert routes["evidence_backed_bridges"][0]["provenance"] == "ckl_documented_claim"
    assert routes["evidence_backed_bridges"][0]["destination_passage"] == "John 1:1-18"


def test_projection_keeps_unknown_bridge_lookup_from_claiming_no_relationship():
    from bhf_agent.presentation.narrative_explorer import DomainLookup, project_narrative_explorer

    object_root = Path(__file__).resolve().parents[1] / "framework" / "canonical_library" / "objects" / "books"
    genesis = json.loads((object_root / "genesis.json").read_text(encoding="utf-8"))
    projected = project_narrative_explorer(
        "Genesis 1",
        canonical_lookup=DomainLookup(domain="ckl", records=[genesis], query_status="complete"),
        source_resolver=_resolver(),
        passage_bridge_records=[_bridge()],
    ).to_dict()

    routes = projected["related_passages"]
    assert routes["state"] == "unknown"
    assert routes["reason_code"] == "bridge_support_unavailable"
    assert "does not establish" not in routes["description"]


def test_checked_in_registry_keeps_only_current_exact_ckl_records_and_record_sources():
    object_root = Path(__file__).resolve().parents[1] / "framework" / "canonical_library" / "objects"
    records = {}
    for path in object_root.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            records[value["id"]] = value

    bridges = load_passage_bridges()
    assert bridges
    assert validate_passage_bridge_registry(bridges, records.get) == len(bridges)
