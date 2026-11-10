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

EXPECTED_A5 = {
    "psalm-39-wisdom-reflection-and-delayed-retribution": ("Psalm 39", "Psalm 39:1-13", "botha-psalm39-retribution-2017"),
    "psalm-48-zion-security-and-remembered-space": ("Psalm 48", "Psalm 48:8-14", "steiner-psalm48-narrated-space-2012"),
    "psalm-62-community-address-and-wealth-warning": ("Psalm 62", "Psalm 62:8-12", "botha-psalm62-community-exhortation-2018"),
    "psalm-71-old-age-and-generational-witness": ("Psalm 71", "Psalm 71:17-21", "liess-psalm71-aging-and-generational-witness-2023"),
}

EXPECTED_A6 = {
    "psalm-12-speech-poor-and-wisdom-polarity": ("Psalm 12", "Psalm 12:2-7", "botha-psalm12-poor-and-speech-2012"),
    "psalm-28-lament-praise-and-final-petition": ("Psalm 28", "Psalm 28:1-9", "barus-psalm28-mood-shift-2023"),
    "psalm-35-battlefield-and-courtroom-movement": ("Psalm 35", "Psalm 35:1-28", "simango-psalm35-structure-and-genre-2022"),
    "psalm-38-embodied-distress-and-prayer-for-wholeness": ("Psalm 38", "Psalm 38:1-22", "human-psalm38-body-imagery-2022"),
    "psalm-45-sound-and-performance-of-royal-poem": ("Psalm 45", "Psalm 45:1-2", "wendland-psalm45-sound-and-rhetoric-2013"),
}

EXPECTED_A7 = {
    "psalm-52-wealth-critique-and-wisdom-intertexts": ("Psalm 52", "Psalm 52:1-9", "botha-psalm52-wisdom-network-2013"),
    "psalm-59-evening-threat-and-morning-confidence": ("Psalm 59", "Psalm 59:1-17", "janowski-psalm59-time-and-prayer-2013"),
    "psalm-61-royal-voice-proposal": ("Psalm 61", "Psalm 61:4-7", "lemon-psalms61-63-hezekiah-bulla-2024"),
    "psalm-63-royal-voice-proposal": ("Psalm 63", "Psalm 63:7-11", "lemon-psalms61-63-hezekiah-bulla-2024"),
    "psalm-64-attack-to-vindication-narrative-movement": ("Psalm 64", "Psalm 64:1-10", "eder-psalm64-narrative-structure-2019"),
    "psalm-65-zion-to-earth-praise-sequence": ("Psalm 65", "Psalm 65:1-13", "botha-psalms65-68-cluster-2023"),
}

EXPECTED_A8 = {
    "psalm-86-korah-collection-lament-frame": ("Psalm 86", "Psalm 86:1-17", "loader-psalm86-korah-contextual-synergy-2010"),
    "psalm-87-zion-status-reading-dispute": ("Psalm 87", "Psalm 87:1-7", "rautenbach-psalm87-social-values-2008"),
    "psalm-70-concentric-structure-proposal": ("Psalm 70", "Psalm 70:1-5", "auffret-psalm70-structure-2011"),
    "psalm-101-royal-voice-and-community-justice": ("Psalm 101", "Psalm 101:1-8", "botha-psalm101-restoration-society-2016"),
    "psalm-108-head-imagery-and-royal-victory-metaphor": ("Psalm 108", "Psalm 108:1-13", "sutton-human-psalms108-110-head-imagery-2017"),
    "psalm-98-yhwh-kingship-in-book-four-cluster": ("Psalm 98", "Psalm 98:1-9", "blunda-psalms93-100-kingship-liturgy-2020"),
}

EXPECTED_A9 = {
    "psalm-57-reuse-in-psalm108-reframes-praise": ("Psalm 57", "Psalm 57:7-11", "botha-psalm108-quest-closure-2010"),
    "psalm-69-restoration-stanza-and-servants": ("Psalm 69", "Psalm 69:34-36", "lyons-servants-psalms-22-69-102-2021"),
    "psalm-94-weekday-song-and-poetic-sequence": ("Psalm 94", "Psalm 94:1-23", "jaffe-psalm94-wednesday-song-2026"),
    "psalm-99-zion-and-kingship-sequence": ("Psalm 99", "Psalm 99:1-9", "hamilton-yhwh-kingship-psalms-2023"),
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


def test_ed2_master_psalms_a5_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED_A5.items():
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


def test_ed2_master_psalms_a6_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED_A6.items():
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


def test_ed2_master_psalms_a7_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED_A7.items():
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
        expected_confidence = "low" if local_id in {
            "psalm-61-royal-voice-proposal",
            "psalm-63-royal-voice-proposal",
        } else "medium"
        assert projected["confidence"] == expected_confidence
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


def test_ed2_master_psalms_a8_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED_A8.items():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        projected_id = f"ckl:psalms#evidence:{local_id}"
        projected = _item(result, projected_id)
        assert [x["reference"] for x in projected["passage_anchors"]] == [anchor]
        assert [x["reference"] for x in projected["applicable_passage_anchors"]] == [anchor]
        assert {"psalms-masoretic", scholarly_source}.issubset(projected["source_ids"])
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        expected_confidence = "low" if local_id in {
            "psalm-70-concentric-structure-proposal",
            "psalm-98-yhwh-kingship-in-book-four-cluster",
        } else "medium"
        assert projected["confidence"] == expected_confidence
        expected_certainty = "disputed" if local_id == "psalm-87-zion-status-reading-dispute" else "plausible"
        expected_dispute = "major_scholarly_disagreement" if local_id == "psalm-87-zion-status-reading-dispute" else "interpretive_uncertainty"
        assert projected["certainty"] == expected_certainty
        assert projected["dispute_status"] == expected_dispute
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []


def test_ed2_master_psalms_a9_project_with_exact_anchors_and_source_disclosure():
    psalms = _load_ckl("books/psalms.json")
    for local_id, (passage, anchor, scholarly_source) in EXPECTED_A9.items():
        result = _project(passage, canonical=_lookup("ckl", records=psalms))
        projected_id = f"ckl:psalms#evidence:{local_id}"
        projected = _item(result, projected_id)
        assert [x["reference"] for x in projected["passage_anchors"]] == [anchor]
        assert [x["reference"] for x in projected["applicable_passage_anchors"]] == [anchor]
        assert {"psalms-masoretic", scholarly_source}.issubset(projected["source_ids"])
        assert all(source["details_available"] for source in projected["sources"])
        assert all(source["bibliographic_details"].get("locator") for source in projected["sources"])
        assert projected["rationale"]["primary_observation"]
        assert projected["rationale"]["scholarly_interpretation"]
        assert projected["content_status"] == "draft"
        assert projected["review_status"] == "in_review"
        assert projected["human_review_required"] is True
        assert result["related_passages"]["authored_relationships"] == []
        assert result["related_passages"]["evidence_backed_bridges"] == []
