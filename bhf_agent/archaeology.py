"""Shared archaeology evidence/media policy helpers.

The deterministic evidence records live in the study database.  This module
contains the small, dependency-free policy boundary used by importers,
serializers, and offline-pack builders so image rights fail closed in one
place.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse


MEDIA_RIGHTS_VALUES = (
    "public_domain",
    "cc0",
    "cc_by",
    "cc_by_sa",
    "other_redistributable",
    "remote_display_only",
    "link_only",
    "unknown",
)

REDISTRIBUTABLE_RIGHTS = frozenset(
    {"public_domain", "cc0", "cc_by", "cc_by_sa", "other_redistributable"}
)

ATTRIBUTION_REQUIRED_RIGHTS = frozenset({"cc_by", "cc_by_sa"})


class ArchaeologyValidationError(ValueError):
    """Raised when archaeology evidence/media violates a hard policy."""


def media_can_bundle(media: Mapping[str, Any]) -> bool:
    """Return whether media may be copied into a repository or offline pack."""

    rights = str(media.get("rights_status") or "unknown").strip().lower()
    return (
        rights in REDISTRIBUTABLE_RIGHTS
        and _as_bool(media.get("can_redistribute"))
        and _as_bool(media.get("can_cache"))
    )


def attribution_text(media: Mapping[str, Any]) -> str:
    """Build a compact, reusable attribution line from normalized metadata."""

    explicit = str(media.get("attribution_text") or "").strip()
    if explicit:
        return explicit
    parts = [
        str(media.get("creator") or "").strip(),
        str(media.get("institution") or "").strip(),
        str(media.get("license_id") or "").strip(),
    ]
    return "\n".join(part for part in parts if part)


def validate_media_record(
    media: Mapping[str, Any],
    *,
    archaeology_item_ids: Iterable[str] = (),
    archaeology_site_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Validate and normalize one archaeology media record.

    Unknown rights are deliberately not an error, but they can never become
    redistributable/cacheable.  This lets remote/link-only records remain
    useful while preventing accidental bundling.
    """

    record = dict(media)
    record_id = str(record.get("id") or "").strip()
    if not record_id:
        raise ArchaeologyValidationError("media id is required")

    rights = str(record.get("rights_status") or "unknown").strip().lower()
    if rights not in MEDIA_RIGHTS_VALUES:
        raise ArchaeologyValidationError(f"unsupported media rights status: {rights}")
    record["rights_status"] = rights

    item_id = str(record.get("archaeology_item_id") or "").strip()
    site_id = str(record.get("archaeology_site_id") or "").strip()
    if bool(item_id) == bool(site_id):
        raise ArchaeologyValidationError(
            "media must reference exactly one archaeology item or archaeology site"
        )
    if item_id and item_id not in {str(value) for value in archaeology_item_ids}:
        raise ArchaeologyValidationError(f"media references missing archaeology item: {item_id}")
    if site_id and site_id not in {str(value) for value in archaeology_site_ids}:
        raise ArchaeologyValidationError(f"media references missing archaeology site: {site_id}")

    source_url = str(record.get("source_url") or "").strip()
    image_url = str(record.get("image_url") or "").strip()
    thumbnail_url = str(record.get("thumbnail_url") or "").strip()
    for field_name, value in (("source_url", source_url), ("image_url", image_url), ("thumbnail_url", thumbnail_url)):
        if value and urlparse(value).scheme not in {"http", "https"}:
            raise ArchaeologyValidationError(f"{field_name} must be an http(s) URL")
        record[field_name] = value

    requested_redistribute = _as_bool(record.get("can_redistribute"))
    requested_cache = _as_bool(record.get("can_cache"))
    requested_modify = _as_bool(record.get("can_modify"))
    if rights not in REDISTRIBUTABLE_RIGHTS and (
        requested_redistribute or requested_cache or requested_modify
    ):
        raise ArchaeologyValidationError(
            f"{rights} media cannot be marked redistributable, cacheable, or modifiable"
        )
    can_redistribute = requested_redistribute
    can_cache = requested_cache
    can_modify = requested_modify
    if rights not in REDISTRIBUTABLE_RIGHTS:
        can_redistribute = False
        can_cache = False
        can_modify = False
    if rights in ATTRIBUTION_REQUIRED_RIGHTS and not attribution_text(record):
        raise ArchaeologyValidationError(
            f"{rights} media requires creator, institution, license, or attribution_text"
        )
    if can_cache and not can_redistribute:
        raise ArchaeologyValidationError("cacheable media must be explicitly redistributable")
    local_asset_path = str(record.get("local_asset_path") or "").strip()
    if local_asset_path and not can_redistribute:
        raise ArchaeologyValidationError("local assets require explicit redistribution permission")

    record.update(
        {
            "archaeology_item_id": item_id,
            "archaeology_site_id": site_id,
            "can_redistribute": can_redistribute,
            "can_cache": can_cache,
            "can_modify": can_modify,
            "attribution_text": attribution_text(record),
            "local_asset_path": local_asset_path,
        }
    )
    return record


def validate_media_records(
    records: Iterable[Mapping[str, Any]],
    *,
    archaeology_item_ids: Iterable[str] = (),
    archaeology_site_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Validate a manifest/import batch, including duplicate media IDs."""

    item_ids = {str(value) for value in archaeology_item_ids}
    site_ids = {str(value) for value in archaeology_site_ids}
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        candidate = validate_media_record(
            record,
            archaeology_item_ids=item_ids,
            archaeology_site_ids=site_ids,
        )
        if candidate["id"] in seen:
            raise ArchaeologyValidationError(f"duplicate media id: {candidate['id']}")
        seen.add(candidate["id"])
        normalized.append(candidate)
    return normalized


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}
