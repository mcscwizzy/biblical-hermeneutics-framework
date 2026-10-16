# Narrative Explorer NE-6 Geography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate source-grounded physical geography and distinct cosmic-geography presentation with verified map selection and preserved NE-5C navigation.

**Architecture:** Extend the existing read-only Narrative Explorer projection, Companion resource routing, and MapPanel controller lifecycle. Keep Explorer-only explicit-reference retrieval, strict displayability, existing exact source-specific conceptual classification, and current history/trail behavior. Add no evidence or map data.

**Tech Stack:** Python projection/services and pytest; existing browser JavaScript and Node test runner; FastAPI; Firefox/Selenium; existing SQLite study database opened read-only.

**Spec:** `docs/superpowers/specs/2026-10-15-narrative-explorer-ne6-geography-design.md` and normative `docs/narrative-explorer/ne6/01-geography-interaction-contract.md`.

## Global Constraints

- Preserve the projection gates for physical geography and coordinate/geometry displayability.
- Keep place identification separate from coordinate/catalog confidence; do not geocode or infer missing source metadata.
- Keep cosmic classification source-specific and authored; no title/description keyword heuristics, doctrinal conclusions, or heavenly map.
- Preserve NE-A2's additive explicit-reference retrieval for Explorer only; do not broaden the global Maps resolver.
- A focus acknowledgment is selected only after exact requested item identity is selected by current MapPanel lifecycle.
- Preserve stable IDs, edge direction/labels, provenance, the three-hop limit, history, origin selection/translation, and Ask BHF behavior.
- Keep feature flag default OFF; no eager map API/layer requests, new cache, CKL/database/schema/deployment changes, or model calls.
- Use the valid existing study DB strictly read-only via `BHF_STUDY_DB_PATH`.

## Review Focus

- Explicitly linked Explorer item absent from legacy Maps results: must return a truthful non-selected result without changing global resolver semantics (Task 2 tests).
- Offline/cache stale state versus loaded item absence: status must distinguish unavailable from not found (Task 2 tests).
- Invalid coordinates, unidentified place, and dispute: source metadata remains, map coordinates/geometry remain hidden (Task 1 tests).
- Exact cosmic source record with wrong evidence type or no applicable authored relation: receives no cosmic role (Task 1 tests).
- Browser Back/Forward, return-to-origin translation/selection, focus restoration, and mobile overflow after failed map selection (Task 3 tests).

---

### Task 1: Preserve geography safety and expose authored cosmic roles

**Files:**
- Modify: `bhf_agent/presentation/narrative_explorer.py`
- Test: `tests/test_narrative_explorer_projection.py`
- Test: `tests/test_narrative_explorer_api.py`

**Interfaces:**
- Consumes: existing `ProjectedItem`, `_SPECIALIZED_EVIDENCE_RULES`, `validate_projection`, and read-only API projection.
- Produces: optional serialized authored `cosmic_geography_role` for records passing the same identity/evidence-type/anchor relation gates; no change to existing geography displayability field names or meanings.

- [ ] **Step 1: Write failing tests** for exact allowed roles and negative classification (wrong type/no direct or comparative applicable anchor), plus physical place fields and suppression of displayability for unidentified/disputed/invalid coordinate records.
- [ ] **Step 2: Run tests to verify failure.** Run `python -m pytest tests/test_narrative_explorer_projection.py tests/test_narrative_explorer_api.py -q`. Expected: new role/field contract assertions fail; existing contracts pass.
- [ ] **Step 3: Implement minimal projection changes** in `bhf_agent/presentation/narrative_explorer.py`, reusing exact source-specific classification gates and current physical safety functions.
- [ ] **Step 4: Run focused tests.** Expected: projection and API tests pass without CKL or database edits.
- [ ] **Step 5: Commit** `feat: project safe geography and authored cosmic roles`.

### Task 2: Acknowledge actual Maps focus selection

**Files:**
- Modify: `bhf_web/static/maps/MapPanel.js`
- Create: `bhf_web/static/maps/MapFocusAcknowledgment.js`
- Modify: `bhf_web/static/maps/BibleMap.js`
- Modify: `bhf_web/static/study-companion.js`
- Modify: `bhf_web/static/companion-discoveries.js`, `bhf_web/static/sw.js`
- Modify as needed: existing map action bridge in `bhf_web/static/resource-router.js` / `bhf_web/static/htmx-lite.js`
- Test: `tests/frontend/map-focus-acknowledgment.test.js`, `tests/frontend/study-companion-context.test.js`, `tests/frontend/companion-discoveries.test.js`, `tests/frontend/narrative-explorer-sw.test.js`; focused `tests/test_web_app.py` asset/map tests; explicit-reference API/map matching tests.

**Interfaces:**
- Consumes: `openMapPanel(context)`, `applyRequestedMapFocus(context)`, existing pending MapPanel context/action lifecycle, Companion `openResource("maps", options)`.
- Produces: optional acknowledgment `{status, requestedKind, requestedId, selectedKind, selectedId, reason}` where status is exactly `selected|not_found|unsupported|unavailable|failed`; legacy calls without an acknowledgment request retain current return behavior.

- [ ] **Step 1: Write failing tests** for exact identity selection, missing target after successful map load, unsupported request kind, data unavailable/offline, lookup/controller failure, and legacy no-ack call behavior. Verify Explorer explicit-reference retrieval remains enabled while global Maps default stays unchanged.
- [ ] **Step 2: Run tests to verify failure.** Run the focused Node frontend suites and targeted pytest cases for `WebAssetTests.test_map_focus_acknowledgment_module_is_in_the_offline_static_shell`, map panel opening, service worker assets, Narrative Explorer explicit links, and the Acts 7 legacy map resolver. Expected: ack propagation and missing offline module cases fail before implementation.
- [ ] **Step 3: Implement a narrow acknowledgment path** through MapPanel's current load/controller lifecycle and Companion return path; preserve queued/pending open behavior and add accurate general Maps fallback for non-selected status.
- [ ] **Step 4: Run focused tests.** Expected: all new outcome statuses and legacy compatibility pass; no global resolver change. The broader `tests/test_web_app.py` file contains unrelated stale assertions; record those failures separately and use the targeted MapPanel/PWA contract tests for this task.
- [ ] **Step 5: Commit** `feat: acknowledge narrative explorer map focus`.

### Task 3: Present physical and conceptual geography in Explorer

**Files:**
- Modify: `bhf_web/static/narrative-explorer.js`
- Modify as needed: `bhf_web/static/resource-router.js`, Companion styles and shared CSS
- Test: `tests/frontend/narrative-explorer.test.js`, `tests/frontend/companion-history.test.js`, `tests/frontend/study-companion-context.test.js`

**Interfaces:**
- Consumes: projection fields and `cosmic_geography_role` from Task 1; Map focus acknowledgment from Task 2; existing source/connection objects and resource router.
- Produces: physical detail and uncertainty presentation; conceptual cosmic sections labeled only from role metadata; supported trail actions and truthful map fallback, without changing trail IDs/history semantics.

- [ ] **Step 1: Write failing DOM/frontend tests** for physical source details and hidden coordinates, distinct sacred-space/comparative/disputed labels, source provenance, relation labels/direction, available map fallback, return-origin translation/selection, three-hop cap, and feature-flag OFF/no eager requests.
- [ ] **Step 2: Run focused frontend tests to verify failure.** Run `node --test tests/frontend/narrative-explorer.test.js tests/frontend/companion-history.test.js tests/frontend/study-companion-context.test.js`. Expected: new presentation and fallback cases fail; existing trail contracts pass.
- [ ] **Step 3: Implement the views and actions** using text-only, source-backed authored values, preserving status distinctions and current routing/history behavior.
- [ ] **Step 4: Run focused frontend tests.** Expected: all presentation, navigation, and no-eager-request tests pass.
- [ ] **Step 5: Commit** `feat: present physical and cosmic geography evidence`.

### Task 4: Document pilots, provenance, coverage, and integration limits

**Files:**
- Create: `docs/narrative-explorer/ne6/02-physical-identification-safety.md`
- Create: `docs/narrative-explorer/ne6/03-cosmic-geography-presentation.md`
- Create: `docs/narrative-explorer/ne6/04-map-focus-and-database-validation.md`
- Test/update evidence fixtures only in tests if strictly synthetic; do not modify CKL.

**Interfaces:**
- Consumes: implementation and existing NE-A1/A2/5C audit evidence.
- Produces: pilot-specific observed outcomes and source/taxonomy gaps for future curation; no unsupported claims about all-chapter resolver coverage.

- [ ] **Step 1: Write/extend focused tests or fixture assertions** for Acts 7 `openbible-a012705`, Joshua 1 Negeb, Eden and Horeb/Sinai safeguards, Genesis 3/6, Deut 32, Psalm 82, identified point/route/unidentified/invalid-pair/conceptual-no-geometry controls.
- [ ] **Step 2: Run those tests to verify missing coverage.** Expected: identify only renderer/contract gaps; no CKL changes are made.
- [ ] **Step 3: Add the pilot reports** with exact source IDs, authored relation labels, identification uncertainty, map behavior, and remaining curation gaps; mark synthetic controls as test fixtures.
- [ ] **Step 4: Run targeted projection/API/map tests.** Expected: pilot assertions pass; evidence records and DB remain unchanged.
- [ ] **Step 5: Commit** `docs: record NE-6 geography pilot outcomes`.

### Task 5: Read-only DB and real Firefox/Selenium verification

**Files:**
- Modify: `tests/test_web_ui_selenium.py` or create a focused Selenium module that uses the existing `BHF_STUDY_DB_PATH` database read-only.
- Create: `docs/narrative-explorer/ne6/05-browser-accessibility-performance-results.md`
- Create: `docs/narrative-explorer/ne6/04-map-focus-and-database-validation.md` if not completed in Task 4.

**Interfaces:**
- Consumes: complete UI, API, map acknowledgment, approved existing DB path.
- Produces: reproducible desktop and mobile Firefox/Selenium outcomes, read-only DB integrity/query results, request/render measurements, accessibility semantics checks, unavailable assistive-technology gaps.

- [ ] **Step 1: Write failing real-browser cases** for dock/sheet, Maps open/close, selected and failed map focus, uncertainty rendering, trail navigation, Back/Forward, return origin selection/translation, keyboard focus, responsive overflow, semantic roles, offline retry, and no eager loading. Configure the actual DB through `BHF_STUDY_DB_PATH`; assert read-only access and no DB writes.
- [ ] **Step 2: Run browser/database tests to verify failure** against current implementation. Expected: unmet NE-6 interactions fail while browser and DB availability are confirmed.
- [ ] **Step 3: Implement only integration fixes revealed by tests**, if any, with focused regression tests first.
- [ ] **Step 4: Run required focused projection/API/frontend/map/archaeology/Companion suites, Firefox desktop+mobile suite, JS syntax checks, Python compilation, and `git diff --check`.** Expected: all relevant checks pass; unrelated baseline failures and unavailable AT checks are recorded separately.
- [ ] **Step 5: Commit** `test: verify NE-6 geography in Firefox and read-only database`.

## Final branch verification and delivery

- Re-read this plan, the approved contract, and the final diff; verify every pilot, prohibited file class, and requested outcome status.
- Confirm DB integrity/path before and after with read-only commands only.
- Run full intended tests once more with fresh output, report all failed/skipped/unavailable tests accurately, and do not call DOM semantics a screen-reader test.
- Confirm feature flag default OFF, clean worktree, branch ancestry, final commit SHA; push only `feat/narrative-explorer-ne6-geography`. Do not merge or deploy.
