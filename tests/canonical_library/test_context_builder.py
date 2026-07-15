from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library import (
    CanonicalContextBuilder,
    CanonicalLibrary,
    CanonicalRelationship,
    build_canonical_prompt_context,
)

from .helpers import make_object, write_library


def expansion_fixture_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "shechem",
            "place",
            "Shechem",
            ["where is shechem"],
            summary="Shechem is a covenant location.",
            related_objects=[
                {
                    "id": "missing-target",
                    "relationship": "associated-place",
                    "weight": 10,
                    "notes": "missing target",
                },
                {
                    "id": "joseph",
                    "relationship": "associated-person",
                    "weight": 9,
                    "notes": "burial connection",
                },
                {
                    "id": "old-shechem-site",
                    "relationship": "associated-place",
                    "weight": 8,
                    "notes": "deprecated target",
                },
                {
                    "id": "rejected-shechem-note",
                    "relationship": "associated-topic",
                    "weight": 7,
                    "notes": "rejected target",
                },
                {
                    "id": "abraham",
                    "relationship": "associated-person",
                    "weight": 4,
                    "notes": "lower weight",
                },
            ],
        ),
        make_object(
            "missing-target",
            "place",
            "Missing Target",
            ["missing target"],
            summary="This object is removed after load to simulate a stale relationship target.",
        ),
        make_object(
            "joseph",
            "person",
            "Joseph",
            ["where was joseph buried"],
            summary="Joseph was buried at Shechem.",
            related_objects=[
                {
                    "id": "shechem",
                    "relationship": "associated-place",
                    "weight": 9,
                    "notes": "cycle back",
                }
            ],
        ),
        make_object(
            "abraham",
            "person",
            "Abraham",
            ["abram"],
            summary="Abraham is connected to Shechem.",
        ),
        make_object(
            "old-shechem-site",
            "place",
            "Old Shechem Site",
            ["archived shechem"],
            summary="An archived Shechem site.",
            content_status="deprecated",
        ),
        make_object(
            "rejected-shechem-note",
            "faq",
            "Rejected Shechem Note",
            ["rejected shechem"],
            summary="A rejected Shechem note.",
            review_status="rejected",
            reviewed_by=["zoe"],
            last_reviewed="2024-07-13",
        ),
    ]


def cycle_fixture_objects() -> list[dict[str, object]]:
    return [
        make_object(
            "alpha",
            "person",
            "Alpha",
            ["who is alpha"],
            summary="Alpha is the starting object.",
            related_objects=[
                {
                    "id": "beta",
                    "relationship": "associated-person",
                    "weight": 9,
                    "notes": "alpha to beta",
                }
            ],
        ),
        make_object(
            "beta",
            "person",
            "Beta",
            ["who is beta"],
            summary="Beta links onward to gamma and back to alpha.",
            related_objects=[
                {
                    "id": "gamma",
                    "relationship": "associated-person",
                    "weight": 8,
                    "notes": "beta to gamma",
                },
                {
                    "id": "alpha",
                    "relationship": "associated-person",
                    "weight": 8,
                    "notes": "cycle back",
                },
            ],
        ),
        make_object(
            "gamma",
            "person",
            "Gamma",
            ["who is gamma"],
            summary="Gamma is the end of the chain.",
        ),
    ]


def budget_fixture_objects() -> list[dict[str, object]]:
    long_notes = " ".join(["token-aware context expansion should stay compact"] * 8)
    return [
        make_object(
            "alpha",
            "person",
            "Alpha",
            ["who is alpha"],
            summary="Alpha is the starting object.",
            related_objects=[
                {
                    "id": "beta",
                    "relationship": "associated-person",
                    "weight": 9,
                    "notes": "alpha to beta",
                }
            ],
        ),
        make_object(
            "beta",
            "person",
            "Beta",
            ["who is beta"],
            summary=f"Beta carries a very detailed summary. {long_notes}.",
            historical_context=f"Beta also has a long historical note. {long_notes}.",
            literary_context=f"Beta has a long literary note. {long_notes}.",
            related_objects=[
                {
                    "id": "gamma",
                    "relationship": "associated-person",
                    "weight": 8,
                    "notes": "beta to gamma",
                },
                {
                    "id": "alpha",
                    "relationship": "associated-person",
                    "weight": 8,
                    "notes": "cycle back",
                },
            ],
        ),
        make_object(
            "gamma",
            "person",
            "Gamma",
            ["who is gamma"],
            summary=f"Gamma also carries a very detailed summary. {long_notes}.",
            historical_context=f"Gamma also has a long historical note. {long_notes}.",
        ),
    ]


def remove_loaded_object(library: CanonicalLibrary, object_id: str) -> None:
    library.objects_by_id.pop(object_id, None)
    for ids in library.objects_by_type.values():
        if object_id in ids:
            ids.remove(object_id)
    for alias, ids in list(library.objects_by_alias.items()):
        if object_id in ids:
            ids.remove(object_id)
            if not ids:
                del library.objects_by_alias[alias]
    for title, ids in list(library._title_index.items()):  # noqa: SLF001 - test-only index cleanup
        if object_id in ids:
            ids.remove(object_id)
            if not ids:
                del library._title_index[title]
    for alias, value in list(library._alias_index.items()):  # noqa: SLF001 - test-only index cleanup
        if value[0] == object_id:
            del library._alias_index[alias]
    for term, ids in list(library.keyword_index.items()):
        ids.discard(object_id)
        if not ids:
            del library.keyword_index[term]
    library.field_keyword_index.pop(object_id, None)


class CanonicalContextBuilderTests(unittest.TestCase):
    def test_builds_context_package_from_placeholder_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "shechem",
                        "place",
                        "Shechem",
                        ["shechem"],
                    ),
                ],
            )
            builder = CanonicalContextBuilder(CanonicalLibrary(root=root).load())

            context = builder.build("Shechem", limit=2)

        self.assertEqual(context["question"], "Shechem")
        self.assertEqual(context["metadata"]["retrieval_method"], "id")
        self.assertGreaterEqual(context["metadata"]["topic_count"], 1)
        self.assertEqual(context["metadata"]["topic_count"], 1)
        self.assertEqual(len(context["retrieved_topics"]), 1)
        self.assertEqual(context["retrieved_topics"][0]["id"], "shechem")
        self.assertEqual(context["retrieved_topics"][0]["match_type"], "id")
        self.assertEqual(context["retrieved_topics"][0]["matched_terms"], ["shechem"])
        self.assertEqual(context["retrieved_topics"][0]["matched_fields"], ["id"])
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
        self.assertEqual(limited["metadata"]["primary_topic_count"], 1)
        self.assertEqual(limited["metadata"]["expanded_topic_count"], 1)
        self.assertEqual(limited["metadata"]["topic_count"], 2)
        self.assertEqual(len(limited["retrieved_topics"]), 2)
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

    def test_relationship_expansion_orders_and_filters_related_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(root, expansion_fixture_objects())
            library = CanonicalLibrary(root=root).load()
            remove_loaded_object(library, "missing-target")
            builder = CanonicalContextBuilder(library, max_expanded_topics=3)

            context = builder.build("Shechem", limit=1)

        retrieved_ids = [item["id"] for item in context["retrieved_topics"]]
        self.assertEqual(retrieved_ids, ["shechem", "joseph", "abraham"])
        self.assertEqual(context["metadata"]["primary_topic_count"], 1)
        self.assertEqual(context["metadata"]["expanded_topic_count"], 2)
        self.assertEqual(context["metadata"]["topic_count"], 3)
        self.assertEqual(context["retrieved_topics"][0]["inclusion_type"], "primary")
        self.assertIsNone(context["retrieved_topics"][0]["included_from"])
        self.assertEqual(context["retrieved_topics"][0]["score"], 1.0)
        self.assertEqual(context["retrieved_topics"][1]["inclusion_type"], "relationship")
        self.assertEqual(context["retrieved_topics"][1]["included_from"], "shechem")
        self.assertEqual(context["retrieved_topics"][1]["relationship"], "associated-person")
        self.assertEqual(context["retrieved_topics"][1]["relationship_weight"], 9)
        self.assertEqual(context["retrieved_topics"][1]["relationship_depth"], 1)
        self.assertEqual(context["retrieved_topics"][2]["relationship_weight"], 4)
        self.assertEqual(context["retrieved_topics"][2]["score"], 0.0)
        self.assertNotIn("missing-target", retrieved_ids)
        self.assertNotIn("old-shechem-site", retrieved_ids)
        self.assertNotIn("rejected-shechem-note", retrieved_ids)

    def test_relationship_expansion_respects_count_limit_and_minimum_weight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(root, expansion_fixture_objects())
            limited_library = CanonicalLibrary(root=root).load()
            threshold_library = CanonicalLibrary(root=root).load()
            remove_loaded_object(limited_library, "missing-target")
            remove_loaded_object(threshold_library, "missing-target")
            limited_builder = CanonicalContextBuilder(limited_library, max_expanded_topics=1)
            threshold_builder = CanonicalContextBuilder(
                threshold_library,
                max_expanded_topics=3,
                min_relationship_weight=5,
            )

            limited_context = limited_builder.build("Shechem", limit=1)
            threshold_context = threshold_builder.build("Shechem", limit=1)

        self.assertEqual([item["id"] for item in limited_context["retrieved_topics"]], ["shechem", "joseph"])
        self.assertEqual(limited_context["metadata"]["expanded_topic_count"], 1)
        self.assertEqual([item["id"] for item in threshold_context["retrieved_topics"]], ["shechem", "joseph"])
        self.assertEqual(threshold_context["metadata"]["expanded_topic_count"], 1)

    def test_relationship_expansion_respects_depth_limits_and_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(root, cycle_fixture_objects())
            shallow_builder = CanonicalContextBuilder(CanonicalLibrary(root=root).load(), max_relationship_depth=1)
            deep_builder = CanonicalContextBuilder(CanonicalLibrary(root=root).load(), max_relationship_depth=2)

            shallow_context = shallow_builder.build("Alpha", limit=1)
            deep_context = deep_builder.build("Alpha", limit=1)

        self.assertEqual([item["id"] for item in shallow_context["retrieved_topics"]], ["alpha", "beta"])
        self.assertEqual(shallow_context["metadata"]["expanded_topic_count"], 1)
        self.assertEqual([item["id"] for item in deep_context["retrieved_topics"]], ["alpha", "beta", "gamma"])
        self.assertEqual(deep_context["metadata"]["expanded_topic_count"], 2)
        self.assertEqual(len({item["id"] for item in deep_context["retrieved_topics"]}), 3)

    def test_relationship_expansion_respects_token_budget_and_tracks_estimates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(root, budget_fixture_objects())
            library = CanonicalLibrary(root=root).load()
            seed_builder = CanonicalContextBuilder(library, max_relationship_depth=0, max_expanded_topics=0)
            expansion_builder = CanonicalContextBuilder(
                library,
                max_relationship_depth=2,
                max_expanded_topics=3,
            )

            seed_context = seed_builder.build("Alpha", limit=1)
            seed_entries = seed_context["retrieved_topics"]
            seen_ids = {seed_entries[0]["id"]}

            low_budget = expansion_builder._expand_relationships(
                seed_entries,
                seen_ids.copy(),
                approved_only=False,
                exclude_deprecated=True,
                exclude_rejected=True,
                include_placeholders=True,
                allowed_statuses=None,
                token_budget=60,
            )
            high_budget = expansion_builder._expand_relationships(
                seed_entries,
                seen_ids.copy(),
                approved_only=False,
                exclude_deprecated=True,
                exclude_rejected=True,
                include_placeholders=True,
                allowed_statuses=None,
                token_budget=2000,
            )

        self.assertIn("estimated_tokens", seed_entries[0])
        self.assertGreater(seed_entries[0]["estimated_tokens"], 0)
        self.assertEqual([item["id"] for item in low_budget], ["beta"])
        self.assertEqual([item["id"] for item in high_budget], ["beta", "gamma"])
        self.assertLess(len(low_budget), len(high_budget))

    def test_builds_compact_prompt_context_from_retrieved_topics(self) -> None:
        library = CanonicalLibrary.load_default()
        builder = CanonicalContextBuilder(library)
        rich_context = builder.build(
            "Why is Shechem important in Joshua 24?",
            limit=4,
            include_placeholders=True,
            allowed_statuses=("unreviewed", "in_review", "reviewed", "approved"),
        )

        compact = build_canonical_prompt_context(
            rich_context,
            max_context_tokens=600,
            max_entries=4,
            max_facts_per_entry=3,
            max_scripture_references_per_entry=4,
            max_caution_notes_per_entry=2,
        )

        self.assertGreaterEqual(compact["metadata"]["entry_count"], 1)
        self.assertLessEqual(compact["metadata"]["entry_count"], 4)
        self.assertLessEqual(compact["metadata"]["estimated_tokens"], 600)

        shechem_entry = next(entry for entry in compact["entries"] if entry["id"] == "shechem")
        self.assertEqual(shechem_entry["title"], "Shechem")
        self.assertEqual(shechem_entry["category"], "Place")
        self.assertEqual(shechem_entry["source_ids"], ["shechem"])
        self.assertTrue(shechem_entry["summary"])
        self.assertTrue(shechem_entry["facts"])
        self.assertGreater(compact["metadata"]["scripture_reference_count"], 0)
        self.assertTrue(
            any(
                any("Joshua 24" in reference for reference in entry["scripture_references"])
                for entry in compact["entries"]
            )
        )
        self.assertGreater(compact["metadata"]["caution_note_count"], 0)
        self.assertNotIn("score", shechem_entry)
        self.assertNotIn("match_type", shechem_entry)
        self.assertNotIn("estimated_tokens", shechem_entry)

    def test_builds_compact_prompt_context_deduplicating_repeated_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "duplicate-entry",
                        "place",
                        "Duplicate Entry",
                        ["duplicate entry"],
                        summary="Duplicate entry summary.",
                        historical_context="Repeated factual sentence.",
                        literary_context="Repeated factual sentence.",
                        covenantal_significance="Repeated factual sentence.",
                        interpretive_notes=[
                            "Repeated caution sentence.",
                            "Repeated caution sentence.",
                        ],
                        scripture_references=[
                            {"reference": "Genesis 1:1", "relationship": "primary", "notes": "first"},
                            {
                                "reference": "Genesis 1:1",
                                "relationship": "supporting",
                                "notes": "duplicate",
                            },
                        ],
                    ),
                ],
            )
            library = CanonicalLibrary(root=root).load()
            builder = CanonicalContextBuilder(library)
            rich_context = builder.build("Duplicate entry", limit=1)

        compact = build_canonical_prompt_context(
            rich_context,
            max_context_tokens=300,
            max_entries=1,
            max_facts_per_entry=5,
            max_scripture_references_per_entry=5,
            max_caution_notes_per_entry=5,
        )

        entry = compact["entries"][0]
        self.assertEqual(entry["summary"], "Duplicate entry summary.")
        self.assertEqual(entry["facts"], ["Repeated factual sentence."])
        self.assertEqual(len(entry["scripture_references"]), 1)
        self.assertTrue(entry["scripture_references"][0].startswith("Genesis 1:1 - "))
        self.assertEqual(entry["caution_notes"], ["Repeated caution sentence."])
        self.assertEqual(compact["metadata"]["fact_count"], 1)
        self.assertEqual(compact["metadata"]["scripture_reference_count"], 1)
        self.assertEqual(compact["metadata"]["caution_note_count"], 1)


if __name__ == "__main__":
    unittest.main()
