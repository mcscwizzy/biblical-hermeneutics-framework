# Genesis G4A Abraham Call and Covenant Evidence Expansion Implementation Plan

> **For agentic workers:** Execute this plan inline under the user's transaction authorization. Do not delegate.

**Goal:** Add one isolated, source-locked `cultural_background` object for Genesis 12–17 and prove the change affects only those six chapter inputs.

**Architecture:** Follow the G2R2/G3 isolated-object pattern. Keep all direct applicability anchors within Genesis 12–17, put local identity-preserving source aliases on the new object, and use only one-way typed links to existing CKL objects.

**Tech Stack:** CKL JSON, Python preparation and validation APIs, pytest regression suites, runtime CKL SQLite builder, Git.

**Spec:** User's `GENESIS_G4A_ABRAHAM_CALL_COVENANT_EVIDENCE_EXPANSION` request in this conversation.

## Global Constraints

- Base on latest clean `origin/master` after G3 merge; branch `feat/genesis-g4a-abraham-call-covenant`.
- Scope direct evidence applicability to Genesis 12–17; do not begin Genesis 18–25.
- Add only `genesis-abraham-call-covenant-context` at `framework/canonical_library/objects/cultural_background/genesis-abraham-call-covenant-context.json`.
- Preserve all historical source-owner rows; required result is zero changed rows.
- Do not modify shared legacy objects, Commentary prose, or Commentary v1.2 package; do not merge or deploy.
- Exact changed chapter set must be Genesis 12, 13, 14, 15, 16, and 17 across all 1,189 chapter inputs.
- Run the user-specified candidate, CKL, preparation, synthesis, classification, applicability, regression, control, runtime DB, frozen Commentary, and diff gates.

## Review Focus

- Comparative and later reception references cannot become applicability anchors — comparative-applicability audit and candidate replay.
- Adding one local source alias cannot change an old source owner or chapter input — source-owner audit and 1,189-chapter identity gate.
- Every accepted item must be passage-specific, source-backed, and synthesis-usable — preparation/synthesis replay and G0 dimension classification.
- New typed relationships cannot create reverse chapter impact — relationship validation and exact impact gate.
- Frozen Commentary v1.2 identities must remain equal to the base capture — package validation and base-to-final identity comparison.

---

### Task 1: Capture the clean G3 base and audit existing evidence

**Files:** Create the G4A deterministic audit artifacts under `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/`.

- [ ] Record exact base commit, CKL inventory/object count, runtime DB identity, frozen Commentary v1.2 identities, all 1,189 chapter preparation/synthesis identities, controls, and Genesis 12–17 existing evidence/dimension audit.
- [ ] Reproduce the G0 starting classifications and record passage-specific gaps without relying on raw count.

### Task 2: Lock sources and dispositions before staging evidence

**Files:** Create `g4a-evidence-plan.json`, `g4a-source-lock.json`, and `g4a-source-ownership-audit.json`.

- [ ] Research required claims using primary sources and established scholarship; classify claims and source records as accepted, rejected, unresolved, or withheld.
- [ ] Use local identity-preserving aliases for works already owned by another object; prove bibliographic identity and zero historical owner-row changes before apply.

### Task 3: Build and replay the isolated candidate object

**Files:** Create the candidate queue, comparative-applicability audit, and production apply manifest; stage the new CKL object only after the source lock passes.

- [ ] Author concise, qualified evidence across Genesis 12–17 and promise progression; use only direct chapter-specific anchors; add only safe one-way typed relationships.
- [ ] Replay every accepted item and validate staged schema, provenance, source IDs, scripture references, typed targets, relationships, and synthesis availability.

### Task 4: Apply and verify exact chapter isolation

**Files:** Create the validation report, chapter impact report, and any separate reconciliation artifact required by observed failures; update only the new object and CKL manifest in production.

- [ ] Recompute Genesis 12–17 G0 dimensions, classes, preparation/synthesis counts, and hashes; retain Genesis 15 quality.
- [ ] Compare every chapter input to the base and require exactly Genesis 12–17 changed; verify required controls and no change to Genesis 22.
- [ ] Confirm stale future Commentary inputs for Genesis 12–17 while preserving the frozen v1.2 package exactly.

### Task 5: Run all gates and close the branch

**Files:** Create `g4a-review-digest.md`; commit all G4A artifacts and the isolated CKL object.

- [ ] Run every requested test and validation, including previous Genesis transaction regressions, runtime DB rebuild/verification, frozen Commentary validation, and `git diff --check`.
- [ ] Record exact changed paths, test outcomes, base/final identities, object/source counts, and merge assessment.
- [ ] Commit and push the named branch; verify local HEAD equals its remote tracking HEAD and the working tree is clean. Do not merge or deploy.
