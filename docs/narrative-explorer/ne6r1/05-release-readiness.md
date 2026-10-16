# NE-6R1 — Release Readiness

## Disposition

**`BHF_NARRATIVE_EXPLORER_NE6R1_VALIDATION_PENDING`**

The oversized payload and browser cache-consumption risks are addressed and verified locally. Release acceptance remains pending because the first local John 2 Maps lookup still had a 33.5-second server wait, the full `test_web_app.py` run stopped making progress, and screen-reader assistive technology was unavailable. This branch is not merged or deployed, and Narrative Explorer remains disabled by default.

## Payload and evidence result

- The legacy John 2 endpoint remains full by default and returns the same 69 marker records and valid 21,687,196-byte JSON body (SHA-256 `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f`). The initial Maps panel explicitly requests compact mode.
- The compact marker response is 187,007 bytes, 21,500,189 bytes smaller (99.138%). It preserves all initial marker fields and defers only the expanded `related_passages` object. The existing detail endpoint returned byte-for-byte-equivalent JSON objects for all 69 marker records: zero mismatches.
- Passage mode now also requests a 713-byte timeline-only catalog response instead of the 3,037,523-byte browse catalog. Full catalog data remains available in browse mode and the offline Maps pack.
- The full-response profile attributes 21,498,809 bytes (99.13%) to repeated `related_passages` expansion: 32,153 serialized entries cover 4,445 unique references. The compact change does not delete or truncate these relationships.
- Acts 7 preserves `openbible-a012705` and its Acts 7:19 link. Eden's precise point remains withheld; Horeb/Sinai uncertainty and Joshua 1's Negeb/Joshua 1:4 anchor remain unchanged. Exact marker/source/reference and relationship parity is documented in `01-response-size-analysis.md` and `02-payload-and-api-contract.md`.

## Service Worker and client cache result

Service Worker v49 caches only complete HTTP 200 Maps JSON responses with identity encoding and known size at or below 512 KiB. A large response is returned directly without cloning or caching. Eligible small responses are cloned synchronously before asynchronous Cache Storage work; a focused test caught and fixed the late-clone `Body has already been consumed` race. Network-first online behavior and explicit offline-unavailable errors remain.

The map cache has 32-entry/8 MiB caps; local storage has 16-entry/2 MiB/512 KiB-per-entry caps; IndexedDB v9 clears rebuildable oversized Maps values and stale Maps-pack metadata. Firefox measured 6,492,067 bytes across 11 Maps Cache Storage entries, 447,240 local-storage bytes across four Maps keys, and five IndexedDB Maps API rows below 512 KiB each. The 21.7 MB legacy body and raw pack envelope were absent. The full offline pack installed seven entries in 10,895 ms; full catalog responses are retained as pack entries.

## Browser and accessibility result

Firefox 155.0.1 parsed the exact 21,687,196-byte legacy body five of five times with v49 active and five of five with Service Workers disabled; every run returned the exact ordered marker IDs. The replay URLs were not stored in Cache Storage. The browser's previous intermittent failure did not reproduce, though these ten runs do not establish universal reliability. Explicit page timers measured body consumption and parsing because Resource Timing reported zero encoded sizes for Service Worker responses.

The mobile Maps flow completed timeline catalog loading, 69-marker rendering, stable-ID selection, full lazy details, chapter switching, close/reopen, cached offline status, and online retry. Browse-mode search selected Jerusalem, details remained usable, focus returned to the Maps control, measured touch targets were at least 44 px, and the actual headless viewport had no horizontal overflow. The test requested 390 px but Firefox reported a 500 px CSS viewport.

The full nine-test Firefox module ran with eight passing and one Selenium stale-element exception in an evidence-trail wait. The wait was changed to read the live DOM, then that case and the synthetic selected-place case were rerun together: both passed. The synthetic test now omits embedded details, injects a one-time 503, verifies the incomplete-links message, retries, and confirms the complete Genesis 2:8 relationship. The compact mobile test also passed independently. The full module was not rerun as one clean pass after these two narrow test changes.

Firefox verified accessible control names, live status/acknowledgment regions, keyboard operation, focus restoration, trail breadcrumb current-step state, and mobile touch targets. No screen-reader environment was available; an actual assistive-technology check remains an NE-7 acceptance task.

## Performance disposition

The matched John 2 resolver profile measured 36,398.201 ms with expanded relationships and 268.705 ms in compact mode; JSON serialization measured 465.623 ms and 3.669 ms respectively. In Firefox, a first local compact Maps open took 33,846 ms; places waited 33,728 ms for response headers and parsed its 187,007-byte body in 7 ms. Warm repeated place requests took 290–299 ms for headers and 4–6 ms for body read/parse. A later warmed-suite first panel open took 3,444 ms, including 3,332 ms for places headers. This identifies the large body and client parser as separate from the remaining first-request server wait, but current NE-6R1 instrumentation does not further split that 33.7-second wait into app import, study DB setup, source loading, retrieval, or projection stages.

The full-response direct HTTP path remained slow: three observed response-header waits were 42,047 ms, 44,553 ms, and 71,556 ms, followed by 9,929–10,523 ms of body reading. Firefox parsing was about 106–146 ms. The variance is material and is not attributed to client parsing. These are local measurements; they do not establish Vercel behavior.

The prior NE-6V matched process-cold, filesystem/page-cache-warm benchmark remains the available CKL backend comparison. It measured a fresh Genesis 2:8 service request at 30,478.701 ms with JSON fallback and 1,964.208 ms with the already-verified read-only SQLite index; warm medians were 1,508.967 ms and 1,490.038 ms. That index passed integrity and source-fingerprint checks and was not rebuilt. The current isolated worktree lacks `.bhf/ckl.sqlite`; no request-time rebuild was attempted. The supported Docker build creates and verifies an index, but Vercel does not provision it. These inherited measurements and their scope are in the [NE-6V cold-start report](../ne6v/03-cold-start-performance-investigation.md).

**Disposition:** the 21.7 MB expansion and its avoidable cache work are mitigated in the Maps panel. The observed cold first-map wait remains outstanding and needs a separately instrumented deployment-path check alongside Vercel index provisioning. No OS filesystem/page-cache-cold benchmark was run in NE-6R1.

## Data safety and repository integrity

All database-backed runs set `BHF_STUDY_DB_PATH` to the existing study database and `BHF_STUDY_DB_READ_ONLY=1`. Firefox setup confirmed SQLite `query_only=1`; test teardown checked database SHA-256 `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`, schema version 37, and `integrity_check=ok`. The manifest SHA-256 was `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4` before and after; it and all protected source inventories are unchanged. Browser synthetic place/route data exists only in intercepted test responses and is absent from the real catalog, projection, and CKL manifest.

The inherited `BHF_STUDY_DB_READ_ONLY` connection guard applies only when the requested path resolves to the configured study database. It uses SQLite `mode=ro` plus `PRAGMA query_only=ON`; unrelated paths retain normal write-enabled behavior. Read-only tests confirmed both paths. Study schema migrations remain unchanged.

## Verification summary

- Frontend Node tests: 13 passed.
- Narrative Explorer, map matching/projection, Maps/KML, archaeology, and read-only DB Python tests: 123 passed.
- Changed map catalog and places-route contract tests in `test_web_app.py`: 2 passed.
- Firefox: full module 8 passed plus one stale-element test-harness error; the errored case and modified synthetic retry case then passed in a focused 2-test rerun. The separate compact mobile run passed; the repeated full-body replay passed 5/5 in each worker mode.
- Python compilation, JavaScript syntax checks, and `git diff --check`: passed.
- A combined run including the whole `test_web_app.py` file stopped advancing for more than two minutes at 82% and was interrupted without a failure report. Its two modified route tests pass separately; the remaining web-app tests are not claimed as rerun to completion.
- The Chrome GUI cache path could not be validated in its test-mode fixture: one attempt stalled before Scripture loaded, and a focused attempt then timed out waiting for `navigator.serviceWorker.ready`. It did not reach cache assertions. Equivalent pack/cache checks completed in Firefox and the Node Service Worker suite.
- No screen-reader test was available.

## Remaining release blockers and scope

1. Characterize and address the local first-map server wait with stage timings; do not infer Vercel latency from this workstation.
2. Provision/verify the CKL index in the Vercel build path in the separate transaction already identified by NE-6V.
3. Perform a basic actual screen-reader check during NE-7 acceptance.
4. Rerun the full `test_web_app.py` suite to completion in an environment where its long-running segment progresses.

This branch is based directly on NE-6V. It does not modify source inventories, evidence, database schema/content, commentary artifacts, reader data, feature-flag defaults, or deployment configuration. Do not merge, deploy, or enable the feature by default as part of NE-6R1.
