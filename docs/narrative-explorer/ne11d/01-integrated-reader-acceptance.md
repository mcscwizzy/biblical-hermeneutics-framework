# NE-11D integrated reader acceptance

## Baseline and method

- Acceptance branch: `test/ne11d-integrated-reader-acceptance`.
- Merged baseline: `2ea868abce02a47bc2fdc403d83f9d083b500cb0`; the starting worktree was clean and NE-11C2 is an ancestor.
- Browser: local BHF app, Firefox headless on Linux, CKL JSON source, Narrative Explorer enabled. No browser fixtures or mocked API data were used in the actual Genesis journey. No screenshots or raw traces were retained.
- A target-equivalent protected Vercel Preview also returned HTTP 200 for the app, Genesis Companion context, and Genesis projection. Its source tree matches the merged baseline.

## Reader journeys

| Journey | Result | Evidence |
|---|---|---|
| Genesis 1:1–5 → John 1:1–5 | **Pass in actual browser** | The visible Companion discovery carried exact identity `john#claim:john-logos`. “Explore this connection” selected `genesis-1-john-1-creation-word`; the card showed `interpretive_association`, original source IDs, and uncertainty that this does not prove direct borrowing. It does not present direct literary borrowing or consensus as established. Following selected John 1:1–5; Return to origin restored Genesis 1:1–5 and verses 1–5. Selection was retained. Repeated runs measured 1.637–1.653 s from action to focused route. |
| Jonah 1:17 → Matthew 12:40 | **Fail at source-side discovery; reciprocal handoff not browser-confirmed** | The current Jonah Companion response has three cards but does not include `jonah#claim:jonah-three-days` in the serialized evidence identities, so the required source-side “Explore this connection” action is absent. The verified projection does contain bridge `jonah-1-17-matthew-12-40-sign-of-jonah`, with `later_canonical_reception`, Jonah → Matthew direction, exact support `jonah#claim:jonah-three-days`, sources `jonah-masoretic` and `jonah-new-testament`, and uncertainty about chronology, idiom, and “heart of the earth.” Matthew 12:40 Companion includes that exact identity. API checks confirmed the route in both projections; the local browser harness timed out on subsequent flows, so reciprocal UI navigation remains unverified. |
| Acts 2 → Psalm 110 | **API/regression evidence only** | The current projection retains two existing authored Psalm 110 routes. The held NE-10 Psalm 110 / Acts 2 candidate is absent from confirmed route results. The actual browser flow did not complete. |
| Psalm 22:1 / Mark 15:34 | **API/regression evidence only** | Psalm 22 projection is `not_represented` and contains no Mark 15 confirmed route. Existing generic cross-reference controls remain in Companion data and their frontend behavior is covered by the frontend suite. The actual browser flow did not complete. |
| No eligible handoff / negative controls | **Automated tests pass; some live outage and race scenarios remain untested** | Frontend tests cover wrong parent, kind, or local ID; shared source/topic matches; duplicate IDs; partial/failed projections; feature flag off; stale chapter selection; disabled/failed handoff; and history not being created before successful verification. The API test keeps Deuteronomy 32 / Psalm 82 held. No explicit test activated two different connections quickly or closed Companion during pending verification; no live outage run was made. See [regression report](03-integrity-and-regression.md). |

The Jonah gap is a real reader-path failure, not an incorrect route: verification remains fail-closed and does not create a false route or history entry. The smallest correction is to make the already-existing Jonah three-days claim eligible for a visible source-side discovery at Jonah 1:17 and serialize its exact identity within the current card limit. This requires no new CKL record or bridge. No application correction was made in NE-11D.

## Browser, responsive, and accessibility outcomes

- Actual Genesis browser result: selected route article had `aria-current="true"`, a `role="status"` selection announcement, and focus moved to the route heading. The rendered heading is an `h6` named from the destination passage; the temporary harness queried `h3`, so its extracted heading field was empty. The route explanation disclosure exposed the category, supporting identity, sources, and uncertainty.
- The existing Selenium handoff regression also verified Enter-key activation and route focus, but its Companion context is fixture-injected. It is not counted as CKL-backed keyboard acceptance. No real screen-reader session was available.
- Firefox was asked for a 390 × 844 window, but reported `window.innerWidth=500`, `documentElement.clientWidth=488`, DPR 1, and `scrollWidth=488`. The 760px responsive breakpoint matched and no horizontal overflow was observed at that effective width. **390 CSS-pixel coverage is incomplete.** No Chrome, physical mobile browser, or device was available.
- Route following and Return to origin passed for Genesis. Browser Back, long-list expansion, Maps/Locations, and Archaeology were covered only by automated regressions, not this actual browser session.
- The first Genesis journey passed twice. The wider temporary browser run completed Genesis, then yielded Selenium timeouts in later scenarios. It was stopped during teardown after about 445 seconds and exited with `KeyboardInterrupt`; those scenarios are reported incomplete. No UI result is inferred from the timeouts.

## Acceptance outcome

The Genesis discovery-to-route handoff preserves identity, context, evidence, uncertainty, focus, and return position. NE-11D acceptance is **NO-GO** until the Jonah source-side discovery is exposed and the incomplete browser journeys are rerun. See [final decision](05-final-acceptance-decision.md).
