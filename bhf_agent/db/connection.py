"""SQLite connection helpers for the BHF local study store."""

from __future__ import annotations

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


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the study database, resolving omitted paths centrally."""

    db_path = Path(path) if path is not None else RUNTIME_DATA_PATHS.study_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, factory=_ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
