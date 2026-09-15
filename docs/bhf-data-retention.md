# BHF `.bhf-data` retention policy

Post-freeze cleanup date: 2026-09-15

This document records why the remaining `.bhf-data` namespaces exist. The
frozen Commentary v1.2 release is authoritative for packaged v1.2 behavior;
candidate data is retained only where current verification, lineage, tests, or
operator workflows still consume it.

## Retained namespaces

| Path | Purpose | Retention reason | Referenced by | Safe to delete |
|---|---|---|---|---|
| `.bhf-data/bhf-commentary-v1.2` | Frozen v1.2 release payload, manifest, and checksums | Release verification and runtime release loading | `tools/commentary_v12_freeze.py`, package/runtime checks | No |
| `.bhf-data/bhf-commentary-v1.1` | Legacy runtime-compatible release | Existing v1.1 runtime and compatibility coverage | runtime paths and v1.1 tests | No |
| `.bhf-data/bhf-commentary` | Default/legacy commentary store | Existing runtime and tests | commentary repository/runtime tests | No |
| `.bhf-data/bhf-commentary-production` | Historical production reconciliation data | Production audit and compatibility workflows | production reconciliation/tests | No |
| `.bhf-data/bhf-commentary-v1.2-enrichment` | Active v1.2 canary, audits, and finalized corpus-runner evidence | Current corpus reconciliation, canary contracts, and release-promotion tests | v1.2 runner/release tools and tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-current-source-lineage-v2` | Current source-lineage baseline | `CURRENT_LINEAGE_VALID` verification and ancestry/provenance inputs | `framework/commentary/v12_current_lineage.py` and lineage tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-terra-75-scale-validation-v1-e8af58131e066def98a2` | Frozen historical 75-chapter validation source | Release promotion and historical validation contract | release promotion tools/tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-provenance-binding-v1-f139d722270544978d04` | Frozen provenance-binding validation source | v1.2 output-conformance and provenance audit chain | validation tools/tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-922472547555015a3ced` | Historical scale-pilot source and contract | Current lineage inputs and scale-pilot provenance tests | lineage/scale-pilot tools/tests | No |
| `.bhf-data/bhf-commentary-candidates/renderer-qualification-v2-prompt-1.6-gpt-5.6-sol-15f2be7cfcc60bb5ea31` | Historical renderer qualification input | Current lineage and qualification tests use its source records | qualification and lineage tools/tests | No |
| `.bhf-data/bhf-commentary-candidates/reader-level-idea-projection-v1-seven-chapter-e01fcbe6fe39ba6949fc` | Seven-chapter reader projection source | Ancestry-envelope and unified reader projection tests use it | reader projection tools/tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-reader-provenance-binding-v2-bounded-validation-v1-023f67f998ec3f853936` | Reader provenance bounded-validation fixture | Reader provenance tests use it | reader provenance tests | No |
| `.bhf-data/bhf-commentary-candidates/reader-projection-ancestry-envelope-seven-chapter-ee44d0e3507b66a10aab` | Unified reader ancestry fixture | Unified reader tests use it | reader integration tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-output-conformance-v1-d278cba2d2151d1b4242` | Retained output-conformance diagnostic | Deterministic checksum regression test reads it | `tests/test_commentary_output_conformance.py` | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-five-chapter-structured-enrichment-v1-22e32598` | Five-chapter structured enrichment artifact | Release-critical tests and CKL structured-claim tests load it directly | v1.2 enrichment and CKL tests | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary` | Canary prompts, accepted responses, synthesis, gates, preflight, import, comparison, and audits | Canary reproducibility and contract tests | canary tests/tools | No |
| `.bhf-data/bhf-commentary-candidates/commentary-v1.1-scale` and `.bhf-data/bhf-commentary-candidates/commentary-v1.1-terra` | v1.1 generation state and certified historical inputs | v1.1 pipeline/operator instructions, tests, and reproducibility | v1.1 tools/tests | No |
| `.bhf-data/jobs.sqlite`, `.bhf-data/lexicon.sqlite`, `.bhf-data/study.sqlite`, `.bhf-data/translations` | Local runtime/build data | Runtime and local package/database workflows | Docker/runtime configuration | No |

Other candidate namespaces remain when current tools, tests, or documented
qualification workflows reference their source contracts. A namespace is not
deleted merely because it is historical.

## Cleanup performed

The deleted set was generated as `/tmp/bhf-data-post-v1-2-delete-set.json`
with one record per file containing its path, size, classification, reason,
and dependency-scan result. The guarded set contained 3,046 files and
43,239,735 bytes. It removed 185 empty directories, including two of the 17
corpus-runner sessions.

Removed categories:

- `UNREFERENCED`: four historical candidate namespaces with no active consumer
- `OBSOLETE_GENERATION_INTERMEDIATE`: two incomplete/superseded runner sessions and rejected canary staging
- `HISTORICAL_REPRODUCIBILITY_ONLY`: runner prompt bodies and canary raw/retry responses
- `DUPLICATE`: optional runner receipts and the accidental nested raw-response copy
- `SCRATCH_OR_TEMP`: canary manual-render staging

The five-chapter structured-enrichment namespace was explicitly retained after
dependency tracing showed that release-critical tests load it.

## Frozen identity and status contract

The reported terminal-state hash
`91df96a0a79571978a7839a29f9c3b22a2fc73dfce52890e27d52a4a087dc0cf` is
`TERMINAL_IDENTITY_NOTE_ONLY`: it has no persisted release field or canonical
derivation. It is not a cleanup gate. Terminal statuses are protected by the
frozen manifest’s canonical identity, which includes all 1,189 chapter rows
and their release states, plus `terminal_state_counts`.

The actual frozen gates remain:

- tag target `f02122eed9642f173e2be3ad39ac5b979a23b898`
- manifest file SHA-256 `aad968530b371ac05de3529c3f0ac0a59afebc66bfaa21c2fcf4ca6306684c5b`
- artifact root `ae31de2fe50c0435387995dd4110579ff2b68ae9f59f9dd1b9f5afc55cb785eb`
- chapter inventory `17c2ecd7eb2ee519b9dce332eb370d97cea42ce75fa0eb5537729c424f4990ae`
- counts 1,189 canonical, 972 published, 185 source-limited, 26 model-rejected, 6 quality-review, 0 missing
- current source lineage status `CURRENT_LINEAGE_VALID`

## Future disposable categories

After dependency scans, future cleanup may remove incomplete runner sessions,
prompt bodies, optional receipts, raw retry staging, rejected/manual-render
scratch, exact duplicate copies, and unreferenced diagnostic roots. Unknown
paths, frozen release data, current-lineage baselines, finalized runner
evidence, package data, runtime stores, and test fixtures remain until an
explicit dependency audit proves otherwise.

No `.gitignore` broadening was made. `.bhf-data` remains visible to release and
development audits.

## Post-cleanup verification

The cleanup was performed without commentary generation or provider calls.
After deletion:

- `.bhf-data`: 16,969 files, 3,220 directories, 618,444,983 bytes
- reduction: 3,046 files, 185 directories, 43,239,735 bytes (6.5348%)
- corpus-runner: 15 sessions, 31,409,526 bytes; two incomplete/superseded
  sessions removed, for 41,256,630 bytes removed

The following checks passed after deletion:

- frozen release verifier: `COMMENTARY_V1_2_FROZEN_READY`
- release inventory: `RECONCILIATION_PASS`
- source lineage: `CURRENT_LINEAGE_VALID`
- release-critical deterministic suite: 179 passed
- retained structured-enrichment/CKL suite: 5 passed
- installed wheel smoke test: checksum-valid packaged v1.2 release with 1,189
  manifest entries and counts 972/185/26/6

The package smoke test resolved Commentary v1.2 from installed
`bhf_agent/data/commentary-v1.2`; it did not require a development or
candidate `.bhf-data` path. The isolated PEP 517 bootstrap could not reach an
external package index in this environment, so the same wheel was built with
the provisioned system build toolchain and installed with dependencies
disabled into a temporary environment.
