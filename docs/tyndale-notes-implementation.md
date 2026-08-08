# Tyndale Open Study Notes Implementation

Status: Phase 6 — production import hardening complete

This document is the working implementation and status log for the phased Tyndale Open Study Notes integration. It is updated as each phase is completed.

## Goal and boundaries

Tyndale Open Study Notes are integrated as a separate, attributed reader companion resource. They are not part of the Canonical Knowledge Library (CKL), do not affect CKL ranking or CKL answer coverage, do not automatically enter BHFAgent prompts, and do not require an AI provider.

Target experience:

`Bible Reader | Tyndale Study Notes`

The commentary follows the current book/chapter, can focus entries overlapping a selected verse or range, and remains usable from a locally installed SQLite database.

## Phase 0 — architecture inspection (complete)

Inspected the existing repository conventions before implementation:

- `bhf_web/app.py` owns the FastAPI application, Bible routes, shared settings, templates, and route registration.
- The Bible reader is rendered by `bhf_web/templates/index.html` and controlled by `bhf_web/static/htmx-lite.js`.
- Reader book/chapter/translation state, multiple reader tabs, chapter navigation, request tokens, and verse selection already exist in the central browser controller.
- Verse selection is represented by `currentSelection` and existing `.verse.selected` elements; selection state is synchronized into the Ask form and study panels.
- Existing study panes are tabs inside the right-side `#study-panel`, with responsive drawer/minimize/expand behavior in the existing workspace CSS.
- Bible chapter data is served by `GET /api/bible/{book}/{chapter}` and uses `bhf_agent.bible.normalize_book_name` for canonical book normalization.
- Existing local/offline behavior uses the service worker in `bhf_web/static/sw.js`, API response caching, and optional offline pack descriptions in `bhf_web/offline.py`.
- Existing SQLite services use standard-library `sqlite3`, isolated database paths, repositories, and schema initialization; commentary will intentionally use a separate database and subsystem rather than extending the study/CKL schema.
- `bhf_agent/study_actions.py` is an optional deterministic study-action layer. The persistent commentary reader will not depend on it.

## Phase 1 — standalone commentary subsystem (complete)

Added `framework.commentary` with versioned SQLite schema, dataclasses, read-only repository, deterministic service, safe importer, provenance metadata, and the `import-tyndale` CLI. The database is `.bhf/commentary.sqlite` by default and generated databases remain Git-ignored.

Supported importer diagnostics include source SHA-256, counts by kind, anchor count, recognized books, warnings, and unmapped record indexes. The importer accepts structured JSON/XML/CSV/TSV members without scraping or AI processing and rejects ZIP path traversal and symlink members.

## Phase 2 — direct API and offline hooks (complete)

Added `GET /api/commentary/{book}/{chapter}` with optional `start_verse`/`end_verse` filtering. Missing commentary returns a structured HTTP 200 unavailable response. The API uses `CommentaryService`, returns source licensing/provenance once at response level and structured entries, and does not invoke AI.

Added commentary to the existing browser API cache, service-worker cacheable API paths, and offline manifest availability/client-store metadata. No separate database is merged into the existing study or CKL database.

## Phase 3 — synchronized reader companion (complete)

Added a collapsible Tyndale Study Notes pane in the existing reader layout. The existing chapter-loading request token remains authoritative for Bible navigation; commentary has its own request sequence/key guard so a stale chapter response cannot replace newer commentary. Current chapter responses are cached and adjacent chapters are lightly prefetched.

The pane follows book/chapter changes, previous/next chapter navigation, restored reader tabs, and translation-reader navigation. Existing verse and range selection state calls the companion focus logic, which highlights and scrolls the first overlapping note without hiding other notes.

## Phase 4 — documentation and validation (complete)

Added the user guide [`tyndale-study-notes.md`](tyndale-study-notes.md), linked it from the documentation index, and added focused tests in `tests/test_commentary.py`.

## Phase 5 — selective AI evidence integration (complete)

Added optional `CommentaryConfig` and a read-only `TyndaleEvidenceProvider` for
the agent pipeline. The provider is disabled by default and retrieves bounded
passage/chapter notes only for an explicit commentary/source request or a
narrowly classified historical, cultural, difficult-passage, original-audience,
or customs gap. Retrieved material is labeled `SECONDARY TYNDALE EVIDENCE`,
keeps source provenance, remains separate from CKL and lexicon context, and is
included in the cache fingerprint. Answer coverage is re-evaluated after the
secondary evidence is selected, before prompt construction and model synthesis.
No network or AI call is made by the provider.

## Phase 6 — production import hardening (complete)

Hardened the local installation workflow for real archive review:

- Import diagnostics now distinguish invalid/unrecognized records, records with
  unresolved Scripture references, and intentionally anchorless entries such as
  introductions or profiles.
- `--fail-on-unmapped` allows an operator to reject an archive before it can
  replace an installed database when any supplied Scripture reference cannot be
  mapped to BHF's canonical book names.
- Database rebuilds are written to a temporary sibling SQLite file and replaced
  atomically only after the complete import succeeds, preserving the previous
  installation on failure.
- `GET /api/commentary/diagnostics` exposes source provenance and the persisted
  import report for deployment checks without granting runtime write access.
- Importer provenance is versioned as `tyndale-2`.

## Decisions and non-goals

- Runtime database path: `.bhf/commentary.sqlite`, configurable for tests and deployments.
- Runtime lookup uses indexed SQLite queries and structured Python models; it does not load the full corpus into memory.
- The importer accepts a locally downloaded official archive, never scrapes a website, preserves source wording, records provenance, and rejects unsafe ZIP paths.
- No semantic search, network calls, LLM calls, CKL mutations, or automatic AI evidence injection are part of Phase 1.

## Implementation updates

- Added `CommentaryConfig` with opt-in enablement, database path, entry limit, and explicit/gap routing controls.
- Added `framework.commentary.evidence.TyndaleEvidenceProvider` and attributed prompt formatting.
- Added runner metadata for eligibility, retrieval, provenance, coverage reassessment, and cache identity.
- Added focused provider and end-to-end prompt routing tests in `tests/test_tyndale_evidence.py`.
- Added atomic import replacement, unmapped-reference reporting, CLI rejection,
  and runtime diagnostics coverage.

## Validation log

- Targeted command: `.venv/bin/pytest -q tests/test_commentary.py`
- Result: 6 passed.
- Reader/offline regression command: `.venv/bin/pytest -q tests/test_web_app.py -k 'not shadow_prompt_preview'`
- Result: 97 passed, 1 deselected.
- Study database regression command: `.venv/bin/pytest -q tests/test_notes.py -k 'not v1_database_migrates_to_saved_studies'`
- Result: 23 passed, 1 deselected.
- JavaScript syntax command: `node --check bhf_web/static/commentary.js`
- Result: passed.
- Combined relevant command: `.venv/bin/pytest -q tests/test_commentary.py tests/test_web_app.py tests/test_notes.py tests/test_study_actions.py`
- Result: 144 passed, 1 skipped, 2 unrelated baseline failures. The failures were `test_ask_result_shows_shadow_prompt_preview_when_ckl_runs_in_shadow_mode` (existing CKL wording assertion) and `test_v1_database_migrates_to_saved_studies` (existing migration list expects 14 while the repository currently emits 15). No commentary test failed.
- Source archive mapping limitation: no official Tyndale archive was present in this repository or attachment, so the importer was implemented to inspect the supplied archive at import time and report unmapped records rather than assuming a third-party conversion. The first archive should be reviewed against its actual record structure before enabling a production import workflow.
- Phase 5 focused command: `.venv/bin/pytest -q tests/test_tyndale_evidence.py`
- Result: 3 passed.
- Phase 6 focused command: `.venv/bin/pytest -q tests/test_commentary.py tests/test_tyndale_evidence.py`
- Result: 10 passed.
- Import compatibility check: `.venv/bin/python -c 'from framework.commentary.service import CommentaryService; from bhf_agent import BHFAgent'`
- Result: passed; the runner is now lazy-loaded so standalone commentary imports do not create a circular import.
- Runner regression check: `.venv/bin/pytest -q tests/test_runner.py --maxfail=1`
- Result: blocked by the existing local CKL database schema mismatch (database version 1, runtime requires version 2); no commentary assertion was reached.
