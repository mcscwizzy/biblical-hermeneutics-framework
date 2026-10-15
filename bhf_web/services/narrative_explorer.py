"""Read-only retrieval orchestration for the Narrative Explorer API."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from bhf_agent.archaeology_service import ArchaeologyService
from bhf_agent.bible import BibleError, resolve_chapter, resolve_passage
from bhf_agent.presentation.narrative_explorer import (
    DomainLookup,
    project_narrative_explorer,
    validate_projection,
)
from bhf_agent.study_db import require_current_study_database
from framework.canonical_library import CKLRepositoryConfig
from framework.canonical_library.json_repository import JsonCanonicalRepository
from framework.canonical_library.repository import repository_config_from_env
from framework.canonical_library.sqlite_repository import (
    SQLiteCanonicalLibrary,
    SQLiteCanonicalRepository,
)

from ..map_service import get_map_routes_for_passage, resolve_places_for_passage


LOGGER = logging.getLogger(__name__)
ARCHAEOLOGY_RESULT_LIMIT = 25
_DEFAULT_PROVIDER = object()


class InvalidNarrativePassage(ValueError):
    """A caller supplied a book/chapter or verse scope that cannot resolve."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class CanonicalLookupUnavailable(RuntimeError):
    """The authoritative CKL lookup could not be completed."""


class NarrativeExplorerService:
    """Assemble existing source records, then delegate projection to NE-2."""

    def __init__(
        self,
        *,
        study_db_path: str | Path,
        canonical_library_provider: Callable[[], Any] | None | object = _DEFAULT_PROVIDER,
        maps_lookup_provider: Callable[..., DomainLookup] | None = None,
        archaeology_lookup_provider: Callable[..., DomainLookup] | None = None,
    ) -> None:
        self.study_db_path = Path(study_db_path)
        self.canonical_library_provider = (
            self._default_canonical_library
            if canonical_library_provider is _DEFAULT_PROVIDER
            else canonical_library_provider
        )
        self.maps_lookup_provider = maps_lookup_provider
        self.archaeology_lookup_provider = archaeology_lookup_provider
        self._canonical_library: Any | None = None

    @staticmethod
    def _default_canonical_library() -> Any:
        # Honor the configured repository while hardening its lifecycle for a
        # GET request: an existing SQLite index is opened read-only, and a
        # missing or stale index falls back to the committed JSON source. In
        # particular, a configured "rebuild" policy never builds here.
        config = repository_config_from_env(CKLRepositoryConfig(read_only=True))
        json_root = (
            Path(config.json_root).expanduser()
            if config.json_root
            else Path(__file__).resolve().parents[2] / "framework" / "canonical_library"
        )
        if config.backend == "json":
            return JsonCanonicalRepository(root=json_root).library
        if config.backend != "sqlite":
            raise ValueError("unsupported canonical repository backend")

        database_path = Path(config.database_path).expanduser()
        stale_policy = config.stale_database_policy
        if not database_path.is_file():
            if stale_policy not in {"fallback_to_json", "rebuild"}:
                raise FileNotFoundError("canonical repository is unavailable")
            return JsonCanonicalRepository(root=json_root).library

        repository = SQLiteCanonicalRepository(
            database_path,
            read_only=True,
            cache_size=config.cache_size,
        )
        try:
            stale = stale_policy != "ignore" and repository.is_stale(json_root)
        except Exception:
            repository.close()
            raise
        if not stale:
            return SQLiteCanonicalLibrary(repository, root=json_root)

        repository.close()
        if stale_policy in {"fallback_to_json", "rebuild"}:
            return JsonCanonicalRepository(root=json_root).library
        raise RuntimeError("canonical repository is stale")

    def build(
        self,
        book: str,
        chapter: int,
        *,
        verse_start: int | None = None,
        verse_end: int | None = None,
    ) -> dict[str, Any]:
        passage = self._resolve_passage(book, chapter, verse_start, verse_end)
        reference = (
            f"{passage['book']} {int(passage['chapter'])}"
            if verse_start is None
            else str(passage["reference"])
        )

        # CKL is authoritative for the exploration. If this lookup cannot run,
        # do not hide the failure behind a projection with empty CKL coverage.
        canonical_lookup = self._lookup_canonical(reference)
        lookup_arguments = {
            "book": str(passage["book"]),
            "chapter": int(passage["chapter"]),
            "verse_start": verse_start,
            "verse_end": verse_end if verse_end is not None else verse_start,
            "passage_text": str(passage.get("selected_text") or ""),
        }
        map_lookup = self._lookup_domain(
            domain="maps",
            provider=self.maps_lookup_provider or self._lookup_maps,
            arguments=lookup_arguments,
        )
        archaeology_lookup = self._lookup_domain(
            domain="archaeology",
            provider=self.archaeology_lookup_provider or self._lookup_archaeology,
            arguments=lookup_arguments,
        )

        result = project_narrative_explorer(
            reference,
            canonical_lookup=canonical_lookup,
            map_lookup=map_lookup,
            archaeology_lookup=archaeology_lookup,
        ).to_dict()
        validate_projection(result)
        return result

    @staticmethod
    def _resolve_passage(
        book: str,
        chapter: int,
        verse_start: int | None,
        verse_end: int | None,
    ) -> dict[str, Any]:
        if verse_end is not None and verse_start is None:
            raise InvalidNarrativePassage(
                "verse_end requires verse_start",
                status_code=422,
            )
        if verse_start is not None and verse_start < 1:
            raise InvalidNarrativePassage("verse_start must be positive", status_code=422)
        if verse_end is not None and verse_end < 1:
            raise InvalidNarrativePassage("verse_end must be positive", status_code=422)
        if verse_start is not None and verse_end is not None and verse_end < verse_start:
            raise InvalidNarrativePassage(
                "verse_end must be greater than or equal to verse_start",
                status_code=422,
            )
        try:
            resolve_chapter(book, chapter)
        except (BibleError, ValueError, TypeError) as exc:
            raise InvalidNarrativePassage("book or chapter not found", status_code=404) from exc
        try:
            return resolve_passage(book, chapter, verse_start, verse_end)
        except (BibleError, ValueError, TypeError) as exc:
            raise InvalidNarrativePassage("verse range not found", status_code=422) from exc

    def _lookup_canonical(self, reference: str) -> DomainLookup:
        provider = self.canonical_library_provider
        if not callable(provider):
            raise CanonicalLookupUnavailable("canonical lookup provider is unavailable")
        try:
            if self._canonical_library is None:
                self._canonical_library = provider()
            library = self._canonical_library
            lookup = getattr(library, "retrieve_by_scripture_reference", None)
            if not callable(lookup):
                raise TypeError("canonical Scripture retrieval is unavailable")
            limit = _full_inventory_limit(library)
            records = lookup(
                reference,
                limit=limit,
                include_placeholders=True,
            )
            if records is None:
                raise TypeError("canonical Scripture retrieval returned no result")
            return DomainLookup(domain="ckl", records=tuple(records), query_status="complete")
        except Exception as exc:  # noqa: BLE001 - public errors must not reveal provider details
            LOGGER.error("Narrative Explorer CKL retrieval failed (%s)", type(exc).__name__)
            raise CanonicalLookupUnavailable("canonical lookup is unavailable") from exc

    @staticmethod
    def _lookup_domain(
        *,
        domain: str,
        provider: Callable[..., DomainLookup],
        arguments: Mapping[str, Any],
    ) -> DomainLookup:
        try:
            result = provider(**arguments)
            if not isinstance(result, DomainLookup) or result.domain != domain:
                raise TypeError("source provider returned an invalid lookup")
            return result
        except Exception as exc:  # noqa: BLE001 - source domains fail independently
            LOGGER.error(
                "Narrative Explorer %s retrieval failed (%s)",
                domain,
                type(exc).__name__,
            )
            return DomainLookup(
                domain=domain,  # type: ignore[arg-type]
                query_status="failed",
                reason_code=f"{domain}_lookup_failed",
            )

    def _lookup_maps(
        self,
        *,
        book: str,
        chapter: int,
        verse_start: int | None,
        verse_end: int | None,
        passage_text: str,
    ) -> DomainLookup:
        try:
            require_current_study_database(self.study_db_path)
        except Exception as exc:  # noqa: BLE001 - preserve an unavailable state, never initialize
            LOGGER.error("Narrative Explorer maps unavailable (%s)", type(exc).__name__)
            return DomainLookup(
                domain="maps",
                query_status="failed",
                reason_code="study_database_unavailable",
                missing_subdomains=("places", "routes"),
            )

        # The existing passage resolvers prefer text matches and only consult
        # stored reference links when no name matches. Use a full chapter
        # window for chapter requests, retain the resolver's anchors, and mark
        # a text-first result partial because anchor-only records may be absent.
        reference_start = verse_start or 1
        reference_end = verse_end if verse_end is not None else (verse_start or 9999)
        records: list[Any] = []
        missing: list[str] = []
        text_first = False
        try:
            places = resolve_places_for_passage(
                book=book,
                chapter=chapter,
                verse_start=reference_start,
                verse_end=reference_end,
                passage_text=passage_text,
                path=self.study_db_path,
                include_related_passages=False,
            )
            records.extend(places.get("markers") or [])
            text_first = text_first or _has_text_match(places.get("matched_terms"), passage_text)
        except Exception as exc:  # noqa: BLE001 - route and place lookup are independent
            LOGGER.error("Narrative Explorer map place lookup failed (%s)", type(exc).__name__)
            missing.append("places")
        try:
            routes = get_map_routes_for_passage(
                book=book,
                chapter=chapter,
                verse_start=reference_start,
                verse_end=reference_end,
                passage_text=passage_text,
                path=self.study_db_path,
            )
            records.extend(routes.get("routes") or [])
            text_first = text_first or _has_text_match(routes.get("matched_terms"), passage_text)
        except Exception as exc:  # noqa: BLE001 - route and place lookup are independent
            LOGGER.error("Narrative Explorer map route lookup failed (%s)", type(exc).__name__)
            missing.append("routes")

        if len(missing) == 2:
            return DomainLookup(
                domain="maps",
                query_status="failed",
                reason_code="map_resolvers_failed",
                missing_subdomains=tuple(missing),
            )
        if missing:
            return DomainLookup(
                domain="maps",
                records=records,
                query_status="partial",
                reason_code="map_subdomain_unavailable",
                missing_subdomains=tuple(missing),
            )
        if text_first:
            return DomainLookup(
                domain="maps",
                records=records,
                query_status="partial",
                reason_code="text_match_precedes_reference_lookup",
                missing_subdomains=("anchor_only_map_records",),
            )
        return DomainLookup(domain="maps", records=records, query_status="complete")

    def _lookup_archaeology(
        self,
        *,
        book: str,
        chapter: int,
        verse_start: int | None,
        verse_end: int | None,
        passage_text: str,
    ) -> DomainLookup:
        try:
            require_current_study_database(self.study_db_path)
            result = ArchaeologyService(self.study_db_path).for_passage(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
                passage_text=passage_text,
                limit=ARCHAEOLOGY_RESULT_LIMIT,
            )
            records = list(result.get("archaeological_items") or [])
        except Exception as exc:  # noqa: BLE001 - archaeology is independent of CKL/maps
            LOGGER.error("Narrative Explorer archaeology lookup failed (%s)", type(exc).__name__)
            return DomainLookup(
                domain="archaeology",
                query_status="failed",
                reason_code="archaeology_lookup_failed",
            )
        if len(records) >= ARCHAEOLOGY_RESULT_LIMIT:
            return DomainLookup(
                domain="archaeology",
                records=records,
                query_status="partial",
                reason_code="archaeology_result_limit_reached",
                missing_subdomains=("remaining_archaeology_items",),
            )
        return DomainLookup(domain="archaeology", records=records, query_status="complete")


def _full_inventory_limit(library: Any) -> int:
    inventory = getattr(library, "objects_by_id", None)
    if inventory is not None:
        try:
            return max(1, len(inventory))
        except (TypeError, AttributeError):
            pass
    manifest = getattr(library, "manifest", None)
    if isinstance(manifest, Mapping):
        try:
            return max(1, int(manifest.get("object_count", 0)))
        except (TypeError, ValueError):
            pass
    # The retrieval APIs require a limit argument. No finite corpus can reach
    # this value; providers with their own cap must return DomainLookup(partial).
    return sys.maxsize


def _has_text_match(matched_terms: Any, passage_text: str) -> bool:
    normalized_text = " ".join(str(passage_text or "").casefold().split())
    if not isinstance(matched_terms, Mapping):
        return False
    return any(
        " ".join(str(term or "").casefold().split()) in normalized_text
        for terms in matched_terms.values()
        for term in (terms if isinstance(terms, (list, tuple)) else [terms])
        if str(term or "").strip()
    )
