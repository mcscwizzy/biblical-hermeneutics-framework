# BHF UI-07 Implementation Plan

**Base:** `origin/master` at `694fa18345135cad8c9a5dbd9d3a0105ba618411`
**Branch:** `feat/bhf-ui07-reader-first-research`
**Design:** [UI-07 design](../specs/2026-10-31-bhf-study-companion-ui07-design.md)

## Files and responsibilities

- `bhf_web/templates/index.html` — keep passage overview concise; isolate the
  separate Explore BHF catalog and add the feature-disabled fallback.
- `bhf_web/static/study-companion.js` — render Explore BHF catalog only in
  browse mode and refresh contextual research from the existing context cache.
- `bhf_web/static/narrative-explorer.js` — add Understand the Passage and
  Browse research sources entries to the Explorer overview.
- `bhf_web/static/resource-router.js` — focused contextual topic and research
  source views, empty/error states, and secondary navigation without opening a
  second projection session.
- `bhf_web/static/companion-history.js` — serialize allowlisted contextual
  topics for the direct fallback and Narrative Explorer view.
- `bhf_web/static/styles/companion.css` — restrained two-choice overview,
  compact topic selector, focus states, and responsive layouts.
- `tests/frontend/` — regression tests for overview contents, view state,
  history, status distinctions, and projection request reuse.
- `tests/test_narrative_explorer_ui_config.py` and the UI-07 cases under
  `tests/gui/` — feature-gate and real-browser flows.
- `docs/ui-modernization/ui07/` — browser captures and brief UX results.

## Test-first tasks

1. Add failing frontend assertions for the overview inventory removal, exactly
   two primary choices, separate Explore BHF catalog, contextual entry,
   secondary source routes, and feature-disabled fallback. Run the focused Node
   tests and confirm the intended failures.
2. Add failing Narrative Explorer and Companion history tests for the
   Understand the Passage entry, topic state allowlist, and secondary source
   view. Confirm Back/Forward preserves topic state.
3. Add failing resource-router tests for the five context topics, recorded
   support/source disclosures, completed-empty vs missing-summary vs unknown
   vs offline status, context selection keys, and no additional projection
   request when opening/switching focused views.
4. Implement the minimum template, JavaScript, history, and CSS changes to
   satisfy those tests while preserving the existing APIs and session.
5. Add and run real-browser tests at desktop and exact 390 px Chrome widths for
   overview, topic switching, passage changes, history/Escape/return, source
   routes, Places & Locations, personal actions, Tyndale, Compare Translations,
   Word Study, Ask BHF, feature-disabled fallback, and offline behavior. Capture
   before/after screenshots.
6. Run `npm test`, the relevant Python and GUI suites, framework validation,
   CKL integrity validation, and `git diff --check`. Review protected file
   boundaries, the complete diff, generated files, and worktree state.
7. Commit and push the requested branch. Do not create a PR, merge, or deploy.
