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

EXPECTED_A2 = {
    "psalm-5-morning-motif-and-setting-limits": (
        "Psalm 5",
        "Psalm 5:1-12",
        "literary-convention",
        "botha-psalm5-polarity-2018",
        {"biblical_narrative", "themes_biblical_connections"},
    ),
    "psalm-20-amherst63-parallel-and-direction-debate": (
        "Psalm 20",
        "Psalm 20:1-5",
        "ancient-text",
        "ward-amherst63-psalm20-2023",
        {"archaeology_ancient_history"},
    ),
    "psalm-25-individual-prayer-and-collective-epilogue": (
        "Psalm 25",
        "Psalm 25:1-22",
        "literary-convention",
        "human-psalm25-tradition-setting-1996",
        {"biblical_narrative", "themes_biblical_connections"},
    ),
}

EXPECTED_A3 = {
    "psalm-7-cush-superscription-and-setting-limits": ("Psalm 7", "Psalm 7:1-17", "literary-convention", "berger-psalm7-benjaminite-conflict-2014"),
    "psalm-11-refuge-and-spatial-argument": ("Psalm 11", "Psalm 11:1-7", "literary-convention", "prinsloo-psalm11-spatial-reading-2015"),
    "psalm-14-psalm53-revision-debate": ("Psalm 14", "Psalm 14:1-7", "literary-convention", "botha-psalm53-canonical-2013"),
    "psalm-17-textual-proposals-verses-11-and-14": ("Psalm 17", "Psalm 17:1-15", "manuscript", "bazylinski-psalm17-text-2021"),
    "psalm-21-request-language-diplomatic-proposal": ("Psalm 21", "Psalm 21:2", "literary-convention", "sheveka-royal-psalms-diplomatic-2005"),
    "psalm-26-walking-integrity-and-wisdom-structure": ("Psalm 26", "Psalm 26:1-12", "literary-convention", "potgieter-psalm26-wisdom-2013"),
    "psalm-33-sea-and-deep-imagery": ("Psalm 33", "Psalm 33:6-9", "literary-convention", "stoltz-psalm33-contextual-2018"),
    "psalm-43-refrain-and-stanza-structure": ("Psalm 43", "Psalm 43:1-5", "literary-convention", "simango-psalm42-43-structure-2025"),
    "psalm-49-wisdom-poem-and-chiastic-focus": ("Psalm 49", "Psalm 49:1-20", "literary-convention", "pleins-psalm49-structure-1996"),
    "psalm-83-coalition-imagery-and-setting-limits": ("Psalm 83", "Psalm 83:1-18", "literary-convention", "mitchell-psalter-psalm83-1995"),
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

EXPECTED_A4 = {
    "psalm-46-chaos-waters-and-stream-imagery": ("Psalm 46", "Psalm 46:2-5", "schader-psalms46-48-spatiality-2010"),
    "psalm-56-superscription-and-editorial-frame": ("Psalm 56", "Psalm 56:1-13", "potgieter-psalm56-editorial-context-2015"),
    "psalm-77-lament-memory-and-exodus-reframing": ("Psalm 77", "Psalm 77:1-20", "kamuwanga-psalm77-exile-suffering-2007"),
    "psalm-91-wisdom-language-and-protection-instruction": ("Psalm 91", "Psalm 91:1-16", "botha-psalm91-wisdom-2012"),
    "psalm-92-creation-order-and-sabbath-song": ("Psalm 92", "Psalm 92:1-15", "tucker-psalm92-ordered-world-2019"),
    "psalm-105-history-recounted-as-liturgy": ("Psalm 105", "Psalm 105:1-45", "gillingham-psalms105-106-liturgy-2015"),
    "psalm-111-acrostic-praise-and-scribal-learning": ("Psalm 111", "Psalm 111:1-10", "prinsloo-psalm111-112-acrostics-2019"),
    "psalm-139-imprecation-and-ambiguity-in-prayer": ("Psalm 139", "Psalm 139:19-24", "firth-psalm139-ambiguity-2019"),
}



def test_psalm_items_do_not_create_cross_passage_or_entity_links():
    psalms = _load_ckl("books/psalms.json")
    for passage, _, _ in EXPECTED.values():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []


def test_ed2_master_psalms_a2_project_with_exact_anchors_and_separate_rationale():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, category, source_id, section_ids) in EXPECTED_A2.items():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        projected_id = f"ckl:psalms#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)
        assert projected["record_kind"] == "evidence"
        assert projected["evidence_category"] == category
        assert [x["reference"] for x in projected["passage_anchors"]] == [anchor]
        assert [x["reference"] for x in projected["applicable_passage_anchors"]] == [anchor]
        assert set(projected["section_ids"]) == section_ids
        assert {"psalms-masoretic", source_id}.issubset(projected["source_ids"])
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["claim_text"]
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["confidence"] == "medium"
        assert projected["certainty"] == "plausible"
        assert projected["dispute_status"] == "interpretive_uncertainty"
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        edges = [entry for entry in result["connections"] if entry.get("source_id") == projected_id]
        assert len(edges) == 1
        assert edges[0]["target_id"] == f"passage:{anchor}"
        assert edges[0]["basis"]["kind"] == "ckl_scripture_anchor"
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []


def test_ed2_master_psalms_a3_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, category, source_id) in EXPECTED_A3.items():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        projected_id = f"ckl:psalms#evidence:{local_id}"
        matches = [entry for entry in result["items"] if entry["id"] == projected_id]
        assert len(matches) == 1
        projected = _item(result, projected_id)
        assert projected["record_kind"] == "evidence"
        assert projected["evidence_category"] == category
        assert [x["reference"] for x in projected["passage_anchors"]] == [anchor]
        assert [x["reference"] for x in projected["applicable_passage_anchors"]] == [anchor]
        assert {"psalms-masoretic", source_id}.issubset(projected["source_ids"])
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        edges = [entry for entry in result["connections"] if entry.get("source_id") == projected_id]
        assert len(edges) == 1
        assert edges[0]["target_id"] == f"passage:{anchor}"
        assert edges[0]["basis"]["kind"] == "ckl_scripture_anchor"
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []



def test_ed2_master_psalms_a4_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED_A4.items():
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
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        edges = [entry for entry in result["connections"] if entry.get("source_id") == projected_id]
        assert len(edges) == 1
        assert edges[0]["target_id"] == f"passage:{anchor}"
        assert edges[0]["basis"]["kind"] == "ckl_scripture_anchor"
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []
