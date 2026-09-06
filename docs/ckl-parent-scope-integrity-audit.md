# CKL Parent-Scope Integrity Audit

Date: 2026-09-06

## Decision

`BATCH_007_REMAINS_BLOCKED`

The scope remediation is successful, but four chapters still fail the existing hardened presentation/textual-routing gates. Batch 007 was not unlocked and no Terra prose was generated.

## What was wrong

CKL parent retrieval established conceptual relatedness, but legacy parent fields were then exposed as if they were passage-valid child evidence. This conflated:

- a concept being related to a passage;
- a child record being anchored to that passage; and
- evidence being eligible for presentation and Terra handoff.

The same issue affected broad word-study parent fields. A lemma parent was not sufficient proof that the lexical item was present or contextually operative in the requested passage. A separate backend issue also made source collisions depend on JSON/SQLite traversal order, producing bundle-hash disagreements without evidence-ID disagreement.

## Changes

The smallest compatible correction was a deterministic retrieval/projection policy; no CKL schema extension was required.

- Structured child records derive `applicability_scope` from their own anchors: `passage`, `section`, or `book`.
- Legacy inherited fields are explicitly broad `global`, `book`, `entity`, or `lexical` scope and cannot become passage evidence merely because the parent was retrieved.
- Legacy word-study fields without an explicit child anchor fail closed.
- Passage-scoped claim ranking now requires an authored overlapping Scripture anchor.
- Cross-book auditing continues to block inherited direct evidence, while allowing explicit global/entity background and anchored child evidence under their declared scope.
- Source-ID collisions are canonically merged by sorted source payload and sorted canonical object IDs, with source variants retained for provenance.
- The orchestrator now distinguishes total protected finalized controls from eligible finalized chapters. The corrected state is 691 total protected controls, 678 eligible finalized chapters, and 257 unresolved eligible chapters.

No CKL JSON or SQLite records were rewritten, no citations or provenance were removed, and historical quarantine artifacts were not modified.

## Corpus accounting

| Set | Count |
|---|---:|
| Low-information population | 1,088 |
| Eligible corpus | 935 |
| Eligible finalized | 678 |
| Unresolved eligible | 257 |
| Regular generated | 665 |
| Released canary controls | 26 |
| Total protected finalized controls | 691 |
| Intentional exclusions outside eligible | 153 |
| Historical quarantined chapters | 257 |

The historical quarantine set is disjoint from finalized controls. The eligible invariant is `935 = 678 + 257`; the 153 intentional exclusions are outside the eligible set and are not used to force that equation to balance.

## Scope and integrity results

| Finding | Before | After |
|---|---:|---:|
| `CROSS_BOOK_PARENT_REUSE` | 5,183 | 0 |
| `WORD_STUDY_BROAD_PARENT_ANCHOR` | 400 | 0 |
| JSON/SQLite bundle-hash disagreements | 36 | 0 |
| Presentation-role raw findings | 7 | 7 |
| Textual-routing raw findings | 7 | 7 |
| Terra suppression chapter signals | 4 | 4 |

The parent impact report contains 369 affected parent records: 319 cross-book parents and 50 word-study parents, with no parent overlap between those two finding classes. The remediation plan marks 339 parent groups as deterministically handled by projection/retrieval policy and 30 as conservative human-review groups. No CKL records required migration.

The prior hash disagreements were handled separately from semantic scope repair. The repaired canonical source merge restores JSON/SQLite parity without rewriting evidence hashes to force agreement. Numbers 1 and Numbers 10 are no longer blocked by those hash disagreements.

## Post-remediation adjudication

The same Luna High preflight and quarantine recovery machinery evaluated the same 257 historical chapters:

| Disposition | Count |
|---|---:|
| `RECOVERABLE` | 253 |
| `STILL_QUARANTINED` | 4 |
| `REQUIRES_CKL_REMEDIATION` | 0 |
| `DATA_GAP` | 0 |
| `ALREADY_RESOLVED` | 0 |

Remaining chapters:

- Deuteronomy 32
- Numbers 6
- Isaiah 40
- Psalms 119

All four retain presentation-role and textual-routing blockers, plus the corresponding Terra suppression signal. These are not being reclassified as CKL scope successes.

Machine-readable artifacts are under `.bhf-data/bhf-commentary-candidates/commentary-v1.1-scale/ckl-scope-audit/`:

- `corpus-accounting-report.json`
- `parent-scope-impact-report.json`
- `word-study-scope-overlap-report.json`
- `ckl-scope-remediation-plan.json`
- `ckl-scope-remediation-result.json`
- `evidence-hash-reconciliation-report.json`
- `post-remediation-quarantine-adjudication.json`

## Validation

Targeted scope, retrieval, recovery, preflight, hashing, accounting, and orchestrator tests passed. The isolated scaled preflight completed with the preserved Luna High workflow and unchanged protected canary/Batch 001–003 fingerprints. The authoritative pipeline remains blocked in Batch 007 candidate selection; it was not advanced.

Recommended next action: remediate the four remaining presentation/textual-routing cases, then rerun the same hardened quarantine adjudication. Do not begin Terra generation until those gates independently pass.
