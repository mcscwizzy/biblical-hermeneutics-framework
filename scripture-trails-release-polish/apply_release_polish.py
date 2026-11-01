#!/usr/bin/env python3
"""Apply Scripture Trails v0.1.1 pre-publication polish to a BHF checkout.

Run from anywhere:
    python /path/to/apply_release_polish.py /path/to/biblical-hermeneutics-framework

Requires the adjacent artwork/ files, Python and the existing BHF build dependencies.
This is a source-code patch generator, not a plugin or a published release.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent


def replace_once(source: str, old: str, new: str, label: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise RuntimeError(f"Expected exactly one {label} anchor; found {occurrences}. Stop and inspect the changed upstream file.")
    return source.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python apply_release_polish.py /path/to/bhf-repo")
    root = Path(sys.argv[1]).resolve()
    plugin = root / "plugins/scripture-trails"
    if not (root / "tools/build_scripture_trails.py").is_file() or not (plugin / "plugin.json").is_file():
        raise SystemExit("Not a BHF checkout with Scripture Trails pipeline; refusing to change files.")
    version_path = plugin / "VERSION"
    if version_path.read_text().strip() != "0.1.0":
        raise SystemExit("Expected Scripture Trails VERSION 0.1.0. Refusing an uncertain upgrade.")

    builder_path = root / "tools/build_scripture_trails.py"
    builder = builder_path.read_text(encoding="utf-8")
    builder = replace_once(builder, "import zipfile\nfrom pathlib", "import zipfile\nimport struct\nfrom pathlib", "builder import")
    builder = replace_once(
        builder,
        'SKILL_REL = Path("skills/explore-scripture/SKILL.md")',
        'SKILL_REL = Path("skills/explore-scripture/SKILL.md")\nASSETS = {"logo": "assets/logo.png", "composerIcon": "assets/composer-icon.png"}',
        "asset constant",
    )
    builder = replace_once(
        builder,
        '        SKILL_REL.as_posix(),\n    ]\n    candidates:',
        '        SKILL_REL.as_posix(),\n        *sorted(ASSETS.values()),\n    ]\n    candidates:',
        "package allowlist",
    )
    builder = replace_once(
        builder,
        'def _plugin_manifest_errors(plugin_manifest: Any, version: str) -> list[str]:',
        '''def _png_asset_errors(name: str, data: bytes) -> list[str]:
    """Check image signatures, square pixel dimensions, and submission size limits."""
    if len(data) > 5 * 1024 * 1024:
        return [f"{name}: PNG icon is larger than 5 MiB"]
    if len(data) < 24 or not data.startswith(b"\\x89PNG\\r\\n\\x1a\\n") or data[12:16] != b"IHDR":
        return [f"{name}: invalid PNG header"]
    width, height = struct.unpack(">II", data[16:24])
    if width != height or width < 48 or width > 4096:
        return [f"{name}: PNG must be square and between 48 and 4096 pixels"]
    return []


def _plugin_manifest_errors(plugin_manifest: Any, version: str) -> list[str]:''',
        "PNG validation",
    )
    builder = replace_once(
        builder,
        '    if "mcpServers" in plugin_manifest or "dependencies" in plugin_manifest:',
        '''        for field, asset in ASSETS.items():
            if interface.get(field) != "./" + asset:
                errors.append(f"plugin.json interface {field} must be './{asset}'")
    if "mcpServers" in plugin_manifest or "dependencies" in plugin_manifest:''',
        "manifest asset paths",
    )
    builder = replace_once(
        builder,
        '    for name, path in runtime_files:\n        if path.is_symlink():',
        '''    for name, path in runtime_files:
        if name in ASSETS.values():
            errors.extend(_png_asset_errors(name, path.read_bytes()))
        if path.is_symlink():''',
        "workspace image validation",
    )
    builder = replace_once(
        builder,
        '                SKILL_REL.as_posix(),\n            }\n            missing_files',
        '                SKILL_REL.as_posix(),\n                *ASSETS.values(),\n            }\n            missing_files',
        "ZIP required images",
    )
    builder = replace_once(
        builder,
        '            if SKILL_REL.as_posix() in names:\n',
        '''            for asset in ASSETS.values():
                if asset in names:
                    errors.extend(_png_asset_errors(asset, archive.read(asset)))

            if SKILL_REL.as_posix() in names:
''',
        "ZIP image validation",
    )

    manifest_path = plugin / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    interface = manifest["extensions"]["com.openai"]["interface"]
    manifest["version"] = "0.1.1"
    interface["logo"] = "./assets/logo.png"
    interface["composerIcon"] = "./assets/composer-icon.png"
    interface["shortDescription"] = "Explore Scripture in context"
    interface["longDescription"] = (
        "Explore Scripture through clear, conversational answers grounded in literary, "
        "historical, and cultural context. Follow meaningful connections between passages, "
        "examine original-language insights with care, and discover rabbit trails worth pursuing. "
        "Scripture Trails distinguishes textual evidence from interpretation, acknowledges "
        "uncertainty, and does not require a separate Bible study service."
    )
    interface["defaultPrompt"] = [
        "Why did Jesus quote Psalm 22 on the cross?",
        "How does John 1 connect to Genesis 1?",
        "Take me down a meaningful rabbit trail from Jonah.",
    ]
    readme_path = plugin / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = readme.replace("scripture-trails-0.1.0.zip", "scripture-trails-0.1.1.zip")
    readme = replace_once(
        readme,
        "The ZIP has `plugin.json` at its archive root.",
        '''The ZIP also contains two square, self-contained PNG branding assets:
`assets/logo.png` for the listing and `assets/composer-icon.png` for the composer.
The manifest uses the required `./assets/` relative paths. The builder explicitly
allowlists the files and validates their dimensions, size, and PNG signatures
in both the workspace and release ZIP. The icon images are source-controlled,
not generated during each build.

The ZIP has `plugin.json` at its archive root.''',
        "README packaging section",
    )
    readme = replace_once(
        readme,
        "## Prepare a publication release\n",
        '''## Prepare a publication release

The plugin has release-ready artwork and draft listing text, but publication
requires **live conversational tests**, publisher verification, and review.
Confirm `developerName` against the actual verified developer identity before
submitting. Do not invent website/support/privacy URLs or screenshots, or
claim that the plugin includes an online CKL research database. Skills-only
packages do not require all four hosted listing URLs under current rules.

''',
        "README publishing section",
    )
    tests_path = root / "tests/test_scripture_trails_build.py"
    tests = tests_path.read_text(encoding="utf-8")
    if "test_release_icons_are_present_and_manifest_paths_resolve" in tests:
        raise SystemExit("Publication icon tests already exist; refusing duplicate application.")
    tests += '''

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
            assert package.read(asset).startswith(b"\\x89PNG\\r\\n\\x1a\\n")


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
        f"{digest}  {broken.name}\\n", encoding="utf-8"
    )
    checked = run_builder(workspace, "validate-zip", ["--zip", str(broken)])
    assert checked.returncode != 0
    assert "invalid PNG header" in checked.stdout + checked.stderr
'''
    release_checklist = '''# Scripture Trails v0.1.1 — Publication checklist

This is a skills-only package; no BHF web services, API, CKL runtime,
account connection, or separate AI model is needed.

## Release gate

- [ ] Verify `developerName` matches the actual OpenAI verified publisher identity.
- [ ] Confirm the plugin's name, description, starter prompts, and two image assets.
- [ ] Run `python tools/validate.py framework/`.
- [ ] Run `python -m pytest -q tests/test_scripture_trails_build.py`.
- [ ] Run `python tools/build_scripture_trails.py --check`.
- [ ] Run `python tools/build_scripture_trails.py --package`.
- [ ] Run `python tools/build_scripture_trails.py --validate-zip`.
- [ ] Confirm the release ZIP includes `assets/logo.png` and `assets/composer-icon.png`.
- [ ] Install plugin for local testing; complete manual acceptance-cases.yml.
- [ ] Verify multi-turn rabbit-trail continuity, source honesty, and no forced connections.
- [ ] Review any missing dependencies and the full repository CI gate.
- [ ] Verify website/support/privacy/terms fields only where requested and backed by published pages.
- [ ] Complete verified developer setup and OpenAI submission/review before publishing.

This checklist is for maintainers; it is not included in the runtime ZIP.
'''
    # Only now that all anchors validated, mutate the checked-out source.
    assets = plugin / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copy2(PACKAGE / "artwork/logo.png", assets / "logo.png")
    shutil.copy2(PACKAGE / "artwork/composer-icon.png", assets / "composer-icon.png")
    builder_path.write_text(builder, encoding="utf-8")
    tests_path.write_text(tests, encoding="utf-8")
    readme_path.write_text(readme, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    version_path.write_text("0.1.1\n", encoding="utf-8")
    (plugin / "RELEASE_CHECKLIST.md").write_text(release_checklist, encoding="utf-8")
    print("Applied publication polish to", root)
    print("Now running the builder to refresh the provenance manifest and generated content.")
    subprocess.run([sys.executable, str(builder_path), "--build"], cwd=root, check=True)
    subprocess.run([sys.executable, str(builder_path), "--check"], cwd=root, check=True)
    subprocess.run([sys.executable, str(builder_path), "--package"], cwd=root, check=True)
    subprocess.run([sys.executable, str(builder_path), "--validate-zip"], cwd=root, check=True)
    print("Check tests and commit on a feature branch:")
    print("  python -m pytest -q tests/test_scripture_trails_build.py")
    print("  python tools/validate.py framework/")
    print("  git diff --check && git status --short")


if __name__ == "__main__":
    main()
