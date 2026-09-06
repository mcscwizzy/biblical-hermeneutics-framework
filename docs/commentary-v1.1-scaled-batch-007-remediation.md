# Commentary v1.1 Batch 007 bounded remediation

Batch 007 began with 143 PASS and 7 QUARANTINE chapters. Every quarantine was
the allowlisted `READER_UNFRIENDLY` quality finding; no evidence-lock,
provenance, CKL, or hash blocker was present. The bounded Terra Medium policy
was preserved: one automatic attempt per chapter, with no more than three
chapters in any runner invocation.

## Deterministic groups

| Group | References | Attempt |
| --- | --- | --- |
| `group-001` | Deuteronomy 32; 1 Samuel 4; 2 Chronicles 32 | 1 |
| `group-002` | Psalms 119; Isaiah 65; Ezekiel 40 | 1 |
| `group-003` | Daniel 10 | 1 |

Each group has its own report and immutable original archive under
`batch-007/terra/remediation-attempts/attempt-001/<group-id>/`. The canonical
consolidated report is `batch-007/remediation-report.json`; the historical
group reports remain in place.

## Remediation result

The defect was an orchestration contract mismatch: the orchestrator supplied
seven references to a runner that correctly accepts only one to three. The
repair added deterministic canonical chunking, group-scoped output/report
paths, durable group checkpoints, recovery of a completed report after an
interruption, and per-chapter attempt accounting. The runner’s safety limit and
validation gates were retained. Its interrupted-promotion recovery compares
semantic chapter content while ignoring only the regenerated timestamp, so an
existing immutable archive cannot be silently replaced.

For every target chapter:

- initial finding: `READER_UNFRIENDLY`
- replacement quality flags: none
- presentation/evidence role: unchanged
- evidence IDs: identical before, after, and locked
- evidence hash: identical before, after, and locked
- original prose: preserved at the group archive path recorded in the JSON report
- final disposition: `PASS`

No CKL content, CKL metadata, evidence bundle, locked evidence selection, or
previously certified prose was changed. The 143 initially passing chapters
were not remediation targets.

## Full recertification

The unchanged post-generation audit was rerun across all 150 Batch 007
chapters, not only the seven replacements:

- PASS: 150
- QUARANTINE: 0
- REGENERATE: 0
- DATA_GAP: 0
- `READER_UNFRIENDLY`: 0
- lock revalidation: 150/150
- stale locks: 0
- evidence/provenance/hash findings: 0
- protected fingerprints: unchanged

Batch 007 is certified GO and complete. Batch 008 is initialized at its normal
Luna-controlled `CANDIDATE_SELECTION` stage; no Batch 008 prose was generated.
