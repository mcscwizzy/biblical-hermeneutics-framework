# NE-6R2 — Cold Request Timeline

## Scope and measurement conditions

The CKL backend comparison and the first Maps wait were investigated as separate paths. The local benchmark used three fresh Python processes for process-cold calls and nine calls after each process had warmed. The operating-system page cache was already warm; no disk-cache-cold claim is made. Each comparison used the same checked-out CKL inventory and the same read-only study database bytes (`2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`). Study DB connections were read-only and had `PRAGMA query_only=1`. Diagnostics were enabled for stage attribution and disabled for the earlier matched direct-request baseline. Browser measurements are separate from direct ASGI measurements.

The index identity used for these runs was inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. The generated index was not read from the developer's `.bhf/` path; indexed runs selected the package-owned build output described in [the artifact report](04-vercel-build-artifact-validation.md).

## Historical measurements retained as separate baselines

| Run | Operation | Result |
| --- | --- | ---: |
| NE-6V | Process-cold Genesis 2:8, JSON fallback | 30,478.701 ms |
| NE-6V | Process-cold Genesis 2:8, verified read-only SQLite | 1,964.208 ms |
| NE-6R1 | Full John 2 Maps resolver | 36,398 ms |
| NE-6R1 | Compact John 2 Maps resolver | 269 ms |
| NE-6R1 | First compact Firefox response-header wait | 33,728 ms |
| NE-6R1 | Warm compact Firefox response-header wait | 290–299 ms |
| NE-6R1 | Compact John 2 response | 187,007 bytes |

Those figures were collected under different conditions and are not pooled with NE-6R2 samples.

## Matched local request measurements

For these measurements, each cold sample was the first request from a new Python process. Warm measurements are nine repetitions across the same benchmark setup. This is process-cold/page-cache-warm. The response hash matched across JSON and SQLite Genesis 2:8 runs: **131,228 bytes**, SHA-256 `31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`.

| Request/backend | Process-cold median (range; n=3) | Process-warm median (range; n=9) | Body bytes / SHA-256 |
| --- | ---: | ---: | --- |
| Genesis 2:8 Narrative, JSON | 30,127.16 ms (30,094–30,203) | 1,546.27 ms (1,528–1,709) | 131,228 / `31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e` |
| Genesis 2:8 Narrative, SQLite | 1,968.20 ms (1,934–2,001) | 1,506.96 ms (1,482–1,559) | Same bytes and hash |
| John 2 compact Maps, SQLite | 368.80 ms (363.55–373.28) | 281.55 ms (279.31–299.90) | 187,007 / `991064790c1e215ce69f09b1885818419c49f90e0f3e71dd408e0d24eb35aa32` |
| John 2 routes, SQLite | 100.02 ms (99.33–102.05) | 23.37 ms (22.92–24.04) | 2,900 / `dc6aa7159c92f956ea4ef48c508b9758f4aad6461713018e8c76526ed177ddcc` |
| Maps timeline metadata, SQLite | 4.30 ms (4.23–4.55) | 2.92 ms (2.69–5.90) | 713 / `5c4f00ecaa7c3897de5b34a46798024fe46d377d9fdecab019c1682ca8711c25` |

No p95 is reported: three process-cold samples are insufficient. App import plus construction ranged 1.166–1.204 seconds for JSON and SQLite runs. Parent-process-to-server-ready ranged 1.266–1.305 seconds; process-to-ready ranged 1.212–1.250 seconds. Route registration was around 86–110 ms. Direct SQLite freshness verification was about 260 ms in the process-cold benchmark. Direct request-stage and wall timings vary slightly because diagnostic instrumentation itself runs in the request path.

The sequential first-Maps direct run measured a compact places header median of 366.14 ms (361.58–367.59) and routes header median of 23.02 ms (22.44–23.12), n=3. A synchronized six-call request batch returned header waits with median 391.60 ms (106.85–412.49); an unsynchronized concurrent batch had median 376.72 ms (99.12–399.20). The ASGI instrumentation recorded overlapping request lifetimes in the browser, while a direct concurrent benchmark showed synchronous route work entering one at a time at the ASGI boundary (maximum in-handler overlap 1). These observations do not establish a shared initialization lock.

## Browser first hits and stage attribution

Firefox 155.0.1 was run against local Uvicorn with a package-built SQLite index and the same protected study DB in read-only mode. A fresh targeted Firefox run passed in 62.43 seconds. The first Genesis 2:8 Explorer response measured 9,499 ms from browser request start to response headers, with 1 ms body transfer for 131,228 bytes. Later Genesis Explorer responses in that run waited 1,907–3,142 ms for headers. A second run measured 9,686 ms browser header wait. These are browser-observed waits, not Vercel timings.

Server spans for the first Narrative Explorer request in the captured rerun were:

| Stage | Elapsed |
| --- | ---: |
| CKL repository open | 446.66 ms |
| CKL freshness and full source-inventory fingerprint verification | 7,114.93 ms |
| CKL passage retrieval | 217.06 ms |
| Map places load / text matching / marker serialization | 40.61 / 24.82 / 11.07 ms |
| Scripture-reference lookup | 65.67 ms |
| Archaeology lookup | 901.34 ms |
| Narrative projection | 403.47 ms |
| Validation and response construction | 0.65 / 2.76 ms |
| Route handler / response headers | 9,433.38 / 9,440.08 ms |

In that same process, the import stage took 1,770.10 ms, route registration 85.80 ms, app construction 86.41 ms, middleware-stack initialization 0.07 ms, and study database acquisition 0.59 ms. This puts the separate CKL fingerprint span in context with startup and request middleware timing.

Five requests were active at the point the slow request completed. This run establishes that CKL freshness verification accounted for about 7.1 seconds of the 9.44-second server time for that Narrative Explorer request. It does not establish why the same verification took about 260 ms in the direct benchmark, and it does not explain the historical John 2 Maps delay.

A separate targeted John 2 compact Maps browser run measured 3,836.51 ms to headers (browser measurement about 3.9 seconds). Its stages included study DB acquisition 72.93 ms, map-place loading 3,133.76 ms, text matching 102.43 ms, marker serialization 569.91 ms, and route handler 3,830.28 ms. The same route was 353–375 ms in direct process-cold measurements and 266–273 ms warm. Because the 3.1-second load outlier did not reproduce in the matched direct runs, this single sample identifies where that sample spent time but not a stable cause.

## Disposition

The local JSON fallback's dominant cold cost is CKL source loading and validation; a verified SQLite index preserves identical response bytes and reduces the process-cold Genesis request to about two seconds. The new build provisioning removes the Vercel missing-index path as a configuration risk, but a real Vercel function artifact/runtime has not been produced here.

The historic 33-second first John 2 Maps header wait was not reproduced in NE-6R2's fresh local Maps benchmark. Firefox showed a separate roughly 3.9-second first compact request once, with an outlier in map-place loading that was not repeated in direct measurements. **The 33-second first-Maps cause is not established and is not claimed fixed.** No speculative cache, background warmer, schema migration, or request architecture change was added. The Narrative Explorer browser outlier and its measured CKL verification stage are recorded separately from Maps.
