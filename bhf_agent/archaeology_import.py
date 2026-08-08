"""Provider-neutral, explicit archaeology media import workflow."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

from .study_db import create_archaeology_media


class ArchaeologyMediaProvider(ABC):
    """Interface for curated providers; application startup never calls it."""

    name = "provider"

    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_record(self, external_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def normalize_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        return dict(record)

    def normalize_license(self, value: str | None) -> str:
        normalized = str(value or "").strip().lower().replace("-", "_")
        compact = normalized.replace(" ", "_").replace(".", "_")
        if compact.startswith("cc_by_sa"):
            return "cc_by_sa"
        if compact.startswith("cc_by"):
            return "cc_by"
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
    imported: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or not str(entry.get("external_id") or "").strip():
            raise ValueError("each archaeology manifest entry requires external_id")
        record = provider.normalize_record(provider.fetch_record(str(entry["external_id"])))
        record["id"] = str(entry.get("id") or record.get("id") or entry["external_id"])
        if entry.get("archaeology_item_id"):
            record["archaeology_item_id"] = entry["archaeology_item_id"]
        if entry.get("archaeology_site_id"):
            record["archaeology_site_id"] = entry["archaeology_site_id"]
        if entry.get("rights_status"):
            record["rights_status"] = entry["rights_status"]
        else:
            record["rights_status"] = provider.normalize_license(record.get("license_id"))
        # The database insertion performs the final validation against the
        # actual archaeology item/site IDs in the target database.
        imported.append(create_archaeology_media(record, path=database_path))
    return imported
