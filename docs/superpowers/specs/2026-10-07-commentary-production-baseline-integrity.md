# Commentary production baseline integrity maintenance

This maintenance starts from Transaction C merge `4847b516` and preserves its
published release and promoted chapter artifacts. It addresses three failures
reproduced from a clean Git archive of that master.

## Baseline failures and repairs

1. **Census test isolation.**
   `tests/test_commentary_production.py::test_census_is_canonical_and_does_not_promote_historical_artifacts`
   expected zero completed records but `build_census(Path("."))` found the 16
   `COMPLETE` records in the tracked run (and nine `QUARANTINED`). This was a
   unit-test fixture problem: the test accidentally used repository production
   state. `build_census` now accepts an explicit `production_data_root`; the
   test points it at an empty temporary root while preserving the repository
   root for historical experiment inventory. A regression assertion confirms
   the checked-in run cannot leak into this isolated census. Tracked run history
   is unchanged.

2. **Exodus 14 historical identity.**
   The frozen run manifest and packet under
   `.bhf-data/bhf-commentary-production/v1/runs/run-04109d5ff664ed80/` record
   packet `0de82498c76c923d6dbdb5825b6fe64842654a49e0977d33ed248e8cd7d1b73e`
   and synthesis
   `1059b0c617109751eb944cc9b22b2d8e83233f720d258561449c4624f8c2b2db`.
   Current deterministic preparation produces packet
   `d2fcf9bbe1d8913bdbde08ebcc90368e837b13866dc0b4dab0a9da7f2817ce7b` and
   synthesis
   `01eefc01d0511fc67457a4c32c195e9e84c76ff670145324f7ce5a0453df1072`.
   Both retain evidence hash
   `a8b53c334b69629f2bbb0ea1ecdafc21ae687a26f7c59ce2d965de9b06058380` and
   validator identity
   `bhf_agent.chapter_commentary.validation:validate_chapter_commentary:sha256:b4bbb3ce24a2d84c3c026138626e2b8c7337d8fe029db31da5a6c28bed2880f2`.
   The canary packet was recorded on 2026-09-08; current synthesis applies the
   evidence-applicability enforcement introduced on 2026-09-10. The same 45-item
   bundle now compiles to six eligible synthesis units rather than the
   historical 34. Synthesis hash and packet hash change because the synthesis
   payload, density, and prompt inputs change; evidence bundle and validator
   identity do not. This is historical provenance, not a stale current-lineage
   fixture. The run manifest and packet remain immutable. A regression test
   names both identities and requires equality only for evidence and validator
   identity, while making the synthesis and packet divergence explicit.

3. **2 Kings 11 replay collision.**
   The historical gate at
   `.../gate/attempt-001/2_kings_011.json` has SHA-256
   `92339443c04655c608ea1c1efce8257b4682dd0f8ab313a6384aa0039e4ebf8d`.
   The reprocess test copied the post-adjudication production run, changed only
   the chapter state back to `QUARANTINED`, and left the accepted and gate
   artifacts at their immutable attempt-001 paths. Re-evaluation therefore
   tried to write current scoring/schema output over the historical gate. The
   immutability check correctly rejected different bytes. Explicit derived
   replay now keeps that historical path intact and stores changed current
   output under `gate/replay-v2/attempt-001/`, with artifact version and lineage
   metadata linking the historical path. Normal production writes still fail
   closed on immutable collisions. Regression coverage checks both the old
   file hash and the distinct replay artifact.

## Verification record

Baseline clean-archive command:

```text
pytest -q tests/test_commentary_production.py tests/test_commentary_production_data_gap_adjudication.py tests/test_commentary_v12_current_lineage.py
```

It produced three failures: the census assertion `assert 16 == 0`; data-gap
reader reconciliation raised `PRODUCTION_PREFLIGHT_FAILED: input identity
mismatch for Exodus 14` because it prepared every manifest chapter although it
only reconciles application-owned data-gap records; and raw reprocessing raised
`ArtifactCollisionError: immutable artifact collision` at the 2 Kings 11
attempt-001 gate path. Reconciliation now filters for the explicit
application-owned fallback record before reconstructing inputs, then validates
the true data-gap conditions from prepared inputs.

The added and updated regressions cover isolated census roots, unrelated
historical inputs during targeted reconciliation, old-versus-current Exodus 14
identity, and immutable gate replay lineage. Verification results:

- Focused new regressions: 4 passed.
- Production, data-gap, handoff, and runtime files: 40 passed.
- Exact broader baseline command above: 26 passed; all three baseline failures
  are resolved.
- Corpus-runner, current-lineage, frozen-release, release-promotion, and
  Transaction C selective-promotion tests: 60 passed.
- Reader integration and BHF projection smoke tests: 15 passed.
- Corpus-runner, frozen-release, release-promotion, Transaction C promotion,
  and reader-related batch: 92 passed, 13 failed. The 13 failures are limited
  to the seven-chapter projection diagnostics, which stop at the pre-existing
  frozen Isaiah 13 source-packet mismatch. A representative test reproduces
  the same `source packet identity changed for Isaiah 13` failure from a clean
  archive of `4847b516`; no source or release files for that diagnostic were
  changed here.
- `git diff --check` passed.

The full release tree and its 12 promoted chapter files were hashed before and
after the maintenance edits. The release tree remains
`2aa8c39e26528136d7242e5fe96d99ac59328f21161907d00ad4fbe7e76bce57`; its
manifest, package checksum root, descriptor, approval manifest, and controls
remain at their protected identities. The tracked historical run, Exodus
packet, and 2 Kings 11 attempt-001 gate remain byte-identical. No CKL geography
path was changed.
