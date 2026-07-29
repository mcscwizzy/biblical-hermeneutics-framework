Review and redesign the biblical map experience in this repository:

https://github.com/mcscwizzy/biblical-hermeneutics-framework

Repository branch: `master`

## Goal

The current biblical maps UI is cluttered, difficult to navigate, and visually disorganized. Redesign it into a focused biblical geography study workspace.

This is not simply a request to make the existing markers prettier. The map should help users understand a passage, place, journey, event, or region without overwhelming them with every available geographic record at once.

Preserve the existing BHF architecture, existing map data, map context used by the agent, saved map studies, notes, offline/PWA behavior, and current backend functionality wherever possible.

Do not replace the existing mapping system with a Google-only implementation.

## First: inspect the implementation

Before editing anything, locate and review all relevant files for:

- Map templates or components
- Map CSS
- Map JavaScript
- Leaflet or other mapping-library initialization
- Backend map routes and API endpoints
- Map-place data models
- Journey, event, region, and location records
- Map context passed into the interpretation agent
- Saved map studies
- Map notes
- Offline caching and PWA support
- Tests related to maps

Document the current flow briefly in your final summary.

Do not assume filenames. Trace the actual implementation from routes to templates, JavaScript, data, and tests.

## Core design direction

The map must become a biblical geography study tool rather than a canvas filled with markers.

The user should begin with a study context such as:

- Passage
- Place
- Journey
- Event
- Region

Only map records relevant to the current study should be emphasized.

General browsing may still exist, but it must not render every marker at full prominence.

## Desktop layout

Create a responsive three-area study workspace:

### Left panel: Study Navigator

Include:

- Search field for places, passages, journeys, events, and regions
- Study mode selector
- Relevant filters
- Current passage or study title
- Ordered stops for journeys
- Related places for passage studies
- Layer controls
- Clear/reset action

Recommended study modes:

- Passage
- Places
- Journeys
- Events
- Regions

Use the existing data capabilities. Do not invent fake journeys or biblical records merely to fill the UI.

### Center: Map

The map must:

- Take the majority of available width
- Resize correctly when panels open or close
- Avoid controls overlapping each other
- Provide useful empty, loading, and error states
- Highlight the selected location or route
- Reduce visual clutter
- Fit bounds to the active study rather than always showing the entire world
- Support marker clustering in broad browse mode when practical
- Avoid rendering unrelated markers during a focused study

### Right panel: Details

Replace small marker popups as the primary information interface.

Selecting a location should open a proper details panel containing available data such as:

- Biblical place name
- Alternate names
- Modern identification
- Region
- Coordinates
- Geographic certainty
- Biblical references
- Associated people
- Associated events
- Historical notes
- Archaeological notes
- Related journeys
- Existing map notes
- Existing saved-study actions
- Ask BHF about this location
- Open in Google Earth

Do not display empty headings for unavailable data.

Small map tooltips may remain for quick identification, but substantial content belongs in the details panel.

## Mobile layout

Do not squeeze the desktop layout into a narrow screen.

On mobile:

- Use a full-width or near-full-screen map
- Put search and layer controls in compact floating controls
- Open location details in an accessible bottom sheet or drawer
- Open the study navigator as a drawer
- Ensure controls meet reasonable touch-target sizes
- Avoid map gestures conflicting with page scrolling
- Make journey stops navigable with previous and next actions
- Respect mobile safe areas where applicable

## Marker and data organization

Implement progressive disclosure.

Examples:

- Broad zoom: emphasize regions and major study objects
- Medium zoom: show major places
- Close zoom: show minor places
- Passage mode: show passage-related places
- Journey mode: show ordered stops and route lines
- Event mode: show places tied to the selected event
- Region mode: emphasize the selected geographic area

If the existing data includes certainty or identification status, represent it visually.

Suggested treatments:

- Identified location: solid marker
- Probable location: reduced-opacity marker
- Disputed location: dashed or ring-style marker
- Traditional location: visually distinct traditional marker
- Approximate region: polygon, circle, or shaded area instead of a falsely precise pin

Do not claim geographic precision that the stored data does not support.

If the current model lacks certainty fields, design the UI and types so certainty can be added later without requiring a second redesign. Do not mass-edit existing records with guessed certainty values.

## Layers

Provide a clean layer-control experience.

Initial useful layers may include:

- Places
- Journeys
- Events
- Regions
- Terrain or physical map
- Modern labels

Only expose layers supported by the current implementation or data.

The interface should allow future layers such as:

- Tribal territories
- Ancient roads
- Political boundaries
- Archaeological sites
- Elevation
- Disputed identifications

Do not implement unsupported historical polygons by guessing boundaries.

## Passage integration

BHF now uses chapter-first interpretation context. The map should align with that principle.

When a map is opened from a biblical passage:

- Preserve the selected book, chapter, and verse range
- Retrieve map locations associated with the focal passage and surrounding chapter context where supported
- Emphasize directly relevant locations
- Avoid showing unrelated global map data
- Make the passage reference visible in the study navigator
- Allow geographic context to remain available to the BHF interpretation pipeline

Do not break existing map context passed into the agent.

## Journey experience

When journey data exists:

- Display ordered numbered stops
- Connect stops with route lines
- Show the active stop clearly
- Provide previous and next navigation
- Fit map bounds to the route
- Display the biblical reference for each stop
- Do not imply that route lines are exact historical paths unless the data explicitly supports that

Use wording such as “approximate route” where appropriate.

## Google Earth integration

Add Google Earth interoperability as an optional external feature.

Do not replace the base map with Google Earth.

### Place-level Earth action

For locations with usable latitude and longitude, add:

`Open in Google Earth`

Generate the appropriate external Google Earth or Google Maps-compatible location URL using the stored coordinates.

Requirements:

- Open externally in a new browser context where appropriate
- Add safe `rel` attributes
- Do not show the action when valid coordinates are unavailable
- Keep the application fully usable without Google
- Do not require a Google API key for this basic action
- Clearly label it as an external online feature
- Gracefully handle offline mode

### KML export

Add a clean KML export capability if it fits the existing backend architecture.

Support practical endpoints or equivalent routes for:

- A single place
- A journey
- A saved map study
- A passage-related map study where sufficient data exists

Possible route structure:

```text
GET /api/maps/places/{place_id}.kml
GET /api/maps/journeys/{journey_id}.kml
GET /api/map-studies/{study_id}.kml
```

Use the repository’s existing route conventions rather than forcing these exact paths if another structure is more appropriate.

KML output should include available:

- Placemark names
- Coordinates
- Descriptions
- Biblical references
- Ordered journey stops
- Route lines
- Appropriate XML escaping
- Correct content type
- Download filename

Do not expose private notes in shared or exported KML unless the user explicitly chooses to include them.

Add tests for KML generation and XML escaping.

Do not add Google API billing, embedded photorealistic 3D tiles, or a mandatory Google Maps SDK in this phase.

## Offline and PWA behavior

Preserve BHF’s offline-first design.

The primary map UI and stored biblical geographic data should continue to work offline to the extent they currently do.

External Google Earth actions must:

- Be clearly identified as requiring internet access
- Be disabled or handled gracefully when offline
- Never prevent local map use
- Not interfere with service-worker caching
- Not attempt to cache prohibited Google resources

Review any service-worker or offline-manifest changes carefully.

## Accessibility

Implement:

- Keyboard-accessible controls
- Visible focus states
- Accessible labels
- Proper buttons rather than clickable generic elements
- Meaningful landmark regions
- Appropriate dialog/drawer semantics
- Escape-key handling for drawers or panels
- Screen-reader labels for map actions
- Sufficient contrast
- Reduced-motion support where animation is used

Ensure marker selection has an accessible non-map equivalent through the navigator or search results.

## Visual styling

Match the existing BHF visual identity rather than importing a completely unrelated design system.

The finished map should feel:

- Calm
- Scholarly
- Modern
- Uncluttered
- Suitable for extended Bible study
- Consistent with the rest of the application

Improve:

- Spacing
- Typography hierarchy
- Panel borders and elevation
- Button hierarchy
- Form controls
- Active states
- Empty states
- Loading states
- Mobile responsiveness

Avoid:

- Excessive gradients
- Oversized decorative headers
- Bright marker colors everywhere
- Tiny text
- Dense walls of controls
- Large amounts of permanent instructional text
- Map controls covering important content

## Architecture expectations

Do not put all map behavior into one giant JavaScript file.

Where appropriate, separate responsibilities such as:

- Map initialization
- Data loading
- Layer management
- Marker rendering
- Study selection
- Detail-panel rendering
- Journey rendering
- Google Earth link generation
- KML generation
- State synchronization

Follow the repository’s existing conventions and avoid unnecessary framework migrations.

Do not introduce React, Vue, or another frontend framework unless the repository already uses it for this area.

Avoid adding large dependencies when the current map library can support the requirement.

## State and URL behavior

Where reasonably compatible with the current app:

- Preserve the selected study mode in URL parameters
- Preserve selected place, journey, event, region, or passage
- Allow browser back and forward navigation
- Make meaningful map states shareable
- Restore state after page refresh
- Avoid storing sensitive notes in public URL parameters

## Testing

Add or update tests for:

- Existing map routes
- Map data API responses
- Place selection
- Focused filtering
- Journey stop ordering
- Invalid or missing coordinates
- Google Earth link generation
- KML generation
- XML escaping
- Offline-safe behavior
- Mobile layout behavior where the current test stack permits
- Accessibility behavior where the current test stack permits
- Preservation of map context passed to the agent

Run the relevant test suite.

Also run the broader regression suite if practical because maps interact with interpretation context, saved studies, routes, and offline behavior.

Do not weaken or delete tests simply to make the changes pass.

## Scope control

Prioritize a solid first implementation rather than attempting every possible future map feature.

Required for this change:

1. Cleaner responsive map workspace
2. Study navigator
3. Details panel or mobile bottom sheet
4. Focused marker filtering
5. Improved place search
6. Basic layer controls
7. Better journey presentation where journey data exists
8. Google Earth external link for valid coordinates
9. KML export if it can be implemented cleanly
10. Tests
11. Preservation of offline behavior and agent map context

Do not invent unsupported archaeological claims, routes, coordinates, boundaries, or biblical associations.

Do not modify unrelated interpretation behavior.

Do not remove existing map features without providing an equivalent or explaining why the existing behavior was broken or redundant.

## Completion criteria

The task is complete when:

- The map no longer presents an uncontrolled wall of markers
- A user can select a study mode and understand what is displayed
- A selected place opens substantial information outside a tiny popup
- Desktop and mobile layouts are both usable
- Passage and journey context visibly influence the map
- Google Earth can be opened for places with valid coordinates
- KML exports are valid if implemented
- Local map functionality remains usable without Google
- Offline behavior is preserved
- Existing agent map context continues to work
- Relevant tests pass

## Final response

At completion, provide:

1. A concise explanation of the original map architecture
2. The primary UI and architectural changes made
3. Files changed
4. New or changed routes
5. New tests
6. Test commands run and results
7. Any limitations caused by missing geographic data
8. Recommended next phase
9. Screenshots or a clear visual description of desktop and mobile behavior if screenshots cannot be produced

Work through the repository carefully and implement the changes. Do not stop after only providing recommendations or a plan.

## Implementation progress

### Phase 1 — repository trace (complete, 2026-07-29)

- Entry point: `bhf_web/templates/index.html` renders the Maps workspace inside the reader's Maps tab and an expandable modal host.
- Client flow: `bhf_web/static/maps/MapPanel.js` owns panel state and orchestration; `BibleMap.js` owns Leaflet rendering; `mapService.js` owns API/offline reads; `MapPanelContent.js` and `MapPanelText.js` render the details interface; `JourneyMapData.js` validates and loads static journey/layer JSON.
- Backend flow: `bhf_web/routes/maps.py` exposes catalog, passage-resolution, search, route/layer, saved-study, and note endpoints; `bhf_web/map_service.py` serializes SQLite-backed places, routes, historical layers, and political context.
- Existing preservation points: map context is still posted through the Ask form as `map_context`; saved studies and notes use the existing study database; `bhf_web/static/offline/db.js` and `mapService.js` cache local map responses; the service worker remains same-origin and does not cache external tile resources.
- Primary redesign target: replace the current stacked controls + map/details arrangement with a responsive study navigator / map / details workspace, while keeping the existing data loaders and selection renderers behind that shell.

Next phase: implement the responsive study workspace and progressive-disclosure controls.

### Phase 2 — study workspace and focused disclosure (complete, 2026-07-29)

- Replaced the two-column map/details surface with a three-area desktop workspace: Study Navigator, map center, and selected-object Details.
- Added focused study modes for Passage, Places, Journeys, Regions, and an explicitly unavailable Events state until local event records exist.
- Moved search, journey selection, ordered stops, route visibility, period filtering, and broad layer toggles into the navigator; browse mode still starts empty and only renders search results.
- Added responsive navigator and details drawers for tablet/mobile, safe-area-aware spacing, touch-sized controls, focusable buttons, and reduced-motion CSS.
- Kept Leaflet, the existing passage-resolution APIs, saved studies, notes, offline API cache, and `map_context` agent handoff intact.
- Place details now disclose only available fields and include coordinate-aware `Open in Google Earth` plus local place KML export actions.

Verification: `node --check` passed for changed map modules; targeted web asset and saved-study tests passed. Selenium browser tests were discovered but skipped because Firefox/selenium/uvicorn dependencies are unavailable in this environment.

Next phase: finish export route coverage, accessibility/offline assertions, and the broader regression run.

### Phase 3 — exports, preservation checks, and handoff (complete, 2026-07-29)

- Added dependency-free KML generation with XML escaping for places, SQLite-backed routes, static journeys, and saved map studies.
- Added export routes: `GET /api/maps/places/{place_id}.kml`, `GET /api/maps/routes/{route_id}.kml`, `GET /api/maps/journeys/{journey_id}.kml`, and `GET /api/map-studies/{study_id}.kml`.
- KML exports omit records without usable coordinates, include available references/descriptions, label journey lines as approximate, and return a download filename/content type.
- Added tests for KML escaping, point/line/journey serialization, place and saved-study export routes, coordinate validation, map context/tool behavior, notes, and the new responsive map shell selectors.
- No service-worker or external tile caching changes were made; Google Earth remains an optional online action and local map use remains independent of it.

Verification:

- Passed: `./.venv/bin/python -m unittest tests.test_web_app.WebAssetTests tests.test_map_kml tests.test_map_tools tests.test_notes -q` — 38 tests.
- Passed: changed Python/JavaScript syntax checks, `git diff --check`, direct KML route smoke checks, and Google Earth URL validation.
- Passed: focused saved-study route test and the restored server-rendered period-option assertion.
- Selenium UI tests were skipped by the harness because Firefox/selenium/uvicorn are unavailable here.
- Full repository discovery was started but interrupted after several minutes in an unrelated canonical-library test; the completed map/web subset is green. Two unrelated web-suite baseline failures remain for Bible search ordering and translation catalog state.

Current limitations: the local database does not provide a first-class event entity, so Events is shown as unavailable; some place records lack coordinates or certainty beyond the stored confidence text; no unsupported ancient boundaries or exact historical routes were added.

Recommended next phase: run the browser smoke suite with Firefox/selenium installed, then add event records only when the backend model supports them and consider URL-state synchronization for shareable study modes/selections.
