# BHF UI-04 — Final Release Decision

## Decision: NO-GO for a repository release

UI-01, UI-02, and UI-03 reader-specific acceptance passes on the tested source commit. The integrated journeys, live Tyndale database checks, responsive checks, focused GUI reruns, frontend tests, Python/API tests, and integrity gates found no newly introduced release-blocking regression. UI-04 also corrected the contextual Tyndale workspace navigation defect found during real-reader verification.

The broader release decision is **NO-GO** because the full GUI suite still has ten failures that reproduce on the untouched `origin/master` baseline. Several cover central reader, Ask BHF, Companion, and navigation behavior. They are not new UI-04 regressions, but they remain unresolved acceptance failures and have not been formally reclassified or waived. Do not release the repository until those cases are fixed or explicitly reviewed and the full GUI gate is green.

## Acceptance status

| Major area | Status | Release finding |
| --- | --- | --- |
| UI-01 Study Companion integration | PASS | Ask BHF handoff, passage actions, personal study, maps, locations, archaeology, and neighboring reader paths were exercised. The persistent baseline GUI failures remain a broader suite blocker. |
| UI-02 Tyndale Study Notes | PASS | Official database integrity and attribution verified; live introductions, single/range matching, chapter changes, restored session, full workspace, mobile, and offline unavailable state passed. The workspace-button defect was fixed and regression-tested. |
| UI-03 Narrative Explorer | PASS | Six topics, Genesis 6 governance disclosures, Exodus 3 geography separation, Jonah/Matthew direction and return, Psalm 22 negative controls, feature gate, trail provenance, and offline/unknown coverage were exercised. |
| Responsive, keyboard, and semantic accessibility | PASS | 320–1440 px responsive coverage includes an actual 390 px browser viewport. Keyboard, focus, visible status semantics, Escape layers, browser history, and sheet transitions passed. Spoken output with a screen reader was not tested. |
| Performance | PASS | Five repeated cold/warm samples show one projection request per Explorer opening, no topic-navigation request, and 62 Explorer nodes versus UI-03’s 60. Different passage/setup prevents an unsupported timing regression claim. |
| CKL, Tyndale, packaging, and retired-route integrity | PASS | CKL is unchanged with 0 errors and the same 14 classified warnings; Tyndale data validates; packaging/framework checks pass; retired BHF Commentary remains HTTP 410. |
| Repository-wide GUI regression gate | FAIL | Ten failures reproduce on the fetched baseline. Full run was 122 passed, 16 failed, 1 setup error, and 2 skipped; isolated reruns resolved transient failures and corrected the stale keyboard expectation, but the ten baseline failures remain. |

## Release blockers and limitations

The release blocker is the ten unresolved baseline GUI failures listed in [the test results](03-performance-and-integrity.md#test-results). Because they affect reader selection, mobile Ask BHF, Companion context, workspace tabs, and primary navigation, a broad repository release should wait for owner review and a green full GUI run. UI-04 did not change the code paths behind those failures, and an untouched baseline run reproduced all ten.

The initial full GUI run also had two Selenium skips and one renderer setup error. Tyndale’s skipped tab test passed on isolated rerun, as did the renderer case and other transient failures. A separate mobile viewport measurement was skipped by Selenium session availability; the required 390 px viewport and responsive widths were verified through other browser tests. No screen-reader runtime was available, so spoken output remains unverified. The fresh live offline Tyndale probe had no service-worker controller; service-worker behavior is covered by separate passing frontend/GUI tests.

## Exact tested revision

- Repository: `mcscwizzy/biblical-hermeneutics-framework`
- Branch: `test/bhf-ui04-integrated-reader-acceptance`
- Fetched `origin/master` baseline: `c44c19a708f1073e1af815a477f8c9b6701bd4ea`
- Exact tested source commit: `183fa056d1b32fc0e1a19aa0eb7115c3e23731cf`
- Test evidence and browser screenshots: [integrated reader report](01-integrated-reader-acceptance.md), [accessibility/mobile report](02-accessibility-mobile-and-navigation.md), and [performance/integrity results](03-performance-and-integrity.md).

The tested source revision contains only the focused Tyndale workspace visibility correction and acceptance-test updates. CKL, curation, bridge, source lock, manifest, provenance, and review records are unchanged. The acceptance reports and screenshots are committed on the branch; no PR, merge, or deployment is part of this transaction.
