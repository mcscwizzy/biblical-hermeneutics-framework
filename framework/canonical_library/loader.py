"""Canonical library loader and in-memory indexes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .normalization import STOP_WORDS, normalize_alias, normalize_id, tokenize_query
from .retrieval import (
    RetrievalResult,
    canonical_search_terms,
    collect_field_search_terms,
    score_keyword_result,
    sort_retrieval_results,
)
from .schema import (
    SUPPORTED_CATEGORIES,
    CanonicalObject,
    CanonicalValidationError,
    validate_library,
    validate_object,
)


def _package_root() -> Path:
    return Path(__file__).resolve().parent


@dataclass
class CanonicalLibrary:
    root: Path = field(default_factory=_package_root)
    objects_by_id: dict[str, CanonicalObject] = field(default_factory=dict)
    objects_by_alias: dict[str, list[str]] = field(default_factory=dict)
    objects_by_type: dict[str, list[str]] = field(default_factory=dict)
    keyword_index: dict[str, set[str]] = field(default_factory=dict)
    field_keyword_index: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.objects_root = self.root / "objects"
        self.manifest_path = self.root / "manifest.json"
        self._loaded = False
        self._source_paths_by_id: dict[str, Path] = {}
        self._title_index: dict[str, list[str]] = {}
        self._alias_index: dict[str, tuple[str, str]] = {}

    @classmethod
    def load_default(cls) -> "CanonicalLibrary":
        return cls().load()

    def load(self) -> "CanonicalLibrary":
        if self._loaded:
            return self
        errors: list[str] = []

        manifest = self._read_manifest(errors)
        objects: list[CanonicalObject] = []
        source_paths: dict[str, Path] = {}

        if self.objects_root.exists():
            paths = sorted(
                (
                    path
                    for path in self.objects_root.rglob("*.json")
                    if path.is_file()
                ),
                key=lambda path: path.relative_to(self.objects_root).as_posix(),
            )
        else:
            paths = []
            errors.append(f"{self.objects_root}: objects directory does not exist")

        for path in paths:
            if path.name.startswith("_"):
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001 - surface parser failures
                errors.append(f"{self._relative_path(path)}: {exc}")
                continue
            try:
                obj = validate_object(raw, path=self._relative_path(path))
            except CanonicalValidationError as exc:
                errors.append(str(exc))
                continue
            if obj.id in source_paths:
                errors.append(
                    f"duplicate canonical id '{obj.id}' found in {self._relative_path(path)} and {self._relative_path(source_paths[obj.id])}"
                )
                continue
            objects.append(obj)
            source_paths[obj.id] = path

        self.objects_by_id = {obj.id: obj for obj in objects}
        self.objects_by_type = {category: [] for category in SUPPORTED_CATEGORIES}
        self.objects_by_alias = {}
        self.keyword_index = {}
        self.field_keyword_index = {}
        self._source_paths_by_id = source_paths
        self._title_index = {}
        self._alias_index = {}

        for obj in objects:
            self.objects_by_type.setdefault(obj.type, []).append(obj.id)
            title_key = normalize_alias(obj.title)
            self._title_index.setdefault(title_key, []).append(obj.id)
            for alias in obj.aliases:
                alias_key = normalize_alias(alias)
                self.objects_by_alias.setdefault(alias_key, []).append(obj.id)
                self._alias_index[alias_key] = (obj.id, alias)
            field_terms = collect_field_search_terms(obj)
            self.field_keyword_index[obj.id] = field_terms
            for terms in field_terms.values():
                for term in terms:
                    self.keyword_index.setdefault(term, set()).add(obj.id)

        try:
            validate_library(objects, manifest=manifest, source_paths=source_paths)
        except CanonicalValidationError as exc:
            errors.append(str(exc))

        if errors:
            raise CanonicalValidationError("\n".join(errors))

        self.manifest = dict(manifest)
        self._loaded = True
        return self

    def _read_manifest(self, errors: list[str]) -> dict[str, Any]:
        if not self.manifest_path.exists():
            errors.append(f"{self._relative_path(self.manifest_path)}: manifest is missing")
            return {}
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface parser failures
            errors.append(f"{self._relative_path(self.manifest_path)}: {exc}")
            return {}
        if not isinstance(raw, dict):
            errors.append(f"{self._relative_path(self.manifest_path)}: manifest must be a JSON object")
            return {}
        return raw

    def _relative_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def _is_retrievable(
        self,
        obj: CanonicalObject,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
    ) -> bool:
        if approved_only and obj.review_status != "approved":
            return False
        if exclude_deprecated and obj.content_status == "deprecated":
            return False
        if exclude_rejected and obj.review_status == "rejected":
            return False
        return True

    def retrieve_by_id(
        self,
        object_id: str,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
    ) -> RetrievalResult | None:
        self._ensure_loaded()
        normalized = normalize_id(object_id)
        obj = self.objects_by_id.get(normalized)
        if obj is None or not self._is_retrievable(
            obj,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
        ):
            return None
        return RetrievalResult(
            object=obj,
            score=1.0,
            match_type="id",
            matched_terms=[normalized],
            matched_fields=["id"],
        )

    def retrieve_by_alias(
        self,
        alias: str,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
    ) -> RetrievalResult | None:
        self._ensure_loaded()
        normalized = normalize_alias(alias)
        ids = self.objects_by_alias.get(normalized)
        if not ids:
            return None
        object_id = next(
            (
                candidate_id
                for candidate_id in sorted(ids)
                if self._is_retrievable(
                    self.objects_by_id[candidate_id],
                    approved_only=approved_only,
                    exclude_deprecated=exclude_deprecated,
                    exclude_rejected=exclude_rejected,
                )
            ),
            None,
        )
        if object_id is None:
            return None
        obj = self.objects_by_id[object_id]
        matched_alias = self._alias_index.get(normalized, (object_id, None))[1]
        return RetrievalResult(
            object=obj,
            score=1.0,
            match_type="alias",
            matched_terms=tokenize_query(alias),
            matched_fields=["aliases"],
            matched_alias=matched_alias,
        )

    def _title_matches(self, query: str) -> list[str]:
        normalized = normalize_alias(query)
        return list(self._title_index.get(normalized, []))

    def retrieve_by_keywords(
        self,
        query: str,
        limit: int = 10,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
    ) -> list[RetrievalResult]:
        self._ensure_loaded()
        if limit <= 0:
            return []
        query_terms = list(dict.fromkeys(term for term in tokenize_query(query) if term not in STOP_WORDS))
        if not query_terms:
            return []
        candidate_ids: set[str] = set()
        for term in query_terms:
            candidate_ids.update(self.keyword_index.get(term, set()))
        results: list[RetrievalResult] = []
        for object_id in candidate_ids:
            obj = self.objects_by_id[object_id]
            if not self._is_retrievable(
                obj,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
            ):
                continue
            field_terms = self.field_keyword_index.get(object_id, {})
            score, matched_terms, matched_fields = score_keyword_result(
                query_terms=query_terms,
                field_terms=field_terms,
                importance=obj.importance,
            )
            if score <= 0:
                continue
            matched_alias = None
            for alias in obj.aliases:
                alias_terms = canonical_search_terms(alias)
                if set(query_terms).issubset(alias_terms):
                    matched_alias = alias
                    break
            results.append(
                RetrievalResult(
                    object=obj,
                    score=score,
                    match_type="keyword",
                    matched_terms=matched_terms,
                    matched_fields=matched_fields,
                    matched_alias=matched_alias,
                )
            )
        results = sort_retrieval_results(results)
        return results[:limit]

    def retrieve_exact(
        self,
        query: str,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
    ) -> RetrievalResult | None:
        self._ensure_loaded()
        normalized_id = normalize_id(query)
        obj = self.objects_by_id.get(normalized_id)
        if obj is not None:
            if not self._is_retrievable(
                obj,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
            ):
                return None
            return RetrievalResult(
                object=obj,
                score=1.0,
                match_type="id",
                matched_terms=[normalized_id],
                matched_fields=["id"],
            )

        normalized_alias = normalize_alias(query)
        alias_ids = self.objects_by_alias.get(normalized_alias)
        if alias_ids:
            alias_result = self.retrieve_by_alias(
                query,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
            )
            if alias_result is not None:
                return alias_result
            return None

        title_matches = self._title_matches(query)
        if title_matches:
            for object_id in sorted(title_matches):
                obj = self.objects_by_id[object_id]
                if not self._is_retrievable(
                    obj,
                    approved_only=approved_only,
                    exclude_deprecated=exclude_deprecated,
                    exclude_rejected=exclude_rejected,
                ):
                    continue
                matched_terms = tokenize_query(query)
                return RetrievalResult(
                    object=obj,
                    score=1.0,
                    match_type="title",
                    matched_terms=matched_terms,
                    matched_fields=["title"],
                )
            return None

        keyword_matches = self.retrieve_by_keywords(
            query,
            limit=1,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
        )
        return keyword_matches[0] if keyword_matches else None

    def retrieve_semantic(self, query: str, limit: int = 10) -> list[RetrievalResult]:  # noqa: ARG002
        raise NotImplementedError("semantic retrieval is not implemented yet")

    def retrieve_hybrid(self, query: str, limit: int = 10) -> list[RetrievalResult]:  # noqa: ARG002
        raise NotImplementedError("hybrid retrieval is not implemented yet")
