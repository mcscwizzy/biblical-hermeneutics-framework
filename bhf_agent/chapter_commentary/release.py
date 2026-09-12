"""Safe read helpers for packaged commentary release manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RELEASE_MANIFEST_FILENAME = ".bhf-commentary-release.json"
RELEASE_CHECKSUMS_FILENAME = ".bhf-commentary-release-checksums.json"


def load_release_manifest(storage_dir: str | Path) -> dict[str, Any] | None:
    """Load a release manifest, returning ``None`` for legacy stores."""

    path = Path(storage_dir) / RELEASE_MANIFEST_FILENAME
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"_manifest_invalid": True}
    return value if isinstance(value, dict) else {"_manifest_invalid": True}


def release_manifest_invalid(storage_dir: str | Path) -> bool:
    """Return whether a present release manifest is malformed."""

    manifest = load_release_manifest(storage_dir)
    return bool(manifest and manifest.get("_manifest_invalid"))


def _chapter_index(manifest: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    rows = manifest.get("chapter_publication_index")
    if not isinstance(rows, list):
        return {}
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        book = str(row.get("book") or "").strip().casefold()
        chapter = row.get("chapter")
        if book and isinstance(chapter, int) and chapter > 0:
            result[(book, chapter)] = row
    return result


def release_chapter_state(
    storage_dir: str | Path,
    book: str,
    chapter: int,
) -> dict[str, Any] | None:
    """Return the safe publication state for one chapter, if manifest-backed."""

    manifest = load_release_manifest(storage_dir)
    if manifest is None:
        return None
    if manifest.get("_manifest_invalid"):
        return {
            "book": book,
            "chapter": chapter,
            "release_state": "RELEASE_MANIFEST_INVALID",
            "reason": "commentary_release_unavailable",
        }
    row = _chapter_index(manifest).get((str(book).strip().casefold(), chapter))
    if row is not None:
        return dict(row)
    return {
        "book": book,
        "chapter": chapter,
        "release_state": "OUTSIDE_VALIDATED_V1_2_POPULATION",
        "reason": "commentary_not_yet_validated_in_release",
    }


def _checksum_status(storage_dir: str | Path, manifest: dict[str, Any]) -> str:
    """Check the package checksum index without exposing implementation detail."""

    root = Path(storage_dir)
    try:
        checksums = json.loads(
            (root / RELEASE_CHECKSUMS_FILENAME).read_text(encoding="utf-8")
        )
        files = checksums.get("files")
        if not isinstance(files, dict):
            return "unavailable"
        for relative, expected in files.items():
            if not isinstance(relative, str) or not isinstance(expected, str):
                return "invalid"
            path = root / relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return "mismatch"
        manifest_digest = files.get(RELEASE_MANIFEST_FILENAME)
        if manifest_digest != hashlib.sha256(
            (root / RELEASE_MANIFEST_FILENAME).read_bytes()
        ).hexdigest():
            return "mismatch"
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        return "unavailable"
    return "valid"


def release_diagnostics(storage_dir: str | Path, selected_release: str) -> dict[str, Any]:
    """Build a safe operational summary for the commentary diagnostics route."""

    root = Path(storage_dir)
    manifest = load_release_manifest(root)
    if manifest is None:
        files = list(root.glob("*.json")) if root.is_dir() else []
        return {
            "release": selected_release,
            "available": bool(files),
            "corpus_available": root.is_dir(),
            "manifest_available": False,
            "total_files": len(files),
            "status": "ok" if files else "no_commentaries",
        }

    if manifest.get("_manifest_invalid"):
        return {
            "release": selected_release,
            "available": False,
            "corpus_available": root.is_dir(),
            "manifest_available": True,
            "checksum_status": "invalid",
            "published_commentary_count": 0,
            "validated_population_count": 0,
            "unpublished_validated_count": 0,
            "release_scope": "unavailable",
            "status": "invalid_manifest",
        }

    published = manifest.get("published_chapter_count")
    validated = manifest.get("validated_population_count")
    unpublished = manifest.get("unavailable_not_published_count")
    return {
        "release": selected_release,
        "available": bool(root.is_dir() and isinstance(published, int) and published > 0),
        "corpus_available": root.is_dir(),
        "manifest_available": True,
        "manifest_release": manifest.get("release"),
        "manifest_identity": manifest.get("manifest_identity"),
        "checksum_status": _checksum_status(root, manifest),
        "published_commentary_count": published if isinstance(published, int) else 0,
        "validated_population_count": validated if isinstance(validated, int) else 0,
        "unpublished_validated_count": unpublished if isinstance(unpublished, int) else 0,
        "release_scope": manifest.get("release_scope", "validated_population_only"),
        "status": "ok" if published else "no_commentaries",
    }


__all__ = [
    "RELEASE_CHECKSUMS_FILENAME",
    "RELEASE_MANIFEST_FILENAME",
    "load_release_manifest",
    "release_manifest_invalid",
    "release_chapter_state",
    "release_diagnostics",
]
