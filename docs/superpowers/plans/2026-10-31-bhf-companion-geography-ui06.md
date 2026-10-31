# BHF UI-06 Companion Geography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove redundant Companion discovery previews and add one passage-scoped Places & Locations resource.

**Architecture:** Add `places_locations` to the existing native resource router and render a composite view from the selected Companion context. Reuse the existing paged location API and location, canonical, and Walk the Land actions; leave persisted `places` and all research records unchanged.

**Tech Stack:** Jinja template, browser JavaScript, CSS, Node's built-in test runner, pytest, Selenium Firefox.

**Spec:** [2026-10-31-bhf-companion-geography-ui06-design.md](../specs/2026-10-31-bhf-companion-geography-ui06-design.md)

## Global Constraints

- Keep CKL JSON objects, source identities, evidence, source locks, schema, manifests, curations, and provenance unchanged.
- Do not change the persisted `places` resource contract.
- Keep Narrative Explorer's discovery and evidence experience and verified relationship navigation intact.
- Keep Tyndale source data, attribution, and licensing intact.
- Do not add a second geography retrieval pipeline or mandatory overview API calls.
- Preserve Ask BHF, personal study, Narrative Explorer, and retired Commentary HTTP 410 behavior.
- Run the full frontend suite, relevant Python and GUI tests, CKL integrity checks, and `git diff --check`.
- Test desktop browser flows and 390 px mobile layouts; capture before/after browser screenshots.
- Commit in focused groups, push the requested branch, and stop before PR, merge, or deployment.

## Review Focus

- A canonical place sharing a name with a Maps entry must stay a distinct source identity; test exact IDs and distinct IDs with the same title in the composite renderer.
- A CKL location already listed by exact CKL ID must not be repeated in Biblical Places; test exact identity de-duplication.
- A delayed location page must not append after the selected chapter changes; test aborted pagination and the browser chapter transition.
- Did You Know-only evidence must not trigger projection requests, while Walk the Land's verified relationship actions remain available; test projection eligibility and route handoff.
- Offline or partial context must keep available locations usable and expose a clear status without claiming unavailable classifications; test offline pagination and uncertainty disclosures.

## File Map

- `bhf_web/templates/index.html` — add the Places & Locations entry and remove overview-only redundant sections.
- `bhf_web/static/resource-router.js` — register and render the new native passage resource.
- `bhf_web/static/companion-places-locations.js` — compose resource status, Locations, Biblical Places, and Walk the Land sections from existing context data.
- `bhf_web/static/companion-locations.js` — retain paging/actions and expose source identity, provenance, uncertainty, and explicit empty state.
- `bhf_web/static/companion-discoveries.js` — retain Walk the Land rendering and remove Did You Know rendering and map-ID suppression.
- `bhf_web/static/study-companion.js` — route the new entry, stop overview discovery/location/entity rendering, avoid duplicate Places recommendations, and limit projections to Walk the Land.
- `bhf_web/static/styles/companion.css` — style the focused view and paired entry cards responsively.
- `tests/frontend/*.test.js` — cover resource composition, current resource contract, states, overview cleanup, projection requests, and route behavior.
- `tests/test_web_ui_selenium.py` — cover the focused UI-06 flow, mobile sheet, exact Narrative Explorer handoff, and unaffected Tyndale/Ask BHF flows.
- `docs/ui-modernization/ui06/` — record the short UX report and browser screenshots.

## Tasks

### Task 1: Add and route the composite Places & Locations resource

**Files:**
- Create: `bhf_web/static/companion-places-locations.js`
- Modify: `bhf_web/static/resource-router.js`
- Modify: `bhf_web/static/companion-locations.js`
- Modify: `bhf_web/templates/index.html` (script registration)
- Test: `tests/frontend/companion-places-locations.test.js`
- Test: `tests/frontend/resource-router.test.js`
- Test: `tests/frontend/companion-locations.test.js`

- [x] Write tests for exact CKL-vs-Maps identity rules, CKL-only canonical actions, empty/partial/offline messages, and the selected context without a second initial request.
- [x] Implement the composite view and router dispatch; reuse `BHFCompanionLocations.render`, loaded context, and existing resource callbacks.
- [x] Add Maps/CKL identities and provenance, source-lock, review, confidence, license, and uncertainty disclosures; only supported Maps identities receive map actions.
- [x] Cover the unchanged `places` contract and CKL duplicates arriving on later pages.
- [x] Commit as `feat: add passage-scoped companion geography view`.

### Task 2: Clean the overview and retain Walk the Land navigation

**Files:**
- Modify: `bhf_web/templates/index.html`
- Modify: `bhf_web/static/study-companion.js`
- Modify: `bhf_web/static/companion-discoveries.js`
- Modify: `bhf_web/static/styles/companion.css`
- Test: `tests/frontend/study-companion-layout.test.js`
- Test: `tests/frontend/companion-discoveries.test.js`
- Test: `tests/frontend/study-companion-context.test.js`

- [x] Assert one Places & Locations entry, no redundant discovery/geography/entity previews, and the existing Explore the Narrative gate.
- [x] Cover no Did You Know projection requests, separate Walk the Land rendering, and exact verified Narrative Explorer handoff.
- [x] Add the required card copy, filter duplicate Places recommendations, remove overview render dependencies, and keep Walk the Land in the focused resource.
- [x] Limit verified projections to Walk the Land evidence while retaining Narrative Explorer relationship behavior.
- [x] Add responsive styles and pass the full frontend suite.
- [x] Commit as `feat: simplify companion geography discovery entry`.

### Task 3: Add browser regressions and capture the UX change

**Files:**
- Modify: `tests/gui/test_companion_locations.py`
- Create or modify: `tests/gui/test_ui06_companion_geography.py`
- Create: `docs/ui-modernization/ui06/`

- [x] Cover selected chapter/verse scope, exact Maps focus, CKL detail navigation, pagination, Walk the Land actions, and history behavior across frontend and browser regressions.
- [x] Cover 390 px mobile overflow/focus/back behavior and stale chapter responses across browser and frontend regressions.
- [x] Capture the baseline overview and updated desktop overview, focused view, and 390 px view.
- [x] Run focused headless Firefox regressions for UI-06, Tyndale, Ask BHF, and Narrative Explorer handoff; inspect the screenshots.
- [x] Write the before/after report at `docs/ui-modernization/ui06/ux-change-report.md`.
- [x] Commit as `test: cover UI-06 companion geography flows`.

### Task 4: Verify and deliver

**Files:**
- Review all branch changes.

- [x] Run `npm test`.
- [x] Run relevant Python tests for Companion context, location rendering contracts, and web routes.
- [x] Run CKL inventory and validation checks; confirm no CKL artifacts changed.
- [x] Run focused Firefox UI regressions for UI-06, Tyndale, Ask BHF, and Narrative Explorer handoff.
- [x] Run `git diff --check`; inspect the diff, generated-file status, screenshots, commits, and worktree.
- [x] Push `feat/bhf-companion-geography-ui06`; stop before PR, merge, or deployment.

The complete `tests/test_web_app.py` run was attempted but stopped after more than 100 seconds in the unrelated canonical-editor placeholder-object test. The two relevant web-asset/offline tests passed separately.
