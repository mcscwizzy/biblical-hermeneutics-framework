"""G3 Genesis 10–11 isolation and applicability regression checks."""

from __future__ import annotations

import json
from pathlib import Path

from bhf_agent.chapter_commentary import evidence_bundling
from framework.canonical_library.loader import CanonicalLibrary
from framework.commentary.production.inputs import prepare_chapter


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
ARTIFACTS = ROOT / ".bhf-data/bhf-commentary-candidates/genesis-g3-nations-babel-evidence-expansion"
G3_OBJECT_ID = "genesis-nations-babel-context"
G3_OBJECT_PATH = CKL_ROOT / "objects/cultural_background/genesis-nations-babel-context.json"
G3_EVIDENCE_IDS = {
    "g10-table-structure",
    "g10-languages-before-babel",
    "g10-genealogical-ethnography",
    "g10-ancient-geographic-horizon",
    "g10-japheth-identification-confidence",
    "g10-ham-cush-mizraim-canaan",
    "g10-shem-line-to-eber",
    "g10-islands-coastlands",
    "g10-nimrod-mighty-hunter",
    "g10-nimrod-city-list",
    "g10-canaan-boundaries-peoples",
    "g10-peleg-divided-earth",
    "g10-table-not-modern-map",
    "g11-shinar-babylon",
    "g11-brick-bitumen",
    "g11-city-tower-ziggurat-context",
    "g11-top-in-heavens",
    "g11-make-a-name-and-abram",
    "g11-prevent-dispersion",
    "g11-yhwh-came-down-irony",
    "g11-let-us-go-down",
    "g11-babel-balal-wordplay",
    "g11-language-confusion-etiology",
    "g11-scattering-narrative-movement",
    "g11-shem-genealogy-lifespans",
    "g11-genealogy-textual-chronology",
    "g11-ur-of-chaldeans-identification",
    "g11-terah-route-to-haran",
    "g11-sarai-barrenness-setup",
}
LEGACY_FALLBACK_IDS = {
    "image-of-god-theme:ancient_near_east_context:0",
    "image-of-god-theme:hebraic_worldview:0",
    "image-of-god-theme:historical_context:0",
    "image-of-god-theme:second_temple_context:0",
}


def _prepared_identity(prepared):
    return {
        "evidence_count": prepared.row["evidence_count"],
        "evidence_hash": prepared.row["input_identity"]["evidence_hash"],
        "synthesis_unit_count": prepared.row["synthesis_unit_count"],
        "synthesis_hash": prepared.row["input_identity"]["synthesis_hash"],
    }


_G3_LIBRARY = None


def _load_g3_library():
    global _G3_LIBRARY
    if _G3_LIBRARY is None:
        _G3_LIBRARY = CanonicalLibrary(root=CKL_ROOT).load()
    evidence_bundling._CANONICAL_LIBRARY_CACHE = _G3_LIBRARY
    return _G3_LIBRARY


def test_g3_items_are_local_to_the_isolated_object_and_synthesis_usable():
    library = _load_g3_library()
    g3 = library.objects_by_id[G3_OBJECT_ID]
    assert G3_OBJECT_PATH.is_file()
    assert {item.id for item in g3.evidence_items} == G3_EVIDENCE_IDS

    production_object = json.loads(G3_OBJECT_PATH.read_text())
    production_items = {item["id"]: item for item in production_object["evidence_items"]}
    candidate_packet = json.loads((ARTIFACTS / "g3-candidate-evidence.json").read_text())
    assert {
        candidate["evidence_item"]["id"]: candidate["evidence_item"]
        for candidate in candidate_packet["candidates"]
    } == production_items

    source_ids = {source.id for source in g3.sources}
    assert len(source_ids) == 20
    assert all(set(item.source_ids) <= source_ids for item in g3.evidence_items)
    assert all(
        reference.reference.startswith(("Genesis 10:", "Genesis 11:"))
        for item in g3.evidence_items
        for reference in item.scripture_references
    )

    for chapter, prefix in ((10, "g10-"), (11, "g11-")):
        prepared = prepare_chapter("Genesis", chapter)
        bundle_ids = {item.id for item in prepared.bundle.evidence_items}
        synthesis_ids = {
            evidence_id
            for unit in prepared.synthesis.synthesis_units
            for evidence_id in unit.evidence_ids
        }
        chapter_ids = {item_id for item_id in G3_EVIDENCE_IDS if item_id.startswith(prefix)}
        assert chapter_ids <= bundle_ids
        assert chapter_ids <= synthesis_ids


def test_g3_source_aliases_preserve_work_identity_without_historical_owner_changes():
    library = _load_g3_library()
    g3 = library.objects_by_id[G3_OBJECT_ID]
    ownership = json.loads((ARTIFACTS / "g3-source-ownership-audit.json").read_text())
    assert ownership["existing_historical_source_owner_rows_changed"] == 0

    aliases = ownership["source_aliases"]
    assert len(aliases) == 3
    fields = ("title", "author", "publisher", "year", "locator", "url", "source_type")
    for alias in aliases:
        local_id = alias["local_source_id"]
        historical_id = alias["historical_source_id"]
        local = next(source for source in g3.sources if source.id == local_id)
        historical = next(
            source
            for obj in library.objects_by_id.values()
            if obj.id != G3_OBJECT_ID
            for source in obj.sources
            if source.id == historical_id
        )
        assert all(getattr(local, field) == getattr(historical, field) for field in fields)
        assert historical_id in local.notes
        notes = local.notes.lower()
        assert "same work" in notes or "same publication/work" in notes

    local_source_ids = {source.id for source in g3.sources}
    historical_source_ids = {
        source.id
        for object_id, obj in library.objects_by_id.items()
        if object_id != G3_OBJECT_ID
        for source in obj.sources
    }
    assert local_source_ids.isdisjoint(historical_source_ids)
    assert all(
        source_id in local_source_ids
        for item in g3.evidence_items
        for source_id in item.source_ids
    )


def test_g3_comparative_references_are_context_only_and_links_are_one_way():
    library = _load_g3_library()
    g3 = library.objects_by_id[G3_OBJECT_ID]
    packet = json.loads((ARTIFACTS / "g3-candidate-evidence.json").read_text())
    applicability = json.loads((ARTIFACTS / "g3-comparative-applicability-audit.json").read_text())

    assert packet["candidate_replay"]["changed_chapters"] == ["Genesis 10", "Genesis 11"]
    assert applicability["comparative_or_later_passages_used_as_applicability_anchors"] == []
    assert applicability["genesis_12_applicability_added"] is False
    assert {ref.reference for ref in g3.scripture_references} == {
        "Genesis 10:1-32",
        "Genesis 11:1-32",
    }
    assert all(target.id in library.objects_by_id for target in g3.related_objects)
    assert not any(
        target.id == G3_OBJECT_ID
        for object_id, obj in library.objects_by_id.items()
        if object_id != G3_OBJECT_ID
        for target in obj.related_objects
    )


def test_g3_controls_and_legacy_fallback_inputs_match_base_exactly():
    library = _load_g3_library()
    impact = json.loads((ARTIFACTS / "g3-chapter-impact.json").read_text())
    controls = impact["required_controls"]
    expected = impact["control_identities"]
    assert len(controls) == 16

    for reference in controls:
        book, chapter = reference.rsplit(" ", 1)
        assert _prepared_identity(prepare_chapter(book, int(chapter))) == expected[reference]

    prepared = prepare_chapter("Genesis", 1)
    assert _prepared_identity(prepared) == expected["Genesis 1"]
    theme_fallback = {
        item.id
        for item in prepared.bundle.evidence_items
        if item.relevance_metadata.get("parent_object_id") == "image-of-god-theme"
        and item.relevance_metadata.get("source_kind") == "ckl_legacy_field"
    }
    assert theme_fallback == LEGACY_FALLBACK_IDS

    for object_id in ("genesis", "babel", "canaan", "assyria", "nineveh"):
        assert not G3_EVIDENCE_IDS.intersection(
            item.id for item in library.objects_by_id[object_id].evidence_items
        )
