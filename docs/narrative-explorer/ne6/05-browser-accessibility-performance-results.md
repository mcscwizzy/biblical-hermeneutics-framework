# NE-6 Browser, Accessibility, Offline, and Performance Results

## Actual browser environment

The integration suite uses real Firefox 155.0.1 through Selenium and geckodriver 0.37.1; it does not treat a DOM shim as browser verification. Firefox is run at a desktop viewport of 1440 × 1100 and a mobile viewport of 390 × 844. The map tests assert the app is not in test mode and that the bundled Leaflet runtime is present.

Automated browser scenarios cover:

- Desktop Companion dock and passage-scoped Explorer opening.
- No Explorer or Maps API requests while reading with Explorer inactive.
- Garden evidence, bibliography/source provenance, authored one-way relationship, and accessible evidence-trail landmarks.
- Browser Back/Forward through the trail, connected CKL subject, and linked Genesis 1 passage.
- Three-hop trail behavior and return to Genesis 2:8 with the original selected verse, translation, and focus target restored.
- Eden's original record ID, unknown identification confidence, withheld-map explanation, absence of stored numeric coordinates in reader content, and general Maps fallback.
- Maps panel opening/closing, exact focus outcomes for not-found, unsupported, failed, and unavailable targets, retry, general Maps browsing, and focus restoration.
- Mobile Companion peek → study → full sheet, Explorer access, Explore → Maps collection card, navigator/details controls and `aria-expanded`, map close, and responsive overflow.

The verified evidence-trail and return-to-origin checks passed in Firefox. The current Maps-data source set contains no strictly displayable passage-linked point or identified route, so the positive browser `selected` focus outcome could not be exercised without violating the physical-identification contract. Its exact-target success contract is verified by the focused frontend test; real-browser checks exercised `not_found`, `unsupported`, `unavailable`, and `failed`. The live online retry returned HTTP 200 for map catalog/place/route data but still produced the controller's truthful `failed` state for the nonexistent test target; the app did not claim selection. Eden's physical uncertainty and recorded source name/URL were inspected in the actual browser.

In the mobile screenshot, the Maps panel was open and its catalog status still read “Loading map catalog…”. The mobile run exercised the navigator/details controls and closed Maps with focus restoration while the map load was pending; it did not verify mobile catalog completion. The desktop browser flow and the 17 map/archaeology API compatibility tests verified the corresponding online data paths.

## Accessibility and responsive results

Firefox assertions inspect landmark and state semantics: the evidence trail is a named `nav`; trail controls are exposed through a named navigation group; map status uses `aria-live="polite"`; Companion full/peek and Maps navigator/details controls expose their expanded state; and map closing restores keyboard focus to Browse maps. Return-to-origin restores focus to the originating evidence item. The mobile Maps path uses the Explore collection card because the legacy workspace tab toolbar is intentionally hidden on that Companion surface.

Horizontal document overflow is checked at the desktop and mobile viewport sizes. These are browser DOM and focus checks, not an assistive-technology audit. No real screen reader was available for this run, so spoken labels, reading order, and announcements with NVDA/JAWS/VoiceOver remain unverified. The viewport is a Firefox mobile-size emulation, not a physical phone/tablet test.

## Request, render, and offline measurements

One real Firefox sample recorded:

| Measurement | Observed |
| --- | ---: |
| Explorer requests before opening the feature | 0 |
| First Genesis 2:8 Explorer response (cold JSON fallback) | 80,285 ms; 131,228-byte payload; 1 network request |
| Later Genesis 1:1–31 responses | 2,575 ms and 2,187 ms; 262,906-byte payload each |
| Later Genesis 2:8 responses | 3,095 ms and 3,847 ms; 131,228-byte payload each |
| Initial overview rendering | 10 ms; 442 DOM nodes added |
| Map API requests during explicit Maps status/retry/browse interaction | 12 |

The worktree has no canonical-library SQLite index; read-only canonical configuration falls back to the existing JSON library. The first request is therefore a cold-start sample and is much slower than later in-process requests. NE-6 adds no eager request, external geocoder, persistent cache, or map-data load while the feature is inactive. The current cold-start response time is recorded as a performance risk for future validation; building a new index is outside this transaction.

Offline behavior is automated with Firefox's online flag and rejected map fetches, not by disabling the host's network interface. The test verifies `unavailable`, an online retry control, subsequent fresh HTTP requests, and a final status that still does not claim selection. Existing PWA/service-worker offline contract tests also run; no new persistent map cache is introduced. Real airplane-mode/device offline behavior and a production service-worker cache install were not tested.

## Test results

The focused Python projection/API/map/archaeology/Companion/read-only suite completed with **143 passed, 8 skipped**. The eight skips are existing `tests/test_companion_context.py` cases explicitly marked for removed web-runtime presentation-inference routes. A separate projection run after the route control fixture was added completed with **53 passed**. The selected map/archaeology API compatibility run completed with **17 passed**. The real Firefox Selenium suite completed with **3 passed** (desktop, mobile viewport, and live Acts 7/Joshua 1). The frontend Node test runner completed with **12 test files passed, 0 failed**.

Python compilation passed with bytecode redirected to `/tmp`; JavaScript syntax checks and `git diff --check` passed. Pytest cache writes were disabled for the real-browser run because the managed worktree does not allow cache writes. The actual Firefox desktop and mobile run result and final protected-database digest are recorded in the final NE-6 report.
