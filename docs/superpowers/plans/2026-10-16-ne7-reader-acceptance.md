# NE-7 Reader Acceptance Plan

> **For agentic workers:** Execute directly in the isolated `test/narrative-explorer-ne7-reader-acceptance` worktree. Do not push, merge, deploy, change environment settings, or enable Narrative Explorer by default.

**Goal:** Establish a source-backed local reader acceptance decision for Narrative Explorer and its integration with existing BHF reader features.

**Architecture:** Treat the NE-6V/6R contracts and committed CKL records as authoritative. Exercise existing APIs, browser behavior, and regression suites; make only a minimal tested integration correction if a reproducible NE-7 regression is found. Record verified, pending, and blocked areas separately across the seven requested acceptance reports.

**Tech Stack:** Python/pytest, Node.js tests, FastAPI local runtime, Selenium with Firefox, Orca/AT-SPI if supported, SQLite read-only integrity checks, Git worktrees.

**Spec:** User-provided `BHF — NE-7: Final Reader Acceptance & Integration Hardening` request.

## Global Constraints

- Base the branch directly on verified `origin/master` `480141f9b19e627c3f1d59ee67ad6aa6562812bd`.
- Preserve the master deployment safeguard and the Narrative Explorer default-off behavior.
- Use `BHF_STUDY_DB_READ_ONLY=1` for protected study data; do not modify CKL or frozen Commentary data.
- Preserve existing source IDs, passage anchors, classifications, uncertainty, and authored edge direction.
- Do not issue paid AI provider requests or generate evidence.
- Do not push, merge, deploy, or change Vercel environment variables.

## Review Focus

- Missing versus incomplete evidence: verify all four coverage states and avoid treating empty results as negative conclusions.
- Relationship identity and direction: verify parent-qualified IDs, authored one-way links, cycles, and traversal limits.
- Physical identification: verify uncertain points and conceptual geography cannot be selected or rendered as literal coordinates.
- Reader state: verify passage, range, translation, focus, Companion, map focus, and history survive navigation and retries.
- External test limits: distinguish local browser/read-only checks from hosted runtime and actual spoken AT acceptance.

---

### Task 1: Baseline and inherited contracts

**Files:** Read `AGENTS.md`, the NE-1 through NE-6R3 implementation/acceptance documents, `vercel.json`, and relevant configuration. Create this plan in `docs/superpowers/plans/`.

- [x] Confirm clean branch/worktree ancestry and deployment safeguard.
- [x] Record inherited CKL, study DB, Commentary, and coverage fingerprints where files are available.
- [x] Map current test commands and runtime dependencies without modifying source data.

### Task 2: Automated API, source, reader, and frontend acceptance

**Files:** Existing `tests/test_narrative_explorer_*.py`, `tests/test_ne6_geography_selenium.py`, `tests/test_web_app.py`, reader/Maps/Commentary/Tyndale/translation/SQLite tests, and `tests/frontend/*.test.js`.

- [x] Run focused projection/API/coverage/trail/geography and source-parity tests.
- [x] Run relevant reader, Maps, Commentary, Tyndale, translation, offline, and read-only DB tests.
- [x] Record every failure against the unmodified baseline and classify it using the NE-6R3 findings.

### Task 3: Live browser, accessibility, mobile, and recovery review

**Files:** Existing app runtime, Firefox Selenium suite, Service Worker/frontend tests; no CKL fixture mutations.

- [x] Start the supported local app against read-only protected study data and use disposable data for any required writes.
- [x] Exercise passage-first Explorer, authored evidence/trails, Maps, return-to-origin, and ordinary reader controls for all specified pilots; record the separate general Firefox smoke discrepancy.
- [x] Measure actual viewport dimensions, keyboard/focus behavior, request/retry behavior, and local cold/warm timing.
- [x] Attempt actual Orca/Firefox spoken review; no desktop/speech session was available, so record conditions and a manual follow-up script.

### Task 4: Narrow integration correction, only if justified

**Files:** Only the directly implicated UI/API/test files and a focused regression test.

- [x] Reproduce the general Firefox browser/API discrepancy; distinguish it from the test helper's no-selection Maps setup.
- [x] Make only test-fixture corrections for retired interfaces and current Maps navigation; no product correction was justified. Re-run the affected web-app and Firefox checks and record the remaining failure.
- [ ] Do not alter evidence rules, CKL, Commentary artifacts, licenses, deployment configuration, or unrelated architecture.

### Task 5: Acceptance record and local commit

**Files:**
- Create `docs/narrative-explorer/ne7/01-end-to-end-reader-acceptance.md`
- Create `docs/narrative-explorer/ne7/02-hermeneutical-and-source-parity.md`
- Create `docs/narrative-explorer/ne7/03-maps-and-evidence-trail-integration.md`
- Create `docs/narrative-explorer/ne7/04-commentary-tyndale-translations.md`
- Create `docs/narrative-explorer/ne7/05-accessibility-mobile-offline.md`
- Create `docs/narrative-explorer/ne7/06-performance-and-regressions.md`
- Create `docs/narrative-explorer/ne7/07-release-readiness.md`

- [x] Include exact commands, results, limitations, fingerprints, state mutation check, and independent category decisions.
- [x] Reconfirm the deployment safeguard and default-off feature state.
- [x] Commit locally on the requested branch and report SHA/worktree state; do not push.
