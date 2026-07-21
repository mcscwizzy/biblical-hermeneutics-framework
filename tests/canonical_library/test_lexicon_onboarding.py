from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from framework.canonical_library.database_builder import build_database
from framework.canonical_library.lexicon_importer import import_normalized_lexicon_file
from framework.canonical_library.lexicon_onboarding import (
    build_onboarding_report,
    format_onboarding_report,
    report_has_failures,
    validate_database_coverage,
)
from tools.lexicon_smoke import run_smoke

from .helpers import make_object, write_library


FIXTURE = Path("tests/fixtures/lexicon_phase1.json")


class LexiconOnboardingTests(unittest.TestCase):
    def test_default_coverage_passes_with_fixture_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = _build_database_with_fixture(Path(tmp))

            report = validate_database_coverage(database)

            self.assertEqual(report["failed"], 0)
            self.assertEqual(report["passed"], 2)
            self.assertIn("λόγος", report["results"][0]["matched"])
            self.assertIn("חֶסֶד", report["results"][1]["matched"])

    def test_onboarding_report_marks_missing_coverage_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = tmp_path / "ckl.sqlite"
            root = tmp_path / "ckl"
            write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
            build_database(root, database)

            report = build_onboarding_report(database_path=database)

            self.assertTrue(report_has_failures(report))
            self.assertEqual(report["coverage"]["failed"], 2)
            self.assertIn("FAIL", format_onboarding_report(report))

    def test_word_study_smoke_uses_real_study_action_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            database = _build_database_with_fixture(tmp_path)

            report = run_smoke(database_path=database, ckl_root=tmp_path / "ckl")

            self.assertEqual(report["failed"], 0)
            self.assertEqual(report["passed"], 2)
            self.assertIn("λόγος", report["results"][0]["matched"])


def _build_database_with_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "ckl"
    database = tmp_path / "ckl.sqlite"
    write_library(root, [make_object("john", "book", "John", ["Gospel of John"])])
    build_database(root, database)
    import_normalized_lexicon_file(database, FIXTURE, rebuild=True)
    return database


if __name__ == "__main__":
    unittest.main()
