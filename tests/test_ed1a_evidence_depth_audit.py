from scripts.audit_ed1a_evidence_depth import (
    classify_anchor_scope,
    compact_chapter_row,
    projected_ckl_record_id,
    record_domain_tags,
    _source_inventory,
    _write_outputs,
    summarize_chapter_records,
)


def test_record_domains_come_from_typed_fields_not_prose_keywords():
    assert record_domain_tags(
        "evidence",
        "cultural_background",
        {"evidence_type": "inscription", "description": "A dated inscription."},
    ) == ("ancient_primary_sources", "archaeology_geography")
    assert record_domain_tags(
        "claim",
        "book",
        {"claim_type": "lexical", "claim": "A word choice shapes the passage."},
    ) == ("lexical_language",)
    assert record_domain_tags(
        "interpretive_note",
        "book",
        {"note_type": "second-temple-context", "certainty": "disputed"},
    ) == ("historical_cultural", "scholarly_discussion")
    assert record_domain_tags(
        "claim",
        "book",
        {"claim_type": "biblical_theology", "claim": "Roman vocabulary appears here."},
    ) == ()
    assert record_domain_tags(
        "claim",
        "book",
        {"claim_type": "biblical_text", "claim": "The text uses a repeated phrase."},
    ) == ()
    assert record_domain_tags(
        "interpretive_note",
        "book",
        {"note_type": "textual-observation", "description": "A textual observation."},
    ) == ()


def test_projected_record_identity_matches_narrative_explorer_namespace():
    assert projected_ckl_record_id("micah", "object") == "ckl:micah"
    assert projected_ckl_record_id("micah", "claim", "micah-structure") == "ckl:micah#claim:micah-structure"
    assert projected_ckl_record_id("micah", "evidence", "micah-inscription") == "ckl:micah#evidence:micah-inscription"
    assert projected_ckl_record_id("micah", "interpretive_note", "sha256-abc") == "ckl:micah#interpretive-note:sha256-abc"


def test_anchor_scope_separates_verse_chapter_broad_and_invalid_references():
    assert classify_anchor_scope("Micah 1:2", "Micah 1") == "verse"
    assert classify_anchor_scope("Micah 1", "Micah 1") == "chapter"
    assert classify_anchor_scope("Micah", "Micah 1") == "book"
    assert classify_anchor_scope("Micah 1:1-2:4", "Micah 1") == "multi_chapter"
    assert classify_anchor_scope("Obadiah 7", "Obadiah 1") == "invalid"


def test_chapter_summary_keeps_traceable_specific_records_separate_from_broad_context():
    records = [
        {
            "id": "micah-context#evidence:lachish-ostracon",
            "record_kind": "evidence",
            "parent_type": "cultural_background",
            "data": {
                "evidence_type": "inscription",
                "source_ids": ["lachish-publication"],
                "scripture_references": [{"reference": "Micah 1:13", "relationship": "contextual"}],
            },
            "sources": [{
                "id": "lachish-publication",
                "title": "Lachish Inscriptions",
                "author": "Author",
                "source_type": "academic-book",
                "locator": "pp. 10–12",
            }],
        },
        {
            "id": "micah#claim:book-level-setting",
            "record_kind": "claim",
            "parent_type": "book",
            "data": {
                "claim_type": "historical_cultural",
                "source_ids": ["micah-introduction"],
                "scripture_references": [{"reference": "Micah", "relationship": "background"}],
            },
            "sources": [{
                "id": "micah-introduction",
                "title": "Micah in Context",
                "publisher": "Academic Press",
                "source_type": "reference-work",
            }],
        },
    ]

    summary = summarize_chapter_records("Micah 1", records)

    assert summary["verse_scoped_record_count"] == 1
    assert summary["chapter_scoped_record_count"] == 0
    assert summary["broad_context_record_count"] == 1
    assert summary["source_traceable_record_count"] == 2
    assert summary["ancient_primary_sources_record_count"] == 1
    assert summary["ancient_primary_sources_source_traceable_count"] == 1
    assert summary["archaeology_geography_record_count"] == 1
    assert summary["historical_cultural_record_count"] == 1


def test_source_locator_variation_is_not_reported_as_identity_metadata_conflict():
    objects = [{
        "id": "sample",
        "sources": [
            {"id": "commentary", "title": "Sample Commentary", "author": "A. Author", "year": "2020", "source_type": "academic-book", "locator": "p. 10"},
            {"id": "commentary", "title": "Sample Commentary", "author": "A. Author", "year": "2020", "source_type": "academic-book", "locator": "pp. 20–21"},
        ],
    }]

    audit = _source_inventory(objects)

    assert audit["source_ids_with_nonempty_identity_metadata_variation_count"] == 0
    assert audit["source_ids_with_locator_variation_count"] == 1
    assert audit["source_locator_variation"]["commentary"] == ["p. 10", "pp. 20–21"]


def test_chapter_output_keeps_counts_but_omits_repeated_identifier_lists():
    row = compact_chapter_row({
        "reference": "Psalm 72",
        "coverage_category": "passage_specific_evidence",
        "eligible_ckl_item_count": 4,
        "source_ids_json": '["a", "b"]',
        "unclassified_ckl_item_ids_json": "[]",
        "review_statuses_json": '{"in_review": 2}',
    })

    assert row == {
        "reference": "Psalm 72",
        "coverage_category": "passage_specific_evidence",
        "eligible_ckl_item_count": 4,
        "review_statuses_json": '{"in_review": 2}',
    }


def test_csv_writer_uses_git_clean_line_endings(tmp_path):
    _write_outputs(
        tmp_path,
        [{"book": "Micah", "chapter": 1, "reference": "Micah 1"}],
        {"audit_version": "ed1a-test"},
    )

    assert b"\r" not in (tmp_path / "chapter-coverage.csv").read_bytes()
