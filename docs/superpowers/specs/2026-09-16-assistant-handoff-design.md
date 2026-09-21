# BHF Assistant Handoff Design

## Goal

Make the BHF web application model-independent at runtime. BHF will own deterministic Scripture, commentary, CKL, lexicon, archaeology, cross-reference, notes, and study experiences; conversational interpretation will be handed off to a configurable external BHF assistant.

## Release boundary

Implementation starts from `origin/master` at `7ae5e1560d16a1453e0064c05933949669fa6048`, after the Commentary v1.2 merge. The `commentary-v1.2` tag and all frozen Commentary v1.2 artifacts, hashes, descriptors, manifests, and content are out of scope and must remain unchanged.

## Current audit and classification

### END_USER_RUNTIME — remove or replace

- `bhf_web/templates/index.html`: AI setup dialog, provider/model settings, hidden AI form fields, internal Ask workspace, and AI presentation controls.
- `bhf_web/static/model-settings.js`: browser provider state, encrypted OpenRouter token storage, model selection, provider health checks, request headers, and AI presentation preference.
- `bhf_web/static/companion-context.js`, `htmx-search.js`, and map search code: provider-header and AI-presentation request paths.
- `bhf_web/routes/ask.py`: interactive end-user inference routes and job polling/reset surface.
- `bhf_web/routes/study.py`: optional AI passage-presentation generation endpoint/path; deterministic companion context remains.
- `bhf_web/jobs.py`: web Ask/presentation job machinery used only by removed interactive inference.
- `bhf_web/presentation_runtime.py`, `bhf_web/ai_config.py`, and AI-only form/configuration helpers.
- `bhf_web/app.py` and `bhf_web/routes/debug.py`: provider runtime initialization and `/api/llm/health` diagnostics.
- Runtime-facing `LLM_PROVIDER`, `BHF_BASE_URL`, `BHF_MODEL`, `BHF_API_KEY`, `OLLAMA_*`, and context/output controls where they only configure web inference.

### MAINTAINER_GENERATION — preserve

- `bhf_agent.runner`, `bhf_agent.adapters`, `bhf_agent.providers`, model-response validation, prompt/context tooling, commentary generators, production runtime, evaluation, renderer qualification, and release engineering.
- Adapter/provider tests and commentary production tests remain unless a test is exclusively coupled to the deleted web surface.

### SHARED — preserve and decouple

- Core `bhf_agent` provider abstractions remain available to offline/maintainer workflows. Web application imports and runtime initialization will no longer instantiate or expose them.
- Deterministic companion context and study database services remain available without a provider.

### DEAD or UNKNOWN

Every remaining AI-related occurrence will be rechecked after implementation. Historical documentation and maintainer-only references are acceptable; normal reader/settings UX must contain no BYO-model terminology.

## Runtime architecture

Add one generic public destination setting using existing runtime configuration conventions:

```text
BHF_ASSISTANT_URL
```

Default:

```text
https://chatgpt.com/g/g-6a36d3641a1c8191afa101ed50a927e9-biblical-hermeneutics-framework-bhf
```

Expose the URL in the serialized browser runtime configuration as a generic assistant destination. It contains no secret and must not be confused with a provider or model setting. The modal consumes the destination through runtime configuration, so a future Plugin or other supported assistant destination only changes configuration.

The web runtime must make no LLM/provider request while loading the reader, navigating, opening the modal, preparing text, or browsing deterministic resources.

## Ask BHF interaction

Replace the internal Ask workspace with one focused handoff composer. The reader/companion retains one clear `Ask BHF` action in the appropriate Bible-reading/evidence context. The modal:

1. Reads `window.BHFStudySelection.getState()` at open time.
2. Displays the current book/chapter and any already-supported selected reference/range.
3. Accepts a question and rejects empty or whitespace-only input inline.
4. Builds concise text in the form:

   ```text
   I'm studying James 1 in the Biblical Hermeneutics Framework (BHF).

   My question:
   Why is wisdom discussed in the middle of the trials section?
   ```

5. Shows the prepared text in a visible, selectable fallback area.
6. Provides `Copy Question & Open BHF` as the primary action, plus manual copy and open-destination fallback actions.

The handoff never embeds, scrapes, automates, or prepopulates the external assistant through undocumented query parameters.

## Browser-security behavior

The primary click reserves a new tab synchronously with `window.open` so the action originates in the user gesture. Clipboard writing is attempted with the supported browser API and handled as a normal UI outcome. If copy fails, the prepared text remains visible/selectable and the user receives an actionable manual-copy message. If popup opening is blocked, the modal keeps the question and exposes a normal `Open BHF` link/button. No exception text is shown to end users.

The modal reuses existing dialog and mobile viewport conventions, constrains its height on small screens, allows internal scrolling for long questions, keeps the textarea and actions reachable with the keyboard open, and remains compact on desktop.

## Tests and verification

- Add unit tests for handoff text generation, current-reference resolution, empty-question handling, configurable URL use, clipboard success/failure, and popup fallback without testing mocks instead of behavior.
- Update frontend tests so removed provider settings/state and provider calls are absent.
- Update Python web tests for runtime configuration and removal of runtime inference routes while preserving deterministic study routes.
- Replace GUI Ask tests with desktop and mobile modal/handoff coverage, including navigation from one chapter to another and checking the new chapter context.
- Preserve and run Commentary v1.2 frozen-release verification plus a before/after protected-artifact comparison.
- Run relevant frontend/backend tests, package/build checks, and browser verification with console-error inspection.
- Search final repository/UI for OpenRouter, Ollama, BYO-model, provider settings, API-key, local-model, and internal-AI terminology; classify remaining references as maintainer-only or historical/docs.

## Documentation

Update the architecture/runtime documentation, `.env.example`, Docker/deployment documentation, and relevant README guidance to explain:

```text
BHF runtime              deterministic study/evidence platform
External BHF assistant   conversational synthesis and follow-up
```

Document `BHF_ASSISTANT_URL` and state that the current destination is hosted in ChatGPT but configurable for future assistant surfaces. Do not document end-user provider configuration.

## Non-goals

- No new verse-selection subsystem.
- No assistant iframe or ChatGPT automation.
- No new general configuration framework.
- No changes to frozen Commentary v1.2 content or release artifacts.
- No deletion of maintainer model/generation infrastructure without import/use evidence.
