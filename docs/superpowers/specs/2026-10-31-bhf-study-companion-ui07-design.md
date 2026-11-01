# BHF UI-07 — Reader-First Research Consolidation

## Intent

Keep Scripture, personal study, Ask BHF, and contextual Tyndale notes ahead of
research discovery. The passage overview ends with two choices: Explore the
Narrative and Places & Locations. Context summaries and source browsing remain
available through focused, secondary views.

## Goals and boundaries

- Remove the passage overview's Research Tools grid and Advanced Research
  Workspaces list. Keep the separate Explore BHF browse mode and all direct
  research routes.
- Add **Understand the Passage** to the Narrative Explorer overview. Its five
  Companion summaries appear one at a time with the existing recorded support,
  uncertainty, interpretation status, and source disclosures.
- Preserve all six Narrative Explorer categories, Follow a Connection,
  Places & Locations, Tyndale, Compare Translations, Lexicon word study, Ask
  BHF, and personal study actions.
- Keep CKL objects, evidence, source locks, fingerprints, manifests, curations,
  bridges, provenance, Tyndale content/licensing, relationship semantics,
  retired Commentary HTTP 410 behavior, APIs, and deployment configuration
  unchanged.

## Approaches

1. **Focused view in the existing Narrative Explorer session (selected).**
   Store the active contextual topic in the existing bounded Companion history
   state and render it from the cached Companion context. This keeps the
   reader selection and projection session intact, avoids a second projection
   request, and gives browser Back/Forward and Escape the existing behavior.
2. **Five resource cards on the passage overview.** Rejected because it
   recreates the inventory UI-07 removes.
3. **A large collapsed research accordion.** Rejected because it hides the
   inventory rather than making the reader-first overview simpler.

## UX and behavior

The passage overview keeps Personal Study actions, Ask BHF, the synchronized
Tyndale card, and Dig Deeper with exactly two primary entries. On desktop those
entries share a restrained two-column row; on narrow screens they stack.
Explore the Narrative retains Follow a Connection and its six existing
categories. A distinct **Understand the Passage** entry opens a compact topic
selector and one selected summary. A secondary **Browse research sources**
view links to the CKL browser, archaeology library, Maps, Cross References,
Timeline, and other existing passage resources.

The summary view reads only the existing Companion context response. It labels
these as contextual summaries, separate from individually projected
Narrative Explorer evidence. Completed empty, missing summary text, unknown
retrieval, offline, and unavailable states remain distinct. Feature-disabled
installations receive compact inline links to contextual summaries and source
browsing; no third large overview card is added.

## Implementation calls

- Keep the current JavaScript, HTML, CSS, Companion router, context cache, and
  history controller; add no framework or dependency.
- Preserve Explore BHF's independent catalog by moving its existing inventory
  into a browse-mode-only section.
- Add no research API or data changes. Test the rendered views, history state,
  no-duplicate projection behavior, feature-disabled path, and browser journeys.
- Capture the UI-06 overview as the before image and a real-browser UI-07
  overview/context view as after images in the UX report.
