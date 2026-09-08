"""Small, content-addressed contracts used by Commentary production."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


PRODUCTION_VERSION = "commentary-production-v1"
PRODUCTION_ROOT_RELATIVE = Path(".bhf-data/bhf-commentary-production/v1")
MANIFEST_STATUS = "PLANNED_NOT_AUTHORIZED"
AUTHORIZATION_STATUS = "AUTHORIZED"
DEFAULT_CANARY_LIMIT = 50
DEFAULT_SYSTEMIC_PROVIDER_FAILURE_THRESHOLD = 3

PENDING = "PENDING"
READY = "READY"
GENERATING = "GENERATING"
RAW_CAPTURED = "RAW_CAPTURED"
VALIDATING = "VALIDATING"
ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"
GATE_PASS = "GATE_PASS"
GATE_WARNING = "GATE_WARNING"
GATE_QUALITY_FAIL = "GATE_QUALITY_FAIL"
DENSE_READER_PENDING = "DENSE_READER_PENDING"
DENSE_READER_COMPLETE = "DENSE_READER_COMPLETE"
COMPLETE = "COMPLETE"
QUARANTINED = "QUARANTINED"
STALE_INPUT = "STALE_INPUT"
BLOCKED = "BLOCKED"

TERMINAL_STATES = frozenset(
    {COMPLETE, GATE_QUALITY_FAIL, QUARANTINED, STALE_INPUT, BLOCKED}
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    PENDING: frozenset({READY, GENERATING, STALE_INPUT, BLOCKED}),
    READY: frozenset({GENERATING, STALE_INPUT, BLOCKED}),
    GENERATING: frozenset({RAW_CAPTURED, QUARANTINED, BLOCKED}),
    RAW_CAPTURED: frozenset({VALIDATING, QUARANTINED, BLOCKED}),
    VALIDATING: frozenset({ACCEPTED, REJECTED, QUARANTINED, BLOCKED}),
    ACCEPTED: frozenset({GATE_PASS, GATE_WARNING, GATE_QUALITY_FAIL, QUARANTINED}),
    REJECTED: frozenset({QUARANTINED}),
    GATE_PASS: frozenset({DENSE_READER_PENDING, COMPLETE}),
    GATE_WARNING: frozenset({DENSE_READER_PENDING, COMPLETE}),
    GATE_QUALITY_FAIL: frozenset(),
    DENSE_READER_PENDING: frozenset({DENSE_READER_COMPLETE, COMPLETE}),
    DENSE_READER_COMPLETE: frozenset({COMPLETE}),
    COMPLETE: frozenset(),
    QUARANTINED: frozenset(),
    STALE_INPUT: frozenset(),
    BLOCKED: frozenset(),
}


class ProductionError(RuntimeError):
    """Base error for a fail-closed production operation."""


class ManifestError(ProductionError):
    """A manifest is malformed, changed, or not suitable for execution."""


class ArtifactCollisionError(ProductionError):
    """An immutable artifact path already contains different bytes."""


class SystemicBatchFailure(ProductionError):
    """A batch-level failure requires stopping before more chapters run."""


class RetryPolicyDisabled(ProductionError):
    """Content retries are intentionally not enabled by production v1."""


@dataclass(frozen=True)
class InputIdentity:
    evidence_hash: str
    synthesis_hash: str
    prompt_version: str
    commentary_schema_version: str
    synthesis_schema_version: str
    synthesis_compiler_version: str
    gate_version: str
    validator_identity: str
    packet_hash: str
    packet_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_hash": self.evidence_hash,
            "synthesis_hash": self.synthesis_hash,
            "prompt_version": self.prompt_version,
            "commentary_schema_version": self.commentary_schema_version,
            "synthesis_schema_version": self.synthesis_schema_version,
            "synthesis_compiler_version": self.synthesis_compiler_version,
            "gate_version": self.gate_version,
            "validator_identity": self.validator_identity,
            "packet_hash": self.packet_hash,
            "packet_id": self.packet_id,
        }


@dataclass(frozen=True)
class GenerationConfig:
    provider_adapter: str
    model: str
    effort: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    runner_version: str = PRODUCTION_VERSION
    reader_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_adapter": self.provider_adapter,
            "model": self.model,
            "effort": self.effort,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "runner_version": self.runner_version,
            "reader_enabled": self.reader_enabled,
        }


@dataclass(frozen=True)
class PreparedChapter:
    """A locked input packet plus the live objects needed during execution."""

    row: dict[str, Any]
    bundle: Any | None = field(default=None, repr=False, compare=False)
    synthesis: Any | None = field(default=None, repr=False, compare=False)
    packet: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_bytes(value)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_immutable(path: Path, value: bytes) -> str:
    digest = sha256_bytes(value)
    if path.exists():
        existing = path.read_bytes()
        if existing != value:
            raise ArtifactCollisionError(f"immutable artifact collision: {path}")
        return sha256_bytes(existing)
    atomic_write_bytes(path, value)
    return digest


def write_json(path: Path, value: Any, *, immutable: bool = False) -> str:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    return write_immutable(path, payload) if immutable else _write_json_atomic(path, payload)


def _write_json_atomic(path: Path, payload: bytes) -> str:
    atomic_write_bytes(path, payload)
    return sha256_bytes(payload)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionError(f"invalid production JSON artifact {path}: {exc}") from exc


def transition(current: str, target: str) -> str:
    if current == target:
        return current
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise ProductionError(f"invalid production state transition: {current} -> {target}")
    return target


def slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{int(chapter):03d}"


def production_root(repo_root: Path) -> Path:
    return repo_root / PRODUCTION_ROOT_RELATIVE
