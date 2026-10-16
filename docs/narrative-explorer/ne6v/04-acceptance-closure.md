# NE-6V Acceptance Closure

## Closure status

**`BHF_NARRATIVE_EXPLORER_NE6V_VALIDATION_PENDING`**

The two missing browser acceptance paths are closed: Firefox selected exact synthetic place and route records through the real Maps controller, and the mobile catalog/search reached completed successful states. A successful online retry against real map data demonstrates `not_found` when all responses parse and the ID is absent. The original John 2 retry also exposed a separate large-body Firefox failure: the endpoint returns 200, but its 21.7 MB JSON body is sometimes aborted or truncated in the Service Worker path. The controller retains `failed` in that case because it did not load all required data. Cold startup is investigated, but first-hit browser latency remains high and Vercel index provisioning is not established. A real screen-reader check is also still required during NE-7 acceptance.

## Baseline and ancestry

- Expected NE-A2: `3d406b6256a6064a35e0e567c8a1304bf3cba2e8`
- Expected NE-5C: `b451428546b87b9cfb0912292f8e3906fa0e0803`
- NE-6 base: `224f691feaa4a9ad3f4c921d6bda70941864b67f`
- Fetched `origin/master`: `a320e0adda1bda0403bdcb2c82cb8b5107d9a4cd`
- NE-A2 → NE-5C → NE-6 ancestry was verified. Those commits had not merged into master, so this branch was based directly on NE-6 in isolated worktree `/tmp/bhf-ne6v-acceptance`.
- Final branch and remote SHA are recorded after commit/push.

## Browser acceptance

- **Positive focus:** Firefox selected the exact synthetic place and route IDs, rendered matching details and KML links, and showed the corresponding Leaflet marker/path. Requested and selected kinds/IDs matched. The details are in [positive map focus validation](01-positive-map-focus-validation.md).
- **Fixture isolation:** controlled test-only API responses are installed in the browser page; they are not stored in a database. The actual catalog, Genesis 2 projection, CKL manifest, source inventory, and release data do not include fixture IDs.
- **Negative controls:** Eden, Acts 7 Nile, Joshua 1 Negeb, and uncertain Horeb/Sinai remain withheld from precise pin promotion. No source evidence was generated and no CKL/source inventory was edited.
- **Mobile Maps:** catalog and search requests completed with HTTP 200; loading cleared, Jerusalem results/details worked, close/reopen focus restored, no horizontal overflow appeared, and measured touch targets met 44 pixels. Firefox clamped the headless mobile width to 500 pixels. See [mobile Maps completion](02-mobile-maps-completion.md).
- **Retry:** on real Firefox with the real no-match passage 3 John 1, catalog, places (1,813 bytes), and routes (1,812 bytes) returned HTTP 200 and parsed. With the requested ID absent, Maps reported `not_found` with no selected item. The original John 2 retry's place response had HTTP 200 and a declared 21,687,196-byte body, but Firefox threw `AbortError` or a JSON `SyntaxError` before parsing completed. A direct HTTP control read all 21,687,196 bytes and parsed valid JSON. In that incomplete browser path, `failed` is accurate; status semantics were not weakened.
- **Feature flag off:** Firefox read Genesis 2 with the feature disabled and observed zero Narrative Explorer or Maps API requests.
- **Trail compatibility:** existing three-hop navigation, breadcrumb/current-step landmarks, connected subject/passages, browser Back, return-to-origin, selected verse, translation, and focus restoration were rechecked.

## Evidence, geography, and databases

The Genesis 2–3, Genesis 6, Deuteronomy 32, Psalm 82, Exodus 3, Acts 7, and Joshua 1 source-backed pilot coverage remains under the existing projection/API/coverage suites. Original CKL identifiers, source/bibliography data, anchors and relationship labels, confidence/certainty, dispute/review metadata, physical and geometry displayability, cosmic-geography classification, and three-hop trail limit remain governed by the existing assertions. No conceptual geography marker was introduced. Exodus 3's documented sacred-space gap remains open.

The documented study database was accessed with `BHF_STUDY_DB_PATH` and `BHF_STUDY_DB_READ_ONLY=1`. Its current schema version remains 37, `integrity_check` returned `ok`, and SHA-256 remains `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`. Tests reject DML in read-only mode and confirm the setting is scoped to the configured protected path; a separate disposable database remains write-enabled. No DDL/DML, migration, or fixture write was issued against the protected database.

The verified CKL SQLite index SHA-256 remains `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182`, passes integrity check, and matches the committed source fingerprint. CKL sources and fingerprints were not modified.

## Accessibility

Real Firefox keyboard/focus assertions passed for accessible navigation names, current trail step, polite loading/map status, keyboard navigation, Maps close/reopen, and evidence detail focus return. Mobile navigator/details and the 44-pixel minimum controls were checked. No supported running screen-reader environment was available; actual announcements and spoken reading order remain a distinct NE-7 acceptance task, not a DOM-based claim.

## Performance disposition

The fresh-process, page-cache-warm benchmark measured JSON fallback at 30,478.701 ms and the verified SQLite index at 1,964.208 ms for the same 131,228-byte Genesis 2:8 response and identical body hash. CKL initialization/fingerprinting accounted for 28,893.038 ms in JSON mode and 293.305 ms in SQLite mode. The real browser measured 8,469–9,906 ms of server wait with SQLite. Docker builds and verifies the SQLite index; Vercel excludes `.bhf/` and has no index build step. The performance issue is locally mitigated for Docker but outstanding for Vercel and unexplained browser first-hit latency. Full timing and deployment evidence is in [cold-start investigation](03-cold-start-performance-investigation.md).

## Verification outcomes

Final command results:

- Firefox/Selenium geography suite: 7 passed in 290.20 seconds, including positive place/route selection, missing-ID control, mobile catalog/search, real-source controls, feature-flag-off requests, trail/focus, and retry.
- Frontend Node suite: 12 passed, 0 failed.
- Narrative Explorer API/projection/matching/coverage/UI config plus read-only DB suite: 96 passed.
- Legacy Maps/archaeology/read-only DB selection: 52 passed, 1 confirmed pre-existing failure. `test_archaeology_corpus_coverage.py::test_expansion_preserves_visible_uncertainty_and_reviewed_media_rights` fails identically at NE-6 base `224f691feaa4a9ad3f4c921d6bda70941864b67f`; no change was made to that unrelated baseline issue.
- Python compilation, JavaScript syntax checks, and `git diff --check`: passed.
- Study DB and CKL hashes/integrity: unchanged and valid.

## Changed files

- `bhf_web/static/sw.js` — bump to cache version v48 and keep the Service Worker alive until successful API response cache writes settle.
- `bhf_web/static/styles/maps.css` — set narrow mobile Maps action controls to the measured 44-pixel minimum.
- `tests/frontend/map-focus-acknowledgment.test.js` — assert wrong-ID/wrong-kind outcomes cannot claim selection.
- `tests/test_db_connection_read_only.py` — test DML rejection and configured-path scoping for read-only DB mode.
- `tests/test_ne6_geography_selenium.py` — isolated positive place/route fixture, wrong-ID path, mobile terminal waits/search/focus/overflow/touch-size checks, retry diagnosis, feature-flag-off network check, and browser measurements.
- Four NE-6V reports in this directory.

No protected source inventory, canonical CKL record, generated Commentary release, or default feature-flag setting was changed. No merge or deployment was performed.

## Remaining release blockers and NE-7 readiness

NE-6 geography integration verification is materially complete. Overall acceptance remains pending because (1) the 21.7 MB John 2 map response is not reliably consumable in real Firefox under the Service Worker path, (2) first Explorer browser TTFB remains unexplained by direct stage measurements, and (3) the Vercel deployment path has no established current SQLite index provisioning. Track the performance work as a separate release dependency. NE-7 must also perform an actual screen-reader check if a supported assistive-technology environment is available. Do not enable Narrative Explorer by default, deploy, or treat the feature as launch-ready until these checks are dispositioned.
