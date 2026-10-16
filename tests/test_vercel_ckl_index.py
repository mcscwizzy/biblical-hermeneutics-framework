from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.9/3.10 compatibility
    import tomli as tomllib

from framework.canonical_library import database_schema
from framework.canonical_library.repository import repository_config_from_env
from framework.canonical_library.sqlite_repository import SQLiteCanonicalRepository
from tests.canonical_library.helpers import make_object, write_library


def _package_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    package_root = tmp_path / "framework" / "canonical_library"
    package_root.mkdir(parents=True)
    (package_root / "repository.py").touch()
    root = package_root
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])

    import framework.canonical_library.repository as repository_module
    import bhf_web.services.narrative_explorer as narrative_module

    monkeypatch.setattr(repository_module, "__file__", str(package_root / "repository.py"))
    monkeypatch.setattr(
        narrative_module,
        "__file__",
        str(tmp_path / "bhf_web" / "services" / "narrative_explorer.py"),
    )
    return package_root, root


def _build_package_index(package_root: Path, source_root: Path) -> Path:
    from framework.canonical_library.vercel_build import build_vercel_ckl_index

    output = package_root / "data" / "ckl.sqlite"
    build_vercel_ckl_index(source_root=source_root, output_path=output)
    return output


def test_vercel_build_creates_and_verifies_index_from_source_root(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_library(source_root, [make_object("john", "book", "John", ["Gospel of John"])])
    output = tmp_path / "output" / "ckl.sqlite"

    repository_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "framework.canonical_library.vercel_build",
            "--source-root",
            str(source_root),
            "--output",
            str(output),
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert output.is_file()
    assert report["object_count"] == 1
    assert report["source_manifest_fingerprint"]
    assert report["source_inventory_signature"]


def test_vercel_index_stays_a_single_file_after_read_only_runtime_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_root, source_root = _package_layout(tmp_path, monkeypatch)
    output = _build_package_index(package_root, source_root)

    connection = sqlite3.connect(f"file:{output.resolve()}?mode=ro", uri=True)
    journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
    connection.close()
    repository = SQLiteCanonicalRepository(output, read_only=True)
    assert repository.get_by_id("john") is not None
    repository.close()

    assert journal_mode == "delete"
    assert sorted(path.name for path in output.parent.iterdir()) == [output.name]


def test_vercel_runtime_selects_read_only_sqlite_without_json_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_root, source_root = _package_layout(tmp_path, monkeypatch)
    output = _build_package_index(package_root, source_root)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BHF_CKL_BACKEND", raising=False)
    monkeypatch.delenv("BHF_CKL_DATABASE_PATH", raising=False)
    monkeypatch.delenv("BHF_CKL_ROOT", raising=False)
    monkeypatch.delenv("BHF_CKL_STALE_DATABASE_POLICY", raising=False)

    import bhf_web.services.narrative_explorer as narrative_module

    monkeypatch.setattr(
        narrative_module,
        "JsonCanonicalRepository",
        lambda **_kwargs: pytest.fail("JSON fallback used in indexed Vercel mode"),
    )
    import framework.canonical_library.json_repository as json_repository_module

    monkeypatch.setattr(
        json_repository_module,
        "JsonCanonicalRepository",
        lambda **_kwargs: pytest.fail("JSON fallback used by the Vercel repository factory"),
    )
    initial_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    library = narrative_module.NarrativeExplorerService._default_canonical_library()

    assert library.retrieve_by_id("john").object.id == "john"
    assert library.repository.__class__.__module__.endswith("sqlite_repository")
    assert library.repository.read_only is True
    assert int(library.repository._conn.execute("PRAGMA query_only").fetchone()[0]) == 1
    with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
        library.repository._conn.execute("UPDATE ckl_metadata SET value = 'mutated' WHERE key = 'object_count'")
    assert hashlib.sha256(output.read_bytes()).hexdigest() == initial_hash
    library.close()

    from framework.canonical_library.repository import load_canonical_repository

    runtime_repository = load_canonical_repository()
    assert runtime_repository.__class__.__module__.endswith("sqlite_repository")
    assert runtime_repository.read_only is True
    assert runtime_repository.get_by_id("john").id == "john"
    runtime_repository.close()


def test_vercel_runtime_fails_when_index_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package_root, _ = _package_layout(tmp_path, monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BHF_CKL_DATABASE_PATH", raising=False)
    monkeypatch.delenv("BHF_CKL_BACKEND", raising=False)

    import framework.canonical_library.database_builder as database_builder

    monkeypatch.setattr(
        database_builder,
        "build_database",
        lambda *_args, **_kwargs: pytest.fail("request-time CKL index rebuilding is forbidden"),
    )

    from bhf_web.services.narrative_explorer import NarrativeExplorerService

    with pytest.raises(FileNotFoundError, match="Vercel CKL SQLite index is missing"):
        NarrativeExplorerService._default_canonical_library()
    assert not (package_root / "data").exists()


def test_vercel_runtime_fails_when_index_is_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package_root, source_root = _package_layout(tmp_path, monkeypatch)
    _build_package_index(package_root, source_root)
    object_path = source_root / "objects" / "books" / "john.json"
    object_path.write_text(object_path.read_text(encoding="utf-8").replace("John", "John Updated"), encoding="utf-8")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BHF_CKL_BACKEND", raising=False)
    monkeypatch.delenv("BHF_CKL_DATABASE_PATH", raising=False)
    monkeypatch.delenv("BHF_CKL_ROOT", raising=False)
    monkeypatch.delenv("BHF_CKL_STALE_DATABASE_POLICY", raising=False)

    from bhf_web.services.narrative_explorer import NarrativeExplorerService

    with pytest.raises(RuntimeError, match="Vercel CKL index is stale"):
        NarrativeExplorerService._default_canonical_library()


def test_vercel_runtime_fails_on_incompatible_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package_root, source_root = _package_layout(tmp_path, monkeypatch)
    output = _build_package_index(package_root, source_root)
    with sqlite3.connect(output) as connection:
        connection.execute(
            "UPDATE ckl_metadata SET value = 'incompatible' WHERE key = 'database_schema_version'"
        )
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BHF_CKL_BACKEND", raising=False)
    monkeypatch.delenv("BHF_CKL_DATABASE_PATH", raising=False)
    monkeypatch.delenv("BHF_CKL_ROOT", raising=False)
    monkeypatch.delenv("BHF_CKL_STALE_DATABASE_POLICY", raising=False)

    from bhf_web.services.narrative_explorer import NarrativeExplorerService

    with pytest.raises(RuntimeError, match="schema version"):
        NarrativeExplorerService._default_canonical_library()


def test_vercel_runtime_fails_on_manifest_metadata_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_root, source_root = _package_layout(tmp_path, monkeypatch)
    output = _build_package_index(package_root, source_root)
    with sqlite3.connect(output) as connection:
        connection.execute(
            "UPDATE ckl_metadata SET value = 'wrong-manifest' "
            "WHERE key = 'source_manifest_fingerprint'"
        )
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BHF_CKL_BACKEND", raising=False)
    monkeypatch.delenv("BHF_CKL_DATABASE_PATH", raising=False)
    monkeypatch.delenv("BHF_CKL_ROOT", raising=False)
    monkeypatch.delenv("BHF_CKL_STALE_DATABASE_POLICY", raising=False)

    from bhf_web.services.narrative_explorer import NarrativeExplorerService

    with pytest.raises(RuntimeError, match="manifest fingerprint"):
        NarrativeExplorerService._default_canonical_library()


def test_vercel_runtime_rejects_backend_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _package_layout(tmp_path, monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("BHF_CKL_BACKEND", "json")

    with pytest.raises(ValueError, match="BHF_CKL_BACKEND"):
        repository_config_from_env()

    assert database_schema.CKL_DATABASE_SCHEMA_VERSION == "4"


def test_vercel_runtime_rejects_database_path_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _package_layout(tmp_path, monkeypatch)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BHF_CKL_BACKEND", raising=False)
    monkeypatch.setenv("BHF_CKL_DATABASE_PATH", str(tmp_path / "unbundled.sqlite"))

    with pytest.raises(ValueError, match="BHF_CKL_DATABASE_PATH"):
        repository_config_from_env()


def test_vercel_config_runs_source_build_and_includes_only_ckl_runtime_inputs() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    project_config = tomllib.loads((repository_root / "pyproject.toml").read_text(encoding="utf-8"))
    vercel_config = json.loads((repository_root / "vercel.json").read_text(encoding="utf-8"))
    ignore_patterns = (repository_root / ".vercelignore").read_text(encoding="utf-8").splitlines()

    assert project_config["tool"]["vercel"]["scripts"]["build"] == (
        "python -m framework.canonical_library.vercel_build"
    )
    includes = vercel_config["functions"]["bhf_web/app.py"]["includeFiles"]
    assert includes == "framework/canonical_library/**"
    assert isinstance(includes, str)
    assert ".bhf-data/**" in ignore_patterns
    assert ".env*" in ignore_patterns
    assert "local.config.json" in ignore_patterns
