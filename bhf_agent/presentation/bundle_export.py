"""Safely export disposable cached packets as a deployment bundle."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .bundles import (
    MAXIMUM_PRESENTATION_BUNDLE_BYTES,
    build_presentation_bundle,
    index_presentation_bundle,
)
from .cache import SQLitePresentationCache


class PresentationBundleExportError(ValueError):
    """Raised when cached packets cannot be safely exported."""


@dataclass(frozen=True)
class PresentationBundleExportResult:
    output_path: Path
    packet_count: int
    byte_count: int


def export_cached_presentations(
    cache_path: str | Path,
    output_path: str | Path,
    *,
    force: bool = False,
) -> PresentationBundleExportResult:
    """Export a cache snapshot atomically without contacting a provider."""

    source = Path(cache_path)
    destination = Path(output_path)
    if not source.is_file():
        raise PresentationBundleExportError(
            f"presentation cache does not exist: {source}"
        )
    try:
        same_file = source.resolve() == destination.resolve() or (
            destination.exists() and os.path.samefile(source, destination)
        )
    except OSError as exc:
        raise PresentationBundleExportError(str(exc)) from exc
    if same_file:
        raise PresentationBundleExportError(
            "bundle output must not replace the source presentation cache"
        )
    if destination.exists() and not force:
        raise PresentationBundleExportError(
            f"{destination} already exists; pass --force to overwrite"
        )

    try:
        entries = SQLitePresentationCache(source).entries_for_export()
        if not entries:
            raise PresentationBundleExportError(
                "presentation cache contains no packets to export"
            )
        for stored_key, packet in entries:
            packet_index = index_presentation_bundle(
                build_presentation_bundle([packet])
            )
            derived_key = next(iter(packet_index))
            if stored_key != derived_key:
                raise PresentationBundleExportError(
                    "presentation cache fingerprint does not match packet metadata"
                )
        bundle = build_presentation_bundle(packet for _, packet in entries)
        indexed = index_presentation_bundle(bundle)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise PresentationBundleExportError(str(exc)) from exc

    if len(indexed) != len(entries):
        raise PresentationBundleExportError("presentation cache has duplicate packets")

    encoded = (
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(encoded) > MAXIMUM_PRESENTATION_BUNDLE_BYTES:
        raise PresentationBundleExportError(
            "exported presentation bundle exceeds the size limit"
        )

    _write_bytes_atomic(destination, encoded, force=force)
    return PresentationBundleExportResult(
        output_path=destination,
        packet_count=len(entries),
        byte_count=len(encoded),
    )


def _write_bytes_atomic(path: Path, data: bytes, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise PresentationBundleExportError(
            f"{path} already exists; pass --force to overwrite"
        )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            delete=False,
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        if path.exists() and not force:
            raise PresentationBundleExportError(
                f"{path} already exists; pass --force to overwrite"
            )
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
