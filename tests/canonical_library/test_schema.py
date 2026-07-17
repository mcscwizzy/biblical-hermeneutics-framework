from __future__ import annotations

import unittest

from framework.canonical_library import (
    CanonicalObject,
    CanonicalInterpretiveNote,
    CanonicalProvenance,
    CanonicalRelationship,
    CanonicalScriptureReference,
    CanonicalSource,
    CanonicalValidationError,
    normalize_id,
    validate_library,
    validate_object,
)


def valid_mapping() -> dict[str, object]:
    return CanonicalObject(
        id="shechem",
        type="place",
        title="Shechem",
        aliases=["where is shechem", "why is shechem important"],
    ).to_dict()


EXPECTED_CONTEXT_APPLICABILITY = {
    "historical": True,
    "ancient_near_east": True,
    "hebraic_worldview": True,
    "second_temple": True,
    "canonical": True,
    "later_christian_reception": True,
}

SOURCE_TYPE_ALIASES = {
    "biblical-text": "scripture",
    "book": "academic-book",
    "journal": "journal-article",
    "commentary": "reference-work",
    "dictionary": "reference-work",
    "encyclopedia": "reference-work",
    "archaeological-report": "excavation-report",
    "museum": "museum-collection",
    "primary-source": "ancient-primary-source",
    "website": "other",
}


def relationship_mapping(
    object_id: str,
    relationship: str,
    *,
    weight: int = 5,
    notes: str = "",
) -> dict[str, object]:
    return CanonicalRelationship(
        id=object_id,
        relationship=relationship,
        weight=weight,
        notes=notes,
    ).to_dict()


def scripture_reference_mapping(
    reference: str,
    relationship: str,
    *,
    notes: str = "",
) -> dict[str, object]:
    return CanonicalScriptureReference(
        reference=reference,
        relationship=relationship,
        notes=notes,
    ).to_dict()


def source_mapping(
    title: str,
    *,
    id: str | None = None,
    source_type: str = "reference-work",
    author: str = "",
    publisher: str = "",
    year: int | None = None,
    locator: str = "",
    url: str = "",
    supports: list[str] | None = None,
    notes: str = "",
) -> dict[str, object]:
    normalized_source_type = SOURCE_TYPE_ALIASES.get(source_type, source_type)
    return CanonicalSource(
        id=normalize_id(id or title),
        title=title,
        author=author,
        publisher=publisher,
        year=year,
        locator=locator,
        url=url,
        source_type=normalized_source_type,
        supports=list(supports or []),
        notes=notes,
    ).to_dict()


def provenance_mapping(
    *,
    type: str = "ai",
    name: str = "codex",
    workflow: str = "ane-hebraic-context-expansion",
    date: str = "2026-07-16",
) -> dict[str, object]:
    return CanonicalProvenance(
        type=type,
        name=name,
        workflow=workflow,
        date=date,
    ).to_dict()


def interpretive_note_mapping(
    note: str,
    *,
    note_type: str = "textual-observation",
    certainty: str = "unknown",
    dispute_status: str = "unknown",
    sources: list[str] | None = None,
) -> dict[str, object]:
    return CanonicalInterpretiveNote(
        note=note,
        note_type=note_type,
        certainty=certainty,
        dispute_status=dispute_status,
        sources=list(sources or []),
    ).to_dict()


class CanonicalSchemaTests(unittest.TestCase):
    def test_valid_canonical_object_passes_validation(self) -> None:
        obj = validate_object(valid_mapping(), path="objects/places/shechem.json")

        self.assertEqual(obj.id, "shechem")
        self.assertEqual(obj.type, "place")
        self.assertEqual(obj.title, "Shechem")
        self.assertEqual(obj.content_status, "placeholder")
        self.assertEqual(obj.review_status, "unreviewed")
        self.assertEqual(obj.generated_by, [])
        self.assertEqual(obj.edited_by, [])
        self.assertEqual(obj.reviewed_by, [])
        self.assertIsNone(obj.last_reviewed)
        self.assertEqual(obj.confidence, "unrated")
        self.assertTrue(obj.human_review_required)
        self.assertEqual(obj.related_objects, [])
        self.assertEqual(obj.scripture_references, [])
        self.assertEqual(obj.sources, [])
        self.assertEqual(obj.context_applicability, EXPECTED_CONTEXT_APPLICABILITY)
        self.assertEqual(obj.hebraic_worldview, "")
        self.assertEqual(obj.second_temple_context, "")
        self.assertEqual(obj.canonical_context, "")
        self.assertEqual(obj.later_christian_reception, "")

    def test_valid_governance_metadata_passes_validation(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "content_status": "complete",
                "review_status": "approved",
                "reviewed_by": ["alice", "bob"],
                "last_reviewed": "2024-07-13",
                "confidence": "high",
                "summary": "Shechem matters as a covenant location in the patriarchal narratives.",
                "scripture_references": [
                    scripture_reference_mapping("Genesis 12:6-7", "primary"),
                ],
                "sources": [
                source_mapping(
                    "Genesis",
                    source_type="scripture",
                    locator="12:6-7",
                ),
            ],
        }
        )

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(obj.content_status, "complete")
        self.assertEqual(obj.review_status, "approved")
        self.assertEqual(obj.generated_by, [])
        self.assertEqual(obj.edited_by, [])
        self.assertEqual(obj.reviewed_by, ["alice", "bob"])
        self.assertEqual(obj.last_reviewed, "2024-07-13")
        self.assertEqual(obj.confidence, "high")
        self.assertFalse(obj.human_review_required)
        self.assertEqual(obj.summary, "Shechem matters as a covenant location in the patriarchal narratives.")
        self.assertEqual(len(obj.scripture_references), 1)
        self.assertEqual(obj.scripture_references[0].reference, "Genesis 12:6-7")
        self.assertEqual(obj.scripture_references[0].relationship, "primary")
        self.assertEqual(len(obj.sources), 1)
        self.assertEqual(obj.sources[0].title, "Genesis")
        self.assertEqual(obj.sources[0].source_type, "scripture")
        self.assertEqual(obj.sources[0].id, "genesis")
        self.assertEqual(obj.sources[0].supports, [])

    def test_new_context_layers_round_trip_through_validation(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "hebraic_worldview": "Covenant identity and communal memory.",
                "second_temple_context": "Temple-centered Jewish life in the Second Temple period.",
                "canonical_context": "Fits the broader covenant storyline.",
                "later_christian_reception": "Later Christians read it typologically.",
            }
        )

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(obj.hebraic_worldview, "Covenant identity and communal memory.")
        self.assertEqual(obj.second_temple_context, "Temple-centered Jewish life in the Second Temple period.")
        self.assertEqual(obj.canonical_context, "Fits the broader covenant storyline.")
        self.assertEqual(obj.later_christian_reception, "Later Christians read it typologically.")
        self.assertEqual(obj.context_applicability, EXPECTED_CONTEXT_APPLICABILITY)

    def test_legacy_ai_reviewers_are_migrated_to_provenance_records(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "content_status": "complete",
                "review_status": "in_review",
                "reviewed_by": ["codex-phase-10"],
                "last_reviewed": "2026-07-16",
                "confidence": "medium",
                "summary": "Shechem matters as a covenant location in the patriarchal narratives.",
                "scripture_references": [
                    scripture_reference_mapping("Genesis 12:6-7", "primary"),
                ],
                "sources": [
                    source_mapping(
                        "Genesis",
                        source_type="scripture",
                        locator="12:6-7",
                    ),
                ],
            }
        )

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(obj.reviewed_by, [])
        self.assertEqual(len(obj.generated_by), 1)
        provenance = obj.generated_by[0]
        self.assertEqual(provenance.type, "ai")
        self.assertEqual(provenance.name, "codex")
        self.assertEqual(provenance.workflow, "ane-hebraic-context-expansion")
        self.assertEqual(provenance.date, "2026-07-16")
        self.assertTrue(obj.human_review_required)

    def test_legacy_interpretive_notes_are_normalized_to_structured_notes(self) -> None:
        data = valid_mapping()
        data["interpretive_notes"] = ["This is a test note."]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.interpretive_notes), 1)
        note = obj.interpretive_notes[0]
        self.assertIsInstance(note, CanonicalInterpretiveNote)
        self.assertEqual(note.note, "This is a test note.")
        self.assertEqual(note.note_type, "textual-observation")
        self.assertEqual(note.certainty, "unknown")
        self.assertEqual(note.dispute_status, "unknown")
        self.assertEqual(note.sources, [])

    def test_structured_interpretive_notes_pass_validation(self) -> None:
        data = valid_mapping()
        data["interpretive_notes"] = [
            interpretive_note_mapping(
                "The covenant ceremony resembles Ancient Near Eastern treaty forms.",
                note_type="historical-context",
                certainty="medium",
                dispute_status="broad-consensus",
                sources=["source-id"],
            )
        ]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.interpretive_notes), 1)
        note = obj.interpretive_notes[0]
        self.assertEqual(note.note_type, "historical-context")
        self.assertEqual(note.certainty, "medium")
        self.assertEqual(note.dispute_status, "broad-consensus")
        self.assertEqual(note.sources, ["source-id"])

    def test_invalid_interpretive_note_metadata_fails_validation(self) -> None:
        data = valid_mapping()
        data["interpretive_notes"] = [
            {
                "note": "The covenant ceremony resembles Ancient Near Eastern treaty forms.",
                "note_type": "historical-context",
                "certainty": "certain",
                "dispute_status": "broad-consensus",
                "sources": ["source-id"],
            }
        ]

        with self.assertRaisesRegex(
            CanonicalValidationError,
            'field "certainty" must be one of',
        ):
            validate_object(data, path="objects/places/shechem.json")

    def test_context_applicability_merges_partial_mappings(self) -> None:
        data = valid_mapping()
        data["context_applicability"] = {
            "historical": False,
            "canonical": False,
        }

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertFalse(obj.context_applicability["historical"])
        self.assertFalse(obj.context_applicability["canonical"])
        self.assertTrue(obj.context_applicability["ancient_near_east"])
        self.assertTrue(obj.context_applicability["hebraic_worldview"])
        self.assertTrue(obj.context_applicability["second_temple"])
        self.assertTrue(obj.context_applicability["later_christian_reception"])

    def test_context_applicability_rejects_unknown_flags(self) -> None:
        data = valid_mapping()
        data["context_applicability"] = {
            "historical": True,
            "mystery": False,
        }

        with self.assertRaisesRegex(
            CanonicalValidationError,
            "unknown context applicability field",
        ):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_governance_consistency_fails(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "content_status": "draft",
                "review_status": "approved",
                "reviewed_by": ["alice"],
                "last_reviewed": "2024-07-13",
                "confidence": "high",
            }
        )

        with self.assertRaisesRegex(
            CanonicalValidationError,
            'field "content_status" must be "complete" when review_status is "approved"',
        ):
            validate_object(data, path="objects/places/shechem.json")

    def test_approved_content_requires_structured_references_and_sources(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "content_status": "complete",
                "review_status": "approved",
                "reviewed_by": ["alice"],
                "last_reviewed": "2024-07-13",
                "confidence": "high",
                "summary": "Shechem matters as a covenant location in the patriarchal narratives.",
            }
        )

        with self.assertRaisesRegex(
            CanonicalValidationError,
            'field "scripture_references" must contain at least one reference when review_status is "approved"',
        ):
            validate_object(data, path="objects/places/shechem.json")

    def test_approved_content_requires_sources(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "content_status": "complete",
                "review_status": "approved",
                "reviewed_by": ["alice"],
                "last_reviewed": "2024-07-13",
                "confidence": "high",
                "summary": "Shechem matters as a covenant location in the patriarchal narratives.",
                "scripture_references": [
                    scripture_reference_mapping("Genesis 12:6-7", "primary"),
                ],
            }
        )

        with self.assertRaisesRegex(
            CanonicalValidationError,
            'field "sources" must contain at least one source when review_status is "approved"',
        ):
            validate_object(data, path="objects/places/shechem.json")

    def test_approved_content_normalizes_legacy_source_strings(self) -> None:
        data = valid_mapping()
        data.update(
            {
                "content_status": "complete",
                "review_status": "approved",
                "reviewed_by": ["alice"],
                "last_reviewed": "2024-07-13",
                "confidence": "high",
                "summary": "Shechem matters as a covenant location in the patriarchal narratives.",
                "scripture_references": [
                    scripture_reference_mapping("Genesis 12:6-7", "primary"),
                ],
                "sources": ["Genesis 12-22"],
            }
        )

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.sources), 1)
        self.assertEqual(obj.sources[0].title, "Genesis 12-22")
        self.assertEqual(obj.sources[0].source_type, "scripture")
        self.assertEqual(obj.sources[0].id, "genesis-12-22")

    def test_valid_related_objects_pass_validation(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [
            relationship_mapping("abraham", "associated-person", weight=5, notes="patriarch"),
            relationship_mapping("shechem-gate", "associated-place", weight=2, notes="nearby place"),
        ]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.related_objects), 2)
        self.assertEqual(obj.related_objects[0].id, "abraham")
        self.assertEqual(obj.related_objects[0].relationship, "associated-person")
        self.assertEqual(obj.related_objects[0].weight, 5)
        self.assertEqual(obj.related_objects[0].notes, "patriarch")
        self.assertIsInstance(obj.related_objects[0], CanonicalRelationship)

    def test_valid_scripture_references_pass_validation(self) -> None:
        data = valid_mapping()
        data["scripture_references"] = [
            scripture_reference_mapping("Genesis 12:6-7", "primary"),
            scripture_reference_mapping("Joshua 24:1-28", "supporting", notes="covenant renewal"),
        ]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.scripture_references), 2)
        self.assertEqual(obj.scripture_references[0].reference, "Genesis 12:6-7")
        self.assertEqual(obj.scripture_references[0].relationship, "primary")
        self.assertEqual(obj.scripture_references[1].relationship, "supporting")
        self.assertIsInstance(obj.scripture_references[0], CanonicalScriptureReference)

    def test_invalid_scripture_reference_relationship_fails(self) -> None:
        data = valid_mapping()
        data["scripture_references"] = [
            {
                "reference": "Genesis 12:6-7",
                "relationship": "primary-text",
                "notes": "",
            }
        ]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "relationship" must be one of'):
            validate_object(data, path="objects/places/shechem.json")

    def test_valid_structured_sources_pass_validation(self) -> None:
        data = valid_mapping()
        data["sources"] = [
            source_mapping(
                "Genesis",
                source_type="scripture",
                locator="12:6-7",
            ),
            source_mapping(
                "The Bible and the Ancient Near East",
                author="John Doe",
                publisher="Example Press",
                year=2020,
                locator="pp. 12-14",
                source_type="academic-book",
                notes="reference sample",
            ),
        ]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.sources), 2)
        self.assertEqual(obj.sources[0].title, "Genesis")
        self.assertEqual(obj.sources[0].source_type, "scripture")
        self.assertEqual(obj.sources[0].id, "genesis")
        self.assertEqual(obj.sources[1].author, "John Doe")
        self.assertEqual(obj.sources[1].year, 2020)
        self.assertIsInstance(obj.sources[0], CanonicalSource)

    def test_invalid_source_type_fails_validation(self) -> None:
        data = valid_mapping()
        data["sources"] = [
            {
                "title": "Genesis",
                "author": "",
                "publisher": "",
                "year": None,
                "locator": "12:6-7",
                "url": "",
                "source_type": "unsupported-source",
                "notes": "",
            }
        ]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "source_type" must be one of'):
            validate_object(data, path="objects/places/shechem.json")

    def test_legacy_structured_source_types_are_normalized(self) -> None:
        data = valid_mapping()
        data["sources"] = [
            {
                "title": "Genesis",
                "author": "",
                "publisher": "",
                "year": None,
                "locator": "12:6-7",
                "url": "",
                "source_type": "biblical-text",
                "notes": "",
            }
        ]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.sources), 1)
        self.assertEqual(obj.sources[0].title, "Genesis")
        self.assertEqual(obj.sources[0].source_type, "scripture")
        self.assertEqual(obj.sources[0].id, "genesis")
        self.assertEqual(obj.sources[0].supports, [])

    def test_duplicate_normalized_major_themes_fail_validation(self) -> None:
        data = valid_mapping()
        data["major_themes"] = ["covenant", "Covenant"]

        with self.assertRaisesRegex(
            CanonicalValidationError,
            'field "major_themes" contains a duplicate normalized theme id "covenant"',
        ):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_source_year_fails(self) -> None:
        data = valid_mapping()
        data["sources"] = [
            {
                "title": "The Bible and the Ancient Near East",
                "author": "John Doe",
                "publisher": "Example Press",
                "year": "2020",
                "locator": "pp. 12-14",
                "url": "",
                "source_type": "academic-book",
                "notes": "",
            }
        ]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "year" expected null or int'):
            validate_object(data, path="objects/places/shechem.json")

    def test_legacy_string_sources_are_migrated(self) -> None:
        data = valid_mapping()
        data["sources"] = ["Westermann, Genesis"]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.sources), 1)
        self.assertEqual(obj.sources[0].title, "Westermann, Genesis")
        self.assertEqual(obj.sources[0].source_type, "reference-work")
        self.assertEqual(obj.sources[0].id, "westermann-genesis")
        self.assertIsInstance(obj.sources[0], CanonicalSource)

    def test_invalid_related_object_id_fails(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [relationship_mapping("Abraham", "associated-person")]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "id" must use lowercase kebab-case'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_related_object_relationship_fails(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [relationship_mapping("abraham", "Associated Person")]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "relationship" must use lowercase kebab-case'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_related_object_weight_fails(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [relationship_mapping("abraham", "associated-person", weight=11)]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "weight" must be an integer between 1 and 10'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_related_object_weight_type_fails(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [
            {
                "id": "abraham",
                "relationship": "associated-person",
                "weight": "5",
                "notes": "",
            }
        ]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "weight" must be an integer between 1 and 10'):
            validate_object(data, path="objects/places/shechem.json")

    def test_duplicate_related_objects_fail(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [
            relationship_mapping("abraham", "associated-person", notes="first"),
            relationship_mapping("abraham", "associated-person", notes="duplicate"),
        ]

        with self.assertRaisesRegex(CanonicalValidationError, "duplicate relationship"):
            validate_object(data, path="objects/places/shechem.json")

    def test_related_object_self_reference_fails(self) -> None:
        data = valid_mapping()
        data["related_objects"] = [relationship_mapping("shechem", "associated-place")]

        with self.assertRaisesRegex(CanonicalValidationError, "cannot reference the object itself"):
            validate_object(data, path="objects/places/shechem.json")

    def test_related_object_missing_target_fails_library_validation(self) -> None:
        shechem = CanonicalObject(
            id="shechem",
            type="place",
            title="Shechem",
            aliases=["where is shechem"],
            related_objects=[CanonicalRelationship(id="abraham", relationship="associated-person", weight=5, notes="")],
        )

        with self.assertRaisesRegex(CanonicalValidationError, 'references unknown canonical id "abraham"'):
            validate_library([shechem])

    def test_related_object_target_resolves_in_library(self) -> None:
        abraham = CanonicalObject(id="abraham", type="person", title="Abraham", aliases=["who is abraham"])
        shechem = CanonicalObject(
            id="shechem",
            type="place",
            title="Shechem",
            aliases=["where is shechem"],
            related_objects=[CanonicalRelationship(id="abraham", relationship="associated-person", weight=5, notes="")],
        )

        validate_library([abraham, shechem])

    def test_invalid_content_status_fails(self) -> None:
        data = valid_mapping()
        data["content_status"] = "published"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "content_status" must be one of'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_review_status_fails(self) -> None:
        data = valid_mapping()
        data["review_status"] = "waiting"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "review_status" must be one of'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_confidence_fails(self) -> None:
        data = valid_mapping()
        data["confidence"] = "certain"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "confidence" must be one of'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_last_reviewed_format_fails(self) -> None:
        data = valid_mapping()
        data["last_reviewed"] = "2024/07/13"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "last_reviewed" must use YYYY-MM-DD format'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_last_reviewed_date_fails(self) -> None:
        data = valid_mapping()
        data["last_reviewed"] = "2024-02-30"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "last_reviewed" must be a valid YYYY-MM-DD date'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_reviewed_by_values_fails(self) -> None:
        data = valid_mapping()
        data["reviewed_by"] = "alice"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "reviewed_by" expected list\\[str\\]'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_reviewed_by_item_types_fail(self) -> None:
        data = valid_mapping()
        data["reviewed_by"] = ["alice", 42]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "reviewed_by" must be a list of strings'):
            validate_object(data, path="objects/places/shechem.json")

    def test_existing_placeholder_object_compatibility(self) -> None:
        data = valid_mapping()
        for field_name in (
            "content_status",
            "review_status",
            "reviewed_by",
            "last_reviewed",
            "confidence",
        ):
            data.pop(field_name)

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(obj.content_status, "placeholder")
        self.assertEqual(obj.review_status, "unreviewed")
        self.assertEqual(obj.reviewed_by, [])
        self.assertIsNone(obj.last_reviewed)
        self.assertEqual(obj.confidence, "unrated")
        self.assertEqual(obj.related_objects, [])
        self.assertEqual(obj.scripture_references, [])
        self.assertEqual(obj.sources, [])

    def test_missing_id_fails(self) -> None:
        data = valid_mapping()
        data.pop("id")

        with self.assertRaisesRegex(CanonicalValidationError, 'field "id" is required'):
            validate_object(data, path="objects/places/shechem.json")

    def test_missing_type_fails(self) -> None:
        data = valid_mapping()
        data.pop("type")

        with self.assertRaisesRegex(CanonicalValidationError, 'field "type" is required'):
            validate_object(data, path="objects/places/shechem.json")

    def test_missing_title_fails(self) -> None:
        data = valid_mapping()
        data.pop("title")

        with self.assertRaisesRegex(CanonicalValidationError, 'field "title" is required'):
            validate_object(data, path="objects/places/shechem.json")

    def test_invalid_alias_type_fails(self) -> None:
        data = valid_mapping()
        data["aliases"] = "shechem"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "aliases" expected list\\[str\\]'):
            validate_object(data, path="objects/places/shechem.json")

    def test_unknown_category_fails(self) -> None:
        data = valid_mapping()
        data["type"] = "unknown"

        with self.assertRaisesRegex(CanonicalValidationError, "must be one of"):
            validate_object(data, path="objects/unknown/shechem.json")

    def test_invalid_field_type_fails(self) -> None:
        data = valid_mapping()
        data["summary"] = ["not", "a", "string"]

        with self.assertRaisesRegex(CanonicalValidationError, 'field "summary" expected str'):
            validate_object(data, path="objects/places/shechem.json")

    def test_duplicate_id_fails(self) -> None:
        first = CanonicalObject(id="shechem", type="place", title="Shechem", aliases=["where is shechem"])
        second = CanonicalObject(id="shechem", type="theme", title="Shechem Theme", aliases=["shechem theme"])

        with self.assertRaisesRegex(CanonicalValidationError, "duplicate canonical id"):
            validate_library([first, second])

    def test_filename_and_id_mismatch_fails(self) -> None:
        data = valid_mapping()

        with self.assertRaisesRegex(CanonicalValidationError, "must match canonical id"):
            validate_object(data, path="objects/places/not-shechem.json")

    def test_invalid_version_fields_fail(self) -> None:
        data = valid_mapping()
        data["framework_version"] = "2.0"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "framework_version" must be "1.0"'):
            validate_object(data, path="objects/places/shechem.json")

        data = valid_mapping()
        data["object_version"] = "2"

        with self.assertRaisesRegex(CanonicalValidationError, 'field "object_version" must be "1"'):
            validate_object(data, path="objects/places/shechem.json")

    def test_missing_placeholder_field_fails(self) -> None:
        data = valid_mapping()
        data.pop("summary")

        with self.assertRaisesRegex(CanonicalValidationError, 'field\\(s\\) missing: summary'):
            validate_object(data, path="objects/places/shechem.json")


if __name__ == "__main__":
    unittest.main()
