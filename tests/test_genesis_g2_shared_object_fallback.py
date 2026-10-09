"""Regression checks for the isolated Genesis G2 evidence container."""

from pathlib import Path

from bhf_agent.chapter_commentary import evidence_bundling
from framework.canonical_library.loader import CanonicalLibrary
from framework.commentary.production.inputs import prepare_chapter


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
LEGACY_FALLBACK_IDS = {
    "image-of-god-theme:ancient_near_east_context:0",
    "image-of-god-theme:hebraic_worldview:0",
    "image-of-god-theme:historical_context:0",
    "image-of-god-theme:second_temple_context:0",
}
GENESIS_1_BASE = {
    "evidence_count": 58,
    "evidence_hash": "68599786c2a557df692d91a1caad2381bcdaba1dda3c0d9ef1b6b1dd572ee110",
    "synthesis_unit_count": 12,
    "synthesis_hash": "04bd8f1219a5d2965037512cbeb51a42b45990104e9f649838ea3338c7c8a778",
}
GENESIS_5_BASE = {
    "evidence_count": 21,
    "evidence_hash": "a08db21d7c8c71db65662dbe74d988fc20976289b04a856b8b948784fe840ef2",
    "synthesis_unit_count": 7,
    "synthesis_hash": "4463d42e98b89c31ca184636b6cd9f4414548d072d9354a650fbf11369f448e8",
}
GENESIS_SOURCE_OWNER_CONTROLS = {
    "Genesis 11": (
        21,
        "0ac359bb7d48c3c63927c7aa49461fc70bf034e0360864f80a6d62b8f4cb4d4c",
        3,
        "9530249112686c9cb712e46278a2f3e130c73ca7b3550e1ea0f562397a973227",
    ),
    "Genesis 12": (
        152,
        "ea5aed62ac331507ab8d72d6adab0cfe6f08e6f8b9a719215aa87e823d0c7bcf",
        9,
        "b5d99419269801a970028a345c350e9620f78a949773538d6134e29ca4d62613",
    ),
    "Genesis 15": (
        69,
        "ea24c129ea6415412cac555aa745c8802a1a988b33c3a69e46238e92cf52221d",
        11,
        "fb9649bb6c8731a0ffd5cfb5998bf89cc2f78faa360e6b0ca602001c8952894e",
    ),
    "Genesis 17": (
        50,
        "9ae11257cf20afc9fc0d11c2dcdc108e298f031c3a8f52f964d65c04979fd60d",
        8,
        "689b68a41cb68e7bb3990c7535e952554e276a6f125a62c9fec67ad031eba25c",
    ),
    "Genesis 22": (
        38,
        "bed3f84ff2f57bf8bdd505ac873a08d6390af69d1238b899836d330962dd3916",
        4,
        "4fae8bfa05ac709b7a6a4a6131fb6c84fe8bbe47e90f0f03b230582281438f53",
    ),
}


def _prepared_identity(prepared):
    return {
        "evidence_count": prepared.row["evidence_count"],
        "evidence_hash": prepared.row["input_identity"]["evidence_hash"],
        "synthesis_unit_count": prepared.row["synthesis_unit_count"],
        "synthesis_hash": prepared.row["input_identity"]["synthesis_hash"],
    }


def _install_library(monkeypatch):
    library = CanonicalLibrary(root=CKL_ROOT).load()
    monkeypatch.setattr(evidence_bundling, "_CANONICAL_LIBRARY_CACHE", library)
    return library


def test_new_g2_container_preserves_shared_theme_legacy_fallback(monkeypatch):
    library = _install_library(monkeypatch)
    g2 = library.objects_by_id[G2_OBJECT_ID]
    assert {item.id for item in g2.evidence_items} == G2_EVIDENCE_IDS

    for object_id in ("genesis", "the-flood", "noah", "covenant-theme", "image-of-god-theme"):
        assert not G2_EVIDENCE_IDS.intersection(
            item.id for item in library.objects_by_id[object_id].evidence_items
        )

    for (book, chapter), expected in {
        ("Genesis", 1): GENESIS_1_BASE,
        ("Genesis", 5): GENESIS_5_BASE,
    }.items():
        prepared = prepare_chapter(book, chapter)
        assert _prepared_identity(prepared) == expected
        theme_fallback = {
            item.id
            for item in prepared.bundle.evidence_items
            if item.relevance_metadata.get("parent_object_id") == "image-of-god-theme"
            and item.relevance_metadata.get("source_kind") == "ckl_legacy_field"
        }
        assert theme_fallback == LEGACY_FALLBACK_IDS


def test_g2_local_sources_do_not_change_historical_source_owners_or_genesis_hashes(monkeypatch):
    library = _install_library(monkeypatch)
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
    assert all(
        "same publication/work" in source.notes.lower()
        for source in local_aliases
    )

    for reference, expected in GENESIS_SOURCE_OWNER_CONTROLS.items():
        book, chapter = reference.rsplit(" ", 1)
        actual = _prepared_identity(prepare_chapter(book, int(chapter)))
        assert actual == {
            "evidence_count": expected[0],
            "evidence_hash": expected[1],
            "synthesis_unit_count": expected[2],
            "synthesis_hash": expected[3],
        }
