"""JSON-backed CKL repository adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .loader import CanonicalLibrary
from .normalization import normalize_alias, normalize_id
from .retrieval import RetrievalResult, query_search_terms
from .schema import CanonicalObject


class JsonCanonicalRepository:
    """Repository implementation backed by the committed CKL JSON files."""

    def __init__(self, root: str | Path | None = None, *, library: CanonicalLibrary | None = None) -> None:
        self.library = library or (CanonicalLibrary(root=Path(root)).load() if root is not None else CanonicalLibrary.load_default())

    def get_by_id(self, object_id: str) -> CanonicalObject | None:
        return self.library.objects_by_id.get(normalize_id(object_id))

    def get_by_alias(self, alias: str, *, category: str | None = None) -> list[CanonicalObject]:
        object_ids = self.library.objects_by_alias.get(normalize_alias(alias), [])
        return self._objects_for_ids(object_ids, category=category)

    def get_by_title(self, title: str, *, category: str | None = None) -> list[CanonicalObject]:
        object_ids = self.library._title_matches(title)
        return self._objects_for_ids(object_ids, category=category)

    def list_by_type(self, object_type: str) -> list[CanonicalObject]:
        return self._objects_for_ids(self.library.objects_by_type.get(object_type, []))

    def search_keywords(
        self,
        terms: Sequence[str],
        *,
        categories: Sequence[str] | None = None,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        query = " ".join(terms)
        results = self.library.retrieve_by_keywords(query, limit=max(limit, 0))
        if categories:
            category_set = set(categories)
            results = [result for result in results if result.object.type in category_set]
        return results[:limit]

    def get_relationships(self, object_id: str, *, minimum_weight: int = 1) -> list[dict[str, object]]:
        obj = self.get_by_id(object_id)
        if obj is None:
            return []
        from .context_builder import CanonicalContextBuilder

        builder = CanonicalContextBuilder(self.library)
        return [
            relationship
            for relationship in builder._normalize_related_objects(obj)
            if int(relationship["weight"]) >= minimum_weight
        ]

    def get_scripture_matches(self, reference: str, *, limit: int = 10) -> list[RetrievalResult]:
        return self.library.retrieve_by_scripture_reference(reference, limit=limit)

    def inventory_fingerprint(self) -> str:
        return self.library.inventory_fingerprint()

    def is_stale(self) -> bool:
        return False

    def _objects_for_ids(self, object_ids: Sequence[str], *, category: str | None = None) -> list[CanonicalObject]:
        objects: list[CanonicalObject] = []
        for object_id in sorted(dict.fromkeys(object_ids)):
            obj = self.library.objects_by_id.get(object_id)
            if obj is None:
                continue
            if category is not None and obj.type != category:
                continue
            objects.append(obj)
        return objects
