"""Importer for Open Scriptures Greek lexical XML exports."""

from __future__ import annotations

from pathlib import Path

from ._xml_common import import_xml


DEFAULT_SOURCE = "Open Scriptures Greek Lexicon"
DEFAULT_LICENSE = "CC BY-SA"
DEFAULT_ATTRIBUTION = "Open Scriptures Project"


def import_greek(
    path: str | Path,
    *,
    source: str = DEFAULT_SOURCE,
    license_name: str = DEFAULT_LICENSE,
    attribution: str = DEFAULT_ATTRIBUTION,
    source_url: str = "https://github.com/openscriptures/strongs",
    revision: str = "unspecified",
):
    return import_xml(
        path,
        language="greek",
        source=source,
        license_name=license_name,
        attribution=attribution,
        source_url=source_url,
        revision=revision,
    )
