from importlib.util import find_spec
from pathlib import Path

from bhf_agent.runtime_paths import resolve_runtime_data_paths


def test_runtime_paths_keep_the_tyndale_database_override():
    paths = resolve_runtime_data_paths(
        {"VERCEL": "1", "BHF_COMMENTARY_DB_PATH": "/tmp/tyndale-notes.sqlite"}
    )

    assert paths.commentary_db_path == Path("/tmp/tyndale-notes.sqlite")
    assert not hasattr(paths, "bhf_commentary_storage_path")


def test_runtime_package_keeps_tyndale_and_drops_generated_commentary():
    assert find_spec("framework.commentary.service") is not None
    assert find_spec("framework.commentary.importer") is not None
    assert find_spec("bhf_agent.chapter_commentary") is None
