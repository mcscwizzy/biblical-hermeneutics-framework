import unittest
from pathlib import Path

from bhf_web.settings import resolve_runtime_data_paths


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

    def test_vercel_defaults_to_tmp_runtime_data(self):
        paths = resolve_runtime_data_paths({"VERCEL": "1"})

        self.assertEqual(paths.data_dir, Path("/tmp/bhf-data"))
        self.assertEqual(paths.study_db_path, Path("/tmp/bhf-data/study.sqlite"))
        self.assertEqual(paths.job_db_path, Path("/tmp/bhf-data/jobs.sqlite"))
        self.assertEqual(
            paths.commentary_db_path,
            Path("/tmp/bhf-data/commentary.sqlite"),
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


if __name__ == "__main__":
    unittest.main()
