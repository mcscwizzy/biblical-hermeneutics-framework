import ast
from pathlib import Path
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.9 and 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PACKAGES = ("bhf_web", "bhf_agent", "framework")
LOCAL_IMPORTS = set(PRODUCTION_PACKAGES)


def _dependency_names(values: list[str]) -> set[str]:
    return {
        re.split(r"[<>=!~;\[]", value, maxsplit=1)[0].strip().lower()
        for value in values
    }


def test_production_dependencies_are_declared_in_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    runtime = _dependency_names(project["dependencies"])

    assert {"fastapi", "jinja2", "python-multipart", "uvicorn"} <= runtime
    assert runtime.isdisjoint(
        {
            "httpx",
            "pytest",
            "pytest-xdist",
            "pyyaml",
            "requests",
            "selenium",
            "webdriver-manager",
        }
    )


def test_production_modules_have_no_undeclared_direct_third_party_imports():
    imported = set()
    for package in PRODUCTION_PACKAGES:
        for path in (ROOT / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.level == 0
                    and node.module
                ):
                    imported.add(node.module.split(".", 1)[0])

    third_party = imported - sys.stdlib_module_names - LOCAL_IMPORTS
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    runtime = _dependency_names(project["dependencies"])

    assert third_party <= runtime


def test_legacy_requirement_files_delegate_to_pyproject_extras():
    gui_requirements = (ROOT / "requirements-gui.txt").read_text(encoding="utf-8")
    tool_requirements = (ROOT / "tools" / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert "-e .[dev,gui]" in gui_requirements
    assert "-e .[dev,gui]" in tool_requirements
