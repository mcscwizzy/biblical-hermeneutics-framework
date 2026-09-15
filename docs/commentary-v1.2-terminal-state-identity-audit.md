# Commentary v1.2 terminal-state identity audit

Date: 2026-09-15

## Classification

`TERMINAL_IDENTITY_NOTE_ONLY`

Reported value:

`91df96a0a79571978a7839a29f9c3b22a2fc73dfce52890e27d52a4a087dc0cf`

The value is not an authoritative frozen-release identity. A complete search
of the working tree, ignored files, reachable Git history, frozen tag, release
descriptor, release manifest, checksum index, release builder, release
verifier, lineage verifier, tests, CI, and `.bhf-data` found no persisted field
or canonical derivation for it. Its only occurrences are the cleanup task and
the audit notes created while investigating the blocker.

## Actual frozen contract

The frozen release verifier independently verifies:

- tag target: `f02122eed9642f173e2be3ad39ac5b979a23b898`
- release manifest file SHA-256: `aad968530b371ac05de3529c3f0ac0a59afebc66bfaa21c2fcf4ca6306684c5b`
- artifact/checksum root identity: `ae31de2fe50c0435387995dd4110579ff2b68ae9f59f9dd1b9f5afc55cb785eb`
- chapter inventory identity: `17c2ecd7eb2ee519b9dce332eb370d97cea42ce75fa0eb5537729c424f4990ae`
- canonical chapter count: 1,189
- terminal-state counts: 972 `PUBLISHED`, 185 `NOT_RENDERABLE_SOURCE_LIMITED`, 26 `MODEL_OUTPUT_REJECTED`, and 6 `QUALITY_REVIEW_REQUIRED`
- missing chapters: 0; duplicate identities: 0; orphan artifacts: 0; checksum conflicts: 0

The authoritative release manifest contains all 1,189 canonical chapter rows,
each with its release state, and contains `terminal_state_counts`. Its
canonical unsigned JSON identity is `1c8972058420f00c2c9f05f52e7924566bf9fb3f56547d16c4c8b9f1f48b65d7`.
The checksum index binds the manifest file and the descriptor binds the
manifest SHA-256 and checksum-root identity.

## Derivation experiment

The existing canonical JSON serialization was used only to inspect existing
contract behavior, not to manufacture a replacement identity. A status-only
projection of `(reference, release_state)` rows produced
`43c2ebd2cc8fabaaf6bb408c5576e9a2843fb1f6ab166f1eca1e0da0bf4a2c91`, which
does not equal the reported value and is not persisted anywhere. Changing one
chapter status in an in-memory copy changed the authoritative manifest digest.
Therefore the old value is not classified as derivable or redundant as a
known digest; it is classified as note-only, while the manifest is the actual
cryptographic status protection.

## Verification commands

~~~
.venv/bin/python tools/commentary_v12_freeze.py verify
.venv/bin/python tools/commentary_v12_release.py inventory
.venv/bin/python tools/commentary_v12_rebaseline_lineage.py verify
~~~

The cleanup gate no longer requires the unproven note-only value. It protects
the frozen tag, manifest file identity, checksum-root identity, chapter
inventory identity, verified terminal counts, current source lineage, and the
existing ancestry/provenance/package checks.

No new status digest was added; the existing manifest contract already binds
the status semantics and a new digest would add no needed protection.
