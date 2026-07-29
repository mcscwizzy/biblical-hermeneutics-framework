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
        self.assertEqual(obj.knowledge_layers["primary"], "lexical")
        self.assertEqual(obj.section_status["core_summary"], "missing")

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
        warning_codes = {issue.code for issue in audit.warning_issues}
        self.assertIn("broken_scripture_reference", warning_codes)
        self.assertIn("missing_required_content", warning_codes)
        self.assertTrue(audit.manifest_issues)

    def test_scan_library_reports_repeated_prose_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repeated = "House churches, roads, cities, and Roman networks shape the background."
            write_library(
                root,
                [
                    make_object(
                        "alpha",
                        "place",
                        "Alpha",
                        ["where is alpha"],
                        ancient_near_east_context=repeated,
                    ),
                    make_object(
                        "beta",
                        "place",
                        "Beta",
                        ["where is beta"],
                        ancient_near_east_context=repeated,
                    ),
                    make_object(
                        "gamma",
                        "place",
                        "Gamma",
                        ["where is gamma"],
                        ancient_near_east_context=repeated,
                    ),
                ],
            )

            audit = scan_library(root)

        self.assertFalse(audit.has_errors)
        self.assertTrue(any(issue.code == "repeated_prose" for issue in audit.warning_issues))

    def test_scan_library_reports_semantic_validation_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "semantic-hygiene",
                        "archaeology",
                        "Semantic Hygiene",
                        ["semantic hygiene"],
                        content_status="draft",
                        review_status="unreviewed",
                        summary="Hebrew thought always works in concrete ways while Greek thought is abstract.",
                        historical_context="This historical setting is described without a named scholarly source.",
                        ancient_near_east_context="This is an Ancient Near Eastern comparison.",
                        hebrew_words=["berit"],
                        archaeology=["artifact"],
                        interpretive_notes=[
                            {
                                "note": "The church has always treated this as a confessional truth.",
                                "note_type": "theological-interpretation",
                                "certainty": "high",
                                "dispute_status": "broad-consensus",
                                "sources": [],
                            }
                        ],
                    ),
                ],
            )

            audit = scan_library(root)

        warning_codes = {issue.code for issue in audit.warning_issues}
        self.assertFalse(audit.has_errors)
        self.assertIn("historical_source_support", warning_codes)
        self.assertIn("lexical_source_support", warning_codes)
        self.assertIn("archaeological_source_support", warning_codes)
        self.assertIn("broad_generalization", warning_codes)
        self.assertIn("simplistic_worldview", warning_codes)
        self.assertIn("generic_ane_comparison", warning_codes)
        self.assertIn("confessional_consensus", warning_codes)

    def test_validate_single_object_reports_empty_applicable_context_for_mature_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "objects" / "themes" / "context-warning.json"
            obj = make_object(
                "context-warning",
                "theme",
                "Context Warning",
                ["context warning"],
                content_status="complete",
                review_status="reviewed",
                reviewed_by=["alice"],
                last_reviewed="2026-07-16",
                confidence="high",
                summary="A note on context layering.",
                historical_context="Historical setting is documented.",
                literary_context="Literary framing is documented.",
                context_applicability={
                    "historical": False,
                    "ancient_near_east": True,
                    "hebraic_worldview": False,
                    "second_temple": False,
                    "canonical": False,
                    "later_christian_reception": False,
                },
                scripture_references=[
                    {
                        "reference": "Genesis 12:6-7",
                        "relationship": "primary",
                        "notes": "",
                    }
                ],
                related_objects=[
                    {
                        "id": "related-topic",
                        "relationship": "associated-topic",
                        "weight": 1,
                        "notes": "",
                    }
                ],
                sources=[
                    {
                        "id": "example-source",
                        "title": "Example Source",
                        "author": "",
                        "publisher": "",
                        "year": None,
                        "locator": "",
                        "url": "",
                        "source_type": "reference-work",
                        "notes": "",
                    }
                ],
                common_questions=["How does it work?"],
                interpretive_notes=["It is a test note."],
            )
            _write_json(file_path, obj)

            audit = validate_single_object(file_path)

        self.assertTrue(audit.has_errors)
        self.assertTrue(any(issue.code == "empty_applicable_context" for issue in audit.validation_issues))

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
                review_status="in_review",
                reviewed_by=["codex-phase-10"],
                last_reviewed="2026-07-16",
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
        warning_codes = {issue.code for issue in audit.warning_issues}
        self.assertIn("legacy_ai_reviewer", warning_codes)
        self.assertIn("broken_scripture_reference", warning_codes)
        self.assertTrue(changed)
        self.assertIsInstance(normalized["sources"][0], dict)
        self.assertEqual(normalized["sources"][0]["title"], "Westermann, Genesis")
        self.assertEqual(normalized["sources"][0]["source_type"], "reference-work")
        self.assertEqual(normalized["generated_by"][0]["type"], "ai")
        self.assertEqual(normalized["generated_by"][0]["name"], "codex")
        self.assertEqual(normalized["generated_by"][0]["workflow"], "ane-hebraic-context-expansion")
        self.assertEqual(normalized["reviewed_by"], [])
        self.assertTrue(normalized["human_review_required"])
        self.assertIsInstance(normalized["interpretive_notes"][0], dict)
        self.assertEqual(
            normalized["interpretive_notes"][0]["note"],
            "This is a test note.",
        )
        self.assertEqual(
            normalized["interpretive_notes"][0]["note_type"],
            "textual-observation",
        )
        self.assertEqual(normalized["section_status"]["core_summary"], "missing")
        self.assertEqual(
            normalized["knowledge_layers"]["primary"],
            "historical_cultural",
        )
        self.assertEqual(normalized["claims"], [])

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
            self.assertIn("Warnings: 1", validate.stdout)
            self.assertIn("Errors: 0", validate.stdout)

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
            self.assertEqual(migrated["sources"][0]["source_type"], "reference-work")
            self.assertIn("updated", migrate.stdout)


if __name__ == "__main__":
    unittest.main()
