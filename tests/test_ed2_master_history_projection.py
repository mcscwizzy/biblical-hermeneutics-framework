from tests.test_narrative_explorer_projection import _item, _lookup, _load_ckl, _project


EXPECTED = {
    "2chronicles-14-cushites-and-rhetorical-setting": (
        "2 Chronicles 14",
        "2 Chronicles 14:9-15",
        "historical-event",
        "jonker-cushites-chronicles-2023",
    ),
    "2chronicles-18-jehoshaphat-and-micaiah": (
        "2 Chronicles 18",
        "2 Chronicles 18:1-34",
        "literary-convention",
        "dillard-chronicles-jehoshaphat-1986",
    ),
    "2chronicles-25-amaziah-and-kings-parallel": (
        "2 Chronicles 25",
        "2 Chronicles 25:1-28",
        "literary-convention",
        "hwang-amaziah-kings-chronicles-2025",
    ),
}


def test_ed2_master_history_c1_projects_exact_passages_and_comparative_sources():
    records = _load_ckl("books/2-chronicles.json")
    canonical = _lookup("ckl", records=records)
    for local_id, (passage, direct_anchor, evidence_type, scholarly_source) in EXPECTED.items():
        result = _project(passage, canonical=canonical)
        projected_id = f"ckl:2-chronicles#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)
        assert projected["evidence_category"] == evidence_type
        assert direct_anchor in [x["reference"] for x in projected["applicable_passage_anchors"]]
        assert scholarly_source in projected["source_ids"]
        assert any(source["bibliographic_details"].get("locator") for source in projected["sources"] if source["id"] == scholarly_source)
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []


def test_ed2_master_history_c2_psalm_doxology_projects_with_disclosed_sources():
    records = _load_ckl("books/1-chronicles.json")
    result = _project("1 Chronicles 16", canonical=_lookup("ckl", records=records))
    projected_id = "ckl:1-chronicles#evidence:first-chronicles-16-36-five-book-psalter"
    assert len([entry for entry in result["items"] if entry["id"] == projected_id]) == 1
    projected = _item(result, projected_id)
    assert projected["evidence_category"] == "literary-convention"
    assert [x["reference"] for x in projected["applicable_passage_anchors"]] == ["1 Chronicles 16:36"]
    assert {"1-chronicles-1-29", "psalm106-masoretic", "longacre-psalter-compiled-2025"}.issubset(projected["source_ids"])
    assert all(source["details_available"] for source in projected["sources"])
    assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
    assert projected["rationale"]["primary_observation"]
    assert projected["rationale"]["scholarly_interpretation"]
    assert projected["certainty"] == "disputed"
    assert projected["dispute_status"] == "major_scholarly_disagreement"
    assert projected["content_status"] == "draft"
    assert projected["review_status"] == "in_review"
    assert projected["human_review_required"] is True
    edges = [entry for entry in result["connections"] if entry.get("source_id") == projected_id]
    assert len(edges) == 1
    assert edges[0]["target_id"] == "passage:1 Chronicles 16:36"
    assert result["related_passages"]["authored_relationships"] == []
    assert result["related_passages"]["evidence_backed_bridges"] == []
