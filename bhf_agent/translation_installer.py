"""Backend translation download, import, validation, and storage workflow."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .translation_storage import (
    DATA_PATH,
    LEGACY_KJV_DATA_PATH,
    TranslationStorageError,
    count_bible_statistics,
    installed_translation_metadata_path,
    installed_translation_path,
    load_asv_bible,
    load_bible_dataset,
    load_legacy_kjv_bible,
    normalize_translation_id,
    parse_bible_xml,
    translations_root,
    write_json_atomic,
)
from .translation_registry import (
    mark_translation_removed,
    upsert_translation,
)


ALLOWLISTED_DOWNLOAD_HOSTS = {"raw.githubusercontent.com"}
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 30
SERVER_TRANSLATION_IDS = frozenset({"asv", "kjv"})


class TranslationInstallError(ValueError):
    """Raised when a translation cannot be downloaded, validated, or installed."""


def get_translation_installation(translation_id: str) -> dict[str, Any]:
    normalized = normalize_translation_id(translation_id)
    if normalized == "asv":
        data = load_asv_bible()
        stats = count_bible_statistics(data)
        translation = dict(data.get("translation", {}))
        translation.setdefault("id", normalized.upper())
        translation.setdefault(
            "name",
            "American Standard Version" if normalized == "asv" else "King James Version",
        )
        return {
            "translation_id": normalized,
            "installed": True,
            "bundled": True,
            "availability": "bundled",
            "offline_supported": True,
            "metadata_path": None,
            "storage_path": str(
                DATA_PATH
            ),
            "translation": translation,
            **stats,
            "private_local_install": False,
            "third_party": False,
        }

    storage_path = installed_translation_path(normalized)
    metadata_path = installed_translation_metadata_path(normalized)
    if not storage_path.exists():
        return {
            "translation_id": normalized,
            "installed": False,
            "bundled": False,
            "availability": "unavailable",
            "offline_supported": False,
            "metadata_path": str(metadata_path),
            "storage_path": str(storage_path),
            "third_party": False,
        }

    data = load_bible_dataset(storage_path)
    stats = count_bible_statistics(data)
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}

    translation = dict(data.get("translation", {}))
    translation.setdefault("id", normalized.upper())
    translation.setdefault("name", metadata.get("name") or translation.get("id") or normalized.upper())
    return {
        "translation_id": normalized,
        "installed": True,
        "bundled": False,
        "availability": "installed",
        "offline_supported": True,
        "metadata_path": str(metadata_path),
        "storage_path": str(storage_path),
        "translation": translation,
        "metadata": metadata,
        **stats,
        "private_local_install": bool(metadata.get("private_local_install", False)),
        "third_party": bool(metadata.get("third_party", False)),
    }


def list_installed_translations() -> list[dict[str, Any]]:
    from .translation_registry import list_installed_registry_translations

    entries = []
    for row in list_installed_registry_translations():
        try:
            installation = get_translation_installation(str(row["id"]))
        except TranslationStorageError:
            continue
        # The registry is intentionally durable, but the dataset is the source
        # of truth for whether a translation can actually be read.  A removed
        # app/data volume can leave an old registry row behind; do not expose
        # that row as an installed translation.
        if not installation.get("installed"):
            continue
        # Copyrighted/manual imports remain local-only and are intentionally
        # excluded from the server translation catalog. KJV is the sole
        # downloadable server-managed exception alongside bundled ASV.
        if not installation.get("bundled") and str(row["id"]).lower() not in SERVER_TRANSLATION_IDS:
            continue
        installation["registry"] = row
        entries.append(installation)
    return entries


def remove_translation(translation_id: str) -> bool:
    normalized = normalize_translation_id(translation_id)
    if normalized in {"asv", "kjv"}:
        raise TranslationInstallError(f"{normalized.upper()} cannot be removed")
    removed = False
    for path in (installed_translation_path(normalized), installed_translation_metadata_path(normalized)):
        if path.exists():
            path.unlink()
            removed = True
    if removed:
        mark_translation_removed(normalized)
        from .bible import clear_bible_search_cache

        clear_bible_search_cache()
    return removed


def download_translation(
    translation_id: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> dict[str, Any]:
    normalized = normalize_translation_id(translation_id)
    entry = _catalog_entry(normalized)
    source = entry.get("source") or {}
    if entry.get("install_mode") != "direct_download":
        raise TranslationInstallError(f"{normalized} is not approved for direct download")
    raw_url = str(source.get("raw_url") or "").strip()
    if not raw_url:
        raise TranslationInstallError(f"{normalized} does not have a curated download URL")
    return _download_and_install(
        normalized,
        raw_url,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
        catalog_entry=entry,
    )


def install_xml_translation(
    translation_id: str,
    xml_content: bytes,
    *,
    source_type: str,
    source_url: str,
    source_repository: str | None = None,
    source_filename: str = "",
    source_sha256: str | None = None,
    catalog_entry: dict[str, Any] | None = None,
    translation_name: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_translation_id(translation_id)
    entry = catalog_entry or _catalog_entry(normalized)
    dataset = parse_bible_xml(
        xml_content,
        translation_id=normalized,
        translation_name=translation_name or entry.get("name"),
        source_filename=source_filename,
    )
    validation = validate_translation_dataset(normalized, dataset, catalog_entry=entry)

    normalized_json = json.dumps(dataset, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    normalized_sha256 = hashlib.sha256(normalized_json).hexdigest()
    source_sha256 = source_sha256 or hashlib.sha256(xml_content).hexdigest()

    storage_path = installed_translation_path(normalized)
    metadata_path = installed_translation_metadata_path(normalized)
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    _write_atomic_bytes(storage_path, normalized_json)
    metadata = {
        "translation_id": normalized,
        "name": validation["translation"]["name"],
        "source_type": source_type,
        "source_url": source_url,
        "source_repository": source_repository,
        "installed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_sha256": source_sha256,
        "normalized_sha256": normalized_sha256,
        "book_count": validation["book_count"],
        "chapter_count": validation["chapter_count"],
        "verse_count": validation["verse_count"],
        "license_status": entry.get("license_status"),
        "third_party": bool(entry.get("third_party", False)),
        "private_local_install": source_type == "manual_xml_import",
    }
    write_json_atomic(metadata_path, metadata)
    upsert_translation(
        normalized,
        name=validation["translation"]["name"],
        source=source_url or source_type,
        installed=True,
    )
    from .bible import clear_bible_search_cache

    clear_bible_search_cache()
    return {
        "translation_id": normalized,
        "installed": True,
        "availability": "installed",
        "offline_supported": True,
        "book_count": validation["book_count"],
        "chapter_count": validation["chapter_count"],
        "verse_count": validation["verse_count"],
        "storage_path": str(storage_path),
        "metadata_path": str(metadata_path),
        "metadata": metadata,
        "translation": validation["translation"],
        "third_party": bool(entry.get("third_party", False)),
    }


def validate_translation_dataset(
    translation_id: str,
    data: dict[str, Any],
    *,
    catalog_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_translation_id(translation_id)
    entry = catalog_entry or _catalog_entry(normalized)
    translation = dict(data.get("translation", {}) or {})
    books = list(data.get("books", []) or [])
    if not translation:
        raise TranslationInstallError("translation metadata is missing")
    actual_name = str(translation.get("name") or "").strip()
    actual_id = str(translation.get("id") or normalized).strip().lower()
    expected_name = str(entry.get("name") or "").strip()
    expected_language = str(entry.get("language_code") or entry.get("language") or "").strip().lower()
    expected_book_count = int(entry.get("validation", {}).get("expected_book_count") or 0)
    expected_minimum_verse_count = int(entry.get("validation", {}).get("expected_minimum_verse_count") or 0)
    expected_maximum_verse_count = int(entry.get("validation", {}).get("expected_maximum_verse_count") or 0)

    if actual_id != normalized:
        raise TranslationInstallError("translation id does not match the curated catalog entry")
    if not actual_name:
        raise TranslationInstallError("translation name is required")
    if expected_name and expected_name.lower() not in actual_name.lower():
        raise TranslationInstallError("source metadata does not identify the expected translation")
    if expected_language and str(translation.get("language") or "").strip().lower() != expected_language:
        raise TranslationInstallError("source metadata does not identify the expected language")
    if not books:
        raise TranslationInstallError("translation does not contain any books")

    book_names: list[str] = []
    seen_verses: set[tuple[str, int, int]] = set()
    chapter_count = 0
    verse_count = 0
    for book in books:
        book_name = str(book.get("name") or "").strip()
        if not book_name:
            raise TranslationInstallError("translation contains a book without a name")
        book_names.append(book_name)
        chapters = list(book.get("chapters", []) or [])
        if not chapters:
            raise TranslationInstallError(f"{book_name} contains no chapters")
        for chapter in chapters:
            chapter_number = int(chapter.get("chapter") or 0)
            if chapter_number <= 0:
                raise TranslationInstallError("chapter numbers must be positive")
            verses = list(chapter.get("verses", []) or [])
            if not verses:
                raise TranslationInstallError(f"{book_name} {chapter_number} contains no verses")
            chapter_count += 1
            for verse in verses:
                verse_number = int(verse.get("verse") or 0)
                text = str(verse.get("text") or "").strip()
                if verse_number <= 0:
                    raise TranslationInstallError("verse numbers must be positive")
                if not text:
                    raise TranslationInstallError("verse text must not be empty")
                key = (book_name, chapter_number, verse_number)
                if key in seen_verses:
                    raise TranslationInstallError("translation contains duplicate verse tuples")
                seen_verses.add(key)
                verse_count += 1

    if expected_book_count and len(books) != expected_book_count:
        raise TranslationInstallError("source does not contain the complete expected canon")
    if expected_minimum_verse_count and verse_count < expected_minimum_verse_count:
        raise TranslationInstallError("source verse count is below the approved review range")
    if expected_maximum_verse_count and verse_count > expected_maximum_verse_count:
        raise TranslationInstallError("source verse count is above the approved review range")
    if expected_book_count == 66:
        if book_names[0] != "Genesis" or book_names[-1] != "Revelation":
            raise TranslationInstallError("66-book catalog entries must include Genesis and Revelation")

    return {
        "translation": translation,
        "books": books,
        "book_count": len(books),
        "chapter_count": chapter_count,
        "verse_count": verse_count,
    }


def _download_and_install(
    translation_id: str,
    raw_url: str,
    *,
    timeout_seconds: int,
    max_bytes: int,
    catalog_entry: dict[str, Any],
) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme != "https":
        raise TranslationInstallError("download URL must use https")
    if parsed.hostname not in ALLOWLISTED_DOWNLOAD_HOSTS:
        raise TranslationInstallError("download host is not allowlisted")

    request = urllib.request.Request(raw_url, headers={"Accept": "application/xml,text/xml,*/*"})
    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            final = urllib.parse.urlparse(final_url)
            if final.scheme != "https" or final.hostname not in ALLOWLISTED_DOWNLOAD_HOSTS:
                raise TranslationInstallError("redirect target is not allowlisted")
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "html" in content_type:
                raise TranslationInstallError("download returned HTML instead of XML")
            payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise TranslationInstallError("download exceeded the maximum allowed size")
    except urllib.error.HTTPError as exc:
        raise TranslationInstallError(f"download failed with HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise TranslationInstallError(f"download failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise TranslationInstallError(f"download timed out: {exc}") from exc

    if not payload.lstrip().startswith(b"<"):
        raise TranslationInstallError("download did not appear to be XML")
    xml_sha256 = hashlib.sha256(payload).hexdigest()
    result = install_xml_translation(
        translation_id,
        payload,
        source_type="beblia_xml",
        source_url=raw_url,
        source_repository=str(catalog_entry.get("source", {}).get("repository_url") or ""),
        source_filename=str(catalog_entry.get("source", {}).get("filename") or ""),
        source_sha256=xml_sha256,
        catalog_entry=catalog_entry,
        translation_name=str(catalog_entry.get("name") or ""),
    )
    result["download_duration_ms"] = int(round((time.perf_counter() - started_at) * 1000))
    return result


def _catalog_entry(translation_id: str) -> dict[str, Any]:
    from .translation_catalog import catalog_entry_for_id

    entry = catalog_entry_for_id(translation_id)
    if entry is None:
        raise TranslationInstallError(f"unknown translation: {translation_id}")
    return entry


def _write_atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    temp_path = Path(temp_name)
    try:
        temp_path.replace(path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
