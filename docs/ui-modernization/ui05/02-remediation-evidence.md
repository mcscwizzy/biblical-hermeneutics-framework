# BHF UI-05 — Remediation Evidence

## Application corrections

| Area | Correction | Evidence |
|---|---|---|
| Word Study | `DeterministicStudyEngine` no longer loads unrelated CKL passage objects for the lexical-only `word_study` action. Complete or ambiguous lexical SQLite evidence still informs the existing confidence score, while `metadata.object_ids` remains empty when no CKL records were retrieved. | Regression unit test supplies a CKL spy that raises on retrieval, uses the lexical SQLite fixture, and checks the result, confidence, Strong's number, and empty CKL object list. Five Word Study unit cases passed after this change. The slow-loading browser case also passed in its isolated rerun and in the study-companion neighboring group. |
| Maps | Each `openMapPanel` call receives an increasing request ID. A response from an older open cannot apply catalog options, marker/route data, or an error after a newer open has started. | The updated browser regression delays both John 1:4 map responses, opens John 1:5 and verifies its detail, then releases the older responses and verifies John 1:5 remains displayed. The maps neighboring group passed 6 cases. |

## Browser helper and fixture corrections

- `BasePage.click` now scrolls by selector and obtains the clickable WebElement after scrolling, avoiding use of a handle invalidated by rerender.
- The canonical editor browser case uses a private synthetic one-record CKL and isolated study database. This retains the draft navigation/edit/save contract while avoiding a full-library cache reload that exceeded the browser renderer timeout. The fixture restores settings, environment, and CKL caches and removes its temporary data after use.
- Canonical result-view clicks use a single DOM operation to choose the visible enabled button and click it, avoiding a second stale-handle window during the result-list rerender.
- The Ask BHF browser case now covers the current passage-aware external handoff modal on mobile. Clipboard and `window.open` are stubbed in the browser; the test checks the prepared text and destination without sending a question to an external service.
- The native resource race case now drives the current Maps endpoints and delays responses deterministically. It previously covered an obsolete Companion endpoint and could not detect the real stale-map-response defect.
- The context result layout test now opens the real deterministic Word Study output in `#lexicon-panel` and measures its `.answer-header`, rather than constructing retired Ask answer markup.

## Test-only contract updates

- Mobile translation badge and translation import assertions now follow the configured active translation (KJV) instead of assuming ASV.
- Verse selection assertions read the shared selection state and check the complete selected verse and text.
- Mobile Ask, workspace Ask, and desktop navigation assertions now verify the current modal handoff and selected passage, while retaining the surrounding notes/highlights/saved/explore and reader-split assertions.
- The archaeology source-inspection test now checks the current click dispatch with its focus target rather than requiring the older function signature without that optional argument. Endpoint, handler export, and detail-rendering assertions remain.

## Isolated GUI reruns

Each of the ten requested GUI node IDs passed in a separate pytest invocation with a fresh app fixture and browser: **10 passed / 10 cases**. These are diagnostic reruns and are not the full GUI acceptance result. The independent neighbor groups also passed: canonical detail/source plus editor (2); mobile Ask and verse selection (3); reader/import (2); map cases (6); workspace panel/navigation (2); Narrative Explorer reader, feature gate, responsive actions, and real CKL handoff (5). The Tyndale browser integration against the provisioned notes DB passed (1).

## Remaining verification record

The requested Python/API, Tyndale, Narrative Explorer, packaging, and retired-route test batch passed: **232 passed, 55 skipped, 4 subtests passed**. The frontend suite passed **16/16**; framework validation accepted **94 modules**; CKL source validation had **0 errors** (14 existing warnings). The definitive clean full GUI output, tested commit, and final decision are recorded in [the full GUI rerun](03-full-gui-rerun.md) and [release decision](05-release-decision.md). No isolated result is used as a substitute for the full GUI gate.
