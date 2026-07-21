"""Importer for Open Scriptures Hebrew lexical XML exports."""

from __future__ import annotations

from pathlib import Path

from ._xml_common import import_xml


DEFAULT_SOURCE = "Open Scriptures Hebrew Lexicon"
DEFAULT_LICENSE = "CC BY-SA"
DEFAULT_ATTRIBUTION = "Open Scriptures Hebrew Bible Project"


def import_hebrew(
    path: str | Path,
    *,
    source: str = DEFAULT_SOURCE,
    license_name: str = DEFAULT_LICENSE,
    attribution: str = DEFAULT_ATTRIBUTION,
    source_url: str = "https://github.com/openscriptures/HebrewLexicon",
    revision: str = "unspecified",
):
    return import_xml(
        path,
        language="hebrew",
        source=source,
        license_name=license_name,
        attribution=attribution,
        source_url=source_url,
        revision=revision,
    )
