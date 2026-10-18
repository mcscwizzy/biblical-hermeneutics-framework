from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from bhf_web.services.ckl_provider import VerifiedCKLProvider
from framework.canonical_library.database_builder import build_database, database_info
from framework.canonical_library.loader import CanonicalLibrary
from framework.canonical_library.repository import CKLRepositoryConfig
from framework.canonical_library.sqlite_repository import SQLiteCanonicalLibrary


def _write_identity_root(root: Path, name: str = "source.json") -> None:
    objects = root / "objects" / "books"
    objects.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps({
            "framework_version": "test",
            "schema_version": "test",
            "object_count": 1,
            "categories": {"books": 1},
        }),
        encoding="utf-8",
    )
    (objects / name).write_text('{"identity": "test"}', encoding="utf-8")


def _config(root: Path, *, backend: str = "json", database_path: Path | None = None):
    return CKLRepositoryConfig(
        backend=backend,
        database_path=str(database_path or root / "ckl.sqlite"),
        json_root=str(root),
        stale_database_policy="error",
        read_only=True,
    )


def test_concurrent_initialization_is_single_flight(tmp_path: Path) -> None:
    root = tmp_path / "ckl"
    _write_identity_root(root)
    config = _config(root)
    start = threading.Barrier(9)
    entered = threading.Event()
    release = threading.Event()
    load_count = 0
    load_lock = threading.Lock()
    library = object()

    def loader(_config):
        nonlocal load_count
        with load_lock:
            load_count += 1
        entered.set()
        assert release.wait(timeout=5), "test did not release the initializer"
        return library

    provider = VerifiedCKLProvider(
        config_provider=lambda: config,
        library_loader=loader,
    )

    def request_library():
        start.wait(timeout=5)
        return provider.get_library()

    with ThreadPoolExecutor(max_workers=8) as executor:
        requests = [executor.submit(request_library) for _ in range(8)]
        start.wait(timeout=5)
        assert entered.wait(timeout=5)
        with provider._condition:
            assert provider._condition.wait_for(
                lambda: provider._initialization_waiters == 7,
                timeout=5,
            )
        release.set()
        results = [request.result(timeout=5) for request in requests]

    assert all(result is library for result in results)
    assert load_count == 1
    assert provider.snapshot()["successful_initializations"] == 1
    assert provider.snapshot()["source_content_signature_computations"] == 1


def test_companion_and_explorer_share_the_same_initialization(tmp_path: Path) -> None:
    from bhf_web.services.companion_context import CompanionContextService
    from bhf_web.services.narrative_explorer import NarrativeExplorerService

    root = tmp_path / "ckl"
    _write_identity_root(root)
    start = threading.Barrier(3)
    entered = threading.Event()
    release = threading.Event()
    calls = 0

    class Library:
        objects_by_id = {}

        def retrieve_by_scripture_reference(self, _reference, *, limit, **_filters):
            return []

    library = Library()

    def loader(_config):
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(timeout=5)
        return library

    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root),
        library_loader=loader,
    )
    companion = CompanionContextService(
        study_db_path=tmp_path / "study.sqlite",
        commentary_db_path=tmp_path / "commentary.sqlite",
        canonical_library_provider=provider.get_library,
        word_study_service=object(),
        commentary_service=object(),
        canonical_narrator=object(),
        presentation_engine=object(),
    )
    explorer = NarrativeExplorerService(
        study_db_path=tmp_path / "study.sqlite",
        canonical_library_provider=provider.get_library,
    )

    def companion_lookup():
        start.wait(timeout=5)
        return companion._canonical_results("Genesis 2:8")

    def explorer_lookup():
        start.wait(timeout=5)
        return explorer._lookup_canonical("Genesis 2:8")

    with ThreadPoolExecutor(max_workers=2) as executor:
        companion_request = executor.submit(companion_lookup)
        explorer_request = executor.submit(explorer_lookup)
        start.wait(timeout=5)
        assert entered.wait(timeout=5)
        with provider._condition:
            assert provider._condition.wait_for(
                lambda: provider._initialization_waiters == 1,
                timeout=5,
            )
        release.set()
        assert companion_request.result(timeout=5) == []
        assert explorer_request.result(timeout=5).records == ()

    assert calls == 1
    assert companion._canonical_library is explorer._canonical_library is library


def test_source_and_configuration_changes_do_not_reuse_old_inventory(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    _write_identity_root(first_root)
    _write_identity_root(second_root)
    selected_config = [_config(first_root)]
    libraries = []

    def loader(_config):
        library = object()
        libraries.append(library)
        return library

    provider = VerifiedCKLProvider(
        config_provider=lambda: selected_config[0],
        library_loader=loader,
    )
    first = provider.get_library()
    selected_config[0] = _config(second_root)
    second = provider.get_library()
    assert second is not first

    selected_config[0] = _config(first_root)
    (first_root / "objects" / "books" / "changed.json").write_text(
        '{"identity": "changed"}',
        encoding="utf-8",
    )
    refreshed = provider.get_library()
    assert refreshed is not first

    selected_config[0] = _config(first_root, backend="sqlite", database_path=tmp_path / "index-a.sqlite")
    sqlite_a = provider.get_library()
    selected_config[0] = _config(first_root, backend="sqlite", database_path=tmp_path / "index-b.sqlite")
    sqlite_b = provider.get_library()
    assert sqlite_b is not sqlite_a
    assert provider.get_library() is sqlite_b
    assert len(libraries) == 5


def test_vercel_missing_sqlite_index_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "ckl"
    _write_identity_root(root)
    monkeypatch.setenv("VERCEL", "1")
    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(
            root,
            backend="sqlite",
            database_path=tmp_path / "missing.sqlite",
        ),
    )
    with pytest.raises(FileNotFoundError, match="Vercel CKL SQLite index is missing"):
        provider.get_library()
    assert provider.snapshot()["successful_initializations"] == 0
    assert provider.snapshot()["failed_initializations"] == 1


def test_rebuild_policy_never_builds_or_falls_back_during_provider_initialization(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ckl"
    _write_identity_root(root)
    database = tmp_path / "missing.sqlite"

    config = CKLRepositoryConfig(
        backend="sqlite",
        database_path=str(database),
        json_root=str(root),
        stale_database_policy="rebuild",
        read_only=True,
    )
    provider = VerifiedCKLProvider(config_provider=lambda: config)
    with pytest.raises(FileNotFoundError, match="canonical repository is unavailable"):
        provider.get_library()

    assert not database.exists()
    assert provider.snapshot()["repository_constructions"] == 0
    assert provider.snapshot()["successful_initializations"] == 0


def test_initialization_exception_propagates_and_is_retryable(tmp_path: Path) -> None:
    root = tmp_path / "ckl"
    _write_identity_root(root)
    calls = 0
    library = object()

    def loader(_config):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("integrity verification failed")
        return library

    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root),
        library_loader=loader,
    )

    with pytest.raises(RuntimeError, match="integrity verification failed"):
        provider.get_library()

    assert provider.get_library() is library
    assert calls == 2
    assert provider.snapshot()["successful_initializations"] == 1
    assert provider.snapshot()["failed_initializations"] == 1


def test_provider_reopens_for_a_new_application_lifecycle(tmp_path: Path) -> None:
    root = tmp_path / "ckl"
    _write_identity_root(root)
    calls = 0

    class Library:
        closed = False

        def close(self):
            self.closed = True

    libraries = []

    def loader(_config):
        nonlocal calls
        calls += 1
        library = Library()
        libraries.append(library)
        return library

    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root),
        library_loader=loader,
    )
    first = provider.get_library()
    provider.close()
    assert first.closed is True
    with pytest.raises(RuntimeError, match="provider is closed"):
        provider.get_library()

    provider.start()
    second = provider.get_library()
    assert second is not first
    assert second.closed is False
    assert calls == 2
    provider.close()


def test_consumers_reconsult_an_injected_provider_after_source_change(tmp_path: Path) -> None:
    from bhf_web.services.companion_context import CompanionContextService
    from bhf_web.services.narrative_explorer import NarrativeExplorerService

    class Library:
        def __init__(self, object_id: str) -> None:
            self.objects_by_id = {object_id: object()}
            self.object_id = object_id

        def retrieve_by_scripture_reference(self, _reference, *, limit, **_filters):
            return [self.object_id]

    selected = [Library("first")]
    provider = lambda: selected[0]
    companion = CompanionContextService(
        study_db_path=tmp_path / "study.sqlite",
        commentary_db_path=tmp_path / "commentary.sqlite",
        canonical_library_provider=provider,
        word_study_service=object(),
        commentary_service=object(),
        canonical_narrator=object(),
        presentation_engine=object(),
    )
    explorer = NarrativeExplorerService(
        study_db_path=tmp_path / "study.sqlite",
        canonical_library_provider=provider,
    )

    assert companion._canonical_results("Genesis 2:8") == ["first"]
    assert explorer._lookup_canonical("Genesis 2:8").records == ("first",)
    selected[0] = Library("second")
    assert companion._canonical_results("Genesis 2:8") == ["second"]
    assert explorer._lookup_canonical("Genesis 2:8").records == ("second",)


def test_verified_sqlite_library_supports_parallel_thread_local_reads(tmp_path: Path) -> None:
    from tests.canonical_library.helpers import make_object, write_library

    root = tmp_path / "ckl-source"
    write_library(root, [
        make_object("john", "book", "John", ["Gospel of John"]),
        make_object("genesis", "book", "Genesis", ["Book of Genesis"]),
    ])
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root, backend="sqlite", database_path=database),
    )
    library = provider.get_library()
    assert isinstance(library, SQLiteCanonicalLibrary)

    start = threading.Barrier(9)

    def read():
        start.wait(timeout=5)
        connection = library.repository._conn
        result = library.retrieve_by_id("john")
        return id(connection), result.object.id

    with ThreadPoolExecutor(max_workers=8) as executor:
        requests = [executor.submit(read) for _ in range(8)]
        start.wait(timeout=5)
        results = [request.result(timeout=5) for request in requests]

    assert {object_id for _, object_id in results} == {"john"}
    assert len({connection_id for connection_id, _ in results}) == 8
    provider.close()


def test_sqlite_inventory_fingerprint_is_revalidated_at_provider_startup(tmp_path: Path) -> None:
    import sqlite3

    from tests.canonical_library.helpers import make_object, write_library

    root = tmp_path / "ckl-source"
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    expected_fingerprint = CanonicalLibrary(root=root).load().inventory_fingerprint()
    assert database_info(database)["inventory_fingerprint"] == expected_fingerprint

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE ckl_metadata SET value = ? WHERE key = 'inventory_fingerprint'",
            ("0" * 64,),
        )

    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root, backend="sqlite", database_path=database),
    )
    with pytest.raises(RuntimeError, match="canonical repository is stale"):
        provider.get_library()

    snapshot = provider.snapshot()
    assert snapshot["source_inventory_fingerprint_computations"] == 1
    assert snapshot["inventory_fingerprint_comparisons"] == 1
    assert snapshot["successful_initializations"] == 0
    assert snapshot["failed_initializations"] == 1


def test_sqlite_inventory_fingerprint_mismatch_obeys_explicit_json_fallback(
    tmp_path: Path,
) -> None:
    import sqlite3

    from tests.canonical_library.helpers import make_object, write_library

    root = tmp_path / "ckl-source"
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE ckl_metadata SET value = ? WHERE key = 'inventory_fingerprint'",
            ("0" * 64,),
        )

    config = CKLRepositoryConfig(
        backend="sqlite",
        database_path=str(database),
        json_root=str(root),
        stale_database_policy="fallback_to_json",
        read_only=True,
    )
    provider = VerifiedCKLProvider(config_provider=lambda: config)
    library = provider.get_library()
    assert isinstance(library, CanonicalLibrary)
    assert library.retrieve_by_id("john") is not None
    assert provider.snapshot()["successful_initializations"] == 1
    provider.close()


def test_vercel_rejects_sqlite_inventory_fingerprint_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    from tests.canonical_library.helpers import make_object, write_library

    root = tmp_path / "ckl-source"
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE ckl_metadata SET value = ? WHERE key = 'inventory_fingerprint'",
            ("0" * 64,),
        )

    monkeypatch.setenv("VERCEL", "1")
    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root, backend="sqlite", database_path=database),
    )
    with pytest.raises(RuntimeError, match="Vercel CKL index inventory fingerprint"):
        provider.get_library()
    assert provider.snapshot()["successful_initializations"] == 0


def test_sqlite_source_change_invalidates_a_successful_provider_entry(tmp_path: Path) -> None:
    from tests.canonical_library.helpers import make_object, write_library

    root = tmp_path / "ckl-source"
    john = make_object("john", "book", "John", ["Gospel of John"])
    write_library(root, [john])
    database = tmp_path / "ckl.sqlite"
    build_database(root, database)
    provider = VerifiedCKLProvider(
        config_provider=lambda: _config(root, backend="sqlite", database_path=database),
    )

    verified = provider.get_library()
    assert provider.get_library() is verified
    genesis = make_object("genesis", "book", "Genesis", ["Book of Genesis"])
    write_library(root, [john, genesis])

    with pytest.raises(RuntimeError, match="canonical repository is stale"):
        provider.get_library()

    snapshot = provider.snapshot()
    assert snapshot["source_inventory_fingerprint_computations"] == 2
    assert snapshot["inventory_fingerprint_comparisons"] == 2
    assert snapshot["successful_initializations"] == 1
    assert snapshot["failed_initializations"] == 1
    provider.close()
