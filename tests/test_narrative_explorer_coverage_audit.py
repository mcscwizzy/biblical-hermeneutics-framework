import json
from types import SimpleNamespace

from scripts.audit_narrative_explorer_coverage import (
    chapters_for_reference,
    coverage_category,
    _matching_anchor_counts,
    _attach_unresolved_source_ids,
    _status_counts,
    scripture_reference_is_canonical,
    select_stratified_sample,
)


def _item(
    *,
    record_kind="object",
    object_type="event",
    sections=("biblical_narrative",),
    source_available=False,
):
    source = SimpleNamespace(
        details_available=source_available,
        bibliographic_details={"title": "Source title", "author": "Source author"}
        if source_available else {},
    )
    return SimpleNamespace(
        record_kind=record_kind,
        object_type=object_type,
        section_ids=sections,
        sources=(source,) if source_available else (),
    )


def test_coverage_category_requires_a_sourced_claim_or_evidence_item():
    sourced_claim = _item(record_kind="claim", source_available=True)
    unsourced_claim = _item(record_kind="claim", source_available=False)

    assert coverage_category([sourced_claim], lookup_status="complete") == "passage_specific_evidence"
    assert coverage_category([unsourced_claim], lookup_status="complete") == "contextual_coverage"

    source_without_bibliography = SimpleNamespace(
        details_available=True,
        bibliographic_details={"title": "Title only"},
    )
    weakly_sourced_claim = SimpleNamespace(
        record_kind="claim", object_type="event", section_ids=("biblical_narrative",),
        sources=(source_without_bibliography,),
    )
    assert coverage_category([weakly_sourced_claim], lookup_status="complete") == "contextual_coverage"


def test_coverage_category_distinguishes_entities_empty_and_unknown():
    entity = _item(object_type="place", sections=("biblical_geography",))

    assert coverage_category([entity], lookup_status="complete") == "entity_only_coverage"
    assert coverage_category([], lookup_status="complete") == "no_eligible_ckl_material"
    assert coverage_category([], lookup_status="failed") == "incomplete_or_unknown"


def test_stratified_sample_is_reproducible_and_covers_each_stratum():
    chapters = [
        {"reference": f"{stratum} {chapter}", "book": stratum, "chapter": chapter,
         "stratum": stratum}
        for stratum in ("Pentateuch", "Historical", "Poetry", "Major Prophets",
                        "Minor Prophets", "Gospels", "Acts", "Epistles", "Revelation")
        for chapter in range(1, 5)
    ]

    first = select_stratified_sample(chapters, seed=20261015, per_stratum=1)
    second = select_stratified_sample(chapters, seed=20261015, per_stratum=1)

    assert first == second
    assert {chapter["stratum"] for chapter in first} == {chapter["stratum"] for chapter in chapters}
    assert len(first) == 9


def test_chapter_expansion_preserves_book_chapter_and_cross_chapter_scopes():
    chapter_counts = {"Genesis": 3, "Exodus": 2}

    assert chapters_for_reference("Genesis", chapter_counts) == [1, 2, 3]
    assert chapters_for_reference("Genesis 1:2-2:3", chapter_counts) == [1, 2]
    assert chapters_for_reference("Gen 3:4", chapter_counts) == [3]
    assert chapters_for_reference("Genesis 4:1", chapter_counts) == []


def test_scripture_anchor_bounds_use_canonical_chapter_and_verse_counts():
    counts = {"Genesis": {1: 31, 2: 25}}

    assert scripture_reference_is_canonical("Genesis 1:1-2:3", counts)
    assert scripture_reference_is_canonical("Gen 2", counts)
    assert not scripture_reference_is_canonical("Genesis 1:32", counts)
    assert not scripture_reference_is_canonical("Genesis 3:1", counts)


def test_broad_anchor_exclusion_compares_each_anchor_not_only_parent_presence():
    projected = SimpleNamespace(
        object_id="genesis", record_kind="object", local_id="",
        applicable_passage_anchors=({"reference": "Genesis 1:1-2:3"},),
    )
    audit = {
        "matching_authored_anchor_count": 2,
        "semantically_misanchored_anchor_count": 0,
        "book_level_anchor_keys": {("genesis", "object", "", "Genesis")},
        "multi_chapter_anchor_keys": {
            ("genesis", "object", "", "Genesis 1:1-2:3"),
            ("genesis", "object", "", "Genesis 1:1-50:26"),
        },
    }

    counts = _matching_anchor_counts(audit, [projected])

    assert counts["book_level_anchor_reference_excluded_count"] == 1
    assert counts["multi_chapter_anchor_reference_excluded_count"] == 1
    assert counts["multi_chapter_parent_records_projected_count"] == 1


def test_unknown_interpretation_state_is_not_counted_as_uncertain():
    counts = _status_counts([
        SimpleNamespace(interpretation_state="unknown", dispute_status="unknown"),
        SimpleNamespace(interpretation_state="not_established", dispute_status="not_established"),
        SimpleNamespace(interpretation_state="plausible", dispute_status="not_disputed"),
        SimpleNamespace(interpretation_state="disputed", dispute_status="contested"),
    ])

    assert counts["disputed_or_uncertain_item_count"] == 2
    assert counts["explicitly_uncertain_item_count"] == 1
    assert counts["explicitly_disputed_item_count"] == 1
    assert counts["interpretation_state_unknown_or_unestablished_count"] == 2


def test_unresolved_source_ids_are_attributed_only_to_eligible_chapter_items():
    rows = [
        {"ckl_item_ids_json": json.dumps(["event-a#claim:c1"]), "chapter": 1},
        {"ckl_item_ids_json": json.dumps(["event-b#evidence:e1"]), "chapter": 2},
    ]
    source_audit = {
        "missing_source_id_references": [
            {
                "item_id": "event-a#claim:c1",
                "source_id": "missing-source",
                "scripture_references": ["Genesis 1:1"],
            },
            {
                "item_id": "event-c#claim:c9",
                "source_id": "unprojected-source",
                "scripture_references": ["Genesis 2:1"],
            },
        ],
    }

    _attach_unresolved_source_ids(rows, source_audit)

    assert rows[0]["unresolved_source_id_reference_count"] == 1
    assert json.loads(rows[0]["unresolved_source_id_references_json"])[0]["source_id"] == "missing-source"
    assert rows[1]["unresolved_source_id_reference_count"] == 0
