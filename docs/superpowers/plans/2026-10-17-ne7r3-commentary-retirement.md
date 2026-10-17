# NE-7R3 Legacy Commentary Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire generated BHF chapter Commentary from the reader and deployed runtime while preserving Tyndale Study Notes, CKL evidence, and the completed Commentary authoring archive.

**Architecture:** Remove the generated BHF card, its runtime projection and coverage services, release browser configuration, and packaged v1.2 prose. Keep explicit HTTP 410 compatibility responses for former public BHF paths. Preserve the separate SQLite-backed Tyndale service and authoring/audit tooling; Narrative Explorer remains the optional contextual evidence entry.

**Tech Stack:** FastAPI, Python 3.12, setuptools, Jinja templates, browser JavaScript/CSS, Service Worker, pytest, Node test runner, Firefox/Selenium, SQLite, Vercel source ignore rules.

**Spec:** `docs/narrative-explorer/ne7r3/01-commentary-dependency-audit.md` and the NE-7R3 mission in the task request.

## Global Constraints

- Base commit: `26938c76b4ea813d728e156b3702b81ec6342ec0` on branch `refactor/narrative-explorer-ne7r3-commentary-retirement`.
- Narrative Explorer remains OFF by default; it is the primary contextual BHF evidence entry only when enabled.
- Former generated BHF Commentary APIs return HTTP `410 Gone` with `feature_retired`; no generated prose or synthesized summary is returned.
- Keep `framework.commentary` Tyndale service, its reader routes, panel, Companion navigation, agent provider, SQLite schema, and importer.
- Keep `.bhf-data` unchanged, the v1.1 orchestrator at `CORPUS_COMPLETE`, and all CKL sources/evidence/provenance and SQLite databases unchanged.
- Preserve translations, Tyndale notes, Maps, archaeology, lexical lookup, timelines, Evidence Trails, notes, highlights, and offline Study packs.
- Keep `git.deploymentEnabled.master=false`; no push, merge, deploy, Vercel environment change, Commentary generation, or evidence addition.
- Preserve all CKL source-attestation, canonical inventory fingerprint, and SQLite/JSON parity checks.

## Review Focus

1. `/api/bhf-commentary/*` and coverage callers must receive an explicit 410 response with no old service or data load; `/api/commentary/*` must remain Tyndale.
2. With the Explorer flag OFF, the ordinary reader and Tyndale tab must load without a generated BHF panel or Explorer asset; with it ON, the Explorer entry/API/browser flow must work.
3. Removing BHF card controls must not remove separate translation comparison, note, or highlight actions.
4. Offline manifests and Service Worker routing must stop referencing generated BHF assets while retaining Tyndale and the optional Study pack.
5. Packaging assertions must match `.vercelignore`, keep Bible/CKL/lexical runtime resources, and report no claim about hosted function size without a Vercel build.

---

### Task 1: Retire generated BHF APIs and coverage routes

**Files:**
- Create: `tests/test_commentary_retirement.py`
- Create: `bhf_web/routes/retired_commentary.py`
- Modify: `bhf_web/app.py`
- Delete: `bhf_web/routes/bhf_commentary.py`
- Delete: `bhf_web/routes/commentary_coverage.py`
- Delete: `bhf_web/services/bhf_commentary.py`
- Delete: `bhf_web/templates/commentary_coverage.html`
- Modify: `tests/test_commentary_coverage.py`
- Delete: `tests/test_bhf_commentary_projection.py`
- Delete: `tests/test_commentary_v12_reader_integration.py`
- Modify: `tests/test_vercel_startup.py`

**Interfaces:**
- Compatibility router registers GET paths for `/api/bhf-commentary`, `/api/bhf-commentary/{path:path}`, `/internal/commentary-coverage`, and `/api/internal/bhf-commentary/coverage`.
- Each retired path returns status 410 and JSON with `reason: "feature_retired"` and a plain message. No retired route imports `bhf_agent.chapter_commentary` or reads `.bhf-data`.
- `/api/commentary/*` remains registered by `bhf_web.routes.commentary` and continues to use `CommentaryService`.

- [x] **Step 1: Write failing route tests** for diagnostics, search, chapter, evidence, coverage HTML, and coverage JSON; assert 410 and the stable retirement reason. Add assertions that Tyndale API routes remain registered.
- [x] **Step 2: Run focused tests and confirm expected failures**. Initial route test returned 200 for `/api/bhf-commentary/diagnostics`; after isolating old data lookup, that is the expected red.
- [x] **Step 3: Implement the 410 compatibility router** and remove generated service/coverage registrations and imports from `create_app()`. Preserve `bhf_web.services.commentary_coverage` as a local reporting dependency for the existing tools.
- [x] **Step 4: Run focused tests**: 24 passed across retirement, startup, coverage reporting, and authoring reconciliation tests. Removed tests that exercised only retired reader projections; retained authoring pipeline/reconciliation tests.
- [ ] **Step 5: Commit** as `refactor: retire generated BHF commentary APIs`.

### Task 2: Remove the generated card and client dependencies

**Files:**
- Modify: `bhf_web/templates/index.html`
- Delete: `bhf_web/static/bhf-commentary-card.js`
- Delete: `bhf_web/static/commentary-coverage.js`
- Modify: `bhf_web/static/api/http.js`
- Modify: `bhf_web/static/sw.js`
- Modify: `bhf_web/offline.py`
- Modify: `bhf_web/static/styles/companion.css`
- Modify: `bhf_web/static/styles/layout.css`
- Modify: `bhf_web/static/htmx-lite.js`
- Keep: `bhf_web/static/commentary.js`, `bhf_web/static/resource-router.js` Tyndale path, and the Tyndale panel/tab.
- Modify: `tests/test_narrative_explorer_ui_config.py`
- Delete: `tests/frontend/bhf-commentary-card.test.js`
- Delete: `tests/frontend/bhf-commentary-offline.test.js`
- Create: `tests/frontend/commentary-retirement.test.js`
- Modify: `tests/frontend/commentary-search.test.js` only if assertions need the retained Tyndale contract clarified.

**Interfaces:**
- Disabled UI contains no BHF Context card, BHF card script, or generated release browser config. Reader and Tyndale Study Notes remain available.
- Enabled UI exposes the existing “Explore the Narrative” Companion entry and loads the existing Narrative Explorer asset/API.
- Tyndale resource id `commentary` continues to call `/api/commentary/*`.
- Translation comparison fallback no longer targets the removed BHF status node; the comparison action remains available.

- [x] **Step 1: Add failing template/Node assertions** for absence of the generated card/assets and presence of the Tyndale and feature-off reader controls.
- [x] **Step 2: Run focused Python and Node tests** and confirm expected failures: the rendered page still contained `BHF Context`, and Compare Translations only existed inside that card.
- [x] **Step 3: Remove the generated card and coverage UI, cache prefixes, and styles; repair the translation-comparison fallback.** Kept the Tyndale reader and Companion route intact, and put a direct translation comparison control in the Companion overview.
- [x] **Step 4: Run focused tests**: reader and retirement Python checks → 6 passed; `npm test` → 12 passed.
- [ ] **Step 5: Commit** as `refactor: remove generated commentary reader panel`.

### Task 3: Remove compiled release runtime packaging

**Files:**
- Modify: `bhf_web/runtime.py`
- Modify: `bhf_web/settings.py`
- Modify: `bhf_web/app.py` if any old storage constant remains
- Modify: `bhf_web/static/api/http.js` if any release identity remains
- Modify: `bhf_agent/runtime_paths.py` only if a web-only selector can be removed without breaking publisher/audit tools; retain authoring path helpers still used by `framework.commentary.publish` and release tooling.
- Modify: `pyproject.toml`
- Delete: all tracked files under `bhf_agent/data/commentary-v1.2/` (974 files, 3,519,570 bytes)
- Modify: `.vercelignore` to exclude proven development-only `tools/**` and `bhf_agent/chapter_commentary/**` from deployment source after Task 1 removes the only web runtime imports; do not edit `vercel.json` or its master deployment guard.
- Modify: `tests/test_web_settings.py`
- Modify: `tests/test_vercel_packaging.py`
- Modify: `tests/test_vercel_startup.py`

**Interfaces:**
- Browser runtime config has no `commentaryRelease` key; generated release selection is not available to the reader.
- Tyndale `commentary_db_path` and `BHF_COMMENTARY_DB_PATH` remain.
- Internal release helpers needed by completed Commentary generation/audit/publish tooling remain explicitly development-only.
- Vercel source packaging excludes `.bhf-data` (existing), generation-only `bhf_agent/chapter_commentary`, and the `tools` directory (after proving no live app import remains).

- [ ] **Step 1: Add failing tests** asserting the browser config omits `commentaryRelease`, the wheel source no longer has the v1.2 package-data tree, Vercel source excludes generation-only tools, and Tyndale database path resolution remains.
- [ ] **Step 2: Run focused tests and confirm expected failures.**
- [ ] **Step 3: Remove only web runtime selection and v1.2 package data.** Preserve `.bhf-data`, publisher helpers, authoring modules, and all Bible/CKL/lexical package data.
- [ ] **Step 4: Rebuild and install a no-dependency wheel in `/tmp`; measure compressed wheel bytes, installed payload bytes, and ignored Vercel source bytes.** Compare to the baseline captured in Task 1's audit.
- [ ] **Step 5: Run focused settings, Vercel packaging, and Vercel startup tests.**
- [ ] **Step 6: Commit** as `chore: remove retired commentary runtime package data`.

### Task 4: Regression, integrity, performance, and report

**Files:**
- Create: `docs/narrative-explorer/ne7r3/02-feature-retirement.md`
- Create: `docs/narrative-explorer/ne7r3/03-runtime-package-reduction.md`
- Create: `docs/narrative-explorer/ne7r3/04-reader-regression-results.md`
- Create: `docs/narrative-explorer/ne7r3/05-post-retirement-performance.md`
- Update applicable active documentation without rewriting certified Commentary prose or historical audit claims.

**Interfaces:**
- Reports give exact removed files/APIs, retained data/services, status codes, bytes removed, and Vercel staging versus unverified hosted function size.
- Performance comparisons use equivalent NE-7R2 local methods for app import, reader startup, Genesis 2:8 process-cold/warm SQLite retrieval, concurrent Companion/Explorer startup, John 2 Maps, and Firefox startup.
- Integrity report compares source inventory count/fingerprint, claims/evidence/source hashes, SQLite/JSON parity, protected database hashes, and retrieval parity before/after.

- [ ] **Step 1: Run the task-specific Python tests** for Tyndale/Companion, NE API and map matching, CKL provider concurrency, Evidence Trails, Maps, archaeology, lexical lookup, translations, offline packs, and packaging.
- [ ] **Step 2: Run browser acceptance** for the ordinary Firefox reader, feature-off navigation, feature-on Narrative Explorer, and retained Companion/Tyndale flow; record outcomes and skips exactly.
- [ ] **Step 3: Run `npm test` and the offline Study-pack installation/regression tests.**
- [ ] **Step 4: Re-run source attestation, 687-object inventory/fingerprint, CKL SQLite/JSON parity and Genesis 2:8 response hash; verify protected study/CKL/Tyndale databases are byte-identical.** Run the v1.1 orchestrator `status` only and confirm it remains `CORPUS_COMPLETE`.
- [ ] **Step 5: Write the four results documents** with exact actual outcomes, existing failure identities, package/staging bytes, and local-only limitations.
- [ ] **Step 6: Review the full diff and commit** as `docs: record NE-7R3 commentary retirement results`.
