#!/usr/bin/env python3
"""Local, attributed review workflow for the immutable ED-3 review queue."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from framework.canonical_library.normalization import normalize_id


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ED3_ROOT = REPOSITORY_ROOT / "docs/evidence-depth/ed3"
DEFAULT_QUEUE = ED3_ROOT / "human-review-queue.csv"
DEFAULT_PACKET_ROOT = ED3_ROOT
DEFAULT_LEDGER = REPOSITORY_ROOT / ".bhf-data/ed4-human-reviews.jsonl"
GENESIS_HASH = "0" * 64
SNAPSHOT_FORMAT = "bhf-ed4-review-snapshot"
SNAPSHOT_FORMAT_VERSION = 1

DECISIONS = {
    "approve_as_written": "Approve as written",
    "approve_with_corrections": "Approve with corrections",
    "request_more_research": "Request more research",
    "hold_insufficient_evidence": "Hold due to insufficient evidence",
    "reject_claim": "Reject the claim",
}


class ReviewWorkflowError(ValueError):
    """Raised when a queue, packet, decision, or review history is invalid."""


class ReviewWorkbench:
    """Search ED-3 packets and append human-attributed review events."""

    def __init__(
        self,
        *,
        queue_path: Path = DEFAULT_QUEUE,
        packet_root: Path = DEFAULT_PACKET_ROOT,
        ledger_path: Path = DEFAULT_LEDGER,
    ) -> None:
        self.queue_path = Path(queue_path)
        self.packet_root = Path(packet_root).resolve()
        self.ledger_path = Path(ledger_path)

    def list_records(
        self,
        *,
        book: str | None = None,
        priority: str | None = None,
        evidence_type: str | None = None,
        source_access: str | None = None,
        source_outcome: str | None = None,
        query: str | None = None,
    ) -> list[dict[str, str]]:
        records = self._read_queue()
        history = self.history()
        latest_decisions = self._latest_decisions(history)
        corrections = self._correction_status(history)
        filtered: list[dict[str, str]] = []
        for record in records:
            if book and normalize_id(record.get("book_id", "")) != normalize_id(book):
                continue
            if (
                priority
                and record.get("recommended_review_priority", "").casefold()
                != priority.casefold()
            ):
                continue
            if (
                evidence_type
                and record.get("evidence_type", "").casefold()
                != evidence_type.casefold()
            ):
                continue
            if (
                source_access
                and source_access.casefold()
                not in record.get("ed3_source_access_class", "").casefold()
            ):
                continue
            if (
                source_outcome
                and source_outcome.casefold()
                not in record.get("ed3_verification_outcome", "").casefold()
            ):
                continue
            if query and query.casefold() not in " ".join(record.values()).casefold():
                continue
            evidence_id = record["evidence_id"]
            decision = latest_decisions.get(evidence_id)
            correction_status = corrections.get(evidence_id, {})
            if any(status == "open" for status in correction_status.values()):
                record["review_workbench_status"] = "correction_pending"
            elif decision:
                record["review_workbench_status"] = str(decision.get("decision", ""))
            elif correction_status:
                record["review_workbench_status"] = "correction_verified"
            else:
                record["review_workbench_status"] = "pending"
            filtered.append(record)
        return filtered

    def show(self, evidence_id: str) -> dict[str, Any]:
        record = self._record(evidence_id)
        packet = self.packet_path(record)
        if not packet.is_file():
            raise ReviewWorkflowError(f"review packet does not exist: {packet}")
        return {
            "record": record,
            "packet_path": packet,
            "packet_text": packet.read_text(encoding="utf-8"),
            "history": [event for event in self.history() if event["evidence_id"] == evidence_id],
        }

    def packet_path(self, record: Mapping[str, str]) -> Path:
        relative = Path(record.get("review_packet_path", ""))
        packet = (self.packet_root / relative).resolve()
        if self.packet_root != packet and self.packet_root not in packet.parents:
            raise ReviewWorkflowError(f"packet path escapes the ED-3 packet directory: {relative}")
        return packet

    def progress(self) -> dict[str, Any]:
        records = self._read_queue()
        history = self.history()
        decisions = self._latest_decisions(history)
        corrections = self._correction_status(history)
        decision_counts: dict[str, int] = {}
        for event in decisions.values():
            decision = str(event["decision"])
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        open_corrections = sum(
            status == "open"
            for per_record in corrections.values()
            for status in per_record.values()
        )
        verified_corrections = sum(
            status == "verified"
            for per_record in corrections.values()
            for status in per_record.values()
        )
        return {
            "total_records": len(records),
            "decided_records": len(decisions),
            "pending_records": len(records) - len(decisions),
            "human_decisions_recorded": sum(
                event.get("event_type") == "decision" for event in history
            ),
            "decision_counts": dict(sorted(decision_counts.items())),
            "open_correction_requests": open_corrections,
            "verified_corrections": verified_corrections,
            "events": len(history),
        }

    def status_report(self) -> dict[str, Any]:
        """Report local chain integrity, trust limits, and queue reconciliation."""

        events = self.history()
        return {
            "event_chain_integrity": "valid",
            "authenticity": "not_independently_authenticated",
            "external_checkpoint": "not_supplied",
            "events": len(events),
            "tail_hash": events[-1]["event_hash"] if events else GENESIS_HASH,
            "queue_reconciliation": _reconcile_queue_events(self._read_queue(), events),
        }

    def history(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        events: list[dict[str, Any]] = []
        seen_event_ids: set[str] = set()
        expected_previous_hash = GENESIS_HASH
        try:
            lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ReviewWorkflowError(f"cannot read review history: {exc}") from exc
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                raise ReviewWorkflowError(
                    f"blank line in review history at line {line_number}"
                )
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReviewWorkflowError(
                    f"invalid JSON in review history at line {line_number}"
                ) from exc
            if not isinstance(event, dict):
                raise ReviewWorkflowError(f"review history line {line_number} is not an object")
            recorded_hash = event.get("event_hash")
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id.strip():
                raise ReviewWorkflowError(
                    f"review history line {line_number} has no event ID"
                )
            if event_id in seen_event_ids:
                raise ReviewWorkflowError(
                    f"duplicate review event ID at line {line_number}: {event_id}"
                )
            if (
                event.get("previous_hash") != expected_previous_hash
                or recorded_hash != _event_hash(event)
            ):
                raise ReviewWorkflowError(f"review history hash chain failed at line {line_number}")
            expected_previous_hash = str(recorded_hash)
            seen_event_ids.add(event_id)
            events.append(event)
        return events

    def create_snapshot(self, output_path: Path) -> dict[str, Any]:
        """Write a versioned snapshot without replacing an existing file."""

        events = self.history()
        snapshot = {
            "format": SNAPSHOT_FORMAT,
            "format_version": SNAPSHOT_FORMAT_VERSION,
            "created_at_utc": (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            ),
            "event_count": len(events),
            "first_event_id": events[0]["event_id"] if events else None,
            "last_event_id": events[-1]["event_id"] if events else None,
            "tail_hash": events[-1]["event_hash"] if events else GENESIS_HASH,
            "events": events,
        }
        serialized = (json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor: int | None = None
        created = False
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            created = True
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise ReviewWorkflowError(
                f"snapshot already exists; choose a new versioned path: {path}"
            ) from exc
        except OSError as exc:
            if descriptor is not None:
                os.close(descriptor)
            if created:
                path.unlink(missing_ok=True)
            raise ReviewWorkflowError(f"cannot create review snapshot: {exc}") from exc
        return self.verify_snapshot(path)

    def verify_snapshot(
        self,
        snapshot_path: Path,
        *,
        trusted_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Verify snapshot structure and hash chain; an external digest is optional."""

        path = Path(snapshot_path)
        try:
            raw = path.read_bytes()
            snapshot = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReviewWorkflowError(f"cannot read valid review snapshot: {exc}") from exc
        if not isinstance(snapshot, dict):
            raise ReviewWorkflowError("review snapshot must be a JSON object")
        if snapshot.get("format") != SNAPSHOT_FORMAT:
            raise ReviewWorkflowError("unrecognized review snapshot format")
        if snapshot.get("format_version") != SNAPSHOT_FORMAT_VERSION:
            raise ReviewWorkflowError("unsupported review snapshot version")
        events = snapshot.get("events")
        if not isinstance(events, list):
            raise ReviewWorkflowError("review snapshot events must be a list")
        expected_previous_hash = GENESIS_HASH
        seen_event_ids: set[str] = set()
        for sequence, event in enumerate(events, start=1):
            if not isinstance(event, dict):
                raise ReviewWorkflowError(f"snapshot event {sequence} is not an object")
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id.strip():
                raise ReviewWorkflowError(f"snapshot event {sequence} has no event ID")
            if event_id in seen_event_ids:
                raise ReviewWorkflowError(f"duplicate review event ID in snapshot: {event_id}")
            if (
                event.get("previous_hash") != expected_previous_hash
                or event.get("event_hash") != _event_hash(event)
            ):
                raise ReviewWorkflowError(f"review snapshot hash chain failed at event {sequence}")
            expected_previous_hash = str(event["event_hash"])
            seen_event_ids.add(event_id)
        if snapshot.get("event_count") != len(events):
            raise ReviewWorkflowError("review snapshot event count does not match its contents")
        expected_first = events[0]["event_id"] if events else None
        expected_last = events[-1]["event_id"] if events else None
        if (
            snapshot.get("first_event_id") != expected_first
            or snapshot.get("last_event_id") != expected_last
            or snapshot.get("tail_hash") != expected_previous_hash
        ):
            raise ReviewWorkflowError("review snapshot sequence summary does not match its contents")
        digest = hashlib.sha256(raw).hexdigest()
        if trusted_sha256 is not None and digest.casefold() != trusted_sha256.strip().casefold():
            raise ReviewWorkflowError("review snapshot does not match the externally retained SHA-256")
        return {
            "integrity": "valid",
            "authenticity": "externally_anchored" if trusted_sha256 else "not_independently_authenticated",
            "event_count": len(events),
            "first_event_id": expected_first,
            "last_event_id": expected_last,
            "tail_hash": expected_previous_hash,
            "snapshot_sha256": digest,
        }

    def restore_snapshot(
        self,
        snapshot_path: Path,
        *,
        confirmed: bool = False,
        trusted_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Explicitly append a valid snapshot suffix; never replace local history."""

        if not confirmed:
            raise ReviewWorkflowError("restore requires explicit confirmation")
        self.verify_snapshot(snapshot_path, trusted_sha256=trusted_sha256)
        snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
        imported = snapshot["events"]
        existing = self.history()
        if len(existing) > len(imported):
            raise ReviewWorkflowError(
                "snapshot is older than the local review history; restore would discard events"
            )
        for sequence, event in enumerate(existing, start=1):
            imported_event = imported[sequence - 1]
            if (
                event["event_id"] != imported_event["event_id"]
                or event["event_hash"] != imported_event["event_hash"]
            ):
                raise ReviewWorkflowError(
                    f"snapshot conflicts with local review history at event {sequence}"
                )
        local_ids = {event["event_id"] for event in existing}
        duplicate_ids = local_ids.intersection(event["event_id"] for event in imported)
        suffix = imported[len(existing):]
        serialized_suffix = "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for event in suffix
        )
        if serialized_suffix:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with self.ledger_path.open("a+b") as stream:
                    stream.seek(0, os.SEEK_END)
                    if stream.tell():
                        stream.seek(-1, os.SEEK_END)
                        has_line_ending = stream.read(1) == b"\n"
                        stream.seek(0, os.SEEK_END)
                        if not has_line_ending:
                            stream.write(b"\n")
                    stream.write(serialized_suffix.encode("utf-8"))
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise ReviewWorkflowError(f"cannot restore review snapshot: {exc}") from exc
        restored_history = self.history()
        return {
            "integrity": "valid",
            "appended_events": len(suffix),
            "existing_prefix_events": len(existing),
            "duplicate_events": len(duplicate_ids),
            "events_after_restore": len(restored_history),
            "tail_hash": restored_history[-1]["event_hash"] if restored_history else GENESIS_HASH,
            "snapshot_sha256": hashlib.sha256(Path(snapshot_path).read_bytes()).hexdigest(),
            "queue_reconciliation": _reconcile_queue_events(self._read_queue(), restored_history),
        }

    def record_decision(
        self,
        *,
        evidence_id: str,
        reviewer_name: str,
        reviewer_expertise: str,
        review_date: str,
        decision: str,
        rationale: str,
        inspections: Sequence[Mapping[str, str]],
        confirmed_human_action: bool,
        required_corrections_or_follow_up: str = "",
    ) -> dict[str, Any]:
        self._record(evidence_id)
        self._validate_human_action(
            reviewer_name,
            reviewer_expertise,
            review_date,
            rationale,
            inspections,
            confirmed_human_action,
        )
        if decision not in DECISIONS:
            raise ReviewWorkflowError(f"unsupported human decision: {decision}")
        if (
            decision == "approve_with_corrections"
            and not required_corrections_or_follow_up.strip()
        ):
            raise ReviewWorkflowError(
                "approve_with_corrections requires the correction or follow-up text"
            )
        return self._append_event(
            {
                "event_type": "decision",
                "evidence_id": evidence_id,
                "reviewer_name": reviewer_name.strip(),
                "reviewer_expertise": reviewer_expertise.strip(),
                "review_date": review_date,
                "decision": decision,
                "decision_label": DECISIONS[decision],
                "rationale": rationale.strip(),
                "inspections": _normalize_inspections(inspections),
                "required_corrections_or_follow_up": required_corrections_or_follow_up.strip(),
            }
        )

    def request_correction(
        self,
        *,
        evidence_id: str,
        reviewer_name: str,
        reviewer_expertise: str,
        review_date: str,
        requested_change: str,
        rationale: str,
        inspections: Sequence[Mapping[str, str]],
        confirmed_human_action: bool,
    ) -> dict[str, Any]:
        self._record(evidence_id)
        self._validate_human_action(
            reviewer_name,
            reviewer_expertise,
            review_date,
            rationale,
            inspections,
            confirmed_human_action,
        )
        if not requested_change.strip():
            raise ReviewWorkflowError("requested_change is required")
        return self._append_event(
            {
                "event_type": "correction_requested",
                "evidence_id": evidence_id,
                "reviewer_name": reviewer_name.strip(),
                "reviewer_expertise": reviewer_expertise.strip(),
                "review_date": review_date,
                "requested_change": requested_change.strip(),
                "rationale": rationale.strip(),
                "inspections": _normalize_inspections(inspections),
            }
        )

    def verify_correction(
        self,
        *,
        evidence_id: str,
        correction_event_id: str,
        reviewer_name: str,
        reviewer_expertise: str,
        review_date: str,
        verification_rationale: str,
        change_reference: str,
        corrected_text: str,
        inspections: Sequence[Mapping[str, str]],
        confirmed_human_action: bool,
    ) -> dict[str, Any]:
        self._record(evidence_id)
        self._validate_human_action(
            reviewer_name,
            reviewer_expertise,
            review_date,
            verification_rationale,
            inspections,
            confirmed_human_action,
        )
        events = self.history()
        correction = next(
            (event for event in events if event["event_id"] == correction_event_id),
            None,
        )
        if (
            correction is None
            or correction.get("event_type") != "correction_requested"
            or correction.get("evidence_id") != evidence_id
        ):
            raise ReviewWorkflowError(
                "correction_event_id must identify a correction request for this evidence record"
            )
        if not change_reference.strip() or not corrected_text.strip():
            raise ReviewWorkflowError(
                "correction verification requires a change reference and the corrected wording"
            )
        return self._append_event(
            {
                "event_type": "correction_verified",
                "evidence_id": evidence_id,
                "reviewer_name": reviewer_name.strip(),
                "reviewer_expertise": reviewer_expertise.strip(),
                "review_date": review_date,
                "correction_event_id": correction_event_id,
                "change_reference": change_reference.strip(),
                "corrected_text": corrected_text.strip(),
                "rationale": verification_rationale.strip(),
                "inspections": _normalize_inspections(inspections),
            }
        )

    def export_json(self) -> str:
        events = self.history()
        decisions = self._latest_decisions(events)
        payload = {
            "summary": self.progress(),
            "decisions": [decisions[key] for key in sorted(decisions)],
            "events": events,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    def export_decisions_csv(self) -> str:
        events = self.history()
        decisions = self._latest_decisions(events)
        columns = (
            "evidence_id",
            "decision",
            "decision_label",
            "reviewer_name",
            "reviewer_expertise",
            "review_date",
            "rationale",
            "required_corrections_or_follow_up",
            "event_id",
            "event_hash",
        )
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for evidence_id in sorted(decisions):
            writer.writerow({column: decisions[evidence_id].get(column, "") for column in columns})
        return stream.getvalue()

    def _append_event(self, values: Mapping[str, Any]) -> dict[str, Any]:
        existing = self.history()
        event: dict[str, Any] = {
            **values,
            "event_id": str(uuid.uuid4()),
            "recorded_at_utc": (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            ),
            "previous_hash": existing[-1]["event_hash"] if existing else GENESIS_HASH,
        }
        event["event_hash"] = _event_hash(event)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.ledger_path.open("a", encoding="utf-8", newline="") as stream:
                serialized = json.dumps(
                    event,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.write(serialized + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise ReviewWorkflowError(f"cannot append review event: {exc}") from exc
        return event

    def _read_queue(self) -> list[dict[str, str]]:
        try:
            with self.queue_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise ReviewWorkflowError(f"cannot read review queue: {exc}") from exc
        seen: set[str] = set()
        for row in rows:
            evidence_id = row.get("evidence_id", "").strip()
            if not evidence_id or evidence_id in seen:
                raise ReviewWorkflowError(
                    f"missing or duplicate queue evidence ID: {evidence_id!r}"
                )
            seen.add(evidence_id)
        return rows

    def _record(self, evidence_id: str) -> dict[str, str]:
        for record in self._read_queue():
            if record.get("evidence_id") == evidence_id:
                return record
        raise ReviewWorkflowError(f"unknown evidence ID: {evidence_id}")

    @staticmethod
    def _validate_human_action(
        reviewer_name: str,
        reviewer_expertise: str,
        review_date: str,
        rationale: str,
        inspections: Sequence[Mapping[str, str]],
        confirmed_human_action: bool,
    ) -> None:
        if not confirmed_human_action:
            raise ReviewWorkflowError("an explicit human action confirmation is required")
        if not reviewer_name.strip() or not reviewer_expertise.strip():
            raise ReviewWorkflowError("reviewer name and relevant expertise are required")
        try:
            parsed_date = date.fromisoformat(review_date)
        except (TypeError, ValueError) as exc:
            raise ReviewWorkflowError("review_date must be a real YYYY-MM-DD date") from exc
        if parsed_date != date.today():
            raise ReviewWorkflowError(
                "review_date must be today's date; backdated decisions are not accepted"
            )
        if not rationale.strip():
            raise ReviewWorkflowError("a reviewer rationale is required")
        if not inspections:
            raise ReviewWorkflowError("at least one source/text inspection scope is required")
        _normalize_inspections(inspections)

    @staticmethod
    def _latest_decisions(events: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for event in events:
            if event.get("event_type") == "decision":
                latest[str(event["evidence_id"])] = dict(event)
        return latest

    @staticmethod
    def _correction_status(events: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
        status: dict[str, dict[str, str]] = {}
        for event in events:
            if event.get("event_type") == "correction_requested":
                status.setdefault(str(event["evidence_id"]), {})[str(event["event_id"])] = "open"
            elif event.get("event_type") == "correction_verified":
                per_record = status.setdefault(str(event["evidence_id"]), {})
                correction_id = str(event["correction_event_id"])
                if correction_id not in per_record:
                    raise ReviewWorkflowError("correction verification refers to a missing request")
                per_record[correction_id] = "verified"
        return status


def _normalize_inspections(inspections: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for inspection in inspections:
        row = {
            key: str(inspection.get(key, "")).strip()
            for key in ("source_id", "locator", "scope")
        }
        if not all(row.values()):
            raise ReviewWorkflowError("each inspection needs source_id, locator, and access scope")
        normalized.append(row)
    return normalized


def _event_hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reconcile_queue_events(
    records: Sequence[Mapping[str, str]],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    queue_ids = {str(record.get("evidence_id", "")) for record in records}
    event_ids = {str(event.get("evidence_id", "")) for event in events}
    decided_ids = {
        str(event["evidence_id"])
        for event in events
        if event.get("event_type") == "decision" and event.get("evidence_id")
    }
    return {
        "queue_records": len(queue_ids),
        "events": len(events),
        "decided_queue_records": len(queue_ids.intersection(decided_ids)),
        "pending_queue_records": len(queue_ids - decided_ids),
        "event_evidence_ids_not_in_queue": sorted(event_ids - queue_ids),
    }


def _parse_inspections(values: Sequence[str]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for value in values:
        parts = value.split("|", maxsplit=2)
        if len(parts) != 3:
            raise ReviewWorkflowError("inspection must use SOURCE_ID|LOCATOR|ACCESS_SCOPE")
        parsed.append(dict(zip(("source_id", "locator", "scope"), parts)))
    return _normalize_inspections(parsed)


def _add_human_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--reviewer",
        required=True,
        help="Human reviewer name, as supplied by the reviewer",
    )
    parser.add_argument(
        "--expertise",
        required=True,
        help="Reviewer affiliation or relevant expertise",
    )
    parser.add_argument(
        "--review-date",
        required=True,
        help="Date of the human action, YYYY-MM-DD (must be today)",
    )
    parser.add_argument(
        "--inspection",
        action="append",
        required=True,
        metavar="SOURCE_ID|LOCATOR|SCOPE",
        help="Source or textual evidence actually inspected; repeat for each item",
    )
    parser.add_argument(
        "--confirm-human-action",
        action="store_true",
        help="Confirm this is an actual human action",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    listing = subparsers.add_parser("list", help="Search or filter the pending queue")
    listing.add_argument("--book")
    listing.add_argument("--priority")
    listing.add_argument("--evidence-type")
    listing.add_argument("--source-access")
    listing.add_argument("--source-outcome")
    listing.add_argument("--query")
    listing.add_argument("--limit", type=int, default=25)
    listing.add_argument("--offset", type=int, default=0)

    showing = subparsers.add_parser("show", help="Open one record and its exact packet")
    showing.add_argument("evidence_id")
    subparsers.add_parser(
        "progress",
        help="Summarize human decisions and correction status",
    )
    exporting = subparsers.add_parser(
        "export",
        help="Export actual decisions and their event history",
    )
    exporting.add_argument("--format", choices=("json", "csv"), default="json")

    snapshot = subparsers.add_parser(
        "snapshot",
        help="Create a versioned, no-overwrite review-history snapshot",
    )
    snapshot.add_argument("--output", required=True, type=Path)

    snapshot_check = subparsers.add_parser(
        "verify-snapshot",
        help="Verify snapshot structure and chain, optionally against an external SHA-256",
    )
    snapshot_check.add_argument("snapshot", type=Path)
    snapshot_check.add_argument("--trusted-sha256")

    restore = subparsers.add_parser(
        "restore-snapshot",
        help="Append a valid snapshot suffix after explicit confirmation",
    )
    restore.add_argument("snapshot", type=Path)
    restore.add_argument("--confirm-restore", action="store_true")
    restore.add_argument("--trusted-sha256")

    subparsers.add_parser("status", help="Report chain integrity and queue reconciliation")

    decision = subparsers.add_parser("decision", help="Record one explicit human decision")
    decision.add_argument("evidence_id")
    decision.add_argument("--decision", choices=tuple(DECISIONS), required=True)
    decision.add_argument("--rationale", required=True)
    decision.add_argument("--required-corrections-or-follow-up", default="")
    _add_human_arguments(decision)

    correction = subparsers.add_parser(
        "correction-request",
        help="Record an attributed correction request",
    )
    correction.add_argument("evidence_id")
    correction.add_argument("--requested-change", required=True)
    correction.add_argument("--rationale", required=True)
    _add_human_arguments(correction)

    verification = subparsers.add_parser(
        "verify-correction",
        help="Record later verification of a correction",
    )
    verification.add_argument("evidence_id")
    verification.add_argument("--correction-event-id", required=True)
    verification.add_argument("--rationale", required=True)
    verification.add_argument(
        "--change-reference",
        required=True,
        help="CKL path/field or commit containing the change",
    )
    verification.add_argument(
        "--corrected-text",
        required=True,
        help="Exact corrected wording inspected",
    )
    _add_human_arguments(verification)
    return parser


def _print_records(records: Sequence[Mapping[str, str]], *, limit: int, offset: int) -> None:
    if limit < 1 or offset < 0:
        raise ReviewWorkflowError("limit must be positive and offset cannot be negative")
    page = records[offset : offset + limit]
    if not page:
        print("No matching review records.")
        return
    print(
        "EVIDENCE ID | BOOK | ANCHOR | PRIORITY | TYPE | MACHINE OUTCOME | "
        "SOURCE ACCESS | HUMAN REVIEW | PACKET"
    )
    for record in page:
        print(
            " | ".join(
                record.get(field, "")
                for field in (
                    "evidence_id",
                    "book_id",
                    "scripture_anchor",
                    "recommended_review_priority",
                    "evidence_type",
                    "ed3_verification_outcome",
                    "ed3_source_access_class",
                    "review_workbench_status",
                    "review_packet_path",
                )
            )
        )
    print(f"Showing {offset + 1}-{offset + len(page)} of {len(records)} matching record(s).")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workbench = ReviewWorkbench()
    try:
        if args.command == "list":
            records = workbench.list_records(
                book=args.book,
                priority=args.priority,
                evidence_type=args.evidence_type,
                source_access=args.source_access,
                source_outcome=args.source_outcome,
                query=args.query,
            )
            _print_records(records, limit=args.limit, offset=args.offset)
        elif args.command == "show":
            detail = workbench.show(args.evidence_id)
            print(f"Packet: {detail['packet_path']}")
            print(
                f"Evidence: {detail['record']['evidence_id']} | "
                f"{detail['record']['scripture_anchor']}"
            )
            print(detail["packet_text"], end="")
            if detail["history"]:
                print("\n## Recorded review events\n")
                for event in detail["history"]:
                    print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
        elif args.command == "progress":
            print(json.dumps(workbench.progress(), indent=2, sort_keys=True))
        elif args.command == "export":
            exported = (
                workbench.export_json()
                if args.format == "json"
                else workbench.export_decisions_csv()
            )
            print(exported, end="")
        elif args.command == "snapshot":
            report = workbench.create_snapshot(args.output)
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "verify-snapshot":
            report = workbench.verify_snapshot(
                args.snapshot,
                trusted_sha256=args.trusted_sha256,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "restore-snapshot":
            report = workbench.restore_snapshot(
                args.snapshot,
                confirmed=args.confirm_restore,
                trusted_sha256=args.trusted_sha256,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "status":
            print(json.dumps(workbench.status_report(), indent=2, sort_keys=True))
        elif args.command == "decision":
            event = workbench.record_decision(
                evidence_id=args.evidence_id,
                reviewer_name=args.reviewer,
                reviewer_expertise=args.expertise,
                review_date=args.review_date,
                decision=args.decision,
                rationale=args.rationale,
                inspections=_parse_inspections(args.inspection),
                confirmed_human_action=args.confirm_human_action,
                required_corrections_or_follow_up=args.required_corrections_or_follow_up,
            )
            print(f"Recorded human decision event {event['event_id']} ({event['decision_label']}).")
        elif args.command == "correction-request":
            event = workbench.request_correction(
                evidence_id=args.evidence_id,
                reviewer_name=args.reviewer,
                reviewer_expertise=args.expertise,
                review_date=args.review_date,
                requested_change=args.requested_change,
                rationale=args.rationale,
                inspections=_parse_inspections(args.inspection),
                confirmed_human_action=args.confirm_human_action,
            )
            print(f"Recorded correction request event {event['event_id']}.")
        elif args.command == "verify-correction":
            event = workbench.verify_correction(
                evidence_id=args.evidence_id,
                correction_event_id=args.correction_event_id,
                reviewer_name=args.reviewer,
                reviewer_expertise=args.expertise,
                review_date=args.review_date,
                verification_rationale=args.rationale,
                change_reference=args.change_reference,
                corrected_text=args.corrected_text,
                inspections=_parse_inspections(args.inspection),
                confirmed_human_action=args.confirm_human_action,
            )
            print(f"Recorded correction verification event {event['event_id']}.")
    except ReviewWorkflowError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
