# NE-7.6 — Performance, regression suite, and baseline failures

## Performance measurements

All values are local diagnostics, not hosted performance claims. Filesystem cache state was not flushed or isolated in the browser environment. SQLite API timings below use a fresh process and a filesystem-cache-warm, identity-verified index. The in-process ASGI transport has no network response-transfer measurement.

| Operation | Condition | Result |
|---|---|---|
| Genesis 2:8 Explorer, browser JSON fallback first request | Browser process/application local; filesystem cache uncontrolled | About 76,397 ms wait; 131,228-byte body. This includes JSON fallback and request/render path. |
| Genesis 2:8 Explorer, browser warm request | Same browser/process | About 2,689–3,006 ms. |
| Genesis 2:8, direct ASGI with SQLite | New process, CKL index process-cold, filesystem cache warm | 1,933.0 ms request; 2.133 ms JSON parse; 131,228 bytes; six sections, 17 items; body SHA-256 `31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`. |
| Genesis 2:8, direct ASGI warm | Same process and input | 2,227.2 ms request; 4.213 ms JSON parse; same size and SHA. |
| John 2 compact Maps places, first / warm | Browser | 187,007 bytes; first wait about 4.285 s, warm about 0.29 s. |
| John 2 catalog / routes | Browser | 713 bytes / 2,900 bytes. |
| Selected John 2 place details | Browser | 32,842 bytes; about 323 ms. |
| John 2 legacy full payload | Direct local HTTP | 21,687,196 bytes, 69 markers; response headers about 42.741 s and body about 10.395 s; SHA-256 `fcb29f0111eb5f169c2541d4429ecd630f0e55f398b182515f24f06e486b243f`. |
| Initial frontend load | Local Firefox 500 × 758 with seeded reader selection / SQLite fixture | `loadEventEnd` 945 ms, DOMContentLoaded 933 ms, DOM interactive 228 ms; first chapter heading ready at about 14,339 ms (51-verse John 1 reader). Separate from the disposable empty-state general smoke, where default selection stayed blank. |
| Companion open / close | Same local browser | About 220 ms / 164 ms to the observed state transition. |
| Detail fetch / trail action | Browser | Detail 323 ms as above; no separate numeric trail-step timing captured. |

Browser wait includes browser scheduling and server processing; request transfer and JSON parse figures are stated separately only where directly measured. Historical NE-6R2 values (JSON cold 30.1 s, SQLite cold 2.0 s, warm SQLite 1.5 s) are comparison references, not guarantees. The browser JSON fallback's 76.4-second first wait is a material local performance finding and warrants follow-up profiling; it is not evidence of hosted performance. No production performance was inferred from these measurements.

## Verification commands and results

The package test dependencies were supplied from `/tmp/bhf-ne6-python-deps`. Protected database commands used `BHF_STUDY_DB_READ_ONLY=1`.

- `npm test` — **13 frontend test files passed**.
- Core projection/API/coverage/map matching/SQLite/storage/read-only group — **137 passed in 476.26 s**. Files: `tests/test_narrative_explorer_projection.py`, `test_narrative_explorer_api.py`, `test_narrative_explorer_coverage_audit.py`, `test_narrative_explorer_map_matching.py`, `test_narrative_explorer_ui_config.py`, `test_ne6r2_projection_parity.py`, `test_map_tools.py`, `test_map_kml.py`, `canonical_library/test_ckl_retrieval_service.py`, `canonical_library/test_sqlite_storage.py`, `test_vercel_ckl_index.py`, and `test_db_connection_read_only.py`.
- `tests/test_ne6_geography_selenium.py` — **9 passed in 444.29 s**; Firefox 155.0.1 / geckodriver 0.37.1. Includes real passage flow, feature-off request absence, evidence details/trails, Maps, focus status, offline/retry, Service Worker, and compact/lazy Maps requests.
- Backend compatibility group (archaeology, translations, Tyndale, Commentary, reader projection, Companion context) — **181 passed, 8 skipped, 15 failed**, 11 subtests, one warning, 140.42 s. The failures are itemized below.
- `tests/test_web_app.py` — **80 passed, 55 skipped**, 4 subtests, 247.53 s after the two stale test expectations were corrected.
- General `tests/test_web_ui_selenium.py` — final run **2 passed, 2 failed in 182.18 s** with the Firefox adapter. The mobile Companion drawer and Explorer case passed. Maps browse timed out waiting for Jerusalem results; reader search/navigation could not proceed because the page's selected passage never initialized. The page shell and script loaded, and a direct Python HTTP Bible request returned HTTP 200 / 6,041 bytes; Firefox-side fetch remained pending. Direct Python map search against the initialized disposable DB returns a Jerusalem seed result. This unresolved browser/runtime integration discrepancy keeps reader/test-suite acceptance pending. The dedicated geography browser suite independently exercised the passage-first reader and Maps paths and passed 9/9.
- Tyndale local browser fixture — **1 passed**.
- Translation comparison preserving selected range/unique installed text — **1 passed**. Chrome CDP-only mobile translation and an offline-page setup timed out under Firefox; not counted as product failures or passes.
- `python3 -m compileall -q bhf_agent bhf_web framework tests` — passed.
- `find bhf_web/static -type f -name '*.js' -print0 | xargs -0 -n1 node --check` — passed.
- `node --test tests/frontend/assistant-handoff.test.js` — passed.
- `git diff --check` — passed before final report creation; rerun before commit.
- `framework.canonical_library verify-db --root framework/canonical_library --database /tmp/ne6r3-ckl.sqlite` — passed against source identity (687 objects; schema v4/index v3).

The exact pytest wrapper and environment were `env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest ...`; Selenium used `env PYTHONPATH=/tmp:/tmp/bhf-ne6-python-deps python3 -m pytest -q -s --tb=short -p ne7_firefox_adapter tests/test_web_ui_selenium.py` with a local disposable DB/server. The first non-escalated run skipped all four browser cases because sandbox policy denied loopback sockets; the escalated run above actually executed them. A Maps-only retry reproduced the empty passage heading. A direct Python HTTP request to the same app returned 200/6,041 bytes while the Firefox-side fetch stayed pending. A retry with `BHF_DATA_DIR` and protected `BHF_STUDY_DB_PATH` explicitly pointed to the source checkout reproduced the failure (1 failed in 40.93 s). The temporary adapter and test DB live under `/tmp` and are not repository artifacts.

The focused commands were run with these file groups:

```text
env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short tests/test_narrative_explorer_projection.py tests/test_narrative_explorer_api.py tests/test_narrative_explorer_coverage_audit.py tests/test_narrative_explorer_map_matching.py tests/test_narrative_explorer_ui_config.py tests/test_ne6r2_projection_parity.py tests/test_map_tools.py tests/test_map_kml.py tests/canonical_library/test_ckl_retrieval_service.py tests/canonical_library/test_sqlite_storage.py tests/test_vercel_ckl_index.py tests/test_db_connection_read_only.py
env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q -s --tb=short tests/test_ne6_geography_selenium.py
env PYTHONPATH=/tmp:/tmp/bhf-ne6-python-deps python3 -m pytest -q -s --tb=short -p ne7_firefox_adapter tests/test_web_ui_selenium.py
env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short tests/test_web_app.py
env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short tests/test_archaeology_ai_packet.py tests/test_archaeology_corpus_coverage.py tests/test_archaeology_import.py tests/test_archaeology_media.py tests/test_archaeology_offline.py tests/test_archaeology_resolver.py tests/test_archaeology_service.py tests/test_wikimedia_archaeology_provider.py tests/test_translation_catalog.py tests/test_translation_registry.py tests/test_translation_settings.py tests/test_tyndale_evidence.py tests/test_chapter_commentary.py tests/test_bhf_commentary_projection.py tests/test_commentary_availability.py tests/test_commentary_canonical_runtime.py tests/test_commentary_v12_reader_integration.py tests/test_commentary_v12_reader_projection_seven_chapter.py tests/test_commentary_v12_freeze.py tests/test_reader_level_idea_projection.py tests/test_companion_context.py
```

The compatibility group used the protected read-only database environment above. `npm test`, Python compilation, JavaScript syntax checks, the assistant-handoff Node test, and `git diff --check` were also run; their results are listed above.

## Fifteen compatibility failures: characterization and disposition

These failures are in established Commentary/archaeology test contracts and were not introduced by an NE-7 product change. The relevant full test group showed the current behavior directly; prior NE-6R3 already listed the rights, synthesis-count, and frozen prompt failures.

1. **Archaeology media rights (1):** `test_expansion_preserves_visible_uncertainty_and_reviewed_media_rights` expects two Wikimedia records to be redistributable. Current `wm-ekron-excavations` and `wm-jerusalem-mikveh` explicitly set `can_redistribute=false`, `can_cache=false`, with `other_redistributable` rights status. These restrictions are legitimate licensing metadata and were preserved. This is a stale expectation; not a new reader defect.
2. **Reader synthesis counts (3):** reader-level tests expect synthesis totals 119/21/34 while the current selective compiler yields 7/4/6 (current evidence-item totals 145/23/45). The implementation's selective-generation behavior dates to commit `cf2d0f8` (2026-10-06). No lost evidence was established by this count mismatch. Prose was not regenerated; snapshot expectations need an independently reviewed migration.
3. **Frozen prompt packet identity (1):** `test_prompt_1_7_frozen_packet_is_unchanged` compares actual prompt hash `0f9d1e98943d939ced4f90b3bfbf4f47b3ee0f537705b13965409951a4994c26` to stale frozen packet hash `6d6331aef8c7b445f434b07cf407f2e6e181efe2fcc3ff0398f0142c6f2a5dd0`; system hash remains `cbe6a47cb9ec7b7186347aa3e25ff05d2b9387f72e6297ce0bce44515283f614`. Neither prompt nor packet was edited.
4. **Generic Commentary test fixtures (4):** `test_unsupported_section_is_not_included_in_salvage`, `test_valid_sections_survive_when_another_section_fails`, `test_explicit_date_must_be_supported_by_cited_evidence`, and `test_generator_stamps_configured_model_and_timestamp` fail because `_bundle()` fixture material has no usable source provenance. The current validator correctly marks it `DATA_GAP` and rejects citation; later tests assume a synthesis unit and hit an empty result. This is a stale source-eligibility fixture. Evidence gates were not weakened.
5. **Frozen seven-chapter identity (6):** all six `tests/test_commentary_v12_reader_projection_seven_chapter.py` tests stop at `DiagnosticError: source packet identity changed for Isaiah 13` following current source/compiler inputs. Test names: `test_exact_seven_chapter_corpus_and_frozen_contracts`, `test_projection_shapes_and_ancestry_cover_dense_and_sparse_controls`, `test_prompt_17_is_unchanged_and_variant_is_additive`, `test_revelation_21_reused_candidate_import_and_evaluation_remain_exact`, `test_candidate_generation_is_fail_closed_until_all_six_missing_responses_exist`, `test_projection_manifest_reproducibility`. Frozen source packets were not rewritten.

The failures indicate stale compatibility expectations or fixtures, except for the real and correctly preserved media rights restrictions. No failure establishes a new NE-7 evidence-integrity defect. The stale tests should be addressed separately with documented source-contract updates; do not alter rights, regenerate Commentary, or weaken provenance gates to make them pass.

## Targeted stale test fixes in this branch

Two failures in `tests/test_web_app.py` were verified obsolete and corrected: a test looked for removed `runBibleSearchFallback` instead of current `submitBibleSearch`; another invoked removed `/ask/jobs` rather than checking the existing manual, selection-aware Ask BHF handoff. Browser smoke fixtures were updated for current Explorer/Maps navigation, no-selection Maps entry, reader readiness, and offline text-search semantics. These changes touch tests only; product behavior is unchanged. The web-app suite passes; general Firefox browser smoke retains the unresolved Bible/Maps request discrepancy described above, while the dedicated geography suite passes.
