# Narrative Explorer NE-5B performance results

## Result

NE-5B keeps the NE-5A evidence and API contract while reducing the mixed
seven-passage warm-request median from **2,944 ms to 1,182 ms**. That saves
**1,762 ms (59.8%)** across 42 matched requests. All 14 chapter and verse-range
responses are byte-for-byte equal to the captured NE-5A responses.

## Baseline and method

- NE-5B branch: `perf/narrative-explorer-ne5b-retrieval`, based directly on
  NE-5A commit `bf1c4772f03f4aa12aef2a0faa5a5aaa1e54b005`.
- The known NE-1, NE-2, NE-3, and NE-4 commits are ancestors. The cached
  `origin/master` ref was `b9812fd0236cc2341fd4b777fe92b009dfb05c8b`, before
  those stacked transactions. A live `git ls-remote` check could not resolve
  `github.com` in this environment.
- The baseline replay used an isolated archive of the exact NE-5A commit. It
  used the same Python environment, repository configuration, CKL SQLite
  snapshot, study database snapshot, route, and benchmark script as NE-5B.
- Machine: Linux `7.0.0-31-generic`, x86_64, Python 3.12.3, FastAPI 0.115.14,
  HTTPX 0.27.2. Requests used the versioned FastAPI route through
  `httpx.ASGITransport`; response bodies are uncompressed JSON bytes.
- CKL was opened as `SQLiteCanonicalLibrary` through
  `SQLiteCanonicalRepository(read_only=True)`, with the existing stale and
  fingerprint check enabled. The study database passed its existing current
  schema check. The configured CKL stale policy remained `fallback_to_json`.
- CKL database SHA-256 before and after: `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182`.
  Study database SHA-256 before and after: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.
- The host OS page cache was not flushed. “Fresh service” means a new service
  and application object, not a guaranteed cold disk read. The matched warm
  baseline replay was run after the first baseline had warmed the host cache;
  its warm results are the baseline used below. The historical NE-5A profile
  reported Genesis 1 as 260,088 bytes; the current unchanged NE-5A route and
  pinned local snapshots returned 260,359 bytes, which is the captured baseline
  used for this transaction.
- Each first-request and per-scope timing has three repetitions. The warm
  aggregate contains 42 requests: three repetitions for each of seven chapter
  scopes and seven verse ranges. p95 is reported only for that 42-sample mixed
  workload. Per-scope p95 is omitted because each scope has three samples.
- Default application import and construction was measured separately in
  three fresh Python processes per revision, using the same shared
  `.venv/bin/python` interpreter and repository configuration. The timer starts
  after interpreter startup and surrounds `import bhf_web.app`, which creates
  the default FastAPI application. The reproducible probe is
  `python -c 'import time; start=time.perf_counter(); import bhf_web.app; print((time.perf_counter()-start)*1000)'`.
- The reproducible harness is
  [`benchmark_narrative_explorer_ne5b.py`](../../scripts/benchmark_narrative_explorer_ne5b.py).
  It can write baseline bodies with `--fixtures DIR` and compare every raw
  response body against existing fixtures with `--fixtures DIR --compare-fixtures`.
  The exact NE-5A response bodies are in
  [`ne5a_baseline`](../../tests/fixtures/narrative_explorer/ne5a_baseline/README.md).

## Before and after

| Measurement | NE-5A median (range) | NE-5B median (range) | Change |
| --- | ---: | ---: | ---: |
| Default app import and construction, 3 fresh processes | 1,195 ms (1,189–1,277) | 1,219 ms (1,195–1,229) | Similar; +24 ms median |
| FastAPI/service object initialization | 3.74 ms (3.27–4.00) | 2.84 ms (2.52–3.90) | No material change |
| Genesis 1 first request with a fresh service | 4,424 ms (4,218–4,442) | 2,030 ms (1,932–2,088) | −2,394 ms (−54.1%) |
| 42 warm passage requests | 2,944 ms (2,172–5,759) | 1,182 ms (677–3,144) | −1,762 ms (−59.8%) |
| Mixed-workload p95, 42 requests | 5,736 ms | 3,104 ms | −2,632 ms (−45.9%) |

Fresh-service request timings share the same no-flush page-cache limitation
described above. The p95 belongs to a workload mixing chapter requests and
smaller verse ranges; it is not a per-passage percentile.

### Warm request medians by scope

Each timing cell is median `[minimum–maximum]` milliseconds across three
repetitions. Response bytes, projected item count, projected connection count,
coverage state/query status, and serialized SHA-256 are identical before and
after.

| Passage | NE-5A ms | NE-5B ms | Bytes | Items / connections | CKL / map / archaeology state and query status | Response SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Deuteronomy 32 | 5,745 [5,736–5,759] | 2,912 [2,802–3,031] | 459,993 | 29 / 82 | available/complete · partial/partial · not_represented/complete | `ff983d1c49d4c5ac480eed9ab6cd2a9e02227c4d9fe604af682b3d0b68cc35a9` |
| Deuteronomy 32:8–9 | 2,464 [2,388–2,526] | 965 [944–977] | 84,025 | 11 / 39 | available/complete · unknown/partial · not_represented/complete | `60693c48ed26bb5026f4535e886ddf6dfb2008ebe689b71ffacb629e711b7fee` |
| Exodus 3 | 5,318 [5,244–5,424] | 3,129 [3,104–3,144] | 562,064 | 36 / 188 | available/complete · partial/partial · not_represented/complete | `5295cce59694ad5dc9584f65c29324ab73a698304baaff611baffc6d7c254a00` |
| Exodus 3:1–6 | 2,735 [2,729–2,793] | 1,176 [1,152–1,179] | 196,197 | 27 / 133 | available/complete · partial/partial · not_represented/complete | `dbea7eea3b9a67cace50b2a6da564af4c723d8f5804dc888a0784cf5e2916b50` |
| Genesis 1 | 3,788 [3,786–3,822] | 1,502 [1,500–1,543] | 260,359 | 34 / 134 | available/complete · unknown/partial · not_represented/complete | `211b593d3854e53cbef88bfc6ebdc57bdd6e3779d64d6929b565c6429fd1949b` |
| Genesis 1:1–2 | 2,639 [2,601–2,779] | 1,198 [1,185–1,287] | 205,650 | 27 / 114 | available/complete · not_represented/complete · not_represented/complete | `8a3280faf1ccf238e4a0b629c63a130b37b26645fb2ffa20eb0bbee4fde29fc6` |
| Genesis 2 | 4,153 [4,069–4,201] | 2,062 [2,028–2,109] | 420,933 | 44 / 129 | available/complete · partial/partial · not_represented/complete | `f2f603e6e99a5c76b2e05ac6baed2ab22995c34b61927ae38425413a1f804f75` |
| Genesis 2:8–14 | 3,234 [3,230–3,240] | 1,639 [1,618–1,675] | 255,175 | 26 / 62 | available/complete · partial/partial · not_represented/complete | `939dc5c32b2e1f60acc224a0d7856a984050ba08d762670b58a82e903fc94b7f` |
| Genesis 3 | 3,119 [3,095–3,147] | 1,027 [990–1,055] | 154,179 | 23 / 61 | available/complete · partial/partial · not_represented/complete | `9ad5a11a456c80f66d8d5c80526bc4d46d66293a67e68aa99ac74b5a9b5dbd87` |
| Genesis 3:22–24 | 2,466 [2,390–2,531] | 923 [914–965] | 81,818 | 13 / 27 | available/complete · partial/partial · not_represented/complete | `da48f04814a8f39ebf8d5f93b58363928ea3faa18c10f0153f34378a05a18f22` |
| Genesis 6 | 3,759 [3,734–3,851] | 1,725 [1,724–1,729] | 247,037 | 26 / 56 | available/complete · unknown/partial · not_represented/complete | `3aa493f4f7de70f14ce80d05c9dedbfe362675df33311d0f7a7dbfa69b578145` |
| Genesis 6:1–4 | 2,626 [2,589–2,672] | 1,137 [1,087–1,155] | 163,550 | 18 / 40 | available/complete · not_represented/complete · not_represented/complete | `f979feaa29a71b684fff05285ced0627fa5b22f09324a79934e2f5c850b1cc9e` |
| Psalm 82 | 2,181 [2,172–2,183] | 688 [677–730] | 45,009 | 6 / 15 | available/complete · unknown/partial · not_represented/complete | `01de735629c6c7562dd67cf50270fe58152c7a27bf133ec8172a9311a9fe471e` |
| Psalm 82:1–8 | 2,257 [2,195–2,278] | 690 [687–764] | 45,045 | 6 / 15 | available/complete · unknown/partial · not_represented/complete | `682729c039e163024340ef0fd754ba6d301946f188be73a1ed49e94917b58cd4` |

## Verified work reduction

The stage measurements below are medians across the 42 warm requests. They are
observed wall time inside each named stage, not cumulative profiler time.

| Stage or work count | NE-5A | NE-5B | Change |
| --- | ---: | ---: | ---: |
| CKL passage lookup | 25.5 ms | 26.2 ms | Essentially unchanged |
| Map lookup | 1,151.8 ms | 123.0 ms | −1,028.8 ms (−89.3%) |
| Place resolver | 1,136.3 ms | 108.5 ms | −1,027.9 ms (−90.5%) |
| Map route resolver | 13.5 ms | 12.1 ms | −1.4 ms |
| Archaeology lookup | 1,075.1 ms | 533.7 ms | −541.4 ms (−50.4%) |
| CKL applicability filtering | 324.2 ms | 346.2 ms | +22.0 ms; no optimization applied |
| Map external-record projection | 83.7 ms | 85.9 ms | Essentially unchanged |
| Archaeology external-record projection | 0.01 ms | 0.01 ms | Essentially unchanged |
| Projection validation | 1.47 ms | 1.56 ms | Essentially unchanged |
| JSON serialization | 3.82 ms | 3.73 ms | Essentially unchanged |
| Map candidate terms checked, Genesis 1 | 7,506 | 7,506 | Same candidates checked |
| Regex searches for those terms | 7,504 | 0 | −7,504 (−100%) |
| SQLite connections opened, Genesis 1 first request | 670 | 329 | −341 (−50.9%) |

The request-scoped parser/reference counters did not change. A separate
`cProfile` call-count pass, whose timings were not used as latency measurements,
counted 3,606 Scripture-reference parses and 1,250 overlap calls for Genesis 1
on both revisions, and 11,326 parses and 4,018 overlap calls for Exodus 3 on
both revisions. The earlier NE-5A cProfile cumulative values identify repeated
work but are not substituted for the wall-clock measurements above.

No parser memoization was added. The call counts confirm substantial parsing
activity, but this pass did not establish how many identical raw references
repeat with the same alias lookup context, so it could not show that a cache
would reduce work. Parsing also feeds distinct anchor validation and
applicability checks; safely reusing parse results would need a request-scoped
cache keyed by the authored input and alias context while still running every
caller’s source-anchor, overlap, and semantic-misanchor checks. That is a
separate optimization to measure and test; no validation was skipped here.

Python `tracemalloc` peak allocation was measured in three separate fresh
processes for a Genesis 1 API request after module imports. Median peak was
19,118,957 bytes on NE-5A and 19,119,048 bytes on NE-5B, a net increase of 91
bytes. The sample ranges overlap; this is no material traced-memory change.
This measures Python-traced allocations, not SQLite or operating-system page
cache memory.

## Changes implemented

1. `PassageTextMatcher` normalizes the passage once and checks normalized
   whole-term membership with the same space boundaries and stopword rule as
   the existing regex matcher. It caches raw candidate-term results in a
   request-local dictionary capped at 8,192 keys. Its source text is checked
   before a resolver reuses it. One instance is shared across the existing
   place and route text-first scans.
2. The archaeology passage resolver now requests site rows without nested
   item, link, and media detail expansion. It still loads the full archaeology
   item list, all item Scripture links and media used in returned cards, and
   the same site identity, location, and source data. The existing explicit
   Scripture-link primary match, named-item/site secondary match, ranking,
   confidence ordering, stable IDs, cautions, source data, 25-item bound, and
   partial-coverage behavior remain in place.

No parser cache, global cache, persistent application cache, database rebuild,
second database, schema migration, projection truncation, source mutation,
generic archaeology keyword retrieval, or API/frontend behavior change was
introduced. Text-first map matches still short-circuit reference fallback and
retain partial coverage when anchor-only map records may be absent.

## Evidence and compatibility checks

The baseline fixtures and optimized API bodies matched exactly for all seven
chapter requests and all seven verse ranges. This byte comparison includes
ordering, IDs, claims, evidence identities, passage anchors, source IDs and
bibliography, relationship types, connection IDs/direction, certainty,
confidence, dispute/review status, section membership, coverage, uncertainty,
and navigation targets. Schema version remains `1.0`; classification policy
remains `ne5a-1`.

The focused assertions also cover:

- Genesis 1 comparative evidence and source identities; no newly classified
  generic creation/worldview material.
- Genesis 2–3 Eden coordinates remain non-displayable; geography and sacred
  space membership remain unchanged.
- Genesis 6 disputed sons-of-God evidence and exclusion of book-wide unrelated
  cross-references.
- Deuteronomy 32 manuscript evidence remains distinct from archaeology lookup.
- Psalm 82 textual observation, Ugaritic comparison, and disputed
  interpretation remain distinct.
- Exodus 3 keeps Presence Theme and Divine Presence in Themes & Biblical
  Connections, keeps cosmic/sacred-space coverage unknown under partial map
  lookup, and retains Horeb/Sinai uncertainty.
- Invalid and reversed passage ranges, verse overlap, aliases, duplicate map
  names without Scripture links, unrelated Genesis 6 references, generic
  archaeology terms, and records without usable passage anchors.

The baseline and final CKL and study database hashes match. The GET-path
read-only test still passes, the real request uses the current read-only SQLite
CKL repository, and no database file changed during the benchmark.

## Test results and unrelated failures

- Combined Python resolver, map, archaeology, NE-2 projection, NE-3 API,
  startup/read-only, and SQLite compatibility run: **137 passed, 1 failed**.
  The failure is `tests/test_notes.py::StudyDatabaseTests::test_archaeology_seed_and_passage_resolution_load_from_database`; its seeded
  site has an empty `source_id`. The same test fails on the exact NE-5A
  baseline archive.
- The final map-matcher test module: **10 passed**.
- Final focused optimization, duplicate-name/no-link, and malformed-reference
  regressions: **12 passed**.
- NE-4 Narrative Explorer frontend and service-worker tests: **2 test files
  passed, 0 failures**.
- The existing hybrid retrieval test still returns
  `genesis-nations-babel-context` for “Abram” instead of `abraham`; this
  reproduces on the NE-5A baseline and was not changed.
- The CKL inventory metadata issue named
  `genesis-abraham-call-covenant-context` remains outside this transaction and
  was not modified.

No unrelated failure was repaired as part of NE-5B.

## Remaining latency and NE-5C recommendation

After both changes, the warm mixed-request median is 1.18 seconds, while the
largest measured full-chapter cases are Exodus 3 at 3.13 seconds and
Deuteronomy 32 at 2.91 seconds. Remaining median costs include archaeology
retrieval at 534 ms and CKL applicability at 346 ms. Validation and JSON
serialization remain below 4 ms each. The 562 KB Exodus 3 body is large, but
the measured loopback profile does not show serialization as a meaningful
cost, and it excludes production network transfer.

For NE-5C, profile passage-scoped archaeology item/link loading and repeated
CKL applicability parsing as separate, testable transactions. Keep the current
map text-first/anchor-only distinction. Consider a lightweight overview route
only if production transfer or browser measurements show that the complete
JSON envelope becomes a material interaction cost after retrieval work is
reduced further.
