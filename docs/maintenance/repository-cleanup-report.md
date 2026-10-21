# Repository modernization report

## Scope and baseline

- Repository: `mcscwizzy/biblical-hermeneutics-framework`.
- Confirmed prerequisite: NE-10 was merged on `origin/master` at
  `4260e1efdac3d2795b8599b22d837cbb8267e74d`.
- Working branch: `chore/bhf-repository-modernization`, created in a separate
  clean worktree from that commit. The original checkout's pre-existing
  untracked `.vercel/` directory was left untouched.
- Starting tree: 19,993 tracked files and 661,068,202 tracked content bytes
  (630.44 MiB). `.bhf-data` held 18,021 files and 500,678,989 bytes
  (477.48 MiB). The relationship inventory CSV was 53,638,723 bytes.
- At baseline, Git stored 4,308 loose objects (47.31 MiB) and 34,995 packed
  objects (91.50 MiB). This cleanup does not rewrite history, so deleted blobs
  remain reachable from earlier commits.
- Baseline checks: `python3 tools/validate.py framework/` passed for 94
  modules; frontend tests passed 12/12; focused active CI tests passed 17/17.
  The initial full `pytest -q` run lost its terminal session before a summary
  and is inconclusive.

The complete path-level classification and its decision bases are in
[`repository-cleanup-inventory.csv`](repository-cleanup-inventory.csv), with
the dependency and retention assessment in
[`repository-cleanup-preflight.md`](repository-cleanup-preflight.md). The
inventory classifies every path from the starting tree. It records 1,839 KEEP,
17,930 RETIRE, 87 CONSOLIDATE, 9 HISTORICAL, and 128 INVESTIGATE paths.

## Retired paths and size change

| Classification | Starting paths removed from their old locations | Starting bytes at those paths |
|---|---:|---:|
| RETIRE | 17,930 | 527,990,152 |
| CONSOLIDATE | 87 | 845,239 |
| HISTORICAL | 1 | 52,948 |
| **Total** | **18,018** | **528,888,339** |

The two renamed tests in CONSOLIDATE were retained under current names:
`tests/test_commentary.py` became `tests/test_tyndale_study_notes.py`, and
`tests/test_ckl_commentary_v12_structured_claims.py` became
`tests/test_ckl_structured_claims.py`. Thus old-path bytes are not the same as
net content bytes removed. Several consolidated docs and audits were replaced
by maintained references and the historical index.

The derived current tree contains 289 tracked `.bhf-data` files totaling
29,414,982 bytes. Those are retained CKL and Narrative Explorer provenance
artifacts, not generated reader prose. The 53,638,723-byte relationship CSV was
removed after exact deterministic regeneration from protected CKL inputs:

```bash
python scripts/audit_ckl_connection_coverage.py \
  --output /tmp/ne9a-relationship-inventory.csv
sha256sum /tmp/ne9a-relationship-inventory.csv
wc -l /tmp/ne9a-relationship-inventory.csv
```

The regenerated file had 53,097 data rows, 53,638,723 bytes, and SHA-256
`b03b5ce267e415b997e6d1cfbe8fe69049731b3a4b10262f1e77d8e395aedef4`. Its
source identity was checked against the unchanged 687-object CKL and canonical
inventory fingerprint below.

## Retention decisions

- CKL source objects, schema, manifest, licenses, source locks, and research
  decisions remain byte-for-byte unchanged: 687 objects; canonical fingerprint
  `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`;
  manifest SHA-256
  `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4`;
  CKL object-tree SHA-256
  `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`.
- NE-9C and NE-10 curation registries, held candidates, relationship evidence,
  acceptance reports, uncertainty, and provenance stay in the tree. Protected
  path comparisons against `origin/master` found no changes to CKL objects or
  the NE-9C/NE-10 registries.
- Genesis G0–G6C evidence roots and the Genesis 1 corrective attestation remain
  because they establish research decisions and reproducibility. Their historic
  `bhf-commentary-candidates` directory names are provenance identifiers; the
  files are not generated prose.
- The Tyndale Open Study Notes schema, importer, service, routes, reader assets,
  attribution, CLI evidence provider, and pinned archive build remain active.
  Stable generated BHF Commentary URLs still return HTTP 410.
- Immutable release identities remain in Git history and the v1.0, v1.0.1,
  v1.1, and v1.2 tags. The frozen v1.2 workflow remains pinned to
  `f02122eed9642f173e2be3ad39ac5b979a23b898`; its inputs are available from
  that immutable commit, so its historical source tree does not need to be
  restored on current master.
- The 128-file Sol qualification handoff subtree (1,884,084 bytes) and its
  export workflow remain INVESTIGATE. The remote branch state could not be
  verified from this environment, so those files were retained.
- The required Bible data, lexical sources and compressed asset, translations,
  maps, archaeology resources, study records, PWA resources, and licenses remain.

Historical decision references include NE7R3 merge `551a998f`, NE9C acceptance
`0e88d104` and merge `c3aba86e`, and NE-10 acceptance `21880d8c` and merge
`4260e1ef`. See
[`historical-decisions.md`](historical-decisions.md) for full commit and tag
identities.

## Source, documentation, and packaging changes

- Removed the retired generated BHF Commentary reader/generator modules,
  release payloads, generation-only tools and tests, obsolete local pipeline
  state, and generation CI references. Removed unused `selective_recompile`
  plumbing and decoupled current CKL coverage reporting from generator
  availability.
- Kept the shared `framework.commentary` package because Tyndale uses it.
  Updated package discovery and manifests to keep the Tyndale service, schema,
  SQLite resource when built, and current CLI. Added regression checks for
  retired 410 routes and to prevent retired generation code from re-entering
  the wheel or Vercel bundle.
- Kept `Validate` and strengthened its package-resource checks for CKL, NE-9C,
  NE-10, Tyndale, and retirement boundaries. Updated `.gitignore`,
  `.dockerignore`, `.vercelignore`, `MANIFEST.in`, `pyproject.toml`, and
  `vercel.json` to exclude obsolete research output from normal packaging while
  allowlisting required provenance and runtime resources.
- Rewrote `AGENTS.md`, the root and docs indexes, architecture, local
  development, Docker, PWA, CKL, data-retention, handoff, and tools docs.
  Added current Narrative Explorer references and a short historical decision
  index. The docs keep CKL methodology and hermeneutical classification history
  available without treating retired Commentary generation as current runtime.
- The frozen geography pilot source lock and candidate JSON were not edited.
  The maintained dry-run tool no longer emits a retired Commentary preview
  field. No CKL scholarly content was changed.

After the build hook generated the Tyndale database, the wheel contained 1,050
files (52,237,833 bytes) and the source distribution 1,230 files
(51,177,541 bytes). Both contained the required CKL manifest and objects,
NE-9C/NE-10 registries, Narrative Explorer assets, the 22,499,328-byte Tyndale
database, its runtime modules and route, and the stable 410 route. Neither
contained retired generation payloads. An installed-wheel smoke loaded the
687-object CKL at the expected fingerprint and confirmed the packaged Tyndale
database healthy with 17,478 entries. The Vercel function configuration
excludes `.bhf-data` and includes the CKL source tree and built Tyndale SQLite
resource.

## Verification

- `python3 tools/validate.py framework/`: PASS, 94 modules.
- `node --test tests/frontend/*.test.js`: PASS, 12 tests.
- Retirement, Tyndale, packaging, CKL structured claim, NE-9C, NE-10,
  Narrative Explorer, passage, projection, coverage, geography, and ASV checks
  were run. Detailed results and unchanged-fixture failures are recorded below.
- Wheel and sdist build: PASS using the system setuptools/wheel in offline
  `--no-isolation` mode. Default isolated build could not fetch build
  requirements because sandbox DNS is unavailable.
- Wheel/sdist resource audit and installed-wheel smoke: PASS.
- Docker image build and basic startup: PASS. The image built, its CKL database
  verified, its pinned Tyndale archive qualified, and its 14,197-entry lexical
  database passed both Word Study smoke checks. A temporary container returned
  `{"service":"bhf-web","status":"ok"}` from `/api/health`. Docker Compose
  v2 is not installed in this environment, so Compose examples could not be
  executed here.
- Vercel CLI is not installed. The actual local Vercel build hook passed with
  network access: it built and verified the packaged 687-object CKL index, then
  downloaded the pinned Tyndale archive, verified its SHA-256, and generated a
  healthy 17,478-entry database (22,499,328 bytes) at the exact configured
  function resource path. The generated SQLite file was removed after the
  packaging check; `vercel.json` explicitly includes that path.
- Markdown local-link scan: PASS, 294 Markdown files scanned with no missing
  local links. Maintained command examples were reviewed; CKL and lexical CLI
  help, the ASV audit command, source validator, frontend tests, and Docker
  build/start commands were exercised.

Focused regression outcomes:

- Retirement, Tyndale, packaging, CKL structured claims, and manifest/release
  checks: 54 passed, 1 failed on the unchanged CKL governance fixture described
  below. The separate current retirement/package regression rerun passed 10/10.
- Narrative Explorer API, passage navigation, projection, coverage, NE-9C,
  geography, and ASV checks: 592 passed, 10 failed in stale geography-pilot
  snapshot assertions described below.
- Archaeology, maps, Bible, notes, translations, lexical engine, and offline
  runtime checks: 145 passed, 1 skipped, 18 subtests passed, 2 failed on the
  unchanged archaeology fixtures described below.
- The baseline full `pytest -q` attempt lost its terminal session before a
  summary; it is inconclusive and is not reported as passing.

The following unchanged upstream fixtures/data still fail focused tests and
were not altered to obtain a green result:

- Canonical inventory governance expects a `generated_by` default on an
  `in_review` CKL object whose field is empty.
- Ten geography-pilot snapshot assertions expect prior pilot candidates and
  hashes, while the authoritative CKL already contains their applied changes.
- The archaeology corpus coverage fixture has one media record that is not both
  redistributable and cacheable; the archaeology seed fixture also has a site
  with an empty source ID.

The CKL source objects/manifest and archaeology seed involved are unchanged
from `origin/master`; the failing fixture assertions remain unchanged. Some
nearby tests were updated to remove retired Commentary expectations, but none
were deleted or weakened to mask these failures.

## Size at closeout, remaining work, and branch

| Measure | Starting tree | Final tree |
|---|---:|---:|
| Tracked files | 19,993 | 1,985 |
| Tracked content bytes | 661,068,202 | 134,673,545 |
| Tracked `.bhf-data` files | 18,021 | 289 |
| Tracked `.bhf-data` bytes | 500,678,989 | 29,414,982 |

Remaining cleanup opportunities are the retained Sol handoff investigation,
stale geography-pilot expectations, and the pre-existing CKL/archaeology
fixture disagreements. Historical Git objects account for much of the
repository's remaining object-store size; reducing that size would require a
separately authorized history rewrite and was not performed.

- Branch: `chore/bhf-repository-modernization`.
- Cleanup implementation commit: `cf11f7f0505cd51feeb0ca958bee603a0308340d`.
  This report is the following report-only commit; the final branch tip is
  recorded in the delivery summary.
- No merge, deployment, production environment change, or history rewrite was
  performed.
