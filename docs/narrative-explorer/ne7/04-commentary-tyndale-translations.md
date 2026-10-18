# NE-7.4 — Commentary, Tyndale, translations, and reader state

## Commentary v1.2

The frozen chapter Commentary and reader integration suites passed in the focused compatibility run, and the full web-app suite passed after replacing two stale interface expectations. Commentary remained associated with chapters and available independently of Narrative Explorer. The feature remains disabled by default, so existing Commentary access does not require Explorer. Companion and Explorer are additive; no summary or synthesis release was replaced.

The frozen v1.2 data, enrichment, and CKL-object tree fingerprints remain the established values `5cdae385fe27dbc3e44d8bf330b75ff2b7e627af`, `b01d814aa10554ecd1f547b426d11cb18cc3ab8c`, and `45fb311c694489474702cb2f4b0c8e0f9872d71a`. No Commentary compilation or generation ran. Several older Commentary tests still fail against the current selective-generation/frozen-source contract; they are preserved as baseline failures in `06-performance-and-regressions.md`, not hidden by rewriting prose or snapshots.

## Tyndale Study Notes

Local browser acceptance passed for opening Tyndale notes, passage association, presentation, chapter following, and selected-passage focus. The test used local test fixtures/mock notes. It establishes local UI compatibility only. NE-6R3 identified that a Tyndale SQLite archive is not tracked package data and hosted archive provisioning is unverified. No archive was downloaded and no production provisioning was changed. Hosted Tyndale remains **PENDING**.

## Translations and reading state

Translation catalog, registry, settings, and reader companion tests were included in the compatibility run. Browser translation comparison passed with local KJV/ASV test data; it preserved selected range and compared distinct installed text. User-imported translation fixtures were unavailable for a complete browser import walkthrough. No license condition or distribution package was changed. Reader selection/navigation smoke checks passed, but exhaustive persistence of every note, highlight, preference, and imported-resource combination was outside this acceptance run.

Some GUI translation tests are Chrome-specific (`execute_cdp_cmd`) or require navigation to the offline page; they could not be completed with the installed Firefox-only harness. The translation-focused backend/frontend tests and the supported desktop comparison test passed. These harness-limited cases are recorded as pending coverage, not product passes.

## Compatibility test outcomes

The compatibility test group produced **181 passed, 8 skipped, 15 failed**, with 11 subtests. The failures are pre-existing rights/frozen-corpus/fixture expectation mismatches; investigation and exact test names are in `06-performance-and-regressions.md`. The complete `tests/test_web_app.py` suite passed **80**, skipped **55**, and completed **4 subtests** after two test assertions were updated to match the current reader and Ask BHF handoff. No external AI provider request was made.

No Commentary, Tyndale source, CKL, translation source, or protected study data was modified. The test-only maintenance changes remove expectations for retired `runBibleSearchFallback` and `/ask/jobs`, and assert the current `submitBibleSearch` and selection-aware manual Ask BHF handoff.
