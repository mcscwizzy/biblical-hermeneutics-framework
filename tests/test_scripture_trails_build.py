"""Deterministic checks for the standalone Scripture Trails package."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_scripture_trails.py"
PLUGIN_REL = Path("plugins/scripture-trails")
REQUIRED_CORE = {
    "core.core-framework",
    "core.genre-awareness",
    "core.original-audience",
    "core.observe-interpret-apply",
    "core.intertextuality",
    "core.epistemic-humility",
    "core.anti-hallucination",
}


def run_builder(
    root: Path,
    operation: str,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    extra_args = extra_args or []
    return subprocess.run(
        [sys.executable, str(BUILDER), f"--{operation}", "--root", str(root), *extra_args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def copy_workspace(destination: Path) -> Path:
    """Copy only the framework module trees and plugin authoring workspace."""
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "LICENSE-CONTENT", destination / "LICENSE-CONTENT")
    for directory in ("core", "genres", "context", "language", "books"):
        source = ROOT / "framework" / directory
        target = destination / "framework" / directory
        shutil.copytree(source, target)
    shutil.copytree(ROOT / PLUGIN_REL, destination / PLUGIN_REL)
    return destination


def test_validate_command_accepts_the_scripture_trails_workspace() -> None:
    result = run_builder(ROOT, "validate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "valid" in result.stdout.lower()


def test_build_tracks_required_modules_versions_paths_hashes_and_outputs(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "build")
    assert result.returncode == 0, result.stdout + result.stderr

    plugin = workspace / PLUGIN_REL
    manifest = json.loads((plugin / "source-module-manifest.json").read_text())
    sources = {entry["id"]: entry for entry in manifest["sources"]}
    assert REQUIRED_CORE <= sources.keys()
    core = sources["core.intertextuality"]
    assert core["version"] == "0.2.0"
    assert core["source_path"] == "framework/core/04-intertextuality.md"
    source_bytes = (workspace / core["source_path"]).read_bytes()
    assert core["sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert "skills/explore-scripture/references/intertextuality.md" in core["outputs"]


def test_validation_rejects_a_dependency_not_assigned_to_a_reference(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    config_path = workspace / PLUGIN_REL / "config/module-selection.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["module_outputs"]["references/genre-and-language.md"].remove("genre.narrative")
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "dependency modules must be explicitly assigned" in result.stdout + result.stderr


def test_validation_cannot_omit_a_foundational_module(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    config_path = workspace / PLUGIN_REL / "config/module-selection.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["module_outputs"].pop("references/intertextuality.md")
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "required foundational modules are not assigned" in result.stdout + result.stderr


def test_validation_rejects_paths_that_escape_the_reference_root(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    config_path = workspace / PLUGIN_REL / "config/module-selection.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["module_outputs"]["../outside.md"] = ["core.core-framework"]
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "unsafe relative path" in result.stdout + result.stderr


def test_validation_rejects_a_module_symlink_outside_the_framework_root(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    source = workspace / "framework/core/00-core-framework.md"
    external = workspace / "outside-framework-module.md"
    shutil.copy2(source, external)
    source.unlink()
    source.symlink_to(external)

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "symlink" in result.stdout.lower() + result.stderr.lower()


def test_validation_rejects_an_unresolved_source_module_reference(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    source = workspace / "framework/core/00-core-framework.md"
    content = source.read_text(encoding="utf-8")
    assert "[[core.genre-awareness]]" in content
    source.write_text(
        content.replace("[[core.genre-awareness]]", "[[core.not-in-framework]]", 1),
        encoding="utf-8",
    )

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "unresolved internal module reference" in result.stdout + result.stderr


def test_build_is_deterministic_for_unchanged_inputs(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    first = run_builder(workspace, "build")
    assert first.returncode == 0, first.stdout + first.stderr
    plugin = workspace / PLUGIN_REL
    generated = sorted(plugin.glob("skills/explore-scripture/references/*.md"))
    generated.append(plugin / "source-module-manifest.json")
    first_bytes = {path.relative_to(plugin): path.read_bytes() for path in generated}

    second = run_builder(workspace, "build")
    assert second.returncode == 0, second.stdout + second.stderr
    assert first_bytes == {
        path.relative_to(plugin): path.read_bytes() for path in generated
    }


def test_check_names_affected_reference_when_a_source_changes(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    built = run_builder(workspace, "build")
    assert built.returncode == 0, built.stdout + built.stderr
    source = workspace / "framework/core/04-intertextuality.md"
    content = source.read_text(encoding="utf-8")
    assert "This module makes you notice" in content
    source.write_text(
        content.replace("This module makes you notice", "That module makes you notice", 1),
        encoding="utf-8",
    )

    checked = run_builder(workspace, "check")
    assert checked.returncode != 0
    assert "references/intertextuality.md" in checked.stdout + checked.stderr


def test_validation_rejects_a_manifest_missing_its_plugin_name(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    plugin_json = workspace / PLUGIN_REL / "plugin.json"
    manifest = json.loads(plugin_json.read_text(encoding="utf-8"))
    manifest.pop("name", None)
    plugin_json.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "name" in result.stdout.lower() + result.stderr.lower()


def test_validation_rejects_unknown_portable_manifest_properties(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    plugin_json = workspace / PLUGIN_REL / "plugin.json"
    manifest = json.loads(plugin_json.read_text(encoding="utf-8"))
    manifest["unexpected"] = True
    plugin_json.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "unknown plugin.json property" in result.stdout + result.stderr


def test_validation_requires_submission_ready_skill_listing_text(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    plugin_json = workspace / PLUGIN_REL / "plugin.json"
    manifest = json.loads(plugin_json.read_text(encoding="utf-8"))
    del manifest["extensions"]["com.openai"]["interface"]["longDescription"]
    plugin_json.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "longDescription is required" in result.stdout + result.stderr


def test_validation_rejects_invalid_skill_frontmatter(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    skill_path = workspace / PLUGIN_REL / "skills/explore-scripture/SKILL.md"
    skill_path.write_text("# Missing frontmatter\n", encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "missing YAML frontmatter" in result.stdout + result.stderr


def test_validation_rejects_stale_or_malformed_source_manifest(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    manifest_path = workspace / PLUGIN_REL / "source-module-manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "source-module-manifest.json" in result.stdout + result.stderr


def test_check_reports_corrupt_manifest_without_traceback(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    manifest_path = workspace / PLUGIN_REL / "source-module-manifest.json"
    manifest_path.write_text('{"sources": null}\n', encoding="utf-8")

    result = run_builder(workspace, "check")
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "source-module-manifest.json" in output
    assert "Traceback" not in output


def test_validation_requires_cc_by_attribution_and_license_text(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    attribution_path = workspace / PLUGIN_REL / "ATTRIBUTION.md"
    license_path = workspace / PLUGIN_REL / "LICENSE-CONTENT"
    attribution_path.write_text("No source attribution.\n", encoding="utf-8")
    license_path.write_text("No license text.\n", encoding="utf-8")

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "ATTRIBUTION.md" in output
    assert "LICENSE-CONTENT" in output


def test_validation_requires_attribution_in_the_runtime_package(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    (workspace / PLUGIN_REL / "ATTRIBUTION.md").unlink()

    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "ATTRIBUTION.md" in result.stdout + result.stderr


def test_package_has_a_portable_root_and_excludes_development_fixtures(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        assert "plugin.json" in names
        assert "skills/explore-scripture/SKILL.md" in names
        assert "skills/explore-scripture/references/trail-selection.md" in names
        assert not any(name.startswith("scripture-trails/") for name in names)
        assert not any("acceptance-cases" in name or "/tests/" in name for name in names)
        assert not any(name.endswith((".sqlite", ".sqlite3", ".db")) for name in names)
        assert "config/module-selection.yml" not in names


def test_all_packaged_skill_references_resolve_inside_the_zip(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        skill = package.read("skills/explore-scripture/SKILL.md").decode("utf-8")
        reference_links = [
            match.group(1)
            for match in re.finditer(
                r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)", skill
            )
        ]
        for link in reference_links:
            target = Path("skills/explore-scripture") / link
            assert target.as_posix() in names


def test_zip_validation_rejects_a_broken_packaged_markdown_reference(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    packaged = run_builder(workspace, "package")
    assert packaged.returncode == 0, packaged.stdout + packaged.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    broken_archive = tmp_path / "broken-plugin.zip"
    with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(
        broken_archive, "w", compression=zipfile.ZIP_DEFLATED
    ) as broken:
        for name in source.namelist():
            data = source.read(name)
            if name.endswith("references/trail-selection.md"):
                text = data.decode("utf-8")
                assert "(intertextuality.md)" in text
                data = text.replace("(intertextuality.md)", "(missing-reference.md)", 1).encode("utf-8")
            broken.writestr(name, data)
    broken_digest = hashlib.sha256(broken_archive.read_bytes()).hexdigest()
    broken_archive.with_suffix(".zip.sha256").write_text(
        f"{broken_digest}  {broken_archive.name}\n", encoding="utf-8"
    )

    result = run_builder(
        workspace,
        "validate-zip",
        ["--zip", str(broken_archive)],
    )
    assert result.returncode != 0
    assert "Markdown link does not resolve" in result.stdout + result.stderr


def test_zip_validation_checks_manifest_and_skill_frontmatter_content(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    packaged = run_builder(workspace, "package")
    assert packaged.returncode == 0, packaged.stdout + packaged.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    invalid_cases = [
        ("plugin.json", b"{}\n", "plugin.json"),
        ("source-module-manifest.json", b"{}\n", "source-module-manifest.json"),
        ("skills/explore-scripture/SKILL.md", b"# No frontmatter\n", "frontmatter"),
        ("ATTRIBUTION.md", b"\n", "attribution"),
        ("LICENSE-CONTENT", b"\n", "license"),
    ]
    for index, (member, replacement, expected_error) in enumerate(invalid_cases):
        invalid_archive = tmp_path / f"invalid-plugin-{index}.zip"
        with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(
            invalid_archive, "w", compression=zipfile.ZIP_DEFLATED
        ) as invalid:
            for name in source.namelist():
                invalid.writestr(name, replacement if name == member else source.read(name))
        digest = hashlib.sha256(invalid_archive.read_bytes()).hexdigest()
        invalid_archive.with_suffix(".zip.sha256").write_text(
            f"{digest}  {invalid_archive.name}\n", encoding="utf-8"
        )
        result = run_builder(workspace, "validate-zip", ["--zip", str(invalid_archive)])
        assert result.returncode != 0, f"archive with invalid {member} was accepted"
        assert expected_error.lower() in (result.stdout + result.stderr).lower()


def test_package_bytes_and_checksum_are_reproducible(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    first = run_builder(workspace, "package")
    assert first.returncode == 0, first.stdout + first.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    first_zip = archive.read_bytes()
    first_digest = hashlib.sha256(first_zip).hexdigest()

    second = run_builder(workspace, "package")
    assert second.returncode == 0, second.stdout + second.stderr
    assert archive.read_bytes() == first_zip
    sidecar = archive.with_suffix(archive.suffix + ".sha256")
    assert sidecar.read_text(encoding="utf-8").startswith(first_digest + "  ")
    validated = run_builder(workspace, "validate-zip")
    assert validated.returncode == 0, validated.stdout + validated.stderr


def test_package_allowlist_excludes_unrelated_local_files(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    plugin = workspace / PLUGIN_REL
    (plugin / "accidental-study.sqlite").write_bytes(b"private test data")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    with zipfile.ZipFile(archive) as package:
        assert "accidental-study.sqlite" not in package.namelist()


def test_package_excludes_unconfigured_reference_markdown(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    references = workspace / PLUGIN_REL / "skills/explore-scripture/references"
    (references / "unconfigured-note.md").write_text("developer scratch\n", encoding="utf-8")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    with zipfile.ZipFile(archive) as package:
        assert "skills/explore-scripture/references/unconfigured-note.md" not in package.namelist()


def test_removed_generated_reference_is_reported_cleaned_and_not_packaged(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    plugin = workspace / PLUGIN_REL
    config_path = plugin / "config/module-selection.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["module_outputs"].pop("references/passage-guides.md")
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    skill_path = plugin / "skills/explore-scripture/SKILL.md"
    skill = skill_path.read_text(encoding="utf-8")
    skill = skill.replace(
        "- Consult [Selected Book Guides](references/passage-guides.md) when the passage\n  belongs to a book covered there.\n",
        "",
    )
    skill_path.write_text(skill, encoding="utf-8")

    stale = run_builder(workspace, "check")
    assert stale.returncode != 0
    assert "passage-guides.md" in stale.stdout + stale.stderr

    built = run_builder(workspace, "build")
    assert built.returncode == 0, built.stdout + built.stderr
    assert not (plugin / "skills/explore-scripture/references/passage-guides.md").exists()
    manifest = json.loads((plugin / "source-module-manifest.json").read_text(encoding="utf-8"))
    assert not any(source["id"].startswith("book.") for source in manifest["sources"])

    packaged = run_builder(workspace, "package")
    assert packaged.returncode == 0, packaged.stdout + packaged.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    with zipfile.ZipFile(archive) as package:
        assert "skills/explore-scripture/references/passage-guides.md" not in package.namelist()


def test_zip_contains_no_runtime_bhf_or_service_dependency(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        assert not any(name.endswith(("mcp.json", ".mcp.json")) for name in names)
        text_files = [
            package.read(name).decode("utf-8")
            for name in names
            if name.endswith((".md", ".json", ".txt"))
        ]
    contents = "\n".join(text_files).lower()
    assert '"mcpservers"' not in contents
    assert "api_key" not in contents
    assert "oauth" not in contents
    assert "connect to the bhf" not in contents
    assert "/api/" not in contents


def test_acceptance_cases_cover_required_topics_and_negative_evaluations() -> None:
    cases_path = ROOT / PLUGIN_REL / "tests/acceptance-cases.yml"
    cases = yaml.safe_load(cases_path.read_text(encoding="utf-8"))
    names = {case["id"] for case in cases["cases"]}
    assert {
        "psalm-22-crucifixion",
        "micah-historical-setting",
        "genesis-john-prologue",
        "jonah-name-and-sign",
        "psalm-82-divine-council",
        "multi-turn-rabbit-trail",
        "negative-fabricated-sources",
        "negative-exaggerated-word-study",
        "negative-unsupported-archaeology",
        "negative-forced-cross-reference",
        "negative-doctrinal-overstatement",
    } <= names
    assert all(case.get("expected") for case in cases["cases"])


def test_source_manifest_and_tests_are_not_packaged_as_runtime_instructions(
    tmp_path: Path,
) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        assert "source-module-manifest.json" in names
        assert not any("tests/" in name for name in names)
        skill = package.read("skills/explore-scripture/SKILL.md").decode("utf-8")
    assert "references/interpretive-method.md" in skill
    assert "references/evidence-and-boundaries.md" in skill
    assert "references/trail-selection.md" in skill


def test_release_icons_are_present_and_manifest_paths_resolve(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    archive = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read("plugin.json"))
        interface = manifest["extensions"]["com.openai"]["interface"]
        for key in ("logo", "composerIcon"):
            assert interface[key].startswith("./assets/")
            asset = interface[key][2:]
            assert asset in package.namelist()
            assert package.read(asset).startswith(b"\x89PNG\r\n\x1a\n")


def test_release_icons_reject_missing_and_corrupt_assets(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    icon = workspace / PLUGIN_REL / "assets/composer-icon.png"
    icon.write_bytes(b"not an image")
    invalid = run_builder(workspace, "validate")
    assert invalid.returncode != 0
    assert "invalid PNG header" in invalid.stdout + invalid.stderr

    icon.unlink()
    missing = run_builder(workspace, "validate")
    assert missing.returncode != 0
    assert "assets/composer-icon.png" in missing.stdout + missing.stderr


def test_release_manifest_requires_both_icon_paths(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    manifest_file = workspace / PLUGIN_REL / "plugin.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["extensions"]["com.openai"]["interface"].pop("composerIcon")
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    result = run_builder(workspace, "validate")
    assert result.returncode != 0
    assert "composerIcon" in result.stdout + result.stderr


def test_release_zip_validation_rejects_tampered_icon(tmp_path: Path) -> None:
    workspace = copy_workspace(tmp_path / "workspace")
    result = run_builder(workspace, "package")
    assert result.returncode == 0, result.stdout + result.stderr
    original = next((workspace / "dist/plugins").glob("scripture-trails-*.zip"))
    broken = tmp_path / "tampered-icon.zip"
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(broken, "w") as target:
        for name in source.namelist():
            data = b"tampered" if name == "assets/logo.png" else source.read(name)
            target.writestr(name, data)
    digest = hashlib.sha256(broken.read_bytes()).hexdigest()
    broken.with_suffix(".zip.sha256").write_text(
        f"{digest}  {broken.name}\n", encoding="utf-8"
    )
    checked = run_builder(workspace, "validate-zip", ["--zip", str(broken)])
    assert checked.returncode != 0
    assert "invalid PNG header" in checked.stdout + checked.stderr
