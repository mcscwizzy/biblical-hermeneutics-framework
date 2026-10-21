"""Regression checks for the isolated Genesis G2 evidence container."""

from pathlib import Path

from framework.canonical_library.loader import CanonicalLibrary


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
G2_OBJECT_ID = "genesis-flood-postflood-context"
G2_EVIDENCE_IDS = {
    "g6-sons-of-god-interpretive-positions",
    "g6-second-temple-watchers-reception",
    "g6-nephilim-and-mighty-men",
    "g6-one-hundred-twenty-years",
    "g6-evil-intention-and-violence",
    "g6-divine-grief-and-regret",
    "g6-noah-favor-righteousness-and-toledot",
    "g6-ark-instructions-and-material-terms",
    "g6-covenant-announced-before-flood",
    "g7-clean-animals-and-family-entry",
    "g7-flood-chronology-and-dated-sequence",
    "g7-cosmic-waters-and-decreation",
    "g7-scope-of-flood-language",
    "g7-judgment-and-death-outside-ark",
    "g8-god-remembered-and-wind",
    "g8-receding-water-chronology",
    "g8-ararat-as-region",
    "g8-raven-dove-and-habitability",
    "g8-departure-and-renewed-creaturely-movement",
    "g8-noah-altar-and-pleasing-aroma",
    "g9-renewed-vocation-and-blood-life-accountability",
    "g9-covenant-with-noah-and-all-flesh",
    "g9-bow-sign-and-interpretive-proposals",
    "g9-noah-vineyard-and-canaan-oracle",
    "g9-noah-sons-and-population-notice",
}
_LIBRARY = None


def _library():
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = CanonicalLibrary(root=CKL_ROOT).load()
    return _LIBRARY


def test_new_g2_container_remains_isolated_from_shared_ckl_objects():
    library = _library()
    g2 = library.objects_by_id[G2_OBJECT_ID]
    assert {item.id for item in g2.evidence_items} == G2_EVIDENCE_IDS

    for object_id in ("genesis", "the-flood", "noah", "covenant-theme", "image-of-god-theme"):
        assert not G2_EVIDENCE_IDS.intersection(
            item.id for item in library.objects_by_id[object_id].evidence_items
        )


def test_g2_local_sources_do_not_change_historical_source_owners():
    library = _library()
    g2 = library.objects_by_id[G2_OBJECT_ID]
    g2_source_ids = {source.id for source in g2.sources}
    historical_sources = {
        source.id
        for object_id, obj in library.objects_by_id.items()
        if object_id != G2_OBJECT_ID
        for source in obj.sources
    }

    assert g2_source_ids.isdisjoint(historical_sources)
    assert all(
        source_id in g2_source_ids
        for item in g2.evidence_items
        for source_id in item.source_ids
    )
    local_aliases = [source for source in g2.sources if source.id.startswith("g2r2-local-")]
    new_g2_sources = [source for source in g2.sources if source.id.startswith("g2-")]
    assert len(local_aliases) == 13
    assert len(new_g2_sources) == 16
    assert all("same publication/work" in source.notes.lower() for source in local_aliases)
