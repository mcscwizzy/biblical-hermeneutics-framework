from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library.authoring import (
    canonical_object_template,
    migrate_object_file,
    scan_library,
    validate_single_object,
)

from .helpers import make_object, write_library


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


class CanonicalAuthoringTests(unittest.TestCase):
    def test_canonical_object_template_normalizes_word_study_types(self) -> None:
        obj = canonical_object_template("word-study", "hesed")

        self.assertEqual(obj.id, "hesed")
        self.assertEqual(obj.type, "word_study")
        self.assertEqual(obj.title, "Hesed")
        self.assertIn("what does hesed mean", obj.aliases)
        self.assertIn("tell me about hesed", obj.aliases)

    def test_scan_library_reports_key_issue_buckets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object("abraham", "person", "Abraham", ["shared alias"]),
                    make_object("isaac", "person", "Isaac", ["shared alias"]),
                    make_object(
                        "shechem",
                        "place",
                        "Shechem",
                        ["where is shechem"],
                        content_status="complete",
                        related_objects=[
                            {
                                "id": "missing-target",
                                "relationship": "associated-place",
                                "weight": 1,
                                "notes": "test target",
                            }
                        ],
                        scripture_references=[
                            {
                                "reference": "Genesis 999:1",
                                "relationship": "primary",
                                "notes": "test reference",
                            }
                        ],
                    ),
                    make_object("dup", "person", "Dup Person", ["who is dup"]),
                ],
            )
            duplicate_path = root / "objects" / "places" / "dup.json"
            _write_json(
                duplicate_path,
                make_object("dup", "place", "Dup Place", ["where is dup"]),
            )
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["object_count"] = 999
            _write_json(manifest_path, manifest)

            audit = scan_library(root)

        self.assertEqual(audit.raw_object_count, 5)
        self.assertEqual(audit.valid_object_count, 4)
        self.assertTrue(audit.has_errors)
        self.assertTrue(audit.duplicate_id_issues)
        self.assertTrue(any(issue.code == "duplicate_alias" for issue in audit.alias_collision_issues))
        self.assertTrue(audit.unresolved_relationship_issues)
        self.assertTrue(audit.broken_scripture_reference_issues)
        self.assertTrue(audit.missing_content_issues)
        self.assertTrue(audit.manifest_issues)

    def test_validate_single_object_and_migrate_object_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "objects" / "places" / "shechem.json"
            obj = make_object(
                "shechem",
                "place",
                "Shechem",
                ["where is shechem"],
                summary="Shechem sits at a covenant crossroads.",
                historical_context="It appears in patriarchal narratives.",
                literary_context="It functions as a narrative location.",
                content_status="complete",
                review_status="approved",
                reviewed_by=["alice"],
                last_reviewed="2024-07-13",
                confidence="high",
                related_objects=[
                    {
                        "id": "abraham",
                        "relationship": "associated-person",
                        "weight": 5,
                        "notes": "patriarch",
                    }
                ],
                scripture_references=[
                    {
                        "reference": "Genesis 999:1",
                        "relationship": "primary",
                        "notes": "test reference",
                    }
                ],
                sources=["Westermann, Genesis"],
                common_questions=["Why does Shechem matter?"],
                interpretive_notes=["This is a test note."],
            )
            _write_json(file_path, obj)

            audit = validate_single_object(file_path)
            normalized, changed = migrate_object_file(file_path)

        self.assertEqual(audit.valid_object_count, 1)
        self.assertFalse(audit.validation_issues)
        self.assertFalse(audit.missing_content_issues)
        self.assertEqual(len(audit.broken_scripture_reference_issues), 1)
        self.assertTrue(changed)
        self.assertIsInstance(normalized["sources"][0], dict)
        self.assertEqual(normalized["sources"][0]["title"], "Westermann, Genesis")
        self.assertEqual(normalized["sources"][0]["source_type"], "other")

    def test_cli_smoke_for_create_validate_manifest_report_and_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            create = subprocess.run(
                [
                    sys.executable,
                    "tools/ckl_create.py",
                    "--type",
                    "word-study",
                    "--id",
                    "hesed",
                    "--root",
                    str(root),
                    "--write",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
            created_path = root / "objects" / "word_studies" / "hesed.json"
            self.assertTrue(created_path.exists())
            created = json.loads(created_path.read_text(encoding="utf-8"))
            self.assertEqual(created["type"], "word_study")
            self.assertIn("what does hesed mean", created["aliases"])
            self.assertIn("wrote", create.stdout)

            manifest = subprocess.run(
                [
                    sys.executable,
                    "tools/ckl_manifest.py",
                    "--root",
                    str(root),
                    "--write",
                    "--stamp",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
            self.assertIn("wrote", manifest.stdout)
            manifest_data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest_data["object_count"], 1)
            self.assertIsNotNone(manifest_data["generated_at"])

            validate = subprocess.run(
                [
                    sys.executable,
                    "tools/ckl_validate.py",
                    "--root",
                    str(root),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
            self.assertIn("Issues found: 0", validate.stdout)

            report = subprocess.run(
                [
                    sys.executable,
                    "tools/ckl_report.py",
                    "--root",
                    str(root),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
            self.assertIn("CKL audit for", report.stdout)
            self.assertIn("Files scanned: 1", report.stdout)

            legacy_path = root / "objects" / "places" / "shechem.json"
            legacy = make_object(
                "shechem",
                "place",
                "Shechem",
                ["where is shechem"],
                sources=["Westermann, Genesis"],
            )
            _write_json(legacy_path, legacy)

            migrate = subprocess.run(
                [
                    sys.executable,
                    "tools/ckl_migrate.py",
                    "--path",
                    str(legacy_path),
                    "--write",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
            migrated = json.loads(legacy_path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["sources"][0]["title"], "Westermann, Genesis")
            self.assertIn("updated", migrate.stdout)


if __name__ == "__main__":
    unittest.main()
