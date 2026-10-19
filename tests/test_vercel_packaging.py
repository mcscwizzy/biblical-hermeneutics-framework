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
    assert exclude_pattern == "{.bhf-data/bhf-commentary-candidates/**,build/**}"
    assert _is_explicitly_excluded(
        ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-008/preflight-report.json"
    )
    assert _matches_function_exclude(
        ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-008/preflight-report.json",
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
        ".bhf-data/bhf-commentary-v1.1/deuteronomy_032.json",
        "bhf_agent/chapter_commentary/models.py",
        "tools/commentary_health_report.py",
        "tools/ckl_coverage_report.py",
        "tests/test_vercel_packaging.py",
        "docs/vercel-function-bundle-audit.md",
        "requirements-gui.txt",
    }
    assert all(_is_explicitly_excluded(path) for path in excluded)


def test_generated_v12_package_data_is_not_declared_or_present():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert "data/commentary-v1.2/" not in pyproject
    assert not (ROOT / "bhf_agent/data/commentary-v1.2").exists()


def test_vercel_app_import_does_not_load_generation_or_report_modules():
    result = _vercel_python(
        "import sys\n"
        "from bhf_web.app import app\n"
        "assert app.title == 'BHF Bible Reader'\n"
        "assert not any(name == 'bhf_agent.chapter_commentary' or name.startswith('bhf_agent.chapter_commentary.') for name in sys.modules)\n"
        "assert not any(name == 'tools' or name.startswith('tools.') for name in sys.modules)\n"
    )

    assert result.returncode == 0, result.stderr
