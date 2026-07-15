# Current AI Request Flow

Audit date: 2026-07-15

Scope: reflects the current runtime after phase 9; the original audit notes are preserved below for continuity.

## Summary

The primary user-question path already performs deterministic CKL lookup before the model call. The frontend now receives only the final answer for ordinary ask responses; CKL metadata is only surfaced in explicit debug or saved-study views.

The main request flow today is:

`User question -> request route -> BHFAgent.ask() -> CKL/context build -> prompt build -> model call -> output cleanup/validation -> response render`

There is also a separate model-assisted Bible search fallback route that asks the model to return structured JSON results.

## Entry Points

### Primary ask flow

- `bhf_web/routes/ask.py::register_ask_routes`
- `POST /ask`
- `POST /ask/jobs`

### Secondary model-assisted search flow

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
   - `_build_prompts`
   - `_call_model`
   - `_clean_output`
   - `_validate_response`
   - `_repair_response` when enabled
   - `_finalize_result`
   - `_save_session_turn`
   - `_to_agent_result`
5. `_lookup_canonical_library` calls `bhf_agent.ckl.build_canonical_context` and `bhf_agent.ckl.format_canonical_context_for_prompt`.
6. `_build_prompts` calls `bhf_agent.prompts.build_prompt`, which assembles the system prompt.
7. `_call_model` sends the prompt to the configured adapter:
   - `bhf_agent/adapters/openai_compatible.py::OpenAICompatibleAdapter`
   - `bhf_agent/adapters/ollama.py::OllamaAdapter`
8. The response is normalized with `bhf_agent/model_response_validation.normalize_model_response` and the legacy cleanup helper is applied inside that normalization step.
9. The sanitized response is validated with `bhf_agent/validation.validate_response`.
10. The result is packaged into `bhf_agent/models.AgentResult`.
11. `bhf_web/routes/ask.py` now sends a public answer payload to the UI by default.
12. `bhf_web/services/web_helpers.result_metadata` and `bhf_web/templates/partials/answer.html` only render CKL metadata when a debug path or saved-study view explicitly supplies it.

## Current Modules And Responsibilities

- `bhf_web/routes/ask.py`
  - Receives the user question.
  - Starts the ask job or direct ask call.
  - Sends only the answer text to the normal template context.
  - Passes canonical context metadata only when debug mode is explicitly enabled.
- `bhf_web/jobs.py`
  - Runs background ask jobs.
  - Provides the search-fallback job path.
  - Parses the search-fallback model response as JSON.
- `bhf_agent/runner.py`
  - Owns the end-to-end agent pipeline.
  - Loads CKL, builds prompts, calls the model, cleans and validates output, and converts the final result.
- `bhf_agent/ckl.py`
  - Deterministic CKL query assembly.
  - Context selection and token budgeting.
  - CKL prompt formatting.
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
  - Preserves structured JSON for the search fallback contract.
  - Removes leaked runtime headings and strips internal analysis blocks before display.
- `bhf_agent/output_cleaner.py`
  - Removes obvious leaked runtime headings after generation.
- `bhf_agent/validation.py`
  - Performs method-oriented response validation.
- `bhf_web/services/web_helpers.py`
  - Formats answer metadata for debug and saved-study views.
- `bhf_web/templates/partials/answer.html`
  - Displays the answer and only renders canonical context or metadata when those fields are explicitly provided.

## What The Model Sees Today

The main prompt path currently includes:

- Profile content
- `AGENT_INSTRUCTIONS`
- Answer-mode instructions
- Detected reference and genre context
- CKL prompt context, including query, retrieval method, retrieved object IDs, topic counts, status filters, and compact object blocks
- Local curated knowledge
- Map context when applicable
- Session memory when enabled

The model is not asked to perform CKL retrieval inside the main ask path, but it does see CKL-derived context that was assembled upstream.

## Where Internal Retrieval Data Reaches The UI

- `bhf_web/routes/ask.py` passes only the answer to the answer template for ordinary requests.
- In debug mode, the route can still pass CKL context and object IDs to the template.
- `bhf_web/services/web_helpers.result_metadata` includes:
  - canonical object IDs
  - canonical retrieval method
  - local knowledge keys
  - adapter errors
- `bhf_web/templates/partials/answer.html` renders the canonical context section and metadata only when those fields are supplied by the caller.

## Where The Model Is Still Asked To Search Or Return Structured Retrieval Data

- `bhf_web/jobs.py::bible_search_fallback_prompt`
  - Asks the model to identify likely Bible passages.
  - Explicitly requests a JSON object with a `results` array.
  - This is a model-assisted retrieval path, not a narrator-only answer path.

## Known Problems

- CKL context is still appended to the model prompt as a prebuilt block, so the model can see retrieval metadata.
- The frontend no longer sees retrieval metadata in ordinary ask responses.
- Debug and saved-study views can still display controlled metadata.
- The search-fallback route uses the model as a search assistant and returns structured retrieval output.
- Output cleanup is now paired with structured-response normalization, but the model can still emit malformed output that must be rejected or repaired.
- Validation remains method-oriented after response normalization.
- There is no dedicated CKL-only retrieval service boundary yet under `framework/canonical_library/retrieval/`.
- The current CKL prompt layer still mixes retrieval, prompt construction, and rendering concerns.

## Notes For The Next Phase

- Phase 2 should introduce a framework-owned deterministic retrieval service that does not call a model.
- Phase 3 should formalize CKL schema validation behind a stable schema package.
- The main ask path should keep deterministic CKL retrieval ahead of model invocation.
- Ordinary ask responses now contain only the final answer; developer and saved-study views remain opt-in.
- Continue with phase 10 model response validation.
