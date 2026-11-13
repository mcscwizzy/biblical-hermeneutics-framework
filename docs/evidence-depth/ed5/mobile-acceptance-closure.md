# ED-5 Mobile Acceptance Closure

## Status

**BLOCKED — the shared browser-connectivity failure is fixed, and all ED-5 cases
pass locally after a viewport correction. The latest Actions runs still need to
verify that correction in Chrome 157, and the bounded broader GUI regression
stops on three journey tests.**

## Scope and protections

- Work remains on `fix/ed5-mobile-acceptance`, based on ED-5 PR #80's merge into
  `master` at `6e33d16e891614f6527fd9ede943cb1a7c5c1913`.
- No CKL records, source identities, held relationships, review states, or
  review decisions were changed.
- The connectivity commit did not edit `vercel.json`. The branch comparison
  includes its existing `fix/ed5-mobile-acceptance: false` deployment guard;
  keep that guard in the PR because removing it could enable branch deployments.
  The base file has `master: false`. No deployment was requested or triggered.

## Actions investigation and root cause

The earlier startup failure was separate and remains fixed: run `43218071067`
did not retain diagnostics, and `43350244152` showed Compose creating the absent
`.bhf` mount as `root:root` mode `0755`. The UID/GID 1000 web process could not
seed `.lexicon.sqlite`. The Actions workflow now prepares `.bhf` as UID/GID 1000
before Compose; the two runs below reached healthy app and Selenium services.

Completed GUI runs `43350876711` and `43359040540` both reached healthy
`bhf-web` and Selenium Chrome containers, then failed with **2 passed and 156
setup errors**. The first browser setup error was `net::ERR_CONNECTION_REFUSED`
while `_seed_browser_offline_fixture()` navigated to `/offline`; later Selenium
session-creation timeouts followed.

The setup error was caused by `tests/gui/ne11d1/conftest.py::base_url` (and the
shared GUI app fixture) binding an ephemeral Uvicorn test server to
`127.0.0.1` inside `gui-tests`. Remote Chrome is in a separate container, where
`127.0.0.1` is its own loopback interface. It could not reach the server. The
pytest driver fixture also only called `quit()` after `yield`, so an exception
while seeding `/offline` skipped cleanup and left failed setup sessions behind.
That session leak explains the subsequent slot/session timeouts; it was not the
initial connectivity failure.

The app-service probes established that the shared Compose network works:

| Probe | `gui-tests` | `selenium-chrome` |
| --- | --- | --- |
| `bhf-web` DNS | `172.20.0.2` | `172.20.0.2` |
| TCP `bhf-web:8080` | Connected | Connected |
| `/api/health` | HTTP 200, `status=ok` | HTTP 200, `status=ok` |
| `/offline` | HTTP 200 | HTTP 200 |
| HTTP(S)/ALL proxy variables | Unset | Unset |

The application log reports Uvicorn listening on `0.0.0.0:8080`. One remote
Chrome session was created and navigated to `/api/health` and `/offline`; both
completed with HTTP 200 and `/offline` reached `document.readyState=complete`.
The browser capabilities contained no proxy endpoint. This separates the
working service network/browser from the incorrectly scoped fixture URL.

The test server endpoint helper now keeps `127.0.0.1` for local Chrome and binds
remote-browser fixture servers to `0.0.0.0`, addressing them as
`http://gui-tests:<ephemeral-port>`. A fail-first utility and a Selenium fixture
smoke run before ED-5 or the broad suite. Driver setup now quits a partially
initialized browser on any setup exception. The Actions job starts the app and
Chrome as healthy services, records DNS/TCP/proxy/HTTP probes from the Chrome
container, and captures Selenium logs with failure diagnostics.

## Remote browser and ED-5 results

The connectivity utility was executed inside `gui-tests`; the explicit route
probe was also executed inside `selenium-chrome`. A single remote Chrome session
reported Chrome **155.0.8059.79** and ChromeDriver **155.0.8059.79**, navigated to
the app, and quit cleanly. The dynamic fixture smoke passed against
`http://gui-tests:<ephemeral-port>`.

Actions runs `43501993153` and `43502606551` both passed service startup, the
Selenium-container route probe, the fail-first browser smoke, and the dynamic
fixture smoke. Each used Chrome/ChromeDriver **157.0.8103.38**. The desktop
1440px acceptance case passed, but both runs failed while clicking the Narrative
Explorer entry in the 390px case. Chrome reported intercepted clicks at
`(195, 888)` and `(195, 1221)` while the test had changed CDP metrics to 390×844
but left the headless window at 1440×1400. Those runs used code before the
viewport correction below.

`_set_viewport()` now sets the actual headless window to the requested width and
height before applying CDP device metrics. After that change, the ED-5 file ran
by itself locally and passed: **5 passed in 141.53 seconds** using remote
Chrome/ChromeDriver **155.0.8059.79**. Each case checked the effective
`window.innerWidth` and `document.documentElement.clientWidth` against the
requested width, so browser chrome or device emulation did not silently change
the CSS viewport.

| Requested width | `window.innerWidth` | `clientWidth` | Result |
| ---: | ---: | ---: | --- |
| 1440px | 1440px | 1440px | Pass |
| 390px | 390px | 390px | Pass |
| 320px | 320px | 320px | Pass |

The five cases cover the empty research notice and terminology guide at all
three widths, plus the Genesis 12 exact-record source disclosure at 1440px and
390px. Assertions passed for native disclosure behavior, Enter/Space keyboard
operation, visible focus, reduced motion, 44px minimum targets, 4.5:1 text
contrast, long-definition readability, and horizontal-overflow bounds. Browser
and driver versions were recorded by the tests.

I inspected the generated desktop 1440px and mobile 390px/320px expanded-guide
screenshots, plus the Genesis 12 mobile source disclosure. The layouts fit their
CSS widths, keep the mobile navigation visible, and show the expanded evidence
in the passage panel without horizontal clipping. The local screenshots and
JUnit output are generated evidence and are not committed; the Actions job
uploads its screenshots and separate ED-5/regression JUnit reports.

## Bounded broader regression

After the corrected ED-5 cases passed locally, the non-slow GUI suite ran with a
60-minute command timeout and `--maxfail=3`. It stopped at the configured limit:
**3 failed, 16 passed in 678.82 seconds**. No network refusal or viewport failure
occurred.

The failures are in three journey tests whose current entry selectors are not
present in the reader-first screen captured by Chrome:

1. `test_fresh_matthew_handoff` waits for `_connection_action()` to find the old
   `.companion-discovery-card` / `data-presentation-action` controls.
2. `test_psalm_22_generic_cross_references_do_not_promote_held_bridge` waits for
   the old `[data-companion-resource="cross_references"]` control.
3. `test_real_jonah_verification_interrupted_by_chapter_change` also waits for
   `_connection_action()` and its old companion discovery controls.

The current reader-first UI exposes the passage relationships through Narrative
Explorer. These test failures need review against that current flow while
retaining their CKL identity, held-bridge, cancellation, and destination
assertions. They were not hidden or weakened as part of the connectivity fix.
The broad suite is incomplete; its JUnit summary and failure screenshots were
inspected locally.

## CI gate and next step

The GUI Compose command now orders the standalone route/browser smoke, fixture
connectivity test, ED-5 acceptance file, and then the bounded non-slow regression.
The Actions job has a 110-minute ceiling; the broad run stops after three
failures and has its own JUnit report. This keeps a broken browser connection
from generating a large collection of setup errors.

**Closure remains BLOCKED** pending the Chrome 157 Actions rerun with the
viewport correction and resolution of the three broader GUI journey failures
listed above. The connectivity and ED-5 checks pass locally in real remote
Chrome.

## Other validation carried forward

The following checks were recorded for the ED-5 branch before this connectivity
work and were not rerun because no framework, CKL, or frontend implementation
code changed:

- `npm test`: 17 test files passed.
- Reader/API/projection/curation and diagnostics: 572 passed.
- Release/source-integrity/NE-9C/NE-10 compatibility set: 73 passed, with 13
  subtests passed.
- Framework validation: 94 modules valid.
- CKL strict validation: 687 valid objects, zero errors, and 14 existing
  warnings.
- NE-9C compatibility validation: passed; 3,925 reviewed relationships,
  4,061 inventory rows, 433 curated runtime identities, 44 bridges, and 7 held
  candidates; protected hashes remained stable.
- Current GUI collection: 158 cases, including ED-5 acceptance.
- Connectivity-gate, driver-cleanup, endpoint-selection, and Docker context
  tests for this change: 10 passed in 0.87 seconds.
