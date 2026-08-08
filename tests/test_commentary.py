import asyncio
import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from urllib.parse import urlsplit

from framework.commentary.database_schema import SCHEMA_VERSION, initialize_database
from framework.commentary.importer import CommentaryImportError, import_tyndale_archive
from framework.commentary.service import CommentaryService


def make_archive(path: Path) -> Path:
    archive = path / "tyndale.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(
            "notes.json",
            json.dumps(
                {
                    "entries": [
                        {"id": "ruth-3-4", "book": "Ruth", "chapter": 3, "verse": 4, "body": "Verse wording."},
                        {"id": "ruth-3-4-6", "reference": "Ruth 3:4-6", "kind": "range_note", "body": "Range wording."},
                        {"id": "ruth-intro", "book": "Ruth", "kind": "book_introduction", "body": "Introduction wording."},
                        {"id": "unmapped", "title": "Profile", "body": "No Scripture anchor."},
                    ]
                }
            ),
        )
    return archive


def test_schema_creation_and_versioning(tmp_path):
    database = initialize_database(tmp_path / "commentary.sqlite")
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"commentary_metadata", "commentary_sources", "commentary_entries", "commentary_anchors"} <= tables


def test_import_is_safe_attributed_and_normalizes_books(tmp_path):
    result = import_tyndale_archive(make_archive(tmp_path), tmp_path / "commentary.sqlite")
    assert result["entry_count"] == 4
    assert result["anchor_count"] == 3
    assert result["unrecognized_records"] == []
    service = CommentaryService(tmp_path / "commentary.sqlite")
    source = service.source()
    assert source.license == "CC BY-SA 4.0"
    assert "Tyndale House Publishers" in source.attribution
    assert [entry.external_id for entry in service.lookup_chapter("Ruth", 3)] == [
        "ruth-3-4", "ruth-3-4-6", "ruth-intro"
    ]
    assert {entry.anchor.book for entry in service.lookup_passage("Ruth", 3, 4, 4)} == {"Ruth"}


def test_import_rejects_zip_slip(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../outside.json", "{}")
    with pytest.raises(CommentaryImportError, match="unsafe ZIP member"):
        import_tyndale_archive(archive, tmp_path / "commentary.sqlite")


def test_missing_database_is_normal_unavailable_state(tmp_path):
    service = CommentaryService(tmp_path / "missing.sqlite")
    assert service.diagnostics() == {"available": False, "reason": "commentary_not_installed"}


def test_import_rebuild_is_deterministic_for_content(tmp_path):
    archive = make_archive(tmp_path)
    first = tmp_path / "first.sqlite"
    second = tmp_path / "second.sqlite"
    import_tyndale_archive(archive, first)
    import_tyndale_archive(archive, second)
    for database in (first, second):
        with sqlite3.connect(database) as connection:
            rows = connection.execute(
                "SELECT external_id, kind, title, body, sort_order FROM commentary_entries ORDER BY id"
            ).fetchall()
            assert rows[0][0] == "ruth-3-4"
    with sqlite3.connect(first) as left, sqlite3.connect(second) as right:
        assert left.execute("SELECT external_id, kind, title, body, sort_order FROM commentary_entries ORDER BY id").fetchall() == right.execute(
            "SELECT external_id, kind, title, body, sort_order FROM commentary_entries ORDER BY id"
        ).fetchall()


def test_commentary_api_success_and_unavailable_response(tmp_path):
    from bhf_web.app import create_app

    database = tmp_path / "commentary.sqlite"
    import_tyndale_archive(make_archive(tmp_path), database)

    async def request(app, path):
        parsed = urlsplit(path)
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await app(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": parsed.path,
                "raw_path": parsed.path.encode(),
                "query_string": parsed.query.encode(),
                "headers": [],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        status = next(message["status"] for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return status, json.loads(body)

    with patch("bhf_web.app.COMMENTARY_DB_PATH", database):
        app = create_app()
    status, payload = asyncio.run(request(app, "/api/commentary/Ruth/3"))
    assert status == 200
    assert payload["available"] is True
    assert payload["source"]["license"] == "CC BY-SA 4.0"
    assert payload["entries"][0]["body"] == "Verse wording."

    with patch("bhf_web.app.COMMENTARY_DB_PATH", tmp_path / "missing.sqlite"):
        status, payload = asyncio.run(request(create_app(), "/api/commentary/Ruth/3"))
    assert status == 200
    assert payload == {
        "available": False,
        "reason": "commentary_not_installed",
        "book": "Ruth",
        "chapter": 3,
        "entries": [],
    }
