# Safe Refactor Progress

Snapshot date: 2026-06-30

## Completed

- Phase 2A: extracted reader-state database helpers from `bhf_agent/study_db.py`.
- Phase 2B: extracted database repository helpers into `bhf_agent/db/repositories/`.
- Phase 2C: split map-service logic into `bhf_web/services/map_matching.py`, `bhf_web/services/map_serializers.py`, and `bhf_web/map_service.py`.
- Phase 2D, pass 1: extracted route-adjacent helpers into `bhf_web/services/web_helpers.py`.
- Phase 2D, pass 2: extracted map and map-study route registration into `bhf_web/routes/maps.py`.
- Phase 2D, pass 3: extracted curation and study route registration into `bhf_web/routes/curation.py` and `bhf_web/routes/study.py`.
- Phase 2D, pass 4: extracted ask and search-fallback route registration into `bhf_web/routes/ask.py`.
- Phase 2D, pass 5: extracted ask-job state and worker helpers into `bhf_web/jobs.py`.
- Phase 3A: split map-panel render helpers into `bhf_web/static/maps/MapPanelContent.js`.
- Phase 3B: split Bible map styles and popup builders into `bhf_web/static/maps/MapStyles.js` and `bhf_web/static/maps/MapPopups.js`.
- Phase 3C: centralized shared HTTP request helpers in `bhf_web/static/api/http.js` and moved repeated request boilerplate out of `bhf_web/static/htmx-lite.js` and `bhf_web/static/maps/MapPanel.js`.
- Phase 4A: split `bhf_web/static/style.css` into imported style bundles under `bhf_web/static/styles/`.
- Phase 4B: kept `bhf_web/static/htmx-lite.js` intentionally monolithic with an explicit rationale comment; shared request helpers were already extracted in Phase 3C.
- Phase 5A, pass 1: extracted Bible guide tables and reference parsing constants into `bhf_agent/bible_support.py`.
- Phase 5A, pass 2: extracted runner pipeline status tables into `bhf_agent/runner_state.py`.
- Phase 5A, pass 3: extracted curation schema and normalization helpers into `bhf_agent/curation_schema.py`.
- Phase 5A: completed the remaining Python file review targets and reduced all three files below the 800-line threshold.
- Phase 5B: completed the verification sweep with full `unittest` discovery and Python compilation.
- Phase 5C: removed one dead helper and tightened imports during cleanup.
- Post-plan refactor: split shared status/waiting helpers into `bhf_web/static/htmx-status.js`.
- Post-plan refactor: split notes/highlights/saved-study helpers into `bhf_web/static/htmx-study-panels.js`.
- Post-plan refactor: split Bible search helpers into `bhf_web/static/htmx-search.js`.
- Post-plan refactor: kept reader context-menu logic in `bhf_web/static/htmx-lite.js` for now.
- Post-plan refactor: split map study summary and saved-study/orientation rendering into `bhf_web/static/maps/MapPanelContent.js`.
- Post-plan refactor: split map selection and layer overview rendering into `bhf_web/static/maps/MapPanelContent.js`.
- Post-plan refactor: split map toggle and visibility sync helpers into `bhf_web/static/maps/MapPanelStateHelpers.js`.
- Post-plan refactor: split map study payload and selection helpers into `bhf_web/static/maps/MapPanelStateHelpers.js`.
- Post-plan refactor: split shared map text and attribution helpers into `bhf_web/static/maps/MapPanelText.js`.

## Current Files Of Interest

- `bhf_agent/study_db.py`
- `bhf_agent/bible.py`
- `bhf_agent/bible_support.py`
- `bhf_agent/runner.py`
- `bhf_agent/runner_state.py`
- `bhf_agent/curation.py`
- `bhf_agent/curation_schema.py`
- `bhf_web/app.py`
- `bhf_web/jobs.py`
- `bhf_web/map_service.py`
- `bhf_web/services/web_helpers.py`
- `bhf_web/routes/ask.py`
- `bhf_web/routes/curation.py`
- `bhf_web/routes/study.py`
- `bhf_web/static/maps/MapPanel.js`
- `bhf_web/static/maps/MapPanelContent.js`
- `bhf_web/static/maps/BibleMap.js`
- `bhf_web/static/maps/MapStyles.js`
- `bhf_web/static/maps/MapPopups.js`
- `bhf_web/static/api/http.js`
- `bhf_web/static/htmx-status.js`
- `bhf_web/static/htmx-study-panels.js`
- `bhf_web/static/htmx-search.js`
- `bhf_web/static/style.css`
- `bhf_web/static/styles/layout.css`
- `bhf_web/static/styles/workspace.css`
- `bhf_web/static/styles/maps.css`
- `bhf_web/static/styles/utilities.css`
- `bhf_web/static/htmx-lite.js`

## Current Size Notes

- `bhf_agent/study_db.py`: 3424 lines
- `bhf_agent/bible.py`: 541 lines
- `bhf_agent/bible_support.py`: 254 lines
- `bhf_agent/runner.py`: 619 lines
- `bhf_agent/runner_state.py`: 48 lines
- `bhf_agent/curation.py`: 138 lines
- `bhf_agent/curation_schema.py`: 450 lines
- `bhf_web/app.py`: 157 lines
- `bhf_web/jobs.py`: 372 lines
- `bhf_web/map_service.py`: 434 lines
- `bhf_web/services/web_helpers.py`: 554 lines
- `bhf_web/routes/ask.py`: 173 lines
- `bhf_web/routes/maps.py`: 240 lines
- `bhf_web/routes/curation.py`: 109 lines
- `bhf_web/routes/study.py`: 169 lines
- `bhf_web/static/maps/MapPanel.js`: 1525 lines
- `bhf_web/static/maps/MapPanelContent.js`: 665 lines
- `bhf_web/static/maps/MapPanelStateHelpers.js`: 169 lines
- `bhf_web/static/maps/MapPanelText.js`: 416 lines
- `bhf_web/static/maps/BibleMap.js`: 609 lines
- `bhf_web/static/maps/MapStyles.js`: 119 lines
- `bhf_web/static/maps/MapPopups.js`: 96 lines
- `bhf_web/static/api/http.js`: 24 lines
- `bhf_web/static/htmx-status.js`: 169 lines
- `bhf_web/static/htmx-study-panels.js`: 435 lines
- `bhf_web/static/htmx-search.js`: 264 lines
- `bhf_web/static/style.css`: 21 lines
- `bhf_web/static/styles/layout.css`: 252 lines
- `bhf_web/static/styles/workspace.css`: 582 lines
- `bhf_web/static/styles/maps.css`: 349 lines
- `bhf_web/static/styles/utilities.css`: 510 lines
- `bhf_web/static/htmx-lite.js`: 872 lines

## Next Planned Step

- Continue with the next safe client-side extraction target if one is needed; otherwise the current plan phases are complete.
