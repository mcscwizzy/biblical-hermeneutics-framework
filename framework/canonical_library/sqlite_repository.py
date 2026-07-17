"""SQLite-backed CKL repository and compatibility library."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Sequence

from .database_builder import verify_database
from .database_schema import CKL_DATABASE_SCHEMA_VERSION
from .loader import CanonicalLibrary
from .normalization import normalize_alias, normalize_id, tokenize_query
from .query_analysis import AmbiguousEntityResolution
from .retrieval import (
    RetrievalResult,
    apply_relevance_thresholds,
    category_bonus,
    governance_bonus,
    infer_query_categories,
    query_search_terms,
    score_keyword_result,
    score_text_match,
    sort_retrieval_results,
)
from .scripture import (
    ScriptureReferenceSpan,
    build_book_alias_lookup,
    parse_scripture_query,
    scripture_match_score,
    scripture_query_terms,
    scripture_reference_overlaps,
)
from .schema import SUPPORTED_CATEGORIES, CanonicalObject, CanonicalValidationError, validate_object


class SQLiteCanonicalRepository:
    """Read-mostly repository over the generated CKL SQLite database."""

    def __init__(self, path: str | Path, *, read_only: bool = True, cache_size: int = 256) -> None:
        self.path = Path(path)
        self.read_only = read_only
        self.cache_size = max(int(cache_size), 1)
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()
        self._metadata = self._load_metadata()
        self._validate_schema_version()
        self._get_by_id_cached = lru_cache(maxsize=self.cache_size)(self._get_by_id_uncached)
        self._book_alias_lookup_cached = lru_cache(maxsize=1)(self._book_alias_lookup_uncached)

    def close(self) -> None:
        with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()
        for conn in connections:
            try:
                conn.close()
            except sqlite3.ProgrammingError:
                pass

    @property
    def metadata(self) -> dict[str, str]:
        return dict(self._metadata)

    def get_by_id(self, object_id: str) -> CanonicalObject | None:
        normalized = normalize_id(object_id)
        if not normalized:
            return None
        return self._get_by_id_cached(normalized)

    def get_by_alias(self, alias: str, *, category: str | None = None) -> list[CanonicalObject]:
        rows = self._conn.execute(
            """
            SELECT o.id
            FROM canonical_aliases a
            JOIN canonical_objects o ON o.id = a.object_id
            WHERE a.normalized_alias = ?
              AND (? IS NULL OR o.type = ?)
            ORDER BY o.id
            """,
            (normalize_alias(alias), category, category),
        ).fetchall()
        return self._objects_for_rows(rows)

    def get_alias_match(self, alias: str, *, category: str | None = None) -> tuple[CanonicalObject, str] | None:
        row = self._conn.execute(
            """
            SELECT o.id, a.original_alias
            FROM canonical_aliases a
            JOIN canonical_objects o ON o.id = a.object_id
            WHERE a.normalized_alias = ?
              AND (? IS NULL OR o.type = ?)
            ORDER BY o.id
            LIMIT 1
            """,
            (normalize_alias(alias), category, category),
        ).fetchone()
        if row is None:
            return None
        obj = self.get_by_id(str(row["id"]))
        return (obj, str(row["original_alias"])) if obj is not None else None

    def get_by_title(self, title: str, *, category: str | None = None) -> list[CanonicalObject]:
        rows = self._conn.execute(
            """
            SELECT id
            FROM canonical_objects
            WHERE normalized_title = ?
              AND (? IS NULL OR type = ?)
            ORDER BY id
            """,
            (normalize_alias(title), category, category),
        ).fetchall()
        return self._objects_for_rows(rows)

    def list_by_type(self, object_type: str) -> list[CanonicalObject]:
        rows = self._conn.execute(
            "SELECT id FROM canonical_objects WHERE type = ? ORDER BY id",
            (object_type,),
        ).fetchall()
        return self._objects_for_rows(rows)

    def search_keywords(
        self,
        terms: Sequence[str],
        *,
        categories: Sequence[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        query = " ".join(str(term) for term in terms if str(term).strip())
        return self.retrieve_by_keywords(query, limit=limit, categories=categories)

    def get_relationships(self, object_id: str, *, minimum_weight: int = 1) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT target_id, relationship, weight, notes
            FROM canonical_relationships
            WHERE source_id = ?
              AND weight >= ?
            ORDER BY weight DESC, relationship, target_id, notes
            """,
            (normalize_id(object_id), int(minimum_weight)),
        ).fetchall()
        return [
            {
                "id": str(row["target_id"]),
                "relationship": str(row["relationship"]),
                "weight": int(row["weight"]),
                "notes": str(row["notes"] or ""),
            }
            for row in rows
        ]

    def get_scripture_matches(self, reference: str, *, limit: int = 10) -> list[RetrievalResult]:
        return self.retrieve_by_scripture_reference(reference, limit=limit)

    def inventory_fingerprint(self) -> str:
        return self._metadata.get("inventory_fingerprint", "")

    def is_stale(self, root: str | Path | None = None) -> bool:
        root_path = Path(root) if root is not None else Path(__file__).resolve().parent
        source_fingerprint = CanonicalLibrary(root=root_path).load().inventory_fingerprint()
        return self.inventory_fingerprint() != source_fingerprint

    def verify(self, *, root: str | Path | None = None, compare_fingerprint: bool = True) -> dict[str, Any]:
        return verify_database(self.path, root=root, compare_fingerprint=compare_fingerprint)

    def book_alias_lookup(self) -> dict[str, str]:
        return dict(self._book_alias_lookup_cached())

    def _book_alias_lookup_uncached(self) -> dict[str, str]:
        rows = self._conn.execute(
            """
            SELECT title, payload_json
            FROM canonical_objects
            WHERE type = 'book'
            ORDER BY id
            """
        ).fetchall()
        books = [validate_object(json.loads(str(row["payload_json"]))) for row in rows]
        return build_book_alias_lookup(books)

    def object_types(self) -> dict[str, list[str]]:
        rows = self._conn.execute(
            "SELECT type, id FROM canonical_objects ORDER BY type, id"
        ).fetchall()
        by_type = {category: [] for category in SUPPORTED_CATEGORIES}
        for row in rows:
            by_type.setdefault(str(row["type"]), []).append(str(row["id"]))
        return by_type

    def title_matches(self, title: str, *, categories: Sequence[str] | None = None) -> list[str]:
        normalized = normalize_alias(title)
        if categories:
            placeholders = ",".join("?" for _ in categories)
            rows = self._conn.execute(
                f"SELECT id FROM canonical_objects WHERE normalized_title = ? AND type IN ({placeholders}) ORDER BY id",
                (normalized, *categories),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id FROM canonical_objects WHERE normalized_title = ? ORDER BY id",
                (normalized,),
            ).fetchall()
        return [str(row["id"]) for row in rows]

    def alias_matches(self, alias: str, *, categories: Sequence[str] | None = None) -> list[str]:
        normalized = normalize_alias(alias)
        if categories:
            placeholders = ",".join("?" for _ in categories)
            rows = self._conn.execute(
                f"""
                SELECT a.object_id
                FROM canonical_aliases a
                JOIN canonical_objects o ON o.id = a.object_id
                WHERE a.normalized_alias = ? AND o.type IN ({placeholders})
                ORDER BY a.object_id
                """,
                (normalized, *categories),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT object_id FROM canonical_aliases WHERE normalized_alias = ? ORDER BY object_id",
                (normalized,),
            ).fetchall()
        return [str(row["object_id"]) for row in rows]

    def partial_title_matches(self, entity: str, *, categories: Sequence[str]) -> list[CanonicalObject]:
        normalized = normalize_alias(entity)
        if not normalized:
            return []
        placeholders = ",".join("?" for _ in categories)
        rows = self._conn.execute(
            f"""
            SELECT id
            FROM canonical_objects
            WHERE type IN ({placeholders})
              AND (normalized_title = ? OR normalized_title LIKE ?)
            ORDER BY id
            """,
            (*categories, normalized, f"{normalized} %"),
        ).fetchall()
        return self._objects_for_rows(rows)

    def retrieve_by_scripture_reference(
        self,
        reference: Any,
        limit: int = 10,
        *,
        library: Any | None = None,
        **filters: Any,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            return []
        query = parse_scripture_query(reference, book_alias_lookup=self.book_alias_lookup())
        if query is None:
            return []
        rows = self._conn.execute(
            """
            SELECT object_id, reference_text, book, start_chapter, start_verse, end_chapter, end_verse
            FROM canonical_scripture_references
            WHERE book = ?
            ORDER BY object_id, reference_text
            """,
            (query.book,),
        ).fetchall()
        matches_by_id: dict[str, list[ScriptureReferenceSpan]] = {}
        for row in rows:
            candidate = ScriptureReferenceSpan(
                book=str(row["book"]),
                start_chapter=row["start_chapter"],
                start_verse=row["start_verse"],
                end_chapter=row["end_chapter"],
                end_verse=row["end_verse"],
            )
            if scripture_reference_overlaps(query, candidate):
                matches_by_id.setdefault(str(row["object_id"]), []).append(candidate)
        results: list[RetrievalResult] = []
        for object_id in sorted(matches_by_id):
            obj = self.get_by_id(object_id)
            if obj is None or (library is not None and not library._is_retrievable(obj, **filters)):
                continue
            results.append(
                RetrievalResult(
                    object=obj,
                    score=scripture_match_score(
                        query,
                        match_count=len(matches_by_id[object_id]),
                        importance=obj.importance,
                    ),
                    match_type="scripture",
                    matched_terms=scripture_query_terms(query),
                    matched_fields=["scripture_references"],
                    matched_alias=query.book,
                )
            )
        return sort_retrieval_results(results)[:limit]

    def retrieve_by_keywords(
        self,
        query: str,
        limit: int = 10,
        *,
        library: Any | None = None,
        apply_thresholds: bool = False,
        categories: Sequence[str] | None = None,
        **filters: Any,
    ) -> list[RetrievalResult]:
        if limit <= 0:
            return []
        query_terms = query_search_terms(query)
        scripture_query = parse_scripture_query(query, book_alias_lookup=self.book_alias_lookup())
        if not query_terms and (scripture_query is None or scripture_query.start_chapter is None):
            return []

        candidate_ids: set[str] = set()
        if query_terms:
            placeholders = ",".join("?" for _ in query_terms)
            rows = self._conn.execute(
                f"SELECT DISTINCT object_id FROM canonical_keywords WHERE term IN ({placeholders})",
                tuple(query_terms),
            ).fetchall()
            candidate_ids.update(str(row["object_id"]) for row in rows)
        if scripture_query is not None:
            rows = self._conn.execute(
                "SELECT DISTINCT object_id FROM canonical_scripture_references WHERE book = ?",
                (scripture_query.book,),
            ).fetchall()
            candidate_ids.update(str(row["object_id"]) for row in rows)
        normalized_query = normalize_alias(query)
        if normalized_query:
            candidate_ids.update(self.title_matches(query))
            candidate_ids.update(self.alias_matches(query))

        category_set = set(categories or ())
        preferred_categories = infer_query_categories(query, query_terms)
        scripture_scores = {
            result.object.id: result.score
            for result in self.retrieve_by_scripture_reference(
                query,
                limit=max(len(candidate_ids), limit),
                library=library,
                **filters,
            )
        }
        results: list[RetrievalResult] = []
        for object_id in sorted(candidate_ids):
            obj = self.get_by_id(object_id)
            if obj is None:
                continue
            if category_set and obj.type not in category_set:
                continue
            if library is not None and not library._is_retrievable(obj, **filters):
                continue
            field_terms = self._field_terms_for(object_id)
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
                scripture_mode=scripture_score > 0,
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

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            conn.execute("PRAGMA query_only = ON")
        else:
            conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -20000")
        return conn

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = self._connect()
            self._local.connection = conn
            with self._connections_lock:
                self._connections.append(conn)
        return conn

    def _load_metadata(self) -> dict[str, str]:
        return {
            str(row["key"]): str(row["value"])
            for row in self._conn.execute("SELECT key, value FROM ckl_metadata")
        }

    def _validate_schema_version(self) -> None:
        found = self._metadata.get("database_schema_version")
        if found != CKL_DATABASE_SCHEMA_VERSION:
            raise RuntimeError(
                f"CKL SQLite database schema version {CKL_DATABASE_SCHEMA_VERSION} is required, "
                f"but version {found or '<missing>'} was found. Rebuild the database with: "
                "python -m framework.canonical_library build-db"
            )

    def _get_by_id_uncached(self, object_id: str) -> CanonicalObject | None:
        row = self._conn.execute(
            "SELECT payload_json FROM canonical_objects WHERE id = ?",
            (object_id,),
        ).fetchone()
        if row is None:
            return None
        return validate_object(json.loads(str(row["payload_json"])))

    def _objects_for_rows(self, rows: Sequence[sqlite3.Row]) -> list[CanonicalObject]:
        objects: list[CanonicalObject] = []
        for row in rows:
            obj = self.get_by_id(str(row["id"]))
            if obj is not None:
                objects.append(obj)
        return objects

    def _field_terms_for(self, object_id: str) -> dict[str, set[str]]:
        rows = self._conn.execute(
            """
            SELECT field_name, term
            FROM canonical_keywords
            WHERE object_id = ?
            ORDER BY field_name, term
            """,
            (object_id,),
        ).fetchall()
        field_terms: dict[str, set[str]] = {}
        for row in rows:
            field_terms.setdefault(str(row["field_name"]), set()).add(str(row["term"]))
        return field_terms


class LazyCanonicalObjectMap(Mapping[str, CanonicalObject]):
    def __init__(self, repository: SQLiteCanonicalRepository) -> None:
        self.repository = repository

    def __getitem__(self, key: str) -> CanonicalObject:
        obj = self.repository.get_by_id(key)
        if obj is None:
            raise KeyError(key)
        return obj

    def __iter__(self) -> Iterator[str]:
        rows = self.repository._conn.execute("SELECT id FROM canonical_objects ORDER BY id").fetchall()
        return iter(str(row["id"]) for row in rows)

    def __len__(self) -> int:
        return int(self.repository._conn.execute("SELECT COUNT(*) FROM canonical_objects").fetchone()[0])

    def get(self, key: str, default: Any = None) -> CanonicalObject | Any:
        obj = self.repository.get_by_id(key)
        return default if obj is None else obj


class SQLiteCanonicalLibrary(CanonicalLibrary):
    """Compatibility facade exposing CanonicalLibrary retrieval APIs over SQLite."""

    def __init__(self, repository: SQLiteCanonicalRepository, *, root: str | Path | None = None) -> None:
        super().__init__(root=Path(root) if root is not None else Path(__file__).resolve().parent)
        self.repository = repository
        self.objects_by_id = LazyCanonicalObjectMap(repository)  # type: ignore[assignment]
        self.objects_by_type = repository.object_types()
        self.objects_by_alias = {}
        self.keyword_index = {}
        self.field_keyword_index = {}
        self.manifest = {
            "framework_version": repository.metadata.get("framework_version"),
            "schema_version": repository.metadata.get("schema_version"),
            "object_count": int(repository.metadata.get("object_count", "0")),
        }
        self._loaded = True
        self._book_alias_lookup = repository.book_alias_lookup()

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        root: str | Path | None = None,
        read_only: bool = True,
        cache_size: int = 256,
    ) -> "SQLiteCanonicalLibrary":
        return cls(SQLiteCanonicalRepository(path, read_only=read_only, cache_size=cache_size), root=root)

    def load(self) -> "SQLiteCanonicalLibrary":
        return self

    def inventory_fingerprint(self) -> str:
        return self.repository.inventory_fingerprint()

    def source_path_for(self, object_id: str) -> Path | None:
        row = self.repository._conn.execute(
            "SELECT source_path FROM canonical_objects WHERE id = ?",
            (normalize_id(object_id),),
        ).fetchone()
        if row is None or row["source_path"] is None:
            return None
        return self.root / str(row["source_path"])

    def _title_matches(self, query: str) -> list[str]:
        return self.repository.title_matches(query)

    def retrieve_by_id(self, object_id: str, **filters: Any) -> RetrievalResult | None:
        obj = self.repository.get_by_id(object_id)
        if obj is None or not self._is_retrievable(obj, **filters):
            return None
        normalized = normalize_id(object_id)
        return RetrievalResult(obj, 1.0, "id", [normalized], ["id"])

    def retrieve_by_alias(self, alias: str, **filters: Any) -> RetrievalResult | None:
        match = self.repository.get_alias_match(alias)
        if match is None:
            return None
        obj, matched_alias = match
        if not self._is_retrievable(obj, **filters):
            return None
        return RetrievalResult(
            object=obj,
            score=1.0,
            match_type="alias",
            matched_terms=tokenize_query(alias),
            matched_fields=["aliases"],
            matched_alias=matched_alias,
        )

    def retrieve_by_keywords(
        self,
        query: str,
        limit: int = 10,
        *,
        apply_thresholds: bool = False,
        **filters: Any,
    ) -> list[RetrievalResult]:
        return self.repository.retrieve_by_keywords(
            query,
            limit=limit,
            library=self,
            apply_thresholds=apply_thresholds,
            **filters,
        )

    def retrieve_hybrid(self, query: str, limit: int = 10, *, apply_thresholds: bool = True, **filters: Any) -> list[RetrievalResult]:
        return self.retrieve_by_keywords(query, limit=limit, apply_thresholds=apply_thresholds, **filters)

    def retrieve_by_scripture_reference(self, reference: Any, limit: int = 10, **filters: Any) -> list[RetrievalResult]:
        return self.repository.retrieve_by_scripture_reference(reference, limit=limit, library=self, **filters)

    def retrieve_exact(self, query: str, **filters: Any) -> RetrievalResult | None:
        normalized_id = normalize_id(query)
        obj = self.repository.get_by_id(normalized_id)
        if obj is not None:
            if not self._is_retrievable(obj, **filters):
                return None
            return RetrievalResult(obj, 1.0, "id", [normalized_id], ["id"])

        alias = self.retrieve_by_alias(query, **filters)
        if alias is not None:
            return alias

        for obj in self.repository.get_by_title(query):
            if not self._is_retrievable(obj, **filters):
                continue
            return RetrievalResult(obj, 1.0, "title", tokenize_query(query), ["title"])
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
        category = categories[0] if categories and len(categories) == 1 else None
        category_set = set(categories or ())
        for candidate in entity_candidates:
            if match_type == "id":
                objects = [obj] if (obj := self.repository.get_by_id(candidate)) is not None else []
                matched_alias = None
                matched_fields = ["id"]
                matched_terms = [normalize_id(candidate)]
            elif match_type == "title":
                objects = self.repository.get_by_title(candidate, category=category)
                matched_alias = None
                matched_fields = ["title"]
                matched_terms = tokenize_query(candidate)
            elif match_type == "alias":
                if category is not None:
                    alias_objects = self.repository.get_by_alias(candidate, category=category)
                    matched_alias = candidate
                else:
                    alias_match = self.repository.get_alias_match(candidate)
                    alias_objects = [alias_match[0]] if alias_match is not None else []
                    matched_alias = alias_match[1] if alias_match is not None else candidate
                objects = alias_objects
                matched_fields = ["aliases"]
                matched_terms = tokenize_query(candidate)
            else:
                objects = []
                matched_alias = None
                matched_fields = []
                matched_terms = []
            for obj in objects:
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
        candidates: list[RetrievalResult] = []
        for obj in self.repository.partial_title_matches(entity, categories=categories):
            if not self._is_retrievable(
                obj,
                approved_only=approved_only,
                exclude_deprecated=exclude_deprecated,
                exclude_rejected=exclude_rejected,
                include_placeholders=include_placeholders,
                allowed_statuses=allowed_statuses,
            ):
                continue
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
