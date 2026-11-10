from tests.test_narrative_explorer_projection import _item, _lookup, _load_ckl, _project


EXPECTED = {
    "psalm-55-betrayal-and-historical-setting-limits": ("Psalm 55", "Psalm 55:9-14", "declaissé-walford-psalter-violence-2023"),
    "psalm-60-communal-defeat-and-book-context": ("Psalm 60", "Psalm 60:1-12", "verde-psalms-trauma-2022"),
    "psalm-66-collective-and-individual-praise": ("Psalm 66", "Psalm 66:1-20", "sutton-psalm66-piety-2021"),
    "psalm-75-proposed-wordplay-in-judgment-poem": ("Psalm 75", "Psalm 75:5-8", "jensen-psalm75-poetic-context-2001"),
    "psalm-80-vine-lament-and-son-ambiguity": ("Psalm 80", "Psalm 80:8-19", "streett-psalm80-historical-context-2014"),
    "psalm-81-hinge-lines-and-colometry-proposal": ("Psalm 81", "Psalm 81:5-12", "weber-psalm81-monocola-2024"),
    "psalm-97-kingship-and-book-four-narrative": ("Psalm 97", "Psalm 97:1-12", "hamilton-yhwh-kingship-psalms-2023"),
    "psalm-100-worship-and-the-psalter-sequence": ("Psalm 100", "Psalm 100:1-5", "firth-psalm100-worship-war-language-2021"),
}


def test_ed2_master_psalms_project_once_with_exact_scope_and_sources():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED.items():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        projected_id = f"ckl:psalms#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)
        assert projected["record_kind"] == "evidence"
        assert projected["evidence_category"] == "literary-convention"
        assert [x["reference"] for x in projected["passage_anchors"]] == [anchor]
        assert [x["reference"] for x in projected["applicable_passage_anchors"]] == [anchor]
        assert set(projected["section_ids"]) == {"biblical_narrative", "themes_biblical_connections"}
        assert {"psalms-masoretic", scholarly_source}.issubset(projected["source_ids"])
        assert projected["sources"]
        assert all(x["details_available"] for x in projected["sources"])
        assert all(x["bibliographic_details"].get("locator") for x in projected["sources"])
        assert projected["confidence"] == ("low" if local_id.startswith("psalm-75-") else "medium")
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        edges = [x for x in result["connections"] if x.get("source_id") == projected_id]
        assert len(edges) == 1
        assert edges[0]["target_id"] == f"passage:{anchor}"
        assert edges[0]["basis"]["kind"] == "ckl_scripture_anchor"


def test_psalm_items_do_not_create_cross_passage_or_entity_links():
    psalms = _load_ckl("books/psalms.json")
    for passage, _, _ in EXPECTED.values():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []
