# Current AI Request Flow

Audit date: 2026-07-15

Scope: reflects the current runtime request path.

## Summary

The primary user-question path already performs deterministic CKL lookup before the model call and now short-circuits repeat requests through retrieval, context, and response caches. The request path also emits a structured observability log with request ID, CKL timing, cache behavior, model usage, and fallback status. The frontend now receives only the final answer for ordinary ask responses; CKL metadata is only surfaced in explicit debug or saved-study views. A developer-only retrieval inspector is now available in debug ask responses and via `POST /api/debug/ckl-search`. The CKL pipeline is now gated by explicit rollout controls, including a shadow mode that performs retrieval without injecting CKL context into the model prompt. When the model backend fails or returns invalid output, the runner now substitutes a deterministic CKL fallback answer or a controlled empty search-results payload instead of surfacing the raw failure. The separate Bible-search fallback route now uses deterministic CKL-backed passage suggestions and no longer calls the model.

The main request flow today is:

`User question -> request route -> BHFAgent.ask() -> CKL retrieval cache -> CKL context cache -> response cache -> prompt build -> model call -> output cleanup/validation -> deterministic fallback if needed -> response render`

There is also a separate deterministic Bible search fallback route that asks the CKL for likely passages and returns a small, structured result payload without calling the model.

## Entry Points

### Primary ask flow

- `bhf_web/routes/ask.py::register_ask_routes`
- `POST /ask`
- `POST /ask/jobs`
- `POST /api/debug/ckl-search`

### Secondary deterministic search flow

- `bhf_web/jobs.py::run_search_fallback_job`
- `POST /api/bible/search/fallback/jobs`

## Current End-to-End Flow

1. The web UI submits the question to `bhf_web/routes/ask.py::ask`.
2. The route loads defaults with `bhf_web/forms.py::load_web_defaults` and converts form values with `config_from_form`.
3. The route calls `agent_factory()(config).ask(question)`.
4. `bhf_agent/runner.py::BHFAgent.ask` orchestrates the pipeline:
   - `_initialize_context`
   - `_detect_reference` via `bhf_agent.references.detect_reference`
   - `_classify_genre` via `bhf_agent.genre.classify_genre`
   - `_classify_question_type` via `bhf_agent.question_types.classify_question_type`
   - `_load_profile`
   - `_lookup_local_knowledge` via `bhf_agent.knowledge.lookup_local_knowledge`
   - `_lookup_canonical_library`
   - `_lookup_public_answer_cache`
   - `_load_session_memory`
   - `_lookup_response_cache`
   - `_build_prompts`
   - `_call_model`
   - `_clean_output`
   - `_validate_response`
   - `_repair_response` when enabled
   - `_apply_deterministic_fallback` when the model output is unavailable or invalid
   - `_finalize_result`
   - `_store_response_cache`
   - `_save_session_turn`
   - `_to_agent_result`
5. `_lookup_canonical_library` calls `bhf_agent.ckl.build_canonical_context` and `bhf_agent.ckl.format_canonical_context_for_prompt`.
6. `_lookup_response_cache` computes a prompt-context hash from the canonical context key, local knowledge, map context, session memory, and prompt version, then returns a cached answer when the exact request has already been answered.
7. `_build_prompts` calls `bhf_agent.prompts.build_prompt`, which assembles the system prompt.
8. `_call_model` sends the prompt to the configured adapter:
   - `bhf_agent/adapters/openai_compatible.py::OpenAICompatibleAdapter`
   - `bhf_agent/adapters/ollama.py::OllamaAdapter`
9. The response is normalized with `bhf_agent/model_response_validation.normalize_model_response` and the legacy cleanup helper is applied inside that normalization step.
10. The sanitized response is validated with `bhf_agent/validation.validate_response`.
11. `_store_response_cache` records the final answer, validation outcome, and cleanup details for repeat use.
12. The result is packaged into `bhf_agent/models.AgentResult`.
13. `bhf_web/routes/ask.py` now sends a public answer payload to the UI by default.
14. `bhf_web/services/web_helpers.result_metadata`, `bhf_web/services/ckl_inspector.py`, and `bhf_web/templates/partials/answer.html` only render CKL metadata when a debug path or saved-study view explicitly supplies it.
15. `bhf_web/routes/debug.py` exposes a developer-only CKL search inspection endpoint without invoking the model.

## Current Modules And Responsibilities

- `bhf_web/routes/ask.py`
  - Receives the user question.
  - Starts the ask job or direct ask call.
  - Sends only the answer text to the normal template context.
  - Passes canonical context metadata only when debug mode is explicitly enabled.
- `bhf_web/routes/debug.py`
  - Exposes a developer-only CKL inspection endpoint.
  - Returns deterministic retrieval traces without invoking the model.
- `bhf_web/jobs.py`
  - Runs background ask jobs.
  - Provides the deterministic search-fallback job path.
  - Builds deterministic CKL-backed passage suggestions for the Bible-search fallback.
- `bhf_agent/runner.py`
  - Owns the end-to-end agent pipeline.
  - Loads CKL, builds prompts, manages deterministic cache layers, emits request observability logs, calls the model, cleans and validates output, substitutes deterministic fallback text when needed, and converts the final result.
- `bhf_agent/ckl.py`
  - Deterministic CKL query assembly.
  - Context selection and token budgeting.
  - CKL prompt formatting.
- `bhf_agent/observability.py`
  - Request-level observability config and usage normalization helpers.
- `framework/canonical_library/runtime_cache.py`
  - In-memory retrieval, context, and response caches keyed by CKL inventory and prompt versions.
- `framework/canonical_library/loader.py`
  - Loads the CKL inventory from disk.
  - Builds indexes.
  - Exposes deterministic retrieval helpers.
- `framework/canonical_library/context_builder.py`
  - Builds compact CKL context packages.
  - Handles relationship expansion and token-aware rendering.
- `framework/canonical_library/retrieval.py`
  - Contains deterministic scoring and retrieval helper types.
- `framework/canonical_library/schema.py`
  - Validates CKL objects and governance metadata.
- `bhf_agent/prompts.py`
  - Builds the system and user prompts.
  - Appends CKL context and local knowledge to the system prompt.
- `bhf_agent/model_response_validation.py`
  - Normalizes model output into answer-only text for ordinary asks.
  - Keeps a legacy structured JSON compatibility branch for older search callers.
  - Removes leaked runtime headings and strips internal analysis blocks before display.
- `bhf_agent/output_cleaner.py`
  - Removes obvious leaked runtime headings after generation.
- `bhf_agent/validation.py`
  - Performs method-oriented response validation.
- `bhf_web/services/web_helpers.py`
  - Formats answer metadata for debug and saved-study views.
- `bhf_web/services/ckl_inspector.py`
  - Builds developer-facing CKL retrieval traces and prompt previews.
- `bhf_web/templates/partials/answer.html`
  - Displays the answer and only renders canonical context or metadata when those fields are explicitly provided.

## What The Model Sees Today

The main prompt path currently includes:

- Compact hermeneutical safeguards
- One unified final-answer instruction set
- Detected reference and genre context
- CKL prompt context, including query, retrieval method, retrieved object IDs, topic counts, status filters, and compact object blocks
- Local curated knowledge
- Map context when applicable
- Session memory when enabled

The model is not asked to perform CKL retrieval inside the main ask path, but it does see CKL-derived context that was assembled upstream.
If CKL retrieval finds only weak matches, the prompt receives a short no-strong-match instruction instead of a full context dump.

## Where Internal Retrieval Data Reaches The UI

- `bhf_web/routes/ask.py` passes only the answer to the answer template for ordinary requests.
- In debug mode, the route can still pass CKL context and object IDs to the template.
- In debug mode, the route also renders a developer retrieval inspector with search analysis, result scores, selected prompt facts, and prompt previews.
- `bhf_web/services/web_helpers.result_metadata` includes:
  - canonical object IDs
  - canonical retrieval method
  - local knowledge keys
  - adapter errors
- `bhf_web/templates/partials/answer.html` renders the canonical context section and metadata only when those fields are supplied by the caller.
- `bhf_agent/observability.py` emits structured per-request logs that stay redacted by default and only add verbose developer details when debug mode explicitly enables them.
- `bhf_web/routes/debug.py::debug_ckl_search` returns deterministic CKL search traces without calling the model.

## Deterministic Bible Search Fallback

- `bhf_web/jobs.py::run_search_fallback_job`
  - Uses deterministic CKL retrieval and local Bible data to suggest likely passages.
  - Returns a compact JSON payload with `results`, `reason`, and `confidence`.
  - Does not call the model.

## Known Problems

- CKL context is still appended to the model prompt as a prebuilt block, so the model can see retrieval metadata.
- The frontend no longer sees retrieval metadata in ordinary ask responses.
- Debug and saved-study views can still display controlled metadata.
- Output cleanup is now paired with structured-response normalization, but the model can still emit malformed output that must be rejected or repaired.
- Validation remains method-oriented after response normalization.
- The current CKL prompt layer still mixes retrieval, prompt construction, and rendering concerns.
- Response cache invalidation depends on CKL inventory fingerprints, selected entry versions, prompt version, model signature, and the canonical context cache key.
- Observability logging is intentionally summary-first so it can measure latency and cache behavior without exposing raw prompts or model text.
- The developer retrieval inspector is debug-only and does not alter the ordinary answer payload.
