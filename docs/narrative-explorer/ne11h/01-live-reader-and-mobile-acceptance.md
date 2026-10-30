# NE-11H — Live Reader and Mobile Acceptance

## Result and scope

The designated Vercel Preview was independently checked and is tree-equivalent
to merged master, but the graphical browser was redirected to Vercel Login by
the project's SSO protection. The live Preview journeys and responsive checks
were therefore **NOT EXECUTED**. The local Chromium results below are useful
regression evidence and are not represented as live Preview results.

No production deployment, Preview deployment, alias, project setting, or CKL
record was changed.

## Source and deployment identity

| Item | Verified value |
|---|---|
| Repository baseline | `origin/master` `79fd53a0d40fdb0e66b945e04b3494b3ef9e1b97` |
| Baseline Git tree | `32fa0ea8ccc893e8237f6f90e37a8e2534cbd592` |
| Existing Preview | `dpl_NvpSAm8Uc6edx98ABP6Lf4asvYgk` |
| Preview URL | `https://biblical-hermeneutics-framework-j2joaza64-mcscwizzys-projects.vercel.app` |
| Preview state and project | Ready, Preview, `prj_15SaSVJykrPDrncFg6jehwGzr3j9` |
| Preview source | `294763d66135f59560fcf4069ea7f2cf36bf79d2` |
| Preview Git tree | `32fa0ea8ccc893e8237f6f90e37a8e2534cbd592` |

The Preview is **tree-equivalent to merged master**, not an exact-commit master
deployment. The URL opened in Selenium reached Vercel's login page instead of
the application. No authenticated browser session or short-lived Trusted
Sources credential was available to the test harness. Deployment protection
was not bypassed or changed.

## Local browser environment

The local suite used Selenium 4.46.0 with headless Chromium 155.0.8059.79 on a
Linux Selenium container; the host reports Linux kernel
`7.0.0-31-generic`. The Python test runner was 3.12.3. Each GUI test server
used a temporary database and a temporary copy of the checked-out CKL. The
Selenium browser profile and test data were disposable. Screenshots and any
browser artifacts are under `/tmp/ne11h-browser-artifacts`, outside Git. The
local browser connected over the host-local test network; these measurements
do not represent internet or Preview network conditions.

## Reader journeys — local Chromium

All results in this table are local-browser observations against the current
checkout.

| Journey | Observed result |
|---|---|
| Genesis 1:1–5 → John 1:1–5 | The Companion selected `ckl:john#claim:john-logos`; “Explore this connection” opened route `genesis-1-john-1-creation-word`. The displayed relationship was `interpretive_association`; expanded route detail explicitly said it was not proof of direct borrowing. Related passage selection reached John 1:1–5, and the in-app return restored Genesis 1:1–5 and verses 1–5. |
| Jonah 1:17 → Matthew 12:40 | The eligible discovery used object `jonah`, claim `jonah-three-days`, with source IDs `jonah-masoretic` and `jonah-new-testament` (the fresh Matthew-first journey also exposed bibliography source `graybill-kaltner-mckenzie-jonah`). Route `jonah-1-17-matthew-12-40-sign-of-jonah` displayed `later_canonical_reception` and the historical direction Jonah 1:17 → Matthew 12:40. Its details exposed the claim and source IDs, chronology and idiom qualifications, and “heart of the earth.” The route retained the MT/LXX Jonah 2:1 numbering note. Selecting Matthew 12:40 and returning restored Jonah 1:17. |
| Fresh Matthew 12:40 → Jonah 1:17 | A separate test browser started at Matthew without visiting Jonah first. It found the same Jonah claim and source IDs, retained the classification and Jonah → Matthew direction, navigated to Jonah 1:17, and returned to Matthew 12:40. |
| Acts 2:34–35 → Psalm 110 | The existing authored pathway opened Psalm 110 through Narrative Explorer. Expanded details identified an authored CKL relationship and showed `ckl:messiah-theme#source:luke-24`, `ckl:messiah-theme#source:psalm-110`, and `ckl:resurrection-theme#source:1-corinthians-15`. Browser Back restored Acts 2:34–35, Forward restored Psalm 110, and the in-app return restored the Acts selection. Held candidate `psalm-110-acts-2-enthronement` remained held and was not emitted as a verified bridge. |

The local negative controls passed:

- Psalm 22:1 produced no approved Psalm 22 / Mark 15 route or Companion action.
- Deuteronomy 32:8–9 produced no Deuteronomy 32 / Psalm 82 / Job 1 route or
  Companion action.
- A controlled empty projection displayed the safe empty state, no route
  cards, and no enabled “inspect” actions. Refresh removed only the test
  interception; the normal projection and Jonah route then recovered.
- The delayed Jonah route projection was held after an HTTP 200 response. A
  chapter change to Jonah 2 aborted the pending activation; releasing the
  response did not create a stale route or trail.

The tested Genesis and Jonah routes used their exact CKL record identities;
the held candidate was not promoted. These local outcomes do not establish
the live Preview result.

## Responsive layout — local Chromium

The action-row suite measured `clientWidth/scrollWidth`; the passage suite
measured rendered element bounds, text overflow, and document
`clientWidth/scrollWidth`. No tested document, action row, overview, discovery
card, or related-passage card had horizontal overflow or clipped text.

### Companion actions

| CSS viewport | Document client/scroll | Overview client/scroll | Action row client/scroll | Observed button x-bounds (px) |
|---:|---:|---:|---:|---|
| 320 | 320 / 320 | 318 / 318 | 290 / 290 | Add Note 15–156; Save Passage 164–305; Narrative Explorer 15–156; Compare Translations 164–305 |
| 390 | 390 / 390 | 388 / 388 | 360 / 360 | Add Note 15–191; Save Passage 199–375; Narrative Explorer 15–191; Compare Translations 199–375 |
| 768 | 753 / 753 in the action test | 736 / 736 | 708 / 708 | Add Note 15–186; Save Passage 194–365; Narrative Explorer 373–544; Compare Translations 552–723 |
| 1440 | 1425 / 1425 | 874 / 874 | 830 / 830 | Add Note 660.2–783.1; Save Passage 791.1–952.9; Narrative Explorer 960.9–1160.6; Compare Translations 1168.6–1371 |

Measured button heights were 64 px at 320 px, at least 44 px at 390 px, 64 px
at 768 px, and 43 px at 1440 px. The test enforces a 44 px minimum through
680 px and 38 px above that breakpoint. Text remained inside each button.
At 768 px the passage-layout run also measured document client/scroll as
768/768; the action-row run measured 753/753 while the vertical document
scrollbar was present. Both observations had no horizontal overflow.

The expanded Jonah discovery and related-passage cards also passed a text
clipping scan:

| CSS viewport | Discovery bounds (left–right, width; client/scroll) | Related passage bounds (left–right, width; client/scroll) | Document client/scroll |
|---:|---|---|---|
| 320 | 15–305, 290; 288/288 | 31–289, 258; 254/254 | 320/320 |
| 390 | 15–375, 360; 358/358 | 31–359, 328; 324/324 | 390/390 |
| 768 | 15–723, 708; 706/706 | 31–371.5, 340.5; 337/337 | 768/768 |
| 1440 | 540.6–1371, 830.4; 828/828 | 556.6–950.8, 394.2; 390/390 | 1425/1425 |

The 320 px mobile test exercised Add Note and Save Passage in the disposable
profile. Compare Translations and Narrative Explorer opened and returned with
the selected Jonah 1:17 intact. The focused mobile Maps workspace test passed.
Governance disclosure at 320 px and 390 px is recorded in report 02.

## Keyboard and browser history — local Chromium

The four-width route keyboard test passed at 320, 390, 768, and 1440 px. It
used Tab to reach the discovery disclosure and action; Shift+Tab moved to a
prior focusable control and Tab returned to “Explore this connection.” Space
expanded “Dig In”; Enter activated the route. The route heading received
focus, the polite status text named Jonah 1:17, and Escape closed the route
and restored focus to the discovery action. Selected Scripture remained
Jonah 1:17.

The Maps history test passed the NE-11E5 sequence: Maps → browser Back →
Companion `study` overview → browser Back → `peek`; Forward restored `study`
and then Maps while preserving the selected Scripture. A separate delayed
Map-catalog test also used Back during “Loading map data...”; Back restored
the study overview, and releasing the delayed response did not overwrite it.
The Acts 2 / Psalm 110 journey independently passed browser Back and Forward.

Automated keyboard results are not spoken screen-reader acceptance. The live
Preview keyboard result remains **NOT EXECUTED**.

## Commands and results

All Selenium commands used the following exact prefix with the local
temporary app server, followed by the target and options in the table:

```sh
BHF_WEBDRIVER_URL=http://127.0.0.1:4444/wd/hub BHF_GUI_ARTIFACTS_DIR=/tmp/ne11h-browser-artifacts .venv/bin/python -m pytest
```

| Exact command target (after the common prefix) | Result |
|---|---|
| `tests/gui/ne11d1/test_real_ckl_handoff.py tests/gui/ne11d1/test_ne11d3_journeys.py -q` | 7 passed; added Acts source-disclosure assertion rerun separately with `tests/gui/ne11d1/test_ne11d3_journeys.py::test_acts_authored_psalm_route_and_return -q`: 1 passed |
| `tests/gui/ne11h -s -q` | 8 passed; includes the independent Matthew-first journey, five governance cases, failed Companion retry, and Back during delayed Map catalog loading |
| `tests/gui/ne11d1/test_ne11d3_mobile.py -s -q` | 4 passed at 320, 390, 768, 1440 px |
| `tests/gui/ne11d1/test_ne11d5_responsive_actions.py -s -q` | 2 passed at 320, 390, 768, 1440 px, with Narrative Explorer enabled and disabled |
| `tests/gui/ne11d1/test_ne11d3_keyboard.py -q` | 4 passed at all four widths, including the added Shift+Tab assertion |
| `tests/gui/ne11g/test_governance_disclosure_mobile.py -q` | 2 passed at 320 and 390 px |
| `tests/gui/test_study_companion.py::test_mobile_maps_explorer_opens_visible_map_workspace -s -q` | 1 passed |
| `tests/gui/test_study_companion.py::test_browser_back_unwinds_resource_then_companion_overview tests/gui/test_study_companion.py::test_stale_context_response_cannot_replace_newer_selection tests/gui/ne11d1/test_ne11d3_offline.py::test_offline_failure_cached_reading_and_recovery tests/gui/ne11d1/test_ne11d4_feature_gate.py::test_controlled_empty_projection_has_no_actions_and_recovers -q` | 4 passed |

The new reusable test assertions are limited to browser acceptance. No product
feature code was changed.
