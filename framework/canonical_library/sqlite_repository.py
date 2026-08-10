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
from .evidence import RetrievedClaimEvidence, rank_claims
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
from .retrieval.indexer import inventory_content_signature, inventory_signature
from .scripture import (
    ScriptureReferenceSpan,
    build_book_alias_lookup,
    parse_scripture_query,
    scripture_match_score,
    scripture_query_terms,
    scripture_reference_overlaps,
)
from .schema import SUPPORTED_CATEGORIES, CanonicalObject, CanonicalValidationError, validate_object


_SOURCE_FINGERPRINT_CACHE: dict[str, tuple[str, str]] = {}
_SOURCE_FINGERPRINT_LOCK = threading.Lock()


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

    def __del__(self) -> None:
        """Close thread-local connections if the repository is not closed explicitly."""

        try:
            self.close()
        except (AttributeError, TypeError):
            # Destructors can run after partially initialized objects or module
            # globals have already been torn down during interpreter shutdown.
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

    def get_claims(self, object_ids: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
        """Bulk-fetch normalized claims with their Scripture/source relationships."""

        ids = sorted({normalize_id(value) for value in object_ids if normalize_id(value)})
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"""
            SELECT object_id, claim_id, claim_text, claim_type, certainty,
                   dispute_status, rationale, notes
            FROM canonical_claims
            WHERE object_id IN ({placeholders})
            ORDER BY object_id, claim_id
            """,
            tuple(ids),
        ).fetchall()
        references = self._conn.execute(
            f"""
            SELECT object_id, claim_id, reference_text
            FROM canonical_claim_scripture_references
            WHERE object_id IN ({placeholders})
            ORDER BY object_id, claim_id, reference_text
            """,
            tuple(ids),
        ).fetchall()
        source_rows = self._conn.execute(
            f"""
            SELECT object_id, claim_id, source_id, relationship, source_order
            FROM canonical_claim_sources
            WHERE object_id IN ({placeholders})
            ORDER BY object_id, claim_id,
                     CASE relationship WHEN 'source_id' THEN 0 ELSE 1 END,
                     source_order, source_id
            """,
            tuple(ids),
        ).fetchall()
        refs_by_claim: dict[tuple[str, str], list[str]] = {}
        sources_by_claim: dict[tuple[str, str], list[str]] = {}
        relationships_by_claim: dict[tuple[str, str], dict[str, list[str]]] = {}
        for row in references:
            refs_by_claim.setdefault((str(row["object_id"]), str(row["claim_id"])), []).append(
                str(row["reference_text"])
            )
        for row in source_rows:
            key = (str(row["object_id"]), str(row["claim_id"]))
            source_id = str(row["source_id"])
            if str(row["relationship"]) == "source_id" and source_id not in sources_by_claim.setdefault(key, []):
                sources_by_claim[key].append(source_id)
            relationships_by_claim.setdefault(key, {}).setdefault(str(row["relationship"]), []).append(source_id)
        claims: dict[str, list[dict[str, Any]]] = {object_id: [] for object_id in ids}
        for row in rows:
            key = (str(row["object_id"]), str(row["claim_id"]))
            claims[key[0]].append(
                {
                    "id": key[1],
                    "claim": str(row["claim_text"]),
                    "claim_type": str(row["claim_type"]),
                    "certainty": str(row["certainty"]),
                    "dispute_status": str(row["dispute_status"]),
                    "rationale": str(row["rationale"] or ""),
                    "notes": str(row["notes"] or ""),
                    "scripture_references": refs_by_claim.get(key, []),
                    "source_ids": sources_by_claim.get(key, []),
                    "source_relationships": relationships_by_claim.get(key, {}),
                }
            )
        return claims

    def get_sources(self, object_ids: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
        """Bulk-fetch normalized sources and their authored support metadata."""

        ids = sorted({normalize_id(value) for value in object_ids if normalize_id(value)})
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"""
            SELECT object_id, source_id, title, author, publisher, year, locator,
                   url, source_type, notes
            FROM canonical_sources
            WHERE object_id IN ({placeholders})
            ORDER BY object_id, source_id
            """,
            tuple(ids),
        ).fetchall()
        support_rows = self._conn.execute(
            f"""
            SELECT object_id, source_id, supported_item
            FROM canonical_source_supports
            WHERE object_id IN ({placeholders})
            ORDER BY object_id, source_id, supported_item
            """,
            tuple(ids),
        ).fetchall()
        supports: dict[tuple[str, str], list[str]] = {}
        for row in support_rows:
            supports.setdefault((str(row["object_id"]), str(row["source_id"])), []).append(
                str(row["supported_item"])
            )
        sources: dict[str, list[dict[str, Any]]] = {object_id: [] for object_id in ids}
        for row in rows:
            key = (str(row["object_id"]), str(row["source_id"]))
            sources[key[0]].append(
                {
                    "id": key[1],
                    "title": str(row["title"]),
                    "author": str(row["author"] or ""),
                    "publisher": str(row["publisher"] or ""),
                    "year": row["year"],
                    "locator": str(row["locator"] or ""),
                    "url": str(row["url"] or ""),
                    "source_type": str(row["source_type"]),
                    "supports": supports.get(key, []),
                    "notes": str(row["notes"] or ""),
                }
            )
        return sources

    def retrieve_claim_evidence(
        self,
        question: str,
        object_ids: Sequence[str],
        *,
        parent_scores: Mapping[str, float] | None = None,
        requested_dimensions: Sequence[str] = (),
        scripture_references: Sequence[str] = (),
        limit_per_object: int = 3,
    ) -> dict[str, list[RetrievedClaimEvidence]]:
        ids = sorted({normalize_id(value) for value in object_ids if normalize_id(value)})
        claims_by_id = self.get_claims(ids)
        sources_by_id = self.get_sources(ids)
        objects = self._objects_by_ids(ids)
        ranked: dict[str, list[RetrievedClaimEvidence]] = {}
        for object_id in ids:
            obj = objects.get(object_id)
            if obj is None:
                continue
            parent = {
                "id": obj.id,
                "title": obj.title,
                "type": obj.type,
                "claims": claims_by_id.get(object_id, []),
                "sources": sources_by_id.get(object_id, []),
            }
            ranked[object_id] = rank_claims(
                question,
                parent,
                parent_relevance=float((parent_scores or {}).get(object_id, 0.0)),
                requested_dimensions=requested_dimensions,
                scripture_references=scripture_references,
                limit=limit_per_object,
            )
        return ranked

    def search_fts(self, query: str, *, limit: int = 25) -> list[tuple[str, float]]:
        """Return deterministic FTS5/BM25 candidates (lower raw BM25 is better)."""

        terms = query_search_terms(query)
        if limit <= 0 or not terms:
            return []
        expression = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
        rows = self._conn.execute(
            """
            SELECT object_id,
                   bm25(canonical_fts, 0.0, 12.0, 10.0, 7.0, 8.0, 9.0, 6.0, 3.0, 9.0) AS rank
            FROM canonical_fts
            WHERE canonical_fts MATCH ?
            ORDER BY rank, object_id
            LIMIT ?
            """,
            (expression, int(limit)),
        ).fetchall()
        return [(str(row["object_id"]), float(row["rank"])) for row in rows]

    def get_scripture_matches(self, reference: str, *, limit: int = 10) -> list[RetrievalResult]:
        return self.retrieve_by_scripture_reference(reference, limit=limit)

    def inventory_fingerprint(self) -> str:
        return self._metadata.get("inventory_fingerprint", "")

    def is_stale(self, root: str | Path | None = None) -> bool:
        root_path = Path(root) if root is not None else Path(__file__).resolve().parent
        root_key = root_path.resolve().as_posix()
        signature = inventory_signature(root_path)
        built_signature = self._metadata.get("source_inventory_signature", "")
        if built_signature:
            return built_signature != inventory_content_signature(root_path)
        with _SOURCE_FINGERPRINT_LOCK:
            cached = _SOURCE_FINGERPRINT_CACHE.get(root_key)
        if cached is not None and cached[0] == signature:
            source_fingerprint = cached[1]
        else:
            source_fingerprint = CanonicalLibrary(root=root_path).load().inventory_fingerprint()
            with _SOURCE_FINGERPRINT_LOCK:
                _SOURCE_FINGERPRINT_CACHE[root_key] = (signature, source_fingerprint)
        return self.inventory_fingerprint() != source_fingerprint

    def verify(self, *, root: str | Path | None = None, compare_fingerprint: bool = True) -> dict[str, Any]:
        return verify_database(self.path, root=root, compare_fingerprint=compare_fingerprint)

    def book_alias_lookup(self) -> dict[str, str]:
        return dict(self._book_alias_lookup_cached())

    def _book_alias_lookup_uncached(self) -> dict[str, str]:
        rows = self._conn.execute(
            """
            SELECT o.title, a.original_alias
            FROM canonical_objects o
            LEFT JOIN canonical_aliases a ON a.object_id = o.id
            WHERE o.type = 'book'
            ORDER BY o.id, a.original_alias
            """
        ).fetchall()
        lookup = build_book_alias_lookup(())
        for row in rows:
            title = str(row["title"] or "").strip()
            if not title:
                continue
            lookup[normalize_alias(title)] = title
            alias = str(row["original_alias"] or "").strip()
            if alias:
                lookup[normalize_alias(alias)] = title
        return lookup

    def object_types(self) -> dict[str, list[str]]:
        rows = self._conn.execute(
            "SELECT type, id FROM canonical_objects ORDER BY type, id"
        ).fetchall()
        by_type = {category: [] for category in SUPPORTED_CATEGORIES}
        for row in rows:
            by_type.setdefault(str(row["type"]), []).append(str(row["id"]))
        return by_type

    def object_headers(self, categories: Sequence[str] | None = None) -> list[dict[str, str]]:
        """Return cheap identity metadata without deserializing CKL payloads."""

        if categories:
            normalized = tuple(dict.fromkeys(str(value) for value in categories))
            placeholders = ",".join("?" for _ in normalized)
            rows = self._conn.execute(
                f"SELECT id, type, title FROM canonical_objects WHERE type IN ({placeholders}) ORDER BY type, id",
                normalized,
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, type, title FROM canonical_objects ORDER BY type, id"
            ).fetchall()
        return [
            {"id": str(row["id"]), "type": str(row["type"]), "title": str(row["title"])}
            for row in rows
        ]

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
        scripture_mode = bool(scripture_query is not None and scripture_query.start_chapter is not None)
        if scripture_mode:
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
        } if scripture_mode else {}
        field_terms_by_id = self._field_terms_for_many(sorted(candidate_ids))
        scoring_rows = self._scoring_rows(sorted(candidate_ids))
        exact_ids = set(self.title_matches(query)) | set(self.alias_matches(query))
        preliminary: list[tuple[float, str]] = []
        for object_id in sorted(candidate_ids):
            row = scoring_rows.get(object_id)
            if row is None:
                continue
            base_score, _matched_terms, _matched_fields = score_keyword_result(
                query_terms=query_terms,
                field_terms=field_terms_by_id.get(object_id, {}),
                importance=int(row["importance"]),
            )
            base_score = max(base_score, scripture_scores.get(object_id, 0.0))
            base_score += category_bonus(str(row["type"]), preferred_categories)
            base_score += governance_bonus(str(row["review_status"]), str(row["confidence"]))
            if object_id in exact_ids:
                base_score += 1.0
            preliminary.append((base_score, object_id))
        competitive_limit = max(limit, 30)
        competitive_ids = [
            object_id
            for _score, object_id in sorted(preliminary, key=lambda item: (-item[0], item[1]))[:competitive_limit]
        ]
        objects_by_id = self._objects_by_ids(competitive_ids)
        results: list[RetrievalResult] = []
        for object_id in competitive_ids:
            obj = objects_by_id.get(object_id)
            if obj is None:
                continue
            if category_set and obj.type not in category_set:
                continue
            if library is not None and not library._is_retrievable(obj, **filters):
                continue
            field_terms = field_terms_by_id.get(object_id, {})
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

    def retrieve_hybrid(
        self,
        query: str,
        limit: int = 10,
        *,
        library: Any | None = None,
        apply_thresholds: bool = True,
        categories: Sequence[str] | None = None,
        **filters: Any,
    ) -> list[RetrievalResult]:
        """Fuse deterministic keyword/exact/Scripture and FTS5 BM25 rankings."""

        if limit <= 0:
            return []
        pool_limit = max(30, limit * 2)
        keyword_results = self.retrieve_by_keywords(
            query,
            limit=pool_limit,
            library=library,
            apply_thresholds=False,
            categories=categories,
            **filters,
        )
        fts_results = self.search_fts(query, limit=pool_limit)
        keyword_by_id = {result.object.id: result for result in keyword_results}
        keyword_rank = {result.object.id: index for index, result in enumerate(keyword_results, start=1)}
        fts_rank = {object_id: index for index, (object_id, _rank) in enumerate(fts_results, start=1)}
        candidate_ids = set(keyword_by_id) | set(fts_rank)
        objects = {object_id: result.object for object_id, result in keyword_by_id.items()}
        missing_ids = sorted(candidate_ids - set(objects))
        objects.update(self._objects_by_ids(missing_ids))
        category_set = set(categories or ())
        fused: list[RetrievalResult] = []
        for object_id in sorted(candidate_ids):
            obj = objects.get(object_id)
            if obj is None or (category_set and obj.type not in category_set):
                continue
            if library is not None and not library._is_retrievable(obj, **filters):
                continue
            keyword = keyword_by_id.get(object_id)
            rank = fts_rank.get(object_id)
            query_terms = set(query_search_terms(query))
            title_terms = set(query_search_terms(obj.title))
            alias_exact = any(
                set(query_search_terms(alias)).issubset(query_terms)
                for alias in obj.aliases
                if query_search_terms(alias)
            )
            entity_bonus = 0.24 if (title_terms and title_terms.issubset(query_terms)) or alias_exact else 0.0
            if keyword is not None:
                # A bounded reciprocal-rank boost improves recall but cannot
                # displace privileged exact/entity/Scripture evidence.
                fts_boost = 0.0 if rank is None else 0.16 / (1.0 + 0.10 * (rank - 1))
                keyword_boost = 0.06 / (1.0 + 0.08 * (keyword_rank[object_id] - 1))
                score = min(1.0, keyword.score + fts_boost + keyword_boost + entity_bonus)
                match_type = keyword.match_type
                fields = list(keyword.matched_fields)
                if rank is not None:
                    fields = list(dict.fromkeys([*fields, "fts5"] ))
                fused.append(
                    RetrievalResult(
                        object=obj,
                        score=round(score, 4),
                        match_type=match_type,
                        matched_terms=list(keyword.matched_terms),
                        matched_fields=fields,
                        matched_alias=keyword.matched_alias,
                        ranking_score=round(score, 4),
                        confidence=keyword.confidence,
                    )
                )
                continue
            if rank is None:
                continue
            score = round(0.50 + (0.18 / (1.0 + 0.12 * (rank - 1))) + entity_bonus, 4)
            fused.append(
                RetrievalResult(
                    object=obj,
                    score=score,
                    match_type="keyword",
                    matched_terms=query_search_terms(query),
                    matched_fields=["fts5"],
                    ranking_score=score,
                )
            )
        fused = sort_retrieval_results(fused)
        if apply_thresholds:
            fused = apply_relevance_thresholds(fused)
        return fused[:limit]

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
        holder = getattr(self._local, "connection_holder", None)
        if holder is None:
            conn = self._connect()
            holder = _ThreadConnection(conn)
            self._local.connection_holder = holder
            with self._connections_lock:
                self._connections.append(conn)
        return holder.connection

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

    def _objects_by_ids(self, object_ids: Sequence[str]) -> dict[str, CanonicalObject]:
        ids = sorted({normalize_id(value) for value in object_ids if normalize_id(value)})
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"SELECT id, payload_json FROM canonical_objects WHERE id IN ({placeholders}) ORDER BY id",
            tuple(ids),
        ).fetchall()
        objects: dict[str, CanonicalObject] = {}
        for row in rows:
            object_id = str(row["id"])
            objects[object_id] = validate_object(json.loads(str(row["payload_json"])))
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

    def _field_terms_for_many(self, object_ids: Sequence[str]) -> dict[str, dict[str, set[str]]]:
        ids = sorted({normalize_id(value) for value in object_ids if normalize_id(value)})
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"""
            SELECT object_id, field_name, term
            FROM canonical_keywords
            WHERE object_id IN ({placeholders})
            ORDER BY object_id, field_name, term
            """,
            tuple(ids),
        ).fetchall()
        result: dict[str, dict[str, set[str]]] = {object_id: {} for object_id in ids}
        for row in rows:
            result[str(row["object_id"])].setdefault(str(row["field_name"]), set()).add(str(row["term"]))
        return result

    def _scoring_rows(self, object_ids: Sequence[str]) -> dict[str, sqlite3.Row]:
        ids = sorted({normalize_id(value) for value in object_ids if normalize_id(value)})
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"""
            SELECT id, type, importance, review_status, confidence
            FROM canonical_objects
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        ).fetchall()
        return {str(row["id"]): row for row in rows}


def _close_connection(connection: sqlite3.Connection) -> None:
    try:
        connection.close()
    except sqlite3.ProgrammingError:
        pass


class _ThreadConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __del__(self) -> None:
        _close_connection(self.connection)


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

    def close(self) -> None:
        """Close the SQLite repository backing this compatibility facade."""

        self.repository.close()

    def __del__(self) -> None:
        try:
            self.close()
        except (AttributeError, TypeError):
            pass

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

    def object_headers(self, categories: Sequence[str] | None = None) -> list[dict[str, str]]:
        return self.repository.object_headers(categories)

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
        return self.repository.retrieve_hybrid(
            query,
            limit=limit,
            library=self,
            apply_thresholds=apply_thresholds,
            **filters,
        )

    def retrieve_claim_evidence(
        self,
        question: str,
        object_ids: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, list[RetrievedClaimEvidence]]:
        return self.repository.retrieve_claim_evidence(question, object_ids, **kwargs)

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
