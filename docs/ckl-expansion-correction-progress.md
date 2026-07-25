# CKL Expansion and Correction Progress

Last updated: 2026-07-25

This is the durable handoff for the **BHF Canonical Knowledge Library Expansion
and Correction Plan**. The supplied plan explicitly says to begin with the
repository audit and Phase 1 quality reporting, avoid immediate bulk content
generation, and stop after each major phase. Phases 1–4 are now implemented at
the schema/runtime level. Phase 5 Waves 1–21 have corrected Genesis through
Amos as honest, source-backed drafts; none has been mechanically approved.

## Current checkpoint

| Plan area | Status | Continuation note |
| --- | --- | --- |
| Phase 1: inventory, reporting, quality metrics | **Implemented** | Deep JSON and Markdown reports, CLI support, and calculation tests are present. |
| Phase 2: section-level completeness | **Implemented; content migration pending** | Additive `section_status`, type-specific rules, readiness helpers, approval gates, audit warnings, and tests are present. Twenty-nine records now have evidence-based draft statuses; 591 still need explicit migration. |
| Phase 3: knowledge-layer classification | **Implemented; content migration pending** | Controlled primary/secondary layers flow through JSON, retrieval, prompt context, and SQLite payloads. Twenty-nine records now have explicit layers; 591 still need migration. |
| Phase 4: certainty and dispute taxonomies | **Implemented; evidence migration pending** | Current taxonomies and granular claim records are supported. Legacy values remain readable but are forbidden for approved notes; no `unknown` value was guessed or mass-relabeled. |
| Phase 5: audit/correct all 66 books | **Waves 1–21 implemented; human review pending** | Genesis through Amos are corrected drafts with sources, claims, tests, and reviewer notes. Thirty-seven books remain. |
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
The Genesis/Exodus, Leviticus/Numbers, Deuteronomy/Joshua, and Judges/Ruth
and 1 Samuel/2 Samuel and 1 Kings/2 Kings pairs are now implemented. The
recommended next pair is `1-chronicles.json` and `2-chronicles.json`,
continuing the historical-book sequence while keeping the wave small enough
for factual and source review.

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
[`ckl-phase-5-amos-review.md`](ckl-phase-5-amos-review.md).
Do not mark any corrected record complete merely because its automated checks
pass.

Then continue Phase 5 with a controlled Obadiah correction wave:

1. create book-specific factual regression fixtures before editing content;
2. audit every populated field against the book it describes;
3. gather Scripture anchors and independent sources before drafting claims;
4. distinguish Obadiah's superscription, YHWH's reported speech, the prophetic
   voice, the nations summoned against Edom, Edom or Esau, Jacob or Israel,
   Judah and Jerusalem, foreign invaders, fugitives, allies, sages, warriors,
   survivors on Mount Zion, the houses of Jacob and Joseph, the house of Esau,
   Benjamin, the Negeb, the Shephelah, Gilead, Sepharad, and the kingdom
   belonging to YHWH;
5. map Obadiah 1, 2–9, 10–14, 15–16, 17–21 while qualifying the oracle's
   headings, addressees, tense, speaker transitions, poetic units, seams,
   relationship to Jeremiah 49, and alternative outlines;
6. qualify the name Obadiah, the absence of patronymic or royal dating,
   seventh-century, 587/586 BCE, early Persian, and later proposals, Edom's
   highland geography and trade routes, Jerusalem's fall, Nabataean and later
   Idumean histories, possible collections, redaction, placement after Amos,
   and Book-of-the-Twelve shaping;
7. distinguish prophetic superscription, vision report, divine messenger
   report, nations oracle, taunt, accusation, prohibition or ironic
   retrospective command, day-of-YHWH oracle, reversal saying, salvation
   oracle, territorial catalogue, and kingship conclusion;
8. address kinship betrayal, pride, security, wisdom, alliances, plunder,
   violence, gloating, looting, blocking fugitives, handing over survivors,
   day of YHWH, reciprocal judgment, drinking imagery, holiness, survivors,
   dispossession, fire, land, restoration, and divine kingship;
9. preserve uncertainty concerning historical Edom, the fall of Jerusalem in
   view, the force and time of verses 12–14, Edom's precise actions, allies,
   Teman, the messenger, nations, drinking, survivor language, the identities
   and geography in verses 19–20, Sepharad, conquerors or deliverers, and the
   date and unity of verses 17–21;
10. address Masoretic Obadiah, Old Greek Abdias, 4Q82 and other Judean Desert
    witnesses, ancient versions, Jeremiah 49, Joel, Amos, Psalms, Ezekiel,
    Malachi, Obadiah within the Twelve, early Jewish and rabbinic reception,
    New Testament resonances without invented quotation, and later Jewish,
    Christian, political, postcolonial, and trauma-aware interpretation;
11. distinguish historical referent, literary symbol, canonical trajectory,
    quotation, shared tradition, allusion, typology, Jewish reception, and
    later christological or ecclesial reception, especially Edom, Jacob,
    Jerusalem, Mount Zion, survivors, land, day of YHWH, kingdom, Jeremiah 49,
    and proposed New Testament echoes;
12. add safeguards concerning racialized or ethnic essentialism, collective
    hereditary guilt, antisemitism, anti-Arab racism, using Edom as a code for
    a modern people, supersessionism, sibling hatred, survivor blame, trauma
    exploitation, refugees and border violence, betrayal, looting, empire,
    colonialism, nationalism, war, genocide, land seizure, forced
    displacement, divine violence, vengeance, dehumanization, and partisan
    capture;
13. populate only applicable hermeneutical and retrieval sections;
14. use current certainty/dispute labels only where evidence justifies them;
15. keep section statuses honest and leave human review missing;
16. run schema, graph, golden retrieval, factual, and SQLite parity tests;
17. produce a reviewer-facing report; and
18. refresh this handoff and both generated quality reports.
