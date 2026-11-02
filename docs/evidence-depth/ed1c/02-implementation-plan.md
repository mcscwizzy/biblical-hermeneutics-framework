# ED-1C implementation plan

**Goal:** Make source-backed, passage-anchored CKL child records discoverable without changing their scholarly classification or scope.

**Architecture:** Keep CKL data, the section classifier, API schema, and curated routes unchanged. Add a collapsed overview disclosure that derives its entries from the existing passage projection, filters to source-backed child records with a non-empty applicable passage anchor and no section assignment, and renders them with the existing item card and paged list components.

**Tech stack:** Python/FastAPI API tests, JavaScript Node test runner, existing Selenium reader tests, Markdown reports.

**Spec:** `docs/evidence-depth/ed1c/01-baseline-and-classification.md` and the user request “BHF — ED-1C: Evidence Discoverability and Reader Accessibility.”

## Global constraints

- Correct no more than five verified discoverability defects; this plan addresses the missing reader path and one misleading lexical type label.
- Do not add evidence, mass-remap CKL records, or revise scholarly content.
- Preserve exact evidence identities and passage scopes, source attribution, uncertainty, curation classifications, and historical/later-reception distinctions.
- Keep broad or ineligible records and the held Ezekiel/Revelation bridge out of the new path.
- Keep the six existing section categories, APIs, and projection schema.
- Keep the passage-first reader concise through collapsed disclosure and existing two-card previews with paged expansion.
- Validate desktop and mobile reader behavior and negative scope / duplication cases.
- Do not merge or deploy; commit and push the requested branch and provide a PR comparison URL.

## Review focus

- Passage scope: only use non-empty `applicable_passage_anchors`; test an unassigned item with no applicable anchor is excluded.
- Object versus child identity: parent objects such as `new-jerusalem-prophecy` stay out; test that they are excluded.
- Duplicate cards: items already assigned to a section or already shown in the connection preview do not appear as additional records.
- Attribution: eligible cards retain their stable ID, claim/evidence identity, original and applicable anchors, source IDs/details, uncertainty, and review metadata.
- Progressive disclosure and layout: no child cards appear before activation; test desktop and mobile viewport behavior and horizontal overflow.

### Task 1: Add the additional sourced-record disclosure

**Files:**

- Modify `bhf_web/static/narrative-explorer.js`.
- Modify `bhf_web/static/styles/companion.css`.
- Test `tests/frontend/narrative-explorer.test.js`.

**Interfaces:**

- Consumes the existing projection’s `items`, `sections`, and `connections`.
- Produces a collapsed overview control and, after activation, existing `renderSection` / `renderItem` cards for selected unassigned child records.
- Does not change `project_narrative_explorer`, API fields, or section assignment.

- [x] Add a failing Node test that proves the control is hidden when there are no eligible records, starts collapsed, exposes a sourced child claim with an applicable anchor after activation, and excludes assigned items, parent objects, source-less items, missing-anchor items, and already previewed evidence.
- [x] Run the focused frontend test file against the baseline; confirm the new test fails because the control/path is absent.
- [x] Implement a single filtering helper and a collapsed overview disclosure. Require `domain === "ckl"`, a child `record_kind`, no `section_ids`, a non-empty `applicable_passage_anchors`, at least one source ID, and no current connection-preview presentation. Reuse `renderSection` and existing provenance details.
- [x] Style the disclosure control to fit the current overview design and fill available width on narrow viewports.
- [x] Use the recorded `claim_type: lexical` to display “Lexical research” rather than “Evidence type not recorded”; do not assign a new section.
- [x] Run the frontend test file and confirm all tests pass.

### Task 2: Lock exact API scope and bridge exclusion

**Files:**

- Test `tests/test_narrative_explorer_api.py`.

**Interfaces:**

- Uses the existing `NarrativeExplorerService` and real CKL test fixture.
- The API projection remains unchanged; this test guards the data consumed by the new disclosure.

- [x] Add real-CKL acceptance assertions for Proverbs 31 (`proverbs-greek-order` applies at `Proverbs 31:1-31`), Mark 2:23–28 (the separate Mark 2:1–12 disability claim is absent), and the held Ezekiel 40–48 / Revelation 21–22 bridge (absent from accepted routes).
- [x] Run the targeted API test; confirm exact overlapping anchors are retained, non-overlapping verse scopes and held bridge routes are excluded, and no production API behavior needs changing.

### Task 3: Verify the reader at desktop and mobile sizes

**Files:**

- Test `tests/gui/ne11d1/test_ed1c_additional_records.py`.

**Interfaces:**

- Uses the real CKL enabled GUI server, existing `HomePage`, browser, and waits fixtures.
- Exercises 1 Corinthians 11 at desktop and mobile viewport sizes.

- [x] Add a browser acceptance test that opens 1 Corinthians 11, verifies the disclosure is initially collapsed, opens it, finds `ckl:1-corinthians#claim:1cor-kephale` exactly once, and opens its existing source/provenance details.
- [x] Assert the item retains 1 Corinthians 11:3, the `bdag` / `thiselton-1cor` source identities, and its recorded disputed lexical state.
- [x] At both 1440px desktop and 390px mobile, assert no horizontal overflow and that the disclosure and provenance details remain operable.
- [x] Run the focused Selenium test; record browser, viewport, and artifact paths in `04-reader-acceptance.md`.

### Task 4: Record findings, regression results, and remaining work

**Files:**

- Create `docs/evidence-depth/ed1c/README.md`.
- Create `docs/evidence-depth/ed1c/03-before-after-and-backlog.md`.
- Create `docs/evidence-depth/ed1c/04-reader-acceptance.md`.
- Create `docs/evidence-depth/ed1c/05-regression-results.md`.

**Interfaces:**

- Reports the reproduced inventory, representative decisions, exact before/after UI state, acceptance evidence, test results, and prioritized backlog.
- Records that projection assignments and the unclassified inventory remain unchanged.

- [x] Record the unchanged API projection and section counts, plus the new path’s included and excluded cases.
- [x] Record accepted and intentionally excluded cases and backlog priorities.
- [x] Run applicable CKL, source integrity, Narrative Explorer, frontend, and reader regression gates; record exact commands and results.
- [ ] Check Markdown links and commands, review `git diff --check`, the full diff, generated-file status, and final commit state.
- [ ] Commit the focused change and reports; push `fix/ed1c-evidence-discoverability`; provide a PR comparison URL without merging or deploying.
