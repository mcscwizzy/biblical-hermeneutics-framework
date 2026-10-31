# BHF UI-05 — Implementation Plan

**Base branch:** `test/bhf-ui04-integrated-reader-acceptance`

**Base SHA:** `d279e94d71577b738d4a07d21ab00215e63e28f9`

**Remediation branch:** `fix/bhf-ui05-repository-gui-gate`

The remote fetch identified `origin/master` at `c44c19a708f1073e1af815a477f8c9b6701bd4ea` and the UI-04 branch at the expected SHA above. The remediation branch was created from the UI-04 SHA, not from master.

## Scope

UI-05 addresses the ten persistent GUI cases called out by UI-04 acceptance. The work preserves the UI-01 through UI-03 interactions and the reviewed CKL and Narrative Explorer inputs. It does not change deployment configuration or release production.

## Method

1. Confirm the UI-04 branch identity and read the repository instructions and all four UI-04 reports.
2. Reproduce each listed GUI case independently from a clean browser/app fixture and record its original failure signature.
3. Trace each failure through its test, browser selector/state, application route or service, and approved product interaction contract.
4. Make only the required application, test-helper, fixture, or expectation correction; keep different root causes separable.
5. Run each affected case independently, then its neighboring journey tests, followed by the one controlled full GUI run.
6. Run the requested frontend, Python/API, Tyndale, Narrative Explorer, CKL, framework, packaging, retired-route, and preservation checks.
7. Record exact results and tested SHA, review the complete diff, commit and push the remediation branch, and leave the worktree clean.

## Acceptance rule

Recommend GO only if the complete required GUI run and every mandatory repository gate pass, with no unresolved release-blocking finding. No exception has been approved in advance. Isolated GUI reruns are supporting diagnostics and do not substitute for the complete suite.
