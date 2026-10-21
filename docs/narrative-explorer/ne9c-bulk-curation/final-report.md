# NE-9C Scholarly Quality Gate — Final Acceptance Report

## Acceptance decision

The eight-wave backlog is complete and the acceptance audit is complete. Of the **898 relationships originally classified** in the backlog, **384 retained their classification, 24 changed classification, 481 were downgraded to held, and 9 were excluded**. The accepted registry now contains 408 new object curations. Held and excluded relationships remain uncategorized in Narrative Explorer.

The 3,925-item workflow ledger now records **408 curated, 1,895 held, and 1,622 excluded**, with no unreviewed items and no current wave. These workflow totals include the decisions that were held or excluded before the acceptance audit.

## Classification standard

The operational definitions and minimum evidence thresholds for all nine connection types are in [Narrative Explorer’s evidence and connection contract](../03-evidence-and-connection-contract.md#operational-classification-rules). In particular, `explicit_textual_reference` requires a biblical text to identify another biblical text as a source or object of reference. A passage naming a person, event, place, institution, doctrine, or topic does not meet that threshold by itself. Direct quotation, later canonical reception, shared motif, narrative parallel, thematic relation, proposed echo, and interpretive association retain separate tests and evidence requirements.

### Audit disposition by wave

“Changed” means the relationship remains curated under a different classification. Counts are relative to the 898 classifications that entered this acceptance pass.

| Wave | Retained | Changed | Held | Excluded |
|---:|---:|---:|---:|---:|
| 1 | 169 | 8 | 122 | 9 |
| 2 | 36 | 13 | 99 | 0 |
| 3 | 6 | 0 | 65 | 0 |
| 4 | 89 | 0 | 58 | 0 |
| 5 | 41 | 1 | 76 | 0 |
| 6 | 16 | 0 | 20 | 0 |
| 7 | 18 | 0 | 16 | 0 |
| 8 | 9 | 2 | 25 | 0 |
| **Total** | **384** | **24** | **481** | **9** |

### Explicit-reference audit

Every one of the **483** initially `explicit_textual_reference` entries was examined. **None met the text-to-text operational definition**. Nine were retained under a more specific supported classification: 4 became `later_canonical_reception`, 2 `interpretive_association`, 2 `thematic_relationship`, and 1 `narrative_parallel`. The other **465 were held** and **9 excluded**.

The other 415 original classifications received a risk-weighted audit across all eight waves. Review covered all high-confidence non-explicit entries, all motif entries, the parallel and quotation entries, all Wave 2 later-reception entries, and a moderate-confidence sample across every wave. The audit expanded around systematic overuse of explicit reference and around endpoint scope, passage projection, archaeological attribution, and generic subject links. In total, 13 original later-reception entries changed to thematic or interpretive association, and 2 original motif entries changed to thematic relationship.

The accepted corpus contains **544 classified object relationships**: 113 base-taxonomy relationships, 23 preserved legacy object curations, and 408 newly accepted curations. The final classification census is:

| Classification | Total corpus | New NE-9C |
|---|---:|---:|
| Direct quotation | 2 | 1 |
| Explicit textual reference | 0 | 0 |
| Interpretive association | 253 | 248 |
| Later canonical reception | 53 | 45 |
| Narrative parallel | 2 | 1 |
| Shared literary motif | 7 | 6 |
| Thematic relationship | 227 | 107 |
| **Total** | **544** | **408** |

The 408 newly accepted curations have 28 high-confidence and 380 moderate-confidence records. Confidence is not human approval; all new records continue to record `human_scholarly_approval: not_recorded`.

## Evidence and explanation review

The source audit checked the content behind every supporting reference for the 409 curations active before the final source correction; one unsupported Qumran/Great Isaiah Scroll provenance claim was held, leaving 408 active. The audit distinguished primary biblical passages, scholarly publications, contextual background, and generated CKL historical-orientation records. It verified that each retained citation supports its specific observation, and identified circular reasoning, generic source lists, and statements that overstated scholarly agreement.

Corrections included adding 18 exact, already-existing CKL scholarly or artifact references; removing 4 empty generic references and 93 generated historical-orientation records from active support lists; and softening unsupported consensus or historical assertions in the Corinthians, Claudius, Genesis, *hesed*, and Romans 14–15 entries. No scholarship, quotation, or CKL source record was invented or edited.

The mechanical-description audit covered a 155-entry templated family: 144 retained with specific textual observations and reader explanations, and 11 held. Eighty-four mechanically appended `why` explanations were replaced with the original authored note or passage observation. Textual observation, scholarly interpretation, and uncertainty remain separately represented.

## Runtime, API, and integrity

The registry-load investigation reproduced a startup cost as the new registry grew. In seven fresh-process comparisons, observed import/application-construction times were 404/979 ms at the pre-NE-9C baseline, 3,284/3,939 ms with the initial 923-row registry, 842/1,472 ms after alias reuse, and 624/1,246 ms with 434 post-audit rows. The final registry has 433 rows after one more held decision; the measured 434-row result is adjacent to the final state. Alias reuse in `narrative_explorer_curations.py` removes repeated book-alias initialization. The app exposed the same 99 routes in each comparison.

The API/navigation diagnostic returned HTTP 200 for 5 of 5 Acts 2 Narrative Explorer route checks. Across 14 projected connections, warm request median was about 104 ms and warm projection median about 64.5 ms; the clean `f01db9dd` comparison was about 104 ms and 67.5 ms. The diagnostic used authentic parsed CKL theme objects but injected CKL lookup and empty map/archaeology providers. A full JSON-provider initialization probe exceeded 180 seconds and was interrupted, so those injected-provider timings do not establish full-provider cold-start latency.

The cold-start regression was traced to the metadata-only `/api/maps/catalog?include_records=false` branch entering the thread pool despite doing no I/O. It now returns static metadata directly. `tests/test_cold_start_diagnostics.py` passes all 7 cases, including a first request through the constructed app. Narrative Explorer API, projection, UI configuration, and navigation tests also pass.

Protected CKL object-source fingerprint: `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766` (unchanged). No records under `framework/canonical_library/objects` or the preserved `wave-legacy` curation directory changed. All 25 legacy registry entries remain unchanged. Current registry size is 433 records: 431 object curation records (23 legacy and 408 new) plus 2 pre-existing evidence curation records. The derived workflow remains `CORPUS_COMPLETE`.

## Verification results

- `python scripts/ne9c_bulk_curation.py validate` — passed; 3,925 reviewed identities and the protected fingerprint validated, with 408 curated, 1,895 held, and 1,622 excluded.
- Focused Python suite across bulk curation, curation registry, Narrative Explorer API, projection, UI configuration, and cold-start diagnostics — **559 passed** in 231.18 seconds.
- Cold-start diagnostic subset — **7 passed** in 1.53 seconds.
- Frontend `npm test` — **12 passed**.
- Curation projection audit — **0 unprojected applications** among active object curations.

Three retrieval queries in `FirstCorinthiansRecordTests.test_retrieval_answers_book_specific_questions` remain **reproduced failures**, separately from the passing suites:

1. “Who are weaker members and what is conscience?”
2. “What do weakness, illness, and death mean at the Corinthian meal?”
3. “What does one body and many members mean?”

In each case retrieval ranked a topical CKL object ahead of `1-corinthians`. The same failures reproduced on untouched base `76de4a5b`; this task changed neither the retrieval path nor its CKL records. They are not counted as successful tests.

## Branch and release status

- Branch: `research/ne9c-bulk-curation`, starting from `f01db9dd`.
- All eight backlog waves are complete; no further bulk curation was run.
- Corrections, evidence decisions, and this report are committed and pushed to `origin/research/ne9c-bulk-curation` after acceptance verification.
- No merge or deployment was performed.
