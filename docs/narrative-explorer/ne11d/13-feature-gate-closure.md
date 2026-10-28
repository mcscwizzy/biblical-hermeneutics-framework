# NE-11D4 — Final Feature Acceptance Gate Closure

## Decision

**NE-11 feature-level acceptance: FAIL.** A real narrow-screen clipping defect was demonstrated in the Study Companion overview action row at 320px and 390px. The NE-11 discovery card and route details remain readable, but the requested viewport clipping criterion fails. Production behavior was left unchanged as instructed. The conditional screen-reader session is recorded separately as **MANUAL** because this environment has no graphical app or browser session; it is not the reason for the FAIL decision.

This decision is limited to NE-11 feature acceptance. Repository-wide CI, Vercel deployment readiness, and production promotion are separate decisions and were not used to determine this result. No production behavior, CKL content, or curation record changed.

## Requirement disposition

| Requirement | Status | Evidence and decision |
|---|---|---|
| Real-data passage with no eligible connection | **PASS** | `tests/gui/ne11d1/test_ne11d3_journeys.py::test_psalm_22_generic_cross_references_do_not_promote_held_bridge` uses real Psalms 22:1 data. The completed projection has no eligible route or matching action; opening Cross References does not expose the held Mark 15 route. |
| Zero-item projection UI, absent actions, navigation stability, and recovery | **PASS** | `test_controlled_empty_projection_has_no_actions_and_recovers` transforms a real Jonah 1:17 endpoint response into a schema-valid controlled empty fixture. It verifies empty sections, disabled “No records available” controls, no route buttons or Companion handoff actions, an unchanged Jonah selection with only its origin trail node, then reloads and completes the real Jonah route handoff. |
| Naturally zero-item Scripture passage | **NOT APPLICABLE** | Scripture passages need not naturally produce zero CKL results. The controlled fixture verifies the empty state directly; no further real-data search is required. |
| Page-level overflow and clipping in NE-11 discovery cards and route details at 320, 390, 768, and 1440 CSS px | **PASS** | `test_ne11d3_mobile.py` retains the real Jonah route journey and checks target text boxes for horizontal, vertical, and line-clamp clipping, checks document `scrollWidth <= clientWidth`, and captures discovery and route screenshots at each width. The four screenshots were visually inspected; the NE-11 target text remained readable. |
| Companion overview action-row clipping at narrow widths | **FAIL** | The same viewport run measured `.companion-overview-actions` at 320px with `clientWidth=290`, `scrollWidth=415`; at 390px, `clientWidth=360`, `scrollWidth=415`. The “Compare Translations” button ends at x=430.4 while the row ends at x=305 (320px viewport) or x=375 (390px viewport); its right side is clipped by the overview pane. This is a demonstrated product defect, not an environment limitation. It is outside the NE-11 card/detail rendering, but it fails the requested viewport clipping check. |
| Keyboard order and focus restoration at all four widths | **PASS** | `test_ne11d3_keyboard.py` passes at 320, 390, 768, and 1440 px: Tab reaches the discovery disclosure and action in order; Space expands; Enter opens the route and moves focus to its heading; Escape returns focus to the original action. |
| Semantic headings, accessible names, and live-region text | **PASS** | The keyboard journey checks the Narrative Explorer `h3` and Related Biblical Passages `h4`, the names “Explore this connection” and “Open related passage: Matthew 12:40”, and the polite live-region text `Jonah 1:17`. |
| Actual screen-reader session | **MANUAL** | The CUA inventory reported no graphical apps or browsers; `DISPLAY` and `WAYLAND_DISPLAY` are unset and the session is a TTY. A human accessibility reviewer should use a graphical desktop with Chrome or Firefox and Orca or NVDA to verify heading navigation, the spoken action name and passage update, and route focus/restoration. No unsupported headless screen-reader setup was attempted. |
| Controlled cold/warm Genesis execution | **PASS** | An isolated server run made the first Genesis 1:1–5 endpoint request after health startup, then repeated the same request in the same process. Both returned HTTP 200, the same 236,489-byte body, and SHA-256 `0a1d678d653216d53fbe1b6f30c4a70c3d773cdd40b6f5f88a2ae40b67cc4474`. Observed cold/warm times were 9,807.7/1,425.4 ms. |
| Cancellation and request outcomes | **PASS** | `test_real_jonah_verification_interrupted_by_chapter_change` records the real activation response (HTTP 200, 141,151 bytes), observes the pending activation signal abort after changing to Jonah 2, then releases the response and confirms no stale route or trail is committed. This verifies client-side cancellation and stale-result handling; it does not claim the already-returned HTTP transfer was canceled. |
| Negative-passage request counts | **PASS** | Instrumented browser calls to `BHFNarrativeExplorer.load` recorded one completed HTTP 200 projection request per explicit measurement: Psalms 22:1 returned 9 items / 113,678 bytes; Psalms 119:176 returned 7 items / 52,443 bytes. Both had complete results, zero authored routes, zero bridges, and zero Companion handoff actions. |
| Matched Genesis endpoint comparison against NE-11C1 | **PASS** | Reuse the completed NE-11D3 matched endpoint samples: current 10,661/1,433/1,428 ms versus NE-11C1 31,243/1,514/1,495 ms, each with a 236,489-byte body. An equivalent Genesis end-to-end handoff was not practical in NE-11C1; its attempted route wait timed out. No historical end-to-end comparison is claimed. |
| CKL inventory and fingerprints | **PASS** | Inventory is 687 objects with fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. The object/source tree fingerprint is `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`. CKL validation reports 687 valid objects, zero errors, and 14 existing warnings. |
| NE-9C curation identities | **PASS** | Validator passed 3,925 reviewed decisions: 408 curated, 1,895 held, and 1,622 excluded. The curation JSON tree fingerprint remains `691c9201d50eb0cceccac1b1a6d1beaa58f65b96cac54241cc856c8e2bc87a31`. All 433 active identities match fingerprint `344ef13860f82f60621a950e160a6a550dd14a4e2c4cdfe935d6eb7541911c3c`. |
| NE-10 bridge and held-candidate identities | **PASS** | Passage regression tests validate all 44 bridge identities and keep all seven candidates held. Bridge registry SHA-256: `8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b`; sorted bridge-ID hash: `0dc65dbd54622e186329f150df23e1f5dac5de83300a8b5bb7f999dde1050470`. Held file SHA-256: `15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3`; sorted held-ID hash: `47b7c53959c1e414c65b71f735ead90b50818eb44878dba1927a89cc267b34cd`. |
| Reviewed support-pair restriction | **PASS** | `tests/test_ne11d3_support_safety.py` passed all 10 cases, including unrelated shared-word/source candidates, incompatible scope/parent/anchor, an unreviewed competing candidate, an explicitly reviewed pair, and cached/uncached packets. |
| Jonah and Genesis handoff regressions | **PASS** | Real CKL-backed Jonah↔Matthew and Genesis↔John browser handoff tests passed, including return-to-origin behavior. |

## Performance observations

The NE-11D3 three-sample journey timings remain the basis for phase latency. Values below are median and observed range in milliseconds; these are observations, not acceptance thresholds.

| Journey | Preflight | Activation verification | Action to route focus | Destination selection |
|---|---:|---:|---:|---:|
| Genesis | 1,805 (1,649–2,090) | 1,646 (1,545–1,698) | 2,269 (1,706–2,344) | 778 (361–788) |
| Jonah | 1,150 (1,059–5,923) | 1,211 (1,078–1,259) | 1,696 (1,659–1,779) | 730 (662–1,002) |
| Matthew | 1,508 (1,129–2,411) | 1,292 (1,089–1,387) | 1,759 (1,669–1,813) | 786 (679–853) |

The high first-run spread, especially Jonah preflight, shows substantial variability. The controlled Genesis cold/warm pair also shows startup cost followed by a much faster repeated request. The matched NE-11C1 endpoint bodies are byte-identical; current warm endpoint samples are comparable to or faster than the NE-11C1 warm samples. **No performance regression is demonstrated by the available measurements.** The samples do not support a general performance guarantee.

## Verification record

- `.venv/bin/python -m framework.canonical_library --root framework/canonical_library --json` — 687 objects and expected inventory fingerprint.
- `.venv/bin/python tools/ckl_validate.py --root framework/canonical_library --json` — 687 valid, zero errors, 14 warnings.
- `.venv/bin/python scripts/ne9c_bulk_curation.py --source-root . --state-dir docs/narrative-explorer/ne9c-bulk-curation validate` — passed 3,925 decisions.
- Focused integrity/regression batch: `tests/test_narrative_explorer_passages.py`, `tests/test_ne9c_bulk_curation.py`, `tests/test_narrative_explorer_api.py`, `tests/test_ne11d3_support_safety.py`, and `tests/test_ne11d1_jonah_handoff.py` — **63 passed**.
- Focused browser acceptance batch for the controlled fixture, negative passage, chapter-change cancellation, real no-eligible behavior, responsive checks, and Jonah/Genesis handoffs — **12 passed**. The final keyboard test was then run at all four widths — **4 passed**.
- Isolated cold/warm Genesis measurement — **1 passed**.
- Final focused reruns after the evidence assertions were tightened: negative-passage request counts — **2 passed**; cancellation outcomes — **1 passed**; 320px/390px clipping diagnostics — **2 passed**.

CKL, NE-9C, NE-10, source-lock, and reviewed curation inputs were not edited. The six structured-output failures, CKL governance issue, sanitizer findings, and First Corinthians ranking failures remain in the separately reviewed NE-11E scope.

## Delivery boundary

The branch was created from fetched `origin/master` at `772ea3c1`; required commit `c3d4aa5a495a5932196aacb056c7b6688cbd87ea` is an ancestor. This report and its focused test evidence are ready for review. No merge or deployment was performed.
