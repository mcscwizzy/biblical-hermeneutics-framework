"""Approved-answer cache helpers for the Canonical Knowledge Library.

The public answer cache is intentionally conservative. It only serves reviewed
answers when the current CKL inventory fingerprint and framework fingerprint
still match the cached entry.
"""

from __future__ import annotations

import hashlib
import json
from importlib import metadata
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .normalization import normalize_id, normalize_text
from .schema import REVIEW_STATUS_VALUES


CACHE_SCHEMA_VERSION = 1
DEFAULT_PUBLIC_CACHE_PATH = Path(".bhf/public-answer-cache.json")
DEFAULT_ALLOWED_REVIEW_STATUSES: tuple[str, ...] = (
    "reviewed",
    "approved",
)
DEFAULT_MINIMUM_QUALITY_SCORE = 80.0
DEFAULT_TTL_DAYS = 365
_DISTRIBUTION_NAME = "biblical-hermeneutics-framework"

_FRAMEWORK_VERSION_PATH = Path(__file__).resolve().parents[2] / "VERSION"


def _stable_digest(data: Any) -> str:
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat().replace("+00:00", "Z")


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def load_framework_version(default: str = "unknown") -> str:
    """Return the installed release version when available."""

    try:
        version = metadata.version(_DISTRIBUTION_NAME).strip()
    except metadata.PackageNotFoundError:
        version = ""
    if version:
        return version
    try:
        version = _FRAMEWORK_VERSION_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default
    return version or default


def load_framework_version_fingerprint(version: str | None = None) -> str:
    """Return a stable fingerprint for the current framework version line."""

    version_text = str(version or load_framework_version()).strip() or "unknown"
    return _stable_digest({"framework_version": version_text})


def normalize_public_question(question: str) -> str:
    """Return the canonical cache key question form."""

    return normalize_text(question)


def normalize_public_answer_mode(answer_mode: str | None) -> str:
    """Return the canonical cache key answer-mode form."""

    normalized = " ".join(str(answer_mode or "study").split()).strip().lower()
    return normalized or "study"


def public_cache_key(normalized_question: str, answer_mode: str) -> str:
    """Build the stable lookup key used by the public answer cache."""

    return f"{normalize_public_question(normalized_question)}\u0000{normalize_public_answer_mode(answer_mode)}"


def _coerce_object_dependency_ids(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple)):
        candidates = [str(item) for item in value]
    else:
        raise ValueError("object_dependency_ids must be a string or a list of strings")

    normalized = [normalize_id(candidate) for candidate in candidates]
    deduped = tuple(dict.fromkeys(item for item in normalized if item))
    return deduped


def _default_expiry(days: int | None) -> str | None:
    if days is None:
        return None
    return (_now_utc() + timedelta(days=int(days))).isoformat().replace("+00:00", "Z")


def _valid_review_statuses(statuses: Sequence[str]) -> tuple[str, ...]:
    cleaned = tuple(
        dict.fromkeys(
            str(status).strip().lower()
            for status in statuses
            if str(status).strip()
        )
    )
    if not cleaned:
        raise ValueError("allowed_review_statuses must not be empty")
    invalid = sorted(set(cleaned) - set(REVIEW_STATUS_VALUES))
    if invalid:
        raise ValueError(
            "allowed_review_statuses must be one of: " + ", ".join(REVIEW_STATUS_VALUES)
        )
    return cleaned


@dataclass(frozen=True)
class PublicCacheEntry:
    normalized_question: str
    answer_mode: str = "study"
    answer: str = ""
    quality_score: float = 0.0
    usage_count: int = 0
    review_status: str = "reviewed"
    framework_version: str = ""
    framework_version_fingerprint: str = ""
    ckl_version_fingerprint: str = ""
    object_dependency_ids: tuple[str, ...] = field(default_factory=tuple)
    created_at: str | None = None
    updated_at: str | None = None
    expires_at: str | None = None
    invalidated_at: str | None = None
    invalidated_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["object_dependency_ids"] = list(self.object_dependency_ids)
        return data

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "PublicCacheEntry":
        normalized_question = normalize_public_question(str(mapping.get("normalized_question", "")))
        if not normalized_question:
            raise ValueError("normalized_question must not be blank")
        answer_mode = normalize_public_answer_mode(mapping.get("answer_mode"))
        answer = str(mapping.get("answer", "") or "")
        try:
            quality_score = float(mapping.get("quality_score", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("quality_score must be numeric") from exc
        try:
            usage_count = int(mapping.get("usage_count", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("usage_count must be an integer") from exc
        review_status = (
            str(mapping.get("review_status", "reviewed") or "reviewed")
            .strip()
            .lower()
            or "reviewed"
        )
        framework_version = str(mapping.get("framework_version", "") or "").strip()
        framework_version_fingerprint = str(
            mapping.get("framework_version_fingerprint", "") or ""
        ).strip()
        ckl_version_fingerprint = str(mapping.get("ckl_version_fingerprint", "") or "").strip()
        object_dependency_ids = _coerce_object_dependency_ids(
            mapping.get("object_dependency_ids", ())
        )
        created_at = str(mapping.get("created_at")).strip() if mapping.get("created_at") else None
        updated_at = str(mapping.get("updated_at")).strip() if mapping.get("updated_at") else None
        expires_at = str(mapping.get("expires_at")).strip() if mapping.get("expires_at") else None
        invalidated_at = (
            str(mapping.get("invalidated_at")).strip() if mapping.get("invalidated_at") else None
        )
        invalidated_reason = (
            str(mapping.get("invalidated_reason")).strip()
            if mapping.get("invalidated_reason")
            else None
        )
        return cls(
            normalized_question=normalized_question,
            answer_mode=answer_mode,
            answer=answer,
            quality_score=quality_score,
            usage_count=usage_count,
            review_status=review_status,
            framework_version=framework_version,
            framework_version_fingerprint=framework_version_fingerprint,
            ckl_version_fingerprint=ckl_version_fingerprint,
            object_dependency_ids=object_dependency_ids,
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            invalidated_at=invalidated_at,
            invalidated_reason=invalidated_reason,
        )


class PublicAnswerCache(Protocol):
    def lookup(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        *,
        ckl_version_fingerprint: str | None = None,
        framework_version_fingerprint: str | None = None,
    ) -> PublicCacheEntry | None:
        ...

    def store(self, entry: PublicCacheEntry) -> None:
        ...

    def increment_usage(self, normalized_question: str, answer_mode: str = "study") -> None:
        ...

    def update_review_status(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        status: str = "",
    ) -> None:
        ...


class NullPublicAnswerCache:
    """No-op cache implementation used when the feature is disabled."""

    last_lookup_status: str = "disabled"
    last_lookup_reason: str | None = None
    last_lookup_key: str | None = None
    last_lookup_entry: PublicCacheEntry | None = None

    def lookup(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        *,
        ckl_version_fingerprint: str | None = None,
        framework_version_fingerprint: str | None = None,
    ) -> PublicCacheEntry | None:  # noqa: ARG002 - protocol surface
        self.last_lookup_status = "disabled"
        self.last_lookup_reason = None
        self.last_lookup_key = public_cache_key(normalized_question, answer_mode)
        self.last_lookup_entry = None
        return None

    def store(self, entry: PublicCacheEntry) -> None:  # noqa: ARG002 - no-op
        return None

    def increment_usage(self, normalized_question: str, answer_mode: str = "study") -> None:  # noqa: ARG002 - no-op
        return None

    def update_review_status(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        status: str = "",
    ) -> None:  # noqa: ARG002 - no-op
        return None


class JsonPublicAnswerCache:
    """Small JSON-backed cache for reviewed public answers."""

    def __init__(
        self,
        path: str | Path,
        *,
        minimum_quality_score: float = DEFAULT_MINIMUM_QUALITY_SCORE,
        allowed_review_statuses: Sequence[str] = DEFAULT_ALLOWED_REVIEW_STATUSES,
        default_ttl_days: int | None = DEFAULT_TTL_DAYS,
    ) -> None:
        self.path = Path(path).expanduser()
        self.minimum_quality_score = float(minimum_quality_score)
        if not 0 <= self.minimum_quality_score <= 100:
            raise ValueError("minimum_quality_score must be between 0 and 100")
        self.allowed_review_statuses = _valid_review_statuses(allowed_review_statuses)
        if default_ttl_days is not None and int(default_ttl_days) <= 0:
            raise ValueError("default_ttl_days must be greater than 0")
        self.default_ttl_days = int(default_ttl_days) if default_ttl_days is not None else None
        self.last_lookup_status: str = "miss"
        self.last_lookup_reason: str | None = None
        self.last_lookup_key: str | None = None
        self.last_lookup_entry: PublicCacheEntry | None = None

    def lookup(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        *,
        ckl_version_fingerprint: str | None = None,
        framework_version_fingerprint: str | None = None,
    ) -> PublicCacheEntry | None:
        key = public_cache_key(normalized_question, answer_mode)
        self.last_lookup_key = key
        self.last_lookup_entry = None

        state = self._read_state()
        entry_mapping = self._entries(state).get(key)
        if not isinstance(entry_mapping, Mapping):
            self.last_lookup_status = "miss"
            self.last_lookup_reason = "no matching entry"
            return None

        entry = PublicCacheEntry.from_mapping(entry_mapping)
        if entry.invalidated_at:
            self.last_lookup_status = "stale"
            self.last_lookup_reason = entry.invalidated_reason or "entry already invalidated"
            return None
        if entry.review_status not in self.allowed_review_statuses:
            self.last_lookup_status = "filtered"
            self.last_lookup_reason = f"review_status {entry.review_status!r} is not allowed"
            return None
        if entry.quality_score < self.minimum_quality_score:
            self.last_lookup_status = "filtered"
            self.last_lookup_reason = (
                f"quality_score {entry.quality_score} is below "
                f"minimum_quality_score {self.minimum_quality_score}"
            )
            return None

        expiry = _parse_iso_datetime(entry.expires_at)
        if expiry is not None and expiry <= _now_utc():
            self._invalidate_entry(state, key, entry, reason="entry expired")
            self.last_lookup_status = "stale"
            self.last_lookup_reason = "entry expired"
            return None

        fingerprint_reason = self._fingerprint_mismatch_reason(
            entry,
            ckl_version_fingerprint=ckl_version_fingerprint,
            framework_version_fingerprint=framework_version_fingerprint,
        )
        if fingerprint_reason is not None:
            self._invalidate_entry(state, key, entry, reason=fingerprint_reason)
            self.last_lookup_status = "stale"
            self.last_lookup_reason = fingerprint_reason
            return None

        self.last_lookup_status = "hit"
        self.last_lookup_reason = None
        self.last_lookup_entry = entry
        return entry

    def store(self, entry: PublicCacheEntry) -> None:
        normalized = self._normalize_entry(entry)
        key = public_cache_key(normalized.normalized_question, normalized.answer_mode)
        state = self._read_state()
        entries = self._entries(state)
        existing_mapping = entries.get(key)
        existing = (
            PublicCacheEntry.from_mapping(existing_mapping)
            if isinstance(existing_mapping, Mapping)
            else None
        )
        now = _now_iso()
        created_at = normalized.created_at or (existing.created_at if existing else now)
        usage_count = max(normalized.usage_count, existing.usage_count if existing else 0)
        expires_at = normalized.expires_at or _default_expiry(self.default_ttl_days)
        stored = replace(
            normalized,
            created_at=created_at,
            updated_at=now,
            usage_count=usage_count,
            expires_at=expires_at,
            invalidated_at=None,
            invalidated_reason=None,
        )
        entries[key] = stored.to_dict()
        self._write_state(state)

    def increment_usage(self, normalized_question: str, answer_mode: str = "study") -> None:
        key = public_cache_key(normalized_question, answer_mode)
        state = self._read_state()
        entries = self._entries(state)
        mapping = entries.get(key)
        if not isinstance(mapping, Mapping):
            return None
        entry = PublicCacheEntry.from_mapping(mapping)
        updated = replace(entry, usage_count=entry.usage_count + 1, updated_at=_now_iso())
        entries[key] = updated.to_dict()
        self._write_state(state)

    def update_review_status(
        self,
        normalized_question: str,
        answer_mode: str = "study",
        status: str = "",
    ) -> None:
        normalized_status = str(status).strip().lower()
        if not normalized_status:
            raise ValueError("status must not be blank")
        key = public_cache_key(normalized_question, answer_mode)
        state = self._read_state()
        entries = self._entries(state)
        mapping = entries.get(key)
        if not isinstance(mapping, Mapping):
            return None
        entry = PublicCacheEntry.from_mapping(mapping)
        updated = replace(
            entry,
            review_status=normalized_status,
            updated_at=_now_iso(),
        )
        entries[key] = updated.to_dict()
        self._write_state(state)

    def _normalize_entry(self, entry: PublicCacheEntry) -> PublicCacheEntry:
        normalized_question = normalize_public_question(entry.normalized_question)
        if not normalized_question:
            raise ValueError("normalized_question must not be blank")
        answer_mode = normalize_public_answer_mode(entry.answer_mode)
        if not entry.answer.strip():
            raise ValueError("answer must not be blank")
        if not 0 <= float(entry.quality_score) <= 100:
            raise ValueError("quality_score must be between 0 and 100")
        if int(entry.usage_count) < 0:
            raise ValueError("usage_count must be greater than or equal to 0")
        dependency_ids = _coerce_object_dependency_ids(entry.object_dependency_ids)
        review_status = str(entry.review_status).strip().lower() or "reviewed"
        return replace(
            entry,
            normalized_question=normalized_question,
            answer_mode=answer_mode,
            answer=entry.answer.strip(),
            review_status=review_status,
            object_dependency_ids=dependency_ids,
            framework_version=str(entry.framework_version).strip() or load_framework_version(),
            framework_version_fingerprint=str(entry.framework_version_fingerprint).strip()
            or load_framework_version_fingerprint(entry.framework_version or None),
            ckl_version_fingerprint=str(entry.ckl_version_fingerprint).strip(),
        )

    def _fingerprint_mismatch_reason(
        self,
        entry: PublicCacheEntry,
        *,
        ckl_version_fingerprint: str | None,
        framework_version_fingerprint: str | None,
    ) -> str | None:
        if framework_version_fingerprint is not None:
            cached = str(entry.framework_version_fingerprint).strip()
            if not cached:
                return "framework version fingerprint missing"
            if cached != framework_version_fingerprint:
                return "framework version fingerprint changed"
        if ckl_version_fingerprint is not None:
            cached = str(entry.ckl_version_fingerprint).strip()
            if not cached:
                return "CKL version fingerprint missing"
            if cached != ckl_version_fingerprint:
                return "CKL version fingerprint changed"
        return None

    def _invalidate_entry(
        self,
        state: dict[str, Any],
        key: str,
        entry: PublicCacheEntry,
        *,
        reason: str,
    ) -> None:
        entries = self._entries(state)
        invalidated = replace(
            entry,
            updated_at=_now_iso(),
            invalidated_at=_now_iso(),
            invalidated_reason=reason,
        )
        entries[key] = invalidated.to_dict()
        self._write_state(state)

    def _read_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
        except Exception:
            return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
        if not isinstance(raw, dict):
            return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}
        entries = raw.get("entries")
        if not isinstance(entries, dict):
            entries = {}
        return {
            "schema_version": int(raw.get("schema_version", CACHE_SCHEMA_VERSION)),
            "entries": entries,
        }

    def _write_state(self, state: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "entries": self._entries(state),
        }
        tmp_path = self.path.with_name(f"{self.path.name}.tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(self.path)

    def _entries(self, state: Mapping[str, Any]) -> dict[str, Any]:
        entries = state.get("entries", {})
        if isinstance(entries, dict):
            return entries
        return {}
