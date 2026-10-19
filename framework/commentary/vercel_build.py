"""Build and verify the Tyndale SQLite database for Vercel functions."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import socket
import ssl
import tempfile
from pathlib import Path
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .importer import import_tyndale_archive
from .service import CommentaryService

TYNDALE_PUBLIC_SOURCE_URL = "https://tyndaleopenresources.com/"
_ARCHIVE_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_DOWNLOAD_TIMEOUT_SECONDS = 120
_DOWNLOAD_CHUNK_BYTES = 1024 * 1024
_DOWNLOAD_USER_AGENT = "BHF Framework Tyndale Archive Builder/1.0"


def package_database_path() -> Path:
    """Return the generated database path included in the Vercel function."""

    repository_root = Path(__file__).resolve().parents[2]
    return repository_root / "framework" / "commentary" / "data" / "tyndale.sqlite"


def build_vercel_tyndale_database(
    *,
    environ: Mapping[str, str] | None = None,
    output_path: str | Path | None = None,
    urlopen_fn: Callable[..., object] | None = None,
) -> dict[str, object] | None:
    """Download, checksum, import, and validate Tyndale notes for Vercel."""

    values = os.environ if environ is None else environ
    if not values.get("VERCEL"):
        return None

    archive_url = str(values.get("BHF_TYNDALE_ARCHIVE_URL") or "").strip()
    expected_sha256 = str(values.get("BHF_TYNDALE_ARCHIVE_SHA256") or "").strip()
    if not archive_url:
        raise ValueError("BHF_TYNDALE_ARCHIVE_URL is required for a Vercel build.")
    if not _ARCHIVE_SHA256_RE.fullmatch(expected_sha256):
        raise ValueError(
            "BHF_TYNDALE_ARCHIVE_SHA256 is required and must be a 64-character SHA-256."
        )
    parsed_url = urlsplit(archive_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("BHF_TYNDALE_ARCHIVE_URL must be an HTTPS URL.")

    destination = Path(output_path) if output_path is not None else package_database_path()
    opener = urlopen_fn or urlopen
    with tempfile.TemporaryDirectory(prefix="bhf-tyndale-") as temp_dir:
        archive_path = Path(temp_dir) / "tyndale-open-study-notes.zip"
        try:
            request = Request(
                archive_url,
                headers={"User-Agent": _DOWNLOAD_USER_AGENT},
            )
            with opener(request, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
                with archive_path.open("wb") as archive_file:
                    while True:
                        chunk = response.read(_DOWNLOAD_CHUNK_BYTES)
                        if not chunk:
                            break
                        archive_file.write(chunk)
        except Exception as exc:
            raise RuntimeError(_download_failure_message(exc)) from None

        actual_sha256 = _sha256_file(archive_path)
        if not hmac.compare_digest(actual_sha256, expected_sha256.lower()):
            raise ValueError("Tyndale archive checksum verification failed.")

        try:
            import_report = import_tyndale_archive(
                archive_path,
                destination,
                source_url=TYNDALE_PUBLIC_SOURCE_URL,
                strict=True,
            )
            diagnostics = CommentaryService(destination).diagnostics()
        except Exception:
            raise RuntimeError("Tyndale database import or validation failed.") from None

    if not diagnostics.get("available") or not diagnostics.get("healthy"):
        raise RuntimeError("Tyndale database import or validation failed.")

    return {
        "available": True,
        "healthy": True,
        "entry_count": import_report["entry_count"],
        "anchor_count": import_report["anchor_count"],
        "archive_verified": True,
        "database_bytes": destination.stat().st_size,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_failure_message(exc: Exception) -> str:
    """Describe transport failures without including exception text or URLs."""

    if isinstance(exc, HTTPError):
        return (
            "Tyndale archive download failed "
            f"(category=HTTPError, http_status={exc.code})."
        )

    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, socket.gaierror):
        category = "DNS"
    elif isinstance(reason, ssl.SSLError):
        category = "TLS"
    elif isinstance(reason, (TimeoutError, socket.timeout)):
        category = "timeout"
    elif isinstance(reason, ConnectionError):
        category = "connection"
    else:
        category = type(reason).__name__

    details = [f"category={category}"]
    if isinstance(exc, URLError):
        details.append(f"exception_type={type(exc).__name__}")
        details.append(f"reason_type={type(reason).__name__}")
    errno = getattr(reason, "errno", None)
    if isinstance(errno, int):
        details.append(f"errno={errno}")
    return f"Tyndale archive download failed ({', '.join(details)})."
