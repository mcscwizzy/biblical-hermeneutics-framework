# NE-6R1 — Service Worker and Client Cache Review

## Observed cache paths

Maps requests passed through three cache layers: the Service Worker's Cache Storage, the Maps service's page-memory/local-storage cache, and IndexedDB API responses installed as part of offline packs. The Maps offline pack serializes about 6,269,428 bytes across its responses. The oversized response issue therefore also created avoidable clone and persistence work when large relationship expansions or the raw pack envelope were duplicated.

## Service Worker v49

Maps API requests use network-first behavior so current online source data is returned before any offline copy. Cache Storage writes accept only complete HTTP 200 JSON responses with identity encoding and a known `Content-Length` at or below 512 KiB. This prevents the 21.7 MB legacy passage response and oversized selected-place detail responses from being cloned for dynamic caching. For eligible small Maps responses, the worker tees the body synchronously after `fetch()` returns and before awaiting Cache Storage. A regression test reproduced `Response.clone: Body has already been consumed` when that clone was delayed behind an asynchronous cache lookup; this race could make Firefox intermittently fail to parse the response. The worker keeps its `event.waitUntil` cache-write lifecycle and waits for the bounded write attempt before it can be terminated.

The map cache is capped at 32 entries and 8 MiB total. Dynamic entries are evicted before explicit offline-pack entries. A network refresh preserves the offline-pack retention header on an existing Maps cache key while replacing its payload with the current network body. The offline Maps pack may retain only `/api/maps/catalog` and `/api/maps/biblical-places` up to 4 MiB each; other Maps-pack entries follow the 512 KiB per-entry limit. The passage panel now fetches timeline-only catalog metadata, while browse and pack installation retain the complete catalog. The 6.27 MB `/api/offline/packs/maps` envelope is not copied into Cache Storage.

When offline, a cache hit carries `X-BHF-Offline: true`. A miss returns an explicit JSON 503 stating that the item is not available offline. The client does not rewrite an offline Service Worker result into its local persistent cache.

## Page and IndexedDB limits

The Maps local-storage namespace is versioned and bounded to 16 entries and 2 MiB total, with a 512 KiB serialized-entry limit. Older unversioned Maps keys are removed. Oversized responses remain in current-page memory only when needed by the active interaction and are not serialized to local storage.

IndexedDB schema version 9 removes the rebuildable raw Maps pack envelope, old oversized Maps API responses, and stale `pack:maps` install metadata. The current Maps pack is then reinstalled and marked with `cache_version: v49`. Personal data and unrelated API/offline stores are preserved. Maps pack metadata stores a small summary rather than a duplicate copy of every response.

## Cache version and privacy boundaries

Activation of v49 deletes older Service Worker caches, preventing stale v48 Maps responses from silently winning. PWA Maps API writes are same-origin only. Existing authentication callback exclusions and the BHF offline PWA remain in place. The migration only clears rebuildable Maps response data; it does not touch CKL sources, study records, personal notes, or translations.

## Browser measurements

Firefox Cache Storage size, entry count, offline pack installation state, local-storage bytes/entry count, and IndexedDB Maps rows are collected by the real-browser acceptance test. Final browser results and any deviations are recorded in `04-browser-reliability-results.md`.
