# Tyndale and Translation Comparison UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the BHF Context comparison action and add a real, transient side-by-side Scripture comparison while preserving the independent Tyndale Companion.

**Architecture:** Dispatch `compare_translations` to the Study Companion's existing resource navigation. Add `translation_comparison` to the native resource router, read installed/device-local translations through the existing translation state and Bible request path, and render the selected passage in the existing detail host. Preserve all Tyndale IDs and API contracts.

**Tech Stack:** Browser JavaScript, Study Companion/resource-router, existing BHFApi/BHFOfflineDB reader abstractions, CSS, pytest/Selenium GUI tests, Node frontend tests.

**Spec:** `docs/superpowers/specs/2026-10-07-tyndale-translation-comparison-ui-design.md`

## Global Constraints

- Preserve `commentary` as the persisted Tyndale resource ID, the Tyndale workspace tab ID, and `/api/commentary/...` endpoints.
- Use `translation_comparison` as a separate transient companion resource; do not add a workspace tab or mutate `BHFStudySelection`.
- Compare the exact selected verse/range; use chapter data only when no verse is selected.
- Put the current/source translation first, then deduplicated installed/readable translations.
- Do not fetch text for uninstalled/license-required translations; do not download, install, or import automatically.
- Use existing translation state, Bible request, device-local merge, and offline cache behavior.
- Leave CKL, evidence locks, Commentary v1.2 content/release artifacts, and Tyndale source content unchanged.
- Do not call a model or deploy.
- Compare Commentary v1.2 identities to the recorded values from commit `7400f926f5f8f4000bef323be00a3d38471952ba` before completion.

## Review Focus

- No explicit verse selection: preserve selection state and display the chapter context.
- Duplicate, missing, or unknown translation IDs: render each readable ID once and skip IDs that are not present in installed state.
- Device-local/imported translations: merge through existing translation state and read through the normal Bible request path.
- Unavailable/offline chapter data: show a resource-local unavailable message while leaving the rest of the companion usable.
- Tyndale DB missing or a selected verse has no matching note: retain the normal missing-database message and note focus behavior.

---

### Task 1: Route the study action into the companion resource history

**Files:**
- Modify: `bhf_web/static/htmx-lite.js`
- Modify: `bhf_web/static/study-companion.js`
- Test: `tests/gui/test_study_companion.py`
- Test: `tests/frontend/bhf-commentary-card.test.js`

**Interfaces:**
- `BHFStudyActions.perform("compare_translations")` dispatches an explicit action.
- `BHFStudyCompanion.openResource("translation_comparison", {trigger})` opens the resource in normal companion history.
- Unsupported actions produce a development/test-visible failure while production remains quiet.

- [x] **Step 1: Add a failing regression for the BHF Context action**

Extend the existing BHF Commentary card action test to click the `compare_translations` action and assert the Study Companion opens `translation_comparison` without selecting the Tyndale workspace tab.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `pytest tests/gui/test_study_companion.py -k translation_comparison -q`
Expected: the action currently returns without opening a companion resource.

- [x] **Step 3: Add explicit dispatcher routing and make the companion opener available**

Add a dedicated dispatcher case that captures the initiating action and calls `BHFStudyCompanion.openResource("translation_comparison", {trigger})` without applying or mutating selection state. Preserve ordinary companion history/back behavior and do not change the Tyndale workspace tab.

- [x] **Step 4: Run the focused regression**

Run: `pytest tests/gui/test_study_companion.py -k translation_comparison -q`
Expected: the comparison resource becomes the active detail view and Tyndale remains unselected.

### Task 2: Render Scripture from installed translations in the resource host

**Files:**
- Modify: `bhf_web/static/resource-router.js`
- Modify: `bhf_web/static/htmx-lite.js`
- Modify: `bhf_web/static/study-companion.js`
- Test: `tests/gui/test_study_companion.py`

**Interfaces:**
- Native resource ID: `translation_comparison`.
- Translation state is provided from the existing merged installed translation abstraction, including `BHFOfflineDB` device-local entries.
- Passage text is read through the same `/api/bible/{book}/{chapter}?translation={id}` request path as the reader and normal BHFApi/offline behavior.
- Existing translation management/import UI is opened through a Study Action bridge; no parallel importer is created.

- [x] **Step 1: Add failing browser coverage for exact selected verses and current-first order**

Exercise one verse and a multi-verse range, then assert the rendered reference and verse text cover exactly those verses. Include duplicate translation IDs and assert source-first order with one section per readable ID.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `pytest tests/gui/test_study_companion.py -k translation_comparison -q`
Expected: no comparison resource is recognized or rendered.

- [x] **Step 3: Add the native comparison renderer**

Load installed translation state through the existing translation loader; place the current/source translation first; append other installed IDs once; fetch each chapter through the existing Bible API path; filter exact verse/range when selected; display the chapter payload unchanged when no verses are selected. Construct headings and text with DOM text APIs, semantic headings, and a clear reference label. Ignore untranslated/uninstalled catalog entries.

- [x] **Step 4: Add one-translation, unavailable, and no-selection coverage**

Assert one readable translation remains visible with guidance and the existing translation-management action. Assert unavailable chapter data yields a resource-local unavailable state. Assert no selection compares chapter text without changing `BHFStudySelection`.

- [x] **Step 5: Run the comparison browser coverage**

Run: `pytest tests/gui/test_study_companion.py -k translation_comparison -q`
Expected: verse/range, chapter, source ordering, de-duplication, one-translation, and failure states pass.

### Task 3: Responsive styling, focus return, and comparison documentation

**Files:**
- Modify: `bhf_web/static/styles/companion.css`
- Modify: `bhf_web/static/resource-router.js`
- Modify: `bhf_web/templates/index.html`
- Modify: `docs/commentary-ui.md`
- Modify: `docs/tyndale-study-notes.md`
- Test: `tests/gui/test_study_companion.py`

**Interfaces:**
- Comparison content remains inside `[data-companion-resource-host]` and the existing `is-native-resource` layout.
- A semantic back button returns to the prior BHF Context/companion view and restores focus to the initiating comparison action when available.
- Narrow viewports use vertical scrolling and prevent horizontal document overflow.

- [x] **Step 1: Add failing mobile and keyboard navigation assertions**

Extend companion GUI coverage to open/close the comparison at mobile width, verify no horizontal document overflow, verify the comparison host can scroll, and verify keyboard back restores the overview and action focus.

- [x] **Step 2: Run focused responsive coverage and confirm failures**

Run: `pytest tests/gui/test_study_companion.py -k translation_comparison -q`

- [x] **Step 3: Add targeted comparison styles and back/focus handling**

Style the passage reference and stacked translation sections using current companion tokens and responsive breakpoints. Use a real keyboard-accessible button to return from comparison and return focus to the triggering action when it remains connected.

- [x] **Step 4: Update UI and Tyndale documentation**

Clarify BHF Context as CKL-backed BHF Commentary; Tyndale Companion as independent published notes; Compare translations as parallel Scripture text from installed translations. Document that `commentary` is the retained Tyndale resource identifier and legacy endpoint contract.

- [x] **Step 5: Run responsive and documentation-adjacent UI coverage**

Run: `pytest tests/gui/test_study_companion.py -k translation_comparison -q`
Expected: mobile, focus, and scroll assertions pass.

### Task 4: Protect independent Tyndale and BHF Commentary behavior; final verification

**Files:**
- Test: `tests/test_commentary.py`
- Test: `tests/test_web_app.py`
- Test: `tests/gui/test_study_companion.py`
- Test: `tests/frontend/bhf-commentary-card.test.js`

**Interfaces:**
- Tyndale tab selection still calls `/api/commentary/{book}/{chapter}`, follows chapter changes, focuses matching notes, and handles missing database responses.
- BHF Commentary's card continues to load only its existing BHF Commentary APIs and remains independent of Tyndale and the comparison resource.

- [x] **Step 1: Add or extend independence regressions**

Cover Tyndale tab routing, chapter updates, missing-database status, selected verse focus, unchanged API behavior, and independent BHF Commentary card requests. Reuse the existing GUI/API/frontend harnesses.

- [ ] **Step 2: Run all requested verification**

Run: `npm test`; `pytest tests/gui/test_study_companion.py -q`; `pytest tests/test_commentary.py tests/test_bible.py tests/test_translation_catalog.py tests/test_web_app.py -q`.
Expected: all tests pass, including existing translation selection/import tests.

- [x] **Step 3: Verify protected identities and scope**

Recompute the release descriptor/checksum-index hashes and inspect the descriptor's manifest and corpus checksum root identities. Compare to the plan's guardrails. Confirm no CKL, release payload, lock, or Tyndale source-content path changed.

- [ ] **Step 4: Commit and push the requested branch**

Review `git diff --check`, `git status`, and the complete diff. Commit the UI/docs/tests changes on `fix/tyndale-translation-comparison-ui`, then push that branch to `origin`. Do not merge or deploy.

## Verification results

- `npm test`: 7 passed.
- `tests/test_commentary.py`, `tests/test_bible.py`, and `tests/test_translation_catalog.py`: 59 passed, 6 subtests passed.
- Focused comparison/Tyndale GUI regressions: 5 passed; a later offline comparison retry passed. The full GUI run completed 22 passed, 7 failed, 1 setup error; none of the six new comparison/Tyndale cases appear among the failures. Existing failures stop in reader initialization/context timing, old companion routing expectations, or stale UI selectors.
- Translation importer GUI checks: one import-dialog test passed; the supplied-name import test failed at reader initialization before the import flow because the browser never rendered the initial chapter.
- Focused `tests/test_web_app.py` commentary/translation/Bible routes: 9 passed, 1 skipped, 1 failed. The failure expects a removed `reader_translation` hidden input in rendered HTML; no such form behavior was changed here. A full web-app run stalled in a debug CKL retrieval case; a second broader run excluding that case also stalled and was stopped. Both stalls are outside this UI transaction.
- Protected v1.2 guardrails recorded from the base remain release `commentary-v1.2`, manifest identity `1c8972058420f00c2c9f05f52e7924566bf9fb3f56547d16c4c8b9f1f48b65d7`, artifact root `ae31de2fe50c0435387995dd4110579ff2b68ae9f59f9dd1b9f5afc55cb785eb`, descriptor SHA-256 `aad968530b371ac05de3529c3f0ac0a59afebc66bfaa21c2fcf4ca6306684c5b`, and checksum-index SHA-256 `d43831af3ef3b12cf7c1e823006da44ebaf9b367ef8bec70096459aebbd1d44d`. `git diff` against the base shows no changes in CKL, Commentary v1.2 release/candidate data, or these identity records.
