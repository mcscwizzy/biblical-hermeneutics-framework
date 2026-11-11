# ED-3 Scholarly Integrity and Research Quality

ED-3 is a source-verification and quality-assurance program for the 99 evidence
items added by ED-2, inherited CKL provenance, reader disclosure, and future
research priorities. It does not confer human scholarly approval.

## Status

Phases 0–2 are committed on the fetched ED-2 merge. Phase 1 reconciles all 99
additions to stable CKL evidence IDs, anchors, source records, locators,
research packets, reported access categories, review state, and reader
projection. Fresh source material was independently inspected for 30 records;
69 reported full-text records were not freshly reproduced. Phase 2
rechecked every access-limited group and documents the remaining article and
primary-witness gaps. Phase 3 repaired two exact local source references and
the stale Psalm 17 access note; the 102 inherited target heuristics remain
open. All outcomes are machine-assisted, 71 records remain unable to be
independently verified, and all additions remain draft, in review, and
human-review required. Semantic re-reading of every passage and primary-witness
verification remain open.

## Navigation

- [Baseline and reproducible fingerprint](baseline.md)
- [Phase ledger](progress.json)
- [ED-2 evidence review inventory](evidence-review-inventory.csv)
- [Source verification](source-verification.md)
- [Inherited source integrity findings](source-integrity-findings.md)
- [Source integrity fixes](source-integrity-fixes.md)
- [Row-level source-target findings](supporting/source-support-targets.csv)
- [Sparse bibliography triage](supporting/sparse-bibliography-triage.csv)
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
