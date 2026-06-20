#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate BHF modules against docs/module-spec.md.

Usage:
    python tools/validate.py [framework/ ...]

Exits 0 if all modules are valid, 1 otherwise. Checks frontmatter schema,
id/type/filename agreement, required body sections (and ordering), dependency
and cross-reference resolution, acyclicity, and token-estimate plausibility.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bhf_lib import (
    ID_PATTERN,
    SEMVER_PATTERN,
    STATUSES,
    TYPE_PRIORITY,
    discover_module_paths,
    estimate_tokens,
    load_module,
    resolve,
)

REQUIRED_SECTIONS = [
    "Purpose",
    "When to apply",
    "Interpretive moves",
    "Common errors to avoid",
    "Handling uncertainty",
    "Cross-references",
]

BOOK_EXTRA_SECTIONS = [
    "Genre signals",
    "Historical anchors",
    "Key interpretive cruxes (method, not verdicts)",
]

TOKEN_TOLERANCE = 0.35  # declared `tokens` must be within this fraction of measured.


def heading_order(body: str) -> list[str]:
    return [m.strip() for m in re.findall(r"^##\s+(.+?)\s*$", body, re.MULTILINE)]


def validate_module(path: Path, errors: list[str]) -> "object | None":
    rel = path
    try:
        mod = load_module(path)
    except Exception as exc:  # noqa: BLE001 - surface any parse failure as an error
        errors.append(f"{rel}: {exc}")
        return None

    def err(msg: str) -> None:
        errors.append(f"{rel}: {msg}")

    # --- frontmatter field rules ---
    if not mod.id or not ID_PATTERN.match(mod.id):
        err(f"invalid or missing id '{mod.id}' (must match <type>.<slug>)")
    if not mod.title:
        err("missing title")
    if mod.type not in TYPE_PRIORITY:
        err(f"invalid type '{mod.type}'")
    elif mod.id and not mod.id.startswith(mod.type + "."):
        err(f"id '{mod.id}' does not match type '{mod.type}'")
    if not SEMVER_PATTERN.match(str(mod.version)):
        err(f"version '{mod.version}' is not SemVer MAJOR.MINOR.PATCH")
    if mod.status not in STATUSES:
        err(f"invalid status '{mod.status}'")
    if not isinstance(mod.tokens, int) or mod.tokens <= 0:
        err(f"tokens must be a positive integer, got {mod.tokens!r}")

    # filename folder should match type (framework/<type-plural>/...)
    folder = path.parent.name
    expected_folders = {
        "core": "core", "genre": "genres", "book": "books",
        "context": "context", "language": "language", "profile": "profiles",
    }
    if mod.type in expected_folders and folder != expected_folders[mod.type]:
        expected = expected_folders[mod.type]
        err(f"type '{mod.type}' but file is in '{folder}/' "
            f"(expected '{expected}/')")

    # --- required body sections + ordering ---
    headings = heading_order(mod.body)
    required = list(REQUIRED_SECTIONS)
    if mod.type == "book":
        # extra book sections must appear after "Interpretive moves"
        for s in BOOK_EXTRA_SECTIONS:
            if s not in headings:
                err(f"missing required book section '## {s}'")
    present_required = [h for h in headings if h in required]
    for s in required:
        if s not in headings:
            err(f"missing required section '## {s}'")
    if present_required != [s for s in required if s in headings]:
        err("required sections are present but out of order")

    # --- token plausibility ---
    measured = estimate_tokens(mod.body)
    if isinstance(mod.tokens, int) and mod.tokens > 0:
        lo = measured * (1 - TOKEN_TOLERANCE)
        hi = measured * (1 + TOKEN_TOLERANCE)
        if not (lo <= mod.tokens <= hi):
            err(f"declared tokens={mod.tokens} far from measured ~{measured} "
                f"(allowed {int(lo)}-{int(hi)})")

    return mod


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path("framework")]
    errors: list[str] = []
    modules: dict[str, object] = {}
    seen_ids: dict[str, Path] = {}

    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            errors.append(f"{root}: path does not exist")
            continue
        paths.extend(discover_module_paths(root))

    for path in paths:
        mod = validate_module(path, errors)
        if mod is None:
            continue
        if mod.id in seen_ids:
            errors.append(
                f"{path}: duplicate id '{mod.id}' "
                f"(also in {seen_ids[mod.id]})")
        else:
            seen_ids[mod.id] = path
            modules[mod.id] = mod

    # --- cross-module reference resolution + acyclicity ---
    for mid, mod in modules.items():
        ref_groups = (
            ("requires", mod.requires),
            ("recommends", mod.recommends),
        )
        for ref_kind, refs in ref_groups:
            for ref in refs:
                if ref not in modules:
                    errors.append(f"{mod.path}: {ref_kind} unknown module '{ref}'")
        for ref in mod.xrefs:
            if ref not in modules:
                errors.append(f"{mod.path}: cross-reference [[{ref}]] does not resolve")

    if modules:
        try:
            resolve(modules, list(modules.keys()))
        except ValueError as exc:
            errors.append(f"dependency graph: {exc}")
        except KeyError as exc:
            errors.append(f"dependency graph: unknown module {exc}")

    if errors:
        print(f"FAIL — {len(errors)} problem(s) in {len(modules)} module(s):\n")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK — {len(modules)} module(s) valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
