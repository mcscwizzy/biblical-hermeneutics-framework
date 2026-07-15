# Canonical Knowledge Library Retrieval Plan

Purpose: carry the CKL-first retrieval refactor forward across sessions without needing to rediscover the current state.

Resume rule: continue from the next unchecked phase without asking for confirmation unless a requirement is actually missing or contradictory.

## Current State

- Phase 1 audit is complete.
- Phase 2 deterministic CKL retrieval service is complete under `framework/canonical_library/retrieval/`.
- Phase 3 schema standardization is complete under `framework/canonical_library/schema/`.
- Phase 4 initial search indexing lifecycle is complete with in-memory caching and refresh helpers.
- Phase 5 deterministic query analysis is complete with facet detection and scripture-reference parsing.
- Phase 6 ranking and relevance thresholds are complete with direct-match preference, thresholding, and near-duplicate suppression.
- The live code already performs deterministic CKL lookup before the main model call.
- The current implementation now projects CKL retrieval results into a compact prompt-safe context block and uses sectioned prompt instructions that tell the model to narrate retrieved material rather than search or expose internals.
- Normal ask responses now surface only the answer text, while debug and saved-study views retain controlled access to metadata.
- The model-assisted Bible search fallback route still uses the model to return structured retrieval data.
- Model output normalization now parses structured answer envelopes, strips internal prompt leakage, and keeps the search-fallback JSON contract intact.
- Deterministic fallback answers now replace model/provider failures with either a CKL summary or a controlled empty search-results payload.
- Runtime caches now short-circuit repeated retrieval, context, and response work while staying keyed to CKL and prompt versions.
- Request observability now logs CKL timing, cache behavior, model usage, and fallback outcomes without exposing prompts or model text.

## Reusable Baseline That Already Exists

- `framework/canonical_library/loader.py` loads CKL objects, builds indexes, and exposes deterministic retrieval helpers.
- `framework/canonical_library/retrieval.py` already contains deterministic scoring and ranking primitives.
- `framework/canonical_library/context_builder.py` now builds both the rich retrieval package and a compact prompt-safe CKL context projection with token budgeting.
- `framework/canonical_library/schema.py` already validates CKL objects and governance metadata.
- `bhf_agent/ckl.py` already assembles CKL queries and prompt context from deterministic retrieval results.
- `bhf_agent/prompts.py` now separates system instructions, CKL context guidance, optional conversation context, and output requirements in the model prompt.

## Refactor Goals

- Search CKL before any request is sent to an AI model.
- Keep the model as a narrator and synthesizer only.
- Stop exposing retrieval metadata in ordinary user responses.
- Make CKL retrieval deterministic, measurable, and testable without an AI model.
- Preserve the CKL JSON files as the source of truth.

## Phase Status

| Phase | Status | Resume point |
| --- | --- | --- |
| 1 - Audit the Existing Request Pipeline | complete | Architecture note created in `docs/architecture/current_ai_request_flow.md` |
| 2 - Create a CKL Retrieval Service | complete | Framework-owned deterministic search layer implemented under `framework/canonical_library/retrieval/` |
| 3 - Standardize CKL Document Schemas | complete | Stable schema package and validator implemented under `framework/canonical_library/schema/` |
| 4 - Build the Initial Search Index | complete | In-memory cached indexing with refresh helpers and build logging implemented |
| 5 - Implement Query Analysis Without an LLM | complete | Deterministic query normalization, facet detection, and scripture-reference parsing implemented |
| 6 - Add Ranking and Relevance Thresholds | complete | Weighted ranking, thresholds, direct-match preference, and deduplication implemented |
| 7 - Create a Controlled Context Builder | complete | Compact prompt-safe CKL context projection implemented |
| 8 - Simplify the Model Prompt | complete | Sectioned prompt instructions now frame CKL context as explanatory input |
| 9 - Separate Internal and User-Facing Responses | complete | Normal ask responses now return only the answer |
| 10 - Add Model Response Validation | complete | Enforce answer-only output and a structured adapter contract |
| 11 - Add Fallback Behavior | complete | Deterministic CKL summary and empty search-result fallbacks now replace model/provider failures |
| 12 - Add Caching | complete | Retrieval, context, and response caches are keyed by CKL and prompt versions |
| 13 - Add Observability | complete | Structured per-request observability logs now capture retrieval timing, model timing, and cache behavior |
| 14 - Create a Developer Retrieval Inspector | pending | Add a diagnostics endpoint or panel for CKL search inspection |
| 15 - Testing | pending | Add unit, integration, and golden-query coverage |
| 16 - Rollout Strategy | pending | Gate the new pipeline behind a feature flag and shadow mode |

## Implementation Order

1. Build the deterministic retrieval service and keep it model-free.
2. Formalize the schema boundary so invalid CKL entries are rejected early.
3. Add indexing, query analysis, and ranking.
4. Tighten prompt construction so only a compact context block reaches the model.
5. Separate internal metadata from user-facing responses.
6. Add validation, fallback behavior, caching, and observability.
7. Finish with a developer inspector and rollout controls.

## Working Constraints

- Do not move to the next phase until the current phase has a concrete, testable artifact.
- Do not use the model to decide which CKL files to load.
- Do not expose file paths, retrieval scores, or debug metadata to ordinary users.
- Preserve backward compatibility where practical while the refactor is in flight.
- Prefer deterministic search primitives first; defer embeddings and vector search.

## Open Risks To Track

- The current ask path still mixes retrieval metadata into the prompt.
- Debug and saved-study views still render controlled canonical context and metadata, so phase 10+ must keep ordinary ask responses answer-only.
- The search-fallback route is model-driven and does not fit the narrator-only rule.
- CKL schema and retrieval code are split across existing modules, so the refactor will need a careful migration path.

## Next Session Start Point

- Phase 8 prompt simplification is complete.
- Phase 9 internal and user-facing response separation is complete.
- Phase 10 model response validation is complete.
- Phase 11 fallback behavior is complete.
- Phase 12 caching is complete.
- Phase 13 observability is complete.
- Continue with the developer retrieval inspector in Phase 14.
