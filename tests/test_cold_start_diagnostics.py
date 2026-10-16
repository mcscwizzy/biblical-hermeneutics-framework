from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse


def test_diagnostics_are_disabled_by_default_and_do_not_change_response(monkeypatch, caplog) -> None:
    from bhf_web.cold_start_diagnostics import ColdStartDiagnosticsMiddleware, diagnostic_stage

    monkeypatch.delenv("BHF_COLD_START_DIAGNOSTICS", raising=False)
    caplog.set_level(logging.INFO, logger="bhf.cold_start")
    app = FastAPI()
    app.add_middleware(ColdStartDiagnosticsMiddleware)

    @app.get("/api/maps/places-for-passage")
    async def places_for_passage() -> JSONResponse:
        with diagnostic_stage("map_text_matching"):
            return JSONResponse({"private_selection": "PRIVATE_SELECTION"})

    async def call() -> bytes:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/maps/places-for-passage", params={"passage_text": "PRIVATE_QUERY"})
            return response.content

    response = asyncio.run(call())

    assert response == b'{"private_selection":"PRIVATE_SELECTION"}'
    assert not [record for record in caplog.records if record.name == "bhf.cold_start"]


def test_diagnostics_record_sanitized_concurrent_first_requests_and_headers(monkeypatch, caplog) -> None:
    from bhf_web.cold_start_diagnostics import (
        ColdStartDiagnosticsMiddleware,
        diagnostic_stage,
        safe_route_label,
    )

    monkeypatch.delenv("BHF_COLD_START_DIAGNOSTICS", raising=False)
    caplog.set_level(logging.INFO, logger="bhf.cold_start")
    app = FastAPI()
    app.add_middleware(ColdStartDiagnosticsMiddleware)

    @app.get("/api/maps/places-for-passage")
    async def places_for_passage() -> JSONResponse:
        with diagnostic_stage("map_text_matching"):
            await asyncio.sleep(0.02)
            return JSONResponse(
                {"private_selection": "PRIVATE_SELECTION", "evidence": "PRIVATE_EVIDENCE"}
            )

    async def call(query: str) -> bytes:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/maps/places-for-passage",
                params={"passage_text": query},
                headers={"Authorization": "Bearer PRIVATE_TOKEN"},
            )
            return response.content

    async def call_both() -> tuple[bytes, bytes]:
        return await asyncio.gather(call("PRIVATE_QUERY_ONE"), call("PRIVATE_QUERY_TWO"))

    baseline_first, baseline_second = asyncio.run(call_both())
    assert not [record for record in caplog.records if record.name == "bhf.cold_start"]
    monkeypatch.setenv("BHF_COLD_START_DIAGNOSTICS", "1")
    caplog.clear()
    first, second = asyncio.run(call_both())
    log_text = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "bhf.cold_start"
    )
    events = [json.loads(line) for line in log_text.splitlines()]

    expected_response = b'{"private_selection":"PRIVATE_SELECTION","evidence":"PRIVATE_EVIDENCE"}'
    assert baseline_first == baseline_second == first == second == expected_response
    assert safe_route_label("/api/narrative-explorer/v1/passages/Genesis/2") == "narrative_explorer_passage"
    assert {event["event"] for event in events} >= {"request_start", "response_headers", "request_complete", "stage_complete"}
    starts = [event for event in events if event["event"] == "request_start"]
    assert len(starts) == 2
    assert all(event["route_label"] == "maps_places_for_passage" for event in starts)
    assert len({event["request_id"] for event in starts}) == 2
    assert sorted(event["first_request"] for event in starts) == [False, True]
    assert max(event["active_request_count"] for event in starts) == 2
    assert all(event["pid"] > 0 and event["process_elapsed_ms"] >= 0 for event in events)
    assert all("wall_time_utc" in event for event in events)
    assert all(event["response_bytes"] == len(first) for event in events if event["event"] == "request_complete")
    assert "PRIVATE_SELECTION" not in log_text
    assert "PRIVATE_EVIDENCE" not in log_text
    assert "PRIVATE_QUERY" not in log_text
    assert "PRIVATE_TOKEN" not in log_text
    assert "passage_text" not in log_text


def test_diagnostic_route_labels_are_fixed_and_do_not_contain_dynamic_path_values() -> None:
    from bhf_web.cold_start_diagnostics import safe_route_label

    assert safe_route_label("/api/maps/catalog") == "maps_catalog"
    assert safe_route_label("/api/maps/routes-for-passage") == "maps_routes_for_passage"
    assert safe_route_label("/api/maps/places-for-passage") == "maps_places_for_passage"
    assert safe_route_label("/api/narrative-explorer/v1/passages/Genesis/2") == "narrative_explorer_passage"
    assert safe_route_label("/api/narrative-explorer/v1/passages/ReaderPrivateBook/93") == "narrative_explorer_passage"
    assert safe_route_label("/api/unknown?query=private") == "other"


def test_maps_and_study_database_stages_are_recorded_without_paths_or_passage_text(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    import bhf_agent as _bhf_agent  # noqa: F401 - preserve the package's existing import order
    import bhf_web.map_service as map_service

    monkeypatch.setenv("BHF_COLD_START_DIAGNOSTICS", "1")
    caplog.set_level(logging.INFO, logger="bhf.cold_start")
    caplog.clear()
    monkeypatch.setattr(
        map_service,
        "list_biblical_places",
        lambda **_kwargs: [{"id": "eden", "name": "Eden", "aliases": []}],
    )
    monkeypatch.setattr(
        map_service,
        "resolve_passage",
        lambda *_args, **_kwargs: {"selected_text": "PRIVATE_SOURCE_TEXT"},
    )
    monkeypatch.setattr(map_service, "_resolve_from_reference", lambda **_kwargs: ([], {}))
    monkeypatch.setattr(map_service, "_place_to_marker", lambda place, *_args, **_kwargs: {"id": place["id"]})

    result = map_service.resolve_places_for_passage(
        book="Genesis",
        chapter=2,
        include_related_passages=False,
    )
    from bhf_agent.db.connection import connect

    connection = connect(tmp_path / "study.sqlite")
    connection.close()
    log_text = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "bhf.cold_start"
    )
    events = [json.loads(line) for line in log_text.splitlines()]

    assert result["passage_text"] == "PRIVATE_SOURCE_TEXT"
    expected_stages = {
        "study_database_acquisition",
        "map_place_loading",
        "passage_text_resolution",
        "map_text_matching",
        "scripture_reference_lookup",
        "map_marker_serialization",
    }
    assert expected_stages.issubset({event.get("stage") for event in events})
    assert "PRIVATE_SOURCE_TEXT" not in log_text
    assert str(tmp_path) not in log_text


def test_study_database_acquisition_diagnostic_is_bounded_to_one_event_per_request(
    tmp_path,
    monkeypatch,
    caplog,
) -> None:
    from bhf_agent.db.connection import connect
    from bhf_web.cold_start_diagnostics import ColdStartDiagnosticsMiddleware

    monkeypatch.setenv("BHF_COLD_START_DIAGNOSTICS", "1")
    caplog.set_level(logging.INFO, logger="bhf.cold_start")
    app = FastAPI()
    app.add_middleware(ColdStartDiagnosticsMiddleware)

    @app.get("/api/maps/places-for-passage")
    async def places_for_passage() -> JSONResponse:
        for _ in range(3):
            with connect(tmp_path / "study.sqlite"):
                pass
        return JSONResponse({"ok": True})

    async def call() -> bytes:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return (await client.get("/api/maps/places-for-passage")).content

    assert asyncio.run(call()) == b'{"ok":true}'
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "bhf.cold_start"
    ]
    acquisition_events = [
        event
        for event in events
        if event.get("event") == "stage_complete"
        and event.get("stage") == "study_database_acquisition"
    ]

    assert len(acquisition_events) == 1


def test_startup_stage_records_process_relative_timing_without_source_values(monkeypatch, caplog) -> None:
    from bhf_web.cold_start_diagnostics import record_startup_stage

    monkeypatch.setenv("BHF_COLD_START_DIAGNOSTICS", "1")
    caplog.set_level(logging.INFO, logger="bhf.cold_start")
    started = time.perf_counter()
    time.sleep(0.001)

    record_startup_stage("application_construction", started)

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "bhf.cold_start"
    ]
    assert len(events) == 1
    assert events[0]["event"] == "initialization_stage"
    assert events[0]["stage"] == "application_construction"
    assert events[0]["elapsed_ms"] >= 0
    assert events[0]["process_elapsed_ms"] >= 0


def test_fastapi_stack_initialization_is_correlated_to_first_incoming_request(monkeypatch, caplog) -> None:
    monkeypatch.setenv("BHF_COLD_START_DIAGNOSTICS", "1")
    caplog.set_level(logging.INFO, logger="bhf.cold_start")
    from bhf_web.app import DiagnosticFastAPI, create_app

    caplog.clear()
    app = create_app()

    async def call() -> bytes:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return (await client.get("/api/maps/catalog", params={"include_records": "false"})).content

    response = asyncio.run(call())
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "bhf.cold_start"
    ]
    request_start = next(event for event in events if event["event"] == "request_start")
    stack_init = next(
        event
        for event in events
        if event.get("event") == "initialization_stage"
        and event.get("stage") == "middleware_stack_initialization"
    )

    assert isinstance(app, DiagnosticFastAPI)
    assert b'"timeline"' in response
    assert stack_init["request_id"] == request_start["request_id"]
    assert stack_init["route_label"] == "maps_catalog"
    assert any(
        event.get("stage") == "fastapi_dependency_and_route_handler"
        for event in events
    )
    assert any(event.get("stage") == "route_registration_maps" for event in events)
    assert any(event.get("stage") == "route_registration_narrative_explorer" for event in events)
    assert any(event.get("stage") == "application_construction" for event in events)
    assert any(event.get("stage") == "response_construction" for event in events)
