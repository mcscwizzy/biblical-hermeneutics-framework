"""Process-lifetime sharing for verified, read-only CKL repositories."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.database_builder import (
    manifest_fingerprint,
    source_inventory_fingerprint,
)
from framework.canonical_library.json_repository import JsonCanonicalRepository
from framework.canonical_library.repository import (
    is_vercel_runtime,
    repository_config_from_env,
)
from framework.canonical_library.retrieval.indexer import (
    inventory_content_signature,
    inventory_signature,
)
from framework.canonical_library.sqlite_repository import (
    SQLiteCanonicalLibrary,
    SQLiteCanonicalRepository,
)

from ..cold_start_diagnostics import diagnostic_stage


LOGGER = logging.getLogger(__name__)
_FileSignature = tuple[int, int, int, int, int] | None
_SourceSignatureKey = tuple[str, str, str]
_ProviderKey = tuple[Any, ...]
_MAX_VERIFY_MMAP_SIZE_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True)
class _SourceIdentity:
    key: _ProviderKey
    json_root: Path
    database_path: Path | None
    inventory_signature: str
    inventory_fingerprint: str
    manifest_fingerprint: str
    database_signature: _FileSignature
    vercel_runtime: bool


class VerifiedCKLProvider:
    """Single-flight owner of verified CKL state for one FastAPI app lifetime.

    Each call resolves configuration and a lightweight filesystem identity
    before consulting the cache. Changes to the configured source root,
    inventory file stats, manifest contents, or SQLite index file select a new
    cache entry. Successful validation lives until app shutdown.
    """

    def __init__(
        self,
        *,
        config_provider: Callable[[], CKLRepositoryConfig] | None = None,
        library_loader: Callable[[CKLRepositoryConfig], Any] | None = None,
    ) -> None:
        self._config_provider = config_provider or self._environment_config
        self._library_loader = library_loader
        self._condition = threading.Condition(threading.RLock())
        self._verified: dict[_ProviderKey, Any] = {}
        self._inflight: dict[_ProviderKey, Future[Any]] = {}
        self._source_signatures: dict[_SourceSignatureKey, str] = {}
        self._source_signature_inflight: dict[_SourceSignatureKey, Future[str]] = {}
        self._source_fingerprints: dict[_SourceSignatureKey, str] = {}
        self._source_fingerprint_inflight: dict[_SourceSignatureKey, Future[str]] = {}
        self._initialization_waiters = 0
        self._closed = False
        self._metrics = {
            "successful_initializations": 0,
            "failed_initializations": 0,
            "cache_hits": 0,
            "single_flight_waits": 0,
            "repository_constructions": 0,
            "index_integrity_verifications": 0,
            "source_manifest_validations": 0,
            "source_inventory_verifications": 0,
            "source_content_signature_computations": 0,
            "source_inventory_fingerprint_computations": 0,
            "inventory_fingerprint_comparisons": 0,
        }

    @staticmethod
    def _environment_config() -> CKLRepositoryConfig:
        return repository_config_from_env(CKLRepositoryConfig(read_only=True))

    def get_library(self) -> Any:
        """Return verified CKL state without doing initialization on an event loop."""

        config = self._config_provider()
        if not config.read_only:
            raise ValueError("the shared CKL provider requires a read-only repository")
        identity = self._source_identity(config)

        with self._condition:
            if self._closed:
                raise RuntimeError("the shared CKL provider is closed")
            cached = self._verified.get(identity.key)
            if cached is not None:
                self._metrics["cache_hits"] += 1
                return cached

            future = self._inflight.get(identity.key)
            if future is None:
                future = Future()
                self._inflight[identity.key] = future
                initialize = True
            else:
                self._metrics["single_flight_waits"] += 1
                self._initialization_waiters += 1
                self._condition.notify_all()
                initialize = False

        if not initialize:
            try:
                with diagnostic_stage("ckl_provider_single_flight_wait"):
                    return future.result()
            finally:
                with self._condition:
                    self._initialization_waiters -= 1
                    self._condition.notify_all()

        try:
            with diagnostic_stage("ckl_provider_initialization"):
                library = (
                    self._library_loader(config)
                    if self._library_loader is not None
                    else self._construct_verified_library(config, identity)
                )
                if self._source_identity(config).key != identity.key:
                    raise RuntimeError("CKL sources changed during repository initialization")
        except BaseException as exc:
            with self._condition:
                self._inflight.pop(identity.key, None)
                self._metrics["failed_initializations"] += 1
                future.set_exception(exc)
                self._condition.notify_all()
            raise

        with self._condition:
            self._inflight.pop(identity.key, None)
            if self._closed:
                _close_library(library)
                error = RuntimeError("the shared CKL provider closed during initialization")
                self._metrics["failed_initializations"] += 1
                future.set_exception(error)
                self._condition.notify_all()
                raise error
            self._verified[identity.key] = library
            self._metrics["successful_initializations"] += 1
            future.set_result(library)
            self._condition.notify_all()
            return library

    def snapshot(self) -> dict[str, int | bool]:
        """Return bounded process diagnostics without exposing source paths."""

        with self._condition:
            return {
                **self._metrics,
                "verified_entries": len(self._verified),
                "inflight_initializations": len(self._inflight),
                "initialization_waiters": self._initialization_waiters,
                "closed": self._closed,
            }

    def start(self) -> None:
        """Begin an application lifecycle after construction or prior shutdown."""

        with self._condition:
            if self._inflight:
                raise RuntimeError("the shared CKL provider cannot restart while initialization is active")
            self._closed = False

    def close(self) -> None:
        """Close verified repositories during application shutdown."""

        with self._condition:
            if self._closed:
                return
            self._closed = True
            libraries = list(self._verified.values())
            self._verified.clear()
            self._source_signatures.clear()
            self._source_fingerprints.clear()
            self._condition.notify_all()
        for library in libraries:
            _close_library(library)

    def _source_identity(self, config: CKLRepositoryConfig) -> _SourceIdentity:
        backend = str(config.backend or "").strip().lower()
        if backend not in {"json", "sqlite"}:
            raise ValueError(f"unsupported CKL backend: {backend}")
        json_root = (
            Path(config.json_root).expanduser().resolve(strict=False)
            if config.json_root
            else Path(__file__).resolve().parents[2] / "framework" / "canonical_library"
        )
        with diagnostic_stage("ckl_source_inventory_identity"):
            source_file_signature = inventory_signature(json_root)
            source_manifest = manifest_fingerprint(json_root)

        database_path: Path | None = None
        database_signature: _FileSignature = None
        if backend == "sqlite":
            database_path = Path(config.database_path).expanduser().resolve(strict=False)
            with diagnostic_stage("ckl_sqlite_index_discovery"):
                try:
                    stat = database_path.stat()
                    database_signature = (
                        stat.st_dev,
                        stat.st_ino,
                        stat.st_size,
                        stat.st_mtime_ns,
                        stat.st_ctime_ns,
                    )
                except FileNotFoundError:
                    database_signature = None

        source_signature = self._source_content_signature(
            json_root,
            source_file_signature,
            source_manifest,
        )
        source_fingerprint = ""
        if backend == "sqlite" and database_signature is not None:
            source_fingerprint = self._source_inventory_fingerprint(
                json_root,
                source_file_signature,
                source_manifest,
            )

        key: _ProviderKey = (
            backend,
            json_root.as_posix(),
            source_file_signature,
            source_signature,
            source_fingerprint,
            source_manifest,
            database_path.as_posix() if database_path else None,
            database_signature,
            str(config.stale_database_policy or "").strip().lower(),
            bool(config.read_only),
            max(int(config.cache_size), 1),
            is_vercel_runtime(),
        )
        return _SourceIdentity(
            key=key,
            json_root=json_root,
            database_path=database_path,
            inventory_signature=source_signature,
            inventory_fingerprint=source_fingerprint,
            manifest_fingerprint=source_manifest,
            database_signature=database_signature,
            vercel_runtime=is_vercel_runtime(),
        )

    def _construct_verified_library(self, config: CKLRepositoryConfig, identity: _SourceIdentity) -> Any:
        if config.backend.strip().lower() == "json":
            self._increment("repository_constructions")
            with diagnostic_stage("ckl_json_repository_construction"):
                repository = JsonCanonicalRepository(root=identity.json_root)
            self._increment("source_inventory_verifications")
            with diagnostic_stage("ckl_json_repository_readiness"):
                return repository.library

        assert identity.database_path is not None
        path = identity.database_path
        stale_policy = str(config.stale_database_policy or "").strip().lower()
        with diagnostic_stage("ckl_sqlite_index_discovery"):
            index_exists = path.is_file()
        if not index_exists:
            if identity.vercel_runtime:
                raise FileNotFoundError(
                    f"Vercel CKL SQLite index is missing at {path}; "
                    "the deployment build must generate and bundle it"
                )
            if stale_policy == "fallback_to_json":
                return self._load_json_fallback(identity.json_root)
            raise FileNotFoundError("canonical repository is unavailable")

        self._increment("repository_constructions")
        repository = None
        try:
            with diagnostic_stage("ckl_sqlite_repository_construction"):
                repository = SQLiteCanonicalRepository(
                    path,
                    read_only=True,
                    cache_size=config.cache_size,
                )
            self._increment("index_integrity_verifications")
            with diagnostic_stage("ckl_index_integrity_verification"):
                verify_mmap_size = min(path.stat().st_size, _MAX_VERIFY_MMAP_SIZE_BYTES)
                repository.verify(
                    root=identity.json_root,
                    compare_fingerprint=False,
                    mmap_size_bytes=verify_mmap_size,
                )

            metadata = repository.metadata
            self._increment("source_manifest_validations")
            with diagnostic_stage("ckl_source_manifest_validation"):
                recorded_manifest = metadata.get("source_manifest_fingerprint", "")
                manifest_stale = bool(
                    recorded_manifest
                    and recorded_manifest != identity.manifest_fingerprint
                )
                recorded_inventory_fingerprint = metadata.get("inventory_fingerprint", "")
                if identity.vercel_runtime:
                    required = (
                        "inventory_fingerprint",
                        "source_manifest_fingerprint",
                        "source_inventory_signature",
                    )
                    missing = [key for key in required if not metadata.get(key)]
                    if missing:
                        raise RuntimeError(
                            "Vercel CKL index is missing required source identity metadata: "
                            + ", ".join(missing)
                        )
                    if manifest_stale:
                        raise RuntimeError(
                            "Vercel CKL index manifest fingerprint does not match "
                            "the packaged JSON manifest"
                        )

            self._increment("source_inventory_verifications")
            with diagnostic_stage("ckl_inventory_fingerprint_verification"):
                self._increment("inventory_fingerprint_comparisons")
                inventory_fingerprint_stale = (
                    recorded_inventory_fingerprint != identity.inventory_fingerprint
                )
                recorded_source_signature = metadata.get("source_inventory_signature", "")
                source_stale = (
                    recorded_source_signature != identity.inventory_signature
                    if recorded_source_signature
                    else repository.is_stale(identity.json_root)
                )
            stale = manifest_stale or source_stale or inventory_fingerprint_stale
            if stale:
                if identity.vercel_runtime:
                    if inventory_fingerprint_stale:
                        raise RuntimeError(
                            "Vercel CKL index inventory fingerprint does not match "
                            "the validated packaged JSON inventory"
                        )
                    raise RuntimeError(
                        "Vercel CKL index is stale relative to the packaged JSON source inventory"
                    )
                repository.close()
                repository = None
                if stale_policy == "fallback_to_json":
                    return self._load_json_fallback(identity.json_root)
                raise RuntimeError("canonical repository is stale")

            with diagnostic_stage("ckl_repository_readiness"):
                library = SQLiteCanonicalLibrary(repository, root=identity.json_root)
            return library
        except BaseException:
            if repository is not None:
                repository.close()
            raise

    def _load_json_fallback(self, json_root: Path) -> Any:
        self._increment("repository_constructions")
        with diagnostic_stage("ckl_explicit_json_fallback"):
            repository = JsonCanonicalRepository(root=json_root)
        self._increment("source_inventory_verifications")
        return repository.library

    def _increment(self, key: str) -> None:
        with self._condition:
            self._metrics[key] += 1

    def _source_content_signature(
        self,
        root: Path,
        file_signature: str,
        manifest_fingerprint: str,
    ) -> str:
        key = (root.as_posix(), file_signature, manifest_fingerprint)
        with self._condition:
            cached = self._source_signatures.get(key)
            if cached is not None:
                return cached
            future = self._source_signature_inflight.get(key)
            if future is None:
                future = Future()
                self._source_signature_inflight[key] = future
                initialize = True
            else:
                initialize = False

        if not initialize:
            with diagnostic_stage("ckl_source_content_signature_wait"):
                return future.result()

        try:
            with diagnostic_stage("ckl_source_content_signature"):
                signature = inventory_content_signature(root)
        except BaseException as exc:
            with self._condition:
                self._source_signature_inflight.pop(key, None)
                future.set_exception(exc)
                self._condition.notify_all()
            raise

        with self._condition:
            self._source_signature_inflight.pop(key, None)
            if not self._closed:
                self._source_signatures[key] = signature
            self._metrics["source_content_signature_computations"] += 1
            future.set_result(signature)
            self._condition.notify_all()
        return signature

    def _source_inventory_fingerprint(
        self,
        root: Path,
        file_signature: str,
        manifest_fingerprint_value: str,
    ) -> str:
        key = (root.as_posix(), file_signature, manifest_fingerprint_value)
        with self._condition:
            cached = self._source_fingerprints.get(key)
            if cached is not None:
                return cached
            future = self._source_fingerprint_inflight.get(key)
            if future is None:
                future = Future()
                self._source_fingerprint_inflight[key] = future
                initialize = True
            else:
                initialize = False

        if not initialize:
            with diagnostic_stage("ckl_source_inventory_fingerprint_wait"):
                return future.result()

        try:
            with diagnostic_stage("ckl_source_inventory_fingerprint_computation"):
                fingerprint = source_inventory_fingerprint(root)
        except BaseException as exc:
            with self._condition:
                self._source_fingerprint_inflight.pop(key, None)
                future.set_exception(exc)
                self._condition.notify_all()
            raise

        with self._condition:
            self._source_fingerprint_inflight.pop(key, None)
            if not self._closed:
                self._source_fingerprints[key] = fingerprint
            self._metrics["source_inventory_fingerprint_computations"] += 1
            future.set_result(fingerprint)
            self._condition.notify_all()
        return fingerprint


def _close_library(library: Any) -> None:
    close = getattr(library, "close", None)
    if not callable(close):
        return
    try:
        close()
    except Exception:  # noqa: BLE001 - shutdown must still close remaining resources
        LOGGER.exception("Could not close shared CKL repository during shutdown")
