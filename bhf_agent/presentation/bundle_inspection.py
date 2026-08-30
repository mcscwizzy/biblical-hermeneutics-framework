"""Content-free inspection for deployable presentation bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bundles import (
    PRESENTATION_BUNDLE_FORMAT,
    PRESENTATION_BUNDLE_VERSION,
    PresentationBundleError,
    load_presentation_bundle,
)
from .models import EVIDENCE_BUNDLE_VERSION, PRESENTATION_SCHEMA_VERSION


@dataclass(frozen=True)
class PresentationBundleInspection:
    """A content-free summary of a structurally valid bundle."""

    path: Path
    byte_count: int
    packet_count: int
    prompt_versions: tuple[str, ...]
    models: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": True,
            "path": str(self.path),
            "byte_count": self.byte_count,
            "packet_count": self.packet_count,
            "format": PRESENTATION_BUNDLE_FORMAT,
            "bundle_version": PRESENTATION_BUNDLE_VERSION,
            "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
            "presentation_schema_version": PRESENTATION_SCHEMA_VERSION,
            "prompt_versions": list(self.prompt_versions),
            "models": list(self.models),
        }


def inspect_presentation_bundle(
    path: str | Path,
    *,
    expected_prompt_version: str | None = None,
    expected_model: str | None = None,
    require_packets: bool = False,
) -> PresentationBundleInspection:
    """Validate a bundle envelope and optionally enforce deployment metadata."""

    bundle_path = Path(path)
    indexed = load_presentation_bundle(bundle_path)
    if require_packets and not indexed:
        raise PresentationBundleError("presentation bundle contains no packets")

    prompt_versions = tuple(
        sorted(
            {
                str(packet["generated_from"]["prompt_version"])
                for packet in indexed.values()
            }
        )
    )
    models = tuple(
        sorted(
            {
                str(packet["generated_from"]["model"])
                for packet in indexed.values()
            }
        )
    )
    if expected_prompt_version is not None and prompt_versions != (
        expected_prompt_version,
    ):
        raise PresentationBundleError(
            "presentation bundle prompt version does not match the expected value"
        )
    if expected_model is not None and models != (expected_model,):
        raise PresentationBundleError(
            "presentation bundle model does not match the expected value"
        )

    return PresentationBundleInspection(
        path=bundle_path,
        byte_count=bundle_path.stat().st_size,
        packet_count=len(indexed),
        prompt_versions=prompt_versions,
        models=models,
    )
