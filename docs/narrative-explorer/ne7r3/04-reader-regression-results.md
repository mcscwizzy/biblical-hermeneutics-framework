# NE7R3 reader regression and preservation results

## Acceptance results

The following retirement and preservation checks passed on the current
uncommitted NE7R3 tree:

| Check | Result | Evidence |
|---|---:|---|
| `tests/test_web_ui_selenium.py` | **9 passed** in 161.27 s | Firefox 155.0.1 / geckodriver 0.37.1; generated URL/UI removal, ordinary reader, Tyndale notes, comparison, Maps, and optional Explorer flows |
| Selected real-data `tests/test_ne6_geography_selenium.py` | **5 passed** in 112.31 s | Read-only CKL/study stores; feature-off request absence, manual Study pack/offline persistence, cached Maps and retry, mobile Explorer/Maps, uncertain references |
| `npm test` | **12 passed, 0 failed** | Node reader, cache, and retirement behavior |
| `tests/test_commentary_retirement.py`, `tests/test_narrative_explorer_ui_config.py`, `tests/test_vercel_packaging.py`, `tests/test_vercel_startup.py` | **15 passed** | Retired endpoints and release UI removal; Tyndale route registration; package/startup contracts |
| Direct translation, Notes, Highlights, Maps, archaeology, and lexical route cases | **6 passed** | Temporary test database fixtures |
| Tyndale database diagnostics | **healthy** | SQLite integrity `ok`; 17,478 entries/anchors; no orphaned anchors |

The Firefox retirement assertion fetched six former generated Commentary and
coverage paths. Each returned HTTP 410 with `reason: "feature_retired"`. The
rendered reader had no generated BHF card, coverage element, release identity,
or generated Commentary/coverage script. The retained Tyndale panel rendered
entries from a disposable copy of `.bhf/commentary.sqlite`; Compare
Translations rendered at least two translation sections. Closing Companion
preserved the selected passage and left Tyndale notes available.

The feature-off browser run observed no Narrative Explorer or Maps requests
during ordinary reading. With the feature enabled, the existing Explorer
Companion flow remained usable. The offline acceptance cases covered manual
Study pack installation, persistence, cached Maps use while the server was
stopped, and recovery after server restart. They used disposable browser
storage; no study database was changed.

## Broader Python results and existing failures

A selected cross-subsystem run collected 432 tests: **362 passed, 64 skipped,
6 failed**. Reruns with the fixtures those tests require resolved five of the
six failures: four direct web/editor route cases passed with temporary writable
study and Tyndale databases, and the SQLite stale-database-policy test passed
on rerun. The remaining failure is
`tests/canonical_library/test_manifest.py::CanonicalInventoryTests::test_all_inventory_json_files_validate_and_receive_governance_defaults`.
It reports five existing `review_status=in_review` CKL source objects without
`generated_by`. The source tree and test are unchanged from NE7R2. No CKL
source was edited to address it.

The following two frozen v1.2 promotion checks still fail with the protected
`ckl_database` fingerprint mismatch:

- `tests/test_commentary_v12_five_chapter_structured_enrichment.py::test_frozen_contracts_are_unchanged`
- `tests/test_commentary_v12_post_applicability_coverage_census.py::test_contract_snapshot_keeps_protected_contracts_and_records_asv_repair`

They fail identically on NE7R2 and NE7R3 and are not a retirement regression.
The original expected database artifact is unavailable locally. See the
[fingerprint investigation](02-ckl-fingerprint-investigation.md). The full
repository suite and the v1.2 freeze workflow are **not reported as passing**.
The freeze workflow was not run because it rebuilds `.bhf/ckl.sqlite`; its
installed-package step also still requires the payload removed by this
retirement (see [03-runtime-package-reduction.md](03-runtime-package-reduction.md)).

## Completion classification

| Category | Result |
|---|---|
| Retirement-specific behavior | Browser, Node, and focused Python targets pass; preserved reader/API flows and read-only database integrity checks pass. |
| Unchanged baseline failures | The two frozen CKL fingerprints fail identically on NE7R2/NE7R3. One canonical manifest source-quality test also fails on unchanged NE7R2 source rows. |
| New retirement integration blocker | The PR-triggered v1.2 freeze workflow still names the removed reader integration test and asserts that the retired v1.2 payload is installed in the wheel. This gate will reject the retirement until its contract is separately reviewed and aligned. |

The remaining release workflow alignment is not classified as a CKL data
regression. It is a new CI incompatibility caused by retiring a package that
the workflow still expects.

## Integrity and preservation

Read-only SQLite checks on the CKL, study, and Tyndale databases each returned
`PRAGMA integrity_check = ok`, zero foreign-key errors, and `query_only = 1`.
CKL `verify_database(..., compare_fingerprint=True)` passed against the
checked-in source inventory with 687 objects, 2,329 claims, 5,232 sources,
1,297 evidence rows, and inventory fingerprint
`90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.

| Protected file | SHA-256 after verification |
|---|---|
| `.bhf/ckl.sqlite` | `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182` |
| `.bhf-data/study.sqlite` | `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf` |
| `.bhf/commentary.sqlite` | `2652edde56b22cf22628ced0da7dd81d7668c305ce17581a5a817aa97765e17f` |

The CKL source/manifests, `framework/canonical_library`, shared
`bhf_web/services/ckl_provider.py`, `bhf_agent/chapter_commentary/`, and
`.bhf-data` compare unchanged to NE7R2. The v1.1 `pipeline-state.json` hash is
`52d4e06976b7f0fbf8546eb816f33dd702b77237ea1a0de98743afb8698690d7`; the
orchestrator `status` command reports `CORPUS_COMPLETE`, 935/935 eligible
chapters, zero remaining, and no validation errors. No pipeline stage was
advanced.

The preserved service boundaries are exercised by the tests above:

- `/api/commentary/*` remains the Tyndale Study Notes API; its routes remain
  registered and the browser reads notes from the retained SQLite store.
- Compare Translations stays directly available from Companion.
- Notes, Highlights, Bible translations, Maps, and optional Narrative Explorer
  routes and data are outside the generated Commentary removal.
- Commentary v1.1/v1.2 source releases, provenance, authoring/publishing tools,
  CKL evidence, and source attestations remain intact.

## Limits and blockers

The five browser tests are selected retirement-relevant geography cases, not
the entire geography module. Headless Firefox clamps the requested 390 × 844
viewport to 500 × 758 in this environment, so this run does not establish a
true 390-pixel layout. Whole-reader cold offline navigation remains unverified
as in the NE7R2 report; the accepted offline evidence is cached Maps behavior,
manual Study pack persistence, and restart recovery.

No production deployment was tested. NE7R3 is ready for technical review of
the retirement behavior, but it is not merge-ready while the PR-triggered v1.2
freeze workflow still points to the deleted reader test and package payload.
The workflow alignment requires a separate maintainer/release decision; the
two historic CKL fingerprint failures remain unchanged and must not be
suppressed or rewritten.
