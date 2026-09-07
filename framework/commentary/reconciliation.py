"""Canonical Commentary release reconciliation and overlay assembly.

The v1.1 scaled pipeline is an upgrade population.  This module keeps that
population separate from the canonical runtime corpus and composes a release
from immutable source populations keyed by canonical chapter reference.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from bhf_agent.bible import list_books
from bhf_agent.chapter_commentary.models import CommentaryStatus
from bhf_agent.chapter_commentary.storage import get_commentary_filename, load_commentary


CANONICAL_RUNTIME_STATUS = "RUNTIME_CANONICAL_COMPLETE"
UPGRADE_POPULATION_STATUS = "UPGRADE_CORPUS_COMPLETE"
BASELINE_RELEASE = "commentary-v1.0.1"
BASELINE_RELATIVE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.0.1")
SCALE_RELATIVE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale")
ELIGIBLE_RELATIVE_ROOT = Path(".bhf-data/bhf-commentary-candidates/commentary-v1.1")
_CHAPTER_FILENAME = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*_\d{3}\.json$")


class ReconciliationError(RuntimeError):
    """Raised when a release source cannot be reconciled safely."""


@dataclass(frozen=True)
class SourceCandidate:
    """One valid immutable source artifact for one chapter reference."""

    reference: str
    book: str
    chapter: int
    path: Path
    provenance: str
    source_release: str
    source_certified_batch: str | None = None

    @property
    def sha256(self) -> str:
        digest = hashlib.sha256()
        with self.path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


@dataclass(frozen=True)
class ReconciliationResult:
    """Deterministic classification of every canonical chapter."""

    canonical_references: tuple[str, ...]
    v1_1_certified: tuple[str, ...]
    baseline_fallback: tuple[str, ...]
    missing: tuple[str, ...]
    conflicts: tuple[str, ...]
    invalid_source_records: tuple[dict[str, Any], ...]
    selected_sources: Mapping[str, SourceCandidate]

    @property
    def canonical_total(self) -> int:
        return len(self.canonical_references)

    @property
    def final_publishable_count(self) -> int:
        return len(self.selected_sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_total": self.canonical_total,
            "v1_1_certified_count": len(self.v1_1_certified),
            "baseline_fallback_count": len(self.baseline_fallback),
            "missing_count": len(self.missing),
            "conflict_count": len(self.conflicts),
            "invalid_source_count": len(self.invalid_source_records),
            "final_publishable_count": self.final_publishable_count,
            "v1_1_certified": list(self.v1_1_certified),
            "baseline_fallback": list(self.baseline_fallback),
            "missing": list(self.missing),
            "conflicts": list(self.conflicts),
            "invalid_source_records": list(self.invalid_source_records),
        }


def canonical_chapter_references() -> tuple[str, ...]:
    """Return the authoritative 66-book Protestant chapter inventory."""

    references: list[str] = []
    for book in list_books():
        name = str(book.get("name") or "").strip()
        chapter_total = int(book.get("chapters") or 0)
        if not name or chapter_total < 1:
            raise ReconciliationError(f"invalid canonical inventory book: {book!r}")
        references.extend(f"{name} {chapter}" for chapter in range(1, chapter_total + 1))
    if len(references) != len(set(references)):
        raise ReconciliationError("canonical inventory contains duplicate chapter references")
    return tuple(references)


def canonical_inventory_fingerprint(references: Sequence[str] | None = None) -> str:
    values = list(references or canonical_chapter_references())
    return hashlib.sha256(
        json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _canonical_sort_key(reference: str, order: Mapping[str, int]) -> tuple[int, int, str]:
    book, _, chapter = reference.rpartition(" ")
    try:
        chapter_number = int(chapter)
    except ValueError:
        chapter_number = 0
    return order.get(book, len(order)), chapter_number, reference


def _chapter_paths(directory: Path) -> list[Path]:
    return sorted(
        (path for path in directory.glob("*.json") if _CHAPTER_FILENAME.fullmatch(path.name)),
        key=lambda path: path.name,
    )


def _invalid(path: Path, population: str, reason: str, reference: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"population": population, "source": path.as_posix(), "reason": reason}
    if reference:
        value["reference"] = reference
    return value


def _candidate_from_path(
    path: Path,
    *,
    population: str,
    provenance: str,
    source_release: str,
    canonical: set[str],
    source_certified_batch: str | None = None,
) -> tuple[SourceCandidate | None, dict[str, Any] | None]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, _invalid(path, population, f"invalid JSON: {exc}")
    if not isinstance(record, dict):
        return None, _invalid(path, population, "chapter artifact is not a JSON object")
    book = str(record.get("book") or "").strip()
    chapter = record.get("chapter")
    reference = str(record.get("reference") or "").strip()
    if not book or not isinstance(chapter, int) or chapter < 1:
        return None, _invalid(path, population, "missing valid book/chapter identity", reference or None)
    expected_reference = f"{book} {chapter}"
    if reference != expected_reference:
        return None, _invalid(path, population, "reference does not match book/chapter", reference or expected_reference)
    if reference not in canonical:
        return None, _invalid(path, population, "noncanonical chapter reference", reference)
    if path.name != get_commentary_filename(book, chapter):
        return None, _invalid(path, population, "filename does not match canonical identity", reference)
    if record.get("status") != CommentaryStatus.VALIDATED.value:
        return None, _invalid(path, population, f"source status is {record.get('status')!r}", reference)
    if record.get("failure_reason") or record.get("validation_errors"):
        return None, _invalid(path, population, "source contains failure or validation errors", reference)
    availability = record.get("evidence_availability")
    if availability not in {"AVAILABLE", "THIN", "DATA_GAP"}:
        return None, _invalid(path, population, "source has invalid evidence availability", reference)
    metadata = record.get("generated_metadata")
    if not isinstance(metadata, dict) or not str(metadata.get("evidence_hash") or ""):
        return None, _invalid(path, population, "source has no evidence hash", reference)
    try:
        loaded = load_commentary(path.parent, book, chapter)
    except (OSError, KeyError, TypeError, ValueError):
        loaded = None
    if loaded is None or loaded.reference != reference or loaded.status != CommentaryStatus.VALIDATED.value:
        return None, _invalid(path, population, "source failed commentary schema deserialization", reference)
    return SourceCandidate(
        reference=reference,
        book=book,
        chapter=chapter,
        path=path,
        provenance=provenance,
        source_release=source_release,
        source_certified_batch=source_certified_batch,
    ), None


def load_validated_baseline(
    repo_root: str | Path,
    canonical_references: Sequence[str] | None = None,
    *,
    require_manifest: bool = True,
) -> tuple[list[SourceCandidate], list[dict[str, Any]]]:
    """Load only valid v1.0.1 baseline chapter artifacts."""

    root = Path(repo_root).resolve()
    directory = root / BASELINE_RELATIVE_ROOT
    canonical_values = tuple(canonical_references or canonical_chapter_references())
    canonical = set(canonical_values)
    invalid: list[dict[str, Any]] = []
    if not directory.is_dir():
        return [], [_invalid(directory, "baseline", "baseline directory is missing")]
    if require_manifest:
        manifest_path = directory / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid.append(_invalid(manifest_path, "baseline", f"invalid baseline manifest: {exc}"))
        else:
            summary = manifest.get("validation_summary") if isinstance(manifest, dict) else None
            if not isinstance(manifest, dict) or manifest.get("release") != BASELINE_RELEASE:
                invalid.append(_invalid(manifest_path, "baseline", "baseline manifest release is not v1.0.1"))
            elif manifest.get("chapters_total") != len(canonical_values):
                invalid.append(_invalid(manifest_path, "baseline", "baseline manifest chapter total disagrees with canonical inventory"))
            elif not isinstance(summary, dict) or summary.get("validated") != len(canonical_values) or any(summary.get(key, 0) for key in ("partial", "needs_review", "failed")):
                invalid.append(_invalid(manifest_path, "baseline", "baseline manifest validation summary is incomplete"))
    candidates: list[SourceCandidate] = []
    for path in _chapter_paths(directory):
        candidate, problem = _candidate_from_path(
            path,
            population="baseline",
            provenance="validated baseline fallback",
            source_release=BASELINE_RELEASE,
            canonical=canonical,
        )
        if problem:
            invalid.append(problem)
        elif candidate:
            candidates.append(candidate)
    return candidates, invalid


def _source_batch(path: Path) -> str | None:
    for part in path.parts:
        if part.startswith("batch-") and part[6:].isdigit():
            return part
    if "commentary-v1.1-terra" in path.parts:
        return "canary"
    return None


def load_certified_v1_1(
    repo_root: str | Path,
    canonical_references: Sequence[str] | None = None,
) -> tuple[list[SourceCandidate], list[dict[str, Any]], set[str]]:
    """Load the protected eligible v1.1 upgrade population only."""

    root = Path(repo_root).resolve()
    canonical_values = tuple(canonical_references or canonical_chapter_references())
    canonical = set(canonical_values)
    state_path = root / SCALE_RELATIVE_ROOT / "pipeline-state.json"
    eligible_path = root / ELIGIBLE_RELATIVE_ROOT / "low-information-commentary.json"
    invalid: list[dict[str, Any]] = []
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        low_information = json.loads(eligible_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [_invalid(state_path, "v1.1", f"v1.1 certification inputs are invalid: {exc}")], set()
    eligible = {
        str(value).strip()
        for value in low_information.get("chapters_evidence_supports_regeneration", [])
        if str(value).strip()
    }
    if state.get("status") != "CORPUS_COMPLETE" or state.get("current_stage") != "CORPUS_COMPLETE":
        invalid.append(_invalid(state_path, "v1.1", "upgrade population is not complete"))
    if len(eligible) != int(state.get("eligible_corpus_total", 0)):
        invalid.append(_invalid(eligible_path, "v1.1", "eligible population disagrees with pipeline state"))
    if not eligible.issubset(canonical):
        invalid.append(_invalid(eligible_path, "v1.1", "eligible population contains noncanonical references"))
    protected = state.get("protected_fingerprints")
    if not isinstance(protected, dict):
        return [], invalid + [_invalid(state_path, "v1.1", "protected fingerprint map is missing")], eligible
    candidates: list[SourceCandidate] = []
    seen: dict[str, Path] = {}
    for relative, expected_hash in sorted(protected.items()):
        path = root / str(relative)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            invalid.append(_invalid(path, "v1.1", f"protected source is missing: {exc}"))
            continue
        if digest != str(expected_hash):
            invalid.append(_invalid(path, "v1.1", "protected fingerprint changed"))
            continue
        candidate, problem = _candidate_from_path(
            path,
            population="v1.1",
            provenance="certified Commentary v1.1",
            source_release="commentary-v1.1",
            canonical=canonical,
            source_certified_batch=_source_batch(path),
        )
        if problem:
            invalid.append(problem)
            continue
        assert candidate is not None
        if candidate.reference not in eligible:
            continue
        if candidate.reference in seen:
            invalid.append(_invalid(path, "v1.1", f"duplicate certified chapter; first source is {seen[candidate.reference]}", candidate.reference))
        else:
            seen[candidate.reference] = path
            candidates.append(candidate)
    return candidates, invalid, eligible


def reconcile_candidates(
    canonical_references: Sequence[str],
    v1_1_candidates: Iterable[SourceCandidate],
    baseline_candidates: Iterable[SourceCandidate],
    invalid_source_records: Iterable[dict[str, Any]] = (),
) -> ReconciliationResult:
    """Apply v1.1-over-baseline precedence for the exact canonical set."""

    canonical = tuple(canonical_references)
    if len(canonical) != len(set(canonical)):
        raise ReconciliationError("canonical inventory contains duplicate references")
    order = {reference: index for index, reference in enumerate(canonical)}
    v11_by_ref: dict[str, list[SourceCandidate]] = {}
    baseline_by_ref: dict[str, list[SourceCandidate]] = {}
    invalid = list(invalid_source_records)
    canonical_set = set(canonical)
    for population, target in (("v1.1", v11_by_ref), ("baseline", baseline_by_ref)):
        for candidate in (v1_1_candidates if population == "v1.1" else baseline_candidates):
            if candidate.reference not in canonical_set:
                invalid.append(_invalid(candidate.path, population, "source reference is outside canonical inventory", candidate.reference))
            else:
                target.setdefault(candidate.reference, []).append(candidate)
    selected: dict[str, SourceCandidate] = {}
    v11_refs: list[str] = []
    baseline_refs: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []
    for reference in canonical:
        v11 = v11_by_ref.get(reference, [])
        baseline = baseline_by_ref.get(reference, [])
        if len(v11) > 1 or (not v11 and len(baseline) > 1):
            conflicts.append(reference)
        elif len(v11) == 1:
            selected[reference] = v11[0]
            v11_refs.append(reference)
        elif len(baseline) == 1:
            selected[reference] = baseline[0]
            baseline_refs.append(reference)
        else:
            missing.append(reference)
    sort_key = lambda value: _canonical_sort_key(value, order)
    return ReconciliationResult(
        canonical_references=canonical,
        v1_1_certified=tuple(sorted(v11_refs, key=sort_key)),
        baseline_fallback=tuple(sorted(baseline_refs, key=sort_key)),
        missing=tuple(sorted(missing, key=sort_key)),
        conflicts=tuple(sorted(conflicts, key=sort_key)),
        invalid_source_records=tuple(invalid),
        selected_sources=selected,
    )


def reconcile_release(repo_root: str | Path = ".") -> ReconciliationResult:
    """Reconcile the repository's certified upgrade and validated baseline."""

    canonical = canonical_chapter_references()
    v11, v11_invalid, _eligible = load_certified_v1_1(repo_root, canonical)
    baseline, baseline_invalid = load_validated_baseline(repo_root, canonical)
    return reconcile_candidates(canonical, v11, baseline, [*v11_invalid, *baseline_invalid])


def validate_runtime_reference_set(
    runtime_references: Iterable[str],
    canonical_references: Sequence[str] | None = None,
    *,
    allow_partial: bool = False,
) -> dict[str, list[str]]:
    """Validate exact canonical membership, uniqueness, and completeness."""

    canonical = tuple(canonical_references or canonical_chapter_references())
    runtime = list(runtime_references)
    counts: dict[str, int] = {}
    for reference in runtime:
        counts[reference] = counts.get(reference, 0) + 1
    canonical_set = set(canonical)
    duplicate = sorted(reference for reference, count in counts.items() if count > 1)
    missing = [reference for reference in canonical if reference not in counts]
    unexpected = sorted(reference for reference in counts if reference not in canonical_set)
    result = {
        "missing_canonical_refs": missing,
        "unexpected_refs": unexpected,
        "duplicate_refs": duplicate,
    }
    if not allow_partial and any(result.values()):
        raise ReconciliationError(
            "runtime corpus is not an exact canonical set: "
            f"missing={missing[:5]}, unexpected={unexpected[:5]}, duplicates={duplicate[:5]}"
        )
    return result


def reconciliation_markdown(result: ReconciliationResult) -> str:
    """Render a human-readable report while retaining exact reference lists."""

    data = result.to_dict()
    lines = [
        "# Commentary v1.1 canonical runtime reconciliation",
        "",
        "## Result",
        "",
        "The v1.1 eligible population is an upgrade population, not the runtime corpus. The release overlay selects certified v1.1 artifacts first and otherwise selects validated v1.0.1 baseline artifacts by exact canonical chapter reference.",
        "",
        f"- Canonical total: **{data['canonical_total']}**",
        f"- Certified v1.1 replacements: **{data['v1_1_certified_count']}**",
        f"- Validated baseline fallbacks: **{data['baseline_fallback_count']}**",
        f"- Truly missing: **{data['missing_count']}**",
        f"- Conflicts: **{data['conflict_count']}**",
        f"- Invalid source records: **{data['invalid_source_count']}**",
        f"- Final publishable: **{data['final_publishable_count']}**",
        "",
        "The release gate compares the exact runtime reference set with the authoritative canonical inventory; a matching count alone is insufficient.",
        "",
        "## Before and after terminology",
        "",
        "- Before: `935/935 corpus complete` (ambiguous; it described only the selected upgrade population).",
        f"- After: `{data['v1_1_certified_count']}/{data['v1_1_certified_count']} upgrade population complete`.",
        f"- After: `{data['final_publishable_count']}/{data['canonical_total']} canonical runtime chapters publishable`.",
        "",
    ]
    sections = (
        ("V1_1_CERTIFIED", data["v1_1_certified"]),
        ("BASELINE_VALIDATED", data["baseline_fallback"]),
        ("MISSING", data["missing"]),
        ("CONFLICT", data["conflicts"]),
    )
    for title, values in sections:
        lines.extend([f"## {title}", ""])
        if values:
            lines.extend(f"- `{value}`" for value in values)
        else:
            lines.append("- None")
        lines.append("")
    lines.extend(["## INVALID_SOURCE", ""])
    if data["invalid_source_records"]:
        lines.extend(f"- `{json.dumps(value, ensure_ascii=False, sort_keys=True)}`" for value in data["invalid_source_records"])
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "BASELINE_RELEASE",
    "CANONICAL_RUNTIME_STATUS",
    "ReconciliationError",
    "ReconciliationResult",
    "SourceCandidate",
    "UPGRADE_POPULATION_STATUS",
    "canonical_chapter_references",
    "canonical_inventory_fingerprint",
    "load_certified_v1_1",
    "load_validated_baseline",
    "reconcile_candidates",
    "reconcile_release",
    "reconciliation_markdown",
    "validate_runtime_reference_set",
]


def main() -> int:
    """Write the deterministic repository reconciliation artifacts."""

    import argparse

    parser = argparse.ArgumentParser(description="Reconcile Commentary v1.1 with the canonical runtime corpus")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    result = reconcile_release(args.repo_root)
    payload = result.to_dict()
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(reconciliation_markdown(result), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "canonical_total",
        "v1_1_certified_count",
        "baseline_fallback_count",
        "missing_count",
        "conflict_count",
        "invalid_source_count",
        "final_publishable_count",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
