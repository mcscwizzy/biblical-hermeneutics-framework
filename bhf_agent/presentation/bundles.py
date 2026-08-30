"""Load versioned pre-generated presentation packets from local JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from .cache import presentation_cache_key_for_versions
from .models import EVIDENCE_BUNDLE_VERSION, PRESENTATION_SCHEMA_VERSION


PRESENTATION_BUNDLE_FORMAT = "bhf.presentation-bundle"
PRESENTATION_BUNDLE_VERSION = "1.0"
MAXIMUM_PRESENTATION_BUNDLE_BYTES = 16 * 1024 * 1024
MAXIMUM_PRESENTATION_BUNDLE_PACKETS = 5000
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_GENERATED_FROM_FIELDS = {
    "evidence_hash",
    "evidence_bundle_version",
    "presentation_schema_version",
    "prompt_version",
    "model",
}


class PresentationBundleError(ValueError):
    """Raised when a bundled packet file is not safe to activate."""


def load_presentation_bundle(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load an all-or-nothing bundle indexed by the engine cache fingerprint."""

    bundle_path = Path(path)
    encoded = bundle_path.read_bytes()
    if len(encoded) > MAXIMUM_PRESENTATION_BUNDLE_BYTES:
        raise PresentationBundleError("presentation bundle exceeds the size limit")
    try:
        value = json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PresentationBundleError(
            "presentation bundle is not valid UTF-8 JSON"
        ) from exc
    return index_presentation_bundle(value)


def build_presentation_bundle(
    packets: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build and structurally validate a deterministic bundle envelope."""

    value: dict[str, Any] = {
        "format": PRESENTATION_BUNDLE_FORMAT,
        "version": PRESENTATION_BUNDLE_VERSION,
        "packets": [dict(packet) for packet in packets],
    }
    index_presentation_bundle(value)
    return value


def index_presentation_bundle(value: Any) -> dict[str, dict[str, Any]]:
    """Validate an in-memory envelope and index packets by fingerprint."""

    if not isinstance(value, Mapping):
        raise PresentationBundleError("presentation bundle must be an object")
    if set(value) != {"format", "version", "packets"}:
        raise PresentationBundleError("presentation bundle fields are invalid")
    if value.get("format") != PRESENTATION_BUNDLE_FORMAT:
        raise PresentationBundleError("presentation bundle format is unsupported")
    if value.get("version") != PRESENTATION_BUNDLE_VERSION:
        raise PresentationBundleError("presentation bundle version is unsupported")

    packets = value.get("packets")
    if not isinstance(packets, list):
        raise PresentationBundleError("presentation bundle packets must be a list")
    if len(packets) > MAXIMUM_PRESENTATION_BUNDLE_PACKETS:
        raise PresentationBundleError("presentation bundle has too many packets")

    indexed: dict[str, dict[str, Any]] = {}
    for index, packet in enumerate(packets):
        cache_key = _packet_cache_key(packet, index)
        if cache_key in indexed:
            raise PresentationBundleError(
                f"presentation bundle packet {index} duplicates a fingerprint"
            )
        indexed[cache_key] = dict(packet)
    return indexed


def _packet_cache_key(packet: Any, index: int) -> str:
    label = f"presentation bundle packet {index}"
    if not isinstance(packet, Mapping):
        raise PresentationBundleError(f"{label} must be an object")
    passage_ref = _required_text(packet, "passage_ref", label)
    cards = packet.get("cards")
    if not isinstance(cards, list):
        raise PresentationBundleError(f"{label} cards must be a list")
    generated = packet.get("generated_from")
    if not isinstance(generated, Mapping):
        raise PresentationBundleError(f"{label} generated_from must be an object")
    if set(generated) != _GENERATED_FROM_FIELDS:
        raise PresentationBundleError(f"{label} generated_from fields are invalid")

    metadata = {
        field: _required_text(generated, field, f"{label} generated_from")
        for field in _GENERATED_FROM_FIELDS
    }
    if not _HASH_RE.fullmatch(metadata["evidence_hash"]):
        raise PresentationBundleError(f"{label} evidence hash is invalid")
    if metadata["evidence_bundle_version"] != EVIDENCE_BUNDLE_VERSION:
        raise PresentationBundleError(f"{label} evidence schema is unsupported")
    if metadata["presentation_schema_version"] != PRESENTATION_SCHEMA_VERSION:
        raise PresentationBundleError(f"{label} presentation schema is unsupported")

    return presentation_cache_key_for_versions(
        passage_ref=passage_ref,
        evidence_hash=metadata["evidence_hash"],
        evidence_bundle_version=metadata["evidence_bundle_version"],
        presentation_schema_version=metadata["presentation_schema_version"],
        prompt_version=metadata["prompt_version"],
    )


def _required_text(value: Mapping[str, Any], field: str, label: str) -> str:
    text = str(value.get(field) or "").strip()
    if not text:
        raise PresentationBundleError(f"{label} {field} is required")
    return text
