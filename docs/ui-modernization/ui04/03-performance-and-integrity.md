# BHF UI-04 — Performance, Integrity, and Test Results

**Tested source commit:** `183fa056d1b32fc0e1a19aa0eb7115c3e23731cf`<br>
**Baseline:** `c44c19a708f1073e1af815a477f8c9b6701bd4ea`<br>
**Result:** PASS for performance shape and research/data integrity. The full GUI suite remains red on ten failures reproduced at the baseline; that is a release gate in [the final decision](04-final-release-decision.md).

## Repeated browser performance

Five fresh Chrome sessions each measured a cold Explorer opening followed by a warm re-opening in the same browser session. Each used the local application with Narrative Explorer enabled, Genesis 1 selected, a 1440 × 1100 viewport, and browser HTTP cache disabled. “Click to ready” ends when the overview and all six categories are present. Topic-ready time ends when the focused Themes & Biblical Connections view is rendered. Projection timing/body size come from browser Resource Timing. DOM-node count uses the same `bhf:narrative-explorer-metrics` field used in the UI-03 report.

| Sample | Cold click → overview (ms) | Cold projection (ms) | Cold topic ready (ms) | Warm click → overview (ms) | Warm projection (ms) | Warm topic ready (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,525.7 | 8,297.6 | 231.8 | 2,339.5 | 2,107.0 | 145.8 |
| 2 | 8,145.5 | 7,550.5 | 279.8 | 2,233.1 | 1,993.4 | 146.5 |
| 3 | 7,566.7 | 7,184.3 | 278.8 | 2,245.3 | 1,956.4 | 138.1 |
| 4 | 8,114.6 | 7,610.3 | 172.6 | 2,343.1 | 2,101.3 | 148.4 |
| 5 | 7,989.2 | 7,814.6 | 162.7 | 2,248.7 | 2,069.6 | 143.9 |
| **Median** | **8,114.6** | **7,610.3** | **231.8** | **2,248.7** | **2,069.6** | **145.8** |

Cold click-to-ready varied from 7,566.7 to 8,525.7 ms; projection time varied from 7,184.3 to 8,297.6 ms. Warm click-to-ready varied from 2,233.1 to 2,343.1 ms. Each Explorer opening issued one passage projection request; focused-topic navigation issued no additional request. The Genesis 1 response was 300,562 encoded bytes (300,862 transferred) for each opening.

Initial reader DOM count was 1,100 elements in these five runs; the full document after Explorer opened had 1,284. The Explorer’s in-app render metric was 62 nodes in every run, with median overview render time of 5.1 ms cold and 1.2 ms warm.

The [UI-03 report](../../narrative-explorer/ui03/02-performance-and-visual-results.md) records one matched John 1 sample: 7,292 ms click-to-ready, 6,950.4 ms projection response, 430,833 response bytes, one request, and 60 Explorer nodes. UI-04’s five-sample Genesis 1 test has a different passage payload and repeated cold/warm protocol. The DOM metric is directly comparable (62 vs 60 nodes); request count remains one per opening and focused category navigation adds none. Passage and run differences prevent a reliable timing or payload delta claim. The small two-node increase does not demonstrate a material regression. No performance optimization or backend/schema change was made.

## Research and source integrity

| Check | Result | Evidence |
| --- | --- | --- |
| CKL source tree vs fetched baseline | PASS | No diff under `framework/canonical_library`; CKL objects, evidence, locks, fingerprints, manifests, curations, NE-10 bridges, provenance, and review metadata are unchanged. |
| CKL validator | PASS | 687 raw objects, 687 valid, 0 errors, 14 warnings. All warnings remain `incomplete_section_status` on `abba`, `arad-ostraca`, `branch-prophecy`, `chiasm`, and `exile-and-return-storyline`; no new warning class or integrity error. |
| CKL SQLite parity/integrity | PASS | 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence rows; SQLite integrity passed. Inventory fingerprint: `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. |
| Tyndale local database | PASS | 17,478 entries and anchors; no orphaned, unmapped, unrecognized, or unanchored entries; SQLite integrity passed. Source archive and database checksums are recorded in [reader acceptance](01-integrated-reader-acceptance.md#tyndale-source-provisioning). |
| Retired BHF Commentary | PASS | Compatibility tests retain HTTP 410 for retired `/api/bhf-commentary` paths; the separate active Tyndale service remains available. |
| Package and framework checks | PASS | `python tools/validate.py framework/`: 94 modules. Package/manifest-focused checks in the Python batch: 30 passed, 13 subtests passed. |
| Diff and repository hygiene | PASS | `git diff --check` clean; Tyndale database/archive and generated test runtime data excluded from Git. |

## Test results

| Check | Result | Notes |
| --- | --- | --- |
| `npm test` | PASS | 16 frontend test files; no failures or skips. Includes the new Tyndale workspace-navigation regression. |
| Focused Python/API/packaging batch | PASS | 632 tests passed, including Narrative Explorer projection/API, Tyndale, Companion, retirement, CKL, and packaging coverage. |
| Framework validation | PASS | 94 modules validated. |
| Full GUI suite, initial run | FAIL | 141 cases: 122 passed, 16 failed, 1 setup error, 2 skipped. The run used a single Selenium Chrome slot and accumulated stale browser sessions. |
| Focused GUI reruns | PASS | Six rerun cases passed: Companion cache refresh, selected-range translation comparison, My Study consolidation, Tyndale companion tab, rapid Tyndale chapter loading, and the actual Tyndale card/workspace/restoration flow. The updated layered Escape test passed at 320, 390, 768, and 1440 px (4 cases). |
| Untouched-baseline GUI subset | FAIL | On `c44c19a708f1073e1af815a477f8c9b6701bd4ea`, the 13-case neighboring-flow subset reproduced the same ten persistent failures; three cases passed. These failures are listed below and are not attributed to UI-04 changes. |
| Real-data browser acceptance | PASS | Verified Tyndale introductions, anchor/selection matching, full workspace, restored session, rapid chapter changes, and an actual offline cache miss. Browser screenshots are included under `screenshots/`. |

The four original keyboard failures expected one Escape to exit all Explorer history; after aligning the assertion with the approved two-layer behavior, all four width cases pass. The full-run failures in cache refresh and selected-range translation, the My Study renderer setup error, and the Tyndale session skip were followed by successful focused reruns. `test_mobile_viewport_measurement` was also skipped by Selenium session availability; separate responsive checks covered 320–1440 px, including the required 390 px browser viewport.

The ten failures reproduced against the untouched fetched baseline are:

- `test_canonical_browser_opens_editor_for_draft_object`
- `test_mobile_passage_heading_updates_with_translation_badge`
- `test_mobile_ask_submit_still_works`
- `test_clicking_verse_number_selects_entire_verse`
- `test_import_dialog_uses_user_supplied_translation_name`
- `test_native_resource_never_renders_previous_selection_context`
- `test_word_study_choice_updates_and_restores_shared_selection`
- `test_workspace_tabs_switch`
- `test_desktop_primary_navigation_preserves_reader_split`
- `test_context_result_header_keeps_title_readable_in_study_panel`

Their baseline reproduction establishes that UI-04 did not introduce them. Their continued presence means the repository-wide GUI acceptance gate is not green; the release consequence is stated in [the decision report](04-final-release-decision.md).
