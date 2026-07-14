from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import CanonicalContextBuilder, CanonicalLibrary, CanonicalRelationship

from .helpers import make_object, write_library


class CanonicalContextBuilderTests(unittest.TestCase):
    def test_builds_context_package_from_placeholder_inventory(self) -> None:
        library = CanonicalLibrary.load_default()
        builder = CanonicalContextBuilder(library)

        context = builder.build("Shechem", limit=2)

        self.assertEqual(context["question"], "Shechem")
        self.assertEqual(context["metadata"]["retrieval_method"], "id")
        self.assertGreaterEqual(context["metadata"]["topic_count"], 1)
        self.assertEqual(context["metadata"]["topic_count"], 1)
        self.assertEqual(len(context["retrieved_topics"]), 1)
        self.assertEqual(context["retrieved_topics"][0]["id"], "shechem")
        self.assertEqual(context["retrieved_topics"][0]["match_type"], "id")
        self.assertEqual(context["historical_context"], [])
        self.assertEqual(context["ancient_near_east_context"], [])
        self.assertEqual(context["literary_context"], [])
        self.assertEqual(context["covenantal_significance"], [])
        self.assertEqual(context["cross_references"], [])
        self.assertEqual(context["word_studies"], [])
        self.assertEqual(context["related_topics"], [])
        self.assertEqual(context["related_objects"], [])
        self.assertEqual(context["timeline"], [])
        self.assertEqual(context["archaeology"], [])
        self.assertEqual(context["new_testament_connections"], [])

    def test_builds_deduplicated_context_with_stable_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "covenant-theme",
                        "theme",
                        "Covenant Theme",
                        ["covenant motif"],
                        historical_context="Patriarchal covenant",
                        ancient_near_east_context="Treaty form",
                        literary_context="Narrative repetition",
                        covenantal_significance="Promise and loyalty",
                        intertextuality=["genesis-15"],
                        timeline=["Patriarchal era"],
                        maps=["shechem"],
                        archaeology=["Dead Sea Scrolls"],
                        hebrew_words=["berit"],
                        greek_words=["diatheke"],
                        related_people=["abraham"],
                        related_places=["shechem"],
                        related_events=["call-of-abraham"],
                        cross_references=["shared-ref"],
                        new_testament_connections=["galatians-3"],
                        interpretive_notes=["note-1"],
                        common_questions=["question-1"],
                        sources=["source-1"],
                    ),
                    make_object(
                        "abraham",
                        "person",
                        "Abraham",
                        ["who is abraham"],
                        historical_context="Patriarchal covenant",
                        ancient_near_east_context="Treaty form",
                        literary_context="Faithful response",
                        covenantal_significance="Promise and loyalty",
                        intertextuality=["genesis-15"],
                        timeline=["Patriarchal era"],
                        maps=["shechem"],
                        archaeology=["Dead Sea Scrolls"],
                        hebrew_words=["berit"],
                        greek_words=["diatheke"],
                        related_people=["covenant-theme"],
                        related_places=["shechem"],
                        related_events=["call-of-abraham"],
                        cross_references=["shared-ref"],
                        new_testament_connections=["galatians-3"],
                    ),
                ],
            )
            builder = CanonicalContextBuilder(CanonicalLibrary(root=root).load())

            first = builder.build("covenant abraham", limit=2)
            second = builder.build("covenant abraham", limit=2)
            limited = builder.build("covenant abraham", limit=1)

        self.assertEqual(first["question"], "covenant abraham")
        self.assertEqual([item["id"] for item in first["retrieved_topics"]], [item["id"] for item in second["retrieved_topics"]])
        self.assertEqual(first["metadata"]["retrieval_method"], "keyword")
        self.assertEqual(first["metadata"]["topic_count"], 2)
        self.assertEqual(limited["metadata"]["topic_count"], 1)
        self.assertEqual(len(limited["retrieved_topics"]), 1)
        self.assertEqual(len(first["historical_context"]), 1)
        self.assertEqual(len(first["ancient_near_east_context"]), 1)
        self.assertEqual(len(first["covenantal_significance"]), 1)
        self.assertEqual(len(first["cross_references"]), 1)
        self.assertEqual(len(first["timeline"]), 1)
        self.assertEqual(len(first["archaeology"]), 1)
        self.assertEqual(len(first["new_testament_connections"]), 1)
        self.assertEqual(len(first["word_studies"]), 2)
        self.assertEqual(len(first["related_topics"]), 4)
        self.assertEqual(len(first["related_objects"]), 4)
        self.assertEqual(len(set(first["historical_context"])), len(first["historical_context"]))
        self.assertEqual(len(set(first["related_topics"])), len(first["related_topics"]))
        self.assertEqual(
            len({(item["id"], item["relationship"]) for item in first["related_objects"]}),
            len(first["related_objects"]),
        )

    def test_builds_normalized_related_objects_from_legacy_and_typed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object("abraham", "person", "Abraham", ["who is abraham"]),
                    make_object(
                        "covenant-theme",
                        "theme",
                        "Covenant Theme",
                        ["covenant motif"],
                        related_people=["isaac"],
                        related_places=["shechem"],
                        related_events=["call-of-abraham"],
                        related_objects=[
                            CanonicalRelationship(
                                id="abraham",
                                relationship="associated-person",
                                weight=5,
                                notes="patriarch",
                            ),
                        ],
                    ),
                ],
            )
            builder = CanonicalContextBuilder(CanonicalLibrary(root=root).load())

            context = builder.build("covenant theme", limit=1)

        expected_related_objects = [
            {
                "id": "abraham",
                "relationship": "associated-person",
                "weight": 5,
                "notes": "patriarch",
            },
            {
                "id": "isaac",
                "relationship": "associated-person",
                "weight": 1,
                "notes": "",
            },
            {
                "id": "shechem",
                "relationship": "associated-place",
                "weight": 1,
                "notes": "",
            },
            {
                "id": "call-of-abraham",
                "relationship": "associated-event",
                "weight": 1,
                "notes": "",
            },
        ]

        self.assertEqual(context["related_topics"], ["abraham", "isaac", "shechem", "call-of-abraham"])
        self.assertEqual(context["related_objects"], expected_related_objects)
        self.assertEqual(context["retrieved_topics"][0]["related_objects"], expected_related_objects)


if __name__ == "__main__":
    unittest.main()
