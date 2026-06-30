# Safe Refactor Plan

This plan starts after Phase 2A, which extracted the reader-state database helpers from `bhf_agent/study_db.py` into `bhf_agent/db/`.

## Constraints

- No behavior changes.
- No UI redesign.
- No database schema changes unless absolutely required.
- Prefer extraction over rewrites.
- Keep phases small and reviewable.
- After each phase:
  - run compile/build/tests
  - fix import errors before moving on

## Current Status

Completed:

- Phase 1: inventory of oversized files and extraction targets
- Phase 2A: extracted reader-state database access from `bhf_agent/study_db.py`

Remaining high-value oversized files:

- `bhf_agent/study_db.py`
- `bhf_web/static/maps/MapPanel.js`
- `bhf_web/app.py`
- `bhf_web/static/htmx-lite.js`
- `bhf_web/static/style.css`
- `bhf_web/map_service.py`
- `bhf_web/static/maps/BibleMap.js`
- `bhf_agent/bible.py`
- `bhf_agent/runner.py`
- `bhf_agent/curation.py`

## Phase 2B: Backend Repository Extraction From `bhf_agent/study_db.py`

Goal:

- Continue shrinking `bhf_agent/study_db.py` without changing its public API.

Primary extraction targets:

- map catalog reads
- source lookups
- map note persistence
- archaeological and manuscript read helpers

Recommended modules:

- `bhf_agent/db/repositories/maps.py`
- `bhf_agent/db/repositories/sources.py`
- `bhf_agent/db/repositories/map_notes.py`
- `bhf_agent/db/repositories/archaeology.py`
- `bhf_agent/db/repositories/manuscripts.py`

Approach:

- Keep `bhf_agent/study_db.py` as a facade.
- Move SQL and row-to-dict mapping into repository modules.
- Share common validators and connection helpers through `bhf_agent/db/common.py` and `bhf_agent/db/connection.py`.
- Preserve function names in `study_db.py` and delegate internally.

Verification:

- `python3 -m py_compile bhf_agent/study_db.py bhf_agent/db/**/*.py`
- targeted unit tests covering notes/web/maps if present

Acceptance for 2B:

- `bhf_agent/study_db.py` is materially smaller.
- No route or import breakage.
- Existing tests still pass.

## Phase 2C: Backend Service Layer Split In `bhf_web/map_service.py`

Goal:

- Separate business logic from data retrieval and AI fallback orchestration.

Likely responsibilities to extract:

- curated place matching
- region-only / no-pin reasoning
- AI fallback prompt construction
- AI fallback result normalization
- map explanation text assembly

Recommended modules:

- `bhf_web/services/map_matching.py`
- `bhf_web/services/map_fallbacks.py`
- `bhf_web/services/map_explanations.py`
- `bhf_web/services/map_serializers.py`

Approach:

- Keep exported functions in `bhf_web/map_service.py` as compatibility wrappers at first.
- Move pure logic and transformation code first.
- Leave web handlers untouched in this phase.

Verification:

- existing map-related tests
- app-level tests hitting map endpoints if available

Acceptance:

- `bhf_web/map_service.py` drops below the current size materially.
- AI fallback and curated map behavior remain unchanged.

## Phase 2D: Backend Route Thinning In `bhf_web/app.py`

Goal:

- Reduce `bhf_web/app.py` by extracting route-adjacent helpers and keeping handlers thin.

Recommended structure:

- `bhf_web/routes/maps.py`
- `bhf_web/routes/study.py`
- `bhf_web/routes/search.py`
- `bhf_web/routes/reader.py`
- `bhf_web/services/` for non-trivial orchestration

Approach:

- Identify helper clusters currently embedded in `app.py`.
- Extract request parsing, response shaping, and repeated error handling.
- If the framework setup makes route extraction risky, keep route registration in `app.py` and extract only helper functions first.

Verification:

- `tests.test_web_app`
- any route-specific tests
- smoke start of app if feasible

Acceptance:

- `app.py` becomes mostly app wiring plus route registration.
- No endpoint behavior changes.

## Phase 3A: Frontend Refactor Of `bhf_web/static/maps/MapPanel.js`

Goal:

- Break the largest frontend file into responsibility-based pieces without changing UX or behavior.

Likely extractions:

- tab/tool state
- no-pin explanation UI
- AI fallback response display
- modal map viewer
- search/result controls
- action menus including mobile long-press handling

Recommended structure:

- `bhf_web/static/maps/components/`
- `bhf_web/static/maps/hooks/`
- `bhf_web/static/maps/api/`
- `bhf_web/static/maps/utils/`

Suggested modules:

- `components/MapPanelHeader.js`
- `components/MapSummaryCard.js`
- `components/WhyNoPinCard.js`
- `components/MapFallbackCard.js`
- `components/MapModal.js`
- `components/ResourceList.js`
- `hooks/useMapPanelState.js`
- `hooks/useLongPressMenu.js`
- `api/maps.js`
- `utils/mapFormatting.js`

Approach:

- Extract presentational child components first.
- Extract fetch logic into `api/maps.js`.
- Extract long-press behavior into a dedicated hook.
- Keep `MapPanel.js` as composition glue.

Verification:

- existing frontend build
- manual smoke test of maps tab, modal, fallback text, no-pin explanation, mobile actions

Acceptance:

- `MapPanel.js` drops well below current size.
- No UI redesign, only structural cleanup.

## Phase 3B: Frontend Refactor Of `bhf_web/static/maps/BibleMap.js`

Goal:

- Separate rendering helpers from interaction logic.

Likely extractions:

- marker rendering helpers
- GeoJSON/layer utilities
- viewport fit logic
- popup content formatting

Recommended modules:

- `bhf_web/static/maps/utils/mapLayers.js`
- `bhf_web/static/maps/utils/viewport.js`
- `bhf_web/static/maps/utils/popupContent.js`

Acceptance:

- `BibleMap.js` becomes a thinner map composition file.

## Phase 3C: Frontend API And Search Cleanup

Goal:

- Consolidate fetch logic used by study tools and Bible search.

Recommended modules:

- `bhf_web/static/api/maps.js`
- `bhf_web/static/api/study.js`
- `bhf_web/static/api/search.js`

Approach:

- Move raw `fetch` calls out of large UI files.
- Normalize response/error handling in wrappers.
- Preserve existing payloads and endpoints.

Acceptance:

- Large UI files no longer contain repeated request boilerplate.

## Phase 4A: CSS Organization

Goal:

- Reduce `bhf_web/static/style.css` by grouping related styles into scoped files without changing layout or appearance.

Recommended structure:

- `bhf_web/static/styles/layout.css`
- `bhf_web/static/styles/workspace.css`
- `bhf_web/static/styles/maps.css`
- `bhf_web/static/styles/search.css`
- `bhf_web/static/styles/utilities.css`

Approach:

- Move existing rules as-is.
- Keep import order deterministic.
- Avoid selector changes unless required for file split safety.

Verification:

- frontend render smoke check on desktop and mobile widths

Acceptance:

- Styling remains visually unchanged.
- Root stylesheet becomes an import/index file or materially smaller.

## Phase 4B: Legacy Utility Review

Goal:

- Review whether `bhf_web/static/htmx-lite.js` can be split safely or annotated for later.

Approach:

- If it is vendored or intentionally monolithic, add a comment explaining why it remains large.
- If it contains app-specific custom logic, extract only that custom logic into local helpers.

Acceptance:

- Either smaller file or explicit rationale for leaving it large.

## Phase 5A: Remaining Python File Review

Targets:

- `bhf_agent/bible.py`
- `bhf_agent/runner.py`
- `bhf_agent/curation.py`

Approach:

- inventory responsibilities inside each file
- extract pure helpers, schemas, and service logic into adjacent modules
- preserve public imports where possible

Potential structure:

- `bhf_agent/services/`
- `bhf_agent/models/`
- `bhf_agent/utils/`

Acceptance:

- No app-specific source file remains over 800 lines unless justified.
- Any remaining large file gets a comment or follow-up note explaining why.

## Phase 5B: Verification Sweep

Run:

- Python compile checks
- unit tests
- web app tests
- frontend build if available

Manual verification checklist:

- Ask still works
- Notes still work
- Highlights still work
- Saved studies still work
- Maps still work
- Bible search still works
- modal map still works
- no-pin explanation still works
- mobile long-press alternative still works
- no console import errors

## Phase 5C: Cleanup

Tasks:

- remove stale compatibility helpers no longer needed
- sort imports
- add concise comments only where a large file remains intentionally large
- confirm no accidental behavior changes slipped in

## Review Strategy

Keep each commit or review slice narrow:

1. extract one responsibility cluster
2. keep compatibility facade
3. run verification
4. fix breakage immediately
5. move to the next cluster

