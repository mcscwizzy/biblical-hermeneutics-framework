# BHF UI-02: Tyndale First-Class Reader Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the correctly matched Tyndale notes in the Study Companion as the reader's chapter and verse selection changes, while retaining the full Tyndale workspace.

**Architecture:** Keep the existing `/api/commentary/{book}/{chapter}` endpoint and read-only SQLite model. Share a chapter payload cache and in-flight requests between the full notes browser and a contextual-card renderer subscribed to `BHFStudySelection`; correct book identity in repository chapter queries and filter entries against actual selected verses. Start the Tyndale chapter load with reader chapter navigation so stale content is cleared promptly, then preserve the restored tab selection when chapter data finishes loading.

**Tech Stack:** Existing Python/FastAPI/SQLite repository and service; framework-free browser JavaScript; Node built-in test runner; pytest/Selenium GUI tests; existing Study Companion CSS and service worker.

**Spec:** `docs/superpowers/specs/2026-10-30-bhf-tyndale-first-class-reader-design.md`

## Global Constraints

- Keep CKL research records, curations, evidence, provenance, Narrative Explorer APIs/feature flags, Ask BHF handoff behavior, translation comparison, notes, saved passages, highlights, retired BHF Commentary HTTP 410 behavior, public API compatibility, and workspace persistence identifiers unchanged.
- Do not rewrite, regenerate, or alter published Tyndale source text, licensing, attribution, importer output, SQLite schema, or database contents.
- Preserve the existing Tyndale workspace tab and API response fields; only return chapter entries with a matching Scripture book anchor.
- Use the UI-01 Study Companion styling and the existing `data-companion-tyndale-card-slot`.
- Do not add dependencies, nested scrolling, or automatic focus/scroll movement.
- Retain graceful missing/offline behavior and provide source attribution.

## Review Focus

1. **Book identity:** Genesis and Ruth each show their own introduction; unanchored records cannot be safely assigned to either. Pin this in Task 1's repository and API tests.
2. **Non-contiguous selection:** selecting verses 1 and 3 must not show a note anchored only to verse 2. Pin this in Task 2's frontend selection test.
3. **Late responses and restored tabs:** a delayed response for an old chapter cannot replace current notes, and restored selected verses remain focused after `loadChapter`. Pin this in Tasks 2 and 3.
4. **Unavailable data:** uninstalled, offline, failed, and no-matching-note states must be readable without implying that the whole book has no relevant notes. Pin this in Tasks 2 and 3.
5. **Small screens and assistive technology:** the card must fit narrow layouts, expose a clear heading and keyboard-operable disclosures, and update without moving focus. Pin this in Task 3's GUI tests.

---

### Task 1: Enforce book-specific chapter retrieval

**Files:**
- Modify: `framework/commentary/repository.py`
- Test: `tests/test_tyndale_study_notes.py`

**Interfaces:**
- Consumes: `CommentaryService.lookup_chapter(book, chapter)` and the existing imported entry/anchor schema.
- Produces: chapter lookup/count results containing only entries whose anchor book equals the normalized requested book and whose anchor overlaps the chapter.

- [ ] **Step 1: Write the failing retrieval regression test**

Add an archive fixture with book-anchored Genesis and Ruth introductions plus unanchored `book_introduction` and `profile` records. Add `test_chapter_lookup_returns_only_entries_anchored_to_requested_book` asserting Genesis 1 returns only Genesis entries, Ruth 1 returns only Ruth entries, and neither book receives either unanchored record. Assert `count_chapter` equals each lookup length. Extend the API fixture to request Genesis 1 and Ruth 1 and assert each response keeps the existing payload keys and includes only the matching introduction.

- [ ] **Step 2: Run the test and confirm it fails for the cross-book fallback**

Run: `pytest tests/test_tyndale_study_notes.py::test_chapter_lookup_returns_only_entries_anchored_to_requested_book -q`

Expected: FAIL because the current unanchored `book_introduction`/`profile` SQL fallback returns entries for both requested books.

- [ ] **Step 3: Remove the unanchored fallback from lookup and count**

In `CommentaryRepository.lookup_chapter` and `count_chapter`, remove the `OR (a.entry_id IS NULL AND e.kind IN (...))` clause. Keep the anchored book equality and chapter overlap conditions identical between both queries. Do not change passage lookup, schema, or importer behavior.

- [ ] **Step 4: Run the focused Python tests**

Run: `pytest tests/test_tyndale_study_notes.py -q`

Expected: PASS, including the new book-identity/count regression and existing import/API compatibility checks.

- [ ] **Step 5: Commit the retrieval fix**

Commit `framework/commentary/repository.py` and `tests/test_tyndale_study_notes.py` as `fix: require book anchors for Tyndale chapter lookup`.

### Task 2: Synchronize the contextual card and full reader

**Files:**
- Modify: `bhf_web/static/commentary.js`
- Modify: `bhf_web/static/htmx-lite.js`
- Test: `tests/frontend/commentary-card.test.js`

**Interfaces:**
- Consumes: existing `BHFStudySelection.subscribe`, `BHFApi.requestJson`, and `BHFCommentary.loadChapter/focusSelection/clearSelection` callers.
- Produces: a `BHFCommentary` runtime that shares cached/in-flight chapter payloads, updates the contextual card from the current normalized selection, and keeps the existing full-pane interface functional.

- [ ] **Step 1: Add failing Node tests for selection matching, priority, and card states**

Create `tests/frontend/commentary-card.test.js` with a minimal DOM fixture and a controllable `BHFApi.requestJson`. Cover: (a) Genesis 1 chooses the Genesis introduction and a published summary when present; (b) Ruth 1 excludes the Genesis introduction; (c) chapter 2 suppresses book introductions and shows anchored chapter notes; (d) selected verse 3 displays its matching note; (e) selected verses `[1, 3]` include notes overlapping 1 or 3, exclude a verse-2-only note, and order direct matches before a wider range; (f) no matching verse note uses non-misleading fallback text; and (g) unavailable API payloads/errors, including an offline-style rejection, render a readable unavailable state.

- [ ] **Step 2: Run the Node file and confirm failures are behavioral**

Run: `node --test tests/frontend/commentary-card.test.js`

Expected: FAIL because the contextual card is not rendered and current chapter entries are not filtered by the reader selection.

- [ ] **Step 3: Add shared chapter payload and in-flight request handling**

In `commentary.js`, add one `loadPayload(book, chapter)` path backed by the existing chapter cache and a keyed in-flight request map. Reuse it for both `loadChapter` and contextual selection updates; retain adjacent-chapter prefetch without allowing prefetch responses to render into the active surface.

- [ ] **Step 4: Subscribe the card to the normalized reader selection**

In `commentary.js`, render into `[data-companion-tyndale-card-slot]` and increment a context generation on every context change. Filter entries by exact book and chapter overlap. For verse selection, use the actual `selectedVerses` array when present; for chapter selection, keep only chapter-level entries, except that chapter 1 may display anchored book introductions and summaries. Rank exact/narrow verse matches before wider overlaps. Prefer a `book_introduction` over `book_introduction_summary`; use a published summary as preview when available, otherwise show an excerpt copied from the full body and make the full body expandable. Do not make up missing copy.

- [ ] **Step 5: Keep reader loads and restored selections in sync**

In `htmx-lite.js`, initiate `BHFCommentary.loadChapter(book, chapter)` when `loadReaderChapter` begins so the old card is invalidated and the chapter request can run alongside Scripture loading. Keep the post-response load call so the response's canonical book is reconciled through the shared cache. In `commentary.js`, preserve `pendingSelection` only when its book/chapter match the requested chapter; this lets `tab.selection` reapplied by `applySelectionContext` survive the subsequent full-pane `loadChapter` call. Gate card and full-pane rendering by their current context/request generations.

- [ ] **Step 6: Run the new Node tests and verify they pass**

Run: `node --test tests/frontend/commentary-card.test.js`

Expected: PASS for book identity, chapter/verse filtering, range priority, request reuse, missing data, and restored selection handling.

- [ ] **Step 7: Commit the synchronization changes**

Commit `commentary.js`, `htmx-lite.js`, and `tests/frontend/commentary-card.test.js` as `feat: synchronize Tyndale notes with reader selection`.

### Task 3: Present the accessible card and verify full browser behavior

**Files:**
- Modify: `bhf_web/templates/index.html`
- Modify: `bhf_web/static/styles/companion.css`
- Modify: `bhf_web/static/sw.js`
- Test: `tests/frontend/study-companion-layout.test.js`
- Test: `tests/frontend/narrative-explorer-sw.test.js`
- Test: `tests/frontend/commentary-card.test.js`
- Test: `tests/gui/test_study_companion.py`

**Interfaces:**
- Consumes: the contextual card renderer and current selection state produced in Task 2.
- Produces: a responsive, keyboard-accessible Tyndale card with attribution and a link to the existing complete notes workspace.

- [ ] **Step 1: Add failing markup, cache, and GUI coverage**

Extend frontend layout tests to assert the card slot remains between Ask BHF and Dig Deeper, has an accessible Tyndale heading/live status, and exposes a button for the commentary workspace. Extend service-worker tests to require `/static/commentary.js` in the precache list. Add GUI coverage asserting Genesis 1 displays only the Genesis introduction with source attribution, Ruth 1 displays Ruth's introduction, chapter 2 does not show an introduction, selecting a verse/range updates matching headings and bodies, stale responses do not replace newer notes, restored tab selections retain note context, missing/offline data is understandable, and the full workspace tab remains usable. At 390px, 768px, and 1440px widths, assert no horizontal overflow and a readable card width. Assert `<details>` controls work by keyboard, section/button names are accessible, and note updates do not move focus from Scripture.

- [ ] **Step 2: Run the focused frontend and GUI tests to confirm the expected failures**

Run: `node --test tests/frontend/study-companion-layout.test.js tests/frontend/narrative-explorer-sw.test.js tests/frontend/commentary-card.test.js`

Run: `pytest tests/gui/test_study_companion.py -k tyndale -q`

Expected: FAIL on missing card markup/behavior, while test setup succeeds. If Selenium or the browser driver is unavailable, record the environment failure and continue with the repository's available GUI mechanism.

- [ ] **Step 3: Add the semantic card structure and workspace action**

In `index.html`, keep the existing reserved slot and add only any necessary status or heading structure there. In `commentary.js`, construct source-derived text with DOM text APIs, label the card **Tyndale Study Notes**, show the current passage, note headings/bodies, attribution, expandable full introductions/long notes, and a button wired to `BHFStudyActions.openWorkspaceTab("commentary")`. Do not use focus or scroll methods.

- [ ] **Step 4: Style the card for desktop, tablet, and mobile**

In `companion.css`, use the existing surface, spacing, border, and typography variables. Ensure text wraps at narrow widths, native disclosure controls stay visible, the card does not create a nested scroll area, and the responsive layout has no horizontal overflow.

- [ ] **Step 5: Make the updated reader script available offline**

In `index.html`, bump the `commentary.js` asset query version. In `sw.js`, bump the cache version and include `/static/commentary.js` in `STATIC_ASSETS`. Keep commentary API cache rules unchanged.

- [ ] **Step 6: Run frontend and Tyndale GUI tests**

Run: `npm test`

Run: `pytest tests/gui/test_study_companion.py -k tyndale -q`

Expected: PASS for all Node frontend tests and focused browser scenarios, including mobile and accessible navigation.

- [ ] **Step 7: Commit the presentation and browser coverage**

Commit the template, CSS, service worker, frontend layout, and GUI test changes as `feat: present contextual Tyndale study notes`.

### Task 4: Full verification, review, and delivery

**Files:**
- Verify all changed files and commits on `feat/bhf-tyndale-first-class-ui-02`.

**Interfaces:**
- Consumes: the completed implementation and tests from Tasks 1–3.
- Produces: a pushed review branch with no PR, merge, or deployment.

- [ ] **Step 1: Run required project verification**

Run: `npm test`

Run: `pytest tests/test_tyndale_study_notes.py tests/test_commentary_retirement.py tests/test_vercel_packaging.py tests/test_web_app.py -q`

Run: `pytest tests/gui/test_study_companion.py -k tyndale -q`

Run: `python tools/validate.py framework/`

Expected: all commands pass; report any environment skips or pre-existing failures precisely.

- [ ] **Step 2: Review the entire diff and repository state**

Run: `git diff --check`, `git diff --stat`, `git diff`, and `git status --short --branch`. Confirm no CKL/source-data/database artifacts or generated local data changed, all user-required cases are covered, and retired `/api/bhf-commentary` behavior remains intact.

- [ ] **Step 3: Push the feature branch**

Run: `git push -u origin feat/bhf-tyndale-first-class-ui-02`.

Expected: the branch and its commits are available on origin; do not open a PR, merge, or deploy.

## Self-Review

- **Spec coverage:** Task 1 covers book identity, the chapter-query fallback, and unchanged API response shape. Task 2 covers automatic chapter/verse synchronization, single/range selection semantics, prioritization, cache sharing, restored selections, asynchronous races, and unavailable states. Task 3 covers introductions, expandable notes, attribution, full-workspace access, offline script availability, responsive layout, and accessibility. Task 4 covers the named test suites, validation, diff review, and push-only delivery.
- **Step scan:** Each task has red, green, then commit steps; integration verification is isolated in Task 4.
- **Type/interface consistency:** `loadPayload(book, chapter)` shares the existing JSON payload; public `BHFCommentary.loadChapter/focusSelection/clearSelection` methods remain available.
- **Review focus:** All five failure groups above have tests assigned to the task that owns their behavior.
- **Proportion:** The plan names the files and behavior boundaries without prescribing implementation bodies beyond the selection/cache constraints fixed by the design.
