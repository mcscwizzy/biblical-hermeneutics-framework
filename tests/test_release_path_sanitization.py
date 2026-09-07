from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATHS = (
    ROOT / "docs",
    ROOT / ".bhf-data",
    ROOT / ".BHF-GENERATION-RESUME.md",
)


def test_release_and_audit_artifacts_contain_no_machine_absolute_paths():
    home = "/" + "home/"
    users = "/" + "Users/"
    windows = "[A-Za-z]:" + r"\\Users\\"
    pattern = re.compile(
        rf"(?:{re.escape(home)}|{re.escape(users)})[A-Za-z0-9._-]+"
        rf"|{windows}"
    )
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
        if pattern.search(text):
            violations.append(str(path.relative_to(ROOT)))
    assert violations == []
