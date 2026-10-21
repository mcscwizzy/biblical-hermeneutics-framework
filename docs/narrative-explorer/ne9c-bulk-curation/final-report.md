# NE-9C Large-Scale Scholarly Curation — Final Report

## Corpus accounting

- **Unique authored object relationships inventoried:** 4,061.
- **Backlog presented for scholarly disposition:** 3,925. The remaining 136 were already outside the uncategorized backlog: 113 have a base taxonomy classification and 23 were covered by the pre-existing object-curation registry.
- **Backlog relationships actually reviewed:** 3,925 of 3,925. Deterministic inventory counts were kept separate from scholarly disposition counts.
- **Newly classified from the backlog:** 898.
- **Held:** 1,414, with edge-specific reasons retained.
- **Excluded:** 1,613, with edge-specific reasons retained.
- **Remaining unreviewed in the requested backlog:** 0. Held and excluded edges remain uncategorized in Narrative Explorer.
- **Total object relationships classified in the corpus:** 1,034 (113 base-taxonomy relationships, 23 preserved pre-existing object curations, and 898 new curations).
- **Curation registry after the work:** 923 entries: 921 object-edge curations and the 2 pre-existing evidence-edge curations. All 25 pre-existing entries were preserved.
- All new records are machine-assisted. Human scholarly approval remains `not_recorded`.

## Wave results

| Wave | Reviewed | Curated | Held | Excluded |
|---:|---:|---:|---:|---:|
| 1 | 500 | 308 | 128 | 64 |
| 2 | 500 | 148 | 146 | 206 |
| 3 | 500 | 71 | 188 | 241 |
| 4 | 500 | 147 | 181 | 172 |
| 5 | 500 | 118 | 250 | 132 |
| 6 | 500 | 36 | 298 | 166 |
| 7 | 500 | 34 | 194 | 272 |
| 8 | 425 | 36 | 29 | 360 |
| **Total** | **3,925** | **898** | **1,414** | **1,613** |

## Classification distribution

The following counts include the 113 base-taxonomy classifications and all 921 object curation entries:

| Classification | Count |
|---|---:|
| Direct quotation | 2 |
| Explicit textual reference | 483 |
| Interpretive association | 253 |
| Later canonical reception | 67 |
| Narrative parallel | 2 |
| Shared literary motif | 9 |
| Thematic relationship | 218 |
| **Total classified object relationships** | **1,034** |

Among the 898 new curation entries, 495 have high curation confidence and 403 moderate confidence. Confidence is not a measure of human approval.

## Scholarly uncertainty recorded

Curation notes preserve uncertainty about original literary and historical settings; the distinction between quotation, reception, allusion, and shared motif; language and translation range; archaeological identification and chronology; genre, symbolism, and historical referents; the reconstruction of institutions and social practices; and competing theological interpretations. New curation categories were not introduced. Broad or unsupported proposals remain held or excluded.

## Validation and tests

- Final workflow validation: `python3 scripts/ne9c_bulk_curation.py validate` — **passed**.
- Final terminal workflow state: **CORPUS_COMPLETE** (`review_complete: true`, `current_wave: null`; all eight wave manifests completed).
- Focused wave 6 regressions: **893 passed**.
- Focused wave 7 bulk and projection regressions: **200 passed** (5 bulk tests and 195 Narrative Explorer projection tests).
- Focused wave 8 bulk and projection regressions: **304 passed** (5 bulk tests and 299 Narrative Explorer projection tests).
- Frontend suite: **12 passed, 0 failed** (`npm test`), including Narrative Explorer service worker and browser-navigation tests.
- Complete implementation-specific Python/API set (`tests/test_ne9c_bulk_curation.py`, `tests/test_narrative_explorer_curation.py`, `tests/test_narrative_explorer_api.py`, `tests/test_narrative_explorer_ui_config.py`): **989 passed** in 7m17s. This includes parameterized projection validation across the full registry.
- The complete repository-wide Python suite was not green. The temporary test venv initially lacked declared `httpx` and `jinja2` dependencies; both were installed into `/tmp` only. The serial full-suite run was interrupted because of its unusually long runtime, and a four-worker attempt failed early in canonical-library retrieval tests. Serial isolation found three failing subqueries in `FirstCorinthiansRecordTests.test_retrieval_answers_book_specific_questions` (weaker members/conscience; weakness, illness, and death at the meal; and “one body and many members”). The same three failures reproduce on the untouched base worktree at `76de4a5b`, with the retrieval ranking a topical CKL object ahead of `1-corinthians`. This retrieval path and its CKL records were not changed in this task. The targeted Narrative Explorer/API suites pass.
- CKL source-object fingerprint remained `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`. No canonical CKL source records were modified.

The registry’s parameterized identity/provenance validation and focused projection tests confirm that authored direction and metadata are preserved, supporting CKL sources resolve, direct applicability is passage-scoped, and no reverse edge or book-level passage scope is invented. Held/excluded entries remain uncategorized. The existing Narrative Explorer API and navigation remain in use.

## Branch and commits

- Starting NE-9C research branch: `research/ne9c-scholarly-curation`, based on `76de4a5b`.
- Isolated worktree: `/tmp/bhf-ne9c-bulk-curation`.
- Feature branch: `research/ne9c-bulk-curation`, pushed to `origin`.
- Wave commits: `55c708be`, `324c7da6`, `0488a03a`, `482d79b9`, `063069f3`, `9d3c5402`, `e4c9791a`, `fa318663`.
- Final accumulated report committed and pushed after final workflow certification.
- The work was not merged to master and was not deployed.

No resume command is needed: the requested backlog is complete and certified. To re-check the terminal checkpoint, run:

```sh
python3 scripts/ne9c_bulk_curation.py validate
python3 scripts/ne9c_bulk_curation.py next
```
