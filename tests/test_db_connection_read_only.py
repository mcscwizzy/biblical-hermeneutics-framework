from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

import bhf_agent.db.connection as db_connection
from bhf_agent.db.connection import connect
from bhf_agent.study_db import _ensure_schema, initialize_database


def test_read_only_connections_are_sqlite_read_only_and_schema_checks_do_not_write(tmp_path):
    database = tmp_path / "study.sqlite"
    initialize_database(database)

    with connect(database, read_only=True) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        _ensure_schema(connection)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("CREATE TABLE should_not_exist (id INTEGER)")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("UPDATE schema_migrations SET version = version")

    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='should_not_exist'").fetchone() is None


def test_study_read_only_environment_guard_does_not_change_unrelated_paths(tmp_path, monkeypatch):
    protected = tmp_path / "protected-study.sqlite"
    initialize_database(protected)
    unrelated = tmp_path / "unrelated.sqlite"
    monkeypatch.setattr(db_connection, "RUNTIME_DATA_PATHS", SimpleNamespace(study_db_path=protected))
    monkeypatch.setenv("BHF_STUDY_DB_READ_ONLY", "1")

    with connect(protected) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("UPDATE schema_migrations SET version = version")

    with connect(unrelated) as connection:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 0
        connection.execute("CREATE TABLE normal_write_path (value TEXT)")
        connection.execute("INSERT INTO normal_write_path (value) VALUES ('allowed')")
        assert connection.execute("SELECT value FROM normal_write_path").fetchone()[0] == "allowed"
