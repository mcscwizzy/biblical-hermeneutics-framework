"""Versioned presentation-packet cache contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import PRESENTATION_SCHEMA_VERSION, EvidenceBundle


def presentation_cache_key(
    bundle: EvidenceBundle,
    *,
    prompt_version: str,
    generation_profile: str | None = None,
) -> str:
    return presentation_cache_key_for_versions(
        passage_ref=bundle.passage_ref,
        evidence_hash=bundle.evidence_hash,
        evidence_bundle_version=bundle.version,
        presentation_schema_version=PRESENTATION_SCHEMA_VERSION,
        prompt_version=prompt_version,
        generation_profile=generation_profile,
    )


def presentation_cache_key_for_versions(
    *,
    passage_ref: str,
    evidence_hash: str,
    evidence_bundle_version: str,
    presentation_schema_version: str,
    prompt_version: str,
    generation_profile: str | None = None,
) -> str:
    """Build a credential-free packet fingerprint from versions and model profile."""

    payload = {
        "passage_ref": passage_ref,
        "evidence_hash": evidence_hash,
        "evidence_bundle_version": evidence_bundle_version,
        "presentation_schema_version": presentation_schema_version,
        "prompt_version": prompt_version,
    }
    if generation_profile:
        payload["generation_profile"] = str(generation_profile)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PresentationCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def put(self, key: str, packet: dict[str, Any]) -> None:
        raise NotImplementedError

    def discard(self, key: str) -> None:
        """Remove a rejected packet when supported."""


class MemoryPresentationCache(PresentationCache):
    """Small process-local cache; mobile/PWA stores can implement the same API."""

    def __init__(self, maximum_entries: int = 256) -> None:
        self.maximum_entries = max(1, int(maximum_entries))
        self._values: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._values.get(key)
            return json.loads(json.dumps(value)) if value is not None else None

    def put(self, key: str, packet: dict[str, Any]) -> None:
        with self._lock:
            if key not in self._values and len(self._values) >= self.maximum_entries:
                self._values.pop(next(iter(self._values)))
            self._values[key] = json.loads(json.dumps(packet))

    def discard(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)


class SQLitePresentationCache(PresentationCache):
    """Durable disposable packets stored separately from canonical knowledge."""

    def __init__(self, path: str | Path, *, maximum_entries: int = 512) -> None:
        self.path = Path(path)
        self.maximum_entries = max(1, int(maximum_entries))
        self._lock = threading.RLock()

    def get(self, key: str) -> dict[str, Any] | None:
        normalized = str(key or "").strip()
        if not normalized or not self.path.exists():
            return None
        with self._lock, self._connect() as connection:
            if not self._table_exists(connection):
                return None
            row = connection.execute(
                "SELECT packet_json FROM presentation_packets WHERE cache_key = ?",
                (normalized,),
            ).fetchone()
            if row is None:
                return None
            try:
                packet = json.loads(str(row[0]))
            except (TypeError, ValueError):
                connection.execute(
                    "DELETE FROM presentation_packets WHERE cache_key = ?",
                    (normalized,),
                )
                return None
            if not isinstance(packet, dict):
                connection.execute(
                    "DELETE FROM presentation_packets WHERE cache_key = ?",
                    (normalized,),
                )
                return None
            connection.execute(
                "UPDATE presentation_packets SET accessed_at = ? WHERE cache_key = ?",
                (time.time_ns(), normalized),
            )
            return packet

    def put(self, key: str, packet: dict[str, Any]) -> None:
        normalized = str(key or "").strip()
        if not normalized:
            raise ValueError("presentation cache key is required")
        encoded = json.dumps(
            packet,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        timestamp = time.time_ns()
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                self._ensure_schema(connection)
                connection.execute(
                    """
                    INSERT INTO presentation_packets (
                        cache_key, packet_json, created_at, accessed_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        packet_json = excluded.packet_json,
                        created_at = excluded.created_at,
                        accessed_at = excluded.accessed_at
                    """,
                    (normalized, encoded, timestamp, timestamp),
                )
                connection.execute(
                    """
                    DELETE FROM presentation_packets
                    WHERE cache_key NOT IN (
                        SELECT cache_key
                        FROM presentation_packets
                        ORDER BY accessed_at DESC, created_at DESC, cache_key
                        LIMIT ?
                    )
                    """,
                    (self.maximum_entries,),
                )

    def discard(self, key: str) -> None:
        normalized = str(key or "").strip()
        if not normalized or not self.path.exists():
            return
        with self._lock, self._connect() as connection:
            if self._table_exists(connection):
                connection.execute(
                    "DELETE FROM presentation_packets WHERE cache_key = ?",
                    (normalized,),
                )

    def diagnostics(self) -> dict[str, Any]:
        """Return content-free cache health information."""

        result: dict[str, Any] = {
            "path": str(self.path),
            "exists": self.path.exists(),
            "maximum_entries": self.maximum_entries,
            "entry_count": 0,
            "healthy": True,
        }
        if not self.path.exists():
            return result
        try:
            with self._lock, self._connect() as connection:
                if self._table_exists(connection):
                    result["entry_count"] = int(
                        connection.execute(
                            "SELECT COUNT(*) FROM presentation_packets"
                        ).fetchone()[0]
                    )
        except (OSError, sqlite3.Error) as exc:
            result["healthy"] = False
            result["error"] = type(exc).__name__
            return result
        return result

    def entries_for_export(self) -> list[tuple[str, dict[str, Any]]]:
        """Read a stable packet snapshot without changing cache recency."""

        if not self.path.exists():
            return []
        with self._lock, self._connect() as connection:
            if not self._table_exists(connection):
                return []
            rows = connection.execute(
                """
                SELECT cache_key, packet_json
                FROM presentation_packets
                ORDER BY cache_key
                """
            ).fetchall()

        entries: list[tuple[str, dict[str, Any]]] = []
        for cache_key, encoded in rows:
            try:
                packet = json.loads(str(encoded))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"presentation cache entry {cache_key} is not valid JSON"
                ) from exc
            if not isinstance(packet, dict):
                raise ValueError(
                    f"presentation cache entry {cache_key} is not a packet object"
                )
            entries.append((str(cache_key), packet))
        return entries

    @staticmethod
    def _table_exists(connection: sqlite3.Connection) -> bool:
        return connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'presentation_packets'
            """
        ).fetchone() is not None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=1.0)

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS presentation_packets (
                cache_key TEXT PRIMARY KEY,
                packet_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                accessed_at INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_presentation_packets_accessed
            ON presentation_packets(accessed_at DESC)
            """
        )


def default_presentation_cache_path(study_db_path: str | Path) -> Path:
    path = Path(study_db_path)
    return path.with_name(f"{path.stem}.presentation-cache.sqlite")
