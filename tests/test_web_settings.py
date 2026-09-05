import unittest
from pathlib import Path

from bhf_web.settings import (
    packaged_commentary_storage_path,
    resolve_runtime_data_paths,
)


class RuntimeDataPathTests(unittest.TestCase):
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

    def test_local_default_uses_bhf_data_directory(self):
        paths = resolve_runtime_data_paths({})

        self.assertEqual(paths.data_dir, Path(".bhf-data"))
        self.assertEqual(paths.study_db_path, Path(".bhf-data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path(".bhf-data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path(".bhf-data/commentary.sqlite"),
        )
        self.assertEqual(
            paths.bhf_commentary_storage_path,
            Path(".bhf-data/bhf-commentary"),
        )
        self.assertTrue(paths.bhf_commentary_storage_path.is_dir())
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

    def test_patch_release_uses_separate_packaged_snapshot(self):
        paths = resolve_runtime_data_paths({"BHF_COMMENTARY_RELEASE": "commentary-v1.0.1"})

        self.assertEqual(
            paths.bhf_commentary_storage_path,
            Path(".bhf-data/bhf-commentary-candidates/commentary-v1.0.1"),
        )

    def test_invalid_release_identifier_falls_back_to_frozen_release(self):
        paths = resolve_runtime_data_paths({"BHF_COMMENTARY_RELEASE": "../mutable"})

        self.assertEqual(paths.bhf_commentary_storage_path, Path(".bhf-data/bhf-commentary"))

    def test_vercel_defaults_to_tmp_runtime_data(self):
        paths = resolve_runtime_data_paths({"VERCEL": "1"})

        self.assertEqual(paths.data_dir, Path("/tmp/bhf-data"))
        self.assertEqual(paths.study_db_path, Path("/tmp/bhf-data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path("/tmp/bhf-data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path("/tmp/bhf-data/commentary.sqlite"),
        )
        self.assertEqual(
            paths.bhf_commentary_storage_path,
            packaged_commentary_storage_path(),
        )
        self.assertNotEqual(
            paths.bhf_commentary_storage_path,
            Path("/tmp/bhf-data/bhf-commentary"),
        )
        self.assertTrue(paths.bhf_commentary_storage_path.is_dir())
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

    def test_explicit_commentary_path_overrides_packaged_vercel_default(self):
        paths = resolve_runtime_data_paths(
            {
                "VERCEL": "1",
                "BHF_COMMENTARY_STORAGE_PATH": "/custom/commentary",
            }
        )

        self.assertEqual(paths.bhf_commentary_storage_path, Path("/custom/commentary"))

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
