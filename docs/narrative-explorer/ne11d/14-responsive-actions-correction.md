# NE-11D5 — Study Companion Responsive Action Correction

## Baseline

- Fetched `origin/master` at `ee926de3bf55039ca26e710025f20da2f0b1737c`.
- Confirmed NE-11D4 commit `945c9feb5c528cef35b27434033f34ad2e133e34` is an ancestor of that baseline.
- Created branch `fix/ne11d5-companion-mobile-actions` from the fetched baseline.
- Read the [NE-11D4 feature-gate closure](13-feature-gate-closure.md).

## Root cause

The `.companion-overview-actions` row used a non-wrapping flex layout. The existing narrow-screen rule stretched its flex items but kept all four actions on one line. At 320px, the row had 290px of client width and 415px of scroll width; at 390px it had 360px and 415px. “Compare Translations” occupied x=304.1–430.4px, beyond the row's right edge at x=305px or x=375px. The overview pane clips horizontal overflow, so the button was partly hidden.

The baseline Chrome run showed no clipping at 768px or 1440px.

## CSS correction

At widths up to 680px, [companion.css](../../../bhf_web/static/styles/companion.css) now lays out the overview actions in a two-column grid with `minmax(0, 1fr)` tracks. Each button fills its track, can shrink below its intrinsic width, wraps its existing label normally, and has a 44px minimum height. Grid placement keeps the current DOM and keyboard order.

```css
@media (max-width: 680px) {
  .companion-overview-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
  }

  .companion-overview-actions > button {
    width: 100%;
    min-width: 0;
    min-height: 44px;
    flex: none;
    white-space: normal;
    text-align: center;
  }
}
```

The 320px test provides 141px per button, which fits every label with natural wrapping, so a one-column fallback was unnecessary. No button, label, event handler, feature flag, route, or evidence logic changed. Safe-area padding and mobile sheet rules remain in place.

## Before and after measurements

Widths below are CSS pixels. Row and overview values are `clientWidth / scrollWidth`; document values are `clientWidth / scrollWidth`. Enabled and disabled feature-flag runs produced the same container widths.

| Viewport | Before row | After row, flag on | After row, flag off | After overview | After document |
|---:|---:|---:|---:|---:|---:|
| 320 | 290 / 415 | 290 / 290 | 290 / 290 | 318 / 318 | 320 / 320 |
| 390 | 360 / 415 | 360 / 360 | 360 / 360 | 388 / 388 | 390 / 390 |
| 768 | 708 / 708 | 708 / 708 | 708 / 708 | 736 / 736 | 753 / 753 |
| 1440 | 830 / 830 | 830 / 830 | 830 / 830 | 874 / 874 | 1425 / 1425 |

At 320px, enabled action bounds are x=15–156px and x=164–305px on each of two rows; button heights are 64px as the longer labels wrap. With the flag off, the three actions occupy the first two grid cells and the first cell on the second row. At 390px, enabled actions use those same two columns at x=15–191px and x=199–375px; the second row grows to 64px for wrapped labels. At 768px and desktop, all visible actions remain within the row and overview container. Browser screenshots for both flag states and all four widths are in `/tmp/bhf-ne11d5-review/`; they are temporary review artifacts and are not tracked.

## Responsive and interaction results

The focused Chrome/Selenium regression uses the real BHF app and its checked-in CKL data. It measures row, overview, document, and button rectangles at all four widths, checks horizontal and vertical text overflow, accessible names, focus-ring bounds, and keyboard traversal.

| Feature flag | Actions | 320px | 390px | 768px | 1440px |
|---|---:|---|---|---|---|
| Enabled | 4 | Pass | Pass | Pass | Pass |
| Disabled | 3 | Pass | Pass | Pass | Pass |

The checks also confirmed:

- Save Passage remains disabled before passage selection with its existing `aria-disabled` and accessible label. Selecting Jonah 1:17 enables it; saving leaves the selected passage unchanged and restores the existing saved/disabled state.
- Add Note opens its resource and leaves Jonah 1:17 selected.
- Explore the Narrative and Compare Translations open from the overview and return with focus restored to their triggering buttons at every tested width.
- Keyboard Tab traversal follows the visible controls' DOM order. Each enabled action receives a visible `:focus-visible` outline whose bounds remain inside the overview and Companion pane.
- At 320px and 390px, the action buttons meet the 44px minimum touch height; all measured controls are at least 38px at 768px and desktop.
- The row, Companion overview, and document have no horizontal overflow. No labels were hidden or shortened.

The compact screenshot artifacts are outside Git. The actual screen-reader check remains **MANUAL**: this run used headless Chrome and did not include a spoken NVDA/Orca session.

## NE-11 regression and integrity results

- `tests/gui/ne11d1` — **30 passed**. This includes real CKL-backed Jonah 1:17 → Matthew 12:40 and Genesis 1:1–5 → John 1:1–5 journeys and returns, narrow route inspection, keyboard Enter/Space/Escape and focus restoration, evidence-source disclosure, and mobile Companion open/close interactions.
- `tests/test_narrative_explorer_passages.py` and `tests/test_ne11d3_support_safety.py` — **all passed**. The 44 bridge identities remain unchanged, all seven held candidates remain held, and reviewed support-pair restrictions remain enforced. The real CKL handoff checks also retain the three-card presentation limit. No newly confirmed relationship appeared.
- `npm test` — **14 passed**.
- Focused responsive test: `tests/gui/ne11d1/test_ne11d5_responsive_actions.py` — **2 passed**, covering the full width matrix with the flag enabled and disabled.
- Six selected existing Companion GUI checks plus the passage and support-safety tests — **34 passed, 1 failed**. The failure was `test_browser_back_unwinds_resource_then_companion_overview`, which expected `study` after Back and observed `peek`. The same failure reproduced on clean `origin/master` at `ee926de3`; it is pre-existing and unrelated to this row layout.

No CKL data, NE-9C curation, NE-10 bridges, evidence model, presentation ranking, route matching, production configuration, or CI governance changed.

## Remaining release gates

The manual spoken screen-reader check remains open. The separate NE-11E findings recorded in the closure report also remain open: structured-output failures, a CKL governance issue, sanitizer findings, and First Corinthians ranking failures. They were not modified or reclassified by this layout correction. This branch is ready for review; it has not been merged or deployed.
