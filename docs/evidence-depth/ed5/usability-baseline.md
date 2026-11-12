# ED-5 usability baseline

## Method and limits

This is an expert/heuristic review of source, presentation, existing tests,
and deterministic reader projections. No people were recruited, no
comprehension or satisfaction ratings were collected, and no observations are
attributed to human participants. Scripted projection checks describe
retrieval and behavior only.

## Before-state measures

| Measure | Baseline evidence |
|---|---|
| Locate exact passage evidence | ED-4 tests established deterministic passage projection and exact applicability; the new 12-case suite measures exact record/anchor discovery. No click count is claimed for the current environment. |
| Navigation depth to source | Existing reader disclosures require opening the relevant evidence details; ED-4 Selenium checks found one native disclosure from the selected record to source metadata. Current browser interaction count was not remeasured. |
| Source disclosure | Existing contracts and ED-4 acceptance cover source IDs, title, author, publisher/year, locator, source type, draft state, and mobile long-locator wrapping. |
| Duplicate display | ED-4 browser acceptance reported one record after additional-record disclosure; selected projections check the expected record identity. |
| Review and uncertainty | Existing presentation exposes draft/human-review and dispute/certainty metadata; selected cases include disputed and abstract-limited records. |
| Empty result | A completed no-eligible CKL response had category-level “No linked records returned” wording, without an overview-level statement that this was BHF coverage rather than passage significance. |
| Keyboard/focus/mobile | ED-4 recorded 1440×1200 desktop, 390 CSS-px Chromium device emulation, 320px source wrapping, keyboard disclosures, history, and focus restoration. These are inherited test results, not a new ED-5 browser run. |

## Current browser environment

At this run, `BHF_WEBDRIVER_URL` and `BHF_GUI_BASE_URL` were unset and the
container had no local Chrome or ChromeDriver. The ED-5 browser acceptance
could not be reproduced. ED-4's measured 390px Chromium results are useful
historical evidence but do not validate the new DOM/CSS in ED-5. Manual
comprehension, touch use, contrast sampling, reduced-motion behavior, and
screen-reader behavior remain open for a browser-enabled review.

## Reproducibility

The repository evidence is in `docs/evidence-depth/ed4/reader-acceptance.md`,
`docs/evidence-depth/ed4/validation-results.md`, and
`docs/evidence-depth/ed3/reader-acceptance.md`. The new deterministic journey
suite is documented in [reader journeys](reader-journeys.md). Do not interpret
the number of projection cases as a usability score.
