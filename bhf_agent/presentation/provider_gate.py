"""Bound process-local concurrency for optional presentation providers."""

from __future__ import annotations

import threading


class ProviderRequestGate:
    """Reject excess provider work without retaining request content."""

    def __init__(self, maximum_concurrent_requests: int) -> None:
        limit = int(maximum_concurrent_requests)
        if limit < 1:
            raise ValueError("maximum_concurrent_requests must be at least 1")
        self.limit = limit
        self._semaphore = threading.BoundedSemaphore(limit)
        self._guard = threading.Lock()
        self._active = 0
        self._peak_active = 0

    def try_acquire(self) -> bool:
        acquired = self._semaphore.acquire(blocking=False)
        if acquired:
            with self._guard:
                self._active += 1
                self._peak_active = max(self._peak_active, self._active)
        return acquired

    def release(self) -> None:
        with self._guard:
            if self._active < 1:
                raise RuntimeError("provider request gate released without acquisition")
            self._active -= 1
        self._semaphore.release()

    def diagnostics(self) -> dict[str, int | bool]:
        with self._guard:
            return {
                "enabled": True,
                "limit": self.limit,
                "active": self._active,
                "peak_active": self._peak_active,
            }
