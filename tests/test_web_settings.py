import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from bhf_agent.db.common import DEFAULT_DB_PATH
from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS, resolve_runtime_data_paths
from bhf_web import settings as web_settings


class RuntimeDataPathTests(unittest.TestCase):
    def test_web_settings_keep_tyndale_database_path(self):
        self.assertEqual(web_settings.COMMENTARY_DB_PATH.name, "commentary.sqlite")
        self.assertFalse(hasattr(web_settings, "BHF_COMMENTARY_STORAGE_PATH"))
        self.assertEqual(
            web_settings.RUNTIME_DATA_PATHS.commentary_db_path,
            Path(".bhf-data/commentary.sqlite"),
        )

    def test_data_directory_supplies_default_database_paths(self):
        paths = resolve_runtime_data_paths({"BHF_DATA_DIR": "/tmp/test-data"})

        self.assertEqual(paths.data_dir, Path("/tmp/test-data"))
        self.assertEqual(paths.study_db_path, Path("/tmp/test-data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path("/tmp/test-data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path("/tmp/test-data/commentary.sqlite"),
        )
        self.assertEqual(paths.translations_path, Path("/tmp/test-data/translations"))
        self.assertEqual(
            paths.reader_settings_path,
            Path("/tmp/test-data/reader-settings.json"),
        )
        self.assertEqual(paths.web_config_path, Path("/tmp/test-data/web-config.json"))
        self.assertEqual(paths.memory_path, Path("/tmp/test-data/sessions"))
        self.assertEqual(
            paths.public_cache_path,
            Path("/tmp/test-data/public-answer-cache.json"),
        )

    def test_explicit_job_path_overrides_data_directory(self):
        paths = resolve_runtime_data_paths(
            {
                "BHF_DATA_DIR": "/tmp/test-data",
                "BHF_JOB_DB_PATH": "/custom/jobs.sqlite",
            }
        )

        self.assertEqual(paths.job_db_path, Path("/custom/jobs.sqlite"))

    def test_local_default_uses_tyndale_and_user_data_paths(self):
        paths = resolve_runtime_data_paths({})

        self.assertEqual(paths.data_dir, Path(".bhf-data"))
        self.assertEqual(paths.study_db_path, Path(".bhf-data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path(".bhf-data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path(".bhf-data/commentary.sqlite"),
        )
        self.assertEqual(paths.translations_path, Path(".bhf-data/translations"))
        self.assertEqual(
            paths.reader_settings_path,
            Path(".bhf-data/reader-settings.json"),
        )
        self.assertEqual(paths.web_config_path, Path(".bhf-data/web-config.json"))
        self.assertEqual(
            paths.public_cache_path,
            Path(".bhf-data/public-answer-cache.json"),
        )

    def test_vercel_defaults_to_tmp_runtime_data(self):
        paths = resolve_runtime_data_paths({"VERCEL": "1"})

        self.assertEqual(paths.data_dir, Path("/tmp/bhf-data"))
        self.assertEqual(paths.study_db_path, Path("/tmp/bhf-data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path("/tmp/bhf-data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path("/tmp/bhf-data/commentary.sqlite"),
        )
        self.assertEqual(paths.translations_path, Path("/tmp/bhf-data/translations"))
        self.assertEqual(
            paths.reader_settings_path,
            Path("/tmp/bhf-data/reader-settings.json"),
        )
        self.assertEqual(paths.web_config_path, Path("/tmp/bhf-data/web-config.json"))
        self.assertEqual(paths.memory_path, Path("/tmp/bhf-data/sessions"))
        self.assertEqual(
            paths.public_cache_path,
            Path("/tmp/bhf-data/public-answer-cache.json"),
        )

    def test_agent_db_default_matches_central_runtime_study_path(self):
        self.assertEqual(DEFAULT_DB_PATH, RUNTIME_DATA_PATHS.study_db_path)
        self.assertEqual(DEFAULT_DB_PATH, Path(".bhf-data/study.sqlite"))
        self.assertNotEqual(DEFAULT_DB_PATH, Path(".bhf/study.sqlite"))

    def test_vercel_agent_map_context_uses_runtime_db_without_explicit_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            app_root = temp_root / "app"
            runtime_root = temp_root / "runtime"
            app_root.mkdir()
            environment = os.environ.copy()
            environment["VERCEL"] = "1"
            environment["BHF_DATA_DIR"] = str(runtime_root)
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
            script = textwrap.dedent(
                """
                import json

                from bhf_agent.db.common import DEFAULT_DB_PATH
                from bhf_agent.map_tools import build_map_tool_context
                from bhf_agent.models import QuestionContext, ReferenceContext
                from bhf_agent.study_db import initialize_database

                initialize_database()
                reference = ReferenceContext(
                    book="John",
                    chapter=9,
                    verse=7,
                    testament="New Testament",
                    is_reference_based=True,
                    confidence=0.95,
                )
                context = build_map_tool_context(
                    "What archaeology is connected with John 9?",
                    reference_context=reference,
                    question_context=QuestionContext(
                        question_type="historical_context",
                        confidence=0.8,
                    ),
                )
                print(json.dumps({
                    "default_db_path": str(DEFAULT_DB_PATH),
                    "context_requested_tools": context["requested_tools"],
                }))
                """
            )
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=app_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual(result["default_db_path"], str(runtime_root / "study.sqlite"))
            self.assertNotIn(".bhf/study.sqlite", result["default_db_path"])
            self.assertIn("getPlacesForPassage", result["context_requested_tools"])
            self.assertTrue((runtime_root / "study.sqlite").is_file())
            self.assertFalse((app_root / ".bhf").exists())

    def test_connect_without_path_uses_central_runtime_database(self):
        with tempfile.TemporaryDirectory() as tempdir:
            environment = os.environ.copy()
            environment["VERCEL"] = "1"
            environment["BHF_DATA_DIR"] = tempdir
            script = textwrap.dedent(
                """
                import json
                from pathlib import Path

                from bhf_agent.db.connection import connect
                from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS

                with connect() as connection:
                    connection.execute("CREATE TABLE runtime_probe (value TEXT)")
                    connection.execute("INSERT INTO runtime_probe VALUES ('ok')")
                    connection.commit()

                print(json.dumps({
                    "resolved_path": str(RUNTIME_DATA_PATHS.study_db_path),
                    "database_exists": Path(RUNTIME_DATA_PATHS.study_db_path).is_file(),
                }))
                """
            )
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

        result = json.loads(completed.stdout)
        self.assertEqual(result["resolved_path"], str(Path(tempdir) / "study.sqlite"))
        self.assertTrue(result["database_exists"])
        self.assertNotIn(".bhf/study.sqlite", result["resolved_path"])

    def test_vercel_agent_lookup_local_knowledge_never_uses_app_root_bhf(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            app_root = temp_root / "app"
            runtime_root = temp_root / "runtime"
            app_root.mkdir()
            environment = os.environ.copy()
            environment["VERCEL"] = "1"
            environment["BHF_DATA_DIR"] = str(runtime_root)
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
            script = textwrap.dedent(
                """
                import json
                from pathlib import Path

                from bhf_agent.config import AgentConfig, CanonicalLibraryConfig
                from bhf_agent.runtime_paths import RUNTIME_DATA_PATHS
                from bhf_agent.runner import BHFAgent

                question = "What archaeology is connected with John 9?"
                agent = BHFAgent(
                    AgentConfig(
                        base_url="http://localhost:1234/v1",
                        model="test-model",
                        canonical_library=CanonicalLibraryConfig(enabled=False),
                    ),
                    adapter=object(),
                )
                agent._lookup_lexical_engine = lambda context: context
                context = agent._initialize_context(question)
                context = agent._detect_reference(context)
                context = agent._retrieve_scripture_context(context)
                context = agent._classify_genre(context)
                context = agent._classify_question_type(context)
                context = agent._load_profile(context)
                context = agent._lookup_local_knowledge(context)
                print(json.dumps({
                    "map_tool_keys": context.debug_metadata["map_tool_keys"],
                    "runtime_db_exists": RUNTIME_DATA_PATHS.study_db_path.is_file(),
                    "app_root_bhf_exists": Path(".bhf").exists(),
                }))
                """
            )
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=app_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(completed.stdout)
            self.assertIn("getPlacesForPassage", result["map_tool_keys"])
            self.assertTrue(result["runtime_db_exists"])
            self.assertFalse(result["app_root_bhf_exists"])

    def test_explicit_data_directory_beats_vercel_default(self):
        paths = resolve_runtime_data_paths(
            {"VERCEL": "1", "BHF_DATA_DIR": "/custom/data"}
        )

        self.assertEqual(paths.data_dir, Path("/custom/data"))
        self.assertEqual(paths.study_db_path, Path("/custom/data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path("/custom/data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path("/custom/data/commentary.sqlite"),
        )

    def test_individual_database_overrides_beat_vercel_defaults(self):
        paths = resolve_runtime_data_paths(
            {
                "VERCEL": "1",
                "BHF_STUDY_DB_PATH": "/custom/study.db",
                "BHF_JOB_DB_PATH": "/custom/jobs.db",
                "BHF_COMMENTARY_DB_PATH": "/custom/commentary.db",
            }
        )

        self.assertEqual(paths.data_dir, Path("/tmp/bhf-data"))
        self.assertEqual(paths.study_db_path, Path("/custom/study.db"))
        self.assertEqual(paths.job_db_path, Path("/custom/jobs.db"))
        self.assertEqual(paths.commentary_db_path, Path("/custom/commentary.db"))

    def test_explicit_tyndale_path_overrides_vercel_default(self):
        paths = resolve_runtime_data_paths(
            {
                "VERCEL": "1",
                "BHF_COMMENTARY_DB_PATH": "/custom/tyndale.sqlite",
            }
        )

        self.assertEqual(paths.commentary_db_path, Path("/custom/tyndale.sqlite"))

    def test_individual_writable_path_overrides_beat_vercel_defaults(self):
        paths = resolve_runtime_data_paths(
            {
                "VERCEL": "1",
                "BHF_TRANSLATIONS_PATH": "/custom/translations",
                "BHF_READER_SETTINGS_PATH": "/custom/reader.json",
                "BHF_WEB_CONFIG_PATH": "/custom/web.json",
                "BHF_MEMORY_PATH": "/custom/sessions",
                "BHF_PUBLIC_CACHE_PATH": "/custom/public-cache.json",
            }
        )

        self.assertEqual(paths.translations_path, Path("/custom/translations"))
        self.assertEqual(paths.reader_settings_path, Path("/custom/reader.json"))
        self.assertEqual(paths.web_config_path, Path("/custom/web.json"))
        self.assertEqual(paths.memory_path, Path("/custom/sessions"))
        self.assertEqual(paths.public_cache_path, Path("/custom/public-cache.json"))


if __name__ == "__main__":
    unittest.main()
