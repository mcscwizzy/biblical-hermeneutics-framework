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
        self.assertIn("hebraic_worldview", schema["required"])
        self.assertIn("second_temple_context", schema["required"])
        self.assertIn("canonical_context", schema["required"])
        self.assertIn("later_christian_reception", schema["required"])
        self.assertIn("context_applicability", schema["required"])
        self.assertIn("generated_by", schema["required"])
        self.assertIn("edited_by", schema["required"])
        self.assertIn("human_review_required", schema["required"])
        self.assertEqual(schema["properties"]["hebraic_worldview"]["type"], "string")
        self.assertEqual(schema["properties"]["second_temple_context"]["type"], "string")
        self.assertEqual(schema["properties"]["canonical_context"]["type"], "string")
        self.assertEqual(schema["properties"]["later_christian_reception"]["type"], "string")
        self.assertEqual(schema["properties"]["context_applicability"]["$ref"], "#/$defs/contextApplicability")
        self.assertEqual(schema["properties"]["generated_by"]["items"]["$ref"], "#/$defs/provenance")
        self.assertEqual(schema["properties"]["edited_by"]["items"]["type"], "string")
        self.assertEqual(schema["properties"]["human_review_required"]["type"], "boolean")
        self.assertIn("major_themes", schema["properties"])
        self.assertEqual(schema["properties"]["original_audience"]["type"], "string")
        self.assertEqual(schema["properties"]["genre"]["$ref"], "#/$defs/stringList")
        self.assertEqual(schema["properties"]["primary_sources"]["$ref"], "#/$defs/stringList")
        self.assertEqual(schema["$defs"]["provenance"]["required"], ["type", "name", "workflow", "date"])
        self.assertEqual(schema["$defs"]["provenance"]["properties"]["type"]["enum"], ["ai", "human", "import", "migration", "other"])
        self.assertIn("id", schema["$defs"]["source"]["required"])
        self.assertIn("supports", schema["$defs"]["source"]["required"])
        self.assertEqual(schema["$defs"]["source"]["properties"]["id"]["$ref"], "#/$defs/canonicalId")
        self.assertEqual(schema["$defs"]["source"]["properties"]["supports"]["$ref"], "#/$defs/stringList")
        self.assertEqual(
            schema["$defs"]["source"]["properties"]["source_type"]["enum"],
            [
                "scripture",
                "ancient-primary-source",
                "academic-book",
                "journal-article",
                "lexicon",
                "grammar",
                "excavation-report",
                "museum-collection",
                "reference-work",
                "confessional-source",
                "other",
            ],
        )
        interpretive_items = schema["properties"]["interpretive_notes"]["items"]["oneOf"]
        self.assertEqual(interpretive_items[0]["type"], "string")
        self.assertEqual(interpretive_items[1]["$ref"], "#/$defs/interpretiveNote")
        self.assertEqual(schema["$defs"]["interpretiveNote"]["required"], ["note"])
        self.assertIn("certainty", schema["$defs"]["interpretiveNote"]["properties"])
        self.assertIn("claims", schema["required"])
        self.assertIn("section_status", schema["required"])
        self.assertIn("knowledge_layers", schema["required"])
        self.assertEqual(schema["properties"]["claims"]["items"]["$ref"], "#/$defs/claim")

    def test_validate_base_object_accepts_normalized_inventory_shape(self) -> None:
        obj = validate_base_object(make_object("shechem", "place", "Shechem", ["where is shechem"]))

        self.assertEqual(obj["id"], "shechem")
        self.assertEqual(obj["content_status"], "placeholder")
        self.assertEqual(obj["review_status"], "unreviewed")
        self.assertEqual(obj["generated_by"], [])
        self.assertEqual(obj["edited_by"], [])
        self.assertEqual(obj["sources"], [])
        self.assertEqual(obj["claims"], [])
        self.assertEqual(obj["section_status"]["core_summary"], "missing")
        self.assertEqual(
            obj["knowledge_layers"],
            {"primary": "historical_cultural", "secondary": []},
        )
        self.assertEqual(obj["related_objects"], [])
        self.assertTrue(obj["human_review_required"])
        self.assertEqual(
            obj["context_applicability"],
            {
                "historical": True,
                "ancient_near_east": True,
                "hebraic_worldview": True,
                "second_temple": True,
                "canonical": True,
                "later_christian_reception": True,
            },
        )
        self.assertEqual(obj["hebraic_worldview"], "")
        self.assertEqual(obj["second_temple_context"], "")
        self.assertEqual(obj["canonical_context"], "")
        self.assertEqual(obj["later_christian_reception"], "")

    def test_validate_base_object_accepts_structured_interpretive_notes(self) -> None:
        data = make_object("shechem", "place", "Shechem", ["where is shechem"])
        data["interpretive_notes"] = [
            {
                "note": "The covenant ceremony resembles Ancient Near Eastern treaty forms.",
                "note_type": "historical-context",
                "certainty": "medium",
                "dispute_status": "broad-consensus",
                "sources": ["source-id"],
            }
        ]

        obj = validate_base_object(data, path="objects/places/shechem.json")

        self.assertEqual(len(obj["interpretive_notes"]), 1)
        self.assertEqual(obj["interpretive_notes"][0]["note"], "The covenant ceremony resembles Ancient Near Eastern treaty forms.")
        self.assertEqual(obj["interpretive_notes"][0]["note_type"], "historical-context")

    def test_validate_base_object_accepts_current_claim_taxonomy(self) -> None:
        data = make_object("shechem", "place", "Shechem", ["where is shechem"])
        data["claims"] = [
            {
                "id": "shechem-location",
                "claim": "Shechem is named as a location in Genesis 12.",
                "claim_type": "biblical_text",
                "certainty": "textually_explicit",
                "dispute_status": "not_disputed",
                "scripture_references": ["Genesis 12:6"],
                "source_ids": [],
                "traditions": [],
                "rationale": "The place name appears explicitly.",
                "notes": "",
            }
        ]

        obj = validate_base_object(data, path="objects/places/shechem.json")

        self.assertEqual(obj["claims"][0]["certainty"], "textually_explicit")

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
