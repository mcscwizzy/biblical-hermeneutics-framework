"""SQLite connection helpers for the BHF local study store."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from ..runtime_paths import RUNTIME_DATA_PATHS


class _ClosingConnection(sqlite3.Connection):
    """SQLite connection whose context manager also releases the handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(path: str | Path | None = None, *, read_only: bool | None = None) -> sqlite3.Connection:
    """Open the study database, resolving omitted paths centrally.

    ``BHF_STUDY_DB_READ_ONLY=1`` forces connections to the configured study
    database through SQLite's read-only URI and query-only guard. It is useful
    for protected local data and integration verification; the default remains
    the existing writable runtime behavior.
    """

    db_path = Path(path) if path is not None else RUNTIME_DATA_PATHS.study_db_path
    configured_read_only = (
        os.environ.get("BHF_STUDY_DB_READ_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}
        and db_path.expanduser().resolve(strict=False)
        == RUNTIME_DATA_PATHS.study_db_path.expanduser().resolve(strict=False)
    )
    use_read_only = configured_read_only if read_only is None else bool(read_only or configured_read_only)
    if use_read_only:
        database_uri = db_path.expanduser().resolve(strict=False).as_uri() + "?mode=ro"
        connection = sqlite3.connect(database_uri, uri=True, factory=_ClosingConnection)
        connection.execute("PRAGMA query_only = ON")
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path, factory=_ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
