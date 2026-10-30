# UI-03 Performance and Visual Results

## Matched reader comparison

The comparison used the same warmed local Chrome browser path, John 1 selection, feature-enabled Companion entry, and one passage projection request on the UI-02 `origin/master` baseline (`f4b203de`) and the UI-03 branch. It is one matched sample per build; click-to-ready values are wall-clock browser measurements and should be treated as indicative, not a benchmark. Cold request times varied substantially during fixture startup and are excluded.

| Measurement | UI-02 baseline | UI-03 | Change |
| --- | ---: | ---: | ---: |
| Click to Explorer ready | 6,914 ms | 7,292 ms | +5.5% (one sample; within observed timing variance) |
| Projection response duration | 6,688.4 ms | 6,950.4 ms | +3.9% (same request path) |
| Projection response body | 430,833 bytes | 430,833 bytes | unchanged |
| Projection requests | 1 | 1 | unchanged |
| Explorer DOM descendants on initial view | 433 | 60 | 373 fewer (86.1% reduction) |

The redesign does not add a projection request or change the API payload. Its initial view renders the passage header, connection entry, and six topic cards, while the records and source details remain in the chosen focused view. A single pair of browser timing samples cannot establish a performance regression; the click and response deltas were small compared with the cold-start variation observed in the same local environment. No material initial-DOM or payload regression was measured.

## Screenshots

- [UI-02 John 1 desktop](screenshots/before-john-1-desktop.png)
- [UI-03 John 1 desktop](screenshots/after-john-1-desktop.png)
- [UI-03 John 1 connection category](screenshots/after-john-1-connections-desktop.png)
- [UI-03 John 1 mobile smoke capture](screenshots/after-john-1-mobile.png) (500 px Firefox viewport floor)
- [UI-03 Genesis 1 desktop](screenshots/after-genesis-1-desktop.png)
- [UI-03 Genesis 1 focused connection view](screenshots/after-genesis-1-connections-desktop.png)
- [UI-03 Genesis 1 mobile](screenshots/after-genesis-1-mobile.png) (390 px Chrome viewport)

The screenshots come from actual browser sessions, not generated mockups. The before/after John 1 captures show the move from a stacked initial evidence inventory to the concise topic overview. Genesis 1 captures show selected-passage retention and the mobile single-column layout.

## Verification record

- `npm test`: 16 frontend test files passed.
- Targeted Python regression batch: 116 passed across Narrative Explorer projection, API and UI configuration, retired Commentary runtime/retirement, and Tyndale Study Notes/evidence.
- CKL validation scanned 687 objects: 0 errors and 14 warnings. The warnings concern section-status fields in Arad Ostraca, exile-and-return storyline, chiasm, branch prophecy, and abba records; none of those CKL files changed from the UI-02 baseline.
- Packaging and canonical manifest/schema checks: 30 tests passed, with 13 subtests passed.
- Focused browser regression: the Exodus 3 availability/geography journey passed; passage/source/review journey and Companion handoff passed; the desktop/mobile feature-gate browser check passed after its selector was updated for the discovery overview. The two legacy Psalm alias and connection-preview browser regressions passed after assertions were moved into the focused category flow.
- NE-11D browser/GUI journeys: 28 passed in the initial run; five stale inventory-flow expectations were corrected and all five passed on focused rerun. Coverage includes Genesis 1, Jonah/Matthew, Psalm 22's negative route, draft governance, feature gating, keyboard, mobile, and offline behavior.
- The retired Commentary reader browser check passed. The active Tyndale notes/translation comparison browser check skipped because no local Tyndale notes database is available; the Tyndale API and evidence tests passed in the Python batch.
- `git diff --check` and local Markdown-link validation passed. No framework module, CKL record, manifest, source lock, curation, bridge, route schema, or deployment configuration changed.

No backend, projection, route schema, CKL, curation, bridge, source lock, manifest, or production configuration changes were needed. UI-02 response/request compatibility is retained.
