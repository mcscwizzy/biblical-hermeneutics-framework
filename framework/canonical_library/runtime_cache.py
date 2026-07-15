"""In-memory runtime caches for deterministic CKL-backed requests."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict, dataclass
from threading import RLock
from typing import Any, Mapping, Sequence

from .normalization import normalize_id, normalize_text


CACHE_KEY_VERSION = 1
DEFAULT_MAX_ENTRIES = 512


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _cache_key(namespace: str, payload: Any) -> str:
    return f"{namespace}:{_stable_digest(payload)}"


def _normalized_text(value: Any) -> str:
    return normalize_text(str(value or "")).strip()


def _normalized_sequence(values: Sequence[Any] | None) -> list[str]:
    if not values:
        return []
    items: list[str] = []
    for value in values:
        text = _normalized_text(value)
        if text and text not in items:
            items.append(text)
    return items


def _entry_version_signature(entries: Sequence[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    signature: list[dict[str, str]] = []
    if not entries:
        return signature
    for item in entries:
        object_id = normalize_id(str(item.get("id") or "").strip())
        if not object_id:
            continue
        version = str(
            item.get("object_version")
            or item.get("version")
            or ""
        ).strip() or "unknown"
        signature.append({"id": object_id, "version": version})
    return signature


def build_retrieval_cache_key(
    *,
    canonical_query: str,
    inventory_fingerprint: str,
    answer_mode: str,
    max_results: int,
    include_placeholders: bool,
    allowed_statuses: Sequence[str] | None,
    max_context_tokens: int,
) -> str:
    payload = {
        "cache_key_version": CACHE_KEY_VERSION,
        "canonical_query": _normalized_text(canonical_query),
        "inventory_fingerprint": str(inventory_fingerprint or "").strip(),
        "answer_mode": str(answer_mode or "study").strip().lower() or "study",
        "max_results": int(max_results),
        "include_placeholders": bool(include_placeholders),
        "allowed_statuses": _normalized_sequence(allowed_statuses),
        "max_context_tokens": int(max_context_tokens),
    }
    return _cache_key("retrieval", payload)


def build_context_cache_key(
    *,
    canonical_query: str,
    retrieved_topics: Sequence[Mapping[str, Any]] | None,
    answer_mode: str,
    max_context_tokens: int,
    prompt_mode: str,
    prompt_version: str,
) -> str:
    payload = {
        "cache_key_version": CACHE_KEY_VERSION,
        "canonical_query": _normalized_text(canonical_query),
        "answer_mode": str(answer_mode or "study").strip().lower() or "study",
        "max_context_tokens": int(max_context_tokens),
        "prompt_mode": str(prompt_mode or "summary").strip().lower() or "summary",
        "prompt_version": str(prompt_version or "").strip(),
        "retrieved_entries": _entry_version_signature(retrieved_topics),
    }
    return _cache_key("context", payload)


def build_model_signature(
    *,
    adapter: str,
    base_url: str | None,
    model: str | None,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    return {
        "adapter": str(adapter or "").strip(),
        "base_url": str(base_url or "").strip(),
        "model": str(model or "").strip(),
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }


def build_prompt_context_hash(
    *,
    normalized_question: str,
    canonical_query: str,
    canonical_context_cache_key: str,
    reference_context: Mapping[str, Any] | None,
    genre_context: Mapping[str, Any] | None,
    question_context: Mapping[str, Any] | None,
    local_knowledge_keys: Sequence[str] | None,
    map_tool_keys: Sequence[str] | None,
    session_memory: Mapping[str, Any] | None,
    profile_name: str | None,
    answer_mode: str,
    show_method_notes: bool,
    prompt_version: str,
    prompt_mode: str,
) -> str:
    payload = {
        "cache_key_version": CACHE_KEY_VERSION,
        "prompt_version": str(prompt_version or "").strip(),
        "normalized_question": _normalized_text(normalized_question),
        "canonical_query": _normalized_text(canonical_query),
        "canonical_context_cache_key": str(canonical_context_cache_key or "").strip(),
        "reference_context": dict(reference_context or {}),
        "genre_context": dict(genre_context or {}),
        "question_context": dict(question_context or {}),
        "local_knowledge_keys": _normalized_sequence(local_knowledge_keys),
        "map_tool_keys": _normalized_sequence(map_tool_keys),
        "session_memory": dict(session_memory or {}),
        "profile_name": str(profile_name or "").strip(),
        "answer_mode": str(answer_mode or "study").strip().lower() or "study",
        "show_method_notes": bool(show_method_notes),
        "prompt_mode": str(prompt_mode or "").strip().lower(),
    }
    return _cache_key("prompt", payload)


def build_response_cache_key(
    *,
    normalized_question: str,
    prompt_context_hash: str,
    model_signature: Mapping[str, Any],
    response_contract: str,
    prompt_version: str,
) -> str:
    payload = {
        "cache_key_version": CACHE_KEY_VERSION,
        "normalized_question": _normalized_text(normalized_question),
        "prompt_context_hash": str(prompt_context_hash or "").strip(),
        "model_signature": dict(model_signature),
        "response_contract": str(response_contract or "").strip(),
        "prompt_version": str(prompt_version or "").strip(),
    }
    return _cache_key("response", payload)


@dataclass
class CacheLayerStats:
    hits: int = 0
    misses: int = 0
    stores: int = 0
    evictions: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class CacheRecord:
    payload: Any
    created_at: str


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class _MemoryCacheLayer:
    def __init__(self, max_entries: int) -> None:
        self.max_entries = max(1, int(max_entries))
        self._records: OrderedDict[str, CacheRecord] = OrderedDict()
        self._lock = RLock()
        self.stats = CacheLayerStats()

    def lookup(self, key: str) -> Any | None:
        with self._lock:
            record = self._records.get(key)
            if record is None:
                self.stats.misses += 1
                return None
            self.stats.hits += 1
            self._records.move_to_end(key)
            return deepcopy(record.payload)

    def store(self, key: str, payload: Any) -> None:
        with self._lock:
            self._records[key] = CacheRecord(payload=deepcopy(payload), created_at=_now_iso())
            self._records.move_to_end(key)
            self.stats.stores += 1
            while len(self._records) > self.max_entries:
                self._records.popitem(last=False)
                self.stats.evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = self.stats.to_dict()
            data["size"] = len(self._records)
            data["max_entries"] = self.max_entries
            return data


class CKLRuntimeCache:
    """Thread-safe in-memory cache for CKL retrieval, context, and responses."""

    def __init__(self, *, enabled: bool = True, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self.enabled = bool(enabled)
        self.max_entries = max(1, int(max_entries))
        self.retrieval = _MemoryCacheLayer(self.max_entries)
        self.context = _MemoryCacheLayer(self.max_entries)
        self.response = _MemoryCacheLayer(self.max_entries)

    def lookup_retrieval(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        return self.retrieval.lookup(key)

    def store_retrieval(self, key: str, payload: Any) -> None:
        if not self.enabled:
            return None
        self.retrieval.store(key, payload)

    def lookup_context(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        return self.context.lookup(key)

    def store_context(self, key: str, payload: Any) -> None:
        if not self.enabled:
            return None
        self.context.store(key, payload)

    def lookup_response(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        return self.response.lookup(key)

    def store_response(self, key: str, payload: Any) -> None:
        if not self.enabled:
            return None
        self.response.store(key, payload)

    def clear(self) -> None:
        self.retrieval.clear()
        self.context.clear()
        self.response.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "retrieval": self.retrieval.snapshot(),
            "context": self.context.snapshot(),
            "response": self.response.snapshot(),
        }

