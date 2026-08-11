"""Public internal boundary for deterministic archaeology retrieval.

The service deliberately composes the established study database repository and
passage resolver.  Callers outside the archaeology domain should not need to
know table names, media policy, or resolver ranking details.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .archaeology_resolver import resolve_archaeology_evidence
from .study_db import (
    DEFAULT_DB_PATH,
    StudyDataError,
    get_archaeology_item,
    get_archaeology_site,
    list_archaeology_ckl_links,
    list_archaeology_items,
    list_archaeology_media,
    list_archaeology_scripture_links,
    list_archaeology_sites,
)


class ArchaeologyService:
    """Deterministic, local-first archaeology evidence service."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self.path = path

    def get_item(self, item_id: str) -> dict[str, Any]:
        item = get_archaeology_item(item_id, path=self.path)
        item["related_ckl"] = self.related_ckl_objects(item_id)
        item["related_passages"] = self.related_passages(item_id)
        return item

    def get_site(self, site_id: str) -> dict[str, Any]:
        site = get_archaeology_site(site_id, path=self.path)
        site["related_ckl"] = self._unique_links(
            link for item in site.get("archaeology_items", []) for link in self.related_ckl_objects(item["id"])
        )
        return site

    def for_passage(self, **kwargs: Any) -> dict[str, Any]:
        return resolve_archaeology_evidence(path=self.path, **kwargs)

    def search(
        self,
        query: str | None = None,
        *,
        period: str | None = None,
        item_type: str | None = None,
        site: str | None = None,
        biblical_book: str | None = None,
        confidence: str | None = None,
        relationship: str | None = None,
        limit: int = 100,
        include_media: bool = True,
    ) -> list[dict[str, Any]]:
        """Search independently browsable archaeology records with simple filters."""

        normalized_query = str(query or "").strip().casefold()
        normalized_type = str(item_type or "").strip().casefold()
        normalized_site = str(site or "").strip().casefold()
        normalized_book = str(biblical_book or "").strip().casefold()
        normalized_confidence = str(confidence or "").strip().casefold()
        normalized_relationship = str(relationship or "").strip().casefold()
        sites = {
            record["id"]: record
            for record in list_archaeology_sites(path=self.path, include_details=False)
        }
        results: list[dict[str, Any]] = []
        for item in list_archaeology_items(
            period=period,
            path=self.path,
            include_media=include_media,
        ):
            site_record = sites.get(item.get("site_id"), {})
            links = item.get("scripture_links", [])
            searchable = " ".join(
                str(value or "")
                for value in (
                    item.get("id"), item.get("name"), item.get("item_type"), item.get("period"),
                    item.get("why_it_matters"), site_record.get("name"), site_record.get("ancient_region"),
                )
            ).casefold()
            if normalized_query and normalized_query not in searchable:
                continue
            if normalized_type and normalized_type not in str(item.get("item_type") or "").casefold():
                continue
            if normalized_site and normalized_site not in {str(item.get("site_id") or "").casefold(), str(site_record.get("name") or "").casefold()}:
                continue
            if normalized_confidence and normalized_confidence != str(item.get("confidence") or "").casefold():
                continue
            if normalized_book and not any(normalized_book == str(link.get("book") or "").casefold() for link in links):
                continue
            if normalized_relationship and not any(normalized_relationship == str(link.get("relationship_type") or "").casefold() for link in links):
                continue
            results.append(self._card(item, site_record, include_media=include_media))
            if len(results) >= max(1, min(int(limit), 100)):
                break
        return results

    def browse(self, **filters: Any) -> list[dict[str, Any]]:
        return self.search(**filters)

    def media_for_item(self, item_id: str) -> list[dict[str, Any]]:
        return list_archaeology_media(item_id=item_id, path=self.path)

    def related_passages(self, item_id: str) -> list[dict[str, Any]]:
        return list_archaeology_scripture_links(item_id, path=self.path)

    def related_ckl_objects(self, item_id: str) -> list[dict[str, str]]:
        return list_archaeology_ckl_links(item_id, path=self.path)

    def related_to_ckl(
        self,
        ckl_object_id: str,
        *,
        include_media: bool = True,
    ) -> list[dict[str, Any]]:
        normalized = str(ckl_object_id or "").strip()
        if not normalized:
            return []
        return [
            self._card(
                get_archaeology_item(
                    link["archaeology_item_id"],
                    path=self.path,
                    include_media=include_media,
                ),
                {},
                include_media=include_media,
            ) | {"relationship": link["relationship"], "relationship_notes": link["notes"]}
            for link in list_archaeology_ckl_links(
                path=self.path,
                ckl_object_id=normalized,
            )
        ]

    def _card(
        self,
        item: dict[str, Any],
        site: dict[str, Any],
        *,
        include_media: bool = True,
    ) -> dict[str, Any]:
        media = list(item.get("media") or self.media_for_item(item["id"])) if include_media else []
        primary_media = next((record for record in media if record.get("thumbnail_url") or record.get("image_url")), None)
        return {
            "id": item["id"], "title": item.get("name", ""), "item_type": item.get("item_type", ""),
            "period": item.get("period", ""), "site_id": item.get("site_id", ""),
            "site_name": site.get("name", ""), "confidence": item.get("confidence", "unknown"),
            "summary": item.get("why_it_matters", ""),
            "caution": item.get("bhf_caution", ""),
            "scripture_links": list(item.get("scripture_links") or self.related_passages(item["id"])),
            "media": media, "primary_media": primary_media,
        }

    @staticmethod
    def _unique_links(links: Iterable[dict[str, str]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for link in links:
            key = (link["ckl_object_id"], link["relationship"])
            if key not in seen:
                result.append(link)
                seen.add(key)
        return result
