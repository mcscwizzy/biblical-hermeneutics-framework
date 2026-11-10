from __future__ import annotations

from tests.test_narrative_explorer_projection import _item, _lookup, _load_ckl, _project


EVIDENCE_CONTEXTS = {
    "psalm-06-embodied-lament-language": (
        "Psalm 6",
        "Psalm 6:2-8",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "wessels-coetzee-psalms-body-2013"},
        "medium",
    ),
    "psalm-15-ethical-entrance-liturgy": (
        "Psalm 15",
        "Psalm 15:1-5",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "boloje-groenewald-psalm15-2016"},
        "medium",
    ),
    "psalm-30-superscription-and-reuse": (
        "Psalm 30",
        "Psalm 30:1-12",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "sommer-psalm30-2022"},
        "medium",
    ),
    "psalm-37-acrostic-gap-debate": (
        "Psalm 37",
        "Psalm 37:1-40",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "benun-acrostics-psalms-2006"},
        "medium",
    ),
    "psalm-44-communal-lament-and-book-context": (
        "Psalm 44",
        "Psalm 44:1-26",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "verde-psalms-trauma-2022"},
        "medium",
    ),
    "psalm-47-enthronement-hymn-setting-debate": (
        "Psalm 47",
        "Psalm 47:1-9",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "perdue-psalm47-1974"},
        "medium",
    ),
    "psalm-67-jussive-call-and-cultic-setting-debate": (
        "Psalm 67",
        "Psalm 67:1-7",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "botha-psalm67-2004"},
        "medium",
    ),
    "psalm-96-kingship-hymn-and-memory-proposal": (
        "Psalm 96",
        "Psalm 96:1-13",
        {"biblical_narrative", "themes_biblical_connections"},
        {"psalms-masoretic", "hays-psalm96-2023", "rahlfs-hanhart-septuaginta-2006"},
        "medium",
    ),
    "psalm-145-nun-verse-witness": (
        "Psalm 145:13",
        "Psalm 145:13",
        {"archaeology_ancient_history"},
        {
            "psalms-masoretic",
            "sanders-11qpsa-1965",
            "rahlfs-hanhart-septuaginta-2006",
            "gentry-textual-criticism-2020",
            "benun-acrostics-psalms-2006",
            "iaa-11q5-digital-library",
        },
        "high",
    ),
}


def test_ed2a_psalms_items_project_with_exact_scopes_sources_and_sections():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, expected_anchor, expected_sections, expected_sources, confidence) in EVIDENCE_CONTEXTS.items():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        projected_id = f"ckl:psalms#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)

        assert projected["record_kind"] == "evidence"
        assert projected["evidence_id"] == local_id
        assert projected["evidence_category"] == (
            "manuscript" if local_id == "psalm-145-nun-verse-witness" else "literary-convention"
        )
        assert [anchor["reference"] for anchor in projected["passage_anchors"]] == [expected_anchor]
        assert [anchor["reference"] for anchor in projected["applicable_passage_anchors"]] == [expected_anchor]
        assert set(projected["section_ids"]) == expected_sections
        assert set(projected["source_ids"]) == expected_sources
        assert projected["sources"]
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["certainty"]
        assert projected["dispute_status"]
        assert projected["confidence"] == confidence
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        anchor_edges = [
            edge for edge in result["connections"]
            if edge.get("source_id") == projected_id
        ]
        assert len(anchor_edges) == 1
        assert anchor_edges[0]["target_id"] == f"passage:{expected_anchor}"
        assert anchor_edges[0]["basis"]["kind"] == "ckl_scripture_anchor"
        assert anchor_edges[0]["basis"]["reference"] == expected_anchor


def test_psalm145_textual_witness_has_no_unreviewed_relationship_suggestion():
    psalms = _load_ckl("books/psalms.json")
    result = _project("Psalm 145:13", canonical=_lookup("ckl", records=psalms))
    projected_id = "ckl:psalms#evidence:psalm-145-nun-verse-witness"
    projected = _item(result, projected_id)
    assert projected["certainty"] == "textually_explicit"
    assert projected["dispute_status"] == "textual_variant"
    assert {source["id"] for source in projected["sources"]} >= {
        "sanders-11qpsa-1965",
        "rahlfs-hanhart-septuaginta-2006",
        "gentry-textual-criticism-2020",
        "iaa-11q5-digital-library",
    }
    assert result["related_passages"]["authored_relationships"] == []
    assert result["related_passages"]["evidence_backed_bridges"] == []
