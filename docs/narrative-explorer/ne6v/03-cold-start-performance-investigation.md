# NE-6V Cold-Start Performance Investigation

## Disposition

The severe JSON-fallback cold request is **mitigated in the supported SQLite configuration but remains a release dependency for Vercel and is not considered resolved**. The verified SQLite index materially reduced the fresh-service local benchmark. A real Firefox first request against the local application still had roughly 9.4 seconds of server wait, versus about 2.0 seconds in the direct fresh-service benchmark. The repository does not provision the index in its Vercel build, so this local result cannot establish Vercel cold-start behavior.

No persistent cache, evidence truncation, repository rewrite, schema change, or request-time index build was introduced. Do not rebuild the canonical index from an Explorer GET request. A Vercel build/deployment design change is a separate performance release dependency.

## Matched local benchmark

The existing NE-5B benchmark harness was copied to `/tmp` and narrowed to Genesis 2:8. It was run at NE-6 revision `224f691feaa4a9ad3f4c921d6bda70941864b67f` against the same source snapshot and verified SQLite index. Each run used one fresh service request and three warm Genesis 2:8 requests. The process was fresh, but the OS filesystem/page cache was **not** flushed. These are process-cold, page-cache-warm measurements, not disk-cold measurements. Both backends returned 131,228 bytes with identical response SHA-256 `31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`.

| Measurement | JSON fallback | Read-only SQLite index |
| --- | ---: | ---: |
| Fresh-service Genesis 2:8 request | 30,478.701 ms | 1,964.208 ms |
| CKL initialization and fingerprint | 28,893.038 ms | 293.305 ms |
| Total CKL lookup | 28,946.742 ms | 398.445 ms |
| Archaeology lookup | 887.322 ms | 899.631 ms |
| Maps lookup | 164.436 ms | 159.646 ms |
| Place resolver | 143.477 ms | 138.978 ms |
| Route resolver | 18.897 ms | 18.852 ms |
| CKL applicability filtering | 343.554 ms | 348.129 ms |
| Evidence projection total | 380.363 ms | 403.907 ms |
| Projection validation | 1.121 ms | 1.116 ms |
| JSON serialization | 2.441 ms | 2.452 ms |
| Warm Genesis 2:8 requests | 1,508.819–1,513.180 ms; median 1,508.967 ms | 1,484.302–1,530.187 ms; median 1,490.038 ms |

The SQLite run reduced the measured fresh-service request by 28,514.493 ms (93.6%); CKL initialization/fingerprinting accounts for nearly all of the difference. App startup was measured separately in fresh Python processes: importing `bhf_web.app` and creating the default app took 1,205.445 ms with JSON configured and 1,182.598 ms with SQLite configured. Service object initialization took 3.738 ms and 3.706 ms, respectively. Interpreter startup is outside that import timer.

This instrumented request breaks down CKL setup and data-domain work, but it does not separately time every underlying JSON file read/validation or response network transfer. The CKL initialization/fingerprint stage is the dominant JSON-fallback cost. Passage retrieval is represented by CKL lookup; map and archaeology retrieval, projection, validation, and serialization are shown above.

## Real browser timing

The Firefox run used the verified SQLite index. Browser `PerformanceResourceTiming` for the first Genesis 2:8 request recorded:

| Browser measurement | Observed |
| --- | ---: |
| First Genesis 2:8 response | 8,496 ms in the final full Firefox run; other runs recorded 9,440, 9,667, and 9,926 ms |
| First request server wait (`responseStart - requestStart`) | 8,469 ms in the final run |
| Response body transfer | 0 ms in the final run; content was 131,228 bytes |
| Later Genesis 1:1–31 responses | 2,314 ms, then 1,944 ms |
| Later Genesis 2:8 responses | 2,763 ms, then 3,133 ms |
| Initial overview render after response | 13 ms; 442 DOM nodes added |

Resource timing places the delay before response headers, not in response body transfer or Explorer rendering. The browser's local server first-hit measurement is not matched to the direct ASGI benchmark execution path and remains unexplained by the stage recorder; the difference is reported rather than attributed to a specific subsystem. The original NE-6 Firefox JSON-fallback observation was 80,285 ms. A later cold JSON benchmark with the same source and warm page cache measured 30,478.701 ms. These are separate runs and environments; neither should be replaced with an average.

## Separate large Maps response observation

The online retry investigation also exercised the real `/api/maps/places-for-passage?book=John&chapter=2` response. `resolve_places_for_passage()` returned 69 place records; local resolver/serialization work measured 36,517.6 ms and produced 21,687,382 bytes under the direct Python serializer. The actual Uvicorn HTTP response declared `Content-Length: 21687196`; `urlopen` read exactly 21,687,196 bytes and `json.loads` succeeded with SHA-256 `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f`.

On Firefox with the Service Worker active, requests for the same endpoint sometimes returned status 200 but `Response.json()` failed with an `AbortError` or `SyntaxError` (unterminated string) before the body was parsed. Other Firefox retry attempts consumed it successfully. A Service Worker-disabled control parsed the map responses. The available evidence places this failure in the browser/Service Worker response-consumption path, not the server's JSON serialization. It is separate from the Narrative Explorer passage endpoint and is not explained by the Explorer stage recorder. The final acknowledgment stays `failed` when this body does not reach the controller; the smaller real 3 John 1 retry, where all responses completed, returned `not_found` for the absent ID.

## Index and deployment observations

The isolated worktree did not contain `.bhf/ckl.sqlite`. The read-only index used for measurement already existed in the original checkout. Its SHA-256 was `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182`; `PRAGMA integrity_check` returned `ok`, it was not stale, and its source fingerprint matched the committed CKL JSON manifest (`90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`). The benchmark never rebuilt it.

The Dockerfile already sets `BHF_CKL_BACKEND=sqlite`, builds the index from the canonical source during image construction, and verifies it. `.vercelignore` excludes `.bhf/`, and `vercel.json` does not build or provision the CKL SQLite index. Therefore the local SQLite mitigation is supported for the Docker path, while Vercel's cold request remains unverified and likely follows JSON fallback unless a separate build artifact/provisioning design is implemented. No Vercel deployment or production measurement was made.

## Performance conclusion

The original 80-second event is reproducible in direction: fresh JSON repository initialization dominates, and it is substantially slower than warm requests. A verified, current SQLite index reduces direct fresh-service latency to about two seconds while preserving identical response bytes. The end-to-end browser first response still showed 9.4–9.9 seconds even with SQLite, and production Vercel has no established index provisioning. The separate, large John 2 Maps response also remains intermittently unreadable in Firefox with the Service Worker active. Performance is **mitigated locally for Docker, outstanding for Vercel, and outstanding for unexplained browser first-hit and large Maps response behavior**. Resolve these as separately scoped release tasks before treating cold-start launch readiness as established.
