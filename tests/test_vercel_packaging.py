import fnmatch
import json
import os
from pathlib import Path
import subprocess
import sys

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.9/3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


def _vercelignore_entries() -> list[str]:
    return [
        line.strip()
        for line in (ROOT / ".vercelignore").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _is_explicitly_excluded(path: str) -> bool:
    normalized = path.strip("/")
    for entry in _vercelignore_entries():
        pattern = entry.rstrip("/")
        if pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        elif pattern.endswith("*"):
            if normalized.startswith(pattern[:-1]):
                return True
        elif normalized == pattern or normalized.startswith(pattern + "/"):
            return True
    return False


def _matches_function_exclude(path: str, pattern: str) -> bool:
    normalized = path.strip("/")
    patterns = pattern[1:-1].split(",") if pattern.startswith("{") and pattern.endswith("}") else [pattern]
    return any(fnmatch.fnmatchcase(normalized, item) for item in patterns)


def _vercel_python(command: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith("BHF_"):
            environment.pop(name)
    environment["VERCEL"] = "1"
    return subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_vercel_config_excludes_build_generated_package_tree():
    config = json.loads((ROOT / "vercel.json").read_text())
    function = config["functions"]["bhf_web/app.py"]
    exclude_pattern = function["excludeFiles"]
    assert isinstance(exclude_pattern, str)
    assert exclude_pattern == "{.bhf-data/**,build/**}"
    assert _is_explicitly_excluded(
        ".bhf-data/local-study-output.sqlite"
    )
    assert _matches_function_exclude(
        ".bhf-data/local-study-output.sqlite",
        exclude_pattern,
    )
    assert _matches_function_exclude(
        "build/lib/framework/canonical_library/__init__.py",
        exclude_pattern,
    )
    assert not _matches_function_exclude(
        "framework/canonical_library/data/ckl.sqlite",
        exclude_pattern,
    )
    assert not _matches_function_exclude(
        "framework/lexical/database/lexicon.sqlite.gz",
        exclude_pattern,
    )


def test_vercel_function_explicitly_includes_built_tyndale_database():
    config = json.loads((ROOT / "vercel.json").read_text())
    function = config["functions"]["bhf_web/app.py"]
    include_pattern = function["includeFiles"]
    patterns = (
        include_pattern[1:-1].split(",")
        if include_pattern.startswith("{") and include_pattern.endswith("}")
        else [include_pattern]
    )

    assert "framework/commentary/data/tyndale.sqlite" in patterns
    assert not _is_explicitly_excluded("framework/commentary/data/tyndale.sqlite")


def test_vercel_uv_sync_does_not_install_project_twice():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["tool"]["uv"]["package"] is False


def test_vercel_ignore_keeps_active_reader_resources_and_excludes_dev_inputs():
    required = {
        "bhf_web/app.py",
        "bhf_agent/data/asv_bible.json",
        "bhf_agent/data/kjv_bible.json",
        "framework/canonical_library/objects/books/genesis.json",
        "framework/lexical/database/lexicon.sqlite.gz",
        "framework/commentary/service.py",
        "bhf_web/routes/commentary.py",
        "bhf_web/static/commentary.js",
        "bhf_web/static/narrative-explorer.js",
    }
    assert all(not _is_explicitly_excluded(path) for path in required)

    excluded = {
        ".bhf-data/local-study-output.sqlite",
        "tools/ckl_coverage_report.py",
        "tests/test_vercel_packaging.py",
        "docs/architecture.md",
        "requirements-gui.txt",
    }
    assert all(_is_explicitly_excluded(path) for path in excluded)


def test_retired_reader_payload_and_python_sources_are_absent():
    assert not (ROOT / "bhf_agent/data/commentary-v1.2").exists()
    legacy_source = ROOT / "bhf_agent/chapter_commentary"
    if legacy_source.exists():
        assert not list(legacy_source.rglob("*.py"))
    assert (ROOT / "framework/commentary/service.py").is_file()
    assert (ROOT / "framework/commentary/importer.py").is_file()
    assert (ROOT / "framework/commentary/evidence.py").is_file()


def test_vercel_app_import_does_not_load_generation_or_report_modules():
    result = _vercel_python(
        "import sys\n"
        "from bhf_web.app import app\n"
        "assert app.title == 'BHF Bible Reader'\n"
        "assert not any(name == 'bhf_agent.chapter_commentary' or name.startswith('bhf_agent.chapter_commentary.') for name in sys.modules)\n"
        "assert not any(name == 'tools' or name.startswith('tools.') for name in sys.modules)\n"
    )

    assert result.returncode == 0, result.stderr
