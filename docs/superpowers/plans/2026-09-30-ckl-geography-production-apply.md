# CKL Geography Production Apply, Transaction A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a disabled-by-default, recoverable 29-path production writer for the frozen geography pilot CKL transaction, with an exhaustive simulation on isolated copies.

**Architecture:** Keep pilot identities and counts in a frozen contract, derive a canonical mutation plan from `apply_candidate_queue(..., write=False)`, and validate serialized staged bytes as a full CKL before writing. A same-filesystem storage layer, checksummed journal, exclusive writer lock, and coordinator perform object-first/manifest-last replacements, post-write reload, commit, or exact rollback. A CLI exposes plan/simulate by default and production only through a separate operator authorization record.

**Tech Stack:** Python 3.9+, standard-library `hashlib`, `json`, `os`, `fcntl` on the supported local POSIX platform, existing CKL loader/schema/authoring/expansion code, pytest.

**Spec:** `docs/superpowers/specs/2026-09-29-ckl-geography-production-apply-design.md`, originally committed at `4031a600799ad23aec6f8cf12bb673c143523fff` and amended with this plan before implementation. The approved spec and plan SHA-256 identities are taken from their final reviewed file bytes after the correction commit, never from the superseded plan commit.

## Global Constraints

- Implement **Transaction A only**. Do not change SQLite/runtime publication, EvidenceBundles, Commentary, selective rebuild helpers, release/version data, UI, or unrelated tests.
- Never mutate the frozen source lock, candidate JSON, original-20 fixture, OpenBible data, production CKL, or the completed Commentary corpus during implementation or testing. Use isolated copied roots for every destructive test.
- Freeze base CKL/master `02aa16d354f8dd8d5a98f528e16fbda647651c3b`, the five file hashes, Git object-tree identity, loaded inventory fingerprint, and byte signature exactly as specified. Lower-level utilities accept injected expected values for tests; the pilot entry point does not.
- Pilot acceptance is exact: 28 accepted candidate evidence insertions, 14 new bootstrap objects and identity evidence items, 14 existing objects modified, 29 paths including manifest, manifest 665 → 679, places 77 → 90, people 101 → 102, and zero provenance merges. These are pilot assertions, not generic storage defaults.
- Materialize the literal allowlist from the spec's IDs: nine existing book files (`1-samuel`, `2-kings`, `acts`, `genesis`, `isaiah`, `john`, `judges`, `matthew`, `ruth`), four existing place files (`bethlehem-1`, `jericho-1`, `judea-1`, `nazareth`), existing institution `levites`, 13 new place files (`abana`, `azekah`, `cnidus`, `crete`, `cyprus`, `fair-havens`, `italy`, `judah-territory`, `lasea`, `myra`, `pharpar`, `socoh-1`, `sychar`), new person `archelaus`, and `manifest.json`. All paths are under `framework/canonical_library` and use `CATEGORY_FOLDERS`.
- The 12 frozen changed chapters are `1 Samuel 17`, `2 Kings 5`, `Acts 27`, `Genesis 13`, `Genesis 34`, `Isaiah 36`, `John 4`, `Joshua 6`, `Judges 20`, `Matthew 2`, `Numbers 18`, and `Ruth 1`. Compare actual anchors and chapters to frozen replay; do not use the chapter list to choose scope.
- Preserve 14 baseline `incomplete_section_status` warning identities `(code, object ID, path, field)`; require zero errors and no added, removed, or altered warnings. Stage and post-write validation use serialized disk bytes and a fresh `CanonicalLibrary(root).load()`.
- Require an offline exclusive maintenance window for production. The `fcntl` lock excludes concurrent writers only; it does not exclude arbitrary readers. The receipt records the operator assertion.
- Require same-filesystem staging/backups/journal/target paths, regular-file and no-symlink checks, atomic replacement, file flush and `fsync`, directory `fsync`, and durable journal progress. Fail closed if the supported platform/filesystem cannot meet these assumptions.
- A valid incomplete journal rolls back to exact pre-apply bytes and requires an entirely new preflight. A corrupt, unreadable, or unverifiable journal or backups yields `RECOVERY_BLOCKED`, preserves recovery material, and makes no new production writes or automatic deletions.
- The writer stays disabled by default. Its implementation does not authorize production apply. Final reviewed apply SHA is established only after implementation and whole-branch review.
- An operator authorization outside the repository binds one successful full-path simulation receipt and its exact canonical mutation-plan hash. A new plan requires a new simulation, review, and authorization. No implementation or test creates a production authorization record or writes the real production CKL.

## Review Focus

- A symlink, nonregular file, cross-device directory, or unsupported directory `fsync` must stop before the first CKL replacement (Task 4 tests).
- A journal checkpoint may lag an atomic replacement by one file; recovery must accept only a byte state proven by the plan, backups, and journal, then roll back (Task 5 tests).
- A valid terminal journal with unexpected current CKL bytes must block a new transaction rather than conceal drift (Task 5 test).
- A late candidate or converter change that keeps all counts but changes evidence IDs, bootstrap bytes, or anchors must fail replay (Task 2 tests).
- A receipt or authorization path inside CKL/Commentary inputs must be rejected so control files cannot enter evidence or corpus scans (Tasks 6–7 tests).

## File Structure

- Create `framework/canonical_library/geography_apply_contract.py`: frozen identities, byte signature, baseline checks, warning identity extraction, pilot allowlist/counts.
- Create `framework/canonical_library/geography_apply_plan.py`: locked-candidate replay, exact decisions, serialized mutation plan and hash, full staged overlay validation.
- Create `framework/canonical_library/geography_apply_storage.py`: POSIX writer lock, filesystem checks, durable replace/copy/delete primitives.
- Create `framework/canonical_library/geography_apply_journal.py`: checksummed journal, transition validation, recovery proof, rollback, blocked diagnostic.
- Create `framework/canonical_library/geography_apply.py`: Transaction A coordinator, post-write reload, changed-reference comparison, and CKL receipt.
- Create `tools/ckl_geography_production_apply.py`: plan/simulate/production CLI and operator authorization gate. Do not add the unsafe `write=True` path to `expansion.py`.
- Create `tests/canonical_library/test_geography_apply_contract.py`, `test_geography_apply_plan.py`, `test_geography_apply_storage.py`, `test_geography_apply_journal.py`, `test_geography_apply.py`, and `test_geography_apply_cli.py`: focused TDD and isolated full-path cases. Put copied-tree fixtures in `tests/canonical_library/geography_apply_fixtures.py`; copy bytes, never rewrite production inputs.

## Binding execution setup

Before Task 1, use `superpowers:using-git-worktrees` to create an isolated implementation branch/worktree from the committed spec. Record branch, HEAD, clean status, and production CKL/source-lock byte signatures. Keep implementation commits on that branch; do not execute production mode. Make the existing `.venv` available read-only in each worktree so the commands below use the same dependencies. A copied test root must contain the frozen CKL tree and copies of the five frozen input files; mutations in a test touch only the copy. Freeze a detached pre-implementation baseline and run `.venv/bin/pytest -q -n 8 --dist loadfile`; record its exit status and failing node IDs for final comparison. Before final review, run focused tests, simulation, and the recovery fault matrix; compare frozen production input signatures again. No production authorization record is created as part of implementation.

### Task 1: Freeze and verify the baseline

**Files:** Create `geography_apply_contract.py`, `test_geography_apply_contract.py`, and copied-root helpers in `geography_apply_fixtures.py`.

**Interfaces:** Produce `PILOT_BASELINE: FrozenBaseline`, `verify_frozen_inputs(repo_root: Path, ckl_root: Path, baseline: FrozenBaseline = PILOT_BASELINE) -> VerifiedBaseline`, `ckl_byte_signature(ckl_root: Path) -> str`, and `warning_identities(audit: LibraryAudit) -> tuple[WarningIdentity, ...]`. Define `WarningIdentity` as `(code: str, object_id: str, path: str, field: str)`; `VerifiedBaseline` carries manifest/object bytes and hashes, inventory fingerprint, warning identities, and the frozen base SHA. Use the spec's eight frozen identities and exact 29-path pilot allowlist.

- [ ] **Step 1: Write failing tests** for unchanged copied input PASS and separate source-lock hash mismatch, candidate hash mismatch, original-20 fixture mismatch, OpenBible hash mismatch, starting manifest mismatch, changed existing object byte, unexpected object JSON, symlink, wrong Git object-tree identity, wrong inventory fingerprint, and exact 14-warning baseline. Assert each failure names its input and leaves copied CKL bytes unchanged.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply_contract.py`; expect the new tests to fail for missing interfaces.
- [ ] **Step 3: Implement** the signatures above. The byte signature uses manifest first, then sorted regular `objects/**/*.json` excluding `_` names, with eight-byte big-endian path/content lengths exactly as the spec. Reject unexpected files/symlinks before loading; run `CanonicalLibrary(root).load()` and `scan_library(root)`; compare warning identities including `details['section']` as the field. Verify the frozen Git object tree from the base commit without treating current HEAD as the baseline.
- [ ] **Step 4: Rerun** the Task 1 test command; expect all tests PASS and no write under production CKL.
- [ ] **Step 5: Commit** only Task 1 files with `git commit -m 'feat: verify frozen geography CKL baseline'`.

### Task 2: Replay frozen decisions and hash an exact mutation plan

**Files:** Create `geography_apply_plan.py` and `test_geography_apply_plan.py`.

**Interfaces:** Consume `VerifiedBaseline`; produce `prepare_mutation_plan(repo_root: Path, ckl_root: Path, baseline: VerifiedBaseline) -> PreparedPlan`. `PreparedPlan` contains canonical compact UTF-8 `plan_bytes`, `plan_sha256`, 29 ordered `PlannedPath` entries, 28 serialized object payloads, manifest bytes, replay decisions, predicted anchors/chapters, and expected IDs. `PlannedPath` records literal relative path, `replace` or `create`, exact before/after SHA-256, and `must_not_exist` for creations.

- [ ] **Step 1: Write failing tests**: load only `candidate_payload` from frozen candidate records with `outcome in {'NEW', 'COMPLEMENTARY'}`; expect 28 accepted decisions, 13 complementary, 28 insertions, 14 bootstraps with 14 identity evidence items, 14 existing changes, 29 allowlisted paths, zero merges, and exact 665 → 679/77 → 90/101 → 102 counts. A second run must produce byte-identical plan/hash. Mutate a candidate evidence ID, bootstrap bytes, expected classification, changed anchor, or source merge while keeping counts; expect rejection. Reject a planned path outside the literal allowlist, wrong existing-file hash, and a pre-existing new-object path before writing.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply_plan.py`; expect missing-interface failures.
- [ ] **Step 3: Implement** `prepare_mutation_plan` using `apply_candidate_queue(ckl_root, payloads, write=False)` and `CATEGORY_FOLDERS`; never use the candidate Markdown report or `write=True`. Compare every accepted decision, evidence ID/parent, bootstrap identity, source addition/merge, zero provenance merge, changed anchor/chapter, and changed object ID to the frozen candidate artifact. Serialize objects in the CKL's existing JSON style, build manifest from verified before counts, require exact paths, and hash canonical `json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')` bytes. Reject any mismatch before staging.
- [ ] **Step 4: Rerun** the Task 2 test command; expect PASS.
- [ ] **Step 5: Commit** only Task 2 files with `git commit -m 'feat: plan exact geography CKL mutation'`.

### Task 3: Validate a complete staged CKL from serialized bytes

**Files:** Modify `geography_apply_plan.py`; extend `test_geography_apply_plan.py`.

**Interfaces:** Produce `stage_and_validate(plan: PreparedPlan, ckl_root: Path, staging_root: Path) -> ValidatedStage`, carrying staged file paths/hashes, full-tree signature, loaded inventory, audit warning identities, and validated actual references. `staging_root` is private, on the target filesystem, and outside the CKL input tree.

- [ ] **Step 1: Write failing tests** that build a 679-object overlay from 651 unchanged copied files plus 28 staged objects and manifest, reload it with a new `CanonicalLibrary`, and require zero errors and exact 14-warning parity. Corrupt serialized object bytes, manifest count/category, original-20 payload, bootstrap identity, source reference, or an unchanged file after baseline verification; each must fail before a production path changes.
- [ ] **Step 2: Run** the Task 3 tests; expect failure until staged validation exists.
- [ ] **Step 3: Implement** `stage_and_validate` with complete serialized overlay and `scan_library`, loader, round-trip, original-20, target/provenance/structural gates. Compare staged actual anchors and chapters with frozen replay; keep stage private until writer promotion. Revalidate hashes from disk after serialization.
- [ ] **Step 4: Rerun** the Task 3 tests; expect PASS.
- [ ] **Step 5: Commit** Task 3 changes with `git commit -m 'feat: validate serialized geography CKL stage'`.

### Task 4: Enforce exclusive writer and durable same-filesystem primitives

**Files:** Create `geography_apply_storage.py` and `test_geography_apply_storage.py`.

**Interfaces:** Produce `writer_lock(lock_path: Path, owner: LockOwner) -> ContextManager[None]`, `verify_storage_layout(ckl_root: Path, control_root: Path, planned_paths: Sequence[PlannedPath]) -> None`, `durable_replace(destination: Path, data: bytes) -> None`, `durable_copy(source: Path, destination: Path) -> str`, and `durable_unlink(path: Path) -> None`. Lock metadata is diagnostic; only a live `fcntl.flock(LOCK_EX | LOCK_NB)` owns the lock.

- [ ] **Step 1: Write failing tests** for second live apply lock rejection, stale metadata with no live lock acquisition, path escape/symlink/nonregular file/cross-device rejection, and injected `fsync` or `os.replace` failure. Spy on operation order: complete temp write → flush → file `fsync` → atomic replace → parent directory `fsync`; journal advancement is the caller's next step. Verify private backup creation and deletion also sync their parent directories.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply_storage.py`; expect missing-interface failures.
- [ ] **Step 3: Implement** POSIX-only primitives with explicit capability probes and device checks for staging, backups, journal, and every target parent. Refuse unsupported guarantees; never fall back to non-atomic copy on a production target. Close descriptors and clean only unpromoted temporary files after exceptions.
- [ ] **Step 4: Rerun** the Task 4 test command; expect PASS.
- [ ] **Step 5: Commit** Task 4 files with `git commit -m 'feat: add durable CKL storage and writer lock'`.

### Task 5: Journal, recovery proof, and exact rollback

**Files:** Create `geography_apply_journal.py` and `test_geography_apply_journal.py`.

**Interfaces:** Produce `JournalStore(control_root: Path)`, `JournalStore.load() -> JournalState`, `JournalStore.advance(state: JournalState) -> None`, `recover_or_block(journal: JournalStore, ckl_root: Path, plan: PreparedPlan | None) -> RecoveryOutcome`, and `rollback_verified(journal: JournalStore, ckl_root: Path) -> RecoveryOutcome`. Journal state includes transaction ID, plan hash, immutable path/pre/post hashes, backup paths/hashes, progress, state, and checksum. `RecoveryOutcome.status` is `ROLLED_BACK`, `RECOVERY_BLOCKED`, or a verified terminal state. `RECOVERY_BLOCKED` writes a separate durable diagnostic and preserves journal/backups.

- [ ] **Step 1: Write failing tests** for interruption before writes, after one or more object writes, after all objects before manifest, after manifest before post-write validation, and during rollback. Inject faults after each durable transition and after an atomic replace but before progress journaling; recovery must accept only expected before/after bytes, restore all 15 originals byte-for-byte, remove only the 14 planned new files, and reproduce frozen signature, inventory, manifest 665, and 14 warnings. An incomplete valid journal requires a new preflight after rollback.
- [ ] **Step 2: Add failing blocked tests** for unreadable, malformed, checksum-invalid, wrong plan hash, absent or mismatched backup, current CKL byte outside the proven before/after set, unexpected new-object bytes, unexpected file, and terminal journal with unexpected CKL drift. Assert `RECOVERY_BLOCKED`, exact diagnostic, no new CKL write/deletion, and preserved journal/backups. Test stale lock metadata plus valid incomplete journal enters recovery; active lock blocks a second process.
- [ ] **Step 3: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply_journal.py`; expect missing-interface failures.
- [ ] **Step 4: Implement** a versioned checksummed journal with durable writes and strict state transitions from the spec. Before `WRITE_IN_PROGRESS`, verify and durably store 15 backup files, 14 absent paths, plan hash, and journal. On startup under the lock inspect the journal before new preflight. For valid incomplete states default to exact rollback; never guess on invalid evidence. Rollback itself journals progress and is idempotent.
- [ ] **Step 5: Rerun** the Task 5 test command; expect PASS.
- [ ] **Step 6: Commit** Task 5 files with `git commit -m 'feat: recover interrupted CKL transactions'`.

### Task 6: Controlled writer, post-write authority, and receipt

**Files:** Create `geography_apply.py` and `test_geography_apply.py`.

**Interfaces:** Produce `execute_transaction(repo_root: Path, ckl_root: Path, control_root: Path, authorization: ProductionAuthorization | SimulationAuthorization, fault: FaultHook | None = None) -> CKLReceipt`; define `FaultHook = Callable[[str, Path | None], None]` for deterministic interruption points. The coordinator consumes Tasks 1–5. `ProductionAuthorization` carries the complete Task 7 record, including the reviewed implementation, approved spec and plan, frozen baseline, exact mutation-plan and successful simulation-receipt hashes, fixed action, and maintenance-window assertion; the coordinator enforces the Git/code and exact-plan gates before backups or production writes. `SimulationAuthorization` is accepted only for a copied CKL root whose resolved path differs from the canonical production root. Production receipt fields include `frozen_ckl_baseline_sha`, `reviewed_apply_implementation_sha`, plan hash, assertion, owner/transitions, per-path hashes, backup/recovery actions, staged/post-write validation, warning identities, and actual anchors/chapters.

- [ ] **Step 1: Write failing copied-root tests** for a complete 29-path commit: journal and backups flushed before first replacement; 28 objects written before manifest; fresh disk reload validates 679 objects, places 90, people 102, exact 14 warnings and all staged hashes; actual `changed_references(before, fresh_after)` and derived chapters equal frozen replay; receipt is outside CKL/Commentary paths. Assert `COMMITTED` only after post-write validation and durable receipt. Inject unexpected changed-reference set, warning difference, post-write hash mismatch, or reload failure; expect rollback to exact original bytes and no committed receipt.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply.py`; expect missing-interface failures.
- [ ] **Step 3: Implement** coordinator under the exclusive writer lock. Check recovery first, then frozen inputs, plan, staged full-tree validation, path preconditions and whole-tree signature immediately before first write, storage assumptions, authorization identity/clean-tree/ancestry/plan-hash/maintenance gates, backups/journal, object replacements, manifest last, fresh reload, actual reference comparison, receipt, and durable commit. Never use `apply_candidate_queue(..., write=True)`. Keep maintenance assertion in the receipt and refuse receipt/control paths under CKL or Commentary inputs. The simulation authorization can write only to the copied CKL root.
- [ ] **Step 4: Rerun** the Task 6 tests; expect PASS.
- [ ] **Step 5: Commit** Task 6 files with `git commit -m 'feat: apply and validate CKL geography transaction'`.

### Task 7: Gate production and prove full-path simulation

**Files:** Create `tools/ckl_geography_production_apply.py` and `test_geography_apply_cli.py`.

**Interfaces:** `main(argv: Sequence[str] | None = None) -> int` supports `plan`, `simulate`, and `apply`. `plan` emits canonical mutation-plan bytes and `mutation_plan_sha256` without CKL writes. `simulate` copies the complete frozen input/CKL set into a private temporary root and runs the same coordinator/storage/journal/recovery path against the copy, using an internal simulation context that cannot target production. Only a successful full-path simulation emits an immutable receipt with `simulation_receipt_sha256`; the receipt binds its mutation-plan hash and validated copied-root outcome. `apply` requires `--authorization-file PATH` plus `--production` and an existing, hash-verified successful simulation receipt. The operator creates the authorization JSON outside the repository only after reviewing the successful simulation. The tool never creates or updates it. Its complete fields are:

```text
authorization_version
authorized_action
reviewed_apply_implementation_sha
approved_design_spec_sha256
approved_implementation_plan_sha256
frozen_ckl_baseline_sha
mutation_plan_sha256
simulation_receipt_sha256
exclusive_maintenance_window_asserted
authorized_at
operator
```

`authorized_action` is exactly `"ckl-geography-production-apply"`; `exclusive_maintenance_window_asserted` must be `true`. `authorized_at` must follow the successful simulation receipt's completion time. The approved spec and plan SHA-256 values hash their final reviewed bytes after the correction commit; the reviewed apply implementation SHA is established only after implementation and whole-branch review. This authorization permits one exact reviewed transaction, not general CKL writes.

- [ ] **Step 1: Write failing CLI tests**: no arguments and `plan` cannot write; `simulate` performs 29 replacements in a copied root, produces canonical plan bytes/hash and an immutable successful receipt/hash, and leaves production byte signature and frozen input hashes unchanged. `apply` without both explicit gates, with invalid/missing maintenance assertion, wrong reviewed commit, dirty worktree, wrong branch ancestry, or control path inside CKL/Commentary fails before writing. Reject a correct implementation SHA paired with a wrong mutation-plan hash; a mutation-plan hash from a different simulation; a wrong simulation-receipt hash; a wrong approved spec hash; a wrong approved plan hash; a wrong action identifier; stale authorization after any frozen input changes; and authorization created before a successful simulation receipt exists. For each rejection assert zero changes to the copied CKL. Add a positive integration test: simulate to obtain receipt and mutation-plan hash, construct an external fixture authorization binding those exact identities, then invoke production-mode execution against an isolated copied CKL; it must independently recompute the same plan and proceed only when all identities match. A stale lock plus valid journal must recover before any new plan is accepted. No test targets the real production CKL.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply_cli.py`; expect missing-interface failures.
- [ ] **Step 3: Implement** explicit CLI gating and check `git rev-parse HEAD == reviewed_apply_implementation_sha`, `git status --porcelain` empty, and base SHA an ancestor of HEAD. Verify the authorization's fixed action, final approved spec/plan byte hashes, frozen baseline, successful immutable simulation-receipt hash and its bound plan hash, and operator maintenance assertion. Independently rerun frozen-input verification, replay, staging, validation, and canonical plan construction; require `freshly_computed_mutation_plan_sha256 == authorization.mutation_plan_sha256` before backups or any production write. Fail closed with zero production CKL changes on any mismatch. A changed transaction requires a new simulation, review, and authorization; never update or reuse the old record. Reject ordinary/default invocation. `simulate` uses an explicit test/copy target and never points a writer at production. Do not generate a production authorization file, infer authorization from a test flag, or let the tool select a later arbitrary implementation SHA silently.
- [ ] **Step 4: Rerun** the Task 7 tests; expect PASS.
- [ ] **Step 5: Commit** Task 7 files with `git commit -m 'feat: gate CKL production apply and simulate transaction'`.

### Task 8: Adversarial integration and final review gate

**Files:** Extend only the six Transaction A test modules and copied-root fixture as needed; do not change unrelated tests.

**Interfaces:** No new public API. Produce an execution ledger with test commands/results, fault points, frozen input hashes before/after, simulation receipt and plan hash, task commit SHAs, and whole-branch review findings.

- [ ] **Step 1: Add any missing failing adversarial tests** from the matrix below, particularly journal corruption and between-replace/checkpoint faults. Run each new test red, then make the smallest Transaction A change and rerun green. Do not relax a frozen expectation to make a test pass.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/canonical_library/test_geography_apply_*.py tests/canonical_library/test_geography_apply.py tests/canonical_library/test_expansion.py tests/canonical_library/test_geography_candidates.py tests/canonical_library/test_source_locks.py tests/canonical_library/test_manifest.py`; expect zero failures. Run the CLI simulation on a copied root and verify source-lock, candidate, fixture, OpenBible, manifest, object-tree signature, and production CKL bytes are unchanged.
- [ ] **Step 3: Commit** any focused integration-test/fix changes with `git commit -m 'test: harden CKL transaction recovery'`. Run `.venv/bin/pytest -q -n 8 --dist loadfile` at the final implementation HEAD and compare failing node IDs against the detached baseline; newly failing Transaction A tests are blockers, while unrelated baseline failures are recorded without out-of-scope fixes.
- [ ] **Step 4: Review** the whole implementation branch diff against the recorded starting commit and the amended spec, including every failure mode, full receipt fields, exact 29-path allowlist, write ordering, and absence of Transaction B/C changes. Run `git diff --check`, inspect `git status --short`, and record the final HEAD and review findings. Any fix after this review requires rerunning affected tests and the whole-branch review. Do not create the authorization file or run production apply.

## Adversarial matrix and crash strategy

Use a copied frozen CKL root for each case; capture its raw-byte inventory before fault injection and after recovery. Tasks 1–3 cover the source-lock, candidate, OpenBible, fixture, manifest, CKL byte drift, unexpected existing hash/new path, off-allowlist path, count, warning parity, and changed-reference cases. Task 4 covers lock contention and durability assumptions. Task 5 injects a process-equivalent interruption at every journal transition and immediately after a replacement with a lagging checkpoint: before writes, after object 1 and an intermediate object, after object 28, after manifest, after post-write validation before commit, and during rollback. Also corrupt journal/backup/current bytes and require `RECOVERY_BLOCKED` with zero automatic CKL changes. Tasks 6–7 prove exact rollback, new-file cleanup, post-write validation, production gate rejection, and complete simulation without production mutation.

## Final verification and authorization gate

Implementation may be called ready for **review**, not production use, only when the focused command in Task 8 exits zero, the full `.venv/bin/pytest -q -n 8 --dist loadfile` run has no new attributable failures against its frozen baseline, every fault-matrix case demonstrates exact rollback or `RECOVERY_BLOCKED` as specified, and CLI simulation yields canonical mutation-plan bytes/hash and a validated, immutable copied-root receipt/hash while production input hashes remain unchanged. Require `git diff --check` to exit zero, a clean final implementation worktree, and whole-branch review with no out-of-scope edits. Establish the exact `reviewed_apply_implementation_sha` only after final code review. A separate human-authorized production step then requires the complete Task 7 authorization record, created outside the repository after review of that successful simulation, binding the reviewed implementation SHA, final approved spec/plan hashes, frozen baseline, fixed action, exact simulation-receipt hash, and exact mutation-plan hash. It also requires a clean worktree, expected ancestry, verified maintenance window with all readers quiesced, and fresh independent preflight, replay, staging, validation, and plan construction. Before backups or production writes, the freshly computed plan hash must equal the authorized plan hash; any mismatch leaves production CKL unchanged. A changed transaction requires a new simulation, human review, and authorization. This plan does not execute production apply.
