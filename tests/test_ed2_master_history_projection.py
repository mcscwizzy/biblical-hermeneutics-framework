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
