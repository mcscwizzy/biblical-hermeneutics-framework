# Ask BHF Desktop Clipboard Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix desktop Ask BHF clipboard timing and provide accurate, accessible recovery when clipboard permission or popup behavior varies by browser.

**Architecture:** Keep the existing handoff controller and dialog. Begin the clipboard operation synchronously in the primary click handler, attempt the external destination immediately without awaiting, and keep the protected Open BHF link available because the popup return value is ambiguous with `noopener`.

**Tech Stack:** Existing vanilla JavaScript, Node.js `node:test`, Selenium browser tests, Jinja template, Markdown documentation.

**Spec:** `docs/superpowers/specs/2026-11-01-ask-bhf-desktop-clipboard-design.md`

## Global Constraints

- Preserve passage context, mobile behavior, accessibility, the configured GPT destination, and `noopener noreferrer`.
- Never report copy success unless the clipboard promise resolves successfully.
- Keep failed-copy text visible and manually selectable.
- Limit changes to Ask BHF handoff code, tests, its cache key, and documentation.

## Review Focus

- Clipboard initiation must precede a popup attempt that can shift focus; assert invocation order in Node and desktop browser tests.
- A clipboard promise may reject after simulated focus loss; assert visible text selection and the manual-copy plus Open BHF recovery controls.
- A `null` popup return may still represent a successful `noopener` open; assert it does not produce a blocked-popup claim and retains the fallback link.
- Copy success must only be announced after promise resolution; assert rejection copy feedback contains no success claim.
- The fallback link must retain the configured HTTPS destination and `noopener noreferrer`; assert its attributes in browser coverage and URL handling in frontend coverage.

---

### Task 1: Frontend handoff behavior and controller

**Files:**
- Modify: `tests/frontend/assistant-handoff.test.js`
- Modify: `bhf_web/static/assistant-handoff.js`

**Interfaces:**
- Consumes: Existing `create(options)` controller and injected `openWindow` / `writeClipboard` functions.
- Produces: Clipboard invocation before popup attempt, accurate copy feedback, and an explicit Open BHF fallback independent of `window.open`'s return value.

- [x] Write failing tests for clipboard-before-popup ordering, `null` popup results, visible Open BHF fallback, and manual recovery after rejected clipboard writes.
- [x] Run `node --test tests/frontend/assistant-handoff.test.js` and confirm the new expectations fail against the current implementation.
- [x] Update the controller to initiate clipboard writing synchronously before the popup attempt, avoid awaiting before `openWindow`, always expose the fallback after a valid attempt, and report copy success only after success.
- [x] Re-run the focused frontend test and confirm the expectations pass.

### Task 2: Desktop browser regression and release documentation

**Files:**
- Modify: `tests/gui/test_ask.py`
- Modify: `bhf_web/templates/index.html`
- Modify: `docs/assistant-handoff.md`

**Interfaces:**
- Consumes: Current Ask BHF dialog and browser test fixtures.
- Produces: A desktop regression for post-focus-loss clipboard failure, a fresh JavaScript cache key, and user-facing recovery documentation.

- [x] Add a desktop browser test whose `writeText` promise rejects after the popup attempt simulates focus loss; assert invocation order, selectable prepared text, visible Copy prepared question and Open BHF controls, and no false copy-success status.
- [x] Run the focused browser test and confirm it fails against the old event ordering.
- [x] Bump the `assistant-handoff.js` query version and document the secure popup attempt, ambiguous popup return, and two-step recovery.
- [x] Run `node --test tests/frontend/assistant-handoff.test.js` and `.venv/bin/pytest tests/gui/test_ask.py tests/gui/test_mobile_layout.py::test_mobile_ask_submit_still_works -q -k 'not test_escape_closes_handoff_without_collapsing_companion'`.
- [x] Review `git diff --check`, the full diff, final branch status, and record the verification results in `docs/assistant-handoff.md`.
