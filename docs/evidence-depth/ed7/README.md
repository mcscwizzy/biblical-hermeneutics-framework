# ED-7 — Reader-First Research Cleanup

ED-7 makes the Narrative Explorer a Bible study companion first. It keeps its
six topic areas, chapter Location quick glance, exact source records, Scripture
relationships, and uncertainty while moving research workflow detail out of
ordinary reading cards.

## Program state

- Base: `origin/master` at `c0b6cb25c7a78447459cafd0619b333b7c749e9e` (ED-6 PR
  #82 merge, 2026-11-16).
- Branch: `feat/ed7-reader-first-evidence-triage`.
- The ED-3 human-review queue remains 99 pending records. ED-7 records machine
  audit findings only; no human approval or peer review was recorded.
- CKL objects, sources, and accepted/held relationships were not changed.
- No merge or deployment is part of ED-7.

## What changed

The opening view now leads with up to three source-checked discoveries, then a
plain-language path to passage connections and the same six study topics. The
current policy features two discoveries; legitimate contextual records remain
available on demand, and records without adequate support for promotion are
withheld from reader promotion without being deleted. “How we know” discloses
the cited works and material access limits. Detailed record IDs, review-state
labels, and evidence diagnostics remain in research and maintainer workflows.

## Reports

- [Baseline](baseline.md)
- [Reader clutter audit](reader-clutter-audit.md)
- [AI-assisted source audit](ai-source-audit.md)
- [Record-level verification results](source-verification-results.json)
- [Reader presentation policy](reader-presentation-policy.md)
- [Before and after reader experience](before-after-reader-experience.md)
- [Withheld research report](withheld-research-report.md)
- [Validation results](validation-results.md)
- [Final report](final-report.md)
- [Progress ledger](progress.json)

The [screenshots](screenshots/) and [journey measurements](screenshots/journey-metrics.json)
show deterministic browser states, not participant comprehension or usability
outcomes. ED-6's participant study remains independent and ready for use.
