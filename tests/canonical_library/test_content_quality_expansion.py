from __future__ import annotations

from framework.canonical_library import CanonicalLibrary, audit_evidence, rank_evidence_items


EXPANSION_OBJECTS = {
    "mesopotamian-creation-and-flood-comparisons": 3,
    "ancient-divine-assembly-imagery": 4,
    "egyptian-forced-labor-and-brickmaking": 2,
    "thessalonian-civic-and-funerary-context": 3,
    "egyptian-kingship-and-divine-order": 4,
    "exodus-wilderness-routes-and-water": 3,
    "late-bronze-iron-transition-and-highland-settlement": 4,
    "judges-household-religion-and-regional-cult-sites": 4,
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
    assert [item.evidence_id for item in ranked] == [
        "parousia-apantesis-civic-arrival-proposal",
        "later-thessalonian-funerary-comparison",
    ]
    assert ranked[0].chronological_relation == "contemporary"
    assert ranked[1].chronological_relation == "later-comparative"
    assert ranked[0].retrieval_score > ranked[1].retrieval_score


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
    assert report["evidence_count"] == 32
    assert report["evidence_with_primary_sources_count"] == 31
    assert report["evidence_with_academic_secondary_sources_count"] == 27
    assert report["evidence_with_chronology_count"] == 32
    assert report["evidence_with_passage_relevance_count"] == 32
    assert report["disputed_evidence_count"] == 23
    assert report["worldview_evidence_count"] == 5
    assert report["archaeology_linked_evidence_count"] == 5
    assert report["internal_source_only_evidence_count"] == 0
    assert report["missing_source_locator_count"] == 0
    assert report["missing_confidence_rationale_count"] == 0
    assert report["overbroad_context_applicability_count"] == 0
    assert report["error_count"] == 0
