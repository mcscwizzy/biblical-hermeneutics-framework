# ED-5 validation results

This log separates strict errors, inherited warnings, heuristic signals,
scholarly review gaps, and checks that were unavailable or not completed.

## Baseline and targeted results

| Check | Result |
|---|---|
| Branch/base and worktree | Feature branch from fetched ED-4 merge; initial worktree clean. |
| CKL inventory and chapter census | Pass: 687 objects, 2,329 claims, 1,408 typed evidence items, 2,897 source identities; 1,189 chapters with 1,090 specific, 56 contextual, 2 entity-only, 41 no-eligible, 0 unknown. Inventory fingerprint matches baseline. 19 deterministic samples and 16 service builds passed. |
| Framework validator | `.venv/bin/python tools/validate.py framework/` — 94 modules valid. |
| CKL strict validator | 687 valid objects, 0 strict errors, 14 inherited incomplete-section warnings. |
| Current NE-9C/NE-10 compatibility | Pass, read-only: 3,925 reviewed identities, 433 accepted identities, 44 bridges, 7 held candidates. All protected hashes match. Historical CKL fingerprint mismatch is expected and informational. |
| CKL source locks, manifest, Scripture-reference integrity, release group | 64 passed, 13 subtests passed. |
| Narrative Explorer API/projection and retrieval regressions | 13 passed, including exact selected scopes, unavailable-vs-empty state, held relationship exclusion, and unprefixed 1 John retrieval. |
| ED-4 workbench and ED-5 portability/journey tests | 16 passed, 6 subtests passed; includes mode-0600 snapshots, no-overwrite, explicit suffix restore, malformed/truncated rejection, queue reconciliation, and all 12 reader cases. |
| ED-5 identity-strengthened journey test | `tests/test_ed5_reader_evaluation.py` — 1 passed; all 12 journeys pass, including unique exact IDs for 10 projected records. |
| Standalone reader evaluation | `scripts/ed5_reader_evaluation.py --output /tmp/ed5-reader-evaluation.json` — 12 passed, 0 failed; every pinned projected ID matched exactly once. |
| ED-4 retrieval ranking regressions | `tests/canonical_library/test_ed4_retrieval_regressions.py` — 8 passed, 14 subtests passed. |
| Frontend suite | `npm test`: 17 test files passed, 0 failed. |
| Framework profile freshness | `minimal-7b`, `standard`, and `scholar` regenerated in memory with no differences. |
| Wheel and source distribution | `python -m build --no-isolation --wheel --sdist --outdir /tmp/ed5-package` passed. Existing license deprecation notices and absent optional Commentary SQLite glob warning remain. |
| Installed-wheel smoke | Isolated `--target /tmp/ed5-wheel-site` import resolved `bhf_web.app` from the installed wheel and loaded 687 packaged CKL objects. |
| ED-5 Markdown links and diff whitespace | All local Markdown links resolve; `git diff --check` passes. |

## Browser and packaging gates

The ED-5 browser gate is **BLOCKED / UNVERIFIED at narrow widths**. The
repository's existing Selenium Firefox harness was used with Mozilla Firefox
159.0 and geckodriver 0.37.1 against branch
`feat/ed5-discovery-experience` at `5a954bda`. The browser's effective CSS
viewport was measured directly:

| Requested browser size | Effective CSS viewport width | Result |
|---|---:|---|
| 1440 x 1200 | 1440 px | Browser acceptance completed at desktop width. |
| 390 x 844 | 500 px | Firefox clamps the requested window to 500 px; responsive acceptance at 390 px was not run. |
| 320 x 740 | 500 px | Firefox clamps the requested window to 500 px; responsive acceptance at 320 px was not run. |

At 1440 px, the completed-empty notice appeared for 1 Kings 2, and the native
collapsed research-term disclosure contained exactly 14 definitions. Keyboard
Tab focus was visible; Enter and Space toggled the disclosure. The summary
touch target measured 44 px high and the notice CTA measured 67.9 px high. The
long notice and all guide terms wrapped without horizontal overflow. Light
theme contrast measured 6.13:1 for notice text, 9.93:1 for the guide summary,
and 6.37:1 for a term definition. Dark theme contrast measured 7.56:1, 7.45:1,
and 7.45:1 for those same elements.

Browser checks also passed for the completed-empty notice being absent when a
synthetic intercepted CKL lookup reported `failed` and `partial`; Genesis 12
source disclosure with both expected source identities; 1 Corinthians 11:3
additional lexical evidence with its disputed status and both expected
sources; and verified Jonah/Matthew navigation from both endpoints with
return-to-origin. The synthetic snapshot export/no-overwrite and valid
append-only restore checks passed (2 tests); no real review decisions were
written. No release-blocking UI defect was reproduced.

The GitHub Actions GUI run for this commit (run 43218071067) failed before
browser tests started because the `bhf-web` Compose dependency exited with
status 1; no browser artifacts were produced. An authorized job rerun was
rejected by the GitHub connector with HTTP 403 (`Resource not accessible by
integration`). A READY Vercel preview existed for the same commit, but no
browser session was available to inspect it. Inherited ED-4 browser checks
are reported separately in [usability baseline](usability-baseline.md).
Keyboard disclosure behavior, desktop contrast, and desktop touch-size checks
are verified here; narrow responsive behavior at 390 px and 320 px remains
unverified.

The bounded full repository command
`timeout --signal=INT --kill-after=20s 1500s .venv/bin/python -m pytest -q`
reached its 25-minute limit and exited 124. Pytest reported 54 passed and 907
subtests passed in 1500.13 seconds before the interrupt; the repository suite
did not complete, so this is an incomplete run, not a full-suite pass. No test
failure was reported before interruption. The targeted suites above passed.

## Governance and review limits

No source lock, CKL object, curated relationship, verified bridge, or held
candidate was changed. The frozen historical NE-9C validator/checkpoint was
not edited. Synthetic review events live only in temporary test directories.
The actual review queue remains 99 pending; no real event or human decision
was created. The new snapshot hash chain reports internal integrity only;
authenticity still requires a separately retained trusted digest and human
reviewer identity validation.
