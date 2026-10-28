# NE-7R1 integration and regression results

## Local browser journeys

| Journey / suite | Result | Coverage and conditions |
|---|---:|---|
| General Firefox reader smoke, `tests/test_web_ui_selenium.py` | **8 passed in 135.96 s** | Firefox 155.0.1 / geckodriver 0.37.1, Service Worker enabled. The isolated worktree lacked its default `.bhf/ckl.sqlite`, so the app followed its configured `fallback_to_json` behavior. Includes cold reader initialization with Explorer disabled, concurrent Bible request during study-pack generation, ordinary Genesis 2 reader/translation/range/chapter/back flow, existing Commentary in Companion and context-preserving close, Maps browse/search, and Explorer rendered-state checks. |
| Geography Firefox, `tests/test_ne6_geography_selenium.py` | **9 passed in 235.55 s** | Firefox 155.0.1 / geckodriver 0.37.1, protected study DB read-only and hash-checked. Includes Genesis 2:8 Explorer evidence and authored trail/return, source-backed geography controls, John 2 passage-first compact Maps markers/place detail/return, map-selection acknowledgment and focus restoration, feature-off request absence, Service Worker cached/offline use, stop/restart recovery, restored-connectivity retry. |
| Browser regression before the fix | **failed as expected** | The fresh-browser regression failed while waiting for reader initialization: `/api/offline/packs/study` ran inline in the async route before translation setup and the Bible request. The same fixture now proves the chapter fetch has a completed response, JSON is consumed, selection is initialized, and the chapter DOM is rendered. |

The general browser suite also exercises the 390 × 844 requested Firefox window, but Firefox 155 clamps this headless environment to 500 × 758 CSS pixels. The test validates its rendered mobile drawer at the measured width; this is not a 390-pixel acceptance result.

## Python and API regression groups

| Group | Result | Notes |
|---|---:|---|
| Narrative Explorer projection/API, coverage, map matching, UI configuration, parity, Maps/KML, CKL retrieval/SQLite storage, Vercel CKL index and read-only connections | **137 passed in 457.76 s** | All targeted modules passed under the protected study DB read-only setting. |
| `tests/test_web_app.py` | **80 passed, 55 skipped, 4 subtests passed in 248.26 s** | The direct-ASGI helper previously stalled on the archaeology offline-pack case. Isolated diagnosis showed the synchronous worker completed but this environment’s selector loop did not service its cross-thread result without another loop event. The helper now schedules a short loop tick while the in-process ASGI call is active; the isolated archaeology test passed in 4.41 s, and the full suite completed. |
| Commentary/archaeology/translation/Tyndale compatibility group | **181 passed, 8 skipped, 15 failed**, 11 subtests passed, 1 warning, 138.36 s | The same 15 pre-existing failures were reproduced and are itemized in `03-compatibility-failure-triage.md`; no fixture, contract, rights field, prompt, source packet, or evidence gate was changed. |
| Offline-pack runtime default tests, `tests/test_optional_offline_pack_runtime.py` | **2 passed in 0.46 s** | Covers false-by-default and explicit opt-in configuration. |
| Focus/accessibility GUI checks | **5 skipped in 0.46 s** | The `tests/gui` fixture could not bind a local port in the restricted sandbox (`Operation not permitted`). Firefox keyboard/focus journeys are covered by the passing browser suites; no real screen-reader claim is made. |

### Commands

All commands ran from the isolated NE-7R1 worktree. The Python 3.12.3 environment used the repository package dependencies staged in `/tmp/bhf-ne6-python-deps`. Protected study-database tests used read-only mode. The general Firefox fixture used a disposable study DB and its default CKL path; the missing worktree-local SQLite index caused JSON fallback. The matched SQLite/JSON profile separately used the verified read-only index from the original checkout.

```sh
env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short \
  tests/test_narrative_explorer_projection.py \
  tests/test_narrative_explorer_api.py \
  tests/test_narrative_explorer_coverage_audit.py \
  tests/test_narrative_explorer_map_matching.py \
  tests/test_narrative_explorer_ui_config.py \
  tests/test_ne6r2_projection_parity.py \
  tests/test_map_tools.py tests/test_map_kml.py \
  tests/canonical_library/test_ckl_retrieval_service.py \
  tests/canonical_library/test_sqlite_storage.py \
  tests/test_vercel_ckl_index.py tests/test_db_connection_read_only.py

env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q -s --tb=short tests/test_ne6_geography_selenium.py

env PYTHONPATH=/tmp:/tmp/bhf-ne6-python-deps python3 -m pytest -q -s --tb=short -p ne7_firefox_adapter tests/test_web_ui_selenium.py

env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short tests/test_web_app.py

env PYTHONPATH=/tmp/bhf-ne6-python-deps BHF_STUDY_DB_PATH=./.bhf-data/study.sqlite BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short \
  tests/test_archaeology_ai_packet.py tests/test_archaeology_corpus_coverage.py \
  tests/test_archaeology_import.py tests/test_archaeology_media.py \
  tests/test_archaeology_offline.py tests/test_archaeology_resolver.py \
  tests/test_archaeology_service.py tests/test_wikimedia_archaeology_provider.py \
  tests/test_translation_catalog.py tests/test_translation_registry.py \
  tests/test_translation_settings.py tests/test_tyndale_evidence.py \
  tests/test_chapter_commentary.py tests/test_bhf_commentary_projection.py \
  tests/test_commentary_availability.py tests/test_commentary_canonical_runtime.py \
  tests/test_commentary_v12_reader_integration.py \
  tests/test_commentary_v12_reader_projection_seven_chapter.py \
  tests/test_commentary_v12_freeze.py tests/test_reader_level_idea_projection.py \
  tests/test_companion_context.py

PYTHONPATH=/tmp/bhf-ne6-python-deps:$PWD python3 -m pytest -q tests/test_optional_offline_pack_runtime.py

PYTHONPATH=/tmp/bhf-ne6-python-deps:$PWD BHF_STUDY_DB_READ_ONLY=1 python3 -m pytest -q --tb=short \
  tests/gui/test_reader.py::test_reader_tabs_preserve_selection_and_restore_after_refresh \
  tests/gui/test_study_companion.py::test_mobile_selection_opens_accessible_companion_states \
  tests/gui/test_study_companion.py::test_translation_comparison_mobile_layout_back_navigation_and_focus \
  tests/gui/test_ask.py::test_ask_bhf_restores_focus_to_its_trigger_on_close \
  tests/gui/test_maps.py::test_mobile_map_navigator_can_be_closed

npm test
```

The browser commands used a temporary study DB and reader settings under the test fixture. Browser response traces recorded request IDs, method/URL, safe `Accept` and refresh headers, fetch initiation, response headers, body consumption, JSON parse completion, initialized selection, rendered heading, Service Worker state, and server request/handler/body timings. No authorization, cookie, or user data was logged.

The 137-test core command above is the exact NE-7 group; the compatibility command is the unchanged NE-7 compatibility group. The legacy `tests/test_web_app.py` direct-ASGI helper now runs with a small periodic loop tick because the isolated sandbox's asyncio selector did not wake for AnyIO's worker callback without another loop event. This was confined to the test harness; the Uvicorn/Firefox regression exercises the actual server response path.

## Frontend, syntax, and integrity checks

- `npm test`: **13 frontend test files passed**, 0 failures. Includes Narrative Explorer UI/provenance, Maps focus acknowledgment, Service Worker cache behavior, and ordinary reader modules.
- `PYTHONPATH=/tmp/bhf-ne6-python-deps:$PWD python3 -m compileall -q bhf_agent bhf_web framework tests`: passed after the test-helper adjustment.
- `find bhf_web/static -type f -name '*.js' -print0 | xargs -0 -n1 node --check`: passed after the test-helper adjustment.
- `git diff --check`: passed before final document edits; the final pre-commit check is still required.
- `PYTHONPATH=/tmp/bhf-ne6-python-deps:$PWD python3 -m framework.canonical_library --root framework/canonical_library verify-db --database ./.bhf/ckl.sqlite`: passed read-only. CKL object count **687**, schema v4, retrieval index v3, inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.
- Recomputed source inventory signature `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea` and source manifest fingerprint `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40`; both match NE-7.
- Protected study DB `./.bhf-data/study.sqlite`: final observed SHA-256 `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`.

## Legitimate skips and remaining validation

The 8 compatibility-group skips and 55 legacy web-app skips are existing skip contracts, including removed runtime/model test surfaces. The selected GUI focus/accessibility tests skipped because `tests/gui/conftest.py` could not bind a local port in this sandbox. Firefox browser journeys cover the requested reader, focus, Maps, offline, and recovery paths. No spoken screen-reader test or genuine 390-pixel rendering is claimed.
