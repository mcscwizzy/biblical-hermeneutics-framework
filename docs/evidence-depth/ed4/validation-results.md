# ED-4 validation results

## Strict and heuristic inventory checks

| Check | Result |
|---|---|
| Framework modules | `.venv/bin/python tools/validate.py framework/` — 94 modules valid. |
| CKL strict validator | 687 valid objects, 0 errors, 14 warnings. The warnings are unchanged `incomplete_section_status` records. |
| CKL deep report | 1,408 typed evidence items; 63 heuristic error-severity findings; 1,093 heuristic warnings; 102 source-support-target signals; 0 unresolved source references; 0 Scripture-reference errors. |
| Full chapter census | Pass: 1,189 chapter rows; 687 objects; 19 deterministic retrieval/projection sample checks; 16 live service builds; no unresolved anchors. Report generated under `/tmp/ed4-census`. |
| Current NE-9C/NE-10 compatibility | Pass, read-only. Checks current registries, protected hashes, 3,925 reviewed relationship identities, 44 verified bridges, and 7 held candidates. The historical CKL fingerprint intentionally differs. |

The 63 deep-report error-severity items and 1,093 warnings are heuristic
quality signals, not strict validation errors. The 102 source-support-target
signals remain classified as 45 cross-object claim identities, 14 existing
top-level fields, 24 generic field/category labels, and 19 unresolved
semantic targets. The report was not weakened or filtered. The unresolved 19
are documented for human research in
[source integrity results](source-integrity-results.md).

## Focused Python, API, and governance suites

| Suite | Result |
|---|---|
| ED-4 review workbench, source locks, CKL quality, typed evidence targets, Scripture reference integrity, manifest, release | 109 passed, 19 subtests passed (130.32 seconds). |
| Retrieval regressions, precision, tokenizer/indexing, and CKL retrieval service | 51 passed, 18 subtests passed (239.77 seconds). |
| Narrative Explorer API, projection, passage, curation, held candidate, current compatibility, and ED-2 projection | 580 passed (327.92 seconds). |
| Workflow release-focused Python group | 50 passed (96.17 seconds). |
| Reader and evidence API regression additions | Included in the 580-test suite; Obadiah anchor and reader observation/interpretation tests pass. |

The broad retrieval run first exposed that removing an accidental `Judges`
match from “judging” made the 1 Corinthians result lose an unrelated book
category bonus. This was corrected by including only individually
Scripture-anchored interpretive-note text in the existing coherent-match
signal; rationales, caveats, and unanchored notes remain excluded. The full
retrieval suite passed after the correction. The two ED-3 inherited ranking
failures were also rerun and pass.

## Frontend and browser

- `npm test`: 17 passed, 0 failed.
- Selenium/headless Chromium acceptance: 7 selected desktop/mobile journeys
  passed, including 1440px desktop and actual 390 CSS-pixel device emulation.
- The selected browser cases covered overview navigation, 1 Corinthians
  additional sourced evidence, Genesis 12 draft labels and provenance,
  bibliography locators at 320px/390px, reader search, and back/forward
  history. No overflow, duplicate display, or passage-scope defect was
  reproduced. See [reader acceptance](reader-acceptance.md).

## Release and packaging

- Both committed module profiles regenerated without a diff.
- `python -m build --no-isolation` produced a wheel and sdist. Existing
  setuptools license deprecation notices and the optional missing Commentary
  SQLite glob warning remain.
- Artifact checks passed: 1,052 wheel entries, 1,243 sdist entries, all
  required runtime files present, and no retired generated Commentary payload.
- Installed-wheel smoke passed from `/tmp/ed4-wheel-site`: FastAPI app import,
  Commentary CLI help, `ckl-version --json`, and the packaged 687-object CKL
  inventory resolved from the installed wheel.

## Full test suite

The repository-wide run was bounded to 25 minutes:

```bash
timeout --signal=INT --kill-after=20s 1500s .venv/bin/python -m pytest -q
```

It exited with timeout status 124 after 25:00.78, with 55 tests and 934
subtests passed and no failures reported. Pytest was interrupted while entering
the slower SQLite setup at `framework/canonical_library/scripture.py:327` for
the next collected test,
`tests/canonical_library/test_2_john_record.py::SecondJohnRecordTests::test_sqlite_preserves_claims_and_governance_fields` (test 56). This is an
incomplete full-suite run, not a full-suite pass. The focused retrieval,
Narrative Explorer, CKL/governance, browser, package, and release checks listed
above completed separately. ED-3 had reproduced two inherited retrieval
failures on the fetched baseline; both now pass, as does the formerly weak
unprefixed heart-condemnation query. No new regression was reported by the
completed focused gates. The separate focused suites above have completed.
