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


def repository_config_from_env(base: CKLRepositoryConfig | None = None) -> CKLRepositoryConfig:
    config = base or CKLRepositoryConfig()
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
