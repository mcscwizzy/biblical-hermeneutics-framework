# BHF UI-02: Tyndale First-Class Reader Integration

## Intent

Make published Tyndale Open Study Notes visible in the Study Companion as the
reader changes passages. Readers should see the current chapter's relevant
notes next to Ask BHF without opening another tab, while keeping the existing
Tyndale workspace tab as the full notes browser.

## Goals

- Show a book-specific introduction on chapter 1 when no verse is selected,
  preferring a full `book_introduction` and using a published
  `book_introduction_summary` when present.
- Show relevant chapter-level notes on other chapters without a verse selection.
- On verse selections, show only notes whose Scripture anchors overlap the
  actual normalized selection, including non-contiguous `selectedVerses`.
- Keep note ordering readable, with directly matching notes ahead of wider
  passage notes. Keep source attribution, accessible expand/collapse, and an
  action to open the full Tyndale workspace.
- Prevent stale responses and restored selections from losing or mismatching
  their Tyndale context.
- Keep the existing API and read-only database model, and exclude
  unbooked/unanchored entries from chapter lookup when book identity cannot be
  proven.

## Non-goals

- Rewrite, regenerate, or change Tyndale source text, licenses, attribution,
  importer output, or database schema.
- Change CKL research, Narrative Explorer, Ask BHF, personal study features,
  retired BHF Commentary routes, or workspace persistence identifiers.
- Add a new Tyndale API endpoint or require a new external service.

## Constraints

- Start from the freshly fetched `origin/master` after UI-01 is merged.
- Preserve `/api/commentary/{book}/{chapter}` response compatibility and the
  SQLite repository's read-only access.
- Use the UI-01 Study Companion hierarchy and reserved
  `data-companion-tyndale-card-slot`.
- Preserve the Tyndale workspace tab and its existing behavior.
- No automatic scrolling or focus movement may interrupt Scripture reading.
- Unavailable or offline data must produce a clear, non-misleading state.

## Approaches

1. **Share the existing chapter API/cache and filter against reader selection
   (chosen).** The reader already loads the chapter notes, and the API already
   returns anchored entries. A shared cache and in-flight request avoid
   duplicate retrieval; the client can apply the exact `selectedVerses` set
   without changing the API. This also keeps the full workspace and contextual
   card in sync.
2. **Request a verse-range payload for each selection.** This can reduce
   payload size, but it introduces extra requests for non-contiguous
   selections, can duplicate the chapter request, and requires client filtering
   for the actual set semantics anyway.
3. **Add a separate introduction or card endpoint.** This isolates the card
   response, but duplicates lookup behavior and adds API surface for data the
   existing chapter response can supply.

The user approved approach 1. It best satisfies API compatibility, request
reuse, and selection semantics.

## Design

### Retrieval and book identity

Keep canonical book normalization in `CommentaryService`. In
`CommentaryRepository.lookup_chapter` and `count_chapter`, require a matching
anchor book for every returned record. Remove the unanchored
`book_introduction`/`profile` fallback because an entry with no book anchor
cannot be safely assigned to the selected book. Keep chapter overlap rules,
read-only connections, row shape, API response fields, and passage lookup
contract intact.

### Reader synchronization and caching

Use `BHFStudySelection` as the active selection source. Share chapter payloads
and in-flight requests between `BHFCommentary.loadChapter` (the full workspace)
and the contextual card. Render only when the response key still matches the
current book/chapter/selection generation. A chapter change invalidates the
previous card immediately; a restored verse selection remains attached to its
chapter when `loadChapter` runs. Do not scroll the Scripture reader.

### Contextual card

Render into the existing hidden slot between Ask BHF and Dig Deeper. Identify
the source as **Tyndale Study Notes**, show the current reference, note heading,
body, source attribution, and a button that opens the existing commentary tab.
Use native `<details>/<summary>` for long material and introductions; retain a
short readable preview and put full published introduction text inside the
expandable region. When an explicit published summary exists, use it as the
preview; otherwise use an excerpt of the published introduction, without
rewriting its wording.

For chapter 1 with no verse selection, show only introduction records anchored
to the selected book, preferring the full introduction. For other chapters
with no verse selection, show anchored chapter-level notes and suppress book
introductions. For verse selections, include anchored records whose covered
verses intersect the selected verse set; use each selected verse rather than
the start/end envelope for non-contiguous selection. Rank exact/narrow matches
ahead of broader overlapping notes. If no matching entry exists, say that no
verse-specific Tyndale note is available for this selection and point to the
full workspace for broader notes. Never say that the book has no Tyndale
information.

### Accessibility and responsive layout

Give the card a heading and a named section, keep interactive disclosure
controls keyboard-operable, and announce loading/result changes concisely
without moving focus. Apply the existing companion surface styles at desktop,
tablet, and mobile widths; avoid a nested scrolling region.

## Verification

- Python repository/service/route tests prove matching Genesis/Ruth
  introductions, exclusion of unanchored cross-book records, and unchanged
  response contracts.
- Frontend tests cover intro/chapter/verse selection rendering, actual
  multi-verse semantics, note ordering, restoration, request reuse, races, and
  unavailable states.
- GUI tests cover Genesis 1, Ruth 1, a later chapter, single/range selections,
  rapid changes, restored selections, missing/offline data, full workspace
  access, mobile sizing, and screen-reader-friendly controls.
- Run `npm test`, relevant Python and GUI tests, `python tools/validate.py
  framework/`, `git diff --check`, and inspect the complete diff and final
  branch state before delivery.
