# NE-7R1 browser reader failure analysis

## Reproduced baseline

The NE-7 general Firefox run had two failing tests:

| Test | Browser symptom | Browser request/state at failure |
|---|---|---|
| `WebUiSeleniumTests.test_reader_search_selection_navigation_and_next_chapter_are_mobile_usable` | Reader remained at “Loading Scripture text…”; the selection was empty and no chapter heading rendered. | `GET /api/offline/packs/study` entered FastAPI while the browser also started `/api/offline/manifest`, `/api/translations`, and `/api/translations/kjv/offline-data`. Those dependencies had not completed when the reader wait expired, so `/api/bible/John/1?translation=kjv` had not yet been initiated. |
| `WebUiSeleniumTests.test_map_browse_search_is_available_without_selection` | Maps stayed in its “Searching the map catalog for Jerusalem…” state and no Jerusalem result appeared before the wait expired. | The browser initiated `GET /api/maps/search?q=Jerusalem&kind=all&limit=30`; FastAPI entered the route, but no response headers arrived before the UI wait expired. The browser trace showed an outstanding search and zero results. |

The first request lifecycle was traced from browser `fetch` creation, through Service Worker state, ASGI request entry, route timing, response headers/body, JSON consumption, and page state. A clean-profile reproduction with Service Workers disabled still stalled, so Service Worker interception was not the cause. The Service Worker was active in the final full-suite run, which passed.

The correlated pre-fix cold-reader reproduction recorded these stages (server epoch timestamps; `browser-N` identifiers were forwarded from the browser fetch wrapper):

| Time / request ID | Stage | Observation |
|---|---|---|
| `1792208724.0289`, `browser-2` | Browser fetch and FastAPI entry | `GET /api/offline/packs/study`, with `Accept: application/json` and `X-BHF-Refresh: true`, entered the async endpoint. Synchronous pack construction ran inline. |
| Until the 37.68-second browser timeout | Handler and response | No response headers or body completion were logged for the pack request before the browser fixture failed. This is a pending request, not a completed response with a stuck UI. |
| `1792208754.2449`, `browser-3` | Queued request entry | `GET /api/offline/manifest` entered about 30.2 seconds after pack construction began and returned HTTP 200 in about 90 ms; `/api/translations` followed. Translation setup and `/api/translations/kjv/offline-data` had not completed in time to initiate `/api/bible/John/1?translation=kjv`. |
| `1792209603.2157`, page-local `browser-8` | First-use Companion context | `GET /api/study/companion-context?book=John&chapter=1&translation=kjv` began about 10.7 seconds before the Maps search and completed in 37.96 seconds. It overlapped the Maps request. |
| `1792209613.9533`, page-local `browser-6` | Maps search fetch and route entry | With Service Workers disabled, `GET /api/maps/search?q=Jerusalem&kind=all&limit=30` entered the server. No response headers arrived during the UI assertion window. The server later recorded HTTP 200, a 1,681-byte body, and completion 29.79 seconds after entry—after the failed browser wait. |

The instrumentation records fetch initiation, method and URL, non-sensitive `Accept`/refresh headers, response-header delivery where observed, body reads, JSON parse completion, reader-selection initialization, visible chapter heading, map query/result state, Service Worker state, and server request/handler/body timings. Browser `browser-N` IDs are page-local, not global. The Maps trace is reported separately from its eventual server completion so it is not mistaken for a settled UI assertion.

## Root causes

The optional `study` offline pack was installed automatically on a new profile. The async `/api/offline/packs/study` handler called synchronous `build_offline_pack` inline. It occupied the FastAPI event loop for about 29.9 seconds, then serialized a 15,099,413-byte JSON body. The browser’s translation setup could not finish, so the reader never issued its Scripture request. The Maps failure was a separate slow route: its async handler called synchronous catalog/search code inline, and the server spent 29.79 seconds from request entry through response-body completion. That blocked the event loop while it ran. First-use Companion-context JSON initialization overlapped the request, but the original trace did not instrument map-service sub-stages, so it cannot establish whether database readiness, lock contention, catalog construction, or another map operation accounted for the full interval. It does establish that the Maps request eventually returned after the test’s wait expired; this was not a browser fetch that remained pending indefinitely. A direct Python request returning HTTP 200 did not reproduce either browser lifecycle because it did not share the browser’s running process, profile, and worktree configuration.

The browser fixture used a disposable study database and per-test reader settings. Its worktree did not contain the ignored `.bhf/ckl.sqlite` file. The default CKL configuration selected SQLite at `.bhf/ckl.sqlite` with `fallback_to_json`; because that file was absent, Companion initialization loaded the JSON inventory. The main checkout did contain a verified read-only index. The browser and direct Python observations therefore did not use the same CKL path or backend. Exact translation inventories and process state were not established as identical for the earlier standalone Python probe.

The JSON fallback was a contributing first-use cost, not the direct cause of the blank reader: the Bible request depends on translation setup, while the event loop was occupied by offline-pack generation. For Maps, the directly observed application defect was synchronous catalog/search work on the async request path. Its precise internal 29.79-second stage remains unresolved. The dedicated geography fixture had disabled automatic optional-pack installation for its Maps case, explaining why its startup did not match the general smoke fixture.

## Changes and regression coverage

- `/api/offline/packs/{pack_id}` now runs pack construction in Starlette’s thread pool.
- Optional offline packs are no longer installed automatically by default. Users can still install them from the existing controls; deployments can explicitly opt in with `BHF_AUTO_INSTALL_OFFLINE_PACKS=true`.
- Maps catalog and search work now runs in the thread pool. The browse panel requests only the period catalog (`include_records=false`, 713 bytes in Firefox) because it does not use the full record collection; search still uses `/api/maps/search`. In the final general Firefox run, the API returned HTTP 200 in 4.86 seconds and the UI rendered one Jerusalem result. This verifies completion, while leaving the slower internal map-data stage unexplained.
- The general Firefox fixture now isolates reader settings and translation registry state, waits for the selected Companion context to settle before teardown, and records completed browser fetches and rendered reader state.
- New browser regressions prove that a real Bible request and translation change complete while a study pack is being built, the cold reader loads Scripture without optional-pack or Explorer requests, and Maps search returns and renders Jerusalem.
- The mobile drawer test now waits for the CSS transition to reach its final position before measuring it. Its earlier assertion measured the panel during the 180 ms transition.

## Verification

The assertion waits for rendered reader text or the requested Jerusalem result; the traces show those conditions were not reached within the baseline wait, rather than a test waiting on an obsolete condition. Page instrumentation recorded no JavaScript or page errors. Selenium's native browser-log collection returned `HTTP method not allowed`, so a native Firefox console transcript was unavailable; the associated server request trace showed no exception for the late Maps HTTP 200. The general browser fixture used a disposable study DB and temporary translation registry; the worktree had no default `.bhf/ckl.sqlite`, so its CKL configuration took the `fallback_to_json` path. The earlier direct Python API request used a different checkout/configuration and was not an apples-to-apples control. The matched SQLite/JSON timings and first-use stages are recorded in `02-cold-initialization-profile.md`. Final complete suite totals are in `04-integration-regression-results.md`.

The protected study database remained configured read-only. No CKL, Commentary, source manifest, translation, or study-schema data was changed.
