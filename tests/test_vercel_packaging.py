import json
from pathlib import Path

from bhf_agent.chapter_commentary.storage import list_commentaries
from bhf_agent.genre import classify_genre
from bhf_agent.models import ReferenceContext
from bhf_agent.runtime_paths import packaged_commentary_storage_path, resolve_runtime_data_paths
from bhf_web.services.bhf_commentary import load_commentary_projection


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_COMMENTARY = ROOT / ".bhf-data" / "bhf-commentary-v1.1"
RUNTIME_FINGERPRINT = "9df456a3a22003587347cc0a78a9de5ca292e1d9554c4af3fc591207dd87e5db"


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


def test_vercel_config_targets_fastapi_entrypoint_and_candidate_exclusion():
    config = json.loads((ROOT / "vercel.json").read_text())
    function = config["functions"]["bhf_web/app.py"]
    assert function["excludeFiles"] == ".bhf-data/bhf-commentary-candidates/**"
    assert _is_explicitly_excluded(
        ".bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/batch-008/preflight-report.json"
    )


def test_vercel_ignore_preserves_required_runtime_paths():
    required = {
        "bhf_web/app.py",
        "bhf_agent/data/asv_bible.json",
        "bhf_agent/data/kjv_bible.json",
        "framework/canonical_library/objects/books/genesis.json",
        ".bhf-data/bhf-commentary-v1.1/commentary-v1.1-manifest.json",
        ".bhf-data/bhf-commentary-v1.1/deuteronomy_032.json",
        "bhf_web/static/style.css",
        "tools/commentary_health_report.py",
        "tools/ckl_coverage_report.py",
    }
    assert all(not _is_explicitly_excluded(path) for path in required)
    assert _is_explicitly_excluded("tests/test_vercel_packaging.py")
    assert _is_explicitly_excluded("docs/vercel-function-bundle-audit.md")
    assert _is_explicitly_excluded("requirements-gui.txt")


def test_certified_runtime_corpus_count_and_fingerprint_are_unchanged():
    assert len(list_commentaries(RUNTIME_COMMENTARY)) == 935
    manifest = json.loads(
        (RUNTIME_COMMENTARY / "commentary-v1.1-manifest.json").read_text()
    )
    assert manifest["chapter_count"] == 935
    assert manifest["corpus_fingerprint"] == RUNTIME_FINGERPRINT


def test_all_production_genres_and_remediated_chapters_load_from_runtime_corpus():
    genre_references = {
        "Torah": ("Deuteronomy", 32),
        "narrative": ("Joshua", 1),
        "poetry": ("Psalms", 119),
        "wisdom literature": ("Proverbs", 1),
        "prophecy": ("Isaiah", 40),
        "Gospel": ("Matthew", 1),
        "epistle": ("Romans", 1),
        "apocalyptic": ("Revelation", 1),
    }
    for expected_genre, (book, chapter) in genre_references.items():
        assert classify_genre(ReferenceContext(book=book)).primary_genre == expected_genre
        projection = load_commentary_projection(RUNTIME_COMMENTARY, book, chapter)
        assert projection is not None
        assert projection["release"] == "commentary-v1.1"
        assert projection["commentary"]

    for book, chapter in (
        ("Deuteronomy", 32),
        ("Numbers", 6),
        ("Isaiah", 40),
        ("Psalms", 119),
    ):
        assert load_commentary_projection(RUNTIME_COMMENTARY, book, chapter) is not None


def test_vercel_runtime_never_resolves_commentary_candidates():
    paths = resolve_runtime_data_paths({"VERCEL": "1"})
    assert paths.bhf_commentary_storage_path == packaged_commentary_storage_path()
    assert "bhf-commentary-candidates" not in str(paths.bhf_commentary_storage_path)
    assert paths.bhf_commentary_storage_path.name == "bhf-commentary-v1.1"
