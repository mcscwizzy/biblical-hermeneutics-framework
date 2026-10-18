# NE-7R3 Commentary dependency and data-flow audit

Audit baseline: local NE-7R2 parent `26938c76b4ea813d728e156b3702b81ec6342ec0`, checked out on `refactor/narrative-explorer-ne7r3-commentary-retirement`. The working tree was clean before this audit. No application code or data was changed while tracing dependencies.

## Executive finding

The repository contains two different Commentary systems. The compiled BHF chapter release is the reader feature being retired. `framework.commentary.service.CommentaryService` is the separate SQLite-backed Tyndale Open Study Notes service; it is user-visible in the reader and Companion and is also available as selective secondary evidence to the agent. It must remain.

The `framework.commentary` namespace also contains BHF generation, reconciliation, publishing, and certification tools. Those tools use `bhf_agent.chapter_commentary` and frozen `.bhf-data` releases. The v1.1 pipeline state is already `CORPUS_COMPLETE` (935/935 eligible chapters; 1,189 runtime chapters). The audit ran `python3 -m framework.commentary.orchestrator status` after reading its state file. No stage was advanced, no evidence was changed, and the pipeline is to remain at `CORPUS_COMPLETE`.

## System A: compiled BHF chapter Commentary

### Data and runtime path

1. Generated chapter records are represented and read by `bhf_agent/chapter_commentary/` (28 Python files, 948,137 source bytes). The compiler, release validator, evidence bundler, and production pipeline also import this package. It is not only reader code.
2. Published release trees in `.bhf-data/bhf-commentary`, `.bhf-data/bhf-commentary-v1.1`, and `.bhf-data/bhf-commentary-v1.2` contain 1,192, 1,190, and 974 tracked files respectively. They occupy 1,575,836, 4,255,616, and 3,793,546 bytes in this checkout.
3. `bhf_agent/runtime_paths.py` resolves `BHF_COMMENTARY_RELEASE` and `BHF_COMMENTARY_STORAGE_PATH` to a release tree. `bhf_web/settings.py` exposes that as `BHF_COMMENTARY_STORAGE_PATH`; `bhf_web/app.py` passes it to the compiled reader and coverage route registrations.
4. `bhf_web/services/bhf_commentary.py` reads chapter records from `bhf_agent.chapter_commentary.storage`, projects prose and references, and uses the chapter evidence bundler for its evidence route. `bhf_web/routes/bhf_commentary.py` exposes:
   - `GET /api/bhf-commentary/diagnostics`
   - `GET /api/bhf-commentary/search`
   - `GET /api/bhf-commentary/{book}/{chapter}`
   - `GET /api/bhf-commentary/{book}/{chapter}/evidence`
5. The Companion template `bhf_web/templates/index.html` contains the hidden “BHF Context” card. It loads `bhf_web/static/bhf-commentary-card.js`, which calls the chapter and evidence APIs and wires verse navigation plus note, highlight, and translation-comparison shortcuts. The card is independent of the Tyndale tab below it.
6. The reader formerly registered `/internal/commentary-coverage` and `/api/internal/bhf-commentary/coverage`. The local `bhf_web.services.commentary_coverage` snapshot function is also used by the standalone commentary and CKL reporting tools, so that developer reporting function remains while its reader routes and template are retired.
7. Release identity is injected to the browser as `commentaryRelease` by `bhf_web/runtime.py`; `bhf_web/static/api/http.js` uses that release identity for generated-commentary API cache handling. `bhf_web/static/sw.js`, `bhf_web/offline.py`, and the card asset list the compiled card or its API prefix. Compiled-card styling is in `bhf_web/static/styles/companion.css`; coverage styling is in `bhf_web/static/styles/layout.css`.
8. `pyproject.toml` packages `bhf_agent/data/commentary-v1.2/` and its release manifests. This copy has 974 tracked files and occupies 3,519,570 bytes. It is the published v1.2 reader fallback, distinct from `.bhf-data` development and certification artifacts.

### Packaging facts and preserved artifacts

The current `.vercelignore` contains `.bhf-data/**`; the published, candidate, and production `.bhf-data` trees are excluded from the Git deployment source already. They are also used by release auditing and reproducibility tooling: `tools/commentary_artifact_inventory.py` classifies the v1.1/v1.2 trees as active release inputs, and the v1.2 promotion/freeze tools and `framework.commentary` publisher refer to them. Therefore this retirement will not delete or broadly filter `.bhf-data`. The obsolete packaged copy under `bhf_agent/data/commentary-v1.2/` is the runtime package payload and can be removed once the reader no longer selects it; Git history and retained `.bhf-data` release inputs preserve recovery.

The package finder includes `bhf_agent.chapter_commentary` because generation and certification tools still use it. It will remain in the repository for that purpose. Runtime retirement removes the web import/loading edge; it does not delete CKL source objects, cited evidence, the production pipeline, or frozen provenance.

## System B: SQLite-backed Tyndale Open Study Notes

### Data and runtime path

1. `framework/commentary/database_schema.py`, `repository.py`, `models.py`, `service.py`, and `evidence.py` define a separate normalized SQLite store and read-only lookup service. Its standalone/importer default is `.bhf/commentary.sqlite`.
2. The web app resolves `RuntimeDataPaths.commentary_db_path` from `BHF_COMMENTARY_DB_PATH`, otherwise `<runtime data dir>/commentary.sqlite` (normally `.bhf-data/commentary.sqlite` locally or `/tmp/bhf-data/commentary.sqlite` on Vercel). `bhf_web/app.py` passes this path to `bhf_web/routes/commentary.py` and `CompanionContextService`. The API is:
   - `GET /api/commentary/diagnostics`
   - `GET /api/commentary/{book}/{chapter}`
3. The reader keeps `bhf_web/static/commentary.js`, the `Tyndale Study Notes` panel in `index.html`, and the Companion resource-router mapping for the persisted `commentary` resource ID. These read only `/api/commentary/*`.
4. `bhf_web/services/companion_context.py` includes Tyndale availability/counts in Companion resource context. `bhf_agent/runner.py` constructs `framework.commentary.evidence.TyndaleEvidenceProvider` and selectively retrieves explicitly requested or gap-relevant Tyndale notes. Agent configuration uses `CommentaryConfig.database_path`; it is a Tyndale setting, not a generated BHF release selector.
5. The local checkout contains `.bhf/commentary.sqlite` (22,499,328 bytes); the web default `.bhf-data/commentary.sqlite` is absent in this checkout unless configured. Neither file is part of this retirement. The distinct CKL SQLite index is `.bhf/ckl.sqlite`; the protected study database used by the web runtime is `.bhf-data/study.sqlite`.

**Decision:** preserve this service, both API routes, the reader panel, Companion navigation, agent provider, database schema, import tooling, and the `framework.commentary` Python package. Removing them would remove the explicitly preserved Tyndale Study Notes experience and selective Tyndale evidence path.

## Narrative Explorer and neighboring reader features

`BHF_NARRATIVE_EXPLORER_ENABLED` defaults to `false` in `bhf_web/runtime.py`. When enabled, `index.html` loads `narrative-explorer.js` and shows the Companion “Explore the Narrative” entry. `resource-router.js` calls `/api/narrative-explorer/v1/passages/{book}/{chapter}`; the route/service use the shared CKL provider and current Maps/archaeology integrations. This is the primary BHF contextual evidence entry when enabled; it does not synthesize replacement prose.

The Bible translation routes/data, Tyndale panel/API, Maps, archaeology, lexical lookup, CKL/Evidence Trails, timelines, notes, highlights, and optional Study-pack behavior have no dependency on the compiled chapter projection service. Their existing routes/data and reader navigation must remain. The translation-comparison fallback in `htmx-lite.js` currently targets the soon-to-be-removed BHF card status node; that small error-reporting edge must be redirected or removed while preserving the comparison action.

## Retirement behavior for existing consumers

The compiled BHF endpoints and coverage paths have no first-party caller after their UI and runtime imports are removed, but may have external callers. The selected explicit compatibility behavior is HTTP `410 Gone` with a stable `feature_retired` response and a clear message. This changes `/api/bhf-commentary/*`, `/internal/commentary-coverage`, and `/api/internal/bhf-commentary/coverage` from their prior generated-content responses to JSON 410 responses; consumers must remove those integrations or use the optional Narrative Explorer interface. The payload will not contain a generated summary and will not proxy or reinterpret the request through Narrative Explorer. `/api/commentary/*` remains the separate Tyndale API.

## Baseline measurements and known test state

- `bhf_agent/data/commentary-v1.2/`: 974 tracked files, 3,519,570 bytes.
- Baseline Python wheel: 49,502,734 compressed bytes; install target: 82,423,044 bytes, measured by building and installing the wheel without dependencies in `/tmp/bhf-ne7r3-baseline`.
- Baseline `from bhf_web.app import app`: 5 fresh Python 3.12.3 processes, median 1,304.99 ms (1,299.01–1,329.04 ms); `BHF_STUDY_DB_READ_ONLY=1`.
- Baseline focused reader/runtime test group: 64 passed, 8 skipped, 3 subtests passed, 1 failed. The pre-existing failure is `tests/test_vercel_packaging.py::test_vercel_ignore_preserves_required_runtime_paths`: its expected `.bhf-data/bhf-commentary-v1.1` deployment files are excluded by the current `.vercelignore` rule `.bhf-data/**`. NE-7R2 documentation had already identified this packaging assertion mismatch. Retirement tests will assert the new runtime contract and will not relabel the failure as resolved before rerunning.
- Protected `.bhf-data/study.sqlite` SHA-256 at audit start: `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf` (3,416,064 bytes). The existing NE-7R2 integrity report records 687 CKL objects and inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`; both will be verified again after the retirement.

No CKL source attestation or fingerprint check has been weakened. No SQLite database or schema has been modified.
