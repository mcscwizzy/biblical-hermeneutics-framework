# NE-11D final acceptance decision

## Decision: NO-GO

### Feature acceptance

Genesis 1:1–5 → John 1:1–5 passes in the actual CKL-backed browser: exact identity, classification, sources, uncertainty, focus, destination selection, and return to origin were preserved. The Jonah 1:17 source-side journey fails its required acceptance condition because the current Companion response omits `jonah#claim:jonah-three-days` from visible card evidence. The verified Jonah → Matthew route itself is present and retains later reception direction and uncertainty, but the required source-side handoff is unavailable. That is a blocking reader-path defect. No incorrect route is produced.

**Smallest corrective work:** in a separately authorized correction phase, adjust deterministic Companion presentation eligibility/ranking so the existing Jonah three-days claim is surfaced on the Jonah 1:17 discovery within the existing card limit, preserving the exact object/kind/local-ID identity. Do not add a CKL object, change the bridge, or promote curation. Add a real CKL-backed browser regression for the source and reciprocal Matthew starts, then rerun both endpoint journeys and return/history checks.

### Repository CI health

The targeted NE-11 backend/package suite passed 691 tests (8 skipped; 11 subtests passed), the focused CKL protection suite passed 135 tests, and all 14 frontend test files passed. Six presentation structured-output failures, one CKL governance failure, and 24 release-path sanitizer violations reproduce identically on clean merged master. They are baseline issues, not NE-11 regressions, but they leave overall repository CI/release gates red. Preserve the gates and correct these items in their own reviewed work.

### Vercel build readiness

The merged-tree Preview is Ready and serves CKL-backed API responses. Local packaging and relevant Vercel/Tyndale tests pass. Production is **not ready for NE-11 promotion** until the Jonah correction and its acceptance pass. Production remains on pre-NE-11 SHA `e2f696db98be2e1662916a14781a6203073a4605`; `master` Git deployments are disabled. No deployment or promotion occurred.

### Coverage conditions before reconsideration

1. Fix and browser-verify the Jonah source-side discovery and Matthew reverse handoff.
2. Complete actual browser checks for Acts 2/Psalm 110, Psalm 22’s generic cross-reference path, no-eligible-route behavior, and the pending/stale/failure cases. Current code-level regressions pass, but these live browser cases did not complete.
3. Exercise 390 CSS pixels in a browser/device that reports that effective width; the available Firefox clamped to 488 CSS pixels. Run keyboard-only acceptance with real CKL evidence and a screen reader when available.
4. Run actual cold and warmed network samples for Genesis, Jonah, Psalm 22, and a no-linkable-evidence chapter, including request cancellation and a matched NE-11C1 run. Current Genesis local measurements show 1.645 s median action-to-focus across two cold launches and roughly 236 kB per projection response; other required browser timings and the C1 comparison remain unmeasured.
5. Recheck offline/error recovery with explicit simulated outage and reconnect steps, and verify only resources present in the installed offline pack.
6. Resolve or separately accept the documented baseline CI/release-gate failures, then verify a Preview from the exact reviewed commit and obtain explicit deployment authorization.

### Release status separation

| Area | Status |
|---|---|
| NE-11 feature acceptance | **NO-GO** — Jonah source-side handoff missing; several required browser journeys incomplete |
| Targeted NE-11 regression coverage | **Pass**, with listed live-browser coverage gaps |
| Repository-wide CI/release health | **Not green** — baseline test and sanitizer failures remain |
| Vercel build | **Preview Ready**; production promotion gate not met |
| Production deployment | **Not deployed**; serving pre-NE-11 SHA |

Next authorized work is a narrow Jonah discovery presentation correction followed by a renewed acceptance run. This NE-11D branch contains reports only and is not merged or deployed.
