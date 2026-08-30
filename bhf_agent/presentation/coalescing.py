"""Process-local coalescing for identical concurrent work."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar, cast


T = TypeVar("T")
_MISSING = object()


@dataclass
class _Flight(Generic[T]):
    completed: threading.Event = field(default_factory=threading.Event)
    result: object = _MISSING
    error: BaseException | None = None


class RequestCoalescer(Generic[T]):
    """Share one result among callers doing the same work concurrently."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._flights: dict[str, _Flight[T]] = {}
        self._shared_requests = 0

    def run(self, key: str, operation: Callable[[], T]) -> T:
        with self._guard:
            flight = self._flights.get(key)
            if flight is None:
                flight = _Flight()
                self._flights[key] = flight
                leader = True
            else:
                leader = False
                self._shared_requests += 1

        if leader:
            try:
                flight.result = operation()
            except BaseException as exc:
                flight.error = exc
            finally:
                flight.completed.set()
                with self._guard:
                    if self._flights.get(key) is flight:
                        self._flights.pop(key, None)
        else:
            flight.completed.wait()

        if flight.error is not None:
            raise flight.error
        if flight.result is _MISSING:
            raise RuntimeError("coalesced operation completed without a result")
        return cast(T, flight.result)

    def diagnostics(self) -> dict[str, int]:
        with self._guard:
            return {
                "active_fingerprints": len(self._flights),
                "shared_requests_total": self._shared_requests,
            }
