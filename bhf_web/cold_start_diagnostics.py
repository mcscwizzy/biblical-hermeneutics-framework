"""Opt-in, privacy-bounded initialization and request timing diagnostics."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator


LOGGER = logging.getLogger("bhf.cold_start")
LOGGER.setLevel(logging.INFO)


def _process_start_time() -> float:
    """Use Linux process start ticks when available, else diagnostic import time."""

    try:
        with open("/proc/self/stat", encoding="utf-8") as stat_file:
            stat = stat_file.read()
        fields_after_command = stat[stat.rfind(")") + 2 :].split()
        started = int(fields_after_command[19]) / os.sysconf("SC_CLK_TCK")
        current = time.perf_counter()
        return started if 0 <= current - started <= 60 * 60 * 24 * 365 else current
    except (OSError, ValueError, IndexError, TypeError):
        return time.perf_counter()


_PROCESS_ORIGIN = _process_start_time()
_REQUEST_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar("bhf_cold_start_request", default=None)
_REQUEST_LOCK = threading.Lock()
_ACTIVE_REQUESTS = 0
_REQUEST_NUMBER = 0
_SEEN_ROUTE_LABELS: set[str] = set()


def diagnostics_enabled() -> bool:
    """Return whether opt-in diagnostics are enabled for this process."""

    return os.environ.get("BHF_COLD_START_DIAGNOSTICS") == "1"


def safe_route_label(path: str) -> str:
    """Map URL paths to fixed labels without retaining dynamic components."""

    normalized = str(path or "").split("?", 1)[0]
    if normalized == "/api/maps/catalog":
        return "maps_catalog"
    if normalized == "/api/maps/places-for-passage":
        return "maps_places_for_passage"
    if normalized == "/api/maps/routes-for-passage":
        return "maps_routes_for_passage"
    if normalized.startswith("/api/narrative-explorer/v1/passages/"):
        return "narrative_explorer_passage"
    if normalized.startswith("/api/archaeology"):
        return "archaeology"
    if normalized.startswith("/api/maps/"):
        return "maps_other"
    return "other"


def _emit(event: str, **fields: Any) -> None:
    if not diagnostics_enabled():
        return
    state = _REQUEST_CONTEXT.get()
    payload: dict[str, Any] = {
        "event": event,
        "wall_time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "process_elapsed_ms": round((time.perf_counter() - _PROCESS_ORIGIN) * 1000, 3),
        "pid": os.getpid(),
    }
    if state is not None:
        with _REQUEST_LOCK:
            active_request_count = _ACTIVE_REQUESTS
        payload.update(
            request_id=state["request_id"],
            route_label=state["route_label"],
            first_request=state["first_request"],
            route_first_request=state["route_first_request"],
            active_request_count=active_request_count,
            active_request_count_at_start=state["active_request_count"],
        )
    else:
        payload["active_request_count"] = 0
    payload.update(fields)
    LOGGER.info("%s", json.dumps(payload, sort_keys=True, separators=(",", ":")))


def record_startup_stage(stage: str, started_at: float) -> None:
    """Record a bounded startup span using a monotonic start value."""

    _emit(
        "initialization_stage",
        stage=stage,
        elapsed_ms=round((time.perf_counter() - started_at) * 1000, 3),
    )


def record_import_completion(stage: str) -> None:
    """Record imports completed since this diagnostics module was first loaded."""

    record_startup_stage(stage, _PROCESS_ORIGIN)


@contextmanager
def diagnostic_stage(stage: str) -> Iterator[None]:
    """Measure a fixed-name synchronous or coroutine-compatible code span."""

    if not diagnostics_enabled():
        yield
        return
    started_at = time.perf_counter()
    try:
        yield
    except Exception as exc:
        _emit(
            "stage_complete",
            stage=stage,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000, 3),
            error_type=type(exc).__name__,
        )
        raise
    else:
        _emit(
            "stage_complete",
            stage=stage,
            elapsed_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )


class ColdStartDiagnosticsMiddleware:
    """Record request boundaries, response headers, byte counts, and overlap."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        global _ACTIVE_REQUESTS, _REQUEST_NUMBER
        if scope.get("type") != "http" or not diagnostics_enabled():
            await self.app(scope, receive, send)
            return

        route_label = safe_route_label(str(scope.get("path") or ""))
        request_id = uuid.uuid4().hex
        with _REQUEST_LOCK:
            _REQUEST_NUMBER += 1
            first_request = _REQUEST_NUMBER == 1
            route_first_request = route_label not in _SEEN_ROUTE_LABELS
            _SEEN_ROUTE_LABELS.add(route_label)
            _ACTIVE_REQUESTS += 1
            active_request_count = _ACTIVE_REQUESTS

        state = {
            "request_id": request_id,
            "route_label": route_label,
            "first_request": first_request,
            "route_first_request": route_first_request,
            "active_request_count": active_request_count,
        }
        token = _REQUEST_CONTEXT.set(state)
        request_started_at = time.perf_counter()
        response_bytes = 0
        status_code: int | None = None
        _emit("request_start", elapsed_ms=0.0)

        async def send_timed(message: dict[str, Any]) -> None:
            nonlocal response_bytes, status_code
            message_type = message.get("type")
            if message_type == "http.response.start":
                status_code = int(message.get("status", 0))
                await send(message)
                _emit(
                    "response_headers",
                    elapsed_ms=round((time.perf_counter() - request_started_at) * 1000, 3),
                    status_code=status_code,
                )
                return
            if message_type == "http.response.body":
                response_bytes += len(message.get("body", b""))
                await send(message)
                if not message.get("more_body", False):
                    _emit(
                        "request_complete",
                        elapsed_ms=round((time.perf_counter() - request_started_at) * 1000, 3),
                        status_code=status_code,
                        response_bytes=response_bytes,
                    )
                return
            await send(message)

        try:
            await self.app(scope, receive, send_timed)
        except Exception as exc:
            _emit(
                "request_error",
                elapsed_ms=round((time.perf_counter() - request_started_at) * 1000, 3),
                status_code=status_code,
                error_type=type(exc).__name__,
            )
            raise
        finally:
            _REQUEST_CONTEXT.reset(token)
            with _REQUEST_LOCK:
                _ACTIVE_REQUESTS -= 1
