"""Canonical library loader and in-memory indexes."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .normalization import normalize_alias, normalize_id, tokenize_query
from .query_analysis import (
    AmbiguousEntityCandidate,
    AmbiguousEntityResolution,
)
from .scripture import (
    ScriptureReferenceSpan,
    build_book_alias_lookup,
    parse_scripture_query,
    parse_scripture_reference,
    scripture_match_score,
    scripture_query_terms,
    scripture_reference_overlaps,
)
from .retrieval import (
    category_bonus,
    governance_bonus,
    infer_query_categories,
    RetrievalResult,
    apply_relevance_thresholds,
    collect_field_search_terms,
    score_keyword_result,
    score_text_match,
    query_search_terms,
    sort_retrieval_results,
)
from .schema import (
    SUPPORTED_CATEGORIES,
    CanonicalObject,
    CanonicalValidationError,
    validate_library,
    validate_object,
)


LOGGER = logging.getLogger(__name__)


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _stable_json_fingerprint(data: Any) -> str:
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
        self._inventory_fingerprint_cache: str | None = None
        self._source_paths_by_id: dict[str, Path] = {}
        self._title_index: dict[str, list[str]] = {}
        self._alias_index: dict[str, tuple[str, str]] = {}
        self._book_alias_lookup: dict[str, str] = {}
        self._scripture_references_by_object: dict[str, list[ScriptureReferenceSpan]] = {}
        self._scripture_book_index: dict[str, set[str]] = {}

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
                LOGGER.error("%s", exc)
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
        self._book_alias_lookup = {}
        self._scripture_references_by_object = {}
        self._scripture_book_index = {}
        self._inventory_fingerprint_cache = None

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

        self._book_alias_lookup = build_book_alias_lookup(
            obj for obj in objects if obj.type == "book"
        )
        for obj in objects:
            parsed_references: list[ScriptureReferenceSpan] = []
            for reference in obj.scripture_references:
                parsed = parse_scripture_reference(
                    reference.reference,
                    book_alias_lookup=self._book_alias_lookup,
                )
                if parsed is None:
                    continue
                parsed_references.append(parsed)
                self._scripture_book_index.setdefault(parsed.book, set()).add(obj.id)
            self._scripture_references_by_object[obj.id] = parsed_references

        try:
            validate_library(objects, manifest=manifest, source_paths=source_paths)
        except CanonicalValidationError as exc:
            LOGGER.error("%s", exc)
            errors.append(str(exc))

        if errors:
            raise CanonicalValidationError("\n".join(errors))

        self.manifest = dict(manifest)
        self._loaded = True
        return self

    def inventory_fingerprint(self) -> str:
        """Return a stable fingerprint for the loaded CKL inventory."""

        self._ensure_loaded()
        if self._inventory_fingerprint_cache:
            return self._inventory_fingerprint_cache
        payload = {
            "manifest": {
                "framework_version": self.manifest.get("framework_version"),
                "schema_version": self.manifest.get("schema_version"),
                "object_count": self.manifest.get("object_count"),
                "categories": self.manifest.get("categories"),
            },
            "objects": [
                self.objects_by_id[object_id].to_dict()
                for object_id in sorted(self.objects_by_id)
            ],
        }
        self._inventory_fingerprint_cache = _stable_json_fingerprint(payload)
        return self._inventory_fingerprint_cache

    def source_path_for(self, object_id: str) -> Path | None:
        """Return the on-disk source path for a loaded object, if known."""

        self._ensure_loaded()
        return self._source_paths_by_id.get(normalize_id(object_id))

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
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> bool:
        if approved_only and obj.review_status != "approved":
            return False
        if not include_placeholders and obj.content_status == "placeholder":
            return False
        if allowed_statuses is not None and obj.review_status not in allowed_statuses:
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
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> RetrievalResult | None:
        self._ensure_loaded()
        normalized = normalize_id(object_id)
        obj = self.objects_by_id.get(normalized)
        if obj is None or not self._is_retrievable(
            obj,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
            include_placeholders=include_placeholders,
            allowed_statuses=allowed_statuses,
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
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
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
                    include_placeholders=include_placeholders,
                    allowed_statuses=allowed_statuses,
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
        apply_thresholds: bool = False,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> list[RetrievalResult]:
        self._ensure_loaded()
        if limit <= 0:
            return []
        query_terms = query_search_terms(query)
        scripture_query = parse_scripture_query(query, book_alias_lookup=self._book_alias_lookup)
        if not query_terms:
            if scripture_query is None or scripture_query.start_chapter is None:
                return []

        scripture_scores: dict[str, float] = {}
        scripture_mode = bool(
            scripture_query is not None
            and (scripture_query.start_chapter is not None or scripture_query.start_verse is not None)
        )
        if scripture_mode:
            for result in self.retrieve_by_scripture_reference(
                query,
                limit=max(len(self.objects_by_id), limit),
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            ):
                scripture_scores[result.object.id] = result.score

        preferred_categories = infer_query_categories(query, query_terms)
        results: list[RetrievalResult] = []
        for object_id in sorted(self.objects_by_id):
            obj = self.objects_by_id[object_id]
            if not self._is_retrievable(
                obj,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            ):
                continue
            field_terms = self.field_keyword_index.get(object_id, {})
            score, matched_terms, matched_fields = score_keyword_result(
                query_terms=query_terms,
                field_terms=field_terms,
                importance=obj.importance,
            )
            scripture_score = scripture_scores.get(object_id, 0.0)
            if scripture_score > score:
                score = scripture_score
            text_bonus, text_match_type, text_fields, matched_alias = score_text_match(
                query,
                obj,
                scripture_mode=scripture_mode,
            )
            if score <= 0 and text_bonus <= 0:
                continue
            score += text_bonus
            score += category_bonus(obj.type, preferred_categories)
            score += governance_bonus(obj.review_status, obj.confidence)
            score = round(min(score, 1.0), 4)
            if scripture_score > 0:
                match_type = "scripture"
                matched_fields = list(dict.fromkeys([*matched_fields, *text_fields, "scripture_references"]))
                if matched_alias is None and scripture_query is not None:
                    matched_alias = scripture_query.book
            elif text_bonus > 0:
                match_type = text_match_type
                matched_fields = list(dict.fromkeys([*matched_fields, *text_fields]))
            else:
                match_type = "keyword"
            results.append(
                RetrievalResult(
                    object=obj,
                    score=score,
                    match_type=match_type,
                    matched_terms=matched_terms,
                    matched_fields=matched_fields,
                    matched_alias=matched_alias,
                )
            )
        results = sort_retrieval_results(results)
        if apply_thresholds:
            results = apply_relevance_thresholds(results)
        return results[:limit]

    def retrieve_hybrid(
        self,
        query: str,
        limit: int = 10,
        *,
        apply_thresholds: bool = True,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> list[RetrievalResult]:
        self._ensure_loaded()
        return self.retrieve_by_keywords(
            query,
            limit=limit,
            apply_thresholds=apply_thresholds,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
            include_placeholders=include_placeholders,
            allowed_statuses=allowed_statuses,
        )

    def retrieve_by_scripture_reference(
        self,
        reference: Any,
        limit: int = 10,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> list[RetrievalResult]:
        self._ensure_loaded()
        if limit <= 0:
            return []

        query = parse_scripture_query(reference, book_alias_lookup=self._book_alias_lookup)
        if query is None:
            return []

        candidate_ids = sorted(self._scripture_book_index.get(query.book, set()))
        if not candidate_ids:
            return []

        results: list[RetrievalResult] = []
        query_terms = scripture_query_terms(query)
        for object_id in candidate_ids:
            obj = self.objects_by_id[object_id]
            if not self._is_retrievable(
                obj,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            ):
                continue

            matching_references = [
                candidate
                for candidate in self._scripture_references_by_object.get(object_id, [])
                if scripture_reference_overlaps(query, candidate)
            ]
            if not matching_references:
                continue

            score = scripture_match_score(
                query,
                match_count=len(matching_references),
                importance=obj.importance,
            )
            results.append(
                RetrievalResult(
                    object=obj,
                    score=score,
                    match_type="scripture",
                    matched_terms=query_terms,
                    matched_fields=["scripture_references"],
                    matched_alias=query.book,
                )
            )

        results = sort_retrieval_results(results)
        return results[:limit]

    def trace_relationship_graph(
        self,
        seed: str | Sequence[str],
        *,
        max_depth: int = 1,
        limit: int = 10,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        self._ensure_loaded()
        from .context_builder import CanonicalContextBuilder

        if isinstance(seed, str):
            seed_values = [seed]
        else:
            seed_values = [value for value in seed if str(value).strip()]

        builder = CanonicalContextBuilder(
            self,
            max_topics=max(len(seed_values), 1),
            max_expanded_topics=max(limit, 0),
            max_relationship_depth=max(max_depth, 0),
        )
        seed_entries: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for value in seed_values:
            result = self.retrieve_exact(
                value,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            )
            if result is None or result.object.id in seen_ids:
                continue
            builder._append_topic(
                seed_entries,
                result.object,
                inclusion_type="primary",
                seen_ids=seen_ids,
                score=result.score,
                match_type=result.match_type,
                matched_alias=result.matched_alias,
                matched_terms=result.matched_terms,
                matched_fields=result.matched_fields,
            )

        expanded: list[dict[str, Any]] = []
        remaining_limit = max(limit - len(seed_entries), 0)
        if seed_entries and max_depth > 0 and remaining_limit > 0:
            builder.max_expanded_topics = remaining_limit
            expanded = builder._expand_relationships(
                seed_entries,
                seen_ids,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            )

        retrieved_topics = seed_entries + expanded
        return {
            "seed_ids": [entry["id"] for entry in seed_entries],
            "retrieved_topics": retrieved_topics,
            "metadata": {
                "retrieval_method": "relationship",
                "seed_count": len(seed_entries),
                "expanded_count": len(expanded),
                "topic_count": len(retrieved_topics),
                "max_depth": max_depth,
                "requested_limit": limit,
                "include_placeholders": include_placeholders,
                "allowed_statuses": list(allowed_statuses) if allowed_statuses is not None else None,
            },
        }

    def audit_bidirectional_relationships(self, limit: int | None = None) -> list[dict[str, Any]]:
        self._ensure_loaded()
        from .context_builder import CanonicalContextBuilder

        builder = CanonicalContextBuilder(self)
        issues: list[dict[str, Any]] = []
        for source_id in sorted(self.objects_by_id):
            source = self.objects_by_id[source_id]
            for relationship in builder._normalize_related_objects(source):
                target_id = relationship["id"]
                target = self.objects_by_id.get(target_id)
                if target is None:
                    continue
                reverse_matches = [
                    candidate
                    for candidate in builder._normalize_related_objects(target)
                    if candidate["id"] == source_id
                ]
                if reverse_matches:
                    continue
                issues.append(
                    {
                        "source_id": source_id,
                        "source_title": source.title,
                        "target_id": target_id,
                        "target_title": target.title,
                        "relationship": relationship["relationship"],
                        "weight": relationship["weight"],
                        "notes": relationship["notes"],
                    }
                )
                if limit is not None and len(issues) >= limit:
                    return issues
        return issues

    def retrieve_exact(
        self,
        query: str,
        *,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
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
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
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
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
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
                    include_placeholders=include_placeholders,
                    allowed_statuses=allowed_statuses,
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
        return None

    def resolve_entity(
        self,
        entity_candidates: Sequence[str],
        preferred_categories: Sequence[str] = (),
        *,
        category_confidence: float = 1.0,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> RetrievalResult | None:
        resolution = self.resolve_entity_with_status(
            entity_candidates,
            preferred_categories,
            category_confidence=category_confidence,
            approved_only=approved_only,
            exclude_deprecated=exclude_deprecated,
            exclude_rejected=exclude_rejected,
            include_placeholders=include_placeholders,
            allowed_statuses=allowed_statuses,
        )
        return resolution if isinstance(resolution, RetrievalResult) else None

    def resolve_entity_with_status(
        self,
        entity_candidates: Sequence[str],
        preferred_categories: Sequence[str] = (),
        *,
        category_confidence: float = 1.0,
        approved_only: bool = False,
        exclude_deprecated: bool = True,
        exclude_rejected: bool = True,
        include_placeholders: bool = True,
        allowed_statuses: tuple[str, ...] | None = None,
    ) -> RetrievalResult | AmbiguousEntityResolution | None:
        self._ensure_loaded()
        candidates = [candidate for candidate in entity_candidates if str(candidate or "").strip()]
        if not candidates:
            return None

        constrained_categories = tuple(
            category for category in preferred_categories if category in self.objects_by_type
        )
        use_category_constraint = bool(constrained_categories and category_confidence >= 0.75)
        categories: tuple[str, ...] | None = constrained_categories if use_category_constraint else None

        for match_type in ("id", "title", "alias"):
            matches = self._exact_entity_matches(
                candidates,
                match_type=match_type,
                categories=categories,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            )
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                return self._ambiguous_resolution(candidates[0], matches)

        if not use_category_constraint:
            for match_type in ("id", "title", "alias"):
                matches = self._exact_entity_matches(
                    candidates,
                    match_type=match_type,
                    categories=None,
                    approved_only=approved_only,
                    exclude_deprecated=exclude_deprecated,
                    exclude_rejected=exclude_rejected,
                    include_placeholders=include_placeholders,
                    allowed_statuses=allowed_statuses,
                )
                if len(matches) == 1:
                    return matches[0]
                if len(matches) > 1:
                    return self._ambiguous_resolution(candidates[0], matches)

        if use_category_constraint:
            ambiguous = self._partial_entity_ambiguity(
                candidates[0],
                categories=constrained_categories,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            )
            if ambiguous is not None:
                return ambiguous

        return None

    def _exact_entity_matches(
        self,
        entity_candidates: Sequence[str],
        *,
        match_type: str,
        categories: Sequence[str] | None,
        approved_only: bool,
        exclude_deprecated: bool,
        exclude_rejected: bool,
        include_placeholders: bool,
        allowed_statuses: tuple[str, ...] | None,
    ) -> list[RetrievalResult]:
        matches: dict[str, RetrievalResult] = {}
        category_set = set(categories or ())
        for candidate in entity_candidates:
            if match_type == "id":
                object_ids = [normalize_id(candidate)]
                matched_alias = None
                matched_fields = ["id"]
                matched_terms = [normalize_id(candidate)]
            elif match_type == "title":
                object_ids = self._title_matches(candidate)
                matched_alias = None
                matched_fields = ["title"]
                matched_terms = tokenize_query(candidate)
            elif match_type == "alias":
                normalized_alias = normalize_alias(candidate)
                object_ids = list(self.objects_by_alias.get(normalized_alias, []))
                matched_alias = self._alias_index.get(normalized_alias, ("", candidate))[1]
                matched_fields = ["aliases"]
                matched_terms = tokenize_query(candidate)
            else:
                object_ids = []
                matched_alias = None
                matched_fields = []
                matched_terms = []

            for object_id in sorted(set(object_ids)):
                obj = self.objects_by_id.get(object_id)
                if obj is None:
                    continue
                if category_set and obj.type not in category_set:
                    continue
                if not self._is_retrievable(
                    obj,
                    approved_only=approved_only,
                    exclude_deprecated=exclude_deprecated,
                    exclude_rejected=exclude_rejected,
                    include_placeholders=include_placeholders,
                    allowed_statuses=allowed_statuses,
                ):
                    continue
                matches[obj.id] = RetrievalResult(
                    object=obj,
                    score=1.0 if match_type != "alias" else 0.98,
                    match_type=match_type,
                    matched_terms=matched_terms,
                    matched_fields=matched_fields,
                    matched_alias=matched_alias,
                    ranking_score=1.0 if match_type != "alias" else 0.98,
                    confidence=1.0 if match_type != "alias" else 0.98,
                )
        return sort_retrieval_results(list(matches.values()))

    def _partial_entity_ambiguity(
        self,
        entity: str,
        *,
        categories: Sequence[str],
        approved_only: bool,
        exclude_deprecated: bool,
        exclude_rejected: bool,
        include_placeholders: bool,
        allowed_statuses: tuple[str, ...] | None,
    ) -> AmbiguousEntityResolution | None:
        normalized_entity = normalize_alias(entity)
        if not normalized_entity:
            return None
        candidates: list[RetrievalResult] = []
        for object_id in sorted(self.objects_by_id):
            obj = self.objects_by_id[object_id]
            if obj.type not in categories:
                continue
            if not self._is_retrievable(
                obj,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            ):
                continue
            normalized_title = normalize_alias(obj.title)
            if normalized_title == normalized_entity or normalized_title.startswith(f"{normalized_entity} "):
                candidates.append(
                    RetrievalResult(
                        object=obj,
                        score=0.86,
                        match_type="ambiguous",
                        matched_terms=tokenize_query(entity),
                        matched_fields=["title"],
                        ranking_score=0.86,
                        confidence=0.66,
                    )
                )
        if len(candidates) <= 1:
            return None
        return self._ambiguous_resolution(entity, candidates)

    def _ambiguous_resolution(
        self,
        entity: str,
        matches: Sequence[RetrievalResult],
    ) -> AmbiguousEntityResolution:
        candidates = tuple(
            AmbiguousEntityCandidate(
                id=result.object.id,
                title=result.object.title,
                type=result.object.type,
            )
            for result in sort_retrieval_results(list(matches))
        )
        return AmbiguousEntityResolution(entity=entity, candidates=candidates)

    def retrieve_semantic(self, query: str, limit: int = 10) -> list[RetrievalResult]:  # noqa: ARG002
        raise NotImplementedError("semantic retrieval is not implemented yet")
