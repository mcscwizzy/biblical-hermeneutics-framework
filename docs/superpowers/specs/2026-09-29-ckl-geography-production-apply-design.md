# CKL geography pilot production apply boundary

## Decision and scope

This specification defines a local, fail-closed production transaction for the
already reviewed geography pilot queue. Its purpose is to promote the exact
dry-run CKL change while making a crash, concurrent reader, stale input, or
post-write mismatch recoverable and visible. The selected architecture is an
explicit mutation plan, staged files and complete-tree validation, then a
29-path replacement transaction with durable backups and a rollback journal.
Production apply requires an offline, exclusive maintenance window in which
no application or runtime process reads the canonical CKL tree.

This document authorizes no apply, source research,
candidate regeneration, source-lock edit, CKL edit, derived rebuild, or
Commentary edit. The 14 bootstraps must remain the reviewed identity-only
representations. It introduces no distributed CKL root or generic migration
framework. The existing Commentary v1.1 corpus remains at `CORPUS_COMPLETE`.

## Frozen production inputs

The base is clean `master` commit
`02aa16d354f8dd8d5a98f528e16fbda647651c3b`. A later specification-only
commit may change repository HEAD; the CKL object tree and the files below
must still match these identities at apply preflight. All SHA-256 values are of
raw file bytes. These identities are the **frozen evidence/data baseline**,
not the final production writer identity: that writer does not exist yet. The
writer must replay the frozen decisions and validate frozen outputs under its
reviewed implementation before writing anything.

| Input | Frozen identity |
| --- | --- |
| `docs/ckl-geography-pilot-source-lock.json` | `ebed284f492a60f438c2503eefbc591fd2a56795c4bba1e2021c34c9bc335fc8` |
| `docs/ckl-geography-pilot-candidates.json` | `3364ba366e6ced1721e3b4f102cf619a08577a28b3819152f7f3b7a6ac5c9a3f` |
| `tests/fixtures/canonical_library/geography_original_20_payload_hashes.json` | `6cf3670165e2b8abaceb653383e38777b60b7b86d979282691bdc1a7268ceae4` |
| `framework/canonical_library/manifest.json` | `7eb5e4ba4e8832561862b303a40525a3c0a99906f2cf8cfec38e63745803ebfd` |
| `bhf_agent/data/openbible_places.json` | `22c50abfc77b9b1f0df501becfe48270b1df0e6cce25132cfdbd9bcfde9be0fb` |
| Git object tree `02aa16d:framework/canonical_library/objects` | `dc0a53ab068735cfe2b9aa31f87493ae73cc2b7e` |
| Loaded CKL inventory fingerprint, from a fresh `CanonicalLibrary().load()` | `f9bedc78cdebf508fd877a119b5cb7e521354f5dee32e4d55c720b0569ae8b47` |
| Byte-level CKL content signature v1, defined below | `a2944a684f32d73caad182eedf4863aea31904cd1a06ad0630eef86f7729c8b7` |

The byte signature is SHA-256 over `manifest.json`, then every regular
`objects/**/*.json` except `_`-prefixed filenames, sorted by relative POSIX
path. For each file, feed an unsigned eight-byte big-endian path-byte length,
UTF-8 path relative to `framework/canonical_library`, an unsigned eight-byte
big-endian content length, and the raw content bytes. The preflight also checks
that no unexpected object JSON or symlink is present; the signature and Git
tree identity complement the loaded semantic fingerprint. The manifest starts
at 665 objects.

The replay code identities observed at this base are:

| Code | SHA-256 |
| --- | --- |
| `framework/canonical_library/geography_candidates.py` | `c0cd4bbadee25f0eb3795fb7a3db70072a242e3179a92abb6bd08acfa536f891` |
| `framework/canonical_library/expansion.py` | `f6bf271fcfeb58502dbc2120e47bc15dde4307e50ca296dc504c242177e3df7e` |
| `framework/canonical_library/schema.py` | `c31104d38f7c2059012544f081bd93841754ec10a4e1479d2e916688f074b6f8` |
| `framework/canonical_library/loader.py` | `7eccbcdcd13e07da58d901c46e25a1798f968156cc653501d39ded9829699ddc` |
| Git tree `02aa16d:framework/canonical_library/schema` | `8592140be3c19f1c54d952fa8c38f6a35d377e6a` |

Preflight must also record and check the Git tree identity of the transitive
schema package and any other converter/validator dependencies used by the
reviewed replay. The final `reviewed_apply_implementation_sha` is established
only after implementation and final code review. Production apply requires
that exact reviewed commit as HEAD, a clean worktree, expected ancestry from
the frozen base, and no uncommitted transaction-critical code changes. An
arbitrary later working-tree version cannot execute the frozen transaction.
Code changes require new review and explicit code-identity authorization;
matching counts alone do not authorize substitution. The candidate Markdown
report
(`docs/ckl-geography-pilot-candidates.md`, SHA-256
`014d4c6295342c05effd0ab55c80ea4d6e3c7de9300c52e3303ef8276daf15f4`)
is audit material, not a semantic input; the writer must not parse it.

## Exclusive local access and startup order

Use a fixed CKL-local lock file and a nonblocking operating-system exclusive
file lock. The file may persist; *ownership* means a live kernel lock, not mere
file existence. Record process ID, host, transaction ID, and acquisition time
for diagnostics. A second apply fails closed if it cannot acquire the lock.
This lock prevents concurrent production writers; it does not coordinate
arbitrary CKL readers. The operator must separately assert an exclusive
maintenance window with no application or runtime process reading the
canonical CKL tree. Record this assertion in the receipt. Keep readers
quiesced through commit or completed rollback and lock release. Subsequent
work must discard cached CKL instances and reload the committed tree. Live,
uninterrupted readership would require a versioned-root architecture outside
this implementation. Do not make every CKL reader lock-aware in this task.

Acquire the exclusive lock before preflight. Under that lock, inspect journal
presence first. Any incomplete journal enters recovery before input checks,
staging, or a new transaction. A stale lock metadata file with no live lock
does not skip recovery; a live owner cannot be overridden on PID or age alone.
If the journal cannot prove safe automatic recovery, enter `RECOVERY_BLOCKED`:
make no new production writes or automatic deletions, preserve the journal
and backups, report the exact inconsistency, and require explicit operator
review. Do not guess whether to resume or roll back. The apply lock may be
released after the blocked condition is durably reported; the production
gate stays closed. Normal release follows a durable `COMMITTED` or
`ROLLED_BACK` decision and receipt.

## Replay, staging, and exact mutation plan

Under the lock, verify every frozen input, a clean CKL content tree, baseline
validation, and the original-20 payload hashes. Replay the *locked* candidate
JSON with the reviewed converter and `apply_candidate_queue(..., write=False)`.
Do not regenerate candidates from the source lock or accept a new candidate
classification. The frozen dry run has 28 accepted insertions, 13 classified
as complementary, zero provenance merges, and 14 bootstrap objects. Replay
must reproduce those decisions, source additions/merges, evidence IDs,
bootstrap identity IDs, and absence of provenance merges exactly; any drift
stops before staging promotion.

Serialize all changed objects and the manifest to private files on the same
filesystem as their production paths. Build a complete 679-object overlay from
the unchanged 651 objects plus these staged replacements and creations.
Validate that overlay with the same object parser and full-library validator
used for production: manifest and category counts, target resolution,
bootstrap identity and source validity, structural deduplication,
source/provenance validity, Scripture anchors, serialization round trips, and
the original-20 protection. Stage validation must inspect the *serialized
bytes*, not only in-memory mappings. No production file changes at this point.

Before any production replacement, emit one canonical JSON mutation plan,
with deterministic key order and compact UTF-8 serialization, and SHA-256 hash
its exact bytes. It contains a plan version, all frozen identities, replay code
identity, the expected before/after inventory and category counts, the exact
ordered path list, per-path operation and before/after raw SHA-256, and the
expected evidence IDs, bootstrap identity IDs, source additions/merges,
provenance merges, changed anchors and chapters. A new path has the explicit
precondition `must_not_exist`; a replacement has an exact before-hash.
Unchanged paths are constrained by the frozen object-tree and byte signature.
Immediately before the first write, recheck every path precondition and the
whole-tree signature. A mismatch aborts without writing.

The mutation set is exactly 29 paths:

| Operation | Exact object IDs and count |
| --- | --- |
| Modify 14 objects | `1-samuel`, `2-kings`, `acts`, `bethlehem-1`, `genesis`, `isaiah`, `jericho-1`, `john`, `judea-1`, `judges`, `levites`, `matthew`, `nazareth`, `ruth` |
| Create 14 objects | `abana`, `archelaus`, `azekah`, `cnidus`, `crete`, `cyprus`, `fair-havens`, `italy`, `judah-territory`, `lasea`, `myra`, `pharpar`, `socoh-1`, `sychar` |
| Modify last | `framework/canonical_library/manifest.json` |

Object paths are the canonical paths from the frozen candidate dry run and
`CATEGORY_FOLDERS`; the plan stores each literal path, not just these IDs.
The 14 creations mean places 77 → 90 and people 101 → 102; all other category
counts stay fixed, yielding 665 → 679 objects. The 28 inserted evidence IDs
are extracted from the frozen candidate payloads and verified against replay;
the plan stores every literal ID and parent object. The 14 bootstrap identity
evidence IDs and their exact serialized object bytes likewise come from the
reviewed candidate payloads. No changed path, additional evidence, source, or
provenance merge may be accepted as “close enough.”

The predicted changed chapters are `1 Samuel 17`, `2 Kings 5`, `Acts 27`,
`Genesis 13`, `Genesis 34`, `Isaiah 36`, `John 4`, `Joshua 6`, `Judges 20`,
`Matthew 2`, `Numbers 18`, and `Ruth 1`. They are an integrity comparison only.

## Durable CKL transaction and recovery state machine

The writer is a same-filesystem transaction on the repository's supported
platform. Before mutation, verify that staging, backups, journal, and target
CKL files meet the filesystem assumptions needed for atomic replacement and
durability; reject cross-filesystem paths, symlinks, or unsupported filesystem
operations. For each durable write, write a complete temporary file, flush
its contents, `fsync` the file, atomically replace into the intended path,
`fsync` its parent directory, then durably advance the transaction journal.
Use the same discipline for backup and journal creation. Backups and journal
must be flushed and verified before the first production replacement. If the
actual platform cannot satisfy these guarantees, fail closed rather than
silently downgrade. Do not build a generic cross-platform transaction system.

The journal and backup directory are private control data outside the CKL
object tree. The journal records transaction ID, immutable plan hash and path
list, frozen input identities, before and staged after hashes, backup paths and
hashes, intended new paths, last durable state, per-file progress, and an
integrity checksum. A transition is effective only after its journal update
is durable and readable.

| State | Durable entry condition | Permitted next state |
| --- | --- | --- |
| `PREFLIGHT_VERIFIED` | Exclusive lock, recovery check, frozen-input and baseline checks pass | `STAGED_AND_VALIDATED` or `ROLLED_BACK` |
| `STAGED_AND_VALIDATED` | Exact plan hashed; serialized full overlay validates | `BACKUPS_COMPLETE` or `ROLLED_BACK` |
| `BACKUPS_COMPLETE` | All 15 existing files backed up, all 14 absent paths recorded, all before-hashes checked, journal flushed and reread | `WRITE_IN_PROGRESS` or `ROLLED_BACK` |
| `WRITE_IN_PROGRESS` | Durable intent recorded before first replacement; object-file progress recorded durably | `FILES_WRITTEN` or `ROLLBACK_IN_PROGRESS` |
| `FILES_WRITTEN` | All 28 object files and manifest-last replacement are durable with expected hashes | `POSTWRITE_VALIDATED` or `ROLLBACK_IN_PROGRESS` |
| `POSTWRITE_VALIDATED` | Fresh disk reload and every post-write gate pass | `COMMITTED` or `ROLLBACK_IN_PROGRESS` |
| `COMMITTED` | Final decision and CKL receipt durable; rollback material may then be retired | terminal |
| `ROLLBACK_IN_PROGRESS` | Rollback intent durable; restoration progress recorded | `ROLLED_BACK` |
| `ROLLED_BACK` | Exact frozen byte signature and loaded inventory restored and verified; receipt durable | terminal; next apply needs new preflight |
| `RECOVERY_BLOCKED` | Journal or backup integrity is insufficient to prove safe automatic rollback; material is preserved and exact inconsistency reported | terminal for automatic apply; explicit operator review required |

Before entering `WRITE_IN_PROGRESS`, create and hash-check all 15 backups
(14 modified objects and manifest), record before-hashes for each, record all
14 planned new paths as absent, flush the journal, and reread it. Replace the
28 object files from the staged same-filesystem files with atomic renames;
write `manifest.json` last. Recheck staged after-hash at each replacement.
Manifest-last is an ordering rule, not the commit point. Commit requires a
fresh post-write reload and validation. Keep backups until `COMMITTED` is
durable.

For any valid incomplete journal short of `COMMITTED`, default recovery is
rollback followed by a completely new preflight, never silent resume. For
states before `BACKUPS_COMPLETE`, no production write was permitted: verify
the frozen before-state; if it differs, enter `RECOVERY_BLOCKED`. From
`BACKUPS_COMPLETE` onward, enter
`ROLLBACK_IN_PROGRESS`, restore every original file from its verified backup,
remove each planned new file if present, and verify the exact frozen byte
signature, manifest, 665-object load, inventory fingerprint, and baseline
warnings. Rollback is idempotent; interruption during rollback repeats it
under the lock. An unreadable, malformed, checksum-invalid, or otherwise
unverifiable journal, or a journal inconsistent with backups or current CKL
bytes, enters `RECOVERY_BLOCKED` without new writes or automatic deletions.
Unknown files, backup/hash disagreement, or a failed restoration likewise
preserve journal and backups for explicit operator review. A blocked condition
is reported in a separate durable diagnostic; the corrupt journal is never
rewritten to claim a verified state. A crash after `POSTWRITE_VALIDATED` but
before durable `COMMITTED` still rolls back. No downstream stage starts before
commit.

## CKL validation and changed-reference authority

The baseline authoring audit is 665 valid objects, zero errors, and 14
`incomplete_section_status` warnings: ten fields on `arad-ostraca`, and one
each on `exile-and-return-storyline`, `chiasm`, `branch-prophecy`, and `abba`.
The plan records each warning identity as `(code, object ID, path, field)`.
The staged and post-write gates require zero errors and no warning identity
outside that frozen set. None of those five objects is in the 29-path plan, so
this run expects the same 14 warning identities afterward. Any disappearance
must be explained by an actual, separately approved mutation; a count-only
comparison is insufficient. The receipt includes both before and after lists.

After manifest replacement, instantiate a *new* CKL loader against disk,
verify all 679 objects, manifest, categories, structural and provenance gates,
staged after-hashes, full-tree signature, and original-20 invariants. Compute
changed Scripture references from the actual before and freshly loaded after
canonical objects using the canonical changed-reference function, then derive
chapters. Compare exact anchors and chapters to the frozen replay. An
unexpected reference is a CKL transaction integrity failure and triggers
rollback; it does not widen downstream work. Only then enter
`POSTWRITE_VALIDATED` and durably `COMMITTED`.

## Transaction boundaries after CKL commit

**Transaction A — CKL:** the locked 29-path transaction above. A valid commit
is retained even if later work fails. Its receipt stores actual changed
references and the committed post-apply CKL fingerprint.
The first implementation plan covers only Transaction A: frozen input
verification, state model, writer lock, mutation plan, staged validation,
backups, durable journal, controlled writer, rollback and recovery, fresh
post-write validation, actual changed references, receipt, and a full-path
simulation against an isolated copied CKL root. The production writer stays
disabled by default. Its implementation does not authorize production apply.
Production execution requires a separate human authorization after
implementation and whole-branch review, adversarial and recovery tests,
frozen-input verification, and mutation-plan review. No test or ordinary CLI
invocation may mutate the production CKL.

**Transaction B — derived runtime/database artifacts:** start from a new,
explicitly verified CKL load with the committed fingerprint. Rebuild runtime
and database artifacts in a separate candidate location, validate them
independently, and publish them only through their own gate. Record the CKL
fingerprint consumed. Failure marks derived readiness blocked without
rolling back a valid Transaction A. It requires a separate implementation
plan after Transaction A is implemented, tested, and reviewed.

**Transaction C — EvidenceBundles and Commentary:** derive the impacted
chapter set only from Transaction A's actual changed references. Use a fresh
verified CKL load and record its fingerprint; selectively rebuild bundles and
syntheses, then perform quality review before publication. The dry run's 12
chapters are an exact integrity expectation, not a selection input. No new
evidence research is part of this workflow.

Transaction C likewise requires a separate implementation plan after
Transaction A review. Neither B nor C is part of the first implementation.

`docs/commentary-v1.2-release.json` says `"frozen": true`. Rebuilt commentary
must go into a separate, versioned candidate namespace pending its own release
approval; it cannot overwrite the published v1.2 release or its checksums.
“v1.2” may describe compatibility of the bundle/synthesis format, not
permission to mutate that release. A later promotion decides a new release
identity and validates its quality and lineage separately.

The current `selective_recompile` default helper in
`framework/canonical_library/expansion.py` passes `study_db_path` and
`read_only_inputs` to `framework.commentary.production.inputs.prepare_chapter`;
the latter accepts neither keyword. This is a Transaction C prerequisite,
tracked as `DERIVED_REBUILD_BLOCKED` until a bounded, separately reviewed code
change corrects and verifies that interface. Do not patch it inside the CKL
writer. A successful A may therefore be reported as
`CKL_COMMITTED / DERIVED_REBUILD_BLOCKED`; publication is not ready.

## Receipt and readiness

The Transaction A production receipt is control/audit metadata outside CKL
and Commentary input paths. It records `frozen_ckl_baseline_sha`,
`reviewed_apply_implementation_sha`, the operator's exclusive-maintenance
assertion, frozen input identities, plan hash, journal transitions, lock
owner, per-path before and after hashes, backup and recovery actions, staged
and actual validation results, warning identities, and actual changed anchors
and chapters. Its CKL status is `CKL_COMMITTED`, `ROLLED_BACK`, or
`RECOVERY_BLOCKED` as applicable. Later transaction receipts may record their
own CKL fingerprints, gate states, and Commentary quality classifications;
they do not expand the Transaction A implementation. No receipt may be
ingested as CKL evidence, a source, or Commentary context.

## Remaining design risks and review gates

1. The repository apply lock prevents concurrent writers. Reader exclusion
   depends on the asserted exclusive maintenance window and requires
   operational verification before production apply.
2. An unreadable journal or failed/partial backup has no safe automatic
   recovery proof. `RECOVERY_BLOCKED` preserves recovery material and stops
   for explicit operator review.
3. Directory `fsync` and atomic rename guarantees must be verified on the
   actual local filesystem; cross-filesystem staging is forbidden.
4. Converter/schema dependency identities and the future writer's exact
   reviewed commit need a reviewed authorization record before apply. The
   frozen evidence/data baseline does not certify new code.
5. Transaction C is currently blocked by the preparer interface mismatch;
   the CKL commit does not imply publication readiness.

The approved design direction permits a Transaction A implementation plan
after this amendment is committed and self-reviewed. The plan requires its
own review before implementation. Production apply remains a separate human
authorization gate.

## Specification self-review

The candidate report's 28 changed object IDs reconcile to the 14 existing
and 14 new IDs above; those plus the manifest are exactly 29 paths. The
source-lock, candidate JSON, original-20 fixture, manifest, and OpenBible
hashes above were checked against the current files. The current CKL load and
authoring audit returned 665 objects, the stated inventory fingerprint, zero
errors, and the 14 identified warnings. The byte-signature calculation covered
the manifest and 665 object JSON files. The frozen v1.2 release marker and the
selective helper/preparer signature mismatch were checked in their current
files. The amendment distinguishes writer exclusion from the maintenance
window, requires fail-closed same-filesystem durability and recovery, defers
final writer identity until review, and limits the first plan to Transaction A.
No production CKL, source lock, candidate, fixture, or Commentary file was
changed while writing this specification.
