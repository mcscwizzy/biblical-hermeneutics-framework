"""Bundle real BHF evidence for a canonical chapter from CKL and data services."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from bhf_agent import bible
from bhf_agent.presentation.evidence import build_evidence_bundle
from bhf_agent.presentation.models import EvidenceBundle
from bhf_agent.ckl import load_canonical_library
from bhf_agent.study_db import (
    list_archaeology_passage_summaries,
    list_passage_map_summaries,
)
from framework.canonical_library import CKLRepositoryConfig


LOGGER = logging.getLogger(__name__)
_CANONICAL_LIBRARY_CACHE: Any | None = None


def get_chapter_evidence_bundle(
    book: str,
    chapter: int,
    study_db_path: str | Path | None = None,
) -> EvidenceBundle | None:
    """Retrieve REAL evidence bundle for a canonical chapter from BHF systems.

    Integrates:
    - Canonical Scripture text
    - CKL (people, places, events, themes, historical context, etc.)
    - Archaeology data
    - Map/geography data
    - Narration/context from CKL

    Only evidence explicitly anchored to this passage is included.
    """
    try:
        chapter_data = bible.resolve_chapter(book, chapter)
    except bible.BibleError:
        return None

    reference = bible.verse_range_reference(book, chapter)

    # Retrieve canonical library results for this chapter
    canonical_results = _retrieve_canonical_results(reference)

    # Retrieve archaeology summaries for this chapter
    archaeology_records = _retrieve_archaeology(book, chapter, study_db_path)

    # Retrieve map/geography for this chapter
    geography_data = _retrieve_geography(book, chapter, study_db_path)

    # Build the evidence bundle using BHF's standard integration
    try:
        bundle = build_evidence_bundle(
            reference,
            canonical_results=canonical_results,
            geography=geography_data,
            archaeology=archaeology_records,
        )
        return bundle
    except Exception as exc:
        LOGGER.error(f"Failed to build evidence bundle for {reference}: {exc}")
        return None


def _retrieve_canonical_results(reference: str) -> list[Any]:
    """Query the canonical library for all objects relevant to this scripture reference."""
    global _CANONICAL_LIBRARY_CACHE

    try:
        if _CANONICAL_LIBRARY_CACHE is None:
            _CANONICAL_LIBRARY_CACHE = load_canonical_library(
                config=CKLRepositoryConfig()
            )
        library = _CANONICAL_LIBRARY_CACHE

        lookup = getattr(library, "retrieve_by_scripture_reference", None)
        if not callable(lookup):
            LOGGER.warning("Canonical library scripture index unavailable")
            return []

        results = list(lookup(reference, limit=100, include_placeholders=False))
        return results

    except Exception as exc:
        LOGGER.error(f"Error retrieving canonical results for {reference}: {exc}")
        return []


def _retrieve_archaeology(book: str, chapter: int, study_db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Retrieve archaeology records for this chapter."""
    try:
        if study_db_path is None:
            from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS
            study_db_path = RUNTIME_DATA_PATHS.study_db_path

        records = list_archaeology_passage_summaries(
            book,
            chapter,
            start_verse=1,
            end_verse=9999,
            path=study_db_path,
            limit=20,
            prepare_schema=False,
        )
        return records or []

    except Exception as exc:
        LOGGER.debug(f"No archaeology data for {book} {chapter}: {exc}")
        return []


def _retrieve_geography(book: str, chapter: int, study_db_path: str | Path | None = None) -> dict[str, Any]:
    """Retrieve map/geography data for this chapter."""
    try:
        if study_db_path is None:
            from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS
            study_db_path = RUNTIME_DATA_PATHS.study_db_path

        map_data = list_passage_map_summaries(
            book,
            chapter,
            start_verse=1,
            end_verse=9999,
            path=study_db_path,
            limit=20,
        )
        if map_data:
            return {"places": map_data.get("places", []), "routes": map_data.get("routes", [])}
        return {}

    except Exception as exc:
        LOGGER.debug(f"No map data for {book} {chapter}: {exc}")
        return {}
