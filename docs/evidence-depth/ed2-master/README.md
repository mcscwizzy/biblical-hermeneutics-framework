# ED-2 Master Evidence Expansion

This is the working ledger for the comprehensive evidence-enrichment branch. It records a reproducible ED-1A baseline, a 1,189-chapter prioritization inventory, source-verification packets, batch gates, and open research. A chapter inventory row describes current eligible CKL material; it is not a scholarly-completeness score. A new record is added only when a precise question and verified source justify it.

## Program state

- Branch: `feat/ed2-comprehensive-evidence-expansion`
- Base: `origin/master` at `04eed56ece941f9efce2f7f05b3908baf0197648`; ED-2A is already merged in PR #76.
- Baseline audit: all 1,189 chapters; 687 CKL objects; 2,329 claims; 1,309 typed evidence items.
- Current phase and per-wave status: [progress.json](progress.json).
- Chapter-level triage: [research-backlog.csv](research-backlog.csv).

## Wave directories

- [Wave A — Psalms](wave-a-psalms/)
- [Wave B — Wisdom literature](wave-b-wisdom/)
- [Wave C — Historical books](wave-c-history/)
- [Wave D — Prophetic literature](wave-d-prophets/)
- [Wave E — Gospels and New Testament](wave-e-new-testament/)

## Reports

- [Baseline](baseline.md)
- [Source register and access limits](sources.md)
- [Before/after coverage](coverage-before-after.md)
- [Validation history](validation-results.md)
- [Deferred research](deferred-research.md)
- [Final review](final-review.md)

Every addition remains draft/in-review and requires human review. No reviewed NE-9C/NE-10 decision may be changed by this program. Archaeological catalog metadata remains owned by the archaeology service.

Latest completed batch: E2 (Luke 8 and 13), evidence commit `372a642e`. Since the ED-2A baseline, the program has added 93 evidence items (78 Psalms, 4 Wisdom, 3 History, 3 Prophets, 5 New Testament) from 92 new scholarly source identities and reused 5 scholarly identities. The last complete ED-1A census, after E1, reported 1,084 passage-specific chapters, 57 contextual-only, 2 entity-only, 45 no-eligible, and 1 incomplete/unknown. Exact-anchor tests project Luke 8 and 13 to passage-specific eligibility; the full census will be rerun after Wave E’s final batch. Coverage labels are eligibility counts, not completeness scores. Waves A–E remain in progress. Wave B still has nine Proverbs zero-eligible chapters and Wave A has 11 contextual-only Psalms pending qualitative review.
