# BHF Assistant Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Remove end-user runtime BYO AI from BHF and replace it with a generic, context-aware Ask BHF clipboard handoff to an external assistant.

**Architecture:** Keep bhf_agent providers, adapters, commentary generators, and release tooling available for maintainer workflows. Remove their web-runtime consumers and replace the web Ask surface with a browser-only handoff utility that reads current selection state, builds concise text, copies it, and opens a configurable assistant destination.

**Tech Stack:** FastAPI, Jinja2, vanilla JavaScript, Node node:test, pytest, Selenium GUI tests, Docker Compose.

**Spec:** docs/superpowers/specs/2026-09-16-assistant-handoff-design.md

## Global Constraints

- Start from origin/master after the Commentary v1.2 merge on feat/assistant-handoff.
- Do not modify frozen Commentary v1.2 artifacts, release manifest, frozen descriptor, lineage state, tag, hashes, or content.
- Do not modify CKL records.
- No runtime LLM/provider call may occur while browsing, opening the modal, preparing handoff text, or using deterministic study tools.
- Preserve maintainer generation, renderer qualification, evaluation, and release-engineering model tooling unless import/use evidence proves it obsolete.
- Use generic names such as assistantUrl and BHF_ASSISTANT_URL; do not introduce provider-specific application abstractions.
- Do not add an iframe, undocumented assistant query parameters, scraping, or automation of the external assistant.
- Use existing selection state; do not build a new verse-selection subsystem.
- Write each new behavior test before its production implementation and verify the intended red state.

## File Map

### Create

- bhf_web/static/assistant-handoff.js — formatting helpers and modal handoff controller.
- tests/frontend/assistant-handoff.test.js — formatter, modal, clipboard, popup, and no-network tests.
- tests/test_assistant_handoff.py — runtime configuration and route-boundary tests.

### Modify or delete after import audit

- bhf_web/runtime.py, bhf_web/app.py, bhf_web/routes/study.py, and bhf_web/routes/debug.py — public runtime configuration, route registration, deterministic study routes, and removal of web provider setup.
- bhf_web/templates/index.html, bhf_web/static/study-companion.js, and CSS files — replace internal Ask UI and add responsive handoff modal.
- bhf_web/static/companion-context.js, companion-context-controller.js, htmx-search.js, maps/MapPanelSearch.js, and sw.js — remove browser provider/presentation plumbing while preserving deterministic/offline behavior.
- bhf_web/routes/ask.py, bhf_web/jobs.py, bhf_web/forms.py, bhf_web/ai_config.py, bhf_web/presentation_runtime.py, and bhf_web/services/web_helpers.py — remove web-only inference code; extract deterministic search fallback if it shares job code.
- .env.example, docker-compose.yml, docker-compose.ollama.yml, Dockerfile, and vercel.json — remove runtime provider defaults and add public assistant URL where applicable.
- README.md, docs/architecture.md, docs/web-pwa.md, docs/local-development.md, docs/docker.md, and docs/deployment-routing.md — document the deterministic/external-assistant boundary.
- Existing runtime-AI tests, GUI Ask page objects, and affected companion tests — replace deleted behavior assertions; retain maintainer generation/provider tests.

### Preserve

- bhf_agent/adapters, bhf_agent/providers, bhf_agent/runner.py, bhf_agent/chapter_commentary, framework/commentary, model validation, prompts, evaluations, and release tests.
- Frozen .bhf-data Commentary v1.2 corpus/release artifacts and all protected hashes.

---

### Task 1: Reconfirm release boundary and capture baseline

Files: none.

- [ ] Verify the isolated worktree is feat/assistant-handoff, based on origin/master at 7ae5e1560d16a1453e0064c05933949669fa6048, and that commentary-v1.2 is an ancestor. Run:
  git branch --show-current
  git rev-parse HEAD
  git merge-base --is-ancestor commentary-v1.2 HEAD
  git status --short --branch
- [ ] Snapshot protected paths:
  git diff --name-status commentary-v1.2..HEAD -- .bhf-data docs/commentary-v1.2-release.json bhf_agent/data/commentary-v1.2
  Expected: no implementation changes touch frozen paths.
- [ ] Run npm test and the frozen v1.2 pytest tests. The known baseline is 9 frontend suites and 13 frozen tests; rerun the broader web tests in focused slices because the initial combined baseline did not return a final result.
- [ ] Do not commit code in this task. Carry the evidence into the final report.

### Task 2: Add generic assistant destination configuration

Files:
- Create tests/test_assistant_handoff.py.
- Modify bhf_web/runtime.py, tests/test_web_app.py, and .env.example.

Interface: load_runtime_config()[assistantUrl] reads BHF_ASSISTANT_URL, defaulting to the supplied ChatGPT URL. Serialized runtime config contains no ai, provider, model, or credential object.

- [ ] Write failing tests:
  test_runtime_config_exposes_generic_assistant_destination: with BHF_ASSISTANT_URL absent, assert config["assistantUrl"] starts with https://chatgpt.com/ and config does not contain "ai".
  test_runtime_config_uses_configured_assistant_destination: set BHF_ASSISTANT_URL to https://assistant.example/bhf and assert the exact value is returned.
- [ ] Run pytest -q tests/test_assistant_handoff.py -k assistant_destination and confirm the missing key/old AI config causes failure.
- [ ] Add a trimmed public URL default/read to bhf_web/runtime.py; remove browser_ai_config() and provider labels from browser runtime output while preserving backend, offline, commentary, and study-vault fields.
- [ ] Add to .env.example:
  BHF_ASSISTANT_URL=https://chatgpt.com/g/g-6a36d3641a1c8191afa101ed50a927e9-biblical-hermeneutics-framework-bhf
- [ ] Run the focused tests, then commit:
  git add bhf_web/runtime.py tests/test_assistant_handoff.py tests/test_web_app.py .env.example
  git commit -m "feat: configure generic Ask BHF destination"

### Task 3: Build handoff formatter and controller with TDD

Files:
- Create bhf_web/static/assistant-handoff.js and tests/frontend/assistant-handoff.test.js.

Interfaces:
- window.BHFAssistantHandoff.formatReference(selection) returns a string.
- window.BHFAssistantHandoff.buildHandoffText({reference, question}) returns a string.
- window.BHFAssistantHandoff.create(options) returns an object with open, close, and prepare.

- [ ] Write failing formatter tests. formatReference({book:"James", chapter:1, reference:"James 1:2-4"}) must return "James 1:2-4"; when reference is "James 2" it must return "James 2". buildHandoffText with question " Why wisdom? " must return:
  I'm studying James 1 in the Biblical Hermeneutics Framework (BHF).

  My question:
  Why wisdom?
  Blank/whitespace-only questions must throw a user-facing validation error.
- [ ] Run node --test tests/frontend/assistant-handoff.test.js and confirm failure because the API is missing.
- [ ] Implement pure reference resolution: use selection.reference when present, otherwise use the current book and chapter. Trim only the question envelope and add no large methodology prompt.
- [ ] Write failing controller tests for current selection on open, no fetch/network side effect, successful copy and configured URL, clipboard failure with visible/selectable text, and popup-blocked explicit-open fallback. Inject getSelection, openWindow, writeClipboard, and DOM nodes so tests exercise behavior.
- [ ] Run the controller tests and confirm the missing controller behavior fails.
- [ ] Implement the controller. Open the dialog from current selection; reserve the popup synchronously on the primary click; attempt clipboard copy; keep prepared text visible; report friendly status; expose manual copy and explicit open fallback.
- [ ] Run node --test tests/frontend/assistant-handoff.test.js, then commit:
  git add bhf_web/static/assistant-handoff.js tests/frontend/assistant-handoff.test.js
  git commit -m "feat: add context-aware Ask BHF handoff controller"

### Task 4: Replace internal Ask UI and wire reader context

Files: bhf_web/templates/index.html, bhf_web/static/study-companion.js, bhf_web/static/style.css and/or bhf_web/static/styles, tests/test_web_app.py, tests/gui/test_ask.py, and tests/gui/pages/ask.py.

Interface: one data-ask-bhf action opens the handoff controller; each open reads window.BHFStudySelection.getState().

- [ ] Add failing template/GUI assertions for exactly one handoff modal/action, no AI setup dialog, no provider/model controls, no data-testid="ask-submit", no model-settings script, and current chapter after James 1 to James 2 navigation.
- [ ] Run focused tests and observe old internal Ask UI failing the new assertions.
- [ ] Remove AI setup, provider/model controls, hidden AI form fields, internal Ask pane, AI presentation controls, and quick-ask form. Add a compact dialog with reference, question textarea, readonly prepared text, status, primary Copy Question & Open BHF, manual copy, explicit Open BHF, and close controls.
- [ ] Wire the companion/reader Ask action to one controller. Preserve deterministic resource/evidence cards and existing selection ownership.
- [ ] Add responsive styles: desktop max width, mobile viewport-constrained height, internal scrolling, keyboard-safe action area, focus restoration, and no horizontal overflow.
- [ ] Run npm test and these exact focused backend/GUI commands:
  npm test
  /home/johnwalker/Documents/github/biblical-hermeneutics-framework/.venv/bin/pytest -q tests/test_web_app.py -k "ask or reader_toolbar or explore_questions"
  /home/johnwalker/Documents/github/biblical-hermeneutics-framework/.venv/bin/pytest -q tests/gui/test_ask.py tests/gui/test_study_companion.py -k "ask or chapter"
- [ ] Commit the UI replacement:
  git add bhf_web/templates/index.html bhf_web/static/study-companion.js bhf_web/static/style.css bhf_web/static/styles tests/test_web_app.py tests/gui/test_ask.py tests/gui/pages/ask.py
  git commit -m "feat: replace internal Ask workspace with handoff modal"

### Task 5: Remove web-runtime inference surface while preserving maintainer tooling

Files: bhf_web/app.py, routes/ask.py, routes/study.py, routes/debug.py, jobs.py, forms.py, ai_config.py, presentation_runtime.py, services/web_helpers.py, and affected tests.

Interface: deterministic companion-context, Bible, commentary, CKL, notes, highlights, maps, and saved-study routes remain; /api/llm/health, /ask*, and /api/study/presentation* disappear.

- [ ] Write failing route-boundary tests:
  test_runtime_app_has_no_interactive_ai_routes: create_app routes must not contain /api/llm/health, /ask or /ask/*, or /api/study/presentation*.
  test_deterministic_companion_context_route_remains: create_app routes must contain /api/study/companion-context.
- [ ] Run the route tests and confirm the old routes fail the new assertions.
- [ ] Trace imports before deletion:
  rg -n "bhf_web.(forms|ai_config|presentation_runtime|jobs)|from .jobs|BHFAgent|build_chat_adapter|run_ask_job|run_presentation_job|AskJobStore|presentation" bhf_web framework bhf_agent tests --glob "*.py"
- [ ] Remove web imports/configuration of BHFAgent, provider adapters, present_context_with_ai, register_ask_routes, and configure_presentation_runtime; remove provider CORS headers and app state.
- [ ] Remove presentation-generation endpoint/action branches and Ask/presentation job classes. If deterministic Bible-search fallback shares the job file, extract it into a focused deterministic module and preserve its route/tests.
- [ ] Delete bhf_web/ai_config.py and bhf_web/presentation_runtime.py only after the import audit proves they are web-only; do not alter bhf_agent maintainer modules.
- [ ] Update obsolete web tests while retaining provider/adapters/commentary-generation tests. Run:
  /home/johnwalker/Documents/github/biblical-hermeneutics-framework/.venv/bin/pytest -q tests/test_assistant_handoff.py tests/test_web_app.py tests/test_companion_context.py tests/test_study_actions.py tests/test_web_settings.py
- [ ] Commit the route/runtime removal:
  git add bhf_web tests/test_assistant_handoff.py tests/test_web_app.py tests/test_companion_context.py tests/test_study_actions.py tests/test_web_settings.py tests/test_ai_setup.py tests/test_job_store.py tests/test_presentation_jobs.py tests/test_presentation_runtime.py
  git commit -m "refactor: remove web runtime model inference surface"

### Task 6: Remove browser provider state and presentation plumbing

Files: delete bhf_web/static/model-settings.js after audit; modify companion-context.js, companion-context-controller.js, htmx-search.js, maps/MapPanelSearch.js, sw.js, and affected frontend tests.

- [ ] Add failing source-behavior assertions: deterministic search contains no BHFModelSettings or X-BHF-OpenRouter-Key; companion context contains no ai_profile or /api/study/presentation.
- [ ] Run node --test tests/frontend/*.test.js and confirm the assertions fail against old scripts.
- [ ] Remove provider token/model/endpoint/limit state, migrations, persistence, headers, provider health calls, AI presentation preference, and all BHFModelSettings consumers. Stale browser keys must simply be ignored.
- [ ] Remove deleted AI assets/routes from the service worker while retaining offline deterministic resources.
- [ ] Run all frontend tests and commit:
  npm test
  git add bhf_web/static tests/frontend
  git commit -m "refactor: remove browser BYO AI state and requests"

### Task 7: Clean runtime environment, dependencies, and documentation

Files: .env.example, Docker/deployment files, README/docs, and dependency tests.

- [ ] Add failing assertions for BHF_ASSISTANT_URL, absence of runtime provider defaults, and documentation describing deterministic BHF plus external assistant.
- [ ] Trace actual imports before dependency removal:
  rg -n "openai|ollama|openrouter|httpx|requests|tiktoken|litellm" pyproject.toml package.json bhf_agent bhf_web framework tests --glob "*.py" --glob "*.js" --glob "*.toml"
- [ ] Remove runtime provider defaults and obsolete Ollama runtime overlay only when no supported runtime or maintainer workflow uses them. Preserve packages/providers used by generation/release tests.
- [ ] Document BHF_ASSISTANT_URL, clipboard handoff, manual fallback, popup behavior, and offline expectation. State that current hosting is ChatGPT without making the architecture Custom GPT-specific.
- [ ] Run dependency, compose, and documentation tests:
  /home/johnwalker/Documents/github/biblical-hermeneutics-framework/.venv/bin/pytest -q tests/test_docker_compose.py tests/test_project_dependencies.py tests/test_assistant_handoff.py
- [ ] Commit the environment and documentation changes:
  git add .env.example docker-compose.yml docker-compose.ollama.yml Dockerfile vercel.json README.md docs tests/test_docker_compose.py tests/test_project_dependencies.py
  git commit -m "docs: document deterministic BHF and external assistant boundary"

### Task 8: Full verification and final audit

Files: only tests/docs/code needed to correct verified defects; never frozen Commentary v1.2 paths.

- [ ] Run relevant frontend/backend suites, build/package checks, and retained maintainer generation tests.
- [ ] Start the normal development server and use agent-browser on desktop and 390px mobile sizes. Verify reader load, Ask BHF modal, current reference, question entry, prepared text, clipboard success/fallback, popup fallback, chapter navigation freshness, and no console errors/provider requests.
- [ ] Run offline/PWA and deterministic study tests to confirm Bible, Commentary v1.2, CKL/evidence, lexicon, notes/highlights, and local resources remain usable without provider configuration.
- [ ] Search and classify leftovers:
  rg -n -i --hidden --glob "!.git/**" --glob "!*.sqlite*" "OpenRouter|Ollama|Bring Your Own Model|BYO model|AI provider|model selector|API key|Internal AI|local model" README.md docs bhf_web tests .env.example docker-compose*.yml
  Runtime/user-facing occurrences must be gone; maintainer-only and historical/docs occurrences must be identified in the final report.
- [ ] Run final frozen comparison:
  git diff --name-status commentary-v1.2..HEAD -- .bhf-data docs/commentary-v1.2-release.json bhf_agent/data/commentary-v1.2
  git diff --check
  git status --short --branch
- [ ] Use fresh command output for the final report; do not claim completion without exit codes for tests, browser verification, build, package, and Commentary v1.2 frozen verification.
