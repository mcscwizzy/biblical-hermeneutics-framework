from tests.test_narrative_explorer_projection import _item, _lookup, _load_ckl, _project


EXPECTED_B1 = {
    "proverbs-2-conditional-argument-structure": (
        "Proverbs 2",
        "books/proverbs.json",
        "Proverbs 2:1-22",
        "loader-proverbs2-syntactic-structure-2013",
    ),
    "proverbs-28-rulers-and-poor-structure": (
        "Proverbs 28",
        "books/proverbs.json",
        "Proverbs 28:1-28",
        "gilbert-proverbs28-29-ruling-class-2007",
    ),
    "ecclesiastes-10-1-flies-of-death-translation": (
        "Ecclesiastes 10",
        "books/ecclesiastes.json",
        "Ecclesiastes 10:1",
        "whybray-ecclesiastes10-1-lexical-1989",
    ),
}


def test_ed2_master_wisdom_b1_projects_exact_scopes_and_discloses_sources():
    records = {
        path: _load_ckl(path)
        for path in {value[1] for value in EXPECTED_B1.values()}
    }
    for local_id, (passage, path, anchor, scholarly_source) in EXPECTED_B1.items():
        result = _project(passage, canonical=_lookup("ckl", records=records[path]))
        projected_id = f"ckl:{records[path][0]['id']}#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)
        assert projected["record_kind"] == "evidence"
        assert projected["evidence_category"] == "literary-convention"
        assert [x["reference"] for x in projected["passage_anchors"]] == [anchor]
        assert [x["reference"] for x in projected["applicable_passage_anchors"]] == [anchor]
        assert {"biblical_narrative", "themes_biblical_connections"}.issubset(projected["section_ids"])
        assert {"proverbs-masoretic" if records[path][0]["id"] == "proverbs" else "ecclesiastes-masoretic", scholarly_source}.issubset(projected["source_ids"])
        assert len(projected["sources"]) >= 2
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["confidence"] in {"low", "medium"}
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        edges = [entry for entry in result["connections"] if entry.get("source_id") == projected_id]
        assert len(edges) == 1
        assert edges[0]["target_id"] == f"passage:{anchor}"
        assert edges[0]["basis"]["kind"] == "ckl_scripture_anchor"
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []
