"""Focused CKL checks for the five-chapter structured enrichment."""

from __future__ import annotations

import json

from tools.commentary_v12_five_chapter_structured_enrichment import TARGET_PATHS


def _target(book: str) -> dict:
    return json.loads(TARGET_PATHS[book].read_text(encoding="utf-8"))


def test_five_chapters_have_exact_structured_claim_anchors() -> None:
    expected = {
        "Psalms": {
            "psalm-19-creation-proclamation": "Psalms 19:1-6", "psalm-19-sun-bridegroom-runner": "Psalms 19:4-6",
            "psalm-19-creation-to-torah-movement": "Psalms 19:7-11", "psalm-19-torah-gold-honey-value": "Psalms 19:10-11",
            "psalm-19-hidden-and-presumptuous-faults": "Psalms 19:12-13", "psalm-19-closing-prayer-rock-redeemer": "Psalms 19:14",
            "psalm-103-personal-blessing-catalogue": "Psalms 103:1-5", "psalm-103-righteousness-moses": "Psalms 103:6-7",
            "psalm-103-exodus-mercy-formula": "Psalms 103:8-13", "psalm-103-dust-grass-mortality": "Psalms 103:14-18",
            "psalm-103-throne-universal-blessing": "Psalms 103:19-22", "psalm-2-nations-kings-rebellion": "Psalms 2:1-3",
            "psalm-2-yhwh-zion-anointed": "Psalms 2:4-6", "psalm-2-son-decree-inheritance": "Psalms 2:7-9",
            "psalm-2-royal-ane-idiom-caution": "Psalms 2:6-9", "psalm-2-closing-wisdom-warning": "Psalms 2:10-12",
        },
        "2 Kings": {
            "second-kings-4-widow-oil-debt": "2 Kings 4:1-7", "second-kings-4-shunammite-hospitality-promise": "2 Kings 4:8-17",
            "second-kings-4-shunem-child-carmel": "2 Kings 4:18-37", "second-kings-4-prophetic-community-famine": "2 Kings 4:38-41",
            "second-kings-4-firstfruits-feeding": "2 Kings 4:42-44",
        },
        "Genesis": {
            "genesis-5-adam-seth-image-lineage": "Genesis 5:1-3", "genesis-5-repeated-genealogy-formula": ["Genesis 5:3-20", "Genesis 5:25-32"],
            "genesis-5-and-he-died-mortality": "Genesis 5:5-31", "genesis-5-enoch-walks-with-god": "Genesis 5:21-24",
            "genesis-5-methuselah-lamech-noah-naming": "Genesis 5:25-32", "genesis-5-genealogy-narrative-function": "Genesis 5:1-32",
        },
    }
    for book, claims in expected.items():
        by_id = {claim["id"]: claim for claim in _target(book)["claims"]}
        for claim_id, anchor in claims.items():
            assert by_id[claim_id]["scripture_references"] == (anchor if isinstance(anchor, list) else [anchor])


def test_target_claim_sources_resolve_and_use_allowed_child_claim_types() -> None:
    prefixes = ("psalm-19-", "psalm-103-", "psalm-2-", "second-kings-4-", "genesis-5-")
    allowed = {"biblical_text", "literary", "historical_cultural", "lexical"}
    for book in ("Psalms", "2 Kings", "Genesis"):
        data = _target(book)
        source_ids = {source["id"] for source in data["sources"]}
        for claim in data["claims"]:
            assert set(claim["source_ids"]).issubset(source_ids)
            if claim["id"].startswith(prefixes):
                assert claim["claim_type"] in allowed
