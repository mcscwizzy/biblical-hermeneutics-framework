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

Latest completed batch: A13 (Psalms 34, 40, 73, and 78), evidence commit `d892a7d2`. Since the ED-2A baseline, Wave A has added 78 evidence items from 77 new scholarly source identities and reused 3 existing identities. The all-chapter census reports 1,071 passage-specific chapters, 57 contextual-only, 2 entity-only, 58 no-eligible, and 1 incomplete/unknown. Psalms has 139 specific chapters and 11 contextual-only; the A13 census found no entity-only Psalm chapter. These are eligibility counts, not completeness scores. The 11 contextual-only Psalms remain in qualitative triage while Waves B–E proceed.
