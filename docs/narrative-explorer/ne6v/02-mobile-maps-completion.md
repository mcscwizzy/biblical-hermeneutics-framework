# NE-6V Mobile Maps Completion

## Browser result

The Firefox mobile-sized Companion flow completed the Maps catalog and a real catalog search. Explicit browser waits observe the catalog request's terminal result and status state; the test does not use a sleep as evidence of completion.

The run opened the mobile Companion, selected Explore, opened the Maps collection card, and waited until `/api/maps/catalog` completed. It returned HTTP 200 and the loading status became hidden. The test then opened the navigator and details panels, submitted a Jerusalem search with Enter, waited for `/api/maps/search` to finish, selected its result, and checked the displayed Jerusalem details and KML link.

| Check | Firefox observation |
| --- | --- |
| Headless viewport | `500 × 758` CSS pixels. Firefox clamped the requested 390-pixel width to 500. |
| Catalog | `/api/maps/catalog` completed with HTTP 200; loading status was hidden afterward. |
| Search | `/api/maps/search` completed with HTTP 200; one or more results appeared and the selected detail heading was `Jerusalem`. |
| Controls | Navigator/details controls opened and closed, exposed their `aria-expanded` state, and remained usable after selection. |
| Reopen/focus | Closing Maps returned focus to `map-browse-button`; reopening Maps completed without remaining in loading state. |
| Horizontal overflow | `document.documentElement.scrollWidth` did not exceed `window.innerWidth`. |
| Touch targets | Navigator `108.57 × 64`, details `83.62 × 64`, close Maps `117.38 × 44`, search `157.08 × 44`, and search result `314 × 124.7` pixels. Every measured target met the 44-pixel minimum used by this interface. |

The NE-6 CSS had search and close controls at 43 pixels in this viewport. The narrow responsive rule now sets those controls to at least 44 pixels. No map loading-state code change was needed: the earlier test ended while the request was still in flight and therefore had not established a terminal state. The bounded wait now distinguishes success, meaningful error, and timeout.

## Accessible status and focus

The map status uses `aria-live="polite"`. Firefox checks verified that the success path removes the loading status, navigator/details controls expose expanded state, and closing Maps restores keyboard focus to the opener. The mobile browser assertions are DOM and keyboard checks, not spoken-output evidence.

No screen-reader environment was available: Orca and speech-dispatcher commands were installed, but the run had no display/virtual display and neither accessibility service was running. A basic real assistive-technology check remains an NE-7 release-acceptance task. This report does not claim screen-reader verification.

## Scope limits

This was headless Firefox at a mobile-sized viewport, not a physical device. Firefox's width clamp is recorded above. The test verifies the Maps catalog and search requests in the running local application and does not establish network behavior on a mobile carrier or production host.
