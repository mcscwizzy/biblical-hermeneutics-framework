from __future__ import annotations

from framework.canonical_library import CanonicalLibrary, audit_evidence, rank_evidence_items


EXPANSION_OBJECTS = {
    "mesopotamian-creation-and-flood-comparisons": 3,
    "ancient-divine-assembly-imagery": 4,
    "egyptian-forced-labor-and-brickmaking": 2,
    "thessalonian-civic-and-funerary-context": 16,
    "egyptian-kingship-and-divine-order": 4,
    "exodus-wilderness-routes-and-water": 3,
    "late-bronze-iron-transition-and-highland-settlement": 4,
    "judges-household-religion-and-regional-cult-sites": 4,
    "tabernacle-presence-access-and-mobility": 4,
    "ancient-portable-sanctuaries-and-tabernacle-comparisons": 4,
    "assyrian-deportation-and-provincial-incorporation": 4,
    "assyrian-tribute-and-royal-representation": 4,
    "babylonian-conquest-deportation-and-judean-diaspora": 4,
    "persian-restoration-and-yehud-administration": 4,
    "second-temple-priesthood-and-temple-authority": 4,
    "second-temple-synagogues-scribes-and-sectarian-groups": 5,
    "galilean-villages-households-and-subsistence": 7,
    "judean-pilgrimage-taxation-and-roman-power": 8,
    "roman-corinth-civic-household-and-association-life": 10,
    "roman-ephesus-civic-cultic-and-household-life": 12,
    "roman-philippi-colonial-civic-and-household-life": 12,
    "roman-rome-jewish-civic-household-and-imperial-life": 17,
    "roman-macedonia-road-network-and-city-diversity": 11,
}


def _rank(
    library: CanonicalLibrary,
    object_id: str,
    question: str,
    reference: str,
    *dimensions: str,
):
    return rank_evidence_items(
        question,
        library.objects_by_id[object_id],
        scripture_references=(reference,),
        requested_dimensions=dimensions,
        limit=10,
    )


def test_expansion_clusters_are_sourced_chronological_and_reviewable() -> None:
    library = CanonicalLibrary.load_default()
    for object_id, expected_count in EXPANSION_OBJECTS.items():
        obj = library.objects_by_id[object_id]
        assert obj.content_status == "draft"
        assert obj.human_review_required is True
        assert obj.reviewed_by == []
        assert len(obj.evidence_items) == expected_count
        source_ids = {source.id for source in obj.sources}
        for item in obj.evidence_items:
            assert item.source_ids
            assert set(item.source_ids) <= source_ids
            assert item.temporal_scope.periods
            assert item.passage_relevance
            assert item.confidence_rationale
            assert item.primary_observation != item.scholarly_interpretation
            assert item.scripture_references


def test_genesis_evidence_prefers_direct_text_then_ane_comparison_without_leakage() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "mesopotamian-creation-and-flood-comparisons",
        "What ancient creation evidence helps explain Genesis 1?",
        "Genesis 1:1-31",
        "ancient near eastern background",
    )
    assert [item.evidence_id for item in ranked] == [
        "genesis-ordered-worldview-observation",
        "enuma-elish-cosmic-ordering-comparison",
    ]
    assert ranked[0].chronological_relation == "diachronic"
    assert ranked[1].chronological_relation == "earlier-comparative"
    assert all("Roman" not in item.description for item in ranked)
    assert all("Johannine" not in item.description for item in ranked)


def test_psalm_82_retrieves_textual_worldview_and_ugaritic_comparison_with_dispute() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Psalm 82:1-8", limit=20)
    }
    assert "ancient-divine-assembly-imagery" in passage_objects
    ranked = _rank(
        library,
        "ancient-divine-assembly-imagery",
        "What evidence helps explain the divine assembly in Psalm 82?",
        "Psalm 82:1-8",
        "ancient near eastern background",
    )
    assert {item.evidence_id for item in ranked} == {
        "psalm-82-assembly-language",
        "ugaritic-council-comparison",
    }
    assert all(item.dispute_status != "not_disputed" for item in ranked)
    assert any(item.evidence_type == "worldview-concept" for item in ranked)


def test_thessalonian_context_prefers_contemporary_proposal_over_later_funerary_data() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference(
            "1 Thessalonians 4:13-18", limit=30
        )
    }
    assert "thessalonian-civic-and-funerary-context" in passage_objects
    ranked = _rank(
        library,
        "thessalonian-civic-and-funerary-context",
        "What civic, funerary, and arrival context helps explain 1 Thessalonians 4?",
        "1 Thessalonians 4:13-18",
        "greco roman context",
        "cultural practice",
    )
    ranked_by_id = {item.evidence_id: item for item in ranked}
    arrival = ranked_by_id["parousia-apantesis-civic-arrival-proposal"]
    funerary = ranked_by_id["later-thessalonian-funerary-comparison"]
    assert arrival.chronological_relation == "contemporary"
    assert funerary.chronological_relation == "later-comparative"
    assert arrival.retrieval_score > funerary.retrieval_score


def test_thessalonian_city_expansion_covers_geography_civic_process_and_audience_limits() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["thessalonian-civic-and-funerary-context"]
    items = {item.id: item for item in cluster.evidence_items}
    assert {
        "via-egnatia-port-and-free-city",
        "thessalonian-politarch-inscription",
        "jason-house-civic-security",
        "acts-synagogue-and-audience-limits",
        "prominent-women-status-limits",
    } <= set(items)
    assert items["via-egnatia-port-and-free-city"].evidence_type == "geography-environment"
    assert items["jason-house-civic-security"].confidence == "medium"
    assert "proportions" in items["acts-synagogue-and-audience-limits"].confidence_rationale
    assert "unproven" in items["prominent-women-status-limits"].confidence_rationale


def test_thessalonian_cult_and_imperial_evidence_remains_plural_and_nonexclusive() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["thessalonian-civic-and-funerary-context"]
    items = {item.id: item for item in cluster.evidence_items}
    assert items["turning-from-idols-living-god"].evidence_type == "worldview-concept"
    assert items["julio-claudian-imperial-honors"].evidence_type == "worldview-concept"
    assert items["julio-claudian-imperial-honors"].dispute_status == "major_scholarly_disagreement"
    assert "sole cause" in items["julio-claudian-imperial-honors"].scholarly_interpretation
    assert "No single cult" in items["turning-from-idols-living-god"].notes


def test_thessalonian_household_labor_affliction_and_peace_claims_are_bounded() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["thessalonian-civic-and-funerary-context"]
    items = {item.id: item for item in cluster.evidence_items}
    assert "No excavated" in items["household-venue-uncertainty"].notes
    assert "worker shaming" in items["missionary-manual-labor"].notes
    assert items["work-instruction-and-patronage-proposal"].confidence == "low"
    assert "collective Jewish blame" in items["thessalonian-affliction-opponents-uncertain"].passage_relevance
    assert items["peace-security-competing-backgrounds"].confidence == "low"
    assert "headline matching" in items["peace-security-competing-backgrounds"].notes


def test_macedonian_route_cluster_distinguishes_trunk_stations_and_beroean_branch() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-macedonia-road-network-and-city-diversity"]
    items = {item.id: item for item in cluster.evidence_items}
    assert {
        "macedonia-call-and-aegean-entry",
        "via-egnatia-east-macedonian-corridor",
        "amphipolis-apollonia-named-transit",
        "beroea-branch-road-constraint",
    } <= set(items)
    assert items["via-egnatia-east-macedonian-corridor"].confidence == "high"
    assert "branch" in items["beroea-branch-road-constraint"].description
    assert "rather than sitting" in items["beroea-branch-road-constraint"].description
    assert "preaching" in items["amphipolis-apollonia-named-transit"].passage_relevance


def test_macedonian_cluster_preserves_city_and_source_differences() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-macedonia-road-network-and-city-diversity"]
    items = {item.id: item for item in cluster.evidence_items}
    civic = items["philippi-thessalonica-beroea-civic-differences"]
    itinerary = items["acts-first-thessalonians-itinerary-comparison"]
    gifts = items["macedonian-gifts-and-collection-rhetoric"]
    assert civic.confidence == "medium"
    assert "uniform" in civic.notes
    assert itinerary.dispute_status == "major_scholarly_disagreement"
    assert "harmonization" in itinerary.notes
    assert gifts.dispute_status == "major_scholarly_disagreement"
    assert "Poverty is not praised" in gifts.notes


def test_macedonian_route_evidence_is_discoverable_without_city_flattening() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Acts 17:1", limit=30)
    }
    assert "roman-macedonia-road-network-and-city-diversity" in passage_objects
    ranked = _rank(
        library,
        "roman-macedonia-road-network-and-city-diversity",
        "Which Via Egnatia stations connect Philippi and Thessalonica in Acts?",
        "Acts 17:1",
        "historical setting",
    )
    ranked_by_id = {item.evidence_id: item for item in ranked}
    assert ranked[0].evidence_id == "amphipolis-apollonia-named-transit"
    assert "via-egnatia-east-macedonian-corridor" in ranked_by_id
    assert ranked[0].passage_relationship == "direct"
    assert ranked_by_id["via-egnatia-east-macedonian-corridor"].passage_relationship == "contextual"


def test_macedonia_place_record_replaces_legacy_empire_boilerplate() -> None:
    library = CanonicalLibrary.load_default()
    macedonia = library.objects_by_id["macedonia"]
    assert macedonia.title == "Roman Macedonia"
    assert macedonia.content_status == "complete"
    assert macedonia.context_applicability["ancient_near_east"] is False
    assert "Babylon" not in macedonia.summary
    assert "Beroea" in macedonia.historical_context
    assert any(
        relation.id == "roman-macedonia-road-network-and-city-diversity"
        for relation in macedonia.related_objects
    )


def test_exodus_brickmaking_cluster_is_discoverable_by_passage() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Exodus 5:6-19", limit=20)
    }
    assert "egyptian-forced-labor-and-brickmaking" in passage_objects
    ranked = _rank(
        library,
        "egyptian-forced-labor-and-brickmaking",
        "What Egyptian evidence contextualizes the brick quota?",
        "Exodus 5:6-19",
        "cultural practice",
        "archaeology",
    )
    assert [item.evidence_id for item in ranked] == [
        "exodus-brickmaking-and-quota",
        "rekhmire-brickmaking-scene",
    ]
    assert ranked[0].passage_relationship == "direct"
    assert ranked[1].passage_relationship == "comparative"


def test_egyptian_kingship_context_keeps_text_and_artifacts_distinct() -> None:
    library = CanonicalLibrary.load_default()
    authority = _rank(
        library,
        "egyptian-kingship-and-divine-order",
        "How does Pharaoh's authority compare with Egyptian royal ideology?",
        "Exodus 5:1-5",
        "ancient near eastern background",
        "archaeology",
    )
    assert authority[0].evidence_id == "pharaoh-authority-question"
    assert authority[0].passage_relationship == "direct"
    assert {
        item.evidence_id for item in authority[1:]
    } == {"seti-royal-offering-scene", "seti-son-of-ra-titulary"}
    assert all(item.passage_relationship == "comparative" for item in authority[1:])

    gods = _rank(
        library,
        "egyptian-kingship-and-divine-order",
        "What does Exodus say about judgment on the gods of Egypt?",
        "Exodus 12:12",
        "ancient near eastern background",
    )
    assert gods[0].evidence_id == "judgment-on-egypts-gods"
    assert gods[0].evidence_type == "worldview-concept"
    assert gods[0].dispute_status == "interpretive_uncertainty"


def test_wilderness_geography_prefers_direct_water_data_and_preserves_route_uncertainty() -> None:
    library = CanonicalLibrary.load_default()
    water = _rank(
        library,
        "exodus-wilderness-routes-and-water",
        "What do Marah and Elim show about water along the wilderness route?",
        "Exodus 15:22-27",
        "historical setting",
    )
    assert [item.evidence_id for item in water] == ["marah-elim-water-stations"]
    assert water[0].passage_relationship == "direct"

    sea = _rank(
        library,
        "exodus-wilderness-routes-and-water",
        "Where was the Sea crossing and how certain is the route?",
        "Exodus 14:1-31",
        "historical setting",
    )
    assert [item.evidence_id for item in sea] == ["yam-suf-route-identification"]
    assert sea[0].confidence == "medium"
    assert sea[0].dispute_status == "identification_uncertainty"


def test_judges_settlement_evidence_prefers_the_text_and_limits_archaeological_inference() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Judges 1:1-36", limit=30)
    }
    assert "late-bronze-iron-transition-and-highland-settlement" in passage_objects
    ranked = _rank(
        library,
        "late-bronze-iron-transition-and-highland-settlement",
        "What archaeological evidence contextualizes settlement in Judges 1?",
        "Judges 1:1-36",
        "archaeology",
        "historical setting",
    )
    assert ranked[0].evidence_id == "judges-regional-settlement-pattern"
    assert ranked[0].passage_relationship == "direct"
    assert {item.evidence_id for item in ranked[1:]} == {
        "merneptah-israel-people-reference",
        "iron-i-central-highland-villages",
        "iron-i-regional-continuity-and-change",
    }
    assert all(item.passage_relationship == "contextual" for item in ranked[1:])
    merneptah = next(
        item for item in ranked if item.evidence_id == "merneptah-israel-people-reference"
    )
    assert merneptah.chronological_relation == "near-contemporary"
    assert merneptah.external_references[0]["domain"] == "archaeology-item"
    assert merneptah.external_references[0]["id"] == "merneptah-stele"


def test_judges_household_religion_keeps_direct_text_ahead_of_cult_site_comparison() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "judges-household-religion-and-regional-cult-sites",
        "What does Micah's household shrine show about divine favor?",
        "Judges 17:1-13",
        "cultural practice",
        "ancient near eastern background",
    )
    assert [item.evidence_id for item in ranked] == [
        "micah-household-cult-and-divine-favor",
        "bull-site-open-cult-place-comparison",
    ]
    assert ranked[0].passage_relationship == "direct"
    assert ranked[0].evidence_type == "worldview-concept"
    assert ranked[1].passage_relationship == "comparative"
    assert ranked[1].dispute_status == "identification_uncertainty"

    shiloh = _rank(
        library,
        "judges-household-religion-and-regional-cult-sites",
        "What evidence helps explain the annual festival at Shiloh?",
        "Judges 21:19-23",
        "historical setting",
    )
    assert [item.evidence_id for item in shiloh] == [
        "shiloh-sanctuary-and-festival"
    ]
    assert shiloh[0].passage_relationship == "direct"


def test_tabernacle_presence_evidence_prefers_direct_textual_controls() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Exodus 25:1-9", limit=30)
    }
    assert "tabernacle-presence-access-and-mobility" in passage_objects
    ranked = _rank(
        library,
        "tabernacle-presence-access-and-mobility",
        "Why does Exodus build the tabernacle for divine presence?",
        "Exodus 25:1-9",
        "ancient near eastern background",
        "cultural practice",
    )
    assert ranked[0].evidence_id == "tabernacle-dwelling-purpose"
    assert ranked[0].passage_relationship == "direct"
    assert ranked[0].evidence_type == "worldview-concept"

    access = _rank(
        library,
        "tabernacle-presence-access-and-mobility",
        "How does the veil regulate access to sacred space?",
        "Exodus 26:31-37",
        "cultural practice",
    )
    assert [item.evidence_id for item in access] == [
        "tabernacle-graded-sacred-space"
    ]
    assert access[0].passage_relationship == "direct"


def test_portable_sanctuary_comparisons_remain_comparative_and_nonidentifying() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "ancient-portable-sanctuaries-and-tabernacle-comparisons",
        "What ancient evidence compares with the tabernacle?",
        "Exodus 26:1-37",
        "ancient near eastern background",
        "archaeology",
    )
    assert [item.evidence_id for item in ranked] == [
        "mari-large-public-tent-comparison",
        "timna-tented-shrine-comparison",
        "qadesh-royal-tent-comparison",
    ]
    assert all(item.passage_relationship == "comparative" for item in ranked)
    assert all(item.chronological_relation == "earlier-comparative" for item in ranked)
    timna = ranked[1]
    assert timna.dispute_status == "archaeological_uncertainty"
    assert timna.external_references[0]["domain"] == "archaeology-site"
    assert timna.external_references[0]["id"] == "timna-site-200"

    bark = _rank(
        library,
        "ancient-portable-sanctuaries-and-tabernacle-comparisons",
        "How do Egyptian bark shrines compare with sacred transport?",
        "Numbers 4:4-20",
        "archaeology",
    )
    assert bark[0].evidence_id == "egyptian-processional-bark-shrine-contrast"
    assert bark[0].passage_relationship == "contrast"
    assert bark[1].evidence_id == "timna-tented-shrine-comparison"
    assert bark[1].passage_relationship == "comparative"


def test_assyrian_deportation_evidence_keeps_kings_direct_and_sargon_contextual() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("2 Kings 17:1-6", limit=40)
    }
    assert "assyrian-deportation-and-provincial-incorporation" in passage_objects
    ranked = _rank(
        library,
        "assyrian-deportation-and-provincial-incorporation",
        "What Assyrian evidence helps explain Samaria's fall and deportation?",
        "2 Kings 17:1-6",
        "historical setting",
        "ancient near eastern background",
    )
    assert ranked[0].evidence_id == "kings-staged-assyrian-reduction"
    assert ranked[0].passage_relationship == "direct"
    sargon = next(
        item for item in ranked if item.evidence_id == "sargon-samaria-conquest-claim"
    )
    assert sargon.passage_relationship == "contextual"
    assert sargon.chronological_relation == "near-contemporary"
    assert sargon.dispute_status == "minor_scholarly_disagreement"
    assert sargon.external_references[0]["domain"] == "external-dataset"


def test_assyrian_tribute_evidence_distinguishes_text_artifacts_and_media() -> None:
    library = CanonicalLibrary.load_default()
    jehu = _rank(
        library,
        "assyrian-tribute-and-royal-representation",
        "What does the Black Obelisk show about Jehu's tribute?",
        "2 Kings 9:1-37",
        "archaeology",
        "historical setting",
    )
    assert [item.evidence_id for item in jehu] == ["black-obelisk-jehu-tribute"]
    assert jehu[0].passage_relationship == "contextual"
    assert jehu[0].chronological_relation == "near-contemporary"
    assert jehu[0].external_references[0]["id"] == "black-obelisk"

    hezekiah = _rank(
        library,
        "assyrian-tribute-and-royal-representation",
        "What Assyrian evidence contextualizes Hezekiah's tribute and Lachish?",
        "2 Kings 18:13-37",
        "archaeology",
        "ancient near eastern background",
    )
    assert hezekiah[0].evidence_id == "kings-tribute-vassalage-sequence"
    assert hezekiah[0].passage_relationship == "direct"
    assert {item.evidence_id for item in hezekiah[1:]} == {
        "sennacherib-hezekiah-tribute",
        "lachish-royal-victory-display",
    }
    assert all(item.passage_relationship == "contextual" for item in hezekiah[1:])
    assert all(item.chronological_relation == "near-contemporary" for item in hezekiah[1:])


def test_babylonian_conquest_evidence_distinguishes_597_from_the_later_fall() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("2 Kings 24:8-17", limit=40)
    }
    assert "babylonian-conquest-deportation-and-judean-diaspora" in passage_objects
    ranked = _rank(
        library,
        "babylonian-conquest-deportation-and-judean-diaspora",
        "What Babylonian evidence helps explain Jerusalem's capture and deportation?",
        "2 Kings 24:8-17",
        "historical setting",
        "archaeology",
    )
    assert [item.evidence_id for item in ranked] == [
        "kings-jeremiah-deportation-sequence",
        "babylonian-chronicle-597-capture",
        "jehoiachin-palace-ration-lists",
    ]
    assert ranked[0].passage_relationship == "direct"
    assert ranked[1].passage_relationship == "contextual"
    assert ranked[1].chronological_relation == "near-contemporary"
    assert "does not narrate the later temple destruction" in ranked[1].passage_relevance


def test_jehoiachin_ration_lists_contextualize_court_life_without_claiming_release() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "babylonian-conquest-deportation-and-judean-diaspora",
        "What do palace ration lists show about Jehoiachin in Babylon?",
        "2 Kings 25:27-30",
        "archaeology",
    )
    assert [item.evidence_id for item in ranked] == [
        "jehoiachin-palace-ration-lists",
        "kings-jeremiah-deportation-sequence",
    ]
    assert ranked[0].passage_relationship == "contextual"
    assert "stopping short of confirming the release scene" in ranked[0].passage_relevance


def test_persian_evidence_keeps_cyrus_and_elephantine_comparisons_bounded() -> None:
    library = CanonicalLibrary.load_default()
    cyrus = _rank(
        library,
        "persian-restoration-and-yehud-administration",
        "How does the Cyrus Cylinder contextualize the return under Cyrus?",
        "Ezra 1:1-11",
        "historical setting",
        "archaeology",
    )
    assert [item.evidence_id for item in cyrus] == [
        "ezra-persian-return-and-temple-sequence",
        "cyrus-cylinder-babylonian-restoration-scope",
    ]
    assert cyrus[0].passage_relationship == "direct"
    assert cyrus[1].passage_relationship == "contextual"
    assert "silence about Judah and Jerusalem" in cyrus[1].passage_relevance

    administration = _rank(
        library,
        "persian-restoration-and-yehud-administration",
        "What evidence contextualizes Persian provincial administration in Judah?",
        "Nehemiah 5:14-19",
        "historical setting",
        "archaeology",
    )
    assert [item.evidence_id for item in administration] == [
        "yehud-stamp-administration",
        "elephantine-judah-governor-correspondence",
    ]
    assert administration[0].chronological_relation == "contemporary"
    assert administration[1].passage_relationship == "comparative"
    assert administration[1].chronological_relation == "later-comparative"


def test_second_temple_priesthood_keeps_text_artifact_and_later_history_distinct() -> None:
    library = CanonicalLibrary.load_default()
    warning = _rank(
        library,
        "second-temple-priesthood-and-temple-authority",
        "What temple boundary explains the accusation against Paul?",
        "Acts 21:27-36",
        "archaeology",
    )
    assert [item.evidence_id for item in warning] == [
        "temple-warning-inscription-boundary"
    ]
    assert warning[0].passage_relationship == "contextual"
    assert warning[0].chronological_relation == "contemporary"
    assert warning[0].external_references[0]["id"] == "temple-warning-inscription"

    caiaphas = _rank(
        library,
        "second-temple-priesthood-and-temple-authority",
        "How did Caiaphas and the high priesthood operate under Rome?",
        "John 11:47-53",
        "historical setting",
        "archaeology",
    )
    assert [item.evidence_id for item in caiaphas] == [
        "caiaphas-ossuary-identification",
        "gospel-acts-priestly-authority",
        "josephus-high-priestly-appointments",
    ]
    assert caiaphas[0].confidence == "medium"
    assert caiaphas[1].passage_relationship == "direct"
    assert caiaphas[2].chronological_relation == "later-comparative"


def test_second_temple_synagogue_and_group_evidence_preserves_locality_and_dates() -> None:
    library = CanonicalLibrary.load_default()
    synagogue = _rank(
        library,
        "second-temple-synagogues-scribes-and-sectarian-groups",
        "What evidence explains synagogue reading and teaching?",
        "Luke 4:16-30",
        "historical setting",
    )
    assert [item.evidence_id for item in synagogue] == [
        "gospel-acts-synagogue-reading",
        "theodotus-synagogue-inscription",
    ]
    assert synagogue[0].passage_relationship == "direct"
    assert synagogue[1].passage_relationship == "contextual"

    groups = _rank(
        library,
        "second-temple-synagogues-scribes-and-sectarian-groups",
        "What explains the Pharisee Sadducee resurrection dispute?",
        "Acts 23:1-10",
        "historical setting",
    )
    assert [item.evidence_id for item in groups] == [
        "josephus-jewish-group-descriptions",
        "4qmmt-legal-disagreement",
    ]
    assert groups[0].chronological_relation == "later-comparative"
    assert groups[1].chronological_relation == "earlier-comparative"
    assert groups[1].dispute_status == "major_scholarly_disagreement"


def test_second_temple_legal_debate_does_not_identify_4qmmt_with_a_named_group() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "second-temple-synagogues-scribes-and-sectarian-groups",
        "What evidence contextualizes legal and purity disputes?",
        "Mark 7:1-23",
        "cultural practice",
    )
    assert [item.evidence_id for item in ranked] == [
        "4qmmt-legal-disagreement",
        "josephus-jewish-group-descriptions",
    ]
    assert all(item.passage_relationship == "comparative" for item in ranked)
    assert "without making its authors" in ranked[0].passage_relevance


def test_galilean_household_and_village_evidence_stays_passage_bounded() -> None:
    library = CanonicalLibrary.load_default()
    capernaum = _rank(
        library,
        "galilean-villages-households-and-subsistence",
        "What household and roof context helps explain the Capernaum scene?",
        "Mark 2:1-12",
        "cultural practice",
        "archaeology",
    )
    assert [item.evidence_id for item in capernaum] == [
        "gospel-galilean-households",
        "capernaum-domestic-remains",
    ]
    assert capernaum[0].passage_relationship == "direct"
    assert capernaum[1].passage_relationship == "contextual"
    assert "local-scale comparison" in capernaum[1].passage_relevance

    nazareth = _rank(
        library,
        "galilean-villages-households-and-subsistence",
        "What archaeological evidence establishes an Early Roman settlement at Nazareth?",
        "Luke 4:16-30",
        "archaeology",
    )
    assert [item.evidence_id for item in nazareth] == [
        "nazareth-early-roman-dwelling"
    ]
    assert "no evidence for the synagogue speech or a named family home" in nazareth[0].passage_relevance


def test_galilean_material_comparisons_do_not_become_gospel_identifications() -> None:
    library = CanonicalLibrary.load_default()
    vessels = _rank(
        library,
        "galilean-villages-households-and-subsistence",
        "How do stone vessels contextualize the jars at Cana?",
        "John 2:1-12",
        "archaeology",
    )
    assert [item.evidence_id for item in vessels] == [
        "reina-stone-vessel-production"
    ]
    assert vessels[0].passage_relationship == "contextual"
    assert "without identifying" in vessels[0].passage_relevance

    boat = _rank(
        library,
        "galilean-villages-households-and-subsistence",
        "What boat evidence contextualizes the storm crossing?",
        "Mark 4:35-41",
        "archaeology",
    )
    assert boat[0].evidence_id == "galilee-boat-comparison"
    assert boat[0].passage_relationship == "contextual"
    assert "contemporary physical control" in boat[0].passage_relevance
    assert "the Ginosar vessel was Jesus's boat" in library.objects_by_id[
        "galilean-villages-households-and-subsistence"
    ].hermeneutical_lens["common_misinterpretations"]


def test_judean_taxation_and_prefectural_evidence_keeps_institutions_distinct() -> None:
    library = CanonicalLibrary.load_default()
    tax = _rank(
        library,
        "judean-pilgrimage-taxation-and-roman-power",
        "What explains tribute to Caesar and the denarius?",
        "Mark 12:13-17",
        "cultural practice",
    )
    assert [item.evidence_id for item in tax] == ["gospel-taxation-distinctions"]
    assert "flattened into a single tax" in tax[0].passage_relevance

    pilate = _rank(
        library,
        "judean-pilgrimage-taxation-and-roman-power",
        "What evidence contextualizes Pilate's Roman authority?",
        "John 18:28-40",
        "historical setting",
        "archaeology",
    )
    assert [item.evidence_id for item in pilate] == [
        "gospel-roman-hearing",
        "pilate-prefect-inscription",
    ]
    assert pilate[0].passage_relationship == "direct"
    assert pilate[1].passage_relationship == "contextual"
    assert "supplies no evidence for Jesus" in pilate[1].passage_relevance


def test_crucifixion_and_burial_archaeology_blocks_impossibility_and_proof_claims() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "judean-pilgrimage-taxation-and-roman-power",
        "What evidence contextualizes crucifixion and Jewish burial?",
        "Mark 15:21-47",
        "archaeology",
        "cultural practice",
    )
    assert [item.evidence_id for item in ranked] == [
        "gospel-crucifixion-and-burial",
        "yehohanan-crucifixion-burial",
    ]
    assert ranked[0].passage_relationship == "direct"
    assert ranked[1].passage_relationship == "comparative"
    assert "not proving Jesus's case" in ranked[1].passage_relevance


def test_corinthian_gallio_evidence_separates_hearing_from_external_chronology() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "What does the Gallio inscription establish about the Corinthian hearing?",
        "Acts 18:12-17",
        "archaeology",
        "historical setting",
    )
    assert [item.evidence_id for item in ranked[:2]] == [
        "acts-gallio-hearing",
        "gallio-delphi-inscription",
    ]
    assert ranked[0].passage_relationship == "direct"
    assert ranked[1].passage_relationship == "contextual"
    assert "does not mention Paul" in ranked[1].passage_relevance
    assert ranked[1].chronological_relation == "near-contemporary"


def test_corinthian_erastus_and_port_evidence_preserves_identification_limits() -> None:
    library = CanonicalLibrary.load_default()
    erastus = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "Does the Erastus pavement identify Paul's coworker?",
        "Romans 16:23",
        "archaeology",
    )
    assert erastus[0].evidence_id == "erastus-benefaction-inscription"
    assert erastus[0].passage_relationship == "disputed"
    assert erastus[0].dispute_status == "identification_uncertainty"
    assert "neither proving the donor is Paul's associate" in erastus[0].passage_relevance

    ports = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "How does Cenchreae contextualize Phoebe and travel?",
        "Romans 16:1-2",
        "historical setting",
    )
    assert ports[0].evidence_id == "two-harbor-travel-network"
    assert ports[0].passage_relationship == "direct"


def test_corinthian_food_and_meal_context_keeps_settings_and_analogies_distinct() -> None:
    library = CanonicalLibrary.load_default()
    food = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "What settings explain idol food, market meat, and private invitations?",
        "1 Corinthians 10:14-33",
        "cultural practice",
    )
    assert [item.evidence_id for item in food] == ["sanctuary-market-idol-food"]
    assert "Distinguishing cultic tables" in food[0].passage_relevance

    meal = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "What household and association evidence explains hunger and humiliation at the Lord's supper?",
        "1 Corinthians 11:17-34",
        "cultural practice",
    )
    assert [item.evidence_id for item in meal[:2]] == [
        "household-slavery-status",
        "association-meal-status",
    ]
    assert meal[0].passage_relationship == "direct"
    assert meal[1].passage_relationship == "comparative"
    assert "without proving the meeting occurred in a known dining room" in meal[1].passage_relevance


def test_corinthian_slavery_and_athletic_context_resists_endorsement_and_identification() -> None:
    library = CanonicalLibrary.load_default()
    slavery = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "How do slavery and status contextualize remaining in one's calling?",
        "1 Corinthians 7:17-24",
        "cultural practice",
    )
    assert [item.evidence_id for item in slavery] == ["household-slavery-status"]
    assert "without turning description into endorsement" in slavery[0].passage_relevance

    athletics = _rank(
        library,
        "roman-corinth-civic-household-and-association-life",
        "Do the Isthmian Games prove that Paul competed there?",
        "1 Corinthians 9:24-27",
        "archaeology",
    )
    assert athletics[0].evidence_id == "isthmian-athletic-comparison"
    assert athletics[0].passage_relationship == "contextual"
    assert "not making the metaphor exclusive" in athletics[0].passage_relevance


def test_ephesian_ritual_and_artisan_evidence_keeps_text_cult_and_economy_distinct() -> None:
    library = CanonicalLibrary.load_default()
    ritual = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "What do ritual texts establish about the burned books?",
        "Acts 19:11-20",
        "ancient text",
        "cultural practice",
    )
    assert ritual[0].evidence_id == "acts-exorcism-and-book-burning"
    assert ritual[0].passage_relationship == "direct"
    assert "neither identify the burned books as Ephesia grammata" in ritual[0].passage_relevance

    artisans = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "How did Artemis craft income relate to cultic honor?",
        "Acts 19:23-27",
        "historical setting",
    )
    assert artisans[0].evidence_id == "artemis-craft-economy"
    assert artisans[0].passage_relationship == "direct"
    assert "without proving a formal guild" in artisans[0].passage_relevance


def test_ephesian_theater_and_artemision_evidence_respects_monument_phases() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "What do the theater and civic offices establish about the riot?",
        "Acts 19:28-41",
        "archaeology",
        "institution",
    )
    assert [item.evidence_id for item in ranked[:3]] == [
        "theater-civic-assembly-offices",
        "artemision-civic-cult",
        "imperial-cult-and-civic-honor",
    ]
    assert ranked[0].passage_relationship == "contextual"
    assert "preventing the present enlarged theater" in ranked[0].passage_relevance
    assert "no physical proof for Demetrius" in ranked[1].passage_relevance


def test_ephesian_letter_controls_separate_destination_setting_and_opponents() -> None:
    library = CanonicalLibrary.load_default()
    destination = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "Was Ephesians certainly addressed to Ephesus?",
        "Ephesians 1:1",
        "manuscript",
        "textual criticism",
    )
    assert [item.evidence_id for item in destination] == ["ephesians-destination-variant"]
    assert destination[0].dispute_status == "textual_variant"
    assert "possible reception context rather than certain evidence" in destination[0].passage_relevance

    opponents = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "Does Ephesian evidence identify the opponents in First Timothy?",
        "1 Timothy 1:3-7",
        "historical setting",
    )
    assert [item.evidence_id for item in opponents] == ["first-timothy-ephesian-setting"]
    assert opponents[0].passage_relationship == "direct"
    assert "neither dates the letter from Acts nor identifies its teachers" in opponents[0].passage_relevance


def test_ephesian_household_and_association_comparisons_resist_endorsement_and_identity() -> None:
    library = CanonicalLibrary.load_default()
    household = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "How do household and slavery contexts illuminate the instructions?",
        "Ephesians 6:1-9",
        "cultural practice",
    )
    assert household[0].evidence_id == "household-slavery-status-comparison"
    assert household[0].passage_relationship == "comparative"
    assert "without making hierarchy timeless" in household[0].passage_relevance

    offices = _rank(
        library,
        "roman-ephesus-civic-cultic-and-household-life",
        "What association evidence explains overseers and deacons?",
        "1 Timothy 3:1-13",
        "institution",
    )
    assert [item.evidence_id for item in offices[:2]] == [
        "association-benefaction-office-comparison",
        "household-slavery-status-comparison",
    ]
    assert offices[0].passage_relationship == "comparative"
    assert "without deriving church offices from one cult" in offices[0].passage_relevance


def test_philippian_prison_and_colony_evidence_separates_setting_from_identification() -> None:
    library = CanonicalLibrary.load_default()
    prison = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "Does archaeology identify Paul and Silas's prison at Philippi?",
        "Acts 16:23-40",
        "archaeology",
    )
    assert prison[0].evidence_id == "custody-and-traditional-prison"
    assert prison[0].passage_relationship == "disputed"
    assert prison[0].chronological_relation == "later-comparative"
    assert "has not found Paul and Silas's prison" in prison[0].passage_relevance

    colony = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "What does the Roman colony and forum establish about Acts 16?",
        "Acts 16:12",
        "archaeology",
        "historical setting",
    )
    assert colony[0].evidence_id == "philippi-roman-colony-and-forum"
    assert colony[0].passage_relationship == "contextual"
    assert "without assuming every recipient" in colony[0].passage_relevance


def test_philippian_lydia_and_enslaved_diviner_evidence_centers_agency_and_exploitation() -> None:
    library = CanonicalLibrary.load_default()
    lydia = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "Was Lydia a wealthy patron because she sold purple goods?",
        "Acts 16:14-15",
        "cultural practice",
    )
    assert lydia[0].evidence_id == "lydia-trade-household-hospitality"
    assert lydia[0].passage_relationship == "direct"
    assert "without converting purple trade into certain elite wealth" in lydia[0].passage_relevance

    exploited = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "How did owners profit from the enslaved diviner?",
        "Acts 16:16-19",
        "worldview",
        "cultural practice",
    )
    assert exploited[0].evidence_id == "enslaved-diviner-profit-exploitation"
    assert exploited[0].evidence_type == "worldview-concept"
    assert "double exploitation" in exploited[0].passage_relevance


def test_philippian_legal_and_civic_language_remains_contextual_and_nonexclusive() -> None:
    library = CanonicalLibrary.load_default()
    legal = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "What explains the magistrates, lictors, and Roman citizenship?",
        "Acts 16:35-40",
        "institution",
        "historical setting",
    )
    assert legal[0].evidence_id == "magistrates-lictors-and-citizenship"
    assert legal[0].passage_relationship == "contextual"
    assert "complete Roman legal handbook" in legal[0].passage_relevance

    civic = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "How do politeuesthe and politeuma resonate in a Roman colony?",
        "Philippians 3:20-21",
        "ancient text",
        "historical setting",
    )
    assert civic[0].evidence_id == "politeuesthe-politeuma-colonial-resonance"
    assert civic[0].passage_relationship == "direct"
    assert "not reducing the exhortation to local politics" in civic[0].passage_relevance


def test_philippian_women_gifts_and_provenance_resist_speculative_identifications() -> None:
    library = CanonicalLibrary.load_default()
    women = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "Do inscriptions identify Euodia and Syntyche's offices and dispute?",
        "Philippians 4:2-3",
        "institution",
    )
    assert women[0].evidence_id == "women-public-roles-and-coworkers"
    assert women[0].passage_relationship == "comparative"
    assert "without deriving Christian offices from cults" in women[0].passage_relevance

    gift = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "Was the Philippians' gift patronage, friendship, or partnership?",
        "Philippians 4:10-20",
        "cultural practice",
    )
    assert gift[0].evidence_id == "gift-partnership-and-economic-range"
    assert "without assigning every gift to Lydia" in gift[0].passage_relevance

    provenance = _rank(
        library,
        "roman-philippi-colonial-civic-and-household-life",
        "Do praetorium and Caesar's household prove that Paul wrote from Rome?",
        "Philippians 1:13",
        "ancient text",
    )
    assert provenance[0].evidence_id == "praetorium-caesars-household-provenance-limit"
    assert "prevent praetorium from automatically meaning Rome's Praetorian Guard" in provenance[0].passage_relevance


def test_roman_claudian_and_jewish_evidence_preserves_scope_and_chronology() -> None:
    library = CanonicalLibrary.load_default()
    claudius = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Did Claudius expel every Jew because of Christ and Chrestus?",
        "Acts 18:1-3",
        "historical setting",
    )
    assert claudius[0].evidence_id == "claudian-action-and-chrestus"
    assert claudius[0].passage_relationship == "direct"
    assert "without turning Chrestus into unambiguous proof of Christ" in claudius[0].passage_relevance

    catacombs = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "What do later Monteverde Jewish catacomb inscriptions prove?",
        "Romans 9:1-11:36",
        "archaeology",
    )
    assert [item.evidence_id for item in catacombs[:2]] == [
        "roman-jewish-communities",
        "jewish-cemetery-inscriptions-later-control",
    ]
    assert catacombs[0].chronological_relation == "near-contemporary"
    assert catacombs[1].chronological_relation == "later-comparative"


def test_roman_people_and_group_evidence_resists_overconfident_biography() -> None:
    library = CanonicalLibrary.load_default()
    groupings = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "What do those of Aristobulus and Narcissus and the saints with Philologus reveal about multiple groupings?",
        "Romans 16:3-16",
        "ancient text",
    )
    assert groupings[0].evidence_id == "romans-16-multiple-gatherings"
    assert "without making every cluster a separate house church" in groupings[0].passage_relevance

    phoebe = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "What does the commendation call Phoebe diakonos prostatis sister and what probable carrier role follows?",
        "Romans 16:1-2",
        "literary convention",
    )
    assert phoebe[0].evidence_id == "phoebe-commendation-and-travel"
    assert "without treating a likely delivery role" in phoebe[0].passage_relevance

    coworkers = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "How did Prisca and Aquila travel from Corinth to Ephesus and teach Apollos?",
        "Acts 18:18-26",
        "ancient text",
    )
    assert coworkers[0].evidence_id == "prisca-aquila-mobility"
    assert "from becoming a complete biography" in coworkers[0].passage_relevance


def test_roman_authority_practice_and_worldview_evidence_remains_non_prescriptive() -> None:
    library = CanonicalLibrary.load_default()
    authority = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Does Romans 13 require obedience to every authoritarian government?",
        "Romans 12:14-13:10",
        "institution",
    )
    assert authority[0].evidence_id == "authorities-taxes-and-limited-inference"
    assert "prevent a blanket endorsement" in authority[0].passage_relevance

    practices = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Were the weak and strong simply Jews and gentiles?",
        "Romans 14:1-23",
        "cultural practice",
    )
    assert practices[0].evidence_id == "weak-strong-food-and-days"
    assert "without equating weak with Jews" in practices[0].passage_relevance

    imperial = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Does imperial cult make every gospel and Lord title an anti-Caesar polemic?",
        "Romans 1:1-17",
        "worldview",
    )
    assert imperial[0].evidence_id == "imperial-divine-honors-and-allegiance"
    assert imperial[0].evidence_type == "worldview-concept"
    assert "without decoding every title as a Caesar parody" in imperial[0].passage_relevance


def test_roman_custody_nero_and_apostolic_memory_stay_in_separate_layers() -> None:
    library = CanonicalLibrary.load_default()
    custody = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Can archaeology identify Paul's rented house or Mamertine prison?",
        "Acts 28:16-31",
        "archaeology",
        "institution",
    )
    assert custody[0].evidence_id == "acts-28-custody-and-rented-lodging"
    assert "blocks identification of the Mamertine Prison" in custody[0].passage_relevance

    nero = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Was Nero's persecution after the fire already the setting of Romans?",
        "Romans 8:17-39",
        "ancient text",
    )
    assert nero[0].evidence_id == "neronian-violence-after-romans"
    assert nero[0].chronological_relation == "later-comparative"
    assert "should not be treated as the original crisis" in nero[0].passage_relevance

    memory = _rank(
        library,
        "roman-rome-jewish-civic-household-and-imperial-life",
        "Does 1 Clement identify Peter and Paul's tombs and exact deaths?",
        "Acts 28:30-31",
        "ancient text",
    )
    assert memory[0].evidence_id == "peter-paul-memory-and-sites"
    assert memory[0].chronological_relation == "later-comparative"


def test_roman_legacy_place_and_coworker_records_are_passage_specific() -> None:
    library = CanonicalLibrary.load_default()
    rome = library.objects_by_id["rome"]
    aquila = library.objects_by_id["aquila"]
    priscilla = library.objects_by_id["priscilla"]

    assert rome.scripture_references[0].reference == "Romans 1:7-15"
    assert rome.context_applicability["ancient_near_east"] is False
    assert "roman-rome-jewish-civic-household-and-imperial-life" in {
        relationship.id for relationship in rome.related_objects
    }
    expected_coworker_references = [
        "Acts 18:1-3",
        "Acts 18:18-26",
        "Romans 16:3-5",
        "1 Corinthians 16:19",
        "2 Timothy 4:19",
    ]
    assert [reference.reference for reference in aquila.scripture_references] == expected_coworker_references
    assert [reference.reference for reference in priscilla.scripture_references] == expected_coworker_references
    assert all(
        obj.context_applicability["ancient_near_east"] is False
        and obj.context_applicability["second_temple"] is True
        for obj in (rome, aquila, priscilla)
    )
    assert all(
        "Canonical historical orientation" not in source.title
        for obj in (rome, aquila, priscilla)
        for source in obj.sources
    )


def test_legacy_passages_and_context_applicability_are_cleaned() -> None:
    library = CanonicalLibrary.load_default()
    flood = library.objects_by_id["the-flood"]
    thessalonica = library.objects_by_id["thessalonica"]
    plagues = library.objects_by_id["plagues-of-egypt"]
    crossing = library.objects_by_id["red-sea-crossing"]
    wilderness = library.objects_by_id["wilderness-wandering"]
    judges_cycle = library.objects_by_id["judges-cycle"]
    canaan = library.objects_by_id["canaan"]
    dan = library.objects_by_id["dan"]
    shiloh = library.objects_by_id["shiloh"]
    merneptah = library.objects_by_id["merneptah-stele"]
    tabernacle = library.objects_by_id["tabernacle"]
    tabernacle_faq = library.objects_by_id["what-is-the-tabernacle"]
    sanctuary_theme = library.objects_by_id["sanctuary-theme"]
    black_obelisk = library.objects_by_id["black-obelisk"]
    lachish_reliefs = library.objects_by_id["lachish-reliefs"]
    fall_of_samaria = library.objects_by_id["fall-of-samaria"]
    assyrian_exile = library.objects_by_id["assyrian-exile-of-israel"]
    assyria = library.objects_by_id["assyria"]
    babylonian_chronicles = library.objects_by_id["babylonian-chronicles"]
    cyrus_cylinder = library.objects_by_id["cyrus-cylinder"]
    babylonian_exile = library.objects_by_id["babylonian-exile"]
    fall_of_jerusalem = library.objects_by_id["fall-of-jerusalem"]
    return_from_exile = library.objects_by_id["return-from-exile"]
    rebuilding_the_temple = library.objects_by_id["rebuilding-the-temple"]
    babylon = library.objects_by_id["babylon-1"]
    persia = library.objects_by_id["persia"]
    temple_warning = library.objects_by_id["temple-warning-inscription"]
    high_priesthood = library.objects_by_id["high-priesthood"]
    pharisees = library.objects_by_id["pharisees"]
    sadducees = library.objects_by_id["sadducees"]
    scribes = library.objects_by_id["scribes"]
    synagogue = library.objects_by_id["synagogue"]
    sanhedrin = library.objects_by_id["sanhedrin"]
    pilgrimage_road = library.objects_by_id["pilgrimage-road-in-jerusalem"]
    capernaum = library.objects_by_id["capernaum"]
    nazareth = library.objects_by_id["nazareth"]
    galilee = library.objects_by_id["galilee-1"]
    judea = library.objects_by_id["judea-1"]
    burial = library.objects_by_id["burial-of-jesus"]
    roman_governorship = library.objects_by_id["roman-governorship"]
    temple_tax = library.objects_by_id["temple-tax"]
    corinth = library.objects_by_id["corinth"]
    phoebe = library.objects_by_id["phoebe-of-cenchreae"]
    patronage = library.objects_by_id["patronage"]
    lords_supper = library.objects_by_id["lords-supper"]
    ephesus = library.objects_by_id["ephesus"]
    philippi = library.objects_by_id["philippi"]
    lydia = library.objects_by_id["lydia"]
    assert flood.scripture_references[0].reference == "Genesis 6:1-22"
    assert all(reference.reference != "Genesis 11:1-9" for reference in flood.scripture_references)
    assert thessalonica.scripture_references[0].reference == "Acts 17:1-9"
    assert all(
        not reference.reference.startswith(("Matthew", "Mark", "Luke", "John"))
        for reference in thessalonica.scripture_references
    )
    assert plagues.scripture_references[0].reference == "Exodus 5:1-5"
    assert crossing.scripture_references[0].reference == "Exodus 13:17-22"
    assert wilderness.scripture_references[0].reference == "Exodus 15:22-27"
    assert "Roman administration" not in plagues.ancient_near_east_context
    assert "Roman administration" not in crossing.ancient_near_east_context
    assert "Roman administration" not in judges_cycle.ancient_near_east_context
    assert judges_cycle.scripture_references[0].reference == "Judges 2:6-23"
    assert canaan.scripture_references[0].reference == "Genesis 12:5-9"
    assert dan.scripture_references[0].reference == "Judges 18:1-31"
    assert shiloh.scripture_references[0].reference == "Joshua 18:1-10"
    assert merneptah.scripture_references[0].reference == "Judges 1:1-36"
    assert tabernacle.scripture_references[0].reference == "Exodus 25:1-9"
    assert tabernacle_faq.scripture_references[0].reference == "Exodus 25:1-9"
    assert sanctuary_theme.scripture_references[0].reference == "Exodus 25:8-9"
    assert "Roman civic administration" not in tabernacle.ancient_near_east_context
    assert {
        "tabernacle-presence-access-and-mobility",
        "ancient-portable-sanctuaries-and-tabernacle-comparisons",
    } <= {relationship.id for relationship in tabernacle.related_objects}
    assert black_obelisk.scripture_references[0].reference == "2 Kings 9:1-37"
    assert "Greek, or Roman settings" not in black_obelisk.ancient_near_east_context
    assert lachish_reliefs.scripture_references[0].reference == "2 Kings 18:13-37"
    assert "CKL archaeology entry focused on" not in lachish_reliefs.summary
    assert fall_of_samaria.context_applicability["hebraic_worldview"] is True
    assert assyrian_exile.scripture_references[0].reference == "2 Kings 17:1-23"
    assert "Roman administration" not in assyrian_exile.ancient_near_east_context
    assert assyria.scripture_references[1].reference == "2 Kings 17:1-23"
    assert {
        "assyrian-deportation-and-provincial-incorporation",
        "assyrian-tribute-and-royal-representation",
    } <= {relationship.id for relationship in assyria.related_objects}
    assert babylonian_chronicles.scripture_references[0].reference == "2 Kings 24:8-17"
    assert "587/586" in fall_of_jerusalem.historical_context
    assert babylonian_exile.context_applicability["hebraic_worldview"] is True
    assert return_from_exile.scripture_references[0].reference == "2 Chronicles 36:22-23"
    assert rebuilding_the_temple.scripture_references[1].reference == "Ezra 3:1-13"
    assert cyrus_cylinder.context_applicability["second_temple"] is True
    assert "neither names Judah or Jerusalem" in cyrus_cylinder.historical_context
    assert {
        "babylonian-conquest-deportation-and-judean-diaspora",
        "persian-restoration-and-yehud-administration",
    } <= {relationship.id for relationship in babylon.related_objects}
    assert persia.scripture_references[0].reference == "2 Chronicles 36:22-23"
    assert all(
        not reference.reference.startswith(("Genesis", "Exodus", "Acts"))
        for reference in persia.scripture_references
    )
    assert "persian-restoration-and-yehud-administration" in {
        relationship.id for relationship in persia.related_objects
    }
    assert temple_warning.scripture_references[0].reference == "Acts 21:27-36"
    assert "House of David" not in temple_warning.summary
    assert "second-temple-priesthood-and-temple-authority" in {
        relationship.id for relationship in temple_warning.related_objects
    }
    assert high_priesthood.context_applicability["second_temple"] is True
    assert pharisees.scripture_references[0].reference == "Mark 7:1-23"
    assert sadducees.scripture_references[0].reference == "Matthew 22:23-33"
    assert scribes.scripture_references[1].reference == "Ezra 7:1-10"
    assert synagogue.scripture_references[0].reference == "Mark 1:21-28"
    assert sanhedrin.scripture_references[0].reference == "Mark 14:53-65"
    assert all(
        obj.context_applicability["second_temple"] is True
        for obj in (high_priesthood, pharisees, sadducees, scribes, synagogue, sanhedrin)
    )
    assert all(
        "Canonical Knowledge Library" not in {source.publisher for source in obj.sources}
        for obj in (pharisees, sadducees, scribes, synagogue, sanhedrin)
    )
    assert pilgrimage_road.scripture_references[0].reference == "Luke 19:28-48"
    assert "Tell Dan" not in pilgrimage_road.summary
    assert "judean-pilgrimage-taxation-and-roman-power" in {
        relationship.id for relationship in pilgrimage_road.related_objects
    }
    assert capernaum.scripture_references[0].reference == "Matthew 4:12-17"
    assert nazareth.scripture_references[1].reference == "Mark 6:1-6"
    assert galilee.title == "Galilee"
    assert judea.title == "Judea"
    assert burial.scripture_references[0].reference == "Matthew 27:57-61"
    assert roman_governorship.scripture_references[0].reference == "Matthew 27:1-26"
    assert temple_tax.scripture_references[0].reference == "Exodus 30:11-16"
    assert all(
        obj.context_applicability["second_temple"] is True
        for obj in (
            pilgrimage_road,
            capernaum,
            nazareth,
            galilee,
            judea,
            burial,
            roman_governorship,
            temple_tax,
        )
    )
    assert corinth.scripture_references[0].reference == "Acts 18:1-18"
    assert "Gospels" not in corinth.literary_context
    assert "roman-corinth-civic-household-and-association-life" in {
        relationship.id for relationship in corinth.related_objects
    }
    assert phoebe.scripture_references[0].reference == "Romans 16:1-2"
    assert len(phoebe.scripture_references) == 1
    assert patronage.scripture_references[0].reference == "Romans 16:1-2"
    assert lords_supper.scripture_references[0].reference == "Matthew 26:17-30"
    assert all(
        obj.context_applicability["second_temple"] is True
        for obj in (corinth, phoebe, patronage, lords_supper)
    )
    assert ephesus.scripture_references[0].reference == "Acts 18:18-28"
    assert all(
        not reference.reference.startswith(("Matthew", "Mark", "Luke", "John"))
        for reference in ephesus.scripture_references
    )
    assert ephesus.context_applicability["ancient_near_east"] is False
    assert ephesus.context_applicability["second_temple"] is True
    assert "roman-ephesus-civic-cultic-and-household-life" in {
        relationship.id for relationship in ephesus.related_objects
    }
    assert "textually disputed" in ephesus.summary
    assert philippi.scripture_references[0].reference == "Acts 16:11-15"
    assert all(
        not reference.reference.startswith(("Matthew", "Mark", "Luke", "John"))
        for reference in philippi.scripture_references
    )
    assert philippi.context_applicability["ancient_near_east"] is False
    assert philippi.context_applicability["second_temple"] is True
    assert "roman-philippi-colonial-civic-and-household-life" in {
        relationship.id for relationship in philippi.related_objects
    }
    assert any(
        "Caesarea Philippi" in item
        for item in philippi.hermeneutical_lens["common_misinterpretations"]
    )
    assert [reference.reference for reference in lydia.scripture_references] == [
        "Acts 16:14-15",
        "Acts 16:40",
    ]
    assert lydia.context_applicability["ancient_near_east"] is False
    assert "roman-philippi-colonial-civic-and-household-life" in {
        relationship.id for relationship in lydia.related_objects
    }
    assert all(
        "Canonical Knowledge Library" not in {source.publisher for source in obj.sources}
        for obj in (philippi, lydia)
    )

    context_fields = {
        "historical": "historical_context",
        "ancient_near_east": "ancient_near_east_context",
        "hebraic_worldview": "hebraic_worldview",
        "second_temple": "second_temple_context",
        "canonical": "canonical_context",
        "later_christian_reception": "later_christian_reception",
    }
    for obj in library.objects_by_id.values():
        for flag, field_name in context_fields.items():
            if obj.context_applicability[flag]:
                assert str(getattr(obj, field_name)).strip(), f"{obj.id}: {flag}"


def test_corpus_evidence_quality_metrics_have_no_structural_failures() -> None:
    library = CanonicalLibrary.load_default()
    report = audit_evidence(library.objects_by_id.values())
    assert report["evidence_count"] == 155
    assert report["evidence_with_primary_sources_count"] == 153
    assert report["evidence_with_academic_secondary_sources_count"] == 146
    assert report["evidence_with_chronology_count"] == 155
    assert report["evidence_with_passage_relevance_count"] == 155
    assert report["disputed_evidence_count"] == 144
    assert report["worldview_evidence_count"] == 11
    assert report["archaeology_linked_evidence_count"] == 24
    assert report["internal_source_only_evidence_count"] == 0
    assert report["missing_source_locator_count"] == 0
    assert report["missing_confidence_rationale_count"] == 0
    assert report["overbroad_context_applicability_count"] == 0
    assert report["error_count"] == 0
