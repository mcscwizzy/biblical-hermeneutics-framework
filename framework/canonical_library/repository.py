"""Repository abstraction and backend factory for the CKL runtime store."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .database_schema import DEFAULT_CKL_DATABASE_PATH
from .loader import CanonicalLibrary
from .retrieval import RetrievalResult
from .schema import CanonicalObject


class CanonicalRepository(Protocol):
    def get_by_id(self, object_id: str) -> CanonicalObject | None: ...

    def get_by_alias(self, alias: str, *, category: str | None = None) -> list[CanonicalObject]: ...

    def get_by_title(self, title: str, *, category: str | None = None) -> list[CanonicalObject]: ...

    def list_by_type(self, object_type: str) -> list[CanonicalObject]: ...

    def search_keywords(
        self,
        terms: Sequence[str],
        *,
        categories: Sequence[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalResult]: ...

    def get_relationships(self, object_id: str, *, minimum_weight: int = 1) -> list[dict[str, object]]: ...

    def get_scripture_matches(self, reference: str, *, limit: int = 10) -> list[RetrievalResult]: ...

    def inventory_fingerprint(self) -> str: ...


@dataclass(frozen=True)
class CKLRepositoryConfig:
    backend: str = "sqlite"
    database_path: str = DEFAULT_CKL_DATABASE_PATH
    json_root: str | None = None
    stale_database_policy: str = "fallback_to_json"
    read_only: bool = True
    cache_size: int = 256


def vercel_ckl_database_path() -> Path:
    """Resolve the build-generated index beside the packaged CKL sources."""

    return Path(__file__).resolve().parent / "data" / "ckl.sqlite"


def is_vercel_runtime() -> bool:
    return os.environ.get("VERCEL") == "1"


def _vercel_repository_config(base: CKLRepositoryConfig) -> CKLRepositoryConfig:
    expected_database = vercel_ckl_database_path()
    expected_root = expected_database.parent.parent

    backend_override = os.environ.get("BHF_CKL_BACKEND")
    if backend_override and backend_override.strip().lower() != "sqlite":
        raise ValueError("BHF_CKL_BACKEND must be sqlite when running on Vercel")

    database_override = os.environ.get("BHF_CKL_DATABASE_PATH")
    if database_override and Path(database_override).expanduser().resolve() != expected_database:
        raise ValueError("BHF_CKL_DATABASE_PATH conflicts with the packaged Vercel CKL index path")

    root_override = os.environ.get("BHF_CKL_ROOT")
    if root_override and Path(root_override).expanduser().resolve() != expected_root:
        raise ValueError("BHF_CKL_ROOT conflicts with the packaged Vercel CKL source root")

    stale_override = os.environ.get("BHF_CKL_STALE_DATABASE_POLICY")
    if stale_override and stale_override.strip().lower() != "error":
        raise ValueError("BHF_CKL_STALE_DATABASE_POLICY must be error when running on Vercel")

    if base.backend.strip().lower() != "sqlite":
        raise ValueError("CKL backend must be sqlite when running on Vercel")
    if base.database_path != DEFAULT_CKL_DATABASE_PATH and Path(base.database_path).expanduser().resolve() != expected_database:
        raise ValueError("CKL database path conflicts with the packaged Vercel CKL index path")
    if base.json_root and Path(base.json_root).expanduser().resolve() != expected_root:
        raise ValueError("CKL JSON source root conflicts with the packaged Vercel CKL source root")
    if base.stale_database_policy not in {"fallback_to_json", "error"}:
        raise ValueError("CKL stale database policy must fail closed when running on Vercel")
    if not base.read_only:
        raise ValueError("CKL repository must be read-only when running on Vercel")

    return CKLRepositoryConfig(
        backend="sqlite",
        database_path=str(expected_database),
        json_root=str(expected_root),
        stale_database_policy="error",
        read_only=True,
        cache_size=base.cache_size,
    )


def repository_config_from_env(base: CKLRepositoryConfig | None = None) -> CKLRepositoryConfig:
    config = base or CKLRepositoryConfig()
    if is_vercel_runtime():
        return _vercel_repository_config(config)
    return CKLRepositoryConfig(
        backend=os.environ.get("BHF_CKL_BACKEND", config.backend).strip().lower() or config.backend,
        database_path=os.environ.get("BHF_CKL_DATABASE_PATH", config.database_path).strip() or config.database_path,
        json_root=os.environ.get("BHF_CKL_ROOT", config.json_root or "").strip() or config.json_root,
        stale_database_policy=os.environ.get(
            "BHF_CKL_STALE_DATABASE_POLICY",
            config.stale_database_policy,
        ).strip().lower()
        or config.stale_database_policy,
        read_only=config.read_only,
        cache_size=config.cache_size,
    )


def load_canonical_repository(config: CKLRepositoryConfig | None = None) -> CanonicalRepository:
    config = repository_config_from_env(config)
    if config.backend == "json":
        from .json_repository import JsonCanonicalRepository

        return JsonCanonicalRepository(root=Path(config.json_root) if config.json_root else None)
    if config.backend != "sqlite":
        raise ValueError(f"unsupported CKL backend: {config.backend}")

    from .database_builder import build_database
    from .json_repository import JsonCanonicalRepository
    from .sqlite_repository import SQLiteCanonicalRepository

    path = Path(config.database_path)
    json_root = Path(config.json_root) if config.json_root else Path(__file__).resolve().parent
    if not path.exists():
        if is_vercel_runtime():
            raise FileNotFoundError(
                f"Vercel CKL SQLite index is missing at {path}; "
                "the deployment build must generate and bundle it"
            )
        if config.stale_database_policy == "rebuild":
            build_database(json_root, path)
        elif config.stale_database_policy == "fallback_to_json":
            return JsonCanonicalRepository(root=json_root)
        elif config.stale_database_policy == "ignore":
            return SQLiteCanonicalRepository(path, read_only=config.read_only, cache_size=config.cache_size)
        else:
            raise FileNotFoundError(
                f"CKL SQLite database not found at {path}. Rebuild with: python -m framework.canonical_library build-db"
            )

    repository = SQLiteCanonicalRepository(path, read_only=config.read_only, cache_size=config.cache_size)
    if is_vercel_runtime():
        try:
            validate_vercel_runtime_repository(repository, json_root)
        except Exception:
            repository.close()
            raise
        return repository

    if config.stale_database_policy != "ignore" and repository.is_stale(json_root):
        if config.stale_database_policy == "rebuild":
            repository.close()
            build_database(json_root, path)
            return SQLiteCanonicalRepository(path, read_only=config.read_only, cache_size=config.cache_size)
        if config.stale_database_policy == "fallback_to_json":
            repository.close()
            return JsonCanonicalRepository(root=json_root)
        raise RuntimeError(
            "CKL SQLite database is stale. Rebuild with: python -m framework.canonical_library build-db"
        )
    return repository


def validate_vercel_runtime_repository(repository: object, json_root: str | Path) -> None:
    """Fail closed if the packaged index lacks the build-time source identity."""

    from .database_builder import manifest_fingerprint

    metadata = getattr(repository, "metadata", {})
    required = (
        "inventory_fingerprint",
        "source_manifest_fingerprint",
        "source_inventory_signature",
    )
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise RuntimeError("Vercel CKL index is missing required source identity metadata: " + ", ".join(missing))
    expected_manifest = manifest_fingerprint(json_root)
    if metadata.get("source_manifest_fingerprint") != expected_manifest:
        raise RuntimeError("Vercel CKL index manifest fingerprint does not match the packaged JSON manifest")
    if repository.is_stale(json_root):  # type: ignore[attr-defined]
        raise RuntimeError("Vercel CKL index is stale relative to the packaged JSON source inventory")
