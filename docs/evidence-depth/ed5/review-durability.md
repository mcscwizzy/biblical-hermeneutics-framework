# ED-5 review-history durability

`tools/ed4_review_workbench.py` now supports a versioned JSON snapshot,
read-only snapshot verification, explicit append-only restore, and queue
status reconciliation.

## Maintainer procedure

Use a private, access-controlled destination outside the repository. The
snapshot contains reviewer names, expertise, decisions, rationales, and source
inspection notes. The CLI creates a new file exclusively and sets mode 0600;
it refuses to replace an existing versioned file.

```bash
.venv/bin/python tools/ed4_review_workbench.py status
.venv/bin/python tools/ed4_review_workbench.py snapshot \
  --output /secure/private-location/ed4-review-2026-11-11-v1.json
sha256sum /secure/private-location/ed4-review-2026-11-11-v1.json
.venv/bin/python tools/ed4_review_workbench.py verify-snapshot \
  /secure/private-location/ed4-review-2026-11-11-v1.json
```

Record the printed snapshot SHA-256 in a separate trusted location controlled
by the maintainer (for example, an organizational credential vault or
separately protected records system), and retain another encrypted backup in
a different failure domain. Do not store only the snapshot and its digest
together: anyone able to replace both could recalculate the digest. The local
hash chain detects inconsistent edits inside the file; it does not establish
who reviewed it, authenticate a reviewer, prevent full replacement, or detect
tail truncation without an independently retained checkpoint.

To check against the separately retained digest:

```bash
.venv/bin/python tools/ed4_review_workbench.py verify-snapshot \
  /secure/private-location/ed4-review-2026-11-11-v1.json \
  --trusted-sha256 TRUSTED_DIGEST
```

Restore only after reviewing the verification and queue report and explicitly
choosing to import:

```bash
.venv/bin/python tools/ed4_review_workbench.py restore-snapshot \
  /secure/private-location/ed4-review-2026-11-11-v1.json \
  --trusted-sha256 TRUSTED_DIGEST --confirm-restore
.venv/bin/python tools/ed4_review_workbench.py status
```

Restore validates the snapshot before writing, accepts an identical existing
prefix, appends only the missing suffix, reports duplicate prefix events, and
refuses an older or conflicting history. It does not overwrite the ledger.
Malformed JSON, sequence summaries, duplicate event IDs, hash-chain failures,
and an incorrect external digest are rejected. A syntactically valid snapshot
with a recomputed unanchored hash is still not authenticated.

## Test and current data status

Snapshot creation, permission mode, no-overwrite behavior, verification,
explicit restore, suffix append, idempotent prefix reconciliation, conflict
preservation, malformed/truncated rejection, duplicate IDs, and pending-queue
counts are tested with temporary synthetic fixtures. The real `.bhf-data`
ledger remains absent; no human decision was entered. At baseline, status
reports 0 events and 99 pending queue records. ED-5 did not write review
history or reviewer identity into Git.
