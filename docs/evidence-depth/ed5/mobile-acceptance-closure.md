# ED-5 Mobile Acceptance Closure

## Status

**BLOCKED — browser acceptance remains unverified.** The corrected GitHub Actions
GUI job is still running its Compose/browser step. No completed-run logs or browser
evidence artifacts are available yet. Do not treat this gate as passed until the
1440px, 390px, and 320px Chromium cases complete and report their effective CSS
viewport widths.

## Baseline and scope

- ED-5 PR #80 was merged into `master` at `6e33d16e891614f6527fd9ede943cb1a7c5c1913`.
- Work is on `fix/ed5-mobile-acceptance`, based on that merge commit.
- No CKL records, source identities, held relationships, or human-review states
  were changed. No real review decisions were written.
- No Vercel deployment was triggered. The existing `master` production setting
  is preserved; Vercel reported zero deployments for this branch's commits.

## GUI startup investigation

The original failed GUI run was `43218071067`. It built the `bhf-web` image but
did not preserve container diagnostics before teardown. The failure was
reproduced in GUI run `43350244152` (job `131639279871`), whose diagnostic artifact
was uploaded before cleanup:

- Compose created the absent `.bhf` bind-mount directory as `root:root` with
  mode `0755`.
- The web container runs as UID/GID 1000. Its entrypoint could not seed the
  lexical database and exited with status 1:
  `cp: cannot create regular file '/app/.bhf-data/.lexicon.sqlite.tmp.1': Permission denied`.
- The lexical database was missing, `bhf-web` was exited/unhealthy, and Selenium
  tests did not begin. This was a filesystem ownership failure, not a missing
  runtime setting or failed health-check dependency.

The minimal fix prepares `.bhf` in the Actions runner as UID/GID 1000 with mode
`0755` before Compose starts. Health checks and healthy-service dependencies stay
enabled. The workflow now captures `docker compose ps -a`, no-color web logs,
health state/logs, mount metadata, and host directory ownership before cleanup
on failure. Diagnostic filtering redacts configuration values and credentials.

Corrected run `43350876711` (job `131641351956`, tested code SHA
`ea6c0ed94bbbaaafb984b53f6713984a1fc5d9ed`) passed checkout, artifact-directory,
and writable-mount preparation. At `2026-11-13 03:22 UTC`, its combined Compose
and browser-test step remained in progress; the browser version, effective
viewport widths, test outcomes, and screenshots were not yet available.
At `2026-11-13 03:25 UTC`, that step was still in progress and had no published
logs or artifacts.

## Browser matrix

The repeatable Selenium suite uses the existing `selenium/standalone-chrome`
service. Each ED-5 case asserts `browserName == Chrome`, records the Chrome and
ChromeDriver versions, and checks both `window.innerWidth` and
`document.documentElement.clientWidth` before counting the viewport as valid.

| Requested CSS width | `window.innerWidth` | `documentElement.clientWidth` | Result / evidence |
| ---: | ---: | ---: | --- |
| 1440px | Pending | Pending | Unverified; corrected Actions run still active |
| 390px | Pending | Pending | Unverified; corrected Actions run still active |
| 320px | Pending | Pending | Unverified; corrected Actions run still active |

Browser/driver versions: **pending completed-run output**.

The GUI test writes light/dark collapsed and expanded screenshots for each width
to `tests/gui/artifacts/` for the Actions artifact. No acceptance screenshots
are available from the active run yet.

## Repeatable coverage added

`tests/gui/ne11d1/test_ed5_mobile_acceptance.py` adds these browser cases:

- `test_ed5_empty_notice_and_terminology_guide_acceptance` at 1440px, 390px,
  and 320px.
- `test_genesis_12_source_disclosure_stays_attached_to_exact_record` at 1440px
  and 390px.

The ED-5 cases verify the completed-empty 1 Kings 2 notice, absence of that
notice for failed and partial CKL states, the collapsed guide and all 14 terms,
native disclosure semantics, Tab/Enter/Space behavior, visible focus, reduced
motion, light/dark contrast, 44px minimum targets, long-definition readability,
and document/element horizontal overflow. They log browser versions and actual
viewport metrics. The collected GUI suite also includes regression journeys for
1 Corinthians 11:3, Jonah 1:17 / Matthew 12:40, and return-to-origin navigation.
The Genesis 12 source disclosures are checked at 1440px and 390px.

The GUI workflow runs the non-slow suite for both pull requests and pushes to
`fix/ed5-mobile-acceptance`. Configured remote Chrome failures now fail the test
instead of being skipped. Firefox cannot satisfy these viewport cases.

## Completed checks

- Frontend: `npm test` — 17 test files passed.
- Reader/API/projection/curation regressions and diagnostics — 572 passed.
- Release/source-integrity/NE-9C/NE-10 compatibility set — 73 passed,
  13 subtests passed.
- Framework validation — 94 modules valid.
- CKL strict validation — 687 valid objects, zero errors, 14 existing warnings.
- Current NE-9C compatibility validation — passed; 3,925 reviewed relationships,
  4,061 inventory rows, 433 curated runtime identities, 44 bridges, and 7 held
  candidates; protected hashes remained stable.
- GUI test collection — 158 cases collected, including the ED-5 cases above.
- `git diff --check` — passed.

Local Chromium and Docker execution were unavailable, so the browser run depends
on GitHub Actions. The corrected Actions run is the only outstanding acceptance
evidence; until it completes successfully and its artifacts are inspected, the
release recommendation remains **BLOCKED**.
