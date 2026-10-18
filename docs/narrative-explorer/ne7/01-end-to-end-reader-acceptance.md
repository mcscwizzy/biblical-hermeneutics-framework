# NE-7.1 — End-to-end reader acceptance

**Date:** 2026-10-16
**Baseline:** `origin/master` = `480141f9b19e627c3f1d59ee67ad6aa6562812bd`
**Acceptance branch:** `test/narrative-explorer-ne7-reader-acceptance`

## Decision

The integrated Narrative Explorer reader flow passed its local Firefox acceptance cases: passage selection, Companion entry, section navigation, source inspection, authored connection navigation, trail history, reader return, ordinary reading, Maps focus outcomes, retry, and offline cache behavior. Browser-history restoration and focus/selection prerequisites were exercised. CKL-backed projection and API contract tests passed. This is a local result; it does not certify hosted runtime or public launch.

NE-7 overall remains **VALIDATION PENDING** because a real spoken screen-reader session and true 390 CSS-pixel viewport were not available, the hosted Vercel runtime is unverified and has a recorded bundle-size failure, and the compatibility run still contains 15 pre-existing Commentary/fixture/licensing expectation failures documented in `06-performance-and-regressions.md`.

## Baseline and conditions

- The worktree was created directly from the verified master SHA above. Master was not changed.
- The master deployment safeguard remains `"deploymentEnabled":{"master":false}` in `vercel.json`; Narrative Explorer remains disabled by default.
- Browser: Firefox 155.0.1 headless, geckodriver 0.37.1; browser and application were local. The geography Selenium suite ran against a disposable study database and SQLite CKL index. Synthetic focus records existed only in browser fixtures.
- Tests against the protected study database used `BHF_STUDY_DB_READ_ONLY=1`. Its SHA-256 was identical before and after: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.
- No paid AI provider was called. No deployment or environment configuration was touched.

## Reader journey

| Step | Result | Evidence |
|---|---|---|
| Open reader, choose book/chapter and passage | PASS | Browser checks waited for the live selection state and rendered passage before opening Companion. Genesis 1:1 was explicitly selected for keyboard activation checks; John 1 was used for reader smoke navigation. |
| Open Companion → Explore the Narrative | PASS | Explorer stays disabled by default; feature-off browser test saw no Explorer or Maps request. With passage selected, the resource loaded the selected passage. |
| Navigate six sections and inspect evidence | PASS | UI/API browser path and projection tests confirmed section navigation and evidence detail access. See the six section contract and coverage caveats in `02-hermeneutical-and-source-parity.md`. |
| Follow authored connection and trail | PASS | Trail/browser-history path passed in the geography suite; authored relationship constraints and traversal limits passed projection/API tests. |
| Open Maps and return | PASS | Actual passage maps and isolated synthetic exact-target fixtures passed; absent and unsupported focus outcomes remained distinct. |
| Return to passage and continue reading | PASS | Selection and browser back/forward checks passed; ordinary search/navigation and Companion open/close smoke checks were exercised. |

The browser harness verified the current application contracts, not every possible user path or every chapter. The protected study database remained read-only. Full browser command and test names are recorded in `05-accessibility-mobile-offline.md` and `06-performance-and-regressions.md`.

The general Firefox smoke suite separately exposed a pending default reader fetch: the page shell and JavaScript load, but the passage heading/selection does not initialize. A direct Python HTTP request to the same API returns the expected chapter. This discrepancy did not reproduce in the dedicated feature-enabled geography suite, but leaves ordinary default reader initialization unverified in that harness and keeps broader reader acceptance pending.

## Preservation and restoration

The browser suite preserved the selected book/chapter/verse context across Explorer, trail, Maps and reader return, and verified Back/Forward navigation. Translation/range preservation was separately exercised by translation comparison tests. Browser focus was usable for keyboard activation and Companion open/close; actual speech output and every focus-return branch still need human AT review. Scroll/focus restoration was not measured for every combination of trail and map close behavior, so those edge cases remain a manual release check.

## Coverage is not a research-completeness claim

The current census has 1,189 chapters: 985 with passage-specific eligible evidence, 132 with no eligible CKL material, 68 with contextual coverage, 3 with entity-only coverage, and 1 with incomplete/unknown coverage. These are inventory states, not judgments that a chapter is fully researched. The residual NE-A2 queue still has 330 distinct CKL IDs; the current placement audit reports 839 distinct unclassified IDs. Chapters with no eligible source material are not presented as interpretive conclusions. Details and pilot counts are in `02-hermeneutical-and-source-parity.md`.

## Local / hosted distinction

This acceptance verifies a local reader and locally built source-backed CKL index. It does not verify Vercel packaging, hosted SQLite inclusion, hosted cold starts, Tyndale archive provisioning, assistive technology, Production deployment, or public feature enablement. Public launch is **NO-GO** pending those release gates.
