"""Structured models returned by the commentary subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScriptureAnchor:
    book: str
    start_chapter: int | None = None
    start_verse: int | None = None
    end_chapter: int | None = None
    end_verse: int | None = None
    relationship: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "book": self.book,
            "start_chapter": self.start_chapter,
            "start_verse": self.start_verse,
            "end_chapter": self.end_chapter,
            "end_verse": self.end_verse,
            "relationship": self.relationship,
        }


@dataclass(frozen=True)
class CommentarySource:
    id: str
    name: str
    copyright: str | None = None
    license: str | None = None
    license_url: str | None = None
    attribution: str | None = None
    source_url: str | None = None
    source_sha256: str | None = None
    imported_at: str | None = None
    importer_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "copyright": self.copyright,
            "license": self.license,
            "license_url": self.license_url,
            "attribution": self.attribution,
            "source_url": self.source_url,
            "source_sha256": self.source_sha256,
            "imported_at": self.imported_at,
            "importer_version": self.importer_version,
        }


@dataclass(frozen=True)
class CommentaryEntry:
    id: int
    source: CommentarySource
    source_id: str
    external_id: str | None
    kind: str
    title: str | None
    body: str
    sort_order: int
    source_locator: str | None
    anchor: ScriptureAnchor | None = None
    payload: dict[str, Any] | None = None
    match_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "external_id": self.external_id,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "sort_order": self.sort_order,
            "source_locator": self.source_locator,
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "source": self.source.to_dict(),
            "match_type": self.match_type,
            "payload": self.payload,
        }
