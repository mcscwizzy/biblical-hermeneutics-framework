#!/usr/bin/env python3
"""Verify the immutable, packaged Commentary v1.2 release.

This verifier intentionally inspects only the release package and tracked
canonical chapter inventory.  It does not inspect candidate state, corpus
runner sessions, provider configuration, or generation tooling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RELEASE = "commentary-v1.2"
RELEASE_ROOT = ROOT / ".bhf-data/bhf-commentary-v1.2"
DESCRIPTOR = ROOT / "docs/commentary-v1.2-release.json"
MANIFEST_NAME = ".bhf-commentary-release.json"
CHECKSUMS_NAME = ".bhf-commentary-release-checksums.json"
EXPECTED_COUNTS = {
    "PUBLISHED": 972,
    "NOT_RENDERABLE_SOURCE_LIMITED": 185,
    "MODEL_OUTPUT_REJECTED": 26,
    "QUALITY_REVIEW_REQUIRED": 6,
}
TERMINAL_STATES = frozenset(EXPECTED_COUNTS)


class FrozenReleaseError(RuntimeError):
    """A frozen release invariant failed closed."""


def _fail(message: str) -> None:
    raise FrozenReleaseError(f"FROZEN_RELEASE_MUTATION_DETECTED: {message}")


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON: {path}")
        raise AssertionError from exc


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _fail(f"missing or unreadable file: {path}")
        raise AssertionError from exc


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _slug(book: str, chapter: int) -> str:
    return f"{book.lower().replace(' ', '_')}_{int(chapter):03d}"


def _reference(row: dict[str, Any]) -> str:
    return f"{row.get('book')} {int(row.get('chapter', -1))}"


def _canonical_inventory() -> list[dict[str, Any]]:
    from framework.commentary.production.census import canonical_chapters

    return [
        {
            "reference": row["reference"],
            "book": row["book"],
            "chapter": int(row["chapter"]),
            "canonical_ordinal": int(row["canonical_ordinal"]),
        }
        for row in canonical_chapters()
    ]


def _verify_descriptor(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    descriptor = _read(DESCRIPTOR)
    if not isinstance(descriptor, dict) or descriptor.get("release") != RELEASE:
        _fail("release descriptor has the wrong release identity")
    if descriptor.get("frozen") is not True:
        _fail("release descriptor is not frozen")
    identity = descriptor.get("descriptor_identity")
    unsigned = dict(descriptor)
    unsigned.pop("descriptor_identity", None)
    if not isinstance(identity, str) or _sha256_json(unsigned) != identity:
        _fail("release descriptor identity mismatch")
    if descriptor.get("manifest_sha256") != _sha256(manifest_path):
        _fail("release descriptor does not bind the release manifest")
    if descriptor.get("package_checksum_root_identity") != manifest.get("corpus_checksum_root_identity"):
        _fail("release descriptor package identity mismatch")
    if descriptor.get("source_lineage_identity") != manifest.get("source_validation_artifact_identity"):
        _fail("release descriptor source-lineage identity mismatch")
    if descriptor.get("schema_version") != manifest.get("reconciliation_version"):
        _fail("release descriptor schema identity mismatch")
    if descriptor.get("output_contract") != "commentary-v1.2-runtime-release-checksums-v2":
        _fail("release descriptor output contract mismatch")
    renderer = descriptor.get("renderer_contract")
    if renderer != {
        "artifact_version": "commentary-v1.2-corpus-result-v1",
        "effort": "high",
        "input_version": "commentary-v1.2-renderer-input-v1",
        "model": "gpt-5.6-terra",
        "prompt_version": "1.8",
    }:
        _fail("release descriptor renderer contract mismatch")
    return descriptor


def _verify_checksum_index(manifest: dict[str, Any]) -> tuple[dict[str, str], str]:
    checksum_path = RELEASE_ROOT / CHECKSUMS_NAME
    checksums = _read(checksum_path)
    files = checksums.get("files") if isinstance(checksums, dict) else None
    if checksums.get("artifact_version") != "commentary-v1.2-runtime-release-checksums-v2" or not isinstance(files, dict):
        _fail("checksum index is malformed")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            _fail("checksum index contains malformed entries")
        path = RELEASE_ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            _fail(f"checksum mismatch: {relative}")
    if files.get(MANIFEST_NAME) != _sha256(RELEASE_ROOT / MANIFEST_NAME):
        _fail("manifest checksum is not indexed")
    root_identity = _sha256_json(
        {name: digest for name, digest in files.items() if name not in {MANIFEST_NAME, CHECKSUMS_NAME}}
    )
    if root_identity != manifest.get("corpus_checksum_root_identity"):
        _fail("corpus checksum root identity mismatch")
    return files, root_identity


def verify_frozen_release() -> dict[str, Any]:
    """Verify package identity, inventory, states, artifacts, and contracts."""

    manifest_path = RELEASE_ROOT / MANIFEST_NAME
    manifest = _read(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("release") != RELEASE:
        _fail("release manifest has the wrong identity")
    unsigned = dict(manifest)
    identity = unsigned.pop("manifest_identity", None)
    if not isinstance(identity, str) or _sha256_json(unsigned) != identity:
        _fail("release manifest identity mismatch")
    if manifest.get("generation_performed") is not False:
        _fail("frozen release records generation")
    if manifest.get("promotion_mode") != "deterministic_finalized_artifact_reconciliation":
        _fail("unexpected promotion mode")

    canonical = _canonical_inventory()
    if len(canonical) != 1189 or manifest.get("canonical_chapter_count") != 1189:
        _fail("canonical chapter count is not 1189")
    canonical_by_ref = {row["reference"]: row for row in canonical}
    rows = manifest.get("chapter_publication_index")
    if not isinstance(rows, list) or len(rows) != 1189:
        _fail("manifest entry count is not 1189")
    if len({(_reference(row), row.get("canonical_ordinal")) for row in rows if isinstance(row, dict)}) != 1189:
        _fail("duplicate chapter identity")

    files, root_identity = _verify_checksum_index(manifest)
    descriptor = _verify_descriptor(manifest, manifest_path)
    seen: set[str] = set()
    state_counts: Counter[str] = Counter()
    published_names: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            _fail("manifest contains a non-object entry")
        reference = _reference(row)
        expected = canonical_by_ref.get(reference)
        if expected is None or reference in seen:
            _fail(f"invalid or duplicate canonical identity: {reference}")
        seen.add(reference)
        if any(row.get(key) != expected[key] for key in ("reference", "book", "chapter", "canonical_ordinal")):
            _fail(f"canonical identity disagreement: {reference}")
        state = row.get("release_state")
        if state not in TERMINAL_STATES or row.get("validated") is not True:
            _fail(f"unknown or non-terminal state: {reference}")
        state_counts[state] += 1
        lineage = row.get("source_lineage")
        if row.get("source") != "historical-75-release" and state != "MODEL_OUTPUT_REJECTED" and (
            not isinstance(lineage, dict)
            or not isinstance(lineage.get("evidence_hash"), str)
            or not isinstance(lineage.get("synthesis_hash"), str)
        ):
            _fail(f"missing source lineage: {reference}")
        filename = row.get("filename")
        if state == "PUBLISHED":
            expected_filename = _slug(row["book"], int(row["chapter"])) + ".json"
            if filename != expected_filename or filename in published_names:
                _fail(f"published filename mismatch: {reference}")
            published_names.add(filename)
            artifact = RELEASE_ROOT / filename
            if not artifact.is_file() or row.get("artifact_sha256") != _sha256(artifact):
                _fail(f"published artifact checksum mismatch: {reference}")
            payload = _read(artifact)
            if not isinstance(payload, dict) or any(payload.get(key) != row[key] for key in ("reference", "book", "chapter")):
                _fail(f"published artifact identity mismatch: {reference}")
            metadata = payload.get("generated_metadata")
            if not isinstance(metadata, dict) or metadata.get("commentary_schema_version") != "1.2" or metadata.get("commentary_prompt_version") != "1.8":
                _fail(f"published artifact contract mismatch: {reference}")
        elif filename is not None:
            _fail(f"non-published state exposes an artifact: {reference}")

    if seen != set(canonical_by_ref):
        _fail("canonical chapter is missing from the release")
    if dict(sorted(state_counts.items())) != dict(sorted(EXPECTED_COUNTS.items())):
        _fail(f"state counts changed: {dict(state_counts)}")
    actual_artifacts = {
        path.name for path in RELEASE_ROOT.glob("*.json")
        if path.name not in {MANIFEST_NAME, CHECKSUMS_NAME}
    }
    if actual_artifacts != published_names:
        _fail("orphan or missing published artifact")
    if manifest.get("published_chapter_count") != EXPECTED_COUNTS["PUBLISHED"] or manifest.get("unavailable_not_published_count") != 217:
        _fail("published/unavailable counts changed")
    if descriptor.get("chapter_inventory_hash") != _sha256_json(canonical):
        _fail("chapter inventory identity mismatch")
    return {
        "status": "COMMENTARY_V1_2_FROZEN_READY",
        "release": RELEASE,
        "canonical_chapters": len(canonical),
        "manifest_entries": len(rows),
        "state_counts": dict(sorted(state_counts.items())),
        "missing": 0,
        "orphan_artifacts": 0,
        "duplicate_identities": 0,
        "checksum_conflicts": 0,
        "manifest_sha256": _sha256(manifest_path),
        "chapter_inventory_hash": descriptor["chapter_inventory_hash"],
        "package_checksum_root_identity": root_identity,
        "release_descriptor": str(DESCRIPTOR.relative_to(ROOT)) if DESCRIPTOR.is_relative_to(ROOT) else str(DESCRIPTOR),
        "checksum_files": len(files),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify",))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_frozen_release(), ensure_ascii=False, sort_keys=True))
    except FrozenReleaseError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
