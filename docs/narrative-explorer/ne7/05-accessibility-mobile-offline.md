# NE-7.5 — Accessibility, mobile, and offline behavior

## Keyboard and focus

Headless Firefox keyboard checks used Enter and Space on the selected passage's Explore the Narrative action. Both opened the Explorer and its six sections. The browser/geography tests also exercised trail navigation, browser Back/Forward, close/open, status text, map search, and current-step UI. The browser entry test waits until the actual selected book and chapter exist; otherwise the action correctly reports that selection is required. No keyboard trap was observed in the tested Explorer and Maps paths.

Projection and UI tests cover accessible names/roles and the rendered hierarchy, but this is not spoken screen-reader acceptance. The browser smoke suite also exercised current Companion open/close behavior and focusable Maps controls. A human check is still needed for all close/return focus paths, loading/error announcements, and screen-reader reading order.

## Actual assistive technology

**PENDING — no spoken test was run.** The environment has Orca 46.1, `pyatspi`, and speech-dispatcher packages. Attempted `timeout 15s dbus-run-session -- env GTK_A11Y=1 MOZ_ENABLE_ACCESSIBILITY=1 orca --list-apps`; a D-Bus session and AT-SPI registry could start, but the execution environment provides neither `DISPLAY` nor `WAYLAND_DISPLAY`, so there was no accessible Firefox application/window or speech session to test. DOM assertions are not being represented as an AT pass.

### Human-operated check script

Run with a supported desktop session using Firefox + Orca, NVDA + Firefox/Chrome, or VoiceOver + Safari:

1. Open a passage (Genesis 2:8), focus Companion, and activate **Explore the Narrative**.
2. Listen for the panel title, six section names, selected reference, and coverage status. Navigate headings and section controls by keyboard.
3. Open an evidence item. Verify the CKL identity, source attribution, Scripture anchor, confidence/dispute labels, and links are announced in a useful order.
4. Follow an authored connection. Check breadcrumb names, current step, and Back/Forward changes; return to the original passage.
5. Open Maps. Listen for exact selection or `not_found`/`unsupported`/`unavailable`/`failed` status. Trigger a failed detail request, reconnect, retry, and verify the loading and completion/failure announcements.
6. Close Maps and Explorer with keyboard and verify focus returns to the invoking control and the reader's passage/translation remain intact.
7. Repeat with an empty-coverage chapter and with Explorer disabled. Confirm empty-state text and that ordinary reading does not make Explorer requests.

Record OS, browser and exact AT versions, output device, and spoken results for section names, coverage, source detail, trail step, loading/failure, Maps outcome, and return focus.

## Mobile viewport

Firefox 155.0.1 headless clamped a requested **390 × 844 CSS-pixel** window to an actual **500 × 758** viewport. The measured viewport was used in reporting; the 390-pixel requirement is therefore **PENDING**. `/usr/bin/firefox` was the only available browser; Chrome/Chromium/Playwright was unavailable. At the actual 500-pixel width, the tested reader, Explorer/Maps navigator, search and details fit without unexpected horizontal overflow; observed `scrollWidth` was 500. Maps touch controls met the existing 44-pixel target. Desktop layouts were exercised at 1280/1440-pixel browser widths. A true 768-pixel tablet layout was not captured and remains **PENDING** along with the genuine 390-pixel run.

Long citations and every trail state were not manually checked at tablet or 390-pixel widths. Narrow-width acceptance should be repeated in a browser/device that reports the requested viewport unmodified.

## Offline and recovery

Firefox tests covered ordinary cached Scripture navigation, cached resources, Service Worker v49, offline Maps behavior, explicit unavailable-evidence responses, and online reconnect/retry. The observed diagnostic Cache Storage footprint was approximately 6,492,067 bytes over 11 entries; this is a test observation, not a universal quota guarantee. Feature-off testing confirmed ordinary reader loading made no Narrative Explorer/Maps request. No failure was observed to modify study notes, highlights, translation selection, or protected study data.

## Browser test details

- Geography end-to-end: `tests/test_ne6_geography_selenium.py` — 9 passed in Firefox 155.0.1/geckodriver 0.37.1.
- General UI smoke: `tests/test_web_ui_selenium.py` — **2 passed, 2 failed in 182.18 s** with Firefox 155.0.1/geckodriver 0.37.1. The mobile workspace drawer and Explorer keyboard/history/mobile-sheet case passed. Maps browse timed out waiting for Jerusalem results; reader search/navigation timed out waiting for the selected passage heading. The Firefox page contained the reader shell and loaded `htmx-lite.js`, but stayed at “Loading Scripture text...” with empty selection. A direct Python HTTP request to the same local Bible endpoint returned HTTP 200 / 6,041 bytes while the browser-side fetch remained pending. The app used a disposable study DB. Retrying the Maps case with `BHF_DATA_DIR` and protected `BHF_STUDY_DB_PATH` explicitly pointed at the source checkout reproduced the failure (**1 failed in 40.93 s**). Direct Python map search against the same kind of initialized disposable database returns the seeded Jerusalem result. This unresolved Firefox/test-server discrepancy is not attributed to an NE-7 product change.
- Tyndale local fixture case passed.
- Translation comparison preserving selected range passed; Chrome CDP-only mobile case and an offline-page setup case could not run successfully under the Firefox-only test adapter.
