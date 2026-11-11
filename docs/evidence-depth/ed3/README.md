# ED-3 Scholarly Integrity and Research Quality

ED-3 is a source-verification and quality-assurance program for the 99 evidence
items added by ED-2, inherited CKL provenance, reader disclosure, and future
research priorities. It does not confer human scholarly approval.

## Status

Phase 0 is baselined on the fetched ED-2 merge. The machine-assisted review
inventory reconciles all 99 additions to stable CKL evidence IDs and preserves
ED-2's reported source-access categories as historical claims awaiting fresh
verification. Detailed source review, provenance triage, and reader acceptance
are in progress. All ED-2 additions remain draft, in review, and human-review
required.

## Navigation

- [Baseline and reproducible fingerprint](baseline.md)
- [Phase ledger](progress.json)
- [ED-2 evidence review inventory](evidence-review-inventory.csv)
- [Source verification](source-verification.md)
- [Inherited source integrity findings](source-integrity-findings.md)
- [Source integrity fixes](source-integrity-fixes.md)
- [Scholarly corrections](scholarly-corrections.md)
- [Human review queue](human-review-queue.csv)
- [Reusable human review process](human-review-process.md)
- [Reader and mobile acceptance](reader-acceptance.md)
- [Research depth priorities](research-depth-priorities.md)
- [Validation results](validation-results.md)
- [Final report](final-report.md)
- Reviewer packets are grouped by ED-2 wave under `review-packets/`.

## Assessment language

The verification outcomes in the CSV are machine-assisted status labels, not
scholarly approval. Source access is scoped to the material actually inspected:
full text, excerpt, abstract, metadata, secondary report, primary edition or
artifact, or unavailable. An ED-2 packet's historical access statement is kept
separate from ED-3's fresh inspection record.

The CKL's current governance fields remain authoritative: `content_status`,
`review_status`, `reviewed_by`, `last_reviewed`, and
`human_review_required`. CKL child evidence inherits review state from its
parent object unless child-level state is explicitly present. `reviewed` or
`approved` requires actual review metadata; ED-3 does not write that state.
NE-9C relationship decisions and NE-10 passage bridges are separate reviewed
registries and are not changed by this audit.
