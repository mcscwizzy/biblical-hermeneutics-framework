# NE7R3 CKL Fingerprint Blocker Investigation

**Classification:** Pre-existing CKL fingerprint mismatch

**Confidence:** High that NE7R3 did not introduce the failing checks; medium-high on the historical artifact diagnosis because the original SQLite file is unavailable locally.

## Finding

The frozen value `19c66f931b6afe907bbef85ac29f34a3aefd288886d516c318e7965474ca2322` is a SHA-256 of the bytes at `.bhf/ckl.sqlite` when the v1.2 contract was frozen. It is not the CKL inventory fingerprint stored inside the database. The current local file has byte SHA-256 `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182`; its separately verified CKL inventory fingerprint is `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.

Both failing tests fail on NE7R2 parent `26938c76b4ea813d728e156b3702b81ec6342ec0` and on NE7R3 HEAD with the same `CensusError: protected contract fingerprint changed: ckl_database`. The same `847…` database passes the read-only CKL database verifier against both revisions. This is a baseline contract mismatch, not an NE7R3 CKL regression.

Historical provenance shows why the pin differs: the expected `19c…` database was already attested on 2026-09-05 as not matching its then-current JSON inventory (`matches_json_inventory: false`, 665 database objects versus 679 source objects). The available current database was built on 2026-10-12 and verifies against the current source inventory. The original `19c…` database file is not present among the repository-local SQLite files, so it could not be replayed directly. No arbitrary database was substituted as though it were that original file; the parent reproduction used the separately documented and source-verified `847…` runtime database.

## Frozen checks and fingerprint provenance

The frozen contract is `docs/commentary-v1.2-evidence-applicability-contract-freeze-v1.json`. It records `path: .bhf/ckl.sqlite` and the `19c…` SHA-256 at lines 43–45. The contract was introduced by commit `5c00d961` on 2026-09-10, with `starting_sha` `d6dfa57307a60a4e0e042b4705f7b68e0cf03b72`.

The two checks are:

- `tests/test_commentary_v12_five_chapter_structured_enrichment.py::test_frozen_contracts_are_unchanged` (lines 18–20).
- `tests/test_commentary_v12_post_applicability_coverage_census.py::test_contract_snapshot_keeps_protected_contracts_and_records_asv_repair` (lines 147–155).

Both call `tools/commentary_v12_post_applicability_coverage_census.py::contract_snapshot`. That code reads the frozen `sha256`, hashes the current file bytes via `sha256_file(path)`, and raises when a protected hash differs (lines 229–243). Thus `19c…` and `847…` are directly comparable file hashes in this check. They are not interchangeable with the database's `inventory_fingerprint`, manifest fingerprint, or source-inventory signature. `framework/canonical_library/database_builder.py` opens the database using SQLite `mode=ro`, runs integrity and foreign-key checks, and separately compares those internal/source identities (lines 105–175).

The expected file's provenance is present in `.bhf-data/bhf-commentary-candidates/genesis-g0-evidence-census/genesis-evidence-census.json`:

- Lines 79122–79136 record the build timestamp `2026-09-05T18:39:10.904497Z`, file size 107,597,824, file SHA `19c…`, internal inventory fingerprint `4110222a…`, 665 objects, and `matches_json_inventory: false`.
- Lines 79158–79175 record the source side of that same before/after comparison: 679 source objects and source inventory fingerprint `78d983e0…`, against the same 665-object database.
- The later applicability-enforcement manifest and final report again identify `.bhf/ckl.sqlite` with SHA `19c…` (`manifest.json:5`; `final-report.json:18–20, 1634–1636`). These records explain the frozen value but do not include the SQLite binary itself.

The current `.bhf/ckl.sqlite` has SHA `847…`, size 116,334,592, build timestamp `2026-10-12T03:30:43.334452Z`, schema 4, retrieval index 3, and 687 objects. The read-only verifier reports 2,329 claims, 5,232 sources, 1,297 evidence records, and inventory fingerprint `90fa…`. Earlier NE6/NE7 reports independently record the same `847…` byte hash and `90fa…` source fingerprint (for example, `docs/narrative-explorer/ne6v/03-cold-start-performance-investigation.md:55` and `docs/narrative-explorer/ne7r1/04-integration-regression-results.md:82`).

## Baseline and reproduction

Checkout captured before this report was created:

| Item | Value |
|---|---|
| Branch | `refactor/narrative-explorer-ne7r3-commentary-retirement` |
| HEAD | `c4e1a7a00dd36d459b0f86088fab28fb864a7eac` |
| Direct parent of HEAD | `7a79f73d7e78490ce7082940ca7f9b551d6bd828` |
| NE7R3 baseline / NE7R2 parent | `26938c76b4ea813d728e156b3702b81ec6342ec0` |
| Working-tree state | 974 unstaged deletions under `bhf_agent/data/commentary-v1.2/` and 10 unstaged modified files; no staged entries. These existing Task 3 changes were preserved. |
| Current database byte SHA-256 | `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182` |

The repository-local SQLite inventory did not contain the expected `19c…` binary. For a clean parent baseline, a source archive of `26938c76b4ea813d728e156b3702b81ec6342ec0` was extracted under `/tmp/bhf-ne7r3-parent.gSKEX8`; the documented current `.bhf/ckl.sqlite` was copied there without modification. The copy's SHA remained `847…` and `verify-db` passed against the parent's checked-in CKL sources.

Commands run from the current checkout (the two targeted tests intentionally fail):

```bash
sha256sum .bhf/ckl.sqlite
PYTHONDONTWRITEBYTECODE=1 python3 -m framework.canonical_library --root framework/canonical_library verify-db --database .bhf/ckl.sqlite
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_commentary_v12_five_chapter_structured_enrichment.py::test_frozen_contracts_are_unchanged \
  tests/test_commentary_v12_post_applicability_coverage_census.py::test_contract_snapshot_keeps_protected_contracts_and_records_asv_repair
```

Parent reproduction setup and commands. This archives only the committed NE7R2 tree, then supplies the documented current CKL database as an external input; it does not recreate or impersonate the unavailable historical `19c…` file:

```bash
mkdir -p /tmp/bhf-ne7r3-parent-repro
git archive --format=tar --output=/tmp/bhf-ne7r3-parent-repro/parent.tar 26938c76b4ea813d728e156b3702b81ec6342ec0
tar -xf /tmp/bhf-ne7r3-parent-repro/parent.tar -C /tmp/bhf-ne7r3-parent-repro
mkdir -p /tmp/bhf-ne7r3-parent-repro/.bhf
cp -p .bhf/ckl.sqlite /tmp/bhf-ne7r3-parent-repro/.bhf/ckl.sqlite
cd /tmp/bhf-ne7r3-parent-repro
sha256sum .bhf/ckl.sqlite
PYTHONDONTWRITEBYTECODE=1 python3 -m framework.canonical_library --root framework/canonical_library verify-db --database .bhf/ckl.sqlite
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q \
  tests/test_commentary_v12_five_chapter_structured_enrichment.py::test_frozen_contracts_are_unchanged \
  tests/test_commentary_v12_post_applicability_coverage_census.py::test_contract_snapshot_keeps_protected_contracts_and_records_asv_repair
```

The current checkout produced **2 failed** with the `ckl_database` protected-fingerprint error. The NE7R2 archive produced the same **2 failed** and same error. `verify-db` passed on both copies: 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence records, schema 4, retrieval index 3, inventory fingerprint `90fa…`. Its SQLite `integrity_check` and `foreign_key_check` both passed. The current database SHA was unchanged after verification.

**Limit:** this reproduces the frozen checks before NE7R3 using the documented current CKL artifact. It does not reproduce the historical `19c…` file itself because that binary is unavailable locally. The available attestations establish its hash and stale-source status, but do not allow a row-by-row content comparison with the current database.

## NE7R3 preservation review

| Protected area | Evidence and result |
|---|---|
| CKL records, identities, source attestations | No NE7R3 commit or current worktree path changes under `framework/canonical_library`, CKL source objects/manifests, `bhf_agent/chapter_commentary`, `bhf_agent/data/asv_bible.json`, the frozen contract, or `.bhf-data`. The local SQLite file's byte hash was unchanged by this investigation. |
| Shared CKL provider from NE7R2 | `26938c76` introduced `bhf_web/services/ckl_provider.py`; the provider and its consumers have no NE7R3 diff. Its configuration remains read-only and its database verifier enforces integrity, foreign keys, and source identity. |
| SQLite integrity and foreign-key guarantees | `verify-db` passed in the current checkout and parent archive using its read-only connection; no database-builder, SQLite repository, schema, or migration file changed in NE7R3. |
| Tyndale Study Notes and `/api/commentary/*` | `bhf_web/routes/commentary.py` remains registered in `bhf_web/app.py` and still exposes `/api/commentary/diagnostics` and `/api/commentary/{book}/{chapter}`. The new retirement router only handles `/api/bhf-commentary/*` and generated-commentary coverage paths. Tyndale's separate `commentary_db_path` remains in runtime path resolution. |
| Translations, Notes, Highlights, Maps, Narrative Explorer | The corresponding source data and route/service modules have no NE7R3 diff. Narrative Explorer remains imported and registered, still receives the shared CKL provider, and its feature flag remains in runtime config. Translation comparison remains in the reader after removal of the generated BHF card. This is a source/diff inspection, not a full feature regression run. |
| `.bhf-data` and v1.1 authoring state | No `.bhf-data` paths are modified. The v1.1 pipeline state file's observed SHA-256 is `52d4e06976b7f0fbf8546eb816f33dd702b77237ea1a0de98743afb8698690d7`; this task did not invoke or advance the orchestrator. |
| v1.2 authoring and promotion inputs | The 974-file package copy under `bhf_agent/data/commentary-v1.2/` is being removed, but `.bhf-data/bhf-commentary-v1.2/` (974 files), its release attestations, candidate artifacts, and `bhf_agent/chapter_commentary/` remain. `tools/commentary_artifact_inventory.py:14–20, 120–122` identifies the `.bhf-data` release and validation trees as inputs to v1.2 promotion/reproducibility; the v1.1 publisher defaults to `commentary-v1.1` (`framework/commentary/publish.py:97–102`). No still-supported source tree was found to depend on the removed package duplicate after the web reader no longer selects it. |

The generated `docs/commentary-artifact-inventory.json` still reflects the pre-removal package tree; it is a recorded inventory snapshot, not a live source. It was not regenerated as part of this read-only diagnosis.

## Resolution

Keep the frozen tests and their expected value unchanged. The smallest safe next action is to locate the original `19c…` SQLite artifact in its approved backup/provenance store and reproduce these two checks against a read-only copy in isolation. Do not restore it over the current database: its historical attestation marks it stale against its source JSON inventory.

If the original artifact cannot be recovered and the v1.2 checks must be brought forward to the current CKL source, treat that as a separate, explicitly approved CKL source transition. The approval should define the new source identity and review any affected v1.2 evidence/provenance before changing a contract or database. Do not replace the expected SHA merely to make the tests pass. NE7R3 itself did not cause these failures; its existing retirement changes can be evaluated separately while this frozen baseline discrepancy remains documented.
