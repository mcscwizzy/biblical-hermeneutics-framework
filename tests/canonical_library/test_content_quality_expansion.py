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
    "roman-athens-agora-cult-and-philosophy": 16,
    "roman-galatia-regions-roads-cities-and-audience": 19,
    "pauline-kinship-guardianship-slavery-and-inheritance": 19,
    "ritual-purity-and-communal-holiness": 20,
    "patronage-hospitality-and-debt": 20,
    "pauline-women-coworkers-prophecy-and-assembly-authority": 20,
    "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration": 23,
    "pauline-suffering-weakness-disability-healing-power-and-apostolic-legitimacy": 28,
    "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead": 30,
    "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order": 34,
    "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel": 40,
    "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status": 49,
    "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity": 50,
    "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance": 52,
    "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory": 54,
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


def test_athens_cluster_distinguishes_public_spaces_and_areopagus_uncertainty() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-athens-agora-cult-and-philosophy"]
    items = {item.id: item for item in cluster.evidence_items}
    assert {
        "acts-synagogue-agora-sequence",
        "classical-agora-mixed-public-space",
        "roman-athens-layered-urban-center",
        "areopagus-place-council-and-procedure-ambiguity",
    } <= set(items)
    assert items["classical-agora-mixed-public-space"].confidence == "high"
    assert "distinct Roman Agora" in items["classical-agora-mixed-public-space"].notes
    areopagus = items["areopagus-place-council-and-procedure-ambiguity"]
    assert areopagus.confidence == "medium"
    assert areopagus.dispute_status == "major_scholarly_disagreement"
    assert "formal criminal trial" in areopagus.passage_relevance


def test_athens_unknown_god_and_philosophical_comparisons_remain_bounded() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-athens-agora-cult-and-philosophy"]
    items = {item.id: item for item in cluster.evidence_items}
    altar = items["unknown-god-literary-comparanda"]
    assert altar.dispute_status == "identification_uncertainty"
    assert altar.scripture_references[0].temporal_relation == "later-comparative"
    assert "No exact singular" in altar.notes
    assert items["epicurean-gods-death-and-providence-comparison"].evidence_type == "worldview-concept"
    assert "simple atheism" in items["epicurean-gods-death-and-providence-comparison"].notes
    assert items["stoic-providence-and-aratean-poetry-comparison"].evidence_type == "worldview-concept"
    assert "neither simple endorsement" in items["stoic-providence-and-aratean-poetry-comparison"].scholarly_interpretation


def test_athens_poetry_speech_and_named_hearer_limits_are_explicit() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-athens-agora-cult-and-philosophy"]
    items = {item.id: item for item in cluster.evidence_items}
    poetry = items["aratus-offspring-quotation-and-first-clause-uncertainty"]
    assert poetry.confidence == "high"
    assert "Epimenides" in poetry.notes
    assert items["acts-speech-as-literary-composition"].confidence == "medium"
    assert "verbatim" in items["acts-speech-as-literary-composition"].notes
    hearers = items["dionysius-damaris-and-audience-limits"]
    assert hearers.evidence_type == "people-group"
    assert "not defined through a man" in hearers.notes
    assert "Pseudo-Dionysius" in hearers.notes


def test_athens_evidence_is_discoverable_by_passage_and_place_is_reviewable() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Acts 17:22-34", limit=30)
    }
    assert "athens" in passage_objects
    assert "roman-athens-agora-cult-and-philosophy" in passage_objects
    ranked = _rank(
        library,
        "roman-athens-agora-cult-and-philosophy",
        "What can be known about Dionysius, Damaris, and the resurrection response?",
        "Acts 17:32-34",
        "historical setting",
        "direct textual explanation",
    )
    assert ranked[0].evidence_id == "dionysius-damaris-and-audience-limits"
    assert ranked[0].passage_relationship == "direct"
    athens = library.objects_by_id["athens"]
    assert athens.title == "Roman Athens"
    assert athens.content_status == "complete"
    assert athens.context_applicability["ancient_near_east"] is False
    assert any(
        "Mars Hill" in item
        for item in athens.hermeneutical_lens["common_misinterpretations"]
    )
    assert "roman-athens-agora-cult-and-philosophy" in {
        relationship.id for relationship in athens.related_objects
    }


def test_galatia_cluster_distinguishes_province_roads_and_city_status() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-galatia-regions-roads-cities-and-audience"]
    items = {item.id: item for item in cluster.evidence_items}
    assert {
        "roman-province-and-ethnic-galatia",
        "via-sebaste-material-road-network",
        "pisidian-antioch-colony-and-road-center",
        "iconium-regional-and-civic-ambiguity",
        "lystra-roman-colony-and-local-diversity",
        "derbe-name-and-site-identification-limits",
    } <= set(items)
    assert items["via-sebaste-material-road-network"].confidence == "high"
    assert "not a GPS record" in items["via-sebaste-material-road-network"].notes
    assert items["iconium-regional-and-civic-ambiguity"].dispute_status == "major_scholarly_disagreement"
    assert items["derbe-name-and-site-identification-limits"].dispute_status == "identification_uncertainty"
    assert "uniform" in items["lystra-roman-colony-and-local-diversity"].scholarly_interpretation


def test_galatia_cluster_bounds_lystra_language_cult_disability_and_violence() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-galatia-regions-roads-cities-and-audience"]
    items = {item.id: item for item in cluster.evidence_items}
    language = items["lycaonian-language-and-multilingual-interaction"]
    cult = items["lystra-zeus-hermes-and-sacrifice-comparanda"]
    healing = items["lystra-healing-disability-and-agency"]
    violence = items["lystra-crowd-reversal-and-stoning-limits"]
    assert language.confidence == "medium"
    assert "primitiveness" in language.passage_relevance
    assert cult.evidence_type == "worldview-concept"
    assert cult.dispute_status == "major_scholarly_disagreement"
    assert "Ovid" in cult.notes
    assert healing.evidence_type == "person"
    assert "forced healing" in healing.notes
    assert "unanimous crowd" in violence.notes


def test_galatia_destination_audience_illness_and_itinerary_remain_disputed() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["roman-galatia-regions-roads-cities-and-audience"]
    items = {item.id: item for item in cluster.evidence_items}
    destination = items["north-south-galatia-destination-dispute"]
    audience = items["galatians-plural-assemblies-and-demographic-limits"]
    weakness = items["galatians-bodily-weakness-and-route-diagnosis-limits"]
    comparison = items["acts-and-galatians-distinct-itinerary-witnesses"]
    assert destination.dispute_status == "major_scholarly_disagreement"
    assert "no city" in destination.description
    assert "not a uniform ethnic or social type" in audience.notes
    assert "malaria" in weakness.notes
    assert comparison.dispute_status == "major_scholarly_disagreement"
    assert "harmonization" in comparison.notes


def test_galatia_evidence_is_discoverable_and_place_record_controls_overreach() -> None:
    library = CanonicalLibrary.load_default()
    passage_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference("Acts 14:8-20", limit=40)
    }
    assert "galatia" in passage_objects
    assert "roman-galatia-regions-roads-cities-and-audience" in passage_objects
    ranked = _rank(
        library,
        "roman-galatia-regions-roads-cities-and-audience",
        "Why did the Lystra crowd call Barnabas Zeus and Paul Hermes?",
        "Acts 14:11-18",
        "historical setting",
        "worldview",
    )
    ranked_by_id = {item.evidence_id: item for item in ranked}
    assert "lystra-zeus-hermes-and-sacrifice-comparanda" in ranked_by_id
    assert ranked_by_id["lystra-zeus-hermes-and-sacrifice-comparanda"].passage_relationship == "direct"
    galatia = library.objects_by_id["galatia"]
    assert galatia.title == "Roman and Ethnic Galatia"
    assert galatia.content_status == "complete"
    assert galatia.context_applicability["ancient_near_east"] is False
    assert "roman-galatia-regions-roads-cities-and-audience" in {
        relationship.id for relationship in galatia.related_objects
    }
    assert any(
        "uniform" in item
        for item in galatia.hermeneutical_lens["common_misinterpretations"]
    )


def test_pauline_kinship_cluster_bounds_paidagogos_guardians_and_roman_law() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-kinship-guardianship-slavery-and-inheritance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    assert {
        "paidagogos-household-role",
        "minor-heir-analogy",
        "guardians-and-estate-managers",
        "father-appointed-time",
        "roman-adoption-bounded-comparison",
    } <= set(items)
    assert "modern schoolteacher" in items["paidagogos-household-role"].notes
    guardians = items["guardians-and-estate-managers"]
    assert guardians.confidence == "medium"
    assert guardians.dispute_status == "major_scholarly_disagreement"
    assert guardians.scripture_references[0].temporal_relation == "later-comparative"
    adoption = items["roman-adoption-bounded-comparison"]
    assert all(
        link.temporal_relation == "later-comparative"
        for link in adoption.scripture_references
    )
    assert "modern welfare-centered adoption" in adoption.notes


def test_pauline_kinship_cluster_preserves_status_slavery_and_torah_ethics() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-kinship-guardianship-slavery-and-inheritance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    status = items["galatians-status-triad"]
    slavery = items["slave-son-heir-and-real-slavery"]
    torah = items["torah-temporality-and-anti-jewish-limits"]
    assert status.dispute_status == "major_scholarly_disagreement"
    assert "erase race" in status.notes
    assert "historical abolition" in slavery.passage_relevance
    assert "trafficking" in slavery.notes
    assert "anti-Jewish" in torah.title
    assert "Judaism is primitive" in torah.notes


def test_pauline_kinship_cluster_keeps_abba_suffering_and_adoption_embodied() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-kinship-guardianship-slavery-and-inheritance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    abba = items["abba-bilingual-prayer"]
    suffering = items["coheirs-suffering-and-safeguarding"]
    embodied = items["creation-groaning-and-bodily-adoption"]
    comparison = items["distinct-pauline-metaphor-networks"]
    assert "Daddy" in abba.passage_relevance
    assert {link.reference for link in abba.scripture_references} == {
        "Mark 14:36",
        "Galatians 4:6",
        "Romans 8:15",
    }
    assert "safeguarding" in suffering.notes
    assert "redemption of the body" in embodied.primary_observation
    assert embodied.evidence_type == "worldview-concept"
    assert "universal Roman family-law system" in comparison.passage_relevance


def test_pauline_kinship_cluster_is_discoverable_and_cross_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = "pauline-kinship-guardianship-slavery-and-inheritance"
    galatians_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference(
            "Galatians 4:1-7", limit=40
        )
    }
    romans_objects = {
        result.object.id
        for result in library.retrieve_by_scripture_reference(
            "Romans 8:12-25", limit=40
        )
    }
    assert cluster_id in galatians_objects
    assert cluster_id in romans_objects
    ranked = _rank(
        library,
        cluster_id,
        "What did a paidagogos do, and was that person a modern teacher?",
        "Galatians 3:24-25",
        "historical setting",
        "lexical evidence",
    )
    ranked_by_id = {item.evidence_id: item for item in ranked}
    assert "paidagogos-household-role" in ranked_by_id
    assert ranked_by_id["paidagogos-household-role"].passage_relationship == "comparative"
    assert cluster_id in {
        relationship.id
        for relationship in library.objects_by_id["galatians"].related_objects
    }
    assert cluster_id in {
        relationship.id
        for relationship in library.objects_by_id["romans"].related_objects
    }
    assert cluster_id in {
        relationship.id
        for relationship in library.objects_by_id["adoption"].related_objects
    }


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


def test_mark_7_retrieval_preserves_handwashing_and_syntax_dispute() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "ritual-purity-and-communal-holiness",
        "Does Mark 7 abolish Jewish food law, or address handwashing and defilement?",
        "Mark 7:1-23",
        "second temple",
        "literary convention",
    )
    items = {item.evidence_id: item for item in ranked}
    assert {"mark-handwashing-trigger", "mark-7-19-syntax-dispute"} <= set(items)
    syntax = items["mark-7-19-syntax-dispute"]
    assert syntax.confidence == "low"
    assert syntax.dispute_status == "major_scholarly_disagreement"
    cluster_items = {
        item.id: item
        for item in library.objects_by_id[
            "ritual-purity-and-communal-holiness"
        ].evidence_items
    }
    assert "rather than deciding a modern diet" in cluster_items[syntax.evidence_id].notes


def test_acts_vision_and_decree_retrieval_keeps_people_and_variants_visible() -> None:
    library = CanonicalLibrary.load_default()
    vision = _rank(
        library,
        "ritual-purity-and-communal-holiness",
        "How does Acts interpret the animal vision through people, hospitality, and Spirit?",
        "Acts 10:24-48",
        "cultural practice",
        "historical setting",
    )
    assert vision[0].evidence_id == "acts-people-hospitality-spirit"
    assert "gentile persons" in vision[0].passage_relevance

    decree = _rank(
        library,
        "ritual-purity-and-communal-holiness",
        "What textual variants and legal backgrounds affect the apostolic decree?",
        "Acts 15:19-29",
        "manuscript",
        "second temple",
    )
    assert decree[0].evidence_id == "apostolic-decree-forms-and-backgrounds"
    assert decree[0].dispute_status == "textual_variant"
    cluster_items = {
        item.id: item
        for item in library.objects_by_id[
            "ritual-purity-and-communal-holiness"
        ].evidence_items
    }
    assert "later manuscript" in cluster_items[decree[0].evidence_id].notes


def test_romans_14_retrieval_limits_group_labels_and_food_coercion() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "ritual-purity-and-communal-holiness",
        "Were the Romans 14 groups simply Jews and gentiles, and may someone be forced to eat?",
        "Romans 14:1-23",
        "cultural practice",
    )
    items = {item.evidence_id: item for item in ranked}
    assert {"romans-practices-identity-limits", "romans-conscience-noncoercion"} <= set(items)
    assert "Blocks automatic equations" in items["romans-practices-identity-limits"].passage_relevance
    cluster_items = {
        item.id: item
        for item in library.objects_by_id[
            "ritual-purity-and-communal-holiness"
        ].evidence_items
    }
    assert "must not be coerced" in cluster_items["romans-conscience-noncoercion"].notes


def test_corinth_retrieval_distinguishes_cult_market_home_and_later_comparison() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "ritual-purity-and-communal-holiness",
        "How does First Corinthians distinguish idol temples, market meat, and private meals?",
        "1 Corinthians 10:14-33",
        "worldview",
        "cultural practice",
    )
    items = {item.evidence_id: item for item in ranked}
    assert {"corinth-idol-ontology-cultic-table", "corinth-market-home-disclosure"} <= set(items)
    sarapis = items["later-sarapis-meal-comparison"]
    assert sarapis.chronological_relation == "later-comparative"
    assert "later and non-Corinthian" in sarapis.passage_relevance


def test_food_cluster_rejects_universal_menu_and_is_bidirectionally_discoverable() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["ritual-purity-and-communal-holiness"]
    items = {item.id: item for item in cluster.evidence_items}
    safeguard = items["cross-passage-diet-code-limit"]
    assert "timeless diet rule" in safeguard.passage_relevance
    assert "not a prescribed modern diet" in safeguard.notes

    linked_ids = {"mark", "acts", "romans", "1-corinthians", "leviticus", "lords-supper"}
    for object_id in linked_ids:
        assert cluster.id in {
            relation.id
            for relation in library.objects_by_id[object_id].related_objects
        }


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


def test_pauline_economic_cluster_distinguishes_categories_rights_and_nonuse() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["patronage-hospitality-and-debt"]
    items = {item.id: item for item in cluster.evidence_items}
    categories = items["economic-categories-not-synonyms"]
    maintenance = items["corinthian-maintenance-right-and-nonuse"]
    assert categories.evidence_type == "worldview-concept"
    assert "master key" in categories.passage_relevance
    assert "right" in maintenance.description
    assert "nonuse" in maintenance.description
    assert "unpaid-labor mandate" in maintenance.notes


def test_pauline_collection_evidence_preserves_capacity_accountability_and_pressure() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["patronage-hospitality-and-debt"]
    items = {item.id: item for item in cluster.evidence_items}
    willingness = items["collection-willingness-capacity"]
    delegates = items["collection-delegates-accountability"]
    pressure = items["collection-readiness-shame-pressure"]
    cheerful = items["collection-cheerful-noncompulsion"]
    assert "what one has" in willingness.description
    assert "independent oversight" in delegates.notes
    assert "manipulated shame" in pressure.notes
    assert "guaranteed investment return" in cheerful.passage_relevance


def test_pauline_gift_and_labor_evidence_rejects_poverty_and_worker_harm() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["patronage-hospitality-and-debt"]
    items = {item.id: item for item in cluster.evidence_items}
    assert "neither romanticized nor prescribed" in items["macedonian-poverty-rhetoric"].notes
    assert "not medical neglect" in items["philippian-need-contentment"].notes
    assert items["thessalonian-community-work"].confidence == "low"
    assert "disability" in items["thessalonian-community-work"].notes
    assert "guaranteed financial return" in items["philippian-giving-receiving-account"].notes


def test_acts_economic_evidence_controls_trade_delegation_and_narrative_chronology() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id["patronage-hospitality-and-debt"]
    items = {item.id: item for item in cluster.evidence_items}
    workshop = items["acts-corinth-workshop"]
    return_party = items["acts-return-party-collection-limit"]
    farewell = items["acts-miletus-labor-support"]
    assert workshop.scripture_references[0].temporal_relation == "diachronic"
    assert "No exact material" in workshop.notes
    assert return_party.confidence == "low"
    assert "Plausibility is not identification" in return_party.notes
    assert "supported, not blamed" in farewell.notes


def test_pauline_economic_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "patronage-hospitality-and-debt",
        "How did Paul organize the Jerusalem collection without coercion?",
        "2 Corinthians 8:1-24",
        "historical institution",
        "worldview concept",
    )
    assert ranked[0].evidence_id in {
        "collection-willingness-capacity",
        "collection-delegates-accountability",
    }
    cluster = library.objects_by_id["patronage-hospitality-and-debt"]
    linked_books = {
        "romans",
        "1-corinthians",
        "2-corinthians",
        "philippians",
        "1-thessalonians",
        "acts",
    }
    assert linked_books <= {relation.id for relation in cluster.related_objects}
    for book_id in linked_books:
        assert cluster.id in {
            relation.id for relation in library.objects_by_id[book_id].related_objects
        }


def test_pauline_women_cluster_keeps_roles_and_later_offices_distinct() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-women-coworkers-prophecy-and-assembly-authority"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    roles = items["role-categories-not-synonyms"]
    phoebe = items["romans-phoebe-commendation"]
    junia = items["romans-junia-name-and-apostleship"]
    assert "own evidentiary weight" in roles.passage_relevance
    assert "later office" in phoebe.passage_relevance
    assert junia.confidence == "medium"
    assert "Gender and apostolic syntax are separate" in junia.notes


def test_corinthian_women_prophecy_speech_and_silence_evidence_is_textually_controlled() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-women-coworkers-prophecy-and-assembly-authority"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    speech = items["corinthian-women-pray-prophesy"]
    silence = items["corinthian-three-silence-contexts"]
    variant = items["corinthian-silence-textual-displacement"]
    control = items["corinthian-chapters-eleven-fourteen-control"]
    assert speech.confidence == "medium"
    assert "primary evidence" in speech.passage_relevance
    assert "three times" in silence.primary_observation
    assert variant.evidence_type == "manuscript"
    assert variant.dispute_status == "textual_variant"
    assert variant.scripture_references[0].temporal_relation == "later-comparative"
    assert "total speech ban" in control.passage_relevance


def test_pauline_women_cluster_blocks_gender_essentialism_and_clerical_immunity() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-women-coworkers-prophecy-and-assembly-authority"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    assert "gender essentialism" in items["corinthian-kephale-dispute"].notes
    assert "no immunity" in items["corinthian-prophecy-edification-testing"].notes
    assert "abuse" in items["corinthian-three-silence-contexts"].notes
    assert "coerced proximity" in items["philippian-reconciliation-role-limits"].notes


def test_acts_women_evidence_bounds_wealth_teaching_and_source_chronology() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-women-coworkers-prophecy-and-assembly-authority"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    lydia = items["acts-lydia-household-agency"]
    prisca = items["acts-prisca-aquila-instruction"]
    chronology = items["acts-letter-chronology-control"]
    assert lydia.confidence == "medium"
    assert "elite wealth" in lydia.passage_relevance
    assert "still teaching" in prisca.notes
    assert chronology.evidence_type == "historical-period"
    assert "Narrated event dates" in chronology.notes


def test_pauline_women_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "pauline-women-coworkers-prophecy-and-assembly-authority",
        "Did Paul command all women to be silent even though women prophesied?",
        "1 Corinthians 14:26-40",
        "literary context",
        "historical institution",
    )
    assert ranked[0].evidence_id in {
        "corinthian-three-silence-contexts",
        "corinthian-chapters-eleven-fourteen-control",
        "corinthian-silence-textual-displacement",
    }
    cluster = library.objects_by_id[
        "pauline-women-coworkers-prophecy-and-assembly-authority"
    ]
    linked_books = {"romans", "1-corinthians", "philippians", "acts"}
    assert linked_books <= {relation.id for relation in cluster.related_objects}
    for book_id in linked_books:
        assert cluster.id in {
            relation.id for relation in library.objects_by_id[book_id].related_objects
        }


def test_pauline_bodies_cluster_keeps_rhetoric_categories_and_identity_mapping_bounded() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    assert "own evidentiary weight" not in items["categories-remain-distinct"].passage_relevance
    assert "each passage" in items["categories-remain-distinct"].passage_relevance
    assert "Romans 1-3" in items["romans-vice-rhetoric-universal-turn"].passage_relevance
    identity = items["romans-same-sex-acts-identity-limit"]
    assert identity.evidence_type == "worldview-concept"
    assert identity.confidence == "medium"
    assert "LGBTQ dehumanization" in identity.passage_relevance


def test_corinthian_body_marriage_and_discipline_evidence_controls_consent_and_power() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    labels = items["corinthian-vice-labels-disputed"]
    marriage = items["corinthian-marriage-mutuality-consent"]
    mixed = items["corinthian-mixed-marriage-separation-safety"]
    assert labels.dispute_status == "lexical_uncertainty"
    assert "modern identity label" in labels.passage_relevance
    assert "marital rape" in marriage.notes
    assert "Protective separation" in mixed.notes
    assert "consent" in items["corinthian-incest-case-bounds"].passage_relevance
    assert "sex-worker stigma" in items["corinthian-prostitution-power-and-body"].passage_relevance


def test_pauline_discipline_evidence_ends_excess_without_erasing_safeguarding() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    identity = items["second-corinthians-offender-identity-limit"]
    comfort = items["second-corinthians-sufficient-discipline-comfort"]
    grief = items["second-corinthians-grief-repentance"]
    restoration = items["galatians-gentle-restoration-burdens"]
    assert identity.confidence == "medium"
    assert identity.scripture_references[1].relationship == "disputed"
    assert "automatic restoration" in comfort.passage_relevance
    assert "self-harm" in grief.notes
    assert "safeguarding" in restoration.passage_relevance


def test_acts_decree_evidence_preserves_gentile_inclusion_dispute_and_chronology() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    decree = items["acts-gentile-inclusion-decree"]
    porneia = items["acts-decree-porneia-legal-dispute"]
    chronology = items["acts-paul-chronology-control"]
    assert "complete sexuality code" in decree.passage_relevance
    assert porneia.confidence == "low"
    assert porneia.scripture_references[1].temporal_relation == "earlier-comparative"
    assert chronology.evidence_type == "historical-period"
    assert "Narrated event dates" in chronology.temporal_scope.notes


def test_pauline_bodies_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    ranked = _rank(
        library,
        "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration",
        "How should discipline lead to forgiveness and restoration without unsafe access?",
        "2 Corinthians 2:5-11",
        "historical institution",
        "worldview concept",
    )
    assert {
        "second-corinthians-sufficient-discipline-comfort",
    } <= {item.evidence_id for item in ranked[:3]}
    cluster = library.objects_by_id[
        "pauline-bodies-marriage-sexual-ethics-discipline-and-restoration"
    ]
    linked_books = {"romans", "1-corinthians", "2-corinthians", "galatians", "acts"}
    assert linked_books <= {relation.id for relation in cluster.related_objects}
    for book_id in linked_books:
        assert cluster.id in {
            relation.id for relation in library.objects_by_id[book_id].related_objects
        }


def test_pauline_suffering_cluster_distinguishes_weakness_disability_and_diagnosis() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-suffering-weakness-disability-healing-power-and-apostolic-legitimacy"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    assert items["categories-remain-distinct"].evidence_type == "worldview-concept"
    assert "generic suffering praise" in items["categories-remain-distinct"].passage_relevance
    thorn = items["thorn-diagnosis-limit"]
    galatians = items["galatians-illness-eyes-limit"]
    assert thorn.confidence == "medium"
    assert thorn.scripture_references[1].relationship == "disputed"
    assert "Speculative diagnoses" in thorn.notes
    assert "ophthalmia" in galatians.passage_relevance
    assert "diagnosing" in items["acts-letter-chronology-control"].passage_relevance


def test_pauline_suffering_cluster_rejects_coerced_harm_and_founder_immunity() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-suffering-weakness-disability-healing-power-and-apostolic-legitimacy"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    power = items["power-in-weakness-not-coercion"]
    signs = items["signs-authority-accountability"]
    leadership = items["leadership-hardship-not-immunity"]
    assert "escape" in power.passage_relevance
    assert "medical neglect" in power.notes
    assert "founder status" in signs.passage_relevance
    assert "Retaliation" in signs.notes
    assert "founder immunity" in leadership.passage_relevance
    assert leadership.confidence == "medium"


def test_pauline_suffering_cluster_controls_prison_labor_illness_and_crisis_care() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-suffering-weakness-disability-healing-power-and-apostolic-legitimacy"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    support = items["support-right-not-extraction"]
    prison = items["philippians-prison-life-death"]
    illness = items["epaphroditus-illness-recovery"]
    despair = items["despair-death-sentence-honesty"]
    assert "compulsory unpaid labor" in support.passage_relevance
    assert "self-harm risk" in prison.passage_relevance
    assert "forced-healing" in illness.passage_relevance
    assert "immediate competent support" in despair.notes


def test_pauline_suffering_cluster_bounds_acts_violence_recovery_and_advocacy() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-suffering-weakness-disability-healing-power-and-apostolic-legitimacy"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    damascus = items["acts-damascus-blindness-recovery"]
    lystra = items["acts-lystra-stoning-recovery"]
    philippi = items["acts-philippi-beating-custody-protest"]
    chronology = items["acts-letter-chronology-control"]
    assert "thorn" in damascus.passage_relevance
    assert lystra.scripture_references[1].relationship == "disputed"
    assert "legal protest" in philippi.passage_relevance
    assert "Narrated event dates" in chronology.temporal_scope.notes


def test_pauline_suffering_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-suffering-weakness-disability-healing-power-and-apostolic-legitimacy"
    )
    ranked = _rank(
        library,
        cluster_id,
        "What was Paul's thorn in the flesh, and does power in weakness require refusing care?",
        "2 Corinthians 12:7-10",
        "disability",
        "worldview concept",
    )
    assert {"thorn-diagnosis-limit", "power-in-weakness-not-coercion"} <= {
        item.evidence_id for item in ranked[:5]
    }
    cluster = library.objects_by_id[cluster_id]
    reciprocal_ids = {
        "1-corinthians",
        "2-corinthians",
        "galatians",
        "philippians",
        "acts",
        "apostleship",
        "theology-of-suffering",
        "theology-of-the-cross",
    }
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_resurrection_cluster_distinguishes_participation_death_and_proxy_baptism() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    categories = items["death-life-categories-distinct"]
    romans = items["romans-baptismal-participation"]
    proxy = items["baptism-for-dead-underdetermined"]
    assert categories.evidence_type == "worldview-concept"
    assert "suppressing grief" in categories.passage_relevance
    assert romans.scripture_references[1].relationship == "contrast"
    assert "proxy baptism" in romans.notes
    assert proxy.confidence == "low"
    assert proxy.certainty == "insufficient_evidence"
    assert proxy.assertion_type == "scholarly-reconstruction"
    assert "override consent" in proxy.notes


def test_pauline_resurrection_cluster_keeps_transformation_embodied_and_inclusive() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    spiritual = items["spiritual-body-spirit-animated"]
    flesh = items["flesh-blood-transformation"]
    diversity = items["created-body-diversity"]
    identity = items["embodied-identity-no-exclusion"]
    assert "anti-body dualism" in spiritual.passage_relevance
    assert "same noun soma" in spiritual.primary_observation
    assert "sex traits" in flesh.passage_relevance
    assert "binary" in diversity.passage_relevance
    assert identity.assertion_type == "secondary-evidence"
    assert "forced normalization" in identity.passage_relevance


def test_pauline_resurrection_cluster_preserves_grief_and_rejects_date_setting() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    grief = items["thessalonian-grief-with-hope"]
    parousia = items["thessalonian-parousia-sequence"]
    timing = items["thessalonian-day-no-date-setting"]
    assert "grief suppression" in grief.passage_relevance
    assert "Lament" in grief.notes
    assert "together language" in parousia.primary_observation
    assert "subsequent direction" in parousia.notes
    assert "failed predictions" in timing.passage_relevance
    assert "accountability" in timing.notes


def test_pauline_resurrection_cluster_labels_intermediate_state_and_acts_chronology() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    intermediate = items["second-corinthians-clothing-intermediate"]
    acts = items["acts-letter-chronology-resurrection"]
    assert intermediate.assertion_type == "scholarly-reconstruction"
    assert "explicit chronological chart" in intermediate.description
    assert "No single intermediate-state proposal" in intermediate.notes
    assert acts.evidence_type == "historical-period"
    assert "verbatim Pauline transcripts" in acts.passage_relevance
    assert "Narrated event dates" in acts.temporal_scope.notes


def test_pauline_resurrection_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-death-resurrection-transformed-embodiment-grief-hope-judgment-and-baptism-for-the-dead"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Does spiritual body mean disembodied, and what is baptism for the dead?",
        "1 Corinthians 15:29",
        "worldview concept",
        "cultural practice",
    )
    assert "baptism-for-dead-underdetermined" in {
        item.evidence_id for item in ranked[:5]
    }
    cluster = library.objects_by_id[cluster_id]
    reciprocal_ids = {
        "romans",
        "1-corinthians",
        "2-corinthians",
        "philippians",
        "1-thessalonians",
        "acts",
        "resurrection-theme",
        "resurrection-doctrine",
        "eschatology",
        "final-judgment",
    }
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_spirit_cluster_distinguishes_gifts_fruit_roles_and_healings() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    categories = items["spirit-categories-distinct"]
    distribution = items["corinthian-distributed-not-entitled"]
    fruit = items["galatian-fruit-communal-ethics"]
    healing = items["corinthian-healings-plural-limits"]
    assert categories.evidence_type == "worldview-concept"
    assert "compulsory hierarchy" in categories.passage_relevance
    assert "compulsory tongues" in distribution.passage_relevance
    assert "personality" in fruit.passage_relevance
    assert "guaranteed technique" in healing.title
    assert "medication withdrawal" in healing.passage_relevance


def test_pauline_spirit_cluster_controls_tongues_prophecy_and_order() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    tongues = items["corinthian-tongues-underdetermined"]
    interpretation = items["corinthian-interpretation-required"]
    prophecy = items["corinthian-prophecy-weighed"]
    order = items["corinthian-peace-order-not-suppression"]
    assert tongues.certainty == "disputed"
    assert "Acts 2" in tongues.passage_relevance
    assert "silence instructions" in interpretation.confidence_rationale
    assert "leader immunity" in prophecy.passage_relevance
    assert "suppress dissent" in order.passage_relevance


def test_pauline_spirit_cluster_preserves_indwelling_fruit_and_testing() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    romans = items["romans-indwelling-adoption-prayer"]
    flesh = items["galatian-flesh-spirit-not-body-hatred"]
    thessalonians = items["thessalonian-prophecy-test-hold"]
    assert "wordless" in romans.passage_relevance
    assert "medical neglect" in flesh.passage_relevance
    assert "automatic dismissal" in thessalonians.passage_relevance
    assert "evidence" in thessalonians.notes


def test_pauline_spirit_cluster_controls_acts_sequences_and_chronology() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    pentecost = items["acts-pentecost-languages-joel"]
    samaria = items["acts-samaria-power-not-for-sale"]
    sequences = items["acts-variable-reception-sequences"]
    chronology = items["acts-letters-chronology-spirit"]
    assert "multilingual" in pentecost.passage_relevance
    assert "selling" in samaria.passage_relevance
    assert len(sequences.scripture_references) == 4
    assert "verbatim Pauline manual" in chronology.passage_relevance
    assert "Narrated Acts dates" in chronology.temporal_scope.notes


def test_pauline_spirit_cluster_enforces_medical_and_reception_boundaries() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    medical = items["modern-medical-discernment-boundary"]
    reception = items["later-continuation-cessation-dispute"]
    assert medical.confidence == "high"
    assert "seizure" in medical.passage_relevance
    assert "qualified clinicians" in medical.notes
    assert reception.evidence_type == "historical-period"
    assert reception.certainty == "disputed"
    assert "modern system" in reception.passage_relevance


def test_pauline_spirit_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-spirit-gifts-tongues-prophecy-discernment-healing-worship-and-assembly-order"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Must every Christian speak in tongues, and how should prophecy be tested?",
        "1 Corinthians 14:26-33",
        "worldview concept",
        "cultural practice",
    )
    assert {"corinthian-prophecy-weighed", "corinthian-interpretation-required"} & {
        item.evidence_id for item in ranked[:6]
    }
    cluster = library.objects_by_id[cluster_id]
    reciprocal_ids = {
        "romans",
        "1-corinthians",
        "galatians",
        "1-thessalonians",
        "acts",
        "spirit-theme",
        "spiritual-gifts",
        "prophets",
        "worship-theme",
    }
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_israel_cluster_distinguishes_identity_justification_and_abraham() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    categories = items["pauline-identity-categories-distinct"]
    pistis = items["romans-justification-pistis-christou"]
    abraham = items["romans-abraham-father-both"]
    assert categories.evidence_type == "worldview-concept"
    assert "replacement ownership" in categories.passage_relevance
    assert pistis.certainty == "disputed"
    assert "faith in messiah" in pistis.scholarly_interpretation.lower()
    assert "dispossess" in abraham.passage_relevance


def test_pauline_israel_cluster_controls_election_olive_tree_and_all_israel() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    election = items["romans-election-scriptural-examples"]
    olive = items["romans-olive-root-anti-boast"]
    israel = items["romans-all-israel-disputed"]
    mercy = items["romans-mercy-all"]
    assert election.certainty == "disputed"
    assert "deterministic system" in election.passage_relevance
    assert "supersessionist" in olive.passage_relevance
    assert israel.confidence == "low"
    assert "No timetable" in israel.temporal_scope.notes
    assert "Christian superiority" in mercy.passage_relevance


def test_pauline_israel_cluster_preserves_torah_circumcision_and_jewish_identity() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    works = items["galatians-works-torah-scope"]
    pedagogue = items["galatians-torah-pedagogue"]
    identity = items["galatians-neither-jew-greek"]
    circumcision = items["galatians-gentile-circumcision-obligation"]
    assert "merit earning" in works.passage_relevance
    assert "childish" in pedagogue.passage_relevance
    assert "identity erasure" in identity.title
    assert "Neither cutting nor non-cutting" in circumcision.notes


def test_pauline_israel_cluster_bounds_calling_accommodation_and_polemic() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    calling = items["corinthians-circumcision-calling"]
    mission = items["corinthians-mission-accommodation"]
    philippians = items["philippians-israelite-polemic"]
    assert "forced surgical reversal" in calling.passage_relevance
    assert "colonial mimicry" in mission.passage_relevance
    assert "Paul's Jewish identity" in philippians.passage_relevance
    assert "ableist and antisemitic" in philippians.notes


def test_pauline_israel_cluster_controls_acts_chronology_and_modern_harm() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    chronology = items["acts-letters-chronology-israel"]
    reception = items["later-supersessionism-antisemitism-boundary"]
    body = items["circumcision-intersex-consent-boundary"]
    assert "verbatim Pauline transcript" in chronology.passage_relevance
    assert "Narrated event dates" in chronology.temporal_scope.notes
    assert "living Jewish communities" in reception.passage_relevance
    assert "nonconsensual intersex normalization" in body.passage_relevance
    assert "lawful consent" in body.notes


def test_pauline_israel_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-israel-jewish-gentile-relations-abraham-torah-circumcision-justification-faith-election-hardening-remnant-olive-tree-and-all-israel"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Does the olive tree mean the church replaced Israel, and who is all Israel?",
        "Romans 11:25-27",
        "worldview concept",
        "literary convention",
    )
    assert {"romans-all-israel-disputed", "romans-olive-root-anti-boast"} & {
        item.evidence_id for item in ranked[:6]
    }
    cluster = library.objects_by_id[cluster_id]
    reciprocal_ids = {
        "romans",
        "galatians",
        "1-corinthians",
        "philippians",
        "acts",
        "abraham",
        "torah",
        "justification",
        "faith",
        "covenant-theme",
    }
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_food_cluster_distinguishes_ontology_participation_and_venues() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    ontology = items["corinth-idol-and-one-god-confession"]
    tables = items["corinth-incompatible-cups-tables"]
    market = items["corinth-market-food-case"]
    private = items["corinth-private-host-case"]
    assert "cultic participation" in ontology.passage_relevance
    assert "ordinary market purchase" in tables.passage_relevance
    assert "all or most meat" in market.temporal_scope.notes
    assert "freedom not to attend" in private.passage_relevance


def test_pauline_food_cluster_preserves_conscience_love_and_noncoercion() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    conscience = items["syneidesis-awareness-self-perception"]
    love = items["corinth-knowledge-love-known"]
    weak = items["corinth-former-idol-association"]
    harm = items["corinth-destroyed-sibling-wounded-conscience"]
    assert conscience.certainty == "disputed"
    assert "infallible inner oracle" in conscience.passage_relevance
    assert "override" in love.passage_relevance
    assert "stupid" in weak.passage_relevance
    assert "blank check" in harm.notes


def test_pauline_food_cluster_limits_weak_strong_labels_and_accommodation() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    identities = items["romans-practice-labels-identity-limit"]
    strong = items["romans-strong-bear-upbuild"]
    accommodation = items["corinth-bounded-mission-accommodation"]
    assert "equating weak with Jews" in identities.passage_relevance
    assert "demanding that vulnerable people adapt" in strong.passage_relevance
    assert "colonial mimicry" in accommodation.passage_relevance
    assert "transparency and consent" in accommodation.temporal_scope.notes


def test_pauline_food_cluster_keeps_supper_tradition_and_economic_rebuke_together() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    hunger = items["corinth-own-meal-hunger-intoxication"]
    humiliation = items["corinth-humiliating-have-nots"]
    tradition = items["corinth-received-supper-tradition"]
    manner = items["corinth-unworthy-manner-grammar"]
    body = items["corinth-discern-body-views"]
    assert "material inequality" in hunger.passage_relevance
    assert "poverty and class humiliation" in humiliation.passage_relevance
    assert "economic rebuke" in tradition.passage_relevance
    assert "unworthy-person category" in manner.passage_relevance
    assert body.certainty == "disputed"


def test_pauline_food_cluster_controls_acts_chronology_and_modern_access() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    chronology = items["acts-pauline-letters-chronology"]
    access = items["modern-access-care-table-boundary"]
    illness = items["corinth-sickness-death-causation-limit"]
    assert "silently overwriting" in chronology.passage_relevance
    assert "Narrated dates" in chronology.temporal_scope.notes
    assert "allergy" in access.description.lower()
    assert "safe alternatives" in access.notes
    assert "Rejects blaming sick" in illness.passage_relevance


def test_pauline_food_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-idols-sacrificed-food-market-temple-meals-conscience-knowledge-love-weak-strong-stumbling-participation-lords-supper-shared-table-and-economic-status"
    )
    ranked = _rank(
        library,
        cluster_id,
        "How are idol temple dining, market meat, and a private invitation different?",
        "1 Corinthians 10:14-30",
        "cultural practice",
        "institution",
    )
    assert {"corinth-market-food-case", "corinth-private-host-case", "corinth-incompatible-cups-tables"} & {
        item.evidence_id for item in ranked[:8]
    }
    cluster = library.objects_by_id[cluster_id]
    reciprocal_ids = {
        "romans",
        "1-corinthians",
        "galatians",
        "acts",
        "lords-supper",
        "ritual-purity-and-communal-holiness",
        "worship-theme",
        "household",
        "patronage",
    }
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_economics_cluster_keeps_support_rights_and_nonuse_together() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    rights = items["first-corinth-apostolic-rights"]
    nonuse = items["first-corinth-nonuse-avoid-obstacle"]
    thess = items["second-thess-example-right-not-burden"]
    assert "compensation" in rights.passage_relevance
    assert "compulsory unpaid labor" in nonuse.passage_relevance
    assert "retain a right" in thess.description
    assert "employers cannot impose" in nonuse.notes


def test_pauline_economics_cluster_distinguishes_unwillingness_from_inability() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    maxim = items["second-thess-unwilling-not-unable"]
    good = items["second-thess-do-not-weary-good"]
    sibling = items["second-thess-sibling-not-enemy"]
    assert "unable" in maxim.description
    assert "disabled" in maxim.passage_relevance
    assert "mutual aid" in good.passage_relevance
    assert "permanent ostracism" in sibling.passage_relevance


def test_pauline_economics_cluster_limits_collection_pressure_by_capacity_and_consent() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    capacity = items["second-corinth-readiness-according-has"]
    equality = items["second-corinth-relief-equality-not-affliction"]
    consent = items["second-corinth-heart-not-compulsion"]
    pressure = items["second-corinth-readiness-boasting-pressure"]
    assert "borrowing" in capacity.passage_relevance
    assert "enforced destitution" in equality.passage_relevance
    assert "compulsory tithes" in consent.passage_relevance
    assert "private no" in pressure.notes


def test_pauline_economics_cluster_requires_shared_and_honorable_administration() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    carriers = items["first-corinth-approved-carriers-letters"]
    delegates = items["second-corinth-titus-brothers-administration"]
    honor = items["second-corinth-avoid-blame-honorable"]
    assert "shared custody" in carriers.passage_relevance
    assert "multiple accountable agents" in delegates.passage_relevance
    assert "independent review" in honor.notes


def test_pauline_economics_cluster_rejects_prosperity_extraction_and_controls_acts() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    sowing = items["second-corinth-sowing-reaping-metaphor"]
    philippians = items["philippians-gift-sacrifice-provision"]
    acts = items["acts-ephesian-farewell-hands-weak"]
    modern = items["modern-worker-donor-governance-boundary"]
    assert "investment contract" in sowing.passage_relevance
    assert "donor-return promises" in philippians.passage_relevance
    assert acts.scripture_references[0].temporal_relation == "diachronic"
    assert "direct-letter rights" in acts.passage_relevance
    assert "restricted funds" in modern.description
    assert "United States example" in modern.temporal_scope.notes


def test_pauline_economics_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-work-labor-wages-maintenance-poverty-wealth-collection-giving-reciprocity-equality-partnership-idleness-need-and-economic-solidarity"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Was Paul's collection voluntary, capacity-sensitive, and transparently administered?",
        "2 Corinthians 8:1-9:15",
        "cultural practice",
        "institution",
    )
    assert {
        "second-corinth-readiness-according-has",
        "second-corinth-heart-not-compulsion",
        "second-corinth-titus-brothers-administration",
        "second-corinth-avoid-blame-honorable",
    } & {item.evidence_id for item in ranked[:10]}
    cluster = library.objects_by_id[cluster_id]
    reciprocal_ids = {
        "1-thessalonians",
        "2-thessalonians",
        "1-corinthians",
        "2-corinthians",
        "romans",
        "philippians",
        "acts",
        "apostleship",
        "patronage",
        "diaconate",
        "household",
        "patronage-hospitality-and-debt",
    }
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_politics_cluster_bounds_authority_by_enemy_care_love_and_nonharm() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    unit = items["romans-unit-blessing-through-love"]
    submission = items["romans-every-person-submit"]
    rulers = items["romans-rulers-good-evil-claim"]
    sword = items["romans-sword-coercive-power"]
    assert "one sustained exhortation" in unit.description
    assert "worship" in submission.passage_relevance
    assert "empirical guarantee" in rulers.passage_relevance
    assert "no use-of-force policy" in sword.notes


def test_pauline_politics_cluster_does_not_hide_abuse_inside_church_mediation() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    dispute = items["corinth-lawsuits-insider-dispute"]
    boundary = items["corinth-mediation-reporting-boundary"]
    assert "mandatory reporting" in dispute.passage_relevance
    assert "voluntary" in boundary.passage_relevance
    assert "Never force mediation" in boundary.notes


def test_pauline_politics_cluster_keeps_imperial_and_warfare_images_nonliteral() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    triumph = items["corinth-triumph-procession-ambiguity"]
    warfare = items["corinth-warfare-not-fleshly"]
    strongholds = items["corinth-strongholds-arguments"]
    armor = items["thess-ethical-armor"]
    assert "captive" in triumph.passage_relevance
    assert "literal militarization" in warfare.passage_relevance
    assert "People are not strongholds" in strongholds.notes
    assert "Metaphorical defense does not authorize attack" in armor.notes


def test_pauline_politics_cluster_preserves_civic_resonance_and_imperial_disputes() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    conduct = items["philippians-live-as-citizens-worthy"]
    commonwealth = items["philippians-heavenly-commonwealth"]
    household = items["philippians-caesar-household-limit"]
    peace = items["thess-peace-security-disputed"]
    assert "Roman colony" in conduct.passage_relevance
    assert "statelessness romanticization" in commonwealth.passage_relevance
    assert "Roman provenance certainty" in household.passage_relevance
    assert "without treating" in peace.passage_relevance
    assert peace.dispute_status != "consensus"


def test_pauline_politics_cluster_controls_acts_chronology_and_modern_rights() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    prison = items["philippians-prison-praetorium-uncertain"]
    philippi = items["acts-philippi-beating-custody-rights"]
    custody = items["acts-citizenship-hearings-appeal-custody"]
    modern = items["modern-political-detention-safeguard"]
    assert "not approval of prison conditions" in prison.notes
    assert philippi.scripture_references[0].temporal_relation == "diachronic"
    assert "status-dependent" in custody.notes
    assert "statelessness" in modern.description
    assert "current law" in modern.notes


def test_pauline_politics_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-governing-authorities-citizenship-empire-taxation-public-order-courts-peace-nonretaliation-violence-armor-triumph-imprisonment-civic-rights-and-political-allegiance"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Does Romans 13 require unconditional obedience and approve every use of state violence?",
        "Romans 12:14-13:14",
        "cultural practice",
        "institution",
    )
    assert {
        "romans-unit-blessing-through-love",
        "romans-every-person-submit",
        "romans-rulers-good-evil-claim",
        "romans-sword-coercive-power",
    } & {item.evidence_id for item in ranked[:10]}
    reciprocal_ids = {
        "romans",
        "1-corinthians",
        "2-corinthians",
        "philippians",
        "1-thessalonians",
        "acts",
        "roman-rome-jewish-civic-household-and-imperial-life",
        "roman-corinth-civic-household-and-association-life",
        "roman-philippi-colonial-civic-and-household-life",
        "thessalonian-civic-and-funerary-context",
        "roman-citizenship-and-legal-process",
        "peace-theme",
    }
    cluster = library.objects_by_id[cluster_id]
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_mission_cluster_preserves_letter_first_chronology() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-mission-proclamation-travel-coworkers-letters-messengers-hospitality-house-assemblies-synagogues-marketplaces-adaptability-church-planting-and-interassembly-networks"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    galatians = items["galatians-call-independent-chronology"]
    acts = items["acts-galatians-chronology-control"]
    farewell = items["acts-miletus-farewell-later-witness"]
    assert "earlier direct letter" in galatians.passage_relevance
    assert acts.scripture_references[0].temporal_relation == "diachronic"
    assert "forcing every visit" in acts.passage_relevance
    assert "not a verbatim transcript" in farewell.passage_relevance


def test_pauline_mission_cluster_preserves_coworker_and_womens_agency() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-mission-proclamation-travel-coworkers-letters-messengers-hospitality-house-assemblies-synagogues-marketplaces-adaptability-church-planting-and-interassembly-networks"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    phoebe = items["romans-phoebe-recommendation"]
    women = items["romans-women-laborers"]
    apollos = items["corinth-apollos-agency"]
    coworkers = items["philippians-euodia-syntyche-coworkers"]
    assert "likely letter-carrier role as an inference" in phoebe.passage_relevance
    assert "male-only" in women.passage_relevance
    assert "decline" in apollos.passage_relevance
    assert "mission agency" in coworkers.passage_relevance


def test_pauline_mission_cluster_bounds_adaptability_and_conversion_by_consent() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-mission-proclamation-travel-coworkers-letters-messengers-hospitality-house-assemblies-synagogues-marketplaces-adaptability-church-planting-and-interassembly-networks"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    adaptation = items["corinth-bounded-adaptability"]
    household = items["acts-household-baptism-consent-gap"]
    modern = items["modern-religious-consent"]
    assert "deceptive identity" in adaptation.passage_relevance
    assert "forced baptism" in household.passage_relevance
    assert "aid-conditioned belief" in modern.passage_relevance
    assert "decline belief" in modern.notes


def test_pauline_mission_cluster_limits_hospitality_travel_and_hardship_pressure() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-mission-proclamation-travel-coworkers-letters-messengers-hospitality-house-assemblies-synagogues-marketplaces-adaptability-church-planting-and-interassembly-networks"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    lydia = items["acts-lydia-hospitality-boundary"]
    illness = items["philippians-epaphroditus-envoy-illness"]
    danger = items["corinth-travel-hardship-catalogue"]
    travel = items["modern-travel-migration-safety"]
    assert "right to withdraw access" in lydia.notes
    assert "medical care" in illness.notes
    assert "loyalty test" in danger.notes
    assert "unpenalized right to pause or leave" in travel.passage_relevance


def test_pauline_mission_cluster_requires_fair_support_access_and_accountability() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-mission-proclamation-travel-coworkers-letters-messengers-hospitality-house-assemblies-synagogues-marketplaces-adaptability-church-planting-and-interassembly-networks"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    support = items["corinth-support-right-nonuse"]
    domination = items["corinth-paul-not-lord-faith"]
    access = items["modern-fair-support-accessibility"]
    colonial = items["modern-anticolonial-local-accountability"]
    assert "unpaid ministry compulsory" in support.passage_relevance
    assert "founder domination" in domination.passage_relevance
    assert "communication access" in access.passage_relevance
    assert "founder or apostolic immunity" in colonial.passage_relevance


def test_pauline_mission_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-mission-proclamation-travel-coworkers-letters-messengers-hospitality-house-assemblies-synagogues-marketplaces-adaptability-church-planting-and-interassembly-networks"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Did Phoebe carry Romans, and did Paul control coworkers and house assemblies?",
        "Romans 16:1-16",
        "cultural practice",
        "institution",
    )
    assert {
        "romans-phoebe-recommendation",
        "romans-prisca-aquila-house",
        "romans-women-laborers",
        "romans-multiple-house-groups",
    } & {item.evidence_id for item in ranked[:10]}
    reciprocal_ids = {
        "romans",
        "1-corinthians",
        "2-corinthians",
        "galatians",
        "philippians",
        "1-thessalonians",
        "acts",
        "phoebe-of-cenchreae",
        "priscilla",
        "lydia",
        "apostleship",
        "household",
        "patronage-hospitality-and-debt",
    }
    cluster = library.objects_by_id[cluster_id]
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_conflict_cluster_preserves_letter_first_chronology_and_missing_voices() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    sexual_case = items["corinth-reported-sexual-case"]
    antioch = items["antioch-public-confrontation-limit"]
    council = items["acts-council-later-comparator"]
    rupture = items["acts-coworker-rupture-unresolved"]
    assert "woman is not addressed" in sexual_case.description
    assert "only Paul's retrospective account" in antioch.description
    assert council.scripture_references[0].temporal_relation == "diachronic"
    assert "not a verbatim meeting record" in council.scholarly_interpretation
    assert "safe separation" in rupture.passage_relevance


def test_pauline_conflict_cluster_makes_discipline_proportionate_and_revisable() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    removal = items["corinth-mourning-removal-dispute"]
    majority = items["majority-punishment-evidence-gap"]
    forgiveness = items["forgive-comfort-excess-grief"]
    reaffirm = items["reaffirm-love-revisable-boundary"]
    assert removal.confidence == "low"
    assert "permanent expulsion" in removal.passage_relevance
    assert "minority" in majority.description
    assert "proportionality" in forgiveness.passage_relevance
    assert "reviewable action" in reaffirm.passage_relevance


def test_pauline_conflict_cluster_rejects_apostolic_immunity_and_humiliation() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    domination = items["corinth-not-lord-faith"]
    signs = items["signs-no-apostolic-immunity"]
    irony = items["apostolic-irony-status"]
    confrontation = items["antioch-public-confrontation-limit"]
    assert "apostolic immunity" in domination.passage_relevance
    assert "independent review" in signs.passage_relevance
    assert "demanding apostolic misery" in irony.notes
    assert "humiliation" in confrontation.passage_relevance


def test_pauline_conflict_cluster_separates_forgiveness_reconciliation_and_contact() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    modern = items["modern-forgiveness-not-forced-reconciliation"]
    access = items["modern-access-restoration-without-contact"]
    grief = items["grief-repentance-causation-limit"]
    assert "different timelines" in modern.description
    assert "no joint meeting" in modern.passage_relevance
    assert "no forced encounter" in access.passage_relevance
    assert "not a harm method" in grief.title


def test_pauline_conflict_cluster_requires_safe_reporting_due_process_and_access() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    confidentiality = items["modern-confidentiality-not-concealment"]
    process = items["modern-due-process-proportion-review"]
    trauma = items["modern-trauma-aware-communication"]
    reporting = items["modern-independent-reporting-nonretaliation"]
    access = items["modern-access-restoration-without-contact"]
    assert "institutional reputation" in confidentiality.notes
    assert "appeal" in process.passage_relevance
    assert "retraumatization" in trauma.title
    assert "outside the accused person's authority" in reporting.description
    assert "asynchronous participation" in access.passage_relevance


def test_pauline_conflict_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-authority-factions-discipline-shame-grief-forgiveness-reconciliation-restoration-commendation-boasting-weakness-and-conflict-transformation"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Does forgiveness require reconciliation, restored trust, or contact after church discipline?",
        "2 Corinthians 2:5-11",
        "cultural practice",
        "institution",
    )
    assert {
        "forgive-comfort-excess-grief",
        "reaffirm-love-revisable-boundary",
        "modern-forgiveness-not-forced-reconciliation",
        "modern-access-restoration-without-contact",
    } & {item.evidence_id for item in ranked[:10]}
    reciprocal_ids = {
        "1-corinthians",
        "2-corinthians",
        "galatians",
        "philippians",
        "1-thessalonians",
        "acts",
        "apostleship",
        "honor-and-shame",
        "restoration-theme",
        "peace-theme",
        "theology-of-the-cross",
        "theology-of-suffering",
    }
    cluster = library.objects_by_id[cluster_id]
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_pauline_prayer_cluster_holds_lament_groaning_hope_and_uncertainty_together() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    assert items["believers-groan-bodied-redemption"].confidence == "high"
    assert "cure guarantee" in items["believers-groan-bodied-redemption"].scholarly_interpretation
    assert "silence" in items["not-knowing-how-to-pray"].passage_relevance
    assert items["spirit-inexpressible-groans"].dispute_status == "major_scholarly_disagreement"
    assert "does not rename harm as good" in items["all-things-not-called-good"].title
    assert "anti-Jewish" in items["romans-israel-lament"].passage_relevance


def test_pauline_prayer_cluster_rejects_compulsory_positivity_and_outcome_promises() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    rejoice = items["philippian-rejoice-not-compulsory-positivity"]
    anxiety = items["philippian-anxiety-prayer-no-shame"]
    thanks = items["thess-joy-prayer-thanks-context"]
    rescue = items["corinth-prayer-thanksgiving-rescue"]
    assert "enforced cheerfulness" in rejoice.passage_relevance
    assert "clinical assessment" in anxiety.passage_relevance
    assert "gratitude for abuse" in thanks.passage_relevance
    assert "failed prayer" in rescue.passage_relevance


def test_pauline_prayer_cluster_joins_prayer_to_material_and_clinical_care() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    material = items["corinth-material-aid-thanksgiving"]
    safety = items["modern-prayer-not-safety-substitute"]
    access = items["modern-access-referral-material-aid"]
    assert "food, housing, healthcare" in material.passage_relevance
    assert "independent investigation" in safety.description
    assert "qualified referral" in access.description
    assert "Never promise cure" in access.notes


def test_pauline_prayer_cluster_requires_consent_confidentiality_access_and_nonretaliation() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    consent = items["modern-public-prayer-consent"]
    privacy = items["modern-prayer-confidentiality-not-surveillance"]
    reading = items["thess-prayer-greeting-reading-access"]
    benediction = items["modern-benediction-no-leader-immunity"]
    assert "no surprise prayer circle" in consent.passage_relevance
    assert "data governance" in privacy.temporal_scope.narrative_setting
    assert "sign language" in reading.notes
    assert "Nonretaliation" in benediction.notes


def test_pauline_prayer_cluster_preserves_acts_as_later_narrative_comparator() -> None:
    library = CanonicalLibrary.load_default()
    cluster = library.objects_by_id[
        "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory"
    ]
    items = {item.id: item for item in cluster.evidence_items}
    lydia = items["acts-prayer-place-lydia-later"]
    miletus = items["acts-miletus-prayer-farewell-later"]
    assert lydia.scripture_references[0].temporal_relation == "diachronic"
    assert "universal conversion" in lydia.passage_relevance
    assert miletus.scripture_references[0].temporal_relation == "diachronic"
    assert "descriptive, not transferable consent" in miletus.notes


def test_pauline_prayer_cluster_is_retrievable_and_bidirectionally_linked() -> None:
    library = CanonicalLibrary.load_default()
    cluster_id = (
        "pauline-prayer-thanksgiving-intercession-lament-groaning-joy-peace-hope-benediction-blessing-and-communal-memory"
    )
    ranked = _rank(
        library,
        cluster_id,
        "Does Romans 8 promise a cure, or can faithful prayer include groaning and uncertainty?",
        "Romans 8:23-27",
        "worldview concept",
        "cultural practice",
    )
    assert {
        "believers-groan-bodied-redemption",
        "hope-unseen-patient-waiting",
        "not-knowing-how-to-pray",
        "spirit-inexpressible-groans",
        "modern-access-referral-material-aid",
    } & {item.evidence_id for item in ranked[:10]}
    reciprocal_ids = {
        "romans",
        "1-corinthians",
        "2-corinthians",
        "galatians",
        "philippians",
        "1-thessalonians",
        "acts",
        "prayer-theme",
        "peace-theme",
        "hope-theme",
        "worship-theme",
        "theology-of-prayer",
        "theology-of-suffering",
    }
    cluster = library.objects_by_id[cluster_id]
    assert reciprocal_ids <= {relation.id for relation in cluster.related_objects}
    for object_id in reciprocal_ids:
        assert cluster_id in {
            relation.id for relation in library.objects_by_id[object_id].related_objects
        }


def test_corpus_evidence_quality_metrics_have_no_structural_failures() -> None:
    library = CanonicalLibrary.load_default()
    report = audit_evidence(library.objects_by_id.values())
    assert report["evidence_count"] == 773
    assert report["evidence_with_primary_sources_count"] == 771
    assert report["evidence_with_academic_secondary_sources_count"] == 758
    assert report["evidence_with_chronology_count"] == 773
    assert report["evidence_with_passage_relevance_count"] == 773
    assert report["disputed_evidence_count"] == 761
    assert report["worldview_evidence_count"] == 198
    assert report["archaeology_linked_evidence_count"] == 31
    assert report["internal_source_only_evidence_count"] == 0
    assert report["missing_source_locator_count"] == 0
    assert report["missing_confidence_rationale_count"] == 0
    assert report["overbroad_context_applicability_count"] == 0
    assert report["error_count"] == 0
