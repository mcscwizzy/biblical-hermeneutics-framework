# NE-7.7 — Release readiness decision

**Decision:** `BHF_NARRATIVE_EXPLORER_NE7_VALIDATION_PENDING`
**Local reader:** accepted for the verified paths, with limitations below
**Hosted/public release:** **NO-GO**

## Acceptance matrix

| Acceptance area | Outcome | Basis |
|---|---|---|
| Narrative Explorer UI | PASS | Local Firefox passage-first workflow, six-section navigation, evidence inspection, trail, return, and feature-off request behavior passed. |
| CKL source integrity | PASS | Source fingerprints and verified SQLite identity match; no CKL mutation. |
| Hermeneutical classification | PASS | NE-5A classification and source-specific uncertainty safeguards passed pilot/projection checks; coverage is explicitly partial. |
| Evidence Trails | PASS | Authored relationship, identity, hop/node limit, source and browser-history tests passed. |
| Maps integration | PASS | Local ordinary and passage-first Maps, focus outcomes, synthetic exact matches, compact payload, and deferred detail passed. |
| Commentary compatibility | PASS | Existing reader availability and focused integration tests passed; frozen material unchanged. Older snapshot/count tests have characterized baseline failures. |
| Tyndale compatibility | PENDING | Local fixture/UI passed. Hosted SQLite/archive provisioning remains unverified. |
| Translation and reader state | PENDING | Existing catalog/registry/settings and selected-range comparison passed. General Firefox smoke saw a stuck initial Bible fetch and no selected passage; imported-translation end-to-end and exhaustive note/highlight persistence coverage remain limited. |
| Mobile and keyboard accessibility | PENDING | Enter/Space and tested keyboard flows passed; Firefox viewport clamped to 500px, leaving 390px and 768px tablet acceptance pending. No trap found in exercised paths. |
| Actual screen-reader acceptance | PENDING | No accessible desktop/speech session; the report provides a human test script. |
| Offline and recovery | PASS | Local offline cached reading, SW v49, explicit missing evidence, retry and feature-off behavior passed. |
| Local performance | PENDING | SQLite API request measured about 1.9–2.2 s locally; the JSON fallback browser first request measured about 76.4 s, materially slower than the historical 30.1 s diagnostic. Filesystem state was uncontrolled, so this needs a comparable rerun/profile before release. No hosted claim. |
| Test-suite health | PENDING | Projection/contract and dedicated geography browser suites passed, but general Firefox UI smoke has 2 unresolved reader-initialization failures and 15 characterized compatibility failures remain. |
| Hosted Vercel runtime | BLOCKED | Latest failed Preview exceeded enforced 225 MB function limit at 317.82 MB; large-function activation and hosted SQLite/cold-start checks are unverified. NE-7 made no deployment/configuration change. |
| **Public launch readiness** | **NO-GO** | Required hosted runtime, real AT review, Tyndale provisioning, narrow viewport, and compatibility failure disposition remain outstanding. |

## Separate release states

- **Local feature acceptance:** Explorer flow and source contracts passed in the dedicated geography browser suite. Broader acceptance remains pending because general Firefox smoke left the default reader fetch unresolved; actual AT, 390px and tablet items are also pending.
- **Local release artifact:** source-built SQLite index verifies against committed CKL identity. This is not a Vercel function artifact.
- **Hosted Preview:** not verified in NE-7. Prior Preview failed with `LAMBDA_SIZE_EXCEEDED`: 317.82 MB versus a 225 MB enforced limit. Hosted SQLite inclusion, cold starts and current Maps/Explorer API behavior therefore remain unproven.
- **Production deployment:** none.
- **Public enablement:** none; Explorer remains disabled by default.

## Outstanding release blockers

1. Resolve the Vercel function-size limit or approve a supported hosting alternative, then validate an actual Preview artifact and CKL SQLite runtime.
2. Measure hosted cold-start and warm passage/Maps behavior after Preview succeeds.
3. Verify Tyndale archive provisioning through the deployed runtime without downloading unapproved data.
4. Complete spoken review with Firefox + Orca, NVDA, or VoiceOver.
5. Repeat narrow/tablet layout acceptance at measured ~390 and 768 CSS-pixel viewports.
6. Independently disposition the 15 pre-existing compatibility failures, preserving archaeology rights, frozen Commentary and evidence-provenance rules.
7. Diagnose why the general Firefox smoke's page-side Bible request remains pending although the same local API returns HTTP 200; verify ordinary reader initialization after resolving the runtime/test harness discrepancy.

## Protected state and transaction boundary

- Verified master SHA: `480141f9b19e627c3f1d59ee67ad6aa6562812bd`.
- Branch: `test/narrative-explorer-ne7-reader-acceptance`, created directly from that SHA in an isolated worktree.
- Master's Vercel deployment safeguard remains intact. No push, merge, deployment, environment-variable update, feature-default change, or production setting change occurred.
- Protected study database pre/post SHA-256: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.
- No CKL or generated biblical evidence, Commentary prose, translation licensing data, or production Tyndale provisioning was changed.
- Local commit SHA and final worktree status are supplied in the transaction handoff after commit.
