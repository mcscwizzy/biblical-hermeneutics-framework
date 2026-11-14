# ED-5 Mobile Acceptance Closure

## Validation status

The remote-browser connectivity and mobile viewport failures are isolated and
fixed locally. The fail-first browser gate, ED-5 acceptance, and bounded
non-slow GUI regression all pass using real remote Chrome in a separate
container. Actions run `43561414091` passed connectivity and ED-5 but exposed
three broader GUI failures; the follow-up fixes documented below pass locally.
No merge or deployment has been performed.

## Scope and protections

- Work remains on `fix/ed5-mobile-acceptance`, continuing the ED-5 PR #80 line.
- No CKL records, source identities, evidence, held relationships, review
  states, or review decisions were changed.
- The existing `fix/ed5-mobile-acceptance: false` Vercel deployment guard is
  retained. Do not remove it in the PR: doing so could enable branch deployment.
  No deployment was requested or triggered.

## Actions investigation and root cause

Completed GUI runs `43350876711` and `43359040540` both reported healthy
`bhf-web` and Selenium Chrome containers, then ended with **2 passed and 156
setup errors**. The first setup error was `net::ERR_CONNECTION_REFUSED` while
`_seed_browser_offline_fixture()` in `tests/gui/conftest.py` navigated to
`/offline`; later Selenium session-creation timeouts followed.

The root cause was the ephemeral Uvicorn server created by the GUI fixtures.
It bound only to `127.0.0.1` inside `gui-tests`, while Chrome ran in another
container. That loopback address belongs to `gui-tests` and cannot serve the
remote browser. When the fixture failed during setup, its driver cleanup was
also skipped, leaving sessions behind and causing later session-creation
timeouts. The first failure was a fixture endpoint scope problem; the later
timeouts were a cleanup consequence, not an independent Chrome or Compose
network failure.

The current fixture binds ephemeral servers to `0.0.0.0` for remote Chrome and
uses `http://gui-tests:<ephemeral-port>`; local Chrome still uses loopback.
Driver setup now quits a partially initialized session on any setup exception.
The Actions workflow probes the application from Selenium, and the Compose test
command runs the fail-first connectivity utility and browser smoke before ED-5
or the broader regression.

| Probe | `gui-tests` | `selenium-chrome` |
| --- | --- | --- |
| `bhf-web` DNS | `172.20.0.2` | `172.20.0.2` |
| TCP `bhf-web:8080` | Connected | Connected |
| `/api/health` | HTTP 200, `status=ok` | HTTP 200, `status=ok` |
| `/offline` | HTTP 200 | HTTP 200 |
| HTTP(S)/ALL proxy variables | Unset | Unset |

The `bhf-web` Uvicorn log reports `0.0.0.0:8080`; the temporary fixture server
reported `GUI_TEST_SERVER_BIND=0.0.0.0` with the `gui-tests` alias and ephemeral
port. An explicit remote Chrome session had no proxy endpoint. It navigated to
`http://bhf-web:8080/api/health` and `/offline`; health was `ok`, and `/offline`
returned HTTP 200 with `document.readyState=complete`. The fixture smoke also
created a temporary server on `0.0.0.0` and reached both routes from Chrome.
These checks demonstrate that Chrome can reach the healthy app over the shared
network after the test fixture uses a container-reachable address. A local
smoke attempt also showed that a timed-out `webdriver.Remote` constructor can
leave a server-side session without returning a Python driver object. The smoke
now checks that Grid is idle before requesting Chrome and removes only sessions
created by that probe if the session response times out. A unit test verifies
that cleanup leaves any preexisting session untouched.

## Browser gate and ED-5 acceptance

The latest ordered local run passed `scripts/gui_connectivity_smoke.py` and
`tests/gui/ne11d1/test_connectivity_smoke.py` (**3 passed**, including the live
browser smoke and two Grid lifecycle checks). The smoke recorded Chrome and
ChromeDriver **155.0.8059.79**, created one remote session, loaded `/api/health`
and `/offline`, captured a screenshot, and quit the session.

The ED-5 acceptance file then passed: **5 passed in 143.25 seconds**. Chrome
and ChromeDriver were both **155.0.8059.79**. `_set_viewport()` sets the actual
headless window dimensions before CDP device metrics; every case verified that
both `window.innerWidth` and `document.documentElement.clientWidth` exactly
matched the requested CSS width.

| Requested width | Effective `innerWidth` | Effective `clientWidth` | Result |
| ---: | ---: | ---: | --- |
| 1440px | 1440px | 1440px | Pass |
| 390px | 390px | 390px | Pass |
| 320px | 320px | 320px | Pass |

The five cases cover the empty research notice and terminology guide at all
three widths, plus the Genesis 12 exact-record source disclosure at 1440px and
390px. Accessibility assertions passed for native `<details>`/`<summary>`
semantics (`DisclosureTriangle` in the accessibility tree), Enter and Space
operation, a visible 3px focus indicator, and reduced motion. Interactive
targets measured at least 44px. Text contrast passed the 4.5:1 threshold; the
lowest recorded ratio was 6.13:1. The tests also passed long-definition
readability, exact source/record identity, and horizontal-overflow checks.

I inspected the latest expanded-guide screenshots at 1440px, 390px, and 320px,
and the Genesis 12 mobile source disclosure. The guide wraps at 320px, keeps the
mobile navigation visible, and shows definitions without horizontal clipping.
The source disclosure shows the expected Genesis 12:1-3 claim and CKL identity;
review metadata remains displayed as draft and requiring human review. The
ED-5 JUnit report contains 5 passing cases. Screenshot and JUnit files are
generated evidence in `tests/gui/artifacts/` and are not source inputs to commit.

## Bounded GUI regression

After the connectivity and ED-5 gates passed, the bounded non-slow GUI
regression ran with `--maxfail=3` and a 60-minute timeout. Result: **158 passed,
3 skipped in 2215.05 seconds**. The JUnit report contains 161 tests, zero
failures, and zero errors. The previously isolated canonical detail,
canonical-to-note link, 390px companion click, and keyboard focus cases passed.
No setup errors, connection refusals, or WebDriver session timeouts recurred.

The broader regression exposed and verified a few related UI lifecycle and
interaction fixes. Passage-context refreshes are now limited to context-backed
resources so a late context response cannot replace an independent translation
comparison. Availability errors preserve usable local recommendations. GUI
journey selectors follow the current reader-first Browse research flow, and
native Selenium clicks wait out transient stale elements and mobile overlays.
The tests preserve their content, identity, navigation, and hit-target
assertions.

Actions run `43561414091` passed service health, the Selenium network probe, the
fail-first smoke, and all 5 ED-5 cases on Chrome/ChromeDriver
**157.0.8103.38**. Its broader run stopped at `--maxfail=3` with 19 passes and
these failures:

- `test_kephale_additional_record_is_passage_scoped_and_readable[390-844-True-mobile]`
- `test_psalms_evidence_is_contextual_scoped_traceable_and_readable[psalm145-mobile]`
- `test_keyboard_discovery_route_focus_and_escape[768-False]`

The first two clicks were intercepted by the fixed app dock because CDP
reported a 390px CSS viewport while headless Chrome's outer window stayed at
1440px. `tests/gui/viewport.py` now resizes the real Chrome window before CDP
metrics and asserts the effective dimensions; all GUI viewport tests use that
helper. The keyboard test now waits for the app's animation-frame focus restore
after the resource closes. The local targeted rerun passed all three failures,
and the full regression passed them as well. Earlier Actions runs
`43501993153` and `43502606551` also passed network and smoke but exposed the
same mobile hit-target mismatch. The hosted outcome for the follow-up commit is
reported from its branch Actions run.

## Generated reports and other validation

The latest local ordered and regression runs wrote:

- `tests/gui/artifacts/gui-connectivity-smoke-final.xml` — 3 passed, including
  the remote Chrome route check.
- `tests/gui/artifacts/ed5-mobile-acceptance-final.xml` — 5 passed.
- `tests/gui/artifacts/gui-connectivity-smoke-regression.xml` — 3 passed.
- `tests/gui/artifacts/gui-regression-final.xml` — 158 passed, 3 skipped, zero
  failures or errors (161 tests total).
- The three skips are PWA tests that require a service worker, unavailable in
  the headless Selenium environment.
- ED-5 PNGs under `tests/gui/artifacts/`, including light/dark collapsed and
  expanded guide views at all three widths and Genesis 12 source disclosures.

Current-source `npm test` passed all 17 frontend test files. Earlier branch
validation remains recorded in the ED-5 PR history: framework validation, CKL
integrity, NE-9C compatibility, and NE-10 bridge checks passed. This work did
not change CKL or reviewed curation inputs, so those data gates were not rerun.
Do not merge or deploy as part of this closure.
