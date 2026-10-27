# NE-11D performance and network audit

## Method and limitations

Network timing came from Firefox `PerformanceResourceTiming` in two independent local app/browser launches against the actual current CKL JSON repository. The code revision and machine were the same; the second run may have benefited from OS/filesystem caches. These are cold launches, not a controlled cold-versus-warm cache experiment. Resource timing reported zero body/transfer bytes for Companion-context requests, so those byte counts are unavailable from the browser trace. Vercel Preview API body sizes below are UTF-8 response sizes, not compressed wire sizes.

The matched NE-11C1 baseline was not run under the same browser and hardware conditions. Consequently, this report records measured current cost but does not claim a performance regression or improvement against `628f7d13e35d77297586751f584c5a32c06d570d`. Warm-session and matched-baseline medians remain unmeasured.

## Measured Genesis handoff

Both actual browser runs completed Genesis 1:1–5 → John 1:1–5. The Companion-related request count includes Companion context and Narrative Explorer requests; total API requests also include translation/offline-data and reader commentary calls.

| Measure | Run 1 | Run 2 | Summary |
|---|---:|---:|---:|
| Companion-context requests | 4 | 4 | 4 per journey; Firefox did not expose body sizes/timing for these entries |
| Narrative Explorer requests | 3 | 3 | 2 for Genesis 1 (preflight plus activation-time revalidation), 1 for John 1 after following the route |
| Companion-related total | 7 | 7 | 4 context + 3 projection requests |
| All API requests in trace | 10 | 11 | Difference was one reader commentary request |
| Genesis projection preflight | 1.726 s | 1.549 s | Median 1.638 s; range 1.549–1.726 s |
| Genesis activation-time revalidation | 1.476 s | 1.485 s | Median 1.481 s; range 1.476–1.485 s |
| Connection action to route focus | 1.637 s | 1.653 s | Median 1.645 s; range 1.637–1.653 s |
| John projection after following route | 4.060 s | 4.096 s | Median 4.078 s; range 4.060–4.096 s |

Each Genesis projection response was 236,489 encoded body bytes and 236,789 transfer bytes in Firefox (300 bytes of transfer overhead). The John response was 196,673 body bytes and 196,973 transfer bytes. The two Genesis requests were sequential and did not overlap; one is the discovery preflight and one is the intentional activation-time verification. No repeated parallel request for that selection was observed.

## Current CKL Preview response sizes

These are API response-body sizes from the target-equivalent Preview, not browser wire measurements. They establish projection scale only; the Jonah, Psalm 22, and no-linkable-chapter Companion request counts and interaction timings were not obtained from a completed browser run.

| Selected passage | Narrative Explorer body | Result |
|---|---:|---|
| Genesis 1:1–5 | 236,489 bytes | Exact John Logos bridge available |
| Jonah 1:17 | 141,151 bytes | Jonah–Matthew bridge available; Companion source discovery omits its exact supporting claim |
| Psalm 22:1 | 113,678 bytes | No confirmed Mark 15 route |
| Psalm 100 (no linkable Companion evidence) | Not measured in browser | Companion API returned no cards/evidence identities; no live request-count result was captured |

The Genesis Companion-context response body on Preview was 142,853 bytes. The actual-browser timing entries did not expose its body size.

## Acceptance assessment

- **No eligible handoff request:** the feature code and unit coverage request a projection only when a visible discovery carries a complete CKL identity. The no-linkable Psalm 100 browser sample timed out before instrumentation completed, so a live request-count pass is not claimed.
- **Duplicate calls:** two same-selection Genesis projections were observed per complete handoff, sequentially, for preflight and activation-time revalidation. They are intentional checks, but cost about 236 kB and 1.5–1.7 s each. No duplicate parallel lookup or render loop was observed in the successful journey.
- **Chapter changes and cancellation:** frontend tests confirm abort/invalidation of stale work; browser network cancellation/discard counts were not captured.
- **Mobile suitability:** action-to-focus was about 1.6 s locally; the 236 kB projection is material for mobile networks. No mobile network profile or effective 390px viewport was available, and no service objective has been established, so no threshold is asserted.
- **C1 comparison:** unavailable under matched conditions. Do not treat the historical NE-5B profile as an equivalent baseline.

Preserve the existing retrieval design pending the Jonah correction and a matched warm/cold performance run. Repeat the four-passage network audit, including a chapter with no linkable evidence and the NE-11C1 baseline, before claiming a performance comparison.
