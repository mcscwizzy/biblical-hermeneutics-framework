# NE7R3 runtime package reduction

## Result

The compiled BHF Commentary v1.2 package payload is absent from the current
wheel and source distribution. The packaged removal is measurable. Tyndale
Study Notes, its SQLite store, the CKL sources, and the Commentary authoring
and release tools remain present.

The application runtime no longer selects the removed package. However, the
existing pull request workflow `commentary-v1.2-freeze.yml` still explicitly
requires that package in its installed-wheel smoke check and names a reader
integration test removed by this retirement. The package retirement therefore
does not satisfy the current release workflow. This report records a release
gate requiring maintainer approval before the work can be committed.

## Package measurements

The baseline is a clean archive of `c4e1a7a00dd36d459b0f86088fab28fb864a7eac`
(the NE7R3 pre-Task-3 tree). The current snapshot is that archive with the
uncommitted Task 3 diff applied. Both were built and installed in `/tmp` with
Python 3.12.3, `python -m build --wheel --no-isolation`, and pip without
dependencies. SQLite payloads were not included in these measurements.

| Measure | Pre-Task-3 `c4e1a7a0` | Current NE7R3 | Change |
|---|---:|---:|---:|
| Compressed wheel | 49,464,200 B | 47,897,472 B | −1,566,728 B (−3.17%) |
| Installed package, no bytecode | 77,661,275 B | 74,038,739 B | −3,622,536 B |
| Installed package, default bytecode | 82,150,272 B | 78,526,955 B | −3,623,317 B |
| Installed files, no bytecode | 2,035 | 1,061 | −974 |
| v1.2 packaged files | 974 | 0 | −974 |

The removed v1.2 package tree accounted for 3,519,570 source bytes. A current
source distribution was 46,945,990 B with 1,290 members; it contained no
`bhf_agent/data/commentary-v1.2` members and retained
`bhf_agent/chapter_commentary/storage.py`.

The `.vercelignore` source estimate, calculated from tracked files and the
ignore patterns, was 80,052,181 B / 2,304 included files at the baseline and
74,182,913 B / 1,200 included files currently (−5,869,268 B). This is a
static estimate, not Vercel CLI staging output or a hosted function bundle
measurement. No hosted deployment or function-size claim is made.

The earlier NE7R2 report measured a 49,502,734 B wheel and an 82,423,044 B
installed target. The exact pre-Task-3 archive comparison above controls for
the NE7R3 source and build environment and is the primary comparison here.

## Runtime and source preservation

- The removed payload is the duplicate compiled reader copy under
  `bhf_agent/data/commentary-v1.2/`. NE7R3 removes the web runtime release
  selector and generated BHF reader loading path.
- The source release under `.bhf-data/bhf-commentary-v1.2/` remains intact:
  974 files, including its release descriptor and checksum manifest. The
  candidate/provenance trees and `bhf_agent/chapter_commentary/` remain.
- `framework.commentary` publishing, validation, and authoring modules remain.
  The reader's SQLite-backed Tyndale service and `BHF_COMMENTARY_DB_PATH`
  configuration remain separate from the removed compiled release selector.
- `.bhf-data`, `framework/canonical_library`, the shared CKL provider, and the
  v1.1 authoring pipeline state are unchanged from NE7R2. Protected database
  hashes and read-only integrity results are recorded in
  [04-reader-regression-results.md](04-reader-regression-results.md).

## Existing release workflow conflict

`.github/workflows/commentary-v1.2-freeze.yml` runs on pull requests changing
`bhf_agent/**` or `pyproject.toml` (lines 4–12). This retirement changes both.
The workflow then:

1. names `tests/test_commentary_v12_reader_integration.py` in its explicit
   release-critical pytest command (line 51); that reader integration test is
   removed as part of retirement; and
2. builds an installed wheel and asserts that
   `packaged_commentary_storage_path("commentary-v1.2")` exists, its release
   checksum is valid, and `load_commentary(root, "Genesis", 1)` returns data
   (lines 68–89). The retired package is absent by design, so that assertion
   no longer describes the runtime contract.

The workflow was inspected but not run. Its earlier step rebuilds
`.bhf/ckl.sqlite` (line 38), which would regenerate a protected database and is
outside this task's authorization. The two frozen fingerprint tests were run
separately and their identical pre-existing failures are documented in
[02-ckl-fingerprint-investigation.md](02-ckl-fingerprint-investigation.md).

## Resolution required before commit

Request maintainer/release approval to align the v1.2 freeze workflow with the
retired reader package: remove the stale reader-test reference and replace the
installed runtime-package assertion with checks against the still-authoritative
source release and its provenance. Keep the frozen CKL fingerprints, CKL
integrity checks, source attestations, and promotion-contract checks unchanged.
Do not merge NE7R3 until the updated release gate is approved and passes in an
isolated CI environment.
