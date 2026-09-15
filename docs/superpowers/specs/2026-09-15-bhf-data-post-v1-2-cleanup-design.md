# BHF `.bhf-data` post-v1.2 cleanup design

Date: 2026-09-15

## Objective

Prune proven-obsolete Commentary v1.2 generation residue after the frozen
release while preserving every artifact needed by the frozen release,
runtime, package, verification, tests, current source lineage, ancestry, and
provenance contracts.

No commentary generation, provider call, CKL mutation, release mutation, or
lineage rebaseline is permitted.

## Frozen invariants

The following must remain byte-for-byte and identity-for-identity unchanged:

- tag `commentary-v1.2` peeled target
  `f02122eed9642f173e2be3ad39ac5b979a23b898`
- manifest identity
  `aad968530b371ac05de3529c3f0ac0a59afebc66bfaa21c2fcf4ca6306684c5b`
- artifact root
  `ae31de2fe50c0435387995dd4110579ff2b68ae9f59f9dd1b9f5afc55cb785eb`
- chapter inventory
  `17c2ecd7eb2ee519b9dce332eb370d97cea42ce75fa0eb5537729c424f4990ae`
- corpus counts: 1,189 canonical; 972 published; 185 source-limited;
  26 model-rejected; 6 quality-review; 0 missing

The previously reported terminal-state identity
`91df96a0a79571978a7839a29f9c3b22a2fc73dfce52890e27d52a4a087dc0cf` is
note-only: no authoritative release field or canonical derivation exists for
it. Terminal statuses are instead protected by the frozen manifest identity,
whose canonical payload includes the complete chapter publication index and
terminal-state counts.

## Approved deletion scope

The deletion inventory will be generated deterministically immediately before
mutation and must contain exactly the following classes:

1. Four candidate namespaces with no active code, test, runtime, package,
   verification, or current-lineage consumer:
   - `commentary-output-conformance-v1-d66...`
   - `reader-idea-ancestry-envelope-v1-b970...`
   - `reader-level-idea-projection-v1-2c6...`
   - `reader-level-idea-projection-v1-aba...`
2. Two incomplete/superseded corpus-runner sessions:
   - `batch-f69143177d9d0682`
   - `session-batch-2e86556dfb1e5a52`
3. The exact duplicate nested raw-response file under the accidental nested
   `.bhf-data/biblical-hermeneutics-framework` path.
4. Corpus-runner renderer receipts, because the reconciliation verifier treats
   them as optional and does not use them for artifact identity, ancestry,
   provenance, or package integrity.
5. Corpus-runner system and user prompt bodies, which are historical renderer
   inputs; their retained `metadata.json` files preserve the evidence,
   synthesis, and binding hashes required by reconciliation.
6. Canary raw, rerun, rejected-response, and manual-render staging material.
   Canary prompts, accepted responses, synthesis, gate/preflight state, audit
   results, and import/comparison contracts remain.

The approved estimate is 3,046 files and 43,239,735 bytes. The exact
machine-readable inventory is authoritative if the live pre-delete scan
differs; any unexpected path, unknown classification, or protected path is a
hard stop.

The five-chapter structured-enrichment namespace is intentionally retained:
`tests/test_commentary_v12_five_chapter_structured_enrichment.py` and
`tests/test_ckl_commentary_v12_structured_claims.py` load it directly.

## Retention boundaries

Retain the frozen release directory, current source-lineage baseline and its
historical inputs, finalized corpus-runner results/manifests/states/finalize
audits, required raw responses, renderer metadata, active test fixtures,
runtime-compatible commentary data, package-source data, and SQLite/local
runtime stores. Retain source-referenced historical qualification, validation,
provenance, ancestry, and audit namespaces even when they are not needed by
the frozen verifier.

Do not delete anything classified `UNKNOWN`, any current-lineage baseline, any
release/package artifact, any finalized runner evidence, or any path read by a
release-critical test.

## Validation gates

Before mutation, record the baseline and verify the proposed inventory has no
protected paths. After mutation, run:

- `tools/commentary_v12_freeze.py verify`
- `tools/commentary_v12_release.py inventory`
- `tools/commentary_v12_rebaseline_lineage.py verify`
- the release-critical deterministic Commentary v1.2 test suite
- package build/install and installed-package loading/count checks

Recheck all frozen identities, tag target, corpus counts, git diff scope,
absence of generation/provider calls, and before/after `.bhf-data` metrics.

If any verifier unexpectedly reads a proposed deletion, stop and restore the
cleanup operation through normal version control review rather than changing
the verifier or release contract.

## Documentation

Add `docs/bhf-data-retention.md` describing retained namespaces, their
consumers and retention reasons, plus categories that are intentionally
disposable in future development. Do not broadly ignore `.bhf-data`; add only
narrow scratch rules if the final audit proves a predictable transient path is
safe to ignore.
