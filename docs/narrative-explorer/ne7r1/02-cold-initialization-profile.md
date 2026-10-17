# NE-7R1 cold initialization profile

## Matched bounded measurements

One fresh process per backend made a first Genesis 2:8 Explorer request and a second request in the same process. Both used the same `framework/canonical_library` source tree, the same protected study database opened read-only, and the same endpoint and query. The source inventory had 687 objects and was identity-verified. The SQLite index was opened read-only; no index build or rebuild ran during HTTP handling.

The operating-system filesystem cache was not flushed. These are process-cold, filesystem-cache-warm measurements, not disk-cold measurements.

| Backend / condition | Status | Request time | Serialized body | SHA-256 |
|---|---:|---:|---:|---|
| SQLite with the verified index, first request in a new process | 200 | 1,912.8 ms | 131,228 bytes | `31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e` |
| SQLite, second request in the same process | 200 | 1,502.8 ms | 131,228 bytes | same |
| SQLite backend with the worktree index absent and the configured `fallback_to_json` policy, first request in a new process | 200 | 30,473.2 ms | 131,228 bytes | same |
| JSON fallback, second request in the same process | 200 | 1,515.2 ms | 131,228 bytes | same |

The serialized responses matched byte-for-byte. The JSON fallback’s process-cold stage spent 28,864.8 ms loading the source inventory. SQLite opened the index in 2.0 ms, verified source freshness in 253.9 ms, and retrieved the passage in 106.0 ms. The remaining SQLite request time was in map/archaeology lookup and projection construction. The fingerprint check is not repeated on every request: the Explorer service retains its loaded canonical library for subsequent calls.

These results do not directly compare with NE-7’s 76.4-second browser wait or the earlier 30.1-second JSON versus 2.0-second SQLite observations; those runs had different process and filesystem conditions. The matched run here reproduced a 30.47-second JSON first request and showed that warm JSON and SQLite requests converge near 1.5 seconds.

## Why Firefox selected JSON fallback

The general Firefox test ran from the isolated worktree, where the ignored default `.bhf/ckl.sqlite` file was absent. The default local configuration selects the SQLite backend but uses `fallback_to_json` when the index file is missing. This was a **missing-index fallback**, not a stale-index check. The browser fixture did not create or rebuild the index.

A read-only index was available at `/home/johnwalker/Documents/github/biblical-hermeneutics-framework/.bhf/ckl.sqlite`. `framework.canonical_library verify-db` verified it against the worktree’s CKL sources: 687 objects, schema version 4, retrieval index version 3, and the expected inventory fingerprint. Browser acceptance explicitly configured this index with stale policy `error`; the environment override was local to the test command.

## Browser overlap and remaining contention

An instrumented Firefox Genesis 2:8 trail flow started the first Explorer request while five server requests were active. Two were Companion-context requests for the chapter and selected verse. The Explorer response was 131,228 bytes and completed successfully; the server recorded 9.51 seconds total, including 7.46 seconds in read-only CKL freshness fingerprint verification. The same stage took 253.9 ms in the matched isolated process profile. Later Explorer calls in the browser completed in about 2.0–2.6 seconds.

There is no duplicate initialization within one Explorer service after it has stored its canonical library. Companion Context and Narrative Explorer each own a separate repository instance, however, and may initialize and verify the same inventory concurrently on the first passage interaction. This overlap is visible in the browser request trace and explains the larger first-browser delay. The fingerprint remains fail-closed and was not suppressed.

Ordinary Bible requests do not call Narrative Explorer, and the feature-off Firefox test observed no Explorer API request. The browser regression also completed a real `/api/bible/John/1?translation=asv` response while a study pack was still being built. A first Explorer request can still occupy the async route’s event loop while its synchronous fingerprint scan runs; if reader requests are concurrently in flight, this can delay them during that first initialization.

The narrow follow-up is to share one process-scoped, read-only verified CKL provider between Companion Context and Narrative Explorer, with a concurrency regression proving only one freshness scan occurs while all callers receive the same verified repository. Any such change must keep fingerprint validation enabled and fail closed on an absent or stale index.
