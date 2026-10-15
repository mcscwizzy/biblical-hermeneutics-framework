# Narrative Explorer NE-5A performance profile

## Method and boundaries

Measurements used the local FastAPI ASGI request path and the current read-only SQLite CKL index. The same Genesis 1 API-shaped request was measured once with a fresh service/repository instance, then three times in a warm process. Exodus 3 was measured later in the same process. The existing repository stale/fingerprint check was enabled; no index rebuild, database write, or persistent application cache was used. OS page-cache state was not flushed, so “cold” here means fresh service/repository process state, not a guaranteed cold disk cache.

Timings are local wall-clock milliseconds and response bodies are uncompressed JSON byte counts. They do not include production network transfer. Browser parsing and overview rendering were measured in the NE-4 work at milliseconds, and are not reproduced by this server-side profile. NE-5A makes no performance code changes.

## End-to-end request measurements

| Passage / request state | Wall time | JSON response |
| --- | ---: | ---: |
| Genesis 1, fresh service/repository | 4,280.65 ms | 260,088 B |
| Genesis 1, warm request 1 | 3,669.98 ms | 260,088 B |
| Genesis 1, warm request 2 | 3,658.33 ms | 260,088 B |
| Genesis 1, warm request 3 | 3,736.95 ms | 260,088 B |
| Genesis 1, warm median | 3,669.98 ms | 260,088 B |
| Exodus 3, same process | 5,233.51 ms | 562,061 B |

NE-4 had previously recorded approximately 32 seconds for a cold Genesis 1 request and 2–5.5 seconds for warm pilot requests. The NE-5A local Genesis 1 timings are materially lower than that earlier cold observation, but the process/cache conditions and instrumentation differ; this is not evidence of a code-level speedup or a directly comparable before/after benchmark.

## Measured stage timings

| Stage | Fresh Genesis 1 | Warm Genesis 1 | Exodus 3 same process |
| --- | ---: | ---: | ---: |
| CKL repository initialization | 326.24 ms | Already initialized | Already initialized |
| CKL fingerprint/stale check (within initialization) | 288.24 ms | Read-only check retained | Read-only check retained |
| CKL indexed passage retrieval | 179.19 ms | 26–27 ms | 106 ms |
| CKL lookup total | 505.67 ms | 26–27 ms | 106 ms |
| CKL item projection / applicability | 666.69 ms | 708–782 ms | 461 ms |
| Map lookup | 1,854.72 ms | 1,800–1,840 ms | 1,809 ms |
| Archaeology lookup | 1,060.75 ms | 1,019–1,023 ms | 1,036 ms |
| External-result projection | 47.88 ms | Not isolated in each warm sample | 1,690 ms |
| Total projection | 716.14 ms | 708–782 ms | 2,153 ms |
| Projection validation | 1.16 ms | About 1 ms | 1.48 ms |
| JSON serialization | 4.84 ms | About 5 ms | 9.42 ms |
| Study database integrity checks | 2.64 ms cumulative | Negligible in request | Negligible in request |

Stage instrumentation is nested: the lookup and projection subtotals are not additive with every row. The Genesis 1 fresh-request subtotal is consistent with the 4.28-second request. On warm Genesis 1, map and archaeology passage resolution account for about 2.8 seconds before CKL projection and framework overhead. Exodus 3 took longer primarily because its external projection stage was much larger; its response was 2.16 times the Genesis response size.

## Profile clues

A `cProfile` pass reported 14.5 million calls and 12.497 seconds under profiler instrumentation. That profiled wall time is not used as an API timing because profiling substantially perturbed execution. The call-site profile nevertheless identified repeated work worth measuring in NE-5B:

- `_project_external_lookup`: two calls, 5.075 seconds cumulative under profiler.
- `parse_scripture_references`: 11,326 calls, 5.713 seconds cumulative.
- `references_overlap`: 4,018 calls, 4.214 seconds cumulative.
- `resolve_places_for_passage`: 3.282 seconds cumulative.
- `term_in_text`: 7,506 calls, 3.158 seconds cumulative.
- Regex `search`: 18,831 calls, 3.019 seconds cumulative.
- Archaeology passage resolution: 1.115 seconds cumulative.

Cumulative profiler timings overlap across the call tree and are not stage sums. The actionable signal is repeated passage-reference parsing and full-catalog text/regex matching in map resolution, plus the archaeology lookup. The SQLite repository/index itself was not the dominant warm-request cost.

## NE-5B recommendation

Prioritize **read-only indexed retrieval and anchor processing** in the map and archaeology passage resolvers. Measure an implementation that narrows candidate records before repeated text-term regex matching and avoids reparsing the same authored scripture references within one request. Preserve read-only operation, CKL fingerprint/stale-index protections, exact passage applicability, current partial-coverage signaling, and source identity. Do not use a persistent cache or modify/rebuild the database as part of the first optimization experiment.

Do not start with a lightweight overview endpoint: response validation and JSON serialization measured below 10 ms even for the 562 KB Exodus 3 payload, while map and archaeology lookup consumed seconds. Reconsider a separate overview projection only if a post-retrieval-optimization end-to-end and browser profile shows JSON transfer or client-side rendering becoming a material part of latency. Keep a before/after benchmark with the same process/cache conditions and report wall time, payload size, and per-stage time.

No truncation of evidence or change to the existing API envelope is proposed in NE-5A.
