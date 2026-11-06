# ED-1C — Evidence Discoverability and Reader Accessibility

ED-1C addresses a reader-path gap: some source-backed CKL child records already
matched the selected passage in the Narrative Explorer API but had no section
assignment and no passage-specific route in the reader. A collapsed
“Additional sourced records” disclosure now makes those records available on
request while preserving their existing classification, identity, scope, and
provenance.

## Reports

- [Baseline and classification analysis](01-baseline-and-classification.md)
- [Before/after projection and prioritized backlog](03-before-after-and-backlog.md)
- [Desktop and mobile reader acceptance](04-reader-acceptance.md)
- [Regression and integrity results](05-regression-results.md)
- [Implementation plan](02-implementation-plan.md)

## Outcome

The reproduced baseline was 12,665 eligible CKL item-to-chapter placements,
11,642 section-assigned placements, and 1,023 unassigned placements across 394
chapters. ED-1C changes reader presentation only. It does not change CKL data,
section assignments, API responses, source records, NE-9C curation, or NE-10
bridge decisions. The unassigned count is therefore still 1,023; the goal was
to make eligible existing records findable, not to eliminate unclassified
material.

The browser acceptance case is 1 Corinthians 11:3 and
`ckl:1-corinthians#claim:1cor-kephale`. Desktop and mobile tests confirmed the
disclosure starts closed, presents the record once after activation, retains
its applicable passage relationship and source identities, displays
“Lexical research” from its structured claim type, and preserves its disputed
status.
