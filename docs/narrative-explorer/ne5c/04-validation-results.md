# NE-5C validation results

## Baseline and ancestry

- Required NE-A2 commit: `3d406b6256a6064a35e0e567c8a1304bf3cba2e8`.
- Fetched `origin/master`: `a320e0adda1bda0403bdcb2c82cb8b5107d9a4cd`.
- NE-A2 was not an ancestor of the fetched master, so this branch is based
  directly on the exact NE-A2 commit in the isolated worktree
  `/tmp/bhf-ne5c-evidence-trails`.
- The implementation keeps the NE-5B retrieval path and schema `1.0`.

## Pilot evidence

The checked projections preserve the exact child IDs and source fields:

- Genesis 2–3: Eden planting remains geography/context with `interpretive_uncertainty`;
  the detail states that a temple identification is not explicit. Cherubim
  evidence keeps its Genesis 3:24 anchor and later sanctuary sources distinct.
  No sanctuary relation is invented for either child item.
- Genesis 6: `g6-sons-of-god-interpretive-positions` retains
  `major_scholarly_disagreement`; the Second Temple Watchers item is displayed
  separately as later reception. The scoped API test confirms the child stays
  applicable to Genesis 6:1–4 and excludes unrelated book-level cross-reference
  leakage.
- Psalm 82: the assembly-language observation has its own item and its
  `primary_observation` and `scholarly_interpretation` remain separate. The
  Ugaritic comparison has comparative anchors and its caution against deciding
  Psalm 82's referents.
- Deuteronomy 32: the Deuteronomy 32:8 manuscript variant remains a
  manuscript/textual-witness item with disputed status and its Qumran source.
  No territorial conclusion is added.
- Exodus 3: the projection contains Presence Theme and Divine Presence and an
  authored `related-concept` edge. The separate sacred-space gap is not filled
  with a synthetic evidence item.
- Acts 7: the existing Nile record is identified by `openbible-a012705`, with
  its Acts 7:19 `directly_named` anchor and non-displayable geometry. The
  projection test uses the stored source identity and verifies it is not
  marked displayable. The default map lookup in this test environment returned
  `StudyDataError`, so the live local map database could not be exercised.
- Tabernacle and temple: the canonical detail route resolves both exact CKL
  objects and preserves `later-sanctuary-development`. The UI labels this
  endpoint relation as a descriptive association because the endpoint does
  not return the projection's validated relationship category.
- Exile and restoration: the canonical route returns the authored
  `babylonian-exile → return-from-exile` label `partial-restoration-event` and
  the reverse object's distinct `preceding-displacement` label. These remain
  separately authored one-way labels, not an inferred reciprocal edge.

## Test and syntax results

The final verification pass completed with:

- `node --test tests/frontend/*.test.js`: 11 test files passed. The Narrative
  Explorer suite contains 23 focused checks for exact evidence IDs,
  source/bibliography display, safe URLs, certainty and dispute state,
  typed/uncategorized and one-way/reciprocal relationships, resolved target
  identity, trail depth and cycles, pending-request sharing, stale request
  cancellation, offline failures, and passage-selection ownership.
- `PYTHONPATH=/tmp/bhf-ne5c-python-deps pytest -q
  tests/test_narrative_explorer_projection.py
  tests/test_narrative_explorer_map_matching.py tests/test_map_tools.py
  tests/test_narrative_explorer_api.py
  tests/test_narrative_explorer_ui_config.py
  tests/test_web_app.py::WebAppTests::test_canonical_detail_route_resolves_authored_trail_targets_without_relabeling`:
  86 passed and 4 subtests passed in 107.41 seconds. Temporary test dependencies
  were installed under `/tmp`; no repository dependency files changed.
- JavaScript `node --check`, Python `py_compile`, and `git diff --check`: passed.
- The feature-flag tests confirm the production default stays off and the
  Narrative Explorer entry and script are present only when enabled.
- DOM-level checks cover labelled breadcrumb landmarks, native button actions,
  focused detail headings, safe text rendering, and history focus identifiers.
  The browser has no Chromium/Chrome executable, so no real browser keyboard,
  screen-reader, or desktop/mobile visual session was available.

## Loading, performance, and availability

No connected-object request is issued during initial projection rendering.
Identical pending canonical-target requests share one fetch. An aborted final
subscriber cancels the fetch; stale results are ignored. Target response timing
and payload size use the existing Narrative Explorer metric event. There is no
persistent cache.

NE-5B's recorded mixed warm-request median was 1,182 ms; the NE-A2 local sample
was approximately 1.26 seconds. NE-5C adds no projection fields or eager graph
request. Connected-subject retrieval now emits request duration and response
byte metrics, but no end-to-end browser latency measurement was possible in
this environment. No headless browser or screen-reader runtime was installed,
so desktop/mobile visual checks and assistive-technology checks remain limited
to responsive styles and automated DOM interaction tests.

An offline projection miss retains the existing unavailable message. A
connected CKL subject has no offline snapshot in this feature and is reported
unavailable while the trail and return controls remain available.

## Scope and readiness

The implementation changes only Narrative Explorer/Companion navigation,
reader navigation option handling, presentation styles, tests, and these NE-5C
documents. No CKL object, source fingerprint, schema, Commentary artifact,
Tyndale, Lexicon, translation comparison, notes, saved study, Ask BHF, or
deployment configuration is changed. The feature default remains off. No
merge or deployment is part of this transaction.

NE-6 can proceed after the final branch and remote checks. Known limits are the
missing default local map database in this test environment and the absence of
headless browser / screen-reader verification.
