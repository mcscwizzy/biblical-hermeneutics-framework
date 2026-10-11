# Genesis G5B Jacob–Esau Return Evidence Expansion Implementation Plan

> **For agentic workers:** Execute implementation inline on the user-created feature branch under the supplied G5B transaction authorization. Use one fresh reviewer for the final whole-branch review as required by the execution workflow.

**Goal:** Add one isolated, source-locked `cultural_background` object for Genesis 31–36 and prove that exactly those six chapter preparation/synthesis identities change.

**Architecture:** Follow the isolated passage-domain pattern from G2R2 through G5A. Keep all direct Scripture applicability inside Genesis 31–36, use object-local identity-preserving source aliases when existing sources already have owners, and add only one-way typed relationships to existing objects.

**Tech Stack:** CKL JSON, Python chapter preparation/synthesis and G0 classifier, pytest isolation suites, runtime CKL SQLite builder, Git.

**Spec:** User-supplied `GENESIS_G5B_JACOB_ESAU_RETURN_EVIDENCE_EXPANSION` specification in the active conversation.

## Global Constraints

- Base: clean `origin/master` commit `f752f9841a0ffc32e167afe7b79a4ecd62e475e4`; branch `feat/genesis-g5b-jacob-esau-return`.
- Direct evidence applicability is strictly Genesis 31–36; do not begin Genesis 37–50.
- Add only `genesis-jacob-esau-return-context` at `framework/canonical_library/objects/cultural_background/genesis-jacob-esau-return-context.json` plus its CKL manifest entry.
- Historical source-owner rows changed must equal `0`; create local aliases preserving full bibliographic identity when needed.
- Do not modify shared CKL objects, Commentary, or Commentary v1.2; do not merge or deploy.
- Exact changed preparation/synthesis identity set must be Genesis 31–36 across all 1,189 chapter identities; every specified control remains byte/identity exact to base.
- Stop before commit/push if any required gate fails or any unrelated chapter changes.

## Review Focus

- Ethical and lexical treatment of Dinah, Shechem, the deception, and massacre must represent the text without euphemism, invented details, ethnic generalization, or claims of divine command.
- Teraphim, marriage/property custom, covenant boundary practice, and comparative ANE material must remain qualified and must not be collapsed into one proven motive or universal law.
- Genesis 32's opponent, Israel wordplay, injury, and dietary note must distinguish the text from Jacob's interpretation and later reception.
- Genesis 36 genealogy, Anah's difficult term, Edomite kings, and 36:31 chronology must preserve uncertainty and avoid single-verse certainty.
- Local source aliases, one-way typed links, and comparative reception must leave historical owners and all out-of-scope chapter identities unchanged.

---

### Task 1: Freeze the base and audit Genesis 31–36

**Files:** Create `g5b-existing-evidence-audit.json` and `g5b-jacob-esau-return-evidence-plan.json` under `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/`.

- [x] Capture base commit, CKL object/inventory identities, historical source-owner rows, runtime DB identity, frozen Commentary v1.2 identities, and all 1,189 preparation/synthesis identities.
- [x] Record the six supplied G0 starting classifications and dimension-level gaps from the established G0 classifier; do not infer coverage from evidence counts.
- [x] Freeze the full supplied control set and verify each control equals the clean base.

### Task 2: Research, source-lock, and curate passage-specific evidence

**Files:** Create `g5b-source-lock.json`, `g5b-source-ownership-audit.json`, `g5b-comparative-applicability-audit.json`, `g5b-candidate-evidence.json`, and `g5b-candidate-replay-final.json` under the G5B artifact directory.

- [x] Research and represent the requested Genesis 31–36 topics, responsible interpretations, and explicit claim dispositions. Cover every supplied chapter focus without padding or duplicating a literary observation across chapters.
- [x] Keep Hosea 12, Genesis 28/37/49, other later Scripture, and comparative ANE material contextual rather than direct applicability anchors.
- [x] Audit source ownership before apply. Use aliases preserving author/editor, title, publisher, year, locator, stable identifier, and bibliographic work identity; require zero historical owner-row changes.
- [x] Replay each candidate; require direct references only in Genesis 31–36, synthesis usability, typed-target validity, and no reverse applicability.

### Task 3: Test and stage the isolated object

**Files:** Create `tests/test_genesis_g5b_jacob_esau_return_isolation.py`, `.bhf-data/.../staging/new-object.json`, and `g5b-production-apply-manifest.json`.

- [x] Write and run a failing isolation test before applying the object. Pin object ID/type/path, local source resolution, direct-reference bounds, one-way links, candidate parity, and synthesis consumption.
- [x] Validate staged schema, source provenance, typed targets, relationships, Scripture references, and comparative-applicability rules.
- [x] Create the production apply manifest and confirm pre-apply source ownership remains unchanged.

### Task 4: Apply and verify the six-chapter impact

**Files:** Add the new object and one CKL manifest entry; create `g5b-post-apply-validation.json`, `g5b-g0-target-results.json`, `g5b-chapter-impact.json`, `g5b-final-ckl-identities.json`, and `g5b-runtime-db-preparation-verification.json`.

- [x] Recompute preparation, synthesis, and G0 dimension classifications for Genesis 31–36. If any chapter remains below GOOD, name the missing dimension without padding.
- [x] Compare all 1,189 identities; require the exact changed set Genesis 31–36 and base-exact results for all controls.
- [x] Confirm CKL object count increases by one, runtime SQLite matches the JSON inventory, no reverse links or historical source-owner changes exist, and Commentary v1.2 frozen identities remain exact.
- [x] Reconcile any inherited historical test snapshots only in a new G5B reconciliation artifact; preserve original results.

### Task 5: Run all gates and close the branch

**Files:** Create `g5b-validation-report.json`, `g5b-review-digest.md`, and (if needed) `g5b-regression-reconciliation.json`; complete the G5B artifact set and this plan; commit and push only after every gate passes.

- [x] Run candidate replay; new-object schema; source/provenance/owner; typed-target, relationship, and Scripture-reference; whole-CKL; Genesis 31–36 preparation/synthesis/G0; comparative-applicability, legacy-fallback, and isolated-owner regressions; previous Genesis transaction isolation suites; representative controls; exact all-1,189 impact; runtime DB; frozen Commentary; and `git diff --check` gates.
- [x] Reproduce any known stale historical tests on the clean base before classifying them as inherited; do not rewrite old snapshots opportunistically.
- [x] Generate the final validation report and review digest with all 32 requested completion-report fields.
- [x] Commit and push `feat/genesis-g5b-jacob-esau-return`; verify local HEAD equals upstream HEAD and the worktree is clean. Do not merge or deploy.
