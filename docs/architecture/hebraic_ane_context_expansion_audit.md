# Hebraic and Ancient Near Eastern Context Expansion - Phase 1 Audit

Audit date: 2026-07-16

Scope: current CKL schema, retrieval, context-building, prompt assembly, and ask-path integration. This audit records the existing request flow and identifies what already supports the next expansion phases. It does not change runtime behavior.

## Executive Summary

The current BHF runtime already performs deterministic CKL lookup before the model call. The primary ask path starts in `bhf_web/routes/ask.py`, flows into `bhf_agent/runner.py::BHFAgent.ask()`, performs CKL retrieval in `bhf_agent/ckl.py` and `framework/canonical_library`, then builds prompts in `bhf_agent/prompts.py` before calling the configured model adapter.

The existing CKL schema already supports several fields that are useful for the Hebraic and Ancient Near Eastern expansion, including `historical_context`, `ancient_near_east_context`, `literary_context`, `covenantal_significance`, `intertextuality`, `new_testament_connections`, `interpretive_notes`, and `sources`. The current inventory also already has book-level metadata such as `authorship_positions`, `date_ranges`, `original_audience`, `historical_setting`, `genre`, `structure`, `major_themes`, `canonical_placement`, `key_people`, `key_places`, `key_events`, `interpretive_disputes`, and `primary_sources`.

The main gaps for the new feature are not in retrieval existence but in schema expressiveness and context-layer separation. The current schema does not yet have dedicated fields for `hebraic_worldview`, `second_temple_context`, `canonical_context`, `later_christian_reception`, or `context_applicability`. Interpretive notes were later structured in Phase 4, and source typing was later upgraded in Phase 5 to use canonical source IDs, `supports` metadata, and the expanded source-type vocabulary while still accepting legacy string sources during migration.

## Current Request Flow

1. The user submits a question to `POST /ask`.
2. `bhf_web/routes/ask.py::ask()` loads config and calls `agent_factory()(config).ask(question)`.
3. `bhf_agent/runner.py::BHFAgent.ask()` orchestrates the request pipeline.
4. The agent initializes context, detects references, classifies genre and question type, loads the profile, checks local knowledge, checks caches, loads session memory, and then looks up CKL context.
5. `bhf_agent/ckl.py::build_canonical_context()` performs the deterministic CKL retrieval.
6. `bhf_agent/runner.py::_build_prompts()` calls `bhf_agent.prompts.build_prompt()` to assemble the system and user prompts.
7. The configured provider adapter is called through `_call_model()`.
8. The model response is normalized, cleaned, validated, and repaired or replaced with a deterministic fallback when needed.
9. `bhf_agent.models.AgentResult` is returned to the web layer.
10. `bhf_web/routes/ask.py` renders `partials/answer.html` with the public answer for ordinary users.

## Primary Modules And Roles

- `bhf_web/routes/ask.py`
  - Receives the user question.
  - Starts the ask flow.
  - Renders the answer partial for the frontend.

- `bhf_agent/runner.py`
  - Owns the end-to-end agent pipeline.
  - Coordinates caches, CKL lookup, prompt construction, model invocation, cleanup, validation, fallback, and observability.

- `bhf_agent/ckl.py`
  - Owns deterministic CKL query building, context assembly, and fallback-answer support.

- `framework/canonical_library/loader.py`
  - Loads the CKL inventory and supports deterministic retrieval and indexing.

- `framework/canonical_library/retrieval.py`
  - Holds the current ranking and scoring signals.

- `framework/canonical_library/context_builder.py`
  - Converts retrieval results into compact prompt context with token budgeting and relationship expansion.

- `framework/canonical_library/schema.py`
  - Validates canonical objects and governance metadata.

- `framework/canonical_library/authoring.py`
  - Provides normalization, auditing, manifest, and migration helpers.

- `bhf_agent/prompts.py`
  - Builds the system and user prompts and injects CKL context.

- `bhf_agent/model_response_validation.py`
  - Removes leaked runtime headings, rejects raw JSON when prose is expected, and blocks retrieval/debug leakage.

- `bhf_agent/output_cleaner.py`
  - Performs final text cleanup before display.

- `bhf_agent.models.AgentResult`
  - Holds the internal agent result.
  - Exposes `public_response()` for normal UI consumption.
  - Exposes `internal_response()` for diagnostics.

## What The Model Sees Today

The prompt currently includes:

- Profile content
- `AGENT_INSTRUCTIONS`
- Answer-mode instructions
- Detected reference and genre context
- Canonical Knowledge Library context when available
- Optional local knowledge
- Optional map context
- Optional session memory
- Output requirements

The canonical prompt instructions already tell the model not to search the CKL itself, not to mention filenames or scores, not to output internal analysis, and not to invent facts or citations.

## Current Places Where The Model Is Asked To Do Extra Work

The runtime does not ask the model to search CKL files directly, but there are still a few non-final-answer paths that matter for the new architecture:

- Structured output path:
  - `bhf_agent/runner.py::_response_contract()` switches to a `search_results` contract when the request is clearly asking for a structured result payload.
  - That path is still model-mediated and is not the same as deterministic CKL retrieval.

- Method-note path:
  - `bhf_agent/prompts.py` can ask for brief method notes when `show_method_notes` is enabled.
  - The prompt still forbids internal analysis leakage, but this is the closest current equivalent to reasoning-style output.

- Debug and diagnostics path:
  - `bhf_agent.models.AgentResult.internal_response()` exposes retrieval IDs, context token counts, and model metadata.
  - `bhf_agent/runner.py` also records broader debug metadata for observability and developer inspection.

## Existing Schema Support Relevant To The New Feature

Already supported:

- `historical_context`
- `ancient_near_east_context`
- `literary_context`
- `covenantal_significance`
- `intertextuality`
- `new_testament_connections`
- `interpretive_notes`
- `sources`
- `related_objects`
- `scripture_references`
- Book-level metadata fields such as `authorship_positions`, `date_ranges`, `original_audience`, `historical_setting`, `genre`, `structure`, `major_themes`, `canonical_placement`, `key_people`, `key_places`, `key_events`, `interpretive_disputes`, and `primary_sources`

Observed in live objects:

- `framework/canonical_library/objects/books/genesis.json`
- `framework/canonical_library/objects/books/joshua.json`
- `framework/canonical_library/objects/institutions/temple.json`
- `framework/canonical_library/objects/faq/what-is-the-second-temple.json`
- `framework/canonical_library/objects/themes/covenant-theme.json`
- `framework/canonical_library/objects/events/council-of-jerusalem.json`
- `framework/canonical_library/objects/word_studies/christos.json`
- `framework/canonical_library/objects/archaeology/city-of-david-excavations.json`

These objects already show the library using historical, ANE, literary, covenantal, interpretive, and source-backed content in the way the new expansion needs.

## Existing Support That Helps Migration

- `CanonicalSource.from_mapping()` already accepts legacy string sources.
- `normalize_sources_field()` already converts legacy source values into structured source objects.
- `framework/canonical_library/authoring.py` already normalizes and validates loaded inventory entries.
- The context builder already uses a fixed token budget and can omit irrelevant fields.
- The context builder now also emits ordered prompt sections and honors answer-mode tiers so compact prompts stay stable without empty filler sections.
- Retrieval ranking already uses weighted signals from the current schema, so the next phase can extend weights rather than replace the retrieval stack.

## Known Problems

- The current schema does not yet separate Hebraic worldview, Second Temple context, canonical context, and later Christian reception into distinct fields.
- The current interpretive notes were not structured enough to track certainty, dispute status, or note type cleanly at the time of this audit; Phase 4 later addressed that gap by adding structured note records.
- The source model now carries canonical IDs, normalized source types, and `supports` metadata while still preserving legacy string migration.
- The context builder and retrieval weights are tuned to the existing fields, and explicit prompt ordering is now in place for later framework guidance and prompt-shaping work.
- The request pipeline already blocks many kinds of leakage, but the prompt assembly still mixes profile text, CKL context, local knowledge, map context, and session memory in one prompt object.

## Phase 1 Conclusion

The runtime is already CKL-first and deterministic. Phase 2 can build on the existing schema and retrieval stack without changing the ask flow, but it will need new schema fields, applicability metadata, and context-builder ordering to support Hebraic, Ancient Near Eastern, Second Temple, and canonical context as separate layers.
