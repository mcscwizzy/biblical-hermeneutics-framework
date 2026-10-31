# BHF UI-05 — Release Decision

## Recommendation: GO

The repository GUI gate is green on source SHA `77a9901f549057703351ecc0b00afe633a8a45aa`. The final serialized GUI run completed with **141 passed, 0 failed, 0 errors, 0 skipped**. All ten UI-04 cases passed within that same full run. The two additional full-suite failures found on the first socket-enabled run were verified as test setup isolation issues, corrected without application behavior changes, and passed in the final complete run.

## Release gates

| Gate | Result | Evidence |
|---|---|---|
| Full GUI acceptance | PASS | 141 passed, 0 failed, 0 errors, 0 skipped; 1,909.87 seconds. See [full GUI rerun](03-full-gui-rerun.md). |
| UI-04 persistent cases | PASS | All ten original node IDs passed in the full suite and in separate isolated reruns. |
| Frontend | PASS | `npm test`: 16 tests passed, 0 failed, 0 skipped. |
| Python/API, Tyndale, Narrative Explorer, packaging, retired Commentary routes | PASS | 232 passed, 55 pre-existing skips, 4 subtests passed. The active Tyndale browser integration passed against the provisioned notes database; retired generated Commentary endpoints retained HTTP 410. |
| Framework validation | PASS | `.venv/bin/python tools/validate.py framework/`: 94 modules valid. |
| CKL source and generated database integrity | PASS | 687/687 source objects valid with 0 errors; provisioned CKL database verified with 687 objects and inventory fingerprint `90fa7547ea4146328ab1fc4e9f4ca1b262f810e0e503c589b64a5f9b8c4a08c6`. |
| Preservation boundaries | PASS | No CKL or Narrative Explorer research inputs, Tyndale content/services/licensing, deployment settings, or retired route behavior changed. The provisioned Tyndale database hash remained identical before and after integration. |
| Diff and worktree | PASS | Final `git diff --check` is clean; the remediation branch is committed with no generated repository artifacts. |

The Python/API batch reports 55 skips. The test sources contain pre-existing explicit skips for removed or obsolete web model/runtime inference behavior; UI-05 added no skips. The final GUI run had no skips. CKL validation retains 14 pre-existing warnings and reports zero errors; UI-05 made no CKL edits.

## Changes and remaining findings

The two application changes are limited to avoiding an unrelated CKL load in the lexical Word Study path and preventing late map requests from overwriting a newer passage. The other changes correct Selenium click lifecycle, use a private one-record editor fixture, and update tests to the current approved Ask BHF handoff, selection, translation, and study-panel contracts. The additional cache and range fixes repair test isolation only. Details are in [failure classification](01-failure-classification.md) and [remediation evidence](02-remediation-evidence.md).

There are no unresolved release-blocking findings and no exception or waiver is required. The branch has not been merged or deployed; no PR was created. The tested source commit is `77a9901f549057703351ecc0b00afe633a8a45aa`; the follow-on documentation commit records this final acceptance decision.
