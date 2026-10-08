"""Regression checks for Genesis G1 comparative-reference applicability."""

from pathlib import Path

from bhf_agent.chapter_commentary import evidence_bundling
from framework.canonical_library.loader import CanonicalLibrary
from framework.commentary.production.inputs import prepare_chapter


ROOT = Path(__file__).resolve().parents[1]
CKL_ROOT = ROOT / "framework/canonical_library"
COMPARATIVE_IDS = {
    "g3-serpent-later-canonical-reception",
    "g3-seed-later-jewish-christian-reception",
    "g3-cherubim-biblical-sacred-space-context",
}


def test_genesis_3_comparative_references_do_not_apply_to_later_chapters(monkeypatch):
    library = CanonicalLibrary(root=CKL_ROOT).load()
    monkeypatch.setattr(evidence_bundling, "_CANONICAL_LIBRARY_CACHE", library)

    genesis_three = prepare_chapter("Genesis", 3)
    evidence_by_id = {
        item.id: item for item in genesis_three.bundle.evidence_items
    }
    assert COMPARATIVE_IDS <= evidence_by_id.keys()

    for book, chapter in (("Exodus", 25), ("1 Kings", 6), ("Revelation", 12)):
        prepared = prepare_chapter(book, chapter)
        assert COMPARATIVE_IDS.isdisjoint(
            item.id for item in prepared.bundle.evidence_items
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
