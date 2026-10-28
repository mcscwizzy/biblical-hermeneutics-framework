# NE-11E2: CKL governance and legacy attribution

**Governance tests pass under a narrow, hash-pinned legacy exception registry.** This records missing historical generator attribution; it does not recover or assign a generator, attest to human review, or promote any object.

## Full inventory audit

The audit covered all 687 CKL object files. Exactly five populated objects have `content_status: draft`, `review_status: in_review`, and an empty `generated_by` array. Each has `reviewed_by: []`, `human_review_required: true`, and `last_reviewed: null`. No other object with `content_status` `draft` or `complete` and `review_status: in_review` had empty `generated_by`.

The object bytes match the bytes introduced by the historical commit listed below. The retained transaction manifests identify the transaction and object path. **No independent evidence identifies the human or AI generator for any of the five objects.** Commit authors are not treated as generators.

| CKL object ID | Repository path | Current SHA-256 | Introduction commit | Transaction | Retained audit manifest |
| --- | --- | --- | --- | --- | --- |
| `genesis-flood-postflood-context` | `framework/canonical_library/objects/cultural_background/genesis-flood-postflood-context.json` | `d22862694a5b6a9799074703a36d4a572d14731a51ab4e8ed70a574734e7c44b` | `ce3a58e195a82af086fbce7dfecccbcc80ad99ae` | `GENESIS_G2R2_ISOLATED_EVIDENCE_CONTAINER` | `.bhf-data/bhf-commentary-candidates/genesis-g2-flood-postflood-evidence-expansion/g2-production-apply-manifest.json` |
| `genesis-nations-babel-context` | `framework/canonical_library/objects/cultural_background/genesis-nations-babel-context.json` | `ee22202a8bfc1be62469d1e710ae2383149ecad445dc4d721008a18d42a22f23` | `3991acf388822065eac171fa4cf2b81834726968` | `GENESIS_G3_NATIONS_BABEL_EVIDENCE_EXPANSION` | `.bhf-data/bhf-commentary-candidates/genesis-g3-nations-babel-evidence-expansion/g3-production-apply-manifest.json` |
| `genesis-abraham-call-covenant-context` | `framework/canonical_library/objects/cultural_background/genesis-abraham-call-covenant-context.json` | `02aeceb005539c7175afa4631cffc808ef377b73185b760f582e48119fb38aa9` | `42c821a7639366a2338963b11a475958f586d2fa` | `GENESIS_G4A_ABRAHAM_CALL_COVENANT_EVIDENCE_EXPANSION` | `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/g4a-production-apply-manifest.json` |
| `genesis-abraham-late-cycle-context` | `framework/canonical_library/objects/cultural_background/genesis-abraham-late-cycle-context.json` | `95413e73224c3242589c0d9891444f3c7b438bd562d70cdb6ae239d7fd5d7408` | `52a77843ae0be8c94ca33494278be7b209911ac6` | `GENESIS_G4B_ABRAHAM_LATE_CYCLE_EVIDENCE_EXPANSION` | `.bhf-data/bhf-commentary-candidates/genesis-g4b-abraham-late-cycle-evidence-expansion/g4b-production-apply-manifest.json` |
| `genesis-isaac-jacob-transition-context` | `framework/canonical_library/objects/cultural_background/genesis-isaac-jacob-transition-context.json` | `22f8d2d0b6c7625b1267193ab1fb4e500981ad95713f702b83466b031bcb28cb` | `76c5beabd4ba98093f02d22d2eb95ed9a9372acb` | `GENESIS_G5A_ISAAC_JACOB_TRANSITION_EVIDENCE_EXPANSION` | `.bhf-data/bhf-commentary-candidates/genesis-g5a-isaac-jacob-transition-evidence-expansion/g5a-production-apply-manifest.json` |

The supplied G5A commit in the task description was one character short. Git history identifies the actual 40-character introduction commit above. All five current file hashes were compared with `git show <introduction-commit>:<object-path>` and matched.

## Exception policy

[`docs/maintenance/ckl-legacy-provenance-exceptions.json`](../../maintenance/ckl-legacy-provenance-exceptions.json) contains exactly these five audited records. Each entry pins its exact ID, path, object SHA-256, introduction commit, transaction name, and retained audit manifest. It records the reason as “original generator attribution was not documented,” sets status to `legacy_attribution_unverified`, and requires the record to remain `in_review` with `human_review_required: true`.

The manifest test validates the registry against a separate exact allowlist and validates the retained transaction manifest, object ID/path, raw-byte SHA, and current review state. It rejects duplicate, missing, stale, invented, malformed, and unmatched entries. An exception is refused if `generated_by` becomes populated, `reviewed_by` is nonempty, the record is no longer a draft in review, or human review is no longer required. Unregistered new drafts with empty `generated_by` continue to fail. Ordinary populated in-review objects continue through the existing generation-provenance check. No object, manifest, source lock, evidence value, or curation was changed.

This is consistent with repository guidance to preserve verified provenance and document uncertainty when attribution cannot be established. The exception does not weaken source, passage-applicability, evidence-integrity, or source-lock validation. The unknown generator remains unknown; human review remains outstanding for all five records.

## Verification and identities

Before and after the registry correction, the CKL identity values are unchanged:

| Identity | Before | After |
| --- | --- | --- |
| 687-object inventory fingerprint | `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` | `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` |
| Object-source tree SHA-256 | `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766` | `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766` |
| CKL manifest SHA-256 | `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4` | `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4` |

Source-lock validation passes. The NE-9C validator retains all 4,061 authored relationship identities and 3,925 reviewed dispositions (408 curated, 1,895 held, 1,622 excluded). The NE-10 registry contains **44 verified passage bridges** and **7 held research candidates**; none was changed.

| Check | Before correction | After correction |
| --- | --- | --- |
| Exact former inventory assertion | Failed on the first empty `generated_by` record | **PASS**, 1 test |
| Full manifest suite | 7 passed, 1 failed at the first unaffiliated populated draft | **PASS**, 18 tests and 13 subtests |
| CKL schema/governance batch (manifest, schema, package schema, source locks, Scripture references, release metadata) | The previous consolidated integrity batch had 571 passed, 1 manifest failure | **PASS**, 128 tests and 13 subtests |
| Source-lock tests | Not reached as an independent final result in the failing batch | **PASS**, 27 tests |
| CKL validator | Previously 687 valid, 0 errors, 14 warnings | **PASS**, 687 valid, 0 errors, 14 existing warnings |
| NE-9C / NE-10 / Narrative Explorer identity and projection tests | Previously part of the batch with the manifest failure | **PASS**, 505 tests |
| Release-path sanitizer, Vercel packaging/startup, provider identity | Existing gates passed before this correction | **PASS**, 26 tests |

Adversarial tests verify the exact five records, reject an unlisted lookalike and changed bytes, reject wrong ID/path, duplicates, missing transaction evidence, unknown fields, reviewed/completed states, and new unattributed drafts, and preserve the ordinary populated-provenance path. The exception never becomes a human-review attestation.

## Release status

**NE-11E2's manifest and CKL governance tests pass under the documented legacy policy. The overall branch is NOT READY FOR RELEASE while these five populated draft objects still require human review.** The change records the unknown historical generator without fabricating certainty; it does not satisfy the five outstanding content reviews or promote the objects.
