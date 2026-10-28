from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATHS = (
    ROOT / "docs",
    ROOT / ".bhf-data",
    ROOT / ".BHF-GENERATION-RESUME.md",
)


def test_source_urls_are_not_machine_paths():
    assert not machine_absolute_paths('"url": "https://example.org/home/bookDetails/7283"')
    assert machine_absolute_paths('"path": "/home/alice/project/file.json"')
    assert machine_absolute_paths('"path": "C:\\Users\\alice\\project"')
    assert machine_absolute_paths('https://example.org/home/bookDetails and /home/alice/private')


def machine_absolute_paths(text):
    home = "/" + "home/"
    users = "/" + "Users/"
    windows = "[A-Za-z]:" + r"\\Users\\"
    pattern = re.compile(
        rf"(?:{re.escape(home)}|{re.escape(users)})[A-Za-z0-9._-]+"
        rf"|{windows}"
    )
    return [
        match.group()
        for match in pattern.finditer(text)
        if not re.search(r"https?://[^\s/\"']+$", text[:match.start()])
    ]


def test_release_and_audit_artifacts_contain_no_machine_absolute_paths():
    violations = []
    paths = [path for path in AUDIT_PATHS if path.is_file()] + [
        child
        for root in AUDIT_PATHS
        if root.is_dir()
        for child in root.rglob("*")
        if child.is_file()
    ]
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if machine_absolute_paths(text):
            violations.append(str(path.relative_to(ROOT)))
    assert violations == []
