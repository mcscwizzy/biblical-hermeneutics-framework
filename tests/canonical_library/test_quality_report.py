from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from framework.canonical_library.quality_report import (
    build_quality_report,
    format_quality_markdown,
)

from .helpers import make_object, write_library


REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(
    source_id: str,
    *,
    source_type: str = "reference-work",
    publisher: str = "",
    supports: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": source_id,
        "title": source_id.replace("-", " ").title(),
        "author": "",
        "publisher": publisher,
        "year": None,
        "locator": "",
        "url": "",
        "source_type": source_type,
        "supports": supports or [],
        "notes": "",
    }


class CKLQualityReportTests(unittest.TestCase):
    def test_deep_report_calculates_inventory_quality_metrics(self) -> None:
        repeated_summary = (
            "A deliberately repeated summary that is long enough for duplicate analysis."
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_library(
                root,
                [
                    make_object(
                        "alpha",
                        "person",
                        "Shared Title",
                        ["shared alias"],
                        summary=repeated_summary,
                        content_status="complete",
                        related_objects=[
                            {
                                "id": "beta",
                                "relationship": "related-person",
                                "weight": 3,
                                "notes": "one-way test edge",
                            }
                        ],
                        interpretive_notes=[
                            {
                                "note": "An unresolved note.",
                                "note_type": "textual-observation",
                                "certainty": "unknown",
                                "dispute_status": "unknown",
                                "sources": ["missing-source"],
                            }
                        ],
                        sources=[
                            _source(
                                "alpha-orientation",
                                publisher="Canonical Knowledge Library",
                            )
                        ],
                        human_review_required=True,
                    ),
                    make_object(
                        "beta",
                        "place",
                        "Shared Title",
                        ["shared alias"],
                        summary=repeated_summary,
                        retrieval_metadata={
                            "aliases": [],
                            "search_terms": ["beta"],
                            "common_questions": ["Where is beta?"],
                            "related_topics": [],
                            "frequently_confused_with": [],
                            "semantic_keywords": [],
                        },
                        reviewed_by=["human-reviewer"],
                        human_review_required=False,
                        sources=[_source("beta-source", supports=["summary"])],
                    ),
                    make_object(
                        "gamma",
                        "event",
                        "Gamma",
                        ["gamma event"],
                        summary=repeated_summary,
                    ),
                ],
            )

            report = build_quality_report(root)

        self.assertEqual(report["inventory"]["raw_object_count"], 3)
        self.assertEqual(
            report["inventory"]["category_counts"],
            {"event": 1, "person": 1, "place": 1},
        )
        self.assertEqual(report["graph"]["missing_reciprocal_relationship_count"], 1)
        self.assertEqual(report["graph"]["orphaned_object_count"], 1)
        self.assertEqual(
            report["completeness"][
                "complete_records_with_empty_required_fields_count"
            ],
            1,
        )
        self.assertEqual(
            report["governance"]["records_with_unknown_certainty_count"], 1
        )
        self.assertEqual(
            report["governance"]["records_with_unknown_dispute_status_count"], 1
        )
        self.assertEqual(
            report["foundation_migration"][
                "records_with_incomplete_required_sections_count"
            ],
            3,
        )
        self.assertEqual(
            report["foundation_migration"][
                "interpretive_notes_using_legacy_taxonomies_count"
            ],
            1,
        )
        self.assertEqual(
            report["foundation_migration"]["records_missing_knowledge_layers_count"],
            0,
        )
        self.assertEqual(
            report["governance"]["records_with_no_reviewed_by_count"], 2
        )
        self.assertEqual(report["duplicates"]["duplicate_title_group_count"], 1)
        self.assertEqual(report["duplicates"]["duplicate_summary_group_count"], 1)
        self.assertEqual(report["duplicates"]["alias_collision_count"], 1)
        self.assertEqual(
            report["duplicates"]["unrelated_alias_collision_count"], 1
        )
        self.assertEqual(
            report["template_repetition"][
                "suspicious_template_repetition_group_count"
            ],
            1,
        )
        self.assertEqual(
            report["retrieval_gaps"]["objects_without_retrieval_search_terms_count"],
            2,
        )
        self.assertEqual(
            report["sources"]["unresolved_source_reference_count"], 1
        )
        self.assertEqual(
            report["sources"]["sources_supporting_no_field_or_claim_count"], 1
        )
        self.assertEqual(
            report["sources"][
                "internally_self_cited_without_external_support_count"
            ],
            1,
        )
        self.assertIn("person", report["field_coverage_by_category"])
        self.assertIn("# CKL Deep Quality Report", format_quality_markdown(report))

    def test_deep_report_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            write_library(
                root,
                [make_object("alpha", "person", "Alpha", ["who is alpha"])],
            )
            json_output = Path(tmp) / "report.json"
            markdown_output = Path(tmp) / "report.md"

            for output, extra_args in (
                (json_output, ["--json"]),
                (markdown_output, []),
            ):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "tools/ckl_report.py",
                        "--root",
                        str(root),
                        "--deep",
                        "--output",
                        str(output),
                        *extra_args,
                    ],
                    cwd=REPO_ROOT,
                    check=True,
                    capture_output=True,
                    encoding="utf-8",
                )
                self.assertIn("wrote", completed.stdout)

            payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["inventory"]["raw_object_count"], 1)
            self.assertIn(
                "# CKL Deep Quality Report",
                markdown_output.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
