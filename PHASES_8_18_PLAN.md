# Maps / Historical Geography / Archaeology Continuation Plan

This file is a handoff plan for continuing the BHF map feature after Phase 7.

Current status:
- Phase 1 complete: interactive Leaflet map foundation
- Phase 2 complete: local biblical places database
- Phase 3 complete: deterministic passage-to-place resolution
- Phase 4 complete: map side panel with BHF-style place explanation
- Phase 5 complete: curated route overlays
- Phase 6 complete: historical geography layers with period filter
- Phase 7 complete: map-study integration, saved map studies, map notes, structured `map_context`

Repo-specific reality:
- App stack is FastAPI + Jinja + client-side JS, not React
- Map UI lives in `bhf_web/static/maps/`
- Persistent study data lives in `bhf_agent/study_db.py`
- Tests live in `tests/test_notes.py` and `tests/test_web_app.py`

Implementation rules to keep:
- Do not use AI-generated map images
- Do not invent places, routes, archaeology, manuscripts, or claims
- Retrieve curated structured data first, then allow explanation
- Keep every phase independently working
- Add source metadata and confidence labels everywhere possible

## Phase 8

Goal:
- Add archaeology as a first-class map layer

Data work:
- Add `archaeology_sites`
- Add `archaeology_items`
- Add `archaeology_scripture_links`
- Seed a conservative starter set from curated local data only

Suggested starter entries:
- Tel Dan Stele
- Mesha Stele
- Siloam Inscription
- Hezekiah's Tunnel
- Lachish Letters
- Dead Sea Scrolls / Qumran
- Cyrus Cylinder
- Black Obelisk of Shalmaneser III
- Pilate Stone
- Pool of Bethesda
- Pool of Siloam

Backend work:
- Add DB migration
- Add list and detail helpers in `study_db.py`
- Add archaeology map-service serializers
- Add APIs for archaeology markers and archaeology-by-passage

Frontend work:
- Add archaeology marker layer with visually distinct markers
- Add toggle in map panel
- Add archaeology detail card with:
  `name`, `type`, `period`, `location`, `related passages`, `relationship`, `confidence`, `source`, `why it matters`, `BHF caution`

Acceptance:
- Archaeology layer toggles on and off
- Archaeology markers are distinct from place markers
- Cards show source, confidence, relationship type, and caution

## Phase 9

Goal:
- Add a timeline filter across map content

Data work:
- Define canonical period labels
- Allow places, routes, archaeology, and historical layers to carry one or more periods
- Preserve an `uncertain / broad period` bucket

Backend work:
- Add period metadata where missing
- Add filtering helpers shared across map entity types

Frontend work:
- Add a timeline dropdown or slider
- Filter:
  places, routes, archaeology, historical layers

Acceptance:
- One period control filters all map data types
- Uncertain items are not silently lost

## Phase 10

Goal:
- Add empires, kingdoms, and political context overlays

Data work:
- Store major political entities as curated layers
- Tie layers to periods and passages where possible

Suggested entities:
- Egypt
- Canaanite city-states
- Philistia
- Israel
- Judah
- Aram-Damascus
- Assyria
- Babylon
- Persia
- Greece
- Rome

Frontend work:
- Add dedicated political-context toggles
- Add short summaries for each entity

Acceptance:
- User can inspect dominant political background for a passage
- Explanations stay historically careful

## Phase 11

Goal:
- Add manuscripts and textual witnesses as a distinct layer

Data work:
- Add `manuscript_items`
- Keep manuscript data separate from archaeology, with optional cross-links

Suggested entries:
- Dead Sea Scrolls
- Nash Papyrus
- Septuagint tradition markers where appropriate
- Major NT manuscript-location entries where appropriate

Frontend work:
- Add manuscript cards with:
  `name`, `language`, `date`, `material`, `discovery location`, `current location`, `related books`, `significance`

Acceptance:
- Manuscript layer can be surfaced from map context
- Claims remain careful and non-triumphalistic

## Phase 12

Goal:
- Add location-aware cross references

Backend work:
- Build grouped cross-reference lookup by:
  directly mentioned, same region, same route, same empire/period, OT/NT location links

Frontend work:
- Show grouped related passages on place cards

Acceptance:
- Place cards surface related passages by relationship type
- OT/NT links are careful and explicit

## Phase 13

Goal:
- Add a simple curation interface

Scope:
- Developer-only or admin-only screen
- CRUD for:
  places, aliases, archaeology items, scripture links, routes, historical layers, sources, confidence labels

Additional work:
- JSON import/export
- Validation of required fields

Acceptance:
- Data can be edited without hand-editing code
- Export format is commit-friendly

## Phase 14

Goal:
- Centralize source, license, and attribution management

Data work:
- Add a `sources` table
- Replace repeated raw source strings with source references where practical

Frontend work:
- Add visible attribution panel
- Add source detail view
- Flag missing source metadata in curation and display layers

Acceptance:
- Every visible item can show source and license details

## Phase 15

Goal:
- Improve offline and local-first behavior

Work:
- Cache local structured data
- Reduce unnecessary API calls
- Add graceful fallback when map tiles fail
- Keep saved studies and local datasets usable offline

Acceptance:
- Structured local map data remains usable without network
- Public tile usage remains restrained

## Phase 16

Goal:
- Expose map and archaeology retrieval as agent-callable tools

Candidate tools:
- `getPlacesForPassage(reference)`
- `getPlaceDetails(placeId)`
- `getArchaeologyForPassage(reference)`
- `getArchaeologyForPlace(placeId)`
- `getRoutesForPassage(reference)`
- `getHistoricalContextForPeriod(period)`
- `getRelatedPassagesByPlace(placeId)`

Rules:
- Agent must retrieve before answering
- Agent must refuse to invent absent curated data

Acceptance:
- Agent answers map/archaeology questions from structured local data only

## Phase 17

Goal:
- Expand tests and guardrails

Test areas:
- map renders
- markers render
- alias resolution
- route GeoJSON validity
- archaeology cards require sources
- historical layers render
- saved map studies restore
- agent refuses archaeology invention without retrieved data

Acceptance:
- Add unit, component, and seed-validation coverage for the new data system

## Phase 18

Goal:
- Polish UX and mobile behavior

Work:
- Add map icons by entity type
- Improve mobile panel behavior
- Add richer loading and empty states
- Add reset-map-view and related-item shortcuts
- Add compact vs expanded cards where useful

Acceptance:
- Feature feels integrated
- Small-screen usability is solid
- Layer and study controls remain understandable

## Recommended execution order

Suggested order:
1. Phase 8
2. Phase 9
3. Phase 12
4. Phase 10
5. Phase 11
6. Phase 14
7. Phase 13
8. Phase 15
9. Phase 16
10. Phase 17
11. Phase 18

Reason:
- Archaeology and timeline filtering will shape most later UX and tooling decisions
- Source management should land before large-scale curation and agent tooling mature

## Current technical notes

Map state already supports:
- place selection
- route selection
- historical layer selection
- saved map studies
- map notes
- structured `map_context` submission into the ask form

Before starting Phase 8:
- Re-run:
  `python3 -m unittest tests.test_notes tests.test_web_app -q`
- Re-check JS module load:
  `node --input-type=module -e "import('./bhf_web/static/maps/mapService.js'); import('./bhf_web/static/maps/BibleMap.js'); import('./bhf_web/static/maps/MapPanel.js'); console.log('js-ok');"`
