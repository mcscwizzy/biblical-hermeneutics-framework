# Narrative Explorer reader acceptance

## Scope and outcome

The reader disclosure architecture was inspected in `bhf_web/static/narrative-explorer.js` and its existing frontend contract tests. Draft evidence previews display **“Draft evidence — awaiting human review.”** before the collapsed source disclosure is opened. The detail view retains review state, confidence, certainty, dispute status, human-review requirement, original Scripture anchors, source IDs, and bibliographic metadata. A separate frontend test confirms published evidence receives no draft preview label.

No UI changes were needed. The available desktop and responsive browser checks passed at their reported widths. The prior Firefox request for 390 CSS pixels still produced a 500 CSS-pixel viewport, so that Firefox result is recorded as a 500px run, not a 390px pass. Cached Chromium was used for the genuine 390 CSS-pixel layout check.

## Browser and viewport report

- **Browser:** Chrome for Testing 151.0.7922.77, headless Chromium, with matching ChromeDriver.
- **Method:** Chromium DevTools Protocol device metrics emulation, `width=390`, `height=844`, `deviceScaleFactor=1`, `mobile=true`.
- **Verified page values:** `window.innerWidth=390`, `screen.width=390`, DPR 1. The Chromium smoke check also reported `visualViewport.width=390`.
- **Live reader samples:** all six sample passages reported `innerWidth=390`, `screen.width=390`, DPR 1, and `document.documentElement.scrollWidth=390` while preview details were visible.
- **Expanded disputed-text sample:** Mark 7:3 kept document width at 390 after opening the source disclosure; browser focus remained on the `<summary>` control, and the card text computed to 16px.
- **Firefox comparison:** the repository Firefox browser journey passed its existing interaction and overflow assertions, but its measured effective width was 500px after a 390px request. It is not counted as a 390px test.

This verifies a 390 CSS-pixel Chromium layout through browser device emulation. It is not a test on a physical handset.

## Representative live reader samples

Each live sample selected the anchor verse in the Scripture reader, requested the passage projection, and rendered the matching card from its section. The response contained exactly one record matching the stable ED-2 evidence ID; one visible card was present. The card showed the draft/human-review notice while source details remained collapsed. Keyboard activation opened the native disclosure and exposed the record's source IDs. No page-level horizontal overflow was observed at the reported 390px viewport.

| Wave | Passage and record | Reader check |
|---|---|---|
| ED-2 A | Psalm 20:1 — Papyrus Amherst 63 comparison | Exact item projected and rendered once; draft notice and keyboard source disclosure passed. |
| ED-2 B | Proverbs 15:25 — MT / Old Greek comparison anchored through 16:9 | Exact item projected and rendered once; draft notice and keyboard source disclosure passed. |
| ED-2 C | 2 Chronicles 25:1 — Amaziah / Kings comparison; cited article access is abstract-limited | Exact item projected and rendered once; draft notice and keyboard source disclosure passed. |
| ED-2 D | Nahum 3:8 — textual reconstruction | Exact item projected and rendered once; draft notice and keyboard source disclosure passed. |
| ED-2 E | Mark 7:3 — `pugmē` / proposed `pykna` reading | Exact item projected and rendered once; draft notice and keyboard source disclosure passed. |
| ED-1C control | Genesis 6:1 — later reception evidence | Exact item projected and rendered once; draft notice and keyboard source disclosure passed. |

For Mark 7:3, the browser also confirmed the visible **“Textual variant · wording and implications remain debated”** qualification. With the source details expanded, the three listed source locators (`Mark 1-16 in SBLGNT`; `Mark`; and `65, no. 2, pp. 139–147; abstract and displayed footnote 1 inspected`) appeared in the disclosure. The expanded view remained 390px wide, the summary stayed keyboard-focused, and the 16px card text remained readable.

## Disclosure, provenance, and uncertainty behavior

The review notice is outside the collapsed `<details>` element, so a reader sees draft status before opening provenance. Browser keyboard input opened the native summary control for all six representative records. The source IDs in each live projection were present after expansion. The frontend contract tests additionally exercise bibliographic title, author, publisher, year, locator, source ID, dispute state, and human-review metadata in the evidence detail view.

Textual and interpretive uncertainty remains attributed in the source record. The Mark 7 preview keeps the variant disputed. The renderer's dispute notice says the hypothesis is not settled evidence; the ED-2 records retain their own confidence and dispute metadata. These checks do not establish the historical or textual conclusions as correct.

The frontend regression also verifies that published evidence is not mislabeled as draft. Existing review-state tests and all ED-2 wave tests preserve draft / in-review / human-review-required status. No accepted or published record was edited.

## Commands and results

- `npm test` — **17 frontend test files passed; 17 passed, 0 failed**.
- `.venv/bin/python -m pytest tests/test_web_ui_selenium.py::NarrativeExplorerWebUiTests::test_ne8b_connection_preview_desktop_mobile -q -rs` — **1 passed** in Firefox. Its measured viewport was 500 CSS pixels; not counted as the 390px pass.
- Live Chromium integration — **6 of 6** representative records passed at a verified 390 CSS-pixel viewport, as detailed above.
- Mark 7:3 focused Chromium expansion — visible dispute qualification, locators, focus, 16px text, and no horizontal document overflow after disclosure passed.

## Review boundary

These are reader-rendering and responsive-layout checks. They do not provide human scholarly review or publication approval. All 99 ED-2 additions still require independent human scholarly review. No browser UI regression was identified, so no UI change or new regression test was necessary.
