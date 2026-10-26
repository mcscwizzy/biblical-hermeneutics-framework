from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import FastAPI

from bhf_agent.study_db import initialize_database, list_passage_location_summaries
from bhf_web.services.companion_locations import select_ckl_locations
from bhf_web.services.companion_context import CompanionContextService
from bhf_web.routes.study import register_study_routes


def _anchor(reference: str, relationship: str = "primary", notes: str = "") -> dict:
    return {"reference": reference, "relationship": relationship, "notes": notes}


def _ckl_result(
    *,
    object_id: str = "test-place",
    title: str = "Test Place",
    review_status: str = "in_review",
    content_status: str = "complete",
    references: list[dict] | None = None,
    sources: list[dict] | None = None,
    evidence_items: list[dict] | None = None,
    interpretive_notes: list[dict] | None = None,
    **fields,
):
    item = SimpleNamespace(
        id=object_id,
        title=title,
        type="place",
        review_status=review_status,
        content_status=content_status,
        scripture_references=references or [_anchor("Genesis 12:6")],
        sources=sources if sources is not None else [{"id": "scripture-genesis-12", "title": "Genesis 12"}],
        evidence_items=evidence_items or [],
        interpretive_notes=interpretive_notes or [],
        **fields,
    )
    return SimpleNamespace(object=item, score=1.0)


class CklLocationEligibilityTests(unittest.TestCase):
    def test_direct_source_backed_in_review_place_is_not_gated_on_approved(self):
        result = select_ckl_locations("Genesis 12", [_ckl_result()])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test-place")
        self.assertEqual(result[0]["review_status"], "in_review")
        self.assertEqual(result[0]["reference"], "Genesis 12:6")
        self.assertEqual(result[0]["source_lock"]["status"], "not_recorded")
        self.assertNotIn("map_focus_id", result[0])

    def test_identity_only_draft_has_name_and_reference_without_invented_geography(self):
        result = select_ckl_locations(
            "Acts 27",
            [_ckl_result(
                object_id="ckl-lasea",
                title="Lasea",
                review_status="unreviewed",
                content_status="draft",
                references=[_anchor("Acts 27:8")],
                sources=[{"id": "acts-primary", "title": "Acts primary source"}],
                evidence_items=[{
                    "id": "source-lock-acts-27",
                    "evidence_type": "geography-environment",
                    "scripture_references": [_anchor("Acts 27:1-8", "direct")],
                    "source_ids": ["acts-primary"],
                    "notes": "Source-lock identity: acts-27-itinerary; status: LOCKED. Subject: voyage.",
                }],
                coordinates={"latitude": 0.0, "longitude": 0.0},
                modern_location="Invented modern site",
                description="Invented description",
            )],
        )

        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item["source_lock"]["status"], "locked")
        self.assertEqual(item["source_lock"]["id"], "acts-27-itinerary")
        self.assertEqual(item["reference"], "Acts 27:8")
        for field in ("coordinates", "modern_location", "description", "region", "map_focus_id"):
            self.assertNotIn(field, item)

    def test_non_direct_unsupported_and_rejected_ckl_places_are_excluded(self):
        results = [
            _ckl_result(object_id="supporting", references=[_anchor("Genesis 12:6", "supporting")]),
            _ckl_result(object_id="rejected", review_status="rejected"),
            _ckl_result(object_id="source-less", sources=[]),
            _ckl_result(object_id="held-lock", references=[_anchor("Acts 27:8", "supporting")], evidence_items=[{
                "evidence_type": "geography-environment",
                "scripture_references": [_anchor("Acts 27:1-8", "direct")],
                "source_ids": ["acts-primary"],
                "notes": "Source-lock identity: acts-27-held; status: HELD. Subject: voyage.",
            }]),
        ]

        self.assertEqual(select_ckl_locations("Genesis 12", results[:3]), [])
        self.assertEqual(select_ckl_locations("Acts 27", [results[3]]), [])

    def test_locked_direct_geography_evidence_is_distinct_from_object_review_status(self):
        result = select_ckl_locations("Acts 27", [_ckl_result(
            object_id="locked-place",
            title="Locked Place",
            review_status="unreviewed",
            content_status="draft",
            references=[_anchor("Acts 27:8", "supporting")],
            sources=[{"id": "acts-primary", "title": "Acts primary source"}],
            evidence_items=[{
                "id": "source-lock-acts-27",
                "evidence_type": "geography-environment",
                "scripture_references": [_anchor("Acts 27:1-8", "direct")],
                "source_ids": ["acts-primary"],
                "notes": "Source-lock identity: acts-27-itinerary; status: LOCKED. Subject: voyage.",
            }],
        )])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["review_status"], "unreviewed")
        self.assertEqual(result[0]["source_lock"]["status"], "locked")
        self.assertEqual(result[0]["reference"], "Acts 27:1-8")

    def test_held_geography_lock_does_not_supply_an_anchor_or_description(self):
        result = select_ckl_locations("Acts 27", [_ckl_result(
            object_id="held-place",
            title="Held Place",
            references=[_anchor("Acts 27:8", "primary")],
            summary="This description must stay hidden.",
            sources=[{"id": "source", "title": "Source", "supports": ["summary"]}],
            evidence_items=[{
                "evidence_type": "geography-environment",
                "scripture_references": [_anchor("Acts 27:8", "direct")],
                "source_ids": ["source"],
                "notes": "Source-lock identity: held-map-id; status: HELD. Subject: location.",
            }],
        )])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_lock"], {"status": "held", "id": "held-map-id"})
        self.assertNotIn("description", result[0])
        self.assertNotIn("map_focus_id", result[0])

    def test_source_lock_anchor_requires_a_source_resolved_by_the_ckl_object(self):
        result = select_ckl_locations("Acts 27", [_ckl_result(
            object_id="unresolved-source-place",
            title="Unresolved Source Place",
            content_status="draft",
            references=[_anchor("Acts 27:8", "supporting")],
            evidence_items=[{
                "evidence_type": "geography-environment",
                "scripture_references": [_anchor("Acts 27:8", "direct")],
                "source_ids": ["missing-source"],
                "notes": "Source-lock identity: acts-27-unresolved; status: LOCKED. Subject: location.",
            }],
        )])

        self.assertEqual(result, [])

    def test_ckl_uncertainty_requires_a_direct_source_linked_identification_note(self):
        result = select_ckl_locations("Acts 27", [_ckl_result(
            object_id="disputed-place",
            title="Disputed Place",
            references=[_anchor("Acts 27:8")],
            sources=[{"id": "resolved-source", "title": "Source"}],
            interpretive_notes=[{
                "note": "The site's identification is disputed.",
                "certainty": "plausible",
                "dispute_status": "major_scholarly_disagreement",
                "sources": ["resolved-source"],
                "scripture_references": [_anchor("Acts 27:8", "primary")],
            }],
        )])
        unsupported = select_ckl_locations("Acts 27", [_ckl_result(
            object_id="unsupported-note",
            title="Unsupported Note",
            references=[_anchor("Acts 27:8")],
            interpretive_notes=[{
                "note": "This note has no resolved source.",
                "certainty": "plausible",
                "dispute_status": "major_scholarly_disagreement",
                "sources": ["missing-source"],
                "scripture_references": [_anchor("Acts 27:8", "primary")],
            }],
        )])

        self.assertEqual(result[0]["identification_uncertainty"], "The site's identification is disputed.")
        self.assertNotIn("identification_uncertainty", unsupported[0])

    def test_real_genesis_12_ckl_places_keep_only_explicitly_supported_summaries(self):
        root = Path(__file__).resolve().parents[1]
        records = [
            json.loads((root / "framework/canonical_library/objects/places" / f"{name}.json").read_text())
            for name in ("canaan", "shechem")
        ]

        result = select_ckl_locations("Genesis 12", records)
        by_id = {item["id"]: item for item in result}

        self.assertEqual(set(by_id), {"canaan", "shechem"})
        self.assertEqual(by_id["canaan"]["reference"], "Genesis 12:5-9")
        self.assertIn("biblical land west of the Jordan", by_id["canaan"]["description"])
        self.assertNotIn("description", by_id["shechem"])

    def test_revelation_21_does_not_turn_supporting_jerusalem_vision_links_into_locations(self):
        root = Path(__file__).resolve().parents[1]
        jerusalem = json.loads(
            (root / "framework/canonical_library/objects/places/jerusalem.json").read_text()
        )

        self.assertEqual(select_ckl_locations("Revelation 21", [jerusalem]), [])


class MapLocationRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "study.sqlite"
        initialize_database(self.database)

    def tearDown(self):
        self.temporary.cleanup()

    def test_representative_chapters_keep_audited_direct_map_coverage(self):
        expected = {
            ("Genesis", 1): 0,
            ("Genesis", 12): 8,
            ("Genesis", 13): 10,
            ("Genesis", 14): 24,
            ("Psalm", 82): 0,
            ("Jonah", 1): 3,
            ("Acts", 27): 20,
            ("Revelation", 21): 0,
        }

        for (book, chapter), count in expected.items():
            with self.subTest(reference=f"{book} {chapter}"):
                page = list_passage_location_summaries(
                    book, chapter, 1, 9999, path=self.database, limit=25,
                    prepare_schema=False,
                )
                self.assertEqual(page["total"], count)

    def test_map_records_preserve_exact_verse_references_and_catalog_uncertainty(self):
        page = list_passage_location_summaries(
            "Genesis", 12, 1, 9999, path=self.database, limit=25,
            prepare_schema=False,
        )
        canaan = next(item for item in page["items"] if item["id"] == "openbible-a581f0c")

        self.assertEqual(canaan["references"], ["Genesis 12:5", "Genesis 12:10"])
        self.assertEqual(canaan["map_confidence"], "likely")
        self.assertEqual(canaan["provenance"]["name"], "OpenBible.info Bible Geocoding Data")
        self.assertEqual(canaan["map_focus_id"], "openbible-a581f0c")
        self.assertNotIn("latitude", canaan)
        self.assertNotIn("longitude", canaan)

        possible = list_passage_location_summaries(
            "Genesis", 14, 1, 9999, path=self.database, limit=25,
            prepare_schema=False,
        )
        uncertain_item = next(item for item in possible["items"] if item["map_confidence"] == "possible")
        self.assertRegex(uncertain_item["identification_uncertainty"], r"catalog.*possible|possible.*catalog")

    def test_pagination_covers_chapters_over_twenty_five_without_duplicates(self):
        first = list_passage_location_summaries(
            "Joshua", 15, 1, 9999, path=self.database, limit=25,
            prepare_schema=False,
        )
        second_repeat = list_passage_location_summaries(
            "Joshua", 15, 1, 9999, path=self.database, limit=25,
            offset=0, prepare_schema=False,
        )
        all_items = list(first["items"])
        offset = len(first["items"])
        while offset < first["total"]:
            page = list_passage_location_summaries(
                "Joshua", 15, 1, 9999, path=self.database, limit=25,
                offset=offset, prepare_schema=False,
            )
            all_items.extend(page["items"])
            offset += len(page["items"])

        ids = [item["id"] for item in all_items]
        self.assertGreater(first["total"], 25)
        self.assertEqual(first["items"], second_repeat["items"])
        self.assertEqual(len(ids), first["total"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_duplicate_names_with_distinct_map_ids_remain_distinct(self):
        with sqlite3.connect(self.database) as connection:
            source_id = connection.execute(
                "SELECT source_id FROM biblical_places WHERE source_id <> '' LIMIT 1"
            ).fetchone()[0]
            for place_id in ("duplicate-map-a", "duplicate-map-b"):
                connection.execute(
                    """INSERT INTO biblical_places (
                        id,name,aliases,periods,latitude,longitude,modern_location,
                        ancient_region,description,confidence,confidence_rank,
                        source_name,source_url,license,notes,source_id
                    ) VALUES (?,?, '[]','[]',1,1,'','','', 'likely',4,
                              'Test map source','https://example.test/maps','CC-BY-4.0','',?)""",
                    (place_id, "Same Name", source_id),
                )
                connection.execute(
                    """INSERT INTO place_references (
                        id,place_id,book,chapter,verse_start,verse_end,relationship_type,notes
                    ) VALUES (?,?, 'Genesis',1,1,1,'directly_named','Direct test anchor')""",
                    (f"ref-{place_id}", place_id),
                )
            connection.execute(
                """INSERT INTO biblical_places (
                    id,name,aliases,periods,latitude,longitude,modern_location,
                    ancient_region,description,confidence,confidence_rank,
                    source_name,source_url,license,notes,source_id
                ) VALUES ('held-map-place','Held Map Place','[]','[]',1,1,'','','',
                          'strong',5,'Test map source','https://example.test/maps',
                          'CC-BY-4.0','',?)""",
                (source_id,),
            )
            connection.execute(
                """INSERT INTO place_references (
                    id,place_id,book,chapter,verse_start,verse_end,relationship_type,notes
                ) VALUES ('ref-held-map-place','held-map-place','Genesis',1,1,1,
                          'speculative','Unsupported relation')"""
            )

        page = list_passage_location_summaries(
            "Genesis", 1, 1, 9999, path=self.database, limit=25,
            prepare_schema=False,
        )
        duplicates = [item for item in page["items"] if item["title"] == "Same Name"]

        self.assertEqual({item["id"] for item in duplicates}, {"duplicate-map-a", "duplicate-map-b"})
        self.assertNotIn("held-map-place", {item["id"] for item in page["items"]})


class _Library:
    def __init__(self, objects):
        self.objects = list(objects)

    def retrieve_by_scripture_reference(self, _reference, **_options):
        return [SimpleNamespace(object=item, score=1.0) for item in self.objects]


class _Commentary:
    def count_chapter(self, *_args):
        return 0

    def count_passage(self, *_args):
        return 0


class _WordRepository:
    def count_passage_words(self, *_args):
        return 0


class _WordService:
    repository = _WordRepository()


def _service(database: Path, objects=()):
    return CompanionContextService(
        study_db_path=database,
        commentary_db_path=database.parent / "commentary.sqlite",
        canonical_library_provider=lambda: _Library(objects),
        translation_provider=lambda: [],
        word_study_service=_WordService(),
        commentary_service=_Commentary(),
        presentation_cache_path=database.parent / "presentation-cache.sqlite",
    )


def _ckl_place(object_id: str, title: str, reference: str, *, status="in_review", content="complete"):
    return SimpleNamespace(
        id=object_id,
        title=title,
        type="place",
        review_status=status,
        content_status=content,
        summary="A CKL summary that should not be used as a passage role.",
        sources=[{"id": f"source-{object_id}", "title": f"Source for {title}"}],
        scripture_references=[_anchor(reference, "primary")],
        evidence_items=[],
        interpretive_notes=[],
        cross_references=[],
        intertextuality=[],
    )


class CompanionLocationServiceTests(unittest.TestCase):
    def test_context_exposes_initial_locations_outside_compact_map_summaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "study.sqlite"
            initialize_database(database)
            service = _service(database, [
                _ckl_place("canaan", "Canaan", "Genesis 12:5-9"),
                _ckl_place("shechem", "Shechem", "Genesis 12:6-7"),
            ])

            context = service.build(book="Genesis", chapter=12)

        self.assertEqual(context["locations"]["total"], 10)
        self.assertEqual(len(context["locations"]["items"]), 5)
        self.assertEqual(context["locations"]["page_size"], 5)
        self.assertEqual(context["locations"]["next_cursor"], "5")
        self.assertTrue(all(item["origin"] == "maps" for item in context["locations"]["items"]))
        self.assertTrue(context["evidence_bundle"]["compact"])
        self.assertNotIn("locations", context["evidence_bundle"])
        self.assertEqual(
            context["presentation_packet"]["generated_from"]["evidence_hash"],
            context["evidence_bundle"]["evidence_hash"],
        )
        self.assertEqual(
            context["presentation_enhancement"]["evidence_hash"],
            context["evidence_bundle"]["evidence_hash"],
        )
        self.assertLessEqual(len(context["summaries"]["maps"]["places"]), 12)

    def test_view_all_exceeds_the_legacy_twelve_map_summary_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "study.sqlite"
            initialize_database(database)
            service = _service(database)
            first = service.locations_page(book="Genesis", chapter=14, limit=5)
            rest = service.locations_page(
                book="Genesis", chapter=14, cursor=first["next_cursor"], limit=25
            )

        all_items = [*first["items"], *rest["items"]]
        ids = [(item["origin"], item["id"]) for item in all_items]
        self.assertEqual(first["total"], 24)
        self.assertEqual(len(first["items"]), 5)
        self.assertEqual(len(rest["items"]), 19)
        self.assertIsNone(rest["next_cursor"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_view_all_pages_include_ckl_records_without_fuzzy_map_join(self):
        root = Path(__file__).resolve().parents[1]
        object_ids = ("cnidus", "cyprus", "crete", "fair-havens", "italy", "lasea", "myra")
        objects = []
        for object_id in object_ids:
            record = __import__("json").loads(
                (root / "framework/canonical_library/objects/places" / f"{object_id}.json").read_text()
            )
            objects.append(SimpleNamespace(**record))

        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "study.sqlite"
            initialize_database(database)
            service = _service(database, objects)

            first = service.locations_page(book="Acts", chapter=27, limit=5)
            rest = service.locations_page(
                book="Acts", chapter=27, cursor=first["next_cursor"], limit=25
            )

        all_items = [*first["items"], *rest["items"]]
        ckl_items = [item for item in all_items if item["origin"] == "ckl"]
        map_items = [item for item in all_items if item["origin"] == "maps"]
        self.assertEqual(first["total"], 27)
        self.assertEqual(len(all_items), 27)
        self.assertIsNone(rest["next_cursor"])
        self.assertEqual(len({(item["origin"], item["id"]) for item in all_items}), 27)
        self.assertEqual(len(ckl_items), 7)
        self.assertEqual(len(map_items), 20)
        self.assertTrue(all("map_focus_id" not in item for item in ckl_items))
        self.assertTrue(all(item.get("map_focus_id") == item["id"] for item in map_items))
        self.assertTrue(all(item["review_status"] == "unreviewed" for item in ckl_items))
        self.assertTrue(all("description" not in item and "modern_location" not in item for item in ckl_items))


class CompanionLocationsRouteTests(unittest.TestCase):
    def test_route_paginates_bounded_pages_and_rejects_negative_cursor(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "study.sqlite"
            initialize_database(database)
            service = _service(database)
            app = FastAPI()
            register_study_routes(
                app,
                study_db_path=str(database),
                templates=None,
                companion_context_service=service,
            )

            async def requests():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    pages = []
                    cursor = None
                    while True:
                        params = {"book": "Joshua", "chapter": 15, "limit": 25}
                        if cursor is not None:
                            params["cursor"] = cursor
                        page = await client.get("/api/study/companion-locations", params=params)
                        pages.append(page)
                        cursor = page.json().get("next_cursor")
                        if cursor is None:
                            break
                    invalid = await client.get(
                        "/api/study/companion-locations",
                        params={"book": "Joshua", "chapter": 15, "cursor": -1},
                    )
                    return pages, invalid

            async def direct_threadpool(callable_, *args, **kwargs):
                return callable_(*args, **kwargs)

            with patch("bhf_web.routes.study.run_in_threadpool", new=direct_threadpool):
                pages, invalid = asyncio.run(requests())

        self.assertEqual(len(pages), 7)
        self.assertTrue(all(page.status_code == 200 for page in pages))
        page_data = [page.json() for page in pages]
        self.assertTrue(all(page["total"] == 162 for page in page_data))
        items = [item for page in page_data for item in page["items"]]
        item_ids = [item["id"] for item in items]
        self.assertEqual(len(items), 162)
        self.assertEqual(len(item_ids), len(set(item_ids)))
        self.assertEqual(page_data[0]["next_cursor"], "25")
        self.assertEqual(page_data[1]["next_cursor"], "50")
        self.assertIsNone(page_data[-1]["next_cursor"])
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("non-negative integer", invalid.json()["error"])


if __name__ == "__main__":
    unittest.main()
