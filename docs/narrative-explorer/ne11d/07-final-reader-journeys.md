# NE-11D2 reader journey evidence

Baseline: fetched `origin/master` at `1283ffc5cde83bcec26bc4e20596eb87e574bc9c`; the required NE-11D1 commit is that same commit. The starting worktree was clean. The browser harness copies the repository CKL to a temporary root, enables `BHF_NARRATIVE_EXPLORER_ENABLED=1`, and uses a temporary study database. It seeds KJV offline data in IndexedDB; it does not mock the Companion or projection responses. Headless Chrome and ChromeDriver 156.0.8078.47 were available. `pytest tests/gui/ne11d1 -q -s` ran the existing four tests before additional coverage was added: **4 passed**.

| Journey | Observed in existing real-data browser tests |
|---|---|
| Jonah 1:17 → Matthew 12:40 → return | Pass: fish card cites `jonah#claim:jonah-three-days`; exact identity, route, later reception, historical direction, sources and uncertainty asserted; return restores verse 17. Three Companion and three projection requests. |
| Matthew 12:40 → Jonah 1:17 → return | Pass after reloading the app in the same browser; direction and original selection asserted. Three Companion and three projection requests. A fresh browser session is a separate test. |
| Genesis 1:1–5 → John 1:1–5 → return | Pass: `john#claim:john-logos`, `genesis-1-john-1-creation-word`, interpretive association and no proof of direct borrowing asserted. Seven Companion and three projection requests. |
| Psalm 22:1 | No projected route or Companion action; generic cross-reference navigation was not exercised. Two Companion and one projection request. |
| Deuteronomy 32:8–9 | No projected route or Companion action for the held candidate. Three Companion and one projection request. |

These tests assert trail state and selection, not browser Back or keyboard focus. They do not establish Acts 2/Psalm 110 navigation, a no-evidence chapter, or a verified route without matching discovery. The fish card order and ranking were not independently measured in this run; the correction report documents the earlier comparison. Do not infer those untested cases from the positive results.

A separate `test_fresh_matthew_handoff` starts with a new WebDriver session and independently passed Matthew → Jonah → return, preserving the Jonah → Matthew direction. The additional test file also contains the limited mobile viewport measurement; see [mobile and recovery](08-mobile-accessibility-and-recovery.md).
