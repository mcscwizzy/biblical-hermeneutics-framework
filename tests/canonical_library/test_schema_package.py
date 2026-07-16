from __future__ import annotations

import unittest
from types import SimpleNamespace

from framework.canonical_library import CanonicalObject, CanonicalValidationError
from framework.canonical_library.retrieval import CKLIndex
from framework.canonical_library.schema import load_base_schema, validate_base_object

from .helpers import make_object


class CanonicalSchemaPackageTests(unittest.TestCase):
    def test_base_schema_document_exposes_standard_structure(self) -> None:
        schema = load_base_schema()

        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["framework_version"]["const"], "1.0")
        self.assertEqual(schema["properties"]["object_version"]["const"], "1")
        self.assertIn("related_objects", schema["required"])
        self.assertIn("scripture_references", schema["properties"])
        self.assertEqual(schema["properties"]["aliases"]["minItems"], 1)
        self.assertIn("authorship_positions", schema["required"])
        self.assertIn("major_themes", schema["properties"])
        self.assertEqual(schema["properties"]["original_audience"]["type"], "string")
        self.assertEqual(schema["properties"]["genre"]["$ref"], "#/$defs/stringList")
        self.assertEqual(schema["properties"]["primary_sources"]["$ref"], "#/$defs/stringList")

    def test_validate_base_object_accepts_normalized_inventory_shape(self) -> None:
        obj = validate_base_object(make_object("shechem", "place", "Shechem", ["where is shechem"]))

        self.assertEqual(obj["id"], "shechem")
        self.assertEqual(obj["content_status"], "placeholder")
        self.assertEqual(obj["review_status"], "unreviewed")
        self.assertEqual(obj["sources"], [])
        self.assertEqual(obj["related_objects"], [])

    def test_validate_base_object_rejects_invalid_alias_values(self) -> None:
        data = make_object("shechem", "place", "Shechem", ["where is shechem"])
        data["aliases"] = ["Shechem", 123]

        with self.assertRaises(CanonicalValidationError):
            validate_base_object(data, path="objects/places/shechem.json")

    def test_indexer_logs_and_skips_invalid_entries(self) -> None:
        valid = CanonicalObject(
            id="shechem",
            type="place",
            title="Shechem",
            aliases=["where is shechem"],
            summary="A covenant location.",
            importance=5,
        )
        invalid = CanonicalObject(
            id="bad-entry",
            type="place",
            title="Bad Entry",
            aliases=[123],
            summary="This entry should be rejected by the base schema.",
            importance=1,
        )
        library = SimpleNamespace(
            objects_by_id={"shechem": valid, "bad-entry": invalid},
            objects_root=None,
            source_path_for=lambda _object_id: None,
        )

        with self.assertLogs("framework.canonical_library.retrieval.indexer", level="ERROR") as captured:
            index = CKLIndex.from_library(library)

        self.assertEqual(index.stats.valid_documents, 1)
        self.assertEqual(index.stats.invalid_documents, 1)
        self.assertEqual(index.stats.indexed_entries, 1)
        self.assertIn("shechem", index.entries_by_id)
        self.assertNotIn("bad-entry", index.entries_by_id)
        self.assertTrue(any("Skipping invalid CKL entry during indexing" in message for message in captured.output))


if __name__ == "__main__":
    unittest.main()
