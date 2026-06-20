# SPDX-License-Identifier: MIT
"""Shared helpers for BHF tooling (loading, parsing, dependency resolution).

Used by validate.py and compose.py. Depends only on PyYAML + the standard
library. See ../docs/module-spec.md for the authoritative module contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Module `type` values and their composition/ordering priority (lower = earlier).
TYPE_PRIORITY = {
    "core": 0,
    "language": 1,
    "historical": 2,
    "genre": 3,
    "book": 4,
    "profile": 5,
}

ID_PATTERN = re.compile(r"^(core|genre|book|historical|language|profile)\.[a-z0-9-]+$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
STATUSES = {"draft", "review", "stable", "deprecated"}
XREF_PATTERN = re.compile(r"\[\[([a-z]+\.[a-z0-9-]+)\]\]")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass
class Module:
    id: str
    title: str
    type: str
    version: str
    status: str
    tokens: int
    body: str
    path: Path
    requires: list[str] = field(default_factory=list)
    recommends: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    sources_required: bool = True
    maintainers: list[str] = field(default_factory=list)
    license: str = "CC-BY-4.0"
    # Optional within-type sequencing hint (lower = earlier). Controls the
    # order modules appear in a composed prompt; defaults late so unordered
    # modules fall back to id ordering. See docs/module-spec.md.
    order: int = 100

    @property
    def xrefs(self) -> list[str]:
        return XREF_PATTERN.findall(self.body)


def estimate_tokens(text: str) -> int:
    """Rough, model-agnostic token estimate (~4 chars/token)."""
    return max(1, round(len(text) / 4))


def is_template(path: Path) -> bool:
    return path.name.startswith("_")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Raises ValueError if frontmatter is missing."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(
            "missing or malformed YAML frontmatter "
            "(expected leading '---' block)")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter did not parse to a mapping")
    return meta, match.group(2)


def load_module(path: Path) -> Module:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return Module(
        id=meta.get("id", ""),
        title=meta.get("title", ""),
        type=meta.get("type", ""),
        version=meta.get("version", ""),
        status=meta.get("status", ""),
        tokens=meta.get("tokens", 0),
        body=body,
        path=path,
        requires=list(meta.get("requires", []) or []),
        recommends=list(meta.get("recommends", []) or []),
        tags=list(meta.get("tags", []) or []),
        sources_required=bool(meta.get("sources_required", True)),
        maintainers=list(meta.get("maintainers", []) or []),
        license=meta.get("license", "CC-BY-4.0"),
        order=int(meta.get("order", 100)),
    )


def discover_module_paths(root: Path) -> list[Path]:
    """All non-template .md files under root."""
    return sorted(p for p in root.rglob("*.md") if not is_template(p))


def load_modules(root: Path) -> dict[str, Module]:
    """Load every module under root, keyed by id. Raises on parse error."""
    modules: dict[str, Module] = {}
    for path in discover_module_paths(root):
        mod = load_module(path)
        modules[mod.id] = mod
    return modules


def resolve(modules: dict[str, Module], selected: list[str]) -> list[Module]:
    """Return selected modules plus all transitive `requires`, topologically
    ordered (dependencies first), with a stable tiebreak by (type, id).

    Raises KeyError on an unknown id and ValueError on a dependency cycle.
    """
    # Gather transitive closure over `requires`.
    needed: set[str] = set()
    stack = list(selected)
    while stack:
        mid = stack.pop()
        if mid in needed:
            continue
        if mid not in modules:
            raise KeyError(mid)
        needed.add(mid)
        stack.extend(modules[mid].requires)

    # Kahn topological sort with a deterministic tiebreak.
    indegree = {mid: 0 for mid in needed}
    dependents: dict[str, list[str]] = {mid: [] for mid in needed}
    for mid in needed:
        for dep in modules[mid].requires:
            indegree[mid] += 1
            dependents[dep].append(mid)

    def sort_key(mid: str) -> tuple[int, int, str]:
        mod = modules[mid]
        return (TYPE_PRIORITY.get(mod.type, 99), mod.order, mid)

    ready = sorted((m for m in needed if indegree[m] == 0), key=sort_key)
    ordered: list[str] = []
    while ready:
        mid = ready.pop(0)
        ordered.append(mid)
        for child in dependents[mid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
        ready.sort(key=sort_key)

    if len(ordered) != len(needed):
        cycle = sorted(needed - set(ordered))
        raise ValueError(f"dependency cycle involving: {', '.join(cycle)}")

    return [modules[mid] for mid in ordered]
