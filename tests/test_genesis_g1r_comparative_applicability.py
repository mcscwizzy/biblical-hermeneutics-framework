"""Regression checks for Genesis G1 comparative-reference applicability."""

from pathlib import Path

from framework.canonical_library.loader import CanonicalLibrary


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
COMPARATIVE_IDS = {
    "g3-serpent-later-canonical-reception",
    "g3-seed-later-jewish-christian-reception",
    "g3-cherubim-biblical-sacred-space-context",
}


def test_genesis_3_comparative_references_do_not_apply_to_later_chapters():
    library = CanonicalLibrary(root=CKL_ROOT).load()

    genesis_three = library.retrieve_evidence_items(
        "reception and cherubim", ["genesis"], scripture_references=["Genesis 3"],
        limit_per_object=100,
    )
    evidence_by_id = {item.evidence_id: item for item in genesis_three["genesis"]}
    assert COMPARATIVE_IDS <= evidence_by_id.keys()

    for book, chapter in (("Exodus", 25), ("1 Kings", 6), ("Revelation", 12)):
        prepared = library.retrieve_evidence_items(
            "reception and cherubim", ["genesis"],
            scripture_references=[f"{book} {chapter}"], limit_per_object=100,
        )
        assert COMPARATIVE_IDS.isdisjoint(
            item.evidence_id for item in prepared["genesis"]
        )


def test_comparative_references_and_source_provenance_remain_on_genesis_evidence():
    library = CanonicalLibrary(root=CKL_ROOT).load()
    genesis = library.objects_by_id["genesis"]
    evidence = {item.id: item for item in genesis.evidence_items}
    expected_context = {
        "g3-serpent-later-canonical-reception": (
            "Revelation 12:9",
            {"g1-revelation-text", "g1-zhakevich-genesis-315"},
        ),
        "g3-seed-later-jewish-christian-reception": (
            "Revelation 12:9",
            {"g1-revelation-text", "g1-zhakevich-genesis-315"},
        ),
        "g3-cherubim-biblical-sacred-space-context": (
            "Exodus 25:18",
            {"g1-exodus-text", "g1-kings-text", "g1-lexham-cherubim"},
        ),
    }

    for evidence_id, (reference_text, source_ids) in expected_context.items():
        item = evidence[evidence_id]
        assert all(
            link.reference.startswith("Genesis ")
            for link in item.scripture_references
        )
        assert reference_text in item.notes
        assert source_ids <= set(item.source_ids)
