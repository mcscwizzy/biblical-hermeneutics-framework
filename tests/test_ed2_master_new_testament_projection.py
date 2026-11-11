from tests.test_narrative_explorer_projection import _item, _lookup, _load_ckl, _project


EXPECTED = {
    "luke-5-30-grumbling-and-wilderness-language": (
        "Luke 5",
        "books/luke.json",
        "Luke 5:30",
        "tuohy-luke5-meal-scene-2012",
    ),
    "acts-15-29-eu-prassete-range": (
        "Acts 15",
        "books/acts.json",
        "Acts 15:29",
        "moxon-acts15-eu-prassete-2024",
    ),
    "revelation-13-land-beast-as-asian-elite-network": (
        "Revelation 13",
        "books/revelation.json",
        "Revelation 13:11-18",
        "friesen-beast-land-2003",
    ),
}


def test_ed2_master_new_testament_e1_projects_exact_passages_and_discloses_sources():
    records = {path: _load_ckl(path) for path in {value[1] for value in EXPECTED.values()}}
    for local_id, (passage, path, anchor, scholarly_source) in EXPECTED.items():
        canonical = _lookup("ckl", records=records[path])
        result = _project(passage, canonical=canonical)
        projected_id = f"ckl:{records[path][0]['id']}#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)
        assert anchor in [x["reference"] for x in projected["applicable_passage_anchors"]]
        assert scholarly_source in projected["source_ids"]
        assert any(
            source["bibliographic_details"].get("locator")
            for source in projected["sources"]
            if source["id"] == scholarly_source
        )
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        edges = [entry for entry in result["connections"] if entry.get("source_id") == projected_id]
        expected_targets = {f"passage:{item['reference']}" for item in projected["passage_anchors"]}
        assert {edge["target_id"] for edge in edges} == expected_targets
        assert len(edges) == len(expected_targets)
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []
