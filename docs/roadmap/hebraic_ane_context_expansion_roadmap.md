# Hebraic and Ancient Near Eastern Context Expansion Roadmap

Resume aid for the CKL expansion stream. This file is the handoff note for continuing the feature safely in future sessions.

Last audited: 2026-07-16

Current phase: Phase 12 complete. Next phase: none in this roadmap.

## Current State

- The CKL request pipeline is already deterministic and runs before the model call.
- The current CKL schema already covers historical, Ancient Near Eastern, literary, covenantal, intertextual, New Testament, interpretive, and source fields.
- The new Hebraic/Second Temple/canonical/later-reception layers are now first-class schema fields with backward-compatible defaults and retrieval support.
- The context builder now emits ordered prompt sections with answer-mode tiers so compact prompts keep summary, scripture references, context layers, cautions, and sources in a stable sequence.
- The compact context builder now also reserves a small per-entry token floor so later high-priority entries keep their summaries instead of collapsing to title-only stubs under tight budgets.
- The framework prompt now carries explicit interpretive-order guardrails separate from CKL facts, covering literary, historical, Ancient Near Eastern, Hebraic, Second Temple, canonical, Christological, and application boundaries.
- Interpretive notes are now structured but still accept legacy strings during migration so older inventory files stay valid.
- Source records now have canonical IDs, source-type normalization, and `supports` metadata while still accepting legacy string sources during migration.
- Review metadata now separates AI provenance from human review. `generated_by` tracks Codex or other non-human creation/migration workflows, `reviewed_by` is reserved for human reviewers, and `human_review_required` marks items that still need human sign-off.
- Validation now reports actionable warnings for legacy inventory hygiene issues and errors for newly authored records that violate the expanded schema rules.
- Test coverage now includes semantic warning buckets, empty applicable context detection, ordered prompt-section construction, Hebrews/Second Temple prompt regressions, and unreviewed-content retrieval filtering.
- Documentation now explains the validation-warning split, production retrieval filtering, and authoring boundaries for the expanded context layers.
- The next work should add structure without rewriting the whole CKL architecture.

## Update Protocol

- After each phase, update this roadmap and the architecture note if the runtime picture changes.
- Keep the handoff concise enough that the next session can pick up without re-auditing the entire codebase.
- Do not mark phases complete unless the relevant code or docs have actually been changed and checked.

## Phase Tracker

- Phase 1 - Audit Existing Schema and Runtime: complete
- Phase 2 - Add Context Layers: complete
- Phase 3 - Add Interpretation-Layer Metadata: complete
- Phase 4 - Structure Interpretive Claims: complete
- Phase 5 - Improve Source Governance: complete
- Phase 6 - Add Context Builder Ordering: complete
- Phase 7 - Add Framework Guidance: complete
- Phase 8 - Populate a High-Quality Pilot Set: complete
- Phase 9 - Fix Review Metadata: complete
- Phase 10 - Add Validation Rules: complete
- Phase 11 - Add Tests: complete
- Phase 12 - Documentation: complete

## Immediate Next Move

This roadmap is complete. Use the general CKL roadmap or a new feature brief for future expansion work.
