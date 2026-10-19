from __future__ import annotations

import hashlib
import io
import json
import zipfile

import pytest

from bhf_agent import runtime_paths
from framework.canonical_library import vercel_build as ckl_vercel_build
from framework.commentary.service import CommentaryService
from framework.commentary.vercel_build import (
    TYNDALE_PUBLIC_SOURCE_URL,
    build_vercel_tyndale_database,
)


def _archive_bytes() -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "notes.json",
            json.dumps(
                {
                    "entries": [
                        {
                            "id": "genesis-1-1",
                            "reference": "Genesis 1:1",
                            "kind": "study_note",
                            "title": "Creation",
                            "body": "A disposable test note.",
                        }
                    ]
                }
            ),
        )
    return stream.getvalue()


def test_vercel_tyndale_build_verifies_archive_and_redacts_transport_url(
    tmp_path, monkeypatch
):
    archive_bytes = _archive_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    transport_url = "https://archive.example.test/notes.zip?token=fixture-secret"
    output_path = tmp_path / "framework" / "commentary" / "data" / "tyndale.sqlite"
    requested_urls: list[str] = []

    def fake_urlopen(url: str, *, timeout: float):
        requested_urls.append(url)
        return io.BytesIO(archive_bytes)

    result = build_vercel_tyndale_database(
        environ={
            "VERCEL": "1",
            "BHF_TYNDALE_ARCHIVE_URL": transport_url,
            "BHF_TYNDALE_ARCHIVE_SHA256": archive_sha256,
        },
        output_path=output_path,
        urlopen_fn=fake_urlopen,
    )

    assert requested_urls == [transport_url]
    assert result["available"] is True
    assert result["healthy"] is True
    assert result["entry_count"] == 1
    assert result["archive_verified"] is True
    assert output_path.is_file()
    source = CommentaryService(output_path).source()
    assert source is not None
    assert source.source_url == TYNDALE_PUBLIC_SOURCE_URL
    assert "fixture-secret" not in json.dumps(result)
    assert "fixture-secret" not in json.dumps(source.to_dict())


def test_vercel_tyndale_build_rejects_checksum_mismatch_without_replacing_database(
    tmp_path,
):
    output_path = tmp_path / "tyndale.sqlite"
    output_path.write_bytes(b"existing generated output")

    def fake_urlopen(url: str, *, timeout: float):
        return io.BytesIO(_archive_bytes())

    with pytest.raises(ValueError, match="checksum"):
        build_vercel_tyndale_database(
            environ={
                "VERCEL": "1",
                "BHF_TYNDALE_ARCHIVE_URL": "https://archive.example.test/notes.zip?token=fixture-secret",
                "BHF_TYNDALE_ARCHIVE_SHA256": "0" * 64,
            },
            output_path=output_path,
            urlopen_fn=fake_urlopen,
        )

    assert output_path.read_bytes() == b"existing generated output"


def test_vercel_tyndale_build_requires_both_archive_settings_without_showing_values():
    with pytest.raises(ValueError, match="BHF_TYNDALE_ARCHIVE_SHA256") as error:
        build_vercel_tyndale_database(
            environ={
                "VERCEL": "1",
                "BHF_TYNDALE_ARCHIVE_URL": "https://archive.example.test/notes.zip?token=fixture-secret",
            }
        )

    assert "fixture-secret" not in str(error.value)


def test_local_build_skips_tyndale_download():
    assert build_vercel_tyndale_database(environ={}) is None


def test_canonical_vercel_build_runs_tyndale_provisioning(monkeypatch, capsys):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(
        ckl_vercel_build,
        "build_vercel_ckl_index",
        lambda **_kwargs: {"inventory_fingerprint": "ckl-test"},
    )
    monkeypatch.setattr(
        "framework.commentary.vercel_build.build_vercel_tyndale_database",
        lambda: {
            "available": True,
            "healthy": True,
            "entry_count": 1,
            "archive_verified": True,
        },
    )

    assert ckl_vercel_build.main([]) == 0

    output = capsys.readouterr().out
    assert '"inventory_fingerprint": "ckl-test"' in output
    assert '"entry_count": 1' in output
    assert "fixture-secret" not in output


def test_vercel_runtime_uses_bundled_tyndale_database_when_present(tmp_path, monkeypatch):
    packaged = tmp_path / "tyndale.sqlite"
    packaged.touch()
    monkeypatch.setattr(runtime_paths, "packaged_tyndale_database_path", lambda: packaged)

    paths = runtime_paths.resolve_runtime_data_paths({"VERCEL": "1"})

    assert paths.commentary_db_path == packaged


def test_explicit_commentary_database_path_overrides_bundled_database(
    tmp_path, monkeypatch
):
    packaged = tmp_path / "tyndale.sqlite"
    packaged.touch()
    monkeypatch.setattr(runtime_paths, "packaged_tyndale_database_path", lambda: packaged)

    paths = runtime_paths.resolve_runtime_data_paths(
        {"VERCEL": "1", "BHF_COMMENTARY_DB_PATH": "/tmp/custom/commentary.sqlite"}
    )

    assert str(paths.commentary_db_path) == "/tmp/custom/commentary.sqlite"
