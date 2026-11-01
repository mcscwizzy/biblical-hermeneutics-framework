#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and package the standalone Scripture Trails ChatGPT plugin.

The BHF framework is read only at build time. The generated plugin contains
portable instructions and references; it does not import or call BHF at run
time.

Usage:
    python tools/build_scripture_trails.py --validate
    python tools/build_scripture_trails.py --build
    python tools/build_scripture_trails.py --package
    python tools/build_scripture_trails.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from bhf_lib import (  # noqa: E402
    Module,
    XREF_PATTERN,
    discover_module_paths,
    load_modules,
    resolve,
)
from validate import validate_module  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_REL = Path("plugins/scripture-trails")
CONFIG_REL = PLUGIN_REL / "config/module-selection.yml"
VERSION_REL = PLUGIN_REL / "VERSION"
SOURCE_MANIFEST = "source-module-manifest.json"
SKILL_REL = Path("skills/explore-scripture/SKILL.md")
REFERENCE_DIR = Path("skills/explore-scripture/references")
REQUIRED_CORE = (
    "core.core-framework",
    "core.genre-awareness",
    "core.original-audience",
    "core.observe-interpret-apply",
    "core.intertextuality",
    "core.epistemic-humility",
    "core.anti-hallucination",
)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
PLUGIN_NAME_RE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
PLUGIN_MANIFEST_PROPERTIES = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
SKILL_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")


class BuildError(ValueError):
    """Raised when plugin inputs or generated package content is invalid."""


def _read_yaml(path: Path, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"{label} is missing: {path}") from exc
    except yaml.YAMLError as exc:
        raise BuildError(f"{label} is not valid YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise BuildError(f"{label} must contain a YAML mapping")
    return value


def _safe_relative(value: str, *, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in value
    ):
        raise BuildError(f"unsafe relative path for {label}: {value!r}")
    return path


def _inside(base: Path, relative: str | PurePosixPath, *, label: str) -> Path:
    safe = _safe_relative(str(relative), label=label)
    path = base.joinpath(*safe.parts)
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError as exc:
        raise BuildError(f"{label} escapes its root: {relative}") from exc
    return path


def _load_config(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / CONFIG_REL
    if config_path.is_symlink():
        raise BuildError("module selection must not be a symlink")
    config = _read_yaml(config_path, "module selection")
    if not isinstance(config.get("required_modules"), list):
        raise BuildError("module selection requires a required_modules list")
    outputs = config.get("module_outputs")
    supports = config.get("supports", {})
    if not isinstance(outputs, dict) or not outputs:
        raise BuildError("module selection requires a non-empty module_outputs mapping")
    if not isinstance(supports, dict):
        raise BuildError("module selection supports must be a mapping")
    return config


def _selected_modules(repo_root: Path) -> tuple[dict[str, Module], list[Module], dict[str, list[str]], dict[str, list[str]]]:
    config = _load_config(repo_root)
    plugin_root = repo_root / PLUGIN_REL
    if plugin_root.is_symlink() or not plugin_root.is_dir():
        raise BuildError(f"plugin workspace must be a real directory: {plugin_root}")
    framework_dir = repo_root / "framework"
    if not framework_dir.is_dir():
        raise BuildError(f"framework source directory is missing: {framework_dir}")

    paths = discover_module_paths(framework_dir)
    symlinked_sources = [path for path in paths if path.is_symlink()]
    if symlinked_sources:
        raise BuildError(
            "framework module sources must not be symlinks: "
            + ", ".join(path.relative_to(repo_root).as_posix() for path in symlinked_sources)
        )
    modules = load_modules(framework_dir)
    if len(modules) != len(paths):
        raise BuildError("framework contains duplicate module IDs")

    module_outputs: dict[str, list[str]] = {}
    outputs: dict[str, list[str]] = {}
    for output, ids in config["module_outputs"].items():
        safe_output = _safe_relative(output, label="generated reference path")
        if not str(safe_output).startswith("references/") or safe_output.suffix != ".md":
            raise BuildError(f"generated output must be a Markdown reference path: {output}")
        if not isinstance(ids, list) or not ids:
            raise BuildError(f"module output {output} must select at least one module")
        outputs[str(safe_output)] = []
        for module_id in ids:
            if not isinstance(module_id, str) or not module_id:
                raise BuildError(f"invalid module ID in output {output}: {module_id!r}")
            if module_id in module_outputs:
                raise BuildError(f"module {module_id} is assigned to more than one output")
            if module_id not in modules:
                raise BuildError(f"unknown module ID in selection: {module_id}")
            module_outputs[module_id] = [str(safe_output)]
            outputs[str(safe_output)].append(module_id)

    selected_ids = list(module_outputs)
    required = config["required_modules"]
    if not all(isinstance(module_id, str) for module_id in required):
        raise BuildError("required_modules must contain only module IDs")
    missing_required = sorted(set(REQUIRED_CORE) - set(required))
    if missing_required:
        raise BuildError(
            "required_modules omits foundational modules: " + ", ".join(missing_required)
        )
    unselected_required = sorted(set(REQUIRED_CORE) - set(selected_ids))
    if unselected_required:
        raise BuildError(
            "required foundational modules are not assigned to a reference: "
            + ", ".join(unselected_required)
        )
    extra_required = sorted(set(required) - set(REQUIRED_CORE))
    if extra_required:
        raise BuildError(
            "required_modules contains IDs outside the foundational set: "
            + ", ".join(extra_required)
        )

    for reference, supporting_ids in config.get("supports", {}).items():
        safe_reference = _safe_relative(reference, label="supporting reference path")
        if not str(safe_reference).startswith("references/") or safe_reference.suffix != ".md":
            raise BuildError(f"supporting reference must be Markdown under references/: {reference}")
        if not isinstance(supporting_ids, list):
            raise BuildError(f"supporting modules for {reference} must be a list")
        for module_id in supporting_ids:
            if module_id not in modules:
                raise BuildError(f"unknown supporting module ID: {module_id}")
            if module_id not in selected_ids:
                raise BuildError(f"supporting module is not selected: {module_id}")
            module_outputs.setdefault(module_id, []).append(str(safe_reference))

    try:
        ordered = resolve(modules, selected_ids)
    except (KeyError, ValueError) as exc:
        raise BuildError(f"could not resolve selected modules: {exc}") from exc

    implicit_dependencies = sorted({module.id for module in ordered} - set(selected_ids))
    if implicit_dependencies:
        raise BuildError(
            "dependency modules must be explicitly assigned to a reference: "
            + ", ".join(implicit_dependencies)
        )

    errors: list[str] = []
    for module in ordered:
        validate_module(module.path, errors)
        if module.status != "stable":
            errors.append(f"{module.path}: selected module status is {module.status!r}, not 'stable'")
        for reference in module.xrefs:
            if reference not in modules:
                errors.append(f"{module.path}: unresolved internal module reference [[{reference}]]")
    if errors:
        raise BuildError("selected BHF modules are invalid:\n  - " + "\n  - ".join(errors))

    return modules, ordered, outputs, module_outputs


def _plugin_version(plugin_root: Path) -> str:
    try:
        version = (plugin_root / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise BuildError(f"plugin VERSION file is missing: {plugin_root / 'VERSION'}") from exc
    if not SEMVER_RE.fullmatch(version):
        raise BuildError(f"plugin VERSION is not SemVer MAJOR.MINOR.PATCH: {version!r}")
    return version


def _replace_module_references(body: str, modules: dict[str, Module], source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        module_id = match.group(1)
        if module_id not in modules:
            raise BuildError(f"{source}: unresolved internal module reference [[{module_id}]]")
        return f"**{modules[module_id].title}**"

    return XREF_PATTERN.sub(replace, body)


def _render_reference(title: str, module_ids: list[str], modules: dict[str, Module]) -> str:
    sections = [f"# {title}\n", "<!-- Generated from selected BHF modules; see source-module-manifest.json. -->\n"]
    for module_id in module_ids:
        module = modules[module_id]
        body = _replace_module_references(module.body.strip(), modules, str(module.path))
        body = re.sub(r"^##\s+(.+)$", r"### \1", body, flags=re.MULTILINE)
        sections.append(f"## {module.title}\n\n{body}\n")
    return "\n".join(sections).rstrip() + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_resources(repo_root: Path = REPO_ROOT) -> dict[str, str]:
    """Return deterministic generated resources keyed by plugin-relative path."""
    repo_root = repo_root.resolve()
    plugin_root = repo_root / PLUGIN_REL
    modules, ordered, outputs, module_outputs = _selected_modules(repo_root)
    version = _plugin_version(plugin_root)
    ordered_ids = {module.id for module in ordered}

    # Keep the visible reference order stable and the module order from the
    # shared resolver. The title map also adapts BHF-only [[id]] syntax.
    generated: dict[str, str] = {}
    reference_titles = {
        "references/interpretive-method.md": "Interpretive Method",
        "references/historical-context.md": "Historical and Cultural Context",
        "references/genre-and-language.md": "Genre and Original-Language Guidance",
        "references/intertextuality.md": "Intertextuality and Biblical Connections",
        "references/evidence-and-boundaries.md": "Evidence, Sources, and Interpretive Boundaries",
        "references/passage-guides.md": "Selected Book-Level Guidance",
    }
    module_by_output = {
        output: [module_id for module_id in ids if module_id in ordered_ids]
        for output, ids in outputs.items()
    }
    for output, ids in module_by_output.items():
        missing_title = output not in reference_titles
        if missing_title:
            raise BuildError(f"no generated title registered for configured output {output}")
        ordered_for_output = [module.id for module in ordered if module.id in ids]
        generated[f"{(SKILL_REL.parent / output).as_posix()}"] = _render_reference(
            reference_titles[output], ordered_for_output, modules
        )

    config = _load_config(repo_root)
    supporting = config.get("supports", {})
    sources: list[dict[str, Any]] = []
    for module in ordered:
        source_path = module.path.relative_to(repo_root).as_posix()
        raw = module.path.read_bytes()
        sources.append(
            {
                "id": module.id,
                "title": module.title,
                "version": module.version,
                "status": module.status,
                "license": module.license,
                "source_path": source_path,
                "sha256": _sha256(raw),
                "outputs": sorted(
                    (SKILL_REL.parent / output).as_posix()
                    for output in module_outputs.get(module.id, [])
                ),
            }
        )

    reference_entries: list[dict[str, Any]] = []
    for output in sorted(module_by_output):
        relative = (SKILL_REL.parent / output).as_posix()
        content = generated[relative].encode("utf-8")
        reference_entries.append(
            {
                "path": relative,
                "kind": "generated",
                "sha256": _sha256(content),
                "source_modules": module_by_output[output],
            }
        )
    for reference in sorted(supporting):
        path = _inside(plugin_root / SKILL_REL.parent, reference, label="supporting reference")
        if not path.is_file():
            raise BuildError(f"supporting reference file is missing: {path}")
        raw = path.read_bytes()
        reference_entries.append(
            {
                "path": (SKILL_REL.parent / reference).as_posix(),
                "kind": "authored",
                "sha256": _sha256(raw),
                "source_modules": supporting[reference],
            }
        )

    manifest = {
        "schema_version": 1,
        "plugin": "scripture-trails",
        "plugin_version": version,
        "sources": sources,
        "references": sorted(reference_entries, key=lambda entry: entry["path"]),
    }
    generated[SOURCE_MANIFEST] = json.dumps(
        manifest, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    generated["LICENSE-CONTENT"] = (repo_root / "LICENSE-CONTENT").read_text(
        encoding="utf-8"
    )
    return generated


def _runtime_files(plugin_root: Path) -> list[tuple[str, Path]]:
    """Return only approved plugin runtime files; tests/config are excluded."""
    if plugin_root.is_symlink() or not plugin_root.is_dir():
        raise BuildError(f"plugin workspace must be a real directory: {plugin_root}")
    exact = [
        "plugin.json",
        "README.md",
        "ATTRIBUTION.md",
        "LICENSE-CONTENT",
        "VERSION",
        SOURCE_MANIFEST,
        SKILL_REL.as_posix(),
    ]
    candidates: list[tuple[str, Path]] = []
    for name in exact:
        path = _inside(plugin_root, name, label="runtime file")
        if path.is_symlink():
            raise BuildError(f"plugin runtime files must not be symlinks: {name}")
        if not path.is_file():
            raise BuildError(f"required runtime file is missing: {name}")
        candidates.append((name, path))
    config = _load_config(plugin_root.parent.parent)
    reference_paths: set[str] = set()
    for output in config["module_outputs"]:
        reference_paths.add((SKILL_REL.parent / _safe_relative(
            output, label="generated reference path"
        )).as_posix())
    for reference in config.get("supports", {}):
        reference_paths.add((SKILL_REL.parent / _safe_relative(
            reference, label="supporting reference path"
        )).as_posix())
    for relative in sorted(reference_paths):
        path = _inside(plugin_root, relative, label="runtime reference")
        if path.is_symlink():
            raise BuildError(f"plugin runtime references must not be symlinks: {relative}")
        if not path.is_file():
            raise BuildError(f"configured runtime reference is missing: {relative}")
        candidates.append((relative, path))
    if len({name for name, _ in candidates}) != len(candidates):
        raise BuildError("plugin runtime file list contains duplicate paths")
    return sorted(candidates, key=lambda item: item[0])


def _plugin_manifest_errors(plugin_manifest: Any, version: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(plugin_manifest, dict):
        errors.append("plugin.json must contain a JSON object")
        plugin_manifest = {}
    unknown_properties = sorted(set(plugin_manifest) - PLUGIN_MANIFEST_PROPERTIES)
    if unknown_properties:
        errors.append("unknown plugin.json property: " + ", ".join(unknown_properties))
    if plugin_manifest.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        errors.append("plugin.json must use the portable Agent Plugins schema")
    if plugin_manifest.get("name") != "scripture-trails":
        errors.append("plugin.json name must be 'scripture-trails'")
    name = plugin_manifest.get("name")
    if not isinstance(name, str) or len(name) > 64 or not PLUGIN_NAME_RE.fullmatch(name):
        errors.append("plugin.json name must match the portable lowercase plugin-name format")
    if plugin_manifest.get("version") != version:
        errors.append("plugin.json version must match VERSION")
    if not isinstance(plugin_manifest.get("version"), str):
        errors.append("plugin.json version must be a string")
    if plugin_manifest.get("license") != "CC-BY-4.0":
        errors.append("plugin.json license must be CC-BY-4.0 for the included BHF content")
    if not isinstance(plugin_manifest.get("description"), str) or not plugin_manifest["description"].strip():
        errors.append("plugin.json requires a non-empty description")
    for field in ("homepage", "repository", "license"):
        if field in plugin_manifest and not isinstance(plugin_manifest[field], str):
            errors.append(f"plugin.json {field} must be a string")
    if "keywords" in plugin_manifest and (
        not isinstance(plugin_manifest["keywords"], list)
        or not all(isinstance(keyword, str) for keyword in plugin_manifest["keywords"])
    ):
        errors.append("plugin.json keywords must be an array of strings")
    author = plugin_manifest.get("author")
    if author is not None:
        if not isinstance(author, dict):
            errors.append("plugin.json author must be an object")
        else:
            unknown_author_properties = sorted(set(author) - {"name", "email", "url"})
            if unknown_author_properties:
                errors.append("unknown plugin.json author property: " + ", ".join(unknown_author_properties))
            if not all(isinstance(value, str) for value in author.values()):
                errors.append("plugin.json author properties must be strings")
    extensions = plugin_manifest.get("extensions")
    if extensions is not None and (
        not isinstance(extensions, dict)
        or not all(isinstance(value, dict) for value in extensions.values())
    ):
        errors.append("plugin.json extensions must map namespaces to objects")
    openai = (extensions or {}).get("com.openai", {}) if isinstance(extensions, dict) else {}
    interface = openai.get("interface", {}) if isinstance(openai, dict) else {}
    if not isinstance(interface, dict):
        errors.append("plugin.json OpenAI interface must be an object")
    else:
        for field, limit in (
            ("displayName", 30),
            ("shortDescription", 30),
            ("longDescription", 4000),
            ("developerName", 80),
        ):
            value = interface.get(field)
            if value is None:
                errors.append(f"plugin.json interface {field} is required")
            elif not isinstance(value, str) or not value.strip() or len(value) > limit:
                errors.append(f"plugin.json interface {field} must be a string of at most {limit} characters")
        category = interface.get("category")
        if not isinstance(category, str) or not category.strip():
            errors.append("plugin.json interface category is required")
        capabilities = interface.get("capabilities")
        if capabilities is not None and (
            not isinstance(capabilities, list)
            or len(capabilities) > 20
            or not all(isinstance(value, str) and len(value) <= 120 for value in capabilities)
        ):
            errors.append("plugin.json interface capabilities must have at most 20 strings of 120 characters")
        prompts = interface.get("defaultPrompt")
        if prompts is not None:
            prompt_values = [prompts] if isinstance(prompts, str) else prompts
            if (
                not isinstance(prompt_values, list)
                or len(prompt_values) > 3
                or not all(isinstance(value, str) and len(value) <= 128 for value in prompt_values)
            ):
                errors.append("plugin.json interface defaultPrompt must contain at most three strings of 128 characters")
    if "mcpServers" in plugin_manifest or "dependencies" in plugin_manifest:
        errors.append("skills-only plugin manifest must not require MCP tools or dependencies")
    return errors


def _skill_frontmatter_errors(skill_text: str) -> list[str]:
    errors: list[str] = []
    frontmatter = SKILL_FRONTMATTER_RE.match(skill_text)
    if not frontmatter:
        return [f"{SKILL_REL.as_posix()}: missing YAML frontmatter"]
    try:
        metadata = yaml.safe_load(frontmatter.group(1))
    except yaml.YAMLError as exc:
        return [f"{SKILL_REL.as_posix()}: invalid YAML frontmatter: {exc}"]
    if not isinstance(metadata, dict):
        errors.append(f"{SKILL_REL.as_posix()}: frontmatter must be a YAML mapping")
    else:
        if metadata.get("name") != "explore-scripture":
            errors.append("skill name must be 'explore-scripture'")
        if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
            errors.append("skill frontmatter requires a description")
    return errors


def _attribution_errors(text: str) -> list[str]:
    normalized = text.lower()
    if (
        "biblical hermeneutics framework" not in normalized
        or "cc by 4.0" not in normalized
        or "creativecommons.org/licenses/by/4.0" not in normalized
    ):
        return ["ATTRIBUTION.md must identify BHF and its CC BY 4.0 license"]
    return []


def _content_license_errors(text: str) -> list[str]:
    normalized = text.lower()
    if (
        "creative commons attribution 4.0" not in normalized
        or "creativecommons.org/licenses/by/4.0" not in normalized
        or "public license" not in normalized
    ):
        return ["LICENSE-CONTENT does not contain the CC BY 4.0 license text"]
    return []


def _markdown_text_errors(text: str, relative: str, available_files: set[str]) -> list[str]:
    errors: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(text):
        target = match.group(1)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue
        target_path, _, _fragment = target.partition("#")
        if not target_path:
            continue
        if target_path.startswith("/") or "\\" in target_path:
            errors.append(f"{relative}: unsafe Markdown link {target!r}")
            continue
        resolved = PurePosixPath(relative).parent.joinpath(target_path)
        normalized = PurePosixPath(os.path.normpath(str(resolved)))
        if normalized.is_absolute() or ".." in normalized.parts:
            errors.append(f"{relative}: Markdown link escapes the plugin: {target!r}")
        elif normalized.as_posix() not in available_files:
            errors.append(f"{relative}: Markdown link does not resolve in the package: {target!r}")
    return errors


def _markdown_errors(path: Path, relative: str, available_files: set[str]) -> list[str]:
    return _markdown_text_errors(path.read_text(encoding="utf-8"), relative, available_files)


def validate_workspace(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate module selection and plugin files without writing resources."""
    repo_root = repo_root.resolve()
    errors: list[str] = []
    plugin_root = repo_root / PLUGIN_REL
    try:
        _selected_modules(repo_root)
        version = _plugin_version(plugin_root)
    except (BuildError, OSError, TypeError, ValueError) as exc:
        return [str(exc)]

    plugin_manifest_path = plugin_root / "plugin.json"
    try:
        plugin_manifest = json.loads(plugin_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"plugin.json: {exc}"]
    errors.extend(_plugin_manifest_errors(plugin_manifest, version))

    skill_path = plugin_root / SKILL_REL
    try:
        skill_text = skill_path.read_text(encoding="utf-8")
    except OSError as exc:
        return errors + [f"skill file is missing or unreadable: {exc}"]
    errors.extend(_skill_frontmatter_errors(skill_text))

    try:
        cases = _read_yaml(plugin_root / "tests/acceptance-cases.yml", "acceptance cases")
        if not isinstance(cases.get("cases"), list) or not cases["cases"]:
            errors.append("acceptance cases must contain a non-empty cases list")
    except BuildError as exc:
        errors.append(str(exc))

    if not (plugin_root / SOURCE_MANIFEST).is_file():
        errors.append(f"generated {SOURCE_MANIFEST} is missing; run --build")
    try:
        runtime_files = _runtime_files(plugin_root)
    except BuildError as exc:
        return errors + [str(exc)]
    runtime_names = {name for name, _ in runtime_files}
    for name, path in runtime_files:
        if path.is_symlink():
            errors.append(f"plugin runtime files must not be symlinks: {name}")
        if path.suffix.lower() in {".sqlite", ".sqlite3", ".db", ".zip"}:
            errors.append(f"unrelated or restricted data file in runtime resources: {name}")
        if path.suffix.lower() in {".md", ".json", ".txt"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(f"runtime text resource is not UTF-8: {name}")
                continue
            if "[[" in text and "]]" in text:
                errors.append(f"unresolved BHF module-reference syntax in runtime resource: {name}")
            if name.endswith(".md"):
                errors.extend(_markdown_errors(path, name, runtime_names))

    try:
        expected = build_resources(repo_root)
        source_manifest = json.loads(expected[SOURCE_MANIFEST])
        actual_manifest_path = plugin_root / SOURCE_MANIFEST
        try:
            actual_manifest_bytes = actual_manifest_path.read_bytes()
        except OSError as exc:
            errors.append(f"{SOURCE_MANIFEST} is missing or unreadable: {exc}")
        else:
            try:
                json.loads(actual_manifest_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                errors.append(f"{SOURCE_MANIFEST} is invalid JSON: {exc}")
            if actual_manifest_bytes != expected[SOURCE_MANIFEST].encode("utf-8"):
                errors.append(f"{SOURCE_MANIFEST} is stale; run --build")
        configured_outputs = {
            (SKILL_REL.parent / output).as_posix()
            for output in _load_config(repo_root)["module_outputs"]
        }
        configured_outputs.update(
            (SKILL_REL.parent / reference).as_posix()
            for reference in _load_config(repo_root).get("supports", {})
        )
        for relative in sorted(configured_outputs):
            if not (plugin_root / relative).is_file():
                errors.append(f"packaged reference is missing: {relative}; run --build")
        if not isinstance(source_manifest, dict) or not isinstance(source_manifest.get("sources"), list):
            errors.append(f"{SOURCE_MANIFEST} must contain a sources list")
        try:
            attribution = (plugin_root / "ATTRIBUTION.md").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"ATTRIBUTION.md is missing or invalid: {exc}")
        else:
            errors.extend(_attribution_errors(attribution))
        try:
            content_license = (plugin_root / "LICENSE-CONTENT").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"LICENSE-CONTENT is missing or invalid: {exc}")
        else:
            errors.extend(_content_license_errors(content_license))
    except (BuildError, OSError, ValueError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def write_generated_resources(repo_root: Path = REPO_ROOT) -> list[str]:
    repo_root = repo_root.resolve()
    plugin_root = repo_root / PLUGIN_REL
    resources = build_resources(repo_root)
    current_manifest = json.loads(resources[SOURCE_MANIFEST])
    current_references = {
        entry["path"] for entry in current_manifest.get("references", [])
    }
    old_manifest_path = plugin_root / SOURCE_MANIFEST
    if old_manifest_path.is_file():
        try:
            old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            old_manifest = {}
        old_references = old_manifest.get("references", []) if isinstance(old_manifest, dict) else []
        if isinstance(old_references, list):
            for reference in old_references:
                if not isinstance(reference, dict) or reference.get("kind") != "generated":
                    continue
                relative = reference.get("path")
                if not isinstance(relative, str) or relative in current_references:
                    continue
                if not relative.startswith(REFERENCE_DIR.as_posix() + "/"):
                    continue
                stale_path = _inside(plugin_root, relative, label="obsolete generated reference")
                if stale_path.is_symlink():
                    raise BuildError(f"obsolete generated reference must not be a symlink: {relative}")
                if stale_path.is_file():
                    stale_path.unlink()
    for relative, text in resources.items():
        path = _inside(plugin_root, relative, label="generated resource")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(text)
    return sorted(resources)


def _manifest_output_sources(repo_root: Path) -> dict[str, set[str]]:
    plugin_root = repo_root / PLUGIN_REL
    path = plugin_root / SOURCE_MANIFEST
    if not path.is_file():
        return {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(manifest, dict):
        return {}
    result: dict[str, set[str]] = {}
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        return result
    for source in sources:
        if not isinstance(source, dict):
            continue
        for output in source.get("outputs", []):
            if isinstance(output, str):
                result.setdefault(output, set()).add(str(source.get("id", "")))
    return result


def check_generated_resources(repo_root: Path = REPO_ROOT) -> list[str]:
    """Return stale-resource diagnostics; an empty list means byte-for-byte fresh."""
    repo_root = repo_root.resolve()
    plugin_root = repo_root / PLUGIN_REL
    expected = build_resources(repo_root)
    previous_sources = _manifest_output_sources(repo_root)
    current_manifest = json.loads(expected[SOURCE_MANIFEST])
    current_sources = {
        source["id"]: source for source in current_manifest["sources"]
    }
    output_sources: dict[str, set[str]] = {}
    for source in current_manifest["sources"]:
        for output in source.get("outputs", []):
            output_sources.setdefault(output, set()).add(source["id"])
    configured_references = {
        entry["path"] for entry in current_manifest.get("references", [])
    }

    errors: list[str] = []
    for relative, text in expected.items():
        path = _inside(plugin_root, relative, label="generated resource")
        expected_bytes = text.encode("utf-8")
        if not path.is_file() or path.read_bytes() != expected_bytes:
            if relative == SOURCE_MANIFEST:
                old_manifest_path = plugin_root / SOURCE_MANIFEST
                try:
                    old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    old_manifest = {}
                old_sources_data = old_manifest.get("sources", []) if isinstance(old_manifest, dict) else []
                if not isinstance(old_sources_data, list):
                    old_sources_data = []
                old_sources = {
                    source.get("id"): source
                    for source in old_sources_data
                    if isinstance(source, dict)
                }
                changed_modules = sorted(
                    module_id
                    for module_id, source in current_sources.items()
                    if old_sources.get(module_id, {}).get("sha256") != source.get("sha256")
                    or old_sources.get(module_id, {}).get("version") != source.get("version")
                )
                impacted = sorted(
                    {
                        output
                        for module_id in changed_modules
                        for output in current_sources[module_id].get("outputs", [])
                    }
                )
                detail = f"source modules: {', '.join(changed_modules) or 'manifest inputs changed'}"
                if impacted:
                    detail += f"; affected references: {', '.join(impacted)}"
            else:
                modules = sorted(output_sources.get(relative, set()) | previous_sources.get(relative, set()))
                detail = f"source modules: {', '.join(modules) or 'selection or builder changed'}"
            errors.append(f"stale generated resource {relative} ({detail})")
    reference_root = plugin_root / REFERENCE_DIR
    if reference_root.is_dir():
        for path in sorted(reference_root.rglob("*.md")):
            relative = path.relative_to(plugin_root).as_posix()
            if relative in configured_references:
                continue
            modules = sorted(previous_sources.get(relative, set()))
            detail = (
                f"; previously generated from source modules: {', '.join(modules)}"
                if modules
                else ""
            )
            errors.append(f"stale unconfigured reference {relative}{detail}")
    return errors


def _package_entries(plugin_root: Path) -> list[tuple[str, Path]]:
    entries = _runtime_files(plugin_root)
    missing = [name for name, path in entries if not path.is_file()]
    if missing:
        raise BuildError("required runtime files are missing: " + ", ".join(missing))
    return entries


def _source_manifest_errors(manifest: Any, archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return [f"{SOURCE_MANIFEST} must contain a JSON object"]
    if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1:
        errors.append(f"{SOURCE_MANIFEST} schema_version must be 1")
    if manifest.get("plugin") != "scripture-trails":
        errors.append(f"{SOURCE_MANIFEST} plugin must be 'scripture-trails'")
    version = manifest.get("plugin_version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        errors.append(f"{SOURCE_MANIFEST} plugin_version must be SemVer MAJOR.MINOR.PATCH")

    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{SOURCE_MANIFEST} must contain a non-empty sources list")
        sources = []
    source_by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        label = f"{SOURCE_MANIFEST} sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object")
            continue
        module_id = source.get("id")
        if not isinstance(module_id, str) or not module_id.strip():
            errors.append(f"{label} requires a module id")
            continue
        if module_id in source_by_id:
            errors.append(f"{SOURCE_MANIFEST} contains duplicate source module {module_id}")
        source_by_id[module_id] = source
        for field in ("title", "version", "status", "license"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                errors.append(f"{label} requires a non-empty {field}")
        if isinstance(source.get("version"), str) and not SEMVER_RE.fullmatch(source["version"]):
            errors.append(f"{label} version must be SemVer MAJOR.MINOR.PATCH")
        if source.get("status") != "stable":
            errors.append(f"{label} status must be 'stable'")
        source_path = source.get("source_path")
        if not isinstance(source_path, str):
            errors.append(f"{label} requires a repository-relative source_path")
        else:
            try:
                safe_source = _safe_relative(source_path, label=f"{label} source_path")
                if not source_path.startswith("framework/") or safe_source.suffix != ".md":
                    errors.append(f"{label} source_path must identify a framework Markdown module")
            except BuildError as exc:
                errors.append(str(exc))
        if not isinstance(source.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
            errors.append(f"{label} sha256 must be a lowercase SHA-256 digest")
        outputs = source.get("outputs")
        if not isinstance(outputs, list) or not all(isinstance(item, str) for item in outputs):
            errors.append(f"{label} outputs must be a list of reference paths")
        else:
            if len(outputs) != len(set(outputs)):
                errors.append(f"{label} outputs must not contain duplicates")
            for output in outputs:
                try:
                    safe_output = _safe_relative(output, label=f"{label} output")
                    if not output.startswith(REFERENCE_DIR.as_posix() + "/") or safe_output.suffix != ".md":
                        errors.append(f"{label} output must be a packaged Markdown reference")
                except BuildError as exc:
                    errors.append(str(exc))

    missing_core = sorted(set(REQUIRED_CORE) - set(source_by_id))
    if missing_core:
        errors.append(
            f"{SOURCE_MANIFEST} omits required source modules: " + ", ".join(missing_core)
        )

    references = manifest.get("references")
    if not isinstance(references, list) or not references:
        errors.append(f"{SOURCE_MANIFEST} must contain a non-empty references list")
        references = []
    reference_by_path: dict[str, dict[str, Any]] = {}
    for index, reference in enumerate(references):
        label = f"{SOURCE_MANIFEST} references[{index}]"
        if not isinstance(reference, dict):
            errors.append(f"{label} must be an object")
            continue
        path = reference.get("path")
        if not isinstance(path, str):
            errors.append(f"{label} requires a reference path")
            continue
        if path in reference_by_path:
            errors.append(f"{SOURCE_MANIFEST} contains duplicate reference {path}")
        reference_by_path[path] = reference
        try:
            safe_path = _safe_relative(path, label=f"{label} path")
            if not path.startswith(REFERENCE_DIR.as_posix() + "/") or safe_path.suffix != ".md":
                errors.append(f"{label} path must be a packaged Markdown reference")
        except BuildError as exc:
            errors.append(str(exc))
        if reference.get("kind") not in ("generated", "authored"):
            errors.append(f"{label} kind must be 'generated' or 'authored'")
        digest = reference.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{label} sha256 must be a lowercase SHA-256 digest")
        elif path in archive.namelist():
            if _sha256(archive.read(path)) != digest:
                errors.append(f"{label} sha256 does not match packaged file {path}")
        else:
            errors.append(f"{label} file is missing from the ZIP: {path}")
        module_ids = reference.get("source_modules")
        if not isinstance(module_ids, list) or not module_ids or not all(isinstance(item, str) for item in module_ids):
            errors.append(f"{label} source_modules must be a non-empty list of module ids")
        else:
            if len(module_ids) != len(set(module_ids)):
                errors.append(f"{label} source_modules must not contain duplicates")
            unknown = sorted(set(module_ids) - set(source_by_id))
            if unknown:
                errors.append(f"{label} contains unknown source modules: " + ", ".join(unknown))

    packaged_references = {
        name for name in archive.namelist()
        if name.startswith(REFERENCE_DIR.as_posix() + "/") and name.endswith(".md")
    }
    if packaged_references != set(reference_by_path):
        missing = sorted(packaged_references - set(reference_by_path))
        extra = sorted(set(reference_by_path) - packaged_references)
        if missing:
            errors.append(f"{SOURCE_MANIFEST} does not track packaged references: " + ", ".join(missing))
        if extra:
            errors.append(f"{SOURCE_MANIFEST} tracks absent references: " + ", ".join(extra))

    for module_id, source in source_by_id.items():
        outputs = source.get("outputs")
        if not isinstance(outputs, list):
            continue
        for output in outputs:
            if not isinstance(output, str):
                continue
            reference = reference_by_path.get(output)
            if reference is None:
                errors.append(f"{SOURCE_MANIFEST} source {module_id} names untracked output {output}")
            elif (
                not isinstance(reference.get("source_modules"), list)
                or module_id not in reference["source_modules"]
            ):
                errors.append(f"{SOURCE_MANIFEST} output mapping disagrees for source {module_id}: {output}")
    for path, reference in reference_by_path.items():
        module_ids = reference.get("source_modules")
        if not isinstance(module_ids, list):
            continue
        for module_id in module_ids:
            if not isinstance(module_id, str):
                continue
            source = source_by_id.get(module_id)
            outputs = source.get("outputs") if source is not None else []
            if source is not None and (not isinstance(outputs, list) or path not in outputs):
                errors.append(f"{SOURCE_MANIFEST} output mapping disagrees for reference {path}: {module_id}")
    return errors


def validate_archive(archive_path: Path, plugin_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                errors.append("ZIP contains duplicate paths")
            for name in names:
                safe = PurePosixPath(name)
                if safe.is_absolute() or ".." in safe.parts or "\\" in name:
                    errors.append(f"unsafe ZIP path: {name}")
            required_files = {
                "plugin.json",
                "README.md",
                "ATTRIBUTION.md",
                "LICENSE-CONTENT",
                "VERSION",
                SOURCE_MANIFEST,
                SKILL_REL.as_posix(),
            }
            missing_files = sorted(required_files - set(names))
            if missing_files:
                errors.append("ZIP is missing required files: " + ", ".join(missing_files))
            if any(name.endswith((".sqlite", ".sqlite3", ".db", ".zip")) for name in names):
                errors.append("ZIP contains unrelated or restricted data files")
            if any("acceptance-cases" in name or "/tests/" in name for name in names):
                errors.append("ZIP contains developer test fixtures")
            if any(name.endswith(("mcp.json", ".mcp.json")) for name in names):
                errors.append("skills-only ZIP must not include MCP configuration")
            if plugin_root is not None:
                expected_names = {name for name, _ in _package_entries(plugin_root)}
                if set(names) != expected_names:
                    errors.append("ZIP members differ from the explicit plugin runtime allowlist")
            plugin_manifest: Any = None
            for name in names:
                if name.endswith(".json"):
                    try:
                        parsed = json.loads(archive.read(name))
                        if name == "plugin.json":
                            plugin_manifest = parsed
                    except (json.JSONDecodeError, KeyError) as exc:
                        errors.append(f"invalid JSON resource {name}: {exc}")
                if name.endswith(".md"):
                    try:
                        text = archive.read(name).decode("utf-8")
                    except (UnicodeDecodeError, KeyError) as exc:
                        errors.append(f"invalid Markdown resource {name}: {exc}")
                        continue
                    if "[[" in text and "]]" in text:
                        errors.append(f"unresolved BHF module-reference syntax in ZIP resource: {name}")
                    errors.extend(_markdown_text_errors(text, name, set(names)))

            version = ""
            if "VERSION" in names:
                try:
                    version = archive.read("VERSION").decode("utf-8").strip()
                except UnicodeDecodeError:
                    errors.append("VERSION must be UTF-8 text")
                if not SEMVER_RE.fullmatch(version):
                    errors.append("VERSION must contain SemVer MAJOR.MINOR.PATCH")
            if "plugin.json" in names:
                errors.extend(_plugin_manifest_errors(plugin_manifest, version))

            if SKILL_REL.as_posix() in names:
                try:
                    skill_text = archive.read(SKILL_REL.as_posix()).decode("utf-8")
                except UnicodeDecodeError:
                    errors.append(f"{SKILL_REL.as_posix()} must be UTF-8 text")
                else:
                    errors.extend(_skill_frontmatter_errors(skill_text))

            if "ATTRIBUTION.md" in names:
                try:
                    attribution = archive.read("ATTRIBUTION.md").decode("utf-8").lower()
                except UnicodeDecodeError:
                    errors.append("ATTRIBUTION.md must be UTF-8 text")
                else:
                    errors.extend(_attribution_errors(attribution))
            if "LICENSE-CONTENT" in names:
                try:
                    content_license = archive.read("LICENSE-CONTENT").decode("utf-8").lower()
                except UnicodeDecodeError:
                    errors.append("LICENSE-CONTENT must be UTF-8 text")
                else:
                    errors.extend(_content_license_errors(content_license))

            if SOURCE_MANIFEST in names:
                try:
                    source_manifest = json.loads(archive.read(SOURCE_MANIFEST))
                except (json.JSONDecodeError, KeyError) as exc:
                    errors.append(f"invalid {SOURCE_MANIFEST}: {exc}")
                else:
                    errors.extend(_source_manifest_errors(source_manifest, archive))
                    if (
                        isinstance(source_manifest, dict)
                        and source_manifest.get("plugin_version") != version
                    ):
                        errors.append(f"{SOURCE_MANIFEST} plugin_version must match VERSION")
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"invalid ZIP archive: {exc}")
    return errors


def create_package(repo_root: Path = REPO_ROOT) -> tuple[Path, Path, Path]:
    repo_root = repo_root.resolve()
    plugin_root = repo_root / PLUGIN_REL
    version = _plugin_version(plugin_root)
    output_dir = repo_root / "dist/plugins"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"scripture-trails-{version}.zip"
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    manifest_path = output_dir / "scripture-trails-build-manifest.json"
    entries = _package_entries(plugin_root)

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name, path in entries:
            if path.is_symlink():
                raise BuildError(f"plugin runtime files must not be symlinks: {name}")
            data = path.read_bytes()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    archive_errors = validate_archive(archive_path, plugin_root)
    if archive_errors:
        raise BuildError("ZIP validation failed:\n  - " + "\n  - ".join(archive_errors))
    archive_bytes = archive_path.read_bytes()
    digest = _sha256(archive_bytes)
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    build_manifest = {
        "schema_version": 1,
        "plugin": "scripture-trails",
        "version": version,
        "archive": archive_path.name,
        "sha256": digest,
        "source_manifest_sha256": _sha256((plugin_root / SOURCE_MANIFEST).read_bytes()),
        "files": [
            {"path": name, "sha256": _sha256(path.read_bytes())}
            for name, path in entries
        ],
    }
    manifest_path.write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return archive_path, checksum_path, manifest_path


def _print_errors(errors: list[str]) -> int:
    if errors:
        print(f"FAIL — {len(errors)} Scripture Trails issue(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK — Scripture Trails workspace is valid.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the standalone Scripture Trails plugin.")
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument("--validate", action="store_true", help="validate selected sources and plugin resources")
    operations.add_argument("--build", action="store_true", help="generate plugin references and source manifest")
    operations.add_argument("--package", action="store_true", help="build resources and create a validated ZIP")
    operations.add_argument("--check", action="store_true", help="fail when committed generated resources are stale")
    operations.add_argument("--validate-zip", action="store_true", help="validate a built plugin ZIP and checksum")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--zip", type=Path, help="ZIP path for --validate-zip")
    args = parser.parse_args(argv)
    repo_root = args.root.resolve()

    try:
        if args.build:
            files = write_generated_resources(repo_root)
            errors = validate_workspace(repo_root)
            if errors:
                return _print_errors(errors)
            print("Generated " + ", ".join(files))
            print("OK — Scripture Trails workspace is valid.")
            return 0
        if args.package:
            write_generated_resources(repo_root)
            errors = validate_workspace(repo_root)
            if errors:
                return _print_errors(errors)
            archive, checksum, manifest = create_package(repo_root)
            print(f"Packaged {archive.relative_to(repo_root)}")
            print(f"Checksum {checksum.relative_to(repo_root)}")
            print(f"Build manifest {manifest.relative_to(repo_root)}")
            return 0
        if args.validate_zip:
            if args.zip:
                archive_path = args.zip if args.zip.is_absolute() else repo_root / args.zip
            else:
                version = _plugin_version(repo_root / PLUGIN_REL)
                archive_path = repo_root / "dist/plugins" / f"scripture-trails-{version}.zip"
            errors = validate_archive(archive_path, repo_root / PLUGIN_REL)
            checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
            if not checksum_path.is_file():
                errors.append(f"ZIP checksum is missing: {checksum_path}")
            else:
                expected_checksum = f"{_sha256(archive_path.read_bytes())}  {archive_path.name}\n"
                if checksum_path.read_text(encoding="utf-8") != expected_checksum:
                    errors.append(f"ZIP checksum does not match: {checksum_path}")
            if errors:
                return _print_errors(errors)
            print("OK — Scripture Trails ZIP and checksum are valid.")
            return 0
        errors = validate_workspace(repo_root)
        if args.check:
            errors.extend(check_generated_resources(repo_root))
        return _print_errors(errors)
    except (BuildError, OSError, ValueError, KeyError) as exc:
        print(f"FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
