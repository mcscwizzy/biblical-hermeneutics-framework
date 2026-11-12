# ED-5 — Discovery Experience

ED-5 evaluates how a reader moves from a Scripture passage to its available
context, source evidence, approved passage connections, and next question. It
makes bounded presentation and review-history portability improvements while
preserving CKL research and relationship governance.

## Reports

- [Baseline](baseline.md) and [reader journeys](reader-journeys.md)
- [Usability baseline](usability-baseline.md), [discovery findings](discovery-findings.md), and [before/after results](before-after-results.md)
- [Reader improvements](reader-improvements.md) and [clarity and terminology](clarity-and-terminology.md)
- [Connection journeys](connection-journeys.md) and [reader quality scorecard](reader-quality-scorecard.md)
- [Review durability](review-durability.md) and [reviewer pilot](reviewer-pilot.md)
- [Validation results](validation-results.md), [progress ledger](progress.json), and [final report](final-report.md)

The reusable projection and retrieval suite is `scripts/ed5_reader_evaluation.py`;
its isolated regression is `tests/test_ed5_reader_evaluation.py`. It checks
checked-in CKL records and routes in process. It is not a human study or a
browser-rendering measurement.

## Decision boundary

No CKL object, source identity, evidence classification, curation, bridge, or
review decision was changed. All 99 records still require independent human
review. The review ledger is local data and was not created or committed by
this assignment. No merge or deployment is included.
