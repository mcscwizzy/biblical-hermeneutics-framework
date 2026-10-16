# NE-6R2 — Browser and Web-App Regression Results

## Firefox acceptance

The Firefox integration module completed with **9 passed in 409.66 seconds** against the local FastAPI app and the protected study DB in read-only mode. The suite exercised Explorer initial loading and Genesis 2:8 trail, John 2 compact Maps, selected-place detail loading, focus acknowledgments, mobile catalog/search/selection, Back/Forward and return-to-origin, cached offline availability/retry, and feature-disabled request suppression. A separate captured diagnostic rerun of `test_firefox_desktop_mobile_trail_maps_fallback_and_offline_retry` passed in 62.43 seconds. Firefox was 155.0.1. This is local browser evidence and does not represent Vercel latency or a 390 px emulated viewport; headless Firefox reported a 500 px CSS viewport.

The captured Explorer browser measurement showed 9,499 ms from request to headers for the first Genesis 2:8 request and 1 ms to transfer its 131,228-byte response. A second run measured 9,686 ms browser header wait. The captured server stage showed 7,114.93 ms in CKL freshness/source fingerprint verification for that request, with 9,440.08 ms total server response-header time. This is a measured Narrative Explorer first-hit cost; it is distinct from the Maps delay.

In the John 2 compact Maps browser test, the first Places request had browser header wait about 3,907 ms and server header wait 3,836.51 ms; warm requests measured about 294 ms in Firefox (280–284 ms server-side in the captured sample). That one outlier spent 3,133.76 ms in `map_place_loading`, while direct matched process-cold Maps measurements were 353–375 ms. The outlier did not reproduce in the direct benchmark. The historic 33-second Maps wait remains unexplained.

## Maps payload and behavior

John 2 compact Maps remains **187,007 bytes**, SHA-256 `991064790c1e215ce69f09b1885818419c49f90e0f3e71dd408e0d24eb35aa32`. The legacy API full-response default remains available and was observed at 21,687,196 bytes with SHA-256 `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f`. Full related passages load only when a place is selected. The Maps Service Worker returns oversized responses without cloning them, and cache budgets remain bounded. The offline pack deliberately caches individual permitted responses; a Firefox run reported 7 pack responses, 6,492,067 Cache Storage bytes across 11 entries, and 447,240 local-storage bytes. It did not store the oversized John 2 response or the raw pack envelope.

The selected-place, focus, offline, and navigation checks passed. No cache fabricated a selected map target. Acts 7 Nile and Joshua 1 Negeb associations remained intact; Eden and Horeb/Sinai uncertainty remained as authored. The full-response compatibility path is slow and large, but the Maps panel continues to request compact mode; no 21.7 MB initial Maps response was reintroduced.

## Full `tests/test_web_app.py` disposition

The earlier NE-6R1 run stopped progressing at approximately 82%. Bounded isolation showed the first non-progressing test was `WebAppTests::test_local_leaflet_vendor_assets_load`. A standalone invocation without the harness workaround did not progress within its 20-second bound; it passed in 1.36 seconds when run with a temporary pytest plugin that schedules a 10 ms asyncio loop heartbeat. The workaround is test-only and not committed. The failure mode is the test event-loop/AnyIO worker wake-up behavior around the static asset check, not a hanging application request or new production change.

The full suite was then run with the heartbeat harness and no tests hidden or deleted. Result: **78 passed, 55 skipped, 2 failed, 4 subtests passed in 243.92 seconds**. The two failures are existing stale expectations:

1. `test_reader_ask_job_inherits_selection_fields_with_typed_prompt` patches `bhf_web.app.BHFAgent`, an attribute no longer present in the app module.
2. `test_reader_script_searches_scripture_without_bhf_search_coupling` expects the removed `runBibleSearchFallback` name; the current reader script uses the `/api/bible/search` route.

These are not NE-6R2 regressions. The suite completed, and its full disposition is reported rather than suppressed.

The canonical editor test took 88.33 seconds in the initial diagnosis because it loaded the full JSON inventory once directly and again through the route cache. The test harness now reuses the route's cached library. All editing/persistence assertions passed in isolation in 58.83 seconds; the full suite also passed the case. The temporary canonical-root fixture excludes the generated package `data` directory so it does not copy a local build product. Neither change alters production runtime behavior.

## Other test results

- Frontend Node suite: 13 passed, 0 failed.
- `tests/test_ne6r2_projection_parity.py`: 1 passed in 184.04 seconds.
- `tests/test_vercel_ckl_index.py`: 10 passed; missing-index no-rebuild assertion passed separately.
- `tests/test_cold_start_diagnostics.py`: 7 passed, including one-event-per-request bound.
- SQLite storage tests after the WAL publication fix: 11 passed in 108.43 seconds.
- Full Firefox geography module: 9 passed in 409.66 seconds.

## Accessibility and limits

Browser checks verified accessible names, live-region state, keyboard interactions, focus restoration, and touch-target dimensions. No screen-reader application was available. Actual screen-reader acceptance remains NE-7 work. Local Uvicorn results do not establish Vercel function cold starts; the actual Vercel artifact and runtime remain pending.
