# BHF UI-03 Narrative Explorer Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Narrative Explorer's stacked evidence inventory with a passage-first overview, focused category views, and clearer verified connection trails.

**Architecture:** Keep the current read-only projection and resource host. Render the overview or one focused category from the same in-memory projection; persist a bounded `{kind, categoryId}` view in Companion history beside the existing bounded relationship trail. Reuse existing evidence, source, route, reader navigation, and disclosure contracts.

**Tech Stack:** Existing browser JavaScript, CSS custom properties, native SVG/HTML controls, Node's built-in test runner, Python pytest, and the repository's Selenium GUI tests when a browser driver is available.

**Spec:** `docs/superpowers/specs/2026-10-30-bhf-narrative-explorer-ui-03-design.md`

## Global Constraints

- Keep the current passage projection API and schema unchanged; the initial view must not add a request or enlarge its payload.
- Keep CKL objects, NE-9C curations, NE-10 passage bridges, evidence, sources, manifests, fingerprints, and scholarly records unchanged.
- Display counts only when the corresponding query completed; distinguish partial, unknown, and completed empty coverage.
- Preserve authored CKL relationships, CKL-documented passage bridges, and interpretive connections as separate provenance classes.
- Preserve the 3-hop relationship limit, 12-node bounded trail, 12-entry connection/evidence paging rules, direction, reciprocal checks, cycle protection, source IDs, review state, and history semantics.
- Preserve exact evidence IDs, passage anchors, source provenance, confidence, uncertainty, dispute and human-review disclosures, and the distinction between physical and conceptual geography.
- Keep Tyndale Study Notes, Ask BHF, Bible navigation/comparison, notes, highlights, saved studies, maps, archaeology, feature gates, packaging, and retired Commentary HTTP 410 behavior intact.
- Use existing BHF CSS variables and browser primitives; add no frontend dependency, API route, deployment change, generated data, or interpretation.
- Work on `feat/bhf-narrative-explorer-ux-ui-03`, commit logical tasks, push the branch, and do not create a PR, merge, or deploy.

## Review Focus

- A restored history entry with an unknown, malformed, or oversized category ID must fall back to the overview and preserve the valid passage/trail — Task 1 tests the known and invalid `narrativeView` cases.
- A category whose retrieval is partial, unknown, or offline must not appear empty or show an unsupported zero count — Task 2 tests complete, partial, unknown, and unavailable states.
- A draft/in-review evidence item with missing bibliographic metadata must disclose its actual review state and source IDs without implying approval or fabricating a source — Task 2 tests an expanded evidence disclosure.
- A one-way passage bridge or relationship edge must preserve its recorded direction and must not gain a reverse navigation control — Task 3 tests one-way focused route rendering alongside the existing reciprocal/cycle tests.
- Cosmic/symbolic geography carrying a map-like navigation field must not become a physical map action or display generated coordinates — Task 3 retains and exercises the current cosmic map-trap regression case in the focused view.

---

## File Structure

- `bhf_web/static/narrative-explorer.js`: landing cards, focused category/connection views, reader-facing copy, evidence disclosures, and trail progression.
- `bhf_web/static/styles/companion.css`: visual hierarchy, two-column desktop and one-column mobile cards, focus styles, touch targets, disclosure spacing, and text wrapping.
- `bhf_web/static/resource-router.js`: active view state and rendering from the existing projection, with category selection and back callbacks.
- `bhf_web/static/study-companion.js`: include/restore Narrative Explorer view state in existing Companion snapshots and map UI actions onto existing history.
- `bhf_web/static/companion-history.js`: validate and bound the allowlisted Narrative Explorer view state; do not change trail limits or node types.
- `tests/frontend/companion-history.test.js`, `tests/frontend/resource-router.test.js`, `tests/frontend/narrative-explorer.test.js`, `tests/frontend/study-companion-context.test.js`: test view serialization, focused rendering, navigation, and context preservation.
- `tests/gui/ne11d1/` and relevant reader GUI tests: exercise the integrated desktop/mobile journeys if Chrome/WebDriver is available; capture before/after screenshots when browser support permits.
- `docs/narrative-explorer/ui03/`: record reader journey, accessibility, offline, screenshot, and matched performance results after implementation.

## Task 1: Preserve focused view state in Companion history

**Files:**
- Create: `docs/superpowers/specs/2026-10-30-bhf-narrative-explorer-ui-03-design.md`
- Create: `docs/superpowers/plans/2026-10-30-bhf-narrative-explorer-ui-03.md`
- Modify: `bhf_web/static/companion-history.js`
- Modify: `bhf_web/static/study-companion.js`
- Modify: `bhf_web/static/resource-router.js`
- Test: `tests/frontend/companion-history.test.js`
- Test: `tests/frontend/resource-router.test.js`
- Test: `tests/frontend/study-companion-context.test.js`

**Interfaces:**
- Produces `narrativeView: {kind: "overview"}` or `{kind: "category", categoryId: string}` in a Companion history snapshot. `categoryId` is restricted to the six existing section IDs. Invalid values normalize to `{kind: "overview"}`.
- Produces resource-router `getNarrativeView()` and accepts `{view}` in `open("narrative_explorer", options)`; category changes notify `onNarrativeViewChange(view, {push})` without reopening or refetching the projection.
- `study-companion.js` maps the normalized view to/from snapshots and sends category Back through the existing Companion history controller.

- [x] **Step 1: Write failing history, router, and Companion snapshot tests.** Add `testNarrativeExplorerHistoryPreservesKnownViewAndFallsBackForInvalidCategory` to round-trip the themes category and reject an unknown ID, oversized ID, and malformed view. Add `testNarrativeExplorerBackAndForwardRestoreFocusedCategoryAndTrail` to push overview/category/evidence snapshots and assert Back/Forward restores the category together with the exact trail. Add `testNarrativeExplorerRouterRestoresFocusedCategoryFromViewOption` to open with a valid category, assert that render options and `getNarrativeView()` contain it, and assert only the passage's existing session load occurred. Add `testNarrativeExplorerViewIsIncludedInCompanionHistorySnapshot` to assert study-companion snapshots carry the router's normalized category view.
- [x] **Step 2: Run the targeted tests and confirm they fail.**

  Run: `node --test tests/frontend/companion-history.test.js tests/frontend/resource-router.test.js`

  Expected: FAIL because Companion history drops `narrativeView` and the resource router does not expose view state.
- [x] **Step 3: Implement the bounded view contract.** Normalize a plain allowlisted view object in `companion-history.js`; keep all existing trail node validation unchanged. Initialize and expose view state in the resource router, pass it to `renderOverview`, and notify the Companion only when a view changes. Include the view in `historySnapshot()` and pass it through `applyHistoryState()`/`openResource()`.
- [x] **Step 4: Run the focused tests.**

  Run: `node --test tests/frontend/companion-history.test.js tests/frontend/resource-router.test.js tests/frontend/study-companion-context.test.js`

  Expected: PASS, including the existing trail bounds and exact passage/translation/verse restoration tests.
- [x] **Step 5: Commit the approved design artifacts and history contract together.**

  Commit message: `feat: preserve Narrative Explorer focused view history`

## Task 2: Build the discovery overview and focused categories

**Files:**
- Modify: `bhf_web/static/narrative-explorer.js`
- Modify: `bhf_web/static/resource-router.js`
- Modify: `bhf_web/static/styles/companion.css`
- Test: `tests/frontend/narrative-explorer.test.js`
- Test: `tests/frontend/resource-router.test.js`

**Interfaces:**
- Consumes Task 1's `view` and `onNarrativeViewChange` interfaces.
- `renderOverview(projection, options)` renders the overview for `{kind: "overview"}` and one focused category for `{kind: "category", categoryId}`. It calls `onOpenCategory(categoryId, trigger)` and `onBackToOverview(trigger)` for local view controls; it continues to use existing `onInspect`, `onOpenPassage`, `onNavigate`, and trail callbacks for evidence and destination navigation.
- The six category IDs remain `biblical_narrative`, `archaeology_ancient_history`, `biblical_geography`, `divine_council_cosmic_geography`, `themes_biblical_connections`, and `people_events_relationships`.

- [x] **Step 1: Write failing renderer tests.** Add `testOverviewShowsSixConciseCategoryCardsAndNoEvidenceInventory`, asserting the passage header, six labelled cards, a prominent Follow a Connection entry, and no evidence-item articles in the initial view. Add `testFocusedCategoryShowsOnlySelectedCategoryAndTwoPreviews`, asserting one selected category, at most two preview records, and a Browse records action. Add `testUnknownAndPartialCategoryCoverageDoNotShowZeroCount`, asserting distinct unknown/partial status with no invented count. Add `testConnectionEntryOpensThemeCategoryWithRecordedPassageRoutes`, asserting that the theme category retains authored/bridge labels and exact destinations. Add `testNarrativeCategoryNavigationReusesPassageProjectionAndHistory` in `resource-router.test.js`, asserting category selection pushes one view snapshot, opens no second projection session, and Back restores the overview.
- [x] **Step 2: Run the targeted renderer/router tests and confirm they fail.**

  Run: `node --test tests/frontend/narrative-explorer.test.js tests/frontend/resource-router.test.js`

  Expected: FAIL because the default renderer currently appends connection routes and all six evidence panels instead of a landing screen.
- [x] **Step 3: Implement the concise overview.** Add decorative inline SVG icons with `aria-hidden="true"` and no dependency. Keep the passage identity and short explanation. Render the Follow a Connection entry with availability/counts derived from `related_passages` state. Render all six topic cards with short plain-English descriptions, `normalizeState(section.state)`, and counts only for completed queries. Do not attach record lists to overview cards.
- [x] **Step 4: Implement focused category rendering.** Render a focused header, selected passage, Back and Return to Passage controls, one or two available previews, and the existing paginated record list. For the themes category, place related passage routes before evidence records; retain separate authored CKL and CKL-documented bridge groups and their expanded provenance. Keep the current exact destination validator and relationship callbacks.
- [x] **Step 5: Reconcile existing tests with the new view boundary.** Move assertions that inspect complete related passage routes or stacked panels to the focused themes/category renderer. Keep tests for projection semantics, source provenance, draft status, map restrictions, connection labels, cycle protection, and page limits intact. Do not weaken assertions to text-only checks when a navigation callback or exact identifier is available.
- [x] **Step 6: Run targeted frontend tests.**

  Run: `node --test tests/frontend/narrative-explorer.test.js tests/frontend/resource-router.test.js tests/frontend/study-companion-context.test.js`

  Expected: PASS with six overview choices, no initial evidence inventory, focused evidence browsing, and unchanged exact passage navigation.
- [x] **Step 7: Commit.**

  Commit message: `feat: add focused Narrative Explorer discovery views`

## Task 3: Clarify trails, evidence disclosure, and responsive behavior

**Files:**
- Modify: `bhf_web/static/narrative-explorer.js`
- Modify: `bhf_web/static/styles/companion.css`
- Modify: relevant tests in `tests/frontend/narrative-explorer.test.js`, `tests/frontend/study-companion-context.test.js`, and `tests/gui/ne11d1/`
- Create: `docs/narrative-explorer/ui03/01-reader-acceptance.md`
- Create: `docs/narrative-explorer/ui03/02-performance-and-visual-results.md`

**Interfaces:**
- Consumes Task 2's category and connection view IDs and Task 1's history round-trip.
- Trail semantics and limits remain the existing `createTrail`, `followEvidence`, `followSubject`, `followPassage`, `returnToOrigin`, and Companion history contract; no new relationship kind or hop is introduced for a category view.

- [x] **Step 1: Write failing trail/detail/accessibility regressions.** Add `testTrailHeaderShowsReadableProgressionWithoutChangingRecordedDirection` asserting origin, connection basis, destination, hop count, the original one-way status, and an accessible visual step sequence. Add `testFocusedDraftEvidenceKeepsReviewAndMissingSourceDisclosure` asserting that draft/in-review/human-review fields are inside a native disclosure, remain available when expanded, and do not synthesize a source title or approval. Update the existing cosmic map-trap regression to render the focused geography category and assert that the item still exposes no physical map action or coordinates. Add `testReturnToPassageRestoresOriginalSelectionAndOverview` to assert that Return to Passage restores the origin selection and resets the view to overview; Task 1 owns the separate Back/Forward history test.
- [x] **Step 2: Run the focused tests and confirm they fail.**

  Run: `node --test tests/frontend/narrative-explorer.test.js tests/frontend/study-companion-context.test.js`

  Expected: the new trail-step assertion fails because the trail currently has no visual step markers, and the draft-disclosure assertion fails because governance metadata is currently always visible outside disclosures. Existing evidence, direction, and history contract tests pass.
- [x] **Step 3: Improve trail progression and navigation feedback.** Render breadcrumb steps as an ordered visual sequence with decorative arrows, an accessible current-step label, and a concise explanation of the connection used. Keep relationship direction, basis, category, source IDs, uncertainty, review state, cycle prevention, and depth information. Route Back through existing history and make Return to Passage reset to the original passage overview.
- [x] **Step 4: Organize evidence details progressively.** Keep the reader-safe claim and evidence classification visible. Group source/bibliography, original and applicable passage anchors, rationale, recorded relationship metadata, confidence/certainty, dispute, temporal, content, and human-review fields under labelled native disclosures where doing so does not hide an essential warning. Preserve all exact values and missing-field disclosures.
- [x] **Step 5: Refine responsive CSS and accessible states.** Use existing variables, consistent card radii/spacing, desktop two-column topic cards, mobile single-column cards, 44px controls, visible focus, text wrapping, non-color availability cues, and no horizontal overflow. Preserve the existing native Companion sheet and dock. Add/adjust live-region status for loading and category changes only if the current host announcement does not already cover them.
- [x] **Step 6: Update integrated GUI journeys and capture screenshots.** Exercise Genesis 1, Genesis 6, Exodus 3, Psalm 22–Mark 15, Jonah–Matthew, and limited/missing-coverage cases through open → category → evidence/connection → Back/Return. Verify source/review disclosure, one-way direction, passage selection/history, feature-disabled behavior, offline behavior, keyboard focus, and mobile layout. Save before/after desktop/mobile screenshots in the plan workspace, then copy only the final shareable screenshots and written results to the documented `docs/narrative-explorer/ui03/` results files. If no usable browser driver is available, run the available Firefox smoke/screenshot path and state which interactions could not be exercised in a real browser.
- [x] **Step 7: Compare performance against the UI-02 baseline.** Use the same passage requests and browser/instrumentation where available. Record request count, API response bytes, initial render duration, and DOM-node growth. Expected: no additional projection request and unchanged API payload; the first-screen DOM should omit full category inventories. Describe timing limits if the browser setup cannot provide a matched run.
- [x] **Step 8: Run final verification for this task.**

  Run: `npm test`

  Expected: all frontend test files pass.

  Run: `python3 -m pytest -q tests/test_narrative_explorer_projection.py tests/test_narrative_explorer_api.py tests/test_narrative_explorer_ui_config.py`

  Expected: all targeted projection/API/feature-gate tests pass without CKL or API changes.

  Run: `git diff --check`

  Expected: no whitespace errors.
- [x] **Step 9: Commit.**

  Commit message: `test: verify Narrative Explorer reader journeys and responsive states`

## Final branch checks

- [x] Review the full diff, all generated/screenshot artifacts, test output, and the clean status on the feature worktree.
- [x] Run the focused GUI suite and relevant reader tests; report browser-driver skips or pre-existing failures exactly.
- [x] Confirm preserved Tyndale, Ask BHF, Bible navigation/comparison, personal study, map/archaeology, feature-gate, API, and Commentary 410 behavior in the targeted regression tests.
- [ ] Push `feat/bhf-narrative-explorer-ux-ui-03` to `origin`; do not create a PR, merge, or deploy.
