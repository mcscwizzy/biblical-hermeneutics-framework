from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tools.ed4_review_workbench import DECISIONS, ReviewWorkflowError, ReviewWorkbench


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ED3_ROOT = REPOSITORY_ROOT / "docs/evidence-depth/ed3"


class ED4ReviewWorkbenchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.ledger_path = Path(self.temp_directory.name) / "reviews.jsonl"
        self.workbench = ReviewWorkbench(
            queue_path=ED3_ROOT / "human-review-queue.csv",
            packet_root=ED3_ROOT,
            ledger_path=self.ledger_path,
        )

    def test_all_pending_records_and_packet_links_are_preserved(self) -> None:
        with (ED3_ROOT / "human-review-queue.csv").open(encoding="utf-8", newline="") as stream:
            original_rows = list(csv.DictReader(stream))
        records = self.workbench.list_records()

        self.assertEqual(len(records), 99)
        self.assertEqual(
            {record["evidence_id"] for record in records},
            {row["evidence_id"] for row in original_rows},
        )
        self.assertTrue(all(self.workbench.packet_path(record).is_file() for record in records))
        self.assertTrue(
            all(
                not row[field]
                for row in original_rows
                for field in (
                    "reviewer_name",
                    "reviewer_affiliation_or_expertise",
                    "review_date",
                    "review_decision",
                    "review_rationale",
                    "required_corrections_or_follow_up",
                )
            )
        )
        self.assertFalse(self.ledger_path.exists())

    def test_search_filters_by_book_priority_evidence_access_and_text(self) -> None:
        record = self.workbench.list_records()[0]

        filters = (
            ("book", record["book_id"]),
            ("priority", record["recommended_review_priority"]),
            ("evidence_type", record["evidence_type"]),
            ("source_access", record["ed3_source_access_class"][:12]),
            ("source_outcome", record["ed3_verification_outcome"][:12]),
            ("query", record["evidence_id"]),
        )
        for filter_name, value in filters:
            with self.subTest(filter=filter_name):
                matches = self.workbench.list_records(**{filter_name: value})
                self.assertIn(record["evidence_id"], {item["evidence_id"] for item in matches})

    def test_show_exposes_packet_claim_sources_locators_and_questions(self) -> None:
        record = self.workbench.list_records()[0]
        detail = self.workbench.show(record["evidence_id"])

        self.assertEqual(detail["record"]["evidence_id"], record["evidence_id"])
        self.assertIn("Claim under review", detail["packet_text"])
        self.assertIn("Sources and inspection record", detail["packet_text"])
        self.assertIn("Questions for the reviewer", detail["packet_text"])
        self.assertIn(record["source_ids"].split(";", maxsplit=1)[0], detail["packet_text"])
        locator = record["bibliographic_locators"].split(";", maxsplit=1)[0]
        self.assertIn(locator, detail["packet_text"])

    def test_empty_history_reports_pending_records_without_human_decisions(self) -> None:
        progress = self.workbench.progress()

        self.assertEqual(progress["total_records"], 99)
        self.assertEqual(progress["decided_records"], 0)
        self.assertEqual(progress["pending_records"], 99)
        self.assertEqual(progress["human_decisions_recorded"], 0)
        self.assertEqual(progress["events"], 0)

    def test_decision_requires_allowed_value_confirmation_identity_and_sources(self) -> None:
        evidence_id = self.workbench.list_records()[0]["evidence_id"]
        self.assertEqual(
            set(DECISIONS.values()),
            {
                "Approve as written",
                "Approve with corrections",
                "Request more research",
                "Hold due to insufficient evidence",
                "Reject the claim",
            },
        )
        base = {
            "evidence_id": evidence_id,
            "reviewer_name": "Qualified Reviewer",
            "reviewer_expertise": "Hebrew Bible and textual criticism",
            "review_date": date.today().isoformat(),
            "decision": "approve_as_written",
            "rationale": "The inspected sources support the bounded wording.",
            "inspections": [
                {"source_id": "source-id", "locator": "section 2", "scope": "full text"}
            ],
        }

        with self.assertRaises(ReviewWorkflowError):
            self.workbench.record_decision(
                **{**base, "decision": "machine_verified"},
                confirmed_human_action=True,
            )
        with self.assertRaises(ReviewWorkflowError):
            self.workbench.record_decision(**base, confirmed_human_action=False)
        with self.assertRaises(ReviewWorkflowError):
            self.workbench.record_decision(
                **{**base, "inspections": []},
                confirmed_human_action=True,
            )
        with self.assertRaises(ReviewWorkflowError):
            self.workbench.record_decision(
                **{**base, "decision": "approve_with_corrections"},
                confirmed_human_action=True,
            )
        self.assertFalse(self.ledger_path.exists())

    def test_explicit_decision_is_attributed_hash_chained_and_exported_reproducibly(self) -> None:
        record = self.workbench.list_records()[0]
        event = self.workbench.record_decision(
            evidence_id=record["evidence_id"],
            reviewer_name="Qualified Reviewer",
            reviewer_expertise="Hebrew Bible and textual criticism",
            review_date=date.today().isoformat(),
            decision="request_more_research",
            rationale="The argument needs independent comparison with the cited edition.",
            inspections=[
                {"source_id": "sample-source", "locator": "section 2", "scope": "full text"}
            ],
            confirmed_human_action=True,
        )

        self.assertEqual(event["reviewer_name"], "Qualified Reviewer")
        self.assertEqual(event["decision"], "request_more_research")
        self.assertTrue(event["event_hash"])
        self.assertEqual(self.workbench.history()[0]["event_hash"], event["event_hash"])
        self.assertEqual(self.workbench.progress()["decided_records"], 1)
        self.assertEqual(self.workbench.export_json(), self.workbench.export_json())
        self.assertIn(record["evidence_id"], self.workbench.export_json())
        csv_export = self.workbench.export_decisions_csv()
        self.assertIn(record["evidence_id"], csv_export)
        self.assertIn("Qualified Reviewer", csv_export)

    def test_correction_request_and_verification_are_separate_attributed_events(self) -> None:
        record = self.workbench.list_records()[0]
        correction = self.workbench.request_correction(
            evidence_id=record["evidence_id"],
            reviewer_name="Qualified Reviewer",
            reviewer_expertise="New Testament Greek",
            review_date=date.today().isoformat(),
            requested_change="Narrow the claim to the attested textual form.",
            rationale="The current wording generalizes beyond the examined witness.",
            inspections=[
                {
                    "source_id": "greek-edition",
                    "locator": "apparatus entry",
                    "scope": "edition and apparatus",
                }
            ],
            confirmed_human_action=True,
        )
        self.assertEqual(
            next(
                row
                for row in self.workbench.list_records()
                if row["evidence_id"] == record["evidence_id"]
            )["review_workbench_status"],
            "correction_pending",
        )
        verification = self.workbench.verify_correction(
            evidence_id=record["evidence_id"],
            correction_event_id=correction["event_id"],
            reviewer_name="Second Reviewer",
            reviewer_expertise="Text criticism",
            review_date=date.today().isoformat(),
            verification_rationale="The revised wording now matches the specified witness scope.",
            change_reference="framework/canonical_library/objects/books/mark.json#claims[2]",
            corrected_text="The specified witness reads the shorter ending.",
            inspections=[
                {
                    "source_id": "greek-edition",
                    "locator": "apparatus entry",
                    "scope": "rechecked edition and apparatus",
                }
            ],
            confirmed_human_action=True,
        )

        self.assertEqual(len(self.workbench.history()), 2)
        self.assertEqual(verification["correction_event_id"], correction["event_id"])
        self.assertEqual(self.workbench.progress()["verified_corrections"], 1)
        self.assertNotIn("decision", verification)
        self.assertEqual(
            next(
                row
                for row in self.workbench.list_records()
                if row["evidence_id"] == record["evidence_id"]
            )["review_workbench_status"],
            "correction_verified",
        )

    def test_tampered_history_is_rejected(self) -> None:
        record = self.workbench.list_records()[0]
        self.workbench.record_decision(
            evidence_id=record["evidence_id"],
            reviewer_name="Qualified Reviewer",
            reviewer_expertise="Hebrew Bible",
            review_date=date.today().isoformat(),
            decision="hold_insufficient_evidence",
            rationale="The source cannot presently be inspected.",
            inspections=[
                {"source_id": "sample-source", "locator": "pp. 2-3", "scope": "abstract only"}
            ],
            confirmed_human_action=True,
        )
        self.ledger_path.write_text(
            self.ledger_path.read_text().replace("cannot", "might"),
            encoding="utf-8",
        )

        with self.assertRaises(ReviewWorkflowError):
            self.workbench.history()


if __name__ == "__main__":
    unittest.main()
