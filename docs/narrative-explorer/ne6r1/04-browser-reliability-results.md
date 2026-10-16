# NE-6R1 — Browser Reliability Results

## Environment and mobile Maps flow

Real-browser checks ran in Firefox 155.0.1 with Service Worker v49 controlling the application. Requesting a 390 × 844 window produced a 500 × 758 CSS viewport in this headless environment. The document width was 488 px, so there was no horizontal overflow at the actual viewport width. The browser was not treated as a 390 px device emulation.

The passage panel's timeline-only catalog request completed with HTTP 200, `include_records=false`, 713 response bytes, 22 ms to response headers, and 1 ms to read and parse JSON in the final run. A separate earlier run measured 87 ms and 2 ms. The full browse catalog remains available for browse mode and offline installation. John 2 then returned 69 compact markers and 2,900 route bytes. The selected marker was `openbible-aac6cda` (`Angle`); selecting it fetched 32,842 bytes from `/api/maps/related-passages-for-place?place_id=openbible-aac6cda`, rendered its grouped related passages, and kept its exact stable ID in the KML link. The selection-to-detail observation was 581 ms; Resource Timing reports zero body sizes under this worker, so this duration is the page's elapsed-time measurement rather than a network transfer-size measurement.

The first John 2 map panel open took 33,846 ms. Its compact places request waited 33,728 ms for response headers and then took 7 ms to read and parse the 187,007-byte body. Routes waited 33,763 ms for headers and parsed in 1 ms. Later warm John 2 requests took 290–299 ms for headers and 4–6 ms to read and parse. A warmed-suite panel open took 3,444 ms, including a 3,332 ms wait for places headers. The first delay is a server-side first-lookup/initialization issue, not JSON parsing or transfer of the compact payload; the available instrumentation does not isolate its internal server stages. It remains an explicit performance issue.

The test opened 3 John 1 and showed zero markers, returned to John 2 and showed the same 69, stopped the server, then confirmed a cached-data warning while Maps remained available. After restart and retry, the warning cleared and online data refreshed. The browse-mode Firefox test completed catalog loading, searched for Jerusalem, selected a result, showed details, closed Maps, and restored focus to the Maps browse control. Catalog controls remained usable and measured touch targets met the 44 px minimum. The document had no horizontal overflow.

## Offline pack and browser storage

The Maps offline pack installed successfully in 10,873 ms with seven responses. Firefox reported:

| Store | Entries | Bytes |
|---|---:|---:|
| Maps Cache Storage | 11 | 6,492,067 |
| Maps local-storage keys | 4 | 447,240 |
| IndexedDB Maps API rows | 5 | Each below 512 KiB |

The full 3,037,361-byte browse catalog and 3,005,684-byte biblical-place catalog remain available in the explicit offline pack. The compact 187,007-byte John 2 response and selected 32,842-byte details response were cacheable. The 21,687,196-byte full John 2 response and the 6.27 MB raw offline-pack envelope were not stored as duplicate entries. The full pack's useful individual responses remain available offline; no whole-pack response is stored in IndexedDB or local storage.

## Full John 2 body replay

The test first captured the actual full legacy endpoint response from the protected read-only API, checked its 21,687,196-byte length, valid JSON, 69 markers, and SHA-256 `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f`. The exact parsed object was then served through the real FastAPI route for repeated browser consumption. Each run checked status, byte count, and exact ordered marker IDs. The Service Worker cache began fresh and the replay URLs were confirmed absent from Cache Storage. A separate Firefox profile with Service Workers disabled was the control.

| Mode | Successful parses | Failures | Median headers | Median body read | Median JSON parse | Median total |
|---|---:|---:|---:|---:|---:|---:|
| Service Worker v49 active | 5/5 | 0 | 450 ms | 175 ms | 113 ms | 741 ms |
| Service Worker disabled | 5/5 | 0 | 490 ms | 529 ms | 130 ms | 1,152 ms |

Individual runs varied, especially in the worker-disabled body's transfer time (one body read took 12,252 ms). These results show that the earlier Firefox body-consumption failure did not reproduce in five repeated runs in either mode; they do not guarantee reliability on every machine. The replay intentionally isolates browser body consumption from repository latency. Three direct API captures took 42,047, 44,553, and 71,556 ms to response headers, followed by 10,056, 10,523, and 9,929 ms to read the body. That large variance remains separate from client JSON parsing. Firefox Resource Timing does not expose useful encoded sizes for these Service Worker responses, so the test uses explicit `fetch` header, `response.text()`, and `JSON.parse()` timers.

## Other Firefox acceptance coverage

The Firefox suite covers enabled Maps navigation, map rendering and selected-place details, feature-flag-off request suppression during ordinary reading, focus close/reopen, keyboard controls, synthetic isolated place and route selections, wrong-ID/kind rejection, supported and unsupported result states, real geography controls, and offline status/retry. A synthetic detail fixture forced one HTTP 503, confirmed the panel disclosed that its authored links were incomplete, clicked retry, and verified the second exact-place request displayed the complete Genesis 2:8 relationship. Browser-injected fixtures are labeled test data and do not enter the study database, source manifest, or production map catalog.

The real-source controls retain Eden's withheld point, uncertain Horeb/Sinai identification, the Acts 7 Nile source ID and Acts 7:19 anchor, and the Joshua 1 Negeb record and Joshua 1:4 anchor. No screen-reader application was available; DOM live-region, accessible-name, keyboard, and focus checks are not reported as assistive-technology verification.

## Limits

The browser measured a 500 px viewport, not the requested 390 px CSS viewport. The map API fetch wrapper measured response-body consumption and parsing; browser Resource Timing under the Service Worker returned zeros for encoded and decoded size. The cold request's internal server-stage breakdown remains unmeasured. These limits are carried into release readiness rather than inferred away.
