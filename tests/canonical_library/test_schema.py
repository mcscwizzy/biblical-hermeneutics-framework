from __future__ import annotations

import unittest

from framework.canonical_library import (
    CanonicalObject,
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


class CanonicalSchemaTests(unittest.TestCase):
    def test_valid_canonical_object_passes_validation(self) -> None:
        obj = validate_object(valid_mapping(), path="objects/places/shechem.json")

        self.assertEqual(obj.id, "shechem")
        self.assertEqual(obj.type, "place")
        self.assertEqual(obj.title, "Shechem")

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
