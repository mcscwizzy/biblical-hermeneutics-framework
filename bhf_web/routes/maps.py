"""Map-related route registration for the FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bhf_agent.bible import BibleError
from bhf_agent.study_db import (
    StudyDataError,
    create_map_note,
    create_saved_map_study,
    delete_saved_map_study,
    get_saved_map_study,
    list_saved_map_studies,
)

from ..map_service import (
    get_archaeology_markers,
    get_biblical_place_markers,
    get_historical_layers,
    get_map_routes_for_passage,
    get_manuscript_markers,
    get_political_context_layers,
    get_related_passages_for_place,
    resolve_archaeology_for_passage,
    resolve_manuscripts_for_passage,
    resolve_places_for_passage,
    resolve_political_context_for_passage,
)
from ..services.web_helpers import (
    map_note_payload_from_request,
    map_study_payload_from_request,
    record_action,
    request_payload,
)


def register_map_routes(app: FastAPI, *, study_db_path: str, job_store: object | None = None) -> None:
    @app.get("/api/maps/biblical-places", response_class=JSONResponse)
    async def maps_biblical_places(period: str | None = None) -> JSONResponse:
        return JSONResponse({"markers": get_biblical_place_markers(period=period, path=study_db_path)})

    @app.get("/api/maps/archaeology", response_class=JSONResponse)
    async def maps_archaeology(period: str | None = None) -> JSONResponse:
        return JSONResponse({"markers": get_archaeology_markers(period=period, path=study_db_path)})

    @app.get("/api/maps/manuscripts", response_class=JSONResponse)
    async def maps_manuscripts(period: str | None = None) -> JSONResponse:
        return JSONResponse({"markers": get_manuscript_markers(period=period, path=study_db_path)})

    @app.get("/api/maps/routes", response_class=JSONResponse)
    async def maps_routes(period: str | None = None) -> JSONResponse:
        return JSONResponse({"routes": get_map_routes_for_passage(period=period, path=study_db_path)["routes"]})

    @app.get("/api/maps/historical-layers", response_class=JSONResponse)
    async def maps_historical_layers(period: str | None = None) -> JSONResponse:
        return JSONResponse({"layers": get_historical_layers(period=period, path=study_db_path)})

    @app.get("/api/maps/political-context", response_class=JSONResponse)
    async def maps_political_context(period: str | None = None) -> JSONResponse:
        return JSONResponse({"layers": get_political_context_layers(period=period, path=study_db_path)})

    @app.get("/api/maps/routes-for-passage", response_class=JSONResponse)
    async def maps_routes_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = get_map_routes_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=study_db_path,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @app.get("/api/maps/places-for-passage", response_class=JSONResponse)
    async def maps_places_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_places_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=study_db_path,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @app.get("/api/maps/related-passages-for-place", response_class=JSONResponse)
    async def maps_related_passages_for_place(
        place_id: str,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = get_related_passages_for_place(
                place_id=place_id,
                period=period,
                path=study_db_path,
            )
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @app.get("/api/maps/archaeology-for-passage", response_class=JSONResponse)
    async def maps_archaeology_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_archaeology_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=study_db_path,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @app.get("/api/maps/manuscripts-for-passage", response_class=JSONResponse)
    async def maps_manuscripts_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_manuscripts_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=study_db_path,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @app.get("/api/maps/political-context-for-passage", response_class=JSONResponse)
    async def maps_political_context_for_passage(
        book: str | None = None,
        chapter: int | None = None,
        verse_start: int | None = None,
        verse_end: int | None = None,
        passage_text: str | None = None,
        period: str | None = None,
    ) -> JSONResponse:
        try:
            result = resolve_political_context_for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                period=period,
                path=study_db_path,
            )
        except BibleError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(result)

    @app.get("/api/maps/sample-markers", response_class=JSONResponse)
    async def maps_sample_markers() -> JSONResponse:
        return JSONResponse({"markers": get_biblical_place_markers(path=study_db_path)})

    @app.get("/api/map-studies", response_class=JSONResponse)
    async def map_studies(book: str | None = None, chapter: int | None = None) -> JSONResponse:
        try:
            return JSONResponse({"saved_map_studies": list_saved_map_studies(book, chapter, path=study_db_path)})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/api/map-studies/{study_id}", response_class=JSONResponse)
    async def map_study(study_id: str) -> JSONResponse:
        try:
            return JSONResponse(get_saved_map_study(study_id, path=study_db_path))
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.post("/api/map-studies", response_class=JSONResponse)
    async def post_map_study(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            study = map_study_payload_from_request(payload)
            saved = create_saved_map_study(study, path=study_db_path)
            record_action("map_study_saved", saved, path=study_db_path)
            return JSONResponse(saved, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    @app.delete("/api/map-studies/{study_id}", response_class=JSONResponse)
    async def remove_map_study(study_id: str) -> JSONResponse:
        try:
            delete_saved_map_study(study_id, path=study_db_path)
            return JSONResponse({"deleted": True})
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

    @app.post("/api/map-notes", response_class=JSONResponse)
    async def post_map_note(request: Request) -> JSONResponse:
        try:
            payload = await request_payload(request)
            note = map_note_payload_from_request(payload)
            saved = create_map_note(note, path=study_db_path)
            record_action("map_note_added", saved, path=study_db_path)
            return JSONResponse(saved, status_code=201)
        except StudyDataError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
