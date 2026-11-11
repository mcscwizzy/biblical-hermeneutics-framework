# Current-state NE-9C and NE-10 compatibility

## Which validator to use

The historical command
`python scripts/ne9c_bulk_curation.py validate` checks a frozen relationship
inventory against the CKL object-tree fingerprint recorded in
`docs/narrative-explorer/ne9c-bulk-curation/checkpoint.json`. Use it with the
CKL snapshot from which that checkpoint was created. Its rejection against a
later CKL is intentional; do not regenerate or relax the checkpoint to make
that command accept new object data.

The read-only current-state validator is:

```bash
.venv/bin/python tools/validate_ne9c_current_compatibility.py
```

It runs in CI and accepts ordinary changes to CKL fields/evidence when the
reviewed relationship identities and protected curation artifacts remain
compatible. It does not replace or change the historical validator. It reports
the frozen and current object-tree hashes separately, and a historical hash
mismatch is informational for this current-state check.

## Checks enforced

- Exact SHA-256 values for the historical checkpoint and decision ledger, the
  complete NE-9C runtime curation directory, and both NE-10 registries.
- Each historical wave file against the wave hash recorded in the pinned
  checkpoint, with unique identities and the expected completed review set.
- All 4,061 currently authored object relationship IDs against the protected
  identity-set digest. Every one of the 3,925 reviewed decisions must resolve
  to the same current authored relationship identity and exact wave row.
- The 408 curated, 1,895 held, and 1,622 excluded decisions. Runtime object
  curations must equal the 23 initial accepted relationships plus the 408
  curated review decisions. Held and excluded decisions cannot appear as
  runtime curations.
- Runtime curation schema, source/record provenance, and correspondence between
  each curated decision and its version-controlled runtime payload. Machine
  review entries must continue to say that human scholarly approval was not
  recorded.
- All 44 NE-10 verified bridges against their exact current CKL record and
  source IDs, and all seven NE-10 held candidates with the held/excluded status.

Any changed protected artifact hash, identity, disposition, or bridge support
fails the command. The validator has no write path: it reads the frozen data,
the runtime registries, and current CKL records only.

## Phase 4 result

The historical checkpoint remains at SHA-256
`0f8e4f690bd701be2856fc5af1a304f864163f7a8adc896b760d0c95b349c6f9`; the
review ledger remains at
`5aefd69b89c69f0d941babbd5ea4f7e8fbb5c8065907cfeab1025c2f1fd41826`. The
NE-9C runtime registry tree hash is
`623acf40bc03c9689387164679802716dec7436aec8baec0ba8d791b45171676`.
NE-10 bridge and held-registry hashes remain the baseline values
`8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b` and
`15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3`.

At the end of the CKL changes, the current object-tree hash is
`da9af6550b144dd8df50c99e7448e72aa154396370bb83a827eadf27e96075ff`, while
the frozen checkpoint records
`e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`. The
new current-state check passes with `historical_ckl_fingerprint_matches=false`;
it has neither rewritten the checkpoint nor treated the two fingerprints as
equal.
