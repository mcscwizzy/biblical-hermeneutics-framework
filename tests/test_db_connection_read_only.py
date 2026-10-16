from __future__ import annotations

import sqlite3

import pytest

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

    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='should_not_exist'").fetchone() is None
