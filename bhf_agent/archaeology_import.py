"""Provider-neutral, explicit archaeology media import workflow."""

from __future__ import annotations

import json
import html
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from .db.common import StudyDataError
from .study_db import create_archaeology_media, list_archaeology_media


class ArchaeologyMediaProvider(ABC):
    """Interface for curated providers; application startup never calls it."""

    name = "provider"

    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_record(self, external_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def fetch_records(self, external_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch a reviewed set of records.

        Providers that support a batched lookup can override this to avoid
        unnecessary requests while preserving the explicit manifest workflow.
        """

        return {
            external_id: self.fetch_record(external_id)
            for external_id in dict.fromkeys(external_ids)
        }

    def normalize_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        return dict(record)

    def normalize_license(self, value: str | None) -> str:
        normalized = str(value or "").strip().lower().replace("-", "_")
        compact = normalized.replace(" ", "_").replace(".", "_")
        if compact.startswith("cc_by_sa"):
            return "cc_by_sa"
        if compact.startswith("cc_by"):
            return "cc_by"
        if compact.startswith("cc0"):
            return "cc0"
        aliases = {
            "public domain": "public_domain",
            "public_domain": "public_domain",
            "pd": "public_domain",
            "cc0": "cc0",
            "cc_by": "cc_by",
            "cc by": "cc_by",
            "cc_by_sa": "cc_by_sa",
            "cc by sa": "cc_by_sa",
        }
        return aliases.get(normalized, aliases.get(compact, "unknown"))


class WikimediaCommonsProvider(ArchaeologyMediaProvider):
    """Explicit Wikimedia Commons file lookup using the MediaWiki API.

    Search returns review candidates only.  ``fetch_record`` accepts a curated
    ``File:`` identifier and captures the file page, direct image URL, preview,
    author/credit and license metadata needed by the normal importer.
    """

    name = "wikimedia"
    api_url = "https://commons.wikimedia.org/w/api.php"
    file_page_base = "https://commons.wikimedia.org/wiki/"

    def __init__(self, *, opener: Any = urlopen, timeout: float = 20.0) -> None:
        self._opener = opener
        self._timeout = timeout

    def search(self, query: str) -> list[dict[str, Any]]:
        payload = self._request(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "list": "search",
                "srsearch": str(query or "").strip(),
                "srnamespace": "6",
                "srlimit": "20",
            }
        )
        candidates = payload.get("query", {}).get("search", [])
        return [
            {
                "external_id": candidate.get("title", ""),
                "title": candidate.get("title", ""),
                "source_url": self._file_page_url(str(candidate.get("title") or "")),
            }
            for candidate in candidates
            if str(candidate.get("title") or "").startswith("File:")
        ]

    def fetch_record(self, external_id: str) -> dict[str, Any]:
        return self.fetch_records([external_id])[external_id]

    def fetch_records(self, external_ids: list[str]) -> dict[str, dict[str, Any]]:
        requested = list(dict.fromkeys(external_ids))
        records: dict[str, dict[str, Any]] = {}
        for start in range(0, len(requested), 50):
            batch = requested[start:start + 50]
            requested_by_title = {
                self._file_title(external_id): external_id
                for external_id in batch
            }
            payload = self._request(
                {
                    "action": "query",
                    "format": "json",
                    "formatversion": "2",
                    "prop": "imageinfo",
                    "iiprop": "url|mime|size|extmetadata",
                    "iiurlwidth": "1200",
                    "titles": "|".join(requested_by_title),
                }
            )
            pages = payload.get("query", {}).get("pages", [])
            pages_by_title = {
                str(page.get("title") or ""): page
                for page in pages
                if not page.get("missing")
            }
            for title, external_id in requested_by_title.items():
                page = pages_by_title.get(title)
                if page is None:
                    raise ValueError(f"Wikimedia Commons file not found: {title}")
                records[external_id] = self._record_from_page(page, title)
        return records

    def _record_from_page(self, page: Mapping[str, Any], title: str) -> dict[str, Any]:
        imageinfo = page.get("imageinfo") or []
        if not imageinfo:
            raise ValueError(f"Wikimedia Commons file has no image metadata: {title}")
        info = imageinfo[0]
        metadata = info.get("extmetadata") or {}
        license_id = _metadata_value(metadata, "LicenseShortName") or _metadata_value(
            metadata, "UsageTerms"
        )
        creator = _metadata_value(metadata, "Artist") or _metadata_value(metadata, "Credit")
        institution = _metadata_value(metadata, "Credit") or _metadata_value(metadata, "Source")
        caption = _metadata_value(metadata, "ImageDescription")
        canonical_title = str(page.get("title") or title)
        return {
            "id": canonical_title,
            "title": canonical_title.removeprefix("File:"),
            "caption": caption,
            "source_url": self._file_page_url(canonical_title),
            "image_url": str(info.get("url") or ""),
            "thumbnail_url": str(info.get("thumburl") or ""),
            "creator": creator,
            "institution": institution,
            "license_id": license_id,
            "license_url": _metadata_value(metadata, "LicenseUrl"),
            "source_record_id": canonical_title,
            "width": info.get("width"),
            "height": info.get("height"),
            "mime": info.get("mime", ""),
        }

    def normalize_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        normalized = dict(record)
        rights = self.normalize_license(str(normalized.get("license_id") or ""))
        normalized["rights_status"] = rights
        reusable = rights in {"public_domain", "cc0", "cc_by", "cc_by_sa"}
        normalized["can_redistribute"] = reusable
        normalized["can_cache"] = reusable
        normalized["can_modify"] = reusable
        creator = str(normalized.get("creator") or "").strip()
        institution = str(normalized.get("institution") or "").strip()
        license_id = str(normalized.get("license_id") or "").strip()
        normalized["attribution_text"] = "\n".join(
            value for value in (creator, institution, license_id) if value
        )
        return normalized

    def normalize_license(self, value: str | None) -> str:
        normalized = str(value or "").strip().lower()
        if "attribution only" in normalized or normalized == "attribution":
            return "other_redistributable"
        return super().normalize_license(value)

    def _request(self, params: Mapping[str, str]) -> dict[str, Any]:
        url = f"{self.api_url}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "BHF-Archaeology-Media/1.0"})
        with self._opener(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Wikimedia Commons API returned an invalid payload")
        return payload

    @staticmethod
    def _file_title(external_id: str) -> str:
        value = str(external_id or "").strip().replace("_", " ")
        if not value:
            raise ValueError("Wikimedia Commons external_id is required")
        return value if value.lower().startswith("file:") else f"File:{value}"

    def _file_page_url(self, title: str) -> str:
        return f"{self.file_page_base}{quote(self._file_title(title).replace(' ', '_'))}"


class MetOpenAccessProvider(ArchaeologyMediaProvider):
    """Curated Metropolitan Museum of Art Open Access object lookup.

    Only API records explicitly marked ``isPublicDomain`` and carrying a
    primary image can be normalized into reusable archaeology media.
    """

    name = "met"
    api_base = "https://collectionapi.metmuseum.org/public/collection/v1"
    open_access_url = "https://www.metmuseum.org/hubs/open-access"

    def __init__(self, *, opener: Any = urlopen, timeout: float = 20.0) -> None:
        self._opener = opener
        self._timeout = timeout

    def search(self, query: str) -> list[dict[str, Any]]:
        payload = self._request(
            "/search",
            {"q": str(query or "").strip(), "hasImages": "true"},
        )
        return [
            {"external_id": str(object_id), "source_url": self._object_url(object_id)}
            for object_id in (payload.get("objectIDs") or [])[:20]
        ]

    def fetch_record(self, external_id: str) -> dict[str, Any]:
        object_id = self._object_id(external_id)
        record = self._request(f"/objects/{object_id}")
        if not record.get("isPublicDomain"):
            raise ValueError(f"Met object is not public domain: {object_id}")
        image_url = str(record.get("primaryImage") or "").strip()
        if not image_url:
            raise ValueError(f"Met public-domain object has no primary image: {object_id}")
        title = str(record.get("title") or record.get("objectName") or f"Met object {object_id}")
        date = str(record.get("objectDate") or "").strip()
        culture = str(record.get("culture") or "").strip()
        medium = str(record.get("medium") or "").strip()
        caption_parts = [value for value in (title, date, culture, medium) if value]
        return {
            "id": str(object_id),
            "title": title,
            "caption": " · ".join(caption_parts),
            "source_url": str(record.get("objectURL") or self._object_url(object_id)),
            "image_url": image_url,
            "thumbnail_url": str(record.get("primaryImageSmall") or ""),
            "creator": str(record.get("artistDisplayName") or "").strip(),
            "institution": str(record.get("repository") or "Metropolitan Museum of Art").strip(),
            "license_id": "Public Domain / Met Open Access",
            "license_url": self.open_access_url,
            "rights_status": "public_domain",
            "can_redistribute": True,
            "can_cache": True,
            "can_modify": True,
            "source_record_id": str(object_id),
            "object_date": date,
            "object_number": str(record.get("accessionNumber") or "").strip(),
        }

    def normalize_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        normalized = dict(record)
        if normalized.get("rights_status") != "public_domain":
            normalized.update(
                {
                    "rights_status": "unknown",
                    "can_redistribute": False,
                    "can_cache": False,
                    "can_modify": False,
                }
            )
            return normalized
        normalized["attribution_text"] = "\n".join(
            value
            for value in (
                str(normalized.get("creator") or "").strip(),
                str(normalized.get("institution") or "").strip(),
                str(normalized.get("license_id") or "").strip(),
            )
            if value
        )
        return normalized

    def _request(self, endpoint: str, params: Mapping[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.api_base}{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "BHF-Archaeology-Media/1.0"})
        with self._opener(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Met Open Access API returned an invalid payload")
        return payload

    @staticmethod
    def _object_id(external_id: str) -> int:
        value = str(external_id or "").strip()
        if not value.isdigit() or int(value) <= 0:
            raise ValueError("Met Open Access external_id must be a positive object ID")
        return int(value)

    @staticmethod
    def _object_url(object_id: int | str) -> str:
        return f"https://www.metmuseum.org/art/collection/search/{object_id}"


class FixtureArchaeologyMediaProvider(ArchaeologyMediaProvider):
    """Provider used by reviewable local fixtures and importer tests."""

    name = "fixture"

    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self.records = {str(key): dict(value) for key, value in records.items()}

    def search(self, query: str) -> list[dict[str, Any]]:
        needle = str(query or "").strip().lower()
        return [
            record
            for record in self.records.values()
            if not needle or needle in json.dumps(record, sort_keys=True).lower()
        ]

    def fetch_record(self, external_id: str) -> dict[str, Any]:
        try:
            return dict(self.records[str(external_id)])
        except KeyError as exc:
            raise ValueError(f"fixture archaeology media record not found: {external_id}") from exc


def import_archaeology_manifest(
    manifest_path: str | Path,
    *,
    provider: ArchaeologyMediaProvider,
    database_path: str | Path,
) -> list[dict[str, Any]]:
    """Import only explicitly listed records through a selected provider."""

    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    entries = payload.get("entries", []) if isinstance(payload, Mapping) else payload
    if not isinstance(entries, list):
        raise ValueError("archaeology manifest entries must be a list")
    external_ids = [
        str(entry["external_id"])
        for entry in entries
        if isinstance(entry, Mapping) and str(entry.get("external_id") or "").strip()
    ]
    fetched_records = provider.fetch_records(external_ids)
    imported: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or not str(entry.get("external_id") or "").strip():
            raise ValueError("each archaeology manifest entry requires external_id")
        external_id = str(entry["external_id"])
        record = provider.normalize_record(fetched_records[external_id])
        record["id"] = str(entry.get("id") or record.get("id") or entry["external_id"])
        if entry.get("archaeology_item_id"):
            record["archaeology_item_id"] = entry["archaeology_item_id"]
        if entry.get("archaeology_site_id"):
            record["archaeology_site_id"] = entry["archaeology_site_id"]
        if entry.get("rights_status"):
            record["rights_status"] = entry["rights_status"]
        else:
            record["rights_status"] = provider.normalize_license(record.get("license_id"))
        for field_name in ("title", "caption", "media_type"):
            if entry.get(field_name):
                record[field_name] = entry[field_name]
        # The database insertion performs the final validation against the
        # actual archaeology item/site IDs in the target database.
        try:
            imported.append(create_archaeology_media(record, path=database_path))
        except StudyDataError as exc:
            if str(exc) != "archaeology media already exists":
                raise
            imported.append(_existing_media(record, database_path))
    return imported


def _metadata_value(metadata: Mapping[str, Any], name: str) -> str:
    value = metadata.get(name, "")
    if isinstance(value, Mapping):
        value = value.get("value", "")
    text = html.unescape(re.sub(r"<[^>]+>", "", str(value or "")))
    return " ".join(text.split())


def _existing_media(record: Mapping[str, Any], database_path: str | Path) -> dict[str, Any]:
    item_id = str(record.get("archaeology_item_id") or "").strip()
    site_id = str(record.get("archaeology_site_id") or "").strip()
    records = list_archaeology_media(
        item_id=item_id if item_id else None,
        site_id=site_id if site_id else None,
        path=database_path,
    )
    return next(
        candidate for candidate in records if candidate.get("id") == record.get("id")
    )
