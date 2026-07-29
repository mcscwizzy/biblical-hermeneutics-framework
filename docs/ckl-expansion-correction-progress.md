# CKL Expansion and Correction Progress

Last updated: 2026-07-28

This is the durable handoff for the **BHF Canonical Knowledge Library Expansion
and Correction Plan**. The supplied plan explicitly says to begin with the
repository audit and Phase 1 quality reporting, avoid immediate bulk content
generation, and stop after each major phase. Phases 1–4 are now implemented at
the schema/runtime level. Phase 5 Waves 1–49 have corrected Genesis through
Hebrews as honest, source-backed drafts; none has been mechanically
approved.

## Current checkpoint

| Plan area | Status | Continuation note |
| --- | --- | --- |
| Phase 1: inventory, reporting, quality metrics | **Implemented** | Deep JSON and Markdown reports, CLI support, and calculation tests are present. |
| Phase 2: section-level completeness | **Implemented; content migration pending** | Additive `section_status`, type-specific rules, readiness helpers, approval gates, audit warnings, and tests are present. Fifty-seven records now have evidence-based draft statuses; 563 still need explicit migration. |
| Phase 3: knowledge-layer classification | **Implemented; content migration pending** | Controlled primary/secondary layers flow through JSON, retrieval, prompt context, and SQLite payloads. Fifty-seven records now have explicit layers; 563 still need migration. |
| Phase 4: certainty and dispute taxonomies | **Implemented; evidence migration pending** | Current taxonomies and granular claim records are supported. Legacy values remain readable but are forbidden for approved notes; no `unknown` value was guessed or mass-relabeled. |
| Phase 5: audit/correct all 66 books | **Waves 1–49 implemented; human review pending** | Genesis through Hebrews are corrected drafts with sources, claims, tests, and reviewer notes. Nine books remain. |
| Phases 6–20 | Not started | Follow the supplied order after the foundation is upgraded. |
| Phase 21: controlled generation workflow | Partially enabled | Reporting, type-specific completeness, and approval gates are present; scoped human-review events still need Phase 19. |

The generated reports are:

- [Human-readable quality baseline](ckl-quality-report.md)
- [Machine-readable quality baseline](ckl-quality-report.json)

Regenerate them from the repository root:

```bash
python3 tools/ckl_report.py \
  --root framework/canonical_library \
  --deep \
  --output docs/ckl-quality-report.md

python3 tools/ckl_report.py \
  --root framework/canonical_library \
  --deep \
  --json \
  --output docs/ckl-quality-report.json
```

## Phase 1 work completed

The new deep reporter measures:

- object totals and category distribution;
- populated, empty, and missing leaf fields by category;
- average summary length, Scripture references, external sources, and graph
  relationships;
- dangling relationships, missing reciprocal relationships, and orphaned
  records;
- current required-field gaps and candidate Phase 2 section gaps among records
  marked complete;
- unknown interpretive certainty and dispute values;
- absent human reviewers and required human review;
- exact and near-duplicate titles and summaries;
- duplicate aliases and cross-type alias collisions;
- missing retrieval search terms, common questions, and canonical placement;
- suspicious exact template repetition in high-value fields;
- Scripture-reference validation findings;
- unresolved legacy object references;
- unresolved source IDs used by interpretive notes or future claim records;
- source records that support no field or claim;
- internal CKL self-citation without external support;
- type/directory and ID/filename inconsistencies; and
- all findings from the pre-existing validator.

The existing non-deep `ckl_report.py` behavior remains unchanged. `--deep`
activates the new report, `--json` selects its machine-readable form, and
`--output` persists either format.

## Baseline and current migration findings

The 2026-07-24 Phase 1 baseline reports:

| Metric | Result |
| --- | ---: |
| JSON records scanned | 620 |
| Schema-valid unique records | 620 |
| Records marked `complete` | 620 |
| Records marked `in_review` | 620 |
| Records requiring human review | 620 |
| Records with no `reviewed_by` entry | 619 |
| Complete records missing fields required by the current shallow rule | 0 |
| Complete records with candidate Phase 2 section gaps | 619 |
| Records containing unknown certainty | 549 |
| Records containing unknown dispute status | 549 |
| Interpretive notes with unknown certainty/dispute | 1,189 / 1,189 |
| Objects without retrieval search terms | 613 |
| Objects without canonical placement | 547 |
| Graph edges | 3,022 |
| Dangling graph targets | 0 |
| Missing reciprocal graph relationships | 2,634 |
| External sources per object (average) | 0.49 |
| Sources supporting no field or claim | 2,752 |
| Internally self-cited records without external support | 466 |
| Suspicious template-repetition groups | 43 |
| Scripture reference format/range errors | 0 |
| Type/path inconsistencies | 0 |

These measurements explain why the old validation output can report zero
errors while the library still needs substantial correction. The existing
records are still valid legacy inputs, while the new section rules expose their
migration debt as warnings and prevent them from becoming approved without
completing the required sections.

The pre-content-migration Phase 4 report recorded:

| Migration metric | Result |
| --- | ---: |
| Raw records missing explicit `section_status` | 620 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 620 |
| Interpretive notes using current certainty/dispute taxonomies | 0 |
| Interpretive notes still using legacy taxonomies | 1,318 |
| Granular claims currently authored | 0 |
| Validator warnings after coalescing by representative object/section | 14 |
| Validator errors | 0 |

These are expected migration counts. Runtime defaults keep old records
loadable, but defaults do not constitute evidence, review, or content
completion.

After Phase 5 Wave 1, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 618 / 2 |
| Raw records missing explicit `section_status` | 618 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 618 |
| Interpretive notes using current taxonomies | 8 |
| Interpretive notes still using legacy taxonomies | 1,314 |
| Granular claims authored | 9 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,040 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

The incomplete-section count remains 620 by design: Genesis and Exodus are
substantively improved but have not received human review, while the other 618
records still rely on migration defaults.

After Phase 5 Wave 2, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 616 / 4 |
| Raw records missing explicit `section_status` | 616 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 616 |
| Interpretive notes using current taxonomies | 17 |
| Interpretive notes still using legacy taxonomies | 1,310 |
| Granular claims authored | 20 |
| External sources | 318 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,060 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All four corrected books remain incomplete because their human-review sections
are still `missing`. The remaining 616 records still rely on section/layer
migration defaults.

After Phase 5 Wave 3, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 614 / 6 |
| Raw records missing explicit `section_status` | 614 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 614 |
| Interpretive notes using current taxonomies | 26 |
| Interpretive notes still using legacy taxonomies | 1,306 |
| Granular claims authored | 30 |
| External sources | 324 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,074 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All six corrected books remain incomplete because their human-review sections
are still `missing`. The remaining 614 records still rely on section/layer
migration defaults.

After Phase 5 Wave 4, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 612 / 8 |
| Raw records missing explicit `section_status` | 612 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 612 |
| Interpretive notes using current taxonomies | 36 |
| Interpretive notes still using legacy taxonomies | 1,302 |
| Granular claims authored | 42 |
| External sources | 330 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,085 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All eight corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 612 records still rely on
section/layer migration defaults.

After Phase 5 Wave 5, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 610 / 10 |
| Raw records missing explicit `section_status` | 610 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 610 |
| Interpretive notes using current taxonomies | 46 |
| Interpretive notes still using legacy taxonomies | 1,298 |
| Granular claims authored | 54 |
| External sources | 333 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,093 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All ten corrected books remain incomplete because their human-review sections
are still `missing`. The remaining 610 records still rely on section/layer
migration defaults.

After Phase 5 Wave 6, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 608 / 12 |
| Raw records missing explicit `section_status` | 608 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 608 |
| Interpretive notes using current taxonomies | 59 |
| Interpretive notes still using legacy taxonomies | 1,294 |
| Granular claims authored | 68 |
| External sources | 341 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,099 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twelve corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 608 records still rely on
section/layer migration defaults.

After Phase 5 Wave 7, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 606 / 14 |
| Raw records missing explicit `section_status` | 606 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 606 |
| Interpretive notes using current taxonomies | 73 |
| Interpretive notes still using legacy taxonomies | 1,290 |
| Granular claims authored | 84 |
| External sources | 350 |
| Source references that do not resolve | 0 |
| Graph edges / unknown targets / orphaned records | 3,116 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All fourteen corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 606 records still rely on
section/layer migration defaults.

After Phase 5 Wave 8, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 604 / 16 |
| Raw records missing explicit `section_status` | 604 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 604 |
| Interpretive notes using current taxonomies | 92 |
| Interpretive notes still using legacy taxonomies | 1,286 |
| Granular claims authored | 99 |
| External sources | 363 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,131 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All sixteen corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 604 records still rely on
section/layer migration defaults.

After Phase 5 Wave 9, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 603 / 17 |
| Raw records missing explicit `section_status` | 603 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 603 |
| Interpretive notes using current taxonomies | 103 |
| Interpretive notes still using legacy taxonomies | 1,284 |
| Granular claims authored | 107 |
| External sources | 371 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,135 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All seventeen corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 603 records still rely on
section/layer migration defaults.

After Phase 5 Wave 10, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 602 / 18 |
| Raw records missing explicit `section_status` | 602 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 602 |
| Interpretive notes using current taxonomies | 117 |
| Interpretive notes still using legacy taxonomies | 1,282 |
| Granular claims authored | 115 |
| External sources | 379 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,140 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All eighteen corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 602 records still rely on
section/layer migration defaults.

After Phase 5 Wave 11, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 601 / 19 |
| Raw records missing explicit `section_status` | 601 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 601 |
| Interpretive notes using current taxonomies | 132 |
| Interpretive notes still using legacy taxonomies | 1,280 |
| Granular claims authored | 124 |
| External sources | 380 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,146 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All nineteen corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 601 records still rely on
section/layer migration defaults.

After Phase 5 Wave 12, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 600 / 20 |
| Raw records missing explicit `section_status` | 600 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 600 |
| Interpretive notes using current taxonomies | 148 |
| Interpretive notes still using legacy taxonomies | 1,278 |
| Granular claims authored | 135 |
| External sources | 394 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,150 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 600 records still rely on
section/layer migration defaults.

After Phase 5 Wave 13, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 599 / 21 |
| Raw records missing explicit `section_status` | 599 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 599 |
| Interpretive notes using current taxonomies | 167 |
| Interpretive notes still using legacy taxonomies | 1,276 |
| Granular claims authored | 147 |
| External sources | 411 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,154 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-one corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 599 records still rely on
section/layer migration defaults.

After Phase 5 Wave 14, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 598 / 22 |
| Raw records missing explicit `section_status` | 598 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 598 |
| Interpretive notes using current taxonomies | 188 |
| Interpretive notes still using legacy taxonomies | 1,274 |
| Granular claims authored | 161 |
| External sources | 426 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,158 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-two corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 598 records still rely on
section/layer migration defaults.

After Phase 5 Wave 15, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 597 / 23 |
| Raw records missing explicit `section_status` | 597 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 597 |
| Interpretive notes using current taxonomies | 214 |
| Interpretive notes still using legacy taxonomies | 1,272 |
| Granular claims authored | 180 |
| External sources | 448 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,167 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-three corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 597 records still rely on
section/layer migration defaults.

After Phase 5 Wave 16, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 596 / 24 |
| Raw records missing explicit `section_status` | 596 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 596 |
| Interpretive notes using current taxonomies | 240 |
| Interpretive notes still using legacy taxonomies | 1,270 |
| Granular claims authored | 198 |
| External sources | 470 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,174 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-four corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 596 records still rely on
section/layer migration defaults.

After Phase 5 Wave 17, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 595 / 25 |
| Raw records missing explicit `section_status` | 595 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 595 |
| Interpretive notes using current taxonomies | 270 |
| Interpretive notes still using legacy taxonomies | 1,268 |
| Granular claims authored | 217 |
| External sources | 497 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,181 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-five corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 595 records still rely on
section/layer migration defaults.

After Phase 5 Wave 18, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 594 / 26 |
| Raw records missing explicit `section_status` | 594 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 594 |
| Interpretive notes using current taxonomies | 299 |
| Interpretive notes still using legacy taxonomies | 1,266 |
| Granular claims authored | 237 |
| External sources | 519 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Graph edges / unknown targets / orphaned records | 3,185 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-six corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 594 records still rely on
section/layer migration defaults.

After Phase 5 Wave 19, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 593 / 27 |
| Raw records missing explicit `section_status` | 593 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 593 |
| Interpretive notes using current taxonomies | 331 |
| Interpretive notes still using legacy taxonomies | 1,264 |
| Granular claims authored | 257 |
| External sources | 548 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Graph edges / unknown targets / orphaned records | 3,188 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-seven corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 593 records still rely on
section/layer migration defaults.

After Phase 5 Wave 20, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 592 / 28 |
| Raw records missing explicit `section_status` | 592 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 592 |
| Interpretive notes using current taxonomies | 364 |
| Interpretive notes still using legacy taxonomies | 1,262 |
| Granular claims authored | 279 |
| External sources | 564 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Graph edges / unknown targets / orphaned records | 3,190 / 0 / 0 |
| Validator warnings / errors | 14 / 0 |

All twenty-eight corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 592 records still rely on
section/layer migration defaults.

After Phase 5 Wave 21, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 591 / 29 |
| Raw records missing explicit `section_status` | 591 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 591 |
| Interpretive notes using current taxonomies | 403 |
| Interpretive notes still using legacy taxonomies | 1,260 |
| Granular claims authored | 301 |
| External sources | 583 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Graph edges / unknown targets / orphaned records | 3,192 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,752 |
| Validator warnings / errors | 14 / 0 |

All twenty-nine corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 591 records still rely on
section/layer migration defaults.

After Phase 5 Wave 22, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 590 / 30 |
| Raw records missing explicit `section_status` | 590 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 590 |
| Interpretive notes using current taxonomies | 440 |
| Interpretive notes still using legacy taxonomies | 1,258 |
| Granular claims authored | 324 |
| External sources | 605 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,194 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,754 |
| Validator warnings / errors | 14 / 0 |

All thirty corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 590 records still rely on
section/layer migration defaults.

After Phase 5 Wave 23, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 589 / 31 |
| Raw records missing explicit `section_status` | 589 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 589 |
| Interpretive notes using current taxonomies | 484 |
| Interpretive notes still using legacy taxonomies | 1,256 |
| Granular claims authored | 348 |
| External sources | 628 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,197 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,757 |
| Validator warnings / errors | 14 / 0 |

All thirty-one corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 589 records still rely on
section/layer migration defaults.

After Phase 5 Wave 24, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 588 / 32 |
| Raw records missing explicit `section_status` | 588 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 588 |
| Interpretive notes using current taxonomies | 536 |
| Interpretive notes still using legacy taxonomies | 1,254 |
| Granular claims authored | 382 |
| External sources | 651 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,200 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,760 |
| Validator warnings / errors | 14 / 0 |

All thirty-two corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 588 records still rely on
section/layer migration defaults.

After Phase 5 Wave 25, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 587 / 33 |
| Raw records missing explicit `section_status` | 587 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 587 |
| Interpretive notes using current taxonomies | 582 |
| Interpretive notes still using legacy taxonomies | 1,252 |
| Granular claims authored | 409 |
| External sources | 673 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,203 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,763 |
| Validator warnings / errors | 14 / 0 |

All thirty-three corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 587 records still rely on
section/layer migration defaults.

After Phase 5 Wave 26, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 586 / 34 |
| Raw records missing explicit `section_status` | 586 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 586 |
| Interpretive notes using current taxonomies | 628 |
| Interpretive notes still using legacy taxonomies | 1,250 |
| Granular claims authored | 437 |
| External sources | 694 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,206 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,766 |
| Validator warnings / errors | 14 / 0 |

All thirty-four corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 586 records still rely on
section/layer migration defaults.

After Phase 5 Wave 27, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 585 / 35 |
| Raw records missing explicit `section_status` | 585 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 585 |
| Interpretive notes using current taxonomies | 678 |
| Interpretive notes still using legacy taxonomies | 1,248 |
| Granular claims authored | 468 |
| External sources | 715 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,210 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,770 |
| Validator warnings / errors | 14 / 0 |

All thirty-five corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 585 records still rely on
section/layer migration defaults.

After Phase 5 Wave 28, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 584 / 36 |
| Raw records missing explicit `section_status` | 584 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 584 |
| Interpretive notes using current taxonomies | 727 |
| Interpretive notes still using legacy taxonomies | 1,246 |
| Granular claims authored | 496 |
| External sources | 737 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,217 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,777 |
| Validator warnings / errors | 14 / 0 |

All thirty-six corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 584 records still rely on
section/layer migration defaults.

After Phase 5 Wave 29, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 583 / 37 |
| Complete records with candidate Phase 2 section gaps | 582 |
| Raw records missing explicit `section_status` | 583 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 583 |
| Interpretive notes using current taxonomies | 795 |
| Interpretive notes still using legacy taxonomies | 1,244 |
| Granular claims authored | 530 |
| External sources | 766 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,224 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,784 |
| Validator warnings / errors | 14 / 0 |

All thirty-seven corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 583 records still rely on
section/layer migration defaults.

After Phase 5 Wave 30, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 582 / 38 |
| Complete records with candidate Phase 2 section gaps | 581 |
| Raw records missing explicit `section_status` | 582 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 582 |
| Interpretive notes using current taxonomies | 862 |
| Interpretive notes still using legacy taxonomies | 1,242 |
| Granular claims authored | 564 |
| External sources | 798 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,231 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,791 |
| Validator warnings / errors | 14 / 0 |

All thirty-eight corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 582 records still rely on
section/layer migration defaults.

After Phase 5 Wave 31, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 581 / 39 |
| Complete records with candidate Phase 2 section gaps | 580 |
| Raw records missing explicit `section_status` | 581 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 581 |
| Interpretive notes using current taxonomies | 934 |
| Interpretive notes still using legacy taxonomies | 1,240 |
| Granular claims authored | 610 |
| External sources | 831 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,239 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,797 |
| Validator warnings / errors | 14 / 0 |

All thirty-nine corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 581 records still rely on
section/layer migration defaults.

After Phase 5 Wave 32, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 580 / 40 |
| Complete records with candidate Phase 2 section gaps | 579 |
| Raw records missing explicit `section_status` | 580 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 580 |
| Interpretive notes using current taxonomies | 1,012 |
| Interpretive notes still using legacy taxonomies | 1,238 |
| Granular claims authored | 651 |
| External sources | 859 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,247 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,805 |
| Validator warnings / errors | 14 / 0 |

All forty corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 580 records still rely on
section/layer migration defaults.

After Phase 5 Wave 33, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 579 / 41 |
| Complete records with candidate Phase 2 section gaps | 578 |
| Raw records missing explicit `section_status` | 579 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 579 |
| Interpretive notes using current taxonomies | 1,080 |
| Interpretive notes still using legacy taxonomies | 1,236 |
| Granular claims authored | 695 |
| External sources | 895 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,248 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,806 |
| Validator warnings / errors | 14 / 0 |

All forty-one corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 579 records still rely on
section/layer migration defaults.

After Phase 5 Wave 34, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 578 / 42 |
| Complete records with candidate Phase 2 section gaps | 577 |
| Raw records missing explicit `section_status` | 578 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 578 |
| Interpretive notes using current taxonomies | 1,167 |
| Interpretive notes still using legacy taxonomies | 1,234 |
| Granular claims authored | 740 |
| External sources | 927 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,255 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,813 |
| Validator warnings / errors | 14 / 0 |

All forty-two corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 578 records still rely on
section/layer migration defaults.

After Phase 5 Wave 35, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 577 / 43 |
| Complete records with candidate Phase 2 section gaps | 576 |
| Raw records missing explicit `section_status` | 577 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 577 |
| Interpretive notes using current taxonomies | 1,248 |
| Interpretive notes still using legacy taxonomies | 1,232 |
| Granular claims authored | 782 |
| External sources | 962 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,259 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,815 |
| Validator warnings / errors | 14 / 0 |

All forty-three corrected books remain incomplete because their human-review
sections are still `missing`. The remaining 577 records still rely on
section/layer migration defaults.

Near-duplicate and template findings are triage signals rather than automatic
proof of error. For example, numbered epistle titles are naturally similar.
The JSON report retains the details so reviewers can distinguish legitimate
repetition from inherited templates.

## Phase 1 implementation audit (historical pre-foundation state)

### Schema and content status

The runtime schema is implemented in both
`framework/canonical_library/schema.py` and
`framework/canonical_library/schema/base.schema.json`. It uses framework
version `1.0`, schema version `1.0`, and object version `1`.

`content_status` is currently a single controlled string:

- `placeholder`
- `draft`
- `complete`
- `deprecated`

The authoring validator currently requires only these content fields for a
record marked complete:

- `summary`
- `canonical_role`
- `historical_context`
- `literary_context`
- `scripture_references`
- `related_objects`
- `sources`
- `common_questions`
- `interpretive_notes`

That rule does not inspect the meaningful contents of `canonical_story`,
`hermeneutical_lens`, or `retrieval_metadata`. It also is not object-type
specific. This is the direct reason all 620 objects can be marked complete
while 619 still show candidate Phase 2 section gaps.

The Python validator fills defaults for legacy records and deliberately
supports legacy string sources and interpretive notes. That compatibility
behavior should be preserved during migration.

### Object inventory

The library has 18 populated categories. Several categories are dramatically
underrepresented: `biblical_theology`, `covenant`, `cultural_background`,
`doctrine`, `literary_device`, `symbol`, and `timeline` each contain one
record. This confirms the supplied plan’s category assessment, but expansion
must wait until completeness, sourcing, and review rules exist.

All 66 book records exist. They have not been factually reviewed merely because
they validate.

### Confirmed factual/template problem

`framework/canonical_library/objects/books/genesis.json` is a confirmed
correction target:

- `key_people` lists Moses, Aaron, and Israel instead of representing the
  Genesis cast;
- `key_places` lists Egypt, Sinai, and Moab instead of representing the range
  of Genesis locations;
- `key_events` mixes Genesis events with the exodus, Sinai covenant, and
  wilderness journey;
- the hermeneutical lens is empty;
- retrieval metadata is empty;
- interpretive certainty and dispute values are unknown; and
- its only non-Scripture support is an internal CKL orientation source.

The template report also identifies repeated settings, people, places, and
events across groups of Pauline letters, historical books, and prophetic
books. Each group needs factual review; the heuristic alone must not rewrite
them.

### Source handling

Sources are inline records within each object. Interpretive-note `sources`
values are local IDs that should resolve against that object’s inline source
list. There is no central source registry, no claim model in current objects,
and no schema support for `claims`.

The current structured source supports bibliographic basics and a `supports`
list, but it does not yet provide all fields requested by the plan, such as
edition, license/usage notes as a distinct field, or a reliability statement.
Most current source objects do not connect themselves to a field or claim.

Internal CKL orientation records are useful provenance, but the deep reporter
now distinguishes them from independent external support.

### Relationship handling

`related_objects` currently stores:

- target `id`;
- free-form kebab-case `relationship`;
- weight from 1 to 10; and
- notes.

Target resolution is enforced, and the current inventory has zero dangling
targets. Relationship vocabulary is not centrally approved. Target type,
direction, Scripture basis, and reciprocal policy are not stored. The graph
helper has a small inverse vocabulary and falls back to generic `related`,
which is why its 2,634 reverse-edge suggestions are guidance rather than safe
automatic patches.

Legacy `related_people`, `related_places`, `related_events`, and
`related_entries` remain in the schema for compatibility.

### Retrieval behavior

Retrieval is deterministic and indexes fields from the validated
`CanonicalObject`. Review/content status filtering already exists, so later
phases can keep incomplete records out of production retrieval.

At the Phase 1 checkpoint there was no `knowledge_layers` field or
layer-priority ranking. Phase 3 has now added it across the Python model, JSON
schema, both deterministic retrieval paths, prompt/context construction,
fixtures, and tests.

### Manifest and SQLite pipeline

The manifest is generated from validated object counts and versions. Existing
validation compares committed manifest counts to the current inventory.

The SQLite database uses normalized tables for aliases, keywords,
relationships, and Scripture references, while also preserving the full object
as `payload_json`. This is favorable for additive migration: new fields can be
retained in the payload before they need normalized tables. However, the
Python/JSON validators currently reject unknown fields, so schema/model support
must land before object migration.

SQLite is a generated artifact. The safe migration is to update JSON/schema
first and rebuild the database, not to edit generated database rows manually.
If knowledge layers, claims, or source relationships need SQL filtering, the
database schema version must be bumped and the builder/repository updated.

## Foundation implemented in Phases 2–4

1. Preserve the legacy `content_status` string during transition and add a
   separate `section_status` mapping. Derive global readiness from
   type-specific rules instead of replacing the field in one breaking edit.
2. Define the allowed section statuses:
   `missing`, `generated`, `draft`, `needs_review`, `reviewed`, `complete`, and
   `not_applicable`.
3. Add type-specific completion profiles in code rather than duplicating the
   rules in every object.
4. Add `knowledge_layers.primary` and `knowledge_layers.secondary` with a
   controlled vocabulary and deterministic retrieval priority.
5. Replace the old certainty/dispute values through an explicit migration map.
   Preserve `unknown` for legacy input during the transition, but forbid it for
   approved content.
6. Add a granular `claims` collection with claim ID, type, certainty, dispute
   status, Scripture references, source IDs, traditions, rationale, and notes.
7. The deep report now measures raw migration coverage for section status,
   knowledge layers, current taxonomies, and claims.

Still deferred to their planned phases:

- source edition/license/reliability fields and expanded source types (Phase 7);
- relationship v2, approved vocabulary, and reciprocal policies (Phase 8);
- scoped review events beyond the existing reviewer/date fields (Phase 19).

### Phase 2 details

- The legacy scalar `content_status` remains intact.
- `section_status` contains 14 controlled sections with the seven plan-defined
  statuses.
- Completion profiles combine common required sections with object-type rules
  for all 18 supported CKL types.
- `section_completion_issues`, `content_completeness_issues`, and
  `is_globally_complete` provide deterministic readiness checks.
- Approved records must have every required section marked `complete` or
  `not_applicable`; current in-review records only receive audit warnings.

### Phase 3 details

- `knowledge_layers.primary` is controlled and required after normalization;
  `secondary` is deduplicated and may not repeat the primary layer.
- Legacy records receive a type-based runtime default, while the report
  continues to distinguish missing raw assignments from explicit content.
- Search indexes knowledge-layer and claim content.
- Layer precedence is a deterministic tie-breaker after direct relevance,
  importance, Scripture coverage, and matched-term evidence. This preserves
  existing high-quality retrieval behavior while preferring lower-inference
  knowledge when evidence is otherwise tied.
- Prompt context identifies the primary knowledge layer so later synthesis is
  not silently presented as biblical text.

### Phase 4 details

- Current certainty values:
  `textually_explicit`, `strong_consensus`, `probable`, `plausible`,
  `disputed`, `tradition_dependent`, `speculative`, and
  `insufficient_evidence`.
- Current dispute values:
  `not_disputed`, `minor_scholarly_disagreement`,
  `major_scholarly_disagreement`, `denominational_disagreement`,
  `textual_variant`, `historical_uncertainty`,
  `chronological_uncertainty`, `archaeological_uncertainty`, and
  `lexical_uncertainty`.
- Legacy certainty/dispute labels and string notes remain readable during the
  migration.
- Interpretive notes can now carry Scripture references, traditions, and a
  certainty rationale.
- Granular claims carry ID, text, type, certainty, dispute status, Scripture
  references, local source IDs, traditions, rationale, and notes.
- Claim source IDs must resolve within the containing object. Approved notes
  and claims require current taxonomies, rationales, and supporting evidence.
- Claims and their metadata are searchable and sourced claims can be rendered
  into prompt context.

## Migration and backward-compatibility implications

- Do not change all 620 JSON files in the schema commit.
- Add schema/model defaults and legacy normalization first.
- Make new fields searchable only after both JSON and SQLite retrieval paths
  understand them.
- Keep `content_status` readable by current agent code until all callers have
  migrated to derived readiness.
- Keep accepting legacy source strings, note strings, relationship `id`, and
  legacy related-object lists during the transition.
- Increment object/schema versions only with a documented migration command.
- Rebuild and verify SQLite after each migrated wave.
- Do not convert `unknown` certainty to consensus mechanically. That requires
  claim-level evidence.
- Do not auto-add all reverse edges. First classify the relationship vocabulary
  because some edges are directional and the current fallback is generic.
- Do not interpret automated validation as human approval.

## Files likely to change next

Phase 5 should modify the 66 JSON files under
`framework/canonical_library/objects/books/` only in controlled review waves.
Genesis through Hebrews are now implemented as unapproved drafts. The active
continuation file is `james.json`, keeping the general-letter wave small
enough for factual, retrieval, and source review.

## Files changed in Phase 1

- `framework/canonical_library/quality_report.py` — deep report calculations
  and Markdown rendering.
- `tools/ckl_report.py` — `--deep` and `--output` CLI support while preserving
  old behavior.
- `tools/README.md` — deep-report usage.
- `tests/canonical_library/test_quality_report.py` — calculation and CLI tests.
- `docs/ckl-quality-report.md` — generated human baseline.
- `docs/ckl-quality-report.json` — generated machine baseline.
- `docs/ckl-expansion-correction-progress.md` — this handoff.

## Files changed in Phases 2–4

- `framework/canonical_library/schema.py` — controlled vocabularies,
  section/type rules, knowledge layers, claims, note metadata, readiness, and
  approval/source validation.
- `framework/canonical_library/schema/base.schema.json` and
  `schema/validator.py` — additive normalized schema and defaults.
- `framework/canonical_library/__init__.py` — public exports for the new model
  and readiness helpers.
- `framework/canonical_library/authoring.py` — type-aware authoring defaults
  and section-completeness audit warnings.
- `framework/canonical_library/retrieval.py` — searchable claims/layers and
  legacy JSON/SQLite tie precedence.
- `framework/canonical_library/retrieval/{indexer,models,ranker,service}.py` —
  indexed/search result layer metadata, claim search, and deterministic
  precedence.
- `framework/canonical_library/context_builder.py` — layer metadata and
  sourced claims in runtime/prompt context.
- Schema, authoring, retrieval, context-builder, quality-report, lifecycle,
  and SQLite parity tests under `tests/canonical_library/`.
- The generated Markdown and JSON quality reports and this progress document.

No database schema bump was needed. SQLite already stores the full normalized
object in `payload_json`; the parity test proves the new fields round-trip.
No content JSON file was rewritten in the foundation wave.

## Phase 5 Wave 1: Genesis and Exodus

Completed implementation work:

- corrected the confirmed Genesis inherited-template defects;
- corrected Exodus's Moab placement, event repetition, and generic inherited
  content;
- rewrote both records around their actual literary movement, people, places,
  events, canonical function, and major interpretive cautions;
- added Scripture and independent publisher/museum sources;
- added nine granular claims and eight structured interpretive notes using the
  current taxonomies;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- added factual, evidence, retrieval, and SQLite parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-genesis-exodus-review.md`](ckl-phase-5-genesis-exodus-review.md).

The expanded draft records initially displaced more focused entries in three
golden retrieval queries. Retrieval now applies a soft penalty to a broad draft
record when the query does not name its subject, while retaining first-place
results for direct questions about those books and passage-specific matches.

## Phase 5 Wave 2: Leviticus and Numbers

Completed implementation work:

- corrected Leviticus's inherited Egypt, Moab, exodus, and wilderness-journey
  fields and anchored it at the Sinai sanctuary;
- corrected Numbers's generic template and represented its actual journey,
  leaders, two generations, rebellions, blessings, and inheritance transition;
- added eleven granular claims and nine structured interpretive notes using
  current taxonomies;
- added Scripture plus independently published Jewish, literary, ancient Near
  Eastern, and archaeological sources;
- marked census totals, route identifications, population scale, composition,
  ritual comparison, and Deir Alla reconstruction with appropriate caution;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- added eight factual, evidence, retrieval, and SQLite parity regression
  tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-leviticus-numbers-review.md`](ckl-phase-5-leviticus-numbers-review.md).

## Phase 5 Wave 3: Deuteronomy and Joshua

Completed implementation work:

- corrected Deuteronomy's duplicate Sinai-covenant event and represented its
  Moab speech setting, covenant instruction, blessing and curse, renewal,
  succession, song, blessing, and narrative close;
- removed Joshua's inherited David, Solomon, monarchy, exile, Jerusalem, and
  Samaria material and rebuilt the record around entry, campaigns, allotment,
  tribal unity, farewell, and Shechem;
- added ten granular claims and nine structured interpretive notes using
  current taxonomies;
- added Scripture plus independently published Jewish, literary, historical,
  ancient Near Eastern, and archaeological sources;
- preserved both Joshua's comprehensive victory/promise summaries and its
  explicit remaining-land notices;
- marked composition, treaty comparison, centralized worship, warfare,
  chronology, conquest models, site identifications, and archaeological
  reconstruction with appropriate caution;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- refined retrieval with a soft draft penalty, focused-archaeology preference,
  and passage-scope tie-breaker;
- added eight factual, evidence, retrieval, archaeology, and SQLite parity
  regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-deuteronomy-joshua-review.md`](ckl-phase-5-deuteronomy-joshua-review.md).

## Phase 5 Wave 4: Judges and Ruth

Completed implementation work:

- removed Ruth from Judges's principal people and separated the narrated
  judges period from later monarchy, exile, and disputed compositional dates;
- rebuilt Judges around its introductions, varied deliverer narratives,
  Gideon/Abimelech turn, Samson cycle, idolatry appendix, and civil-war
  conclusion;
- removed Ruth's inherited Joshua, Solomon, Jerusalem, Samaria, conquest,
  monarchy, and exile fields and rebuilt it around Naomi, Ruth, Boaz, harvest,
  kinship redemption, Obed, and Davidic lineage;
- added twelve granular claims and ten structured interpretive notes using
  current taxonomies;
- added Scripture plus independently published literary, historical, legal,
  ancient Near Eastern, and canonical sources;
- marked judges chronology, archaeology, kingship, Jephthah's vow, violence,
  Ruth's composition, legal reconstruction, threshing-floor language, Moabite
  identity, and typology with appropriate caution;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- refined draft ranking when a query explicitly names one book so adjacent
  broad drafts do not displace its focused results;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-judges-ruth-review.md`](ckl-phase-5-judges-ruth-review.md).

## Phase 5 Wave 5: 1 Samuel and 2 Samuel

Completed implementation work:

- removed inherited Joshua, Solomon, Canaan, Jerusalem, Samaria, conquest, and
  exile content from 1 Samuel's principal people, places, and events;
- rebuilt 1 Samuel around Hannah, Samuel, the ark, the monarchy request,
  Saul's selection and rejection, David's rise and flight, Endor, and Gilboa;
- removed inherited Joshua, Samaria, conquest, and exile content from
  2 Samuel while retaining Solomon's birth and locating his accession in
  1 Kings;
- rebuilt 2 Samuel around David's accession, Jerusalem and the ark, the
  Davidic house promise, royal abuse, household violence, rebellions, and the
  chapters 21–24 appendix;
- added twelve granular claims and ten structured interpretive notes using
  current taxonomies;
- added Scripture plus independently published textual, literary, historical,
  ancient Near Eastern, and archaeological sources;
- marked monarchy, Samuel textual variants, Saul's harmful spirit, Endor,
  Amalek, the Davidic promise, Bathsheba, Tamar, the census parallel, and
  archaeology with appropriate caution;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- fixed punctuation-sensitive named-book retrieval so a query ending in
  “2 Samuel?” is correctly recognized as naming the book;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-samuel-review.md`](ckl-phase-5-samuel-review.md).

## Phase 5 Wave 6: 1 Kings and 2 Kings

Completed implementation work:

- removed inherited Joshua, Canaan, conquest, and exile-wide content from
  1 Kings and rebuilt it around Solomon, temple, division, parallel reigns,
  Elijah, Ahab, Jezebel, Naboth, and Micaiah;
- removed Joshua, David, Solomon, and Jeremiah from 2 Kings's principal cast
  and rebuilt it around Elijah and Elisha, Jehu, Assyrian expansion, Samaria's
  fall, Hezekiah, Josiah, Babylonian destruction, and Jehoiachin's release;
- added fourteen granular claims and thirteen structured interpretive notes
  using current taxonomies;
- added Scripture plus independently published textual, literary, historical,
  ancient Near Eastern, and museum sources;
- marked Solomonic chronology and archaeology, temple comparison, the Horeb
  phrase, Carmel's violence, the Bethel bears, Moab's ending, Jehu, Assyrian
  deportation, Sennacherib, Josiah, and Jehoiachin with appropriate caution;
- distinguished biblical theological explanations from external inscriptional
  and archaeological evidence;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-kings-review.md`](ckl-phase-5-kings-review.md).

## Phase 5 Wave 7: 1 Chronicles and 2 Chronicles

Completed implementation work:

- removed the inherited Joshua, Canaan, conquest, monarchy, and generic exile
  template from 1 Chronicles and rebuilt it around genealogies, Saul, David,
  Jerusalem, the ark, the Davidic promise, Ornan's floor, temple preparation,
  and worship personnel;
- rebuilt 2 Chronicles around Solomon's temple and Judah's kings, including
  prophets, reforms, Passovers, Assyrian and Babylonian crises, exile, land
  Sabbath, and Cyrus's decree;
- preserved the Chronicler's `all Israel` concern alongside the work's
  Judah-, David-, Levi-, Jerusalem-, and temple-centered emphases;
- added sixteen granular claims and fourteen structured interpretive notes
  using current taxonomies;
- added Scripture plus independently published textual, literary, historical,
  ancient Near Eastern, and reception sources;
- marked genealogical compression, all-Israel rhetoric, differences from
  Samuel–Kings, census agency, David's bloodshed, Levitical orders, immediate
  retribution, large numbers, Manasseh, Josiah, Cyrus/Ezra unity, violence,
  coercion, and modern national application with appropriate caution;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-chronicles-review.md`](ckl-phase-5-chronicles-review.md).

## Phase 5 Wave 8: Ezra and Nehemiah

Completed implementation work:

- removed inherited Joshua, David, Solomon, Canaan, conquest, monarchy, and
  generic settlement-through-exile content from both records;
- rebuilt Ezra around the distinct Cyrus-to-Darius return and temple sequence
  and the later Artaxerxes-era Ezra return, Torah mission, confession, and
  marriage reform;
- rebuilt Nehemiah around Susa, royal authorization, Jerusalem's wall,
  regional opposition, armed defense, economic restitution, Torah reading,
  covenant, repopulation, dedication, and the later return and reforms;
- restored the correct Persian kings, governors, priests, scribes, prophets,
  officials, opponents, builders, families, Levites, places, documents,
  lists, prayers, festivals, and covenant obligations;
- added fifteen granular claims and nineteen structured interpretive notes
  using current taxonomies;
- added Scripture plus independently published textual, literary, historical,
  ancient Near Eastern, theological, background, and museum sources;
- distinguished Ezra 4's topical chronology, the two return groups, Hebrew
  and Aramaic documentary sections, Nehemiah memoir material, first and second
  administrations, and Ezra-Nehemiah's debated chronology;
- qualified the Cyrus Cylinder, return totals, collaborator identities,
  Persian dates, archives, wall archaeology, fifty-two-day claim, regional
  opponents, Nehemiah 8:8, intermarriage, divorce, exclusion, armed defense,
  physical force, race, nationalism, and modern coercive application;
- added explicit section statuses and knowledge-layer classifications;
- populated both hermeneutical lenses and retrieval metadata;
- kept both records as `draft` / `in_review`, with human review missing;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-ezra-nehemiah-review.md`](ckl-phase-5-ezra-nehemiah-review.md).

## Phase 5 Wave 9: Esther

Completed implementation work:

- removed inherited Joshua, David, Solomon, Canaan, conquest, monarchy, and
  generic settlement-through-exile content;
- rebuilt Esther around Ahasuerus, Vashti, Esther/Hadassah, Mordecai, Haman,
  Zeresh, Susa, the Persian court, diaspora Jews, two edicts, banquets, fasts,
  reversals, conflict, rest, and Purim;
- added eight granular claims and eleven structured interpretive notes using
  current taxonomies;
- added Masoretic and Greek primary text records plus independently published
  Jewish, Christian, literary, historical, background, encyclopedia, and
  museum sources;
- qualified the Xerxes I identification, royal chronology, 127 provinces,
  court practices, irrevocable-edict claim, execution vocabulary, Susa
  archaeology, historicity, and the limits of material corroboration;
- distinguished the Masoretic form, Old Greek, Alpha Text, and Greek
  additions rather than silently combining their contents;
- addressed the divine-name absence, providential inference, Vashti's
  unstated motive, Esther's constrained court participation and hidden
  identity, Mordecai's unstated bowing motive, threatened genocide,
  antisemitism vocabulary, chapter 9 violence, no-plunder notices, and modern
  ethnic or political misuse;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-esther-review.md`](ckl-phase-5-esther-review.md).

## Phase 5 Wave 10: Job

Completed implementation work:

- removed inherited David, Solomon, Israel, court, temple, monarchic wisdom,
  and generic canonical-book content;
- rebuilt Job around the righteous sufferer, his family and wife, the
  heavenly council and accuser, cascading losses, bodily affliction, three
  friends, Elihu, YHWH's speeches, intercession, restoration, and the named
  daughters;
- distinguished the prose prologue and epilogue, opening lament, three uneven
  dialogue cycles, Job 28 wisdom poem, Job's oath, Elihu speeches, two divine
  speeches, and two Job responses;
- added eight granular claims and fourteen structured interpretive notes using
  current taxonomies;
- added Masoretic, Old Greek, Qumran, Ezekiel, and James anchors plus eight
  independently published literary, textual, historical, comparative,
  theological, reception, and pastoral sources;
- qualified authorship, compositional history, date, Uz, non-Israelite
  setting, historicity, language, ancient Near Eastern comparisons, and
  textual plurality;
- addressed retribution theology, undeserved suffering, lament, protest,
  human limits, creation's wildness, divine justice and freedom, the accuser,
  Job 28, Elihu, Job 19:25, Job 42:6, Behemoth, Leviathan, and the children;
- distinguished epilogue restoration from replacement of the dead or a
  universal prosperity promise and added trauma-aware cautions against victim
  blaming, secret-sin diagnosis, and forced emotional passivity;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, evidence, retrieval, interpretive-caution, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-job-review.md`](ckl-phase-5-job-review.md).

## Phase 5 Wave 11: Psalms

Completed implementation work:

- removed the inherited Solomon-centered wisdom-book authorship, audience,
  setting, Job, court, and generic canonical-book content;
- rebuilt the record around the five-book anthology, Psalms 1–2 gateway,
  doxological seams, Book III covenant crisis, Book IV YHWH-kingship
  emphasis, Book V pilgrimage and Torah groupings, and the final Hallelujah
  sequence;
- distinguished Davidic, Asaphite, Korahite, Solomonic, Mosaic, Hemanite,
  Ethanite, Hallel, Songs of Ascents, and anonymous materials without treating
  titles as uniform modern authorship metadata;
- distinguished lament, praise, thanksgiving, royal, Zion, Torah, wisdom,
  creation, historical, penitential, enthronement, imprecatory, and pilgrimage
  genres while allowing mixed forms;
- added nine granular claims and fifteen structured interpretive notes using
  current taxonomies;
- added Masoretic, Qumran, Greek, Latin, Psalm 151, and New Testament anchors
  plus eight URL-bearing institutional or independently published sources;
- qualified composition, collection, editing, dates, original settings,
  titles, musical terms, historical notices, ancient Near Eastern
  comparisons, speakers, enemies, parallelism, and imagery;
- addressed the Great Psalms Scroll, Greek and Latin numbering, combinations
  of Psalms 9–10 and 114–115, divisions of Psalms 116 and 147, and Psalm 151;
- addressed lament, protest, praise, divine kingship, Torah, wisdom, creation,
  Zion, temple, exile, restoration, royal and messianic trajectories, Jewish
  reception, New Testament reuse, and Christian worship;
- added cautions concerning imprecation, Psalm 137, enemy labeling, political
  or territorial appropriation, protection and prosperity promises, trauma,
  and victim-erasing uses of Psalm 51;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added nine factual, structure, evidence, retrieval, interpretive-caution,
  and SQLite parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-psalms-review.md`](ckl-phase-5-psalms-review.md).

## Phase 5 Wave 12: Proverbs

Completed implementation work:

- removed inherited Job, David, temple, suffering, praise, lament, and generic
  wisdom-book content;
- rebuilt the record around the distinct units and collection headings in
  Proverbs 1–9, 10:1–22:16, 22:17–24:22, 24:23–34, 25–29, 30, and 31;
- distinguished Solomon, unnamed wise teachers, Hezekiah's officials, Agur,
  Lemuel, Lemuel's mother, Woman Wisdom, Woman Folly, the strange or forbidden
  woman, and the capable woman;
- distinguished instruction, sentence sayings, admonitions, comparisons,
  better-than sayings, numerical sayings, riddling observations, royal
  teaching, autobiographical sayings, personification, and alphabetic poetry;
- added eleven granular claims and sixteen structured interpretive notes using
  current taxonomies;
- added Masoretic, Old Greek, Amenemope, and New Testament anchors plus
  fourteen URL-bearing museum, scholarly-organization, university, or
  independently published sources;
- qualified authorship, attribution, collection, Hezekiah-era copying, social
  setting, date, final editing, and ancient Near Eastern relationships;
- addressed fear of YHWH, creation, speech, anger, work, desire, family,
  discipline, friendship, sexuality, wealth, poverty, debt, rulers, bribery,
  justice, and social power;
- distinguished ordinary moral patterns from unconditional promises and used
  Proverbs 26:4–5 as a focused case of context-sensitive judgment;
- addressed Hebrew terms, the different Greek order and additions, canonical
  dialogue with Job and Ecclesiastes, and New Testament and christological
  reception;
- added cautions concerning gendered rhetoric, Proverbs 31 checklists, rod
  sayings and abuse, poverty stigma, victim-blaming, prosperity teaching, and
  misuse of Proverbs 8;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, interpretive-caution,
  and SQLite parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-proverbs-review.md`](ckl-phase-5-proverbs-review.md).

## Phase 5 Wave 13: Ecclesiastes

Completed implementation work:

- removed inherited Job, David, court, temple, suffering, praise, lament,
  generic audience, and vague Solomonic placeholder content;
- rebuilt the record around the frame in 1:1–11, Qohelet's investigation in
  1:12–12:7, the closing refrain in 12:8, and the epilogue in 12:9–14;
- distinguished the frame narrator, Qohelet, the royal persona, represented
  observations and sayings, the aging poem, and the epilogue narrator;
- distinguished wisdom reflection, frame narrative, royal autobiography,
  investigation, observation, comparisons, proverbs, admonitions, enjoyment
  refrains, the time poem, the aging poem, and epilogue;
- added twelve granular claims and nineteen structured interpretive notes
  using current taxonomies;
- added Masoretic, Old Greek, Qumran, and New Testament comparison anchors
  plus sixteen URL-bearing university, scholarly-organization, publisher, and
  manuscript-library sources;
- qualified the title *Qohelet*, traditional Solomonic identification, royal
  persona, authorship, framing, composition, late linguistic evidence,
  Persian- and early Hellenistic-period proposals, and Qumran terminus;
- addressed *hebel*, *yitron*, *heleq*, “under the sun,” toil, enjoyment,
  wisdom, folly, wealth, power, oppression, time, chance, aging, death, God,
  fear, gift, and judgment;
- distinguished a multivalent vapor image from an automatic nihilistic
  reading of *hebel*, and controllable lasting gain from all human value;
- distinguished finite enjoyment as divine gift from hedonism, consumerism,
  and prosperity teaching;
- treated Ecclesiastes 3:1–8 as descriptive antithetical poetry rather than
  commands, explicitly rejecting use of “a time to kill” to authorize harm;
- preserved the book's observations of oppression and corrupt judgment
  without demanding resignation from victims, and held wisdom's comparative
  value together with limits imposed by death, chance, rulers, and unknown
  outcomes;
- addressed 4QQohᵃ, 4QQohᵇ, Greek *Ecclesiast*, title, translation profile,
  textual variants, and the unresolved Aquila proposal;
- placed the book in differentiated canonical dialogue with Genesis, Psalms,
  Proverbs, Job, later Jewish wisdom, and proposed New Testament resonances;
- added cautions concerning violence, abuse, clinical depression,
  suicidality, trauma, grief, aging, disability, exploitative work, overwork,
  wealth, poverty stigma, victim-blaming, and spiritualized inaction;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-ecclesiastes-review.md`](ckl-phase-5-ecclesiastes-review.md).

## Phase 5 Wave 14: Song of Songs

Completed implementation work:

- removed inherited Job, David, suffering, praise, lament, temple, generic
  court, generic audience, and vague Solomonic placeholder content;
- rebuilt the record around the superscription, lyric sequences, awakening
  refrains, searches, body descriptions, garden and vineyard scenes, royal
  procession, watchmen scene, and 8:5–14 conclusion;
- distinguished the woman, man, daughters of Jerusalem, brothers, companions,
  watchmen, Solomon, and uncertain speakers without imposing a fixed cast;
- distinguished love lyric, lyric sequence, dialogue, *wasf*, search poem,
  invitation, refrain, garden and vineyard poem, procession, and wisdom-like
  saying;
- added fourteen granular claims and twenty-one structured interpretive notes
  using current taxonomies;
- added Masoretic, Old Greek, Qumran, and New Testament comparison anchors
  plus fourteen URL-bearing university, publisher, scholarly-organization,
  and manuscript-library sources;
- qualified the superlative title, Solomonic association, authorship,
  collection, unity, female-authorship proposals, linguistic evidence, date,
  historical audience, and proposed plot or wedding settings;
- preserved uncertainty about sequence, speaker, dreams, relationship status,
  geography, age, ethnicity, class, and the Shulammite's identity;
- addressed embodied erotic love, mutual desire and praise, absence, search,
  body, gaze, gardens, vineyards, animals, fragrance, family, royal wealth,
  jealousy, death, flame, waters, and unbuyable love;
- distinguished erotic celebration from pornography, ownership, coercion,
  compulsory marriage, prosperity teaching, and a mandatory gender script;
- qualified the awakening refrains, watchmen's violence, “black and
  beautiful,” *shalhebetyah*, relationship status, body imagery, and vineyard
  economics;
- addressed 4QCantᵃ, 4QCantᵇ, 4QCantᶜ, 6QCant, Greek *Asma asmaton*,
  translation profile, variants, and the limits of manuscript evidence;
- used Egyptian and Mesopotamian love poetry as comparison without asserting
  direct dependence, fertility cult, sacred marriage, or funerary ritual;
- distinguished human erotic sense, Jewish God-Israel allegory, Christian
  Christ-church and Word-soul interpretation, and careful New Testament
  analogy;
- added cautions concerning consent, marital rape, sexual and domestic abuse,
  stalking, victim-blaming, purity culture, colorism, racism, body shame,
  gender stereotypes, singleness, asexuality, infertility, disability, aging,
  trauma, widowhood, divorce, and celibacy;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-song-of-songs-review.md`](ckl-phase-5-song-of-songs-review.md).

## Phase 5 Wave 15: Isaiah

Completed implementation work:

- removed the inherited generic Major Prophets placeholder, including
  Jeremiah and Ezekiel as key people, generic structure and setting fields,
  obsolete evidence labels, and false completion metadata;
- rebuilt the record around 1–12, 13–27, 28–35, 36–39, 40–55, and 56–66 as
  a qualified practical outline;
- distinguished Isaiah son of Amoz, divine and prophetic speech, sign
  children, royal and national addressees, servants, heralds, personified
  cities, communal voices, and prose narration;
- distinguished twenty-one literary genres and added nineteen granular claims
  plus twenty-six structured interpretive notes using current taxonomies;
- added Masoretic, Qumran, Old Greek, narrative-parallel, Second Temple, and
  New Testament anchors plus twenty-two URL-bearing publisher, university,
  scholarly-organization, and manuscript-library sources;
- qualified eighth-century Isaiah, Assyrian crises, the Syro-Ephraimite
  crisis, 701 BCE, Babylonian exile, Cyrus, Persian and postexilic settings,
  authorship, disciples, collection, redaction, and final-form approaches;
- addressed holiness, Zion, remnant, trust, justice, worship, empire, exile,
  return, Immanuel, Davidic rule, servant figures, Cyrus, new exodus, Spirit,
  fasting, Sabbath, inclusion, resurrection imagery, and new creation;
- preserved uncertainty concerning Immanuel, the royal child, Jesse's shoot,
  the morning star, servants, heralds, resurrection, and eschatological
  horizons;
- distinguished Isaiah 14's royal taunt from later Lucifer-Satan reception
  and servant Israel from anonymous, plural, messianic, and christological
  servant readings;
- addressed 1QIsa-a, 1QIsa-b and other Qumran manuscripts, pesharim, Old
  Greek *Esaias*, variants, translation technique, and Greek-aware New
  Testament reuse;
- distinguished historical referent, prediction, typology, quotation,
  allusion, canonical synthesis, Jewish reception, and later Christian
  reception;
- added cautions concerning anti-Judaism, supersessionism, hardening,
  disability metaphors, gendered violence, warfare, genocide, empire,
  nationalism, racism, servant-abuse readings, prosperity, fasting without
  justice, forced migration, refugee trauma, and end-times fear;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-isaiah-review.md`](ckl-phase-5-isaiah-review.md).

## Phase 5 Wave 16: Jeremiah

Completed implementation work:

- removed the inherited generic Major Prophets placeholder, including Isaiah
  and Ezekiel as key people, generic structure and setting fields, obsolete
  evidence labels, internal orientation sourcing, and false completion
  metadata;
- rebuilt the record around 1; 2–25; 26–29; 30–33; 34–45; 46–51; and 52 as
  a qualified practical Masoretic outline;
- distinguished Jeremiah son of Hilkiah, divine and prophetic speech, Baruch,
  kings and officials, priests, competing prophets, exiles, survivors,
  refugees, personified cities, Rachel, communal voices, nations, and prose
  narration;
- distinguished twenty-one literary genres and added eighteen granular claims
  plus twenty-six structured interpretive notes using current taxonomies;
- added Masoretic, Old Greek, Qumran, historical-parallel, Second Temple, New
  Testament, Babylonian, Lachish, and administrative-tablet anchors plus
  twenty-two URL-bearing publisher, university, scholarly-organization, and
  museum sources;
- qualified Josiah's thirteenth year, the 605 BCE scroll horizon, the 597
  deportation, Zedekiah, Jerusalem's 587/586 destruction, Gedaliah, flight to
  Egypt, Baruch, biography, Deuteronomistic prose, collection, redaction,
  two-edition, and final-form approaches;
- addressed word and call, covenant breach, Torah, temple, justice,
  institutional and prophetic authority, land, tears, trauma, Babylon,
  forced migration, seventy years, Branch, field purchase, Rachel,
  restoration, new covenant, Torah on the heart, potter, yoke, nations, and
  hope;
- preserved uncertainty concerning confessions, biography, Baruch's wider
  role, temple-sermon forms, prose and poetry, editing, seventy years, Rachel,
  Branch, new-covenant continuity and novelty, chronology, and identities;
- addressed Masoretic Jeremiah, shorter and differently ordered Old Greek
  *Ieremias*, 4QJer-a through 4QJer-e, multiple ancient editions, Greek-aware
  New Testament reuse, and fragment-level limits;
- distinguished historical promise, inner-biblical reuse, quotation,
  allusion, typology, Jewish reception, christological reception, and
  ecclesial theology;
- added cautions concerning anti-Judaism, supersessionism, temple or church
  immunity, authoritarian prophecy, abusive-yoke readings, potter-clay
  dehumanization, prosperity teaching, end-times date-setting, gendered
  violence, child sacrifice, victim-blaming, mental-health stigma, celibacy
  mandates, warfare, genocide, empire, colonialism, land, nationalism, forced
  migration, and refugee trauma;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-jeremiah-review.md`](ckl-phase-5-jeremiah-review.md).

## Phase 5 Wave 17: Ezekiel

Completed implementation work:

- removed the inherited generic Major Prophets placeholder, including Isaiah
  and Jeremiah as key people, generic multi-book dates and setting, three
  generic structure labels, obsolete evidence labels, internal orientation
  sourcing, and false completion metadata;
- rebuilt the record around chapters 1–3, 4–24, 25–32, 33–39, and 40–48 as a
  qualified practical outline;
- distinguished Ezekiel son of Buzi, reported divine speech, hand and Spirit,
  living creatures, cherubim, wheels, elders, exiles, Jerusalem inhabitants,
  priests, rulers, prophets, shepherds, watchmen, personified cities, prince,
  Gog, temple guide, communal voices, and prose narration;
- distinguished seventeen literary genres and added nineteen granular claims
  plus thirty structured interpretive notes using current taxonomies;
- added Masoretic, Old Greek, Papyrus 967, Qumran, Masada, historical,
  Mesopotamian, Second Temple, New Testament, and Revelation anchors plus
  twenty-six URL-bearing publisher, university, scholarly-organization, and
  museum sources;
- qualified the 597 deportation, 593/592 call, Kebar canal, Jerusalem's
  siege and fall, dated notices through 571/570, Babylon, Tyre, Egypt,
  historical Ezekiel, priestly and scribal work, school, redaction, textual
  growth, and final-form approaches;
- addressed glory and presence, temple departure and return, holiness, name,
  idolatry, Sabbath, responsibility, watchmen, shepherds, Davidic hope,
  covenant, land, exile, remnant, purification, new heart and spirit, dry
  bones, reunification, Gog, temple, sacrifices, prince, river, tribes,
  resident aliens, and YHWH-shammah;
- preserved uncertainty concerning throne imagery, *ben-adam*, signs,
  constrained speech, Ezekiel's wife, responsibility, Tyre's ruler and
  cherub, resurrection reception, Gog, the prince, sacrifices, the final
  temple, chronology, identities, and eschatological horizons;
- addressed Papyrus 967's order, wording and order variation, manuscript
  limits, Mesopotamian iconography, Babylonian and Judean-exile evidence,
  Jewish reception, and Revelation;
- distinguished historical referent, literary symbol, shared tradition,
  canonical trajectory, quotation, allusion, typology, Jewish reception,
  christological reception, ecclesial theology, and modern analogy;
- added cautions concerning disability, nonspeaking people, mental-health
  stigma, authoritarian prophecy, surveillance, clergy abuse,
  victim-blaming, inherited guilt, grief, sexualized and gendered violence,
  child sacrifice, warfare, genocide, Gog fear, date-setting, empire,
  colonialism, land, nationalism, forced migration, refugee trauma,
  antisemitism, supersessionism, environmental harm, animal welfare,
  coercive purity, and temple-reconstruction politics;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-ezekiel-review.md`](ckl-phase-5-ezekiel-review.md).

## Phase 5 Wave 18: Daniel

Completed implementation work:

- removed the inherited Major Prophets placeholder, including Isaiah,
  Jeremiah, and Ezekiel as key people, generic multi-book dates and setting,
  obsolete evidence labels, internal orientation sourcing, and false
  completion metadata;
- rebuilt the record around Daniel 1, 2–6, 7–12, practical subunits, and the
  Aramaic span from 2:4b through 7:28 while qualifying language boundaries,
  resumptive chronology, seams, and alternative structures;
- distinguished Daniel and his three Judean companions, court groups,
  Nebuchadnezzar, Belshazzar, Darius the Mede, Cyrus, Gabriel, Michael,
  heavenly princes, the Ancient of Days, the humanlike figure, beasts, horns,
  saints, royal speakers, court narrators, communal prayer, and visionary
  first person;
- distinguished thirteen literary genres and added twenty granular claims
  plus twenty-nine structured interpretive notes using current taxonomies;
- added Masoretic, Old Greek, Theodotionic, Qumran, Papyrus 967, Prayer of
  Nabonidus, Greek-addition, cuneiform, Second Temple, Gospel, Pauline, and
  Revelation anchors plus twenty URL-bearing publisher, university,
  scholarly-organization, archive, and museum sources;
- separated sixth-century narrated courts from Persian/Hellenistic tale
  growth and the 167–164 BCE Antiochene crisis, and qualified deportation
  chronology, authorship, pseudonymity, multilingual composition, collection,
  redaction, and final form;
- addressed food and identity, education and names, wisdom, prayer, empire,
  coerced worship, sovereignty, human and beastly rule, persecution,
  deliverance, temple desecration, four kingdoms, seventy weeks, heavenly
  court, humanlike rule, saints, angels, books, judgment, resurrection, and
  hope;
- preserved uncertainty concerning Daniel's identity, language dates, the
  statue, four kingdoms, furnace figure, royal humiliation, Belshazzar,
  Darius the Mede, beasts, horns, Ancient of Days, humanlike figure, seventy
  weeks, abomination, angelic princes, kingdom review, chapter 12 periods,
  resurrection, and eschatological horizons;
- addressed the Prayer/Song, Susanna, and Bel and the Dragon with their
  textual forms, placements, and differing canonical status;
- distinguished cuneiform attestation from story verification and
  historical referent from literary symbol, scriptural reuse, canonical
  trajectory, Jewish reception, christological reception, and modern
  analogy;
- added cautions concerning assimilation and food coercion, authoritarian
  government, civil disobedience, persecution, martyrdom, disability and
  mental-health stigma, antisemitism, supersessionism, empire, colonialism,
  nationalism, war, genocide, speculative angelology, spiritual-warfare
  paranoia, conspiracy, end-times fear, date-setting, and modern political
  identification;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-daniel-review.md`](ckl-phase-5-daniel-review.md).

## Phase 5 Wave 19: Hosea

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated Amos,
  Jonah, and Nineveh values, generic corpus-wide dates and setting, obsolete
  evidence labels, internal orientation sourcing, and false completion
  metadata;
- rebuilt the record around Hosea 1–3, 4–11, 12–14, every chapter-level
  practical unit, changing narrators and speakers, metaphor networks, return
  speeches, the final healing oracle, and the wisdom epilogue;
- distinguished Hosea son of Beeri, Gomer daughter of Diblaim, the three
  named children, YHWH's reported speech, personified Israel/Ephraim and
  Judah, priests, kings, prophets, nations, ancestors, third-person family
  narration, Hosea's first-person report, and communal voices;
- distinguished fourteen literary genres and added twenty granular claims
  plus thirty-two structured interpretive notes using current taxonomies;
- added Masoretic Hosea, Old Greek Osee, Qumran Twelve manuscripts, Pesher
  Hosea A and B, ancient-version, Kings, Assyrian, Gospel, Pauline, Petrine,
  rabbinic, and Book-of-the-Twelve anchors plus twenty-nine URL-bearing
  publisher, university, scholarly-organization, archive, and primary-source
  records;
- qualified Jeroboam II, northern prosperity, coups, Neo-Assyrian expansion,
  Syro-Ephraimite conflict, Egypt and Assyria alliances, Samaria's
  approximately 722–720 BCE fall, Judean transmission, historical Hosea,
  disciples or tradents, redaction, and final-form proposals;
- addressed knowledge of God, hesed, cult and Baal rhetoric, kingship,
  priestly failure, elite extraction, land, ecology, fertility, exodus,
  wilderness, Jacob, Gibeah, Baal-peor, Ephraim, divine pathos, judgment,
  repentance, healing, return, and restoration;
- preserved uncertainty concerning the marriage's historicity and ethics,
  *eshet zenunim*, Gomer's identity and agency, the children's paternity,
  chapter 3's unnamed woman, payment, divorce or remarriage, alleged sacred
  prostitution, chronology, northern and late layers, divine change,
  repentance speeches, Hosea 13:14, and resurrection reception;
- distinguished historical referent, literary symbol, scriptural memory,
  textual variant, quotation, figural rereading, Jewish reception,
  christological reception, ecclesial application, and modern analogy;
- added safeguards concerning sexual shaming, misogyny, intimate-partner
  violence, coercive marriage, infidelity accusations, children used as
  symbols, clergy abuse, victim-blaming, purity culture, divorce stigma,
  forced reconciliation, trafficking, prostitution stereotypes,
  antisemitism, supersessionism, empire, colonialism, nationalism, war,
  genocide, land, ecology, and blaming disaster victims;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-hosea-review.md`](ckl-phase-5-hosea-review.md).

## Phase 5 Wave 20: Joel

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Amos, Jonah, and Nineveh values, generic corpus-wide dates and
  setting, obsolete evidence labels, internal orientation sourcing, and false
  completion metadata;
- rebuilt the record around Joel 1:1–20, 2:1–17, 2:18–27, 3:1–5 MT /
  2:28–32 common English, and 4:1–21 MT / 3:1–21 common English;
- distinguished Joel son of Pethuel, YHWH's reported speech, the prophetic
  first-person voice, elders, priests, ministers, land workers, households,
  communal lamenters, nations, warriors, captives, enslaved people, and every
  named group receiving the spirit;
- distinguished fourteen literary genres and added twenty-two granular claims
  plus thirty-three structured interpretive notes using current taxonomies;
- added Masoretic Joel, Old Greek Ioel, 4Q82, prophetic intertexts, Acts,
  Romans, Revelation, critical commentary, discourse, cultic, form-critical,
  textual-variant, and locust-science anchors plus sixteen URL-bearing external
  records;
- corrected the inherited versification assumption: Masoretic Joel is commonly
  divided into four chapters, while Old Greek and many English Bibles use
  three, so affected locators now state both systems;
- qualified monarchic, Persian, Hellenistic, and Maccabean dating proposals,
  Jerusalem and temple setting, historical Joel, cultic-prophet and
  scribal-prophecy models, unity and layering, compositional seams, and
  Book-of-the-Twelve shaping;
- addressed locusts, drought, land, animals, food systems, offerings, fasting,
  lament, return, divine compassion, the day of YHWH, army and theophany,
  cosmic signs, spirit, prophecy, dreams, visions, deliverance, nations,
  judgment, refuge, fertility, and presence;
- preserved uncertainty concerning the four locust terms, historical disaster
  versus symbol, Joel 2's force, tense and chronology, Joel 2:18, the northern
  one, all flesh, cosmic signs, the valley of Jehoshaphat or decision, named
  nations, restoration, and eschatological horizons;
- distinguished historical referent, literary symbol, canonical trajectory,
  textual witness, quotation, allusion, Jewish reception, christological
  reception, ecclesial application, and modern analogy;
- added safeguards concerning disaster blame, climate and ecological trauma,
  famine, food insecurity, animal suffering, coercive fasting, clergy abuse,
  manipulative revival and revelation claims, spiritual-gift gatekeeping,
  ableism, ageism, gender exclusion, antisemitism, supersessionism, empire,
  colonialism, nationalism, war, genocide, land, vengeance, and divine
  violence;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-joel-review.md`](ckl-phase-5-joel-review.md).

## Phase 5 Wave 21: Amos

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Jonah, and Nineveh values, generic corpus-wide dates and setting,
  obsolete evidence labels, internal-only orientation sourcing, and false
  completion and review metadata;
- rebuilt the record around Amos 1:1–2; 1:3–2:16; 3:1–6:14; 7:1–9:10; and
  9:11–15 while preserving alternative outlines and compositional questions;
- distinguished Amos of Tekoa, YHWH's reported speech, the first-person
  vision voice, the third-person Bethel narrator, Amaziah, Jeroboam II,
  Uzziah, Israel, Judah, Samaria's elites, the women addressed as cows of
  Bashan, merchants, judges, poor and oppressed people, Nazirites, prophets,
  neighboring peoples, and David's fallen booth;
- distinguished fourteen literary genres and added twenty-two granular claims
  plus thirty-nine structured interpretive notes using current taxonomies;
- added Masoretic Amos, Old Greek Amos, 4Q78, 4Q82, other Judean Desert
  witnesses, prophetic intertexts, Acts 7, Acts 15, critical commentary,
  theology, literary, social-justice, creation, violence, gender,
  archaeological, form-critical, textual-variant, and reception-history
  anchors plus nineteen URL-bearing external records;
- qualified the mid-eighth-century superscription setting, Tekoa, occupation
  and social status, the earthquake, northern prosperity and inequality,
  Assyrian expansion, northern ministry, Judean transmission, disciples,
  collection, redaction, final form, and Book-of-the-Twelve shaping;
- addressed election and accountability, justice and righteousness, courts
  and gates, debt, land, labor, taxation, elite luxury, sexual exploitation,
  dishonest trade, worship, sacrifice, music, sanctuaries, day of YHWH,
  remnant, exile, creation, earthquake, famine of hearing, judgment,
  intercession, prophetic vocation, and restoration;
- preserved uncertainty concerning the nations sequence, three/four formula,
  calls to seek and live, doxological fragments, day-of-YHWH audience,
  Sikkuth, Kiyyun, the five visions, *anak*, Amaziah's authority, Amos 7:14,
  summer-fruit wordplay, the altar vision, textual difficulties, Amos
  9:11–15's date and unity, and David's fallen booth;
- distinguished historical referent, literary form, canonical trajectory,
  textual witness, quotation, Jewish reception, christological reception,
  ecclesial application, and modern analogy;
- added safeguards concerning poverty romanticization, class contempt,
  wealth shaming without exploitation, blaming poor people, coercive charity,
  debt and labor abuse, racism, misogynistic reuse of the cows-of-Bashan
  metaphor, sexual violence, clergy and prophetic abuse, anti-ritual and
  anti-Jewish readings, antisemitism, supersessionism, empire, colonialism,
  nationalism, war, genocide, land, disaster blame, divine violence,
  vengeance, and partisan capture of justice language;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-amos-review.md`](ckl-phase-5-amos-review.md).

## Phase 5 Wave 22: Obadiah

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated Hosea,
  Amos, Jonah, and Nineveh values, generic corpus-wide dates and setting,
  legacy evidence labels, internal-only orientation sourcing, and false
  completion and review metadata;
- rebuilt the record around Obadiah 1; 2–9; 10–14; 15–16; and 17–21 while
  preserving alternative outlines, speaker questions, and proposed seams;
- distinguished Obadiah's superscription, YHWH's reported speech, the
  prophetic voice, the envoy and summoned nations, Edom or Esau, Jacob or
  Israel, Judah and Jerusalem, invaders, allies, sages, warriors, fugitives,
  survivors, the houses of Jacob, Joseph, and Esau, regional groups, exiles
  in Sepharad, and the unnamed figures ascending Mount Zion;
- distinguished eleven literary genres and added twenty-three granular claims
  plus thirty-seven structured interpretive notes using current taxonomies;
- added Masoretic Obadiah, Old Greek Abdias, CATSS, NETS, 4Q82, Jeremiah 49,
  canonical comparanda, commentary, historical, archaeological, textual,
  reception, race, postcolonial, violence, Jewish-life, and trauma-aware
  anchors plus twenty-two URL-bearing external records;
- qualified the name Obadiah, absence of patronymic and royal date,
  seventh-century, 587/586 BCE, sixth-century, and Persian-period proposals,
  Edom's geography and routes, Jerusalem's fall, southern Judah and Negev
  interaction, later Nabataean and Idumean histories, collection, expansion,
  unity, final form, and Book-of-the-Twelve shaping;
- addressed pride, security, alliances, wisdom, warriors, plunder, kinship
  betrayal, gloating, looting, fugitives, survivors, reciprocal judgment,
  drinking, holiness, fire, land, restoration, and YHWH's kingship;
- preserved uncertainty concerning the envoy and prophetic plural, allies,
  Teman, verses 12–14's mood and discourse time, the exact actions attributed
  to Edom, verse 16's pronouns and drinking, verse 17's possession clause,
  verses 19–20's syntax and geography, Sepharad, verse 21's plural figures,
  and the date and unity of the closing material;
- distinguished historical referent, literary symbol, verbal parallel,
  disputed borrowing, canonical trajectory, direct quotation, Jewish
  reception, Edom-as-Rome reception, christological reception, ecclesial
  application, and modern analogy;
- added safeguards concerning ethnic essentialism, hereditary guilt,
  antisemitism, anti-Arab racism, modern ethnic and national coding,
  supersessionism, sibling hatred, survivor blame, refugee and border
  violence, trauma exploitation, empire, colonialism, nationalism, war,
  genocide, land seizure, forced displacement, revenge, dehumanization, and
  partisan capture;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-obadiah-review.md`](ckl-phase-5-obadiah-review.md).

## Phase 5 Wave 23: Jonah

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated Hosea
  and Amos values, generic corpus-wide dates and setting, legacy evidence
  labels, internal-only orientation sourcing, and false completion and review
  metadata;
- rebuilt the record around Jonah 1:1–3; 1:4–16; the fish and prayer unit with
  common-English/MT numbering differences; 3:1–10; and 4:1–11, preserving
  alternative outlines, direct speech, repetition, reversal, escalation,
  irony, and the unanswered final question;
- distinguished the narrator, YHWH's speeches and appointed agents, Jonah son
  of Amittai, shipmaster, sailors, lot-casters, rowers, vow-makers, great fish,
  Ninevites, king and nobles, fasting humans and animals, plant, worm, east
  wind, cattle, the 2 Kings figure, and later interpreters;
- distinguished twelve genre and mode descriptions and added twenty-four
  granular claims plus forty-four structured interpretive notes using current
  taxonomies;
- added Masoretic Jonah, canonical comparanda, Matthew, Luke, Old Greek Ionas,
  CATSS, NETS, 4Q76, 4Q82, commentary, historical, archaeological, textual,
  early Jewish, Jewish-life, early Christian, Islamic, artistic,
  postcolonial, animal, ecological, and trauma-aware anchors plus twenty-three
  URL-bearing external records;
- qualified the relationship to 2 Kings 14:25, eighth-century referent,
  anonymous authorship, Persian and Hellenistic proposals, Joppa, Tarshish,
  maritime practice, Assyria, historical Nineveh, its fall in 612 BCE, the
  title “king of Nineveh,” composition, prayer insertion or integration, final
  form, and Book-of-the-Twelve shaping;
- addressed vocation, flight, sovereignty, prayer, descent and ascent, death
  and deliverance imagery, outsider worship, warning, conditional judgment,
  turning, divine relenting, mercy, justice, anger, pity, enemy cities, empire,
  animals, nonhuman agency, and reader formation;
- preserved uncertainty concerning Tarshish, the sailors' religious response,
  the lot, Jonah's motives and death wishes, fish species, death in the fish,
  Sheol, the prayer's origin and fit, three days and nights, Nineveh's size,
  the king, conversion, decree, *qiqayon*, wind wording, pity, right and left,
  final response, genre, date, unity, and purpose;
- distinguished historical referent, author, narrator characterization,
  literary mode, textual witness, verbal parallel, canonical trajectory,
  typology, and Jewish, Christian, Islamic, artistic, missionary, and modern
  reception;
- added safeguards concerning antisemitism, supersessionism, ethnic hatred,
  excusing empire, missionary colonialism, coerced conversion and fasting,
  animal mistreatment, disaster and survivor blame, suicide and mental-health
  stigma, racism, nationalism, vengeance, genocide, collective punishment,
  ecological exploitation, and partisan capture;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-jonah-review.md`](ckl-phase-5-jonah-review.md).

## Phase 5 Wave 24: Micah

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Amos, Jonah, and Nineveh values, generic corpus dates and setting,
  legacy evidence labels, internal-only sourcing, and false completion and
  review metadata;
- rebuilt the record around Micah 1; 2; 3; 4–5; 6; and 7 while preserving
  three-cycle, judgment-and-salvation, final-form, and redactional outlines;
- distinguished Micah of Moresheth, YHWH, framing and prophetic voices,
  capitals and communities, land-grabbers and dispossessed households,
  rulers, prophets, priests, judges, seers, diviners, daughter Zion, remnant,
  Bethlehem ruler, woman in labor, shepherds, creation witnesses, Assyria,
  Babylon, nations, enemies, and later interpreters;
- distinguished twelve genre and mode groupings and added thirty-four granular
  claims plus fifty-two structured notes using current evidence taxonomies;
- added Masoretic Micah, Hebrew Bible and New Testament comparanda, Old Greek
  Michaias, CATSS, NETS, 4Q81, 4Q82, MurXII, Greek 8HevXII, commentaries,
  the Sennacherib Prism, Lachish reliefs, and early Jewish, Jewish-life,
  Christian, artistic, postcolonial, gender-critical, ecological, and
  trauma-aware sources, including twenty-three URL-bearing external records;
- qualified Moresheth, Shephelah puns and route, Jotham, Ahaz, Hezekiah,
  Samaria 722/721, Sennacherib 701, Lachish, Assyrian ideology, landholding,
  debt, courts, patronage, social location, eighth-century prophetic memory,
  later additions, final form, and Book-of-the-Twelve shaping;
- preserved uncertainty concerning speakers and quotation boundaries,
  breaker and remnant, prophetic feeding imagery, Jeremiah 26 reception,
  Micah 4 / Isaiah 2 priority, Babylon, numbering, Bethlehem ruler, ancient
  origins, woman in labor, seven/eight leaders, Assyria, purification, Micah
  6 genre and syntax, Omri and Ahab, Micah 7 voices, divine-name wordplay,
  date, unity, redaction, and purpose;
- distinguished historical referent, prophetic memory, compiler, quotation,
  parallel, disputed borrowing, shared tradition, canonical trajectory,
  Jewish messianic, Christian christological, artistic, social-justice,
  political, and modern analogical readings;
- added safeguards concerning antisemitism, supersessionism, anti-ritualism,
  partisan capture, poverty romanticization, land and housing abuse, coercion,
  child sacrifice, domestic violence, weaponized humility and forgiveness,
  disability stigma, gender stereotypes, racism, nationalism, Zionism and
  anti-Zionism mappings, colonialism, empire, war, genocide, displacement,
  disaster blame, survivor safety, and trauma;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-micah-review.md`](ckl-phase-5-micah-review.md).

## Phase 5 Wave 25: Nahum

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Amos, and Jonah values, generic dates and setting, internal-only
  sourcing, legacy labels, and false completion and review metadata;
- rebuilt the record around Nahum 1:1; 1:2–8; 1:9–15; 2:1–13; 3:1–7;
  3:8–13; and 3:14–19, preserving Hebrew/common-English numbering and
  disputed speakers, addressees, sequence, quotation boundaries, and seams;
- distinguished Nahum the Elkoshite, framing and prophetic voices, YHWH,
  Judah, Jacob, good-news messenger, wicked counselor or Belial figure,
  Nineveh as city and feminized personification, Assyrian king, scatterer,
  attackers, soldiers, captives, children, merchants, scribes, guards,
  commanders, shepherds, nobles, peoples, nations, lions, locusts, and later
  interpreters;
- distinguished thirteen genre and mode groupings and added twenty-seven
  granular claims plus forty-six structured notes using current evidence
  taxonomies;
- qualified Elkosh, the 663–612 BCE historical window, Sennacherib,
  Esarhaddon, Ashurbanipal, Thebes, Assyrian contraction, the
  Babylonian-Median campaign, Nineveh's 612 fall, walls, gates, canals,
  palace, trade, tribute, deportation, siege, plunder, and fire;
- added Masoretic Nahum, Hebrew Bible and New Testament comparanda, Old Greek
  Naoum, CATSS, NETS, BHS, 4Q82, 4Q169, Qumran research, critical
  commentaries, feminist and womanist work, BM 21901, Ashurbanipal's royal
  inscriptions, Thebes history, and Assyrian palace and lion imagery,
  including twenty-two URL-bearing external records;
- preserved uncertainty concerning the title, acrostic, chapter 1 sequence,
  plotter, Belial, numbering, messenger, scatterer, battle vocabulary, river
  gates, palace, pool, flood theory, lions, translation and ethics of 3:4–7,
  Thebes' allies, Put, sorcery, locusts, offices, shepherds, nobles, king,
  wound, date, unity, redaction, purpose, and Twelve shaping;
- distinguished biblical text, historical reconstruction, royal propaganda,
  archaeology, textual witness, translation, pesher, verbal parallel,
  canonical contrast, typology, christological reception, postcolonial
  reception, pastoral application, and modern analogy;
- added safeguards concerning antisemitism, supersessionism, anti-Iraqi and
  anti-Middle Eastern racism, modern Assyrian ethnic proxies, collective
  guilt, sexualized humiliation, misogyny, sex-worker stigma, child-killing
  imagery, survivor blame, trauma voyeurism, siege, torture, plunder,
  genocide, displacement, collective punishment, revenge, nationalism,
  colonialism, ecological harm, war propaganda, and partisan enemy-mapping;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-nahum-review.md`](ckl-phase-5-nahum-review.md).

## Phase 5 Wave 26: Habakkuk

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated
  Hosea, Amos, Jonah, and Nineveh values, generic dates and setting,
  internal-only sourcing, legacy labels, and false completion metadata;
- rebuilt the record around Habakkuk 1:1; 1:2–4; 1:5–11; 1:12–17; 2:1;
  2:2–5; 2:6–20; 3:1–2; 3:3–15; and 3:16–19, preserving uncertainty about
  voices, addressees, quotation boundaries, imperatives, pronouns, *selah*,
  and proposed seams;
- distinguished Habakkuk's framing, complaint, watch, prayer, and singing
  voices; YHWH; Judah's wicked and righteous; Torah and justice; Chaldeans;
  arrogant conqueror; conquered and taunting peoples; debtors; idol makers;
  the silent earth; creation; anointed one; agricultural world; musicians;
  and later interpreters;
- distinguished thirteen genre and mode groupings and added twenty-eight
  granular claims plus forty-six structured notes using current evidence
  taxonomies;
- qualified the late-seventh/early-sixth-century horizon, Assyria's collapse,
  Nineveh in 612, Harran in 609, Carchemish in 605, Jehoiakim, Babylonian
  pressure, Jerusalem in 597 and 586, fortification, siege, cavalry,
  deportation, tribute, debt, labor, construction, wine, idolatry, and ecology;
- added Masoretic Habakkuk, Hebrew Bible and New Testament comparanda, Old
  Greek Ambakoum, CATSS, NETS, BHS, 1QpHab, critical commentaries, womanist
  and feminist work, BM 21901, BM 21946, Neo-Babylonian inscriptions, and
  early Jewish, Christian, artistic, postcolonial, trauma-aware, and
  ecological resources, including twenty-one URL-bearing external records;
- preserved uncertainty concerning title, biography, date, addressees,
  divine agency, wicked and righteous, watchpost, tablets, runner, appointed
  time, Habakkuk 2:4, five woes, debt, Sheol, cup, foreskin or nakedness,
  Lebanon, animals, idols, temple, chapter 3, *shigionoth*, *selah*, Teman,
  Paran, Cushan, Midian, cosmic imagery, anointed one, enemy head, musical
  subscription, unity, redaction, liturgy, and Twelve shaping;
- distinguished biblical text, historical reconstruction, royal
  self-presentation, archaeology, textual witness, translation, pesher,
  quotation, canonical trajectory, doctrinal reception, typology, pastoral
  application, and modern analogy;
- added safeguards concerning antisemitism, faith-versus-law anti-Judaism,
  supersessionism, anti-Iraqi and anti-Middle Eastern racism, ethnic proxies,
  quietism, fatalism, prosperity teaching, survivor blame, mental-health and
  disability stigma, sexualized humiliation, conquest, siege, forced labor,
  plunder, genocide, displacement, collective punishment, nationalism,
  colonialism, ecological destruction, war propaganda, revenge, trauma
  voyeurism, and partisan enemy-mapping;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-habakkuk-review.md`](ckl-phase-5-habakkuk-review.md).

## Phase 5 Wave 27: Zephaniah

Completed implementation work:

- removed the inherited Minor Prophets placeholder, including unrelated Hosea,
  Amos, Jonah, and Nineveh values, corpus-wide dates and setting,
  internal-only sourcing, legacy labels, and false completion metadata;
- rebuilt the record around Zephaniah 1:1; 1:2–6; 1:7–13; 1:14–18; 2:1–3;
  2:4–7; 2:8–11; 2:12–15; 3:1–7; 3:8–13; and 3:14–20 while preserving
  uncertainty about speakers, addressees, imperatives, pronouns, textual
  forms, and proposed seams;
- distinguished Zephaniah and the framing voice; YHWH; Judah, Jerusalem,
  officials, royal sons, foreign-clothed people, threshold leapers, merchants,
  complacent residents, humble and poor people, remnant, nations, Daughter
  Zion, dispersed worshipers, leaders, animals, creation, and later
  interpreters;
- distinguished superscription, creation reversal, cultic accusation,
  sacrifice metaphor, Day lament and battle cry, gathering and seeking
  summons, nation oracles, taunts, city woe, courtroom accusation, remnant
  promise, hymn, divine-warrior promise, and restoration;
- added thirty-one granular claims and fifty structured interpretive notes
  using current evidence taxonomies;
- qualified Josiah's reign, reform chronology, Manasseh's legacy, Assyrian
  decline, Scythian proposals, Nineveh before or after 612 BCE, Jerusalem
  topography and economy, imperial sources, and proposed later shaping;
- added Masoretic Zephaniah, Hebrew Bible and New Testament comparanda, Old
  Greek Sophonias, CATSS, NETS, BHS, 4Q77, 4Q78, 1Q15, 4Q170, critical
  commentaries, womanist and feminist work, BM 21901, Neo-Assyrian
  inscriptions, and early Jewish, Christian, artistic, postcolonial,
  trauma-aware, and ecological resources, including twenty-one URL-bearing
  external records;
- preserved uncertainty concerning Cushi, Hezekiah, ancestry, date, reform,
  Scythians, cult terminology, foreign clothing, threshold practice,
  sacrifice guests, Jerusalem districts, lamp search, wine dregs, Day
  development, the summoned nation, Cherethites, Canaan, Moab, Ammon, Cush,
  Nineveh, the unnamed city, purified speech, rivers of Cush, remnant,
  Zephaniah 3:17, disability language, final syntax, unity, redaction,
  liturgy, and Twelve shaping;
- distinguished history, prophetic accusation, divine speech, rhetoric,
  metaphor, archaeology, textual witness, translation, pesher, allusion,
  canonical trajectory, doctrine, typology, application, and modern analogy;
- added safeguards concerning antisemitism, supersessionism, anti-Black and
  anti-African racism, anti-Palestinian and anti-Arab mapping, modern ethnic
  proxies, disability stigma, poverty romanticization, victim and disaster
  blame, silencing survivors, ecological destruction, animal harm, war,
  genocide, ethnic cleansing, displacement, collective punishment,
  nationalism, colonialism, revenge, and partisan enemy-mapping;
- added explicit section statuses and knowledge-layer classifications;
- populated the hermeneutical lens and retrieval metadata;
- kept the record as `draft` / `in_review`, with human review missing;
- added eight factual, structure, evidence, retrieval, safety, and SQLite
  parity regression tests; and
- added a reviewer-facing handoff at
  [`ckl-phase-5-zephaniah-review.md`](ckl-phase-5-zephaniah-review.md).

## Validation performed

Completed after Phases 2–4:

```text
python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced section-migration warnings,
# 0 errors
```

The full CKL suite, including generated SQLite parity, was verified:

```text
python3 -m unittest tests/canonical_library/test_*.py

Ran 187 tests in 22.106s: OK
```

The broader repository suite was additionally attempted with
`python3 -m unittest discover -s tests -t .`. Under the available Python 3.14
runtime it emitted a very large volume of pre-existing unclosed-SQLite
`ResourceWarning` messages, had reported errors in non-CKL modules, and had not
completed after an extended run. It was stopped. The errors were outside the
CKL-focused suite, but the interrupted run did not produce a reliable final
count. A future repository-wide validation should use the project’s supported
test environment and address or suppress those existing resource warnings.
This does not change the clean 187-test CKL result above.

Completed after Phase 5 Wave 1:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 195 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,040 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

The Python 3.14 CKL run still emits known `ResourceWarning` messages for
unclosed SQLite connections in existing tests, but exits successfully.

Completed after Phase 5 Wave 2:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 203 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,060 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave2-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave2-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

Completed after Phase 5 Wave 3:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 211 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,074 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave3-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave3-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

Completed after Phase 5 Wave 4:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 219 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,085 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave4-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave4-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

Completed after Phase 5 Wave 5:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 227 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,093 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave5-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave5-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

Completed after Phase 5 Wave 6:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 235 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,099 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave6-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave6-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

Completed after Phase 5 Wave 7:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 243 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,116 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave7-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave7-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint verified
```

Completed after Phase 5 Wave 8:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 251 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,131 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave8-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave8-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 3ce0b541475a91e7fd1e20fbf2ea538b1db0c447199d5688cdcb77db3bd329af
```

Completed after Phase 5 Wave 9:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 259 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,135 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave9-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave9-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 4d772ce60d80fa1892edb1fcee97977a0b56563205fbd7741eea4450c25f925f
```

Completed after Phase 5 Wave 10:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 267 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,140 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave10-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave10-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# d5008afbe209687fc1741aff6085bed04aff8cb51eb1709657f33b4b4af6632a
```

Completed after Phase 5 Wave 11:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 276 tests in 450.173s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,146 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave11-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave11-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 2255e2ba7edd4aa7440e36bd9db91ee2c08364e7dd5f34f10f1c3a98d7aa70c8
```

Completed after Phase 5 Wave 12:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 284 tests in 131.549s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,150 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave12-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave12-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# fdfbed1572f68cf93ff8ff8c4826dd45bb7502fece5d1d158961945da24ffb75
```

Completed after Phase 5 Wave 13:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 292 tests in 141.295s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,154 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave13-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave13-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# c9a455182562a0643598288b46d959ee6db480cce1ef354d8f3f022e0db7f257
```

Completed after Phase 5 Wave 14:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 300 tests in 154.784s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,158 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave14-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave14-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# e0d0db6ebcaee7ef80932e5fbc16fab278fe002cd28b83df59ad89493cdcc33a
```

Completed after Phase 5 Wave 15:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 308 tests in 176.113s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,167 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave15-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave15-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 655147716152b57c22e160bd8eb4b93eed57d7b9f2ee932e82a114592e348cf2
```

Completed after Phase 5 Wave 16:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 316 tests in 178.856s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,174 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave16-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave16-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# a7b15da9fcb6f2a3b9d4eaf4fdf172dcf7c1a3db31e1828e6d61e1b277029821
```

Completed after Phase 5 Wave 17:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 324 tests in 193.789s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,181 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave17-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave17-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 5e1c28f8d78492241fb86836e6be1d78c21928bda3b3bb200b35e48dfd166d7f
```

Completed after Phase 5 Wave 18:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 332 tests in 207.613s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,185 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave18-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave18-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# cbad451a560572487c5aeca590904a3fc8c730b6272deb8472f6f49436976509
```

Completed after Phase 5 Wave 19:

```text
python3 -m unittest tests/canonical_library/test_*.py
# 340 tests in 228.597s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,188 edges, 0 unknown targets, 0 orphaned objects

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave19-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave19-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b5d829df74e7123152aedd477e2c7c64af170d2df69453f3b8d055e2326afee3
# 33,894,400 bytes
```

Completed after Phase 5 Wave 20:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/joel.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_joel_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 17.871s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 348 tests in 243.165s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,190 edges, 0 unknown targets, 0 orphaned objects
# 2,754 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave20-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave20-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# f2a8ee145bd96a603a5c5fe79bbb82a9dab8f589be73387b170f3637bcec44cf
# 34,361,344 bytes
```

Completed after Phase 5 Wave 21:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/amos.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_amos_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 16.294s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 356 tests in 251.029s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 5
# 620 objects, 3,192 edges, 0 unknown targets, 0 orphaned objects
# 2,752 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave21-final-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave21-final-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 31356a8bf9bc6325121549155cc5b09884555a79967651b1ee5a2fe4038b86fc
# 34,738,176 bytes
```

Completed after Phase 5 Wave 22:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/obadiah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_obadiah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 16.858s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 364 tests in 276.882s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,194 edges, 0 unknown targets, 0 orphaned objects
# 2,754 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave22-final-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave22-final-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# d48df68d09650c084794370c6b36838eb999f6b9adf3ecdd7264d32237d2d84d
# 35,201,024 bytes
```

Completed after Phase 5 Wave 23:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/jonah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_jonah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 16.944s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 372 tests in 310.730s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,197 edges, 0 unknown targets, 0 orphaned objects
# 2,757 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave23-final-ckl.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave23-final-ckl.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 5c7b6961edbc467cd5af81327c86ea4b9804797915b4e72c657e7ef78c030b72
# 35,598,336 bytes
```

Completed after Phase 5 Wave 24:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/micah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_micah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 18.271s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 380 tests in 309.279s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,200 edges, 0 unknown targets, 0 orphaned objects
# 2,760 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave24-micah.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave24-micah.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 8dfdde1054284dd7574072d55fe53480d19082770806299ab16320ce38261049
# 36,188,160 bytes
```

Completed after Phase 5 Wave 25:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/nahum.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_nahum_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 17.853s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 388 tests in 320.569s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,203 edges, 0 unknown targets, 0 orphaned objects
# 2,763 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave25-nahum.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave25-nahum.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b18535bd7ff7307361fe9a6b3528499be722fc8b9fd552390aac2eeb166c1572
# 36,687,872 bytes
```

Completed after Phase 5 Wave 26:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/habakkuk.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_habakkuk_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 18.142s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 396 tests in 334.794s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,206 edges, 0 unknown targets, 0 orphaned objects
# 2,766 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave26-habakkuk.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave26-habakkuk.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 71e940f7ae9995b8d53390a5fc181d398aef12c315ae57af8a6af7cdb823baca
# 37,212,160 bytes
```

Completed after Phase 5 Wave 27:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/zephaniah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_zephaniah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 25.944s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 404 tests in 1289.225s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,210 edges, 0 unknown targets, 0 orphaned objects
# 2,770 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave27-zephaniah.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave27-zephaniah.sqlite
# 620 objects; database schema 2; inventory fingerprint
# c0b63df3d964dfc4591f9701f026dedd1f35092b5da4b96cf3ff2dac92733ad4
# 37,728,256 bytes
```

Completed after Phase 5 Wave 28:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/haggai.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_haggai_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 19.128s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 412 tests in 390.878s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,217 edges, 0 unknown targets, 0 orphaned objects
# 2,777 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave28-haggai.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave28-haggai.sqlite
# 620 objects; database schema 2; inventory fingerprint
# c09fc50d0818d60a1a057708ee3df6e46480f9b4690b4dae3e9e249c1e0010f7
# 38,334,464 bytes
```

Completed after Phase 5 Wave 29:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/zechariah.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_zechariah_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 20.115s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 420 tests in 404.465s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,224 edges, 0 unknown targets, 0 orphaned objects
# 2,784 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave29-zechariah.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave29-zechariah.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 29727dfc85b40a191d9fb706d29967cbcd595f796b2cf2a9195133201bdc071c
# 39,034,880 bytes
```

Completed after Phase 5 Wave 30:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/malachi.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_malachi_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 22.324s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 428 tests in 455.900s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,231 edges, 0 unknown targets, 0 orphaned objects
# 2,791 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave30-malachi.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave30-malachi.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 984d38c758f8ccbf8b565e3068e48d6bb2862681b80a038f6014801b323145ea
# 39,620,608 bytes
```

Completed after Phase 5 Wave 31:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/matthew.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_matthew_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 22.168s: OK

python3 -m unittest \
  tests.canonical_library.test_matthew_record \
  tests.canonical_library.test_quality_report
# 10 tests in 16.312s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 436 tests in 466.765s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,239 edges, 0 unknown targets, 0 orphaned objects
# 2,797 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave31-matthew.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave31-matthew.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b9e0b8cf50db951a391a5e326e94d99c1bb1b74fa3f4361d179385c32cfccc14
# 40,280,064 bytes
```

Completed after Phase 5 Wave 32:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/mark.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_mark_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 22.778s: OK

python3 -m unittest \
  tests.canonical_library.test_mark_record \
  tests.canonical_library.test_malachi_record \
  tests.canonical_library.test_matthew_record \
  tests.canonical_library.test_ckl_retrieval_service
# 35 tests in 54.709s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 444 tests in 505.600s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,247 edges, 0 unknown targets, 0 orphaned objects
# 2,805 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave32-mark-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave32-mark-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 26ab61e0b783a0d00fb9f053c7e63c8d2f15aa60f41714781905005561e98262
# 40,898,560 bytes
```

Completed after Phase 5 Wave 33:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/luke.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_luke_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 24.216s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 452 tests in 551.680s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,248 edges, 0 unknown targets, 0 orphaned objects
# 2,806 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave33-luke-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave33-luke-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# c05fa262311788db24622ce4731ed3644908a6f537a3b1dec1e9df64d4237e0c
# 41,521,152 bytes
```

Completed after Phase 5 Wave 34:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/john.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_john_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 26.615s: OK

python3 -m unittest tests/canonical_library/test_*.py
# 460 tests in 610.725s: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,255 edges, 0 unknown targets, 0 orphaned objects
# 2,813 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave34-john-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave34-john-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 708a6558c7d91eeeb8e1ff52c78e76bf973126f9282bb34cac1b236b99596717
# 42,274,816 bytes
```

Completed after Phase 5 Wave 35:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/acts.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_acts_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 31.394s: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 160 + 154 + 154 = 468 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,259 edges, 0 unknown targets, 0 orphaned objects
# 2,815 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave35-acts-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave35-acts-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 059064f7668d71e5cdbd12504a28ad5c2a65d01f1faf862f90548901f30752dc
# 42,840,064 bytes
```

Completed after Phase 5 Wave 36:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/romans.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_romans_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests in 31.555s: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 168 + 154 + 154 = 476 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,264 edges, 0 unknown targets, 0 orphaned objects
# 2,818 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave36-romans-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave36-romans-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 7d8b96ada95ae5ca995d6c8337fb7275cf1edfdffa424bd7e9ac8b5d7a09560e
# 43,405,312 bytes
```

Completed after Phase 5 Wave 37:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/1-corinthians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_1_corinthians_record \
  tests.canonical_library.test_haggai_record.HaggaiRecordTests.test_retrieval_answers_haggai_specific_questions \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 79 tests in 49.335s: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 176 + 154 + 154 = 484 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,268 edges, 0 unknown targets, 0 orphaned objects
# 2,822 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave37-1-corinthians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave37-1-corinthians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# d565d703d4eb9fdeb58ec875e46bcb056020da65da1f7f114c461ac9418e4081
# 44,101,632 bytes
```

Completed after Phase 5 Wave 38:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/2-corinthians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_2_corinthians_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# focused suite: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 184 + 151 + 157 = 492 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,271 edges, 0 unknown targets, 0 orphaned objects
# 2,825 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave38-2-corinthians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave38-2-corinthians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# 6143bd5bf47f7ceb9e69e17bd58b4947f5ea953d34d532289178f8ef72a640b5
# 44,666,880 bytes
```

Completed after Phase 5 Wave 39:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/galatians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_galatians_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 192 + 151 + 157 = 500 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,274 edges, 0 unknown targets, 0 orphaned objects
# 2,828 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave39-galatians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave39-galatians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b38c3543f0b98688e29da6d25e18804b8afe62d933005609059a36b9b314a859
# 45,240,320 bytes
```

Completed after Phase 5 Wave 40:

```text
python3 tools/ckl_validate.py \
  --path framework/canonical_library/objects/books/ephesians.json
# 1 valid object, 0 warnings, 0 errors

python3 -m unittest \
  tests.canonical_library.test_ephesians_record \
  tests.canonical_library.test_ckl_retrieval_service \
  tests.canonical_library.test_schema \
  tests.canonical_library.test_quality_report
# 78 tests: OK

rg --files tests/canonical_library -g 'test_*.py' |
  sort |
  xargs -n 20 -P 3 python3 -m unittest
# 200 + 151 + 157 = 508 tests: OK

python3 tools/ckl_validate.py --root framework/canonical_library
# 620 files, 620 valid objects, 14 coalesced migration warnings, 0 errors

python3 tools/ckl_graph_audit.py --root framework/canonical_library --limit 10
# 620 objects, 3,277 edges, 0 unknown targets, 0 orphaned objects
# 2,831 missing reciprocal suggestions remain as migration debt

python3 -m framework.canonical_library build-db \
  --root framework/canonical_library \
  --output /private/tmp/bhf-phase5-wave40-ephesians-final.sqlite

python3 -m framework.canonical_library verify-db \
  --root framework/canonical_library \
  --database /private/tmp/bhf-phase5-wave40-ephesians-final.sqlite
# 620 objects; database schema 2; inventory fingerprint
# b0a3ab5baeab87f3932601a3ead69174f85da0591c0fdd5218ff656d48a5842c
# 45,711,360 bytes
```

The refreshed Wave 36 report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 576 / 44 |
| Raw records missing explicit `section_status` | 576 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 576 |
| Interpretive notes using current taxonomies | 1,326 |
| Interpretive notes still using legacy taxonomies | 1,230 |
| Granular claims authored | 830 |
| External sources | 1,001 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Validator warnings / errors | 14 / 0 |

The refreshed Wave 37 report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 575 / 45 |
| Raw records missing explicit `section_status` | 575 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 575 |
| Interpretive notes using current taxonomies | 1,414 |
| Interpretive notes still using legacy taxonomies | 1,228 |
| Granular claims authored | 874 |
| External sources | 1,035 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Validator warnings / errors | 14 / 0 |

The refreshed Wave 38 report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 574 / 46 |
| Raw records missing explicit `section_status` | 574 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 574 |
| Interpretive notes using current taxonomies | 1,489 |
| Interpretive notes still using legacy taxonomies | 1,226 |
| Granular claims authored | 914 |
| External sources | 1,064 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Validator warnings / errors | 14 / 0 |

The refreshed Wave 39 report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 573 / 47 |
| Raw records missing explicit `section_status` | 573 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 573 |
| Interpretive notes using current taxonomies | 1,549 |
| Interpretive notes still using legacy taxonomies | 1,224 |
| Granular claims authored | 950 |
| External sources | 1,093 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Validator warnings / errors | 14 / 0 |

The refreshed Wave 40 report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 572 / 48 |
| Complete records with candidate Phase 2 section gaps | 571 |
| Raw records missing explicit `section_status` | 572 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 572 |
| Interpretive notes using current taxonomies | 1,595 |
| Interpretive notes still using legacy taxonomies | 1,222 |
| Granular claims authored | 978 |
| External sources | 1,116 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,277 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,831 |
| Validator warnings / errors | 14 / 0 |

The refreshed Wave 42 report records (Wave 41 Philippians is reflected in
these cumulative totals):

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 570 / 50 |
| Complete records with candidate Phase 2 section gaps | 569 |
| Raw records missing explicit `section_status` | 570 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 570 |
| Interpretive notes using current taxonomies | 1,692 |
| Interpretive notes still using legacy taxonomies | 1,218 |
| Granular claims authored | 1,036 |
| External sources | 1,164 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,283 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,835 |
| Validator warnings / errors | 14 / 0 |

## Recommended next wave

Perform the human review checklists in
[`ckl-phase-5-genesis-exodus-review.md`](ckl-phase-5-genesis-exodus-review.md)
and
[`ckl-phase-5-leviticus-numbers-review.md`](ckl-phase-5-leviticus-numbers-review.md)
and
[`ckl-phase-5-deuteronomy-joshua-review.md`](ckl-phase-5-deuteronomy-joshua-review.md)
and
[`ckl-phase-5-judges-ruth-review.md`](ckl-phase-5-judges-ruth-review.md)
and
[`ckl-phase-5-samuel-review.md`](ckl-phase-5-samuel-review.md)
and
[`ckl-phase-5-kings-review.md`](ckl-phase-5-kings-review.md)
and
[`ckl-phase-5-chronicles-review.md`](ckl-phase-5-chronicles-review.md)
and
[`ckl-phase-5-ezra-nehemiah-review.md`](ckl-phase-5-ezra-nehemiah-review.md)
and
[`ckl-phase-5-esther-review.md`](ckl-phase-5-esther-review.md)
and
[`ckl-phase-5-job-review.md`](ckl-phase-5-job-review.md)
and
[`ckl-phase-5-psalms-review.md`](ckl-phase-5-psalms-review.md)
and
[`ckl-phase-5-proverbs-review.md`](ckl-phase-5-proverbs-review.md)
and
[`ckl-phase-5-ecclesiastes-review.md`](ckl-phase-5-ecclesiastes-review.md)
and
[`ckl-phase-5-song-of-songs-review.md`](ckl-phase-5-song-of-songs-review.md)
and
[`ckl-phase-5-isaiah-review.md`](ckl-phase-5-isaiah-review.md)
and
[`ckl-phase-5-jeremiah-review.md`](ckl-phase-5-jeremiah-review.md)
and
[`ckl-phase-5-ezekiel-review.md`](ckl-phase-5-ezekiel-review.md)
and
[`ckl-phase-5-daniel-review.md`](ckl-phase-5-daniel-review.md)
and
[`ckl-phase-5-hosea-review.md`](ckl-phase-5-hosea-review.md)
and
[`ckl-phase-5-joel-review.md`](ckl-phase-5-joel-review.md)
and
[`ckl-phase-5-amos-review.md`](ckl-phase-5-amos-review.md)
and
[`ckl-phase-5-obadiah-review.md`](ckl-phase-5-obadiah-review.md)
and
[`ckl-phase-5-jonah-review.md`](ckl-phase-5-jonah-review.md)
and
[`ckl-phase-5-micah-review.md`](ckl-phase-5-micah-review.md)
and
[`ckl-phase-5-nahum-review.md`](ckl-phase-5-nahum-review.md)
and
[`ckl-phase-5-habakkuk-review.md`](ckl-phase-5-habakkuk-review.md)
and
[`ckl-phase-5-zephaniah-review.md`](ckl-phase-5-zephaniah-review.md)
and
[`ckl-phase-5-haggai-review.md`](ckl-phase-5-haggai-review.md)
and
[`ckl-phase-5-zechariah-review.md`](ckl-phase-5-zechariah-review.md)
and
[`ckl-phase-5-malachi-review.md`](ckl-phase-5-malachi-review.md)
and
[`ckl-phase-5-matthew-review.md`](ckl-phase-5-matthew-review.md)
and
[`ckl-phase-5-mark-review.md`](ckl-phase-5-mark-review.md)
and
[`ckl-phase-5-luke-review.md`](ckl-phase-5-luke-review.md)
and
[`ckl-phase-5-john-review.md`](ckl-phase-5-john-review.md)
and
[`ckl-phase-5-acts-review.md`](ckl-phase-5-acts-review.md)
and
[`ckl-phase-5-romans-review.md`](ckl-phase-5-romans-review.md)
and
[`ckl-phase-5-1-corinthians-review.md`](ckl-phase-5-1-corinthians-review.md)
and
[`ckl-phase-5-2-corinthians-review.md`](ckl-phase-5-2-corinthians-review.md)
and
[`ckl-phase-5-galatians-review.md`](ckl-phase-5-galatians-review.md)
and
[`ckl-phase-5-ephesians-review.md`](ckl-phase-5-ephesians-review.md)
and
[`ckl-phase-5-philippians-review.md`](ckl-phase-5-philippians-review.md)
and
[`ckl-phase-5-colossians-review.md`](ckl-phase-5-colossians-review.md).
Do not mark any corrected record complete merely because its automated checks
pass.

Wave 42 Colossians is complete. The completed Matthew, Mark, Luke, John, Acts,
Romans, 1 Corinthians, 2 Corinthians, Galatians, Ephesians, Philippians, and
Colossians scopes are retained below for audit:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against the book it describes;
3. gather Scripture anchors and independent sources before drafting claims;
4. distinguish the framing voice, Habakkuk in complaint, prayer, watch, and
   first-person response, YHWH's direct answers and reported action, Judah's
   wicked and righteous, Torah and justice as personified or social realities,
   the Chaldeans or Babylonians, the arrogant one, conquered nations and
   peoples, debtors and taunting witnesses, personified wealth or death,
   makers and worshipers of idols, the silent earth, Cushan, Midian,
   mountains, rivers, sea, sun, moon, horses, the anointed one, musicians,
   fig tree, vine, olive, fields, flock, herd, and later interpreters;
5. map Habakkuk 1:1; 1:2–4; 1:5–11; 1:12–17; 2:1; 2:2–5; 2:6–20; 3:1–2;
   3:3–15; and 3:16–19 while qualifying complaint-answer cycles, watchpost,
   vision-tablet instructions, five-woe sequence, taunt, prayer, divine-warrior
   theophany, psalm, musical directions, and final confession; mark speakers,
   addressees, quotation boundaries, imperatives, *selah*, repetitions,
   pronoun shifts, and proposed seams;
6. qualify Habakkuk's unknown biography, the Chaldeans, Neo-Babylonian rise,
   Assyria's collapse, Nineveh in 612 BCE, Harran in 609, Carchemish in 605,
   Jehoiakim's Judah, Babylonian pressure, the 597 and 586 destructions as
   possible later horizons, fortification, siege ramps, cavalry, deportation,
   tribute, debt, forced labor, timber and stone construction, wine,
   idolatry, and ecology, using Babylonian Chronicles, inscriptions,
   archaeology, and environmental evidence without forcing a single date;
7. distinguish superscription, prophetic complaint or lament, disputation,
   divine response, historical oracle, watchman report, vision instruction,
   wisdom contrast, taunt song, five woe oracles, ridicule, idol polemic,
   temple acclamation, prayer superscription, petition, hymn, divine-warrior
   theophany, victory song, confession of fear and trust, and musical
   subscription;
8. address violence, Torah made numb, justice distorted, the wicked
   surrounding the righteous, divine use of a more wicked nation, human
   agency, empire, conquest, fish and net imagery, pride, faithfulness or
   faith, waiting, appointed time, plunder, debt, exploitation, unjust gain,
   forced labor, blood-built cities, intoxication, sexualized exposure,
   idolatry, divine presence, glory covering the earth, wrath, mercy, exodus
   and creation imagery, the anointed one, trembling, crop and livestock
   failure, joy, strength, and the relationship of protest, judgment,
   perseverance, hope, and theodicy;
9. preserve uncertainty concerning Habakkuk's date and biography, title,
   whether 1:5 addresses Judeans or nations, the Chaldean oracle's original
   function, divine agency and moral culpability, the wicked and righteous,
   complaint-answer boundaries, watchpost imagery, tablet-writing practice,
   vision timing, translation and textual forms of 2:4, the arrogant figure,
   sequence and number of woes, debtor wordplay, *Sheol* or death, Lebanon,
   animals, cup and foreskin or nakedness language, idol vocabulary, temple,
   relation of chapter 3 to chapters 1–2, *shigionoth*, *selah*, Teman, Paran,
   pestilence, rivers, sea, sun and moon, the anointed one, enemy head, and
   musical subscription, as well as unity, redaction, liturgical use, and
   Book-of-the-Twelve shaping;
10. address Masoretic Habakkuk, Old Greek Ambakoum, Judean Desert and
    versional witnesses, 1QpHab Pesher Habakkuk, the Babylonian Chronicles,
    Neo-Babylonian inscriptions and archaeology, Exodus 15, Deuteronomy 32,
    Judges 5, Psalms, Isaiah, Jeremiah, Nahum, Zephaniah, Daniel, Acts 13:41,
    Romans 1:17, Galatians 3:11, Hebrews 10:37–38, early Jewish and Christian
    reception, rabbinic interpretation, patristic and Reformation
    interpretation, “the righteous shall live by faith/faithfulness,”
    liturgy, art and music, liberationist, postcolonial, disability-aware,
    trauma-aware, ecological, and modern political reception;
11. distinguish Babylonian historical referent, prophetic complaint, divine
    speech, rhetorical hyperbole, poetry, metaphor, textual witness, Greek
    translation, pesher interpretation, New Testament quotation, verbal
    parallel, shared tradition, canonical trajectory, doctrinal reception,
    Christian typology, ecclesial application, liberationist reception, and
    modern analogy, especially “How long,” the Chaldeans, watch and wait,
    faith or faithfulness, five woes, cup, idols, divine warrior, anointed
    one, crop failure, and joy;
12. add safeguards concerning antisemitism, anti-Judaism in “faith versus
    law” readings, supersessionism, anti-Iraqi or anti-Middle Eastern racism,
    treating ancient Chaldeans or Babylonians as modern ethnic proxies,
    collective or hereditary guilt, quietism, fatalism, prosperity teaching,
    blaming oppressed people for insufficient faith, coercing survivors to
    wait silently, suicide and mental-health stigma, disability metaphors,
    intoxication and sexualized humiliation, victim blame, dehumanizing fish
    imagery, glorification of conquest, siege, forced labor, plunder,
    genocide, ethnic cleansing, displacement, collective punishment,
    nationalism, colonialism, empire, war propaganda, revenge, divine
    violence, trauma voyeurism, ecological destruction, partisan capture, and
    identifying contemporary cities, religions, or peoples as Chaldeans;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty/dispute labels only where evidence justifies them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 28 Haggai completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Haggai rather than inheriting Minor
   Prophets templates;
3. gather Scripture anchors and independent sources before drafting claims;
4. distinguish the dated framing voice, Haggai as messenger, YHWH's direct
   speech and reported action, Zerubbabel son of Shealtiel as governor,
   Joshua son of Jehozadak as high priest, Darius I, priests answering Torah
   questions, the remnant or people, those who saw the former house, laborers,
   ancestors, nations and kingdoms, heaven, earth, sea, dry land, crops,
   animals, silver, gold, the temple, holy and defiled objects or persons, and
   later interpreters;
5. map Haggai 1:1; 1:2–11; 1:12–15; 2:1–9; 2:10–19; and 2:20–23 while
   qualifying date formulas, messenger formulas, objections, rhetorical
   questions, “consider your ways,” drought and scarcity, obedience, fear,
   “I am with you,” stirred spirits, former and latter glory, “be strong,”
   divine spirit, shaking, nations' treasures or desire, peace, priestly Torah
   consultation, holiness and corpse impurity analogy, foundation, blessing,
   kingdom overthrow, servant, election, and signet;
6. qualify Darius I's second year in 520 BCE, Persian-period Yehud,
   Babylonian destruction in 586, Cyrus and return traditions, Sheshbazzar,
   Zerubbabel, Joshua, Persian administration, imperial authorization,
   Jerusalem's population and economy, drought, agriculture, labor, timber,
   temple foundations, construction, tribute, silver, gold, the temple's 515
   BCE completion as a later Ezra horizon, and modern calendar conversions
   without forcing the book into Ezra's chronology at every point;
7. distinguish superscription, prose prophetic report, messenger formula,
   disputation, accusation, rhetorical question, covenant curse or
   de-creation speech, exhortation, obedience report, divine assurance,
   spirit-stirring notice, dated oracle, comparison with the former temple,
   salvation promise, divine-warrior shaking, priestly Torah inquiry,
   ritual-purity analogy, retrospective oracle, blessing promise, royal
   oracle, servant saying, election formula, and signet metaphor;
8. address procrastination, priorities, paneled houses, scarcity, labor,
   wages, drought, land, crops, animals, obedience, fear, divine presence,
   courage, spirit, temple, glory, silver, gold, nations, peace, holiness,
   impurity, corpses, communal contamination, foundation, blessing, divine
   sovereignty, empire, political upheaval, Zerubbabel, Davidic hope, servant,
   election, signet, restoration, worship, justice, human agency, and hope;
9. preserve uncertainty concerning Haggai's name, title, biography, age,
   relationship to the returned community, date conversions, prose and
   speech sources, redaction, “these people,” paneled houses, reasons for
   delay, economic causation, drought language, former temple witnesses,
   comparative glory, shaking chronology, treasures or desire of all
   nations, filling the house, silver and gold, latter glory, peace, Torah
   consultation, transfer of holiness, corpse impurity, the identity and
   scope of “this people,” foundation date, retrospective crop figures,
   “from this day,” Zerubbabel's historical future, servant, chosen one,
   signet, reversal of Jeremiah 22, messianic reception, unity, liturgy, and
   Book-of-the-Twelve shaping;
10. address Masoretic Haggai, Old Greek Aggaios, Judean Desert and versional
    witnesses, Persian-period inscriptions and administrative evidence,
    Cyrus Cylinder and related imperial sources with perspective labels,
    2 Kings 25, 2 Chronicles 36, Ezra 1–6, Zechariah 1–8, Jeremiah 22 and
    28–29, Leviticus and Numbers purity texts, Hebrews 12:26–29, early Jewish
    and Christian reception, rabbinic, patristic, liturgical, artistic,
    christological, ecclesial, liberationist, feminist, postcolonial,
    disability-aware, trauma-aware, ecological, and modern political
    reception;
11. distinguish dated historical claim, prophetic speech, reported response,
    Persian royal self-presentation, archaeology, economic reconstruction,
    drought rhetoric, covenantal interpretation, Torah analogy, metaphor,
    textual witness, Greek translation, quotation, verbal parallel, shared
    tradition, New Testament reception, canonical trajectory, doctrine,
    typology, christological or ecclesial application, liberationist
    reception, and modern analogy;
12. add safeguards concerning antisemitism, supersessionism, anti-Iranian or
    anti-Persian racism, treating ancient Persia or Yehud as modern proxies,
    modern temple-rebuilding schemes that threaten Jewish, Muslim,
    Palestinian, or other communities and holy sites, coercive fundraising,
    exploitative church building, prosperity teaching, blaming poor or
    displaced people for economic hardship, blaming drought or climate
    disaster on personal sin, forced or unpaid labor, purity stigma involving
    corpses, illness, menstruation, disability, caste, race, or social class,
    glorifying empire or colonial patronage, nationalist and partisan use of
    Zerubbabel, hereditary entitlement, collective guilt, divine violence,
    political upheaval, trauma voyeurism, ecological harm, and silencing
    dissent in the name of obedience;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 29 Zechariah completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Zechariah rather than inheriting Minor
   Prophets templates;
3. gather Scripture anchors and independent sources before drafting claims;
4. distinguish the dated framing voice, Zechariah son of Berechiah son of
   Iddo, YHWH, the angel who speaks with Zechariah, the angel of YHWH, the
   horseman and patrols, Satan or the accuser, Joshua the high priest,
   Zerubbabel, the Branch, the two anointed ones, the flying scroll, the woman
   called Wickedness, the ephah-bearers, four chariots and winds or spirits,
   crowned figures, priests, earlier prophets, Bethel's delegation, the
   remnant, shepherds, flocks, rejected and struck shepherds, Daughter Zion,
   Jerusalem, Judah, nations, a humble king, mourners, living waters, creation,
   and later interpreters;
5. map Zechariah 1:1–6; 1:7–6:15; 7:1–8:23; 9:1–11:17; and 12:1–14:21 while
   also indexing each night vision, symbolic act, oracle, speech, question,
   command, refrain, speaker, addressee, pronoun shift, and proposed seam;
6. qualify Darius I's second through fourth years, 520–518 BCE, early Persian
   Yehud, temple rebuilding, Joshua and Zerubbabel, Persian administration,
   Jerusalem's population and economy, and the much more disputed dates and
   historical horizons of chapters 9–14, including Persian and Hellenistic
   proposals, without forcing the entire book into one moment;
7. distinguish superscription, call to return, prose report, night vision,
   interpreting-angel dialogue, divine-council scene, oracle, accusation,
   symbolic action, sign-act report, crowning, disputation, fasting inquiry,
   ethical exhortation, salvation promise, nation oracle, royal advent,
   shepherd allegory, lament, apocalypse, battle oracle, mourning liturgy,
   purification promise, cosmic transformation, pilgrimage, and holiness
   conclusion;
8. address return, repentance, ancestral memory, divine jealousy and mercy,
   Jerusalem, temple, land, empire, surveillance and patrol, accusation,
   priesthood, cleansing, Branch, spirit, rebuilding, justice, mercy,
   fasting, truth, peace, nations, humble kingship, prisoners, covenant blood,
   shepherds, betrayal, rejection, violence, piercing, mourning,
   purification, remnant, Day of YHWH, kingship, living water, creation, feast,
   holiness, restoration, human agency, and hope;
9. preserve uncertainty concerning Zechariah's genealogy and biography, exact
   vision sequence and number, angelic identities, colored horses, horns and
   craftsmen, measuring line, Satan or accuser, Joshua's garments, Branch,
   stone and seven eyes, lampstand, olive trees and anointed ones, flying
   scroll, ephah and Wickedness, Shinar, chariots and winds or spirits,
   crowns, fasts, prose and oracle sources, unity, redaction, chapters 9–14,
   historical referents, the humble king, covenant blood, shepherds, thirty
   silver pieces, potter or treasury, pierced figure, mourning groups,
   two-thirds, Mount of Olives, living waters, feast, bells, pots, and
   Book-of-the-Twelve shaping;
10. address Masoretic Zechariah, Old Greek Zacharias, Judean Desert and
    versional witnesses, Persian and Hellenistic evidence, Ezra, Haggai,
    Isaiah, Jeremiah, Ezekiel, Daniel, the Psalms, the Gospels, Hebrews,
    Revelation, early Jewish and Christian reception, rabbinic, patristic,
    liturgical, artistic, christological, ecclesial, liberationist, feminist,
    postcolonial, disability-aware, trauma-aware, ecological, and political
    reception;
11. distinguish historical referent, prophetic speech, visionary report,
    angelic interpretation, symbol, royal self-presentation, archaeology,
    textual witness, Greek translation, quotation, allusion, verbal parallel,
    shared tradition, New Testament reception, canonical trajectory, doctrine,
    typology, christological or ecclesial application, liberationist
    reception, and modern analogy;
12. add safeguards concerning antisemitism, supersessionism, anti-Iranian or
    anti-Persian and anti-Greek racism, modern ethnic or political proxies,
    labeling opponents satanic or wicked, priestly and purity stigma,
    disability metaphors, coercive temple or church projects, holy-site
    threats, anti-Palestinian or anti-Muslim readings, nationalism,
    militarism, conquest, siege, divine violence, collective punishment,
    forced labor, betrayal and abuse, trauma voyeurism, prosperity teaching,
    apocalyptic date-setting and conspiracy theories, ecological harm, and
    partisan capture;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 30 Malachi completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Malachi rather than inheriting Minor
   Prophets templates;
3. gather Scripture anchors and independent sources before drafting claims;
4. distinguish the superscription and disputation voice, the possible named
   prophet or title *malakhi*, YHWH's direct speech, priests, Levi and Levites,
   Jacob and Esau, Edom, Judah and Jerusalem, worshipers, blemished animals,
   governor, husbands, wives of youth, people weeping at the altar, the coming
   messenger, the Lord, messenger of the covenant, refiners, sorcerers,
   adulterers, false swearers, wage oppressors, widows, orphans, resident
   aliens, descendants of Jacob, tithers, nations, arrogant and evildoing
   people, those who fear YHWH, a remembrance book, Moses, Elijah, parents,
   children, land, sun, calves, and later interpreters;
5. map Malachi 1:1; 1:2–5; 1:6–2:9; 2:10–16; 2:17–3:5; 3:6–12;
   3:13–21; and 3:22–24 in Hebrew numbering, while recording common Christian
   4:1–6 numbering and indexing each disputation, question, answer,
   accusation, command, quotation boundary, speaker, addressee, pronoun shift,
   messenger saying, and proposed seam;
6. qualify the book's undated Persian-period setting, a functioning Second
   Temple, commonly proposed fifth-century BCE horizons, Persian Yehud,
   priests and Levites, Edom's changed circumstances, imperial
   administration, Jerusalem's population and economy, offerings, livestock,
   wages, tithes, storehouses, agriculture, drought or pests, and uncertain
   relationships before, during, or after Ezra-Nehemiah without inventing one
   exact year or governor;
7. distinguish *massa* superscription, disputation, question-and-answer
   rhetoric, election and love oracle, nation contrast, priestly accusation,
   cultic critique, curse, covenant lawsuit, Torah instruction, lament,
   marriage and kinship accusation, messenger oracle, purification scene,
   judgment catalogue, return call, tithing challenge, blessing promise,
   remembrance notice, eschatological contrast, and Torah-prophetic epilogue;
8. address divine love, Jacob and Esau, Edom, divine name among nations,
   worship, table, food, offerings, priesthood, honor, fear, covenant with
   Levi, Torah knowledge, partiality, communal fatherhood, covenant
   faithlessness, marriage, divorce, violence, tears, justice, delayed
   judgment, messenger, purification, vulnerable neighbors, divine
   constancy, return, tithes, material provision, speech against God,
   remembrance, treasured possession, distinction, Day of YHWH, healing,
   Moses, Elijah, intergenerational repair, curse, human agency, and hope;
9. preserve uncertainty concerning *malakhi* as name or title, authorship and
   date, relation to Ezra-Nehemiah, Edom's historical horizon, Jacob-Esau
   election rhetoric, father and master, polluted food, YHWH's table,
   sacrificial terminology, the rising sun, incense and pure offering among
   nations, governor, covenant with Levi, Torah knowledge, partiality, one
   father and one God in 2:10, foreign-god daughter, cutting off, altar tears,
   wife of youth, the difficult Hebrew of 2:15, hatred or divorce, violence
   and garment, the first messenger, the Lord and covenant messenger, sudden
   coming, refiner and launderer, sons of Levi, tithes and offerings,
   storehouse, testing God, windows of heaven, devourer, remembrance book,
   treasured possession, sun of righteousness, wings, ashes, Horeb, Elijah,
   turning hearts, *herem*, chapter numbering, final-form unity, redaction,
   and Book-of-the-Twelve shaping;
10. address Masoretic Malachi, Old Greek Malachias, Judean Desert and
    versional witnesses, Persian-period inscriptions, archives and
    archaeology, Genesis, Exodus, Leviticus, Numbers, Deuteronomy, Isaiah,
    Jeremiah, Ezekiel, Joel, Obadiah, Haggai, Zechariah, Ezra-Nehemiah, Psalms,
    Matthew, Mark, Luke, Romans, early Jewish and Christian reception,
    rabbinic, patristic, liturgical, artistic, christological, ecclesial,
    liberationist, feminist, womanist, postcolonial, disability-aware,
    trauma-aware, ecological, economic, and political reception;
11. distinguish historical referent, prophetic disputation, divine speech,
    rhetorical question, covenant accusation, cultic critique, metaphor,
    textual witness, Greek translation, quotation, allusion, verbal parallel,
    shared tradition, New Testament reception, canonical trajectory,
    doctrine, typology, christological or ecclesial application,
    liberationist reception, and modern analogy;
12. add safeguards concerning antisemitism, supersessionism, portraying Jews
    or priests as uniquely corrupt, anti-Iranian or anti-Persian racism,
    mapping Edom onto Palestinians, Arabs, Jews, Christians, Muslims, or
    modern states, hereditary or collective guilt, animal harm, purity and
    disability stigma, xenophobic use of marriage language, misogyny,
    coercing people to remain in abusive marriages, excusing domestic
    violence, divorce stigma, silencing spouses or survivors, clerical abuse,
    coercive tithing and fundraising, prosperity teaching, blaming poverty,
    drought, crop loss, illness, infertility, or disaster on insufficient
    giving, exploiting workers, widows, orphans, immigrants, and children,
    forced family reconciliation with abusers, apocalyptic date-setting,
    fear manipulation, ecological harm, nationalism, and partisan capture;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 31 Matthew completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Matthew rather than inheriting Gospels
   and Acts templates, explicitly removing the false Lukan-authorship and Acts
   dating statements, Paul as a key person, duplicated events, and unsupported
   completion metadata;
3. gather Greek-text anchors, Hebrew Bible and Septuagint comparanda,
   manuscript evidence, archaeology, and independent sources before drafting
   claims;
4. distinguish the narrator and embedded speakers, Jesus, Mary, Joseph,
   genealogical figures and women, magi, Herod and his household, John the
   Baptist, Satan or the tempter, disciples and the Twelve, Peter, James, John,
   Matthew the toll collector, women disciples, crowds, children, petitioners,
   centurions, scribes, Pharisees, Sadducees, chief priests, elders, Herod
   Antipas, John’s disciples, Canaanite woman, Roman and Judean authorities,
   Judas, Caiaphas, Pilate, Pilate’s wife, Barabbas, soldiers, Joseph of
   Arimathea, Mary Magdalene, the other Mary, guards, angels, nations, Israel,
   the ekklesia, Father, Son, Spirit, and later interpreters;
5. map Matthew 1:1–4:16; 4:17–7:29; 8:1–11:1; 11:2–13:53;
   13:54–19:2; 19:3–25:46; and 26:1–28:20 while also indexing genealogy,
   infancy narrative, fulfillment formulas, five major discourse endings,
   Sermon on the Mount, mission discourse, parables discourse, community
   discourse, eschatological discourse, controversy sequences, passion,
   resurrection, commission, speakers, audiences, quotations, commands,
   narrative asides, geographic turns, repetitions, and proposed seams;
6. qualify the Gospel’s anonymous internal authorship, later attribution to
   Matthew, debated relationship to Papias, common dependence on Mark and
   other oral or written traditions, proposed dates often around 70–100 CE,
   possible settings and communities, post-70 temple and synagogue debates,
   Jewish and Gentile followers of Jesus, Roman imperial power, Galilee,
   Judea, Jerusalem, Syria proposals, taxation, patronage, households,
   agriculture, fishing, villages, roads, disease, disability, purity,
   crucifixion, burial, and resurrection claims without inventing one author,
   city, audience, date, or community split;
7. distinguish ancient biography or Gospel, genealogy, birth and dream
   narrative, scriptural citation, fulfillment formula, kingdom proclamation,
   call story, healing and exorcism report, controversy, pronouncement,
   commission, aphorism, beatitude, antithesis, prayer, legal instruction,
   wisdom saying, parable, allegorical explanation, miracle story, confession,
   transfiguration, community rule, apocalyptic discourse, passion narrative,
   trial scene, lament, mockery, death scene, empty-tomb narrative,
   appearance, and commissioning scene;
8. address Jesus as Messiah, son of David, son of Abraham, Emmanuel, Son of
   God, Son of Man, teacher and king; kingdom of heaven, righteousness, Torah,
   fulfillment, mercy, justice, purity, faith, doubt, discipleship, mission,
   Israel and nations, church or assembly, authority, forgiveness, wealth,
   poverty, family, children, women, outsiders, leadership, hypocrisy,
   judgment, Gehenna, eschatology, temple, covenant, meal, cross,
   resurrection, divine presence, Spirit, worship, human agency, and hope;
9. preserve uncertainty concerning genealogy structure and names, the four
   women, virgin conception and Isaiah 7:14, dreams, star, magi, Herod,
   Bethlehem, Egypt, massacre, Nazorean formula, temptation, kingdom timing,
   Torah fulfillment, antitheses, divorce exceptions, oaths, retaliation,
   enemy love, Lord’s Prayer wording, almsgiving and fasting, judgment,
   Gehenna, narrow way, miracles, demon language, historicity, mission to
   Israel, Son of Man, John’s doubt, wisdom, parables and hardening, walking
   on water, Canaanite woman, Peter and rock, keys, binding and loosing,
   transfiguration, church discipline, unforgiving servant, eunuchs, rich
   young man, laborers, ransom, triumphal entry, temple action, wicked tenants,
   tribute, resurrection debate, greatest command, woes, blood guilt,
   Jerusalem lament, temple destruction, coming, abomination, tribulation,
   generation, parousia, ten virgins, talents, sheep and goats, anointing,
   Judas, covenant blood, Gethsemane, trials, responsibility for Jesus’ death,
   Barabbas, “his blood,” darkness, earthquake, saints raised, centurion,
   women witnesses, guard story, resurrection appearance, worship and doubt,
   Great Commission, Trinitarian formula, and ending;
10. address major Greek manuscripts and textual variants, Old Latin, Syriac
    and other versional witnesses, Second Temple Jewish texts, Josephus and
    Greco-Roman comparanda, archaeology and inscriptions, Genesis through
    Malachi, Mark, Luke, John, Acts, Paul, Hebrews, James, Revelation, early
    Jewish and Christian reception, patristic, liturgical, artistic,
    christological, Trinitarian, ecclesial, liberationist, Black, womanist,
    feminist, postcolonial, Jewish-Christian-dialogical, disability-aware,
    trauma-aware, ecological, economic, and political reception;
11. distinguish historical claim, narrated event, character speech, parable,
    metaphor, legal interpretation, scriptural quotation, Septuagint wording,
    textual variant, verbal parallel, shared Synoptic tradition, redaction,
    canonical trajectory, doctrine, typology, christological or ecclesial
    application, liberationist reception, and modern analogy;
12. add safeguards concerning antisemitism, supersessionism, deicide and blood
    guilt, collective Jewish blame, portraying Pharisees or Judaism as
    uniquely legalistic or hypocritical, anti-Roman or anti-Italian racism,
    anti-Palestinian or anti-Arab readings, nationalism, empire, colonial
    mission, coercive conversion, forced baptism, religious violence, abuse of
    church discipline and keys, clerical authority, purity and disability
    stigma, demonizing mental illness, misogyny, divorce stigma, forced
    marriage or celibacy, family estrangement, child harm, anti-LGBTQ use,
    racism involving the Canaanite woman or magi, poverty romanticization,
    prosperity teaching, worker exploitation, slavery analogies, victim
    blame, hell and apocalypse fear, date-setting, conspiracy theories,
    ecological harm, silencing doubt or trauma, partisan capture, and modern
    territorial claims;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 32 Mark completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Mark rather than inheriting Gospels and
   Acts templates, explicitly removing the false Lukan-authorship and Acts
   dating statements, Paul as a key person, duplicated events, generic
   resurrection wording that ignores Mark's ending problem, and unsupported
   completion metadata;
3. gather critical Greek-text anchors, Hebrew Bible and Septuagint comparanda,
   manuscript evidence, archaeology, and independent sources before drafting
   claims;
4. distinguish the narrator and scriptural voice, God’s heavenly voice,
   Jesus, the Spirit, John the Baptist, Satan, angels, disciples and the
   Twelve, Peter, James, John, Andrew, women followers, Jesus’ family, crowds,
   children, petitioners, people with diseases and disabilities, people
   described through spirits or demons, Jairus and his daughter, the
   hemorrhaging woman, the Syrophoenician woman and her daughter, the deaf
   man, the blind people at Bethsaida and Jericho, Bartimaeus, scribes,
   Pharisees, Herodians, Sadducees, chief priests, elders, Herod Antipas and
   household, John’s disciples, tax collectors, sinners, wealthy people,
   laborers, tenants, Judas, the high priest, Pilate, Barabbas, soldiers,
   Simon of Cyrene, centurion, Joseph of Arimathea, Mary Magdalene, Mary
   mother of James, Salome, the young man at the tomb, and later interpreters;
5. map Mark 1:1–3:6; 3:7–6:6a; 6:6b–8:21; 8:22–10:52; 11:1–13:37;
   14:1–15:47; and 16:1–8 while indexing prologue, Galilean ministry,
   controversies, parables, sea crossings, feedings, boundary crossings,
   two-stage sight sequence, Caesarea Philippi turn, three passion
   predictions, way to Jerusalem, temple action and controversies,
   eschatological discourse, anointing, meal, Gethsemane, arrest, Jewish and
   Roman hearings, crucifixion, burial, empty tomb, speakers, audiences,
   commands, narrative asides, Aramaic expressions, geographic turns,
   repetitions, intercalations or “sandwiches,” secrecy commands,
   misunderstandings, and proposed seams;
6. qualify the Gospel’s internal anonymity, later attribution to Mark, Papias
   and Peter traditions, common Markan-priority position, oral and written
   tradition, proposed dates often around 65–80 CE, relationship to the
   Jewish revolt and temple destruction, Rome, Syria, Galilee, and other
   setting proposals, Jewish and Gentile hearers, Roman imperial power,
   Galilee, Judea, Jerusalem, villages, cities, roads, boats, fishing,
   agriculture, taxation, patronage, households, purity, illness, disability,
   crucifixion, burial, and resurrection claims without inventing one author,
   city, audience, date, persecution, or community crisis;
7. distinguish ancient biography or Gospel, scriptural incipit, proclamation,
   baptism and temptation, call story, healing, exorcism, controversy,
   pronouncement, commission, aphorism, legal interpretation, parable,
   allegorical explanation, miracle and sea story, feeding, recognition,
   confession, passion prediction, transfiguration, travel narrative,
   prophetic sign action, apocalyptic discourse, anointing, meal, passion,
   trial, mockery, lament, death, burial, and empty-tomb narrative;
8. address Jesus as Messiah, Son of God, Son of Man, teacher, healer,
   exorcist, servant, suffering and vindicated figure, and king; gospel,
   kingdom of God, authority, Spirit, wilderness, conflict, secrecy,
   misunderstanding, hard hearts, fear, faith, discipleship, following on the
   way, cross-bearing, service, ransom, purity, Sabbath, food, family,
   children, women, outsiders, disability, wealth, poverty, leadership,
   prayer, forgiveness, temple, covenant meal, abandonment, cross, burial,
   empty tomb, promised Galilee, human agency, failure, hope, and witness;
9. preserve uncertainty concerning the opening title and “Son of God”
   variant, composite Isaiah citation, baptismal voice, temptation, unclean
   spirits, Sabbath and purity disputes, Son of Man, forgiveness authority,
   fasting, wineskins, Beelzebul, eternal sin, Jesus’ family, parables and
   hardening, Gerasene/Gadarene/Gergesene geography, Legion and pigs, Jairus’
   daughter, hemorrhaging woman, Nazareth rejection, John’s death, two
   feedings, walking on sea, food purity and Mark 7:19, Syrophoenician woman,
   Aramaic words, two-stage sight, Peter’s confession and rebuke,
   transfiguration, Elijah, failed exorcism, divorce, children, wealth,
   ransom, Bartimaeus, entry, fig tree, temple action, tenants, tribute,
   greatest command, widow’s gift, temple destruction, abomination,
   tribulation, this generation, coming Son of Man, anointing, covenant blood,
   Gethsemane, naked fleeing young man, hearings, Barabbas, responsibility for
   Jesus’ death, darkness, cry of dereliction, curtain, centurion, women,
   burial, tomb, young man, fear and silence, ending at 16:8, shorter and
   longer endings, and Freer Logion;
10. address major Greek manuscripts and textual variants, especially Mark
    1:1, 7:19, 10:24, 14:24, 15:28, and 16:8–20; Old Latin, Syriac, Coptic,
    and other versions; Second Temple Jewish texts; Josephus and Greco-Roman
    comparanda; archaeology and inscriptions; Genesis through Malachi;
    Matthew, Luke, John, Acts, Paul, Hebrews, James, 1 Peter, and Revelation;
    early Jewish and Christian reception; patristic, liturgical, artistic,
    christological, sacramental, ecclesial, liberationist, Black, womanist,
    feminist, postcolonial, Jewish-Christian-dialogical, disability-aware,
    trauma-aware, ecological, economic, and political reception;
11. distinguish historical claim, narrated event, narrator comment, character
    speech, parable, metaphor, legal interpretation, scriptural quotation,
    Septuagint wording, textual variant, verbal parallel, shared Synoptic
    tradition, redaction, canonical trajectory, doctrine, typology,
    christological or ecclesial application, liberationist reception, and
    modern analogy;
12. add safeguards concerning antisemitism, supersessionism, deicide and
    collective Jewish blame, portraying Pharisees or Judaism as uniquely
    legalistic, impure, or hard-hearted, anti-Roman or anti-Italian racism,
    anti-Palestinian or anti-Arab readings, nationalism, empire, colonial
    mission, coercive conversion, religious violence, clerical authority,
    secrecy and silencing, family estrangement, child harm, purity and
    disability stigma, demonizing mental illness, dangerous exorcism,
    misogyny, divorce stigma, anti-LGBTQ use, racism or xenophobia around the
    Syrophoenician woman, animal harm in the pigs episode, poverty
    romanticization, prosperity teaching, exploitative use of the widow,
    worker exploitation, slavery analogies, victim blame, cross and trauma
    glorification, apocalypse fear and date-setting, conspiracy theories,
    ecological harm, partisan capture, modern territorial claims, and using
    the longer ending to require snake handling, poison drinking, denial of
    medical care, or testing God;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 27 Zephaniah completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Zephaniah rather than inheriting Minor
   Prophets templates;
3. gather Scripture anchors and independent sources before drafting claims;
4. distinguish the framing voice, Zephaniah son of Cushi and his genealogy,
   YHWH's direct speech and reported action, Judah and Jerusalem, officials,
   royal sons, foreign-clothed people, threshold leapers, merchants, complacent
   residents, remnant, humble and poor, nations, Daughter Zion and Jerusalem,
   dispersed worshipers, priests, prophets, rulers, animals, creation, and
   later interpreters;
5. map Zephaniah 1:1; 1:2–6; 1:7–13; 1:14–18; 2:1–3; 2:4–7; 2:8–11;
   2:12–15; 3:1–7; 3:8–13; and 3:14–20 while qualifying superscription,
   universal undoing, sacrificial summons, search-lamp scene, Day of YHWH,
   nation oracles, city woe, courtroom speech, remnant promise, hymn, divine
   warrior, restoration, speakers, addressees, imperatives, pronouns, and
   proposed seams;
6. qualify Josiah's reign, Zephaniah's unknown biography and genealogy,
   Manasseh's legacy, Assyrian decline, Scythian proposals, Nineveh before
   612 BCE, Judahite politics, cult and reform, Jerusalem neighborhoods,
   trade, dress, rooftops, threshold ritual, silver, houses, vineyards,
   Philistia, Moab, Ammon, Cush, Assyria, Nineveh, deportation, and later
   exilic or Persian-period shaping without forcing one campaign or reform;
7. distinguish superscription, prophetic judgment oracle, creation reversal,
   cultic accusation, sacrifice metaphor, lament, Day-of-YHWH announcement,
   battle cry, imperative summons, nation oracle, taunt, woe, city address,
   disputation, courtroom accusation, remnant promise, salvation oracle,
   hymn, Daughter-Zion address, divine-warrior promise, and restoration;
8. address creation undoing, idolatry and divided allegiance, officials and
   economic elites, complacency, divine search, violence and fraud, wealth,
   Day of YHWH, wrath, darkness, war, human agency, nation judgment, land,
   animals, pride, shame, humility, seeking, remnant, purified speech,
   dispersed peoples, service, refuge, truth, singing, divine presence,
   warrior imagery, quiet love, disability language, exile, return, honor,
   restoration, justice, judgment, mercy, and hope;
9. preserve uncertainty concerning Cushi, Hezekiah, royal ancestry, Josianic
   date, pre- or post-reform setting, Scythians, Baal and astral cult,
   Milcom or Molech, foreign clothing, threshold practice, Maktesh, fish gate,
   second quarter, hills, search lamps, thickening on dregs, sacrifice guests,
   Day-of-YHWH development, nation-oracle sequence, Cherethites, Canaan,
   coastal allotment, Moab-Ammon taunts, Cush, Nineveh's date, city identity
   in 3:1, textual forms, purified lip, rivers of Cush, humble remnant, divine
   silence or love in 3:17, disabled and outcast imagery, unity, redaction,
   liturgy, and Book-of-the-Twelve shaping;
10. address Masoretic Zephaniah, Old Greek Sophonias, Judean Desert and
    versional witnesses, Babylonian Chronicles and Neo-Assyrian evidence,
    Genesis creation and flood, Deuteronomy, Isaiah, Jeremiah, Amos, Micah,
    Nahum, Habakkuk, Joel, Zechariah, Matthew 13, Revelation, early Jewish and
    Christian reception, rabbinic, patristic, liturgical, artistic,
    liberationist, womanist, feminist, postcolonial, disability-aware,
    trauma-aware, ecological, and modern political reception;
11. distinguish historical referent, prophetic accusation, divine speech,
    rhetorical hyperbole, creation reversal, sacrifice metaphor, poetry,
    textual witness, Greek translation, verbal parallel, shared tradition,
    New Testament reception, canonical trajectory, doctrinal reception,
    Christian typology, ecclesial application, liberationist reception, and
    modern analogy;
12. add safeguards concerning antisemitism, supersessionism, anti-African
    racism in readings of Cushi or Cush, anti-Palestinian or anti-Arab
    mappings of Philistia, Moab, and Ammon, modern ethnic proxies, collective
    or hereditary guilt, disability stigma, poverty romanticization, victim
    blame, disaster blame, ecological destruction, animal harm, glorifying
    sacrifice, war, siege, genocide, ethnic cleansing, displacement,
    collective punishment, nationalism, colonialism, empire, revenge, divine
    violence, trauma voyeurism, prosperity teaching, silencing survivors,
    partisan capture, and identifying modern peoples or states as targets;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 33 Luke completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Luke, removing Paul as a narrated key
   person, duplicated resurrection events, generic inherited prose,
   overconfident physician/companion claims, and unsupported completion
   metadata;
3. gather critical Greek-text anchors, Hebrew Bible and Septuagint comparanda,
   P45 and P75, Sinaiticus, Vaticanus, Bezae and other manuscript evidence,
   archaeology, and independent sources before drafting claims;
4. distinguish narrator, implied author and Theophilus; embedded Scripture and
   divine voices; angels; Zechariah, Elizabeth, Mary, Joseph, shepherds,
   Simeon, Anna, John the Baptist, Jesus, Spirit, Satan, disciples and Twelve,
   Peter, James and John, women followers, Mary and Martha, Joanna, Susanna,
   children, poor and wealthy people, petitioners, disabled and sick people,
   people described through spirits, Samaritans, tax collectors and sinners,
   Pharisees, scribes and lawyers, synagogue and temple figures, Herod
   Antipas, Judas, high-priestly leaders, Pilate, soldiers, criminals,
   centurion, Joseph of Arimathea, women at the tomb, Cleopas and the Emmaus
   companion, and later interpreters;
5. map Luke 1:1–4; 1:5–2:52; 3:1–4:13; 4:14–9:50; 9:51–19:27;
   19:28–21:38; 22:1–23:56; and 24:1–53 while indexing the paired infancy
   narratives, songs, genealogy, Nazareth program, Galilean ministry, travel
   narrative, meals, prayers, parables, Jerusalem and temple movement,
   passion, resurrection appearances, ascension, speakers, audiences,
   geographic turns, repetitions, reversals, Synoptic parallels, Lukan
   special material, seams, and Luke-Acts links;
6. qualify the work’s internal anonymity, later Luke attribution, possible
   relation to the Pauline companion traditions, literary unity and
   differences between Luke and Acts, use of Mark and other oral or written
   sources, common dates around 70–100 CE and alternatives, proposed
   locations, Theophilus and broader audiences, Jewish and Gentile hearers,
   temple destruction, Roman imperial rule, economy, households, patronage,
   slavery, illness, disability, crucifixion, burial, resurrection, and
   ascension without inventing one author, profession, city, audience, date,
   or community crisis;
7. distinguish ancient preface, historiographic claim, Gospel and ancient
   biography, annunciation, birth and childhood story, hymn, genealogy,
   proclamation, temptation, synagogue scene, call, healing, exorcism,
   controversy, pronouncement, beatitude and woe, prayer, meal, aphorism,
   legal interpretation, parable, miracle, travel narrative, prophetic sign,
   apocalyptic discourse, anointing, covenant meal, passion, hearing, trial,
   lament, mockery, death, burial, empty-tomb, recognition, appearance,
   commissioning, and ascension narrative;
8. address fulfillment, salvation, Spirit, prayer, joy, reversal, poor and
   wealthy people, women and men, meals, hospitality, mercy, forgiveness,
   repentance, faith, discipleship, journey, Jerusalem, temple, Israel and
   nations, Samaritans and outsiders, kingdom, Son of God, Son of Man,
   Messiah, prophet, Lord, servant, friend, benefactor critique, possessions,
   almsgiving, justice, human agency, cross, resurrection, witness, promise,
   ascension, and Luke-Acts continuity;
9. preserve uncertainty concerning the prologue’s predecessors, sources and
   “order”; infancy chronology, Herod, Quirinius, census, Bethlehem, Nazareth,
   historical plausibility, angelic speech, conception, Magnificat speaker
   and text, songs, purification, Simeon, Anna, child Jesus, genealogy,
   baptismal voice, Nazareth placement, Isaiah 61, Jubilee, Elijah-Elisha
   patterns, beatitudes and woes, poor, enemies, judgment, centurions,
   women’s roles, sinful woman, Samaritans, travel geography, Martha and Mary,
   Lord’s Prayer, kingdom, exorcism, unforgivable sin, sign of Jonah, rich
   fool, narrow door, lament, divorce, prodigal, unjust steward, rich man and
   Lazarus, ten lepers, widow and judge, Pharisee and tax collector,
   Zacchaeus, minas, entry, temple, tribute, resurrection, widow, Luke 21,
   covenant meal, swords, Gethsemane, hearings, Herod and Pilate, Barabbas,
   passion responsibility, “Father forgive,” repentant criminal, darkness,
   curtain, centurion, women, burial, tomb, Emmaus, physicality, commission,
   and ascension;
10. address major textual variants, especially Luke 2:14; 3:22; 4:4; 9:55–56;
    22:19b–20; 22:43–44; 23:17; 23:34a; 24:3, 6, 12, 36, 40, and 51–52;
    Old Latin, Syriac, Coptic and other versions; Marcion’s Gospel and later
    reception; Second Temple texts, Josephus and Greco-Roman comparanda;
    archaeology; Genesis through Malachi; Matthew, Mark, John, Acts, Paul,
    Hebrews, James, 1 Peter, Revelation; and early Jewish and Christian,
    patristic, liturgical, artistic, christological, sacramental, ecclesial,
    liberationist, Black, womanist, feminist, postcolonial,
    Jewish-Christian-dialogical, disability-aware, trauma-aware, ecological,
    economic, and political reception;
11. distinguish historical claim, narrated event, narrator comment, character
    speech, song, parable, metaphor, legal interpretation, quotation,
    Septuagint wording, textual variant, Synoptic parallel, shared tradition,
    redaction, Luke-Acts comparison, canonical trajectory, doctrine,
    typology, ecclesial or liberationist application, reception, and modern
    analogy;
12. add safeguards against antisemitism, supersessionism, deicide and
    collective Jewish blame, portraying Pharisees, lawyers, priests, temple,
    Torah or Judaism as uniquely legalistic, anti-Samaritan stereotyping,
    anti-Roman or anti-Italian racism, anti-Palestinian or anti-Arab mapping,
    nationalism, empire, colonial mission, coercive conversion, religious
    violence, clerical authority, family and child harm, purity and
    disability stigma, demonizing mental illness, dangerous exorcism,
    misogyny, sexual shaming, divorce stigma, anti-LGBTQ coercion, poverty
    romanticization, prosperity teaching, coerced almsgiving, worker and
    slave exploitation, victim blame, trauma and cross glorification,
    apocalypse fear and date-setting, conspiracy theories, ecological harm,
    partisan capture, and modern territorial claims;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 34 John completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against John, removing inherited Synoptic or
   Luke-Acts prose, narrated people who do not occur, duplicated events,
   overconfident apostolic authorship, and unsupported completion metadata;
3. gather critical Greek-text anchors, Hebrew Bible and Septuagint comparanda,
   P52, P66, P75, Sinaiticus, Vaticanus, Bezae and other manuscript evidence,
   archaeology, and independent sources before drafting claims;
4. distinguish narrator and implied author; Logos and divine voices; John the
   Baptist; Jesus' mother and brothers; Andrew, Simon Peter, Philip,
   Nathanael, the Twelve, Judas, Thomas, the beloved disciple, Mary
   Magdalene; Nicodemus, the Samaritan woman, royal official, disabled man,
   people fed, siblings of the man born blind, Mary, Martha, Lazarus, Greeks,
   crowds and petitioners; Pharisees, chief priests, temple figures,
   synagogue communities, Caiaphas, Annas, Pilate, soldiers, Joseph of
   Arimathea, and later interpreters;
5. map John 1:1–18; 1:19–2:12; 2:13–4:54; 5:1–10:42; 11:1–12:50;
   13:1–17:26; 18:1–19:42; 20:1–31; and 21:1–25 while indexing prologue,
   witness, calls, Cana, temple action, signs, festivals, dialogues,
   misunderstanding, irony, discourses, conflict, Lazarus, Book of Signs and
   Book of Glory proposals, footwashing, farewell, prayer, passion, burial,
   empty tomb, appearances, purpose statement, epilogue, speakers,
   audiences, geography, repetitions, seams, and Synoptic relations;
6. qualify internal anonymity, the beloved disciple and witness claims, later
   attribution to John son of Zebedee, elder or school/community proposals,
   sources and signs traditions, possible editions and John 21, common dates
   around 80–100 CE and alternatives, proposed Ephesus and other locations,
   Jewish and Gentile audiences, synagogue-conflict models, post-70 temple
   horizons, Roman rule, and social setting without inventing one author,
   city, community expulsion, date, or publication history;
7. distinguish poetic or hymnic prologue, Gospel and ancient biography,
   witness scene, call, sign, pronouncement, symbolic action, dialogue,
   misunderstanding, irony, controversy, legal and festival discourse,
   healing, feeding, sea scene, shepherd speech, resurrection narrative,
   anointing, footwashing, farewell discourse, prayer, passion, hearing,
   trial, mockery, death, burial, empty-tomb, recognition, appearance,
   commissioning, purpose statement, and epilogue;
8. address Logos, God, creation, life, light and darkness, witness, glory,
   grace and truth, signs, hour, Father and Son, Spirit and Paraclete, birth
   from above, water, bread, shepherd, vine, temple, festivals, Scripture,
   love, friendship, commandment, abiding, unity, world, judgment, faith and
   unbelief, human agency, service, kingship, cross, resurrection, witness,
   mission, and eternal life;
9. preserve uncertainty concerning Logos background; John 1:1 and 1:18;
   Baptist testimony; Lamb of God; Nathanael; Cana and purification; temple
   chronology; Nicodemus and birth from above; John 3:16; Baptist-Jesus
   relation; Samaritan history, husbands, worship, and 4:22; royal official;
   Bethesda and 5:3b–4; Sabbath, Son, judgment, and witnesses; feeding and
   bread of life; eating flesh and drinking blood; walking on sea; festival
   chronology; Jesus' brothers; living water; woman accused of adultery and
   7:53–8:11; light, freedom, Abraham, and “I am”; man born blind; disability
   and sin; synagogue expulsion; shepherd speech and 10:30; Lazarus;
   Caiaphas; anointing; entry; Greeks; grain of wheat; drawing all; unbelief;
   footwashing; Judas; new commandment; Peter; many rooms; 14:6; Paraclete;
   Father greater; vine; world hatred; childbirth imagery; Spirit and truth;
   high-priestly prayer; unity; arrest and hearings; passion responsibility;
   kingship; crucifixion chronology; beloved disciple and Jesus' mother;
   thirst, completion, blood and water, witness, burial, tomb, Mary
   Magdalene, Thomas, forgiveness, purpose statement, John 21, fish, Peter,
   beloved disciple, and ending;
10. address major textual variants, especially John 1:18; 3:13; 5:3b–4;
    6:69; 7:53–8:11; 8:59; 9:35; 10:29; 14:14; 16:16; 19:29; and 20:31;
    P52, P66, P75, Sinaiticus, Vaticanus, Bezae, Old Latin, Syriac, Coptic,
    and other versions; Second Temple texts, Philo, Josephus, Greco-Roman
    comparanda, archaeology, Genesis through Malachi, Synoptics, Acts, Paul,
    Hebrews, Johannine letters, Revelation, and early Jewish and Christian,
    patristic, liturgical, artistic, christological, sacramental, ecclesial,
    liberationist, Black, womanist, feminist, postcolonial,
    Jewish-Christian-dialogical, disability-aware, trauma-aware, ecological,
    economic, and political reception;
11. distinguish historical claim, narrated event, narrator comment, character
    speech, metaphor, sign, misunderstanding, irony, legal interpretation,
    scriptural quotation, Septuagint wording, textual variant, Synoptic
    parallel, shared tradition, redaction, canonical trajectory, doctrine,
    typology, ecclesial or liberationist application, reception, and modern
    analogy;
12. add safeguards against antisemitism, supersessionism, deicide and
    collective Jewish blame, translating or preaching *hoi Ioudaioi* as a
    racial monolith, portraying Pharisees, festivals, temple, Torah or Judaism
    as uniquely blind or hostile, anti-Samaritan stereotyping,
    anti-Palestinian or anti-Arab mapping, anti-Roman or anti-Italian racism,
    nationalism, empire, colonial mission, coercive conversion, religious
    violence, using John 14:6 for domination or exclusionary harm, clerical
    authority, secrecy, family and child harm, misogyny, sexual shaming,
    anti-LGBTQ coercion, disability and mental-health stigma, dangerous
    exorcism, medical neglect, sacramental exclusion, poverty
    romanticization, worker and slave exploitation, victim blame, coerced
    forgiveness, cross and trauma glorification, conspiracy theories,
    anti-intellectualism, ecological harm, partisan capture, and modern
    territorial claims;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty and dispute labels only where evidence justifies
    them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.

Wave 34 John completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-john-review.md`](ckl-phase-5-john-review.md).

Wave 35 Acts completed the following controlled correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Acts, removing inherited Gospel
   summaries, duplicated events, generic structure, overconfident Lukan
   authorship, and unsupported completion metadata;
3. gather critical Greek-text anchors, Hebrew Bible and Septuagint
   comparanda, P45, P53, P74, Sinaiticus, Vaticanus, Bezae, Old Latin, Syriac,
   Coptic and other manuscript evidence, inscriptions, archaeology, Roman
   administrative evidence, Josephus, and independent sources before drafting
   claims;
4. distinguish narrator, implied author and Theophilus; risen Jesus, Spirit,
   angels and Scripture; the Eleven, Matthias, women and Jesus' family; Peter,
   John, Stephen, Philip and the Seven; named women, petitioners, sick and
   disabled people, people described through spirits, enslaved people and
   workers; Jewish crowds, priests, Sadducees, Pharisees, synagogue groups,
   councils and diaspora communities; Samaritans and Ethiopian official;
   Saul or Paul, Barnabas, Ananias, Sapphira, James, Cornelius, Herods, Lydia,
   Priscilla, Aquila, Apollos, Silas, Timothy, companions and “we” narrators;
   Roman officials, magistrates, jailer, Gallio, Felix, Festus, Agrippa,
   Bernice, soldiers, sailors, islanders and later interpreters;
5. map Acts 1:1-2:47; 3:1-5:42; 6:1-8:40; 9:1-12:25; 13:1-15:35;
   15:36-19:20; 19:21-21:16; 21:17-26:32; and 27:1-28:31 while indexing
   prologue, ascension, restoration question, Pentecost, speeches, summary
   passages, signs, property sharing, conflict, trials, martyrdom, Samaria,
   road encounters, household scenes, visions, council, travel, “we”
   passages, city episodes, riot, arrest, defenses, voyage, shipwreck, Malta,
   Rome, and the open ending;
6. qualify Acts' internal anonymity, later Lukan attribution, relationship to
   Luke, common-authorship and coordinated-publication arguments, literary
   and theological differences, “we” passages, sources and speeches, common
   80-100 CE dates and earlier or second-century alternatives, provenance,
   Theophilus and broader audiences, historical reliability, apologetic
   purpose, Roman citizenship, and the abrupt ending without inventing one
   author, companion, itinerary diary, city, audience, trial outcome, or
   publication history;
7. distinguish ancient preface and sequel, historiographic narrative, ancient
   biography, travel and voyage writing, summary, list, call, vision, sign,
   healing, exorcism, judicial hearing, defense speech, missionary sermon,
   deliberative speech, council account, household conversion, martyrdom,
   prison escape, riot, farewell, prophecy, miracle contest, sea narrative,
   hospitality scene, and open ending;
8. address Spirit, witness, kingdom, Israel's restoration, Scripture,
   Pentecost, languages, prophecy, prayer, table fellowship, possessions,
   sharing, deception, judgment, signs, healing, inclusion, baptism,
   repentance, forgiveness, name, persecution, martyrdom, resurrection,
   law, temple, circumcision, nations, food, councils, mission, divine
   guidance, women and households, work, citizenship, empire, suffering,
   providence, hospitality, and Rome;
9. preserve uncertainty concerning the ascension chronology and cloud;
   kingdom restoration; Matthias; Pentecost languages and Joel; communal
   property; Ananias and Sapphira; Gamaliel; the Seven; Stephen's speech and
   responsibility; Philip, Samaritans and Ethiopian official; Paul's call or
   conversion accounts; Damascus, Arabia and Galatians; Peter's vision and
   Cornelius; Herod's death; Antioch mission; Bar-Jesus; speeches and sources;
   Jerusalem council and Galatians 2; decree and variants; women leaders;
   household baptisms; spirits and exorcism; Areopagus; Gallio chronology;
   Ephesus and Artemis; collection journey; Agabus; James and Torah; Roman
   citizenship; trial speeches; resurrection hope; Agrippa and Bernice;
   voyage and shipwreck; snakebite; Malta; Rome; Paul’s fate; and Acts'
   ending;
10. distinguish historical claim, narrated event, narrator comment, character
    speech, summary ideal, miracle, vision, dream, prophecy, rhetoric,
    scriptural quotation, Septuagint wording, textual variant, Luke-Acts
    parallel, Pauline-letter comparison, shared tradition, redaction,
    canonical trajectory, doctrine, ecclesial application, reception, and
    modern analogy;
11. add safeguards against antisemitism, supersessionism, deicide and
    collective Jewish blame, portraying Jewish groups, Torah, circumcision or
    temple as uniquely hostile, anti-Samaritan and anti-African stereotypes,
    racializing the Ethiopian official, anti-Roman or anti-Italian racism,
    colonial mission, forced conversion, religious violence, Christian
    nationalism, territorial claims, authoritarian church unity, clerical
    power, financial coercion, Ananias-Sapphira threats, family and child
    harm, misogyny, anti-LGBTQ coercion, disability and mental-health stigma,
    dangerous exorcism or snake handling, medical neglect, poverty
    romanticization, prosperity extraction, slavery and worker exploitation,
    victim blame, martyrdom and trauma glorification, prison abuse,
    anti-intellectualism, conspiracy theories, partisan capture, and
    ecological harm;
12. populate only applicable hermeneutical and retrieval sections, use current
    certainty and dispute labels only where evidence justifies them, keep
    statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 35 Acts completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-acts-review.md`](ckl-phase-5-acts-review.md).

Wave 36 completed this controlled Romans correction scope:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Romans, removing inherited epistle
   templates, generic events, duplicated themes, overconfident authorship or
   audience claims, and unsupported completion metadata;
3. gather critical Greek-text anchors, Hebrew Bible and Septuagint
   comparanda, P10, P26, P27, P31, P40, P46, P61, Sinaiticus, Vaticanus,
   Alexandrinus, Claromontanus, versions, inscriptions, archaeology,
   Greco-Roman comparanda, early reception, and independent sources before
   drafting claims;
4. distinguish epistolary sender Paul, Tertius as scribe, Phoebe as carrier
   or patron, named coworkers and households in Romans 16, implied Roman
   Christ-followers, Jewish and gentile interlocutors, Adam, Abraham, Sarah,
   Isaac, Jacob, Esau, Moses, Pharaoh, Elijah, Israel, governing authorities,
   weak and strong participants, enslaved people and workers, women leaders,
   petitioners, imperial actors, later interpreters, and rhetorical or
   scriptural voices without inventing one social faction;
5. map Romans 1:1-17; 1:18-3:20; 3:21-4:25; 5:1-8:39; 9:1-11:36;
   12:1-15:13; 15:14-33; and 16:1-27 while indexing prescript,
   thanksgiving, thesis, diatribe, scriptural catena, Abraham argument,
   Adam-Christ comparison, baptism, slavery metaphors, Spirit and lament,
   Israel discourse, paraenesis, gifts, enemies, governing authorities,
   Torah and love, weak and strong, mission plans, collection, greetings,
   warnings, doxology, speakers, interlocutors, questions, objections,
   imperatives, quotations, transitions, and textual seams;
6. qualify Pauline authorship and Tertius's scribal role, date commonly near
   56-58 CE and alternatives, Corinth or Cenchreae provenance, Phoebe's role,
   Rome's assemblies, Claudian expulsion and return, Jewish-gentile
   relations, imperial setting, purpose, occasion, travel plans, collection,
   Spain, rhetoric, sources, integrity, Romans 16 placement, and the
   doxology's locations without inventing one church structure, crisis,
   addressee profile, secretary process, or publication history;
7. distinguish letter prescript, thanksgiving, thesis, apostolic
   self-presentation, diatribe, interlocutor, accusation, scriptural
   quotation, catena, analogy, typology, Adam-Christ comparison, Abraham
   exemplum, rhetorical question, lament, doxology, paraenesis, household
   greeting, travel report, recommendation, warning, and benediction;
8. address gospel, righteousness and justice of God, faith or faithfulness,
   wrath, idolatry, judgment, Torah, circumcision, sin, grace, justification,
   boasting, Abraham, peace, reconciliation, Adam, baptism, union with
   Christ, slavery and freedom, flesh and Spirit, adoption, suffering, hope,
   creation, prayer, election, Israel and nations, mercy, remnant, olive tree,
   worship, gifts, bodies, enemies, peace, governing authority, love,
   conscience, food, days, weak and strong, mission, collection, women,
   households, and unity;
9. preserve uncertainty concerning `pistis Christou`; divine righteousness;
   Romans 1:18-32, desire and modern sexuality; natural theology; judgment
   and conscience; works of Torah; Romans 3:25; justification; Abraham;
   Romans 5:1 and 5:12; original sin; baptism; Romans 7's speaker and time;
   flesh; law; Spirit; groaning; predestination; Romans 9-11, Israel,
   election, hardening, vessels, remnant, `telos`, olive tree, all Israel,
   irrevocable gifts, mercy; living sacrifice; gifts; enemies; Romans 13 and
   the state; debt and love; day and armor; food and days; weak and strong;
   Phoebe, Junia, Prisca, house assemblies; warnings; Romans 16 manuscripts;
   and doxology placement;
10. distinguish historical claim, epistolary voice, rhetorical interlocutor,
    scriptural voice, metaphor, analogy, typology, quotation, Septuagint
    wording, textual variant, Pauline-letter comparison, shared tradition,
    canonical trajectory, doctrine, confessional system, reception,
    liberationist application, and modern analogy;
11. add safeguards against antisemitism, supersessionism, collective Jewish
    guilt, portraying Torah or Judaism as uniquely legalistic, anti-Roman or
    anti-Italian racism, anti-LGBTQ coercion and violence, misogyny, erasing
    Phoebe or Junia, slavery apologetics, worker exploitation, disability and
    mental-health stigma, body shame, coercive baptism, original-sin blame,
    predestination fatalism, despair and suicide harm, silencing lament,
    abuse of governing-authority texts, authoritarianism, nationalism,
    colonial mission, forced conversion, religious violence, poverty
    romanticization, prosperity extraction, victim blame, trauma
    glorification, ecological neglect, conspiracy theories, partisan
    capture, and modern territorial claims;
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 36 Romans completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-romans-review.md`](ckl-phase-5-romans-review.md).

Active next wave: continue Phase 5 with this controlled 1 Corinthians
correction wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against 1 Corinthians, removing inherited
   Pauline-letter templates, generic events, duplicated themes, unsupported
   authorship or audience claims, false completion metadata, and the current
   literary-context and original-audience migration warnings;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P15, P46, P123, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi,
   Claromontanus, versions, inscriptions, Corinthian archaeology,
   association, household, banquet, patronage, slavery, gender, body,
   rhetoric, philosophy, cult, law, economics, and early-reception evidence
   before drafting claims;
4. distinguish Paul and Sosthenes as senders; Chloe's people; the household
   of Stephanas; Crispus, Gaius, Fortunatus and Achaicus; Apollos, Cephas,
   named scriptural figures, apostles and coworkers; the Corinthian
   assemblies, factions and rhetorical interlocutors; women and men who pray
   and prophesy; married, unmarried and widowed people; enslaved and free
   people; patrons, workers, litigants, meal participants, poor and hungry
   members, people with disabilities or illness, and later interpreters
   without inventing one opponent or demographic;
5. map 1 Corinthians 1:1-4:21; 5:1-6:20; 7:1-40; 8:1-11:1; 11:2-14:40;
   15:1-58; and 16:1-24 while indexing prescript, thanksgiving, reports,
   slogans, letter questions, faction rhetoric, cross and wisdom,
   apostolic example, discipline, lawsuits, bodies, marriage and celibacy,
   idol food, rights and renunciation, Israel examples, gendered head
   language, communal meals, Lord's supper, gifts, love, prophecy, tongues,
   resurrection argument, collection, travel, coworkers, greetings, warning,
   and benediction;
6. qualify Pauline authorship and Sosthenes's role, date commonly near 53-55
   CE and alternatives, Ephesian provenance, chronology relative to earlier
   correspondence and the painful visit, Corinth's Roman-colonial and Greek
   setting, audience diversity, Chloe's report, the Corinthians' letter,
   factions, rhetorical opponents, integrity, purpose, and relation to
   2 Corinthians without inventing a complete correspondence, one church
   building, one social class, or a single reconstructed crisis;
7. distinguish Pauline letter, report response, question-and-answer,
   diatribe, rhetorical question, slogan and possible quotation, scriptural
   quotation and exemplum, irony, parody, apostolic self-presentation,
   vice list, case judgment, analogy, household instruction, deliberative
   counsel, apocalyptic warning, thanksgiving tradition, hymn or encomium,
   gift list, resurrection proof, collection instruction, travel report,
   commendation, greeting, anathema, and benediction;
8. address cross, wisdom, power, boasting, division, apostleship, maturity,
   temple, discipline, sex, bodies, lawsuits, slavery and freedom, marriage,
   singleness, divorce, celibacy, calling and vocation, idol food,
   conscience, apostolic rights, Israel, temptation, idolatry, table
   fellowship, head language, veiling and hair, Lord's supper, class
   inequality, body, gifts, love, tongues, prophecy, order, resurrection,
   Adam and Messiah, victory over death, collection, work, hospitality, and
   grace;
9. preserve uncertainty concerning Corinthian factions and slogans; wisdom
   and mystery; God's foolishness; the spiritual person; temple imagery;
   the incest case and Satan; judging insiders; lawsuits; sex-worker
   language and bodies; `malakoi` and `arsenokoitai`; marriage, divorce,
   mixed marriages, slavery and vocation; virgins or betrothed people;
   idol food, demons, conscience and weaker members; women's head coverings,
   `kephale`, angels and nature; supper tradition; baptism for the dead;
   spiritual gifts, tongues and prophecy; whether 13 is an interpolation;
   women speaking in 14:34-35 and textual displacement; resurrection-body
   language; Adam; the collection; and the closing anathema;
10. distinguish historical claim, epistolary report, rhetorical
    interlocutor, Corinthian slogan, scriptural voice, metaphor, analogy,
    exemplum, tradition, possible interpolation, textual variant,
    Pauline-letter comparison, canonical trajectory, doctrine, confessional
    system, reception, pastoral application, and modern analogy;
11. add safeguards against sectarianism, celebrity leadership, financial
    extraction, authoritarian discipline, public shaming, sexual abuse,
    incest mishandling, anti-LGBTQ coercion, misogyny, gender essentialism,
    forced marriage or celibacy, divorce coercion, slavery apologetics,
    worker exploitation, victim blame, body shame, disability and
    mental-health stigma, medical neglect, food-allergy and addiction harm,
    class humiliation at meals, eucharistic exclusion, dangerous exorcism,
    coercive tongues or prophecy, spiritual-gift ranking, silencing women,
    antisemitism, supersessionism, colonial mission, religious violence,
    nationalism, conspiracy theories, partisan capture, prosperity teaching,
    poverty romanticization, trauma glorification, and ecological neglect;
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 37 1 Corinthians completed the controlled scope above. The record remains
an unapproved draft and its reviewer checklist is in
[`ckl-phase-5-1-corinthians-review.md`](ckl-phase-5-1-corinthians-review.md).

The corrected record contains forty-four sourced claims, eighty-eight
current-taxonomy interpretive notes, thirty-five sources, thirty-four
URL-bearing external sources, three high-precision top-level aliases plus
retrieval metadata, fifteen normalized Scripture anchors, ten Hebrew entries,
twenty Greek entries, and nine verified graph relationships. Its focused
eight-method factual and SQLite suite passes, as do sixty-six book-specific
retrieval questions and the completed Haggai neighborhood that initially
collided with broad aliases. The full 484-test CKL suite, single-file and
repository validators, graph audit, generated reports, and final SQLite
artifact are recorded in the reviewer report.

Active next wave: continue Phase 5 with this controlled 2 Corinthians
correction wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against 2 Corinthians, removing inherited
   Pauline-letter templates, generic events, duplicated themes, unsupported
   authorship or audience claims, false completion metadata, and current
   literary-context or original-audience migration warnings;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P46, P99, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus,
   versions, inscriptions, Corinthian and Macedonian archaeology, Roman
   travel and law, patronage, friendship, benefaction, collection,
   ambassadorial, slavery, gender, body, rhetoric, philosophy, economics,
   suffering, disability, and early-reception evidence before drafting
   claims;
4. distinguish Paul and Timothy as senders; the Corinthian assemblies and
   saints in Achaia; Titus and the unnamed brother or brothers; the offender,
   injured party, reconciled majority, rival apostles and rhetorical
   interlocutors; Moses and scriptural voices; Macedonian and Jerusalem
   saints; coworkers, patrons, laborers, enslaved and free people, women and
   men, afflicted or disabled people, collection participants, messengers,
   opponents, and later interpreters without inventing one opponent group or
   demographic;
5. map 2 Corinthians 1:1-2:13; 2:14-7:4; 7:5-16; 8:1-9:15; 10:1-13:10;
   and 13:11-14 while indexing prescript, blessing, affliction and comfort,
   travel explanation, painful visit and letter, forgiveness, triumph
   imagery, letter and Spirit, Moses' veil, earthen vessels, suffering,
   resurrection, reconciliation, ambassador language, holiness appeal,
   Titus's report, collection appeal, boasting, irony, fool's speech,
   visions, thorn, signs, weakness, planned visit, warning, restoration,
   greeting, and benediction;
6. qualify Pauline authorship and Timothy's role, date commonly in the
   mid-50s CE and alternatives, Macedonian provenance, chronology relative
   to 1 Corinthians, the painful visit and severe letter, Titus's missions,
   offender and injured party, reconciliation, collection history, rival
   apostles, integrity and partition theories, purpose, audience, and
   relation to Acts without inventing a complete correspondence, one church
   building, one opponent, or a settled itinerary;
7. distinguish Pauline letter, blessing, thanksgiving-like report, travel
   apology, autobiographical narrative, scriptural exposition, contrast,
   metaphor, ambassadorial appeal, catalog of hardships, commendation,
   collection exhortation, exemplum, irony, invective, parody, boasting,
   fool's speech, vision report, third-person self-reference, warning,
   examination, restoration appeal, greeting, and triadic benediction;
8. address affliction, comfort, conscience, integrity, travel, forgiveness,
   reconciliation, triumph, aroma, sufficiency, letter and Spirit, covenant,
   glory, veil, image, transformation, treasure and earthen vessels,
   suffering, death and life, resurrection, new creation, judgment seat,
   ambassador language, holiness, temple, grief, repentance, collection,
   grace, equality, generosity, accountability, boasting, authority,
   weakness, visions, thorn, signs, discipline, self-examination, peace,
   fellowship, and blessing;
9. preserve uncertainty concerning correspondence sequence and letter
   partitions; Paul's changed travel plan; offender and injured party;
   forgiveness and Satan; triumph-procession imagery; aroma; sufficiency;
   old and new covenant rhetoric; Moses' veil and Jewish interpretation;
   transformation; hardening; earthen vessels; outer and inner person;
   heavenly dwelling; judgment seat; knowing Messiah according to flesh;
   new creation; reconciliation and ambassador language; temple and
   unbelievers; godly grief; Titus's report; Macedonian poverty; collection
   accountability and equality; sowing and reaping; chapters 10-13's
   opponents; letters of commendation; super-apostles; fool's speech;
   ethnicity claims; visions and third heaven; thorn in the flesh; signs of
   an apostle; weakness and power; planned discipline; self-examination; and
   the closing benediction;
10. distinguish historical claim, epistolary voice, travel explanation,
    autobiographical rhetoric, opponent characterization, scriptural voice,
    metaphor, analogy, exemplum, collection appeal, vision report, irony,
    parody, invective, textual variant, possible letter seam, Pauline-letter
    comparison, canonical trajectory, doctrine, confessional system,
    reception, pastoral application, and modern analogy;
11. add safeguards against antisemitism, supersessionism, using veil language
    to demean Jews or Judaism, anti-Roman or anti-Greek racism, sectarianism,
    celebrity leadership, authoritarian discipline, coerced forgiveness,
    reconciliation without safety or repair, spiritual bypassing of trauma,
    glorifying suffering, disability and mental-health stigma, medical
    neglect, dangerous exorcism, sexual abuse, misogyny, anti-LGBTQ coercion,
    slavery apologetics, worker exploitation, financial extraction,
    collection coercion, prosperity teaching, poverty romanticization,
    public shaming, victim blame, colonial mission, forced conversion,
    religious violence, nationalism, conspiracy theories, partisan capture,
    and ecological neglect;
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 38 2 Corinthians completed the controlled scope above. The record remains
an unapproved draft and its reviewer checklist is in
[`ckl-phase-5-2-corinthians-review.md`](ckl-phase-5-2-corinthians-review.md).

The corrected record contains forty sourced claims, seventy-five
current-taxonomy interpretive notes, thirty sources, twenty-nine URL-bearing
external sources, three high-precision top-level aliases plus retrieval
metadata, fifteen normalized Scripture anchors, ten Hebrew entries, twenty
Greek entries, and eight verified graph relationships. Its focused
eight-method factual and SQLite suite and forty-seven book-scoped retrieval
questions pass. The full 492-test CKL suite, single-file and repository
validators, graph audit, generated reports, and final SQLite artifact are
recorded in the reviewer report.

Active next wave: continue Phase 5 with this controlled Galatians correction
wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Galatians, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, geography, or opponent claims;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P46, P51, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus,
   versions, Galatian and Anatolian inscriptions and archaeology, Roman
   provincial geography, ethnicity, circumcision, slavery, household,
   patronage, rhetoric, law, philosophy, and early-reception evidence before
   drafting claims;
4. distinguish Paul and possible scribal collaborators; Barnabas, Titus,
   Cephas, James, John, the Jerusalem poor, Abraham, Sarah, Hagar, Isaac,
   opponents or agitators, teachers, enslaved and free people, women and men,
   Jews, gentiles, Galatian assemblies, and later interpreters without
   inventing one opponent group or demographic;
5. map Galatians 1:1-2:21; 3:1-4:31; 5:1-6:10; and 6:11-18 while indexing
   prescript, curse, autobiography, Jerusalem meetings, Antioch confrontation,
   justification, faith or faithfulness, Spirit, Abraham, Torah, curse,
   pedagogue, baptism, adoption, elemental powers, allegory, freedom,
   circumcision, flesh, Spirit, communal repair, burden-bearing, sowing,
   new creation, autograph, marks, and grace;
6. qualify Pauline authorship, date and north-versus-south Galatia theories,
   provenance, audience ethnicity, chronology relative to Acts and other
   letters, Jerusalem visits, Antioch, opponents, purpose, integrity, and the
   relation of autobiography to persuasion without pretending the itinerary
   or crisis is settled;
7. distinguish Pauline letter, rebuke, curse, autobiography, forensic and
   deliberative rhetoric, scriptural quotation, prosopopoeia, exemplum,
   allegory, diatribe, vice and virtue lists, household language, irony,
   exhortation, warning, autograph, benediction, and later doctrinal use;
8. address gospel, revelation, apostleship, justification, `pistis Christou`,
   works of Torah, Abraham, promise, curse, law, pedagogue, Messiah, Spirit,
   baptism, adoption, heirs, elemental powers, slavery, freedom,
   circumcision, flesh, love, fruit, restoration, burdens, sowing, cross, new
   creation, Israel of God, marks, and grace;
9. preserve uncertainty concerning the addressees and opponents; Jerusalem
   chronology; Titus and circumcision; the Antioch confrontation; faith in
   or faithfulness of Messiah; works of Torah; curse and law; seed; why Torah
   was added; angels and mediator; pedagogue; baptismal unity; elemental
   powers; illness and eyes; Hagar and Sarah; freedom, circumcision, flesh and
   Spirit; the Israel of God; and Paul's marks;
10. distinguish historical claim, autobiographical rhetoric, opponent
    characterization, scriptural voice, metaphor, allegory, lexical claim,
    textual variant, Pauline-letter comparison, canonical trajectory,
    doctrine, confessional system, reception, pastoral application, and
    modern analogy;
11. add safeguards against antisemitism, supersessionism, anti-Jewish Torah
    caricature, ethnic contempt, coercive circumcision or anti-circumcision,
    anti-LGBTQ coercion, misogyny, gender erasure, slavery apologetics,
    authoritarian leadership, public shaming, spiritual abuse, medical
    neglect, disability stigma, worker exploitation, prosperity extraction,
    nationalism, conspiracy theories, partisan capture, colonial mission,
    religious violence, trauma glorification, and ecological neglect; and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 39 Galatians completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-galatians-review.md`](ckl-phase-5-galatians-review.md).

The corrected record contains thirty-six sourced claims, sixty
current-taxonomy interpretive notes, thirty sources, twenty-nine URL-bearing
external sources, three high-precision top-level aliases plus retrieval
metadata, sixteen normalized Scripture anchors, ten Hebrew entries, twenty
Greek entries, and eight verified graph relationships. Its focused
eight-method factual and SQLite suite and forty-one book-scoped retrieval
questions pass. The full-suite rerun, single-file and repository validators,
graph audit, generated reports, and final SQLite artifact are recorded in the
reviewer report.

Active next wave: continue Phase 5 with this controlled Ephesians correction
wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Ephesians, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, geography, or purpose claims;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P46, P49, P92, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi,
   Claromontanus, versions, Ephesian and Anatolian inscriptions and
   archaeology, Roman provincial geography, Artemis evidence, households,
   patronage, slavery, associations, rhetoric, pseudepigraphy, and
   early-reception evidence before drafting claims;
4. distinguish the named Paul, possible secretary or Pauline-school author,
   Tychicus, gentile addressees, Jews and gentiles, apostles and prophets,
   evangelists, pastors and teachers, wives and husbands, children and
   fathers or parents, enslaved people and masters, cosmic rulers and powers,
   the scriptural voice, the Messiah, the Spirit, and later interpreters
   without inventing a single house church or demographic;
5. map Ephesians 1:1-2:10; 2:11-3:21; 4:1-5:20; 5:21-6:9; and 6:10-24 while
   indexing prescript, blessing, election, adoption, inheritance, fullness,
   resurrection and enthronement, grace, good works, hostility and peace,
   one new humanity, temple, mystery, prayer, unity, gifts, body growth, old
   and new humanity, truth, anger, labor, imitation, light, wisdom, Spirit,
   worship, mutual submission, household code, armor, Tychicus, and
   benediction;
6. qualify disputed Pauline authorship, secretary and Pauline-school
   proposals, date, provenance, circular-letter or Laodicean hypotheses, the
   textual status of “in Ephesus,” audience, relation to Colossians and other
   Pauline letters, dependence, purpose, and integrity without treating a
   canonical first-person voice as a solved modern authorship claim;
7. distinguish Pauline-form letter, blessing, prayer report, doxology,
   scriptural quotation and allusion, cosmic and spatial metaphor, body and
   temple imagery, mystery disclosure, paraenesis, vice and virtue
   instruction, household code, armor metaphor, travel notice, greeting,
   benediction, and later doctrinal use;
8. address election, predestination, adoption, redemption, forgiveness,
   inheritance, sealing, wisdom, power, grace, faith, works, flesh,
   reconciliation, hostility, Torah, one new humanity, citizenship,
   household, temple, mystery, church, rulers and powers, vocation, unity,
   gifts, maturity, truth, anger, labor, speech, sexuality, light, wisdom,
   Spirit, worship, submission, marriage, parenting, slavery, armor, prayer,
   peace, love, and grace;
9. preserve uncertainty concerning authorship and pseudepigraphy; “in
   Ephesus”; addressees and circularity; date and provenance; relation to
   Colossians; election and predestination; “faith” in Ephesians 2:8; works;
   flesh; dividing wall; abolition of commandments; one new humanity;
   apostles and prophets; descent into lower regions; gift offices; head and
   body; sexual and gender language; mutual submission and household order;
   the quotation in Ephesians 5:14; armor, rulers, powers, and spiritual
   warfare; and Tychicus's role;
10. distinguish historical claim, epistolary voice, pseudepigraphal
    convention proposal, scriptural voice, metaphor, lexical claim, textual
    variant, Pauline-letter comparison, canonical trajectory, doctrine,
    confessional system, reception, pastoral application, and modern
    analogy;
11. add safeguards against antisemitism, supersessionism, anti-Jewish Torah
    caricature, ethnic contempt, predestination fatalism, spiritual abuse,
    authoritarian church office, clericalism, misogyny, patriarchal marriage,
    marital rape, child abuse, anti-LGBTQ coercion, sexual abuse, slavery
    apologetics, worker exploitation, ableism, mental-health stigma, medical
    neglect, dangerous exorcism, conspiracy theories, militarism, religious
    violence, nationalism, partisan capture, colonial mission, forced
    conversion, financial extraction, prosperity teaching, public shaming,
    trauma glorification, and ecological neglect; and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 40 Ephesians completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-ephesians-review.md`](ckl-phase-5-ephesians-review.md).

The corrected record contains twenty-eight sourced claims, forty-six
current-taxonomy interpretive notes, twenty-four URL-bearing sources, three
high-precision top-level aliases plus retrieval metadata, sixteen normalized
Scripture anchors, ten Hebrew entries, twenty Greek entries, and eight
verified graph relationships. Its focused eight-method factual and SQLite
suite and thirty-two book-scoped retrieval questions pass. The full CKL suite,
single-file and repository validators, graph audit, generated reports, and
final SQLite artifact are recorded in the reviewer report and verification
section.

Active next wave: continue Phase 5 with this controlled Philippians correction
wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Philippians, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, imprisonment, geography, or opponent
   claims;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P16, P46, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus,
   versions, Philippian and Macedonian inscriptions and archaeology, Roman
   colony and citizenship evidence, households, patronage, slavery, gender,
   friendship, gift exchange, rhetoric, and early reception before drafting
   claims;
4. distinguish Paul and Timothy as named senders; Paul as dominant
   first-person voice; Epaphroditus, Euodia, Syntyche, Clement, the true
   companion, overseers and deacons, Caesar's household, rival preachers,
   opponents, coworkers, women and men, enslaved and free people, citizens,
   patrons, petitioners, disabled or ill people, and later interpreters
   without inventing one opponent or social profile;
5. map Philippians 1:1-30; 2:1-30; 3:1-4:1; and 4:2-23 while indexing
   prescript, thanksgiving, prayer, imprisonment, gospel progress, rival
   preaching, life and death, citizenship, unity appeal, Messiah poem,
   obedience, Timothy, Epaphroditus, warning, autobiography, loss and gain,
   resurrection pursuit, heavenly citizenship, named women's conflict,
   rejoicing, anxiety and prayer, contentment, gift partnership, greetings,
   Caesar's household, and grace;
6. qualify strong Pauline-authorship consensus, Timothy's role, commonly
   proposed dates and Rome, Ephesus, or Caesarea imprisonment theories,
   Philippi's Roman-colonial setting, audience composition, opponents,
   letter-unity and partition theories, chronology, purpose, gift exchange,
   and relation to Acts without inventing a complete itinerary or crisis;
7. distinguish Pauline letter, thanksgiving, prayer, prison report,
   deliberative rhetoric, exemplum, possible hymn or poetic passage,
   autobiography, warning, paraenesis, friendship and gift language,
   recommendation, travel report, greeting, and benediction;
8. address gospel partnership, imprisonment, joy, suffering, life and death,
   citizenship, unity, humility, Messiah's self-emptying, obedience,
   exaltation, work, illness, opponents, confidence in flesh, knowing
   Messiah, resurrection, perfection, heavenly citizenship, reconciliation,
   prayer, anxiety, peace, thought, contentment, generosity, gift and account,
   Caesar's household, and grace;
9. preserve uncertainty concerning prison and date; rival preachers;
   opponents; suffering; `politeuesthe`; authorship, background, structure,
   and theology of Philippians 2:6-11; `harpagmos`; emptying; obedience and
   salvation; Epaphroditus's illness; dogs and mutilation; righteousness;
   resurrection; perfection; enemies of the cross; heavenly citizenship;
   Euodia, Syntyche, and the true companion; anxiety; “all things”;
   contentment; gift reciprocity; and Caesar's household;
10. distinguish historical claim, epistolary voice, rhetorical opponent,
    metaphor, lexical claim, scriptural allusion, traditional material,
    possible letter seam, Pauline-letter comparison, canonical trajectory,
    doctrine, confessional system, reception, pastoral application, and
    modern analogy;
11. add safeguards against antisemitism, supersessionism, anti-Jewish
    circumcision rhetoric, misogyny and blaming Euodia or Syntyche, silencing
    conflict, authoritarian leadership, slavery apologetics, worker
    exploitation, disability and illness stigma, medical neglect, anxiety
    shaming, suicide harm, prosperity teaching, financial extraction,
    poverty romanticization, trauma and suffering glorification, coercive
    unity, nationalism, militarism, colonial mission, forced conversion,
    religious violence, conspiracy theories, partisan capture, and
    ecological neglect; and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 41 Philippians completed the controlled scope above. The record remains
an unapproved draft and its reviewer checklist is in
[`ckl-phase-5-philippians-review.md`](ckl-phase-5-philippians-review.md).

The corrected record contains twenty-eight sourced claims, forty-nine
current-taxonomy interpretive notes, twenty-five sources, twenty-four
URL-bearing external sources, three high-precision top-level aliases plus
retrieval metadata, seventeen normalized Scripture anchors, ten Hebrew
entries, twenty Greek entries, and eight verified graph relationships. Its
focused eight-method factual and SQLite suite and thirty-two book-scoped
retrieval questions pass. The full 516-test CKL suite, single-file and
repository validators, graph audit, generated reports, and final SQLite
artifact are recorded in the reviewer report.

Active next wave: continue Phase 5 with this controlled Colossians correction
wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against Colossians, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, imprisonment, geography, or opponent
   claims;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P46, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus,
   versions, Lycus Valley and Colossian inscriptions and archaeology, Roman
   provincial geography, households, patronage, slavery, philosophy, cult,
   associations, rhetoric, and early-reception evidence before drafting
   claims;
4. distinguish the named Paul and Timothy, possible secretary or
   Pauline-school author, Epaphras, Tychicus, Onesimus, Aristarchus, Mark,
   Jesus Justus, Luke, Demas, Nympha, Archippus, household members, enslaved
   and free people, women and men, Jews and gentiles, opponents or teachers,
   angels and powers, and later interpreters without inventing one opponent
   group or demographic;
5. map Colossians 1:1-23; 1:24-2:23; 3:1-4:6; and 4:7-18 while indexing
   prescript, thanksgiving, prayer, image and firstborn poem, creation,
   reconciliation, ministry, mystery, fullness, philosophy warning,
   circumcision, baptism, rulers and powers, festival and Sabbath, asceticism,
   visions, heavenly life, old and new humanity, household code, prayer,
   witness, coworkers, Laodicea, Archippus, autograph, chains, and grace;
6. qualify disputed Pauline authorship, secretary and Pauline-school
   proposals, date, provenance and prison, destination, relation and possible
   dependence between Colossians and Ephesians, relation to Philemon,
   audience, opponents, purpose, integrity, and the lost Laodicean letter
   without treating canonical first-person voice as a solved modern
   authorship claim;
7. distinguish Pauline-form letter, thanksgiving, prayer, poetic or
   traditional material, scriptural allusion, cosmic and body imagery,
   mystery disclosure, polemic, warning, vice and virtue instruction,
   household code, travel notice, greetings, autograph, and benediction;
8. address image, firstborn, creation, reconciliation, body, church, fullness,
   ministry, mystery, knowledge, wisdom, philosophy, circumcision, baptism,
   forgiveness, rulers and powers, cross, festivals, new moon, Sabbath,
   asceticism, angel worship, visions, heavenly life, new humanity, divine
   image, election, love, peace, word, worship, household relations, labor,
   prayer, witness, chains, and grace;
9. preserve uncertainty concerning authorship; prison and date; relation to
   Ephesians and Philemon; poetic or traditional material in 1:15-20;
   “image,” “firstborn,” and “all fullness”; Paul's sufferings and what is
   lacking; the Colossian philosophy or opponents; elemental powers;
   circumcision and baptism; the erased record; rulers and powers; festival,
   new moon, and Sabbath; food and drink; angel worship; visions; asceticism;
   things above; the household code; Nympha's textual variant; Archippus; and
   the Laodicean letter;
10. distinguish historical claim, epistolary voice, pseudepigraphal
    convention proposal, opponent characterization, scriptural voice,
    metaphor, lexical claim, textual variant, traditional material,
    Pauline-letter comparison, canonical trajectory, doctrine, confessional
    system, reception, pastoral application, and modern analogy;
11. add safeguards against antisemitism, supersessionism, anti-Jewish Torah
    and Sabbath caricature, ethnic contempt, spiritual abuse, authoritarian
    church office, misogyny, patriarchal marriage, child abuse, anti-LGBTQ
    coercion, slavery apologetics, worker exploitation, ableism,
    mental-health stigma, medical neglect, dangerous exorcism, conspiracy
    theories, coerced asceticism, body shame, prosperity extraction,
    nationalism, militarism, colonial mission, forced conversion, religious
    violence, partisan capture, public shaming, trauma glorification, and
    ecological neglect; and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 42 Colossians completed the controlled scope above. The record remains
an unapproved draft and its reviewer checklist is in
[`ckl-phase-5-colossians-review.md`](ckl-phase-5-colossians-review.md).

The corrected record contains thirty sourced claims, forty-eight
current-taxonomy interpretive notes, twenty-five sources, twenty-four
URL-bearing external sources, three high-precision top-level aliases plus
retrieval metadata, eighteen normalized Scripture anchors, ten Hebrew
entries, twenty Greek entries, and eight verified graph relationships. Its
focused eight-method factual and SQLite suite and thirty-two book-scoped
retrieval questions pass. The full 524-test CKL suite, single-file and
repository validators, graph audit, generated reports, and final SQLite
artifact are recorded in the reviewer report.

Active next wave: continue Phase 5 with this controlled 1 Thessalonians
correction wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against 1 Thessalonians, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, geography, persecution, or opponent
   claims;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P30, P46 where applicable, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi,
   Claromontanus, versions, Thessalonian and Macedonian inscriptions and
   archaeology, Roman provincial and civic evidence, households, patronage,
   labor, associations, ruler cult, rhetoric, letter conventions, and early
   reception before drafting claims;
4. distinguish Paul, Silvanus, and Timothy as named senders; the shifting
   first-person plural and singular voices; the Thessalonian assembly; Jews
   and gentiles; women and men; workers and patrons; bereaved people; local
   opponents and persecutors; Jesus, God, the Spirit, angels, the dead in
   Messiah, and later interpreters without inventing one house church,
   demographic, or persecuting group;
5. map 1 Thessalonians 1:1-10; 2:1-16; 2:17-3:13; 4:1-12; 4:13-5:11; and
   5:12-28 while indexing prescript, thanksgiving, imitation, turning from
   idols, mission memory, integrity, maternal and paternal metaphors, labor,
   separation, Timothy's mission, prayer, holiness, sexuality, sibling love,
   quiet work, grief, resurrection, coming, meeting, day of the Lord,
   watchfulness, leaders, community care, prophecy, discernment,
   sanctification, greeting, reading, and grace;
6. qualify strong Pauline-authorship consensus, the roles of Silvanus and
   Timothy, date and Corinthian provenance proposals, Thessalonica's setting,
   relation to Acts 17, audience composition, persecution, the polemic in
   2:14-16 and its textual or compositional proposals, occasion, chronology,
   integrity, and relation to 2 Thessalonians without inventing a complete
   itinerary or crisis;
7. distinguish Pauline letter, thanksgiving, autobiographical mission
   defense, familial metaphor, travel report, prayer wish, paraenesis,
   holiness instruction, apocalyptic consolation, day-of-the-Lord warning,
   community exhortation, greeting, reading charge, and benediction;
8. address faith, love, hope, election, imitation, idols, wrath, gospel,
   integrity, suffering, mission, leadership, labor, affection, Satan,
   holiness, sexuality, love, work, grief, resurrection, parousia, descent,
   trumpet, meeting, day of the Lord, wrath and salvation, watchfulness,
   prophecy, discernment, peace, sanctification, and grace;
9. preserve uncertainty concerning coworker roles; date and itinerary;
   audience and persecution; election; imitation; wrath; maternal and
   paternal metaphors; manual labor; Satan; sexual holiness and the meaning
   of `skeuos`; quiet living; the dead in Messiah; sequence and imagery of
   the parousia; `apantēsis`; rapture systems; timing of the day; leaders;
   prophecy; testing everything; and authorship, textual history, rhetoric,
   and antisemitic reception of 2:14-16;
10. distinguish historical claim, epistolary voice, mission-memory rhetoric,
    scriptural voice, familial metaphor, apocalyptic image, lexical claim,
    textual or interpolation proposal, Pauline-letter comparison, canonical
    trajectory, doctrine, confessional system, reception, pastoral
    application, and modern analogy;
11. add safeguards against antisemitism, supersessionism, collective Jewish
    blame, ethnic contempt, sexual coercion, purity culture, misogyny,
    anti-LGBTQ coercion, authoritarian leadership, worker exploitation,
    idleness shaming, grief suppression, disability and mental-health stigma,
    medical neglect, date setting, rapture panic, conspiracy theories,
    militarism, nationalism, partisan capture, colonial mission, forced
    conversion, religious violence, prosperity extraction, public shaming,
    trauma glorification, and ecological neglect; and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 43 1 Thessalonians completed the controlled scope above. The record
remains an unapproved draft and its reviewer checklist is in
[`ckl-phase-5-1-thessalonians-review.md`](ckl-phase-5-1-thessalonians-review.md).

The corrected record contains twenty-six sourced claims, forty-two
current-taxonomy interpretive notes, twenty-one sources, twenty URL-bearing
external sources, five high-precision top-level aliases plus retrieval
metadata, sixteen normalized Scripture anchors, ten Hebrew entries, twenty
Greek entries, and seven verified graph relationships. Its focused
eight-method factual and SQLite suite and thirty-two book-scoped retrieval
questions pass. The full 532-test CKL suite, single-file and repository
validators, graph audit, generated reports, and final SQLite artifact are
recorded in the reviewer report.

After Phase 5 Wave 43, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 569 / 51 |
| Complete records with candidate Phase 2 section gaps | 568 |
| Raw records missing explicit `section_status` | 569 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 569 |
| Interpretive notes using current taxonomies | 1,734 |
| Interpretive notes still using legacy taxonomies | 1,216 |
| Granular claims authored | 1,062 |
| External sources | 1,184 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,285 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,837 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with this controlled 2 Thessalonians
correction wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against 2 Thessalonians, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, geography, persecution, or opponent
   claims;
3. gather the critical Greek text, Hebrew Bible and Septuagint comparanda,
   P30, Sinaiticus, Vaticanus, Alexandrinus, Ephraemi, Claromontanus,
   versions, Thessalonian and Macedonian evidence, Roman civic and imperial
   context, apocalyptic discourse, labor, patronage, rhetoric, pseudepigraphy,
   and early reception before drafting claims;
4. distinguish Paul, Silvanus, and Timothy as named senders; plural and
   singular voices; the Thessalonian assembly; persecutors; the idle or
   disruptive; the man of lawlessness; the restrainer; Satan; rulers and
   powers; Jews and gentiles; women and men; workers and patrons; and later
   interpreters without inventing one opponent or demographic;
5. map 2 Thessalonians 1:1-12; 2:1-17; and 3:1-18 while indexing prescript,
   thanksgiving, endurance, judgment, relief, revelation, glory, prayer,
   coming and gathering, rebellion, man of lawlessness, temple, restrainer,
   Satanic signs, deception, election, tradition, request for prayer,
   deliverance, divine faithfulness, work, discipline, peace, autograph, and
   grace;
6. qualify disputed Pauline authorship, possible secretary or Pauline-school
   composition, date, provenance, relation and sequence relative to
   1 Thessalonians, audience, persecution, pseudonymous-letter concern,
   apocalyptic crisis, integrity, purpose, and relation to Acts without
   treating canonical voice as a solved modern authorship claim;
7. distinguish Pauline-form letter, thanksgiving, judgment oracle,
   apocalyptic disclosure, scriptural allusion, adversary portrait,
   exhortation, prayer wish, labor example, disciplinary command, autograph,
   greeting, and benediction;
8. address suffering, judgment, vengeance, relief, kingdom, glory, calling,
   coming, gathering, rebellion, lawlessness, temple, restraint, Satan,
   signs, deception, truth, election, sanctification, tradition, prayer,
   faithfulness, work, idleness, discipline, siblinghood, peace, autograph,
   and grace;
9. preserve uncertainty concerning authorship; date and sequence; relation to
   1 Thessalonians; persecution; fiery judgment and eternal destruction;
   coming and gathering; the rebellion; man of lawlessness; temple; the
   restrainer; Satanic signs; deceptive power; election; traditions; the
   alleged letter; idleness and work; discipline; and autograph;
10. distinguish historical claim, epistolary voice, pseudepigraphal proposal,
    apocalyptic image, scriptural voice, lexical claim, textual variant,
    Pauline-letter comparison, canonical trajectory, doctrine, confessional
    system, reception, pastoral application, and modern analogy;
11. add safeguards against antisemitism, supersessionism, collective blame,
    ethnic contempt, authoritarian discipline, worker exploitation,
    unemployment and disability shaming, public shunning, spiritual abuse,
    medical neglect, date setting, rapture panic, antichrist accusations,
    conspiracy theories, dangerous exorcism, militarism, nationalism,
    partisan capture, colonial mission, forced conversion, religious
    violence, prosperity extraction, trauma glorification, and ecological
    neglect; and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 44 2 Thessalonians completed the controlled scope above. The record
remains an unapproved draft and its reviewer checklist is in
[`ckl-phase-5-2-thessalonians-review.md`](ckl-phase-5-2-thessalonians-review.md).

The corrected record contains twenty-seven sourced claims, forty-two
current-taxonomy interpretive notes, twenty-two sources, twenty-one URL-bearing
external sources, five high-precision top-level aliases plus retrieval
metadata, seventeen normalized Scripture anchors, ten Hebrew entries, twenty
Greek entries, and seven verified graph relationships. Its focused
eight-method factual and SQLite suite and thirty-two book-scoped retrieval
questions pass. The full 540-test CKL suite, single-file and repository
validators, graph audit, generated reports, and final SQLite artifact are
recorded in the reviewer report.

After Phase 5 Wave 44, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 568 / 52 |
| Complete records with candidate Phase 2 section gaps | 567 |
| Raw records missing explicit `section_status` | 568 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 568 |
| Interpretive notes using current taxonomies | 1,776 |
| Interpretive notes still using legacy taxonomies | 1,214 |
| Granular claims authored | 1,089 |
| External sources | 1,205 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,287 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,839 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with this controlled 1 Timothy correction
wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against 1 Timothy, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, audience, Ephesus, office, opponent, or social
   claims;
3. gather the critical Greek text, early manuscripts and versions, Hebrew
   Bible and Septuagint comparanda, Ephesus and Roman Asia evidence,
   households, patronage, slavery, gender, widows, wealth, education,
   associations, rhetoric, pseudepigraphy, and early reception before
   drafting claims;
4. distinguish the named Paul and Timothy, possible secretary or
   Pauline-school author, teachers of different doctrine, women and men,
   overseers, deacons, elders, widows, enslaved and free people, wealthy
   members, household members, and later interpreters without inventing one
   opponent group or church structure;
5. map 1 Timothy 1:1-20; 2:1-3:16; 4:1-5:2; 5:3-6:2; and 6:3-21 while
   indexing prescript, charge, law, autobiographical example, prayer,
   authorities, salvation, gendered instruction, overseers, deacons, mystery,
   ascetic teaching, training, public reading, gifts, age and kinship,
   widows, elders, accusations, health advice, slavery, wealth, contentment,
   final charge, and grace;
6. qualify disputed Pauline authorship, secretary and Pauline-school
   proposals, date, provenance, destination, relation to Titus and 2 Timothy,
   audience, opponents, church-order development, integrity, purpose, and
   relation to Acts without treating canonical first-person voice as a solved
   modern authorship claim;
7. distinguish Pauline-form letter, administrative instruction, polemic,
   vice list, autobiographical example, prayer rule, household code,
   qualifications list, hymn or confession, prophecy and charge, widow list,
   disciplinary procedure, diatribe, and benediction;
8. address sound teaching, law, gospel, mercy, faith, conscience, prayer,
   mediation, salvation, gender, creation argument, leadership, household,
   mystery, asceticism, embodiment, Scripture reading, gifts, widows, elders,
   slavery, wealth, contentment, knowledge, trust, and grace;
9. preserve uncertainty concerning authorship; date and destination;
   opponents; myths and genealogies; use of law; vice-list translation;
   women's dress, teaching, authority, childbirth, and salvation; overseer
   and deacon roles; women in 3:11; confession; asceticism; bodily training;
   prophecy and ordination; widow enrollment; elder pay and discipline;
   slavery; money, wealth, and falsely named knowledge;
10. distinguish historical claim, epistolary voice, pseudepigraphal proposal,
    rhetorical opponent, household convention, lexical claim, textual
    variant, traditional material, Pauline-letter comparison, canonical
    trajectory, doctrine, confessional system, reception, pastoral
    application, and modern analogy;
11. add safeguards against antisemitism, supersessionism, homophobia and
    mistranslation, misogyny, silencing women, authoritarian office,
    spiritual abuse, clericalism, elder impunity, victim blaming, unsafe
    accusation procedures, slavery apologetics, worker exploitation,
    poverty and disability shaming, medical neglect, coerced asceticism,
    prosperity extraction, nationalism, militarism, colonial mission, forced
    conversion, religious violence, public shaming, and ecological neglect;
    and
12. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, run schema, graph, golden
    retrieval, factual and SQLite parity tests, produce a reviewer-facing
    report, and refresh this handoff and both generated quality reports.

Wave 45 1 Timothy completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-1-timothy-review.md`](ckl-phase-5-1-timothy-review.md).

The corrected record contains thirty-three sourced claims, forty-three
current-taxonomy interpretive notes, twenty-five sources, twenty-three
URL-bearing external sources, six high-precision top-level aliases plus
retrieval metadata, nineteen normalized Scripture anchors, ten Hebrew entries,
twenty-three Greek entries, and eight verified graph relationships. Its
focused eight-method factual and SQLite suite and forty book-scoped retrieval
questions pass. The full 548-test CKL suite, single-file and repository
validators, graph audit, generated reports, and final SQLite artifact are
recorded in the reviewer report.

After Phase 5 Wave 45, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 567 / 53 |
| Complete records with candidate Phase 2 section gaps | 566 |
| Raw records missing explicit `section_status` | 567 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 567 |
| Interpretive notes using current taxonomies | 1,819 |
| Interpretive notes still using legacy taxonomies | 1,212 |
| Granular claims authored | 1,122 |
| External sources | 1,228 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,290 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,842 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with this controlled 2 Timothy correction
wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against 2 Timothy, removing inherited
   Pauline-letter templates, generic events, false completion metadata, and
   unsupported authorship, imprisonment, Rome, Ephesus, coworker, opponent,
   martyrdom, or church-order claims;
3. gather the critical Greek text, early manuscripts and versions, Hebrew
   Bible and Septuagint comparanda, Roman imprisonment and patronage evidence,
   household and slavery context, pseudepigraphy, education and letter
   rhetoric, and early reception before drafting claims;
4. distinguish the named Paul and Timothy, possible secretary or
   Pauline-school author, Lois, Eunice, Onesiphorus and household, Phygelus,
   Hermogenes, Hymenaeus, Philetus, Jannes, Jambres, Demas, Crescens, Titus,
   Luke, Mark, Tychicus, Carpus, Alexander, Prisca, Aquila, Erastus,
   Trophimus, Eubulus, Pudens, Linus, Claudia, brothers and sisters, teachers,
   opponents, enslaved people, and later interpreters without turning the
   greetings into a complete itinerary;
5. map 2 Timothy 1:1-18; 2:1-26; 3:1-17; and 4:1-22 while indexing prescript,
   thanksgiving, ancestry, tears, sincere faith, gift, shame, suffering,
   entrusted deposit, abandonment and loyalty, soldier-athlete-farmer
   metaphors, faithful saying, word handling, resurrection dispute, vessels,
   youthful desires, gentle correction, last-days vice list, learning,
   persecution, sacred writings, God-breathed Scripture, proclamation,
   departure, crown, defense, coworkers, personal requests, warning,
   deliverance, greetings, and grace;
6. qualify disputed Pauline authorship, secretary and Pauline-school
   proposals, date, provenance, imprisonment, relation to Acts, 1 Timothy and
   Titus, audience, opponents, integrity, literary testament proposals,
   historical reliability of personal notices, and martyrdom reconstruction;
7. distinguish Pauline-form letter, prison letter, testament, thanksgiving,
   autobiographical appeal, chain of transmission, metaphors, faithful saying,
   hymn or confession, vice list, household analogy, polemic, paraenesis,
   charge, farewell, travel memorandum, warning, greeting, and benediction;
8. preserve uncertainty concerning spirit of fear, gift and laying on hands,
   deposit, Onesiphorus, soldier entanglement, athlete rules, resurrection
   teaching, approved word handling, vessels, Jannes and Jambres, learning
   women, last days, sacred writings, `theopneustos`, Scripture's scope and
   sufficiency, itching ears, departure, crown, rescue from the lion, first
   defense, coworker movements, cloak, books and parchments, Alexander, and
   Claudia;
9. distinguish historical claim, epistolary voice, pseudepigraphal proposal,
   testament convention, rhetorical opponent, household convention, lexical
   claim, textual variant, traditional material, Pauline-letter comparison,
   canonical trajectory, doctrine, confessional system, reception, pastoral
   application, and modern analogy;
10. add safeguards against antisemitism, supersessionism, homophobia and
    mistranslation, misogyny and blaming women learners, authoritarian office,
    spiritual abuse, clericalism, leader exceptionalism, martyrdom and trauma
    glorification, militarism, sports and productivity coercion, anti-
    intellectualism, disability and mental-health shame, medical neglect,
    coercive discipline, public shaming, slavery apologetics, worker
    exploitation, nationalism, colonial mission, forced conversion, religious
    violence, and ecological neglect;
11. populate only applicable hermeneutical and retrieval sections, use
    current certainty and dispute labels only where evidence justifies them,
    keep statuses honest with human review missing, and ensure book-scoped
    retrieval ranks 2 Timothy ahead of broad Paul, Timothy, Scripture,
    suffering, and pastoral-letter records; and
12. run schema, graph, golden retrieval, factual and SQLite parity tests,
    produce a reviewer-facing report, and refresh this handoff and both
    generated quality reports.

Wave 46 2 Timothy completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-2-timothy-review.md`](ckl-phase-5-2-timothy-review.md).

The corrected record contains thirty-one sourced claims, forty-one
current-taxonomy interpretive notes, twenty-two sources, twenty URL-bearing
external sources, seven high-precision top-level aliases plus retrieval
metadata, nineteen normalized Scripture anchors, ten Hebrew entries,
twenty-five Greek entries, and eight verified graph relationships. Its
focused eight-method factual and SQLite suite and forty book-scoped retrieval
questions pass. The full 556-test CKL suite, validators, graph audit,
generated reports, and final SQLite artifact are recorded in the reviewer
report.

After Phase 5 Wave 46, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 566 / 54 |
| Complete records with candidate Phase 2 section gaps | 565 |
| Raw records missing explicit `section_status` | 566 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 566 |
| Interpretive notes using current taxonomies | 1,860 |
| Interpretive notes still using legacy taxonomies | 1,210 |
| Granular claims authored | 1,153 |
| External sources | 1,248 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,293 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,845 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with a controlled Titus correction wave:

1. create book-specific factual and retrieval regression fixtures before
   editing content;
2. audit every populated field against Titus and remove generic Pastoral
   templates, unsupported Crete, travel, office, opponent, and social claims;
3. gather critical Greek, manuscript and versional evidence, Hebrew Bible and
   Septuagint comparanda, Cretan and Roman provincial evidence, households,
   slavery, patronage, gender, rhetoric, pseudepigraphy, and reception;
4. distinguish Paul and Titus, possible secretary or Pauline-school author,
   elders and overseers, age and gender groups, enslaved people, opponents,
   Artemas, Tychicus, Zenas, Apollos, and later interpreters without inventing
   one opponent group or settled polity;
5. map Titus 1:1-16; 2:1-15; and 3:1-15 while indexing prescript, truth,
   godliness, Crete, elders, overseers, households, opponents, the Cretan
   quotation, age and gender instruction, slavery, grace, appearing,
   self-giving, rulers, works, washing, renewal, justification, heirs,
   controversies, discipline, travel, coworkers, hospitality, and grace;
6. qualify authorship, date, provenance, destination, relation to Acts and
   the Pastorals, audience, opponents, church order, integrity, purpose,
   personal notices, and the Nicopolis reconstruction;
7. preserve uncertainty concerning elder and overseer relation, household
   qualifications, rebellious people, circumcision language, the Epimenides
   quotation, purity, gendered instruction, slavery, `epiphaneia`, washing of
   regeneration, renewal, justification, good works, controversies,
   genealogies, law disputes, divisive-person discipline, and closing travel;
8. distinguish biblical wording, epistolary voice, pseudepigraphal proposal,
   rhetorical opponent, Cretan stereotype, household convention, lexical
   claim, textual variant, traditional material, doctrine, reception,
   pastoral application, and modern analogy;
9. add safeguards against antisemitism, supersessionism, anti-Cretan ethnic
   contempt, misogyny, anti-LGBTQ coercion, authoritarian office, clericalism,
   victim blaming, slavery apologetics, worker exploitation, nationalism,
   colonial mission, forced conversion, religious violence, public shaming,
   prosperity extraction, and ecological neglect; and
10. keep human review missing, ensure Titus ranks ahead of broad Paul, Titus
    person, Crete, leadership, household, grace, works, and Pastoral records,
    then run schema, graph, retrieval, factual, SQLite, report, and reviewer
    checks.

Wave 47 Titus completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-titus-review.md`](ckl-phase-5-titus-review.md).

The corrected record contains thirty-three sourced claims, forty
current-taxonomy interpretive notes, twenty-two sources, twenty URL-bearing
external sources, eight high-precision top-level aliases plus retrieval
metadata, fifteen normalized Scripture anchors, ten Hebrew entries,
twenty-five Greek entries, and eight verified graph relationships. Its
focused eight-method factual and SQLite suite and forty book-scoped retrieval
questions pass. The full 564-test CKL suite, validators, graph audit,
generated reports, and final SQLite artifact are recorded in the reviewer
report.

After Phase 5 Wave 47, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 565 / 55 |
| Complete records with candidate Phase 2 section gaps | 564 |
| Raw records missing explicit `section_status` | 565 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 565 |
| Interpretive notes using current taxonomies | 1,900 |
| Interpretive notes still using legacy taxonomies | 1,208 |
| Granular claims authored | 1,186 |
| External sources | 1,268 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,296 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,848 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with a controlled Philemon correction wave:

1. create book-specific factual and retrieval regression fixtures before
   editing content;
2. audit every populated field against Philemon and remove generic Pauline
   templates, unsupported imprisonment, Colossae, Rome, Ephesus, household,
   legal, manumission, and itinerary claims;
3. gather the critical Greek text, early manuscripts and versions, Hebrew
   Bible and Septuagint comparanda, Roman slavery and manumission evidence,
   household, patronage, friendship, kinship, honor, rhetoric, imprisonment,
   pseudepigraphy, and reception evidence;
4. distinguish Paul, Timothy, Philemon, Apphia, Archippus, Onesimus, Epaphras,
   Mark, Aristarchus, Demas, Luke, the house assembly, enslaved and free
   people, possible secretary or Pauline-school author, and later interpreters
   without inventing biographies or a complete Colossian network;
5. map Philemon 1-7; 8-22; and 23-25 while indexing prescript, house assembly,
   thanksgiving, love, faith, partnership, appeal, age and imprisonment,
   Onesimus, usefulness wordplay, kinship, sending and receiving, consent,
   separation, debt, charge, partnership, confidence, guest room, coworkers,
   greetings, and grace;
6. qualify authorship, date, provenance, imprisonment, destination, relation
   to Colossians, identity and status of Onesimus, nature of the separation,
   legal standing, debt, theft, manumission, household assembly, purpose,
   rhetoric, outcome, and historical reliability;
7. preserve uncertainty concerning `presbytēs`, prisoner language, Paul's
   authority and appeal, Onesimus's conversion, usefulness wordplay,
   `splanchna`, sending, consent, "for this reason he was separated," "no
   longer as a slave," brotherhood, debt, "charge it to me," emancipation,
   obedience, "even more," guest room, and every closing name;
8. distinguish biblical wording, epistolary voice, historical
   reconstruction, legal analogy, rhetorical strategy, lexical claim,
   textual variant, Pauline-letter comparison, doctrine, reception, pastoral
   application, and modern analogy;
9. add safeguards against slavery apologetics, trafficking, worker
   exploitation, coercive reconciliation, returning people to abusers,
   clerical pressure, debt bondage, victim blaming, public shaming, class and
   caste hierarchy, racism, antisemitism, supersessionism, misogyny,
   anti-LGBTQ coercion, nationalism, colonial mission, forced conversion,
   religious violence, prosperity extraction, and ecological neglect; and
10. keep human review missing, ensure Philemon ranks ahead of broad Paul,
    Onesimus, slavery, household, reconciliation, debt, Colossians, and
    Pauline-letter records, then run schema, graph, retrieval, factual,
    SQLite, report, and reviewer checks.

Wave 48 Philemon completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-philemon-review.md`](ckl-phase-5-philemon-review.md).

The corrected record contains thirty-one sourced claims, forty-two
current-taxonomy interpretive notes, twenty-four sources, twenty-two
URL-bearing external sources, eight high-precision top-level aliases plus
retrieval metadata, twelve normalized Scripture anchors, ten Hebrew entries,
twenty-nine Greek entries, and eight verified graph relationships. Its focused
eight-method factual and SQLite suite and forty book-scoped retrieval questions
pass. The full 572-test CKL suite, validators, graph audit, generated reports,
and final SQLite artifact are recorded in the reviewer report. The expanded
record initially displaced Colossians for one existing relationship query; an
exact Colossians alias now preserves that golden result, and both book fixtures
plus the affected 168-test batch pass.

After Phase 5 Wave 48, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 564 / 56 |
| Complete records with candidate Phase 2 section gaps | 563 |
| Raw records missing explicit `section_status` | 564 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 564 |
| Interpretive notes using current taxonomies | 1,942 |
| Interpretive notes still using legacy taxonomies | 1,206 |
| Granular claims authored | 1,217 |
| External sources | 1,290 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,299 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,851 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with a controlled Hebrews correction wave:

1. create book-specific factual and retrieval regression fixtures before
   editing content;
2. audit every populated field against Hebrews and remove generic
   general-letter templates, unsupported Pauline authorship, Rome, Jerusalem,
   temple-date, persecution, audience, and destination claims;
3. gather the critical Greek text, early papyri, manuscripts and versions,
   Hebrew Bible and Septuagint sources, Second Temple priesthood, sacrifice,
   sanctuary, covenant, angel, wisdom, and pilgrimage comparanda, Greco-Roman
   rhetoric, homily and letter forms, persecution, patronage, and reception;
4. distinguish the anonymous speaker or writer, possible authors proposed in
   reception, Jesus, God, Spirit, angels, Moses, Aaron, Melchizedek, Abraham,
   Sarah, the wilderness generation, priests, witnesses, hearers, leaders,
   Timothy, Italian associates, and later interpreters without inventing an
   author, one community crisis, or a settled destination;
5. map Hebrews 1:1-4:13; 4:14-10:39; 11:1-12:29; and 13:1-25 while indexing
   divine speech, Son, angels, warning, rest, high priest, Melchizedek,
   maturity, hope, covenant, sanctuary, sacrifice, conscience, access,
   perseverance, faith, witnesses, discipline, unshakable kingdom, hospitality,
   prisoners, marriage, money, leaders, suffering outside the camp, praise,
   mutual care, benediction, Timothy, Italy, and grace;
6. qualify authorship, date, provenance, destination, audience, language,
   genre, relation to Paul, composition and epistolary ending, pre- or
   post-70 temple inference, social pressure, persecution, apostasy rhetoric,
   and historical reliability;
7. preserve uncertainty concerning Son and wisdom language, angel
   subordination, Psalm readings, `oikoumenē`, rest, Word, high-priest
   Christology, Melchizedek, impossibility passages, oath, hope, covenant,
   `diathēkē`, heavenly sanctuary, sacrifice, blood, conscience, perfection,
   law, supersession, faith, women in the witness list, discipline, Esau,
   Sinai and Zion, unshakable kingdom, leaders, altar, outside the camp, and
   every closing notice;
8. distinguish biblical wording, scriptural quotation, homiletic voice,
   historical reconstruction, Second Temple comparison, rhetorical warning,
   lexical claim, textual variant, typology, doctrine, reception, pastoral
   application, and modern analogy;
9. add safeguards against antisemitism, supersessionism, anti-Judaism,
   denigration of Torah, sacrificial or Jewish worship, spiritual abuse,
   terrorizing people with apostasy texts, victim blaming, authoritarian
   leadership, clericalism, misogyny, anti-LGBTQ coercion, ableism, blood and
   violence glorification, nationalism, colonial mission, forced conversion,
   religious violence, prosperity extraction, and ecological neglect; and
10. keep human review missing, ensure Hebrews ranks ahead of broad Paul,
    priesthood, covenant, sacrifice, faith, warning, angels, Moses,
    Melchizedek, rest, and general-letter records, then run schema, graph,
    retrieval, factual, SQLite, report, and reviewer checks.

Wave 49 Hebrews completed the controlled scope above. The record remains an
unapproved draft and its reviewer checklist is in
[`ckl-phase-5-hebrews-review.md`](ckl-phase-5-hebrews-review.md).

The corrected record contains thirty-two sourced claims, forty
current-taxonomy interpretive notes, twenty-seven sources, twenty-five
URL-bearing external sources, eight high-precision top-level aliases plus
retrieval metadata, twenty normalized Scripture anchors, ten Hebrew entries,
twenty-eight Greek entries, and eight verified graph relationships. Its
focused eight-method factual and SQLite suite and forty book-scoped retrieval
questions pass. The full 580-test CKL suite, validators, graph audit, generated
reports, and final SQLite artifact are recorded in the reviewer report. The
expanded record initially displaced Jeremiah for one existing quotation query;
an exact Jeremiah alias now preserves that golden result, and both book
fixtures plus the affected 139-test batch pass.

After Phase 5 Wave 49, the refreshed report records:

| Migration metric | Result |
| --- | ---: |
| Records marked `complete` / `draft` | 563 / 57 |
| Complete records with candidate Phase 2 section gaps | 562 |
| Raw records missing explicit `section_status` | 563 |
| Raw records with incomplete type-required sections | 620 |
| Raw records missing explicit `knowledge_layers` | 563 |
| Interpretive notes using current taxonomies | 1,982 |
| Interpretive notes still using legacy taxonomies | 1,204 |
| Granular claims authored | 1,249 |
| External sources | 1,315 |
| Source references that do not resolve | 0 |
| Invalid source support targets | 0 |
| Unresolved legacy object references | 14 |
| Scripture reference errors | 0 |
| Graph edges / unknown targets / orphaned records | 3,302 / 0 / 0 |
| Missing reciprocal relationship suggestions | 2,850 |
| Validator warnings / errors | 14 / 0 |

Active next wave: continue Phase 5 with a controlled James correction wave:

1. create book-specific factual and retrieval regression fixtures before
   editing content;
2. audit every populated field against James and remove generic
   general-letter templates, unsupported authorship, Jerusalem, diaspora,
   persecution, audience, opponent, itinerary, and church-order claims;
3. gather the critical Greek text, early papyri, manuscripts and versions,
   Hebrew Bible and Septuagint sources, Jewish wisdom, Torah, prophetic,
   apocalyptic, poverty and wealth, assembly, labor, patronage, healing,
   anointing, prayer, oath, rhetoric, and reception evidence;
4. distinguish James the named sender from proposed historical identities,
   the twelve tribes in diaspora, teachers, rich and poor hearers, laborers,
   merchants, elders, sick people, Elijah, Rahab, Abraham, Job, and later
   interpreters without inventing one audience profile or opponent group;
5. map James 1:1-27; 2:1-26; 3:1-18; 4:1-5:6; and 5:7-20 while indexing
   greeting, testing, wisdom, wealth, desire, birth, hearing and doing,
   religion, partiality, royal law, mercy, faith and works, teachers, speech,
   wisdom, conflict, friendship, humility, judgment, planning, wages, wealth,
   patience, oaths, prayer, healing, confession, Elijah, and restoration;
6. qualify authorship, date, provenance, destination, audience, relation to
   Jesus traditions, Paul and Romans, Jewish and gentile hearers, genre,
   integrity, rhetorical situations, wealth conflict, teachers, elders,
   healing practice, and historical reliability;
7. preserve uncertainty concerning `diaspora`, double-mindedness, perfection,
   temptation, desire, firstfruits, implanted word, religion, law of liberty,
   partiality, royal law, faith and works, Rahab, justification, teaching,
   tongue and fire, wisdom from above, friendship with the world, spirit in
   4:5, judging law, tomorrow, rich oppressors, parousia, Job's endurance,
   oaths, anointing, saving the sick, confession, effective prayer, Elijah,
   sin-covering, and wandering restoration;
8. distinguish biblical wording, paraenetic voice, sapiential convention,
   rhetorical opponent, historical reconstruction, lexical claim, textual
   variant, Jesus-tradition and Pauline comparison, doctrine, reception,
   pastoral application, and modern analogy;
9. add safeguards against antisemitism, supersessionism, class contempt,
   prosperity extraction, poverty romanticization, worker exploitation,
   ableism, disability and illness shame, medical neglect, coercive
   confession, spiritual abuse, authoritarian teaching, misogyny,
   anti-LGBTQ coercion, public shaming, nationalism, colonial mission, forced
   conversion, religious violence, and ecological neglect; and
10. keep human review missing, ensure James ranks ahead of broad James-person,
    wisdom, faith, works, speech, poverty, wealth, prayer, healing, and
    general-letter records, then run schema, graph, retrieval, factual,
    SQLite, report, and reviewer checks.

The active continuation target is Phase 5 Wave 50, James. Follow the controlled
scope above; do not reopen completed Hebrews, Philemon, Titus, 2 Timothy,
1 Timothy, 2 Thessalonians, 1 Thessalonians, Colossians, Philippians,
Ephesians, Galatians, 2 Corinthians, 1 Corinthians, Romans, Acts, John, Luke,
Mark, or Matthew except to address a concrete review or regression finding.
