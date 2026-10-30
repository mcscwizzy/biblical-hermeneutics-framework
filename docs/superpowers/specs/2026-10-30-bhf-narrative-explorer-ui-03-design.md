# BHF UI-03 — Narrative Explorer Experience Redesign

## Intent

Make passage research feel like a guided way into Scripture and its evidence. A reader opening Narrative Explorer should first see the selected passage, a clear invitation to follow a documented connection, and six recognizable topic choices. Detailed records, source metadata, qualifications, and governance remain available when the reader opens a topic or evidence item.

The work follows UI-02, merged into `origin/master` at `f4b203de`. It changes the presentation inside the existing Study Companion resource host and keeps the reader, its selection, the projection API, and the CKL research inputs authoritative.

## Goals

- Replace the stacked initial inventory with a concise, passage-first discovery screen.
- Provide focused category views with a short explanation, up to two useful previews, paginated browsing, expandable evidence and source details, and clear navigation back to the overview or original passage.
- Make connection trails read as a progression from origin through the documented relationship to the destination, while retaining history, direction, limits, and cycle protection.
- Keep the six requested category concepts distinct, with availability and counts derived only from completed source queries.
- Improve visual hierarchy, responsive behavior, keyboard use, focus restoration, and screen-reader announcements using existing BHF styles and native browser semantics.
- Preserve all current evidence and governance disclosures without generating summaries or interpretations.

## Non-goals

- No change to projection, canonical, map, archaeology, or other API schemas or compatibility behavior.
- No CKL, NE-9C, NE-10, evidence, source, fingerprint, manifest, or scholarly record edits.
- No new research claims, theological summaries, geographic coordinates, or inferred graph edges.
- No new application shell, framework, dependency, caching layer, or deployment configuration.
- No changes to Tyndale Study Notes, Ask BHF, Scripture navigation/comparison, personal study features, maps/archaeology workspaces, or retired BHF Commentary HTTP 410 behavior.

## Approaches considered

1. **Focused views in the current resource host — selected.** The overview becomes a landing screen, and one category at a time is rendered as a focused view. Existing projection records and evidence renderers are reused. A small bounded view field in Companion history records the active category, so browser Back/Forward can restore overview, category, and evidence context. This meets the requested flow and avoids a second shell or projection request.
2. **Expandable sections inside the current overview.** This would reduce initial visual noise, but category content would remain in one inventory page and a selected topic would not become a focused view. It does not meet Phase C's requested interaction, so it is not selected.

The user-specified behavior resolves the main design choice: selecting a category opens a focused view inside the existing Study Companion resource host. The implementation uses the current JavaScript/CSS patterns and native inline SVG icons; no dependency is needed.

## Interaction contract

### Entry and overview

- With no selected passage, retain the existing Companion's general exploration behavior; do not request passage-specific projection data.
- On open, keep the selected passage reference visible and explain that Narrative Explorer shows records connected to that passage.
- Lead with a prominent **Follow a Connection** entry. It opens the focused connection view, which distinguishes authored CKL relationships from CKL-documented passage bridges and interpretive connections. Show a count only after complete route retrieval; when route retrieval is partial or unknown, show the recorded state and do not imply zero coverage.
- Show six topic cards: **Biblical Narrative**, **Archaeology & Ancient History**, **Biblical Geography**, **Divine Council & Cosmic Geography**, **Themes & Biblical Connections**, and **People, Events & Relationships**. Each has one consistent decorative icon, a plain-language description, and source-backed availability. Counts appear only when supported by completed queries. For completed empty lookups, say no linked records are represented for this passage; do not imply that evidence or meaning is absent from the world or Scripture. Unknown and offline states remain distinct.
- Do not render evidence inventories or long source lists on the initial screen. Keep the reader's Companion passage state and scroll position stable when switching views.

### Focused category view

- Render one selected category at a time within the current resource host. Include the passage reference, category title, concise explanation, and **Back** and **Return to Passage** actions.
- Show no more than two preview records before **Browse records**. Use existing projection items only; preserve stable IDs, passage anchors, original wording, source identity, and qualifications.
- Browse records in stable order and bounded pages using the existing page size. Do not create a second data request or duplicate record store.
- Keep full evidence, sources/bibliography, relation basis, uncertainty, confidence/certainty, dispute state, review state, human-review status, and temporal context in native expandable disclosures. Missing fields remain “not recorded”/unavailable rather than guessed.
- In **Themes & Biblical Connections**, make verified passage routes the first connection path, with record-backed evidence relationships available in the same view. Preserve relationship basis, direction, exact labels, source IDs, review status, and the distinction between a recorded relationship and an interpretive passage bridge.
- In **Biblical Geography**, continue to distinguish physical records from textual/conceptual geography. Only existing eligible physical map records may lead to map navigation; symbolic or supernatural locations never become markers or receive generated coordinates.

### Evidence detail and connection trail

- Keep the current exact projected child evidence ID, parent identity checks, subject identity checks, and passage-anchor eligibility rules.
- Present the trail as an ordered path: origin passage → recorded connection → related passage, subject, or evidence → any further verified connection. Keep the current breadcrumb landmark and identify the active step. State why the connection exists using its recorded basis and relation type.
- Retain recorded direction, reciprocal-edge checks, source identifiers, review status, and uncertainty. An incoming one-way edge remains non-navigable. Do not promote similarity into quotation, allusion, borrowing, fulfillment, dependence, or historical development.
- Keep the three relationship-hop limit, twelve-node history bound, stable connection ordering, cycle checks, and twelve-item paging rules.
- **Back** returns to the previous Companion history state. **Return to Passage** restores the original reader selection and opens its passage overview. Browser Back and Forward restore the matching reader passage, trail, focused category, and focus target.
- Keep a trail available and show a recoverable unavailable state when a linked CKL subject or projection cannot load. Do not discard the origin or return controls.

### Loading, availability, offline, and accessibility

- Loading retains the passage header and uses the existing resource host's loading state with a live status announcement. Do not jump the reader or sheet scroll position.
- Partial and unknown availability remain separate. An offline cache miss states that the category could not be checked or is unavailable offline; it is not a completed empty lookup. If cached data is available, label it stale/offline only when the existing data contract supports that state.
- Keep semantic headings, buttons for actions, links for destinations, native disclosure elements, labelled decorative/icon controls, visible focus, keyboard navigation, Escape/Back behavior, and focus restoration to the opening control or view heading.
- Keep mobile single-column cards and touch targets of at least 44px; use desktop two-column category cards when available space allows. Long text and technical IDs wrap without horizontal scrolling.

## Evidence and governance invariants

- Keep Scripture text, archaeological/historical evidence, ancient comparative literature, CKL-authored relationships, CKL-documented interpretive connections, uncertain/disputed interpretation, and human editorial review status distinguishable.
- A reference destination does not itself assert that two passages share theological meaning. Similar wording or subject labels do not establish intertextual dependence.
- Draft, in-review, and human-review-required records disclose their actual recorded status. Do not imply scholarly approval that is not present.
- Source attribution, provenance, confidence, certainty, dispute, temporal relation, and evidence classification remain reachable in the expanded detail view. Preserve existing URLs and safety rules.
- NE-9C curations and NE-10 passage bridges remain read-only. Preserve their eligibility, direction, identity, review, and provenance semantics.
- Physical geography and Divine Council/cosmic geography remain separate concepts. No coordinates are synthesized.

## Implementation approach

- `bhf_web/static/narrative-explorer.js`: add the discovery-card renderer and focused category/connection views; reuse the current passage route, category, evidence, source, and subject renderers; add readable trail progression and disclosure organization; keep all navigation callbacks inside the existing host contract.
- `bhf_web/static/styles/companion.css`: refine typography, spacing, card hierarchy, desktop/mobile grids, disclosure behavior, focus, and long-content wrapping with existing CSS variables.
- `bhf_web/static/resource-router.js`: own the active Narrative Explorer view, render the selected focused category without reloading the projection, and expose/restores the view state through existing navigation callbacks.
- `bhf_web/static/study-companion.js` and `bhf_web/static/companion-history.js`: only as needed to serialize an allowlisted, bounded Narrative Explorer view (`overview` or a known category ID) beside the existing bounded trail, and restore it on browser Back/Forward. Do not add a browser-history listener or change unrelated history state.
- `tests/frontend/narrative-explorer.test.js`, `tests/frontend/resource-router.test.js`, `tests/frontend/companion-history.test.js`, `tests/frontend/study-companion-context.test.js`, and relevant GUI/reader tests: cover overview/category/detail state, source disclosure, exact navigation semantics, history restoration, responsive controls, and preservation of neighboring reader actions.
- No API/backend or CKL files are planned. If implementation discovers an API limitation, first determine whether the requested UI can accurately display the current projection's unknown/partial state; do not add an API field without a demonstrated necessity.

## Verification and release boundary

- Preserve and run `npm test`, targeted Python API/projection tests, the relevant GUI/reader tests, packaging/integrity checks required by the changed files, and `git diff --check`.
- Exercise Genesis 1, Genesis 6, Exodus 3, Psalm 22–Mark 15, Jonah–Matthew, and limited/missing-coverage passages. Check category states, direction, source and review disclosure, reader selection/history restoration, mobile layout, keyboard/focus behavior, and offline recovery.
- Compare the same real-reader journey and projection response/request counts against the UI-02 baseline. UI-only view changes must not add projection requests or enlarge the API payload. Record UI render timing/DOM growth where browser instrumentation permits. Existing NE-11D browser numbers were collected in a different, unmatched setup and are not a valid claim of improvement or regression by themselves.
- Capture desktop and mobile before/after screenshots from a real browser if a usable local or remote browser is available. State any browser or assistive-technology limitation explicitly.
- Commit and push `feat/bhf-narrative-explorer-ux-ui-03`. Do not create a PR, merge, or deploy.
