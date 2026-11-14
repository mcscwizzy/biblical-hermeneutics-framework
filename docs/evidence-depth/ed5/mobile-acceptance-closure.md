# ED-5 Mobile Acceptance Closure

## Validation status

The browser connectivity, mobile viewport, and responsive GUI regressions are
closed on `fix/ed5-mobile-acceptance`. GitHub Actions run
[43591754383](https://github.com/mcscwizzy/biblical-hermeneutics-framework/actions/runs/43591754383)
completed successfully on commit `bb16f49a109f74c4f9bd4baf21f99887f60b7b1b`.
It passed the remote-browser smoke gate, all five ED-5 acceptance cases, and
the bounded GUI regression. No merge or deployment has been performed.

## Scope and protections

- Work is on `fix/ed5-mobile-acceptance`; this note does not associate the
  branch with unrelated PR #80.
- No CKL records, source identities, evidence, held relationships, review
  states, or review decisions were changed.
- `vercel.json` retains `deploymentEnabled: false` for
  `fix/ed5-mobile-acceptance`. Keep this branch guard in the eventual PR so
  removing it cannot enable a branch deployment. No deployment was requested
  or triggered.

## Connectivity failure and root cause

The original runs [43350876711](https://github.com/mcscwizzy/biblical-hermeneutics-framework/actions/runs/43350876711)
and [43359040540](https://github.com/mcscwizzy/biblical-hermeneutics-framework/actions/runs/43359040540)
reported healthy `bhf-web` and Selenium Chrome containers but ended with
**2 passed and 156 setup errors**. The first error was
`net::ERR_CONNECTION_REFUSED` from `_seed_browser_offline_fixture()` in
`tests/gui/conftest.py`; Selenium session-creation timeouts followed.

The published app itself was reachable. DNS resolved `bhf-web` to
`172.20.0.2` in both containers, TCP port 8080 accepted connections, both
`/api/health` and `/offline` returned HTTP 200, proxy variables were unset, and
Uvicorn reported a `0.0.0.0:8080` bind. A separate remote Chrome session also
loaded both routes successfully. The failing endpoint was the ephemeral app
started by the GUI fixture: it bound to `127.0.0.1` inside `gui-tests`, which
is not reachable from Chrome in `selenium-chrome`. Driver cleanup was skipped
when setup failed, leaving sessions behind and causing the later session
timeouts. This isolated the initial failure to the fixture's bind address and
the timeout cascade to its setup cleanup lifecycle.

The fixture now binds remote-browser test servers to `0.0.0.0` and gives Chrome
the `http://gui-tests:<ephemeral-port>` address; local-browser runs retain
loopback. Driver setup quits a partially initialized session on setup failure.
The browser smoke checks Grid is idle, opens one remote Chrome session, visits
the health and offline routes, and cleans up only the session it created. A
fast connectivity gate runs before ED-5 and the broader suite, so Chrome/app
reachability failures stop the ordered GUI command immediately.

| Probe | `gui-tests` | `selenium-chrome` |
| --- | --- | --- |
| `bhf-web` DNS | `172.20.0.2` | `172.20.0.2` |
| TCP `bhf-web:8080` | Connected | Connected |
| `/api/health` | HTTP 200, `status=ok` | HTTP 200, `status=ok` |
| `/offline` | HTTP 200 | HTTP 200 |
| HTTP(S)/ALL proxy variables | Unset | Unset |

The Actions job's probe from Selenium passed, followed by
`GUI_CONNECTIVITY_SMOKE=PASS`. The live smoke plus its two Grid lifecycle checks
reported **3 passed in 3.90 seconds**. Remote Chrome navigated to the app and
the ephemeral fixture server without proxy settings or connection errors.

## ED-5 mobile acceptance

The ED-5 file passed **5 tests in 50.53 seconds** in the hosted run. Chrome and
ChromeDriver were both **157.0.8103.38**. Each test set the headless window and
CDP device metrics, then asserted the actual `window.innerWidth` and
`document.documentElement.clientWidth` values:

| Requested viewport | Effective `innerWidth` | Effective `clientWidth` | Result |
| ---: | ---: | ---: | --- |
| 1440 × 1200 | 1440px | 1440px | Pass |
| 390 × 844 | 390px | 390px | Pass |
| 320 × 844 | 320px | 320px | Pass |

Three cases check the empty research notice and terminology guide at desktop,
mobile, and narrow mobile sizes. Two more check that the Genesis 12:1–3 source
disclosure stays attached to the exact CKL claim at 1440px and 390px. The
record remains visibly draft and requires human review.

Accessibility checks passed for native `<details>` / `<summary>` semantics
(`DisclosureTriangle` in Chrome's accessibility tree), Enter and Space
operation, a solid 3px focus indicator, and reduced motion. Tested interactive
targets were at least 44px. The lowest measured text contrast was **6.13:1**,
above the 4.5:1 threshold. The guide's long definitions stayed readable, the
17 checked elements had no horizontal overflow, and the reported document width
matched each effective viewport.

I visually reviewed representative generated ED-5 captures in the local
evidence bundle at 1440px, 390px, and 320px, plus the Genesis 12 mobile
disclosure. The guide wraps at 320px, stays within the viewport, and leaves the
mobile navigation visible. The source view shows the expected claim and CKL
identity together with its draft and human-review status. The hosted run
uploaded its own screenshots, smoke evidence, and JUnit reports in the
`gui-test-artifacts` artifact (ID `14113550361`,
6,286,233 bytes; SHA-256
`27ad20cf3acb078e0eb06829144965598ea9369498f155189642bb1d9c521233`). The
artifact is linked from the [hosted Actions run](https://github.com/mcscwizzy/biblical-hermeneutics-framework/actions/runs/43591754383).

## Bounded GUI regression

After the browser smoke and ED-5 passed, the workflow ran
`pytest -q --maxfail=3 --junitxml=/artifacts/gui-regression.xml
/workspace/tests/gui -m 'not slow'` under a 60-minute shell timeout. The hosted
result was **163 passed, 3 skipped in 847.86 seconds** (14 minutes, 7 seconds).
All three skips are PWA tests that report `Service worker is unavailable` in
the headless Selenium environment. No setup errors, connection refusals, or
WebDriver session-creation timeouts recurred. The uploaded artifact contains
`gui-connectivity-smoke.xml`, `ed5-mobile-acceptance.xml`, and
`gui-regression.xml` plus browser screenshots and failure diagnostics when
present.

The broader runs also exposed responsive interaction timing issues. The fixes
use shared click-readiness helpers, wait for the mobile companion's transition,
and synchronize real Chrome window resizing with the requested viewport before
asserting geometry. The affected mobile sheet, companion navigation, and
reader-first regression cases passed in the final hosted suite.

## Closure

The final hosted browser gate, ED-5 cases, accessibility assertions, exact
viewport checks, and bounded GUI regression all pass. The branch-specific
Vercel deployment guard remains in place. Do not merge or deploy as part of
this closure.
