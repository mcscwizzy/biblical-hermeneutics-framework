from __future__ import annotations

import unittest

from framework.canonical_library import (
    CanonicalObject,
    CanonicalRelationship,
    CanonicalScriptureReference,
    CanonicalSource,
    CanonicalValidationError,
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
    source_type: str = "book",
    author: str = "",
    publisher: str = "",
    year: int | None = None,
    locator: str = "",
    url: str = "",
    notes: str = "",
) -> dict[str, object]:
    return CanonicalSource(
        title=title,
        author=author,
        publisher=publisher,
        year=year,
        locator=locator,
        url=url,
        source_type=source_type,
        notes=notes,
    ).to_dict()


class CanonicalSchemaTests(unittest.TestCase):
    def test_valid_canonical_object_passes_validation(self) -> None:
        obj = validate_object(valid_mapping(), path="objects/places/shechem.json")

        self.assertEqual(obj.id, "shechem")
        self.assertEqual(obj.type, "place")
        self.assertEqual(obj.title, "Shechem")
        self.assertEqual(obj.content_status, "placeholder")
        self.assertEqual(obj.review_status, "unreviewed")
        self.assertEqual(obj.reviewed_by, [])
        self.assertIsNone(obj.last_reviewed)
        self.assertEqual(obj.confidence, "unrated")
        self.assertEqual(obj.related_objects, [])
        self.assertEqual(obj.scripture_references, [])
        self.assertEqual(obj.sources, [])

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
                        source_type="biblical-text",
                        locator="12:6-7",
                    ),
                ],
            }
        )

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(obj.content_status, "complete")
        self.assertEqual(obj.review_status, "approved")
        self.assertEqual(obj.reviewed_by, ["alice", "bob"])
        self.assertEqual(obj.last_reviewed, "2024-07-13")
        self.assertEqual(obj.confidence, "high")
        self.assertEqual(obj.summary, "Shechem matters as a covenant location in the patriarchal narratives.")
        self.assertEqual(len(obj.scripture_references), 1)
        self.assertEqual(obj.scripture_references[0].reference, "Genesis 12:6-7")
        self.assertEqual(obj.scripture_references[0].relationship, "primary")
        self.assertEqual(len(obj.sources), 1)
        self.assertEqual(obj.sources[0].title, "Genesis")
        self.assertEqual(obj.sources[0].source_type, "biblical-text")

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
                source_type="biblical-text",
                locator="12:6-7",
            ),
            source_mapping(
                "The Bible and the Ancient Near East",
                author="John Doe",
                publisher="Example Press",
                year=2020,
                locator="pp. 12-14",
                source_type="book",
                notes="reference sample",
            ),
        ]

        obj = validate_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj.sources), 2)
        self.assertEqual(obj.sources[0].title, "Genesis")
        self.assertEqual(obj.sources[0].source_type, "biblical-text")
        self.assertEqual(obj.sources[1].author, "John Doe")
        self.assertEqual(obj.sources[1].year, 2020)
        self.assertIsInstance(obj.sources[0], CanonicalSource)

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
                "source_type": "book",
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
        self.assertEqual(obj.sources[0].source_type, "other")
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
