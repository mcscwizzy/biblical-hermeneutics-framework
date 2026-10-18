# NE7R3 Release Workflow Compatibility Migration

**Branch:** `refactor/narrative-explorer-ne7r3-commentary-retirement`

**Baseline HEAD:** `c4e1a7a00dd36d459b0f86088fab28fb864a7eac`

This migration changes CI compatibility only. It leaves CKL databases, source
inventories, attestations, frozen fingerprints, commentary release records, and
authoring state untouched.

## 1. Freeze workflow audit

Before this migration, `.github/workflows/commentary-v1.2-freeze.yml` was named
**Commentary v1.2 freeze**. It ran one job, `commentary-v1.2-freeze`, on
path-filtered `pull_request` events and matching pushes to `main`. Its path
filters included `.bhf-data/bhf-commentary-v1.2/**`, `bhf_agent/**`,
`framework/commentary/**`, `tools/commentary_v12_*.py`,
`tests/test_commentary_v12_*.py`, `docs/commentary-v1.2-release.json`, and
`pyproject.toml`.

The job's former contract was:

| Step | Contract and compatibility finding |
|---|---|
| Build deterministic CKL prerequisite | Ran `python -m framework.canonical_library build-db --output .bhf/ckl.sqlite`. This creates or replaces `.bhf/ckl.sqlite`; it is not read-only. |
| Verify frozen release | `tools/commentary_v12_freeze.py verify` checks the source release under `.bhf-data/bhf-commentary-v1.2/`, including its manifest, descriptor, chapter inventory, lineage fields, and checksums. This source release remains preserved. |
| Verify current source lineage | Runs the read-only `tools/commentary_v12_rebaseline_lineage.py verify` command against the v1.2 authoring inputs. |
| Run release-critical tests | Included `tests/test_commentary_v12_reader_integration.py`, which is absent at the migration baseline. The remaining listed tests cover historical authoring, source release, and promotion behavior. |
| Build and inspect installed wheel | Required `packaged_commentary_storage_path("commentary-v1.2")`, release diagnostics for 972 published / 1,189 validated / 217 unpublished chapters, and a readable Genesis 1 record from the duplicate package payload under `bhf_agent/data/commentary-v1.2/`. This is the direct retired-runtime dependency. |
| Detect source release mutation | `git diff --exit-code` protected `.bhf-data/bhf-commentary-v1.2/` and `docs/commentary-v1.2-release.json`. This is historical artifact preservation, distinct from runtime package acceptance. |

The historical `.bhf-data/bhf-commentary-v1.2/` source release is not the
retired duplicate package tree at `bhf_agent/data/commentary-v1.2/`. The source
release and its attestations remain intact and are checked in the separate
manual source verification path described below. Active PR validation checks
that the retired package tree is absent from built artifacts.

The old workflow emitted the status check
`Commentary v1.2 freeze / commentary-v1.2-freeze` when its path filters
matched. The repository contains no branch-protection configuration, so the
remote required-check setting could not be inspected here.

## 2. Historical CKL fingerprint and provenance

The frozen contract
`docs/commentary-v1.2-evidence-applicability-contract-freeze-v1.json` still
records the historical SHA-256
`19c66f931b6afe907bbef85ac29f34a3aefd288886d516c318e7965474ca2322` for the
bytes of `.bhf/ckl.sqlite`. The checked-out, current source-verified database
has byte SHA-256
`847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182` and
inventory fingerprint
`90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`.
Those values are different identities and have not been substituted for one
another.

The historical evidence census records that the `19c…` database was attested
on 2026-09-05 with 665 database objects against 679 source objects and
`matches_json_inventory: false`. The original SQLite binary is unavailable in
the repository checkout. The two frozen tests remain unchanged and still fail
against the available `847…` file with
`CensusError: protected contract fingerprint changed: ckl_database`:

- `tests/test_commentary_v12_five_chapter_structured_enrichment.py::test_frozen_contracts_are_unchanged`
- `tests/test_commentary_v12_post_applicability_coverage_census.py::test_contract_snapshot_keeps_protected_contracts_and_records_asv_repair`

These failures remain visible and unresolved. No frozen fingerprint, source
inventory, source attestation, shared CKL provider, or authoring-pipeline stage
was changed. The full historical database verification is not considered
successful when its original artifact is unavailable.

## 3. Minimal workflow migration

### Active PR contract

`.github/workflows/validate.yml` remains named **Validate**, runs on every pull
request and pushes to `master`, and keeps its existing `validate` job/status.
That job now adds:

- Python acceptance for retired generated Commentary and coverage endpoints,
  Tyndale route registration, Explorer configuration, Vercel packaging, CKL
  source manifest counts, and CKL release metadata.
- The focused frontend retirement test for the reader shell, Tyndale API/cache
  paths, translation comparison, and optional Explorer control.
- A wheel and source-distribution check that rejects any member whose path
  contains `bhf_agent/data/commentary-v1.2`. This check only asserts absence;
  it does not require the retired payload. The sdist member paths are
  normalized by removing their distribution-root directory before required
  files and forbidden paths are compared.
- The existing installed-wheel CKL source smoke test remains in place. It
  loads the JSON inventory and manifest and does not open or create a CKL
  SQLite database.

The active PR workflow no longer invokes the deleted reader integration test,
the removed v1.2 package loader, `build-db`, or any database-writing command.
The old `Commentary v1.2 freeze` status was not renamed to make a different
check appear equivalent; retirement acceptance runs under the existing
`Validate / validate` check.

### Manual historical source path

`.github/workflows/commentary-v1.2-freeze.yml` is now a manual
`workflow_dispatch` workflow named **Commentary v1.2 legacy source
verification**. It checks out immutable freeze commit
`f02122eed9642f173e2be3ad39ac5b979a23b898`, runs the source-only frozen release
verifier, and runs `tests/test_commentary_v12_freeze.py` against those same
immutable inputs. It contains no database build and does not claim to verify
the unavailable historical SQLite file. The source release check passing does
not turn the frozen `ckl_database` fingerprint check into a pass.

This workflow migration resolves the obsolete PR-triggered reader/package
gate described as outstanding in reports 03–05. Those reports record the
pre-migration findings; this report records the final workflow contract.

## 4. Read-only and preservation boundary

The active PR workflow does not access `.bhf/ckl.sqlite`, `.bhf-data/study.sqlite`,
or `.bhf/commentary.sqlite`. The pre-existing source-level CI checks validate
the CKL JSON inventory and manifest without SQLite writes. Locally, the current
CKL database was checked with the existing read-only `verify-db` command; its
SQLite integrity, foreign keys, and source inventory passed. The old workflow's
database build was not run.

Protected file hashes before and after migration work:

| File | SHA-256 |
|---|---|
| `.bhf/ckl.sqlite` | `847960c736f8a31ce9273b93344f6e559e2b978d86a0cbffd993ce07ebca6182` |
| `.bhf-data/study.sqlite` | `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf` |
| `.bhf/commentary.sqlite` | `2652edde56b22cf22628ced0da7dd81d7668c305ce17581a5a817aa97765e17f` |
| Commentary v1.1 `pipeline-state.json` | `52d4e06976b7f0fbf8546eb816f33dd702b77237ea1a0de98743afb8698690d7` |

No tracked differences were found under `.bhf-data/`, `framework/canonical_library/`,
`bhf_web/services/ckl_provider.py`, `bhf_agent/data/asv_bible.json`, or the
frozen contract JSON.

## 5. Verification results

Executed for this migration:

| Verification | Result |
|---|---|
| Focused Python set: retirement API, Explorer config, packaging, CKL manifest count, and CKL release tests | **15 passed** |
| `npm test` | **12 passed** |
| Wheel and sdist build to `/tmp`, followed by the workflow's required-file and retired-payload checks | **Build succeeded.** Wheel had 1,056 members; normalized sdist had 1,289. Required release files were present, and the retired payload was absent from both. The local build emitted existing setuptools license-metadata deprecation warnings. |
| YAML parsing, event/job/action-reference checks, and compilation of inline Python in both changed workflow files | **Passed.** Action references are `actions/checkout@v4`, `actions/setup-python@v5`, and `actions/setup-node@v4`. |
| Immutable source path at `f02122eed9642f173e2be3ad39ac5b979a23b898`: `tools/commentary_v12_freeze.py verify` and `tests/test_commentary_v12_freeze.py` | **Source verifier passed; 11 tests passed.** No CKL database was used. |
| Read-only local CKL `verify-db` | **Passed:** 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence records, inventory fingerprint `90fa…`. |
| Frozen CKL fingerprint tests listed above | **2 failed** with the documented `ckl_database` mismatch. The tests and expected fingerprint were not changed. |

The first test attempt used system Python, which lacks `fastapi` and `httpx`;
the same focused set passed under the repository `.venv`. The full repository
test suite was not run for this workflow-only migration.

The reported Firefox reader acceptance (9), real-data geography/offline
acceptance (5), and the broader 12-test frontend run were already recorded in
NE7R3 report 04. The browser tests were not rerun for this workflow-only
migration. The complete legacy workflow was not run because its previous
version rebuilt `.bhf/ckl.sqlite` and required the retired package.

## 6. Required GitHub branch-protection update

If branch protection currently requires
`Commentary v1.2 freeze / commentary-v1.2-freeze`, remove that requirement; the
workflow no longer runs for pull requests. Require or retain
`Validate / validate`, which now carries the retirement acceptance and package
absence checks on every pull request. Preserve any unrelated required checks.
The live GitHub branch-protection settings were not available in this
repository, so this administrative change remains to be confirmed before
merge.

## Recommendation

The complete NE7R3 branch is safe to commit and submit for review after this
report is reviewed. It is not ready to merge until the required-check setting
is confirmed and the review acknowledges that the historical `19c…` CKL
fingerprint remains unresolved. This migration does not certify the missing
historical database or make either frozen fingerprint test pass.
