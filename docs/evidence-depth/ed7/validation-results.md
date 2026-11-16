# ED-7 Validation Results

## Completed checks

| Area | Result |
|---|---|
| ED-3 review queue coverage and audit integrity | 99/99 stable CKL IDs reconciled; two distinct recorded analytical passes per item; existing packet SHA-256 values verified by `tests/test_ed7_source_audit.py`. |
| Frontend presentation policy | Deterministic eligibility, featured wording, plain source disclosures, uncertainty, withheld handling, deduplication, and exact passage display covered by focused Node tests. Final rerun result is recorded below. |
| Genuine Chromium acceptance | Real Chromium on desktop and 390px/320px for Genesis 6, Psalm 82, and 1 Kings 2; featured source disclosures; Jonah 1:17→Matthew 12:40 direction and navigation. See recorded final result below. |
| Connectivity smoke gate | The existing gate passed for current and baseline app containers using Selenium Chrome; local Selenium compatibility fallback is retained. |
| CKL strict validation and protected relationships | Final commands/results are recorded below. No CKL or protected relationship files were changed. |
| Documentation/artifacts | JSON parse, report links, screenshot presence, whitespace, full diff, and final worktree/commit state checked before PR. |

## Commands and actual results

- `.venv/bin/python -m pytest -q tests/test_ed7_source_audit.py
  tests/test_narrative_explorer_api.py tests/test_narrative_explorer_ui_config.py
  tests/test_vercel_packaging.py tests/canonical_library/test_ckl_retrieval_service.py
  tests/canonical_library/test_source_locks.py tests/canonical_library/test_manifest.py
  tests/canonical_library/test_scripture_reference_integrity.py` — **119 passed,
  13 subtests passed** in 237.34 seconds.
- `npm test` — **18 frontend test files passed, 0 failed**. This includes the
  full Narrative Explorer, presentation policy, cache, companion locations,
  and service-worker coverage.
- `BHF_WEBDRIVER_URL=http://localhost:4444/wd/hub
  BHF_GUI_BROWSER_HOST=172.17.0.1 .venv/bin/python -m pytest -q
  tests/gui/ne11d1/test_connectivity_smoke.py` — **3 passed** in 5.48 seconds.
- `.venv/bin/python -m pytest -q tests/gui/ne11d1/test_ed7_reader_first_acceptance.py
  tests/gui/ne11d1/test_ed5_mobile_acceptance.py::test_ed5_empty_notice_and_terminology_guide_acceptance`
  — **6 passed** in 184.03 seconds on genuine Chromium. Covered two expanded
  “How we know” disclosures, Jonah→Matthew connection and destination,
  1 Kings 2 desktop/390px/320px, and desktop/390px/320px empty-page terminology
  acceptance.
- `.venv/bin/python -m pytest -q tests/gui/ne11d1/test_ed6_reader_pilot_readiness.py`
  — **3 passed** in 82.14 seconds on genuine Chromium. The existing pilot
  readiness assertions now check source titles and uncertainty without
  exposing editorial states; the dynamic result click uses the same fresh-DOM
  pattern as the existing Canonical Browser UI test.
- After simplifying the on-demand relationship wording, a final Chromium
  recheck of the Jonah route plus the Psalm 82 and Deuteronomy 32 ED-6 tasks
  passed **3/3** in 87.71 seconds. Updated route and destination captures are
  in `screenshots/after/`.
- `.venv/bin/python tools/ckl_validate.py --root framework/canonical_library`
  — **687 valid objects, 0 errors, 14 inherited warnings**. The warnings are
  the existing incomplete section-status annotations in four CKL objects;
  no CKL file was modified.
- `.venv/bin/python tools/validate_ne9c_current_compatibility.py` — **passed**
  read-only current-state compatibility. It reported 3,925 reviewed
  relationship identities, 433 runtime curation records, 44 verified
  bridges, 7 held candidates, and unchanged protected registry hashes. The
  known historical CKL fingerprint mismatch remains unchanged.
- `.venv/bin/python tools/validate.py framework/` — **94 modules valid**.

The first attempt to run the modified ED-6 browser check exposed a Selenium
callback argument-order error in the test and a stale-element race in its
Canonical Browser click. Both were traced to test code (not application
behavior), corrected, and the final full ED-6 check passed 3/3. The final ED-7
Chromium run used the working connectivity smoke gate above.

Before commit, JSON parsing, 75 local Markdown links, `git diff --check`, and
protected-path status are checked once more; the results and final commit/PR
state are added before completion.

## Interpretation limits

Chromium assertions establish the specific rendered text, navigation, and
viewport geometry exercised by the tests. They do not demonstrate participant
comprehension, scholarly approval, or universal browser/device behavior. No
CKL scholarly correction was made, so no source-integrity or CKL approval claim
is inferred from the presentation tests.
